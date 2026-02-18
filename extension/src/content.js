// Content script - extracts job posting data from the current page
// Runs on every page, but only does work when the popup requests it

const API_BASE = 'http://127.0.0.1:8000/api/v1';
const browserAPI = (typeof browser !== 'undefined') ? browser : chrome;

// --- Message listener for popup ---
browserAPI.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'extractPage') {
    try {
      const data = extractPageData();
      sendResponse(data);
    } catch (e) {
      sendResponse({ url: window.location.href, pageTitle: document.title, textSnapshot: null, error: e.message });
    }
  }
  return true;
});

// --- Floating capture button ---

function isLikelyJobPage() {
  const url = window.location.href.toLowerCase();
  const title = document.title.toLowerCase();

  // Known job board and ATS domains
  const jobDomains = [
    'linkedin.com/jobs', 'indeed.com', 'greenhouse.io',
    'lever.co', 'workday.com', 'glassdoor.com',
    'ziprecruiter.com', 'monster.com', 'careers.',
    'jobs.', 'apply.', 'recruiting.', 'hire.',
    // ATS / HR platforms
    'corehr.com', 'icims.com', 'taleo.net', 'successfactors.com',
    'bamboohr.com', 'recruitee.com', 'smartrecruiters.com',
    'ashbyhq.com', 'rippling.com', 'pinpointhq.com',
    'jobvite.com', 'myworkdayjobs.com', 'ultipro.com',
  ];
  for (const domain of jobDomains) {
    if (url.includes(domain)) return true;
  }

  // URL path hints (including Oracle PLSQL HR portals)
  const pathHints = [
    '/jobs/', '/job/', '/careers/', '/vacancy/', '/position/', '/apply/', '/opening/',
    '/erecruit', '/recruit', '/vacancy', '/pls/coreportal', '/pls/hrportal',
    'view_erecruit', 'job_posting', 'jobposting',
  ];
  for (const hint of pathHints) {
    if (url.includes(hint)) return true;
  }

  // Title hints
  const titleHints = ['job', 'career', 'hiring', 'position', 'vacancy', 'apply', 'opening', 'role'];
  for (const hint of titleHints) {
    if (title.includes(hint)) return true;
  }

  // Page has job description elements
  const jobSelectors = [
    '[class*="job-description"]', '[class*="jobDescription"]',
    '[id*="job-description"]', '[id*="jobDescription"]',
  ];
  for (const sel of jobSelectors) {
    if (document.querySelector(sel)) return true;
  }

  return false;
}

