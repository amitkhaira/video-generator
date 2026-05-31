/**
 * Prompt templates, character consistency, and scene enrichment.
 */
'use strict';

const PromptEngine = (() => {
  const DEFAULT_TEMPLATE = `Characters Present: {{characters_present}}

{{image_prompt}}`;

  function substitute(template, vars) {
    return String(template || '').replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (_, key) => {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  function parseCharacterNames(charactersPresent) {
    return String(charactersPresent || '')
      .split(/[,;|]/)
      .map((n) => n.trim())
      .filter(Boolean);
  }

  function buildCharacterBlock(names, characterLibrary) {
    if (!names.length || !characterLibrary) return '';

    const blocks = [];
    names.forEach((name) => {
      const profile = characterLibrary[name] || characterLibrary[name.toLowerCase()];
      if (!profile) return;

      const parts = [];
      if (profile.appearance) parts.push(`Appearance: ${profile.appearance}`);
      if (profile.style) parts.push(`Style: ${profile.style}`);
      if (profile.notes) parts.push(`Notes: ${profile.notes}`);

      if (parts.length) {
        blocks.push(`[${name}]\n${parts.join('\n')}`);
      }
    });

    return blocks.length ? `Character Reference:\n${blocks.join('\n\n')}\n` : '';
  }

  function enrichScene(scene, options = {}) {
    const template = options.promptTemplate || DEFAULT_TEMPLATE;
    const characterLibrary = options.characterLibrary || {};
    const stylePrefix = options.stylePrefix || '';

    const charactersPresent =
      scene.characters_present || scene.meta?.characters_present || '';
    const imagePrompt = scene.image_prompt || scene.prompt || '';
    const names = parseCharacterNames(charactersPresent);
    const characterBlock = buildCharacterBlock(names, characterLibrary);

    const vars = {
      scene: scene.scene || scene.title || '',
      characters_present: charactersPresent,
      character: names[0] || '',
      characters: charactersPresent,
      image_prompt: imagePrompt,
      location: scene.location || '',
      action: scene.action || '',
      style: scene.style || '',
    };

    let body = substitute(template, vars).trim();

    if (characterBlock) {
      body = `${characterBlock}\n${body}`;
    }

    if (stylePrefix.trim()) {
      body = `${stylePrefix.trim()}\n\n${body}`;
    }

    return {
      ...scene,
      prompt: body,
      image_prompt: imagePrompt,
      characters_present: charactersPresent,
      enriched: true,
    };
  }

  function enrichJobs(jobs, options = {}) {
    return jobs.map((job) => enrichScene(job, options));
  }

  async function loadStudioConfig() {
    const stored = await chrome.storage.local.get([
      'promptTemplate',
      'characterLibrary',
      'stylePrefix',
      'activeReferenceIds',
    ]);

    return {
      promptTemplate: stored.promptTemplate || DEFAULT_TEMPLATE,
      characterLibrary: stored.characterLibrary || {},
      stylePrefix: stored.stylePrefix || '',
      activeReferenceIds: stored.activeReferenceIds || [],
    };
  }

  async function saveStudioConfig(partial) {
    await chrome.storage.local.set(partial);
  }

  return {
    DEFAULT_TEMPLATE,
    substitute,
    enrichScene,
    enrichJobs,
    loadStudioConfig,
    saveStudioConfig,
    parseCharacterNames,
    buildCharacterBlock,
  };
})();

if (typeof self !== 'undefined') {
  self.PromptEngine = PromptEngine;
}
