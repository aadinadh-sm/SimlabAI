import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Copy,
  Check,
  StopCircle,
  Terminal,
  Bug,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { ChatMessage, Experiment } from '../types';
import { streamChat } from '../lib/api';

interface ChatPageProps {
  experiments: Experiment[];
  selectedExpContext: number | null;
  onSetExpContext: (num: number | null) => void;
}

interface DebugTrace {
  user_input: string;
  extracted_entities: any;
  inferred_topology_lines?: string[];
  user_connection_clauses?: string[];
  resolved_graph?: string[];
  topology_preview?: {
    ascii_diagram: string;
    edge_list_lines: string[];
    resolved_graph_lines: string[];
    user_connection_clauses: string[];
    formatted_preview: string;
  };
  requested_outputs?: {
    explicitly_requested: string[];
    effective_outputs: string[];
    all_fulfilled: boolean;
    fulfilled: Array<{ output_type: string; fulfilled: boolean; verification_detail: string }>;
    omitted: Array<{ output_type: string; fulfilled: boolean; verification_detail: string }>;
  };
  classified_circuit_type: string;
  classification_reason?: string;
  selected_experiment: number | null;
  topology_source: string;
  topology_classification?: 'EXACT MANUAL TOPOLOGY' | 'MODIFIED MANUAL TOPOLOGY' | 'GENERALIZED CIRCUIT' | string;
  user_confirmed: boolean;
  parameter_completeness?: {
    required_count: number;
    user_supplied_count: number;
    manual_default_count: number;
    missing_ambiguous_count: number;
    user_supplied: Array<{ id: string; value: string; manual_default?: string }>;
    manual_defaults: Array<{ id: string; value: string }>;
    missing_ambiguous: Array<{ id: string; description: string }>;
  };
  lifecycle_flags?: {
    TOPOLOGY_RECONSTRUCTED: boolean;
    TOPOLOGY_VALIDATED: boolean;
    SIMULATION_EXECUTED: boolean;
    SIMULATION_SUCCESSFUL: boolean;
    REQUESTED_OUTPUTS_FULFILLED?: boolean;
    TASK_COMPLETED?: boolean;
  };
  final_circuit_ir: any;
}

