const API_BASE = '/api';

export function getAuthHeaders(hasBody = true) {
  const token = localStorage.getItem('esp_auth_token');
  const headers: Record<string, string> = {};
  if (hasBody) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginAdmin(username: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  if (data.access_token) {
    localStorage.setItem('esp_auth_token', data.access_token);
  }
  return data;
}

export async function verifyAuth() {
  const token = localStorage.getItem('esp_auth_token');
  if (!token) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/verify`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function logoutAdmin() {
  localStorage.removeItem('esp_auth_token');
  window.location.reload();
}

export async function fetchAccounts() {
  const res = await fetch(`${API_BASE}/accounts`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch accounts');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data.map((a: any) => ({
    id: a.id,
    provider: a.provider || 'smtp',
    providerType: a.provider_type || a.providerType || a.provider || 'smtp',
    name: a.name || '',
    email: a.email || '',
    fromName: a.from_name || a.fromName || '',
    fromEmail: a.email || '',
    smtpHost: a.smtp_host || a.smtpHost || '',
    smtpPort: a.smtp_port || a.smtpPort || 587,
    smtpSecurity: a.smtp_security || a.smtpSecurity || 'starttls',
    smtpUsername: a.smtp_username || a.smtpUsername || '',
    enabled: a.enabled ?? true,
    dailyLimit: a.daily_limit || a.dailyLimit || 500,
    sentToday: a.sent_today || a.sentToday || 0,
    status: a.status || 'idle',
    createdAt: a.created_at || a.createdAt || new Date().toISOString()
  }));
}

export async function createAccount(data: any) {
  const res = await fetch(`${API_BASE}/accounts`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create account');
  }
  return res.json();
}

export async function updateAccount(id: number, data: any) {
  const res = await fetch(`${API_BASE}/accounts/${id}`, {
    method: 'PUT',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update account');
  }
  return res.json();
}

export async function oauthConnectAccount(data: { provider: string; name: string; email: string; from_name?: string; access_token: string; refresh_token?: string }) {
  const res = await fetch(`${API_BASE}/accounts/oauth`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to connect OAuth account');
  }
  return res.json();
}

export async function testAccountConnection(id: number) {
  const res = await fetch(`${API_BASE}/accounts/${id}/test`, {
    method: 'POST',
    headers: getAuthHeaders(false),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to test account connection');
  }
  return res.json();
}

export async function testSmtpCredentials(data: { host: string; port: number; security: string; username: string; password: string }) {
  const res = await fetch(`${API_BASE}/accounts/test-smtp`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'SMTP authentication failed');
  }
  return res.json();
}

export async function deleteAccount(id: number) {
  const res = await fetch(`${API_BASE}/accounts/${id}`, { method: 'DELETE', headers: getAuthHeaders(false) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete account');
  }
}

export async function fetchLeads() {
  const res = await fetch(`${API_BASE}/leads`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch leads');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data.map((l: any) => ({
    id: String(l.id),
    firstName: l.first_name || '',
    lastName: l.last_name || '',
    email: l.email || '',
    company: l.company || '',
    position: l.position || '',
    senderName: l.sender_name || '',
    senderFullName: l.sender_full_name || l.sender_name || '',
    status: l.status || 'new',
    tags: l.tags || [],
    createdAt: l.created_at || new Date().toISOString()
  }));
}

export async function createLead(data: any) {
  const payload = {
    first_name: data.firstName || data.first_name,
    last_name: data.lastName || data.last_name,
    email: data.email,
    company: data.company,
    position: data.position,
    sender_name: data.senderName || data.sender_name,
    sender_full_name: data.senderFullName || data.senderName || data.sender_full_name
  };
  const res = await fetch(`${API_BASE}/leads`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create lead');
  }
  return res.json();
}

export async function updateLead(id: number | string, data: any) {
  const payload = {
    first_name: data.firstName || data.first_name,
    last_name: data.lastName || data.last_name,
    email: data.email,
    company: data.company,
    position: data.position,
    sender_name: data.senderName || data.sender_name,
    sender_full_name: data.senderFullName || data.senderName || data.sender_full_name
  };
  const res = await fetch(`${API_BASE}/leads/${id}`, {
    method: 'PATCH',
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update lead');
  }
  return res.json();
}

export async function bulkCreateLeads(leads: any[]) {
  const payloadLeads = leads.map(l => ({
    first_name: l.first_name || l.firstName || 'Valued',
    last_name: l.last_name || l.lastName || 'Lead',
    email: l.email,
    company: l.company || '',
    position: l.position || '',
    sender_name: l.sender_name || l.senderName || '',
    sender_full_name: l.sender_full_name || l.senderFullName || l.sender_name || ''
  }));
  const res = await fetch(`${API_BASE}/leads/bulk`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify({ leads: payloadLeads }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to bulk import leads');
  }
  return res.json();
}

export async function importLeadsFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const token = localStorage.getItem('esp_auth_token');
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/leads/import-file`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to import leads file');
  }
  return res.json();
}

