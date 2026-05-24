/**
 * Voiceover Automator — Popup Script
 *
 * Handles the popup UI:
 *  - Tab switching
 *  - JSON validation
 *  - Starting the automation (messaging the content script)
 *  - Displaying live progress updates received from the content script
 *  - Persisting the last-used JSON config in chrome.storage.local
 */

'use strict';

// ─── DOM References ───────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);

const jsonInput       = $('jsonInput');
const validateBtn     = $('validateBtn');
const startBtn        = $('startBtn');
const validationMsg   = $('validationMsg');
const statusDot       = $('statusDot');
const statusText      = $('statusText');
const openAiStudioBtn = $('openAiStudioBtn');
const progressSection = $('progressSection');
const progressFill    = $('progressFill');
const progressFraction = $('progressFraction');
const stepMsg         = $('stepMsg');

// ─── State ────────────────────────────────────────────────────────────────────

let automationRunning = false;

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  // Restore last-used JSON
  try {
    const { lastJson } = await chrome.storage.local.get('lastJson');
    if (lastJson) jsonInput.value = lastJson;
  } catch (_) {}

  initTabs();
  checkAiStudioConnection();
  bindEvents();

  // Listen for messages from content.js (progress/complete/error)
  chrome.runtime.onMessage.addListener(handleContentMessage);
});

// ─── Tab Switching ────────────────────────────────────────────────────────────

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(tabId);
      if (panel) panel.classList.add('active');
    });
  });
}

// ─── Event Bindings ───────────────────────────────────────────────────────────

function bindEvents() {
  validateBtn.addEventListener('click', () => {
    const config = parseAndValidateJson();
    if (config) {
      showValidation('valid', `Valid! ${config.blocks?.length ?? 0} block(s), ${config.speakers?.length ?? 0} speaker(s).`);
      startBtn.disabled = false;
    }
  });

  startBtn.addEventListener('click', startAutomation);

  openAiStudioBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'OPEN_AISTUDIO' });
    // Re-check connection after a short delay
    setTimeout(checkAiStudioConnection, 2500);
  });

  // Re-validate on input change to keep Start button state correct
  jsonInput.addEventListener('input', () => {
    if (validationMsg.classList.contains('valid')) {
      // Clear stale "Valid!" message — user has changed the content
      clearValidation();
      startBtn.disabled = true;
    }
  });
}

// ─── Connection Check ─────────────────────────────────────────────────────────

async function checkAiStudioConnection() {
  setConnectionState('checking', 'Checking AI Studio connection…');

  try {
    const tabs = await chrome.tabs.query({ url: 'https://aistudio.google.com/*' });

    if (tabs.length === 0) {
      setConnectionState('error', 'No AI Studio tab found. Click "Open" to launch it.');
      return;
    }

    // Ping the content script in the first matching tab
    const tab = tabs[0];
    try {
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
      if (response?.alive) {
        const url = response.url || tab.url || '';
        const page = url.includes('speech') ? 'Speech page' : 'AI Studio';
        setConnectionState('connected', `Connected · ${page} · Tab #${tab.id}`);
        return;
      }
    } catch (_) {
      // Content script not yet injected (e.g. page still loading)
    }

    setConnectionState('error', 'AI Studio tab found but script not ready. Reload the page.');
  } catch (err) {
    setConnectionState('error', `Connection error: ${err.message}`);
  }
}

function setConnectionState(state, text) {
  statusDot.dataset.state = state;
  statusText.textContent = text;
}

// ─── Validation ───────────────────────────────────────────────────────────────

