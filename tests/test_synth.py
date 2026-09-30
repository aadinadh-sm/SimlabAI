import re

def synthesize_pyspice_bridge(prompt: str) -> str:
    # Extract voltage
    v_match = re.search(r'(\d+(?:\.\d+)?)\s*v(?:olts?|oltage)?', prompt, re.IGNORECASE)
    v_val = float(v_match.group(1)) if v_match else 10.0

    # Extract resistors
    # matches like r1 - 2kohm, r2 - 1 k ohm, r1 = 2k, etc.
    resistors = {}
    r_matches = re.findall(r'r(\d+)\s*[-:=]?\s*(\d+(?:\.\d+)?)\s*(k|m|u)?\s*(?:ohm)?', prompt, re.IGNORECASE)
    for num, val, unit in r_matches:
        mult = 1.0
        unit_str = "@u_Ohm"
        if unit.lower() == 'k':
            unit_str = "@u_kOhm"
        elif unit.lower() == 'm':
            unit_str = "@u_MOhm"
        elif unit.lower() == 'u':
            unit_str = "@u_uOhm"
        resistors[int(num)] = (float(val), unit_str)

    # Defaults for 5-resistor bridge if not all specified
    default_vals = {1: (2.0, "@u_kOhm"), 2: (1.0, "@u_kOhm"), 3: (2.0, "@u_kOhm"), 4: (2.0, "@u_kOhm"), 5: (1.0, "@u_kOhm")}
    for i in range(1, 6):
        if i not in resistors:
            resistors[i] = default_vals[i]

    code = f'''from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

# Initialize Circuit Container
circuit = Circuit('DC Biases in a Resistor Bridge')

# Independent DC Voltage Source between Node 1 and Ground
circuit.V('input', 1, circuit.gnd, {v_val}@u_V)

# Resistor Bridge Topology per 23EEP20B Manual
circuit.R(1, 1, 2, {resistors[1][0]}{resistors[1][1]})
circuit.R(2, 1, 3, {resistors[2][0]}{resistors[2][1]})
circuit.R(3, 2, circuit.gnd, {resistors[3][0]}{resistors[3][1]})
circuit.R(4, 3, circuit.gnd, {resistors[4][0]}{resistors[4][1]})
circuit.R(5, 2, 3, {resistors[5][0]}{resistors[5][1]})

# Setup Simulator and Perform Operating Point (.op) Analysis
simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.operating_point()

print("--- DC Bias Node Voltages ---")
for node in analysis.nodes.values():
    print(f"Node {{node.name}}: {{float(node):.4f}} V")
'''
    return code

prompt = "i have a circuit with voltage source 10v, r1 - 2kohm, r2 - 1 k ohm, r3 - 2k ohm, r4 - 2k ohm, r5 - 1 k ohm. can you make the pyspice code for this circuit"
print(synthesize_pyspice_bridge(prompt))
