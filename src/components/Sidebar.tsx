import React from 'react';
import { TabType } from '../types';
import { 
  LayoutDashboard, 
  Send, 
  Server, 
  Users, 
  FileText, 
  Activity, 
  Mail,
  ShieldCheck,
  Settings
} from 'lucide-react';

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  activeCampaignsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, activeCampaignsCount }) => {
  const navItems = [
    { id: 'dashboard' as TabType, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'campaigns' as TabType, label: 'Campaigns', icon: Send, badge: activeCampaignsCount > 0 ? activeCampaignsCount : null },
    { id: 'accounts' as TabType, label: 'SMTP & Accounts', icon: Server },
    { id: 'leads' as TabType, label: 'Leads & Contacts', icon: Users },
    { id: 'templates' as TabType, label: 'Templates', icon: FileText },
    { id: 'Email Composer' as TabType, label: 'Email Composer', icon: Mail },
    { id: 'activity' as TabType, label: 'Activity Logs', icon: Activity },
    { id: 'settings' as TabType, label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen select-none shrink-0">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800/80 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-slate-950 shadow-lg shadow-amber-500/20">
          <Mail className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-slate-100 tracking-tight text-base">Email Sender Pro</h1>
          <div className="flex items-center gap-1.5 text-xs text-amber-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Engine Active
          </div>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-5 h-5 ${isActive ? 'text-amber-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== null && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <div className="truncate">
            <p className="font-medium text-slate-300">Secure Transport</p>
            <p className="text-[11px] text-slate-400 truncate">TLS / OAuth2 / ZeptoMail</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
