/**
 * Gemini Image Studio — Content Script (provider-aware)
 */
(function () {
  'use strict';

  const LOG_PREFIX = '[Gemini Image Studio]';

  /** @type {{ jobId: string, aborted: boolean } | null} */
  let activeRun = null;

  /** @type {object|null} */
  let activeProvider = null;

  class AutomationStoppedError extends Error {
    constructor() {
      super('STOPPED_BY_USER');
      this.name = 'AutomationStoppedError';
    }
  }

  function detectPageProvider() {
    const url = window.location.href;
    if (/chatgpt\.com|chat\.openai\.com/.test(url) && typeof ChatGPTProvider !== 'undefined') {
      return ChatGPTProvider;
    }
    if (/gemini\.google\.com/.test(url) && typeof GeminiProvider !== 'undefined') {
      return GeminiProvider;
    }
    return typeof GeminiProvider !== 'undefined' ? GeminiProvider : null;
  }

  function getProvider(config) {
    return config?.provider || detectPageProvider() || {
      id: 'gemini',
      selectors: {
        promptEditor: ['div.ql-editor[contenteditable="true"]', 'div[contenteditable="true"][role="textbox"]'],
        sendButton: ['button[aria-label*="Send"]'],
        stopButton: ['button[aria-label*="Stop"]', 'button[aria-label*="Cancel"]'],
        fileInput: ['input[type="file"]'],
        uploadButton: ['button[aria-label*="Upload"]', 'button[aria-label*="Attach"]'],
        downloadButton: ['button[aria-label*="Download"]'],
      },
      imageRules: {
        minWidth: 120,
        minHeight: 120,
        srcIncludes: ['googleusercontent.com', 'gstatic.com', 'blob:'],
        srcExcludes: ['avatar', 'profile', 'favicon'],
      },
    };
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
    const list = Array.isArray(selectors) ? selectors : [selectors];
    for (const sel of list) {
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

  function findPromptEditor(provider) {
    const editor = queryFirst(provider.selectors.promptEditor);
    if (editor) return editor;

    if (provider.id === 'chatgpt') {
      const editables = document.querySelectorAll('div[contenteditable="true"]');
      for (const el of editables) {
        if (!isVisible(el)) continue;
        const rect = el.getBoundingClientRect();
        if (rect.height >= 30 && rect.width >= 100) return el;
      }
    }

    return null;
  }

  function findSendButton(provider) {
    for (const sel of provider.selectors.sendButton || []) {
      const btn = document.querySelector(sel);
      if (btn && isVisible(btn) && !btn.disabled) return btn;
    }

    const editor = findPromptEditor(provider);
    if (!editor) return null;

    const form = editor.closest('form');
    if (form) {
      const buttons = form.querySelectorAll('button:not([disabled])');
      if (buttons.length) return buttons[buttons.length - 1];
    }

    return queryFirst(provider.selectors.sendButton);
  }

  function isGenerating(provider) {
    if (queryFirst(provider.selectors.stopButton)) return true;

    if (provider.id === 'chatgpt') {
      if (queryFirst(provider.selectors.streamingIndicator)) return true;
      const busy = document.querySelector('[data-message-author-role="assistant"] [aria-busy="true"]');
      if (busy) return true;
    }

    return false;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  async function fillPromptProseMirror(editor, text, run) {
    editor.focus();
    await sleep(150, run);

    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);

    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);

    const inserted = document.execCommand('insertText', false, text);
    if (!inserted) {
      editor.textContent = text;
    }

    editor.dispatchEvent(
      new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: text })
    );
    await sleep(400, run);
  }

  async function fillPrompt(text, run, provider) {
    const deadline = Date.now() + 15000;
    let editor = null;

    while (Date.now() < deadline) {
      throwIfAborted(run);
      editor = findPromptEditor(provider);
      if (editor) break;
      await sleep(250, run);
    }

    if (!editor) throw new Error('Prompt editor not found.');

    if (provider.promptFillMode === 'prosemirror' || provider.id === 'chatgpt') {
      await fillPromptProseMirror(editor, text, run);
      return;
    }

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

  async function waitForSendButton(provider, run, timeoutMs = 8000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      throwIfAborted(run);
      const btn = findSendButton(provider);
      if (btn && !btn.disabled) return btn;
      await sleep(200, run);
    }
    return findSendButton(provider);
  }

  async function submitPrompt(run, provider) {
    const sendBtn = await waitForSendButton(provider, run);
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      await sleep(500, run);
      return;
    }

    const editor = findPromptEditor(provider);
    if (!editor) throw new Error('Prompt editor not found.');

    editor.focus();
    editor.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        bubbles: true,
        cancelable: true,
      })
    );
    await sleep(400, run);
  }

  function dataUrlToFile(dataUrl, name, mime) {
    const [header, base64] = dataUrl.split(',');
    const type = mime || header.match(/data:([^;]+)/)?.[1] || 'image/png';
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new File([bytes], name || 'reference.png', { type });
  }

  async function uploadReferenceImages(referenceImages, run, provider) {
    if (!referenceImages?.length) return;

    for (const ref of referenceImages) {
      throwIfAborted(run);

      let fileInput = queryFirst(provider.selectors.fileInput);

      if (!fileInput) {
        const uploadBtn = queryFirst(provider.selectors.uploadButton);
        if (uploadBtn) {
          uploadBtn.click();
          await sleep(600, run);

          if (provider.selectors.uploadMenuItem) {
            const menuItem = queryFirst(provider.selectors.uploadMenuItem);
            if (menuItem) {
              menuItem.click();
              await sleep(400, run);
            }
          }

          fileInput = queryFirst(provider.selectors.fileInput);
        }
      }

      if (!fileInput) {
        console.warn(`${LOG_PREFIX} Reference upload skipped — no file input found.`);
        continue;
      }

      const file = dataUrlToFile(ref.dataUrl, ref.name || 'reference.png', ref.mime);
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
      fileInput.dispatchEvent(new Event('input', { bubbles: true }));
      await sleep(provider.id === 'chatgpt' ? 1200 : 800, run);
    }
  }

  async function waitForGenerationStart(run, provider, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      throwIfAborted(run);
      if (isGenerating(provider)) return;
      await sleep(300, run);
    }
    console.warn(`${LOG_PREFIX} Generation start not detected — continuing.`);
  }

  async function waitForGenerationComplete(run, provider, timeoutMs = 180000) {
    await waitForGenerationStart(run, provider, 30000);

    const deadline = Date.now() + timeoutMs;
    let stableSince = 0;
    const stableMs = provider.id === 'chatgpt' ? 3000 : 2000;

    while (Date.now() < deadline) {
      throwIfAborted(run);

      if (!isGenerating(provider)) {
        if (!stableSince) stableSince = Date.now();
        if (Date.now() - stableSince >= stableMs) return;
      } else {
        stableSince = 0;
      }

      await sleep(500, run);
    }

    throw new Error('Image generation timed out.');
  }

  function isLikelyGeneratedImage(img, rules) {
    if (!img || !isVisible(img)) return false;
    const src = img.currentSrc || img.src || '';
    if (!src || src.startsWith('data:image/svg')) return false;

    for (const ex of rules.srcExcludes || []) {
      if (src.includes(ex)) return false;
    }

    const w = img.naturalWidth || img.width;
    const h = img.naturalHeight || img.height;
    if (w < (rules.minWidth || 120) || h < (rules.minHeight || 120)) return false;

    const includes = rules.srcIncludes || [];
    if (includes.some((part) => src.includes(part))) return true;
    return w >= 256 && h >= 256;
  }

  function getImageSearchRoots(provider) {
    if (provider.imageRules?.scopeToAssistant) {
      const roots = [];
      for (const sel of provider.selectors.assistantMessage || ['[data-message-author-role="assistant"]']) {
        document.querySelectorAll(sel).forEach((el) => roots.push(el));
      }
      if (roots.length) return roots;
    }
    return [document];
  }

  function collectChatImages(provider) {
    const rules = provider.imageRules || {};
    const images = [];
    const seen = new Set();
    const roots = getImageSearchRoots(provider);

    roots.forEach((root) => {
      root.querySelectorAll('img').forEach((img) => {
        if (!isLikelyGeneratedImage(img, rules)) return;
        const src = img.currentSrc || img.src;
        if (seen.has(src)) return;
        seen.add(src);

        images.push({
          src,
          alt: img.alt || '',
          width: img.naturalWidth || img.width,
          height: img.naturalHeight || img.height,
          element: img,
        });
      });
    });

    return images;
  }

  function getNewImagesSince(baselineUrls, provider) {
    const baseline = new Set(baselineUrls || []);
    return collectChatImages(provider).filter((img) => !baseline.has(img.src));
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

    return ext;
  }

  async function tryUiDownloadButton(imgEl, config, jobId, run, provider) {
    const container = imgEl.closest('button, a, [role="button"]')?.parentElement || imgEl.parentElement;
    if (!container) return false;

    const downloadBtn = queryFirst(provider.selectors.downloadButton, container);
    if (!downloadBtn) return false;

    await registerDownload(config, jobId);
    await sendToBackground({ type: 'ARM_DOWNLOAD_WATCHER', jobId });
    await sleep(100, run);
    downloadBtn.click();

    const result = await sendToBackground({ type: 'AWAIT_DOWNLOAD_START', jobId, timeoutMs: 20000 });
    return !!result?.ok;
  }

  async function downloadImage(img, config, jobId, run, provider) {
    const metadata = {
      scene: config.scene,
      characters_present: config.characters_present || config.meta?.characters_present || '',
      image_prompt: config.image_prompt || '',
      prompt: config.prompt,
      provider: config.providerId || 'gemini',
      image_url: img.src,
      width: img.width,
      height: img.height,
    };

    await registerDownload(config, jobId, metadata);

    let blob;
    let ext = '.png';

    try {
      blob = await fetchImageBlob(img.src, run);
      console.log(`${LOG_PREFIX} Saving image (${Math.round(blob.size / 1024)} KB)`);
      ext = await triggerBlobDownload(blob, config, jobId, run);
    } catch (blobErr) {
      console.warn(`${LOG_PREFIX} Blob fetch failed, trying UI download:`, blobErr.message);
      const ok = await tryUiDownloadButton(img.element || img, config, jobId, run, provider);
      if (!ok) throw new Error(blobErr.message || 'Could not download image.');
      blob = await fetchImageBlob(img.src, run).catch(() => null);
    }

    if (blob) {
      const dataUrl = await blobToDataUrl(blob);
      await sendToBackground({
        type: 'STORE_PROJECT_ASSET',
        projectName: config.projectName,
        filename: config.outputFilename,
        ext,
        mime: blob.type,
        dataUrl,
        metadata,
        providerId: config.providerId,
      });
    }

    await sendToBackground({
      type: 'SAVE_METADATA',
      projectName: config.projectName,
      entry: metadata,
    }).catch(() => {});
  }

  async function runSceneAutomation(config, jobId) {
    const run = startRun(jobId);
    const provider = getProvider(config);
    activeProvider = provider;
    const total = 6;
    let step = 0;

    const progress = (message) => {
      step++;
      sendProgress(step, total, message, jobId, `step_${step}`);
      console.log(`${LOG_PREFIX} [${step}/${total}] ${message}`);
    };

    try {
      throwIfAborted(run);

      const baseline = collectChatImages(provider).map((i) => i.src);

      if (config.referenceImages?.length) {
        progress(`Uploading ${config.referenceImages.length} reference image(s)…`);
        await uploadReferenceImages(config.referenceImages, run, provider);
      }

      progress(`Inserting prompt for "${config.scene}"…`);
      await fillPrompt(config.prompt, run, provider);

      progress('Sending prompt…');
      await submitPrompt(run, provider);

      const timeoutMs = (config.settings?.generationTimeoutSec ?? 180) * 1000;
      progress('Waiting for image generation…');
      await waitForGenerationComplete(run, provider, timeoutMs);

      progress('Detecting generated image…');
      let newImages = getNewImagesSince(baseline, provider);

      for (let attempt = 0; attempt < 10 && !newImages.length; attempt++) {
        await sleep(1000, run);
        newImages = getNewImagesSince(baseline, provider);
      }

      if (!newImages.length) {
        const all = collectChatImages(provider);
        if (all.length) newImages = [all[all.length - 1]];
      }

      if (!newImages.length) {
        throw new Error(
          provider.id === 'chatgpt'
            ? 'No generated image detected. Use a GPT-4o / Images model chat and ask ChatGPT to create an image.'
            : 'No generated image detected in chat.'
        );
      }

      const best = newImages.reduce((a, b) => (a.width * a.height >= b.width * b.height ? a : b));

      progress(`Downloading ${config.outputFilename}…`);
      await downloadImage(best, config, jobId, run, provider);

      sendToBackground({
        type: 'SCENE_COMPLETE',
        jobId,
        message: `${config.scene} saved as ${config.outputFilename}`,
      }).catch(() => {});
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

  async function downloadAllChatImages(projectName, providerId) {
    const provider = activeProvider || getProvider({});
    const images = collectChatImages(provider);
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
        providerId: providerId || 'gemini',
      };
      const jobId = `bulk_${index}_${Date.now()}`;
      try {
        await downloadImage(img, config, jobId, null, provider);
        await sleep(600);
      } catch (err) {
        console.warn(`${LOG_PREFIX} Bulk download failed for image ${index}:`, err.message);
      }
    }

    return { ok: true, count: images.length };
  }

  async function scanChatImages() {
    const provider = activeProvider || detectPageProvider() || getProvider({});
    activeProvider = provider;
    const images = collectChatImages(provider);
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
      const pageProvider = detectPageProvider();
      activeProvider = pageProvider;
      const expectedId = message.providerId || pageProvider?.id;
      const alive = pageProvider && (!message.providerId || pageProvider.id === message.providerId);
      sendResponse({
        alive,
        url: window.location.href,
        providerId: pageProvider?.id || null,
        providerName: pageProvider?.name || null,
        expectedId,
      });
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
      downloadAllChatImages(message.projectName, message.providerId)
        .then(sendResponse)
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    return true;
  });

  activeProvider = detectPageProvider();
  console.log(
    `${LOG_PREFIX} Content script loaded on: ${window.location.href}`,
    activeProvider ? `(provider: ${activeProvider.id})` : ''
  );
})();
