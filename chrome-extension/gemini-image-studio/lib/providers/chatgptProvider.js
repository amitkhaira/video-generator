/**
 * ChatGPT image generation provider.
 */
'use strict';

const ChatGPTProvider = {
  id: 'chatgpt',
  name: 'ChatGPT',
  urlPattern: 'https://chatgpt.com/*',
  urlPatterns: ['https://chatgpt.com/*', 'https://chat.openai.com/*'],
  openUrl: 'https://chatgpt.com/',
  status: 'active',
  promptFillMode: 'prosemirror',

  selectors: {
    promptEditor: [
      'div#prompt-textarea[contenteditable="true"]',
      'div.ProseMirror[contenteditable="true"]',
      'div[contenteditable="true"][data-id]',
      '[data-testid="message-input"]',
      'div[role="textbox"][contenteditable="true"]',
      'textarea#prompt-textarea',
      'textarea[data-id="root"]',
      'main div[contenteditable="true"]',
    ],
    sendButton: [
      'button[data-testid="send-button"]',
      'button[aria-label="Send prompt"]',
      'button[aria-label*="Send"]',
      'form button[type="submit"]',
    ],
    stopButton: [
      'button[data-testid="stop-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop"]',
    ],
    fileInput: [
      'input[type="file"][accept*="image"]',
      'input[type="file"]',
    ],
    uploadButton: [
      'button[data-testid="composer-plus-btn"]',
      'button[aria-label*="Attach"]',
      'button[aria-label*="Add photos"]',
      'button[aria-label*="Upload"]',
    ],
    uploadMenuItem: [
      'button[aria-label*="Add photos"]',
      'div[role="menuitem"]:has(svg)',
      '[data-testid="upload-file"]',
    ],
    downloadButton: [
      'button[aria-label*="Download"]',
      'a[download]',
      'button:has(svg)[aria-label*="Download"]',
    ],
    assistantMessage: [
      '[data-message-author-role="assistant"]',
      'article[data-testid*="conversation-turn"]',
    ],
    streamingIndicator: [
      '[data-testid="stop-button"]',
      '.result-streaming',
      '[aria-busy="true"]',
    ],
  },

  imageRules: {
    minWidth: 120,
    minHeight: 120,
    srcIncludes: [
      'blob:',
      'oaidalle',
      'openai.com',
      'oaiusercontent.com',
      'files.oaiusercontent.com',
      'chatgpt.com',
    ],
    srcExcludes: ['avatar', 'profile', 'favicon', 'emoji', 'svg+xml'],
    scopeToAssistant: true,
  },

  supportsReferenceImages: true,
  generationTimeoutSec: 240,
  jobDelaySec: 10,
};

if (typeof self !== 'undefined') {
  self.ChatGPTProvider = ChatGPTProvider;
}
