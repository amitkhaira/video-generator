/**
 * Phase JSON adapter — shared between side panel (validation) and content script (execution).
 *
 * Input: array of phase objects OR wrapper { projectName, settings, phases }.
 */
(function (root) {
  'use strict';

  const DEFAULT_SETTINGS = {
    maxRetries: 3,
    failureRetryMax: 3,
    jobDelaySec: 5,
    concurrency: 1,
  };

  function slugify(text) {
    return String(text || 'scene')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_|_$/g, '')
      .slice(0, 48) || 'scene';
  }

  /**
   * Normalize speaker_id values to 0-based speakerIndex for AI Studio DOM.
   */
  function buildSpeakerMap(audioBlocks) {
    const ids = [...new Set((audioBlocks || []).map((b) => b.speaker_id))].sort(
      (a, b) => a - b
    );
    const map = new Map();
    ids.forEach((id, idx) => map.set(id, idx));
    return map;
  }

  /**
   * Convert one phase object into the legacy single-run config used by content.js.
   */
  function phaseToConfig(phase, projectName) {
    const blocks = phase.audio_blocks || [];
    const speakerMap = buildSpeakerMap(blocks);

    const speakersByIndex = new Map();

    for (const block of blocks) {
      const speakerIndex = speakerMap.get(block.speaker_id);
      if (speakerIndex === undefined) continue;
      if (speakersByIndex.has(speakerIndex)) continue;

      const note = block.directors_note || {};
      speakersByIndex.set(speakerIndex, {
        speakerIndex,
        aliasName: block.character_name || `Speaker ${speakerIndex + 1}`,
        voice: block.voice,
        audioProfile: block.audio_profile || '',
        style: note.style || 'Natural',
        pace: note.pace || 'Natural',
        accent: note.accent || 'Neutral',
      });
    }

    const phaseNum = String(phase.phase ?? 0).padStart(2, '0');
    const slug = slugify(phase.scene_title);

    return {
      title: phase.scene_title || `Phase ${phase.phase}`,
      scene: phase.scene_description || '',
      sampleContext: phase.sample_context || '',
      clearExistingBlocks: true,
      outputFilename: `${phaseNum}_${slug}`,
      projectName: projectName || 'voiceover_project',
      speakers: Array.from(speakersByIndex.values()),
      blocks: blocks.map((block) => ({
        speakerIndex: speakerMap.get(block.speaker_id) ?? 0,
        text: block.dialogue || '',
      })),
      meta: {
        phase: phase.phase,
        sceneTitle: phase.scene_title,
      },
    };
  }

  function validatePhase(phase, index) {
    const errors = [];
    const label = `Phase ${index + 1}${phase.scene_title ? ` ("${phase.scene_title}")` : ''}`;

    if (phase.phase === undefined || phase.phase === null) {
      errors.push(`${label}: missing "phase" number.`);
    }
    if (!phase.scene_title || !String(phase.scene_title).trim()) {
      errors.push(`${label}: missing "scene_title".`);
    }
    if (!Array.isArray(phase.audio_blocks) || phase.audio_blocks.length === 0) {
      errors.push(`${label}: "audio_blocks" must be a non-empty array.`);
      return errors;
    }

    phase.audio_blocks.forEach((block, bi) => {
      const blockLabel = `${label}, block ${bi + 1}`;
      if (block.speaker_id === undefined || block.speaker_id === null) {
        errors.push(`${blockLabel}: missing "speaker_id".`);
      }
      if (!block.dialogue || !String(block.dialogue).trim()) {
        errors.push(`${blockLabel}: missing "dialogue".`);
      }
      if (!block.voice || !String(block.voice).trim()) {
        errors.push(`${blockLabel}: missing "voice".`);
      }
    });

    return errors;
  }

  /**
   * Parse raw JSON string or object into normalized queue payload.
   */
  function parseInput(raw) {
    let data = raw;
    if (typeof raw === 'string') {
      if (!raw.trim()) {
        return { ok: false, errors: ['Please paste a JSON configuration first.'] };
      }
      try {
        data = JSON.parse(raw);
      } catch (err) {
        return { ok: false, errors: [`JSON parse error: ${err.message}`] };
      }
    }

    let projectName = 'voiceover_project';
    let settings = { ...DEFAULT_SETTINGS };
    let phases;

    if (Array.isArray(data)) {
      phases = data;
    } else if (data && Array.isArray(data.phases)) {
      phases = data.phases;
      if (data.projectName) projectName = String(data.projectName).trim();
      if (data.settings) settings = { ...DEFAULT_SETTINGS, ...data.settings };
    } else {
      return {
        ok: false,
        errors: ['Expected a JSON array of phases or { "projectName", "settings", "phases": [...] }.'],
      };
    }

    if (phases.length === 0) {
      return { ok: false, errors: ['Phases array is empty.'] };
    }

    const errors = [];
    phases.forEach((phase, i) => errors.push(...validatePhase(phase, i)));

    if (errors.length) {
      return { ok: false, errors };
    }

    const jobs = phases
      .slice()
      .sort((a, b) => (a.phase ?? 0) - (b.phase ?? 0))
      .map((phase) => phaseToConfig(phase, projectName));

    return {
      ok: true,
      projectName,
      settings,
      phases,
      jobs,
    };
  }

  const api = {
    DEFAULT_SETTINGS,
    slugify,
    phaseToConfig,
    validatePhase,
    parseInput,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  } else {
    root.PhaseAdapter = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : typeof self !== 'undefined' ? self : this);
