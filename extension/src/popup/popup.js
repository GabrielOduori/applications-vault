// Use browser API (Firefox) with chrome fallback
const browserAPI = (typeof browser !== 'undefined') ? browser : chrome;

function toIsoDate(raw) {
  if (!raw) return null;
  // Already ISO
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw.trim())) return raw.trim();
  // Try native Date parsing (handles "March 15, 2026", "15 March 2026", etc.)
  const d = new Date(raw);
  if (!isNaN(d.getTime())) {
    return d.toISOString().split('T')[0];
  }
  return null;
}

let pageData = null;

// --- API via background script (avoids mixed-content / CORS issues) ---

async function api(method, path, token, body) {
  const res = await browserAPI.runtime.sendMessage({
    action: 'apiRequest', method, path, token, body,
  });
  if (!res) throw new Error('Cannot connect to vault service. Is it running?');
  return res;
}

// --- UI helpers ---

function showStatus(type, text) {
  const el = document.getElementById('status');
  el.className = 'status ' + type;
  document.getElementById('status-text').textContent = text;
}

function showResult(type, text) {
  const el = document.getElementById('result');
  el.style.display = 'block';
  el.className = 'result ' + type;
  el.textContent = text;
}

// --- Init ---

async function init() {
  try {
    const statusRes = await api('GET', '/vault/status');
    if (!statusRes.ok) {
      const detail = statusRes.body && statusRes.body.detail
        ? statusRes.body.detail
        : `HTTP ${statusRes.status}`;
      throw new Error(`Cannot connect to vault service: ${detail}`);
    }
    const status = statusRes.body;

    if (!status.initialized) {
      showStatus('disconnected', 'Vault not set up. Open the dashboard first.');
      return;
    }

    if (status.locked) {
      // Server is locked — all tokens are invalid, clear ours
      // Security: clear token from background memory on lock.
      await browserAPI.runtime.sendMessage({ action: 'clearToken' });
      showStatus('locked', 'Vault is locked');
      document.getElementById('unlock-section').style.display = 'block';
      return;
    }

    // Vault is unlocked — check if our stored token is still valid
    const tokenRes = await browserAPI.runtime.sendMessage({ action: 'getToken' });
    if (tokenRes && tokenRes.token) {
      const checkRes = await api('GET', '/jobs?page=1', tokenRes.token);
      if (checkRes.ok) {
        showUnlocked();
        return;
      }
      // Token was rejected
      await browserAPI.runtime.sendMessage({ action: 'clearToken' });
    }

    showStatus('locked', 'Please unlock the vault.');
    document.getElementById('unlock-section').style.display = 'block';
  } catch (e) {
    showStatus('disconnected', e.message || 'Cannot connect to vault service. Is it running?');
  }
}

async function showUnlocked() {
  showStatus('connected', 'Vault unlocked');
  document.getElementById('unlock-section').style.display = 'none';
  document.getElementById('capture-section').style.display = 'block';

  // Extract page data from active tab
  try {
    const tabs = await browserAPI.tabs.query({ active: true, currentWindow: true });
    const tab = tabs[0];
    if (tab && tab.id) {
      // Try to message the content script; inject it first if not running
      try {
        pageData = await browserAPI.tabs.sendMessage(tab.id, { action: 'extractPage' });
      } catch (_) {
        // Content script not loaded yet — inject programmatically then retry
        try {
          // Chrome MV3 uses chrome.scripting; Firefox MV2 uses tabs.executeScript
          if (typeof chrome !== 'undefined' && chrome.scripting) {
            await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              files: ['src/content.js'],
            });
          } else {
            await browserAPI.tabs.executeScript(tab.id, { file: 'src/content.js' });
          }
          pageData = await browserAPI.tabs.sendMessage(tab.id, { action: 'extractPage' });
        } catch (injectErr) {
          throw injectErr;
        }
      }

      document.getElementById('preview-title').textContent = pageData.pageTitle || 'Untitled';
      document.getElementById('preview-url').textContent = pageData.url || '';
      document.getElementById('preview-snippet').textContent =
        pageData.textSnapshot ? pageData.textSnapshot.substring(0, 150) + '...' : 'No text extracted';
      document.getElementById('job-title').value = pageData.pageTitle || '';

      if (pageData.organisation) {
        document.getElementById('job-org').value = pageData.organisation;
      }
      if (pageData.location) {
        document.getElementById('job-location').value = pageData.location;
      }

      if (pageData.deadline) {
        const iso = toIsoDate(pageData.deadline);
        document.getElementById('job-deadline').value = iso || '';
        const hint = document.getElementById('deadline-hint');
        if (hint) {
          hint.textContent = iso ? 'Auto-detected from page' : 'Could not parse date — enter manually';
          hint.style.color = iso ? '#059669' : '#b45309';
          hint.style.display = 'block';
        }
      }
    }
  } catch (e) {
    document.getElementById('preview-title').textContent = 'Could not extract page data';
    document.getElementById('preview-snippet').textContent = 'Make sure you are on a job posting page and refresh it.';
  }
}

