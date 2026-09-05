import React, { useState, useEffect } from 'react';
import { Settings, Shield, Cpu, RefreshCw, Send, CheckCircle2, AlertTriangle, Database, Save, Key, Sliders, Mail } from 'lucide-react';
import * as api from '../services/api';

const SENDING_MODES: Record<string, [number, number]> = {
  slow: [15.0, 30.0],
  normal: [5.0, 15.0],
  fast: [1.0, 3.0],
};

const DEFAULT_SETTINGS = {
  theme: "Warm Executive Amber",
  timeout: "30",
  email_signature: "",
  sender_name: "",
  max_workers: "4",
  max_retries: "3",
  delay_min: "5.0",
  delay_max: "15.0",
  sleep_seconds: "10.0",
  emails_per_second: "2.0",
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
      sleep_seconds: mode === 'slow' ? '25.0' : mode === 'normal' ? '10.0' : '3.0',
      emails_per_second: mode === 'slow' ? '1.0' : mode === 'normal' ? '2.0' : '5.0',
      max_workers: mode === 'slow' ? '2' : mode === 'normal' ? '4' : '8'
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
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-3">
            <Settings className="w-7 h-7 text-amber-500" />
            Application Settings
          </h2>
          <p className="text-slate-400 text-sm mt-1">Configure identity, delivery behavior, connection preferences, account rotation, and application appearance.</p>
        </div>
      </div>

      {successMessage && (
        <div className="flex items-center gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSaveAll} className="space-y-8 pb-16">
        {/* TOP GRID: 3 Columns (Identity, Connection, Appearance) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* SENDER IDENTITY */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm flex flex-col justify-between">
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Mail className="w-4 h-4 text-amber-400" /> Sender Identity
              </h3>
              <p className="text-xs text-slate-400">Default information used when composing messages.</p>
            </div>
            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Default Sender Name
                </label>
                <input
                  type="text"
                  value={settings.sender_name}
                  onChange={(e) => handleChange('sender_name', e.target.value)}
                  placeholder="Example: John Smith"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">Used when a message does not specify another sender name.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Reply-To Address
                </label>
                <input
                  type="email"
                  value={settings.reply_to_email}
                  onChange={(e) => handleChange('reply_to_email', e.target.value)}
                  placeholder="Optional reply-to address"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">Replies will be directed to this address when configured.</p>
              </div>
            </div>
          </div>

          {/* CONNECTION */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm flex flex-col justify-between">
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-amber-400" /> Connection
              </h3>
              <p className="text-xs text-slate-400">Network timeout and worker configuration.</p>
            </div>
            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Connection Timeout
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="5"
                    max="300"
                    value={settings.timeout}
                    onChange={(e) => handleChange('timeout', e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-16"
                  />
                  <span className="absolute right-4 top-2.5 text-xs text-slate-400">sec</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">Maximum time to wait for an SMTP/API connection.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Worker Threads
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={settings.max_workers}
                    onChange={(e) => handleChange('max_workers', e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-20"
                  />
                  <span className="absolute right-4 top-2.5 text-xs text-slate-400">workers</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">Controls the number of background delivery workers.</p>
              </div>
            </div>
          </div>

          {/* APPEARANCE */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm flex flex-col justify-between">
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Settings className="w-4 h-4 text-amber-400" /> Appearance
              </h3>
              <p className="text-xs text-slate-400">Choose the visual theme used by the application.</p>
            </div>
            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Application Theme
                </label>
                <select
                  value={settings.theme}
                  onChange={(e) => handleChange('theme', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                >
                  <option value="Warm Executive Amber">Warm Executive Amber</option>
                  <option value="Dark (Professional)">Dark (Professional)</option>
                  <option value="Modern Professional Light">Modern Professional Light</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">The theme is applied after saving your settings.</p>
              </div>
            </div>
          </div>
        </div>

        {/* EMAIL SIGNATURE */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-100">Email Signature</h3>
            <p className="text-xs text-slate-400">Default signature inserted into outgoing messages.</p>
          </div>
          <textarea
            rows={4}
            value={settings.email_signature}
            onChange={(e) => handleChange('email_signature', e.target.value)}
            placeholder="Best regards,&#10;&#10;John Smith&#10;Customer Support"
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 text-sm font-mono focus:outline-none focus:border-amber-500 min-h-[110px] max-h-[160px]"
          />
        </div>

        {/* DELIVERY CONFIGURATION SECTION */}
        <div>
          <h3 className="text-lg font-bold text-slate-100 mb-4 tracking-tight">Delivery Configuration</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* DELIVERY MODE */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-100">Delivery Mode</h3>
                <p className="text-xs text-slate-400">Quickly configure a predefined pacing profile.</p>
              </div>
              <div className="space-y-2.5 pt-2">
                {(['slow', 'normal', 'fast'] as const).map(mode => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => handleSetSendingMode(mode)}
                    className={`w-full p-3.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                      pacingMode === mode
                        ? 'bg-amber-500/10 border-amber-500 text-amber-300 shadow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <span className="font-bold uppercase tracking-wider text-xs">{mode}</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {mode === 'slow' && '15-30s delay (Conservative)'}
                        {mode === 'normal' && '5-15s delay (Balanced)'}
                        {mode === 'fast' && '1-3s delay (High throughput)'}
                      </p>
                    </div>
                    <input
                      type="radio"
                      checked={pacingMode === mode}
                      onChange={() => handleSetSendingMode(mode)}
                      className="text-amber-500 focus:ring-amber-500 bg-slate-900 border-slate-700"
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* PACING */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-100">Pacing</h3>
                <p className="text-xs text-slate-400">Fine-tune delivery intervals.</p>
              </div>
              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">Minimum Delay</label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={settings.delay_min}
                      onChange={(e) => handleChange('delay_min', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-16"
                    />
                    <span className="absolute right-4 top-2.5 text-xs text-slate-400">sec</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">Maximum Delay</label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={settings.delay_max}
                      onChange={(e) => handleChange('delay_max', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-16"
                    />
                    <span className="absolute right-4 top-2.5 text-xs text-slate-400">sec</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">Sleep Interval</label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={settings.sleep_seconds}
                      onChange={(e) => handleChange('sleep_seconds', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-16"
                    />
                    <span className="absolute right-4 top-2.5 text-xs text-slate-400">sec</span>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-0.5">Optional pause between delivery operations.</p>
                </div>
              </div>
            </div>

            {/* RETRY POLICY */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-100">Retry Policy</h3>
                <p className="text-xs text-slate-400">Configure how temporary delivery failures are handled.</p>
              </div>
              <div className="space-y-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Maximum Retries</label>
                  <div className="relative">
                    <input
                      type="number"
                      min="0"
                      max="20"
                      value={settings.max_retries}
                      onChange={(e) => handleChange('max_retries', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-24"
                    />
                    <span className="absolute right-4 top-2.5 text-xs text-slate-400">attempts</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Number of additional attempts for retryable failures.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ACCOUNT ROUTING SECTION */}
        <div>
          <h3 className="text-lg font-bold text-slate-100 mb-4 tracking-tight">Account Routing</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* ACCOUNT DISTRIBUTION */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-100">Account Distribution</h3>
                <p className="text-xs text-slate-400">Choose how multiple configured accounts are selected.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Distribution Strategy</label>
                <select
                  value={settings.rotation_mode}
                  onChange={(e) => handleChange('rotation_mode', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                >
                  <option value="round_robin">Sequential / Round-Robin</option>
                  <option value="random">Random Distribution</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">Used when multiple compatible accounts are available.</p>
              </div>
            </div>

            {/* MESSAGE PRIORITY */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-100">Message Priority</h3>
                <p className="text-xs text-slate-400">Default priority assigned to outgoing messages.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Default Priority</label>
                <select
                  value={settings.priority}
                  onChange={(e) => handleChange('priority', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* RATE CONTROL */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-100">Rate Control</h3>
            <p className="text-xs text-slate-400">Optional application-level throughput limit.</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Emails Per Second</label>
            <div className="relative max-w-md">
              <input
                type="number"
                step="0.01"
                min="0"
                value={settings.emails_per_second}
                onChange={(e) => handleChange('emails_per_second', e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-amber-500 pr-16"
              />
              <span className="absolute right-4 top-2.5 text-xs text-slate-400">/ sec</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Set to 0 for no application-level rate limit.</p>
          </div>
        </div>

        {/* SAVE BAR */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg sticky bottom-6 z-20">
          <span className="text-xs text-slate-400">Changes are stored locally in the application database.</span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleResetDefaults}
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-all"
            >
              Reset Defaults
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-xs transition-all shadow-lg shadow-amber-500/20 disabled:opacity-50 min-w-[140px]"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
