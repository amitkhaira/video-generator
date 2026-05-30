/**
 * Gemini Image Studio — Content Script
 * Automates prompt submission and image capture on gemini.google.com
 */
(function () {
  'use strict';

  const LOG_PREFIX = '[Gemini Image Studio]';

  const PROMPT_SELECTORS = [
    'div.ql-editor[contenteditable="true"]',
    'div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"][aria-label*="Enter a prompt"]',
    'div[contenteditable="true"][data-placeholder]',
    'textarea[aria-label*="Enter a prompt"]',
    'textarea[placeholder*="Enter a prompt"]',
    'rich-textarea div[contenteditable="true"]',
  ];

  const SEND_SELECTORS = [
    'button[aria-label*="Send"]',
    'button[mattooltip*="Send"]',
    'button.send-button',
    '[data-test-id="send-button"]',
  ];

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
    if (activeRun) activeRun.aborted = true;
  }

  function throwIfAborted(run) {
    if (run?.aborted) throw new AutomationStoppedError();
  }

  function sleep(ms, run) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const tick = () => {
        if (run?.aborted) {
          reject(new AutomationStoppedError());
          return;
        }
        if (Date.now() - start >= ms) {
          resolve();
          return;
        }
        setTimeout(tick, Math.min(100, ms - (Date.now() - start)));
      };
      setTimeout(tick, Math.min(100, ms));
    });
  }

  function sendToBackground(message) {
    return chrome.runtime.sendMessage(message);
  }

  function sendProgress(current, total, message, jobId, step) {
    sendToBackground({
      type: 'SCENE_PROGRESS',
      jobId,
      current,
      total,
      message,
      step,
    }).catch(() => {});
  }

  function queryFirst(selectors, root = document) {
    for (const sel of selectors) {
      const el = root.querySelector(sel);
      if (el && isVisible(el)) return el;
    }
    return null;
  }

  function isVisible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
  }

  async function waitForElement(selectors, timeoutMs = 15000, run) {
    const list = Array.isArray(selectors) ? selectors : [selectors];
    const deadline = Date.now() + timeoutMs;

    while (Date.now() < deadline) {
      throwIfAborted(run);
      const el = queryFirst(list);
      if (el) return el;
      await sleep(250, run);
    }

    throw new Error(`Element not found: ${list[0]}`);
  }

  function findPromptEditor() {
    return queryFirst(PROMPT_SELECTORS);
  }

  function findSendButton() {
    const btn = queryFirst(SEND_SELECTORS);
    if (btn && !btn.disabled) return btn;

    const editor = findPromptEditor();
    if (!editor) return null;

    let node = editor.parentElement;
    for (let i = 0; i < 8 && node; i++) {
      const candidate = node.querySelector('button[aria-label*="Send"], button[mattooltip*="Send"]');
      if (candidate && !candidate.disabled && isVisible(candidate)) return candidate;
      node = node.parentElement;
    }
    return btn;
  }

  function isGenerating() {
    const stopBtn = document.querySelector('button[aria-label*="Stop"], button[aria-label*="Cancel"]');
    return !!(stopBtn && isVisible(stopBtn));
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  async function fillPrompt(text, run) {
    const editor = await waitForElement(PROMPT_SELECTORS, 15000, run);
    editor.focus();
    await sleep(150, run);

    if (editor.tagName === 'TEXTAREA') {
      editor.value = text;
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      editor.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      editor.innerHTML = `<p>${escapeHtml(text).replace(/\n/g, '<br>')}</p>`;
      editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
    }

    await sleep(300, run);
  }

  async function submitPrompt(run) {
    const sendBtn = findSendButton();
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      await sleep(400, run);
      return;
    }

    const editor = findPromptEditor();
    if (!editor) throw new Error('Prompt editor not found.');

    editor.focus();
    editor.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true, cancelable: true })
    );
    await sleep(400, run);
  }

  async function waitForGenerationStart(run, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      throwIfAborted(run);
      if (isGenerating()) return;
      await sleep(300, run);
    }
    console.warn(`${LOG_PREFIX} Generation start not detected — continuing anyway.`);
  }

  async function waitForGenerationComplete(run, timeoutMs = 180000) {
    await waitForGenerationStart(run, 30000);

    const deadline = Date.now() + timeoutMs;
    let stableSince = 0;

    while (Date.now() < deadline) {
      throwIfAborted(run);

      if (!isGenerating()) {
        if (!stableSince) stableSince = Date.now();
        if (Date.now() - stableSince >= 2000) return;
      } else {
        stableSince = 0;
      }

      await sleep(500, run);
    }

    throw new Error('Image generation timed out.');
  }

  function isLikelyGeneratedImage(img) {
    if (!img || !isVisible(img)) return false;
    const src = img.currentSrc || img.src || '';
    if (!src || src.startsWith('data:image/svg')) return false;
    if (src.includes('avatar') || src.includes('profile') || src.includes('favicon')) return false;

    const w = img.naturalWidth || img.width;
    const h = img.naturalHeight || img.height;
    if (w < 120 || h < 120) return false;

    return (
      src.includes('googleusercontent.com') ||
      src.includes('gstatic.com') ||
      src.includes('blob:') ||
      (w >= 256 && h >= 256)
    );
  }

  function collectChatImages() {
    const images = [];
    const seen = new Set();

    document.querySelectorAll('img').forEach((img) => {
      if (!isLikelyGeneratedImage(img)) return;
      const src = img.currentSrc || img.src;
      if (seen.has(src)) return;
      seen.add(src);

      const responseRoot =
        img.closest('model-response, message-content, .model-response, [data-message-author="model"]') ||
        img.closest('[class*="response"]') ||
        img.parentElement;

      images.push({
        src,
        alt: img.alt || '',
        width: img.naturalWidth || img.width,
        height: img.naturalHeight || img.height,
        element: img,
        responseRoot,
      });
    });

    return images;
  }

  function getNewImagesSince(baselineUrls) {
    const baseline = new Set(baselineUrls || []);
    return collectChatImages().filter((img) => !baseline.has(img.src));
  }

  async function fetchImageBlob(src, run) {
    throwIfAborted(run);

    if (src.startsWith('blob:')) {
      const response = await fetch(src);
      return response.blob();
    }

    const response = await fetch(src, { credentials: 'include', mode: 'cors' });
    if (!response.ok) throw new Error(`Failed to fetch image (${response.status})`);
    const blob = await response.blob();
    if (blob.size < 1024) throw new Error('Downloaded image appears empty or corrupted.');
    return blob;
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Could not read image blob.'));
      reader.readAsDataURL(blob);
    });
  }

  async function registerDownload(config, jobId, metadata) {
    const response = await sendToBackground({
      type: 'REGISTER_DOWNLOAD',
      jobId,
      projectName: config.projectName || 'gemini_project',
      filename: config.outputFilename || 'image',
      metadata,
    });
    if (!response?.ok) throw new Error('Failed to register download.');
  }

  async function triggerBlobDownload(blob, config, jobId, run) {
    await sendToBackground({ type: 'ARM_DOWNLOAD_WATCHER', jobId });
    await sleep(150, run);

    const ext = blob.type.includes('jpeg') || blob.type.includes('jpg') ? '.jpg' : '.png';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${config.outputFilename || 'image'}${ext}`;
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

  async function tryUiDownloadButton(imgEl, config, jobId, run) {
    const container = imgEl.closest('button, a, [role="button"]')?.parentElement || imgEl.parentElement;
    if (!container) return false;

    const downloadBtn = container.querySelector(
      'button[aria-label*="Download"], button[mattooltip*="Download"], a[download], [data-test-id*="download"]'
    );
    if (!downloadBtn || !isVisible(downloadBtn)) return false;

    await registerDownload(config, jobId);
    await sendToBackground({ type: 'ARM_DOWNLOAD_WATCHER', jobId });
    await sleep(100, run);
    downloadBtn.click();

    const result = await sendToBackground({ type: 'AWAIT_DOWNLOAD_START', jobId, timeoutMs: 20000 });
    return !!result?.ok;
  }

  async function downloadImage(img, config, jobId, run) {
    const metadata = {
      scene: config.scene,
      characters_present: config.characters_present || config.meta?.characters_present || '',
      image_prompt: config.image_prompt || '',
      prompt: config.prompt,
      image_url: img.src,
      width: img.width,
      height: img.height,
    };

    await registerDownload(config, jobId, metadata);

    try {
      const blob = await fetchImageBlob(img.src, run);
      console.log(`${LOG_PREFIX} Saving image (${Math.round(blob.size / 1024)} KB)`);
      await triggerBlobDownload(blob, config, jobId, run);
    } catch (blobErr) {
      console.warn(`${LOG_PREFIX} Blob fetch failed, trying UI download:`, blobErr.message);
      const ok = await tryUiDownloadButton(img.element || img, config, jobId, run);
      if (!ok) throw new Error(blobErr.message || 'Could not download image.');
    }

    await sendToBackground({
      type: 'SAVE_METADATA',
      projectName: config.projectName,
      entry: metadata,
    }).catch(() => {});
  }

  async function runSceneAutomation(config, jobId) {
    const run = startRun(jobId);
    const total = 5;
    let step = 0;

    const progress = (message) => {
      step++;
      sendProgress(step, total, message, jobId, `step_${step}`);
      console.log(`${LOG_PREFIX} [${step}/${total}] ${message}`);
    };

    try {
      throwIfAborted(run);

      const baseline = collectChatImages().map((i) => i.src);

      progress(`Inserting prompt for "${config.scene}"…`);
      await fillPrompt(config.prompt, run);

      progress('Sending prompt…');
      await submitPrompt(run);

      const timeoutMs = (config.settings?.generationTimeoutSec ?? 180) * 1000;
      progress('Waiting for image generation…');
      await waitForGenerationComplete(run, timeoutMs);

      progress('Detecting generated image…');
      let newImages = getNewImagesSince(baseline);

      for (let attempt = 0; attempt < 10 && !newImages.length; attempt++) {
        await sleep(1000, run);
        newImages = getNewImagesSince(baseline);
      }

      if (!newImages.length) {
        const all = collectChatImages();
        if (all.length) newImages = [all[all.length - 1]];
      }

      if (!newImages.length) {
        throw new Error('No generated image detected in chat. Try "Create an image" mode in Gemini.');
      }

      const best = newImages.reduce((a, b) => (a.width * a.height >= b.width * b.height ? a : b));

      progress(`Downloading ${config.outputFilename}…`);
      await downloadImage(best, config, jobId, run);

      sendToBackground({
        type: 'SCENE_COMPLETE',
        jobId,
        message: `${config.scene} saved as ${config.outputFilename}`,
      }).catch(() => {});

      console.log(`${LOG_PREFIX} Scene completed: ${config.scene}`);
    } catch (err) {
      const stopped = err instanceof AutomationStoppedError || err.message === 'STOPPED_BY_USER';
      if (!stopped) console.error(`${LOG_PREFIX} Error:`, err);

      sendToBackground({
        type: 'SCENE_ERROR',
        jobId,
        step: `Step ${step}`,
        error: err.message || String(err),
        stopped,
      }).catch(() => {});
    } finally {
      endRun(run);
    }
  }

  async function downloadAllChatImages(projectName) {
    const images = collectChatImages();
    if (!images.length) {
      return { ok: false, error: 'No images found in this chat.', count: 0 };
    }

    let index = 0;
    for (const img of images) {
      index++;
      const config = {
        projectName: projectName || 'gemini_chat_export',
        outputFilename: String(index).padStart(2, '0') + '_image',
        scene: `Image ${index}`,
        prompt: img.alt || '',
      };
      const jobId = `bulk_${index}_${Date.now()}`;
      try {
        await downloadImage(img, config, jobId, null);
        await sleep(600);
      } catch (err) {
        console.warn(`${LOG_PREFIX} Bulk download failed for image ${index}:`, err.message);
      }
    }

    return { ok: true, count: images.length };
  }

  async function scanChatImages() {
    const images = collectChatImages();
    return {
      ok: true,
      count: images.length,
      images: images.map((img, i) => ({
        index: i + 1,
        src: img.src,
        width: img.width,
        height: img.height,
        alt: img.alt,
      })),
    };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === 'RUN_SCENE') {
      runSceneAutomation(message.config, message.jobId);
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

    if (message.type === 'SCAN_CHAT_IMAGES') {
      scanChatImages().then(sendResponse);
      return true;
    }

    if (message.type === 'DOWNLOAD_ALL_IMAGES') {
      downloadAllChatImages(message.projectName)
        .then(sendResponse)
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    return true;
  });

  console.log(`${LOG_PREFIX} Content script loaded on: ${window.location.href}`);
})();