export async function deleteLead(id: number | string) {
  const res = await fetch(`${API_BASE}/leads/${id}`, { method: 'DELETE', headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to delete lead');
}

export async function duplicateLead(id: number | string) {
  const res = await fetch(`${API_BASE}/leads/${id}/duplicate`, { method: 'POST', headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to duplicate lead');
  return res.json();
}

export async function deduplicateLeads() {
  const res = await fetch(`${API_BASE}/leads/deduplicate`, { method: 'POST', headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to deduplicate leads');
  return res.json();
}

export async function clearLeads() {
  const res = await fetch(`${API_BASE}/leads/clear`, { method: 'DELETE', headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to clear leads');
  return res.json();
}

export async function fetchTemplates() {
  const res = await fetch(`${API_BASE}/templates`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch templates');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data.map((t: any) => ({
    id: t.id,
    name: t.name || '',
    subject: t.subject || '',
    bodyHtml: t.body_html || t.bodyHtml || '',
    updatedAt: t.updated_at || t.updatedAt || new Date().toISOString()
  }));
}

export async function createTemplate(data: any) {
  const payload = {
    name: data.name,
    subject: data.subject,
    body_html: data.bodyHtml || data.body_html
  };
  const res = await fetch(`${API_BASE}/templates`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create template');
  }
  return res.json();
}

export async function deleteTemplate(id: number | string) {
  const res = await fetch(`${API_BASE}/templates/${id}`, { method: 'DELETE', headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to delete template');
}

export async function fetchCampaigns() {
  const res = await fetch(`${API_BASE}/campaigns`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch campaigns');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data.map((c: any) => ({
    id: c.id,
    name: c.name || '',
    status: c.status || 'draft',
    tag: c.tag || 'Marketing',
    templateId: c.template_id || c.templateId || 0,
    templateIds: c.template_ids || c.templateIds || (c.template_id ? [c.template_id] : []),
    accountId: c.account_id || c.accountId || null,
    totalLeads: c.total_recipients || c.totalLeads || 0,
    sentCount: c.sent_count || c.sentCount || 0,
    failedCount: c.failed_count || c.failedCount || 0,
    delaySeconds: c.delay_seconds || c.delaySeconds || 30,
    startedAt: c.started_at || c.startedAt || null,
    completedAt: c.completed_at || c.completedAt || null,
    createdAt: c.created_at || c.createdAt || new Date().toISOString()
  }));
}

export async function createCampaign(data: any) {
  const payload = {
    name: data.name,
    tag: data.tag || 'Marketing',
    template_id: data.templateId || data.template_id,
    template_ids: data.templateIds || data.template_ids || [],
    account_id: data.accountId || data.account_id,
    lead_ids: data.leadIds || data.lead_ids || []
  };
  const res = await fetch(`${API_BASE}/campaigns`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create campaign');
  }
  return res.json();
}

export async function updateCampaignStatus(id: number | string, status: string) {
  const res = await fetch(`${API_BASE}/campaigns/${id}/status`, {
    method: 'PATCH',
    headers: getAuthHeaders(true),
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update campaign status');
  }
  return res.json();
}

export async function deleteCampaign(id: number | string) {
  const res = await fetch(`${API_BASE}/campaigns/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders(false),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete campaign');
  }
  return res.json().catch(() => ({ status: 'success' }));
}

export async function fetchActivityLogs() {
  const res = await fetch(`${API_BASE}/logs`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch activity logs');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data.map((l: any) => ({
    id: l.id,
    eventType: l.event_type || l.eventType || '',
    severity: l.severity || 'info',
    message: l.message || '',
    entityId: l.entity_id || l.entityId || null,
    leadEmail: l.lead_email || l.leadEmail || '',
    accountName: l.account_name || l.accountName || '',
    status: l.status || 'SENT',
    providerType: l.provider_type || l.providerType || 'SMTP',
    providerMessageId: l.provider_message_id || l.providerMessageId || '',
    errorCode: l.error_code || l.errorCode || '',
    timestamp: l.created_at || l.timestamp || new Date().toISOString()
  }));
}

export async function fetchDrafts() {
  const res = await fetch(`${API_BASE}/drafts`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch drafts');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data;
}

export async function createDraft(data: any) {
  const res = await fetch(`${API_BASE}/drafts`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create draft');
  }
  return res.json();
}

export async function updateDraft(id: number | string, data: any) {
  const res = await fetch(`${API_BASE}/drafts/${id}`, {
    method: 'PUT',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update draft');
  }
  return res.json();
}

export async function deleteDraft(id: number | string) {
  const res = await fetch(`${API_BASE}/drafts/${id}`, { method: 'DELETE', headers: getAuthHeaders(false) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete draft');
  }
  return true;
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/settings`, { headers: getAuthHeaders(false) });
  if (!res.ok) throw new Error('Failed to fetch settings');
  const ct = res.headers.get("content-type");
  let data = [];
  if (ct && ct.includes("application/json")) {
    data = await res.json();
  }
  if (!Array.isArray(data)) data = [];
  return data;
}

export async function upsertSetting(key: string, value: string) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify({ key, value }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to save setting');
  }
  return res.json();
}

export async function sendEmailMessage(data: { sender_account_id: number | string; recipient: string; subject: string; body: string; from_name?: string; high_priority?: boolean }) {
  const res = await fetch(`${API_BASE}/send`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to send email');
  }
  return res.json();
}
