/**
 * Gemini Image Studio — Side Panel
 */

'use strict';

const $ = (id) => document.getElementById(id);

const projectNameInput = $('projectName');
const sceneInput = $('sceneInput');
const validateBtn = $('validateBtn');
const startBtn = $('startBtn');
const stopBtn = $('stopBtn');
const validationMsg = $('validationMsg');
const statusDot = $('statusDot');
const statusText = $('statusText');
const openGeminiBtn = $('openGeminiBtn');
const queueSection = $('queueSection');
const queueList = $('queueList');
const queueSummary = $('queueSummary');
const progressSection = $('progressSection');
const progressFill = $('progressFill');
const progressFraction = $('progressFraction');
const stepMsg = $('stepMsg');
const maxRetriesInput = $('maxRetries');
const failureRetryMaxInput = $('failureRetryMax');
const jobDelaySecInput = $('jobDelaySec');
const generationTimeoutSecInput = $('generationTimeoutSec');
const retryFailedBtn = $('retryFailedBtn');
const galleryProjectNameInput = $('galleryProjectName');
const galleryStats = $('galleryStats');
const galleryList = $('galleryList');
const scanBtn = $('scanBtn');
const downloadAllBtn = $('downloadAllBtn');
const projectAssetInfo = $('projectAssetInfo');
const promptTemplateInput = $('promptTemplate');
const stylePrefixInput = $('stylePrefix');
const characterLibraryInput = $('characterLibrary');
const referenceUpload = $('referenceUpload');
const referenceList = $('referenceList');
const saveStudioBtn = $('saveStudioBtn');
const studioMsg = $('studioMsg');
const exportProjectNameInput = $('exportProjectName');
const exportStats = $('exportStats');
const exportMetadataBtn = $('exportMetadataBtn');
const exportZipBtn = $('exportZipBtn');
const refreshExportBtn = $('refreshExportBtn');
const exportMsg = $('exportMsg');
const providerSelect = $('providerSelect');
const providerHint = $('providerHint');
const exportMetadataOnComplete = $('exportMetadataOnComplete');
const exportZipOnComplete = $('exportZipOnComplete');

let queueRunning = false;
let connectedTabId = null;
let validatedJobs = [];
let scannedImages = [];
let references = [];
let activeReferenceIds = [];
let activeProviderId = 'gemini';
let providers = [];

document.addEventListener('DOMContentLoaded', async () => {
  await restoreState();
  await loadProviders();
  await loadStudioConfig();
  await loadReferences();
  initTabs();
  bindEvents();
  checkProviderConnection();
  refreshQueueState();
  refreshProjectInfo();
  chrome.runtime.onMessage.addListener(handleRuntimeMessage);
});

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(tabId)?.classList.add('active');
      if (tabId === 'export') refreshExportInfo();
    });
  });
}

function bindEvents() {
  validateBtn.addEventListener('click', validateInput);
  startBtn.addEventListener('click', startQueue);
  stopBtn.addEventListener('click', stopQueue);
  retryFailedBtn.addEventListener('click', retryFailed);
  scanBtn.addEventListener('click', scanGallery);
  downloadAllBtn.addEventListener('click', downloadAllFromChat);
  saveStudioBtn.addEventListener('click', saveStudioConfig);
  referenceUpload.addEventListener('change', handleReferenceUpload);
  exportMetadataBtn.addEventListener('click', exportMetadata);
  exportZipBtn.addEventListener('click', exportZip);
  refreshExportBtn.addEventListener('click', refreshExportInfo);

  openGeminiBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'OPEN_PROVIDER', providerId: activeProviderId });
    setTimeout(checkProviderConnection, 2500);
  });

  sceneInput.addEventListener('input', () => {
    if (validationMsg.classList.contains('valid')) {
      clearValidation();
      startBtn.disabled = true;
      validatedJobs = [];
      renderQueuePreview([]);
    }
  });

  projectNameInput.addEventListener('change', () => {
    persistSettings();
    refreshProjectInfo();
    if (exportProjectNameInput && !exportProjectNameInput.value) {
      exportProjectNameInput.value = projectNameInput.value;
    }
  });

  [
    maxRetriesInput,
    failureRetryMaxInput,
    jobDelaySecInput,
    generationTimeoutSecInput,
    projectNameInput,
    providerSelect,
    exportMetadataOnComplete,
    exportZipOnComplete,
  ].forEach((el) => {
    if (el) el.addEventListener('change', persistSettings);
  });

  if (providerSelect) {
    providerSelect.addEventListener('change', () => {
      activeProviderId = providerSelect.value;
      persistSettings();
      checkProviderConnection();
    });
  }
}

