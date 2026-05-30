/**
 * Gemini Image Studio — Background Service Worker
 * Queue orchestration, download renaming, metadata storage.
 */

'use strict';

importScripts('../lib/sceneAdapter.js');

const LOG = '[Gemini Image Studio BG]';

/** @type {object} */
let queueState = {
  running: false,
  stopRequested: false,
  projectName: 'gemini_project',
  settings: { ...SceneAdapter.DEFAULT_SETTINGS },
  jobs: [],
  tabId: null,
  activeSlots: 0,
  pending: [],
};

const downloadRenameQueue = [];
/** @type {Map<string, { resolve: Function, promise: Promise }>} */
const downloadStartWatchers = new Map();

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((err) => console.warn(LOG, 'sidePanel:', err));

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case 'REGISTER_DOWNLOAD': {
      downloadRenameQueue.push({
        jobId: message.jobId || `job_${Date.now()}`,
        projectName: message.projectName || 'gemini_project',
        filename: message.filename || 'image',
        metadata: message.metadata || null,
      });
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

    case 'SAVE_METADATA': {
      appendMetadata(message.projectName, message.entry)
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'DOWNLOAD_DATA_URL': {
      downloadDataUrl(message)
        .then((result) => sendResponse(result))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'OPEN_GEMINI': {
      openOrFocusGemini().then(() => sendResponse({ ok: true }));
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

    case 'SCENE_PROGRESS': {
      updateJobStatus(message.jobId, 'running', {
        step: message.step,
        message: message.message,
        current: message.current,
        total: message.total,
      });
      broadcastQueueUpdate();
      break;
    }

    case 'SCENE_COMPLETE': {
      handleSceneComplete(message.jobId);
      sendResponse({ ok: true });
      break;
    }

    case 'SCENE_ERROR': {
      handleSceneError(message.jobId, message.error, message.step, message.stopped);
      sendResponse({ ok: true });
      break;
    }

    default:
      break;
  }

  return true;
});

function armDownloadWatcher(jobId) {
  clearDownloadWatcher(jobId);
  let resolveFn;
  const promise = new Promise((resolve) => {
    resolveFn = resolve;
  });
  downloadStartWatchers.set(jobId, { resolve: resolveFn, promise });
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
  notifyDownloadStarted(downloadItem);
});

chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  const next = downloadRenameQueue.shift();
  if (!next) {
    suggest();
    return;
  }

  const originalName = downloadItem.filename || downloadItem.url || '';
  const dotIndex = originalName.lastIndexOf('.');
  const ext = dotIndex !== -1 ? originalName.substring(dotIndex) : '.png';

  const folder = (next.projectName || 'gemini_project').replace(/[/\\]+/g, '_');
  const base = (next.filename || 'image').replace(/[/\\]+/g, '_');
  const newFilename = `${folder}/${base}${ext}`;

  console.log(LOG, `Renaming → "${newFilename}" (${next.jobId})`);
  suggest({ filename: newFilename, conflictAction: 'uniquify' });
});

async function appendMetadata(projectName, entry) {
  const key = `metadata_${(projectName || 'gemini_project').replace(/[/\\]+/g, '_')}`;
  const stored = await chrome.storage.local.get(key);
  const list = Array.isArray(stored[key]) ? stored[key] : [];
  list.push({ ...entry, saved_at: new Date().toISOString() });
  await chrome.storage.local.set({ [key]: list });
}

async function downloadDataUrl({ dataUrl, filename, projectName, jobId }) {
  downloadRenameQueue.push({
    jobId: jobId || `dl_${Date.now()}`,
    projectName: projectName || 'gemini_project',
    filename: filename || 'image',
  });

  const downloadId = await chrome.downloads.download({
    url: dataUrl,
    saveAs: false,
    conflictAction: 'uniquify',
  });

  return { ok: true, downloadId };
}

