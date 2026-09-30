import React, { useState, useEffect, useRef } from 'react';
import {
  Activity,
  Play,
  RotateCcw,
  Sliders,
  TrendingUp,
  CheckCircle2,
  FileCode,
  Download
} from 'lucide-react';
import { Experiment } from '../types';

interface SimulatorPageProps {
  experiments: Experiment[];
}

export const SimulatorPage: React.FC<SimulatorPageProps> = ({ experiments }) => {
  const [selectedExp, setSelectedExp] = useState<number>(4);
  const [resistor, setResistor] = useState<number>(10000); // 10k ohm
  const [capacitance, setCapacitance] = useState<number>(0.000001); // 1 uF
  const [voltage, setVoltage] = useState<number>(10); // 10V
  const [frequency, setFrequency] = useState<number>(50); // 50 Hz
  const [filterCapacitor, setFilterCapacitor] = useState<boolean>(true);
  const [simResults, setSimResults] = useState<{
    tau?: number;
    vMax?: number;
    vMin?: number;
    vAvg?: number;
    ripple?: number;
  } | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const tau = resistor * capacitance;

  const runSimulation = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear background
    ctx.fillStyle = '#09090b';
    ctx.fillRect(0, 0, width, height);

    // Draw grid
    ctx.strokeStyle = '#27272a';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Zero Axis
    const centerY = height / 2;
    ctx.strokeStyle = '#3f3f46';
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();

    if (selectedExp === 4) {
      // Natural Response of RC Circuit: V(t) = V0 * exp(-t / tau)
      const tMax = 5 * tau;
      ctx.strokeStyle = '#34d399'; // Emerald
      ctx.lineWidth = 2.5;
      ctx.beginPath();

      for (let px = 0; px < width; px++) {
        const t = (px / width) * tMax;
        const v = voltage * Math.exp(-t / tau);
        const py = height - 40 - (v / voltage) * (height - 80);
        if (px === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();

      setSimResults({
        tau: parseFloat((tau * 1000).toFixed(2)),
        vMax: voltage,
        vMin: 0,
        vAvg: parseFloat((voltage * 0.368).toFixed(2))
      });
    } else if (selectedExp === 5) {
      // Step Response of RC Circuit: V(t) = Vin * (1 - exp(-t / tau))
      const tMax = 5 * tau;
      ctx.strokeStyle = '#38bdf8'; // Sky blue
      ctx.lineWidth = 2.5;
      ctx.beginPath();

      for (let px = 0; px < width; px++) {
        const t = (px / width) * tMax;
        const v = voltage * (1 - Math.exp(-t / tau));
        const py = height - 40 - (v / voltage) * (height - 80);
        if (px === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();

      setSimResults({
        tau: parseFloat((tau * 1000).toFixed(2)),
        vMax: voltage,
        vMin: 0,
        vAvg: parseFloat((voltage * 0.632).toFixed(2))
      });
    } else if (selectedExp === 13) {
      // Half-Wave Rectifier: with or without capacitor filter
      const periods = 3;
      const tMax = periods * (1 / frequency);
      ctx.strokeStyle = '#fbbf24'; // Amber
      ctx.lineWidth = 2;
      ctx.beginPath();

      let vCap = 0;
      const dt = tMax / width;
      let maxV = 0;
      let minV = voltage;
      let sumV = 0;

      for (let px = 0; px < width; px++) {
        const t = px * dt;
        const vAc = voltage * Math.sin(2 * Math.PI * frequency * t);
        let vOut = 0;

        if (filterCapacitor) {
          if (vAc - 0.7 > vCap) {
            vCap = vAc - 0.7;
          } else {
            vCap = vCap * Math.exp(-dt / (resistor * capacitance));
          }
          vOut = Math.max(0, vCap);
        } else {
          vOut = Math.max(0, vAc - 0.7);
        }

        if (vOut > maxV) maxV = vOut;
        if (vOut < minV) minV = vOut;
        sumV += vOut;

        const py = centerY - (vOut / voltage) * (height / 2 - 40);
        if (px === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();

      setSimResults({
        vMax: parseFloat(maxV.toFixed(2)),
        vMin: parseFloat(minV.toFixed(2)),
        vAvg: parseFloat((sumV / width).toFixed(2)),
        ripple: filterCapacitor
          ? parseFloat(((maxV - minV) / (sumV / width || 1)).toFixed(3))
          : 1.21
      });
    } else if (selectedExp === 14) {
      // Full-Wave Bridge Rectifier
      const periods = 3;
      const tMax = periods * (1 / frequency);
      ctx.strokeStyle = '#a78bfa'; // Purple
      ctx.lineWidth = 2;
      ctx.beginPath();

      let vCap = 0;
      const dt = tMax / width;
      let maxV = 0;
      let minV = voltage;
      let sumV = 0;

      for (let px = 0; px < width; px++) {
        const t = px * dt;
        const vAc = Math.abs(voltage * Math.sin(2 * Math.PI * frequency * t));
        let vOut = 0;

        if (filterCapacitor) {
          if (vAc - 1.4 > vCap) {
            vCap = vAc - 1.4;
          } else {
            vCap = vCap * Math.exp(-dt / (resistor * capacitance));
          }
          vOut = Math.max(0, vCap);
        } else {
          vOut = Math.max(0, vAc - 1.4);
        }

        if (vOut > maxV) maxV = vOut;
        if (vOut < minV) minV = vOut;
        sumV += vOut;

        const py = centerY - (vOut / voltage) * (height / 2 - 40);
        if (px === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();

      setSimResults({
        vMax: parseFloat(maxV.toFixed(2)),
        vMin: parseFloat(minV.toFixed(2)),
        vAvg: parseFloat((sumV / width).toFixed(2)),
        ripple: filterCapacitor
          ? parseFloat(((maxV - minV) / (sumV / width || 1)).toFixed(3))
          : 0.482
      });
    } else if (selectedExp === 11) {
      // PN Junction Diode I-V curve
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 2.5;
      ctx.beginPath();

      const Is = 1e-12; // 1 pA
      const Vt = 0.026; // 26 mV
      for (let px = 0; px < width; px++) {
        const v = (px / width) * 1.0; // 0 to 1V
        const i = Is * (Math.exp(v / (1.5 * Vt)) - 1);
        const py = height - 40 - Math.min(height - 60, (i / 0.05) * (height - 80));
        if (px === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();

      setSimResults({
        vMax: 0.7,
        vMin: 0,
        vAvg: 0.65
      });
    } else if (selectedExp === 12) {
      // Zener Diode Regulator
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 2.5;
      ctx.beginPath();

      const Vz = 5.1;
      for (let px = 0; px < width; px++) {
        const vIn = (px / width) * 20; // 0 to 20V
        const vOut = vIn < Vz ? vIn : Vz + (vIn - Vz) * 0.02; // regulation
        const py = height - 40 - (vOut / 20) * (height - 80);
        if (px === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();

      setSimResults({
        vMax: 5.1,
        vMin: 0,
        vAvg: 5.1
      });
    }
  };

  useEffect(() => {
    runSimulation();
  }, [selectedExp, resistor, capacitance, voltage, frequency, filterCapacitor]);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6 select-text">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight flex items-center space-x-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            <span>Local Simulation Workbench</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Deterministic numerical engine modeling PySpice and Simulink equivalent behavior.
          </p>
        </div>

        {/* Experiment Selector */}
        <select
          value={selectedExp}
          onChange={(e) => setSelectedExp(parseInt(e.target.value))}
          className="bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-700"
        >
          <option value={4}>Exp 4: RC Natural Response</option>
          <option value={5}>Exp 5: RC Step Response</option>
          <option value={11}>Exp 11: Diode I-V Curve</option>
          <option value={12}>Exp 12: Zener Regulator</option>
          <option value={13}>Exp 13: Half-Wave Rectifier</option>
          <option value={14}>Exp 14: Full-Wave Rectifier</option>
        </select>
      </div>

      {/* Main Grid: Parameters + Waveform */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Parameter Panel */}
        <div className="p-5 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-zinc-400 border-b border-zinc-800 pb-2">
            <Sliders className="w-3.5 h-3.5 text-emerald-400" />
            <span>CIRCUIT PARAMETERS</span>
          </div>

          {(selectedExp === 4 || selectedExp === 5 || selectedExp === 13 || selectedExp === 14) && (
            <div className="space-y-3 text-xs font-mono">
              <div className="space-y-1">
                <div className="flex justify-between text-zinc-400">
                  <span>RESISTOR (R):</span>
                  <span className="text-zinc-200">{(resistor / 1000).toFixed(1)} kΩ</span>
                </div>
                <input
                  type="range"
                  min={1000}
                  max={100000}
                  step={1000}
                  value={resistor}
                  onChange={(e) => setResistor(parseInt(e.target.value))}
                  className="w-full accent-emerald-400"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-zinc-400">
                  <span>CAPACITOR (C):</span>
                  <span className="text-zinc-200">{(capacitance * 1000000).toFixed(1)} µF</span>
                </div>
                <input
                  type="range"
                  min={0.0000001}
                  max={0.0001}
                  step={0.0000005}
                  value={capacitance}
                  onChange={(e) => setCapacitance(parseFloat(e.target.value))}
                  className="w-full accent-emerald-400"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-zinc-400">
                  <span>INPUT VOLTAGE:</span>
                  <span className="text-zinc-200">{voltage} V</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={voltage}
                  onChange={(e) => setVoltage(parseInt(e.target.value))}
                  className="w-full accent-emerald-400"
                />
              </div>

              {(selectedExp === 13 || selectedExp === 14) && (
                <>
                  <div className="space-y-1">
                    <div className="flex justify-between text-zinc-400">
                      <span>FREQUENCY:</span>
                      <span className="text-zinc-200">{frequency} Hz</span>
                    </div>
                    <input
                      type="range"
                      min={10}
                      max={120}
                      value={frequency}
                      onChange={(e) => setFrequency(parseInt(e.target.value))}
                      className="w-full accent-emerald-400"
                    />
                  </div>

                  <div className="pt-2">
                    <label className="flex items-center space-x-2 text-zinc-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filterCapacitor}
                        onChange={(e) => setFilterCapacitor(e.target.checked)}
                        className="rounded bg-zinc-950 border-zinc-700 text-emerald-500 focus:ring-0"
                      />
                      <span>Enable Filter Capacitor</span>
                    </label>
                  </div>
                </>
              )}
            </div>
          )}

          <button
            onClick={runSimulation}
            className="w-full py-2.5 rounded bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-xs flex items-center justify-center space-x-1.5 transition font-mono mt-4"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>RUN SIMULATION</span>
          </button>
        </div>

        {/* Right Waveform Canvas & Results */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-4 rounded-lg bg-zinc-900/70 border border-zinc-800">
            <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
              <span className="flex items-center space-x-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                <span>LOCAL WAVEFORM PLOT</span>
              </span>
              <span className="text-[10px] text-zinc-500">HTML5 Deterministic Canvas</span>
            </div>

            <canvas
              ref={canvasRef}
              width={640}
              height={320}
              className="w-full h-72 rounded border border-zinc-800 bg-zinc-950"
            />
          </div>

          {/* Numerical Results */}
          {simResults && (
            <div className="p-4 rounded-lg bg-zinc-900/70 border border-zinc-800 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-850">
                <span className="text-zinc-500 block">Peak Voltage:</span>
                <span className="text-zinc-200 font-semibold">{simResults.vMax ?? 'N/A'} V</span>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-850">
                <span className="text-zinc-500 block">Average DC:</span>
                <span className="text-zinc-200 font-semibold">{simResults.vAvg ?? 'N/A'} V</span>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-850">
                <span className="text-zinc-500 block">Time Constant (tau):</span>
                <span className="text-emerald-400 font-semibold">
                  {simResults.tau ? `${simResults.tau} ms` : 'N/A'}
                </span>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-850">
                <span className="text-zinc-500 block">Ripple Factor:</span>
                <span className="text-amber-400 font-semibold">{simResults.ripple ?? 'N/A'}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
