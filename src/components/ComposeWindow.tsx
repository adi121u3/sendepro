import React, { useState, useEffect } from 'react';
import { Draft, Account } from '../types';
import { X, Send, Check, Paperclip, Plus, Bold, Italic, Underline, Link2, Maximize2, Minimize2, Move, AlertCircle, RefreshCw } from 'lucide-react';
import * as api from '../services/api';

export interface ComposeSession {
  windowId: string;
  draftId?: string | number;
  fromName: string;
  senderAccountId: string | number;
  recipient: string;
  cc: string;
  bcc: string;
  subject: string;
  body: string;
  attachments: string[];
  isMaximized: boolean;
  isMinimized: boolean;
  position: { x: number; y: number };
  zIndex: number;
  isDirty: boolean;
  saving: boolean;
  saveSuccessMsg: string;
  sending: boolean;
  sendSuccess: boolean;
  sendError: string;
}

interface ComposeWindowProps {
  session: ComposeSession;
  accounts: Account[];
  onUpdateSession: (windowId: string, updates: Partial<ComposeSession>) => void;
  onClose: (windowId: string) => void;
  onBringToFront: (windowId: string) => void;
  onDraftSaved: (draft: Draft) => void;
}

export const ComposeWindow: React.FC<ComposeWindowProps> = ({
  session,
  accounts,
  onUpdateSession,
  onClose,
  onBringToFront,
  onDraftSaved,
}) => {
  const [newAttachmentName, setNewAttachmentName] = useState('');
  const [showCcBcc, setShowCcBcc] = useState(Boolean(session.cc || session.bcc));

  // Draggable position state
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      onUpdateSession(session.windowId, {
        position: {
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        }
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset, session.windowId, onUpdateSession]);

  const handleMouseDownHeader = (e: React.MouseEvent) => {
    onBringToFront(session.windowId);
    if (session.isMaximized) return;
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - session.position.x,
      y: e.clientY - session.position.y
    });
  };

  const handleFieldChange = (field: keyof ComposeSession, val: any) => {
    onUpdateSession(session.windowId, {
      [field]: val,
      isDirty: true
    });
  };

  const handleAddAttachment = () => {
    if (!newAttachmentName.trim()) return;
    const updated = [...session.attachments, newAttachmentName.trim()];
    onUpdateSession(session.windowId, {
      attachments: updated,
      isDirty: true
    });
    setNewAttachmentName('');
  };

  const handleRemoveAttachment = (index: number) => {
    const updated = session.attachments.filter((_, i) => i !== index);
    onUpdateSession(session.windowId, {
      attachments: updated,
      isDirty: true
    });
  };

  const handleSaveDraft = async () => {
    onUpdateSession(session.windowId, { saving: true, saveSuccessMsg: '', sendError: '' });
    try {
      const payload = {
        from_name: session.fromName,
        subject: session.subject,
        recipient: session.recipient,
        body: session.body,
        attachments: JSON.stringify(session.attachments),
        sender_account_id: session.senderAccountId ? Number(session.senderAccountId) : null,
      };

      let saved: Draft;
      if (session.draftId) {
        saved = await api.updateDraft(session.draftId, payload);
      } else {
        saved = await api.createDraft(payload);
      }

      onDraftSaved(saved);
      onUpdateSession(session.windowId, {
        draftId: saved.id,
        isDirty: false,
        saving: false,
        saveSuccessMsg: 'Saved to /api/drafts'
      });
      setTimeout(() => {
        onUpdateSession(session.windowId, { saveSuccessMsg: '' });
      }, 2500);
    } catch (e: any) {
      onUpdateSession(session.windowId, {
        saving: false,
        sendError: e.message || 'Failed to save draft'
      });
    }
  };

  const handleSend = async () => {
    if (!session.recipient.trim()) {
      onUpdateSession(session.windowId, { sendError: 'Please specify a recipient email.' });
      return;
    }
    onUpdateSession(session.windowId, { sending: true, sendError: '', sendSuccess: false });
    try {
      await handleSaveDraft();
      await api.sendEmailMessage({
        sender_account_id: session.senderAccountId || (accounts[0] ? accounts[0].id : 1),
        recipient: session.recipient,
        subject: session.subject,
        body: session.body,
        from_name: session.fromName,
        high_priority: (session as any).highPriority || false
      });
      onUpdateSession(session.windowId, {
        sending: false,
        sendSuccess: true
      });
      setTimeout(() => {
        onClose(session.windowId);
      }, 1500);
    } catch (e: any) {
      onUpdateSession(session.windowId, {
        sending: false,
        sendError: e.message || 'Failed to send message'
      });
    }
  };

  const applyFormatting = (tag: string) => {
    const updatedBody = session.body + `[${tag}]Formatted text[/${tag}]`;
    onUpdateSession(session.windowId, {
      body: updatedBody,
      isDirty: true
    });
  };

  // If minimized, render as taskbar pill
  if (session.isMinimized) {
    return (
      <div
        onClick={() => {
          onUpdateSession(session.windowId, { isMinimized: false });
          onBringToFront(session.windowId);
        }}
        style={{ zIndex: session.zIndex }}
        className="fixed bottom-4 right-4 bg-slate-900 border border-slate-700 hover:border-amber-500 rounded-xl px-4 py-2.5 shadow-2xl flex items-center gap-3 cursor-pointer transition-all animate-bounce-short"
      >
        <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
        <div className="text-xs font-semibold text-slate-100 max-w-[180px] truncate">
          {session.subject || session.recipient || 'Compose Window'}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onClose(session.windowId); }}
          className="text-slate-400 hover:text-slate-200 p-1 rounded"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div
      onClick={() => onBringToFront(session.windowId)}
      style={{
        zIndex: session.zIndex,
        ...(session.isMaximized ? {} : { transform: `translate(${session.position.x}px, ${session.position.y}px)` })
      }}
      className={`fixed top-16 left-20 bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden flex flex-col transition-shadow duration-200 ${
        session.isMaximized ? '!inset-4 !w-auto !h-auto max-w-none max-h-none rounded-2xl' : 'w-full max-w-3xl h-[760px]'
      }`}
    >
      {/* Title Bar / Draggable Header */}
      <div
        onMouseDown={handleMouseDownHeader}
        className="px-4 py-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between select-none cursor-move"
        title="Click and drag to move window"
      >
        <div className="flex items-center gap-2.5">
          <Move className="w-4 h-4 text-amber-400" />
          <span className="font-bold text-slate-100 text-xs tracking-wide">
            COMPOSE SESSION #{session.windowId.substring(0, 5)}
          </span>
          <span className="text-[11px] text-amber-400 font-medium">
            {session.isDirty ? 'Unsaved changes' : 'Saved'}
          </span>
          {session.saveSuccessMsg && (
            <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-semibold">
              <Check className="w-3 h-3" /> {session.saveSuccessMsg}
            </span>
          )}
          {session.sendSuccess && (
            <span className="text-[11px] text-teal-400 flex items-center gap-1 font-semibold">
              <Check className="w-3 h-3" /> Sent successfully!
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSend}
            disabled={session.sending}
            className="px-4 py-1.5 bg-teal-600 hover:bg-teal-500 text-slate-50 font-semibold rounded-lg text-xs transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-50"
          >
            {session.sending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            {session.sending ? 'Sending...' : 'Send'}
          </button>
          <div className="flex items-center gap-1 ml-2 border-l border-slate-800 pl-3">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onUpdateSession(session.windowId, { isMinimized: true }); }}
              className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800"
              title="Minimize"
            >
              <Minimize2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onUpdateSession(session.windowId, { isMaximized: !session.isMaximized }); }}
              className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800"
              title="Maximize / Restore"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onClose(session.windowId); }}
              className="text-slate-400 hover:text-red-400 p-1 rounded hover:bg-slate-800"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Error banner if any */}
      {session.sendError && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-2 flex items-center gap-2 text-red-400 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{session.sendError}</span>
        </div>
      )}

      {/* Compose Fields Panel */}
      <div className="flex-1 flex flex-col bg-slate-900 overflow-y-auto p-5 space-y-3.5">
        {/* From Row: SMTP Account & From Name */}
        <div className="flex items-center gap-3">
          <span className="w-24 text-xs font-semibold text-slate-400 uppercase tracking-wider">From Settings</span>
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
            <select
              value={session.senderAccountId}
              onChange={(e) => handleFieldChange('senderAccountId', e.target.value)}
              className="md:col-span-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              {accounts.map(acc => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} &lt;{acc.fromEmail || acc.username}&gt;
                </option>
              ))}
            </select>
            <input
              type="text"
              value={session.fromName}
              onChange={(e) => handleFieldChange('fromName', e.target.value)}
              placeholder="From Name (Display Name)"
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            />
          </div>
        </div>

        {/* To Row */}
        <div className="flex items-center gap-3">
          <span className="w-24 text-xs font-semibold text-slate-400 uppercase tracking-wider">To (Recipient)</span>
          <div className="flex-1 flex items-center gap-2">
            <input
              type="email"
              value={session.recipient}
              onChange={(e) => handleFieldChange('recipient', e.target.value)}
              placeholder="recipient@example.com"
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            />
            <button
              type="button"
              onClick={() => setShowCcBcc(!showCcBcc)}
              className="text-teal-400 hover:text-teal-300 text-xs font-semibold px-2.5 py-1.5 rounded bg-teal-500/10 border border-teal-500/20"
            >
              CC / BCC
            </button>
          </div>
        </div>

        {/* CC / BCC Conditional Row */}
        {showCcBcc && (
          <div className="space-y-2 pl-27">
            <div className="flex items-center gap-3">
              <span className="w-24 text-xs font-semibold text-slate-400 uppercase">CC</span>
              <input
                type="text"
                value={session.cc}
                onChange={(e) => handleFieldChange('cc', e.target.value)}
                placeholder="cc@example.com"
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>
            <div className="flex items-center gap-3">
              <span className="w-24 text-xs font-semibold text-slate-400 uppercase">BCC</span>
              <input
                type="text"
                value={session.bcc}
                onChange={(e) => handleFieldChange('bcc', e.target.value)}
                placeholder="bcc@example.com"
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>
        )}

        {/* Subject Row */}
        <div className="flex items-center gap-3">
          <span className="w-24 text-xs font-semibold text-slate-400 uppercase tracking-wider">Subject</span>
          <input
            type="text"
            value={session.subject}
            onChange={(e) => handleFieldChange('subject', e.target.value)}
            placeholder="Email Subject Line..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-medium"
          />
        </div>

        {/* Formatting Toolbar */}
        <div className="flex items-center flex-wrap gap-1 bg-slate-950/60 border border-slate-800 rounded-lg p-1.5 text-slate-300">
          <button type="button" onClick={() => applyFormatting('b')} className="p-1.5 hover:bg-slate-800 rounded text-xs font-bold" title="Bold"><Bold className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={() => applyFormatting('i')} className="p-1.5 hover:bg-slate-800 rounded text-xs italic" title="Italic"><Italic className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={() => applyFormatting('u')} className="p-1.5 hover:bg-slate-800 rounded text-xs underline" title="Underline"><Underline className="w-3.5 h-3.5" /></button>
          <span className="w-px h-4 bg-slate-800 mx-1"></span>
          <button type="button" onClick={() => setBody(prev => prev + '<small>')} className="px-2 py-1 hover:bg-slate-800 rounded text-xs">A–</button>
          <button type="button" onClick={() => setBody(prev => prev + '<strong>')} className="px-2 py-1 hover:bg-slate-800 rounded text-xs font-bold">A+</button>
          <button type="button" onClick={() => setBody(prev => prev + '<span style="color:teal">')} className="px-2 py-1 hover:bg-slate-800 rounded text-xs text-teal-400 font-semibold">A</button>
          <span className="w-px h-4 bg-slate-800 mx-1"></span>
          <button type="button" onClick={() => setBody(prev => prev + '• ')} className="px-2 py-1 hover:bg-slate-800 rounded text-xs">•</button>
          <button type="button" onClick={() => setBody(prev => prev + '1. ')} className="px-2 py-1 hover:bg-slate-800 rounded text-xs">1.</button>
          <span className="w-px h-4 bg-slate-800 mx-1"></span>
          <button type="button" onClick={() => applyFormatting('a')} className="p-1.5 hover:bg-slate-800 rounded text-xs" title="Insert Link"><Link2 className="w-3.5 h-3.5" /></button>
          <div className="ml-auto flex items-center gap-2">
            <input
              type="text"
              value={newAttachmentName}
              onChange={(e) => setNewAttachmentName(e.target.value)}
              placeholder="Attachment file name..."
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-teal-500 w-48"
            />
            <button
              type="button"
              onClick={handleAddAttachment}
              className="flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded text-xs transition-colors"
            >
              <Plus className="w-3 h-3" />
              Attach files
            </button>
          </div>
        </div>

        {/* Rich Text Body Area */}
        <div className="flex-1 flex flex-col min-h-[220px]">
          <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Rich Text Body & Signature Area
          </label>
          <textarea
            value={session.body}
            onChange={(e) => handleFieldChange('body', e.target.value)}
            placeholder="Type your message body here..."
            className="w-full flex-1 bg-slate-950 border border-slate-800 rounded-lg p-3.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-mono resize-none leading-relaxed"
          ></textarea>
        </div>

        {/* Attachments List */}
        {session.attachments.length > 0 && (
          <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-2.5 space-y-1.5">
            <span className="text-[11px] font-semibold text-slate-400 uppercase flex items-center gap-1">
              <Paperclip className="w-3 h-3 text-teal-400" /> Attachments ({session.attachments.length})
            </span>
            <div className="flex flex-wrap gap-2">
              {session.attachments.map((att, i) => (
                <div key={i} className="flex items-center gap-1.5 bg-slate-800 text-slate-200 px-2.5 py-1 rounded text-xs border border-slate-700">
                  <Paperclip className="w-3 h-3 text-teal-400" />
                  <span>{att}</span>
                  <button type="button" onClick={() => handleRemoveAttachment(i)} className="text-slate-400 hover:text-red-400 ml-1">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Status Bar with Save Draft button */}
      <div className="px-4 py-2.5 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={Boolean((session as any).highPriority)}
              onChange={(e) => onUpdateSession(session.windowId, { highPriority: e.target.checked } as any)}
              className="rounded bg-slate-900 border-slate-700 text-teal-600 focus:ring-0"
            />
            <span>High Priority (X-Priority: 1)</span>
          </label>
          {session.saving && <span className="text-amber-400 font-medium">Saving draft...</span>}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={session.saving}
            onClick={handleSaveDraft}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-xs transition-colors shadow-md shadow-amber-500/20"
          >
            <Check className="w-3.5 h-3.5" />
            {session.saving ? 'Saving...' : 'Save Draft'}
          </button>
          <span className="text-teal-400 font-medium">Ready</span>
        </div>
      </div>
    </div>
  );
};