function getPublicQueueState() {
  return {
    running: queueState.running,
    stopRequested: queueState.stopRequested,
    projectName: queueState.projectName,
    settings: queueState.settings,
    jobs: queueState.jobs.map((j) => ({
      id: j.id,
      title: j.config.title,
      scene: j.config.scene,
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
  if (queueState.running) throw new Error('Queue is already running.');

  const parsed = SceneAdapter.parseInput(payload.rawInput ?? payload.rawJson ?? '');
  if (!parsed.ok) throw new Error(parsed.errors.join(' '));

  const settings = {
    ...SceneAdapter.DEFAULT_SETTINGS,
    ...(payload.settings || parsed.settings || {}),
  };

  const projectName =
    (payload.projectName && String(payload.projectName).trim()) ||
    parsed.projectName ||
    'gemini_project';

  const tabId = await resolveGeminiTabId(payload.tabId);
  if (!tabId) {
    throw new Error('No Gemini tab found. Open gemini.google.com and start a chat first.');
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
      config: { ...config, projectName, settings: { ...settings } },
      status: 'pending',
      attempts: 0,
      error: null,
      progress: null,
    })),
  };

  queueState.pending = [...queueState.jobs];
  console.log(LOG, `Queue started: ${queueState.jobs.length} scene(s), project="${projectName}"`);
  broadcastQueueUpdate();
  pumpQueue();
}

async function retryFailedJobs(payload) {
  if (queueState.running) throw new Error('Queue is already running.');

  const failedJobs = queueState.jobs.filter((j) => j.status === 'failed');
  if (!failedJobs.length) throw new Error('No failed scenes to retry.');

  const tabId = await resolveGeminiTabId(payload.tabId || queueState.tabId);
  if (!tabId) throw new Error('No Gemini tab found.');

  queueState.settings = {
    ...queueState.settings,
    maxRetries: Math.max(0, Math.min(20, payload.failureRetryMax ?? queueState.settings.failureRetryMax ?? 3)),
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
  if (queueState.activeSlots === 0) finishQueue('stopped');
}

async function resolveGeminiTabId(preferredTabId) {
  if (preferredTabId) {
    try {
      const tab = await chrome.tabs.get(preferredTabId);
      if (tab?.url?.includes('gemini.google.com')) return tab.id;
    } catch (_) {}
  }

  const tabs = await chrome.tabs.query({ url: 'https://gemini.google.com/*' });
  return tabs.length ? tabs[0].id : null;
}

function pumpQueue() {
  if (queueState.stopRequested) {
    finishQueue('stopped');
    return;
  }

  const concurrency = Math.max(1, Math.min(1, queueState.settings.concurrency || 1));

  while (
    queueState.activeSlots < concurrency &&
    queueState.pending.length > 0 &&
    !queueState.stopRequested
  ) {
    runJob(queueState.pending.shift());
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
      type: 'RUN_SCENE',
      jobId: job.id,
      config: job.config,
    });
  } catch (err) {
    handleSceneError(job.id, `Could not reach content script: ${err.message}`, 'init');
  }
}

function handleSceneComplete(jobId) {
  const job = queueState.jobs.find((j) => j.id === jobId);
  if (!job) return;

  job.status = queueState.stopRequested ? 'cancelled' : 'done';
  job.error = null;
  queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);
  broadcastQueueUpdate();

  if (queueState.stopRequested && queueState.activeSlots === 0) {
    finishQueue('stopped');
    return;
  }

  if (!queueState.stopRequested) scheduleNextPump();
}

function handleSceneError(jobId, error, step, stopped = false) {
  const job = queueState.jobs.find((j) => j.id === jobId);
  if (!job) return;

  job.error = stopped ? 'Stopped by user' : error;
  job.progress = { step, message: job.error };

  if (stopped || queueState.stopRequested) {
    job.status = 'cancelled';
    queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);
    broadcastQueueUpdate();
    if (queueState.stopRequested && queueState.activeSlots === 0) finishQueue('stopped');
    else if (!queueState.stopRequested) scheduleNextPump();
    return;
  }

  const maxRetries = queueState.settings.maxRetries ?? 3;

  if (job.attempts <= maxRetries && !queueState.stopRequested) {
    job.status = 'retrying';
    broadcastQueueUpdate();
    queueState.activeSlots = Math.max(0, queueState.activeSlots - 1);

    const delayMs = Math.min(60000, 5000 * Math.pow(2, job.attempts - 1));
    console.warn(LOG, `Retry ${jobId} in ${delayMs}ms: ${error}`);
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

  const delayMs = Math.max(0, (queueState.settings.jobDelaySec ?? 8) * 1000);
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

async function openOrFocusGemini() {
  const tabs = await chrome.tabs.query({ url: 'https://gemini.google.com/*' });

  if (tabs.length > 0) {
    const tab = tabs[0];
    await chrome.tabs.update(tab.id, { active: true });
    await chrome.windows.update(tab.windowId, { focused: true });
  } else {
    await chrome.tabs.create({ url: 'https://gemini.google.com/app' });
  }
}
