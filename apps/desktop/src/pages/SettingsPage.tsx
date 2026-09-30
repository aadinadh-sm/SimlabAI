import React, { useState } from 'react';
import {
  Cpu,
  Database,
  ShieldCheck,
  Server,
  Play,
  Square,
  RefreshCw,
  HardDrive,
  Sliders,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { SystemStatus } from '../types';
import { startLLM, stopLLM } from '../lib/api';

interface SettingsPageProps {
  status: SystemStatus | null;
  onRefreshStatus: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ status, onRefreshStatus }) => {
  const [threads, setThreads] = useState<number>(4);
  const [gpuLayers, setGpuLayers] = useState<number>(0);
  const [contextSize, setContextSize] = useState<number>(4096);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string>('');

  const isLoaded = status?.model?.loaded ?? false;

  const applyProfile = (profile: 'LOW' | 'BALANCED' | 'PERFORMANCE') => {
    if (profile === 'LOW') {
      setThreads(4);
      setGpuLayers(0);
      setContextSize(4096);
    } else if (profile === 'BALANCED') {
      setThreads(6);
      setGpuLayers(16);
      setContextSize(4096);
    } else {
      setThreads(8);
      setGpuLayers(33);
      setContextSize(8192);
    }
  };

  const handleStart = async () => {
    setActionLoading(true);
    setActionMessage('Launching local llama.cpp / koboldcpp engine...');
    try {
      await startLLM({ threads, gpu_layers: gpuLayers, context_size: contextSize });
      setActionMessage('Engine started. Waiting for model weights to map...');
      setTimeout(() => {
        onRefreshStatus();
        setActionLoading(false);
      }, 3000);
    } catch (e: any) {
      setActionMessage(`Error: ${e.message}`);
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    setActionMessage('Stopping local AI engine...');
    try {
      await stopLLM();
      setActionMessage('Engine stopped.');
      setTimeout(() => {
        onRefreshStatus();
        setActionLoading(false);
      }, 1000);
    } catch (e: any) {
      setActionMessage(`Error: ${e.message}`);
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 select-text">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
          System Status & AI Model Configuration
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Configure local llama.cpp parameters, view hardware profiles, and audit offline enforcement.
        </p>
      </div>

      {/* AI Model Manager */}
      <div className="p-6 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-5">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center space-x-2">
            <Server className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-zinc-100 font-mono">
              LOCAL AI INFERENCE ENGINE (llama.cpp)
            </h2>
          </div>
          <div className="flex items-center space-x-2">
            <span
              className={`w-2 h-2 rounded-full ${isLoaded ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}
            />
            <span className="text-xs font-mono font-medium text-zinc-200">
              {isLoaded ? 'ONLINE (:5001)' : 'STANDBY / STOPPED'}
            </span>
          </div>
        </div>

        {/* Hardware Preset Profiles */}
        <div>
          <label className="text-xs font-mono uppercase tracking-wider text-zinc-400 block mb-2">
            HARDWARE ADAPTATION PROFILE
          </label>
          <div className="grid grid-cols-3 gap-3">
            <button
              onClick={() => applyProfile('LOW')}
              className="p-3 rounded border border-zinc-800 bg-zinc-900 hover:border-zinc-700 text-left transition"
            >
              <div className="text-xs font-semibold text-zinc-200 font-mono">LOW PROFILE</div>
              <div className="text-[11px] text-zinc-400 mt-0.5">CPU only · 4 threads · 4K ctx</div>
            </button>
            <button
              onClick={() => applyProfile('BALANCED')}
              className="p-3 rounded border border-zinc-800 bg-zinc-900 hover:border-zinc-700 text-left transition"
            >
              <div className="text-xs font-semibold text-zinc-200 font-mono">BALANCED</div>
              <div className="text-[11px] text-zinc-400 mt-0.5">Hybrid CPU/GPU · 16 layers · 4K ctx</div>
            </button>
            <button
              onClick={() => applyProfile('PERFORMANCE')}
              className="p-3 rounded border border-zinc-800 bg-zinc-900 hover:border-zinc-700 text-left transition"
            >
              <div className="text-xs font-semibold text-zinc-200 font-mono">PERFORMANCE</div>
              <div className="text-[11px] text-zinc-400 mt-0.5">Full GPU offload · 33 layers · 8K ctx</div>
            </button>
          </div>
        </div>

        {/* Sliders & Parameters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono text-zinc-400">
              <span>THREADS:</span>
              <span className="text-zinc-200">{threads}</span>
            </div>
            <input
              type="range"
              min={1}
              max={16}
              value={threads}
              onChange={(e) => setThreads(parseInt(e.target.value))}
              className="w-full accent-emerald-400"
            />
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono text-zinc-400">
              <span>GPU LAYERS (VRAM):</span>
              <span className="text-zinc-200">{gpuLayers}</span>
            </div>
            <input
              type="range"
              min={0}
              max={33}
              value={gpuLayers}
              onChange={(e) => setGpuLayers(parseInt(e.target.value))}
              className="w-full accent-emerald-400"
            />
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono text-zinc-400">
              <span>CONTEXT WINDOW:</span>
              <span className="text-zinc-200">{contextSize}</span>
            </div>
            <select
              value={contextSize}
              onChange={(e) => setContextSize(parseInt(e.target.value))}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700"
            >
              <option value={2048}>2048 Tokens</option>
              <option value={4096}>4096 Tokens (Recommended)</option>
              <option value={8192}>8192 Tokens</option>
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3 pt-3 border-t border-zinc-800">
          {!isLoaded ? (
            <button
              onClick={handleStart}
              disabled={actionLoading}
              className="px-4 py-2 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-black font-semibold text-xs flex items-center space-x-1.5 transition font-mono"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>START AI ENGINE</span>
            </button>
          ) : (
            <button
              onClick={handleStop}
              disabled={actionLoading}
              className="px-4 py-2 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-amber-400 font-semibold text-xs flex items-center space-x-1.5 transition border border-zinc-700 font-mono"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>STOP AI ENGINE</span>
            </button>
          )}

          <button
            onClick={onRefreshStatus}
            className="px-3 py-2 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs flex items-center space-x-1.5 border border-zinc-800 transition font-mono"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Check State</span>
          </button>

          {actionMessage && (
            <span className="text-xs font-mono text-zinc-400 italic">
              {actionMessage}
            </span>
          )}
        </div>
      </div>

      {/* Hardware & Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Host Specs */}
        <div className="p-5 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-3">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-zinc-400">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span>HOST HARDWARE DETECTED</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">CPU Logic Cores:</span>
              <span className="text-zinc-200">{status?.hardware?.cpu_cores ?? 'N/A'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">System RAM Total:</span>
              <span className="text-zinc-200">{status?.hardware?.ram_total_gb ?? 'N/A'} GB</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">System RAM Available:</span>
              <span className="text-zinc-200">{status?.hardware?.ram_available_gb ?? 'N/A'} GB</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">Platform OS:</span>
              <span className="text-zinc-200">{status?.hardware?.platform ?? 'Windows'}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-zinc-500">App Root (USB):</span>
              <span className="text-zinc-300 truncate max-w-[220px]" title={status?.app_root}>
                {status?.app_root ?? 'D:/simlab-ai'}
              </span>
            </div>
          </div>
        </div>

        {/* Offline Security Audit */}
        <div className="p-5 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-3">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-zinc-400">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>OFFLINE & PRIVACY AUDIT</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">Internet Connection:</span>
              <span className="text-emerald-400 font-semibold">NOT REQUIRED</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">External Cloud APIs:</span>
              <span className="text-emerald-400 font-semibold">DISABLED</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">Telemetry & Analytics:</span>
              <span className="text-emerald-400 font-semibold">DISABLED</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-zinc-800/60">
              <span className="text-zinc-500">Knowledge Store:</span>
              <span className="text-zinc-200">Local SQLite (FTS5)</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-zinc-500">Inference Runtime:</span>
              <span className="text-zinc-200">Local llama.cpp (127.0.0.1)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