function parseAndValidateJson() {
  const raw = jsonInput.value.trim();

  if (!raw) {
    showValidation('error', 'Please paste a JSON configuration first.');
    return null;
  }

  let config;
  try {
    config = JSON.parse(raw);
  } catch (err) {
    showValidation('error', `JSON parse error: ${err.message}`);
    return null;
  }

  // Required fields
  if (!Array.isArray(config.blocks) || config.blocks.length === 0) {
    showValidation('error', 'Missing or empty "blocks" array.');
    return null;
  }

  // Warn if speakers array is missing (single-speaker mode without alias etc.)
  if (!Array.isArray(config.speakers)) {
    showValidation('info', 'No "speakers" array found — speaker settings will not be configured.');
  }

  // Validate speakerIndex references
  if (Array.isArray(config.speakers)) {
    const speakerIndices = new Set(config.speakers.map((s) => s.speakerIndex));
    for (const block of config.blocks) {
      if (block.speakerIndex !== undefined && !speakerIndices.has(block.speakerIndex)) {
        showValidation(
          'error',
          `Block references speakerIndex ${block.speakerIndex} which is not in the speakers array.`
        );
        return null;
      }
    }
  }

  return config;
}

function showValidation(type, message) {
  validationMsg.className = `validation-msg ${type}`;
  validationMsg.textContent = message;
}

function clearValidation() {
  validationMsg.className = 'validation-msg';
  validationMsg.textContent = '';
}

// ─── Start Automation ─────────────────────────────────────────────────────────

async function startAutomation() {
  if (automationRunning) return;

  const config = parseAndValidateJson();
  if (!config) return;

  // Persist JSON for next popup open
  try {
    await chrome.storage.local.set({ lastJson: jsonInput.value });
  } catch (_) {}

  // Find the AI Studio tab
  const tabs = await chrome.tabs.query({ url: 'https://aistudio.google.com/*' });
  if (tabs.length === 0) {
    showValidation('error', 'No Google AI Studio tab found. Open AI Studio first.');
    return;
  }

  const tab = tabs[0];

  // Show progress UI
  automationRunning = true;
  startBtn.disabled = true;
  validateBtn.disabled = true;
  showProgress(0, estimateTotalSteps(config), 'Initialising automation…');

  clearValidation();

  try {
    await chrome.tabs.sendMessage(tab.id, { type: 'START_AUTOMATION', config });
  } catch (err) {
    finishWithError('Could not reach content script', err.message);
    return;
  }
}

// ─── Progress Handling ────────────────────────────────────────────────────────

function handleContentMessage(message) {
  switch (message.type) {
    case 'PROGRESS_UPDATE':
      showProgress(message.current, message.total, message.message);
      break;

    case 'AUTOMATION_COMPLETE':
      finishWithSuccess(message.message);
      break;

    case 'AUTOMATION_ERROR':
      finishWithError(message.step, message.error);
      break;

    default:
      break;
  }
}

function showProgress(current, total, message) {
  progressSection.classList.add('visible');
  progressSection.style.display = 'block';

  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  progressFill.style.width = `${pct}%`;
  progressFill.classList.remove('complete');
  progressFraction.textContent = `${current} / ${total}`;
  stepMsg.textContent = message;
  stepMsg.className = 'step-msg';
}

function finishWithSuccess(message) {
  automationRunning = false;
  startBtn.disabled = false;
  validateBtn.disabled = false;

  progressFill.style.width = '100%';
  progressFill.classList.add('complete');
  stepMsg.textContent = message || 'Automation complete!';
  stepMsg.className = 'step-msg success-msg';
}

function finishWithError(step, error) {
  automationRunning = false;
  startBtn.disabled = false;
  validateBtn.disabled = false;

  stepMsg.textContent = `Error at ${step}: ${error}`;
  stepMsg.className = 'step-msg error-msg';
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Mirrors calculateTotalSteps() in content.js for the initial progress bar.
 */
function estimateTotalSteps(config) {
  let total = 0;
  if (config.scene) total++;
  if (config.sampleContext) total++;
  if (config.clearExistingBlocks) total++;
  total++; // add blocks
  total += (config.blocks || []).length;
  total += (config.speakers || []).length * 8;
  total += 3; // run + wait + download
  return total;
}
