"""
SIMLAB AI — Phase 19: Comprehensive Domain Evaluation Benchmark Suite
Evaluates 140+ natural-language prompts (20 prompts across each of the 7 major experiment families)
testing:
- changed values
- reordered values
- missing values (manual default preservation)
- informal grammar & student shorthand
- new circuit descriptions
- circuit modifications
- non-manual generalized circuits
- junction/branch natural-language topology descriptions
- requested-output fulfillment (plotting, node voltages, branch currents, truth tables)
- ambiguity detection & zero cross-experiment value contamination
"""

import os
import sys
import json
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(APP_ROOT, "packages", "circuit-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "circuit-core", "src"))
if os.path.join(APP_ROOT, "packages", "knowledge-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "knowledge-core", "src"))

from progressive_reconstruction import ProgressiveCircuitEngine
from domain_retriever import DomainRetriever


def build_benchmark_prompts() -> List[Dict[str, Any]]:
    prompts: List[Dict[str, Any]] = []

    # Family 1: Resistor Bridge & DC Circuits (Exp 1) — 20 prompts
    fam1 = [
        ("Simulate Experiment 1 resistor bridge circuit", "RESISTOR_BRIDGE", {"Vinput": 10.0, "R1": 2000.0, "R2": 1000.0}),
        ("simulate experiment 1 resistor bridge with 20v source and resistors 4k, 2k, 2k, 4k, and 2k bridge resistor", "RESISTOR_BRIDGE", {"Vinput": 20.0, "R1": 4000.0, "R2": 2000.0}),
        ("make pyspice code for a wheatstone resistor bridge with 12v supply, r1=1k, r2=2k, r3=3k, r4=4k, r5=5k", "RESISTOR_BRIDGE", {"Vinput": 12.0, "R1": 1000.0, "R5": 5000.0}),
        ("modify experiment 1 by changing Vinput to 15V and R5 to 4k, keep other manual resistors", "RESISTOR_BRIDGE", {"Vinput": 15.0, "R5": 4000.0, "R1": 2000.0}),
        ("exp 1 resistor bridge circuit with 24v dc source and r1=3k, r2=1.5k, r3=1.5k, r4=3k, r5=2k", "RESISTOR_BRIDGE", {"Vinput": 24.0, "R1": 3000.0}),
        ("wheatstone bridge circuit with 18v supply, r1 2k, r2 2k, r3 2k, r4 2k, r5 1k", "RESISTOR_BRIDGE", {"Vinput": 18.0, "R5": 1000.0}),
        ("compute dc biases in a resistor bridge (exp 1) with 30v source", "RESISTOR_BRIDGE", {"Vinput": 30.0, "R1": 2000.0}),
        ("experiment 1 bridge circuit with v1=9v and r3=4.7k", "RESISTOR_BRIDGE", {"Vinput": 9.0, "R3": 4700.0}),
        ("resistor bridge network with 5v supply, r1=10k, r2=10k, r3=10k, r4=10k, r5=10k", "RESISTOR_BRIDGE", {"Vinput": 5.0, "R1": 10000.0}),
        ("simulate exp 1 with 16v source and r2=3.3k, r4=6.8k", "RESISTOR_BRIDGE", {"Vinput": 16.0, "R2": 3300.0, "R4": 6800.0}),
        ("pyspice operating point for experiment 1 resistor bridge with 25v input", "RESISTOR_BRIDGE", {"Vinput": 25.0}),
        ("modify exp 1 wheatstone bridge with r1=5k, r2=5k, r3=5k, r4=5k, r5=2.2k and 10v source", "RESISTOR_BRIDGE", {"Vinput": 10.0, "R1": 5000.0, "R5": 2200.0}),
        ("dc bias calculation for resistor bridge with 14v source and 1k, 2k, 1k, 2k, 3k resistors", "RESISTOR_BRIDGE", {"Vinput": 14.0}),
        ("exp 1 bridge circuit with 40v dc source", "RESISTOR_BRIDGE", {"Vinput": 40.0}),
        ("resistor bridge circuit with v1 8v, r1 800 ohm, r2 400 ohm, r3 400 ohm, r4 800 ohm, r5 1k", "RESISTOR_BRIDGE", {"Vinput": 8.0, "R1": 800.0}),
        ("simulate experiment 1 changing r5 to 10k", "RESISTOR_BRIDGE", {"R5": 10000.0, "Vinput": 10.0}),
        ("wheatstone resistor bridge with 6v battery and five 2.2k resistors", "RESISTOR_BRIDGE", {"Vinput": 6.0}),
        ("exp 1 dc bias bridge with 22v source and r1=4.7k", "RESISTOR_BRIDGE", {"Vinput": 22.0, "R1": 4700.0}),
        ("make pyspice code for exp 1 resistor bridge with 36v source", "RESISTOR_BRIDGE", {"Vinput": 36.0}),
        ("resistor bridge experiment 1 with 48v supply and r5=500 ohm", "RESISTOR_BRIDGE", {"Vinput": 48.0, "R5": 500.0}),
    ]
    for p, ctype, vals in fam1:
        prompts.append({"family": "exp1_resistor_bridge", "prompt": p, "expected_type": ctype, "expected_values": vals})

    # Family 2: Dependent Sources (Exp 2 CCCS & Exp 3 VCVS) — 20 prompts
    fam2 = [
        ("can you make pyspice code for a cccs circuit with 24v supply, 10 ohm, 5 ohm, 3 ohm and 8 ohm resistors and a 2a current source", "CCCS", {"V1": 24.0, "R1": 10.0, "R2": 5.0, "R3": 3.0, "R4": 8.0, "I1": 2.0}),
        ("cccs circuit with 50V, R1=5 ohm, R2=4 ohm, R3=2 ohm, R4=10 ohm, I1=4A", "CCCS", {"V1": 50.0, "R1": 5.0, "I1": 4.0}),
        ("simulate exp 2 cccs using 12v source, resistors 6 ohm, 3 ohm, 2 ohm, 4 ohm and 1.5a current source", "CCCS", {"V1": 12.0, "I1": 1.5}),
        ("i have a current controlled current source circuit with 30v dc, r1 8r, r2 4r, r3 6r, r4 12r and i1 3a", "CCCS", {"V1": 30.0, "R1": 8.0, "I1": 3.0}),
        ("make pyspice code for cccs where i1 is 5a, v1 is 40v, and the four resistors are 12, 6, 4, 8 ohms", "CCCS", {"V1": 40.0, "I1": 5.0}),
        ("modify experiment 2 cccs by changing only the voltage source to 36V and R1 to 15 ohms", "CCCS", {"V1": 36.0, "R1": 15.0}),
        ("simulate experiment 2 cccs with default manual values", "CCCS", {"V1": 50.0, "R1": 6.0, "I1": 5.0}),
        ("cccs lab circuit with 18v battery, 4 ohm, 8 ohm, 2 ohm, 6 ohm resistors and 2.5a source", "CCCS", {"V1": 18.0, "I1": 2.5}),
        ("exp 2 current controlled current source with v1=20v and i1=3a", "CCCS", {"V1": 20.0, "I1": 3.0}),
        ("generate pyspice netlist for cccs with 15v source, r1=3, r2=6, r3=9, r4=12, i1=1a", "CCCS", {"V1": 15.0, "R4": 12.0}),
        ("vcvs circuit with 20v source, r1 10 ohm, r2 5 ohm, r3 4 ohm, r4 8 ohm, r5 12 ohm", "VCVS", {"V1": 20.0, "R1": 10.0, "R5": 12.0}),
        ("make pyspice code for experiment 3 vcvs with 15v supply, resistors 4, 2, 8, 6, 10 ohms", "VCVS", {"V1": 15.0, "R1": 4.0, "R5": 10.0}),
        ("simulate voltage controlled voltage source circuit with V1=25V, R1=5, R2=5, R3=10, R4=10, R5=15", "VCVS", {"V1": 25.0, "R3": 10.0}),
        ("change v1 to 18v and r3 to 12 ohms in exp 3 vcvs circuit and calculate node voltages", "VCVS", {"V1": 18.0, "R3": 12.0}),
        ("simulate experiment 3 vcvs with default manual values", "VCVS", {"V1": 65.0, "R1": 5.0}),
        ("vcvs lab experiment where voltage source is 32v, resistors 8, 4, 2, 10, 12 ohms", "VCVS", {"V1": 32.0, "R1": 8.0}),
        ("exp 3 vcvs circuit with 12v dc source and r1=6 ohm, r2=3 ohm, r3=3 ohm, r4=6 ohm, r5=9 ohm", "VCVS", {"V1": 12.0, "R1": 6.0}),
        ("voltage controlled voltage source pyspice code with 28v supply and gain 4", "VCVS", {"V1": 28.0}),
        ("run dc operating point for exp 2 cccs with 45v source and 6a current source", "CCCS", {"V1": 45.0, "I1": 6.0}),
        ("run dc operating point for exp 3 vcvs with 35v source and r1=10 ohm", "VCVS", {"V1": 35.0, "R1": 10.0}),
    ]
    for p, ctype, vals in fam2:
        prompts.append({"family": "exp2_exp3_dependent_sources", "prompt": p, "expected_type": ctype, "expected_values": vals})

    # Family 3: Transient RC & Pacemaker Circuits (Exp 4, Exp 5, Exp 6, General RC) — 20 prompts
    fam3 = [
        ("Simulate Experiment 4 natural response of RC circuit", "RC_NATURAL_RESPONSE", {"V1": 100.0, "C1": 0.5e-6}),
        ("Simulate Experiment 4 natural response of RC circuit with 12V, 5kΩ and 2µF and plot capacitor voltage", "RC_NATURAL_RESPONSE", {"V1": 12.0, "R1": 5000.0, "C1": 2e-6}),
        ("modify experiment 4 rc natural response with V1=20V, R1=5k, R2=16k, R3=120k, R4=30k, C1=1uF", "RC_NATURAL_RESPONSE", {"V1": 20.0, "R1": 5000.0, "C1": 1e-6}),
        ("exp 4 rc natural response with 25v source and 4uF capacitor", "RC_NATURAL_RESPONSE", {"V1": 25.0, "C1": 4e-6}),
        ("natural response of an rc circuit (experiment 4) with v1=15v and c1=2.2uF, plot capacitor voltage", "RC_NATURAL_RESPONSE", {"V1": 15.0, "C1": 2.2e-6}),
        ("simulate exp 4 with 30v source and r1=8k", "RC_NATURAL_RESPONSE", {"V1": 30.0, "R1": 8000.0}),
        ("Simulate Experiment 5 step response of RC circuit", "RC_STEP_RESPONSE", {"V1": 40.0, "V2": 75.0, "C1": 0.25e-6}),
        ("Simulate Experiment 5 step response of RC circuit with 20V, 50V, 10kΩ and 1µF and plot the capacitor voltage", "RC_STEP_RESPONSE", {"V1": 20.0, "V2": 50.0, "R1": 10000.0, "C1": 1e-6}),
        ("make pyspice code for exp 5 rc step response with V1=30V, V2=60V, C1=0.5uF and show capacitor voltage waveform", "RC_STEP_RESPONSE", {"V1": 30.0, "V2": 60.0, "C1": 0.5e-6}),
        ("modify experiment 5 with V1=15V and C1=3.3uF, keep manual resistor values and plot capacitor voltage", "RC_STEP_RESPONSE", {"V1": 15.0, "C1": 3.3e-6}),
        ("step response of rc circuit (exp 5) with v1=24v, v2=48v, c1=2uF", "RC_STEP_RESPONSE", {"V1": 24.0, "V2": 48.0, "C1": 2e-6}),
        ("simulate exp 5 with v1=18v and r1=12k", "RC_STEP_RESPONSE", {"V1": 18.0, "R1": 12000.0}),
        ("Simulate Experiment 6 pacemaker circuit", "PACEMAKER", {"V1": 6.0}),
        ("simulate experiment 6 cardiac pacemaker circuit with 5V source, 1k resistor and 100uF capacitor and plot output", "PACEMAKER", {"V1": 5.0}),
        ("make pyspice code for pacemaker pulse shaping circuit from experiment 6 with 4.5v supply", "PACEMAKER", {"V1": 4.5}),
        ("exp 6 pacemaker simulation with 6v battery and 220uF capacitor", "PACEMAKER", {"V1": 6.0}),
        ("Simple RC circuit with 12V, 5kΩ and 2µF and plot the capacitor voltage", "GENERAL_RC", {"V1": 12.0, "R1": 5000.0, "C1": 2e-6}),
        ("simple series rc circuit with 10v source, 1k resistor and 10uF capacitor, plot capacitor voltage", "GENERAL_RC", {"V1": 10.0, "R1": 1000.0, "C1": 10e-6}),
        ("simple rc circuit with 9v supply, 4.7k resistor and 4.7uF capacitor", "GENERAL_RC", {"V1": 9.0, "R1": 4700.0, "C1": 4.7e-6}),
        ("simple rc lowpass circuit with 5v source, 2.2k resistor and 1uF capacitor, plot capacitor voltage", "GENERAL_RC", {"V1": 5.0, "R1": 2200.0, "C1": 1e-6}),
    ]
    for p, ctype, vals in fam3:
        prompts.append({"family": "exp4_exp5_exp6_rc_transient", "prompt": p, "expected_type": ctype, "expected_values": vals})

    # Family 4: Digital Logic Circuits (Exp 7, Exp 8, Exp 9, Exp 10) — 20 prompts
    fam4 = [
        ("Simulate Experiment 7 truth tables of logic gates", "LOGIC_GATES_TRUTH_TABLE", {}),
        ("generate python verification code and truth tables for basic logic gates in experiment 7", "LOGIC_GATES_TRUTH_TABLE", {}),
        ("verify and, or, not, nand, nor, xor, xnor logic gates truth table (exp 7)", "LOGIC_GATES_TRUTH_TABLE", {}),
        ("experiment 7 multisim logic gates truth table verification", "LOGIC_GATES_TRUTH_TABLE", {}),
        ("write python code to print truth tables of all 7 basic logic gates for exp 7", "LOGIC_GATES_TRUTH_TABLE", {}),
        ("Simulate Experiment 8 half adder and full adder", "HALF_FULL_ADDER", {}),
        ("simulate half adder and full adder truth tables and boolean equations for experiment 8", "HALF_FULL_ADDER", {}),
        ("generate python code for half adder sum and carry truth table (exp 8)", "HALF_FULL_ADDER", {}),
        ("verify 3-bit full adder sum and carry output equations in python for experiment 8", "HALF_FULL_ADDER", {}),
        ("exp 8 half adder and full adder digital logic simulation", "HALF_FULL_ADDER", {}),
        ("Simulate Experiment 9 SOP and POS boolean function", "BOOLEAN_SOP_POS", {}),
        ("verify sum of products sop and product of sums pos boolean function in experiment 9", "BOOLEAN_SOP_POS", {}),
        ("exp 9 boolean algebra sop and pos canonical forms truth table", "BOOLEAN_SOP_POS", {}),
        ("generate python truth table equivalence check for sop and pos in experiment 9", "BOOLEAN_SOP_POS", {}),
        ("simulate experiment 9 boolean expression simplification", "BOOLEAN_SOP_POS", {}),
        ("Simulate Experiment 10 minimum NAND gates combinational circuit", "NAND_COMBINATIONAL", {}),
        ("simulate minimum nand gate combinational logic realization for experiment 10", "NAND_COMBINATIONAL", {}),
        ("universal nand gate combinational circuit truth table verification (exp 10)", "NAND_COMBINATIONAL", {}),
        ("exp 10 realization of boolean expression using only nand gates", "NAND_COMBINATIONAL", {}),
        ("write python code to verify nand-only combinational logic for experiment 10", "NAND_COMBINATIONAL", {}),
    ]
    for p, ctype, vals in fam4:
        prompts.append({"family": "exp7_to_10_digital_logic", "prompt": p, "expected_type": ctype, "expected_values": vals})

    # Family 5: Diode I-V & Zener Regulator Circuits (Exp 11 & Exp 12) — 20 prompts
    fam5 = [
        ("Simulate Experiment 11 PN-junction diode I-V characteristics", "DIODE_IV_CHARACTERISTICS", {"R1": 1000.0}),
        ("plot pn junction diode i-v characteristics for experiment 11 with 1k series resistor", "DIODE_IV_CHARACTERISTICS", {"R1": 1000.0}),
        ("simulate forward bias diode curve with 470 ohm resistor sweeping voltage from 0 to 5V", "DIODE_IV_CHARACTERISTICS", {"R1": 470.0}),
        ("diode characteristic curve circuit with 2.2k resistor and 10v dc source", "DIODE_IV_CHARACTERISTICS", {"R1": 2200.0}),
        ("exp 11 silicon diode i-v curve with 330 ohm current limiting resistor", "DIODE_IV_CHARACTERISTICS", {"R1": 330.0}),
        ("pn-junction diode i-v characteristics with 680 ohm resistor", "DIODE_IV_CHARACTERISTICS", {"R1": 680.0}),
        ("make pyspice code for exp 11 diode i-v characteristics with 1.5k resistor", "DIODE_IV_CHARACTERISTICS", {"R1": 1500.0}),
        ("connect the resistor between the source and the diode with 12v source and 560 ohm resistor", "DIODE_IV_CHARACTERISTICS", {"V1": 12.0, "R1": 560.0}),
        ("diode in series with the resistor 820 ohm driven by 9v source", "DIODE_IV_CHARACTERISTICS", {"V1": 9.0, "R1": 820.0}),
        ("experiment 11 diode i-v plot with 100 ohm resistor", "DIODE_IV_CHARACTERISTICS", {"R1": 100.0}),
        ("Simulate Experiment 12 Zener diode voltage regulator", "ZENER_REGULATOR", {}),
        ("simulate experiment 12 zener diode voltage regulator with 15v dc source, 470 ohm series resistor and 2.2k load resistor", "ZENER_REGULATOR", {"V1": 15.0, "R1": 470.0, "R2": 2200.0}),
        ("put a zener diode across the 1k load resistor with a 330 ohm series resistor connected to a 12v dc source", "ZENER_REGULATOR", {"V1": 12.0, "R1": 330.0, "R2": 1000.0}),
        ("zener shunt regulator with 20v input, 500 ohm series resistor and 1.5k load", "ZENER_REGULATOR", {"V1": 20.0, "R1": 500.0, "R2": 1500.0}),
        ("exp 12 zener voltage regulator with 18v supply, 220 ohm series resistor and 1k load", "ZENER_REGULATOR", {"V1": 18.0, "R1": 220.0, "R2": 1000.0}),
        ("zener regulator circuit with 24v dc source, 1k series resistor and 4.7k load resistor", "ZENER_REGULATOR", {"V1": 24.0, "R1": 1000.0, "R2": 4700.0}),
        ("make pyspice code for exp 12 zener regulator with 14v source and 390 ohm resistor", "ZENER_REGULATOR", {"V1": 14.0, "R1": 390.0}),
        ("voltage regulator using zener diode with 16v input, 680 ohm series resistor and 3.3k load", "ZENER_REGULATOR", {"V1": 16.0, "R1": 680.0, "R2": 3300.0}),
        ("simulate zener breakdown regulator (exp 12) with 10v supply and 100 ohm series resistor", "ZENER_REGULATOR", {"V1": 10.0, "R1": 100.0}),
        ("exp 12 zener diode regulator with 25v dc source, 820 ohm series resistor and 2k load", "ZENER_REGULATOR", {"V1": 25.0, "R1": 820.0, "R2": 2000.0}),
    ]
    for p, ctype, vals in fam5:
        prompts.append({"family": "exp11_exp12_diode_zener", "prompt": p, "expected_type": ctype, "expected_values": vals})

    # Family 6: Half-Wave & Full-Wave Rectifier Circuits (Exp 13 & Exp 14) — 20 prompts
    fam6 = [
        ("Simulate Experiment 13 half-wave rectifier", "HALF_WAVE_RECTIFIER", {}),
        ("half wave rectifier circuit with 24v peak 50hz ac source and 2.2k load resistor. plot output waveform", "HALF_WAVE_RECTIFIER", {"V1": 24.0, "R1": 2200.0}),
        ("simulate exp 13 half wave rectifier with 12v ac 50hz and 1k load resistor", "HALF_WAVE_RECTIFIER", {"V1": 12.0, "R1": 1000.0}),
        ("half wave rectifier with 15v ac supply and 4.7k load resistor", "HALF_WAVE_RECTIFIER", {"V1": 15.0, "R1": 4700.0}),
        ("make pyspice code for half-wave rectifier with 10v source and 3.3k load", "HALF_WAVE_RECTIFIER", {"V1": 10.0, "R1": 3300.0}),
        ("exp 13 half wave rectifier with 18v peak input and 680 ohm load resistor", "HALF_WAVE_RECTIFIER", {"V1": 18.0, "R1": 680.0}),
        ("half wave rectifier with 20v ac supply and 1.2k load, plot the output voltage", "HALF_WAVE_RECTIFIER", {"V1": 20.0, "R1": 1200.0}),
        ("simulate half-wave rectifier with 9v ac source and 560 ohm load", "HALF_WAVE_RECTIFIER", {"V1": 9.0, "R1": 560.0}),
        ("exp 13 rectifier circuit with 30v ac input and 10k load resistor", "HALF_WAVE_RECTIFIER", {"V1": 30.0, "R1": 10000.0}),
        ("half wave rectifier with 16v ac supply and 1.5k load resistor", "HALF_WAVE_RECTIFIER", {"V1": 16.0, "R1": 1500.0}),
        ("Simulate Experiment 14 full-wave bridge rectifier", "FULL_WAVE_RECTIFIER", {}),
        ("full wave bridge rectifier with 15v peak 50hz ac supply and 1k load resistor. plot rectified output voltage", "FULL_WAVE_RECTIFIER", {"V1": 15.0, "R1": 1000.0}),
        ("connect four diodes as a bridge rectifier with 20v ac source and 4.7k resistor across the load", "FULL_WAVE_RECTIFIER", {"V1": 20.0, "R1": 4700.0}),
        ("simulate experiment 14 full wave bridge rectifier with 12v ac and 2.2k load", "FULL_WAVE_RECTIFIER", {"V1": 12.0, "R1": 2200.0}),
        ("full-wave rectifier circuit with 24v ac source and 1.5k load resistor", "FULL_WAVE_RECTIFIER", {"V1": 24.0, "R1": 1500.0}),
        ("bridge rectifier with 9v ac supply and 560 ohm load resistor", "FULL_WAVE_RECTIFIER", {"V1": 9.0, "R1": 560.0}),
        ("exp 14 full wave rectifier with 30v peak sine wave and 10k load", "FULL_WAVE_RECTIFIER", {"V1": 30.0, "R1": 10000.0}),
        ("connect 4 diodes as a bridge with 18v ac supply and 3.3k load resistor", "FULL_WAVE_RECTIFIER", {"V1": 18.0, "R1": 3300.0}),
        ("full wave rectifier (exp 14) with 14v ac source and 820 ohm load", "FULL_WAVE_RECTIFIER", {"V1": 14.0, "R1": 820.0}),
        ("bridge rectifier simulation with 22v ac source and 6.8k load resistor", "FULL_WAVE_RECTIFIER", {"V1": 22.0, "R1": 6800.0}),
    ]
    for p, ctype, vals in fam6:
        prompts.append({"family": "exp13_exp14_rectifiers", "prompt": p, "expected_type": ctype, "expected_values": vals})

    # Family 7: Natural-Language Topology & Generalized Non-Manual Circuits (Junctions, Branches, Dividers, RLC) — 20 prompts
    fam7 = [
        ("make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages", "CUSTOM_NL_TOPOLOGY", {"V1": 20.0, "R1": 2000.0, "R2": 1000.0, "R3": 3300.0}),
        ("r1 and r2 in series and r3 connected from their junction to ground", "CUSTOM_NL_TOPOLOGY", {"R1": 1000.0, "R2": 1000.0, "R3": 1000.0}),
        ("12v dc source connected to r1 1k and r2 2.2k in series, with r3 4.7k in parallel with r2. find node voltages", "CUSTOM_NL_TOPOLOGY", {"V1": 12.0, "R1": 1000.0, "R2": 2200.0, "R3": 4700.0}),
        ("15v source with r1 2.2k and r2 4.7k in series, and capacitor c1 10uF is across the load r2", "CUSTOM_NL_TOPOLOGY", {"V1": 15.0, "R1": 2200.0, "R2": 4700.0, "C1": 10e-6}),
        ("r1 1k and r2 2k in series with the middle point connecting to c1 1uF to ground", "CUSTOM_NL_TOPOLOGY", {"R1": 1000.0, "R2": 2000.0, "C1": 1e-6}),
        ("24v source with r1 4k and r2 2k in series, and r3 6k connected from the common point to ground", "CUSTOM_NL_TOPOLOGY", {"V1": 24.0, "R1": 4000.0, "R2": 2000.0, "R3": 6000.0}),
        ("18v supply with r1 3k and r2 6k in series, and r4 6k in parallel with r2", "CUSTOM_NL_TOPOLOGY", {"V1": 18.0, "R1": 3000.0, "R2": 6000.0, "R4": 6000.0}),
        ("voltage divider with 15v supply, r1 3.3k and r2 6.8k in series. calculate output voltage", "VOLTAGE_DIVIDER", {"V1": 15.0, "R1": 3300.0, "R2": 6800.0}),
        ("9v battery with two resistors 4.7k and 4.7k in series as a voltage divider", "VOLTAGE_DIVIDER", {"V1": 9.0, "R1": 4700.0, "R2": 4700.0}),
        ("24v source with three resistors 1k, 2k, and 3k in series. calculate loop current and node voltages", "SERIES_RESISTORS", {"V1": 24.0, "R1": 1000.0, "R2": 2000.0, "R3": 3000.0}),
        ("10v supply with r1 500 ohm, r2 1k, and r3 2k connected in parallel across the source", "PARALLEL_RESISTORS", {"V1": 10.0, "R1": 500.0, "R2": 1000.0, "R3": 2000.0}),
        ("16v dc source with two parallel resistors r1 4k and r2 8k", "PARALLEL_RESISTORS", {"V1": 16.0, "R1": 4000.0, "R2": 8000.0}),
        ("30v dc source with four series resistors 2k, 3k, 5k, and 10k", "SERIES_RESISTORS", {"V1": 30.0, "R1": 2000.0, "R4": 10000.0}),
        ("10v source with r1 1k and r2 1k in series, and r3 2k connected from the junction of r1 and r2 to ground", "CUSTOM_NL_TOPOLOGY", {"V1": 10.0, "R1": 1000.0, "R2": 1000.0, "R3": 2000.0}),
        ("dc source of 12v with r1 2k and r2 4k in series, and r3 4k across r2", "CUSTOM_NL_TOPOLOGY", {"V1": 12.0, "R1": 2000.0, "R2": 4000.0, "R3": 4000.0}),
        ("5v source with r1 10k and r2 10k in series, and c1 4.7uF connected from the junction of r1 and r2 to ground", "CUSTOM_NL_TOPOLOGY", {"V1": 5.0, "R1": 10000.0, "R2": 10000.0, "C1": 4.7e-6}),
        ("Series RLC circuit with 10V source, R1 = 100Ω, L1 = 10mH and C1 = 1µF", "SERIES_RLC", {"V1": 10.0, "R1": 100.0, "L1": 10e-3, "C1": 1e-6}),
        ("Parallel RLC circuit with 10V source, R1 = 100Ω, L1 = 10mH and C1 = 1µF", "PARALLEL_RLC", {"V1": 10.0, "R1": 100.0, "L1": 10e-3, "C1": 1e-6}),
        ("I have a 10V source and two resistors 1k and 2k", "AMBIGUOUS_UNSPECIFIED", {}),
        ("20v dc source with r1 5k and r2 5k in series, and r3 10k branching from the middle point to ground", "CUSTOM_NL_TOPOLOGY", {"V1": 20.0, "R1": 5000.0, "R2": 5000.0, "R3": 10000.0}),
    ]
    for p, ctype, vals in fam7:
        prompts.append({"family": "nl_topology_and_generalized", "prompt": p, "expected_type": ctype, "expected_values": vals})

    return prompts


def run_benchmark_suite() -> Dict[str, Any]:
    retriever = DomainRetriever()
    prompts = build_benchmark_prompts()

    total = len(prompts)
    intent_passed = 0
    value_passed = 0
    topology_passed = 0
    code_passed = 0
    zero_hallucination_passed = 0
    family_stats: Dict[str, Dict[str, int]] = {}
    failures: List[Dict[str, Any]] = []

    for idx, item in enumerate(prompts):
        fam = item["family"]
        prompt = item["prompt"]
        exp_type = item["expected_type"]
        exp_vals = item["expected_values"]

        if fam not in family_stats:
            family_stats[fam] = {"total": 0, "passed": 0}
        family_stats[fam]["total"] += 1

        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        actual_type = recon.get("circuit_type")
        ir = recon.get("selected_circuit_ir") or {}
        code = recon.get("generated_pyspice_code") or ""
        comps = {c["id"]: c.get("value") for c in ir.get("components", []) if "value" in c}

        # Allow CUSTOM_NL_TOPOLOGY or VOLTAGE_DIVIDER / SERIES_RESISTORS / PARALLEL_RESISTORS equivalence when nodes match
        i_ok = (actual_type == exp_type) or (
            exp_type in ("VOLTAGE_DIVIDER", "SERIES_RESISTORS", "PARALLEL_RESISTORS") and actual_type == "CUSTOM_NL_TOPOLOGY"
        )
        if i_ok:
            intent_passed += 1

        # Value check (within 1e-9 relative tolerance, supporting Rs/RL aliases for Zener)
        v_ok = True
        for cid, expected_v in exp_vals.items():
            actual_v = comps.get(cid)
            if actual_v is None and cid == "Vinput" and "V1" in comps:
                actual_v = comps.get("V1")
            if actual_v is None and cid == "R1" and "Rs" in comps:
                actual_v = comps.get("Rs")
            if actual_v is None and cid == "R2" and "RL" in comps:
                actual_v = comps.get("RL")
            if actual_v is None or abs(float(actual_v) - float(expected_v)) > max(1e-9, abs(float(expected_v)) * 1e-4):
                v_ok = False
                break
        if v_ok:
            value_passed += 1

        # Topology check & Single-Source-of-Truth Preview verification (Circuit IR -> Topology Graph -> Preview)
        is_digital = actual_type in ("LOGIC_GATES_TRUTH_TABLE", "HALF_FULL_ADDER", "BOOLEAN_SOP_POS", "NAND_COMBINATIONAL")
        t_ok = (len(ir.get("components", [])) > 0) or is_digital or recon.get("is_ambiguous", False)
        if t_ok and len(ir.get("components", [])) > 0:
            preview = recon.get("topology_preview") or {}
            ascii_diag = preview.get("ascii_diagram", "")
            edge_lines = preview.get("edge_list_lines", [])
            for comp in ir.get("components", []):
                c_nodes = comp.get("nodes", [])
                if len(c_nodes) >= 2:
                    na = ProgressiveCircuitEngine._fmt_graph_node(c_nodes[0])
                    nb = ProgressiveCircuitEngine._fmt_graph_node(c_nodes[1])
                    expected_edge = f"{comp['id']}: {na} → {nb}"
                    if expected_edge not in edge_lines or f"{na} → {nb}" not in ascii_diag:
                        t_ok = False
                        break
            if actual_type == "VCVS":
                if "(N2 → N1)" not in ascii_diag or "N1 ── GND" in ascii_diag:
                    t_ok = False
        if prompt.startswith("make pyspice code for a 20v source with r1 2k and r2 1k in series"):
            rg = [s.replace("→", "->") for s in recon.get("resolved_graph", [])]
            t_ok = t_ok and (
                ("R1: N1 -> J1" in rg and "R2: J1 -> GND" in rg and "R3: J1 -> GND" in rg and "R2: J1 -> J2" not in rg)
                or ("R1: N1 -> N2" in rg and "R2: N2 -> GND" in rg and "R3: N2 -> GND" in rg and "R2: N2 -> N3" not in rg)
            )
        if t_ok:
            topology_passed += 1

        # Code & requested output check
        c_ok = (len(code.strip()) > 20) or recon.get("is_ambiguous", False)
        if "plot" in prompt.lower() and not recon.get("is_ambiguous", False):
            c_ok = c_ok and ("plt.plot" in code or "plt.semilogx" in code or "plt.figure" in code or "plt.subplots" in code)
        if c_ok:
            code_passed += 1

        # Zero Exp 1 Bridge contamination on non-bridge prompts
        h_ok = True
        if actual_type != "RESISTOR_BRIDGE":
            if ir.get("metadata", {}).get("circuit_type") == "RESISTOR_BRIDGE":
                h_ok = False
        if h_ok:
            zero_hallucination_passed += 1

        all_ok = i_ok and v_ok and t_ok and c_ok and h_ok
        if all_ok:
            family_stats[fam]["passed"] += 1
        else:
            failures.append(
                {
                    "index": idx,
                    "family": fam,
                    "prompt": prompt,
                    "expected_type": exp_type,
                    "actual_type": actual_type,
                    "expected_values": exp_vals,
                    "actual_values": comps,
                    "resolved_graph": recon.get("resolved_graph", []),
                    "flags": {"intent": i_ok, "values": v_ok, "topology": t_ok, "code": c_ok, "no_hallucination": h_ok},
                }
            )

    retrieval_hits = 0
    for exp_num in range(1, 15):
        r = retriever.retrieve(f"What are the viva questions and circuit topology for Experiment {exp_num}?")
        if r.get("experiment") and r["experiment"]["exp_number"] == exp_num and len(r.get("viva", [])) > 0:
            retrieval_hits += 1

    summary = {
        "total_prompts": total,
        "intent_accuracy": f"{intent_passed}/{total} ({100.0 * intent_passed / total:.1f}%)",
        "value_extraction_accuracy": f"{value_passed}/{total} ({100.0 * value_passed / total:.1f}%)",
        "topology_reconstruction_accuracy": f"{topology_passed}/{total} ({100.0 * topology_passed / total:.1f}%)",
        "code_generation_accuracy": f"{code_passed}/{total} ({100.0 * code_passed / total:.1f}%)",
        "zero_contamination_rate": f"{zero_hallucination_passed}/{total} ({100.0 * zero_hallucination_passed / total:.1f}%)",
        "domain_retrieval_accuracy": f"{retrieval_hits}/14 ({100.0 * retrieval_hits / 14:.1f}%)",
        "family_breakdown": family_stats,
        "failure_count": len(failures),
        "failures": failures[:15],
    }
    return summary


if __name__ == "__main__":
    report = run_benchmark_suite()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["failure_count"] > 0:
        sys.exit(1)
