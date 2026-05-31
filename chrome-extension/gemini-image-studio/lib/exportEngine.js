/**
 * Project export: metadata JSON files on disk + ZIP bundles.
 */
'use strict';

const ExportEngine = (() => {
  function buildManifest(projectName, scenes, provider) {
    return {
      project: ProjectStore.sanitizeProject(projectName),
      provider: provider || 'gemini',
      exported_at: new Date().toISOString(),
      scene_count: scenes.length,
      scenes: scenes.map((s, i) => ({
        index: i + 1,
        scene: s.scene || s.metadata?.scene,
        filename: `${s.filename}${s.ext || '.png'}`,
        characters_present: s.metadata?.characters_present || '',
        image_prompt: s.metadata?.image_prompt || '',
        prompt_sent: s.metadata?.prompt || '',
        width: s.metadata?.width || null,
        height: s.metadata?.height || null,
        saved_at: s.savedAt || s.metadata?.saved_at || null,
      })),
    };
  }

  function buildSceneMetadata(entry, filename) {
    return {
      scene: entry.scene,
      characters_present: entry.characters_present || '',
      image_prompt: entry.image_prompt || '',
      prompt_sent: entry.prompt || entry.prompt_sent || '',
      image_file: filename,
      image_url: entry.image_url || '',
      width: entry.width || null,
      height: entry.height || null,
      provider: entry.provider || 'gemini',
      saved_at: entry.saved_at || new Date().toISOString(),
    };
  }

  async function downloadTextFile({ projectName, relativePath, content, jobId }) {
    const blob = new Blob([content], { type: 'application/json' });
    const dataUrl = await blobToDataUrl(blob);

    downloadRenameQueuePush({
      jobId: jobId || `meta_${Date.now()}`,
      projectName,
      relativePath,
    });

    return chrome.downloads.download({ url: dataUrl, saveAs: false, conflictAction: 'uniquify' });
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(blob);
    });
  }

  /** Injected by background — set via init() */
  let downloadRenameQueuePush = () => {};

  function init({ pushDownloadRename }) {
    downloadRenameQueuePush = pushDownloadRename;
  }

  async function exportMetadataFiles(projectName, scenes, provider) {
    const safe = ProjectStore.sanitizeProject(projectName);
    const manifest = buildManifest(safe, scenes, provider);

    await downloadTextFile({
      projectName: safe,
      relativePath: 'Metadata/manifest.json',
      content: JSON.stringify(manifest, null, 2),
      jobId: `manifest_${Date.now()}`,
    });

    for (const scene of scenes) {
      const fname = `${scene.filename}${scene.ext || '.png'}`;
      const meta = buildSceneMetadata(scene.metadata || scene, fname);
      await downloadTextFile({
        projectName: safe,
        relativePath: `Metadata/scenes/${scene.filename}.json`,
        content: JSON.stringify(meta, null, 2),
        jobId: `scene_meta_${scene.filename}_${Date.now()}`,
      });
    }

    return { ok: true, sceneCount: scenes.length };
  }

  async function exportProjectZip(projectName, provider) {
    const safe = ProjectStore.sanitizeProject(projectName);
    const assets = await ProjectStore.listProjectAssets(safe);

    if (!assets.length) {
      throw new Error(`No stored assets for project "${safe}". Run a queue first.`);
    }

    const zip = new JSZip();
    const imgFolder = zip.folder('Images');
    const metaFolder = zip.folder('Metadata');
    const scenesFolder = metaFolder.folder('scenes');

    const manifestScenes = [];

    assets.forEach((asset, index) => {
      const fileName = `${asset.filename}${asset.ext || '.png'}`;
      imgFolder.file(fileName, asset.buffer);
      const meta = buildSceneMetadata(asset.metadata || {}, fileName);
      scenesFolder.file(`${asset.filename}.json`, JSON.stringify(meta, null, 2));
      manifestScenes.push({
        index: index + 1,
        scene: meta.scene,
        filename: fileName,
        characters_present: meta.characters_present,
        image_prompt: meta.image_prompt,
        saved_at: asset.savedAt,
      });
    });

    const manifest = {
      project: safe,
      provider: provider || 'gemini',
      exported_at: new Date().toISOString(),
      scene_count: manifestScenes.length,
      scenes: manifestScenes,
    };
    metaFolder.file('manifest.json', JSON.stringify(manifest, null, 2));

    const promptsText = manifestScenes
      .map((s) => `# ${s.scene}\n${s.image_prompt || ''}\n`)
      .join('\n');
    zip.file('Prompts/all_prompts.txt', promptsText);

    const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
    const dataUrl = await blobToDataUrl(blob);

    return chrome.downloads.download({
      url: dataUrl,
      filename: `${safe}/${safe}_export.zip`,
      saveAs: false,
      conflictAction: 'uniquify',
    });
  }

  return {
    init,
    buildManifest,
    buildSceneMetadata,
    exportMetadataFiles,
    exportProjectZip,
  };
})();

if (typeof self !== 'undefined') {
  self.ExportEngine = ExportEngine;
}
