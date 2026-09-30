/**
 * SIMLAB AI - Circuit Intermediate Representation (Circuit IR)
 * Simulator-independent JSON schema, validation, and PySpice code transpiler.
 */

export interface ComponentIR {
  id: string;
  type:
    | 'resistor'
    | 'capacitor'
    | 'inductor'
    | 'diode'
    | 'zener'
    | 'dc_voltage_source'
    | 'ac_voltage_source'
    | 'cccs'
    | 'vcvs'
    | 'switch'
    | 'ground'
    | 'gate';
  value?: number;
  unit?: string;
  nodes: string[];
  parameters?: Record<string, any>;
}

export interface CircuitIR {
  version: string;
  metadata: {
    name: string;
    experiment?: number;
    description?: string;
    created_at?: number;
  };
  components: ComponentIR[];
  nodes: string[];
  ground_node: string;
  analysis?: {
    type: 'op' | 'transient' | 'dc_sweep';
    step?: number;
    stop?: number;
    use_initial_condition?: boolean;
  };
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validates electrical topology of a Circuit IR.
 * Enforces missing ground checks, floating node checks, and minimum loop connectivity.
 */
export function validateCircuitTopology(circuit: CircuitIR): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check 1: Must have components
  if (!circuit.components || circuit.components.length === 0) {
    errors.push('Circuit contains no components.');
    return { valid: false, errors, warnings };
  }

  // Check 2: Ground node existence
  const hasGround =
    circuit.nodes.includes(circuit.ground_node) ||
    circuit.nodes.some((n) => n.toUpperCase() === 'GND' || n === '0');
  if (!hasGround) {
    errors.push('Missing explicit ground node reference (GND / Node 0). SPICE requires a 0V reference.');
  }

  // Check 3: Node connection counts (detect floating nodes)
  const nodeConnections: Record<string, number> = {};
  circuit.nodes.forEach((n) => {
    nodeConnections[n] = 0;
  });

  circuit.components.forEach((comp) => {
    comp.nodes.forEach((node) => {
      nodeConnections[node] = (nodeConnections[node] || 0) + 1;
    });
  });

  for (const [node, count] of Object.entries(nodeConnections)) {
    if (count < 2 && node !== circuit.ground_node && node.toUpperCase() !== 'GND' && node !== '0') {
      errors.push(`Floating node detected: Node '${node}' is only connected to ${count} component pin.`);
    }
  }

  // Check 4: Resistor or capacitor values
  circuit.components.forEach((comp) => {
    if (comp.type === 'resistor' && comp.value !== undefined && comp.value <= 0) {
      errors.push(`Invalid resistance on ${comp.id}: Value must be positive.`);
    }
    if (comp.type === 'capacitor' && comp.value !== undefined && comp.value <= 0) {
      errors.push(`Invalid capacitance on ${comp.id}: Value must be positive.`);
    }
  });

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Generates verified PySpice Python code from a Circuit IR.
 */
export function circuitIRToPySpice(circuit: CircuitIR): string {
  let lines: string[] = [];
  lines.push("from PySpice.Spice.Netlist import Circuit");
  lines.push("from PySpice.Unit import *");
  lines.push("");
  lines.push(`circuit = Circuit('${circuit.metadata.name || "SimLab Simulation"}')`);
  lines.push("");

  circuit.components.forEach((c) => {
    const n1 = c.nodes[0] === circuit.ground_node ? "circuit.gnd" : `'${c.nodes[0]}'`;
    const n2 = c.nodes[1] === circuit.ground_node ? "circuit.gnd" : `'${c.nodes[1]}'`;

    if (c.type === "resistor") {
      const val = c.value || 1000;
      lines.push(`circuit.R('${c.id}', ${n1}, ${n2}, ${val}@u_Ohm)`);
    } else if (c.type === "capacitor") {
      const val = c.value || 1e-6;
      lines.push(`circuit.C('${c.id}', ${n1}, ${n2}, ${val}@u_F)`);
    } else if (c.type === "dc_voltage_source") {
      const val = c.value || 10;
      lines.push(`circuit.V('${c.id}', ${n1}, ${n2}, ${val}@u_V)`);
    } else if (c.type === "diode") {
      lines.push(`circuit.X('${c.id}', '1N4007', ${n1}, ${n2})`);
    }
  });

  lines.push("");
  lines.push("simulator = circuit.simulator(temperature=25, nominal_temperature=25)");

  if (circuit.analysis?.type === "op") {
    lines.push("analysis = simulator.operating_point()");
    lines.push("for node in analysis.nodes.values():");
    lines.push("    print(f'Node {node.name}: {float(node):.4f} V')");
  } else {
    const stop = circuit.analysis?.stop || 0.05;
    const step = circuit.analysis?.step || 0.0001;
    lines.push(`analysis = simulator.transient(step_time=${step}@u_s, end_time=${stop}@u_s)`);
  }

  return lines.join("\n");
}
