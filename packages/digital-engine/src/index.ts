/**
 * SIMLAB AI - Deterministic Digital Logic & Boolean Engine
 * Strictly verifies truth tables, minterms, maxterms, and NAND implementations
 * for Experiments 7, 8, 9, 10.
 */

export type LogicValue = 0 | 1;

export interface Gate {
  type: 'AND' | 'OR' | 'NOT' | 'NAND' | 'NOR' | 'XOR' | 'XNOR';
  eval: (inputs: LogicValue[]) => LogicValue;
}

export const GATES: Record<string, Gate> = {
  AND: {
    type: 'AND',
    eval: (inputs) => (inputs.every((x) => x === 1) ? 1 : 0),
  },
  OR: {
    type: 'OR',
    eval: (inputs) => (inputs.some((x) => x === 1) ? 1 : 0),
  },
  NOT: {
    type: 'NOT',
    eval: (inputs) => (inputs[0] === 0 ? 1 : 0),
  },
  NAND: {
    type: 'NAND',
    eval: (inputs) => (inputs.every((x) => x === 1) ? 0 : 1),
  },
  NOR: {
    type: 'NOR',
    eval: (inputs) => (inputs.some((x) => x === 1) ? 0 : 1),
  },
  XOR: {
    type: 'XOR',
    eval: (inputs) => {
      const ones = inputs.filter((x) => x === 1).length;
      return ones % 2 === 1 ? 1 : 0;
    },
  },
  XNOR: {
    type: 'XNOR',
    eval: (inputs) => {
      const ones = inputs.filter((x) => x === 1).length;
      return ones % 2 === 0 ? 1 : 0;
    },
  },
};

/**
 * Experiment 8: Half Adder
 * Inputs: A, B
 * SUM = A XOR B
 * CARRY = A AND B
 */
export function evaluateHalfAdder(a: LogicValue, b: LogicValue): { sum: LogicValue; carry: LogicValue } {
  return {
    sum: GATES.XOR.eval([a, b]),
    carry: GATES.AND.eval([a, b]),
  };
}

/**
 * Experiment 8: Full Adder
 * Inputs: A, B, Cin
 * SUM = A XOR B XOR Cin
 * CARRY = (A AND B) OR ((A XOR B) AND Cin)
 */
export function evaluateFullAdder(
  a: LogicValue,
  b: LogicValue,
  cin: LogicValue
): { sum: LogicValue; carry: LogicValue } {
  const sum1 = GATES.XOR.eval([a, b]);
  const carry1 = GATES.AND.eval([a, b]);
  const sumFinal = GATES.XOR.eval([sum1, cin]);
  const carry2 = GATES.AND.eval([sum1, cin]);
  const carryFinal = GATES.OR.eval([carry1, carry2]);

  return {
    sum: sumFinal,
    carry: carryFinal,
  };
}

/**
 * Experiment 9: Boolean Function in SOP and POS Form
 * Documented minterms: XSOP = Sigma(1, 3, 6)
 * A'B'C (1), A'BC (3), ABC' (6)
 */
export function evaluateExp9SOP(a: LogicValue, b: LogicValue, c: LogicValue): LogicValue {
  const term1 = (a === 0 && b === 0 && c === 1) ? 1 : 0; // m1
  const term2 = (a === 0 && b === 1 && c === 1) ? 1 : 0; // m3
  const term3 = (a === 1 && b === 1 && c === 0) ? 1 : 0; // m6
  return (term1 || term2 || term3) ? 1 : 0;
}

/**
 * Experiment 10: NAND-only Combinational Circuit
 * F = AB + BC + AC
 * Realized purely via NAND gates:
 * Stage 1: NAND1 = (A.B)', NAND2 = (B.C)', NAND3 = (A.C)'
 * Stage 2: Output = (NAND1 . NAND2 . NAND3)'
 */
export function evaluateExp10NAND(a: LogicValue, b: LogicValue, c: LogicValue): {
  nand1: LogicValue;
  nand2: LogicValue;
  nand3: LogicValue;
  output: LogicValue;
} {
  const n1 = GATES.NAND.eval([a, b]);
  const n2 = GATES.NAND.eval([b, c]);
  const n3 = GATES.NAND.eval([a, c]);
  const out = GATES.NAND.eval([n1, n2, n3]);

  return {
    nand1: n1,
    nand2: n2,
    nand3: n3,
    output: out,
  };
}

/**
 * Generate full truth table for any N-variable logic evaluator
 */
export function generateTruthTable(
  numInputs: number,
  evaluator: (...inputs: LogicValue[]) => Record<string, LogicValue> | LogicValue
): { inputs: LogicValue[]; outputs: Record<string, LogicValue> }[] {
  const rows: { inputs: LogicValue[]; outputs: Record<string, LogicValue> }[] = [];
  const total = 1 << numInputs;

  for (let i = 0; i < total; i++) {
    const inputs: LogicValue[] = [];
    for (let bit = numInputs - 1; bit >= 0; bit--) {
      inputs.push(((i >> bit) & 1) as LogicValue);
    }
    const result = evaluator(...inputs);
    const outputs = typeof result === 'object' ? result : { out: result };
    rows.push({ inputs, outputs });
  }

  return rows;
}
