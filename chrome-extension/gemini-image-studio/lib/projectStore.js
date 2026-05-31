/**
 * IndexedDB asset store for project images + reference files.
 */
'use strict';

const ProjectStore = (() => {
  const DB_NAME = 'gemini_image_studio';
  const DB_VERSION = 1;
  const STORE_ASSETS = 'assets';
  const STORE_REFERENCES = 'references';

  /** @type {IDBDatabase|null} */
  let dbPromise = null;

  function openDb() {
    if (!dbPromise) {
      dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onerror = () => reject(req.error);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(STORE_ASSETS)) {
            db.createObjectStore(STORE_ASSETS, { keyPath: 'id' });
          }
          if (!db.objectStoreNames.contains(STORE_REFERENCES)) {
            db.createObjectStore(STORE_REFERENCES, { keyPath: 'id' });
          }
        };
        req.onsuccess = () => resolve(req.result);
      });
    }
    return dbPromise;
  }

  function sanitizeProject(name) {
    return String(name || 'gemini_project').replace(/[/\\]+/g, '_');
  }

  function assetId(projectName, filename) {
    return `${sanitizeProject(projectName)}/${filename}`;
  }

  function dataUrlToArrayBuffer(dataUrl) {
    const base64 = dataUrl.split(',')[1];
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  async function putAsset({ projectName, filename, ext, mime, dataUrl, metadata }) {
    const db = await openDb();
    const id = assetId(projectName, `${filename}${ext || '.png'}`);
    const record = {
      id,
      projectName: sanitizeProject(projectName),
      filename,
      ext: ext || '.png',
      mime: mime || 'image/png',
      buffer: dataUrlToArrayBuffer(dataUrl),
      metadata: metadata || {},
      savedAt: new Date().toISOString(),
    };

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_ASSETS, 'readwrite');
      tx.objectStore(STORE_ASSETS).put(record);
      tx.oncomplete = () => resolve(record);
      tx.onerror = () => reject(tx.error);
    });
  }

  async function listProjectAssets(projectName) {
    const db = await openDb();
    const prefix = `${sanitizeProject(projectName)}/`;

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_ASSETS, 'readonly');
      const store = tx.objectStore(STORE_ASSETS);
      const req = store.getAll();
      req.onsuccess = () => {
        resolve((req.result || []).filter((r) => r.id.startsWith(prefix)));
      };
      req.onerror = () => reject(req.error);
    });
  }

  async function putReference({ id, name, mime, dataUrl }) {
    const db = await openDb();
    const record = {
      id: id || `ref_${Date.now()}`,
      name: name || 'reference',
      mime: mime || 'image/png',
      buffer: dataUrlToArrayBuffer(dataUrl),
      savedAt: new Date().toISOString(),
    };

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_REFERENCES, 'readwrite');
      tx.objectStore(STORE_REFERENCES).put(record);
      tx.oncomplete = () => resolve(record);
      tx.onerror = () => reject(tx.error);
    });
  }

  async function listReferences() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_REFERENCES, 'readonly');
      const req = tx.objectStore(STORE_REFERENCES).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function getReference(id) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_REFERENCES, 'readonly');
      const req = tx.objectStore(STORE_REFERENCES).get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  }

  async function deleteReference(id) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_REFERENCES, 'readwrite');
      tx.objectStore(STORE_REFERENCES).delete(id);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => reject(tx.error);
    });
  }

  function bufferToDataUrl(buffer, mime) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return `data:${mime || 'image/png'};base64,${btoa(binary)}`;
  }

  return {
    putAsset,
    listProjectAssets,
    putReference,
    listReferences,
    getReference,
    deleteReference,
    bufferToDataUrl,
    sanitizeProject,
    assetId,
  };
})();

if (typeof self !== 'undefined') {
  self.ProjectStore = ProjectStore;
}
