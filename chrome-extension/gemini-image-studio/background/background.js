/**
 * Gemini Image Studio — Background Service Worker
 */

'use strict';

importScripts(
  '../lib/jszip.min.js',
  '../lib/sceneAdapter.js',
  '../lib/projectStore.js',
  '../lib/exportEngine.js',
  '../lib/promptEngine.js',
  '../lib/providers/geminiProvider.js',
  '../lib/providers/chatgptProvider.js',
  '../lib/providers/providerRegistry.js'
);

ExportEngine.init({
  pushDownloadRename: (entry) => downloadRenameQueue.push(entry),
});

const LOG = '[Gemini Image Studio BG]';

let queueState = {
  running: false,
  stopRequested: false,
  projectName: 'gemini_project',
  providerId: 'gemini',
  settings: { ...SceneAdapter.DEFAULT_SETTINGS },
  jobs: [],
  tabId: null,
  activeSlots: 0,
  pending: [],
};

const downloadRenameQueue = [];
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
        relativePath: message.relativePath || null,
        forceExt: message.forceExt || null,
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

    case 'STORE_PROJECT_ASSET': {
      storeProjectAsset(message)
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

    case 'EXPORT_METADATA': {
      exportMetadata(message.projectName, message.providerId)
        .then((result) => sendResponse(result))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'EXPORT_ZIP': {
      ExportEngine.exportProjectZip(message.projectName, message.providerId)
        .then((downloadId) => sendResponse({ ok: true, downloadId }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'GET_PROJECT_INFO': {
      getProjectInfo(message.projectName)
        .then((result) => sendResponse(result))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'GET_PROVIDERS': {
      sendResponse({ ok: true, providers: ProviderRegistry.list() });
      break;
    }

    case 'GET_STUDIO_CONFIG': {
      PromptEngine.loadStudioConfig()
        .then((config) => sendResponse({ ok: true, config }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'SAVE_STUDIO_CONFIG': {
      PromptEngine.saveStudioConfig(message.config || {})
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'LIST_REFERENCES': {
      ProjectStore.listReferences()
        .then((refs) => sendResponse({ ok: true, references: refs.map(publicReference) }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'SAVE_REFERENCE': {
      ProjectStore.putReference(message)
        .then((ref) => sendResponse({ ok: true, reference: publicReference(ref) }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'DELETE_REFERENCE': {
      ProjectStore.deleteReference(message.id)
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'GET_REFERENCE_DATA': {
      ProjectStore.getReference(message.id)
        .then((ref) => {
          if (!ref) return sendResponse({ ok: false, error: 'Reference not found.' });
          sendResponse({
            ok: true,
            reference: {
              ...publicReference(ref),
              dataUrl: ProjectStore.bufferToDataUrl(ref.buffer, ref.mime),
            },
          });
        })
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'OPEN_PROVIDER': {
      ProviderRegistry.openProvider(message.providerId || 'gemini')
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    case 'OPEN_GEMINI': {
      ProviderRegistry.openProvider('gemini').then(() => sendResponse({ ok: true }));
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

function publicReference(ref) {
  return {
    id: ref.id,
    name: ref.name,
    mime: ref.mime,
    savedAt: ref.savedAt,
  };
}

async function storeProjectAsset(message) {
  const ext = message.ext || '.png';
  const record = await ProjectStore.putAsset({
    projectName: message.projectName,
    filename: message.filename,
    ext,
    mime: message.mime,
    dataUrl: message.dataUrl,
    metadata: {
      ...(message.metadata || {}),
      provider: message.providerId || queueState.providerId,
      saved_at: new Date().toISOString(),
    },
  });

  return { ok: true, id: record.id };
}

async function appendMetadata(projectName, entry) {
  const key = `metadata_${ProjectStore.sanitizeProject(projectName)}`;
  const stored = await chrome.storage.local.get(key);
  const list = Array.isArray(stored[key]) ? stored[key] : [];
  list.push({ ...entry, saved_at: entry.saved_at || new Date().toISOString() });
  await chrome.storage.local.set({ [key]: list });
}

async function getProjectInfo(projectName) {
  const safe = ProjectStore.sanitizeProject(projectName);
  const assets = await ProjectStore.listProjectAssets(safe);
  const key = `metadata_${safe}`;
  const stored = await chrome.storage.local.get(key);
  return {
    ok: true,
    projectName: safe,
    assetCount: assets.length,
    metadataCount: (stored[key] || []).length,
    assets: assets.map((a) => ({
      filename: `${a.filename}${a.ext}`,
      scene: a.metadata?.scene,
      savedAt: a.savedAt,
    })),
  };
}

async function exportMetadata(projectName, providerId) {
  const safe = ProjectStore.sanitizeProject(projectName);
  const assets = await ProjectStore.listProjectAssets(safe);
  if (!assets.length) throw new Error(`No assets stored for "${safe}".`);

  return ExportEngine.exportMetadataFiles(
    safe,
    assets.map((a) => ({
      filename: a.filename,
      ext: a.ext,
      metadata: a.metadata,
      savedAt: a.savedAt,
    })),
    providerId || 'gemini'
  );
}

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

  const folder = ProjectStore.sanitizeProject(next.projectName || 'gemini_project');

  if (next.relativePath) {
    const path = `${folder}/${next.relativePath}`;
    suggest({ filename: path, conflictAction: 'uniquify' });
    return;
  }

  const originalName = downloadItem.filename || downloadItem.url || '';
  const dotIndex = originalName.lastIndexOf('.');
  const ext = next.forceExt || (dotIndex !== -1 ? originalName.substring(dotIndex) : '.png');
  const base = (next.filename || 'image').replace(/[/\\]+/g, '_');
  const newFilename = `${folder}/${base}${ext}`;

  suggest({ filename: newFilename, conflictAction: 'uniquify' });
});

function getPublicQueueState() {
  return {
    running: queueState.running,
    stopRequested: queueState.stopRequested,
    projectName: queueState.projectName,
    providerId: queueState.providerId,
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

  const studioConfig = await PromptEngine.loadStudioConfig();
  const enrichedJobs = PromptEngine.enrichJobs(parsed.jobs, studioConfig);

  const settings = {
    ...SceneAdapter.DEFAULT_SETTINGS,
    ...(payload.settings || parsed.settings || {}),
  };

  const providerId = payload.providerId || settings.providerId || 'gemini';
  const provider = ProviderRegistry.get(providerId);
  if (provider.status !== 'active') {
    throw new Error(`Provider "${provider.name}" is not available yet (${provider.status}).`);
  }

  if (provider.jobDelaySec && !payload.settings?.jobDelaySec) {
    settings.jobDelaySec = provider.jobDelaySec;
  }
  if (provider.generationTimeoutSec && !payload.settings?.generationTimeoutSec) {
    settings.generationTimeoutSec = provider.generationTimeoutSec;
  }

  const projectName =
    (payload.projectName && String(payload.projectName).trim()) ||
    parsed.projectName ||
    'gemini_project';

  const tabId = await ProviderRegistry.resolveTabId(payload.tabId, providerId);
  if (!tabId) {
    throw new Error(`No ${provider.name} tab found. Open ${provider.openUrl} first.`);
  }

  const referenceData = await loadReferenceData(studioConfig.activeReferenceIds);

  queueState = {
    running: true,
    stopRequested: false,
    projectName,
    providerId,
    settings,
    tabId,
    activeSlots: 0,
    pending: [],
    jobs: enrichedJobs.map((config, index) => ({
      id: `job_${index}_${Date.now()}`,
      config: {
        ...config,
        projectName,
        providerId,
        settings: { ...settings },
        referenceImages: referenceData,
        provider,
      },
      status: 'pending',
      attempts: 0,
      error: null,
      progress: null,
    })),
  };

  queueState.pending = [...queueState.jobs];
  console.log(LOG, `Queue started: ${queueState.jobs.length} scene(s), provider=${providerId}`);
  broadcastQueueUpdate();
  pumpQueue();
}

async function loadReferenceData(ids) {
  if (!ids?.length) return [];
  const refs = [];
  for (const id of ids) {
    const ref = await ProjectStore.getReference(id);
    if (ref) {
      refs.push({
        id: ref.id,
        name: ref.name,
        mime: ref.mime,
        dataUrl: ProjectStore.bufferToDataUrl(ref.buffer, ref.mime),
      });
    }
  }
  return refs;
}

async function retryFailedJobs(payload) {
  if (queueState.running) throw new Error('Queue is already running.');

  const failedJobs = queueState.jobs.filter((j) => j.status === 'failed');
  if (!failedJobs.length) throw new Error('No failed scenes to retry.');

  const tabId = await ProviderRegistry.resolveTabId(
    payload.tabId || queueState.tabId,
    queueState.providerId
  );
  if (!tabId) throw new Error('Provider tab not found.');

  queueState.settings = {
    ...queueState.settings,
    maxRetries: Math.max(
      0,
      Math.min(20, payload.failureRetryMax ?? queueState.settings.failureRetryMax ?? 3)
    ),
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

function pumpQueue() {
  if (queueState.stopRequested) {
    finishQueue('stopped');
    return;
  }

  while (queueState.activeSlots < 1 && queueState.pending.length > 0 && !queueState.stopRequested) {
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

async function finishQueue(reason) {
  const summary = {
    total: queueState.jobs.length,
    done: queueState.jobs.filter((j) => j.status === 'done').length,
    failed: queueState.jobs.filter((j) => j.status === 'failed').length,
  };

  const projectName = queueState.projectName;
  const providerId = queueState.providerId;
  const settings = { ...queueState.settings };

  queueState.running = false;
  queueState.stopRequested = false;
  queueState.activeSlots = 0;
  queueState.pending = [];

  broadcastQueueUpdate();
  chrome.runtime
    .sendMessage({ type: 'QUEUE_FINISHED', reason, summary, state: getPublicQueueState() })
    .catch(() => {});

  if (summary.done > 0) {
    try {
      if (settings.exportMetadataOnComplete !== false) {
        await exportMetadata(projectName, providerId);
      }
      if (settings.exportZipOnComplete) {
        await ExportEngine.exportProjectZip(projectName, providerId);
      }
    } catch (err) {
      console.warn(LOG, 'Post-queue export failed:', err.message);
    }
  }

  console.log(LOG, `Queue finished (${reason}):`, summary);
}