async function loadProviders() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_PROVIDERS' });
  providers = response?.providers || [];

  if (!providerSelect) return;

  providerSelect.innerHTML = providers
    .map(
      (p) =>
        `<option value="${escapeHtml(p.id)}" ${p.status !== 'active' ? 'disabled' : ''}>${escapeHtml(p.name)}${p.status !== 'active' ? ` (${p.status})` : ''}</option>`
    )
    .join('');

  const active = providers.find((p) => p.id === activeProviderId && p.status === 'active');
  if (!active) {
    activeProviderId = providers.find((p) => p.status === 'active')?.id || 'gemini';
    providerSelect.value = activeProviderId;
  }

  if (providerHint) {
    const planned = providers.filter((p) => p.status !== 'active').map((p) => p.name);
    providerHint.textContent = planned.length
      ? `${providers.filter((p) => p.status === 'active').map((p) => p.name).join(', ')} active. Planned: ${planned.join(', ')}.`
      : 'Gemini and ChatGPT are supported for batch image generation.';
  }
}

async function restoreState() {
  try {
    const stored = await chrome.storage.local.get([
      'lastSceneInput',
      'projectName',
      'galleryProjectName',
      'exportProjectName',
      'maxRetries',
      'failureRetryMax',
      'jobDelaySec',
      'generationTimeoutSec',
      'activeProviderId',
      'exportMetadataOnComplete',
      'exportZipOnComplete',
    ]);
    if (stored.lastSceneInput) sceneInput.value = stored.lastSceneInput;
    if (stored.projectName) projectNameInput.value = stored.projectName;
    if (stored.galleryProjectName) galleryProjectNameInput.value = stored.galleryProjectName;
    if (stored.exportProjectName) exportProjectNameInput.value = stored.exportProjectName;
    else if (stored.projectName) exportProjectNameInput.value = stored.projectName;
    if (stored.maxRetries != null) maxRetriesInput.value = stored.maxRetries;
    if (stored.failureRetryMax != null) failureRetryMaxInput.value = stored.failureRetryMax;
    if (stored.jobDelaySec != null) jobDelaySecInput.value = stored.jobDelaySec;
    if (stored.generationTimeoutSec != null) {
      generationTimeoutSecInput.value = stored.generationTimeoutSec;
    }
    if (stored.activeProviderId) activeProviderId = stored.activeProviderId;
    if (exportMetadataOnComplete) {
      exportMetadataOnComplete.checked = stored.exportMetadataOnComplete !== false;
    }
    if (exportZipOnComplete) {
      exportZipOnComplete.checked = !!stored.exportZipOnComplete;
    }
  } catch (_) {}
}

async function persistSettings() {
  try {
    await chrome.storage.local.set({
      lastSceneInput: sceneInput.value,
      projectName: projectNameInput.value,
      galleryProjectName: galleryProjectNameInput.value,
      exportProjectName: exportProjectNameInput?.value || '',
      maxRetries: Number(maxRetriesInput.value),
      failureRetryMax: Number(failureRetryMaxInput?.value ?? 3),
      jobDelaySec: Number(jobDelaySecInput.value),
      generationTimeoutSec: Number(generationTimeoutSecInput.value),
      activeProviderId: providerSelect?.value || activeProviderId,
      exportMetadataOnComplete: exportMetadataOnComplete?.checked !== false,
      exportZipOnComplete: !!exportZipOnComplete?.checked,
    });
    activeProviderId = providerSelect?.value || activeProviderId;
  } catch (_) {}
}

function getSettings() {
  return {
    maxRetries: Math.max(0, Math.min(20, Number(maxRetriesInput.value) || 3)),
    failureRetryMax: Math.max(0, Math.min(20, Number(failureRetryMaxInput?.value) || 3)),
    jobDelaySec: Math.max(0, Math.min(300, Number(jobDelaySecInput.value) || 8)),
    generationTimeoutSec: Math.max(30, Math.min(600, Number(generationTimeoutSecInput.value) || 180)),
    providerId: providerSelect?.value || activeProviderId,
    exportMetadataOnComplete: exportMetadataOnComplete?.checked !== false,
    exportZipOnComplete: !!exportZipOnComplete?.checked,
    concurrency: 1,
  };
}

