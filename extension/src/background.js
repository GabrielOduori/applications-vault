// Background script — proxies API calls from content scripts
// Content scripts on HTTPS pages can't fetch HTTP directly (mixed content).
// This background script has host permissions and can make the requests.

const API_BASE = 'http://127.0.0.1:8000/api/v1';

const browserAPI = (typeof browser !== 'undefined') ? browser : chrome;

// Security: keep the vault token in memory only to avoid persistent storage.
// Improvement: token is cleared when the background worker restarts.
let vaultToken = null;

browserAPI.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'setToken') {
    vaultToken = request.token || null;
    sendResponse({ ok: true });
    return true;
  }
  if (request.action === 'getToken') {
    sendResponse({ ok: true, token: vaultToken });
    return true;
  }
  if (request.action === 'clearToken') {
    vaultToken = null;
    sendResponse({ ok: true });
    return true;
  }
  if (request.action === 'apiRequest') {
    handleApiRequest(request)
      .then(result => {
        try { sendResponse(result); } catch (_) {}
      })
      .catch(err => {
        console.error('[ApplicationVault] fetch error:', err);
        try {
          sendResponse({ ok: false, status: 0, body: { detail: err.message } });
        } catch (_) {}
      });
    return true; // keep channel open for async response
  }
});

async function handleApiRequest({ method, path, token, body }) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  const effectiveToken = token || vaultToken;
  if (effectiveToken) headers['Authorization'] = `Bearer ${effectiveToken}`;

  const fetchOptions = { method: method || 'GET', headers };
  if (body) fetchOptions.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, fetchOptions);

  const responseBody = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body: responseBody };
}
