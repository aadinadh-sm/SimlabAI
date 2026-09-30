import React from 'react';
import {
  Cpu,
  Database,
  ShieldCheck,
  Zap,
  BookOpen,
  MessageSquare,
  GraduationCap,
  Play,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  FolderGit2
} from 'lucide-react';
import { SystemStatus, Experiment } from '../types';
import { NavTab } from '../components/Navigation';

interface DashboardPageProps {
  status: SystemStatus | null;
  experiments: Experiment[];
  onSelectTab: (tab: NavTab) => void;
  onSelectExperiment: (expNum: number) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  status,
  experiments,
  onSelectTab,
  onSelectExperiment
}) => {
  const isLlmLoaded = status?.model?.loaded ?? false;

  const quickActions = [
    {
      title: 'Ask Lab AI',
      desc: 'Experiment-aware Q&A with manual citations',
      icon: MessageSquare,
      tab: 'chat' as NavTab,
      actionText: 'Open Chat'
    },
    {
      title: 'Start Viva',
      desc: 'Interactive oral viva test with instant assessment',
      icon: GraduationCap,
      tab: 'viva' as NavTab,
      actionText: 'Practice Viva'
    },
    {
      title: 'Open Circuit Lab',
      desc: 'Design and validate digital & analog circuits',
      icon: Cpu,
      tab: 'circuit' as NavTab,
      actionText: 'Launch Canvas'
    },
    {
      title: 'Run Simulation',
      desc: 'Execute PySpice and numerical wave models',
      icon: Play,
      tab: 'simulator' as NavTab,
      actionText: 'View Waveforms'
    }
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fadeIn">
      {/* Top Banner / System State Bar */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {/* Local AI */}
        <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">LOCAL AI</div>
          <div className="flex items-center space-x-2 mt-1.5">
            <span className={`w-2.5 h-2.5 rounded-full ${isLlmLoaded ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            <span className="text-base font-semibold text-zinc-100 font-mono">
              {isLlmLoaded ? 'ONLINE' : 'STANDBY'}
            </span>
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            {isLlmLoaded ? 'koboldcpp :5001' : 'Ready to start'}
          </div>
        </div>

        {/* Model */}
        <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">ACTIVE MODEL</div>
          <div className="text-sm font-semibold text-zinc-100 truncate mt-1.5 font-mono">
            Llama 3.1 8B Q4_K_M
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            GGUF · Local Weights
          </div>
        </div>

        {/* Knowledge */}
        <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">KNOWLEDGE BASE</div>
          <div className="text-base font-semibold text-zinc-100 mt-1.5 font-mono">
            14 Experiments
          </div>
          <div className="text-[11px] text-emerald-400/90 mt-1 font-mono">
            SQLite FTS5 Indexed
          </div>
        </div>

        {/* Simulation Engines */}
        <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">SIMULATION ENGINES</div>
          <div className="text-base font-semibold text-emerald-400 mt-1.5 font-mono flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Ready</span>
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            PySpice · Logic · NumPy
          </div>
        </div>

        {/* Offline Mode */}
        <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">OFFLINE ENFORCED</div>
          <div className="text-base font-semibold text-zinc-100 mt-1.5 font-mono flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>YES</span>
          </div>
          <div className="text-[11px] text-emerald-400 mt-1 font-mono">
            Zero Telemetry
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-3">
          QUICK ACTIONS
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {quickActions.map((qa) => {
            const Icon = qa.icon;
            return (
              <button
                key={qa.title}
                onClick={() => onSelectTab(qa.tab)}
                className="text-left p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-850/80 transition group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 rounded bg-zinc-800 border border-zinc-700 text-emerald-400 group-hover:text-emerald-300">
                    <Icon className="w-4 h-4" />
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-300 transition-transform group-hover:translate-x-0.5" />
                </div>
                <div className="font-medium text-sm text-zinc-200">{qa.title}</div>
                <div className="text-xs text-zinc-400 mt-1 line-clamp-2">{qa.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 14 Official Experiments Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
            OFFICIAL LAB EXPERIMENTS (23EEP20B)
          </h2>
          <button
            onClick={() => onSelectTab('experiments')}
            className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center space-x-1 font-mono"
          >
            <span>View All Details</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {experiments.map((exp) => (
            <div
              key={exp.exp_number}
              onClick={() => {
                onSelectExperiment(exp.exp_number);
                onSelectTab('experiments');
              }}
              className="p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900 cursor-pointer transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 mb-1.5">
                  <span className="font-semibold text-emerald-400/90">
                    EXPERIMENT {exp.exp_number}
                  </span>
                  <span>{exp.pages}</span>
                </div>
                <h3 className="font-medium text-xs text-zinc-200 line-clamp-2 leading-relaxed">
                  {exp.title}
                </h3>
              </div>

              <div className="mt-3 pt-2.5 border-t border-zinc-800/60 flex items-center justify-between text-[11px]">
                <span className="text-zinc-400 font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/60 border border-zinc-700/50">
                  {exp.category}
                </span>
                <span className="text-zinc-500 hover:text-zinc-300 transition text-[11px]">
                  Explore →
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