async function loadStudioConfig() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_STUDIO_CONFIG' });
  if (!response?.ok) return;

  const config = response.config;
  if (promptTemplateInput && config.promptTemplate) {
    promptTemplateInput.value = config.promptTemplate;
  }
  if (stylePrefixInput) stylePrefixInput.value = config.stylePrefix || '';
  if (characterLibraryInput && config.characterLibrary) {
    characterLibraryInput.value = JSON.stringify(config.characterLibrary, null, 2);
  }
  activeReferenceIds = config.activeReferenceIds || [];
}

async function saveStudioConfig() {
  let characterLibrary = {};
  try {
    characterLibrary = JSON.parse(characterLibraryInput.value || '{}');
  } catch (err) {
    showStudioMsg('error', `Invalid character JSON: ${err.message}`);
    return;
  }

  const response = await chrome.runtime.sendMessage({
    type: 'SAVE_STUDIO_CONFIG',
    config: {
      promptTemplate: promptTemplateInput.value,
      stylePrefix: stylePrefixInput.value,
      characterLibrary,
      activeReferenceIds,
    },
  });

  if (response?.ok) {
    showStudioMsg('valid', 'Studio config saved.');
  } else {
    showStudioMsg('error', response?.error || 'Save failed.');
  }
}

function showStudioMsg(type, message) {
  if (!studioMsg) return;
  studioMsg.className = `validation-msg ${type}`;
  studioMsg.textContent = message;
}

async function loadReferences() {
  const response = await chrome.runtime.sendMessage({ type: 'LIST_REFERENCES' });
  references = response?.references || [];
  renderReferenceList();
}

async function handleReferenceUpload(event) {
  const files = event.target.files;
  if (!files?.length) return;

  for (const file of files) {
    const dataUrl = await readFileAsDataUrl(file);
    const response = await chrome.runtime.sendMessage({
      type: 'SAVE_REFERENCE',
      name: file.name,
      mime: file.type,
      dataUrl,
    });
    if (response?.ok) {
      references.push(response.reference);
      if (!activeReferenceIds.includes(response.reference.id)) {
        activeReferenceIds.push(response.reference.id);
      }
    }
  }

  referenceUpload.value = '';
  renderReferenceList();
  await saveStudioConfig();
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function renderReferenceList() {
  if (!referenceList) return;

  if (!references.length) {
    referenceList.innerHTML = '<li class="ref-item"><span>No reference images uploaded.</span></li>';
    return;
  }

  referenceList.innerHTML = references
    .map(
      (ref) => `
    <li class="ref-item">
      <label>
        <input type="checkbox" data-ref-id="${escapeHtml(ref.id)}" ${activeReferenceIds.includes(ref.id) ? 'checked' : ''} />
        ${escapeHtml(ref.name)}
      </label>
      <button class="ref-delete" data-delete-ref="${escapeHtml(ref.id)}">Delete</button>
    </li>`
    )
    .join('');

  referenceList.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.addEventListener('change', async () => {
      const id = cb.dataset.refId;
      if (cb.checked) {
        if (!activeReferenceIds.includes(id)) activeReferenceIds.push(id);
      } else {
        activeReferenceIds = activeReferenceIds.filter((x) => x !== id);
      }
      await saveStudioConfig();
    });
  });

  referenceList.querySelectorAll('[data-delete-ref]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.deleteRef;
      await chrome.runtime.sendMessage({ type: 'DELETE_REFERENCE', id });
      references = references.filter((r) => r.id !== id);
      activeReferenceIds = activeReferenceIds.filter((x) => x !== id);
      renderReferenceList();
      await saveStudioConfig();
    });
  });
}

async function refreshProjectInfo() {
  const projectName = projectNameInput.value.trim();
  if (!projectName || !projectAssetInfo) return;

  const info = await chrome.runtime.sendMessage({ type: 'GET_PROJECT_INFO', projectName });
  if (info?.ok) {
    projectAssetInfo.textContent = `${info.assetCount} stored asset(s) in "${info.projectName}".`;
  }
}

