import React, { useState, useEffect } from 'react';
import { TabType, Campaign, Account, Lead, EmailTemplate, ActivityLog } from './types';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardView } from './components/DashboardView';
import { CampaignsView } from './components/CampaignsView';
import { AccountsView } from './components/AccountsView';
import { LeadsView } from './components/LeadsView';
import { TemplatesView } from './components/TemplatesView';
import { ActivityView } from './components/ActivityView';
import { SettingsView } from './components/SettingsView';
import { DraftsView } from './components/DraftsView';
import * as api from './services/api';

export default function App() {
  const [currentTab, setCurrentTab] = useState<TabType>('dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [loginUsername, setLoginUsername] = useState('admin');
  const [loginPassword, setLoginPassword] = useState('AdminSecure2026!');
  const [loginError, setLoginError] = useState('');

  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const [accs, lds, tpls, cmps, actLogs] = await Promise.all([
        api.fetchAccounts().catch(() => []),
        api.fetchLeads().catch(() => []),
        api.fetchTemplates().catch(() => []),
        api.fetchCampaigns().catch(() => []),
        api.fetchActivityLogs().catch(() => [])
      ]);
      setAccounts(accs);
      setLeads(lds);
      setTemplates(tpls);
      setCampaigns(cmps);
      setLogs(actLogs);
    } catch (e) {
      console.error("Failed to load backend data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.verifyAuth().then(authed => {
      setIsAuthenticated(authed);
      if (authed) {
        loadData();
      } else {
        setLoading(false);
      }
    });
  }, []);

  const handleUpdateCampaignStatus = async (id: string, status: Campaign['status']) => {
    try {
      const numericId = parseInt(String(id).replace(/\D/g, ''), 10) || Number(id);
      await api.updateCampaignStatus(numericId, status);
      await loadData();
    } catch (e: any) {
      console.error("Failed to update campaign status:", e);
      alert(e.message || 'Failed to update campaign status');
    }
  };

  const handleDeleteCampaign = async (id: string) => {
    try {
      const numericId = parseInt(String(id).replace(/\D/g, ''), 10) || Number(id);
      await api.deleteCampaign(numericId);
      await loadData();
    } catch (e: any) {
      console.error("Failed to delete campaign:", e);
      alert(e.message || 'Failed to delete campaign');
    }
  };

  const handleCreateCampaign = async (newCmp: any) => {
    try {
      const templateIds = (newCmp.templateIds || [])
        .map((tid: string | number) => parseInt(String(tid).replace(/\D/g, ''), 10))
        .filter((n: number) => !Number.isNaN(n) && n > 0);

      const primaryTemplateId = newCmp.templateId
        ? parseInt(String(newCmp.templateId).replace(/\D/g, ''), 10)
        : templateIds[0] || null;

      const accountId = newCmp.accountId
        ? parseInt(String(newCmp.accountId).replace(/\D/g, ''), 10)
        : null;

      const created = await api.createCampaign({
        name: newCmp.name,
        tag: newCmp.tag || 'Marketing',
        templateId: primaryTemplateId,
        templateIds: templateIds.length ? templateIds : (primaryTemplateId ? [primaryTemplateId] : []),
        accountId: accountId && accountId > 0 ? accountId : null,
        leadIds: leads.map(l => typeof l.id === 'number' ? l.id : parseInt(String(l.id).replace(/\D/g, ''), 10)).filter((n: number) => !Number.isNaN(n)),
        delaySeconds: newCmp.delaySeconds ?? 30,
        useJitter: newCmp.useJitter !== false,
        jitterSeconds: newCmp.useJitter === false ? 0 : 2,
        maxRetries: newCmp.maxRetries ?? 3,
        rotationMode: newCmp.rotationMode || 'round_robin',
        replyTo: newCmp.replyTo || '',
        deliveryRoute: newCmp.deliveryRoute || 'auto',
      });

      // If user chose Start Campaign, set running after create
      if (newCmp.status === 'running' && created?.id) {
        await api.updateCampaignStatus(created.id, 'running');
      }

      await loadData();
      setCurrentTab('campaigns');
    } catch (e: any) {
      console.error("Failed to create campaign:", e);
      alert(e.message || "Failed to create campaign on backend.");
    }
  };

  const handleAddAccount = async (acc: Omit<Account, 'id' | 'sentToday' | 'status' | 'lastTested'>) => {
    try {
      await api.createAccount({
        provider: (acc as any).providerType || (acc as any).provider || 'smtp',
        name: acc.name,
        email: acc.fromEmail || (acc as any).email,
        from_name: acc.fromName,
        smtp_host: (acc as any).host,
        smtp_port: (acc as any).port,
        smtp_security: (acc as any).security,
        smtp_username: (acc as any).username || acc.fromEmail || (acc as any).email,
        enabled: (acc as any).enabled,
        daily_limit: acc.dailyLimit,
        smtp_password: (acc as any).smtpPassword || (acc as any).password,
        zeptomail_api_key: (acc as any).apiKey
      });
      await loadData();
    } catch (e: any) {
      console.error("Failed to add account:", e);
      alert(e.message || "Failed to add account");
    }
  };

  const handleUpdateAccount = async (id: string | number, acc: any) => {
    try {
      const numericId = Number(id);
      await api.updateAccount(numericId, {
        name: acc.name,
        email: acc.fromEmail || acc.email,
        from_name: acc.fromName,
        smtp_host: acc.host,
        smtp_port: acc.port,
        smtp_security: acc.security,
        smtp_username: acc.username,
        daily_limit: acc.dailyLimit,
        ...(acc.smtpPassword ? { smtp_password: acc.smtpPassword } : {})
      });
      await loadData();
    } catch (e: any) {
      console.error("Failed to update account:", e);
      alert(e.message || "Failed to update account");
    }
  };

  const handleDeleteAccount = async (id: string | number) => {
    try {
      await api.deleteAccount(Number(id));
      await loadData();
    } catch (e: any) {
      console.error("Failed to delete account:", e);
      alert(e.message || "Failed to delete account");
    }
  };

  const handleAddLead = async (lead: Omit<Lead, 'id' | 'createdAt'>) => {
    try {
      await api.createLead(lead);
      await loadData();
    } catch (e: any) {
      console.error("Failed to add lead:", e);
      alert(e.message || "Failed to add lead");
    }
  };

  const handleDeleteLead = async (id: string) => {
    try {
      const numericId = parseInt(id.replace(/\D/g, ''), 10) || Number(id);
      await api.deleteLead(numericId);
      await loadData();
    } catch (e) {
      console.error("Failed to delete lead:", e);
    }
  };

  const handleAddTemplate = async (tpl: Omit<EmailTemplate, 'id' | 'updatedAt'>) => {
    try {
      await api.createTemplate({
        name: tpl.name,
        subject: tpl.subject,
        body_html: tpl.bodyHtml
      });
      await loadData();
    } catch (e: any) {
      console.error("Failed to add template:", e);
      alert(e.message || "Failed to add template");
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    try {
      const numericId = parseInt(id.replace(/\D/g, ''), 10) || Number(id);
      await api.deleteTemplate(numericId);
      await loadData();
    } catch (e) {
      console.error("Failed to delete template:", e);
    }
  };

  const activeCampaignsCount = campaigns.filter(c => c.status === 'running').length;

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm text-slate-400">Loading Email Sender Pro backend database...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-100 p-4">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-center mx-auto text-amber-400 font-bold text-xl">
              ⚡
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100">Email Sender Pro Security</h1>
            <p className="text-xs text-slate-400">Enter administrative credentials to access secure endpoints.</p>
          </div>

          <form onSubmit={async (e) => {
            e.preventDefault();
            setLoginError('');
            try {
              await api.loginAdmin(loginUsername, loginPassword);
              setIsAuthenticated(true);
              setLoading(true);
              await loadData();
            } catch (err: any) {
              setLoginError(err.message || 'Authentication failed');
            }
          }} className="space-y-4">
            {loginError && (
              <div className="p-3 rounded-lg bg-red-950/50 border border-red-800 text-red-300 text-xs">
                {loginError}
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Username</label>
              <input
                type="text"
                value={loginUsername}
                onChange={e => setLoginUsername(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={e => setLoginPassword(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
              />
            </div>
            <div className="text-[11px] text-slate-500 bg-slate-950/50 p-3 rounded-xl border border-slate-800/80">
              Default credentials: <code className="text-amber-400 font-mono">admin</code> / <code className="text-amber-400 font-mono">AdminSecure2026!</code>
            </div>
            <button
              type="submit"
              className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-xs transition-all shadow-lg shadow-amber-500/20"
            >
              Sign In to Admin Dashboard
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar 
        currentTab={currentTab} 
        onSelectTab={setCurrentTab} 
        activeCampaignsCount={activeCampaignsCount} 
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header 
          currentTab={currentTab}
          onNewCampaign={() => setCurrentTab('campaigns')}
          onNewAccount={() => setCurrentTab('accounts')}
          onNewLead={() => setCurrentTab('leads')}
        />

        <main className="flex-1 overflow-y-auto bg-slate-950">
          {currentTab === 'dashboard' && (
            <DashboardView 
              campaigns={campaigns}
              accounts={accounts}
              leads={leads}
              logs={logs}
              onSelectTab={setCurrentTab}
              onNewCampaign={() => setCurrentTab('campaigns')}
            />
          )}

          {currentTab === 'campaigns' && (
            <CampaignsView 
              campaigns={campaigns}
              accounts={accounts}
              templates={templates}
              leads={leads}
              onUpdateCampaignStatus={handleUpdateCampaignStatus}
              onCreateCampaign={handleCreateCampaign}
              onDeleteCampaign={handleDeleteCampaign}
            />
          )}

          {currentTab === 'accounts' && (
            <AccountsView 
              accounts={accounts}
              onAddAccount={handleAddAccount}
              onUpdateAccount={handleUpdateAccount}
              onDeleteAccount={handleDeleteAccount}
            />
          )}

          {currentTab === 'leads' && (
            <LeadsView 
              leads={leads}
              onAddLead={handleAddLead}
              onDeleteLead={handleDeleteLead}
            />
          )}

          {currentTab === 'templates' && (
            <TemplatesView 
              templates={templates}
              onAddTemplate={handleAddTemplate}
              onDeleteTemplate={handleDeleteTemplate}
            />
          )}

          {(currentTab === 'Email Composer' || currentTab === 'drafts') && (
            <DraftsView 
              accounts={accounts}
            />
          )}

          {currentTab === 'activity' && (
            <ActivityView 
              logs={logs}
            />
          )}

          {currentTab === 'settings' && (
            <SettingsView />
          )}
        </main>
      </div>
    </div>
  );
}
