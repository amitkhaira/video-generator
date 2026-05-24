/**
 * Voiceover Automator — Side Panel
 */

'use strict';

const $ = (id) => document.getElementById(id);

const projectNameInput = $('projectName');
const jsonInput = $('jsonInput');
const validateBtn = $('validateBtn');
const startBtn = $('startBtn');
const stopBtn = $('stopBtn');
const validationMsg = $('validationMsg');
const statusDot = $('statusDot');
const statusText = $('statusText');
const openAiStudioBtn = $('openAiStudioBtn');
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
const concurrencyInput = $('concurrency');
const retryFailedBtn = $('retryFailedBtn');

let queueRunning = false;
let connectedTabId = null;
let validatedJobs = [];

document.addEventListener('DOMContentLoaded', async () => {
  await restoreState();
  initTabs();
  bindEvents();
  checkAiStudioConnection();
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

  openAiStudioBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'OPEN_AISTUDIO' });
    setTimeout(checkAiStudioConnection, 2500);
  });

  jsonInput.addEventListener('input', () => {
    if (validationMsg.classList.contains('valid')) {
      clearValidation();
      startBtn.disabled = true;
      validatedJobs = [];
      renderQueuePreview([]);
    }
  });

  [maxRetriesInput, failureRetryMaxInput, jobDelaySecInput, concurrencyInput, projectNameInput].forEach((el) => {
    if (el) el.addEventListener('change', persistSettings);
  });
}

async function restoreState() {
  try {
    const stored = await chrome.storage.local.get([
      'lastJson',
      'projectName',
      'maxRetries',
      'failureRetryMax',
      'jobDelaySec',
      'concurrency',
    ]);
    if (stored.lastJson) jsonInput.value = stored.lastJson;
    if (stored.projectName) projectNameInput.value = stored.projectName;
    if (stored.maxRetries != null) maxRetriesInput.value = stored.maxRetries;
    if (stored.failureRetryMax != null && failureRetryMaxInput) {
      failureRetryMaxInput.value = stored.failureRetryMax;
    }
    if (stored.jobDelaySec != null) jobDelaySecInput.value = stored.jobDelaySec;
    if (stored.concurrency != null) concurrencyInput.value = stored.concurrency;
  } catch (_) {}
}

async function persistSettings() {
  try {
    await chrome.storage.local.set({
      lastJson: jsonInput.value,
      projectName: projectNameInput.value,
      maxRetries: Number(maxRetriesInput.value),
      failureRetryMax: Number(failureRetryMaxInput?.value ?? 3),
      jobDelaySec: Number(jobDelaySecInput.value),
      concurrency: Number(concurrencyInput.value),
    });
  } catch (_) {}
}

function getSettings() {
  return {
    maxRetries: Math.max(0, Math.min(20, Number(maxRetriesInput.value) || 3)),
    failureRetryMax: Math.max(0, Math.min(20, Number(failureRetryMaxInput?.value) || 3)),
    jobDelaySec: Math.max(0, Math.min(300, Number(jobDelaySecInput.value) || 5)),
    concurrency: Math.max(1, Math.min(3, Number(concurrencyInput.value) || 1)),
  };
}

function updateRetryFailedButton(state) {
  if (!retryFailedBtn) return;
  const failedCount = state?.failedCount ?? state?.jobs?.filter((j) => j.status === 'failed').length ?? 0;
  retryFailedBtn.textContent = `Retry Failures (${failedCount})`;
  retryFailedBtn.disabled = queueRunning || failedCount === 0;
}

async function checkAiStudioConnection() {
  setConnectionState('checking', 'Checking AI Studio connection…');

  try {
    const tabs = await chrome.tabs.query({ url: 'https://aistudio.google.com/*' });
    if (!tabs.length) {
      connectedTabId = null;
      setConnectionState('error', 'No AI Studio tab found. Click Open to launch it.');
      return;
    }

    const tab = tabs[0];
    connectedTabId = tab.id;

    try {
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
      if (response?.alive) {
        const page = (response.url || tab.url || '').includes('speech') ? 'Speech page' : 'AI Studio';
        setConnectionState('connected', `Connected · ${page} · Tab #${tab.id}`);
        return;
      }
    } catch (_) {}

    setConnectionState('error', 'AI Studio tab found but script not ready. Reload the page.');
  } catch (err) {
    setConnectionState('error', `Connection error: ${err.message}`);
  }
}

function setConnectionState(state, text) {
  statusDot.dataset.state = state;
  statusText.textContent = text;
}

function validateInput() {
  const parsed = PhaseAdapter.parseInput(jsonInput.value);
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
    `Valid! ${validatedJobs.length} phase(s) queued for project "${projectName}".`
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
  queueSummary.textContent = `${jobs.length} job${jobs.length === 1 ? '' : 's'}`;

  if (!jobs.length) {
    queueList.innerHTML = '';
    return;
  }

  queueList.innerHTML = jobs
    .map(
      (job) => `
    <li class="queue-item" data-phase="${job.meta?.phase ?? ''}">
      <span class="queue-item-phase">Phase ${job.meta?.phase ?? '?'}</span>
      <span class="queue-item-title">${escapeHtml(job.title)}</span>
      <span class="queue-item-file">${escapeHtml(job.projectName)}/${escapeHtml(job.outputFilename)}</span>
      <span class="queue-item-status pending">pending</span>
    </li>`
    )
    .join('');
}

function renderQueueState(state) {
  if (!state?.jobs?.length) return;

  queueSection.classList.add('visible');
  queueSummary.textContent = `${state.jobs.length} job${state.jobs.length === 1 ? '' : 's'}`;

  queueList.innerHTML = state.jobs
    .map((job) => {
      const status = job.status || 'pending';
      const err = job.error ? `<span class="queue-item-error">${escapeHtml(job.error)}</span>` : '';
      return `
    <li class="queue-item status-${status}">
      <span class="queue-item-phase">Phase ${job.phase ?? '?'}</span>
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

  await checkAiStudioConnection();
  if (!connectedTabId) {
    showValidation('error', 'No AI Studio tab available.');
    return;
  }

  await persistSettings();

  queueRunning = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  validateBtn.disabled = true;
  if (retryFailedBtn) retryFailedBtn.disabled = true;
  progressSection.classList.add('visible');
  stepMsg.textContent = 'Starting queue…';

  const response = await chrome.runtime.sendMessage({
    type: 'START_QUEUE',
    payload: {
      rawJson: jsonInput.value,
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
  stepMsg.className = 'step-msg';
  stopBtn.disabled = true;
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

async function retryFailed() {
  if (queueRunning) return;

  await checkAiStudioConnection();
  if (!connectedTabId) {
    showValidation('error', 'No AI Studio tab available.');
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
  stepMsg.textContent = 'Retrying failed phases…';

  const response = await chrome.runtime.sendMessage({
    type: 'RETRY_FAILED',
    payload: {
      tabId: connectedTabId,
      failureRetryMax: settings.failureRetryMax,
      settings: {
        jobDelaySec: settings.jobDelaySec,
        concurrency: settings.concurrency,
      },
    },
  });

  if (!response?.ok) {
    finishQueueUi(`Retry failed: ${response?.error || 'unknown error'}`, true);
  }
}

function handleRuntimeMessage(message) {
  switch (message.type) {
    case 'QUEUE_UPDATE':
      renderQueueState(message.state);
      updateRetryFailedButton(message.state);
      if (message.state?.stopRequested) {
        stepMsg.textContent = 'Stopping…';
      }
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
  return `Queue complete! ${summary.done}/${summary.total} phases downloaded.`;
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
