/**
 * Gemini Image Studio — Scene input parser
 * Supports script text, CSV, and JSON with Characters Present + Image Prompt.
 */
'use strict';

const SceneAdapter = (() => {
  const DEFAULT_SETTINGS = {
    maxRetries: 3,
    failureRetryMax: 3,
    jobDelaySec: 8,
    generationTimeoutSec: 180,
    concurrency: 1,
  };

  const SCENE_HEADER_RE = /^Scene\s+(\d+)\s*:?\s*$/i;

  function slugify(name, index) {
    const base = String(name || `scene_${index + 1}`)
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 60);
    const padded = String(index + 1).padStart(2, '0');
    return base ? `${padded}_${base}` : `${padded}_scene`;
  }

  function pickField(raw, keys) {
    for (const key of keys) {
      if (raw[key] != null && String(raw[key]).trim()) return String(raw[key]).trim();
    }
    return '';
  }

  function buildGenerationPrompt(charactersPresent, imagePrompt) {
    const img = String(imagePrompt || '').trim();
    if (!img) return '';

    const chars = String(charactersPresent || '').trim();
    if (!chars) return img;

    return `Characters Present: ${chars}\n\n${img}`;
  }

  function parseSceneBody(sceneName, body, index) {
    const charactersPresent =
      (body.match(/^\s*Characters\s+Present\s*:\s*(.+?)(?:\r?\n|$)/im) || [])[1]?.trim() || '';

    let imagePrompt = '';
    const promptSplit = body.split(/\r?\n\s*Image\s+Prompt\s*:\s*\r?\n?/i);
    if (promptSplit.length >= 2) {
      imagePrompt = promptSplit.slice(1).join('\n').trim();
    } else {
      imagePrompt = body
        .replace(/^\s*Characters\s+Present\s*:\s*.+?(?:\r?\n|$)/im, '')
        .trim();
    }

    return normalizeScene(
      {
        scene: sceneName || `Scene ${index + 1}`,
        characters_present: charactersPresent,
        image_prompt: imagePrompt,
      },
      index
    );
  }

  function splitScriptBlocks(raw) {
    const lines = raw.split(/\r?\n/);
    const blocks = [];
    let current = null;

    for (const line of lines) {
      const headerMatch = line.match(SCENE_HEADER_RE);
      if (headerMatch) {
        if (current) blocks.push(current);
        current = {
          scene: `Scene ${headerMatch[1]}`,
          body: [],
        };
      } else if (current) {
        current.body.push(line);
      }
    }

    if (current) blocks.push(current);
    return blocks;
  }

  function parseScriptText(raw) {
    const blocks = splitScriptBlocks(raw);
    if (!blocks.length) {
      return { ok: false, errors: ['No scenes found. Start each scene with "Scene 1:" on its own line.'] };
    }

    const scenes = [];
    const errors = [];

    blocks.forEach((block, index) => {
      const normalized = parseSceneBody(block.scene, block.body.join('\n'), index);
      if (!normalized.ok) errors.push(normalized.error);
      else scenes.push(normalized);
    });

    if (errors.length) return { ok: false, errors };
    return { ok: true, scenes, projectName: null, settings: {} };
  }

  function normalizeScene(raw, index) {
    const scene = pickField(raw, ['scene', 'name', 'title', 'scene_name']) || `Scene ${index + 1}`;
    const charactersPresent = pickField(raw, [
      'characters_present',
      'charactersPresent',
      'characters',
    ]);
    const imagePrompt = pickField(raw, [
      'image_prompt',
      'imagePrompt',
      'prompt',
      'description',
      'text',
    ]);

    if (!imagePrompt) {
      return { ok: false, error: `${scene}: Image Prompt is required.` };
    }

    const prompt = buildGenerationPrompt(charactersPresent, imagePrompt);

    return {
      ok: true,
      scene,
      characters_present: charactersPresent,
      image_prompt: imagePrompt,
      prompt,
      outputFilename: slugify(scene, index),
    };
  }

  function parseCsv(raw) {
    const rows = parseCsvRows(raw);
    if (!rows.length) {
      return { ok: false, errors: ['CSV is empty.'] };
    }

    const header = rows[0].map((h) => h.toLowerCase().replace(/[^a-z0-9]/g, ''));
    const sceneIdx = header.findIndex((h) => /^scene$|^scenename$|^name$|^title$/.test(h));
    const charsIdx = header.findIndex((h) => /characterspresent|^characters$/.test(h));
    const promptIdx = header.findIndex((h) =>
      /imageprompt|^prompt$|^description$|^text$/.test(h)
    );

    if (promptIdx === -1) {
      return {
        ok: false,
        errors: ['CSV must include an image_prompt (or prompt) column.'],
      };
    }

    const scenes = [];
    const errors = [];

    for (let i = 1; i < rows.length; i++) {
      const cols = rows[i];
      if (!cols.some((c) => c.trim())) continue;

      const sceneName =
        sceneIdx >= 0 ? cols[sceneIdx]?.trim() : `Scene ${String(i).padStart(2, '0')}`;
      const normalized = normalizeScene(
        {
          scene: sceneName,
          characters_present: charsIdx >= 0 ? cols[charsIdx]?.trim() : '',
          image_prompt: cols[promptIdx]?.trim() || '',
        },
        i - 1
      );

      if (!normalized.ok) errors.push(normalized.error);
      else scenes.push(normalized);
    }

    if (errors.length) return { ok: false, errors };
    if (!scenes.length) return { ok: false, errors: ['No scenes found in CSV.'] };
    return { ok: true, scenes, projectName: null, settings: {} };
  }

  function parseCsvRows(raw) {
    const rows = [];
    let row = [];
    let cur = '';
    let inQuotes = false;

    for (let i = 0; i < raw.length; i++) {
      const ch = raw[i];

      if (ch === '"') {
        if (inQuotes && raw[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        row.push(cur);
        cur = '';
      } else if ((ch === '\n' || ch === '\r') && !inQuotes) {
        if (ch === '\r' && raw[i + 1] === '\n') i++;
        row.push(cur);
        if (row.some((cell) => cell.trim())) rows.push(row);
        row = [];
        cur = '';
      } else {
        cur += ch;
      }
    }

    row.push(cur);
    if (row.some((cell) => cell.trim())) rows.push(row);

    return rows.map((cells) => cells.map((s) => s.replace(/^"|"$/g, '').trim()));
  }

  function parseJson(raw) {
    let data;
    try {
      data = JSON.parse(raw);
    } catch (err) {
      return { ok: false, errors: [`Invalid JSON: ${err.message}`] };
    }

    let projectName = null;
    let settings = {};
    let list = data;

    if (data && !Array.isArray(data) && typeof data === 'object') {
      projectName = data.projectName || data.project || data.name || null;
      settings = data.settings || {};
      list = data.scenes || data.items || data.phases || [];
    }

    if (!Array.isArray(list) || list.length === 0) {
      return { ok: false, errors: ['JSON must be an array of scenes or { scenes: [...] }.'] };
    }

    const scenes = [];
    const errors = [];

    list.forEach((item, index) => {
      const normalized = normalizeScene(item, index);
      if (!normalized.ok) errors.push(normalized.error);
      else scenes.push(normalized);
    });

    if (errors.length) return { ok: false, errors };
    return { ok: true, scenes, projectName, settings };
  }

  function detectFormat(raw) {
    const trimmed = raw.trim();
    if (trimmed.startsWith('[') || trimmed.startsWith('{')) return 'json';

    if (SCENE_HEADER_RE.test(trimmed) || /Image\s+Prompt\s*:/i.test(trimmed)) {
      return 'script';
    }

    const firstLine = (trimmed.split(/\r?\n/)[0] || '').toLowerCase();
    if (
      firstLine.includes(',') &&
      (/scene/.test(firstLine) || /image_prompt/.test(firstLine) || /characters/.test(firstLine))
    ) {
      return 'csv';
    }

    if (firstLine.includes(',') && /prompt/.test(firstLine)) return 'csv';

    return 'script';
  }

  function parseInput(raw) {
    if (!raw || !String(raw).trim()) {
      return { ok: false, errors: ['Paste scene script, JSON, or CSV first.'] };
    }

    const format = detectFormat(raw);
    let result;

    if (format === 'json') result = parseJson(raw);
    else if (format === 'csv') result = parseCsv(raw);
    else result = parseScriptText(raw);

    if (!result.ok) return result;

    const jobs = result.scenes.map((s, index) => ({
      scene: s.scene,
      characters_present: s.characters_present,
      image_prompt: s.image_prompt,
      prompt: s.prompt,
      outputFilename: s.outputFilename,
      meta: {
        index: index + 1,
        total: result.scenes.length,
        characters_present: s.characters_present,
      },
      title: s.scene,
    }));

    return {
      ok: true,
      format,
      projectName: result.projectName || 'gemini_project',
      settings: { ...DEFAULT_SETTINGS, ...result.settings },
      jobs,
    };
  }

  return {
    DEFAULT_SETTINGS,
    parseInput,
    parseScriptText,
    parseCsv,
    parseJson,
    buildGenerationPrompt,
    slugify,
  };
})();

if (typeof self !== 'undefined') {
  self.SceneAdapter = SceneAdapter;
}