function injectCaptureButton() {
  if (!isLikelyJobPage()) return;
  if (document.getElementById('av-capture-fab')) return;

  const fab = document.createElement('div');
  fab.id = 'av-capture-fab';
  fab.innerHTML = `
    <style>
      #av-capture-fab {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 2147483647;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      #av-capture-fab .av-fab-btn {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: #2563eb;
        color: white;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 14px rgba(37,99,235,0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        font-size: 24px;
        font-weight: bold;
      }
      #av-capture-fab .av-fab-btn:hover {
        background: #1d4ed8;
        transform: scale(1.08);
        box-shadow: 0 6px 20px rgba(37,99,235,0.5);
      }
      #av-capture-fab .av-fab-btn.av-capturing {
        background: #f59e0b;
        pointer-events: none;
      }
      #av-capture-fab .av-fab-btn.av-success {
        background: #10b981;
      }
      #av-capture-fab .av-fab-btn.av-error {
        background: #ef4444;
      }
      #av-capture-fab .av-tooltip {
        position: absolute;
        bottom: 64px;
        right: 0;
        background: #1f2937;
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 13px;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s;
      }
      #av-capture-fab:hover .av-tooltip {
        opacity: 1;
      }
      #av-capture-fab .av-panel {
        position: absolute;
        bottom: 68px;
        right: 0;
        width: 300px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        padding: 16px;
        display: none;
      }
      #av-capture-fab .av-panel.av-open {
        display: block;
      }
      #av-capture-fab .av-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }
      #av-capture-fab .av-panel h3 {
        margin: 0;
        font-size: 15px;
        color: #1f2937;
      }
      #av-capture-fab .av-close-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: #9ca3af;
        font-size: 18px;
        line-height: 1;
        padding: 2px 4px;
        border-radius: 4px;
      }
      #av-capture-fab .av-close-btn:hover {
        color: #374151;
        background: #f3f4f6;
      }
      #av-capture-fab .av-panel label {
        display: block;
        font-size: 12px;
        font-weight: 500;
        color: #374151;
        margin-bottom: 4px;
      }
      #av-capture-fab .av-panel input {
        width: 100%;
        padding: 8px 10px;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        font-size: 13px;
        margin-bottom: 10px;
        outline: none;
        box-sizing: border-box;
      }
      #av-capture-fab .av-panel input:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 2px rgba(37,99,235,0.1);
      }
      #av-capture-fab .av-panel .av-preview {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 10px;
        font-size: 12px;
        color: #6b7280;
        max-height: 60px;
        overflow: hidden;
      }
      #av-capture-fab .av-panel .av-btn-capture {
        width: 100%;
        padding: 10px;
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
      }
      #av-capture-fab .av-panel .av-btn-capture:hover {
        background: #1d4ed8;
      }
      #av-capture-fab .av-panel .av-btn-capture:disabled {
        background: #93c5fd;
        cursor: not-allowed;
      }
      #av-capture-fab .av-panel .av-msg {
        margin-top: 8px;
        padding: 8px;
        border-radius: 6px;
        font-size: 12px;
        display: none;
      }
      #av-capture-fab .av-panel .av-msg.av-msg-success {
        display: block;
        background: #ecfdf5;
        color: #065f46;
      }
      #av-capture-fab .av-panel .av-msg.av-msg-error {
        display: block;
        background: #fef2f2;
        color: #991b1b;
      }
    </style>
    <div class="av-tooltip">Capture to Application Vault</div>
    <div class="av-panel" id="av-panel">
      <div class="av-panel-header">
        <h3>Save to Vault</h3>
        <button class="av-close-btn" id="av-close-btn" title="Close">&#10005;</button>
      </div>
      <div class="av-preview" id="av-preview"></div>
      <label>Job Title</label>
      <input type="text" id="av-title" placeholder="e.g. Software Engineer">
      <label>Org / Company</label>
      <input type="text" id="av-org" placeholder="Organisation or company name">
      <label>Location</label>
      <input type="text" id="av-location" placeholder="e.g. London, UK or Remote">
      <label>Deadline <span style="color:#ef4444;font-weight:700;">*</span> <span id="av-deadline-hint" style="display:none;color:#059669;font-size:11px;font-weight:400;">(auto-detected)</span></label>
      <input type="date" id="av-deadline">
      <button class="av-btn-capture" id="av-btn-capture">Capture This Job</button>
      <div class="av-msg" id="av-msg"></div>
    </div>
    <button class="av-fab-btn" id="av-fab-btn" title="Capture to Application Vault">V</button>
  `;
  document.body.appendChild(fab);

  const fabBtn = document.getElementById('av-fab-btn');
  const panel = document.getElementById('av-panel');
  const closeBtn = document.getElementById('av-close-btn');
  const titleInput = document.getElementById('av-title');
  const orgInput = document.getElementById('av-org');
  const locationInput = document.getElementById('av-location');
  const deadlineInput = document.getElementById('av-deadline');
  const deadlineHint = document.getElementById('av-deadline-hint');
  const preview = document.getElementById('av-preview');
  const captureBtn = document.getElementById('av-btn-capture');
  const msg = document.getElementById('av-msg');

  function closePanel() {
    panel.classList.remove('av-open');
    fabBtn.classList.remove('av-success', 'av-error');
  }

  // Close button
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    closePanel();
  });

  // Toggle panel
  fabBtn.addEventListener('click', () => {
    const isOpen = panel.classList.toggle('av-open');
    if (isOpen) {
      const data = extractPageData();
      titleInput.value = data.pageTitle || '';
      preview.textContent = data.textSnapshot
        ? data.textSnapshot.substring(0, 120) + '...'
        : 'No text extracted from page';
      if (data.deadline) {
        const iso = toIsoDate(data.deadline);
        deadlineInput.value = iso || '';
        deadlineHint.style.display = iso ? 'inline' : 'none';
      } else {
        deadlineInput.value = '';
        deadlineHint.style.display = 'none';
      }
      locationInput.value = data.location || '';
      msg.className = 'av-msg';
      msg.style.display = 'none';
      captureBtn.disabled = false;
      captureBtn.textContent = 'Capture This Job';
    }
  });

  // Close panel when clicking outside
  document.addEventListener('click', (e) => {
    if (!fab.contains(e.target)) {
      closePanel();
    }
  });

  // Capture
  captureBtn.addEventListener('click', async () => {
    captureBtn.disabled = true;
    captureBtn.textContent = 'Capturing...';
    msg.className = 'av-msg';
    msg.style.display = 'none';

    try {
      // Get token
      // Security: fetch token from background memory only (no persistent storage).
      const tokenRes = await browserAPI.runtime.sendMessage({ action: 'getToken' });
      let token = tokenRes && tokenRes.token ? tokenRes.token : null;

      if (!token) {
        // Try to check if vault is unlocked but we don't have token
        msg.className = 'av-msg av-msg-error';
        msg.style.display = 'block';
        msg.textContent = 'Vault is locked. Click the extension icon in the toolbar to unlock first.';
        captureBtn.disabled = false;
        captureBtn.textContent = 'Capture This Job';
        return;
      }

      const deadline = deadlineInput.value.trim();
      if (!deadline) {
        msg.className = 'av-msg av-msg-error';
        msg.style.display = 'block';
        msg.textContent = 'Please enter a deadline date before capturing.';
        captureBtn.disabled = false;
        captureBtn.textContent = 'Capture This Job';
        return;
      }

      const pageData = extractPageData();
      const title = titleInput.value || pageData.pageTitle || 'Untitled';
      const org = orgInput.value || undefined;
      const location = locationInput.value.trim() || undefined;

      // Route through background script to avoid mixed-content block on HTTPS pages
      const res = await browserAPI.runtime.sendMessage({
        action: 'apiRequest',
        method: 'POST',
        path: '/captures/quick',
        token: token,
        body: {
          url: pageData.url,
          page_title: pageData.pageTitle,
          text_snapshot: pageData.textSnapshot,
          html_content: pageData.htmlContent,
          capture_method: pageData.captureMethod,
          title: title,
          organisation: org,
          location: location,
          deadline: deadline,
        },
      });

      if (res.status === 401) {
        await browserAPI.runtime.sendMessage({ action: 'clearToken' });
        msg.className = 'av-msg av-msg-error';
        msg.style.display = 'block';
        msg.textContent = 'Session expired. Click the extension icon to unlock the vault again.';
        captureBtn.disabled = false;
        captureBtn.textContent = 'Capture This Job';
        return;
      }
      if (res.status === 409) {
        msg.className = 'av-msg av-msg-error';
        msg.style.display = 'block';
        msg.textContent = res.body.detail || 'This job has already been captured.';
        captureBtn.disabled = false;
        captureBtn.textContent = 'Capture This Job';
        return;
      }
      if (!res.ok) {
        throw new Error(res.body.detail || `HTTP ${res.status}`);
      }

      const result = res.body;
      msg.className = 'av-msg av-msg-success';
      msg.style.display = 'block';
      msg.textContent = `Captured! "${result.job.title}" saved to vault.`;
      captureBtn.textContent = 'Captured!';
      fabBtn.classList.add('av-success');
    } catch (e) {
      msg.className = 'av-msg av-msg-error';
      msg.style.display = 'block';
      msg.textContent = `Error: ${e.message}`;
      captureBtn.disabled = false;
      captureBtn.textContent = 'Capture This Job';
      fabBtn.classList.add('av-error');
      setTimeout(() => fabBtn.classList.remove('av-error'), 2000);
    }
  });
}

