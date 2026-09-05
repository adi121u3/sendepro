import React, { useState } from 'react';
import { Campaign, Account, EmailTemplate, Lead } from '../types';
import { Play, Pause, Square, Plus, Send, Clock, Server, FileText, CheckCircle2, Split } from 'lucide-react';

interface CampaignsViewProps {
  campaigns: Campaign[];
  accounts: Account[];
  templates: EmailTemplate[];
  leads: Lead[];
  onUpdateCampaignStatus: (id: string, status: Campaign['status']) => void;
  onCreateCampaign: (newCmp: Omit<Campaign, 'id' | 'sentCount' | 'failedCount' | 'createdAt'> & { templateIds?: string[] }) => void;
}

export const CampaignsView: React.FC<CampaignsViewProps> = ({
  campaigns,
  accounts,
  templates,
  leads,
  onUpdateCampaignStatus,
  onCreateCampaign
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [tag, setTag] = useState('Marketing');
  const [tagFilter, setTagFilter] = useState('All');
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>(templates[0] ? [templates[0].id] : []);
  const [accountId, setAccountId] = useState(accounts[0]?.id || '');
  const [delaySeconds, setDelaySeconds] = useState(15);

  const toggleTemplate = (id: string) => {
    if (selectedTemplateIds.includes(id)) {
      if (selectedTemplateIds.length > 1) {
        setSelectedTemplateIds(selectedTemplateIds.filter(i => i !== id));
      }
    } else {
      setSelectedTemplateIds([...selectedTemplateIds, id]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (selectedTemplateIds.length === 0) {
      alert("Please select at least one email template.");
      return;
    }
    onCreateCampaign({
      name,
      tag,
      templateId: selectedTemplateIds[0],
      templateIds: selectedTemplateIds,
      accountId,
      status: 'running',
      totalLeads: leads.length,
      delaySeconds
    });
    setName('');
    setTag('Marketing');
    setIsModalOpen(false);
  };

  const filteredCampaigns = campaigns.filter(cmp => {
    if (tagFilter === 'All') return true;
    return (cmp.tag || 'Marketing') === tagFilter;
  });

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100">Campaign Worker Engine</h3>
          <p className="text-slate-400 text-sm">Background execution threads and delivery pacing</p>
        </div>
        <div className="flex items-center gap-3">
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
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            Create Campaign
          </button>
        </div>
      </div>

      {/* Campaigns List */}
      <div className="grid grid-cols-1 gap-5">
        {filteredCampaigns.map((cmp) => {
          const template = templates.find(t => t.id === cmp.templateId);
          const account = accounts.find(a => a.id === cmp.accountId);
          const progress = Math.round((cmp.sentCount / cmp.totalLeads) * 100);

          return (
            <div key={cmp.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className={`w-3 h-3 rounded-full ${
                      cmp.status === 'running' ? 'bg-emerald-500 animate-pulse' :
                      cmp.status === 'paused' ? 'bg-amber-500' : 'bg-slate-500'
                    }`} />
                    <h4 className="text-lg font-bold text-slate-100">{cmp.name}</h4>
                    <span className={`px-3 py-0.5 text-xs rounded-full font-semibold uppercase tracking-wider ${
                      cmp.status === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      cmp.status === 'paused' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {cmp.status}
                    </span>
                    <span className="px-2.5 py-0.5 text-[11px] rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium">
                      {cmp.tag || 'Marketing'}
                    </span>
                  </div>
                  <div className="flex items-center gap-6 text-xs text-slate-400 pt-1">
                    <span className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-amber-400" />
                      {cmp.templateIds && cmp.templateIds.length > 1 ? (
                        <span className="flex items-center gap-1 text-amber-300 font-semibold">
                          <Split className="w-3 h-3" /> A/B Test ({cmp.templateIds.length} templates)
                        </span>
                      ) : (
                        template?.name || 'Unknown Template'
                      )}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-purple-400" />
                      {account?.name || 'Unknown Account'}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-blue-400" />
                      {cmp.delaySeconds}s delay
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {cmp.status === 'running' ? (
                    <button
                      onClick={() => onUpdateCampaignStatus(cmp.id, 'paused')}
                      className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-xl text-sm font-medium transition-all"
                    >
                      <Pause className="w-4 h-4" />
                      Pause
                    </button>
                  ) : (
                    <button
                      onClick={() => onUpdateCampaignStatus(cmp.id, 'running')}
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-sm font-medium transition-all"
                    >
                      <Play className="w-4 h-4" />
                      Resume
                    </button>
                  )}
                  <button
                    onClick={() => onUpdateCampaignStatus(cmp.id, 'stopped')}
                    className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-xl text-sm font-medium transition-all"
                  >
                    <Square className="w-4 h-4" />
                    Stop
                  </button>
                </div>
              </div>

              {/* Progress */}
              <div className="space-y-2 pt-2 border-t border-slate-800/80">
                <div className="flex justify-between text-xs font-medium text-slate-300">
                  <span>Sent: <strong className="text-emerald-400">{cmp.sentCount}</strong> / {cmp.totalLeads} leads</span>
                  <span>Failed: <strong className="text-rose-400">{cmp.failedCount}</strong></span>
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

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100">Launch New Campaign</h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Campaign Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Q4 Enterprise Outreach"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Campaign Tag / Category
                </label>
                <select
                  value={tag}
                  onChange={(e) => setTag(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                >
                  <option value="Marketing">Marketing</option>
                  <option value="Onboarding">Onboarding</option>
                  <option value="Cold Outreach">Cold Outreach</option>
                  <option value="Sales">Sales</option>
                  <option value="Transactional">Transactional</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Email Templates (Select multiple for A/B Testing)
                </label>
                <div className="space-y-2 max-h-40 overflow-y-auto bg-slate-950 border border-slate-800 rounded-xl p-3">
                  {templates.map(t => {
                    const isSelected = selectedTemplateIds.includes(t.id);
                    return (
                      <div 
                        key={t.id}
                        onClick={() => toggleTemplate(t.id)}
                        className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all ${
                          isSelected ? 'bg-amber-500/10 border border-amber-500/30 text-amber-300' : 'hover:bg-slate-900 text-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}} // handled by parent div click
                            className="rounded border-slate-700 bg-slate-900 text-amber-500 focus:ring-0"
                          />
                          <span className="text-xs font-medium">{t.name}</span>
                        </div>
                        <span className="text-[11px] text-slate-500 uppercase">{t.category}</span>
                      </div>
                    );
                  })}
                </div>
                {selectedTemplateIds.length > 1 && (
                  <p className="text-[11px] text-amber-400 mt-1 flex items-center gap-1">
                    <Split className="w-3 h-3" /> A/B Testing Active: {selectedTemplateIds.length} templates will be rotated randomly per recipient.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Sender Account / Transport
                </label>
                <select
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                >
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({a.providerType.toUpperCase()})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Sending Delay Jitter (Seconds)
                </label>
                <input
                  type="number"
                  min={5}
                  max={120}
                  value={delaySeconds}
                  onChange={(e) => setDelaySeconds(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-sm font-semibold transition-all shadow-lg shadow-amber-500/20"
                >
                  Start Campaign Engine
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
