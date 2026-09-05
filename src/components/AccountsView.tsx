import React, { useState } from 'react';
import { Account } from '../types';
import { Server, ShieldCheck, CheckCircle2, AlertTriangle, Plus, RefreshCw, Key, Globe, Lock, ExternalLink, HelpCircle, Pencil, Trash2 } from 'lucide-react';
import * as api from '../services/api';

interface AccountsViewProps {
  accounts: Account[];
  onAddAccount: (acc: Omit<Account, 'id' | 'sentToday' | 'status' | 'lastTested'>) => void;
  onUpdateAccount: (id: string | number, acc: any) => void;
  onDeleteAccount: (id: string | number) => void;
}

export const AccountsView: React.FC<AccountsViewProps> = ({ accounts, onAddAccount, onUpdateAccount, onDeleteAccount }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState<string | number | null>(null);
  const [isOAuthModalOpen, setIsOAuthModalOpen] = useState(false);
  const [oauthProvider, setOauthProvider] = useState<'google' | 'microsoft'>('google');
  const [oauthName, setOauthName] = useState('');
  const [oauthEmail, setOauthEmail] = useState('');
  const [oauthAccessToken, setOauthAccessToken] = useState('');
  const [oauthRefreshToken, setOauthRefreshToken] = useState('');

  // SMTP form state
  const [name, setName] = useState('');
  const [providerType, setProviderType] = useState<Account['providerType']>('smtp');
  const [host, setHost] = useState('smtphm.sympatico.ca');
  const [port, setPort] = useState(587);
  const [security, setSecurity] = useState<Account['security']>('starttls');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fromEmail, setFromEmail] = useState('');
  const [fromName, setFromName] = useState('');
  const [dailyLimit, setDailyLimit] = useState(500);

  const [testingId, setTestingId] = useState<any | null>(null);
  const [testResult, setTestResult] = useState<{ id: any; success: boolean; msg: string } | null>(null);

  const [testingSmtp, setTestingSmtp] = useState(false);
  const [testSmtpMsg, setTestSmtpMsg] = useState('');
  const [testSmtpError, setTestSmtpError] = useState('');

  const resetAccountForm = () => {
    setName('');
    setProviderType('smtp');
    setHost('smtphm.sympatico.ca');
    setPort(587);
    setSecurity('starttls');
    setUsername('');
    setPassword('');
    setFromEmail('');
    setFromName('');
    setDailyLimit(500);
    setEditingAccountId(null);
  };

  const handleEditAccount = (account: Account) => {
    const raw = account as any;
    setEditingAccountId(account.id);
    setName(account.name || '');
    setProviderType((raw.providerType || raw.provider || 'smtp') as Account['providerType']);
    setHost(raw.smtpHost || raw.host || '');
    setPort(raw.smtpPort || raw.port || 587);
    setSecurity((raw.smtpSecurity || raw.security || 'starttls') as Account['security']);
    setUsername(raw.smtpUsername || raw.username || account.email || '');
    setPassword('');
    setFromEmail(account.email || raw.fromEmail || '');
    setFromName(account.fromName || '');
    setDailyLimit(account.dailyLimit || 500);
    setIsModalOpen(true);
  };

  const handleTestSmtp = async () => {
    if (!host || !fromEmail || !password) {
      setTestSmtpError('Please provide Host, From Email, and Password to test.');
      return;
    }
    setTestingSmtp(true);
    setTestSmtpMsg('');
    setTestSmtpError('');
    try {
      const res = await api.testSmtpCredentials({
        host,
        port,
        security,
        username: fromEmail,
        password
      });
      setTestSmtpMsg(res.message || 'SMTP Authentication Successful!');
    } catch (err: any) {
      setTestSmtpError(err.message || 'SMTP authentication failed');
    } finally {
      setTestingSmtp(false);
    }
  };

  const handleTestConnection = async (id: any, accName: string) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const numericId = typeof id === 'number' ? id : parseInt(String(id).replace(/\D/g, ''), 10);
      const res = await api.testAccountConnection(numericId);
      setTestResult({
        id,
        success: true,
        msg: res.message || `Successfully connected to ${accName}. Handshake verified.`
      });
    } catch (e: any) {
      setTestResult({
        id,
        success: false,
        msg: e.message || `Connection failed for ${accName}.`
      });
    } finally {
      setTestingId(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !fromEmail.trim() || (!editingAccountId && !password)) return;
    const accountData = {
      name,
      providerType,
      host,
      port,
      security,
      username,
      fromEmail,
      fromName,
      dailyLimit,
      smtpPassword: password
    } as any;
    if (editingAccountId) {
      onUpdateAccount(editingAccountId, accountData);
    } else {
      onAddAccount(accountData);
    }
    resetAccountForm();
    setIsModalOpen(false);
  };

  const handleOAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!oauthEmail.trim() || !oauthAccessToken.trim()) {
      alert("Please provide email and OAuth access token.");
      return;
    }
    console.log(`[OAuth2 Persistence] Saving connected OAuth account (${oauthProvider}) for ${oauthEmail}`);
    try {
      await api.oauthConnectAccount({
        provider: oauthProvider,
        name: oauthName || `${oauthProvider === 'google' ? 'Google' : 'Microsoft'} Account`,
        email: oauthEmail,
        from_name: oauthName,
        access_token: oauthAccessToken,
        refresh_token: oauthRefreshToken
      });
      console.log(`[OAuth2 Persistence] Successfully stored encrypted credentials for ${oauthEmail}`);
      setIsOAuthModalOpen(false);
      setOauthEmail('');
      setOauthAccessToken('');
      setOauthRefreshToken('');
      setOauthName('');
      window.location.reload();
    } catch (e: any) {
      console.error(`[OAuth2 Persistence Error] Failed to connect OAuth account:`, e);
      alert(e.message || "Failed to connect OAuth account");
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100">SMTP & OAuth2 Provider Accounts</h3>
          <p className="text-slate-400 text-sm">Configure secure sending transports, Google OAuth, Microsoft 365 OAuth2, and API credentials</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              window.open('/api/oauth/authorize?provider=google', '_blank', 'width=700,height=800');
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-blue-600/20"
          >
            <Globe className="w-4 h-4" />
            Connect Google OAuth
          </button>
          <button
            onClick={() => {
              window.open('/api/oauth/authorize?provider=microsoft', '_blank', 'width=700,height=800');
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-sky-700 hover:bg-sky-600 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-sky-700/20"
          >
            <ShieldCheck className="w-4 h-4" />
            Connect Microsoft OAuth2
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            Add SMTP Account
          </button>
        </div>
      </div>

      {testResult && (
        <div className={`p-4 rounded-xl flex items-center justify-between text-sm ${testResult.success ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border border-red-500/30 text-red-300'}`}>
          <div className="flex items-center gap-3">
            {testResult.success ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" /> : <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />}
            <span>{testResult.msg}</span>
          </div>
          <button onClick={() => setTestResult(null)} className="text-xs font-bold hover:underline">Dismiss</button>
        </div>
      )}

      {/* Accounts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.map((acc) => (
          <div key={acc.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                  acc.provider === 'google' || acc.provider === 'gmail' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                  acc.provider === 'microsoft' || acc.provider === 'outlook' ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' :
                  'bg-purple-500/10 text-purple-400 border-purple-500/20'
                }`}>
                  {acc.provider === 'google' || acc.provider === 'gmail' ? <Globe className="w-5 h-5" /> :
                   acc.provider === 'microsoft' || acc.provider === 'outlook' ? <ShieldCheck className="w-5 h-5" /> :
                   <Server className="w-5 h-5" />}
                </div>
                <span className={`px-2.5 py-1 text-xs rounded-full font-semibold uppercase tracking-wider ${
                  acc.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}>
                  {acc.status}
                </span>
              </div>

              <div>
                <h4 className="font-bold text-slate-100 text-base">{acc.name}</h4>
                <p className="text-xs text-slate-400 mt-0.5">{acc.email} ({acc.fromName || acc.name})</p>
              </div>

              <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Provider:</span>
                  <span className="font-semibold uppercase text-slate-200">{acc.provider || acc.providerType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Daily Limit:</span>
                  <span className="text-slate-200">{acc.sentToday || 0} / {acc.dailyLimit} sent</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Encrypted OAuth/SMTP</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleEditAccount(acc)}
                  title="Edit account"
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => {
                    if (window.confirm(`Remove account \"${acc.name}\"?`)) onDeleteAccount(acc.id);
                  }}
                  title="Delete account"
                  className="p-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 rounded-lg border border-rose-500/20"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleTestConnection(acc.id, acc.name)}
                  disabled={testingId === acc.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-all border border-slate-700"
                >
                  <RefreshCw className={`w-3 h-3 ${testingId === acc.id ? 'animate-spin text-amber-400' : ''}`} />
                  {testingId === acc.id ? 'Testing...' : 'Test Connection'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add SMTP Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100">{editingAccountId ? 'Edit Sender Account' : 'Add SMTP Sender Account'}</h3>
              <button onClick={() => { resetAccountForm(); setIsModalOpen(false); }} className="text-slate-400 hover:text-slate-200 font-semibold">✕</button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Account Label</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Sales SMTP Server"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Provider Type</label>
                  <select
                    value={providerType}
                    onChange={(e) => {
                      const val = e.target.value as any;
                      setProviderType(val);
                    {val === 'bell' ? (
                      setName('Bell Sympatico SMTP'),
                      setHost('smtphm.sympatico.ca'),
                      setPort(587),
                      setSecurity('starttls')
                    ) : val === 'gmail' ? (
                      setName('Gmail SMTP'),
                      setHost('smtp.gmail.com'),
                      setPort(587),
                      setSecurity('starttls')
                    ) : val === 'zeptomail_smtp' ? (
                      setName('ZeptoMail SMTP'),
                      setHost('smtp.zeptomail.com'),
                      setPort(587),
                      setSecurity('starttls'),
                      setUsername('emailapikey')
                    ) : val === 'zeptomail' ? (
                      setName('ZeptoMail API Relay'),
                      setHost('api.zeptomail.com'),
                      setPort(443),
                      setSecurity('ssl'),
                      setUsername('emailapikey')
                    ) : null}
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                  >
                    <option value="smtp">Generic SMTP</option>
                    <option value="bell">Bell / Sympatico SMTP</option>
                    <option value="gmail">Gmail SMTP</option>
                    <option value="zeptomail_smtp">ZeptoMail SMTP (smtp.zeptomail.com)</option>
                    <option value="zeptomail">ZeptoMail API (api.zeptomail.com)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Security Type</label>
                  <select
                    value={security}
                    onChange={(e) => setSecurity(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                  >
                    <option value="starttls">STARTTLS</option>
                    <option value="ssl">SSL / TLS</option>
                    <option value="none">None</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">SMTP Host</label>
                  <input
                    type="text"
                    required
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Port</label>
                  <input
                    type="number"
                    required
                    value={port}
                    onChange={(e) => setPort(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">From Email</label>
                  <input
                    type="email"
                    required
                    value={fromEmail}
                    onChange={(e) => setFromEmail(e.target.value)}
                    placeholder="sender@example.com"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">From Name</label>
                  <input
                    type="text"
                    required
                    value={fromName}
                    onChange={(e) => setFromName(e.target.value)}
                    placeholder="Alex Rivers"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">SMTP Password / App Password</label>
                <input
                  type="password"
                  required={!editingAccountId}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                    placeholder={editingAccountId ? 'Leave blank to keep current password' : '••••••••••••'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
              </div>

              {testSmtpMsg && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" /> {testSmtpMsg}
                </div>
              )}
              {testSmtpError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" /> {testSmtpError}
                </div>
              )}

              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleTestSmtp}
                  disabled={testingSmtp}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all flex items-center gap-1.5 border border-slate-700"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${testingSmtp ? 'animate-spin text-amber-400' : ''}`} />
                  {testingSmtp ? 'Testing Login...' : 'Test SMTP Login'}
                </button>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { resetAccountForm(); setIsModalOpen(false); }}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-sm font-semibold transition-all shadow-lg shadow-amber-500/20"
                  >
                    {editingAccountId ? 'Update Account' : 'Save Account'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* OAuth Connect Modal with Interactive Simulation & Manual Token entry */}
      {isOAuthModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                {oauthProvider === 'google' ? <Globe className="w-5 h-5 text-blue-400" /> : <ShieldCheck className="w-5 h-5 text-sky-400" />}
                Connect {oauthProvider === 'google' ? 'Google OAuth (Gmail / Workspace)' : 'Microsoft 365 OAuth2'}
              </h3>
              <button onClick={() => setIsOAuthModalOpen(false)} className="text-slate-400 hover:text-slate-200 font-semibold">✕</button>
            </div>

            <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
              <p className="text-xs text-slate-300">
                Authenticate via official {oauthProvider === 'google' ? 'Google OAuth2' : 'Microsoft 365'} authorization code exchange and paste your issued access & refresh tokens below.
              </p>
            </div>

            <form onSubmit={handleOAuthSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Account Label</label>
                <input
                  type="text"
                  required
                  value={oauthName}
                  onChange={(e) => setOauthName(e.target.value)}
                  placeholder={oauthProvider === 'google' ? "Google Workspace Executive" : "Microsoft Exchange 365"}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Sender Email Address</label>
                <input
                  type="email"
                  required
                  value={oauthEmail}
                  onChange={(e) => setOauthEmail(e.target.value)}
                  placeholder="executive@company.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">OAuth2 Access Token</label>
                <textarea
                  required
                  rows={2}
                  value={oauthAccessToken}
                  onChange={(e) => setOauthAccessToken(e.target.value)}
                  placeholder="ya29.a0AfH6SM..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">OAuth2 Refresh Token</label>
                <input
                  type="password"
                  value={oauthRefreshToken}
                  onChange={(e) => setOauthRefreshToken(e.target.value)}
                  placeholder="1//04..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono text-xs"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsOAuthModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`px-5 py-2 rounded-xl text-white text-sm font-semibold transition-all shadow-lg ${
                    oauthProvider === 'google' ? 'bg-blue-600 hover:bg-blue-500 shadow-blue-600/20' : 'bg-sky-700 hover:bg-sky-600 shadow-sky-700/20'
                  }`}
                >
                  Save & Link OAuth Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
