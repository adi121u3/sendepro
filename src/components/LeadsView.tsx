import React, { useState } from 'react';
import { Lead } from '../types';
import { Users, Search, Plus, Upload, Trash2, Copy, CheckSquare, Square, RefreshCw } from 'lucide-react';
import * as api from '../services/api';

interface LeadsViewProps {
  leads: Lead[];
  onAddLead: (lead: Omit<Lead, 'id' | 'createdAt'>) => void;
  onDeleteLead: (id: string) => void;
  onRefresh?: () => void;
}

export const LeadsView: React.FC<LeadsViewProps> = ({ leads, onAddLead, onDeleteLead, onRefresh }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [importTab, setImportTab] = useState<'bulk' | 'file' | 'single'>('bulk');
  const [editingLeadId, setEditingLeadId] = useState<string | null>(null);

  // Single form state
  const [receiverName, setReceiverName] = useState('');
  const [receiverEmail, setReceiverEmail] = useState('');
  const [senderName, setSenderName] = useState('');
  const [position, setPosition] = useState('');
  const [company, setCompany] = useState('');

  // Bulk paste state (5 lines per lead)
  const [bulkText, setBulkText] = useState(
    'Elaina Ayala\nelaina.ayala@adirondackbasement.com\nTodd Bumbarger\nSales Manager\nAdirondack Basement Systems'
  );

  const filteredLeads = leads.filter(l => 
    l.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (l.firstName && l.firstName.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (l.company && l.company.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredLeads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredLeads.map(l => l.id));
    }
  };

  const toggleSelectOne = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleSingleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!receiverEmail.trim()) return;
    const nameParts = receiverName.trim().split(' ');
    const firstName = nameParts[0] || 'Valued';
    const lastName = nameParts.slice(1).join(' ') || 'Lead';

    try {
      if (editingLeadId) {
        await api.updateLead(editingLeadId, {
          first_name: firstName,
          last_name: lastName,
          email: receiverEmail,
          company,
          position,
          sender_name: senderName,
          sender_full_name: senderName
        });
      } else {
        await api.createLead({
          firstName,
          lastName,
          email: receiverEmail,
          company,
          position,
          senderName,
          senderFullName: senderName
        });
      }
      setReceiverName('');
      setReceiverEmail('');
      setSenderName('');
      setPosition('');
      setCompany('');
      setEditingLeadId(null);
      setIsImportOpen(false);
      if (onRefresh) onRefresh();
      else window.location.reload();
    } catch (e: any) {
      alert(e.message || "Failed to save lead");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await api.importLeadsFile(file);
      alert(`Successfully imported ${res.length} leads from file!`);
      setIsImportOpen(false);
      if (onRefresh) onRefresh();
      else window.location.reload();
    } catch (e: any) {
      alert(e.message || "Failed to import file");
    }
  };

  const handleBulkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const lines = bulkText.split('\n').map(l => l.trim()).filter(Boolean);
    const parsedLeads = [];

    // Group by 5 lines: [Receiver Name, Receiver Email, Sender Name, Position, Company]
    for (let i = 0; i < lines.length; i += 5) {
      const rName = lines[i] || 'Valued Lead';
      const rEmail = lines[i + 1] || '';
      const sName = lines[i + 2] || 'Default Sender';
      const pos = lines[i + 3] || 'Manager';
      const comp = lines[i + 4] || 'Company';

      if (rEmail && rEmail.includes('@')) {
        const nameParts = rName.split(' ');
        parsedLeads.push({
          email: rEmail,
          first_name: nameParts[0] || 'Valued',
          last_name: nameParts.slice(1).join(' ') || 'Lead',
          company: comp,
          position: pos,
          sender_name: sName,
          sender_full_name: sName
        });
      }
    }

    if (parsedLeads.length === 0) {
      alert("No valid leads found. Please ensure format uses exactly 5 lines per lead (Receiver Name, Receiver Email, Sender Name, Position, Company).");
      return;
    }

    try {
      await api.bulkCreateLeads(parsedLeads);
      setIsImportOpen(false);
      if (onRefresh) onRefresh();
      else window.location.reload();
    } catch (e: any) {
      alert(e.message || "Failed to bulk import leads");
    }
  };

  const handleDuplicateSelected = async () => {
    if (selectedIds.length === 0) {
      alert("Please select at least one lead to duplicate.");
      return;
    }
    try {
      for (const id of selectedIds) {
        await api.duplicateLead(Number(id));
      }
      setSelectedIds([]);
      if (onRefresh) onRefresh();
      else window.location.reload();
    } catch (e: any) {
      alert(e.message || "Failed to duplicate leads");
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.length === 0) {
      alert("Please select at least one lead to delete.");
      return;
    }
    if (!confirm(`Are you sure you want to delete ${selectedIds.length} selected leads?`)) return;
    try {
      for (const id of selectedIds) {
        await api.deleteLead(Number(id));
        onDeleteLead(id);
      }
      setSelectedIds([]);
      if (onRefresh) onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to delete leads");
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Are you sure you want to clear ALL leads? This action cannot be undone.")) return;
    try {
      await api.clearLeads();
      if (onRefresh) onRefresh();
      else window.location.reload();
    } catch (e: any) {
      alert(e.message || "Failed to clear leads");
    }
  };

  const handleDeduplicate = async () => {
    try {
      const res = await api.deduplicateLeads();
      alert(res.message || "Deduplication completed.");
      if (onRefresh) onRefresh();
      else window.location.reload();
    } catch (e: any) {
      alert(e.message || "Failed to deduplicate leads");
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-full mx-auto bg-slate-950 min-h-screen text-slate-100">
      {/* System status top line */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>System Ready</span>
        </div>
        <span>Administrator</span>
      </div>

      {/* Header & Actions Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">Leads & Contacts Manager</h2>
        
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsImportOpen(true)}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-xs transition-all shadow-md shadow-amber-500/20"
          >
            Import / Add Leads
          </button>
          <button
            onClick={handleDuplicateSelected}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg text-xs transition-all border border-slate-700"
          >
            Duplicate Lead
          </button>
          <button
            onClick={() => {
              if (selectedIds.length !== 1) {
                alert("Please select exactly 1 lead to edit.");
                return;
              }
              const lead = leads.find(l => l.id === selectedIds[0]);
              if (lead) {
                setEditingLeadId(lead.id);
                setReceiverName(`${lead.firstName} ${lead.lastName}`);
                setReceiverEmail(lead.email);
                setSenderName(lead.senderName || '');
                setPosition(lead.position || '');
                setCompany(lead.company || '');
                setImportTab('single');
                setIsImportOpen(true);
              }
            }}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg text-xs transition-all border border-slate-700"
          >
            Edit Selected
          </button>
          <button
            onClick={handleDeleteSelected}
            className="px-3.5 py-2 bg-rose-950/60 hover:bg-rose-900/60 text-rose-300 font-medium rounded-lg text-xs transition-all border border-rose-800/60"
          >
            Delete Selected
          </button>
          <button
            onClick={handleClearAll}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-lg text-xs transition-all border border-slate-700"
          >
            Clear All Leads
          </button>
          <button
            onClick={handleDeduplicate}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-lg text-xs transition-all border border-slate-700"
          >
            Deduplicate
          </button>
        </div>

        <div className="relative w-full lg:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search leads by email, name..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
          />
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/70 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4 w-10 text-center">
                  <button onClick={toggleSelectAll} className="text-slate-400 hover:text-slate-200">
                    {selectedIds.length > 0 && selectedIds.length === filteredLeads.length ? (
                      <CheckSquare className="w-4 h-4 text-amber-500" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>
                <th className="py-3 px-4">Receiver Name</th>
                <th className="py-3 px-4">Receiver Email</th>
                <th className="py-3 px-4">Sender Name</th>
                <th className="py-3 px-4">Sender Full Name</th>
                <th className="py-3 px-4">Position</th>
                <th className="py-3 px-4">Company</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-xs font-mono">
              {filteredLeads.map((lead, idx) => {
                const isSelected = selectedIds.includes(lead.id);
                return (
                  <tr key={lead.id} className={`hover:bg-slate-800/30 transition-colors ${isSelected ? 'bg-amber-500/10' : ''}`}>
                    <td className="py-3 px-4 text-center">
                      <button onClick={() => toggleSelectOne(lead.id)} className="text-slate-400 hover:text-slate-200">
                        {isSelected ? <CheckSquare className="w-4 h-4 text-amber-500" /> : <Square className="w-4 h-4" />}
                      </button>
                    </td>
                    <td className="py-3 px-4 font-sans font-semibold text-slate-200">
                      {lead.firstName} {lead.lastName}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{lead.email}</td>
                    <td className="py-3 px-4 text-amber-400/90">{lead.senderName || 'Default'}</td>
                    <td className="py-3 px-4 text-slate-300">{lead.senderFullName || lead.senderName || 'Default'}</td>
                    <td className="py-3 px-4 text-slate-400 font-sans">{lead.position}</td>
                    <td className="py-3 px-4 text-slate-300 font-sans">{lead.company}</td>
                  </tr>
                );
              })}
              {filteredLeads.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 font-sans text-xs">
                    No leads found. Click "Import / Add Leads" to add recipients and rotate sender names.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Import & Add Leads Modal */}
      {isImportOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-xl overflow-hidden shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Upload className="w-4 h-4 text-amber-500" />
                Import & Add Leads
              </h3>
              <button onClick={() => setIsImportOpen(false)} className="text-slate-400 hover:text-slate-200 font-bold">✕</button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-slate-800 bg-slate-950/50 px-6 pt-2 gap-2">
              <button
                onClick={() => setImportTab('bulk')}
                className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all ${
                  importTab === 'bulk' ? 'bg-slate-900 text-amber-400 border-t border-x border-slate-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Bulk Paste
              </button>
              <button
                onClick={() => setImportTab('file')}
                className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all ${
                  importTab === 'file' ? 'bg-slate-900 text-amber-400 border-t border-x border-slate-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                File Import
              </button>
              <button
                onClick={() => setImportTab('single')}
                className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all ${
                  importTab === 'single' ? 'bg-slate-900 text-amber-400 border-t border-x border-slate-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Single Form
              </button>
            </div>

            <div className="p-6">
              {importTab === 'bulk' && (
                <form onSubmit={handleBulkSubmit} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Paste leads in bulk using exactly 5 lines per lead (Receiver Name, Receiver Email, Sender Name, Position, Company):
                    </label>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400 mb-2">
                      Example:<br/>
                      ========================<br/>
                      Elaina Ayala<br/>
                      elaina.ayala@adirondackbasement.com<br/>
                      Todd Bumbarger<br/>
                      Sales Manager<br/>
                      Adirondack Basement Systems
                    </div>
                    <textarea
                      rows={8}
                      value={bulkText}
                      onChange={(e) => setBulkText(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-100 text-xs font-mono focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                    <button
                      type="button"
                      onClick={() => setIsImportOpen(false)}
                      className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-all"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-semibold transition-all shadow-lg shadow-amber-500/20"
                    >
                      Import Pasted Leads
                    </button>
                  </div>
                </form>
              )}

              {importTab === 'file' && (
                <div className="space-y-6 py-6 text-center">
                  <label className="border-2 border-dashed border-slate-800 rounded-xl p-8 hover:border-amber-500/50 transition-colors cursor-pointer bg-slate-950/50 block">
                    <Upload className="w-10 h-10 text-amber-500 mx-auto mb-3" />
                    <span className="text-xs font-semibold text-slate-200 block">Click to upload CSV or Excel spreadsheet</span>
                    <span className="text-[11px] text-slate-500 mt-1 block">Supports columns: Receiver Name, Email, Sender Name, Position, Company</span>
                    <input type="file" accept=".csv, .xlsx, .xls, .txt" onChange={handleFileUpload} className="hidden" />
                  </label>
                  <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                    <button
                      type="button"
                      onClick={() => setIsImportOpen(false)}
                      className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}

              {importTab === 'single' && (
                <form onSubmit={handleSingleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Receiver Name</label>
                      <input
                        type="text"
                        required
                        value={receiverName}
                        onChange={(e) => setReceiverName(e.target.value)}
                        placeholder="John Doe"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Receiver Email</label>
                      <input
                        type="email"
                        required
                        value={receiverEmail}
                        onChange={(e) => setReceiverEmail(e.target.value)}
                        placeholder="john@example.com"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Sender Name (Rotated)</label>
                      <input
                        type="text"
                        value={senderName}
                        onChange={(e) => setSenderName(e.target.value)}
                        placeholder="Akeem One"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Position / Title</label>
                      <input
                        type="text"
                        value={position}
                        onChange={(e) => setPosition(e.target.value)}
                        placeholder="Manager"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Company</label>
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="Acme Inc"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                    <button
                      type="button"
                      onClick={() => setIsImportOpen(false)}
                      className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-semibold shadow-lg shadow-amber-500/20"
                    >
                      Save Lead
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