async function refreshExportInfo() {
  const projectName = exportProjectNameInput?.value.trim() || projectNameInput.value.trim();
  if (!projectName) {
    exportStats.textContent = 'Enter a project name to see stored assets.';
    return;
  }

  const info = await chrome.runtime.sendMessage({ type: 'GET_PROJECT_INFO', projectName });
  if (!info?.ok) {
    exportStats.textContent = info?.error || 'Could not load project info.';
    return;
  }

  exportStats.textContent = `${info.assetCount} image(s) stored for "${info.projectName}". Ready for ZIP/metadata export.`;
}

async function exportMetadata() {
  const projectName = exportProjectNameInput?.value.trim() || projectNameInput.value.trim();
  if (!projectName) {
    showExportMsg('error', 'Enter a project name.');
    return;
  }

  exportMetadataBtn.disabled = true;
  const response = await chrome.runtime.sendMessage({
    type: 'EXPORT_METADATA',
    projectName,
    providerId: activeProviderId,
  });
  exportMetadataBtn.disabled = false;

  if (response?.ok) {
    showExportMsg('valid', `Metadata JSON exported for ${response.sceneCount} scene(s).`);
  } else {
    showExportMsg('error', response?.error || 'Export failed.');
  }
}

async function exportZip() {
  const projectName = exportProjectNameInput?.value.trim() || projectNameInput.value.trim();
  if (!projectName) {
    showExportMsg('error', 'Enter a project name.');
    return;
  }

  exportZipBtn.disabled = true;
  showExportMsg('', 'Building ZIP…');

  const response = await chrome.runtime.sendMessage({
    type: 'EXPORT_ZIP',
    projectName,
    providerId: activeProviderId,
  });
  exportZipBtn.disabled = false;

  if (response?.ok) {
    showExportMsg('valid', `ZIP download started for "${projectName}".`);
  } else {
    showExportMsg('error', response?.error || 'ZIP export failed.');
  }
}

function showExportMsg(type, message) {
  if (!exportMsg) return;
  exportMsg.className = type ? `validation-msg ${type}` : 'validation-msg';
  exportMsg.textContent = message;
}

function updateRetryFailedButton(state) {
  if (!retryFailedBtn) return;
  const failedCount = state?.failedCount ?? state?.jobs?.filter((j) => j.status === 'failed').length ?? 0;
  retryFailedBtn.textContent = `Retry Failures (${failedCount})`;
  retryFailedBtn.disabled = queueRunning || failedCount === 0;
}

async function checkProviderConnection() {
  setConnectionState('checking', 'Checking Gemini / ChatGPT connection…');
  updateOpenButtonLabel();

  try {
    const result = await chrome.runtime.sendMessage({
      type: 'FIND_PROVIDER_TAB',
      preferredProviderId: activeProviderId,
      preferredTabId: connectedTabId,
    });

    if (!result?.ok) {
      connectedTabId = null;
      setConnectionState('error', result?.error || 'No provider tab found.');
      return;
    }

    connectedTabId = result.tabId;

    if (result.autoSwitched && result.providerId !== activeProviderId) {
      activeProviderId = result.providerId;
      if (providerSelect) providerSelect.value = activeProviderId;
      persistSettings();
    }

    setConnectionState(
      'connected',
      `Connected · ${result.providerName} · Tab #${result.tabId}${result.autoSwitched ? ' (auto-detected)' : ''}`
    );
    updateOpenButtonLabel();
  } catch (err) {
    connectedTabId = null;
    setConnectionState('error', `Connection error: ${err.message}`);
  }
}

function updateOpenButtonLabel() {
  if (!openGeminiBtn) return;
  const provider = providers.find((p) => p.id === activeProviderId);
  const name = provider?.name || 'Provider';
  openGeminiBtn.title = `Open ${name}`;
  openGeminiBtn.textContent = 'Open';
}

function setConnectionState(state, text) {
  statusDot.dataset.state = state;
  statusText.textContent = text;
}

function validateInput() {
  const parsed = SceneAdapter.parseInput(sceneInput.value);
  if (!parsed.ok) {
    showValidation('error', parsed.errors.join('\n'));
    startBtn.disabled = true;
    validatedJobs = [];
    renderQueuePreview([]);
    return null;
  }

  const projectName = projectNameInput.value.trim() || parsed.projectName;
  validatedJobs = parsed.jobs.map((job) => ({ ...job, projectName }));

  showValidation(
    'valid',
    `Valid (${parsed.format.toUpperCase()})! ${validatedJobs.length} scene(s) for "${projectName}".`
  );
  startBtn.disabled = queueRunning;
  renderQueuePreview(validatedJobs);
  persistSettings();
  return parsed;
}