// Inject after page loads
if (document.readyState === 'complete') {
  injectCaptureButton();
} else {
  window.addEventListener('load', injectCaptureButton);
}

// --- Helpers ---

function toIsoDate(raw) {
  if (!raw) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw.trim())) return raw.trim();
  const d = new Date(raw);
  if (!isNaN(d.getTime())) return d.toISOString().split('T')[0];
  return null;
}

// --- Page data extraction ---

// Parse schema.org/JobPosting JSON-LD — most reliable cross-site source
function extractJsonLd() {
  try {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of scripts) {
      try {
        const data = JSON.parse(script.textContent);
        const items = Array.isArray(data) ? data : [data];
        for (const item of items) {
          if (item['@type'] === 'JobPosting') return item;
          if (item['@graph']) {
            const job = item['@graph'].find(g => g['@type'] === 'JobPosting');
            if (job) return job;
          }
        }
      } catch (_) {}
    }
  } catch (_) {}
  return null;
}

function extractPageData() {
  const ld = extractJsonLd();
  const textSnapshot = extractJobText();

  let title = null;
  let organisation = null;
  let location = null;
  let deadline = null;

  // JSON-LD first (most reliable)
  if (ld) {
    try { title = ld.title || null; } catch (_) {}
    try {
      const org = ld.hiringOrganization;
      if (org) organisation = typeof org === 'string' ? org : (org.name || null);
    } catch (_) {}
    try {
      const loc = ld.jobLocation;
      if (loc) {
        const locs = Array.isArray(loc) ? loc : [loc];
        const parts = locs.map(l => {
          const a = l.address || l;
          const city = a.addressLocality || a.addressRegion || '';
          const country = a.addressCountry || '';
          return city ? (country ? `${city}, ${country}` : city) : country;
        }).filter(Boolean);
        if (parts.length) location = parts.join(' / ');
      }
    } catch (_) {}
    try {
      if (ld.validThrough) {
        const vt = new Date(ld.validThrough);
        if (!isNaN(vt.getTime())) {
          // Sites often set validThrough to midnight UTC of the day AFTER the deadline
          // e.g. deadline=Mar15 → validThrough="2026-03-16T00:00:00Z" → subtract one day
          if (vt.getUTCHours() === 0 && vt.getUTCMinutes() === 0) {
            vt.setUTCDate(vt.getUTCDate() - 1);
          }
          deadline = vt.toISOString().split('T')[0];
        } else {
          deadline = ld.validThrough.split('T')[0];
        }
      }
    } catch (_) {}
  }

  // DOM fallbacks
  if (!title) try { title = extractTitle(); } catch (_) {}
  if (!organisation) try { organisation = extractOrg(); } catch (_) {}
  if (!location) try { location = extractLocation(textSnapshot); } catch (_) {}
  if (!deadline) try { deadline = extractDeadline(textSnapshot); } catch (_) {}

  return {
    url: window.location.href,
    pageTitle: title || document.title,
    textSnapshot: textSnapshot,
    htmlContent: extractJobHtml(),
    captureMethod: detectCaptureMethod(),
    deadline,
    location,
    organisation,
  };
}

