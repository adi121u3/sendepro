export type TabType = 'dashboard' | 'campaigns' | 'accounts' | 'leads' | 'templates' | 'Email Composer' | 'drafts' | 'activity' | 'settings';

export interface Draft {
  id: string | number;
  from_name?: string;
  subject: string;
  recipient: string;
  body: string;
  attachments?: string;
  senderAccountId?: string | number;
  created_at?: string;
  updated_at?: string;
}

export interface Account {
  id: string;
  name: string;
  providerType: 'smtp' | 'gmail' | 'outlook' | 'zeptomail';
  host: string;
  port: number;
  security: 'starttls' | 'ssl' | 'none' | 'oauth2';
  username: string;
  fromEmail: string;
  fromName: string;
  dailyLimit: number;
  sentToday: number;
  status: 'active' | 'warning' | 'error' | 'disconnected';
  lastTested?: string;
}

export interface Lead {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  company: string;
  position: string;
  senderName?: string;
  senderFullName?: string;
  status: 'new' | 'contacted' | 'replied' | 'unsubscribed' | 'bounced';
  tags: string[];
  createdAt: string;
}

export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  bodyHtml: string;
  category: string;
  updatedAt: string;
}

export interface Campaign {
  id: string;
  name: string;
  templateId: string;
  templateIds?: string[];
  accountId: string;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'stopped';
  totalLeads: number;
  sentCount: number;
  failedCount: number;
  delaySeconds: number;
  tag?: string;
  createdAt: string;
}

export interface ActivityLog {
  id: string;
  campaignId: string;
  campaignName: string;
  leadEmail: string;
  accountName: string;
  status: 'sent' | 'failed' | 'skipped';
  errorMessage?: string;
  timestamp: string;
}
