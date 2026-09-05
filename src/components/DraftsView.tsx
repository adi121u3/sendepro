import React, { useState, useEffect, useCallback } from 'react';
import { Draft, Account } from '../types';
import { Mail, Plus, Trash2, RefreshCw, Edit3, Clock, ArrowUpRight, Sliders, Send } from 'lucide-react';
import { ComposeWindow, ComposeSession } from './ComposeWindow';
import * as api from '../services/api';

interface DraftsViewProps {
  accounts: Account[];
}

export const DraftsView: React.FC<DraftsViewProps> = ({ accounts }) => {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [activeSessions, setActiveSessions] = useState<ComposeSession[]>([]);
  const [maxZIndex, setMaxZIndex] = useState(100);

  const loadDrafts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.fetchDrafts();
      setDrafts(data);
      if (data.length > 0 && selectedIndex >= data.length) {
        setSelectedIndex(data.length - 1);
      }
    } catch (e) {
      console.error("Failed to load drafts:", e);
    } finally {
      setLoading(false);
    }
  }, [selectedIndex]);

  useEffect(() => {
    loadDrafts();
  }, [loadDrafts]);

  const openNewCompose = async (draft?: Draft | null) => {
    const windowId = Math.random().toString(36).substring(2, 9);
    const count = activeSessions.length;
    const offset = count * 35;

    let attachmentsArr: string[] = [];
    if (draft && draft.attachments) {
      try {
        const parsed = JSON.parse(draft.attachments);
        attachmentsArr = Array.isArray(parsed) ? parsed : draft.attachments.split(',').filter(Boolean);
      } catch {
        attachmentsArr = draft.attachments.split(',').filter(Boolean);
      }
    }

    // Load Email Signature from settings for every NEW message
    let signature = '';
    let defaultSenderName = accounts[0]?.name || 'Professional Sender';
    if (!draft) {
      try {
        const settings = await api.fetchSettings();
        const map: Record<string, string> = {};
        if (Array.isArray(settings)) {
          settings.forEach((item: any) => {
            if (item?.key) map[item.key] = item.value ?? '';
          });
        }
        signature = (map.email_signature || '').trim();
        if (map.sender_name?.trim()) defaultSenderName = map.sender_name.trim();
      } catch {
        /* settings optional */
      }
    }

    let body = draft?.body || '';
    if (!draft && signature) {
      // Always include signature on new compose (plain text area)
      body = `\n\n--\n${signature}`;
    }

    const newSession: ComposeSession = {
      windowId,
      draftId: draft?.id,
      fromName: draft?.from_name || defaultSenderName,
      senderAccountId: draft?.senderAccountId || draft?.sender_account_id || accounts[0]?.id || '',
      recipient: draft?.recipient || '',
      cc: '',
      bcc: '',
      subject: draft?.subject || '',
      body,
      attachments: attachmentsArr,
      isMaximized: false,
      isMinimized: false,
      position: { x: 80 + offset, y: 80 + offset },
      zIndex: maxZIndex + 1,
      isDirty: false,
      saving: false,
      saveSuccessMsg: '',
      sending: false,
      sendSuccess: false,
      sendError: '',
    };

    setMaxZIndex(prev => prev + 1);
    setActiveSessions(prev => [...prev, newSession]);
  };

  const handleUpdateSession = (windowId: string, updates: Partial<ComposeSession>) => {
    setActiveSessions(prev => prev.map(s => s.windowId === windowId ? { ...s, ...updates } : s));
  };

  const handleCloseSession = (windowId: string) => {
    setActiveSessions(prev => prev.filter(s => s.windowId !== windowId));
  };

  const handleBringToFront = (windowId: string) => {
    const nextZ = maxZIndex + 1;
    setMaxZIndex(nextZ);
    setActiveSessions(prev => prev.map(s => s.windowId === windowId ? { ...s, zIndex: nextZ, isMinimized: false } : s));
  };

  const handleDelete = async (id: string | number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!confirm('Are you sure you want to delete this draft?')) return;
    try {
      await api.deleteDraft(id);
      setDrafts(drafts.filter(d => d.id !== id));
      if (selectedIndex >= drafts.length - 1 && selectedIndex > 0) {
        setSelectedIndex(selectedIndex - 1);
      }
    } catch (e: any) {
      alert(e.message || 'Failed to delete draft');
    }
  };

  // Keyboard navigation for data grid
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (activeSessions.length > 0 || drafts.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, drafts.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (drafts[selectedIndex]) {
          openNewCompose(drafts[selectedIndex]);
        }
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
        e.preventDefault();
        if (drafts[selectedIndex]) {
          handleDelete(drafts[selectedIndex].id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [drafts, selectedIndex, activeSessions.length]);

  const handleDraftSaved = (saved: Draft) => {
    setDrafts(prev => {
      const exists = prev.find(d => d.id === saved.id);
      if (exists) {
        return prev.map(d => d.id === saved.id ? saved : d);
      } else {
        return [saved, ...prev];
      }
    });
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto min-h-screen text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-3">
            <Mail className="w-7 h-7 text-amber-500" />
            Email Composer & Saved Drafts
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Open multiple independent draggable compose windows simultaneously. Changes in Window A never modify Window B. Persists to <code className="text-teal-400">/api/drafts</code>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadDrafts}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-sm transition-all border border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Drafts
          </button>
          <button
            onClick={() => openNewCompose(null)}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            New Compose
          </button>
        </div>
      </div>

      {/* Card 1: Overview & Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex items-center gap-4">
          <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
            <Mail className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-100">{drafts.length}</div>
            <div className="text-xs text-slate-400 font-medium">Saved Drafts in Database</div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex items-center gap-4">
          <div className="p-3 bg-teal-500/10 text-teal-400 rounded-xl border border-teal-500/20">
            <Send className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-100">{activeSessions.length}</div>
            <div className="text-xs text-slate-400 font-medium">Active Compose Windows Open</div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex items-center gap-4">
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-100">Multi-Window V2.0</div>
            <div className="text-xs text-slate-400 font-medium">Independent State Engine</div>
          </div>
        </div>
      </div>

      {/* Card 2: Saved Drafts Data Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Mail className="w-5 h-5 text-amber-500" />
              Drafts Repository Database
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Double click any draft to open an independent draggable compose window.</p>
          </div>
          <button
            onClick={() => openNewCompose(null)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-xs transition-colors border border-slate-700 flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5 text-amber-400" />
            Quick Compose
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider bg-slate-950/20">
                <th className="py-3 px-6">Subject</th>
                <th className="py-3 px-6">Recipient</th>
                <th className="py-3 px-6">Preview Body</th>
                <th className="py-3 px-6">Last Updated</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {drafts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-16 text-center text-slate-400">
                    <Mail className="w-12 h-12 text-slate-700 mx-auto mb-3 animate-pulse" />
                    <p className="font-semibold text-slate-300 text-base">No saved drafts found in database</p>
                    <p className="text-xs text-slate-400 mt-1">Click "New Compose" above to launch multiple independent floating editors.</p>
                  </td>
                </tr>
              ) : (
                drafts.map((draft, idx) => {
                  const isSelected = selectedIndex === idx;
                  return (
                    <tr
                      key={draft.id}
                      onClick={() => setSelectedIndex(idx)}
                      onDoubleClick={() => openNewCompose(draft)}
                      className={`cursor-pointer transition-colors hover:bg-slate-800/40 ${
                        isSelected ? 'bg-amber-500/10 border-l-4 border-amber-500' : ''
                      }`}
                    >
                      <td className="py-4 px-6 font-semibold text-slate-200">
                        {draft.subject || '(No Subject)'}
                      </td>
                      <td className="py-4 px-6 text-slate-300 text-xs">
                        {draft.recipient || 'No recipient'}
                      </td>
                      <td className="py-4 px-6 text-slate-400 text-xs max-w-xs truncate">
                        {draft.body || 'Empty body...'}
                      </td>
                      <td className="py-4 px-6 text-slate-400 text-xs whitespace-nowrap">
                        {draft.updated_at ? new Date(draft.updated_at).toLocaleString() : 'Just now'}
                      </td>
                      <td className="py-4 px-6 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); openNewCompose(draft); }}
                            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-lg text-xs transition-colors flex items-center gap-1"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5 text-amber-400" />
                            Open
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleDelete(draft.id, e)}
                            className="p-1.5 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg transition-colors"
                            title="Delete Draft"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Multiple Independent Floating Compose Windows */}
      {activeSessions.map(session => (
        <ComposeWindow
          key={session.windowId}
          session={session}
          accounts={accounts}
          onUpdateSession={handleUpdateSession}
          onClose={handleCloseSession}
          onBringToFront={handleBringToFront}
          onDraftSaved={handleDraftSaved}
        />
      ))}
    </div>
  );
};
