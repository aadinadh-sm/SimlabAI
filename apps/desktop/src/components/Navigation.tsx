import React from 'react';
import {
  LayoutDashboard,
  BookOpen,
  MessageSquare,
  GraduationCap,
  Cpu,
  PenTool,
  Activity,
  Code2,
  FileText,
  Settings,
  Sparkles
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'experiments'
  | 'chat'
  | 'viva'
  | 'circuit'
  | 'sketch'
  | 'simulator'
  | 'code'
  | 'reports'
  | 'lab-manual'
  | 'settings';

interface NavigationProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ currentTab, onSelectTab }) => {
  const navItems: { id: NavTab; label: string; icon?: React.ComponentType<{ className?: string }>; emoji?: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'experiments', label: 'Experiments', icon: BookOpen },
    { id: 'chat', label: 'Chat Lab AI', icon: MessageSquare },
    { id: 'viva', label: 'Viva System', icon: GraduationCap },
    { id: 'circuit', label: 'Circuit Lab', icon: Cpu },
    { id: 'sketch', label: 'Sketch → Code', icon: PenTool },
    { id: 'simulator', label: 'Simulator', icon: Activity },
    { id: 'code', label: 'Code Lab', icon: Code2 },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'lab-manual', label: 'Lab Manual', emoji: '📘' },
    { id: 'settings', label: 'Settings & Status', icon: Settings },
  ];

  return (
    <aside className="w-56 border-r border-zinc-800 bg-zinc-950 flex flex-col justify-between py-4 select-none shrink-0">
      <div className="space-y-1 px-3">
        <div className="px-2 pb-2 text-[10px] font-mono tracking-wider text-zinc-500 uppercase">
          WORKSPACE
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id as NavTab)}
              className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded text-xs font-medium transition ${
                isActive
                  ? 'bg-zinc-800/90 text-zinc-100 border border-zinc-700/80 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60 border border-transparent'
              }`}
            >
              {item.emoji ? (
                <span className="w-4 h-4 flex items-center justify-center text-sm leading-none">
                  {item.emoji}
                </span>
              ) : Icon ? (
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
              ) : null}
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="px-4 pt-3 border-t border-zinc-900 text-[11px] text-zinc-500 font-mono">
        <div className="flex items-center justify-between">
          <span>PORTABLE</span>
          <span className="text-emerald-500 font-semibold">USB RUN</span>
        </div>
        <div className="text-[10px] text-zinc-600 mt-1 truncate">
          No cloud telemetry
        </div>
      </div>
    </aside>
  );
};
