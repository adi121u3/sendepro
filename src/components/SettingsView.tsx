import React, { useState, useEffect } from 'react';
import { Settings, Shield, Cpu, RefreshCw, Send, CheckCircle2, AlertTriangle, Database, Save, Key, Sliders, Mail } from 'lucide-react';
import * as api from '../services/api';

// Target throughput: ~100 emails in 50 minutes ≈ 30 seconds average gap.
// All modes stay near that baseline so pacing is consistent and deliverable.
const SENDING_MODES: Record<string, [number, number]> = {
  slow: [32.0, 38.0],    // ~100 emails in ~58 minutes
  normal: [28.0, 32.0],  // ~100 emails in ~50 minutes (default)
  fast: [25.0, 30.0],    // ~100 emails in ~45 minutes
};

const DEFAULT_SETTINGS = {
  theme: "Warm Executive Amber",
  timeout: "30",
  email_signature: "",
  sender_name: "",
  max_workers: "2",
  max_retries: "3",
  delay_min: "28.0",
  delay_max: "32.0",
  sleep_seconds: "30.0",
  emails_per_second: "0.033",
  rotation_mode: "round_robin",
  priority: "normal",
  reply_to_email: "",
};

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<Record<string, string>>(DEFAULT_SETTINGS);
  const [pacingMode, setPacingMode] = useState<'slow' | 'normal' | 'fast' | 'custom'>('normal');
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    api.fetchSettings().then((data: any[]) => {
      if (Array.isArray(data)) {
        const map: Record<string, string> = {};
        data.forEach(item => {
          map[item.key] = item.value;
        });
        const merged = { ...DEFAULT_SETTINGS, ...map };
        setSettings(merged);
        detectSendingMode(Number(merged.delay_min), Number(merged.delay_max));
      }
    }).catch(err => console.error("Failed to load settings:", err));
  }, []);

  const detectSendingMode = (minVal: number, maxVal: number) => {
    for (const [mode, [mMin, mMax]] of Object.entries(SENDING_MODES)) {
      if (Math.abs(minVal - mMin) < 0.1 && Math.abs(maxVal - mMax) < 0.1) {
        setPacingMode(mode as any);
        return;
      }
    }
    setPacingMode('custom');
  };

  const handleChange = (key: string, value: string) => {
    setSettings(prev => {
      const updated = { ...prev, [key]: value };
      if (key === 'delay_min' || key === 'delay_max') {
        detectSendingMode(
          key === 'delay_min' ? Number(value) : Number(prev.delay_min),
          key === 'delay_max' ? Number(value) : Number(prev.delay_max)
        );
      }
      return updated;
    });
  };

  const handleSetSendingMode = (mode: 'slow' | 'normal' | 'fast') => {
    setPacingMode(mode);
    const [minVal, maxVal] = SENDING_MODES[mode];
    setSettings(prev => ({
      ...prev,
      delay_min: String(minVal),
      delay_max: String(maxVal),
      sleep_seconds: mode === 'slow' ? '35.0' : mode === 'normal' ? '30.0' : '27.0',
      emails_per_second: mode === 'slow' ? '0.028' : mode === 'normal' ? '0.033' : '0.037',
      max_workers: '2'
    }));
  };

  const handleResetDefaults = () => {
    if (!window.confirm("Reset all application settings to their default values?")) return;
    setSettings(DEFAULT_SETTINGS);
    setPacingMode('normal');
    setSuccessMessage("Settings reset to defaults.");
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  const handleSaveAll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (Number(settings.delay_max) < Number(settings.delay_min)) {
      alert("Maximum delay cannot be lower than minimum delay.");
      return;
    }
    setSaving(true);
    setSuccessMessage('');
    try {
      for (const [key, value] of Object.entries(settings)) {
        await api.upsertSetting(key, value);
      }
      setSuccessMessage("Application settings have been saved successfully.");
      setTimeout(() => setSuccessMessage(''), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto bg-slate-950 min-h-screen text-slate-100">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-3">
            <Settings className="w-7 h-7 text-amber-500" />
            Application Settings
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Pacing is tuned for ~100 emails in 50 minutes (about 30 seconds between sends).
          </p>
        </div>
      </div>

      {successMessage && (
        <div className="flex items-center gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSaveAll} className="space-y-8 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Mail className="w-4 h-4 text-amber-400" /> Sender Identity
            </h3>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Default Sender Name</label>
              <input type="text" value={settings.sender_name} onChange={(e) => handleChange('sender_name', e.target.value)} placeholder="Example: John Smith" className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Reply-To Address</label>
              <input type="email" value={settings.reply_to_email} onChange={(e) => handleChange('reply_to_email', e.target.value)} placeholder="replies@yourdomain.com" className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
              <p className="text-[11px] text-slate-500 mt-1">Recipient replies go here. Reply-To is a standard header (visible if they view source).</p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-amber-400" /> Connection
            </h3>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Connection Timeout</label>
              <input type="number" min="5" max="300" value={settings.timeout} onChange={(e) => handleChange('timeout', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Worker Threads</label>
              <input type="number" min="1" max="10" value={settings.max_workers} onChange={(e) => handleChange('max_workers', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Settings className="w-4 h-4 text-amber-400" /> Appearance
            </h3>
            <select value={settings.theme} onChange={(e) => handleChange('theme', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500">
              <option value="Warm Executive Amber">Warm Executive Amber</option>
              <option value="Dark (Professional)">Dark (Professional)</option>
              <option value="Modern Professional Light">Modern Professional Light</option>
            </select>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
          <h3 className="text-base font-bold text-slate-100">Email Signature</h3>
          <textarea rows={4} value={settings.email_signature} onChange={(e) => handleChange('email_signature', e.target.value)} placeholder="Best regards,&#10;&#10;John Smith" className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 text-sm font-mono focus:outline-none focus:border-amber-500 min-h-[110px]" />
        </div>

        <div>
          <h3 className="text-lg font-bold text-slate-100 mb-4">Delivery Configuration (~100 emails / 50 min)</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-bold text-slate-100">Delivery Mode</h3>
              <div className="space-y-2.5">
                {(['slow', 'normal', 'fast'] as const).map(mode => (
                  <button key={mode} type="button" onClick={() => handleSetSendingMode(mode)} className={`w-full p-3.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                    pacingMode === mode ? 'bg-amber-500/10 border-amber-500 text-amber-300' : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}>
                    <div>
                      <span className="font-bold uppercase tracking-wider text-xs">{mode}</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {mode === 'slow' && '32-38s delay (~100 emails / 58 min)'}
                        {mode === 'normal' && '28-32s delay (~100 emails / 50 min)'}
                        {mode === 'fast' && '25-30s delay (~100 emails / 45 min)'}
                      </p>
                    </div>
                    <input type="radio" checked={pacingMode === mode} onChange={() => handleSetSendingMode(mode)} className="text-amber-500 focus:ring-amber-500 bg-slate-900 border-slate-700" />
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-bold text-slate-100">Pacing</h3>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">Minimum Delay (sec)</label>
                <input type="number" step="0.1" min="0" value={settings.delay_min} onChange={(e) => handleChange('delay_min', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">Maximum Delay (sec)</label>
                <input type="number" step="0.1" min="0" value={settings.delay_max} onChange={(e) => handleChange('delay_max', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">Sleep Interval (sec)</label>
                <input type="number" step="0.1" min="0" value={settings.sleep_seconds} onChange={(e) => handleChange('sleep_seconds', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-bold text-slate-100">Retry Policy</h3>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Maximum Retries</label>
                <input type="number" min="0" max="20" value={settings.max_retries} onChange={(e) => handleChange('max_retries', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Rotation Mode</label>
                <select value={settings.rotation_mode} onChange={(e) => handleChange('rotation_mode', e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500">
                  <option value="round_robin">Round Robin</option>
                  <option value="random">Random</option>
                  <option value="failover">Failover</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 pt-4 border-t border-slate-800">
          <button type="button" onClick={handleResetDefaults} className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-sm border border-slate-700">
            Reset Defaults
          </button>
          <button type="submit" disabled={saving} className="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm shadow-lg shadow-amber-500/20 disabled:opacity-50 flex items-center gap-2">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
};
