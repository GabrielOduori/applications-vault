const BASE_URL = '/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    // Security: avoid persisting tokens in browser storage to reduce XSS theft.
    // Improvement: token lives in memory only and is cleared on refresh.
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

    if (res.status === 401) {
      this.setToken(null);
      window.dispatchEvent(new CustomEvent('vault:locked'));
      throw new Error('Vault locked');
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }

    if (res.headers.get('content-type')?.includes('application/json')) {
      return res.json();
    }
    return res as unknown as T;
  }

  // Vault
  async vaultStatus() {
    return this.request<{ initialized: boolean; locked: boolean }>('/vault/status');
  }

  async vaultSetup(passphrase: string, vaultPath?: string) {
    return this.request<{ vault_path: string; recovery_key: string; message: string }>(
      '/vault/setup',
      { method: 'POST', body: JSON.stringify({ passphrase, vault_path: vaultPath }) }
    );
  }

  async vaultUnlock(passphrase: string) {
    return this.request<{ token: string; expires_in_seconds: number }>(
      '/vault/unlock',
      { method: 'POST', body: JSON.stringify({ passphrase }) }
    );
  }

  async vaultLock() {
    await this.request('/vault/lock', { method: 'POST' });
    this.setToken(null);
  }

  async updateVaultSettings(autoLockSeconds: number) {
    return this.request('/vault/settings', {
      method: 'PUT',
      body: JSON.stringify({ auto_lock_seconds: autoLockSeconds }),
    });
  }

  // Jobs
  async getJobs(params?: { status?: string; tag?: string; q?: string; page?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.tag) searchParams.set('tag', params.tag);
    if (params?.q) searchParams.set('q', params.q);
    if (params?.page) searchParams.set('page', String(params.page));
    const qs = searchParams.toString();
    return this.request<import('../types').JobListResponse>(`/jobs${qs ? `?${qs}` : ''}`);
  }

  async getJob(id: string) {
    return this.request<import('../types').Job>(`/jobs/${id}`);
  }

  async createJob(data: { title: string; organisation?: string; url?: string; location?: string; deadline_type?: string; deadline_date?: string; notes?: string }) {
    return this.request<import('../types').Job>('/jobs', { method: 'POST', body: JSON.stringify(data) });
  }

  async updateJob(id: string, data: Record<string, unknown>) {
    return this.request<import('../types').Job>(`/jobs/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  }

  async deleteJob(id: string) {
    return this.request(`/jobs/${id}`, { method: 'DELETE' });
  }

  // Captures
  async getCaptures(jobId: string) {
    return this.request<import('../types').Capture[]>(`/jobs/${jobId}/captures`);
  }

  async createCapture(jobId: string, data: { url?: string; page_title?: string; text_snapshot?: string; capture_method?: string }) {
    return this.request<import('../types').Capture>(`/jobs/${jobId}/captures`, { method: 'POST', body: JSON.stringify(data) });
  }

  // Events
  async getEvents(jobId: string) {
    return this.request<import('../types').AppEvent[]>(`/jobs/${jobId}/events`);
  }

  async addEvent(jobId: string, data: { event_type: string; notes?: string; next_action_date?: string }) {
    return this.request<import('../types').AppEvent>(`/jobs/${jobId}/events`, { method: 'POST', body: JSON.stringify(data) });
  }

  async getUpcomingEvents() {
    return this.request<import('../types').AppEvent[]>('/events/upcoming');
  }

  // Documents
  async getDocuments(jobId: string) {
    return this.request<import('../types').Document[]>(`/jobs/${jobId}/documents`);
  }

  async uploadDocument(jobId: string, file: File, docType: string, versionLabel?: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);
    if (versionLabel) formData.append('version_label', versionLabel);
    return this.request<import('../types').Document>(`/jobs/${jobId}/documents`, { method: 'POST', body: formData });
  }

  async verifyDocument(jobId: string, docId: string) {
    return this.request<{ verified: boolean; filename: string; stored_hash: string; actual_hash: string }>(
      `/jobs/${jobId}/documents/${docId}/verify`
    );
  }

  async submitDocument(jobId: string, docId: string) {
    return this.request<import('../types').Document>(`/jobs/${jobId}/documents/${docId}/submit`, { method: 'PUT' });
  }

  async unsubmitDocument(jobId: string, docId: string) {
    return this.request<import('../types').Document>(`/jobs/${jobId}/documents/${docId}/submit`, { method: 'DELETE' });
  }

  async matchDocument(jobId: string, docId: string) {
    return this.request<import('../types').MatchResult>(`/jobs/${jobId}/documents/${docId}/match`);
  }

  async downloadDocument(jobId: string, docId: string): Promise<Response> {
    const token = this.getToken();
    const res = await fetch(`${BASE_URL}/jobs/${jobId}/documents/${docId}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('Download failed');
    return res;
  }

  // Tags
  async getTags() {
    return this.request<import('../types').Tag[]>('/tags');
  }

  async createTag(name: string, color?: string) {
    return this.request<import('../types').Tag>('/tags', { method: 'POST', body: JSON.stringify({ name, color }) });
  }

  async addTagToJob(jobId: string, tagName: string) {
    return this.request(`/jobs/${jobId}/tags`, { method: 'POST', body: JSON.stringify({ name: tagName }) });
  }

  async removeTagFromJob(jobId: string, tagId: string) {
    return this.request(`/jobs/${jobId}/tags/${tagId}`, { method: 'DELETE' });
  }

  // Search
  async search(q: string, scope: string = 'all') {
    return this.request<import('../types').SearchResponse>(`/search?q=${encodeURIComponent(q)}&scope=${scope}`);
  }

  // Calendar
  getCalendarUrl(jobId: string): string {
    return `${BASE_URL}/jobs/${jobId}/calendar`;
  }

  // Analytics
  async getAnalytics() {
    return this.request<import('../types').Analytics>('/analytics');
  }
}

export const api = new ApiClient();