export const ChatPage: React.FC<ChatPageProps> = ({
  experiments,
  selectedExpContext,
  onSetExpContext
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello, I am **SimLab AI**, your offline simulation laboratory copilot.\n\n' +
        'I use a strict 8-stage deterministic pipeline: **Latest User Message → Entity Extraction → Circuit Classification → Manual Retrieval → Topology Template & Parameter Completeness → Parameter Substitution → Validation & Simulation → Code Generation**.\n\n' +
        'Every response includes a **Parameter Completeness Report** (`✓ User supplied`, `✓ Manual default`, `? Missing / ambiguous`) and clearly distinguishes **`EXACT MANUAL TOPOLOGY`**, **`MODIFIED MANUAL TOPOLOGY`**, and **`GENERALIZED CIRCUIT`**.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [contextMode, setContextMode] = useState<string>('CIRCUIT');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showDebugPanel, setShowDebugPanel] = useState<boolean>(true);
  const [latestDebugTrace, setLatestDebugTrace] = useState<DebugTrace | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const quickPrompts: { label: string; exp: number | null; prompt: string }[] = [
    {
      label: 'NL Junction: 20V, R1 2k & R2 1k series, R3 3.3k at junction',
      exp: null,
      prompt:
        'make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages'
    },
    {
      label: 'Exp 4 Partial: 12V, 5kΩ and 2µF',
      exp: null,
      prompt: '12V, 5kΩ and 2µF'
    },
    {
      label: 'GENERAL_RC: Simple RC (12V, 5kΩ, 2µF)',
      exp: null,
      prompt: 'Simple RC circuit with 12V, 5kΩ and 2µF'
    },
    {
      label: 'Exp 2: CCCS (24V, 10Ω, 5Ω, 3Ω, 8Ω, 2A)',
      exp: null,
      prompt: 'CCCS circuit with 24V source, 10Ω, 5Ω, 3Ω, 8Ω resistors and 2A current source'
    },
    {
      label: 'Exp 3: VCVS (40V, 4Ω, 6Ω, 2Ω, 8Ω, 12Ω)',
      exp: null,
      prompt: 'VCVS circuit with 40V source and 4Ω, 6Ω, 2Ω, 8Ω, 12Ω resistors with gain 3'
    },
    {
      label: 'Exp 1:Exact Manual Defaults',
      exp: null,
      prompt: 'Simulate Experiment 1 resistor bridge circuit'
    },
    {
      label: 'Ambiguous: Unspecified Topology',
      exp: null,
      prompt: 'I have a 15V voltage source and three resistors: 10Ω, 20Ω, 30Ω'
    }
  ];

  const handleSend = (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      experiment_id: selectedExpContext || undefined
    };

    const botMsgId = (Date.now() + 1).toString();
    const botMsg: ChatMessage = {
      id: botMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      experiment_id: selectedExpContext || undefined
    };

    setMessages((prev) => [...prev, userMsg, botMsg]);
    setInput('');
    setIsStreaming(true);

    const apiMessages = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content
    }));

    streamChat(
      apiMessages,
      selectedExpContext,
      (chunk) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMsgId ? { ...msg, content: msg.content + chunk } : msg
          )
        );
      },
      () => {
        setIsStreaming(false);
      },
      (err) => {
        console.error(err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMsgId
              ? {
                  ...msg,
                  content:
                    msg.content +
                    '\n\n*[Offline Notice: Ensure local server is running at :8000]*'
                }
              : msg
          )
        );
        setIsStreaming(false);
      },
      (trace) => {
        setLatestDebugTrace(trace);
      }
    );
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-100 select-text">
      {/* Top Context Control Bar */}
      <div className="h-12 border-b border-zinc-800 px-5 flex items-center justify-between text-xs font-mono shrink-0">
        <div className="flex items-center space-x-3">
          <span className="text-zinc-500">CONTEXT:</span>
          <select
            value={selectedExpContext || ''}
            onChange={(e) =>
              onSetExpContext(e.target.value ? parseInt(e.target.value) : null)
            }
            className="bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1 text-zinc-200 focus:outline-none focus:border-zinc-700"
          >
            <option value="">[Auto-Classify from Prompt]</option>
            {experiments.map((exp) => (
              <option key={exp.exp_number} value={exp.exp_number}>
                Exp {exp.exp_number}: {exp.title.slice(0, 35)}...
              </option>
            ))}
          </select>

          <span className="text-zinc-600">|</span>

          <div className="flex items-center space-x-1">
            {['GENERAL', 'EXPERIMENT', 'CIRCUIT', 'CODE', 'VIVA'].map((mode) => (
              <button
                key={mode}
                onClick={() => setContextMode(mode)}
                className={`px-2 py-0.5 rounded transition ${
                  contextMode === mode
                    ? 'bg-zinc-800 text-emerald-400 border border-zinc-700'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowDebugPanel(!showDebugPanel)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded border text-[11px] font-mono transition ${
              showDebugPanel
                ? 'bg-emerald-950/60 border-emerald-700/70 text-emerald-300'
                : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Bug className="w-3.5 h-3.5" />
            <span>{showDebugPanel ? 'Hide Debug Panel' : 'Show Debug Panel'}</span>
          </button>
        </div>
      </div>

      {/* Main Split Content Area: Chat + Live Pipeline Debug Panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Chat Stream + Input */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-5 max-w-4xl w-full mx-auto">
            {messages.map((m) => {
              const isUser = m.role === 'user';
              return (
                <div
                  key={m.id}
                  className={`flex items-start space-x-3 ${
                    isUser ? 'flex-row-reverse space-x-reverse' : ''
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded flex items-center justify-center shrink-0 border ${
                      isUser
                        ? 'bg-zinc-800 border-zinc-700 text-zinc-300'
                        : 'bg-zinc-900 border-zinc-800 text-emerald-400'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`group relative max-w-2xl rounded-lg p-4 text-xs leading-relaxed ${
                      isUser
                        ? 'bg-zinc-900 border border-zinc-800 text-zinc-100'
                        : 'bg-zinc-900/60 border border-zinc-800/80 text-zinc-200'
                    }`}
                  >
                    <button
                      onClick={() => handleCopy(m.id, m.content)}
                      className="absolute right-2 top-2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-zinc-800 text-zinc-400 transition"
                      title="Copy message"
                    >
                      {copiedId === m.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>

                    <div className="whitespace-pre-wrap font-sans space-y-2">
                      {m.content || (isStreaming ? <span className="animate-pulse">Thinking...</span> : '')}
                    </div>

                    {/* Interactive [Confirm & Simulate] and [Edit Circuit] Buttons for Reconstructed Topologies */}
                    {m.content.includes('[TOPOLOGY PREVIEW BEFORE SIMULATION]') && !isStreaming && (
                      <div className="mt-3 pt-3 border-t border-zinc-800/80 flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono text-emerald-400 font-semibold uppercase tracking-wider">
                          Topology Actions:
                        </span>
                        <button
                          onClick={() => handleSend('Confirm & Simulate this topology')}
                          className="px-2.5 py-1 bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-600/60 text-emerald-300 rounded text-[11px] font-mono transition"
                        >
                          [Confirm &amp; Simulate]
                        </button>
                        <button
                          onClick={() =>
                            setInput(
                              latestDebugTrace?.user_input ||
                                'Modify circuit connections: '
                            )
                          }
                          className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 rounded text-[11px] font-mono transition"
                        >
                          [Edit Circuit]
                        </button>
                      </div>
                    )}

                    {/* Interactive Candidate Buttons for Ambiguous Topologies */}
                    {m.content.includes('Candidate Topologies Using Your Exact Component Values') && !isStreaming && (
                      <div className="mt-3 pt-3 border-t border-zinc-800/80 flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono text-emerald-400 font-semibold uppercase tracking-wider">
                          Confirm Topology:
                        </span>
                        <button
                          onClick={() => handleSend('Confirm Candidate A')}
                          className="px-2.5 py-1 bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-600/60 text-emerald-300 rounded text-[11px] font-mono transition"
                        >
                          Confirm Candidate A (Series)
                        </button>
                        <button
                          onClick={() => handleSend('Confirm Candidate B')}
                          className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 rounded text-[11px] font-mono transition"
                        >
                          Confirm Candidate B (Parallel)
                        </button>
                        {m.content.includes('Candidate C') && (
                          <button
                            onClick={() => handleSend('Confirm Candidate C')}
                            className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 rounded text-[11px] font-mono transition"
                          >
                            Confirm Candidate C (Bridge)
                          </button>
                        )}
                      </div>
                    )}

                    {/* Interactive Resolution Buttons for Partial RC Prompts (Experiment 4 vs GENERAL_RC) */}
                    {m.content.includes('AMBIGUITY RESOLUTION OPTIONS (Manual Multi-Switch vs `GENERAL_RC`)') && !isStreaming && (
                      <div className="mt-3 pt-3 border-t border-zinc-800/80 flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono text-amber-400 font-semibold uppercase tracking-wider">
                          Resolve RC Mapping:
                        </span>
                        <button
                          onClick={() => handleSend('Confirm Experiment 4 with R1')}
                          className="px-2.5 py-1 bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-600/60 text-emerald-300 rounded text-[11px] font-mono transition"
                        >
                          Keep Modified Exp 4 (R1 Mapped)
                        </button>
                        <button
                          onClick={() => handleSend('Map 5kΩ to R2 in Experiment 4')}
                          className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 rounded text-[11px] font-mono transition"
                        >
                          Map Resistor to R2 (Discharge)
                        </button>
                        <button
                          onClick={() => handleSend('Switch to GENERAL_RC circuit')}
                          className="px-2.5 py-1 bg-cyan-950/70 hover:bg-cyan-900 border border-cyan-600/60 text-cyan-300 rounded text-[11px] font-mono transition"
                        >
                          Switch to GENERAL_RC (Generalized Circuit)
                        </button>
                      </div>
                    )}

                    <div className="mt-2 pt-2 border-t border-zinc-800/50 flex items-center justify-between text-[10px] font-mono text-zinc-500">
                      <span>{m.timestamp}</span>
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Chips */}
          <div className="px-6 py-2 border-t border-zinc-900 max-w-4xl w-full mx-auto flex items-center space-x-2 overflow-x-auto no-scrollbar">
            <span className="text-[10px] font-mono text-zinc-500 uppercase shrink-0">
              TEST PROMPTS:
            </span>
            {quickPrompts.map((qp) => (
              <button
                key={qp.label}
                onClick={() => {
                  onSetExpContext(qp.exp);
                  handleSend(qp.prompt);
                }}
                className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] text-zinc-300 hover:text-emerald-400 whitespace-nowrap transition"
              >
                {qp.label}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-4 border-t border-zinc-800 bg-zinc-950 shrink-0">
            <div className="max-w-4xl mx-auto flex items-center space-x-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Enter circuit prompt (e.g., '12V, 5kΩ and 2µF' or 'CCCS circuit with 24V source, 10Ω, 5Ω, 3Ω, 8Ω resistors and 2A current source')..."
                rows={2}
                className="flex-1 p-2.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-700 resize-none font-sans"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isStreaming}
                className="h-14 px-5 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:hover:bg-zinc-800 border border-zinc-700 text-emerald-400 hover:text-emerald-300 transition flex items-center justify-center font-mono text-xs"
              >
                {isStreaming ? (
                  <StopCircle className="w-4 h-4 animate-spin text-amber-400" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Deterministic Pipeline Debug Panel */}
        {showDebugPanel && (
          <div className="w-96 border-l border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden shrink-0">
            <div className="h-10 px-4 border-b border-zinc-800 bg-zinc-900/60 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-2 text-emerald-400">
                <Terminal className="w-3.5 h-3.5" />
                <span className="font-bold">PIPELINE DEBUG INSPECTOR</span>
              </div>
              <span className="text-[10px] text-zinc-500">8-STAGE TRACE</span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-[11px]">
              {!latestDebugTrace ? (
                <div className="text-zinc-500 text-xs leading-relaxed p-3 border border-zinc-800/80 rounded bg-zinc-900/30">
                  Send a message to inspect the deterministic pipeline stages:
                  <ul className="mt-2 space-y-1 text-[11px] text-zinc-400 list-disc list-inside">
                    <li>1. USER INPUT (Latest Only)</li>
                    <li>2. EXTRACTED ENTITIES</li>
                    <li>3. CLASSIFIED CIRCUIT TYPE</li>
                    <li>4. TOPOLOGY DISTINCTION</li>
                    <li>5. PARAMETER COMPLETENESS</li>
                    <li>6. LIFECYCLE FLAGS</li>
                    <li>7. FINAL CIRCUIT IR</li>
                  </ul>
                </div>
              ) : (
                <>
                  {/* TOPOLOGY DISTINCTION BADGE */}
                  {latestDebugTrace.topology_classification && (
                    <div className="border border-zinc-800 rounded bg-zinc-900/60 p-2.5">
                      <div className="text-[10px] text-zinc-400 uppercase font-bold mb-1">
                        TOPOLOGY DISTINCTION
                      </div>
                      <span
                        className={`inline-block px-2 py-0.5 rounded font-bold text-[11px] border ${
                          latestDebugTrace.topology_classification === 'EXACT MANUAL TOPOLOGY'
                            ? 'bg-emerald-950/70 text-emerald-300 border-emerald-600/60'
                            : latestDebugTrace.topology_classification === 'MODIFIED MANUAL TOPOLOGY'
                            ? 'bg-amber-950/70 text-amber-300 border-amber-600/60'
                            : 'bg-cyan-950/70 text-cyan-300 border-cyan-600/60'
                        }`}
                      >
                        {latestDebugTrace.topology_classification}
                      </span>
                    </div>
                  )}

                  {/* 1. USER INPUT */}
                  <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5">
                    <div className="text-[10px] text-zinc-400 uppercase font-bold mb-1">
                      1. USER INPUT (LATEST MESSAGE ONLY)
                    </div>
                    <div className="text-zinc-100 break-words bg-zinc-950 p-2 rounded border border-zinc-800/60">
                      {latestDebugTrace.user_input}
                    </div>
                  </div>

                  {/* 2. EXTRACTED ENTITIES */}
                  <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5">
                    <div className="text-[10px] text-emerald-400 uppercase font-bold mb-1">
                      2. EXTRACTED ENTITIES
                    </div>
                    <pre className="text-zinc-200 bg-zinc-950 p-2 rounded border border-zinc-800/60 overflow-x-auto text-[10px]">
                      {JSON.stringify(latestDebugTrace.extracted_entities, null, 2)}
                    </pre>
                  </div>

                  {/* INTERMEDIATE TOPOLOGY GRAPH: USER CONNECTION CLAUSES & RESOLVED GRAPH */}
                  {(latestDebugTrace.user_connection_clauses?.length ||
                    latestDebugTrace.resolved_graph?.length) ? (
                    <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5 space-y-2">
                      <div>
                        <span className="text-[10px] text-cyan-400 uppercase font-bold block mb-1">
                          USER CONNECTION CLAUSES
                        </span>
                        <div className="bg-zinc-950 p-2 rounded border border-zinc-800/60 space-y-0.5 text-[10px] text-zinc-200">
                          {(latestDebugTrace.user_connection_clauses || []).map((cl, i) => (
                            <div key={i}>- {cl}</div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] text-emerald-400 uppercase font-bold block mb-1">
                          RESOLVED GRAPH
                        </span>
                        <div className="bg-zinc-950 p-2 rounded border border-zinc-800/60 space-y-0.5 text-[10px] text-emerald-300">
                          {(latestDebugTrace.resolved_graph || []).map((rg, i) => (
                            <div key={i}>- {rg}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {/* 3. CLASSIFIED CIRCUIT TYPE & 4. SELECTED EXPERIMENT & 5. TOPOLOGY SOURCE */}
                  <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5 space-y-2">
                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase font-bold block">
                        3. CLASSIFIED CIRCUIT TYPE
                      </span>
                      <span className="text-amber-300 font-bold">
                        {latestDebugTrace.classified_circuit_type}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase font-bold block">
                        4. SELECTED EXPERIMENT
                      </span>
                      <span className="text-emerald-300 font-bold">
                        {latestDebugTrace.selected_experiment !== null
                          ? `Experiment ${latestDebugTrace.selected_experiment}`
                          : 'None (Generalized / Non-Manual)'}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase font-bold block">
                        5. TOPOLOGY SOURCE
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-cyan-300 border border-zinc-700">
                        {latestDebugTrace.topology_source}
                      </span>
                      <span className="ml-2 text-zinc-400">
                        user_confirmed: {String(latestDebugTrace.user_confirmed)}
                      </span>
                    </div>
                  </div>

                  {/* PARAMETER COMPLETENESS REPORT */}
                  {latestDebugTrace.parameter_completeness && (
                    <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5 space-y-1.5">
                      <div className="text-[10px] text-zinc-400 uppercase font-bold">
                        PARAMETER COMPLETENESS ({latestDebugTrace.parameter_completeness.required_count} REQ)
                      </div>
                      <div className="flex items-center justify-between bg-zinc-950 px-2 py-1 rounded border border-zinc-800/60 text-[10px]">
                        <span className="text-emerald-400">✓ User supplied</span>
                        <span className="font-bold text-emerald-300">
                          {latestDebugTrace.parameter_completeness.user_supplied_count}
                        </span>
                      </div>
                      <div className="flex items-center justify-between bg-zinc-950 px-2 py-1 rounded border border-zinc-800/60 text-[10px]">
                        <span className="text-cyan-400">✓ Manual default</span>
                        <span className="font-bold text-cyan-300">
                          {latestDebugTrace.parameter_completeness.manual_default_count}
                        </span>
                      </div>
                      <div className="flex items-center justify-between bg-zinc-950 px-2 py-1 rounded border border-zinc-800/60 text-[10px]">
                        <span className="text-amber-400">? Missing / ambiguous</span>
                        <span className="font-bold text-amber-300">
                          {latestDebugTrace.parameter_completeness.missing_ambiguous_count}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* REQUESTED OUTPUTS & FULFILLMENT */}
                  {latestDebugTrace.requested_outputs && (
                    <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5 space-y-1.5">
                      <div className="text-[10px] text-zinc-400 uppercase font-bold">
                        REQUESTED OUTPUTS ({latestDebugTrace.requested_outputs.effective_outputs?.length || 0})
                      </div>
                      <div className="bg-zinc-950 px-2 py-1 rounded border border-zinc-800/60 text-[10px] text-zinc-300">
                        <span className="text-zinc-500">Explicit: </span>
                        {latestDebugTrace.requested_outputs.explicitly_requested?.length
                          ? latestDebugTrace.requested_outputs.explicitly_requested.join(', ')
                          : 'Default for topology'}
                      </div>
                      <div className="bg-zinc-950 px-2 py-1 rounded border border-zinc-800/60 text-[10px] text-emerald-300">
                        <span className="text-zinc-500">Active: </span>
                        {latestDebugTrace.requested_outputs.effective_outputs?.join(', ')}
                      </div>
                    </div>
                  )}

                  {/* LIFECYCLE FLAGS */}
                  {latestDebugTrace.lifecycle_flags && (
                    <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5">
                      <div className="text-[10px] text-zinc-400 uppercase font-bold mb-1.5">
                        VALIDATION & SIMULATION LIFECYCLE
                      </div>
                      <div className="grid grid-cols-1 gap-1 text-[10px]">
                        {Object.entries(latestDebugTrace.lifecycle_flags).map(([k, v]) => (
                          <div
                            key={k}
                            className="flex items-center justify-between bg-zinc-950 px-2 py-1 rounded border border-zinc-800/60"
                          >
                            <span className="text-zinc-300">{k}</span>
                            <span
                              className={`font-bold ${
                                v ? 'text-emerald-400' : 'text-zinc-500'
                              }`}
                            >
                              {String(v).toUpperCase()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 6. FINAL CIRCUIT IR */}
                  <div className="border border-zinc-800 rounded bg-zinc-900/40 p-2.5">
                    <div className="text-[10px] text-purple-400 uppercase font-bold mb-1">
                      6. FINAL CIRCUIT IR
                    </div>
                    <pre className="text-zinc-200 bg-zinc-950 p-2 rounded border border-zinc-800/60 overflow-x-auto text-[10px] max-h-72">
                      {latestDebugTrace.final_circuit_ir
                        ? JSON.stringify(latestDebugTrace.final_circuit_ir, null, 2)
                        : 'null (Waiting for topology clarification)'}
                    </pre>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
