/**
 * Google Gemini image generation provider.
 */
'use strict';

const GeminiProvider = {
  id: 'gemini',
  name: 'Google Gemini',
  urlPattern: 'https://gemini.google.com/*',
  openUrl: 'https://gemini.google.com/app',
  status: 'active',

  selectors: {
    promptEditor: [
      'div.ql-editor[contenteditable="true"]',
      'div[contenteditable="true"][role="textbox"]',
      'div[contenteditable="true"][aria-label*="Enter a prompt"]',
      'textarea[aria-label*="Enter a prompt"]',
      'rich-textarea div[contenteditable="true"]',
    ],
    sendButton: [
      'button[aria-label*="Send"]',
      'button[mattooltip*="Send"]',
      '[data-test-id="send-button"]',
    ],
    stopButton: ['button[aria-label*="Stop"]', 'button[aria-label*="Cancel"]'],
    fileInput: [
      'input[type="file"][accept*="image"]',
      'input[type="file"]',
    ],
    uploadButton: [
      'button[aria-label*="Upload"]',
      'button[mattooltip*="Upload"]',
      'button[aria-label*="Add image"]',
      'button[aria-label*="Attach"]',
    ],
    downloadButton: [
      'button[aria-label*="Download"]',
      'button[mattooltip*="Download"]',
    ],
  },

  imageRules: {
    minWidth: 120,
    minHeight: 120,
    srcIncludes: ['googleusercontent.com', 'gstatic.com', 'blob:'],
    srcExcludes: ['avatar', 'profile', 'favicon'],
  },

  supportsReferenceImages: true,
  generationTimeoutSec: 180,
};

if (typeof self !== 'undefined') {
  self.GeminiProvider = GeminiProvider;
}
