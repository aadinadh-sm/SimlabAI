import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Search,
  MessageSquare,
  GraduationCap,
  Play,
  Copy,
  Check,
  ChevronRight,
  ExternalLink,
  Code,
  FileCheck
} from 'lucide-react';
import { Experiment } from '../types';
import { fetchExperiment } from '../lib/api';
import { NavTab } from '../components/Navigation';

interface ExperimentsPageProps {
  experiments: Experiment[];
  selectedExpNum: number;
  onSelectExpNum: (num: number) => void;
  onSelectTab: (tab: NavTab) => void;
  onSetChatContext: (expNum: number) => void;
}

export const ExperimentsPage: React.FC<ExperimentsPageProps> = ({
  experiments,
  selectedExpNum,
  onSelectExpNum,
  onSelectTab,
  onSetChatContext
}) => {
  const [detail, setDetail] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  useEffect(() => {
    if (selectedExpNum) {
      setLoading(true);
      fetchExperiment(selectedExpNum)
        .then((data) => setDetail(data))
        .catch((err) => console.error(err))
        .finally(() => setLoading(false));
    }
  }, [selectedExpNum]);

  const categories = ['All', 'Analog / PySpice', 'Transient / RC', 'Digital Logic', 'Digital Combinational', 'Boolean Algebra', 'Semiconductor / Analog', 'Power Electronics'];

  const filteredExperiments = experiments.filter((exp) => {
    const matchesCategory = selectedCategory === 'All' || exp.category.includes(selectedCategory);
    const matchesQuery =
      exp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      exp.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())) ||
      exp.exp_number.toString() === searchQuery.trim();
    return matchesCategory && matchesQuery;
  });

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="flex h-full overflow-hidden select-text">
      {/* Left List Pane */}
      <div className="w-80 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0">
        {/* Search & Category Filter */}
        <div className="p-3 border-b border-zinc-800 space-y-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-zinc-500" />
            <input
              type="text"
              placeholder="Search experiments or topics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
            />
          </div>

          <div className="flex items-center space-x-1 overflow-x-auto pb-1 text-[10px] font-mono no-scrollbar">
            {categories.slice(0, 4).map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2 py-0.5 rounded whitespace-nowrap transition ${
                  selectedCategory === cat
                    ? 'bg-zinc-800 text-emerald-400 border border-zinc-700'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Experiment Items */}
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-900">
          {filteredExperiments.map((exp) => {
            const isSelected = exp.exp_number === selectedExpNum;
            return (
              <button
                key={exp.exp_number}
                onClick={() => onSelectExpNum(exp.exp_number)}
                className={`w-full text-left p-3.5 transition flex flex-col justify-between ${
                  isSelected
                    ? 'bg-zinc-900/90 border-l-2 border-emerald-400 text-zinc-100'
                    : 'hover:bg-zinc-900/40 text-zinc-400'
                }`}
              >
                <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                  <span className={isSelected ? 'text-emerald-400 font-semibold' : 'text-zinc-500'}>
                    EXP {exp.exp_number}
                  </span>
                  <span className="text-zinc-500">{exp.pages}</span>
                </div>
                <div className="text-xs font-medium line-clamp-2 leading-relaxed text-zinc-200">
                  {exp.title}
                </div>
                <div className="text-[10px] text-zinc-500 font-mono mt-1.5">
                  {exp.software}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right Detail Pane */}
      <div className="flex-1 overflow-y-auto p-8 max-w-5xl bg-zinc-950">
        {loading ? (
          <div className="h-64 flex items-center justify-center text-xs font-mono text-zinc-500">
            Loading experiment data...
          </div>
        ) : detail ? (
          <div className="space-y-6">
            {/* Header info */}
            <div className="border-b border-zinc-800 pb-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700 text-emerald-400">
                  EXPERIMENT {detail.exp_number}
                </span>
                <span className="text-xs font-mono text-zinc-500">
                  Manual Citation: {detail.pages_text}
                </span>
              </div>
              <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
                {detail.title}
              </h1>

              {/* Action Toolbar */}
              <div className="flex items-center space-x-3 mt-4 pt-3 border-t border-zinc-900 text-xs">
                <button
                  onClick={() => {
                    onSetChatContext(detail.exp_number);
                    onSelectTab('chat');
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 transition"
                >
                  <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Ask AI About This Experiment</span>
                </button>

                <button
                  onClick={() => {
                    onSelectTab('viva');
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 transition"
                >
                  <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Start Viva Test</span>
                </button>

                <button
                  onClick={() => {
                    onSelectTab('simulator');
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 transition"
                >
                  <Play className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Simulate Circuit</span>
                </button>
              </div>
            </div>

            {/* Aim */}
            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/80">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1.5">
                AIM
              </h3>
              <p className="text-sm text-zinc-200 leading-relaxed">{detail.aim}</p>
            </div>

            {/* Software / Apparatus */}
            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/80">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1.5">
                APPARATUS / SOFTWARE REQUIRED
              </h3>
              <p className="text-xs font-mono text-zinc-300">{detail.software}</p>
            </div>

            {/* Official Circuit Diagrams / Scans */}
            {detail.diagram_images && detail.diagram_images.length > 0 && (
              <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/80 space-y-3">
                <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                  OFFICIAL MANUAL DIAGRAMS & SCHEMATICS
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {detail.diagram_images.map((imgName, i) => (
                    <div key={imgName} className="rounded border border-zinc-800 bg-black/40 overflow-hidden">
                      <div className="px-3 py-1.5 bg-zinc-900/80 border-b border-zinc-800 text-[10px] font-mono text-zinc-400 flex items-center justify-between">
                        <span>Scan Page {detail.page_start + i}</span>
                        <a
                          href={`http://127.0.0.1:8000/api/images/${imgName}`}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-emerald-400 flex items-center space-x-1"
                        >
                          <span>Full View</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                      <img
                        src={`http://127.0.0.1:8000/api/images/${imgName}`}
                        alt={`Manual page ${detail.page_start + i}`}
                        className="w-full object-contain max-h-72 p-2 hover:scale-[1.02] transition-transform"
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Code Sample (PySpice / Python) */}
            {detail.code_sample && (
              <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/80 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400 flex items-center space-x-2">
                    <Code className="w-3.5 h-3.5 text-emerald-400" />
                    <span>MANUAL PYSPICE SIMULATION CODE</span>
                  </h3>
                  <button
                    onClick={() => handleCopyCode(detail.code_sample || '')}
                    className="flex items-center space-x-1 text-xs font-mono text-zinc-400 hover:text-zinc-200"
                  >
                    {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCode ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <pre className="p-3 rounded bg-black/60 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto leading-relaxed">
                  {detail.code_sample}
                </pre>
              </div>
            )}

            {/* Procedure */}
            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/80">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-2">
                DOCUMENTED PROCEDURE
              </h3>
              <div className="text-xs text-zinc-300 whitespace-pre-line leading-relaxed font-sans">
                {detail.procedure}
              </div>
            </div>

            {/* Result */}
            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/80">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center space-x-1.5">
                <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>EXPECTED RESULT</span>
              </h3>
              <p className="text-xs text-zinc-300 leading-relaxed font-mono">
                {detail.result}
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