function extractTitle() {
  const hostname = window.location.hostname;
  // Site-specific
  if (hostname.includes('linkedin.com')) {
    const el = document.querySelector('.jobs-unified-top-card__job-title, .topcard__title, h1');
    if (el) return el.innerText.trim();
  }
  if (hostname.includes('indeed.com')) {
    const el = document.querySelector('[data-testid="jobsearch-JobInfoHeader-title"], h1');
    if (el) return el.innerText.trim();
  }
  // Generic h1 — most job pages put the role title in h1
  const h1 = document.querySelector('h1');
  if (h1) {
    const t = h1.innerText.trim();
    if (t && t.length > 2 && t.length < 200) return t;
  }
  // Page title with trailing noise stripped (e.g. "Engineer | Acme | LinkedIn")
  return document.title.replace(/\s*[|\-–—]\s*.+$/, '').trim() || document.title;
}

function extractOrg() {
  const hostname = window.location.hostname;
  if (hostname.includes('linkedin.com')) {
    const el = document.querySelector(
      '.jobs-unified-top-card__company-name, .topcard__org-name-link, [class*="company-name"]'
    );
    if (el) return el.innerText.trim();
  }
  if (hostname.includes('indeed.com')) {
    const el = document.querySelector(
      '[data-testid="inlineHeader-companyName"], [class*="company"], [class*="employer"]'
    );
    if (el) return el.innerText.trim();
  }
  // Generic — itemprop or class hints
  const selectors = [
    '[itemprop="hiringOrganization"]',
    '[class*="company-name"]',
    '[class*="employer-name"]',
    '[class*="organisation-name"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) {
      const t = el.innerText.trim();
      if (t && t.length < 100) return t;
    }
  }
  return null;
}

function extractLocation(text) {
  const hostname = window.location.hostname;

  if (hostname.includes('linkedin.com')) {
    const el = document.querySelector(
      '.jobs-unified-top-card__bullet, .jobs-unified-top-card__workplace-type, ' +
      '[class*="job-location"], .topcard__flavor--bullet'
    );
    if (el) return el.innerText.trim();
  }
  if (hostname.includes('indeed.com')) {
    const el = document.querySelector(
      '[data-testid="job-location"], [class*="location"], .icl-u-xs-mt--xs'
    );
    if (el) return el.innerText.trim();
  }

  const locationSelectors = [
    '[itemprop="jobLocation"]',
    '[itemprop="addressLocality"]',
    '[class*="location"]',
    '[id*="location"]',
    '[data-location]',
  ];
  for (const sel of locationSelectors) {
    try {
      const el = document.querySelector(sel);
      if (el) {
        const t = el.innerText.trim();
        if (t && t.length < 120) return t;
      }
    } catch (_) {}
  }

  if (!text) return null;
  const keywords = ['location:', 'location :', 'based in', 'office:', 'work location:'];
  for (const kw of keywords) {
    const idx = text.toLowerCase().indexOf(kw);
    if (idx !== -1) {
      const after = text.slice(idx + kw.length, idx + kw.length + 80).trim();
      const line = after.split('\n')[0].trim();
      if (line.length > 2 && line.length < 100) return line;
    }
  }
  return null;
}

