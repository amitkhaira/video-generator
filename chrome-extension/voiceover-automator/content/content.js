/**
 * Voiceover Automator — Content Script
 * Runs on https://aistudio.google.com/ and performs the full automation
 * sequence for Google AI Studio Speech voiceover generation.
 */
(function () {
  'use strict';

  const LOG_PREFIX = '[Voiceover Automator]';

  /** @type {{ jobId: string, aborted: boolean } | null} */
  let activeRun = null;

  class AutomationStoppedError extends Error {
    constructor() {
      super('STOPPED_BY_USER');
      this.name = 'AutomationStoppedError';
    }
  }

  function startRun(jobId) {
    activeRun = { jobId, aborted: false };
    return activeRun;
  }

  function endRun(run) {
    if (activeRun === run) activeRun = null;
  }

  function abortActiveRun() {
    if (activeRun) {
      activeRun.aborted = true;
      console.log(`${LOG_PREFIX} Abort requested for job ${activeRun.jobId}`);
    }
  }

  function throwIfAborted(run) {
    if (run?.aborted) throw new AutomationStoppedError();
  }

  // ─── Utilities ────────────────────────────────────────────────────────────

  async function sleep(ms, run) {
    const step = 200;
    let remaining = ms;
    while (remaining > 0) {
      throwIfAborted(run);
      const chunk = Math.min(step, remaining);
      await new Promise((resolve) => setTimeout(resolve, chunk));
      remaining -= chunk;
    }
  }

  /**
   * Wait for a CSS selector to appear in the DOM.
   * Uses MutationObserver for efficiency; falls back on rejection after timeout.
   */
  function waitForElement(selector, timeout = 10000, root = document, run = null) {
    return new Promise((resolve, reject) => {
      const existing = root.querySelector(selector);
      if (existing) return resolve(existing);

      const observeTarget = root === document ? document.body : root;
      if (!observeTarget) {
        return reject(new Error(`waitForElement: no root to observe for "${selector}"`));
      }

      const observer = new MutationObserver(() => {
        throwIfAborted(run);
        const found = root.querySelector(selector);
        if (found) {
          observer.disconnect();
          clearInterval(pollId);
          resolve(found);
        }
      });

      observer.observe(observeTarget, { childList: true, subtree: true });

      const pollId = setInterval(() => {
        try {
          throwIfAborted(run);
        } catch (err) {
          observer.disconnect();
          clearInterval(pollId);
          reject(err);
        }
      }, 200);

      setTimeout(() => {
        observer.disconnect();
        clearInterval(pollId);
        reject(new Error(`Timeout (${timeout}ms) waiting for selector: "${selector}"`));
      }, timeout);
    });
  }

  function countSpeechBlocks() {
    return document.querySelectorAll('ms-speech-block').length;
  }

  function findAddSpeechBlockButton() {
    return (
      document.querySelector('button.add-speech-block-button') ||
      document.querySelector('button[aria-label="Add speech block"]') ||
      Array.from(document.querySelectorAll('button')).find((btn) =>
        /add.*speech/i.test(btn.textContent || btn.getAttribute('aria-label') || '')
      ) ||
      null
    );
  }

  /**
   * Wait until speech block count exceeds previousCount (or reaches target).
   */
  async function waitForSpeechBlockCount(minCount, run, timeout = 12000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      throwIfAborted(run);
      const n = countSpeechBlocks();
      if (n >= minCount) return n;
      await sleep(150, run);
    }
    return countSpeechBlocks();
  }

  /**
   * Add speech blocks until count matches target. Bounded retries — never infinite loop.
   */
  async function ensureSpeechBlockCount(targetCount, run) {
    if (targetCount <= 0) return 0;

    let current = await waitForSpeechBlockCount(1, run, 5000);
    if (current >= targetCount) return current;

    const maxAttempts = Math.max(targetCount * 4, 20);
    let attempts = 0;

    while (current < targetCount) {
      throwIfAborted(run);

      if (attempts >= maxAttempts) {
        throw new Error(
          `Could only create ${current}/${targetCount} speech blocks after ${maxAttempts} attempts. ` +
            'Try reloading the Speech page and run again.'
        );
      }

      const addBtn = findAddSpeechBlockButton();
      if (!addBtn) {
        throw new Error('Add speech block button not found on the page.');
      }

      if (addBtn.disabled) {
        await sleep(500, run);
        attempts++;
        continue;
      }

      const before = current;
      addBtn.scrollIntoView({ block: 'center', behavior: 'instant' });
      addBtn.click();
      attempts++;

      current = await waitForSpeechBlockCount(before + 1, run, 10000);
      if (current <= before) {
        // Some AI Studio builds only enable "Add" after the last block has text
        const blockEls = document.querySelectorAll('ms-speech-block');
        const lastBlock = blockEls[blockEls.length - 1];
        if (lastBlock) {
          const ta = await waitForBlockTextarea(lastBlock, run, 3000);
          if (ta && !String(ta.value || '').trim()) {
            await fillAngularTextarea(ta, '.', run);
            await sleep(400, run);
            const addAgain = findAddSpeechBlockButton();
            if (addAgain && !addAgain.disabled) {
              addAgain.click();
              current = await waitForSpeechBlockCount(before + 1, run, 8000);
            }
          }
        }
        if (current <= before) {
          await sleep(600, run);
          current = countSpeechBlocks();
        }
      }

      await sleep(400, run);
    }

    await sleep(500, run);
    return countSpeechBlocks();
  }

  function sendToBackground(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response);
      });
    });
  }

  function findRunButton() {
    return (
      document.querySelector('ms-run-button button') ||
      document.querySelector('button[aria-label="Run"]') ||
      null
    );
  }

  function isRunButtonShowingStop() {
    const btn = findRunButton();
    const text = (btn?.textContent || '').replace(/\s+/g, ' ').trim();
    return /\bstop\b/i.test(text);
  }

  function findMusicPlayer() {
    return document.querySelector('ms-music-player');
  }

  function findDownloadButton() {
    const player = findMusicPlayer();
    const scopes = [player, document].filter(Boolean);

    for (const scope of scopes) {
      const btn =
        scope.querySelector('button.download-button') ||
        scope.querySelector('button[aria-label="Download"]') ||
        scope.querySelector('a[download]') ||
        Array.from(scope.querySelectorAll('button, a')).find((el) => {
          const label = (el.getAttribute('aria-label') || el.textContent || '').trim();
          return /^download$/i.test(label) || /download audio/i.test(label);
        });
      if (btn) return btn;
    }
    return null;
  }

  function capturePlayerSnapshot() {
    const player = findMusicPlayer();
    const audio = player?.querySelector('audio');
    const seek = player?.querySelector('input[matsliderthumb], input[type="range"]');
    const times = player ? Array.from(player.querySelectorAll('.time')) : [];
    const endLabel = times.length > 1 ? times[times.length - 1].textContent.trim() : '';

    return {
      src: audio?.currentSrc || audio?.src || '',
      duration: Number.isFinite(audio?.duration) ? audio.duration : 0,
      seekMax: seek?.max || seek?.getAttribute('max') || '',
      endLabel,
      readyState: audio?.readyState ?? 0,
    };
  }

  function isPlaceholderAudioSrc(src) {
    if (!src) return true;
    const s = src.trim();
    return s === 'data:audio/wav;' || s === 'data:audio/wav' || s === 'data:audio/wav;base64,';
  }

  function hasPlayerSnapshotChanged(before, after) {
    if (!before || !after) return true;
    if (before.src !== after.src && !isPlaceholderAudioSrc(after.src)) return true;
    if (after.duration > 0.5 && Math.abs(after.duration - before.duration) > 0.25) return true;
    if (before.seekMax !== after.seekMax && after.seekMax && after.seekMax !== '0') return true;
    if (before.endLabel !== after.endLabel && after.endLabel && after.endLabel !== '0:00') return true;
    return false;
  }

  function isElementDisabled(el) {
    if (!el) return true;
    if (el.getAttribute('data-disabled') === 'true') return true;
    return el.disabled === true || el.getAttribute('aria-disabled') === 'true';
  }

  function isElementVisible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function isRunInProgress() {
    if (isRunButtonShowingStop()) return true;

    const runHost = document.querySelector('ms-run-button');
    if (runHost?.querySelector('.spin, .progress_activity, mat-spinner, .mat-mdc-progress-spinner')) {
      return true;
    }

    const runBtn = findRunButton();
    if (runBtn?.getAttribute('aria-busy') === 'true') return true;

    const player = findMusicPlayer();
    if (player?.querySelector('mat-spinner, .mat-mdc-progress-spinner, [aria-busy="true"]')) {
      return true;
    }

    return false;
  }

  function isAudioReadyForDownload(snapshot) {
    if (isPlaceholderAudioSrc(snapshot?.src)) return false;
    if (snapshot?.duration > 0.5) return true;
    if (snapshot?.seekMax && Number(snapshot.seekMax) > 0) return true;
    if (snapshot?.endLabel && snapshot.endLabel !== '0:00') return true;
    return false;
  }

  function isDownloadReady(btn, snapshot) {
    if (!btn || !isElementVisible(btn) || isElementDisabled(btn)) return false;
    const snap = snapshot || capturePlayerSnapshot();
    return isAudioReadyForDownload(snap);
  }

  async function waitForGenerationCycleStart(run, beforeSnapshot, timeout = 30000) {
    const deadline = Date.now() + timeout;

    while (Date.now() < deadline) {
      throwIfAborted(run);

      if (isRunInProgress()) return;

      const after = capturePlayerSnapshot();
      if (hasPlayerSnapshotChanged(beforeSnapshot, after)) return;

      const dl = findDownloadButton();
      if (isDownloadReady(dl, beforeSnapshot) && dl && isElementDisabled(dl)) return;

      await sleep(300, run);
    }

    console.warn(`${LOG_PREFIX} Generation start not confirmed; waiting for new audio snapshot.`);
  }

  async function waitForGenerationComplete(run, beforeSnapshot, maxWait = 180000) {
    const pollMs = 1000;
    const requiredStable = 3;
    let elapsed = 0;
    let stableReady = 0;
    let sawInProgress = false;

    while (elapsed < maxWait) {
      throwIfAborted(run);

      if (isRunInProgress()) {
        sawInProgress = true;
        stableReady = 0;
        await sleep(pollMs, run);
        elapsed += pollMs;
        continue;
      }

      const snapshot = capturePlayerSnapshot();
      const dl = findDownloadButton();
      const audioChanged = hasPlayerSnapshotChanged(beforeSnapshot, snapshot);

      if (dl && isDownloadReady(dl, snapshot) && (audioChanged || sawInProgress)) {
        stableReady++;
        if (stableReady >= requiredStable) return { downloadBtn: dl, snapshot };
      } else {
        stableReady = 0;
      }

      await sleep(pollMs, run);
      elapsed += pollMs;
    }

    throw new Error(
      'Audio generation timed out after 3 minutes. New audio never became ready — check the Speech page for errors.'
    );
  }

  async function waitForValidAudioBlob(run, timeout = 20000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      throwIfAborted(run);
      const player = findMusicPlayer();
      const audio = player?.querySelector('audio');
      if (!audio) {
        await sleep(300, run);
        continue;
      }

      const snapshot = capturePlayerSnapshot();
      if (!isAudioReadyForDownload(snapshot)) {
        await sleep(300, run);
        continue;
      }

      const src = audio.currentSrc || audio.src;
      try {
        const response = await fetch(src);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        const snapshot = capturePlayerSnapshot();
        const minBytes = Number(snapshot.seekMax) > 0 || snapshot.duration > 0.5 ? 128 : 512;
        if (blob.size >= minBytes) return blob;
      } catch (err) {
        console.warn(`${LOG_PREFIX} Audio fetch attempt:`, err.message);
      }

      await sleep(400, run);
    }
    throw new Error('Could not read generated audio data from the player.');
  }

  async function triggerBlobDownload(blob, config, jobId, run) {
    await sendToBackground({ type: 'ARM_DOWNLOAD_WATCHER', jobId });
    await sleep(150, run);

    const ext = blob.type.includes('mpeg') || blob.type.includes('mp3') ? '.mp3' : '.wav';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${config.outputFilename || 'audio'}${ext}`;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 10000);

    const result = await sendToBackground({ type: 'AWAIT_DOWNLOAD_START', jobId, timeoutMs: 25000 });
    if (!result?.ok) {
      throw new Error(result?.error || 'Chrome did not accept the download.');
    }
  }

  async function downloadAudioFromPlayer(config, jobId, run, downloadBtn) {
    await registerDownload(config, jobId);
    await sleep(150, run);

    try {
      const blob = await waitForValidAudioBlob(run);
      console.log(`${LOG_PREFIX} Saving audio blob (${Math.round(blob.size / 1024)} KB)`);
      await triggerBlobDownload(blob, config, jobId, run);
      return;
    } catch (blobErr) {
      console.warn(`${LOG_PREFIX} Blob download failed, trying UI button:`, blobErr.message);
    }

    const btn = downloadBtn || findDownloadButton();
    if (!btn) throw new Error('Download button not found on the player.');
    await clickDownloadAndConfirm(jobId, btn, run);
  }

  async function registerDownload(config, jobId) {
    const response = await sendToBackground({
      type: 'REGISTER_DOWNLOAD',
      jobId,
      projectName: config.projectName || 'voiceover_project',
      filename: config.outputFilename || 'audio',
    });
    if (!response?.ok) {
      throw new Error('Failed to register download with extension background.');
    }
  }

  async function clickDownloadAndConfirm(jobId, downloadBtn, run) {
    downloadBtn.scrollIntoView({ block: 'center', behavior: 'instant' });
    await sleep(250, run);

    async function attemptClick() {
      await sendToBackground({ type: 'ARM_DOWNLOAD_WATCHER', jobId });
      await sleep(100, run);
      downloadBtn.click();
      return sendToBackground({ type: 'AWAIT_DOWNLOAD_START', jobId, timeoutMs: 20000 });
    }

    let result = await attemptClick();
    if (!result?.ok) {
      console.warn(`${LOG_PREFIX} Download click retry — first attempt:`, result?.error);
      await sleep(800, run);
      result = await attemptClick();
    }

    if (!result?.ok) {
      throw new Error(
        result?.error ||
          'Download did not start. In Chrome Settings → Downloads, turn off "Ask where to save each file".'
      );
    }
  }

  /**
   * Wait until a selector is no longer present in the DOM.
   * Resolves (does not reject) on timeout to avoid blocking the pipeline.
   */
  function waitForElementGone(selector, timeout = 8000) {
    return new Promise((resolve) => {
      if (!document.querySelector(selector)) return resolve();

      const observer = new MutationObserver(() => {
        if (!document.querySelector(selector)) {
          observer.disconnect();
          resolve();
        }
      });

      observer.observe(document.body, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        resolve(); // resolve — don't block on stubborn overlays
      }, timeout);
    });
  }

  /**
   * Fill an Angular <textarea> by bypassing Angular's internal value tracking.
   * Sets the native value, dispatches required events so Angular's FormControl
   * picks up the change, and also sets `data-value` on the parent
   * ms-autosize-textarea if present.
   */
  async function fillAngularTextarea(el, text, run = null) {
    el.click();
    el.focus();
    await sleep(80, run);

    const nativeSetter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      'value'
    ).set;
    nativeSetter.call(el, text);

    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));

    // ms-autosize-textarea reads from data-value attribute
    const autosizeParent = el.closest('ms-autosize-textarea');
    if (autosizeParent) {
      autosizeParent.setAttribute('data-value', text);
      autosizeParent.dispatchEvent(new Event('input', { bubbles: true }));
    }

    await sleep(180, run);

    // Fallback: execCommand insertText is more reliable on some Angular builds
    if (el.value !== text) {
      el.select();
      document.execCommand('insertText', false, text);
      await sleep(100, run);
    }
  }

  /**
   * Fill an Angular <input> by bypassing Angular's internal value tracking.
   */
  function fillAngularInput(el, text) {
    el.focus();
    const nativeSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      'value'
    ).set;
    nativeSetter.call(el, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
  }

  /**
   * Send a progress update to the side panel via background queue.
   */
  function sendProgress(current, total, message, jobId) {
    chrome.runtime
      .sendMessage({
        type: 'PHASE_PROGRESS',
        jobId,
        current,
        total,
        message,
        step: current,
      })
      .catch(() => {});
  }

  /**
   * Wait for the Angular Material CDK menu panel to appear in the overlay.
   */
  function waitForMenuPanel(timeout = 6000) {
    return new Promise((resolve, reject) => {
      const overlay = document.querySelector('.cdk-overlay-container');
      if (!overlay) return reject(new Error('CDK overlay container not found'));

      const existing = overlay.querySelector('.mat-mdc-menu-panel');
      if (existing) return resolve(existing);

      const observer = new MutationObserver(() => {
        const el = overlay.querySelector('.mat-mdc-menu-panel');
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });

      observer.observe(overlay, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error('CDK menu panel did not appear within timeout'));
      }, timeout);
    });
  }

  /**
   * Wait for the Speaker Settings mat-dialog-container to appear.
   */
  function waitForModal(timeout = 10000) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector('mat-dialog-container');
      if (existing) return resolve(existing);

      // The modal renders inside .cdk-overlay-container which is inside <body>
      const observeRoot = document.querySelector('.cdk-overlay-container') || document.body;

      const observer = new MutationObserver(() => {
        const el = document.querySelector('mat-dialog-container');
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });

      observer.observe(observeRoot, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error('Speaker settings modal did not appear'));
      }, timeout);
    });
  }

  /**
   * Click a menu item by its visible text label.
   *
   * @param {string} labelText  - Exact text label to match
   * @param {boolean} isAccent  - Accent items have plain text nodes; Style/Pace
   *                             items have a <span class="preset-label">
   */
  async function clickMenuOption(labelText, isAccent = false, run = null) {
    const panel = await waitForMenuPanel();
    await sleep(200, run); // wait for menu items to fully render

    const buttons = Array.from(panel.querySelectorAll('button.mat-mdc-menu-item'));

    for (const btn of buttons) {
      let text;
      if (!isAccent) {
        const span = btn.querySelector('span.preset-label');
        text = span ? span.textContent.trim() : btn.textContent.trim();
      } else {
        text = btn.textContent.trim();
      }

      if (text === labelText || text.includes(labelText)) {
        btn.click();
        await sleep(300, run);
        return;
      }
    }

    const available = buttons.map((b) => b.textContent.trim()).join(' | ');
    throw new Error(`Menu option "${labelText}" not found. Available: [${available}]`);
  }

  async function waitForBlockTextarea(blockEl, run, timeout = 8000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      throwIfAborted(run);
      const textarea =
        blockEl.querySelector('textarea[aria-label="Speech block text"]') ||
        blockEl.querySelector('ms-autosize-textarea textarea') ||
        blockEl.querySelector('textarea');
      if (textarea) return textarea;
      await sleep(150, run);
    }
    return null;
  }

  /**
   * Returns the index of the first block in the blocks array that has the given speakerIndex.
   * Falls back to speakerIndex itself so single-speaker configs still work.
   */
  function findFirstBlockForSpeaker(speakerIndex, blocks) {
    const idx = blocks.findIndex((b) => b.speakerIndex === speakerIndex);
    return idx >= 0 ? idx : speakerIndex;
  }

  /**
   * Pre-calculate total step count for accurate progress bar.
   */
  function calculateTotalSteps(config) {
    let total = 0;
    if (config.scene) total++;
    if (config.sampleContext) total++;
    if (config.clearExistingBlocks) total++;
    total++; // adding blocks
    total += (config.blocks || []).length; // fill each block text
    // Per speaker: alias + open modal + audio profile + style + pace + accent + voice + close = 8
    total += (config.speakers || []).length * 8;
    total += 3; // run + wait-for-generation + download
    return total;
  }

  // ─── Main Automation ──────────────────────────────────────────────────────

  async function runAutomation(config, jobId) {
    const run = startRun(jobId);
    const total = calculateTotalSteps(config);
    let current = 0;

    const progress = (message) => {
      current++;
      sendProgress(current, total, message, jobId);
      console.log(`${LOG_PREFIX} [${current}/${total}] ${message}`);
    };

    try {
      throwIfAborted(run);

      // ── 1. Fill Scene ──────────────────────────────────────────────────
      if (config.scene) {
        progress('Filling Scene textarea…');
        const sceneEl = await waitForElement('textarea[aria-label="Scene"]', 10000, document, run);
        await fillAngularTextarea(sceneEl, config.scene, run);
        await sleep(400, run);
      }

      // ── 2. Fill Sample Context ─────────────────────────────────────────
      if (config.sampleContext) {
        progress('Filling Sample Context textarea…');
        const ctxEl = await waitForElement('textarea[aria-label="Sample Context"]', 10000, document, run);
        await fillAngularTextarea(ctxEl, config.sampleContext, run);
        await sleep(400, run);
      }

      // ── 3. Clear existing speech blocks ───────────────────────────────
      if (config.clearExistingBlocks) {
        progress('Clearing existing speech blocks…');
        let deleteBtns = document.querySelectorAll('button[aria-label="Delete speech block"]');
        let safety = 0;
        while (deleteBtns.length > 0 && safety < 30) {
          throwIfAborted(run);
          deleteBtns[0].click();
          await sleep(450, run);
          deleteBtns = document.querySelectorAll('button[aria-label="Delete speech block"]');
          safety++;
        }
        await sleep(500, run);
      }

      // ── 4. Add new speech blocks (dynamic count, bounded retries) ─────
      const blocks = config.blocks || [];
      progress(`Adding ${blocks.length} speech block(s)…`);

      const finalCount = await ensureSpeechBlockCount(blocks.length, run);
      if (finalCount < blocks.length) {
        throw new Error(`Expected ${blocks.length} speech blocks but found ${finalCount} in the DOM.`);
      }

      // ── 5. Fill each block's textarea ─────────────────────────────────
      for (let i = 0; i < blocks.length; i++) {
        throwIfAborted(run);
        const preview = blocks[i].text.substring(0, 40).replace(/\n/g, ' ');
        progress(`Filling block ${i + 1}/${blocks.length}: "${preview}…"`);

        const blockEls = document.querySelectorAll('ms-speech-block');
        const blockEl = blockEls[i];
        if (!blockEl) {
          throw new Error(
            `Speech block element [${i}] not found (DOM has ${blockEls.length}, need ${blocks.length}).`
          );
        }

        blockEl.scrollIntoView({ block: 'center', behavior: 'instant' });
        const textarea = await waitForBlockTextarea(blockEl, run);
        if (!textarea) throw new Error(`Textarea not found in speech block [${i}]`);

        await fillAngularTextarea(textarea, blocks[i].text, run);
        await sleep(400, run);
      }

      await sleep(600, run);

      // ── 6. Configure each unique speaker ──────────────────────────────
      const speakers = config.speakers || [];
      const configuredSpeakers = new Set();

      for (const speaker of speakers) {
        throwIfAborted(run);
        if (configuredSpeakers.has(speaker.speakerIndex)) continue;
        configuredSpeakers.add(speaker.speakerIndex);

        // 6a. Set alias name in the RIGHT SIDE PANEL (not modal)
        progress(`Setting alias: Speaker ${speaker.speakerIndex} → "${speaker.aliasName}"`);
        const aliasInputs = document.querySelectorAll('input[aria-label="Speaker name"]');
        const aliasInput = aliasInputs[speaker.speakerIndex];
        if (aliasInput) {
          fillAngularInput(aliasInput, speaker.aliasName);
          await sleep(400, run);
        } else {
          console.warn(
            `${LOG_PREFIX} Alias input not found for speaker index ${speaker.speakerIndex} ` +
              `(found ${aliasInputs.length} total)`
          );
        }

        // 6b. Open speaker settings modal via voice chip
        progress(`Opening speaker settings for "${speaker.aliasName}"…`);
        const blockIndex = findFirstBlockForSpeaker(speaker.speakerIndex, blocks);
        const blockEls = document.querySelectorAll('ms-speech-block');
        const targetBlock = blockEls[blockIndex];
        if (!targetBlock) {
          throw new Error(
            `Cannot find speech block [${blockIndex}] to open speaker settings for "${speaker.aliasName}"`
          );
        }

        const voiceChip = targetBlock.querySelector('button.voice-chip');
        if (!voiceChip) {
          throw new Error(`voice-chip button not found in block [${blockIndex}]`);
        }

        voiceChip.click();
        await sleep(600, run);

        const modal = await waitForModal(10000);
        await sleep(500, run);

        // 6c. Fill Audio Profile
        progress(`Setting audio profile for "${speaker.aliasName}"…`);
        if (speaker.audioProfile) {
          let profileArea =
            modal.querySelector('ms-speaker-settings-panel textarea') ||
            modal.querySelector('textarea[placeholder*="voice"]') ||
            modal.querySelector('textarea[placeholder*="Voice"]');

          if (!profileArea) {
            // Fallback: wait for it globally
            profileArea = await waitForElement(
              'ms-speaker-settings-panel textarea',
              5000
            ).catch(() => null);
          }

          if (profileArea) {
            await fillAngularTextarea(profileArea, speaker.audioProfile, run);
            await sleep(400, run);
          } else {
            console.warn(`${LOG_PREFIX} Audio profile textarea not found for "${speaker.aliasName}"`);
          }
        }

        // 6d. Select Style
        progress(`Setting style for "${speaker.aliasName}": ${speaker.style}`);
        if (speaker.style) {
          const styleBtn =
            document.querySelector('ms-speaker-settings-panel button[aria-label="Style"]') ||
            modal.querySelector('button[aria-label="Style"]');
          if (styleBtn) {
            styleBtn.click();
            await sleep(400, run);
            await clickMenuOption(speaker.style, false, run);
            await sleep(400, run);
          } else {
            console.warn(`${LOG_PREFIX} Style button not found`);
          }
        }

        // 6e. Select Pace
        progress(`Setting pace for "${speaker.aliasName}": ${speaker.pace}`);
        if (speaker.pace) {
          const paceBtn =
            document.querySelector('ms-speaker-settings-panel button[aria-label="Pace"]') ||
            modal.querySelector('button[aria-label="Pace"]');
          if (paceBtn) {
            paceBtn.click();
            await sleep(400, run);
            await clickMenuOption(speaker.pace, false, run);
            await sleep(400, run);
          } else {
            console.warn(`${LOG_PREFIX} Pace button not found`);
          }
        }

        // 6f. Select Accent
        progress(`Setting accent for "${speaker.aliasName}": ${speaker.accent}`);
        if (speaker.accent) {
          const accentBtn =
            document.querySelector('ms-speaker-settings-panel button[aria-label="Accent"]') ||
            modal.querySelector('button[aria-label="Accent"]');
          if (accentBtn) {
            accentBtn.click();
            await sleep(400, run);
            await clickMenuOption(speaker.accent, true, run);
            await sleep(400, run);
          } else {
            console.warn(`${LOG_PREFIX} Accent button not found`);
          }
        }

        // 6g. Select Voice
        progress(`Selecting voice for "${speaker.aliasName}": ${speaker.voice}`);
        if (speaker.voice) {
          // Search to filter the voice list
          const searchInput = document.querySelector('input[placeholder="Search voices"]');
          if (searchInput) {
            fillAngularInput(searchInput, speaker.voice);
            await sleep(700, run); // Allow search debounce
          }

          // Find and click the voice card
          let voiceCard = document.querySelector(
            `div.voice-card[data-voice-name="${speaker.voice}"]`
          );

          if (!voiceCard) {
            voiceCard = await waitForElement(
              `div.voice-card[data-voice-name="${speaker.voice}"]`,
              4000
            ).catch(() => null);
          }

          if (voiceCard) {
            const cardBtn = voiceCard.querySelector('button') || voiceCard;
            cardBtn.click();
            await sleep(400, run);
          } else {
            throw new Error(`Voice card not found for: "${speaker.voice}". Check spelling.`);
          }
        }

        // 6h. Close modal
        progress(`Closing speaker settings panel for "${speaker.aliasName}"…`);
        const closeBtn =
          document.querySelector('mat-dialog-container button[aria-label="Close panel"]') ||
          document.querySelector('button[aria-label="Close panel"]');

        if (closeBtn) {
          closeBtn.click();
        } else {
          // Fallback: Escape key
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        }

        await sleep(600, run);
        await waitForElementGone('mat-dialog-container', 5000);
        await sleep(400, run);
      }

      await sleep(600, run);

      // ── 7. Click Run and confirm generation started ────────────────────
      progress('Clicking Run to generate audio…');
      let runBtn = findRunButton();
      if (!runBtn) {
        runBtn = await waitForElement('ms-run-button button', 10000, document, run);
      }

      if (isElementDisabled(runBtn)) {
        throw new Error('Run button is disabled. Check that all blocks have text and speakers are configured.');
      }

      const beforeSnapshot = capturePlayerSnapshot();

      runBtn.scrollIntoView({ block: 'center', behavior: 'instant' });
      runBtn.click();
      await sleep(400, run);

      progress('Waiting for generation to start…');
      await waitForGenerationCycleStart(run, beforeSnapshot);

      // ── 8. Wait until NEW audio is ready ───────────────────────────────
      progress('Generating audio (up to 3 minutes)…');
      let lastStatusAt = Date.now();
      const statusInterval = setInterval(() => {
        if (Date.now() - lastStatusAt >= 15000) {
          lastStatusAt = Date.now();
          sendProgress(current, total, 'Still generating audio…', jobId);
        }
      }, 3000);

      let downloadBtn;
      try {
        const result = await waitForGenerationComplete(run, beforeSnapshot);
        downloadBtn = result.downloadBtn;
      } finally {
        clearInterval(statusInterval);
      }

      progress('Audio ready — saving file…');

      // ── 9. Fetch audio blob & download (fallback: UI button) ───────────
      throwIfAborted(run);
      progress(
        `Downloading${config.outputFilename ? ` as "${config.projectName}/${config.outputFilename}"` : ''}…`
      );
      await downloadAudioFromPlayer(config, jobId, run, downloadBtn);
      await sleep(500, run);

      chrome.runtime
        .sendMessage({
          type: 'PHASE_COMPLETE',
          jobId,
          message: `Phase ${config.meta?.phase ?? ''} done — ${config.outputFilename || 'audio'}`,
        })
        .catch(() => {});

      console.log(`${LOG_PREFIX} Phase completed successfully.`);
    } catch (err) {
      const stopped = err instanceof AutomationStoppedError || err.message === 'STOPPED_BY_USER';
      if (stopped) {
        console.log(`${LOG_PREFIX} Automation stopped by user at step ${current}`);
      } else {
        console.error(`${LOG_PREFIX} Error at step ${current}:`, err);
      }
      chrome.runtime
        .sendMessage({
          type: 'PHASE_ERROR',
          jobId,
          step: `Step ${current}`,
          error: err.message || String(err),
          stopped,
        })
        .catch(() => {});
    } finally {
      endRun(run);
    }
  }

  // ─── Message Listener ─────────────────────────────────────────────────────

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === 'RUN_PHASE') {
      console.log(`${LOG_PREFIX} Received RUN_PHASE`, message.jobId, message.config?.title);
      runAutomation(message.config, message.jobId);
      sendResponse({ started: true });
      return true;
    }

    if (message.type === 'START_AUTOMATION') {
      console.log(`${LOG_PREFIX} Received START_AUTOMATION (legacy)`, message.config);
      runAutomation(message.config, message.jobId || 'legacy_job');
      sendResponse({ started: true });
      return true;
    }

    if (message.type === 'PING') {
      sendResponse({ alive: true, url: window.location.href });
      return true;
    }

    if (message.type === 'ABORT_AUTOMATION') {
      abortActiveRun();
      sendResponse({ ok: true });
      return true;
    }

    return true;
  });

  console.log(`${LOG_PREFIX} Content script loaded on: ${window.location.href}`);
})();
