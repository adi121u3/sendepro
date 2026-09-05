import React from 'react';
import { Campaign, Account, Lead, ActivityLog, TabType } from '../types';
import { Send, Users, Server, CheckCircle2, AlertTriangle, ArrowUpRight, Play, Pause, Plus, TrendingUp } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

interface DashboardViewProps {
  campaigns: Campaign[];
  accounts: Account[];
  leads: Lead[];
  logs: ActivityLog[];
  onSelectTab: (tab: TabType) => void;
  onNewCampaign: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  campaigns,
  accounts,
  leads,
  logs,
  onSelectTab,
  onNewCampaign
}) => {
  const totalSent = campaigns.reduce((acc, c) => acc + c.sentCount, 0);
  const totalFailed = campaigns.reduce((acc, c) => acc + c.failedCount, 0);
  const successRate = totalSent + totalFailed > 0 ? ((totalSent / (totalSent + totalFailed)) * 100).toFixed(1) : '100';
  const activeAccountsCount = accounts.filter(a => a.status === 'active').length;

  const chartData = [
    { day: '6 days ago', successRate: 98.2, sent: 340 },
    { day: '5 days ago', successRate: 97.8, sent: 410 },
    { day: '4 days ago', successRate: 99.1, sent: 530 },
    { day: '3 days ago', successRate: 98.5, sent: 480 },
    { day: '2 days ago', successRate: 99.4, sent: 610 },
    { day: 'Yesterday', successRate: 98.9, sent: 570 },
    { day: 'Today', successRate: Number(successRate), sent: totalSent },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Welcome / Quick Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-900/80 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
        <div>
          <span className="px-3 py-1 text-xs rounded-full bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/20">
            Desktop Campaign Engine v2.4
          </span>
          <h3 className="text-2xl font-bold text-slate-100 mt-2">Welcome back, Alex</h3>
          <p className="text-slate-400 text-sm mt-1">
            Your SMTP transports and background workers are operating normally. 
            {campaigns.filter(c => c.status === 'running').length} campaign currently active.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onNewCampaign}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            Launch Campaign
          </button>
          <button
            onClick={() => onSelectTab('campaigns')}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-xl text-sm transition-all border border-slate-700"
          >
            View Engine
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-sm font-medium">Total Emails Sent</span>
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Send className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-100">{totalSent}</span>
            <span className="text-xs text-emerald-400 font-medium flex items-center">
              <ArrowUpRight className="w-3 h-3" /> +18% today
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Across all SMTP & API transports</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-sm font-medium">Delivery Success Rate</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-100">{successRate}%</span>
            <span className="text-xs text-emerald-400 font-medium">Optimal</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">{totalFailed} failed / {totalSent + totalFailed} total</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-sm font-medium">Active Leads</span>
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-100">{leads.length}</span>
            <span className="text-xs text-blue-400 font-medium">Ready</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Filtered and segmented lists</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-sm font-medium">Sender Accounts</span>
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Server className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-100">{activeAccountsCount}/{accounts.length}</span>
            <span className="text-xs text-purple-400 font-medium">Connected</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">SMTP & OAuth2 authenticated</p>
        </div>
      </div>

      {/* 7-Day Success Rate Chart Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-bold text-slate-100 text-base">7-Day Delivery Success Rate</h4>
              <p className="text-xs text-slate-400">Daily percentage of successfully delivered emails over the last week</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
            Average: 98.9%
          </span>
        </div>
        
        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="day" stroke="#64748b" textAnchor="end" tick={{ fontSize: 12 }} />
              <YAxis domain={[95, 100]} stroke="#64748b" tick={{ fontSize: 12 }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#f8fafc', fontSize: '12px' }}
                formatter={(value: any) => [`${value}%`, 'Success Rate']}
              />
              <Line type="monotone" dataKey="successRate" stroke="#f59e0b" strokeWidth={3} dot={{ fill: '#f59e0b', strokeWidth: 2, r: 5 }} activeDot={{ r: 8, fill: '#fbbf24' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Two Column Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Active Campaigns */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h4 className="font-bold text-slate-100 text-base">Campaign Execution Status</h4>
              <p className="text-xs text-slate-400">Background worker thread progress</p>
            </div>
            <button
              onClick={() => onSelectTab('campaigns')}
              className="text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors"
            >
              View All Campaigns →
            </button>
          </div>

          <div className="space-y-4 flex-1">
            {campaigns.map((cmp) => {
              const progress = Math.round((cmp.sentCount / cmp.totalLeads) * 100);
              return (
                <div key={cmp.id} className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${cmp.status === 'running' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                      <h5 className="font-semibold text-slate-100 text-sm">{cmp.name}</h5>
                    </div>
                    <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
                      cmp.status === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      cmp.status === 'paused' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {cmp.status.toUpperCase()}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs text-slate-400 font-medium">
                      <span>Progress: {cmp.sentCount} / {cmp.totalLeads} sent</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
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
        </div>

        {/* Recent Activity Logs */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h4 className="font-bold text-slate-100 text-base">Live Activity Feed</h4>
              <p className="text-xs text-slate-400">Recent transport events</p>
            </div>
            <button
              onClick={() => onSelectTab('activity')}
              className="text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors"
            >
              Full Logs →
            </button>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[340px]">
            {logs.map((log) => (
              <div key={log.id} className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className={`font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${
                    log.status === 'sent' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    log.status === 'failed' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                    'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {log.status}
                  </span>
                  <span className="text-slate-400 text-[11px]">{log.timestamp}</span>
                </div>
                <p className="text-slate-200 font-medium truncate">{log.leadEmail}</p>
                <p className="text-slate-400 text-[11px] truncate">{log.campaignName}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
