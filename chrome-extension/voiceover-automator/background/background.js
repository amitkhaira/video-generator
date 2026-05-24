/**
 * Voiceover Automator — Background Service Worker
 *
 * Queue orchestrator: batch phases, retry failed jobs, rename downloads
 * into project subfolders.
 */

'use strict';

importScripts('../lib/phaseAdapter.js');

const LOG = '[Voiceover BG]';

/** @type {{ running: boolean, stopRequested: boolean, projectName: string, settings: object, jobs: object[], tabId: number|null, activeSlots: number, pending: object[] }} */
let queueState = {
  running: false,
  stopRequested: false,
  projectName: 'voiceover_project',
  settings: { ...PhaseAdapter.DEFAULT_SETTINGS },
  jobs: [],
  tabId: null,
  activeSlots: 0,
  pending: [],
};

/** FIFO queue — one entry per upcoming download rename. */
const downloadRenameQueue = [];

/** @type {Map<string, { resolve: Function, reject: Function, timeoutId: number }>} */
const downloadStartWatchers = new Map();

// ─── Side panel ───────────────────────────────────────────────────────────────

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((err) => console.warn(LOG, 'sidePanel behavior:', err));

// ─── Message Router ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'REGISTER_DOWNLOAD': {
      downloadRenameQueue.push({
        jobId: message.jobId || `job_${Date.now()}`,
        projectName: message.projectName || 'voiceover_project',
        filename: message.filename || 'audio',
      });
      console.log(LOG, 'Download registered:', downloadRenameQueue[downloadRenameQueue.length - 1]);
      sendResponse({ ok: true });
      break;
    }

    case 'ARM_DOWNLOAD_WATCHER': {
      armDownloadWatcher(message.jobId || 'default');
      sendResponse({ ok: true });
      break;
    }

    case 'AWAIT_DOWNLOAD_START': {
      awaitDownloadStart(message.jobId || 'default', message.timeoutMs || 20000)
        .then((result) => sendResponse(result))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'OPEN_AISTUDIO': {
      openOrFocusAiStudio().then(() => sendResponse({ ok: true }));
      return true;
    }

    case 'FIND_AISTUDIO_TAB': {
      chrome.tabs.query({ url: 'https://aistudio.google.com/*' }, (tabs) => {
        sendResponse({ tabs });
      });
      return true;
    }

    case 'START_QUEUE': {
      startQueue(message.payload)
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'RETRY_FAILED': {
      retryFailedJobs(message.payload || {})
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'STOP_QUEUE': {
      stopQueue();
      sendResponse({ ok: true });
      break;
    }

    case 'GET_QUEUE_STATE': {
      sendResponse(getPublicQueueState());
      break;
    }

    case 'PHASE_PROGRESS': {
      updateJobStatus(message.jobId, 'running', {
        step: message.step,
        message: message.message,
        current: message.current,
        total: message.total,
      });
      broadcastQueueUpdate();
      break;
    }

    case 'PHASE_COMPLETE': {
      handlePhaseComplete(message.jobId);
      sendResponse({ ok: true });
      break;
    }

    case 'PHASE_ERROR': {
      handlePhaseError(message.jobId, message.error, message.step, message.stopped);
      sendResponse({ ok: true });
      break;
    }

    default:
      break;
  }

  return true;
});

// ─── Download Renaming & Confirmation ────────────────────────────────────────

function armDownloadWatcher(jobId) {
  clearDownloadWatcher(jobId);
  let resolveFn;
  const promise = new Promise((resolve) => {
    resolveFn = resolve;
  });
  downloadStartWatchers.set(jobId, { resolve: resolveFn, promise, armedAt: Date.now() });
}

function clearDownloadWatcher(jobId) {
  downloadStartWatchers.delete(jobId);
}

function awaitDownloadStart(jobId, timeoutMs) {
  let watcher = downloadStartWatchers.get(jobId);
  if (!watcher) {
    armDownloadWatcher(jobId);
    watcher = downloadStartWatchers.get(jobId);
  }

  return Promise.race([
    watcher.promise.then((item) => ({ ok: true, downloadId: item.id, filename: item.filename })),
    new Promise((resolve) => {
      setTimeout(
        () => resolve({ ok: false, error: 'Download did not start within timeout.' }),
        timeoutMs
      );
    }),
  ]).finally(() => clearDownloadWatcher(jobId));
}

function notifyDownloadStarted(downloadItem) {
  for (const [jobId, watcher] of downloadStartWatchers.entries()) {
    watcher.resolve(downloadItem);
    downloadStartWatchers.delete(jobId);
    return jobId;
  }
  return null;
}

chrome.downloads.onCreated.addListener((downloadItem) => {
  const jobId = notifyDownloadStarted(downloadItem);
  if (jobId) {
    console.log(LOG, `Download started for ${jobId}:`, downloadItem.id, downloadItem.filename);
  }
});

chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  const next = downloadRenameQueue.shift();
  if (!next) {
    suggest();
    return;
  }

  const originalName = downloadItem.filename || downloadItem.url || '';
  const dotIndex = originalName.lastIndexOf('.');
  const ext = dotIndex !== -1 ? originalName.substring(dotIndex) : '.wav';

  const folder = (next.projectName || 'voiceover_project').replace(/[/\\]+/g, '_');
  const base = (next.filename || 'audio').replace(/[/\\]+/g, '_');
  const newFilename = `${folder}/${base}${ext}`;

  console.log(LOG, `Renaming: "${originalName}" → "${newFilename}" (job ${next.jobId})`);
  suggest({ filename: newFilename, conflictAction: 'uniquify' });
});

// ─── Queue Engine ─────────────────────────────────────────────────────────────

function getPublicQueueState() {
  return {
    running: queueState.running,
    stopRequested: queueState.stopRequested,
    projectName: queueState.projectName,
    settings: queueState.settings,
    jobs: queueState.jobs.map((j) => ({
      id: j.id,
      title: j.config.title,
      phase: j.config.meta?.phase,
      status: j.status,
      attempts: j.attempts,
      error: j.error,
      progress: j.progress,
    })),
    failedCount: queueState.jobs.filter((j) => j.status === 'failed').length,
    activeSlots: queueState.activeSlots,
    pendingCount: queueState.pending.length,
  };
}

function broadcastQueueUpdate() {
  chrome.runtime.sendMessage({ type: 'QUEUE_UPDATE', state: getPublicQueueState() }).catch(() => {});
}

function updateJobStatus(jobId, status, extra = {}) {
  const job = queueState.jobs.find((j) => j.id === jobId);
  if (!job) return;
  job.status = status;
  if (extra.error !== undefined) job.error = extra.error;
  if (extra.step !== undefined || extra.message !== undefined) {
    job.progress = {
      step: extra.step,
      message: extra.message,
      current: extra.current,
      total: extra.total,
    };
  }
}

async function startQueue(payload) {
  if (queueState.running) {
    throw new Error('Queue is already running.');
  }

  const parsed = PhaseAdapter.parseInput(payload.rawJson ? payload.rawJson : payload);
  if (!parsed.ok) {
    throw new Error(parsed.errors.join(' '));
  }

  const settings = {
    ...PhaseAdapter.DEFAULT_SETTINGS,
    ...(payload.settings || parsed.settings || {}),
  };

  const projectName =
    (payload.projectName && String(payload.projectName).trim()) ||
    parsed.projectName ||
    'voiceover_project';

  const tabId = await resolveAiStudioTabId(payload.tabId);
  if (!tabId) {
    throw new Error('No Google AI Studio tab found. Open AI Studio Speech page first.');
  }

  queueState = {
    running: true,
    stopRequested: false,
    projectName,
    settings,
    tabId,
    activeSlots: 0,
    pending: [],
    jobs: parsed.jobs.map((config, index) => ({
      id: `job_${index}_${Date.now()}`,
      config: { ...config, projectName },
      status: 'pending',
      attempts: 0,
      error: null,
      progress: null,
    })),
  };

  queueState.pending = [...queueState.jobs];
  console.log(LOG, `Queue started: ${queueState.jobs.length} job(s), project="${projectName}"`);
  broadcastQueueUpdate();
  pumpQueue();
}

async function retryFailedJobs(payload) {
  if (queueState.running) {
    throw new Error('Queue is already running.');
  }

  const failedJobs = queueState.jobs.filter((j) => j.status === 'failed');
  if (failedJobs.length === 0) {
    throw new Error('No failed phases to retry.');
  }

  const tabId = await resolveAiStudioTabId(payload.tabId || queueState.tabId);
  if (!tabId) {
    throw new Error('No Google AI Studio tab found. Open AI Studio Speech page first.');
  }

  const failureRetryMax = Math.max(
    0,
    Math.min(20, payload.failureRetryMax ?? queueState.settings.failureRetryMax ?? 3)
  );

  queueState.settings = {
    ...queueState.settings,
    maxRetries: failureRetryMax,
    ...(payload.settings || {}),
  };
  queueState.tabId = tabId;
  queueState.running = true;
  queueState.stopRequested = false;
  queueState.activeSlots = 0;
  queueState.pending = [];

  failedJobs.forEach((job) => {
    job.status = 'pending';
    job.attempts = 0;
    job.error = null;
    job.progress = null;
    queueState.pending.push(job);
  });

  console.log(
    LOG,
    `Retrying ${failedJobs.length} failed job(s), maxRetries=${failureRetryMax}`
  );
  broadcastQueueUpdate();
  pumpQueue();
}

function stopQueue() {
  if (!queueState.running) return;
  queueState.stopRequested = true;
  queueState.pending = [];

  queueState.jobs.forEach((j) => {
    if (j.status === 'pending') j.status = 'cancelled';
    if (j.status === 'running' || j.status === 'retrying') j.status = 'cancelling';
  });

  if (queueState.tabId) {
    chrome.tabs.sendMessage(queueState.tabId, { type: 'ABORT_AUTOMATION' }).catch(() => {});
  }

  broadcastQueueUpdate();

  if (queueState.activeSlots === 0) {
    finishQueue('stopped');
  }
}

