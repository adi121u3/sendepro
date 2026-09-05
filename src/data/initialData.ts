import { Account, Lead, EmailTemplate, Campaign, ActivityLog } from '../types';

export const initialAccounts: Account[] = [
  {
    id: 'acc-1',
    name: 'Primary Outbound (SMTP)',
    providerType: 'smtp',
    host: 'smtp.mailgun.org',
    port: 587,
    security: 'starttls',
    username: 'postmaster@mg.example.com',
    fromEmail: 'alex@example.com',
    fromName: 'Alex Rivers',
    dailyLimit: 500,
    sentToday: 142,
    status: 'active',
    lastTested: '2026-09-02 10:30 AM'
  },
  {
    id: 'acc-2',
    name: 'Microsoft 365 Executive',
    providerType: 'outlook',
    host: 'smtp.office365.com',
    port: 587,
    security: 'oauth2',
    username: 'alex.rivers@company.onmicrosoft.com',
    fromEmail: 'alex.rivers@company.onmicrosoft.com',
    fromName: 'Alex Rivers (Exec)',
    dailyLimit: 300,
    sentToday: 88,
    status: 'active',
    lastTested: '2026-09-02 09:15 AM'
  },
  {
    id: 'acc-3',
    name: 'ZeptoMail Transactional',
    providerType: 'zeptomail',
    host: 'api.zeptomail.com',
    port: 443,
    security: 'ssl',
    username: 'emailapikey zoho-token...',
    fromEmail: 'no-reply@updates.example.com',
    fromName: 'Example Updates',
    dailyLimit: 2000,
    sentToday: 620,
    status: 'active',
    lastTested: '2026-09-01 04:20 PM'
  }
];

export const initialLeads: Lead[] = [
  {
    id: 'lead-1',
    firstName: 'Sarah',
    lastName: 'Jenkins',
    email: 'sarah.j@acmeproducts.io',
    company: 'Acme Products',
    position: 'VP of Engineering',
    status: 'new',
    tags: ['SaaS', 'Series B'],
    createdAt: '2026-08-28'
  },
  {
    id: 'lead-2',
    firstName: 'Marcus',
    lastName: 'Vance',
    email: 'marcus@nexustech.co',
    company: 'Nexus Tech',
    position: 'Head of Growth',
    status: 'contacted',
    tags: ['Enterprise', 'Fintech'],
    createdAt: '2026-08-29'
  },
  {
    id: 'lead-3',
    firstName: 'Elena',
    lastName: 'Rostova',
    email: 'elena@stellarsoftware.com',
    company: 'Stellar Software',
    position: 'Chief Technology Officer',
    status: 'replied',
    tags: ['SaaS', 'Enterprise'],
    createdAt: '2026-08-30'
  },
  {
    id: 'lead-4',
    firstName: 'David',
    lastName: 'Kim',
    email: 'dkim@cloudscale.net',
    company: 'CloudScale',
    position: 'DevOps Lead',
    status: 'new',
    tags: ['Infrastructure'],
    createdAt: '2026-08-31'
  },
  {
    id: 'lead-5',
    firstName: 'Rachel',
    lastName: 'Greenwood',
    email: 'rachel@greenwoodventures.com',
    company: 'Greenwood Ventures',
    position: 'Managing Partner',
    status: 'new',
    tags: ['Investor', 'Seed'],
    createdAt: '2026-09-01'
  }
];

export const initialTemplates: EmailTemplate[] = [
  {
    id: 'tpl-1',
    name: 'Cold Outbound - SaaS Engineering',
    subject: 'Scaling infrastructure at {{Company}} / Quick Question',
    bodyHtml: `<p>Hi {{FirstName}},</p>
<p>I noticed your team at {{Company}} is scaling up engineering velocity. As {{Position}}, you're probably managing complex deployment pipelines.</p>
<p>We built a streamlined automated delivery engine that cuts SMTP overhead by 40%. Would you be open to a quick 5-minute walkthrough this week?</p>
<p>Best regards,<br>Alex Rivers</p>`,
    category: 'Outbound',
    updatedAt: '2026-08-25'
  },
  {
    id: 'tpl-2',
    name: 'Follow-up Sequence #1',
    subject: 'Following up regarding {{Company}} infrastructure',
    bodyHtml: `<p>Hi {{FirstName}},</p>
<p>Just floating this to the top of your inbox. Did you have any thoughts on optimizing outbound throughput for {{Company}}?</p>
<p>Let me know if next Tuesday works for a brief demo.</p>
<p>Best,<br>Alex</p>`,
    category: 'Follow-up',
    updatedAt: '2026-08-28'
  },
  {
    id: 'tpl-3',
    name: 'Investor Update Q3',
    subject: '{{Company}} & Q3 Growth Metrics',
    bodyHtml: `<p>Dear {{FirstName}},</p>
<p>We are thrilled to share our Q3 metrics with our partners at {{Company}}. Our recurring revenue grew 140% YoY with enterprise retention at 98%.</p>
<p>Attached is the full deck. Let's schedule our quarterly sync soon.</p>
<p>Warm regards,<br>Alex Rivers</p>`,
    category: 'Investor',
    updatedAt: '2026-09-01'
  }
];

export const initialCampaigns: Campaign[] = [
  {
    id: 'cmp-1',
    name: 'Q3 SaaS Outreach Batch 1',
    templateId: 'tpl-1',
    accountId: 'acc-1',
    status: 'running',
    totalLeads: 150,
    sentCount: 142,
    failedCount: 3,
    delaySeconds: 15,
    createdAt: '2026-09-01'
  },
  {
    id: 'cmp-2',
    name: 'Enterprise Tech Follow-ups',
    templateId: 'tpl-2',
    accountId: 'acc-2',
    status: 'paused',
    totalLeads: 75,
    sentCount: 45,
    failedCount: 1,
    delaySeconds: 30,
    createdAt: '2026-09-02'
  }
];

export const initialLogs: ActivityLog[] = [
  {
    id: 'log-1',
    campaignId: 'cmp-1',
    campaignName: 'Q3 SaaS Outreach Batch 1',
    leadEmail: 'sarah.j@acmeproducts.io',
    accountName: 'Primary Outbound (SMTP)',
    status: 'sent',
    timestamp: '2026-09-02 11:42 AM'
  },
  {
    id: 'log-2',
    campaignId: 'cmp-1',
    campaignName: 'Q3 SaaS Outreach Batch 1',
    leadEmail: 'marcus@nexustech.co',
    accountName: 'Primary Outbound (SMTP)',
    status: 'sent',
    timestamp: '2026-09-02 11:41 AM'
  },
  {
    id: 'log-3',
    campaignId: 'cmp-1',
    campaignName: 'Q3 SaaS Outreach Batch 1',
    leadEmail: 'invalid.target@test.domain',
    accountName: 'Primary Outbound (SMTP)',
    status: 'failed',
    errorMessage: 'SMTP 550 5.1.1 User unknown',
    timestamp: '2026-09-02 11:39 AM'
  },
  {
    id: 'log-4',
    campaignId: 'cmp-2',
    campaignName: 'Enterprise Tech Follow-ups',
    leadEmail: 'elena@stellarsoftware.com',
    accountName: 'Microsoft 365 Executive',
    status: 'sent',
    timestamp: '2026-09-02 10:15 AM'
  }
];
