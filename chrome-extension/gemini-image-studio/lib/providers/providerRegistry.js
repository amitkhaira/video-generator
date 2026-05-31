/**
 * Multi-provider registry and tab resolution.
 */
'use strict';

const ProviderRegistry = (() => {
  /** @type {Map<string, object>} */
  const providers = new Map();

  function register(provider) {
    if (!provider?.id) throw new Error('Provider must have an id.');
    providers.set(provider.id, provider);
  }

  function get(id) {
    return providers.get(id) || providers.get('gemini');
  }

  function list() {
    return [...providers.values()];
  }

  function listActive() {
    return list().filter((p) => p.status === 'active');
  }

  function getUrlPatterns(provider) {
    if (provider.urlPatterns?.length) return provider.urlPatterns;
    if (provider.urlPattern) return [provider.urlPattern];
    return [];
  }

  function matchProviderForUrl(url) {
    for (const provider of providers.values()) {
      for (const pattern of getUrlPatterns(provider)) {
        const glob = pattern.replace(/\*/g, '.*');
        if (new RegExp(`^${glob}$`).test(url || '')) return provider;
      }
    }
    return null;
  }

  async function resolveTabId(preferredTabId, providerId) {
    const provider = get(providerId);

    if (preferredTabId) {
      try {
        const tab = await chrome.tabs.get(preferredTabId);
        const matched = matchProviderForUrl(tab?.url || '');
        if (matched?.id === provider.id) return tab.id;
      } catch (_) {}
    }

    for (const pattern of getUrlPatterns(provider)) {
      const tabs = await chrome.tabs.query({ url: pattern });
      if (tabs.length) return tabs[0].id;
    }

    return null;
  }

  async function openProvider(providerId) {
    const provider = get(providerId);

    for (const pattern of getUrlPatterns(provider)) {
      const tabs = await chrome.tabs.query({ url: pattern });
      if (tabs.length > 0) {
        await chrome.tabs.update(tabs[0].id, { active: true });
        await chrome.windows.update(tabs[0].windowId, { focused: true });
        return;
      }
    }

    await chrome.tabs.create({ url: provider.openUrl });
  }

  function initDefaults() {
    if (typeof GeminiProvider !== 'undefined') register(GeminiProvider);
    if (typeof ChatGPTProvider !== 'undefined') register(ChatGPTProvider);
  }

  initDefaults();

  return {
    register,
    get,
    list,
    listActive,
    getUrlPatterns,
    matchProviderForUrl,
    resolveTabId,
    openProvider,
  };
})();

if (typeof self !== 'undefined') {
  self.ProviderRegistry = ProviderRegistry;
}
