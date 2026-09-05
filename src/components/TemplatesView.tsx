import React, { useState, useRef } from 'react';
import { EmailTemplate } from '../types';
import { FileText, Plus, Eye, Code, Edit3, Trash2, Download, Upload, CheckSquare, Square } from 'lucide-react';

interface TemplatesViewProps {
  templates: EmailTemplate[];
  onAddTemplate: (tpl: Omit<EmailTemplate, 'id' | 'updatedAt'>) => void;
  onDeleteTemplate: (id: string) => void;
}

export const TemplatesView: React.FC<TemplatesViewProps> = ({ templates, onAddTemplate, onDeleteTemplate }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<EmailTemplate | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [confirmDeleteModal, setConfirmDeleteModal] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState('Outbound');
  const [bodyHtml, setBodyHtml] = useState('<p>Hi {{FirstName}},</p>\n<p>I wanted to reach out regarding {{Company}}...</p>\n<p>Best regards,<br>Alex</p>');
  const [activeField, setActiveField] = useState<'subject' | 'body'>('body');

  const insertMergeTag = (tag: string) => {
    if (activeField === 'subject') {
      setSubject(prev => prev + ' ' + tag);
    } else {
      setBodyHtml(prev => prev + ' ' + tag);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onAddTemplate({
      name,
      subject,
      category,
      bodyHtml
    });
    setName('');
    setSubject('');
    setIsModalOpen(false);
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === templates.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(templates.map(t => t.id));
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleExportSelected = () => {
    const itemsToExport = selectedIds.length > 0 
      ? templates.filter(t => selectedIds.includes(t.id))
      : templates;

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(itemsToExport, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `email_templates_export_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        if (Array.isArray(json)) {
          let count = 0;
          json.forEach(tpl => {
            if (tpl.name && tpl.subject && tpl.bodyHtml) {
              onAddTemplate({
                name: tpl.name,
                subject: tpl.subject,
                category: tpl.category || 'Imported',
                bodyHtml: tpl.bodyHtml
              });
              count++;
            }
          });
          alert(`Successfully imported ${count} templates!`);
        } else {
          alert('Invalid JSON format: Expected an array of templates.');
        }
      } catch (err) {
        console.error("Failed to parse JSON:", err);
        alert('Failed to parse template JSON file.');
      }
      if (fileInputRef.current) fileInputRef.current.value = '';
    };
    reader.readAsText(file);
  };

  const executeBulkDelete = () => {
    selectedIds.forEach(id => onDeleteTemplate(id));
    setSelectedIds([]);
    setConfirmDeleteModal(false);
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        accept=".json" 
        className="hidden" 
      />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100">Email Templates & Personalization</h3>
          <p className="text-slate-400 text-sm">Create Jinja-style reusable templates with dynamic lead variables</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleImportClick}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-xl text-sm transition-all border border-slate-700"
          >
            <Upload className="w-4 h-4 text-amber-400" />
            Import JSON
          </button>
          <button
            onClick={handleExportSelected}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-xl text-sm transition-all border border-slate-700"
          >
            <Download className="w-4 h-4 text-amber-400" />
            {selectedIds.length > 0 ? `Export Selected (${selectedIds.length})` : 'Export All JSON'}
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            Create Template
          </button>
        </div>
      </div>

      {/* Bulk Action Bar */}
      {selectedIds.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-3">
            <span className="w-6 h-6 rounded-full bg-amber-500 text-slate-950 font-bold text-xs flex items-center justify-center">
              {selectedIds.length}
            </span>
            <span className="text-slate-200 text-sm font-medium">Templates selected</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSelectedIds([])}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 font-medium"
            >
              Deselect All
            </button>
            <button
              onClick={() => setConfirmDeleteModal(true)}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-rose-500 hover:bg-rose-400 text-white text-xs font-semibold rounded-lg transition-all shadow-md shadow-rose-500/20"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete Selected
            </button>
          </div>
        </div>
      )}

      {/* Select All Toggle Bar */}
      {templates.length > 0 && (
        <div className="flex items-center justify-between px-2 text-xs text-slate-400">
          <button 
            onClick={toggleSelectAll}
            className="flex items-center gap-2 hover:text-slate-200 font-medium transition-colors"
          >
            {selectedIds.length === templates.length ? (
              <CheckSquare className="w-4 h-4 text-amber-400" />
            ) : (
              <Square className="w-4 h-4 text-slate-500" />
            )}
            Select All ({templates.length} templates)
          </button>
          <span>{selectedIds.length} selected</span>
        </div>
      )}

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map((tpl) => {
          const isSelected = selectedIds.includes(tpl.id);
          return (
            <div 
              key={tpl.id} 
              className={`bg-slate-900 border rounded-2xl p-6 shadow-sm space-y-4 flex flex-col justify-between transition-all ${
                isSelected ? 'border-amber-500/60 ring-2 ring-amber-500/20 bg-slate-900/90' : 'border-slate-800'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <button 
                      onClick={() => toggleSelect(tpl.id)}
                      className="text-slate-400 hover:text-amber-400 transition-colors"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-amber-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-600" />
                      )}
                    </button>
                    <span className="px-2.5 py-1 text-xs rounded-full bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/20">
                      {tpl.category}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">{tpl.updatedAt}</span>
                </div>
                <div>
                  <h4 className="font-bold text-slate-100 text-base">{tpl.name}</h4>
                  <p className="text-xs text-slate-400 font-mono mt-1 truncate">Subject: {tpl.subject}</p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-xs text-slate-300 font-mono line-clamp-3">
                  {tpl.bodyHtml}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <button
                  onClick={() => setPreviewTemplate(tpl)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-all border border-slate-700"
                >
                  <Eye className="w-3.5 h-3.5 text-amber-400" />
                  Preview
                </button>
                <button
                  onClick={() => onDeleteTemplate(tpl.id)}
                  className="p-2 text-slate-400 hover:text-rose-400 transition-colors"
                  title="Delete template"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Confirm Delete Modal */}
      {confirmDeleteModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-100">Confirm Bulk Deletion</h3>
            <p className="text-slate-300 text-sm">
              Are you sure you want to delete <strong className="text-amber-400">{selectedIds.length}</strong> selected templates? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setConfirmDeleteModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
              >
                Cancel
              </button>
              <button
                onClick={executeBulkDelete}
                className="px-5 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-white text-sm font-semibold transition-all shadow-lg shadow-rose-500/20"
              >
                Delete {selectedIds.length} Templates
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100">Create Email Template</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-200 font-semibold">✕</button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Template Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Cold Outreach v2"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Category</label>
                  <input
                    type="text"
                    required
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              {/* Merge Tags Helper Toolbar */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">Quick Insert Merge Tags (Active Field: <strong className="text-amber-400 uppercase">{activeField}</strong>)</span>
                  <span className="text-[11px]">Click tag to insert</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {['{{FirstName}}', '{{LastName}}', '{{Company}}', '{{Position}}', '{{Email}}'].map(tag => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => insertMergeTag(tag)}
                      className="px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg text-xs font-mono transition-all"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Subject Line</label>
                <input
                  type="text"
                  required
                  value={subject}
                  onFocus={() => setActiveField('subject')}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. Scaling {{Company}} infrastructure"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">HTML Body</label>
                  <span className="text-[11px] text-amber-400 font-medium">Click tags above to insert</span>
                </div>
                <textarea
                  rows={8}
                  required
                  value={bodyHtml}
                  onFocus={() => setActiveField('body')}
                  onChange={(e) => setBodyHtml(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-100 text-xs font-mono focus:outline-none focus:border-amber-500"
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
                  Save Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewTemplate && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100">Template Preview: {previewTemplate.name}</h3>
              <button onClick={() => setPreviewTemplate(null)} className="text-slate-400 hover:text-slate-200 font-semibold">✕</button>
            </div>

            <div className="space-y-4">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-1">
                <span className="text-slate-400 font-semibold">Subject:</span>
                <p className="text-slate-200 font-mono">{previewTemplate.subject.replace('{{Company}}', 'Acme Inc')}</p>
              </div>

              <div className="p-5 bg-white text-slate-900 rounded-xl shadow-inner space-y-3">
                <div className="text-[11px] text-slate-500 border-b pb-2 font-mono">Rendered with sample lead (Sarah Jenkins / Acme Inc)</div>
                <div 
                  className="text-sm prose"
                  dangerouslySetInnerHTML={{ 
                    __html: previewTemplate.bodyHtml
                      .replace(/{{FirstName}}/g, 'Sarah')
                      .replace(/{{LastName}}/g, 'Jenkins')
                      .replace(/{{Company}}/g, 'Acme Inc')
                      .replace(/{{Position}}/g, 'VP of Engineering')
                  }} 
                />
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800">
              <button
                onClick={() => setPreviewTemplate(null)}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold transition-all"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
