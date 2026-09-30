"""
SIMLAB AI — Phase 1 & Phase 2: Structured Domain Knowledge & Canonical Circuit IR Builder
Builds authoritative structured records for all 14 experiments from 'Manual complete.pdf' / 'Manual complete.txt'
and 22 canonical Circuit IR templates (14 Manual Experiments + 8 Generalized Circuit Templates).
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Tuple

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KNOWLEDGE_DIR = os.path.join(APP_ROOT, "knowledge")
EXPERIMENTS_DIR = os.path.join(KNOWLEDGE_DIR, "experiments")
CIRCUITS_DIR = os.path.join(KNOWLEDGE_DIR, "circuits")
VIVA_DIR = os.path.join(KNOWLEDGE_DIR, "viva")
MANUAL_TXT = os.path.join(KNOWLEDGE_DIR, "Manual complete.txt")

CIRCUIT_CORE_SRC = os.path.join(APP_ROOT, "packages", "circuit-core", "src")
if CIRCUIT_CORE_SRC not in sys.path:
    sys.path.insert(0, CIRCUIT_CORE_SRC)

from progressive_reconstruction import ProgressiveCircuitEngine


def get_structured_experiments_catalog() -> Dict[int, Dict[str, Any]]:
    """
    Authoritative structured domain catalog for all 14 experiments of
    '23EEP20B - SIMULATION LAB MANUAL'.
    Every experiment record includes:
      - exp_number, title, category, family, pages
      - aim, apparatus_components, theory, equations
      - circuit_topology, component_relationships, simulation_type
      - procedure, code, expected_observations, result
      - viva_concepts (10 categorized student-level Q&As per experiment)
      - common_mistakes, important_terminology, related_experiments
      - canonical_circuit_ir
    """
    return {
        1: {
            "exp_number": 1,
            "title": "Computation of DC Biases in a Resistor Bridge Using PySpice",
            "category": "Analog / PySpice",
            "family": "PYSPICE_DC",
            "pages": [3, 4],
            "aim": "To compute the DC biases (steady-state node voltages) at various nodes in a five-resistor Wheatstone-style bridge circuit using Python and PySpice.",
            "apparatus_components": [
                "Python 3.x environment with PySpice and Ngspice",
                "DC Voltage Source Vinput = 10 V (Node 1 to GND)",
                "Resistor R1 = 2 kΩ (Node 1 to Node 2)",
                "Resistor R2 = 1 kΩ (Node 1 to Node 3)",
                "Resistor R3 = 1 kΩ (Node 2 to GND)",
                "Resistor R4 = 2 kΩ (Node 3 to GND)",
                "Bridge Resistor R5 = 2 kΩ (Node 3 to Node 2)"
            ],
            "theory": (
                "A resistor bridge (Wheatstone bridge topology) consists of two upper branch resistors (R1, R2), "
                "two lower shunt resistors to ground (R3, R4), and a central bridging resistor (R5) connecting the two "
                "middle nodes (Node 2 and Node 3). Under DC excitation, Kirchhoff's Current Law (KCL) at Node 2 and Node 3 "
                "determines the node voltages V(2) and V(3). When R1*R4 = R2*R3, the bridge is balanced and V(2) = V(3); "
                "in the manual's unbalanced configuration (R1=2kΩ, R2=1kΩ, R3=1kΩ, R4=2kΩ, R5=2kΩ), current flows from "
                "Node 3 to Node 2 through R5."
            ),
            "equations": [
                "KCL at Node 2: (V2 - V1)/R1 + V2/R3 + (V2 - V3)/R5 = 0",
                "KCL at Node 3: (V3 - V1)/R2 + V3/R4 + (V3 - V2)/R5 = 0",
                "Bridge Voltage: V_bridge = V(3) - V(2)",
                "With V1=10V, R1=2kΩ, R2=1kΩ, R3=1kΩ, R4=2kΩ, R5=2kΩ -> V(1)=10.0V, V(2)=4.0V, V(3)=6.0V"
            ],
            "circuit_topology": "Five-resistor bridge network driven by Vinput between Node 1 and GND, with R5 bridging interior nodes 2 and 3.",
            "component_relationships": [
                "Vinput: N1 -> GND (10 V DC source)",
                "R1: N1 -> N2 (2 kΩ upper-left arm)",
                "R2: N1 -> N3 (1 kΩ upper-right arm)",
                "R3: N2 -> GND (1 kΩ lower-left arm)",
                "R4: N3 -> GND (2 kΩ lower-right arm)",
                "R5: N3 -> N2 (2 kΩ center bridge arm)"
            ],
            "simulation_type": "DC Operating Point (.op) via simulator.operating_point()",
            "procedure": (
                "1. Install and import PySpice (`Circuit`, `u_V`, `u_kOhm`).\n"
                "2. Instantiate `circuit = Circuit('Resistor Bridge')`.\n"
                "3. Add `Vinput` (10V) between node 1 and `circuit.gnd`, and add R1..R5 across their respective bridge nodes.\n"
                "4. Run `analysis = simulator.operating_point()` at 25°C.\n"
                "5. Iterate over `analysis.nodes.values()` and print each node's DC voltage."
            ),
            "expected_observations": "Node 1 = 10.0 V, Node 2 = 4.0 V, Node 3 = 6.0 V. Because V(3) > V(2), a 1 mA current flows from Node 3 to Node 2 through R5.",
            "result": "The DC bias voltages at all nodes of the resistor bridge circuit were computed using PySpice operating point analysis: V(1)=10.0 V, V(2)=4.0 V, V(3)=6.0 V.",
            "common_mistakes": [
                "Connecting R5 to ground instead of between interior nodes 3 and 2",
                "Forgetting `circuit.gnd` on Vinput, R3, or R4, causing a singular matrix / floating node error",
                "Treating the 5 resistors as a series chain instead of a bridge topology"
            ],
            "important_terminology": ["DC Bias", "Operating Point (.op)", "Wheatstone Bridge", "Nodal Analysis (KCL)", "Reference Ground (circuit.gnd)"],
            "related_experiments": [2, 3],
            "viva_concepts": [
                {"category": "definition", "q": "What is meant by DC bias or operating point in PySpice?", "a": "DC bias (operating point) is the steady-state DC voltage at every node and DC current through every branch when only constant DC sources are applied."},
                {"category": "why", "q": "Why must every SPICE circuit include `circuit.gnd`?", "a": "SPICE solves nodal matrix equations relative to a 0 V reference node (`circuit.gnd`). Without ground, the conductance matrix is singular and node voltages are undefined."},
                {"category": "how", "q": "How do you run a DC bias simulation in PySpice?", "a": "Create a simulator with `simulator = circuit.simulator(temperature=25, nominal_temperature=25)` and call `analysis = simulator.operating_point()`."},
                {"category": "component", "q": "What role does R5 play in Experiment 1?", "a": "R5 is the central bridge resistor connected between Node 3 and Node 2, coupling the left and right voltage divider arms."},
                {"category": "procedure", "q": "How are node voltages extracted from the `analysis` object in Experiment 1?", "a": "By looping over `for node in analysis.nodes.values():` and converting `str(node)` for the node name and `float(node)` for its voltage in volts."},
                {"category": "code", "q": "What does `2@u_kΩ` or `2@u_kOhm` mean in PySpice?", "a": "The `@` operator attaches a physical unit from `PySpice.Unit` (`kOhm` = 10^3 ohms) to a numeric value."},
                {"category": "topology", "q": "Which components share Node 2 in the Experiment 1 resistor bridge?", "a": "R1 (from Node 1 to Node 2), R3 (from Node 2 to GND), and R5 (between Node 3 and Node 2) all meet at Node 2."},
                {"category": "calculation", "q": "Why is Node 2 at 4.0 V and Node 3 at 6.0 V in Experiment 1?", "a": "Solving KCL: at Node 2, (V2-10)/2k + V2/1k + (V2-V3)/2k = 0 => 2V2 - V3 = 2; at Node 3, (V3-10)/1k + V3/2k + (V3-V2)/2k = 0 => -V2 + 4V3 = 20. Solving gives V2 = 4 V and V3 = 6 V."},
                {"category": "troubleshooting", "q": "What happens if you accidentally connect both ends of R5 to Node 2?", "a": "R5 becomes short-circuited across a single node, which invalidates the bridge topology and triggers a short-circuit validation error."},
                {"category": "expected_output", "q": "When would the voltage across R5 become zero in Experiment 1?", "a": "When the bridge is balanced, i.e., R1 * R4 = R2 * R3, making V(2) equal to V(3)."}
            ]
        },
        2: {
            "exp_number": 2,
            "title": "Simulation of a Current-Controlled Current Source (CCCS) Circuit Using PySpice",
            "category": "Analog / PySpice",
            "family": "PYSPICE_DC",
            "pages": [5, 6],
            "aim": "To simulate a circuit containing a Current-Controlled Current Source (CCCS) using PySpice and compute its DC node voltages and controlling branch current.",
            "apparatus_components": [
                "DC Voltage Source V1 = 50 V (Node 1 to GND)",
                "Zero-Volt Current-Sense Source Vtest = 0 V (Node 1 to Node 2)",
                "Resistor R1 = 6 Ω (Node 2 to Node 3, carries controlling current)",
                "Resistor R2 = 8 Ω (Node 3 to GND)",
                "Resistor R3 = 2 Ω (Node 3 to Node 4)",
                "Resistor R4 = 4 Ω (Node 4 to GND)",
                "Independent DC Current Source I1 = 5 A (GND to Node 4)",
                "CCCS F1 (Node 4 to Node 3, controlled by Vtest, current gain = 3)"
            ],
            "theory": (
                "A Current-Controlled Current Source (CCCS, SPICE 'F' element) produces an output current proportional "
                "to the current flowing through a controlling branch: I_out = gain * I_sense. Because SPICE requires a "
                "voltage source name to sense branch current, a dummy 0 V voltage source (`Vtest`) is placed in series "
                "with R1 between Node 1 and Node 2. Vtest introduces zero voltage drop (V(1) = V(2)) while measuring "
                "the exact controlling current I(Vtest) = (V1 - V3) / R1."
            ),
            "equations": [
                "Controlling Current: I(Vtest) = (V1 - V3) / R1",
                "CCCS Output Current: I(F1) = gain * I(Vtest) = 3 * I(Vtest) (from Node 4 to Node 3)",
                "KCL at Node 3: (V3 - V2)/R1 + V3/R2 + (V3 - V4)/R3 - gain * I(Vtest) = 0",
                "KCL at Node 4: (V4 - V3)/R3 + V4/R4 + gain * I(Vtest) - I1 = 0"
            ],
            "circuit_topology": "Two-mesh resistive network with V1 (50V) and dummy ammeter Vtest (0V) feeding R1 into Node 3, R2 to GND, R3 coupling Node 3 to Node 4, R4 to GND, I1 injecting into Node 4, and CCCS F1 between Node 4 and Node 3.",
            "component_relationships": [
                "V1: N1 -> GND (50 V)",
                "Vtest: N1 -> N2 (0 V current-sense ammeter)",
                "R1: N2 -> N3 (6 Ω series controlling branch)",
                "R2: N3 -> GND (8 Ω shunt)",
                "R3: N3 -> N4 (2 Ω coupling resistor)",
                "R4: N4 -> GND (4 Ω output shunt)",
                "I1: GND -> N4 (5 A current source)",
                "F1: N4 -> N3 (CCCS controlled by Vtest with gain = 3)"
            ],
            "simulation_type": "DC Operating Point (.op) solving node voltages V(1)..V(4) and branch current I(Vtest)",
            "procedure": (
                "1. Create `circuit = Circuit('CCCS Circuit')`.\n"
                "2. Add `V1` (50V) at (1, gnd) and `Vtest` (0V) at (1, 2) to sense the controlling current.\n"
                "3. Connect R1 (2,3), R2 (3,gnd), R3 (3,4), R4 (4,gnd), and current source I1 (gnd, 4, 5A).\n"
                "4. Add CCCS `circuit.F(1, 4, 3, 'Vtest', 3)`.\n"
                "5. Run `simulator.operating_point()` and print `analysis.nodes` and `analysis.branches`."
            ),
            "expected_observations": "Node 1 = 50.0 V, Node 2 = 50.0 V (since Vtest = 0 V), Node 3 = 38.0952 V, Node 4 = 16.6667 V, Controlling Current I(Vtest) = 1.9841 A.",
            "result": "The CCCS circuit was simulated in PySpice and the DC node voltages and branch currents were verified.",
            "common_mistakes": [
                "Omitting the 0 V dummy source `Vtest` and trying to pass `'R1'` directly as the controlling element to `circuit.F(...)`",
                "Deleting `Vtest` when substituting custom user resistor values",
                "Reversing the polarity of `I1` or `F1`"
            ],
            "important_terminology": ["CCCS (F Element)", "Controlling Current", "Zero-Volt Ammeter Source (Vtest)", "Current Gain", "Branch Current (`analysis.branches`)"],
            "related_experiments": [1, 3],
            "viva_concepts": [
                {"category": "definition", "q": "What is a Current-Controlled Current Source (CCCS)?", "a": "A CCCS is a dependent current source whose output current is equal to a dimensionless gain factor multiplied by a controlling current in another branch."},
                {"category": "why", "q": "Why do we insert `Vtest` with 0 V in Experiment 2?", "a": "SPICE's `F` element requires a voltage source name to measure controlling current. A 0 V voltage source acts as an ideal ammeter (zero resistance, zero voltage drop) in series with R1."},
                {"category": "how", "q": "How is the CCCS defined in PySpice code?", "a": "Using `circuit.F(1, 4, 3, 'Vtest', 3)`, where 4 and 3 are output nodes, `'Vtest'` is the current-sensing voltage source, and 3 is the current gain."},
                {"category": "component", "q": "Why are Node 1 and Node 2 at the exact same voltage in Experiment 2?", "a": "Because `Vtest` is a 0 V source connected between Node 1 and Node 2, so V(1) - V(2) = 0 V."},
                {"category": "procedure", "q": "How do you print branch currents after running `operating_point()` in PySpice?", "a": "By iterating over `for branch in analysis.branches.values(): print(str(branch), float(branch))`."},
                {"category": "code", "q": "Can we pass `'R1'` instead of `'Vtest'` to `circuit.F()` in standard SPICE?", "a": "No, standard SPICE syntax requires a voltage source identifier as the current sensor for an F-element."},
                {"category": "topology", "q": "Between which nodes is the independent current source `I1` connected in Experiment 2?", "a": "Between `circuit.gnd` and Node 4, injecting 5 A into Node 4."},
                {"category": "calculation", "q": "If I(Vtest) is 1.9841 A and the CCCS gain is 3, what is the current through F1?", "a": "I(F1) = 3 * 1.9841 A = 5.9524 A."},
                {"category": "troubleshooting", "q": "What happens if a student removes `Vtest` when modifying resistor values in Experiment 2?", "a": "The CCCS `F1` loses its controlling current reference and Ngspice fails with an unknown controlling source error."},
                {"category": "expected_output", "q": "What happens to Node 3 voltage if the CCCS gain is increased?", "a": "Because F1 pumps current from Node 4 into Node 3, increasing the gain raises Node 3's voltage closer to V1."}
            ]
        },
        3: {
            "exp_number": 3,
            "title": "Simulation of a Voltage-Controlled Voltage Source (VCVS) Circuit Using PySpice",
            "category": "Analog / PySpice",
            "family": "PYSPICE_DC",
            "pages": [7, 8],
            "aim": "To simulate a circuit containing a Voltage-Controlled Voltage Source (VCVS) using PySpice and determine its DC node voltages and branch currents.",
            "apparatus_components": [
                "DC Voltage Source V1 = 65 V (Node 2 to Node 1)",
                "Resistor R1 = 5 Ω (Node 3 to GND)",
                "Resistor R2 = 6 Ω (Node 1 to GND)",
                "Resistor R3 = 4 Ω (Node 2 to Node 3, controlling voltage drop)",
                "Resistor R4 = 8 Ω (Node 3 to Node 4)",
                "Resistor R5 = 15 Ω (Node 5 to GND)",
                "VCVS E1 (Output: Node 4 to Node 5; Control: Node 2 to Node 3; Voltage Gain = 3)"
            ],
            "theory": (
                "A Voltage-Controlled Voltage Source (VCVS, SPICE 'E' element) generates an output voltage between "
                "its output terminals (Node 4 and Node 5) equal to a voltage gain multiplied by the differential voltage "
                "across its controlling node pair (Node 2 and Node 3): V(4) - V(5) = gain * (V(2) - V(3)). No dummy "
                "ammeter source is required because voltage is sensed directly across nodes 2 and 3."
            ),
            "equations": [
                "Source Constraint: V(2) - V(1) = V1 = 65 V",
                "VCVS Constraint: V(4) - V(5) = gain * (V(2) - V(3)) = 3 * (V(2) - V(3))",
                "Controlling Voltage: V_ctrl = V(2) - V(3) (voltage across R3)"
            ],
            "circuit_topology": "Multi-node resistive network where V1 is connected as a floating source between Node 2 and Node 1, R3 spans controlling nodes 2 and 3, and VCVS E1 spans output nodes 4 and 5.",
            "component_relationships": [
                "V1: N2 -> N1 (65 V floating DC source)",
                "R1: N3 -> GND (5 Ω shunt at Node 3)",
                "R2: N1 -> GND (6 Ω shunt at Node 1)",
                "R3: N2 -> N3 (4 Ω controlling branch)",
                "R4: N3 -> N4 (8 Ω coupling branch)",
                "R5: N5 -> GND (15 Ω load branch)",
                "E1: Output N4 -> N5, Control N2 -> N3 (gain = 3 V/V)"
            ],
            "simulation_type": "DC Operating Point (.op)",
            "procedure": (
                "1. Instantiate `circuit = Circuit('VCVS Circuit')`.\n"
                "2. Add `V1` (65V) between nodes 2 and 1, and resistors R1..R5.\n"
                "3. Add VCVS `circuit.E(1, 4, 5, 2, 3, 3)`.\n"
                "4. Run `simulator.operating_point()` and print all node voltages and voltage-source branch currents."
            ),
            "expected_observations": "Node 1 = -25.1376 V, Node 2 = 39.8624 V, Node 3 = 23.1651 V, Node 4 = 20.6881 V, Node 5 = -29.4037 V.",
            "result": "The VCVS circuit was simulated in PySpice and the DC node voltages and branch currents were obtained.",
            "common_mistakes": [
                "Connecting V1 to GND instead of between Node 2 and Node 1 as specified in the manual",
                "Swapping output nodes (4, 5) and controlling nodes (2, 3) in `circuit.E(1, 4, 5, 2, 3, 3)`"
            ],
            "important_terminology": ["VCVS (E Element)", "Controlling Nodes", "Differential Control Voltage", "Floating Voltage Source", "Voltage Gain"],
            "related_experiments": [1, 2],
            "viva_concepts": [
                {"category": "definition", "q": "What is a Voltage-Controlled Voltage Source (VCVS)?", "a": "A VCVS is a dependent voltage source whose output terminal voltage is proportional to the voltage difference across a specified pair of controlling nodes."},
                {"category": "why", "q": "Why doesn't Experiment 3 need a 0 V `Vtest` source like Experiment 2?", "a": "Because a VCVS senses voltage directly between two existing nodes (Node 2 and Node 3), whereas a CCCS must sense current flowing through a branch."},
                {"category": "how", "q": "What is the argument order for `circuit.E(1, 4, 5, 2, 3, 3)` in PySpice?", "a": "Element ID `1`, positive output node `4`, negative output node `5`, positive controlling node `2`, negative controlling node `3`, and voltage gain `3`."},
                {"category": "component", "q": "Across which resistor is the controlling voltage measured in Experiment 3?", "a": "Across resistor R3, which is connected between Node 2 and Node 3."},
                {"category": "procedure", "q": "Which branches appear in `analysis.branches` for Experiment 3?", "a": "The independent voltage source `v1` and the dependent voltage source `e1`, since SPICE computes branch currents directly for voltage-defined elements."},
                {"category": "code", "q": "Why is `V1` connected as `circuit.V(1, 2, 1, 65@u_V)` in Experiment 3?", "a": "In the manual schematic, V1 is a floating 65 V source with its positive terminal at Node 2 and negative terminal at Node 1."},
                {"category": "topology", "q": "How many non-ground nodes exist in the Experiment 3 VCVS circuit?", "a": "Five non-ground nodes (Nodes 1, 2, 3, 4, and 5) plus `GND`."},
                {"category": "calculation", "q": "If V(2) = 39.8624 V, V(3) = 23.1651 V, and gain = 3, what is V(4) - V(5)?", "a": "V(4) - V(5) = 3 * (39.8624 - 23.1651) = 3 * 16.6973 = 50.0918 V."},
                {"category": "troubleshooting", "q": "What error occurs if the controlling nodes of E1 are swapped from (2, 3) to (3, 2)?", "a": "The polarity of the dependent voltage source inverts, flipping the sign of V(4) - V(5)."},
                {"category": "expected_output", "q": "Why is Node 1 voltage negative (-25.14 V) in Experiment 3?", "a": "Because V1 (65 V) has its negative terminal at Node 1 and returns current through R2 (6 Ω) to ground."}
            ]
        },
        4: {
            "exp_number": 4,
            "title": "Simulating Natural Response of RC Circuits Using PySpice",
            "category": "Transient / RC",
            "family": "PYSPICE_TRANSIENT",
            "pages": [9, 10, 11],
            "aim": "To simulate the natural response (source-free exponential discharge) of an RC circuit using voltage-controlled switches in PySpice and plot the capacitor voltage and switch activations.",
            "apparatus_components": [
                "DC Charging Source V1 = 100 V (Node 1 to GND)",
                "Charging Resistor R1 = 10 kΩ (Node 1 to Node 'a')",
                "Voltage-Controlled Switch S1 (Node 'a' to 'output', controlled by 'posa')",
                "Energy-Storage Capacitor C1 = 0.5 µF (Node 'output' to GND, ic = 0 V)",
                "Voltage-Controlled Switch S2 (Node 'output' to Node 'b', controlled by 'posb')",
                "Discharge Series Resistor R2 = 32 kΩ (Node 'b' to Node 2)",
                "Discharge Parallel Resistor R3 = 240 kΩ (Node 2 to GND)",
                "Discharge Parallel Resistor R4 = 60 kΩ (Node 2 to GND)",
                "Control Pulse Sources Vpulse2 ('posa') and Vpulse3 ('posb') with Rtesta, Rtestb = 1 kΩ"
            ],
            "theory": (
                "The natural response of an RC circuit describes how a pre-charged capacitor discharges through a "
                "resistive network without any external source connected. In Experiment 4, from t = 0 to switchingtime (50 ms), "
                "Switch S1 is CLOSED and Switch S2 is OPEN, charging C1 (0.5 µF) through R1 (10 kΩ, tau_charge = 5 ms) to 100 V. "
                "At t = 50 ms, S1 OPENS and S2 CLOSES, disconnecting V1 and discharging C1 through R2 in series with (R3 || R4). "
                "The equivalent discharge resistance is R_eq = R2 + (R3*R4)/(R3+R4) = 32 kΩ + 48 kΩ = 80 kΩ, giving "
                "a discharge time constant tau = R_eq * C1 = 80 kΩ * 0.5 µF = 40 ms."
            ),
            "equations": [
                "Equivalent Discharge Resistance: R_eq = R2 + (R3 * R4) / (R3 + R4) = 32 kΩ + 48 kΩ = 80 kΩ",
                "Discharge Time Constant: tau = R_eq * C1 = 80 kΩ * 0.5 µF = 40 ms (0.04 s)",
                "Natural Response Capacitor Voltage (t >= t_sw): V_C(t) = V_0 * exp(-(t - t_sw) / tau)",
                "Natural Response Capacitor Current (t >= t_sw): i_C(t) = -(V_0 / R_eq) * exp(-(t - t_sw) / tau)"
            ],
            "circuit_topology": "Dual-switch charge/discharge RC topology: charging path V1 -> R1 -> S1 -> C1, and discharging path C1 -> S2 -> R2 -> (R3 || R4) to GND.",
            "component_relationships": [
                "V1: N1 -> GND (100 V DC)",
                "R1: N1 -> Na (10 kΩ charging resistor)",
                "S1: Na -> output (controlled by posa -> GND)",
                "C1: output -> GND (0.5 µF capacitor)",
                "S2: output -> Nb (controlled by posb -> GND)",
                "R2: Nb -> N2 (32 kΩ discharge series resistor)",
                "R3: N2 -> GND (240 kΩ discharge parallel branch 1)",
                "R4: N2 -> GND (60 kΩ discharge parallel branch 2)",
                "Vpulse2 & Rtesta: posa -> GND (opens S1 at 50 ms)",
                "Vpulse3 & Rtestb: posb -> GND (closes S2 at 50 ms)"
            ],
            "simulation_type": "Transient Analysis (simulator.transient(step_time=1@u_us, end_time=250@u_ms))",
            "procedure": (
                "1. Define timing parameters: `steptime=1@u_us`, `switchingtime=50@u_ms`, `finaltime=250@u_ms`.\n"
                "2. Define pulse control sources `Vpulse2` (`posa`) and `Vpulse3` (`posb`) with termination resistors `Rtesta`, `Rtestb`.\n"
                "3. Define switch model `circuit.model('switch', 'SW', Ron=1@u_mOhm, Roff=1@u_GOhm)`.\n"
                "4. Connect V1, R1, S1, C1, S2, R2, R3, R4.\n"
                "5. Set `simulator.initial_condition(output=0@u_V)` and run `simulator.transient(...)`.\n"
                "6. Plot switch control pulses and capacitor voltage `analysis['output']`."
            ),
            "expected_observations": "Capacitor charges from 0 V to ~100 V during 0..50 ms (5*tau_charge = 25 ms), then decays exponentially from 100 V toward 0 V after t = 50 ms with time constant tau = 40 ms (reaching 36.79 V at t = 90 ms).",
            "result": "The natural response of the RC circuit was simulated in PySpice and the exponential decay waveform of capacitor voltage was plotted.",
            "common_mistakes": [
                "Silently deleting S1, S2, Vpulse2, Vpulse3, or R2–R4 when the user supplies partial RC values",
                "Using R1 instead of R_eq = R2 + (R3 || R4) for the post-switching discharge time constant",
                "Forgetting `Rtesta` and `Rtestb` across the pulse sources"
            ],
            "important_terminology": ["Natural Response", "Time Constant (tau)", "Voltage-Controlled Switch (SW)", "Equivalent Discharge Resistance (R_eq)", "Initial Condition (`ic`)"],
            "related_experiments": [5, 6],
            "viva_concepts": [
                {"category": "definition", "q": "What is the natural response of an RC circuit?", "a": "It is the transient discharge of energy stored in the capacitor through connected resistors when no independent voltage or current source drives the RC network."},
                {"category": "why", "q": "Why does Experiment 4 include two switches S1 and S2?", "a": "S1 connects V1 to charge the capacitor prior to switchingtime (50 ms), and at 50 ms S1 opens while S2 closes to isolate V1 and discharge C1 purely through R2, R3, and R4."},
                {"category": "how", "q": "How is the discharge time constant calculated in Experiment 4?", "a": "First find R_eq = R2 + (R3 || R4) = 32 kΩ + (240k * 60k)/(240k + 60k) = 32 kΩ + 48 kΩ = 80 kΩ. Then tau = R_eq * C1 = 80 kΩ * 0.5 µF = 40 ms."},
                {"category": "component", "q": "What is the purpose of `Rtesta` and `Rtestb` in Experiment 4?", "a": "They provide a DC path to ground and load termination for the control pulse voltage sources `Vpulse2` and `Vpulse3` at nodes `posa` and `posb`."},
                {"category": "procedure", "q": "How do you set the initial capacitor voltage in PySpice before running transient analysis?", "a": "By calling `simulator.initial_condition(output=0@u_V)` before `simulator.transient(...)`."},
                {"category": "code", "q": "How is the switch model declared in PySpice?", "a": "Using `circuit.model('switch', 'SW', Ron=1@u_mOhm, Roff=1@u_GOhm)`."},
                {"category": "topology", "q": "How are R2, R3, and R4 connected in the discharge network of Experiment 4?", "a": "R3 and R4 are in parallel between Node 2 and GND, and R2 is in series between Switch S2 (Node 'b') and Node 2."},
                {"category": "calculation", "q": "What is the capacitor voltage at 1 time constant after switching (t = 50 ms + 40 ms = 90 ms)?", "a": "V_C(90 ms) = 100 V * e^(-1) ≈ 36.79 V."},
                {"category": "troubleshooting", "q": "What happens if a student asks for Capacitor Voltage plot and the script only runs `simulator.transient()` without `matplotlib`?", "a": "No waveform is displayed or saved; the script must extract `analysis['output']`, plot it against `analysis.time`, label axes, and call `plt.show()` / `plt.savefig()`."},
                {"category": "expected_output", "q": "What happens to the discharge curve if C1 is doubled from 0.5 µF to 1.0 µF?", "a": "The discharge time constant tau doubles from 40 ms to 80 ms, so the capacitor discharges twice as slowly."}
            ]
        },
        5: {
            "exp_number": 5,
            "title": "Simulating Step Response of RC Circuits Using PySpice",
            "category": "Transient / RC",
            "family": "PYSPICE_TRANSIENT",
            "pages": [12, 13, 14],
            "aim": "To simulate the step response of an RC circuit under switched DC excitation in PySpice and plot the capacitor voltage transition.",
            "apparatus_components": [
                "Pre-Switching DC Source V1 = 40 V (Node 1 to GND)",
                "Pre-Switching Divider Resistors R1 = 10 kΩ (Node 1 to 2), R2 = 10 kΩ (Node 2 to GND)",
                "Voltage-Controlled Switch S1 (Node 2 to 'output', controlled by 'posa')",
                "Capacitor C1 = 0.25 µF (Node 'output' to GND)",
                "Voltage-Controlled Switch S2 (Node 'output' to 'b', controlled by 'posb')",
                "Post-Switching Series Resistor R3 = 160 kΩ (Node 'b' to Node 4)",
                "Post-Switching Resistors R4 = 200 kΩ (Node 4 to GND), R5 = 50 kΩ (Node 3 to Node 4)",
                "Post-Switching Forcing DC Source V2 = 75 V (GND to Node 3, so V(3) = -75 V)",
                "Control Pulse Sources Vpulse2 ('posa') and Vpulse3 ('posb') switching at 20 ms"
            ],
            "theory": (
                "The step response of an RC circuit occurs when a capacitor with initial voltage V_0 is switched to a "
                "new Thevenin forcing network with steady-state voltage V_inf and equivalent resistance R_eq. In Experiment 5, "
                "before t_sw = 20 ms, S1 is closed and C1 charges to the Thevenin voltage of (V1, R1, R2): "
                "V_0 = 40 V * (10k / (10k + 10k)) = 20 V. At t_sw = 20 ms, S1 opens and S2 closes, connecting C1 through "
                "R3 (160 kΩ) to the divider formed by R4 (200 kΩ), R5 (50 kΩ), and V2 (-75 V at Node 3). "
                "The post-switching Thevenin voltage is V_inf = -75 V * (200k / (200k + 50k)) = -60 V, and "
                "R_eq = R3 + (R4 || R5) = 160 kΩ + 40 kΩ = 200 kΩ, giving tau_post = R_eq * C1 = 200 kΩ * 0.25 µF = 50 ms."
            ),
            "equations": [
                "Pre-Switch Steady-State Voltage: V_0 = V1 * R2 / (R1 + R2) = 40 * (10k / 20k) = 20 V",
                "Post-Switch Final Steady-State Voltage: V_inf = -V2 * R4 / (R4 + R5) = -75 * (200k / 250k) = -60 V",
                "Post-Switch Equivalent Resistance: R_eq = R3 + (R4 * R5) / (R4 + R5) = 160 kΩ + 40 kΩ = 200 kΩ",
                "Post-Switch Time Constant: tau = R_eq * C1 = 200 kΩ * 0.25 µF = 50 ms",
                "Step Response Equation (t >= 20 ms): V_C(t) = V_inf + (V_0 - V_inf) * exp(-(t - 0.02) / 0.05) = -60 + 80 * exp(-(t - 0.02) / 0.05) V"
            ],
            "circuit_topology": "Two-stage Thevenin-equivalent switched RC circuit with pre-switch divider (V1, R1, R2) and post-switch forcing network (V2, R3, R4, R5).",
            "component_relationships": [
                "V1: N1 -> GND (40 V)",
                "R1: N1 -> N2 (10 kΩ), R2: N2 -> GND (10 kΩ)",
                "S1: N2 -> output (closed for t < 20 ms)",
                "C1: output -> GND (0.25 µF)",
                "S2: output -> Nb (closed for t >= 20 ms)",
                "R3: Nb -> N4 (160 kΩ)",
                "R4: N4 -> GND (200 kΩ)",
                "R5: N3 -> N4 (50 kΩ)",
                "V2: GND -> N3 (75 V, making Node 3 = -75 V)"
            ],
            "simulation_type": "Transient Analysis (step_time=1@u_us, end_time=250@u_ms)",
            "procedure": (
                "1. Set `steptime=1@u_us`, `switchingtime=20@u_ms`, `finaltime=250@u_ms`.\n"
                "2. Add control pulse sources `Vpulse2` and `Vpulse3` and switch model `'SW'`.\n"
                "3. Add pre-switching network (V1, R1, R2, S1), capacitor C1, and post-switching network (S2, R3, R4, R5, V2).\n"
                "4. Run `simulator.transient(step_time=steptime, end_time=finaltime)`.\n"
                "5. Plot `analysis['output']` vs time."
            ),
            "expected_observations": "Capacitor charges rapidly to +20 V before t = 20 ms, then transitions exponentially from +20 V toward -60 V with time constant tau = 50 ms.",
            "result": "The step response of the RC circuit was simulated in PySpice and the transition from V_0 = 20 V to V_inf = -60 V was verified.",
            "common_mistakes": [
                "Connecting V2 as (3, gnd) instead of (gnd, 3), which changes V_inf from -60 V to +60 V",
                "Replacing the 5-resistor dual-switch Experiment 5 circuit with a 1-resistor circuit without asking the user"
            ],
            "important_terminology": ["Step Response", "Initial Voltage V(0+)", "Final Steady-State Voltage V(inf)", "Thevenin Equivalent Resistance", "Forced Response"],
            "related_experiments": [4, 6],
            "viva_concepts": [
                {"category": "definition", "q": "What is the complete step response of an RC circuit?", "a": "It is the sum of the natural response and forced response when an RC circuit with initial capacitor voltage V_0 is subjected to a sudden DC source change: V_C(t) = V_inf + (V_0 - V_inf) * e^(-t/tau)."},
                {"category": "why", "q": "Why does the capacitor voltage settle at 20 V instead of 40 V before switching in Experiment 5?", "a": "Because R1 (10 kΩ) and R2 (10 kΩ) form an equal voltage divider across V1 (40 V), so the Thevenin voltage seen by C1 is 40 V * (10k / 20k) = 20 V."},
                {"category": "how", "q": "How is the final steady-state voltage V_inf = -60 V obtained in Experiment 5?", "a": "V2 (75 V) has its positive terminal at GND and negative at Node 3, so V(3) = -75 V. With C1 open-circuited in steady state, R4 (200 kΩ) and R5 (50 kΩ) divide -75 V to give V(4) = -75 * (200k / 250k) = -60 V."},
                {"category": "component", "q": "What is the post-switching equivalent resistance R_eq in Experiment 5?", "a": "Looking from C1 into S2 after switching, R_eq = R3 + (R4 || R5) = 160 kΩ + (200k * 50k)/(200k + 50k) = 160 kΩ + 40 kΩ = 200 kΩ."},
                {"category": "procedure", "q": "At what time does the switch transition occur in Experiment 5?", "a": "At `switchingtime = 20@u_ms` (20 milliseconds)."},
                {"category": "code", "q": "How is V2's inverted polarity written in PySpice for Experiment 5?", "a": "`circuit.V(2, circuit.gnd, 3, 75@u_V)` — placing `circuit.gnd` as the positive node and `3` as the negative node."},
                {"category": "topology", "q": "What is the pre-switching Thevenin resistance and time constant in Experiment 5?", "a": "R_th_pre = R1 || R2 = 10 kΩ || 10 kΩ = 5 kΩ, so tau_pre = 5 kΩ * 0.25 µF = 1.25 ms."},
                {"category": "calculation", "q": "What is the capacitor voltage at t = 20 ms + 50 ms = 70 ms in Experiment 5?", "a": "V_C(70 ms) = -60 + (20 - (-60)) * e^(-1) = -60 + 80 * 0.3679 = -30.57 V."},
                {"category": "troubleshooting", "q": "Why must we always include `plt.plot(analysis.time, analysis['output'])` when the user asks to show capacitor voltage?", "a": "Because requested outputs are explicit requirements; running `.transient()` without extracting and plotting `analysis['output']` leaves the task incomplete."},
                {"category": "expected_output", "q": "How long after switching (t = 20 ms) does the capacitor take to reach within 1% of -60 V?", "a": "About 5 time constants: 5 * 50 ms = 250 ms after switching."}
            ]
        },
        6: {
            "exp_number": 6,
            "title": "Simulation of a Pacemaker Circuit in PySpice",
            "category": "Biomedical / PySpice",
            "family": "PYSPICE_TRANSIENT",
            "pages": [15, 16, 17, 18],
            "aim": "To design and simulate a cardiac pacemaker timing and discharge circuit in PySpice for a specified heart rate (BPM) and switching threshold factor.",
            "apparatus_components": [
                "DC Supply Voltage Vs (V1) = 6 V (Node 1 to GND)",
                "Calculated Timing Resistor R1 = 755.9 kΩ (Node 1 to 'control', computed from H=70 BPM, C1=1 µF, switching_factor=0.68)",
                "Timing Capacitor C1 = 1 µF (Node 'control' to GND)",
                "Voltage-Controlled Switch S1 (Node 'control' to 'out', threshold Vo = 0.68 * Vs = 4.08 V)",
                "Heart Muscle Equivalent Load Resistor R2 = 1 kΩ (Node 'out' to GND)"
            ],
            "theory": (
                "An artificial cardiac pacemaker generates periodic electrical impulses to stimulate heart contraction. "
                "In Experiment 6, capacitor C1 (1 µF) charges from supply Vs (6 V) through timing resistor R1 until "
                "the capacitor voltage reaches the threshold Vo = switching_factor * Vs (0.68 * 6 V = 4.08 V) at the end "
                "of one heartbeat period T = 60 / H. Using V_C(T) = Vs * (1 - exp(-T / (R1*C1))), the required timing "
                "resistance is R1 = -T / (C1 * ln(1 - Vo/Vs)). When V_C reaches Vo, Switch S1 closes and discharges C1 "
                "rapidly into the 1 kΩ cardiac load resistor R2."
            ),
            "equations": [
                "Cardiac Period: T = 60 / H (for H = 70 BPM, T = 0.8571 s)",
                "Switching Threshold Voltage: Vo = switching_factor * Vs = 0.68 * 6 V = 4.08 V",
                "Timing Resistor Formula: R1 = -(60 / H) / (C1 * ln(1 - Vo / Vs))",
                "For H = 70 BPM, Vs = 6 V, C1 = 1 µF, Vo/Vs = 0.68: R1 = 0.8571 / (1e-6 * 1.1394) ≈ 752.2 kΩ"
            ],
            "circuit_topology": "RC charging relaxation network (Vs -> R1 -> C1 at node 'control') coupled via threshold switch S1 to cardiac load resistor R2 at node 'out'.",
            "component_relationships": [
                "V1 (Vs): N1 -> GND (6 V DC supply)",
                "R1: N1 -> control (calculated timing resistor)",
                "C1: control -> GND (1 µF timing capacitor)",
                "S1: control -> out (closes when V(control) >= Vo)",
                "R2: out -> GND (1 kΩ heart tissue load)"
            ],
            "simulation_type": "Theoretical R1 Calculation + Transient Analysis (simulator.transient)",
            "procedure": (
                "1. Specify heart rate `H` (BPM), supply `Vs` (6V), `C1` (1µF), and `switching_factor` (0.68).\n"
                "2. Calculate threshold `Vo = switching_factor * Vs` and timing resistor `R1 = -(60 / H) / (C1 * math.log(1 - Vo / Vs))`.\n"
                "3. Build the PySpice circuit with V1, R1, C1, S1, and R2 (1 kΩ).\n"
                "4. Run transient simulation and plot the charging voltage at `'control'` and pacing pulse at `'out'`."
            ),
            "expected_observations": "Capacitor voltage at node `'control'` rises exponentially from 0 V to threshold Vo = 4.08 V in T = 0.857 s, triggering Switch S1 and delivering a sharp 4.08 V pacing spike across R2 at node `'out'`.",
            "result": "The pacemaker circuit was simulated in PySpice, R1 was calculated for the target heart rate, and the pacing waveform was verified.",
            "common_mistakes": [
                "Using log10 instead of natural logarithm `math.log` (`ln`) when calculating R1",
                "Forgetting to convert heart rate H (BPM) into period T = 60 / H seconds"
            ],
            "important_terminology": ["Pacemaker", "Beats Per Minute (BPM)", "Switching Factor", "Threshold Voltage (Vo)", "Relaxation Oscillator"],
            "related_experiments": [4, 5],
            "viva_concepts": [
                {"category": "definition", "q": "How does an RC timing circuit work in a cardiac pacemaker?", "a": "The capacitor charges exponentially through a calibrated resistor R1 until it hits a trigger voltage Vo after T = 60/BPM seconds, firing a discharge pulse into the heart load R2."},
                {"category": "why", "q": "Why is R2 (1 kΩ) much smaller than R1 (~752 kΩ) in the pacemaker circuit?", "a": "R1 must be large so C1 charges slowly over ~0.86 seconds, whereas R2 must be small (1 kΩ) so C1 discharges rapidly in a few milliseconds to deliver a crisp pacing pulse."},
                {"category": "how", "q": "How do you calculate the timing resistor R1 for a heart rate of 80 BPM with C1 = 1 µF and switching factor 0.68?", "a": "T = 60 / 80 = 0.75 s. Since -ln(1 - 0.68) = -ln(0.32) = 1.1394, R1 = 0.75 / (1e-6 * 1.1394) ≈ 658.2 kΩ."},
                {"category": "component", "q": "What does resistor R2 represent physically in Experiment 6?", "a": "R2 (1 kΩ) models the electrical impedance of the heart muscle (myocardium) across the pacemaker electrodes."},
                {"category": "procedure", "q": "What happens to the calculated R1 if the patient requires a faster heart rate (higher BPM)?", "a": "A higher BPM requires a shorter period T = 60/H, so R1 must decrease proportionally to charge C1 faster."},
                {"category": "code", "q": "Why does the R1 formula in Experiment 6 independent of the supply voltage magnitude Vs when `switching_factor = Vo/Vs` is fixed?", "a": "Because `Vo / Vs` is the dimensionless switching factor (0.68), so Vs cancels out inside `ln(1 - Vo/Vs)`."},
                {"category": "topology", "q": "Which node holds the timing capacitor voltage and which node delivers the output pulse in Experiment 6?", "a": "Node `'control'` holds the timing capacitor voltage across C1, and Node `'out'` delivers the pacing pulse across R2."},
                {"category": "calculation", "q": "What is the peak discharge current delivered to the 1 kΩ load R2 when Vs = 6 V and switching factor = 0.68?", "a": "Vo = 0.68 * 6 V = 4.08 V, so I_peak = Vo / R2 = 4.08 V / 1 kΩ = 4.08 mA."},
                {"category": "troubleshooting", "q": "Why would `math.log(1 - Vo/Vs)` raise a ValueError in Python?", "a": "If `Vo >= Vs` (`switching_factor >= 1.0`), `1 - Vo/Vs <= 0`, which is physically impossible because an RC circuit fed by Vs can never charge above Vs."},
                {"category": "expected_output", "q": "What is the discharge time constant when Switch S1 closes in Experiment 6?", "a": "tau_discharge = R2 * C1 = 1 kΩ * 1 µF = 1 ms, which is ~750 times faster than the charging time constant."}
            ]
        },
        7: {
            "exp_number": 7,
            "title": "Verification of Truth Tables of Logic Gates Using Multisim",
            "category": "Digital Logic",
            "family": "DIGITAL_LOGIC",
            "pages": [19, 20, 21, 22, 23, 24],
            "aim": "To verify the truth tables of basic and universal digital logic gates (AND, OR, NOT, NAND, NOR, XOR, XNOR) using Multisim / digital logic simulation.",
            "apparatus_components": [
                "AND Gate (IC 7408)",
                "OR Gate (IC 7432)",
                "NOT Gate / Inverter (IC 7404)",
                "NAND Gate (IC 7400)",
                "NOR Gate (IC 7402)",
                "XOR Gate (IC 7486)",
                "XNOR Gate (IC 74266)",
                "Interactive Digital Constants (0/1) and Digital Voltage Probes / Indicators"
            ],
            "theory": (
                "Digital logic gates perform fundamental Boolean algebra operations on binary inputs (0 = LOW = 0 V, "
                "1 = HIGH = 5 V TTL). AND outputs 1 only when all inputs are 1; OR outputs 1 when at least one input is 1; "
                "NOT inverts its input; NAND and NOR are universal gates that invert AND and OR respectively; "
                "XOR outputs 1 when inputs differ (odd parity); XNOR outputs 1 when inputs are equal (even parity)."
            ),
            "equations": [
                "AND: Y = A · B",
                "OR: Y = A + B",
                "NOT: Y = A'",
                "NAND: Y = (A · B)'",
                "NOR: Y = (A + B)'",
                "XOR: Y = A ⊕ B = A'B + AB'",
                "XNOR: Y = (A ⊕ B)' = A'B' + AB"
            ],
            "circuit_topology": "Digital testbench driving 2-input gates (AND, OR, NAND, NOR, XOR, XNOR) and 1-input inverter (NOT) across all 4 binary input combinations (00, 01, 10, 11).",
            "component_relationships": [
                "Inputs A, B -> Gate Input Pins (1, 2)",
                "Gate Output Pin (3) -> Digital Probe / LED Indicator"
            ],
            "simulation_type": "Digital Truth-Table Verification across all 2^N binary states",
            "procedure": (
                "1. Place the logic gate IC (7408, 7432, 7404, 7400, 7402, 7486, or 74266) on the schematic.\n"
                "2. Connect interactive digital switches for inputs A and B and a digital probe at output Y.\n"
                "3. Toggle (A, B) through (0,0), (0,1), (1,0), (1,1) and record output Y in the truth table."
            ),
            "expected_observations": "For (A,B) in [00, 01, 10, 11]: AND=[0,0,0,1], OR=[0,1,1,1], NAND=[1,1,1,0], NOR=[1,0,0,0], XOR=[0,1,1,0], XNOR=[1,0,0,1].",
            "result": "The truth tables of all seven logic gates (AND, OR, NOT, NAND, NOR, XOR, XNOR) were verified.",
            "common_mistakes": [
                "Confusing XOR and XNOR truth table outputs for inputs (0,0) and (1,1)",
                "Leaving TTL input pins floating instead of tying them to logic 0 or 1"
            ],
            "important_terminology": ["Truth Table", "Universal Gate (NAND, NOR)", "TTL 74xx Series", "Parity (XOR/XNOR)", "Boolean Algebra"],
            "related_experiments": [8, 9, 10],
            "viva_concepts": [
                {"category": "definition", "q": "Why are NAND and NOR gates called universal gates?", "a": "Because any Boolean function (NOT, AND, OR, XOR, etc.) can be implemented using only NAND gates or only NOR gates."},
                {"category": "why", "q": "Why is an XOR gate also called an inequality detector or odd-parity gate?", "a": "Because its output is 1 if and only if its two inputs are unequal (01 or 10), which corresponds to an odd number of 1s."},
                {"category": "how", "q": "How do you make a NOT gate from a 2-input NAND or NOR gate?", "a": "Tie both input terminals of the NAND (or NOR) gate together to the same input signal A, or tie one input of a NAND gate to logic 1."},
                {"category": "component", "q": "Match the 74xx TTL IC numbers: 7400, 7402, 7404, 7408, 7432, 7486.", "a": "7400 = NAND, 7402 = NOR, 7404 = NOT, 7408 = AND, 7432 = OR, 7486 = XOR."},
                {"category": "procedure", "q": "How many rows are in the truth table of an N-input logic gate?", "a": "2^N rows (4 rows for 2 inputs, 8 rows for 3 inputs)."},
                {"category": "code", "q": "How areXOR and XNOR expressed in Python bitwise/boolean logic?", "a": "XOR is `A ^ B`, and XNOR is `int(not (A ^ B))` or `int(A == B)`."},
                {"category": "topology", "q": "What happens if a TTL 74xx gate input is left unconnected (floating)?", "a": "A floating TTL input typically acts as a logic HIGH (1), which can cause unexpected truth table readings and noise pickup."},
                {"category": "calculation", "q": "If A = 1 and B = 0, what are the outputs of NAND, NOR, XOR, and XNOR?", "a": "NAND(1,0) = 1, NOR(1,0) = 0, XOR(1,0) = 1, XNOR(1,0) = 0."},
                {"category": "troubleshooting", "q": "Why must truth tables be generated by a deterministic Boolean engine rather than guessed by an LLM?", "a": "Deterministic evaluation guarantees 100% accuracy for every minterm row without arithmetic or token hallucination."},
                {"category": "expected_output", "q": "For which input combinations do OR and XOR produce different outputs?", "a": "Only for (A=1, B=1), where OR outputs 1 and XOR outputs 0."}
            ]
        },
        8: {
            "exp_number": 8,
            "title": "Simulation of Half Adder and Full Adder Circuit in Multisim",
            "category": "Digital Combinational",
            "family": "DIGITAL_LOGIC",
            "pages": [25, 26, 27, 28],
            "aim": "To construct and verify the truth tables of Half Adder and Full Adder combinational arithmetic circuits.",
            "apparatus_components": [
                "XOR Gate IC 7486 (for SUM generation)",
                "AND Gate IC 7408 (for CARRY generation)",
                "OR Gate IC 7432 (for Full Adder Carry-Out combination)",
                "Interactive Digital Inputs (A, B, Cin) and Output Probes (Sum, Cout)"
            ],
            "theory": (
                "A Half Adder adds two 1-bit binary numbers A and B, producing Sum = A ⊕ B and Carry = A · B. "
                "Because it cannot accept a carry-in from a lower significant stage, a Full Adder adds three 1-bit "
                "binary numbers (A, B, Cin) and produces Sum = A ⊕ B ⊕ Cin and Cout = AB + (A ⊕ B)Cin = AB + BCin + ACin."
            ),
            "equations": [
                "Half Adder SUM = A ⊕ B",
                "Half Adder CARRY = A · B",
                "Full Adder SUM = A ⊕ B ⊕ Cin",
                "Full Adder CARRY (Cout) = A·B + Cin·(A ⊕ B) = A·B + B·Cin + A·Cin"
            ],
            "circuit_topology": "Half Adder: 1 XOR + 1 AND in parallel across (A, B). Full Adder: two cascaded Half Adders with their carry outputs combined by an OR gate.",
            "component_relationships": [
                "XOR1(A, B) -> S1",
                "AND1(A, B) -> C1",
                "XOR2(S1, Cin) -> Sum",
                "AND2(S1, Cin) -> C2",
                "OR1(C1, C2) -> Cout"
            ],
            "simulation_type": "Digital Combinational Truth-Table Verification (4 states for Half Adder, 8 states for Full Adder)",
            "procedure": (
                "1. For Half Adder, wire inputs A, B to an XOR gate (Sum) and an AND gate (Carry).\n"
                "2. Verify all 4 input states (00, 01, 10, 11).\n"
                "3. For Full Adder, cascade a second XOR and AND gate with input Cin, and OR the two carry terms.\n"
                "4. Verify all 8 input states (000 through 111)."
            ),
            "expected_observations": "Full Adder outputs Sum=1 when an odd number of inputs are 1 (001, 010, 100, 111) and Cout=1 when at least two inputs are 1 (011, 101, 110, 111).",
            "result": "The Half Adder and Full Adder circuits were simulated and their truth tables were verified.",
            "common_mistakes": [
                "Using an XOR gate instead of an OR gate to combine the two intermediate carry outputs in a Full Adder",
                "Forgetting the Carry-In (Cin) input when building the Full Adder truth table"
            ],
            "important_terminology": ["Half Adder", "Full Adder", "Carry-In (Cin)", "Carry-Out (Cout)", "Cascaded Addition"],
            "related_experiments": [7, 9, 10],
            "viva_concepts": [
                {"category": "definition", "q": "What is the main limitation of a Half Adder?", "a": "A Half Adder has no Carry-In (Cin) input, so it cannot add the carry bit propagated from a previous lower-order bit position."},
                {"category": "why", "q": "Why is the Full Adder Carry-Out expression `AB + BCin + ACin` called the majority function?", "a": "Because Cout is 1 whenever a majority (2 or all 3) of the inputs A, B, Cin are 1."},
                {"category": "how", "q": "How do you build a Full Adder from two Half Adders?", "a": "Connect the first Half Adder to A and B to get S1 = A⊕B and C1 = AB. Connect the second Half Adder to S1 and Cin to get Sum = S1⊕Cin and C2 = S1·Cin. Combine C1 and C2 with an OR gate to get Cout."},
                {"category": "component", "q": "How many 2-input XOR, AND, and OR gates are in a standard Full Adder?", "a": "Two 2-input XOR gates, two 2-input AND gates, and one 2-input OR gate (5 gates total)."},
                {"category": "procedure", "q": "For which input row of the Full Adder are both Sum and Cout equal to 1?", "a": "Only when A = 1, B = 1, and Cin = 1 (binary 1 + 1 + 1 = 3 = 11_2)."},
                {"category": "code", "q": "Can the final OR gate in a two-half-adder Full Adder be replaced by an XOR gate?", "a": "Yes, because C1 = A·B and C2 = (A⊕B)·Cin can never both be 1 simultaneously, so C1 + C2 is identical to C1 ⊕ C2."},
                {"category": "topology", "q": "How many Full Adders are needed to build a 4-bit ripple carry adder?", "a": "One Half Adder (for the LSB) and three Full Adders, or four Full Adders with the first Cin tied to 0."},
                {"category": "calculation", "q": "If A = 1, B = 0, Cin = 1, what are S1, C1, C2, Sum, and Cout?", "a": "S1 = 1⊕0 = 1; C1 = 1·0 = 0; Sum = 1⊕1 = 0; C2 = 1·1 = 1; Cout = 0 + 1 = 1. (So Sum = 0, Cout = 1)."},
                {"category": "troubleshooting", "q": "If a student's Full Adder gives Cout = 0 when A=1, B=1, Cin=1, what mistake did they likely make?", "a": "They likely connected the second AND gate to (A, Cin) incorrectly or omitted the OR gate combining C1 and C2."},
                {"category": "expected_output", "q": "Which minterms produce Sum = 1 and which produce Cout = 1 in a Full Adder?", "a": "Sum = Sigma_m(1, 2, 4, 7) and Cout = Sigma_m(3, 5, 6, 7)."}
            ]
        },
        9: {
            "exp_number": 9,
            "title": "Implementation of Boolean Function in SOP and POS Form Using Multisim",
            "category": "Boolean Algebra",
            "family": "DIGITAL_LOGIC",
            "pages": [29, 30, 31, 32, 33],
            "aim": "To implement a 3-variable Boolean function in both Sum of Products (SOP) and Product of Sums (POS) forms and verify their equivalence via truth table.",
            "apparatus_components": [
                "NOT Gates (IC 7404) for complemented literals A', B', C'",
                "3-Input AND Gates (IC 7411) and OR Gates (IC 7432) for SOP implementation",
                "3-Input OR Gates and AND Gates for POS implementation",
                "3 Binary Inputs (A, B, C) and Output Indicator Y"
            ],
            "theory": (
                "Any Boolean function can be expressed canonically as a Sum of Products (SOP, ORing minterms where output = 1) "
                "or a Product of Sums (POS, ANDing maxterms where output = 0). In Experiment 9, the manual implements "
                "XSOP = Sigma_m(1, 3, 6) = A'B'C + A'BC + ABC' (which simplifies to A'C + ABC') and the complementary POS form "
                "XPOS = Pi_M(0, 2, 4, 5, 7)."
            ),
            "equations": [
                "Canonical SOP: XSOP = Sigma_m(1, 3, 6) = A'B'C + A'BC + ABC'",
                "Simplified SOP: XSOP = A'C + ABC'",
                "Canonical POS: XPOS = Pi_M(0, 2, 4, 5, 7) = (A+B+C)(A+B'+C)(A'+B+C)(A'+B+C')(A'+B'+C')"
            ],
            "circuit_topology": "Two-level AND-OR network (for SOP) and two-level OR-AND network (for POS) driven by input rails A, B, C and their complements A', B', C'.",
            "component_relationships": [
                "Inverters generate A', B', C' from inputs A, B, C",
                "AND1(A', B', C) -> m1",
                "AND2(A', B, C) -> m3",
                "AND3(A, B, C') -> m6",
                "OR(m1, m3, m6) -> Output Y"
            ],
            "simulation_type": "Digital 3-Variable Truth-Table Verification (8 states m0..m7)",
            "procedure": (
                "1. Derive the minterm list Sigma_m(1, 3, 6) from the Boolean expression.\n"
                "2. Construct the AND-OR circuit for SOP (or OR-AND circuit for POS).\n"
                "3. Step inputs (A, B, C) from 000 (m0) to 111 (m7) and verify Y = 1 only at m1 (001), m3 (011), and m6 (110)."
            ),
            "expected_observations": "Output Y = 1 for rows m1 (0,0,1), m3 (0,1,1), and m6 (1,1,0); Output Y = 0 for rows m0, m2, m4, m5, m7.",
            "result": "The Boolean function was implemented in both SOP and POS forms and their identical 8-row truth tables were verified.",
            "common_mistakes": [
                "Using uncomplemented variables where maxterms require complemented variables in POS form",
                "Confusing minterm numbering (e.g., mistaking 110 for m3 instead of m6)"
            ],
            "important_terminology": ["Sum of Products (SOP)", "Product of Sums (POS)", "Minterm (m_i)", "Maxterm (M_i)", "Canonical Form"],
            "related_experiments": [7, 8, 10],
            "viva_concepts": [
                {"category": "definition", "q": "What is the difference between a minterm and a maxterm?", "a": "A minterm is an AND product term of all variables that equals 1 for a single input combination, whereas a maxterm is an OR sum term of all variables that equals 0 for a single input combination."},
                {"category": "why", "q": "Why are variables with value 1 complemented in a maxterm (POS) but uncomplemented in a minterm (SOP)?", "a": "Because a minterm (AND) needs all inputs to be 1 to output 1, while a maxterm (OR) needs all inputs to be 0 to output 0."},
                {"category": "how", "q": "How can `A'B'C + A'BC + ABC'` in Experiment 9 be simplified algebraically?", "a": "Factor `A'C` from the first two terms: `A'C(B' + B) + ABC' = A'C(1) + ABC' = A'C + ABC'`."},
                {"category": "component", "q": "What two-level gate structure implements an SOP expression?", "a": "A first level of AND gates (producing the product terms) feeding a second-level OR gate (summing the products)."},
                {"category": "procedure", "q": "If a 3-variable function has minterms Sigma_m(1, 3, 6), what are its maxterms?", "a": "All remaining indices from 0..7: Pi_M(0, 2, 4, 5, 7)."},
                {"category": "code", "q": "How do you evaluate `XSOP = A'B'C + A'BC + ABC'` for all 8 states in Python?", "a": "Loop `for i in range(8): A, B, C = (i>>2)&1, (i>>1)&1, i&1; Y = int(((not A) and (not B) and C) or ((not A) and B and C) or (A and B and (not C)))`."},
                {"category": "topology", "q": "What two-level gate structure implements a POS expression?", "a": "A first level of OR gates (forming the sum terms) feeding a second-level AND gate."},
                {"category": "calculation", "q": "Evaluate Y for (A=1, B=1, C=0) and (A=1, B=1, C=1) in Experiment 9.", "a": "For (1,1,0) [m6], ABC' = 1·1·1 = 1 so Y = 1. For (1,1,1) [m7], all minterms are 0 so Y = 0."},
                {"category": "troubleshooting", "q": "If the SOP circuit outputs 1 for (0,1,0) instead of (1,1,0), what wiring error occurred?", "a": "Input A on the third AND gate was accidentally connected to A' instead of A."},
                {"category": "expected_output", "q": "How many 1s and how many 0s appear in the output column of Experiment 9?", "a": "Three 1s (at m1, m3, m6) and five 0s (at m0, m2, m4, m5, m7)."}
            ]
        },
        10: {
            "exp_number": 10,
            "title": "Implementation of Combinational Circuit Using Minimum Number of NAND Gates Using Multisim",
            "category": "Digital Combinational",
            "family": "DIGITAL_LOGIC",
            "pages": [34, 35, 36],
            "aim": "To implement a Boolean combinational function (such as F = AB + BC + AC or Experiment 9's SOP function) using the minimum number of universal NAND gates.",
            "apparatus_components": [
                "2-Input and 3-Input NAND Gates (IC 7400 / IC 7410)",
                "Digital Inputs (A, B, C) and Output Probe F"
            ],
            "theory": (
                "By De Morgan's theorem and double negation, any two-level AND-OR (SOP) circuit can be converted "
                "directly into a two-level NAND-NAND circuit: F = AB + BC + AC = ((AB + BC + AC)')' = ((AB)' · (BC)' · (AC)')'. "
                "Every first-level AND gate and the second-level OR gate are replaced by NAND gates, eliminating the need "
                "for separate AND, OR, and NOT IC packages."
            ),
            "equations": [
                "Target Function: F = A·B + B·C + A·C (or XSOP = A'C + ABC')",
                "Double Inversion: F = ((A·B + B·C + A·C)')'",
                "De Morgan NAND-NAND Form: F = ( (A·B)' · (B·C)' · (A·C)' )'"
            ],
            "circuit_topology": "Two-level all-NAND network where first-stage NAND gates compute `(AB)'`, `(BC)'`, `(AC)'` and a final 3-input NAND gate combines them into `F`.",
            "component_relationships": [
                "NAND1(A, B) -> N_AB",
                "NAND2(B, C) -> N_BC",
                "NAND3(A, C) -> N_AC",
                "NAND4(N_AB, N_BC, N_AC) -> Output F"
            ],
            "simulation_type": "Digital Combinational All-NAND Truth-Table Verification",
            "procedure": (
                "1. Minimize the Boolean expression using a K-map into minimum SOP form.\n"
                "2. Apply double inversion and De Morgan's Law to convert AND-OR into NAND-NAND form.\n"
                "3. Wire the circuit using only NAND gates (using single-input-tied NANDs as inverters if needed).\n"
                "4. Verify all 8 rows of the 3-input truth table."
            ),
            "expected_observations": "The NAND-only implementation produces the exact same 8-row truth table as the original AND-OR SOP circuit while using a single IC family.",
            "result": "The combinational logic circuit was implemented using the minimum number of NAND gates and its truth table was verified.",
            "common_mistakes": [
                "Adding an extra inverter after the final NAND gate, which outputs F' instead of F",
                "Failing to simplify the SOP expression via K-map before converting to NAND gates"
            ],
            "important_terminology": ["Universal NAND Gate", "De Morgan's Theorem", "Double Negation", "NAND-NAND Realization", "Karnaugh Map (K-Map) Minimization"],
            "related_experiments": [7, 8, 9],
            "viva_concepts": [
                {"category": "definition", "q": "Why is NAND-NAND implementation preferred in digital hardware design?", "a": "Because NAND gates have smaller transistor count, faster propagation delay in CMOS/TTL, and allow an entire board to use a single quad-NAND IC type (7400)."},
                {"category": "why", "q": "Why does a two-level AND-OR circuit convert directly into a two-level NAND-NAND circuit?", "a": "Because the output bubble of the first-level NAND gates cancels with the input bubbles of the negative-OR (which is functionally a NAND gate) by De Morgan's Law: ((X)' · (Y)')' = X + Y."},
                {"category": "how", "q": "How many 2-input NAND gates are needed to implement `F = A'C + ABC'`?", "a": "Using `A'C = ((A'C)')'`, one NAND inverter for `A'`, one NAND for `(A'C)'`, one 3-input NAND for `(ABC')'` (with C' from a NAND inverter), and one final NAND to combine them."},
                {"category": "component", "q": "Which TTL IC provides triple 3-input NAND gates?", "a": "The 7410 TTL IC provides three independent 3-input NAND gates."},
                {"category": "procedure", "q": "What is the first step before converting a Boolean expression to minimum NAND gates?", "a": "Minimize the Boolean expression into minimal Sum-of-Products (SOP) form using Boolean algebra or a Karnaugh map."},
                {"category": "code", "q": "How do you write a NAND function in Python?", "a": "`def nand(*inputs): return int(not all(inputs))`."},
                {"category": "topology", "q": "How do you implement an OR gate `A + B` using only 2-input NAND gates?", "a": "Use 3 NAND gates: NAND1(A,A) = A', NAND2(B,B) = B', and NAND3(A', B') = (A'·B')' = A + B."},
                {"category": "calculation", "q": "In `F = ((AB)' · (BC)' · (AC)')'`, if A=1, B=1, C=0, what are the outputs of the three first-stage NAND gates and final output F?", "a": "(AB)' = (1·1)' = 0; (BC)' = (1·0)' = 1; (AC)' = (1·0)' = 1. Final NAND(0, 1, 1) = (0·1·1)' = 1."},
                {"category": "troubleshooting", "q": "If every output bit of your NAND circuit is inverted compared to the target truth table, what is wrong?", "a": "There is either a missing second-level NAND inversion or an extra NAND inverter added at the output."},
                {"category": "expected_output", "q": "How many NAND gates are needed to build a single XOR gate `A ⊕ B`?", "a": "Four 2-input NAND gates."}
            ]
        },
        11: {
            "exp_number": 11,
            "title": "Characteristics of PN-Junction Diode in MATLAB/Simulink",
            "category": "Semiconductor / Analog",
            "family": "SIMULINK_SEMICONDUCTOR",
            "pages": [37, 38],
            "aim": "To simulate and plot the forward and reverse I-V (Current-Voltage) characteristics of a silicon PN-junction diode.",
            "apparatus_components": [
                "Variable / Ramp DC Voltage Source V1 (0 V to 10 V sweep, Node 1 to GND)",
                "Silicon PN-Junction Diode D1 (1N4007, Vf ≈ 0.7 V, Anode at Node 1, Cathode at Node 2)",
                "Current-Limiting Load Resistor R1 = 1 kΩ (Node 2 to GND)",
                "Voltage Sensor (across D1) and Current Sensor (in series with D1) feeding X-Y Graph"
            ],
            "theory": (
                "A PN-junction diode conducts current primarily in one direction (from anode to cathode). "
                "According to the Shockley diode equation, I_D = I_S * (exp(V_D / (n * V_T)) - 1). In forward bias, "
                "current is negligible until the diode voltage exceeds the silicon barrier potential (knee/cut-in voltage "
                "V_f ≈ 0.7 V), after which current rises rapidly and is limited externally by series resistor R1."
            ),
            "equations": [
                "Shockley Diode Equation: I_D = I_S * (exp(V_D / (n * V_T)) - 1)",
                "KVL Loop Equation: V_source = V_D + I_D * R1",
                "Forward Current (V_source > 0.7 V): I_D ≈ (V_source - 0.7 V) / R1",
                "Dynamic Resistance: r_d = dV_D / dI_D ≈ (n * V_T) / I_D"
            ],
            "circuit_topology": "Series loop with swept DC voltage source V1 (N1 -> GND), forward-biased PN diode D1 (N1 -> N2), and current-limiting resistor R1 (N2 -> GND).",
            "component_relationships": [
                "V1: N1 -> GND (Swept DC / Ramp voltage source)",
                "D1: N1 (Anode) -> N2 (Cathode) (Silicon PN diode, Vf ≈ 0.7 V)",
                "R1: N2 -> GND (1 kΩ current-limiting resistor)"
            ],
            "simulation_type": "DC Sweep / Ramp Transient Simulation plotting I_D vs V_D (I-V Curve)",
            "procedure": (
                "1. Connect the swept voltage source V1, silicon diode D1, and series resistor R1 (1 kΩ) in a single loop.\n"
                "2. Measure diode voltage V_D = V(1) - V(2) and diode current I_D = V(2) / R1.\n"
                "3. Sweep V1 from -5 V to +10 V and plot I_D on the Y-axis versus V_D on the X-axis."
            ),
            "expected_observations": "For V_D < 0.6 V, I_D ≈ 0 mA. Near the knee voltage V_D ≈ 0.7 V, current turns on sharply and rises exponentially. At V1 = 10 V and R1 = 1 kΩ, V_D ≈ 0.7 V and I_D ≈ 9.3 mA.",
            "result": "The V-I characteristics of the PN-junction diode were simulated and the cut-in voltage (~0.7 V) was verified.",
            "common_mistakes": [
                "Plotting diode current against source voltage V1 instead of diode terminal voltage V_D = V(1) - V(2)",
                "Omitting the current-limiting resistor R1, which causes excessive forward diode current"
            ],
            "important_terminology": ["Cut-in / Knee Voltage (0.7 V)", "Shockley Equation", "Forward Bias", "Reverse Saturation Current (I_S)", "Dynamic Resistance (r_d)"],
            "related_experiments": [12, 13, 14],
            "viva_concepts": [
                {"category": "definition", "q": "What is the cut-in (knee) voltage of a silicon PN-junction diode?", "a": "Approximately 0.7 V for silicon (and 0.3 V for germanium), which is the forward voltage threshold above which the diode conducts significant forward current."},
                {"category": "why", "q": "Why is a series resistor R1 always included when testing a diode's forward I-V curve?", "a": "Because once V_D exceeds 0.7 V, the diode's impedance becomes very small; without R1 to limit current, the current would spike exponentially and destroy the diode."},
                {"category": "how", "q": "How do you extract the diode voltage V_D and diode current I_D in a PySpice DC sweep of Experiment 11?", "a": "`v_diode = np.array(analysis['1']) - np.array(analysis['2'])` and `i_diode = np.array(analysis['2']) / R1`."},
                {"category": "component", "q": "How is the X-Y Graph block used in the Simulink model of Experiment 11?", "a": "The Voltage Sensor across the diode feeds the X-input and the Current Sensor in series with the diode feeds the Y-input to plot I_D vs V_D directly."},
                {"category": "procedure", "q": "How do you simulate reverse bias characteristics in Experiment 11?", "a": "Reverse the diode polarity (or sweep V1 across negative voltages), observing near-zero leakage current until reverse breakdown."},
                {"category": "code", "q": "How is a 1N4007 silicon diode model defined in PySpice?", "a": "`circuit.model('D1N4007', 'D', IS=1e-14@u_A, N=1.0, BV=1000@u_V)` and instantiated via `circuit.Diode(1, 1, 2, model='D1N4007')`."},
                {"category": "topology", "q": "In Experiment 11, which node is connected to the diode's anode and which to its cathode?", "a": "Node 1 (source positive terminal) connects to the Anode, and Node 2 (resistor R1) connects to the Cathode."},
                {"category": "calculation", "q": "If the source voltage is 10 V, R1 = 1 kΩ, and the silicon diode drop is 0.7 V, what is the diode current?", "a": "I_D = (10 V - 0.7 V) / 1 kΩ = 9.3 mA."},
                {"category": "troubleshooting", "q": "If the plotted I-V curve is a straight line starting from 0.7 V up to 10 V on the X-axis, what mistake was made?", "a": "The X-axis was plotted using the total source voltage V(1) instead of the voltage across the diode alone, V(1) - V(2)."},
                {"category": "expected_output", "q": "How does temperature affect the forward I-V curve of a silicon diode?", "a": "The knee voltage decreases by about 2 mV per °C increase in temperature, shifting the forward I-V curve slightly to the left."}
            ]
        },
        12: {
            "exp_number": 12,
            "title": "Design a Voltage Regulator Using Zener Diode in MATLAB/Simulink",
            "category": "Power / Analog",
            "family": "SIMULINK_SEMICONDUCTOR",
            "pages": [39, 40],
            "aim": "To design and simulate a shunt DC voltage regulator using a Zener diode in reverse breakdown and verify constant output voltage across the load.",
            "apparatus_components": [
                "Unregulated DC Input Voltage Source V1 = 12 V (Node 1 to GND)",
                "Series Current-Limiting Resistor Rs = 220 Ω (Node 1 to Node 2)",
                "Zener Diode DZ1 (Vz = 5.1 V, connected in reverse bias across load: Anode at GND, Cathode at Node 2)",
                "Load Resistor RL = 1 kΩ (Node 2 to GND)"
            ],
            "theory": (
                "A Zener diode is heavily doped to operate reliably in the reverse breakdown region at a sharp breakdown "
                "voltage V_Z (e.g., 5.1 V). In a Zener shunt regulator, series resistor R_s drops the excess input voltage "
                "(V_in - V_Z), while the reverse-biased Zener diode is connected in parallel across load resistor R_L. "
                "As long as the open-load Thevenin voltage V_th = V_in * R_L / (R_s + R_L) exceeds V_Z, the Zener clamps "
                "V_out at V_Z and absorbs any current fluctuations: I_Z = I_s - I_L."
            ),
            "equations": [
                "Unloaded Thevenin Voltage: V_th = V_in * R_L / (R_s + R_L)",
                "Regulated Output Voltage: V_out = V_Z (when V_th >= V_Z), else V_th",
                "Series Current: I_s = (V_in - V_out) / R_s",
                "Load Current: I_L = V_out / R_L",
                "Zener Current: I_Z = I_s - I_L"
            ],
            "circuit_topology": "Series resistor Rs from Node 1 to Node 2, with reverse-biased Zener diode DZ1 and load resistor RL connected in parallel from Node 2 to GND.",
            "component_relationships": [
                "V1: N1 -> GND (12 V unregulated DC input)",
                "Rs: N1 -> N2 (220 Ω series current-limiting resistor)",
                "DZ1: GND (Anode) -> N2 (Cathode) (5.1 V Zener diode in reverse bias across load)",
                "RL: N2 -> GND (1 kΩ load resistor in parallel with DZ1)"
            ],
            "simulation_type": "DC Operating Point & Line Regulation Sweep",
            "procedure": (
                "1. Connect unregulated DC supply V1 (12 V) to Node 1 and series resistor Rs (220 Ω) between Node 1 and Node 2.\n"
                "2. Connect Zener diode DZ1 (Vz = 5.1 V) in reverse bias (cathode at Node 2, anode at GND) in parallel with load resistor RL (1 kΩ).\n"
                "3. Simulate and verify that V(2) remains clamped at 5.1 V despite changes in V1 above the breakdown threshold."
            ),
            "expected_observations": "With V1 = 12 V, Rs = 220 Ω, RL = 1 kΩ, and Vz = 5.1 V: V_out = 5.1000 V, I_s = 31.36 mA, I_L = 5.10 mA, and I_Z = 26.26 mA.",
            "result": "The Zener diode voltage regulator was simulated and constant 5.1 V regulated output voltage across the load was verified.",
            "common_mistakes": [
                "Connecting the Zener diode in forward bias instead of reverse bias (which clamps V_out to 0.7 V instead of V_Z = 5.1 V)",
                "Omitting series resistor Rs, which shorts the voltage source across the Zener diode"
            ],
            "important_terminology": ["Zener Breakdown Voltage (Vz)", "Shunt Voltage Regulator", "Line Regulation", "Load Regulation", "Series Limiting Resistor (Rs)"],
            "related_experiments": [11, 13, 14],
            "viva_concepts": [
                {"category": "definition", "q": "Why is a Zener regulator called a shunt regulator?", "a": "Because the regulating Zener diode is connected in parallel (shunt) with the load resistor RL."},
                {"category": "why", "q": "Why must the Zener diode be connected in reverse bias in Experiment 12?", "a": "Because Zener voltage regulation occurs at the reverse breakdown voltage Vz (e.g., 5.1 V). In forward bias, it behaves like an ordinary diode with a 0.7 V drop."},
                {"category": "how", "q": "How do you determine if the Zener diode is in breakdown (regulating) for given V_in, Rs, and RL?", "a": "Calculate the voltage divider voltage without the Zener: V_th = V_in * RL / (Rs + RL). If V_th > Vz, the Zener is in breakdown and V_out = Vz."},
                {"category": "component", "q": "What happens if series resistor Rs is removed from the Zener regulator?", "a": "The voltage source V_in is connected directly across the Zener diode with nothing to drop (V_in - Vz), causing infinite/destructive current through the Zener."},
                {"category": "procedure", "q": "What is the minimum input voltage V_in_min required for a 5.1 V Zener to regulate with Rs = 220 Ω and RL = 1 kΩ?", "a": "V_in_min = Vz * (Rs + RL) / RL = 5.1 * (1220 / 1000) = 6.222 V."},
                {"category": "code", "q": "How do you orient a reverse-biased Zener diode at Node 2 in PySpice?", "a": "`circuit.Diode('Z1', circuit.gnd, 2, model='DZ5V1')` — anode at `circuit.gnd` and cathode at Node `2`."},
                {"category": "topology", "q": "Which components share Node 2 (the regulated output node) in Experiment 12?", "a": "Series resistor Rs (from Node 1), Zener cathode DZ1 (to GND), and load resistor RL (to GND)."},
                {"category": "calculation", "q": "For V_in = 12 V, Vz = 5.1 V, Rs = 220 Ω, and RL = 1 kΩ, calculate I_s, I_L, and I_Z.", "a": "I_s = (12 - 5.1)/220 = 31.36 mA; I_L = 5.1/1000 = 5.10 mA; I_Z = 31.36 - 5.10 = 26.26 mA."},
                {"category": "troubleshooting", "q": "If your simulation shows V_out = 0.7 V instead of 5.1 V, what is wrong?", "a": "The Zener diode anode and cathode are reversed (connected in forward bias instead of reverse bias)."},
                {"category": "expected_output", "q": "What happens to Zener current I_Z if the load resistor RL is disconnected (open load)?", "a": "I_L drops to 0, so the entire series current I_s (31.36 mA) flows through the Zener diode."}
            ]
        },
        13: {
            "exp_number": 13,
            "title": "Simulation of Half-Wave Rectifier in MATLAB/Simulink",
            "category": "Power Electronics",
            "family": "SIMULINK_SEMICONDUCTOR",
            "pages": [41],
            "aim": "To simulate a Half-Wave Rectifier circuit with and without a shunt capacitor filter and observe the rectified pulsating DC output waveform.",
            "apparatus_components": [
                "AC Sinusoidal Voltage Source V1 (Vm = 10 V peak, f = 50 Hz, Node 1 to GND)",
                "Rectifier Diode D1 (1N4007, Anode at Node 1, Cathode at Node 2)",
                "Load Resistor R1 = 1 kΩ (Node 2 to GND)",
                "Optional Shunt Filter Capacitor C1 = 100 µF (Node 2 to GND)"
            ],
            "theory": (
                "A Half-Wave Rectifier converts alternating current (AC) into unidirectional pulsating DC using a single "
                "PN-junction diode. During the positive half-cycle (V_in > 0.7 V), D1 is forward-biased and conducts current "
                "to load resistor R1, producing V_out_peak = V_m - 0.7 V. During the negative half-cycle, D1 is reverse-biased "
                "(blocking) and V_out = 0 V. Adding a shunt filter capacitor C1 in parallel with R1 smooths the output by "
                "charging to V_out_peak and discharging slowly with time constant R1*C1 during the non-conducting interval."
            ),
            "equations": [
                "Peak Rectified Load Voltage: V_peak_out = V_m - 0.7 V",
                "Average (DC) Output Voltage (unfiltered): V_dc = V_peak_out / pi ≈ 0.318 * V_peak_out",
                "RMS Output Voltage (unfiltered): V_rms = V_peak_out / 2",
                "Ripple Factor (unfiltered): gamma = 1.21; (with filter C): gamma ≈ 1 / (2 * sqrt(3) * f * R1 * C1)",
                "Maximum Rectification Efficiency: eta_max = 40.6%"
            ],
            "circuit_topology": "AC source V1 (N1 -> GND) feeding series diode D1 (N1 -> N2) and load resistor R1 (N2 -> GND), with optional filter capacitor C1 across R1.",
            "component_relationships": [
                "V1: N1 -> GND (AC Sine Source, 10 V peak, 50 Hz)",
                "D1: N1 (Anode) -> N2 (Cathode) (Series rectifier diode)",
                "R1: N2 -> GND (1 kΩ load resistor)",
                "C1 (optional): N2 -> GND (Shunt filter capacitor in parallel with R1)"
            ],
            "simulation_type": "Transient Analysis over 2–3 AC cycles (40 ms at 50 Hz)",
            "procedure": (
                "1. Connect AC sinusoidal voltage source V1 (10 V peak, 50 Hz) between Node 1 and GND.\n"
                "2. Connect diode D1 from Node 1 to Node 2 and load resistor R1 (1 kΩ) from Node 2 to GND.\n"
                "3. Run transient simulation for 40 ms and plot both input AC voltage V(1) and rectified output voltage V(2).\n"
                "4. Optionally connect filter capacitor C1 across R1 to observe ripple smoothing."
            ),
            "expected_observations": "Positive half-cycles appear at Node 2 with peak 9.3 V (10 V - 0.7 V), while negative half-cycles are clipped to 0 V.",
            "result": "The Half-Wave Rectifier was simulated and its input/output waveforms were verified.",
            "common_mistakes": [
                "Using a DC source instead of a sinusoidal source when trying to plot rectified waveforms",
                "Connecting the filter capacitor in series with the load instead of in parallel across the load"
            ],
            "important_terminology": ["Half-Wave Rectifier", "Pulsating DC", "Ripple Factor (1.21)", "Peak Inverse Voltage (PIV = Vm)", "Filter Capacitor"],
            "related_experiments": [11, 12, 14],
            "viva_concepts": [
                {"category": "definition", "q": "What is rectification?", "a": "Rectification is the conversion of bidirectional alternating current (AC) into unidirectional pulsating direct current (DC)."},
                {"category": "why", "q": "Why is the efficiency of a half-wave rectifier limited to 40.6%?", "a": "Because the entire negative half-cycle of the AC input wave is blocked and wasted, and power is only delivered during the positive half-cycle."},
                {"category": "how", "q": "How does a capacitor connected across the load reduce ripple in a half-wave rectifier?", "a": "The capacitor charges to V_peak during the positive peak and discharges slowly through the load resistor R1 with time constant R1*C1 when the diode is off, keeping V_out near V_peak."},
                {"category": "component", "q": "What is the Peak Inverse Voltage (PIV) rating required for the diode in a half-wave rectifier?", "a": "Without filter, PIV = V_m. With a capacitor filter, PIV = 2 * V_m because the cathode stays charged near +V_m while the anode swings to -V_m."},
                {"category": "procedure", "q": "What is the output ripple frequency of a half-wave rectifier driven by a 50 Hz AC supply?", "a": "50 Hz (equal to the input AC frequency f), because there is one output pulse per full AC cycle."},
                {"category": "code", "q": "How do you declare a 10 V, 50 Hz sinusoidal source in PySpice?", "a": "`circuit.SinusoidalVoltageSource(1, 1, circuit.gnd, amplitude=10@u_V, frequency=50@u_Hz)`."},
                {"category": "topology", "q": "How is the filter capacitor C1 connected relative to the load resistor R1?", "a": "In parallel (across) the load resistor R1, between Node 2 and GND."},
                {"category": "calculation", "q": "For a 15 V peak AC input and a silicon diode (0.7 V drop), what are V_peak_out and V_dc (unfiltered)?", "a": "V_peak_out = 15 - 0.7 = 14.3 V, and V_dc = 14.3 / pi ≈ 4.55 V."},
                {"category": "troubleshooting", "q": "What happens to the output waveform if diode D1 is reversed in a half-wave rectifier?", "a": "The positive half-cycles are blocked and the negative half-cycles pass through, producing a negative half-wave rectified output."},
                {"category": "expected_output", "q": "What happens to the ripple voltage if the filter capacitance C1 is increased?", "a": "The time constant R1*C1 increases, so the capacitor discharges less between peaks and the peak-to-peak ripple voltage decreases."}
            ]
        },
        14: {
            "exp_number": 14,
            "title": "Simulation of Full-Wave Rectifier in MATLAB/Simulink",
            "category": "Power Electronics",
            "family": "SIMULINK_SEMICONDUCTOR",
            "pages": [42],
            "aim": "To simulate a Full-Wave Bridge Rectifier using four diodes and observe full-cycle AC-to-DC rectification.",
            "apparatus_components": [
                "AC Sinusoidal Source V1 (Vm = 10 V peak, f = 50 Hz, connected between AC input nodes)",
                "Four Bridge Diodes D1, D2, D3, D4 (1N4007)",
                "Load Resistor R1 = 1 kΩ (across DC output terminals)",
                "Optional Shunt Filter Capacitor C1 (across load R1)"
            ],
            "theory": (
                "A Full-Wave Bridge Rectifier uses four diodes arranged in a bridge configuration so that current flows "
                "through load resistor R1 in the same direction during both half-cycles of the AC input. During the positive "
                "half-cycle, one diagonal pair of diodes conducts in series with R1; during the negative half-cycle, the "
                "other diagonal pair conducts. Because two silicon diodes conduct in series at any time, the peak output "
                "voltage is V_peak_out = V_m - 2 * 0.7 V = V_m - 1.4 V, the ripple frequency is doubled (2*f = 100 Hz), "
                "and maximum efficiency reaches 81.2%."
            ),
            "equations": [
                "Peak Rectified Load Voltage: V_peak_out = V_m - 1.4 V (two series diode drops)",
                "Average (DC) Output Voltage (unfiltered): V_dc = 2 * V_peak_out / pi ≈ 0.636 * V_peak_out",
                "RMS Output Voltage (unfiltered): V_rms = V_peak_out / sqrt(2)",
                "Output Ripple Frequency: f_ripple = 2 * f_in (100 Hz for 50 Hz input)",
                "Ripple Factor (unfiltered): gamma = 0.482; Maximum Efficiency: eta_max = 81.2%"
            ],
            "circuit_topology": "Four-diode bridge (D1..D4) driven by AC source V1, delivering full-wave rectified current to load resistor R1 (and optional parallel filter capacitor C1).",
            "component_relationships": [
                "V1: AC source driving the bridge input nodes",
                "D1, D2, D3, D4: Four-diode full-wave bridge network",
                "R1: Load resistor connected from rectified output node 'out' to GND",
                "C1 (optional): Shunt filter capacitor connected in parallel across R1 ('out' to GND)"
            ],
            "simulation_type": "Transient Analysis over 2–3 AC cycles (40 ms at 50 Hz)",
            "procedure": (
                "1. Connect four diodes D1..D4 in a bridge configuration driven by AC source V1 (10 V peak, 50 Hz).\n"
                "2. Connect load resistor R1 (1 kΩ) across the bridge DC output terminals.\n"
                "3. Run transient simulation and plot the full-wave rectified output voltage across R1."
            ),
            "expected_observations": "Both positive and negative half-cycles of the 10 V AC input are rectified into positive pulses with peak V_out = 10 V - 1.4 V = 8.6 V at 100 Hz pulse frequency.",
            "result": "The Full-Wave Bridge Rectifier was simulated and full-wave rectified output waveforms were verified.",
            "common_mistakes": [
                "Subtracting only 0.7 V instead of 1.4 V (two diode drops) when calculating peak load voltage of a bridge rectifier",
                "Shorting one of the AC input nodes directly to the DC load ground in a standard 4-diode bridge"
            ],
            "important_terminology": ["Full-Wave Bridge Rectifier", "Diagonal Diode Pair", "Two-Diode Voltage Drop (1.4 V)", "Ripple Frequency (2f)", "Rectification Efficiency (81.2%)"],
            "related_experiments": [11, 12, 13],
            "viva_concepts": [
                {"category": "definition", "q": "What is the main advantage of a Full-Wave Bridge Rectifier over a Half-Wave Rectifier?", "a": "It utilizes both half-cycles of the AC input, doubling the DC output voltage and efficiency (81.2% vs 40.6%) and lowering the ripple factor (0.482 vs 1.21) without requiring a center-tapped transformer."},
                {"category": "why", "q": "Why is the peak output voltage of a silicon bridge rectifier `Vm - 1.4 V` instead of `Vm - 0.7 V`?", "a": "Because in every half-cycle, current flows through two silicon diodes in series with the load resistor, dropping 2 * 0.7 V = 1.4 V."},
                {"category": "how", "q": "Which diodes conduct during the positive and negative half-cycles in a 4-diode bridge?", "a": "Two diagonally opposite diodes conduct during the positive half-cycle, and the other two diagonally opposite diodes conduct during the negative half-cycle."},
                {"category": "component", "q": "What is the Peak Inverse Voltage (PIV) of each diode in a Full-Wave Bridge Rectifier?", "a": "PIV = V_m (compared to 2*V_m for a center-tapped full-wave rectifier)."},
                {"category": "procedure", "q": "Why is the output ripple frequency 100 Hz when the input AC frequency is 50 Hz?", "a": "Because the negative half-cycle is inverted into a second positive pulse every period, producing two pulses per 20 ms input cycle (period = 10 ms -> 100 Hz)."},
                {"category": "code", "q": "In a SPICE simulation of a bridge rectifier, why can't both V1's negative terminal and the load resistor's negative terminal be tied to `GND` simultaneously?", "a": "Tying both to `GND` would short-circuit one of the lower bridge diodes. Either V1 must float between two non-ground AC nodes or the load voltage must be measured differentially."},
                {"category": "topology", "q": "How many diodes are required in a bridge rectifier versus a center-tapped full-wave rectifier?", "a": "A bridge rectifier requires 4 diodes (no center tap needed), whereas a center-tapped rectifier uses 2 diodes but requires a center-tapped transformer."},
                {"category": "calculation", "q": "For a 20 V peak AC source and a silicon bridge rectifier, calculate V_peak_out and V_dc (unfiltered).", "a": "V_peak_out = 20 - 1.4 = 18.6 V; V_dc = (2 * 18.6) / pi ≈ 11.84 V."},
                {"category": "troubleshooting", "q": "If one diode in a 4-diode bridge rectifier fails open-circuit, what does the output waveform look like?", "a": "One half-cycle stops conducting, so the bridge rectifier degrades into a half-wave rectifier."},
                {"category": "expected_output", "q": "Why is a capacitor filter more effective on a full-wave rectifier than on a half-wave rectifier?", "a": "Because the ripple frequency is twice as high (100 Hz vs 50 Hz), giving the capacitor only half as much time (10 ms vs 20 ms) to discharge between peaks."}
            ]
        }
    }


def build_canonical_circuit_templates() -> Dict[str, Dict[str, Any]]:
    """
    PHASE 2 — Builds 22 Canonical Circuit IR Templates:
      - 14 Official Manual Experiment Topologies (exp1 .. exp14)
      - 8 Generalized Circuit Topologies (general_rc, voltage_divider, series_resistors,
        parallel_resistors, shunted_divider_junction, series_rlc, parallel_rlc, rc_lowpass_filter)
    Each record stores explicit components, values, types, nodes, connections (e.g. R1 -> N1,N2),
    ground, control relationships, source polarity, analysis type, simulation parameters, and canonical Circuit IR.
    """
    os.makedirs(CIRCUITS_DIR, exist_ok=True)
    templates: Dict[str, Dict[str, Any]] = {}

    exp_prompts = {
        1: ("exp1_resistor_bridge", "Simulate Experiment 1 resistor bridge circuit"),
        2: ("exp2_cccs", "Simulate Experiment 2 CCCS circuit"),
        3: ("exp3_vcvs", "Simulate Experiment 3 VCVS circuit"),
        4: ("exp4_rc_natural_response", "Simulate Experiment 4 natural response of RC circuit"),
        5: ("exp5_rc_step_response", "Simulate Experiment 5 step response of RC circuit"),
        6: ("exp6_pacemaker", "Simulate Experiment 6 pacemaker circuit"),
        7: ("exp7_logic_gates", "Simulate Experiment 7 truth tables of logic gates"),
        8: ("exp8_half_full_adder", "Simulate Experiment 8 half adder and full adder"),
        9: ("exp9_boolean_sop_pos", "Simulate Experiment 9 SOP and POS boolean function"),
        10: ("exp10_nand_combinational", "Simulate Experiment 10 minimum NAND gates combinational circuit"),
        11: ("exp11_diode_iv", "Simulate Experiment 11 PN-junction diode I-V characteristics"),
        12: ("exp12_zener_regulator", "Simulate Experiment 12 Zener diode voltage regulator"),
        13: ("exp13_half_wave_rectifier", "Simulate Experiment 13 half-wave rectifier"),
        14: ("exp14_full_wave_rectifier", "Simulate Experiment 14 full-wave bridge rectifier"),
    }

    for exp_num, (tpl_id, prompt) in exp_prompts.items():
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt, experiment_context=exp_num)
        ir = recon["selected_circuit_ir"]
        comps = ir.get("components", []) if ir else []
        connections = []
        control_rels = []
        source_polarities = []
        for c in comps:
            c_nodes = c.get("nodes", [])
            if len(c_nodes) >= 2:
                n0 = f"N{c_nodes[0]}" if str(c_nodes[0]).isdigit() else str(c_nodes[0])
                n1 = f"N{c_nodes[1]}" if str(c_nodes[1]).isdigit() else str(c_nodes[1])
                connections.append(f"{c['id']} -> {n0},{n1}")
                if c.get("type") in ("dc_voltage_source", "ac_voltage_source", "current_source", "dc_current_source"):
                    source_polarities.append(f"{c['id']}: (+) {n0} to (-) {n1}")
            if c.get("controlling_source"):
                control_rels.append(f"{c['id']} controlled by current through {c['controlling_source']} (gain={c.get('gain')})")
            if c.get("control_nodes"):
                cn = c["control_nodes"]
                control_rels.append(f"{c['id']} controlled by nodes ({cn[0]}, {cn[1]})")

        tpl_record = {
            "template_id": tpl_id,
            "experiment_number": exp_num,
            "topology_category": "EXACT MANUAL TOPOLOGY",
            "circuit_type": recon["circuit_type"],
            "name": ir.get("metadata", {}).get("name", tpl_id) if ir else tpl_id,
            "components": [c["id"] for c in comps],
            "component_values": {c["id"]: {"value": c.get("value"), "unit": c.get("unit", "")} for c in comps if "value" in c},
            "component_types": {c["id"]: c.get("type") for c in comps},
            "nodes": ir.get("nodes", []) if ir else [],
            "connections": connections,
            "ground": ir.get("ground_node", "GND") if ir else "GND",
            "control_relationships": control_rels,
            "source_polarity": source_polarities,
            "analysis_type": ir.get("analysis", {}).get("type", "op") if ir else "op",
            "simulation_parameters": ir.get("analysis", {}) if ir else {},
            "default_simulation_results": recon.get("simulation_results"),
            "canonical_circuit_ir": ir,
        }
        templates[tpl_id] = tpl_record
        with open(os.path.join(CIRCUITS_DIR, f"{tpl_id}.json"), "w", encoding="utf-8") as f:
            json.dump(tpl_record, f, indent=2, ensure_ascii=False)

    # 8 Generalized Circuit Templates (Non-Manual Topologies)
    generalized_specs = [
        ("general_rc", "Simple RC circuit with 12V, 5kΩ and 2µF"),
        ("voltage_divider", "Voltage divider circuit with 10V source, R1 = 2kΩ and R2 = 3kΩ in series"),
        ("series_resistors", "15V source with R1 1kΩ, R2 2kΩ and R3 3kΩ in series"),
        ("parallel_resistors", "12V source with R1 1kΩ, R2 2kΩ and R3 4kΩ in parallel"),
        (
            "shunted_divider_junction",
            "make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages"
        ),
        ("series_rlc", "Series RLC circuit with 10V source, R1 = 100Ω, L1 = 10mH and C1 = 1µF"),
        ("parallel_rlc", "Parallel RLC circuit with 10V source, R1 = 100Ω, L1 = 10mH and C1 = 1µF"),
        (
            "rc_lowpass_filter",
            "10V source with R1 1kΩ and C1 1µF in series, and R2 10kΩ connected across C1"
        ),
    ]

    for tpl_id, prompt in generalized_specs:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        ir = recon["selected_circuit_ir"]
        comps = ir.get("components", []) if ir else []
        connections = []
        source_polarities = []
        for c in comps:
            c_nodes = c.get("nodes", [])
            if len(c_nodes) >= 2:
                n0 = f"N{c_nodes[0]}" if str(c_nodes[0]).isdigit() else str(c_nodes[0])
                n1 = f"N{c_nodes[1]}" if str(c_nodes[1]).isdigit() else str(c_nodes[1])
                connections.append(f"{c['id']} -> {n0},{n1}")
                if c.get("type") in ("dc_voltage_source", "ac_voltage_source", "current_source", "dc_current_source"):
                    source_polarities.append(f"{c['id']}: (+) {n0} to (-) {n1}")
        tpl_record = {
            "template_id": tpl_id,
            "experiment_number": None,
            "topology_category": "GENERALIZED CIRCUIT",
            "circuit_type": recon["circuit_type"],
            "name": ir.get("metadata", {}).get("name", tpl_id) if ir else tpl_id,
            "components": [c["id"] for c in comps],
            "component_values": {c["id"]: {"value": c.get("value"), "unit": c.get("unit", "")} for c in comps if "value" in c},
            "component_types": {c["id"]: c.get("type") for c in comps},
            "nodes": ir.get("nodes", []) if ir else [],
            "connections": connections,
            "ground": ir.get("ground_node", "GND") if ir else "GND",
            "control_relationships": [],
            "source_polarity": source_polarities,
            "analysis_type": ir.get("analysis", {}).get("type", "op") if ir else "op",
            "simulation_parameters": ir.get("analysis", {}) if ir else {},
            "default_simulation_results": recon.get("simulation_results"),
            "canonical_circuit_ir": ir,
        }
        templates[tpl_id] = tpl_record
        with open(os.path.join(CIRCUITS_DIR, f"{tpl_id}.json"), "w", encoding="utf-8") as f:
            json.dump(tpl_record, f, indent=2, ensure_ascii=False)

    return templates


def build_and_save_structured_domain_knowledge() -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Executes Phase 1 & Phase 2:
      1. Reads 'Manual complete.txt' pages.
      2. Merges raw page text with rich structured domain records for all 14 experiments.
      3. Attaches canonical Circuit IR and PySpice/simulation code to every experiment.
      4. Saves updated `knowledge/experiments/exp1..14.json`, `knowledge/viva/exp1..14_viva.json`,
         and `knowledge/circuits/*.json`.
    """
    os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
    os.makedirs(VIVA_DIR, exist_ok=True)
    os.makedirs(CIRCUITS_DIR, exist_ok=True)

    raw_pages: List[str] = []
    if os.path.exists(MANUAL_TXT):
        with open(MANUAL_TXT, "r", encoding="utf-8", errors="ignore") as f:
            raw_pages = [p.strip() for p in f.read().split("\x0c")]

    catalog = get_structured_experiments_catalog()
    templates = build_canonical_circuit_templates()

    exp_to_tpl_key = {
        1: "exp1_resistor_bridge",
        2: "exp2_cccs",
        3: "exp3_vcvs",
        4: "exp4_rc_natural_response",
        5: "exp5_rc_step_response",
        6: "exp6_pacemaker",
        7: "exp7_logic_gates",
        8: "exp8_half_full_adder",
        9: "exp9_boolean_sop_pos",
        10: "exp10_nand_combinational",
        11: "exp11_diode_iv",
        12: "exp12_zener_regulator",
        13: "exp13_half_wave_rectifier",
        14: "exp14_full_wave_rectifier",
    }

    for exp_num, record in catalog.items():
        page_nums = record["pages"]
        raw_text = "\n\n".join(raw_pages[p - 1] for p in page_nums if 0 < p <= len(raw_pages))
        tpl = templates[exp_to_tpl_key[exp_num]]
        ir = tpl["canonical_circuit_ir"]
        code_str = ProgressiveCircuitEngine.generate_pyspice_code(ir) if ir else ""

        diagram_images = [f"Manual complete_page-{p:04d}-compressed.jpg" for p in page_nums]
        record["raw_text"] = raw_text
        record["page_start"] = page_nums[0]
        record["page_end"] = page_nums[-1]
        record["software"] = (
            "PySpice, Python 3.x, Ngspice"
            if exp_num <= 6
            else ("Multisim / SIMLAB Digital Logic Engine" if exp_num <= 10 else "MATLAB Simulink / SIMLAB Numerical Engine")
        )
        record["tags"] = ", ".join(record["important_terminology"])
        record["diagram_images"] = diagram_images
        record["code"] = code_str
        record["code_sample"] = code_str
        record["canonical_circuit_ir"] = ir
        record["circuit_template_id"] = exp_to_tpl_key[exp_num]
        record["viva"] = [
            {
                "q": vc["q"],
                "a": vc["a"],
                "category": vc["category"],
                "key_concepts": record["important_terminology"][:4],
            }
            for vc in record["viva_concepts"]
        ]

        with open(os.path.join(EXPERIMENTS_DIR, f"exp{exp_num}.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        with open(os.path.join(VIVA_DIR, f"exp{exp_num}_viva.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "exp_number": exp_num,
                    "title": record["title"],
                    "questions": record["viva"],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    return catalog, templates


if __name__ == "__main__":
    cat, tpls = build_and_save_structured_domain_knowledge()
    print(f"Structured experiments built: {len(cat)}")
    print(f"Canonical circuit templates built: {len(tpls)}")