function showValidation(type, message) {
  validationMsg.className = `validation-msg ${type}`;
  validationMsg.textContent = message;
}

function clearValidation() {
  validationMsg.className = 'validation-msg';
  validationMsg.textContent = '';
}

function renderQueuePreview(jobs) {
  queueSection.classList.toggle('visible', jobs.length > 0);
  queueSummary.textContent = `${jobs.length} scene${jobs.length === 1 ? '' : 's'}`;

  if (!jobs.length) {
    queueList.innerHTML = '';
    return;
  }

  queueList.innerHTML = jobs
    .map(
      (job, i) => `
    <li class="queue-item">
      <span class="queue-item-index">${String(i + 1).padStart(2, '0')}</span>
      <span class="queue-item-title">${escapeHtml(job.title)}</span>
      <span class="queue-item-file">${escapeHtml(job.characters_present || 'No characters listed')} · ${escapeHtml(job.projectName)}/${escapeHtml(job.outputFilename)}.png</span>
      <span class="queue-item-status pending">pending</span>
    </li>`
    )
    .join('');
}

function renderQueueState(state) {
  if (!state?.jobs?.length) return;

  queueSection.classList.add('visible');
  queueSummary.textContent = `${state.jobs.length} scene${state.jobs.length === 1 ? '' : 's'}`;

  queueList.innerHTML = state.jobs
    .map((job, i) => {
      const status = job.status || 'pending';
      const err = job.error ? `<span class="queue-item-error">${escapeHtml(job.error)}</span>` : '';
      return `
    <li class="queue-item status-${status}">
      <span class="queue-item-index">${String(i + 1).padStart(2, '0')}</span>
      <span class="queue-item-title">${escapeHtml(job.title)}</span>
      <span class="queue-item-status ${status}">${status}${job.attempts > 1 ? ` (${job.attempts})` : ''}</span>
      ${err}
    </li>`;
    })
    .join('');

  const running = state.jobs.find((j) => j.status === 'running');
  if (running?.progress) {
    progressSection.classList.add('visible');
    const { current, total, message } = running.progress;
    if (total) {
      const pct = Math.min(100, Math.round((current / total) * 100));
      progressFill.style.width = `${pct}%`;
      progressFraction.textContent = `${current} / ${total}`;
    }
    stepMsg.textContent = message || '';
  }
}

async function startQueue() {
  if (queueRunning) return;

  const parsed = validateInput();
  if (!parsed) return;

  await saveStudioConfig();
  await checkProviderConnection();
  if (!connectedTabId) {
    showValidation('error', 'No provider tab available.');
    return;
  }

  await persistSettings();

  queueRunning = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  validateBtn.disabled = true;
  retryFailedBtn.disabled = true;
  progressSection.classList.add('visible');
  stepMsg.textContent = 'Starting queue…';

  const response = await chrome.runtime.sendMessage({
    type: 'START_QUEUE',
    payload: {
      rawInput: sceneInput.value,
      projectName: projectNameInput.value.trim() || parsed.projectName,
      providerId: activeProviderId,
      settings: getSettings(),
      tabId: connectedTabId,
    },
  });

  if (!response?.ok) {
    finishQueueUi(`Failed to start: ${response?.error || 'unknown error'}`, true);
  }
}

function stopQueue() {
  chrome.runtime.sendMessage({ type: 'STOP_QUEUE' });
  stepMsg.textContent = 'Stopping…';
  stopBtn.disabled = true;
}

async function retryFailed() {
  if (queueRunning) return;

  await checkProviderConnection();
  if (!connectedTabId) {
    showValidation('error', 'No provider tab available.');
    return;
  }

  await persistSettings();
  const settings = getSettings();

  queueRunning = true;
  startBtn.disabled = true;
  retryFailedBtn.disabled = true;
  stopBtn.disabled = false;
  validateBtn.disabled = true;
  progressSection.classList.add('visible');
  stepMsg.textContent = 'Retrying failed scenes…';

  const response = await chrome.runtime.sendMessage({
    type: 'RETRY_FAILED',
    payload: {
      tabId: connectedTabId,
      failureRetryMax: settings.failureRetryMax,
      settings,
    },
  });

  if (!response?.ok) {
    finishQueueUi(`Retry failed: ${response?.error || 'unknown error'}`, true);
  }
}

