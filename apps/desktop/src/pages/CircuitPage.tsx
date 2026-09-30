import React, { useState } from 'react';
import {
  Cpu,
  Play,
  RotateCcw,
  Plus,
  Trash2,
  Table,
  CheckCircle2
} from 'lucide-react';

interface GateNode {
  id: string;
  type: 'AND' | 'OR' | 'NOT' | 'NAND' | 'NOR' | 'XOR' | 'XNOR';
  inputs: [number, number];
  output: number;
}

export const CircuitPage: React.FC = () => {
  const [selectedGate, setSelectedGate] = useState<string>('AND');
  const [inputA, setInputA] = useState<number>(0);
  const [inputB, setInputB] = useState<number>(0);
  const [inputC, setInputC] = useState<number>(0);

  // Digital Logic evaluation
  const evaluateGate = (type: string, a: number, b: number): number => {
    switch (type) {
      case 'AND': return a & b;
      case 'OR': return a | b;
      case 'NOT': return a === 0 ? 1 : 0;
      case 'NAND': return (a & b) === 0 ? 1 : 0;
      case 'NOR': return (a | b) === 0 ? 1 : 0;
      case 'XOR': return a ^ b;
      case 'XNOR': return (a ^ b) === 0 ? 1 : 0;
      default: return 0;
    }
  };

  const outputVal = evaluateGate(selectedGate, inputA, inputB);

  // Exp 8: Half Adder & Full Adder evaluations
  const halfAdderSum = inputA ^ inputB;
  const halfAdderCarry = inputA & inputB;

  const fullAdderSum = inputA ^ inputB ^ inputC;
  const fullAdderCarry = (inputA & inputB) | (inputB & inputC) | (inputA & inputC);

  // Exp 10: NAND-only F = AB + BC + AC
  const nandF = (inputA & inputB) | (inputB & inputC) | (inputA & inputC);

  const gates = ['AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR'];

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6 select-text">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-emerald-400" />
            <span>Circuit Lab: Digital Logic Engine (Multisim Equiv.)</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Deterministic digital circuit simulation, gate verification, and truth table generator.
          </p>
        </div>

        {/* Gate Palette Selector */}
        <div className="flex items-center space-x-1 bg-zinc-900 border border-zinc-800 rounded p-1">
          {gates.map((g) => (
            <button
              key={g}
              onClick={() => setSelectedGate(g)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition ${
                selectedGate === g
                  ? 'bg-zinc-800 text-emerald-400 font-bold border border-zinc-700'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Gate Workbench */}
        <div className="p-6 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-5">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              GATE EVALUATION: {selectedGate}
            </span>
            <span className="text-[11px] font-mono text-emerald-400">Live State</span>
          </div>

          {/* Interactive Switches */}
          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-400">INPUT A:</span>
              <button
                onClick={() => setInputA(inputA === 0 ? 1 : 0)}
                className={`px-4 py-1.5 rounded font-bold transition ${
                  inputA === 1
                    ? 'bg-emerald-500 text-black shadow-sm'
                    : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                }`}
              >
                {inputA} (Logic {inputA === 1 ? 'HIGH' : 'LOW'})
              </button>
            </div>

            {selectedGate !== 'NOT' && (
              <div className="flex items-center justify-between p-3 rounded bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400">INPUT B:</span>
                <button
                  onClick={() => setInputB(inputB === 0 ? 1 : 0)}
                  className={`px-4 py-1.5 rounded font-bold transition ${
                    inputB === 1
                      ? 'bg-emerald-500 text-black shadow-sm'
                      : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                  }`}
                >
                  {inputB} (Logic {inputB === 1 ? 'HIGH' : 'LOW'})
                </button>
              </div>
            )}

            {/* Output LED */}
            <div className="flex items-center justify-between p-4 rounded bg-zinc-950 border border-zinc-800 mt-4">
              <span className="text-zinc-300 font-semibold">OUTPUT {selectedGate}:</span>
              <div className="flex items-center space-x-2">
                <span
                  className={`w-3.5 h-3.5 rounded-full ${
                    outputVal === 1 ? 'bg-emerald-400 shadow-md shadow-emerald-500/50 animate-pulse' : 'bg-zinc-700'
                  }`}
                />
                <span className="text-base font-bold text-zinc-100">{outputVal}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Truth Table Generator */}
        <div className="p-6 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-zinc-400 border-b border-zinc-800 pb-2">
            <Table className="w-3.5 h-3.5 text-emerald-400" />
            <span>VERIFIED TRUTH TABLE ({selectedGate})</span>
          </div>

          <table className="w-full text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="py-2 text-left">A</th>
                {selectedGate !== 'NOT' && <th className="py-2 text-left">B</th>}
                <th className="py-2 text-right">OUTPUT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {selectedGate === 'NOT' ? (
                [0, 1].map((a) => (
                  <tr
                    key={a}
                    className={inputA === a ? 'bg-zinc-800/60 text-emerald-400 font-semibold' : 'text-zinc-300'}
                  >
                    <td className="py-2">{a}</td>
                    <td className="py-2 text-right">{evaluateGate('NOT', a, 0)}</td>
                  </tr>
                ))
              ) : (
                [
                  [0, 0],
                  [0, 1],
                  [1, 0],
                  [1, 1]
                ].map(([a, b]) => {
                  const isActive = inputA === a && inputB === b;
                  return (
                    <tr
                      key={`${a}-${b}`}
                      className={isActive ? 'bg-zinc-800/60 text-emerald-400 font-semibold' : 'text-zinc-300'}
                    >
                      <td className="py-2">{a}</td>
                      <td className="py-2">{b}</td>
                      <td className="py-2 text-right">{evaluateGate(selectedGate, a, b)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Combinational Adders (Exp 8) */}
        <div className="p-6 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              EXP 8: ADDERS TEST
            </span>
            <span className="text-[10px] font-mono text-zinc-500">Multisim Logic</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded bg-zinc-950 border border-zinc-850 space-y-1">
              <span className="text-zinc-400 block font-semibold">Half Adder (Inputs A={inputA}, B={inputB}):</span>
              <div className="flex justify-between text-zinc-300 pt-1">
                <span>SUM (A XOR B): <strong className="text-emerald-400">{halfAdderSum}</strong></span>
                <span>CARRY (A AND B): <strong className="text-emerald-400">{halfAdderCarry}</strong></span>
              </div>
            </div>

            <div className="p-3 rounded bg-zinc-950 border border-zinc-850 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400 font-semibold">Full Adder:</span>
                <button
                  onClick={() => setInputC(inputC === 0 ? 1 : 0)}
                  className="px-2 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-300"
                >
                  Cin: {inputC}
                </button>
              </div>
              <div className="flex justify-between text-zinc-300 pt-1">
                <span>SUM: <strong className="text-emerald-400">{fullAdderSum}</strong></span>
                <span>CARRY: <strong className="text-emerald-400">{fullAdderCarry}</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
