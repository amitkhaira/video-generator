/**
 * ChatGPT image generation provider.
 * Selectors aligned with unified-composer / image mode (2025+ UI).
 */
'use strict';

const ChatGPTProvider = {
  id: 'chatgpt',
  name: 'ChatGPT',
  urlPattern: 'https://chatgpt.com/*',
  urlPatterns: ['https://chatgpt.com/*', 'https://www.chatgpt.com/*', 'https://chat.openai.com/*'],
  openUrl: 'https://chatgpt.com/',
  status: 'active',
  promptFillMode: 'prosemirror',

  selectors: {
    composerForm: ['form[data-type="unified-composer"]'],
    promptEditor: [
      '#prompt-textarea.ProseMirror',
      'div#prompt-textarea[contenteditable="true"]',
      'form[data-type="unified-composer"] div.ProseMirror[contenteditable="true"]',
      'div.ProseMirror[contenteditable="true"][role="textbox"]',
      'div.ProseMirror[contenteditable="true"]',
    ],
    hiddenTextarea: ['textarea.wcDTda_fallbackTextarea', 'textarea[name="prompt-textarea"]'],
    sendButton: [
      'button[data-testid="send-button"]',
      'button[aria-label="Send prompt"]',
      'button[aria-label="Send message"]',
      'button[aria-label*="Send"]',
    ],
    stopButton: [
      'button[data-testid="stop-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop streaming"]',
      'button[aria-label*="Stop"]',
    ],
    fileInput: [
      '#upload-photos',
      '[data-testid="upload-photos-input"]',
      '#upload-files',
      '#upload-camera',
      'input[type="file"][accept*="image"]',
    ],
    uploadButton: ['#composer-plus-btn', 'button[data-testid="composer-plus-btn"]'],
    uploadMenuItem: [
      'button[aria-label*="Add photos"]',
      '[role="menuitem"]:has(svg)',
    ],
    downloadButton: [
      'button[aria-label*="Download"]',
      'a[download]',
    ],
    assistantMessage: [
      '[data-message-author-role="assistant"]',
      'article[data-testid*="conversation-turn"]',
    ],
    streamingIndicator: [
      'button[data-testid="stop-button"]',
      '[data-testid="stop-button"]',
      '.result-streaming',
      '[data-testid="conversation-turn-content"] [aria-busy="true"]',
    ],
    imageModePill: ['button.__composer-pill[aria-label*="Image"]', 'button.__composer-pill[data-tone="accent"]'],
  },

  /** Buttons to never treat as Send in the composer trailing area */
  excludedSendLabels: [
    'start voice',
    'start dictation',
    'add files',
    'aspect ratio',
    'click to remove',
    'choose image',
  ],

  imageRules: {
    minWidth: 100,
    minHeight: 100,
    srcIncludes: [
      'blob:',
      'oaidalle',
      'openai.com',
      'oaiusercontent.com',
      'files.oaiusercontent.com',
      'chatgpt.com',
      'cdn.openai.com',
    ],
    srcExcludes: ['avatar', 'profile', 'favicon', 'emoji', 'svg+xml', 'sprites-core'],
    scopeToAssistant: true,
  },

  supportsReferenceImages: true,
  generationTimeoutSec: 300,
  jobDelaySec: 12,
};

if (typeof self !== 'undefined') {
  self.ChatGPTProvider = ChatGPTProvider;
}
