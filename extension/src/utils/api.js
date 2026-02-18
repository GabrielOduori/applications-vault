const API_BASE = 'http://127.0.0.1:8000/api/v1';

export async function getVaultStatus() {
  const res = await fetch(`${API_BASE}/vault/status`);
  if (!res.ok) throw new Error('Cannot connect to vault');
  return res.json();
}

export async function quickCapture(token, data) {
  const res = await fetch(`${API_BASE}/captures/quick`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getToken() {
  // Security: read token from background memory, not persistent storage.
  const res = await chrome.runtime.sendMessage({ action: 'getToken' });
  return res && res.token ? res.token : null;
}

export async function setToken(token) {
  // Security: write token to background memory only.
  await chrome.runtime.sendMessage({ action: 'setToken', token });
}

export async function clearToken() {
  // Security: clear token from background memory.
  await chrome.runtime.sendMessage({ action: 'clearToken' });
}
