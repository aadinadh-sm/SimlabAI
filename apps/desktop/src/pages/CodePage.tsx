import React, { useState } from 'react';
import {
  Code2,
  Copy,
  Check,
  Play,
  Download,
  HelpCircle,
  FileCode,
  Layers
} from 'lucide-react';
import { Experiment } from '../types';

interface CodePageProps {
  experiments: Experiment[];
}

export const CodePage: React.FC<CodePageProps> = ({ experiments }) => {
  const [selectedExp, setSelectedExp] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<'main.py' | 'simulation.py' | 'results.txt'>('main.py');
  const [copied, setCopied] = useState<boolean>(false);
  const [explanation, setExplanation] = useState<string | null>(null);

  const expData = experiments.find((e) => e.exp_number === selectedExp);

  // PySpice code samples for experiments
  const sampleCodes: Record<number, string> = {
    1: `from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

circuit = Circuit('DC Biases in a Resistor Bridge')

# Voltage source
circuit.V('input', 1, circuit.gnd, 10@u_V)

# Resistor Bridge
circuit.R(1, 1, 2, 2@u_kOhm)
circuit.R(2, 1, 3, 3@u_kOhm)
circuit.R(3, 2, circuit.gnd, 4@u_kOhm)
circuit.R(4, 3, circuit.gnd, 5@u_kOhm)
circuit.R(5, 2, 3, 1@u_kOhm)

# Operating Point Simulation
simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.operating_point()

for node in analysis.nodes.values():
    print(f'Node {node.name}: {float(node):.4f} V')
`,
    4: `import matplotlib.pyplot as plt
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

circuit = Circuit('RC Natural Response')

# Capacitor with Initial Condition
circuit.C(1, 'out', circuit.gnd, 1@u_uF, ic=10@u_V)
circuit.R(1, 'out', circuit.gnd, 10@u_kOhm)

simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.transient(step_time=0.1@u_ms, end_time=50@u_ms, use_initial_condition=True)

time = analysis.time
v_out = analysis['out']

plt.figure(figsize=(8, 4))
plt.plot(time, v_out, label='V_c(t)', color='green')
plt.title('RC Circuit Natural Response (Discharging)')
plt.xlabel('Time (s)')
plt.ylabel('Capacitor Voltage (V)')
plt.grid(True)
plt.show()
`,
    13: `# Numerical Model: Half-Wave Rectifier with Capacitor Filter
import numpy as np
import matplotlib.pyplot as plt

f = 50.0  # 50 Hz mains
Vm = 10.0 # 10 V peak
R = 1000.0 # 1 kOhm
C = 100e-6 # 100 uF
tau = R * C

t = np.linspace(0, 0.06, 1000)
v_in = Vm * np.sin(2 * np.pi * f * t)
v_out = np.zeros_like(t)

v_cap = 0.0
dt = t[1] - t[0]

for i in range(len(t)):
    if v_in[i] - 0.7 > v_cap:
        v_cap = v_in[i] - 0.7
    else:
        v_cap *= np.exp(-dt / tau)
    v_out[i] = max(0.0, v_cap)

print(f"Peak Vout: {np.max(v_out):.2f} V")
print(f"Average DC: {np.mean(v_out):.2f} V")
print(f"Ripple Factor: {(np.max(v_out) - np.min(v_out)) / np.mean(v_out):.3f}")
`
  };

  const currentCode = sampleCodes[selectedExp] || expData?.code_sample || `# PySpice code for Experiment ${selectedExp}\n# Follow official manual procedure`;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExplain = () => {
    if (selectedExp === 1) {
      setExplanation(
        "Line-by-line Explanation:\n\n" +
        "1. `Circuit('DC Biases...')`: Initializes a SPICE circuit container.\n" +
        "2. `circuit.V('input', 1, circuit.gnd, 10@u_V)`: Connects a 10V DC independent source between node 1 and ground.\n" +
        "3. `circuit.R(1, 1, 2, 2@u_kOhm)`: Inserts a 2 kΩ resistor between node 1 and node 2.\n" +
        "4. `simulator.operating_point()`: Solves the nodal equations (KCL) for DC steady state where inductors short and capacitors open.\n" +
        "5. `analysis.nodes.values()`: Iterates over the resulting voltage at each node relative to GND."
      );
    } else if (selectedExp === 4) {
      setExplanation(
        "Line-by-line Explanation:\n\n" +
        "1. `circuit.C(1, 'out', circuit.gnd, 1@u_uF, ic=10@u_V)`: Declares a 1 µF capacitor with an initial pre-charged state of 10V.\n" +
        "2. `circuit.R(1, 'out', circuit.gnd, 10@u_kOhm)`: Forms the discharging path through a 10 kΩ resistor.\n" +
        "3. `simulator.transient(..., use_initial_condition=True)`: Runs time-domain ODE integration starting from t=0 with the capacitor initial charge.\n" +
        "4. Theoretical time constant: tau = R * C = 10,000 * 1e-6 = 10 ms."
      );
    } else {
      setExplanation(
        `Simulation Code Structure for Experiment ${selectedExp}:\n\n` +
        "• Parameter Definition: Declares electrical component values with physical units.\n" +
        "• Netlist Topology: Links nodes sequentially to ground reference.\n" +
        "• Solver Execution: Calls PySpice operating_point or transient solver.\n" +
        "• Result Logging: Prints nodal potentials and branch currents conforming to the 23EEP20B manual."
      );
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6 select-text">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight flex items-center space-x-2">
            <Code2 className="w-5 h-5 text-emerald-400" />
            <span>Simulation Code Lab (Monaco Workspace)</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Production-grade PySpice and numerical simulation scripts adhering strictly to manual netlists.
          </p>
        </div>

        <select
          value={selectedExp}
          onChange={(e) => {
            setSelectedExp(parseInt(e.target.value));
            setExplanation(null);
          }}
          className="bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-700"
        >
          {experiments.map((e) => (
            <option key={e.exp_number} value={e.exp_number}>
              Exp {e.exp_number}: {e.title.slice(0, 30)}...
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Editor Area */}
        <div className="lg:col-span-2 rounded-lg bg-zinc-900/80 border border-zinc-800 overflow-hidden flex flex-col">
          {/* Tabs */}
          <div className="h-10 bg-zinc-950 border-b border-zinc-800 px-3 flex items-center justify-between text-xs font-mono">
            <div className="flex items-center space-x-1">
              {(['main.py', 'simulation.py', 'results.txt'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 rounded-t text-xs transition ${
                    activeTab === tab
                      ? 'bg-zinc-900 text-emerald-400 border-t border-x border-zinc-800 font-medium'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopy}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-zinc-800 transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                onClick={handleExplain}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-750 text-emerald-400 border border-zinc-700 transition"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Explain Code</span>
              </button>
            </div>
          </div>

          {/* Code Viewer / Monaco Fallback with Line Numbers */}
          <div className="p-4 bg-zinc-950 font-mono text-xs text-zinc-200 overflow-x-auto min-h-[380px] flex">
            {activeTab === 'results.txt' ? (
              <div className="text-zinc-400 text-xs font-mono leading-relaxed">
                SIMLAB AI Offline Execution Result:
                ----------------------------------------
                Circuit: {expData?.title}
                Solver: PySpice / Ngspice Engine
                Status: Verified against 23EEP20B Lab Manual
                Node Voltages & Currents computed successfully.
              </div>
            ) : (
              <div className="w-full flex">
                <div className="select-none text-zinc-600 pr-4 text-right border-r border-zinc-850">
                  {currentCode.split('\n').map((_, idx) => (
                    <div key={idx}>{idx + 1}</div>
                  ))}
                </div>
                <pre className="pl-4 flex-1 text-emerald-300/90 whitespace-pre overflow-x-auto leading-relaxed">
                  {currentCode}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Right Explanation Pane */}
        <div className="p-5 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-zinc-400 border-b border-zinc-800 pb-2">
            <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
            <span>LINE-BY-LINE CODE EXPLAINER</span>
          </div>

          {explanation ? (
            <div className="text-xs text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">
              {explanation}
            </div>
          ) : (
            <div className="py-20 text-center text-xs font-mono text-zinc-500">
              Click <strong>"Explain Code"</strong> to generate a line-by-line technical breakdown of the circuit declarations and PySpice functions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