async function resolveAiStudioTabId(preferredTabId) {
  if (preferredTabId) {
    try {
      const tab = await chrome.tabs.get(preferredTabId);
      if (tab?.url?.includes('aistudio.google.com')) return tab.id;
    } catch (_) {}
  }

  const tabs = await chrome.tabs.query({ url: 'https://aistudio.google.com/*' });
  return tabs.length ? tabs[0].id : null;
}

function pumpQueue() {
  if (queueState.stopRequested) {
    finishQueue('stopped');
    return;
  }

  const concurrency = Math.max(1, Math.min(3, queueState.settings.concurrency || 1));

  while (
    queueState.activeSlots < concurrency &&
    queueState.pending.length > 0 &&
    !queueState.stopRequested
  ) {
    const job = queueState.pending.shift();
    runJob(job);
  }

  if (queueState.activeSlots === 0 && queueState.pending.length === 0) {
    const failed = queueState.jobs.some((j) => j.status === 'failed');
    const stopped = queueState.stopRequested;
    finishQueue(stopped ? 'stopped' : failed ? 'completed_with_errors' : 'completed');
  }
}

async function runJob(job) {
  queueState.activeSlots++;
  job.attempts++;
  job.status = 'running';
  job.error = null;
  broadcastQueueUpdate();

  try {
    await chrome.tabs.sendMessage(queueState.tabId, {
      type: 'RUN_PHASE',
      jobId: job.id,
      config: job.config,
    });
  } catch (err) {
    handlePhaseError(job.id, `Could not reach content script: ${err.message}`, 'init');
  }
}

function handlePhaseComplete(jobId) {
  const job = queueState.jobs.find((j) => j.id === jobId);
  if (!job) return;

  if (queueState.stopRequested) {
    job.status = 'cancelled';
  } else {
    job.status = 'done';
    job.error = null;
  }

  queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);
  broadcastQueueUpdate();

  if (queueState.stopRequested && queueState.activeSlots === 0) {
    finishQueue('stopped');
    return;
  }

  if (!queueState.stopRequested) scheduleNextPump();
}

function handlePhaseError(jobId, error, step, stopped = false) {
  const job = queueState.jobs.find((j) => j.id === jobId);
  if (!job) return;

  job.error = stopped ? 'Stopped by user' : error;
  job.progress = { step, message: job.error };

  if (stopped || queueState.stopRequested) {
    job.status = 'cancelled';
    queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);
    broadcastQueueUpdate();
    if (queueState.stopRequested && queueState.activeSlots === 0) {
      finishQueue('stopped');
    } else if (!queueState.stopRequested) {
      scheduleNextPump();
    }
    return;
  }

  const maxRetries = queueState.settings.maxRetries ?? 3;

  if (job.attempts <= maxRetries && !queueState.stopRequested) {
    job.status = 'retrying';
    broadcastQueueUpdate();
    queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);

    const delayMs = 5000;
    console.warn(
      LOG,
      `Job ${jobId} failed (attempt ${job.attempts}/${maxRetries + 1}): ${error}. Retrying in ${delayMs}ms`
    );
    setTimeout(() => {
      if (queueState.stopRequested || !queueState.running) return;
      queueState.pending.unshift(job);
      pumpQueue();
    }, delayMs);
    return;
  }

  job.status = 'failed';
  queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);
  broadcastQueueUpdate();
  scheduleNextPump();
}

function scheduleNextPump() {
  if (queueState.stopRequested) {
    if (queueState.activeSlots === 0) finishQueue('stopped');
    return;
  }

  const delaySec = queueState.settings.jobDelaySec ?? 5;
  const delayMs = Math.max(0, delaySec) * 1000;

  setTimeout(() => {
    if (!queueState.running || queueState.stopRequested) {
      if (queueState.stopRequested && queueState.activeSlots === 0) finishQueue('stopped');
      return;
    }
    pumpQueue();
  }, delayMs);
}

function finishQueue(reason) {
  const summary = {
    total: queueState.jobs.length,
    done: queueState.jobs.filter((j) => j.status === 'done').length,
    failed: queueState.jobs.filter((j) => j.status === 'failed').length,
  };

  queueState.running = false;
  queueState.stopRequested = false;
  queueState.activeSlots = 0;
  queueState.pending = [];

  broadcastQueueUpdate();
  chrome.runtime
    .sendMessage({ type: 'QUEUE_FINISHED', reason, summary, state: getPublicQueueState() })
    .catch(() => {});

  console.log(LOG, `Queue finished (${reason}):`, summary);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function openOrFocusAiStudio() {
  const tabs = await chrome.tabs.query({ url: 'https://aistudio.google.com/*' });

  if (tabs.length > 0) {
    const tab = tabs[0];
    await chrome.tabs.update(tab.id, { active: true });
    await chrome.windows.update(tab.windowId, { focused: true });
  } else {
    await chrome.tabs.create({ url: 'https://aistudio.google.com/' });
  }
}
