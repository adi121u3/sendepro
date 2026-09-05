import React, { useEffect } from 'react';
import { ShieldCheck, CheckCircle2, AlertCircle, X } from 'lucide-react';

interface ToastNotificationProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  onClose?: () => void;
}

export const ToastNotification: React.FC<ToastNotificationProps> = ({ message, type = 'success', onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      if (onClose) onClose();
    }, 3500);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div id="ToastNotification" className="fixed bottom-6 right-6 z-50 bg-slate-900 text-slate-100 px-5 py-3.5 rounded-2xl shadow-2xl border border-slate-700 flex items-center space-x-3.5 animate-bounce-short">
      {type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />}
      {type === 'error' && <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />}
      {type === 'info' && <ShieldCheck className="w-5 h-5 text-amber-400 flex-shrink-0" />}
      <span className="text-xs font-semibold tracking-wide">{message}</span>
      {onClose && (
        <button onClick={onClose} className="text-slate-400 hover:text-slate-200 p-1">
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