async function refreshQueueState() {
  const state = await chrome.runtime.sendMessage({ type: 'GET_QUEUE_STATE' });
  if (state?.running) {
    queueRunning = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    validateBtn.disabled = true;
  }
  if (state?.jobs?.length) renderQueueState(state);
  updateRetryFailedButton(state);
}

async function scanGallery() {
  await checkProviderConnection();
  if (!connectedTabId) {
    galleryStats.textContent = 'No provider tab connected.';
    return;
  }

  galleryStats.textContent = 'Scanning chat…';
  scanBtn.disabled = true;

  try {
    const result = await chrome.tabs.sendMessage(connectedTabId, { type: 'SCAN_CHAT_IMAGES' });
    scannedImages = result?.images || [];
    galleryStats.textContent =
      scannedImages.length > 0
        ? `${scannedImages.length} image(s) found in current chat.`
        : 'No images found. Generate some images first.';
    downloadAllBtn.disabled = scannedImages.length === 0;
    renderGalleryList(scannedImages);
  } catch (err) {
    galleryStats.textContent = `Scan failed: ${err.message}`;
    downloadAllBtn.disabled = true;
  } finally {
    scanBtn.disabled = false;
  }
}

function renderGalleryList(images) {
  if (!images.length) {
    galleryList.innerHTML = '';
    return;
  }

  galleryList.innerHTML = images
    .map(
      (img) => `
    <li class="gallery-item">
      <img class="gallery-thumb" src="${escapeHtml(img.src)}" alt="" loading="lazy" />
      <div class="gallery-meta">
        <strong>#${img.index}</strong> · ${img.width}×${img.height}
        ${img.alt ? `<br>${escapeHtml(img.alt.slice(0, 80))}` : ''}
      </div>
    </li>`
    )
    .join('');
}

async function downloadAllFromChat() {
  await checkProviderConnection();
  if (!connectedTabId) {
    galleryStats.textContent = 'No provider tab connected.';
    return;
  }

  const projectName = galleryProjectNameInput.value.trim() || 'gemini_chat_export';
  await persistSettings();

  downloadAllBtn.disabled = true;
  scanBtn.disabled = true;
  galleryStats.textContent = 'Downloading all images…';

  try {
    const result = await chrome.tabs.sendMessage(connectedTabId, {
      type: 'DOWNLOAD_ALL_IMAGES',
      projectName,
      providerId: activeProviderId,
    });

    if (result?.ok) {
      galleryStats.textContent = `Downloaded ${result.count} image(s) to "${projectName}/".`;
      refreshProjectInfo();
    } else {
      galleryStats.textContent = result?.error || 'Download failed.';
    }
  } catch (err) {
    galleryStats.textContent = `Download failed: ${err.message}`;
  } finally {
    downloadAllBtn.disabled = scannedImages.length === 0;
    scanBtn.disabled = false;
  }
}

function handleRuntimeMessage(message) {
  switch (message.type) {
    case 'QUEUE_UPDATE':
      renderQueueState(message.state);
      updateRetryFailedButton(message.state);
      if (message.state?.stopRequested) stepMsg.textContent = 'Stopping…';
      break;
    case 'QUEUE_FINISHED':
      finishQueueUi(formatFinishMessage(message), message.reason !== 'completed');
      renderQueueState(message.state);
      updateRetryFailedButton(message.state);
      refreshProjectInfo();
      refreshExportInfo();
      break;
    default:
      break;
  }
}

function formatFinishMessage(message) {
  const { summary, reason } = message;
  if (reason === 'stopped') return 'Queue stopped by user.';
  if (summary.failed) {
    return `Queue finished: ${summary.done}/${summary.total} succeeded, ${summary.failed} failed. Metadata exported if enabled.`;
  }
  return `Queue complete! ${summary.done}/${summary.total} images downloaded. Metadata exported if enabled.`;
}

function finishQueueUi(message, isError) {
  queueRunning = false;
  startBtn.disabled = false;
  stopBtn.disabled = true;
  validateBtn.disabled = false;
  progressFill.style.width = isError ? progressFill.style.width : '100%';
  progressFill.classList.toggle('complete', !isError);
  stepMsg.textContent = message;
  stepMsg.className = isError ? 'step-msg error-msg' : 'step-msg success-msg';
  chrome.runtime.sendMessage({ type: 'GET_QUEUE_STATE' }).then(updateRetryFailedButton).catch(() => {});
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
