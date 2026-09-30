import React from 'react';
import { ShieldCheck, Cpu, HardDrive, Database, Terminal, Activity } from 'lucide-react';
import { SystemStatus } from '../types';

interface HeaderProps {
  status: SystemStatus | null;
  onRefreshStatus: () => void;
}

export const Header: React.FC<HeaderProps> = ({ status, onRefreshStatus }) => {
  const isLlmLoaded = status?.model?.loaded ?? false;
  const isDbReady = status?.knowledge_base?.database_ready ?? false;

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950 px-5 flex items-center justify-between select-none">
      {/* Brand & Tagline */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center font-mono font-bold text-emerald-400 text-sm shadow-sm">
          S<span className="text-zinc-400">L</span>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-semibold tracking-tight text-zinc-100 text-sm">SIMLAB AI</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
              v1.0.0 · USB PORTABLE
            </span>
          </div>
          <div className="text-[11px] text-zinc-400">
            23EEP20B Simulation Lab Manual Copilot
          </div>
        </div>
      </div>

      {/* Real-time Status Badges */}
      <div className="flex items-center space-x-4 text-xs font-mono">
        {/* Offline Badge */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-[11px] font-medium text-emerald-400">OFFLINE MODE</span>
          <span className="text-zinc-600">|</span>
          <span className="text-[11px] text-zinc-400">SECURE</span>
        </div>

        {/* Local AI Status */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">
          <span className={`w-2 h-2 rounded-full ${isLlmLoaded ? 'bg-emerald-400 animate-pulse' : 'bg-amber-500'}`} />
          <span className="text-[11px] text-zinc-400">LOCAL AI:</span>
          <span className={`text-[11px] font-medium ${isLlmLoaded ? 'text-zinc-200' : 'text-amber-400'}`}>
            {isLlmLoaded ? 'ONLINE' : 'STANDBY'}
          </span>
        </div>

        {/* Model Spec */}
        <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 text-[11px]">
          <Cpu className="w-3.5 h-3.5 text-zinc-500" />
          <span>Llama 3.1 8B Q4_K_M</span>
        </div>

        {/* Knowledge Base Badge */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 text-[11px]">
          <Database className="w-3.5 h-3.5 text-zinc-500" />
          <span>14 Experiments (FTS5)</span>
        </div>

        {/* Refresh Health */}
        <button
          onClick={onRefreshStatus}
          title="Refresh hardware & status diagnostics"
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-transparent hover:border-zinc-700 transition"
        >
          <Activity className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
