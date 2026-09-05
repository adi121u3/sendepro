import React from 'react';
import { TabType } from '../types';
import { Bell, Search, Plus, Play, LogOut } from 'lucide-react';
import { logoutAdmin } from '../services/api';

interface HeaderProps {
  currentTab: TabType;
  onNewCampaign: () => void;
  onNewAccount: () => void;
  onNewLead: () => void;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onNewCampaign, onNewAccount, onNewLead }) => {
  const getTitle = () => {
    switch (currentTab) {
      case 'dashboard': return 'Campaign Overview & Analytics';
      case 'campaigns': return 'Campaign Manager & Worker Engine';
      case 'accounts': return 'SMTP & Provider Accounts';
      case 'leads': return 'Leads & Contact Lists';
      case 'templates': return 'Email Templates & Personalization';
      case 'activity': return 'Delivery Logs & Audit Trail';
    }
  };

  const getAction = () => {
    if (currentTab === 'campaigns') {
      return (
        <button
          onClick={onNewCampaign}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
        >
          <Plus className="w-4 h-4" />
          New Campaign
        </button>
      );
    }
    if (currentTab === 'accounts') {
      return (
        <button
          onClick={onNewAccount}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
        >
          <Plus className="w-4 h-4" />
          Add Account
        </button>
      );
    }
    if (currentTab === 'leads') {
      return (
        <button
          onClick={onNewLead}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-500/20"
        >
          <Plus className="w-4 h-4" />
          Add Lead
        </button>
      );
    }
    return null;
  };

  return (
    <header className="h-20 bg-slate-900 border-b border-slate-800 px-8 flex items-center justify-between shrink-0">
      <div>
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">{getTitle()}</h2>
        <p className="text-xs text-slate-400">Manage your automated email outreach and delivery infrastructure</p>
      </div>

      <div className="flex items-center gap-4">
        {getAction()}
        <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
          <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold text-sm">
            AR
          </div>
          <button
            onClick={logoutAdmin}
            title="Sign Out"
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-slate-100 transition-colors border border-slate-700"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
