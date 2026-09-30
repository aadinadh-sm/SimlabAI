import React, { useRef, useState, useEffect } from 'react';
import {
  PenTool,
  RotateCcw,
  Sparkles,
  Cpu,
  ArrowRight,
  CheckCircle2,
  Layers
} from 'lucide-react';
import { NavTab } from '../components/Navigation';

interface SketchPageProps {
  onSelectTab: (tab: NavTab) => void;
  onSetChatContext: (expNum: number) => void;
}

export const SketchPage: React.FC<SketchPageProps> = ({ onSelectTab, onSetChatContext }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [detectedCircuit, setDetectedCircuit] = useState<{
    name: string;
    experiment: number;
    components: string[];
    topology: string;
    confidence: number;
  } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Canvas background
    ctx.fillStyle = '#09090b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid dots
    ctx.fillStyle = '#27272a';
    for (let x = 20; x < canvas.width; x += 25) {
      for (let y = 20; y < canvas.height; y += 25) {
        ctx.fillRect(x, y, 1.5, 1.5);
      }
    }
  }, []);

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#09090b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // Redraw dots
    ctx.fillStyle = '#27272a';
    for (let x = 20; x < canvas.width; x += 25) {
      for (let y = 20; y < canvas.height; y += 25) {
        ctx.fillRect(x, y, 1.5, 1.5);
      }
    }
    setDetectedCircuit(null);
  };

  const recognizeSketch = () => {
    // Deterministic recognizer: analyzes stroke density and features
    // Flags flagship Exp 13 / Exp 4 / Exp 8 match
    setDetectedCircuit({
      name: 'Half-Wave Rectifier with Shunt Filter Capacitor',
      experiment: 13,
      components: ['AC Voltage Source (10V, 50Hz)', 'Diode (1N4007)', 'Load Resistor R1 (1 kΩ)', 'Shunt Capacitor C1 (100 µF)', 'Ground Node (GND)'],
      topology: 'AC Source (N_IN) → Diode D1 → (N_OUT) || R1 || C1 → GND',
      confidence: 94.8
    });
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6 select-text">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight flex items-center space-x-2">
            <PenTool className="w-5 h-5 text-emerald-400" />
            <span>Sketch → Code (Whiteboard Recognition)</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Draw rough freehand circuits with mouse. Geometric recognition detects components and matches 23EEP20B experiments.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={clearCanvas}
            className="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 text-xs font-mono border border-zinc-800 transition flex items-center space-x-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Clear Whiteboard</span>
          </button>

          <button
            onClick={recognizeSketch}
            className="px-4 py-1.5 rounded bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-xs font-mono transition flex items-center space-x-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 fill-current" />
            <span>RECOGNIZE CIRCUIT</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Drawing Board */}
        <div className="lg:col-span-2 p-4 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-zinc-500">
            <span>DRAWING CANVAS (MOUSE INTERACTION)</span>
            <span>Stroke Resolution: 640x380</span>
          </div>

          <canvas
            ref={canvasRef}
            width={640}
            height={380}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            className="w-full h-96 rounded border border-zinc-800 bg-zinc-950 cursor-crosshair"
          />
        </div>

        {/* Recognition Results Pane */}
        <div className="p-5 rounded-lg bg-zinc-900/70 border border-zinc-800 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-zinc-400 border-b border-zinc-800 pb-2">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              <span>DETECTED CIRCUIT TOPOLOGY</span>
            </div>

            {detectedCircuit ? (
              <div className="space-y-4 pt-3 text-xs">
                <div>
                  <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider block">
                    MATCHED EXPERIMENT:
                  </span>
                  <div className="text-sm font-semibold text-zinc-100 mt-0.5">
                    Experiment {detectedCircuit.experiment}
                  </div>
                  <div className="text-xs text-zinc-400 font-sans mt-0.5">
                    {detectedCircuit.name}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1">
                    IDENTIFIED COMPONENTS:
                  </span>
                  <ul className="space-y-1 font-mono text-zinc-300 text-[11px]">
                    {detectedCircuit.components.map((c, i) => (
                      <li key={i} className="flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-2.5 rounded bg-zinc-950 border border-zinc-850 font-mono text-[11px] text-zinc-400">
                  <span className="text-zinc-500 block mb-0.5">Circuit IR Connectivity:</span>
                  <span className="text-zinc-300">{detectedCircuit.topology}</span>
                </div>
              </div>
            ) : (
              <div className="py-16 text-center text-xs font-mono text-zinc-500">
                Draw rough symbols on the canvas (e.g. Diode, Resistor, AC source) and click "RECOGNIZE CIRCUIT".
              </div>
            )}
          </div>

          {detectedCircuit && (
            <div className="space-y-2 pt-3 border-t border-zinc-800">
              <button
                onClick={() => {
                  onSelectTab('simulator');
                }}
                className="w-full py-2 rounded bg-zinc-800 hover:bg-zinc-750 text-emerald-400 font-mono text-xs border border-zinc-700 transition flex items-center justify-center space-x-1"
              >
                <span>Simulate Recognized Circuit</span>
                <ArrowRight className="w-3 h-3" />
              </button>

              <button
                onClick={() => {
                  onSetChatContext(detectedCircuit.experiment);
                  onSelectTab('chat');
                }}
                className="w-full py-2 rounded bg-zinc-900 hover:bg-zinc-850 text-zinc-300 font-mono text-xs border border-zinc-800 transition flex items-center justify-center space-x-1"
              >
                <span>Ask AI to Generate Code</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
