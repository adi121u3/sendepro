import React, { useMemo, useState } from 'react';
import { Campaign, Account, EmailTemplate, Lead } from '../types';
import {
  Play,
  Pause,
  Square,
  Plus,
  Clock,
  Server,
  FileText,
  Split,
  Trash2,
  X,
  Settings2,
  Mail,
  CheckCircle2,
} from 'lucide-react';

interface CampaignsViewProps {
  campaigns: Campaign[];
  accounts: Account[];
  templates: EmailTemplate[];
  leads: Lead[];
  onUpdateCampaignStatus: (id: string, status: Campaign['status']) => void;
  onCreateCampaign: (
    newCmp: Omit<Campaign, 'id' | 'sentCount' | 'failedCount' | 'createdAt'> &
      { templateIds?: string[]; subject?: string; bodyHtml?: string; replyTo?: string; maxRetries?: number; rotationMode?: string; useJitter?: boolean }
  ) => void;
  onDeleteCampaign?: (id: string) => void | Promise<void>;
}

type SpeedMode = 'slow' | 'normal' | 'fast';

const SPEED_DELAY: Record<SpeedMode, number> = {
  slow: 60,
  normal: 30,
  fast: 5,
};

export const CampaignsView: React.FC<CampaignsViewProps> = ({
  campaigns,
  accounts,
  templates,
  leads,
  onUpdateCampaignStatus,
  onCreateCampaign,
  onDeleteCampaign,
}) => {
  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [tagFilter, setTagFilter] = useState('All');

  // Workspace form state (mirrors desktop CampaignWorkspace)
  const [name, setName] = useState('');
  const [tag, setTag] = useState('Marketing');
  const [route, setRoute] = useState('auto');
  const [accountId, setAccountId] = useState<string>(accounts[0]?.id || '');
  const [replyTo, setReplyTo] = useState('');
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>(
    templates[0] ? [String(templates[0].id)] : []
  );
  const [subject, setSubject] = useState('');
  const [bodyHtml, setBodyHtml] = useState('');
  const [speed, setSpeed] = useState<SpeedMode>('normal');
  const [delaySeconds, setDelaySeconds] = useState(30);
  const [maxRetries, setMaxRetries] = useState(3);
  const [rotationMode, setRotationMode] = useState('round_robin');
  const [useJitter, setUseJitter] = useState(true);

  const activeLeadCount = useMemo(
    () => leads.filter((l) => l.status === 'new' || l.status === 'contacted' || !l.status).length || leads.length,
    [leads]
  );

  const filteredCampaigns = campaigns.filter((cmp) => {
    if (tagFilter === 'All') return true;
    return (cmp.tag || 'Marketing') === tagFilter;
  });

  const openNewWorkspace = () => {
    setEditingCampaign(null);
    setName('');
    setTag('Marketing');
    setRoute('auto');
    setAccountId(accounts[0]?.id ? String(accounts[0].id) : '');
    setReplyTo('');
    setSelectedTemplateIds(templates[0] ? [String(templates[0].id)] : []);
    setSubject(templates[0]?.subject || '');
    setBodyHtml(templates[0]?.bodyHtml || '');
    setSpeed('normal');
    setDelaySeconds(30);
    setMaxRetries(3);
    setRotationMode('round_robin');
    setUseJitter(true);
    setIsWorkspaceOpen(true);
  };

  const openEditWorkspace = (cmp: Campaign) => {
    setEditingCampaign(cmp);
    setName(cmp.name || '');
    setTag(cmp.tag || 'Marketing');
    setAccountId(cmp.accountId ? String(cmp.accountId) : '');
    setSelectedTemplateIds(
      cmp.templateIds?.length
        ? cmp.templateIds.map(String)
        : cmp.templateId
          ? [String(cmp.templateId)]
          : []
    );
    const tpl = templates.find((t) => String(t.id) === String(cmp.templateId));
    setSubject(tpl?.subject || '');
    setBodyHtml(tpl?.bodyHtml || '');
    setDelaySeconds(cmp.delaySeconds || 30);
    setMaxRetries(3);
    setRotationMode('round_robin');
    setUseJitter(true);
    setRoute('auto');
    setReplyTo('');
    setIsWorkspaceOpen(true);
  };

  const applySpeed = (mode: SpeedMode) => {
    setSpeed(mode);
    setDelaySeconds(SPEED_DELAY[mode]);
  };

  const onTemplateToggle = (id: string) => {
    setSelectedTemplateIds((prev) => {
      if (prev.includes(id)) {
        if (prev.length <= 1) return prev;
        return prev.filter((x) => x !== id);
      }
      return [...prev, id];
    });
  };

  const onPrimaryTemplateChange = (id: string) => {
    const tpl = templates.find((t) => String(t.id) === String(id));
    if (tpl) {
      setSubject(tpl.subject || '');
      setBodyHtml(tpl.bodyHtml || '');
    }
    if (!selectedTemplateIds.includes(id)) {
      setSelectedTemplateIds((prev) => [...prev, id]);
    }
  };

  const handleSaveAndStart = (startImmediately: boolean) => {
    if (!name.trim()) {
      alert('Campaign name is required.');
      return;
    }
    if (selectedTemplateIds.length === 0 && !bodyHtml.trim()) {
      alert('Select a template or enter an HTML message.');
      return;
    }
    if (activeLeadCount === 0) {
      alert('No active leads available. Import leads first.');
      return;
    }

    onCreateCampaign({
      name: name.trim(),
      tag,
      templateId: selectedTemplateIds[0] || '',
      templateIds: selectedTemplateIds,
      accountId: accountId || '',
      status: startImmediately ? 'running' : 'draft',
      totalLeads: leads.length,
      delaySeconds,
      subject,
      bodyHtml,
      replyTo,
      maxRetries,
      rotationMode,
      useJitter,
    });

    setIsWorkspaceOpen(false);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllVisible = () => {
    if (selectedIds.size === filteredCampaigns.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredCampaigns.map((c) => String(c.id))));
    }
  };

  const bulkStatus = (status: Campaign['status']) => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      alert('Select one or more campaigns first.');
      return;
    }
    ids.forEach((id) => onUpdateCampaignStatus(id, status));
    setSelectedIds(new Set());
  };

  const bulkDelete = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      alert('Select one or more campaigns first.');
      return;
    }
    if (!onDeleteCampaign) {
      alert('Delete is not wired to the backend yet.');
      return;
    }
    if (!confirm(`Delete ${ids.length} campaign(s)? This cannot be undone.`)) return;
    for (const id of ids) {
      await onDeleteCampaign(id);
    }
    setSelectedIds(new Set());
  };

  const deleteOne = async (id: string) => {
    if (!onDeleteCampaign) {
      alert('Delete is not wired to the backend yet.');
      return;
    }
    if (!confirm('Delete this campaign? This cannot be undone.')) return;
    await onDeleteCampaign(id);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100">Campaigns</h3>
          <p className="text-slate-400 text-sm">
            Manage campaigns with the same workspace layout as the desktop suite.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2">
            <span className="text-xs text-slate-400 font-medium">Filter Tag:</span>
            <select
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="All">All Tags</option>
              <option value="Marketing">Marketing</option>
              <option value="Onboarding">Onboarding</option>
              <option value="Cold Outreach">Cold Outreach</option>
              <option value="Sales">Sales</option>
              <option value="Transactional">Transactional</option>
            </select>
          </div>

          {selectedIds.size > 0 && (
            <>
              <button
                onClick={() => bulkStatus('paused')}
                className="flex items-center gap-1.5 px-3 py-2 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-xl text-xs font-semibold"
              >
                <Pause className="w-3.5 h-3.5" /> Pause ({selectedIds.size})
              </button>
              <button
                onClick={() => bulkStatus('stopped')}
                className="flex items-center gap-1.5 px-3 py-2 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-semibold"
              >
                <Square className="w-3.5 h-3.5" /> Stop ({selectedIds.size})
              </button>
              <button
                onClick={bulkDelete}
                className="flex items-center gap-1.5 px-3 py-2 bg-rose-600/20 text-rose-300 border border-rose-500/40 rounded-xl text-xs font-semibold"
              >
                <Trash2 className="w-3.5 h-3.5" /> Delete ({selectedIds.size})
              </button>
            </>
          )}

          <button
            onClick={openNewWorkspace}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            New Campaign
          </button>
        </div>
      </div>

      {/* Select all */}
      {filteredCampaigns.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <input
            type="checkbox"
            checked={selectedIds.size === filteredCampaigns.length && filteredCampaigns.length > 0}
            onChange={selectAllVisible}
            className="rounded border-slate-700 bg-slate-900 text-amber-500"
          />
          <span>Select all visible campaigns</span>
        </div>
      )}

      {/* Campaigns List */}
      <div className="grid grid-cols-1 gap-5">
        {filteredCampaigns.length === 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
            <Mail className="w-10 h-10 mx-auto mb-3 text-slate-600" />
            <p className="font-semibold text-slate-300">No campaigns yet</p>
            <p className="text-xs mt-1">Click New Campaign to open the full workspace editor.</p>
          </div>
        )}

        {filteredCampaigns.map((cmp) => {
          const template = templates.find((t) => String(t.id) === String(cmp.templateId));
          const account = accounts.find((a) => String(a.id) === String(cmp.accountId));
          const total = cmp.totalLeads || 0;
          const progress = total > 0 ? Math.round((cmp.sentCount / total) * 100) : 0;
          const id = String(cmp.id);
          const isSelected = selectedIds.has(id);

          return (
            <div
              key={cmp.id}
              className={`bg-slate-900 border rounded-2xl p-6 shadow-sm space-y-5 ${
                isSelected ? 'border-amber-500/50 ring-1 ring-amber-500/20' : 'border-slate-800'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(id)}
                    className="mt-1.5 rounded border-slate-700 bg-slate-900 text-amber-500"
                  />
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          cmp.status === 'running'
                            ? 'bg-emerald-500 animate-pulse'
                            : cmp.status === 'paused'
                              ? 'bg-amber-500'
                              : 'bg-slate-500'
                        }`}
                      />
                      <h4 className="text-lg font-bold text-slate-100">{cmp.name}</h4>
                      <span
                        className={`px-2.5 py-0.5 text-[11px] rounded-full font-semibold uppercase tracking-wider ${
                          cmp.status === 'running'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : cmp.status === 'paused'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {cmp.status}
                      </span>
                      <span className="px-2 py-0.5 text-[11px] rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        {cmp.tag || 'Marketing'}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                      <span className="flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-amber-400" />
                        {cmp.templateIds && cmp.templateIds.length > 1 ? (
                          <span className="text-amber-300 font-semibold flex items-center gap-1">
                            <Split className="w-3 h-3" /> A/B ({cmp.templateIds.length})
                          </span>
                        ) : (
                          template?.name || 'Template'
                        )}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Server className="w-3.5 h-3.5 text-purple-400" />
                        {account?.name || 'Account rotation'}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-blue-400" />
                        {cmp.delaySeconds || 30}s delay
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => openEditWorkspace(cmp)}
                    className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-semibold"
                  >
                    <Settings2 className="w-3.5 h-3.5" /> Open
                  </button>
                  {cmp.status === 'running' ? (
                    <button
                      onClick={() => onUpdateCampaignStatus(id, 'paused')}
                      className="flex items-center gap-1.5 px-3 py-2 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-xl text-xs font-semibold"
                    >
                      <Pause className="w-3.5 h-3.5" /> Pause
                    </button>
                  ) : (
                    <button
                      onClick={() => onUpdateCampaignStatus(id, 'running')}
                      className="flex items-center gap-1.5 px-3 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-semibold"
                    >
                      <Play className="w-3.5 h-3.5" />
                      {cmp.status === 'paused' ? 'Resume' : 'Start'}
                    </button>
                  )}
                  <button
                    onClick={() => onUpdateCampaignStatus(id, 'stopped')}
                    className="flex items-center gap-1.5 px-3 py-2 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-semibold"
                  >
                    <Square className="w-3.5 h-3.5" /> Stop
                  </button>
                  <button
                    onClick={() => deleteOne(id)}
                    className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-slate-700 rounded-xl text-xs font-semibold"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-800/80">
                <div className="flex justify-between text-xs font-medium text-slate-300">
                  <span>
                    Sent: <strong className="text-emerald-400">{cmp.sentCount}</strong> / {total}
                  </span>
                  <span>
                    Failed: <strong className="text-rose-400">{cmp.failedCount}</strong>
                  </span>
                  <span>{progress}% Complete</span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full Campaign Workspace (desktop-parity) */}
      {isWorkspaceOpen && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[92vh] overflow-hidden shadow-2xl flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-start justify-between gap-4 bg-slate-950/40">
              <div>
                <h3 className="text-xl font-bold text-slate-100">
                  {editingCampaign ? 'Edit Campaign' : 'New Campaign'}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Configure your campaign, message, delivery route and sending settings.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
                  {editingCampaign?.status || 'DRAFT'}
                </span>
                <button
                  onClick={() => setIsWorkspaceOpen(false)}
                  className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* LEFT */}
                <div className="lg:col-span-2 space-y-5">
                  {/* Campaign Details */}
                  <section className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-3">
                    <h4 className="text-sm font-bold text-slate-200">Campaign Details</h4>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Campaign Name
                      </label>
                      <input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Example: Q3 Executive Outreach"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-sm text-slate-300">
                        Lead Source:{' '}
                        <strong className="text-amber-400">{activeLeadCount} active leads</strong>
                      </div>
                      <div className="flex gap-2">
                        <select
                          value={tag}
                          onChange={(e) => setTag(e.target.value)}
                          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                        >
                          <option value="Marketing">Marketing</option>
                          <option value="Onboarding">Onboarding</option>
                          <option value="Cold Outreach">Cold Outreach</option>
                          <option value="Sales">Sales</option>
                          <option value="Transactional">Transactional</option>
                        </select>
                      </div>
                    </div>
                  </section>

                  {/* Delivery Configuration */}
                  <section className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-3">
                    <h4 className="text-sm font-bold text-slate-200">Delivery Configuration</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                          Delivery Route
                        </label>
                        <select
                          value={route}
                          onChange={(e) => setRoute(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100"
                        >
                          <option value="auto">Automatic</option>
                          <option value="smtp">SMTP</option>
                          <option value="zeptomail_smtp">ZeptoMail SMTP</option>
                          <option value="zeptomail_api">ZeptoMail API</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                          Sending Account
                        </label>
                        <select
                          value={accountId}
                          onChange={(e) => setAccountId(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100"
                        >
                          <option value="">Automatic Account Rotation</option>
                          {accounts.map((a) => (
                            <option key={a.id} value={a.id}>
                              {a.name} • {(a.providerType || 'smtp').toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Reply-To
                      </label>
                      <input
                        value={replyTo}
                        onChange={(e) => setReplyTo(e.target.value)}
                        placeholder="Optional reply-to address"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  </section>

                  {/* Message & Personalization */}
                  <section className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-3">
                    <h4 className="text-sm font-bold text-slate-200">Message & Personalization</h4>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Template
                      </label>
                      <select
                        value={selectedTemplateIds[0] || ''}
                        onChange={(e) => onPrimaryTemplateChange(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100"
                      >
                        <option value="">No Template — Write New Message</option>
                        {templates.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {templates.length > 1 && (
                      <div className="space-y-1.5 max-h-28 overflow-y-auto border border-slate-800 rounded-lg p-2">
                        <p className="text-[10px] text-slate-500 uppercase font-semibold">A/B templates (optional)</p>
                        {templates.map((t) => {
                          const id = String(t.id);
                          const checked = selectedTemplateIds.includes(id);
                          return (
                            <label
                              key={id}
                              className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-xs ${
                                checked ? 'bg-amber-500/10 text-amber-300' : 'text-slate-300 hover:bg-slate-900'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => onTemplateToggle(id)}
                                className="rounded border-slate-700 text-amber-500"
                              />
                              {t.name}
                            </label>
                          );
                        })}
                      </div>
                    )}

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Subject
                      </label>
                      <input
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        placeholder="Example: Quick question for {{FirstName}}"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        HTML Message
                      </label>
                      <textarea
                        value={bodyHtml}
                        onChange={(e) => setBodyHtml(e.target.value)}
                        rows={8}
                        placeholder="Write your HTML email here... Use {{FirstName}}, {{Company}}, etc."
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-amber-500 resize-y"
                      />
                    </div>
                  </section>
                </div>

                {/* RIGHT */}
                <div className="space-y-5">
                  {/* Sending Settings */}
                  <section className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-3">
                    <h4 className="text-sm font-bold text-slate-200">Sending Settings</h4>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Speed
                      </label>
                      <div className="grid grid-cols-3 gap-1.5">
                        {(['slow', 'normal', 'fast'] as SpeedMode[]).map((mode) => (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => applySpeed(mode)}
                            className={`py-2 rounded-lg text-xs font-semibold capitalize border ${
                              speed === mode
                                ? 'bg-amber-500 text-slate-950 border-amber-400'
                                : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600'
                            }`}
                          >
                            {mode}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Delay
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min={1}
                          max={3600}
                          value={delaySeconds}
                          onChange={(e) => setDelaySeconds(Number(e.target.value) || 1)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100"
                        />
                        <span className="text-xs text-slate-500 shrink-0">sec</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Max Retries
                      </label>
                      <input
                        type="number"
                        min={0}
                        max={20}
                        value={maxRetries}
                        onChange={(e) => setMaxRetries(Number(e.target.value) || 0)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                        Account Rotation
                      </label>
                      <select
                        value={rotationMode}
                        onChange={(e) => setRotationMode(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100"
                      >
                        <option value="round_robin">Round Robin</option>
                        <option value="random">Random</option>
                        <option value="failover">Failover</option>
                      </select>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={useJitter}
                        onChange={(e) => setUseJitter(e.target.checked)}
                        className="rounded border-slate-700 text-amber-500"
                      />
                      Use small random delay variation
                    </label>
                  </section>

                  {/* Campaign Status snapshot */}
                  <section className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-3">
                    <h4 className="text-sm font-bold text-slate-200">Campaign Status</h4>
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="bg-slate-900 rounded-lg p-3 border border-slate-800">
                        <div className="text-lg font-bold text-slate-100">{leads.length}</div>
                        <div className="text-[10px] text-slate-500 uppercase">Total</div>
                      </div>
                      <div className="bg-slate-900 rounded-lg p-3 border border-slate-800">
                        <div className="text-lg font-bold text-emerald-400">
                          {editingCampaign?.sentCount ?? 0}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Sent</div>
                      </div>
                      <div className="bg-slate-900 rounded-lg p-3 border border-slate-800">
                        <div className="text-lg font-bold text-rose-400">
                          {editingCampaign?.failedCount ?? 0}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Failed</div>
                      </div>
                      <div className="bg-slate-900 rounded-lg p-3 border border-slate-800">
                        <div className="text-lg font-bold text-slate-100">
                          {Math.max(
                            0,
                            leads.length -
                              (editingCampaign?.sentCount || 0) -
                              (editingCampaign?.failedCount || 0)
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Remaining</div>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Status: {(editingCampaign?.status || 'DRAFT').toUpperCase()}
                      <br />
                      Route: {route === 'auto' ? 'Automatic' : route}
                    </p>
                  </section>

                  {/* Campaign Controls */}
                  <section className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-2">
                    <h4 className="text-sm font-bold text-slate-200 mb-1">Campaign Controls</h4>
                    <button
                      type="button"
                      onClick={() => handleSaveAndStart(true)}
                      className="w-full py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-sm flex items-center justify-center gap-2"
                    >
                      <Play className="w-4 h-4" /> Start Campaign
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSaveAndStart(false)}
                      className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-sm flex items-center justify-center gap-2 border border-slate-700"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Save Draft
                    </button>
                    {editingCampaign && (
                      <>
                        <button
                          type="button"
                          onClick={() => onUpdateCampaignStatus(String(editingCampaign.id), 'paused')}
                          className="w-full py-2 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-xl text-xs font-semibold"
                        >
                          Pause
                        </button>
                        <button
                          type="button"
                          onClick={() => onUpdateCampaignStatus(String(editingCampaign.id), 'stopped')}
                          className="w-full py-2 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-semibold"
                        >
                          Stop Campaign
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      onClick={() => setIsWorkspaceOpen(false)}
                      className="w-full py-2 text-slate-400 hover:text-slate-200 text-xs font-medium"
                    >
                      Close
                    </button>
                  </section>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
