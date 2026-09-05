import React, { useState, useMemo } from 'react';
import { ActivityLog } from '../types';
import { Activity, CheckCircle2, AlertTriangle, Clock, Search, Filter, Copy, X, ExternalLink, ShieldCheck } from 'lucide-react';
import { ToastNotification } from './ToastNotification';

interface ActivityViewProps {
  logs: ActivityLog[];
}

export const ActivityView: React.FC<ActivityViewProps> = ({ logs }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('all');
  const [campaignFilter, setCampaignFilter] = useState(0);
  const [selectedLog, setSelectedLog] = useState<any | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const getLogActivityType = (log: any) => {
    const campaignId = log.campaignId || log.campaign_id;
    if (campaignId) {
      return `Campaign #${campaignId}`;
    }
    return 'Direct Email';
  };

  const campaignIds = useMemo(() => {
    const ids = new Set<number>();
    logs.forEach(l => {
      const cid = Number(l.campaignId || (l as any).campaign_id);
      if (cid) ids.add(cid);
    });
    return Array.from(ids).sort((a, b) => a - b);
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      const status = (log.status || '').toUpperCase();
      if (statusFilter !== 'All' && status !== statusFilter.toUpperCase()) {
        return false;
      }

      const hasCampaign = Boolean(log.campaignId || (log as any).campaign_id);
      if (typeFilter === 'direct' && hasCampaign) return false;
      if (typeFilter === 'campaign' && !hasCampaign) return false;

      const cid = Number(log.campaignId || (log as any).campaign_id || 0);
      if (campaignFilter > 0 && cid !== campaignFilter) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const combined = [
          log.leadEmail || '',
          log.accountName || '',
          String(log.campaignId || ''),
          log.status || '',
          log.errorMessage || '',
          log.timestamp || ''
        ].join(' ').toLowerCase();
        if (!combined.includes(q)) return false;
      }

      return true;
    });
  }, [logs, searchQuery, statusFilter, typeFilter, campaignFilter]);

  const stats = useMemo(() => {
    const total = logs.length;
    const sent = logs.filter(l => ['sent', 'success', 'delivered'].includes(l.status?.toLowerCase())).length;
    const failed = logs.filter(l => ['failed', 'error', 'permanent_error'].includes(l.status?.toLowerCase())).length;
    const campaigns = logs.filter(l => Boolean(l.campaignId || (l as any).campaign_id)).length;
    return { total, sent, failed, campaigns };
  }, [logs]);

  const copyDetailsToClipboard = (log: any) => {
    const text = 
      `Log ID: ${log.id || 'N/A'}\n` +
      `Date / Time: ${log.timestamp || 'N/A'}\n` +
      `Type: ${getLogActivityType(log)}\n` +
      `Recipient: ${log.leadEmail || log.lead_email || 'N/A'}\n` +
      `Account: ${log.accountName || log.account_name || 'N/A'}\n` +
      `Provider: ${(log.providerType || log.provider_type || 'SMTP').toUpperCase()}\n` +
      `Status: ${log.status || 'N/A'}\n` +
      `Provider Message ID: ${log.providerMessageId || log.provider_message_id || 'N/A'}\n` +
      `Error Code: ${log.errorCode || log.error_code || 'N/A'}\n` +
      `Message: ${log.errorMessage || log.message || 'N/A'}`;

    navigator.clipboard.writeText(text);
    showToast('Log details copied to clipboard');
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto relative">
      {/* Toast Notification */}
      {toastMessage && (
        <ToastNotification message={toastMessage} onClose={() => setToastMessage(null)} />
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-2xl font-bold text-slate-100 tracking-tight">Delivery Logs & Audit Trail</h3>
          <p className="text-slate-400 text-sm">Real-time enterprise record of sent, failed, and queued messages across accounts</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div id="SummaryCard" className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Total Events</div>
          <div className="text-2xl font-bold text-slate-100 mt-2">{stats.total}</div>
        </div>
        <div id="SummaryCard" className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Successful Dispatches</div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">{stats.sent}</div>
        </div>
        <div id="SummaryCard" className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Failed Deliveries</div>
          <div className="text-2xl font-bold text-rose-400 mt-2">{stats.failed}</div>
        </div>
        <div id="SummaryCard" className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider">Campaign Dispatches</div>
          <div className="text-2xl font-bold text-indigo-400 mt-2">{stats.campaigns}</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap gap-4 items-center justify-between">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          <div className="relative min-w-[260px] flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input 
              type="text"
              placeholder="Search logs by recipient, account, status..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="All">All Statuses</option>
            <option value="sent">SENT</option>
            <option value="failed">FAILED</option>
            <option value="queued">QUEUED</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Types</option>
            <option value="direct">Direct Email</option>
            <option value="campaign">Campaign Email</option>
          </select>

          <select
            value={campaignFilter}
            onChange={(e) => setCampaignFilter(Number(e.target.value))}
            className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value={0}>All Campaigns</option>
            {campaignIds.map(cid => (
              <option key={cid} value={cid}>Campaign #{cid}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/50 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-4 px-6">Status</th>
                <th className="py-4 px-6">Recipient</th>
                <th className="py-4 px-6">Type</th>
                <th className="py-4 px-6">Sender Account</th>
                <th className="py-4 px-6">Error / Message</th>
                <th className="py-4 px-6 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {filteredLogs.map((log) => {
                const status = (log.status || 'sent').toLowerCase();
                const isSuccess = ['sent', 'success', 'delivered'].includes(status);
                const isFailed = ['failed', 'error', 'permanent_error'].includes(status);

                return (
                  <tr 
                    key={log.id} 
                    onClick={() => setSelectedLog(log)}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                  >
                    <td className="py-4 px-6">
                      <span className={`px-2.5 py-1 text-xs rounded-full font-semibold uppercase tracking-wider ${
                        isSuccess ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        isFailed ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                        'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="py-4 px-6 font-mono text-xs text-slate-200">{log.leadEmail}</td>
                    <td className="py-4 px-6 font-medium text-slate-300 text-xs">{getLogActivityType(log)}</td>
                    <td className="py-4 px-6 text-slate-400 text-xs">{log.accountName}</td>
                    <td className="py-4 px-6 text-xs text-rose-400 font-mono truncate max-w-xs">{log.errorMessage || '—'}</td>
                    <td className="py-4 px-6 text-right text-xs text-slate-400">{log.timestamp}</td>
                  </tr>
                );
              })}
              {filteredLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    No activity logs match your filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/45">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-lg font-bold text-slate-100">Audit Log Details</h4>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      ['sent', 'success', 'delivered'].includes((selectedLog.status || '').toLowerCase())
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>{selectedLog.status || 'unknown'}</span>
                  </div>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">Event ID: {selectedLog.id}</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-slate-100 p-2 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5 flex-1">
              <div id="InfoPanel" className="bg-slate-950/70 border border-slate-800 rounded-xl p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Log ID</div>
                  <div id="InfoValue" className="text-sm font-medium text-slate-200 mt-1">{selectedLog.id}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Date / Time</div>
                  <div id="InfoValue" className="text-sm font-medium text-slate-200 mt-1">{selectedLog.timestamp}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Type</div>
                  <div id="InfoValue" className="text-sm font-medium text-slate-200 mt-1">{getLogActivityType(selectedLog)}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Recipient</div>
                  <div id="InfoValue" className="text-sm font-mono text-slate-200 mt-1">{selectedLog.leadEmail || selectedLog.lead_email}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Account</div>
                  <div id="InfoValue" className="text-sm font-medium text-slate-200 mt-1">{selectedLog.accountName || selectedLog.account_name}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Provider</div>
                  <div id="InfoValue" className="text-sm font-medium text-slate-200 mt-1 uppercase">{selectedLog.providerType || selectedLog.provider_type || 'SMTP'}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Provider Message ID</div>
                  <div id="InfoValue" className="text-sm font-mono text-slate-200 mt-1">{selectedLog.providerMessageId || selectedLog.provider_message_id || 'N/A'}</div>
                </div>
                <div>
                  <div id="InfoKey" className="text-xs text-slate-400 uppercase tracking-wider">Error Code</div>
                  <div id="InfoValue" className="text-sm font-mono text-rose-400 mt-1">{selectedLog.errorCode || selectedLog.error_code || 'N/A'}</div>
                </div>
              </div>

              <div>
                <div id="SectionTitle" className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Server Response / Error Message</div>
                <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                  {selectedLog.errorMessage || selectedLog.message || 'No additional message recorded.'}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-between bg-slate-950/50">
              <button
                onClick={() => copyDetailsToClipboard(selectedLog)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium flex items-center space-x-2 transition-colors"
              >
                <Copy className="w-4 h-4" />
                <span>Copy Details</span>
              </button>

              <button
                id="PrimaryButton"
                onClick={() => setSelectedLog(null)}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors shadow-lg shadow-indigo-600/20"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
