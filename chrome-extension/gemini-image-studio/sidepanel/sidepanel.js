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

let queueRunning = false;
let connectedTabId = null;
let validatedJobs = [];
let scannedImages = [];

document.addEventListener('DOMContentLoaded', async () => {
  await restoreState();
  initTabs();
  bindEvents();
  checkGeminiConnection();
  refreshQueueState();
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

  openGeminiBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'OPEN_GEMINI' });
    setTimeout(checkGeminiConnection, 2500);
  });

  sceneInput.addEventListener('input', () => {
    if (validationMsg.classList.contains('valid')) {
      clearValidation();
      startBtn.disabled = true;
      validatedJobs = [];
      renderQueuePreview([]);
    }
  });

  [maxRetriesInput, failureRetryMaxInput, jobDelaySecInput, generationTimeoutSecInput, projectNameInput].forEach(
    (el) => {
      if (el) el.addEventListener('change', persistSettings);
    }
  );
}

async function restoreState() {
  try {
    const stored = await chrome.storage.local.get([
      'lastSceneInput',
      'projectName',
      'galleryProjectName',
      'maxRetries',
      'failureRetryMax',
      'jobDelaySec',
      'generationTimeoutSec',
    ]);
    if (stored.lastSceneInput) sceneInput.value = stored.lastSceneInput;
    if (stored.projectName) projectNameInput.value = stored.projectName;
    if (stored.galleryProjectName) galleryProjectNameInput.value = stored.galleryProjectName;
    if (stored.maxRetries != null) maxRetriesInput.value = stored.maxRetries;
    if (stored.failureRetryMax != null) failureRetryMaxInput.value = stored.failureRetryMax;
    if (stored.jobDelaySec != null) jobDelaySecInput.value = stored.jobDelaySec;
    if (stored.generationTimeoutSec != null) {
      generationTimeoutSecInput.value = stored.generationTimeoutSec;
    }
  } catch (_) {}
}

async function persistSettings() {
  try {
    await chrome.storage.local.set({
      lastSceneInput: sceneInput.value,
      projectName: projectNameInput.value,
      galleryProjectName: galleryProjectNameInput.value,
      maxRetries: Number(maxRetriesInput.value),
      failureRetryMax: Number(failureRetryMaxInput?.value ?? 3),
      jobDelaySec: Number(jobDelaySecInput.value),
      generationTimeoutSec: Number(generationTimeoutSecInput.value),
    });
  } catch (_) {}
}

function getSettings() {
  return {
    maxRetries: Math.max(0, Math.min(20, Number(maxRetriesInput.value) || 3)),
    failureRetryMax: Math.max(0, Math.min(20, Number(failureRetryMaxInput?.value) || 3)),
    jobDelaySec: Math.max(0, Math.min(300, Number(jobDelaySecInput.value) || 8)),
    generationTimeoutSec: Math.max(30, Math.min(600, Number(generationTimeoutSecInput.value) || 180)),
    concurrency: 1,
  };
}

function updateRetryFailedButton(state) {
  if (!retryFailedBtn) return;
  const failedCount = state?.failedCount ?? state?.jobs?.filter((j) => j.status === 'failed').length ?? 0;
  retryFailedBtn.textContent = `Retry Failures (${failedCount})`;
  retryFailedBtn.disabled = queueRunning || failedCount === 0;
}

async function checkGeminiConnection() {
  setConnectionState('checking', 'Checking Gemini connection…');

  try {
    const tabs = await chrome.tabs.query({ url: 'https://gemini.google.com/*' });
    if (!tabs.length) {
      connectedTabId = null;
      setConnectionState('error', 'No Gemini tab found. Click Open to launch it.');
      return;
    }

    const tab = tabs[0];
    connectedTabId = tab.id;

    try {
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
      if (response?.alive) {
        setConnectionState('connected', `Connected · Tab #${tab.id}`);
        return;
      }
    } catch (_) {}

    setConnectionState('error', 'Gemini tab found but script not ready. Reload the page.');
  } catch (err) {
    setConnectionState('error', `Connection error: ${err.message}`);
  }
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

  await checkGeminiConnection();
  if (!connectedTabId) {
    showValidation('error', 'No Gemini tab available.');
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

  await checkGeminiConnection();
  if (!connectedTabId) {
    showValidation('error', 'No Gemini tab available.');
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
  await checkGeminiConnection();
  if (!connectedTabId) {
    galleryStats.textContent = 'No Gemini tab connected.';
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
        : 'No images found. Generate some images in Gemini first.';
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
  await checkGeminiConnection();
  if (!connectedTabId) {
    galleryStats.textContent = 'No Gemini tab connected.';
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
    });

    if (result?.ok) {
      galleryStats.textContent = `Downloaded ${result.count} image(s) to "${projectName}/".`;
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
      break;
    default:
      break;
  }
}

function formatFinishMessage(message) {
  const { summary, reason } = message;
  if (reason === 'stopped') return 'Queue stopped by user.';
  if (summary.failed) {
    return `Queue finished: ${summary.done}/${summary.total} succeeded, ${summary.failed} failed.`;
  }
  return `Queue complete! ${summary.done}/${summary.total} images downloaded.`;
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