// --- Event handlers ---

document.getElementById('unlock-btn').addEventListener('click', async () => {
  const passphrase = document.getElementById('passphrase').value;
  if (!passphrase) return;

  const btn = document.getElementById('unlock-btn');
  btn.disabled = true;
  btn.textContent = 'Unlocking...';

  try {
    const res = await api('POST', '/vault/unlock', null, { passphrase });
    if (!res.ok) throw new Error('Invalid passphrase');
    // Security: store token in background memory only.
    await browserAPI.runtime.sendMessage({ action: 'setToken', token: res.body.token });
    showUnlocked();
  } catch (e) {
    showStatus('locked', e.message);
    btn.disabled = false;
    btn.textContent = 'Unlock Vault';
  }
});

document.getElementById('capture-btn').addEventListener('click', async () => {
  const btn = document.getElementById('capture-btn');
  btn.disabled = true;
  btn.textContent = 'Capturing...';

  const tokenRes = await browserAPI.runtime.sendMessage({ action: 'getToken' });
  const token = tokenRes && tokenRes.token ? tokenRes.token : null;

  if (!token) {
    showResult('error', 'No token. Please unlock the vault.');
    btn.disabled = false;
    btn.textContent = 'Capture This Job';
    return;
  }

  const title = document.getElementById('job-title').value || (pageData && pageData.pageTitle) || 'Untitled';
  const org = document.getElementById('job-org').value || undefined;
  const location = document.getElementById('job-location').value || undefined;
  const deadline = document.getElementById('job-deadline').value || undefined;

  if (!deadline) {
    showResult('error', 'Please enter a deadline date before capturing.');
    btn.disabled = false;
    btn.textContent = 'Capture This Job';
    return;
  }

  try {
    const res = await api('POST', '/captures/quick', token, {
      url: pageData ? pageData.url : undefined,
      page_title: pageData ? pageData.pageTitle : undefined,
      text_snapshot: pageData ? pageData.textSnapshot : undefined,
      html_content: pageData ? pageData.htmlContent : undefined,
      capture_method: (pageData && pageData.captureMethod) || 'generic_html',
      title: title,
      organisation: org,
      location: location,
      deadline: deadline,
    });

    if (res.status === 401) {
      await browserAPI.runtime.sendMessage({ action: 'clearToken' });
      showResult('error', 'Session expired. Please unlock the vault again.');
      btn.disabled = false;
      btn.textContent = 'Capture This Job';
      return;
    }
    if (res.status === 409) {
      showResult('error', res.body.detail || 'This job has already been captured.');
      btn.disabled = false;
      btn.textContent = 'Capture This Job';
      return;
    }
    if (!res.ok) {
      throw new Error(res.body.detail || 'HTTP ' + res.status);
    }

    showResult('success', 'Captured! "' + res.body.job.title + '" saved to vault.');
    btn.textContent = 'Captured!';
  } catch (e) {
    showResult('error', 'Error: ' + e.message);
    btn.disabled = false;
    btn.textContent = 'Capture This Job';
  }
});

// Allow Enter key in passphrase field
document.getElementById('passphrase').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('unlock-btn').click();
});

// Start
init();
