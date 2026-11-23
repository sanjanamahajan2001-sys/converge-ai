import React from 'react';
import { GroupMemberSummary } from '@/types/groupConversation';

interface GroupRosterModalProps {
  isOpen: boolean;
  onClose: () => void;
  members: GroupMemberSummary[];
  hostId: string;
}

export const GroupRosterModal: React.FC<GroupRosterModalProps> = ({
  isOpen,
  onClose,
  members,
  hostId,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xl">👥</span>
            <h3 className="font-semibold text-lg text-slate-900 dark:text-white">
              Circle Participants ({members.length})
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg p-1 rounded-md"
            aria-label="Close roster modal"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {members.map((m) => {
            const isHost = m.user_id === hostId || m.role === 'HOST';
            return (
              <div
                key={m.user_id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-brass/10 text-brass border border-brass/20 flex items-center justify-center font-bold text-sm shrink-0">
                    {m.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-sm text-slate-900 dark:text-white truncate">
                        {m.full_name}
                      </p>
                      {isHost && (
                        <span className="text-[10px] font-bold text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-300/40">
                          Host
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {m.job_title ? `${m.job_title} • ` : ''}{m.company_name || 'Delegate'}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium text-xs rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