function extractDeadline(text) {
  if (!text) return null;

  const monthPattern = '(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)';
  const dayPattern = '\\d{1,2}(?:st|nd|rd|th)?';
  const yearPattern = '\\d{4}';

  // Named month formats: "March 15, 2026", "15 March 2026", "Mar 15 2026"
  const namedDate = `(?:${dayPattern}\\s+${monthPattern}|${monthPattern}\\s+${dayPattern}),?\\s+${yearPattern}`;
  // ISO / numeric: "2026-03-15", "15/03/2026", "03/15/2026"
  const numericDate = `(?:${yearPattern}-\\d{2}-\\d{2}|\\d{1,2}/\\d{1,2}/${yearPattern})`;
  const anyDate = `(?:${namedDate}|${numericDate})`;

  const keywords = [
    'application deadline',
    'apply by',
    'applied by',
    'closing date',
    'applications close',
    'application close',
    'close date',
    'due date',
    'submission deadline',
    'submit by',
    'last date',
    'deadline',
  ];

  for (const kw of keywords) {
    const pattern = new RegExp(
      kw + '[:\\s]+(' + anyDate + ')',
      'i'
    );
    const match = text.match(pattern);
    if (match) return match[1].trim();
  }

  return null;
}

function detectCaptureMethod() {
  const hostname = window.location.hostname;
  if (hostname.includes('linkedin.com')) return 'structured';
  if (hostname.includes('indeed.com')) return 'structured';
  if (hostname.includes('greenhouse.io')) return 'structured';
  if (hostname.includes('lever.co')) return 'structured';
  if (hostname.includes('workday.com')) return 'structured';
  return 'generic_html';
}

function extractJobText() {
  const selection = window.getSelection().toString().trim();
  if (selection.length > 50) {
    return selection;
  }

  const hostname = window.location.hostname;

  if (hostname.includes('linkedin.com')) return extractLinkedIn();
  if (hostname.includes('indeed.com')) return extractIndeed();
  if (hostname.includes('greenhouse.io')) return extractGreenhouse();

  return extractGeneric();
}

function extractLinkedIn() {
  const selectors = [
    '.jobs-description__content',
    '.jobs-box__html-content',
    '.description__text',
    '[class*="job-details"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el.innerText.trim();
  }
  return extractGeneric();
}

function extractIndeed() {
  const selectors = [
    '#jobDescriptionText',
    '.jobsearch-jobDescriptionText',
    '[id*="jobDescription"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el.innerText.trim();
  }
  return extractGeneric();
}

function extractGreenhouse() {
  const selectors = [
    '#content',
    '.job__description',
    '[class*="job-description"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el.innerText.trim();
  }
  return extractGeneric();
}

function extractGeneric() {
  const selectors = [
    '[class*="job-description"]',
    '[class*="jobDescription"]',
    '[class*="job_description"]',
    '[id*="job-description"]',
    '[id*="jobDescription"]',
    '[class*="vacancy"]',
    '[id*="vacancy"]',
    '[class*="posting"]',
    'article',
    'main',
    '[role="main"]',
  ];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 100) {
      return el.innerText.trim();
    }
  }

  // Try same-origin iframes (e.g. Oracle PLSQL portals often embed content in frames)
  try {
    for (const frame of document.querySelectorAll('iframe, frame')) {
      try {
        const doc = frame.contentDocument;
        if (doc && doc.body) {
          const text = doc.body.innerText.trim();
          if (text.length > 100) return text.substring(0, 10000);
        }
      } catch (_) { /* cross-origin — skip */ }
    }
  } catch (_) {}

  const body = document.body.innerText.trim();
  return body.substring(0, 10000);
}

function extractJobHtml() {
  const selectors = [
    '[class*="job-description"]',
    '[class*="jobDescription"]',
    'article',
    'main',
    '[role="main"]',
  ];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerHTML.trim().length > 100) {
      return el.innerHTML;
    }
  }

  return null;
}
