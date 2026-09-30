"""
SIMLAB AI — Domain Adaptation Dataset Generator (Phases 3–16)
Generates rich, diverse, tool-grounded instruction & multi-turn datasets in training/*.jsonl
from the authoritative structured manual knowledge (all 14 experiments of 23EEP20B)
and canonical circuit templates.

Datasets produced:
1. training/experiment_knowledge.jsonl
2. training/natural_language_circuits.jsonl
3. training/topology_reasoning.jsonl
4. training/code_generation.jsonl
5. training/viva.jsonl
6. training/ambiguity.jsonl
7. training/error_diagnosis.jsonl
8. training/regression.jsonl
9. training/simlab_sft_combined.jsonl
"""

import os
import sys
import json
from typing import Dict, List, Any, Tuple

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KNOWLEDGE_DIR = os.path.join(APP_ROOT, "knowledge")
TRAINING_DIR = os.path.join(APP_ROOT, "training")

if os.path.join(APP_ROOT, "packages", "knowledge-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "knowledge-core", "src"))
if os.path.join(APP_ROOT, "packages", "circuit-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "circuit-core", "src"))

from domain_knowledge_builder import get_structured_experiments_catalog, build_canonical_circuit_templates
from progressive_reconstruction import ProgressiveCircuitEngine

SYSTEM_PROMPT = (
    "You are SIMLAB AI, an offline Simulation Lab Copilot for 23EEP20B Simulation Lab. "
    "Always extract component values strictly from the latest user prompt, never reuse values from unrelated experiments, "
    "preserve manual topology defaults when modifying a lab experiment, reconstruct natural-language node topologies accurately, "
    "and ground all circuit values and simulation outputs in deterministic Circuit IR and SPICE/Python solvers."
)


def _format_llama_entry(
    category: str,
    exp_id: Any,
    user_prompt: str,
    assistant_response: str,
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    return {
        "category": category,
        "exp_id": exp_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response},
        ],
        "instruction": user_prompt,
        "output": assistant_response,
        "metadata": metadata or {},
    }


def generate_experiment_knowledge_dataset(catalog: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Phase 3: Comprehensive structured experiment knowledge dataset across all 14 experiments."""
    records: List[Dict[str, Any]] = []
    for num, exp in sorted(catalog.items()):
        title = exp["title"]
        aim = exp["aim"]
        theory = exp["theory"]
        eqs = "\n".join(f"- `{e}`" for e in exp["equations"])
        apparatus = "\n".join(f"- {a}" for a in exp["apparatus_components"])
        proc = exp["procedure"] if isinstance(exp["procedure"], str) else "\n".join(exp["procedure"])
        obs = exp["expected_observations"] if isinstance(exp["expected_observations"], str) else "\n".join(exp["expected_observations"])
        mistakes = "\n".join(f"- {m}" for m in exp["common_mistakes"])
        terms = ", ".join(f"`{t}`" for t in exp["important_terminology"])

        # 1. Full overview
        overview_ans = (
            f"### Experiment {num}: {title}\n\n"
            f"**Aim:** {aim}\n\n"
            f"#### Apparatus / Components\n{apparatus}\n\n"
            f"#### Theory & Governing Equations\n{theory}\n\n{eqs}\n\n"
            f"#### Circuit Topology\n{exp['circuit_topology']}\n\n"
            + "\n".join(f"- `{r}`" for r in exp["component_relationships"])
            + f"\n\n#### Procedure\n{proc}\n\n"
            f"#### Expected Observations\n{obs}\n\n"
            f"**Result:** {exp['result']}"
        )
        for q_variant in [
            f"Explain Experiment {num}: {title} from the simulation lab manual.",
            f"what is exp {num} in simulation lab manual? give aim, theory, circuit connections and expected result",
            f"Give me the complete lab manual summary for Experiment {num} ({title}).",
        ]:
            records.append(_format_llama_entry("experiment_overview", num, q_variant, overview_ans, {"family": exp["family"]}))

        # 2. Theory & Equations focus
        theory_ans = (
            f"### Theory & Equations for Experiment {num} ({title})\n\n"
            f"{theory}\n\n#### Key Equations\n{eqs}\n\n#### Important Terminology\n{terms}"
        )
        for q_variant in [
            f"What is the theory and formula for Experiment {num} ({title})?",
            f"explain the governing equations and theory behind exp {num} {title.lower()}",
        ]:
            records.append(_format_llama_entry("experiment_theory", num, q_variant, theory_ans))

        # 3. Topology & Component connections focus
        topo_ans = (
            f"### Circuit Connections for Experiment {num} ({title})\n\n"
            f"**Topology Description:** {exp['circuit_topology']}\n"
            f"**Simulation Type:** `{exp['simulation_type']}`\n\n"
            f"#### Node-by-Node Connections\n"
            + "\n".join(f"- `{r}`" for r in exp["component_relationships"])
            + f"\n\n#### Default Component Values\n{apparatus}"
        )
        for q_variant in [
            f"How are the components connected in Experiment {num} ({title})?",
            f"give node connections and default component values for exp {num}",
        ]:
            records.append(_format_llama_entry("experiment_topology", num, q_variant, topo_ans))

        # 4. Procedure & Common Mistakes
        proc_ans = (
            f"### Lab Procedure & Common Mistakes — Experiment {num} ({title})\n\n"
            f"#### Step-by-Step Procedure\n{proc}\n\n"
            f"#### Common Student Mistakes to Avoid\n{mistakes}\n\n"
            f"#### Expected Output\n{obs}"
        )
        for q_variant in [
            f"What is the step-by-step procedure and common mistakes to watch out for in Experiment {num}?",
            f"how to perform exp {num} in lab and what are the expected observations?",
        ]:
            records.append(_format_llama_entry("experiment_procedure", num, q_variant, proc_ans))

    return records


def generate_natural_language_circuits_dataset() -> List[Dict[str, Any]]:
    """Phases 4 & 7: Natural-language circuit dataset + Parameter Substitution training across all 14 experiments + generalized topologies."""
    records: List[Dict[str, Any]] = []

    nl_prompts_spec: List[Tuple[Any, str, str]] = [
        # Exp 1 Resistor Bridge variations
        (1, "simulate experiment 1 resistor bridge with 20v source and resistors 4k, 2k, 2k, 4k, and 2k bridge resistor", "bridge_param_sub"),
        (1, "make pyspice code for a wheatstone resistor bridge with 12v supply, r1=1k, r2=2k, r3=3k, r4=4k, r5=5k", "bridge_explicit"),
        (1, "modify experiment 1 by changing Vinput to 15V and R5 to 4k, keep other manual resistors", "bridge_partial_mod"),
        # Exp 2 CCCS variations (including Phase 20 target prompt)
        (2, "can you make pyspice code for a cccs circuit with 24v supply, 10 ohm, 5 ohm, 3 ohm and 8 ohm resistors and a 2a current source", "cccs_param_sub"),
        (2, "cccs circuit with 50V, R1=5 ohm, R2=4 ohm, R3=2 ohm, R4=10 ohm, I1=4A, gain=0.5. find node voltages and control current", "cccs_explicit"),
        (2, "simulate exp 2 cccs using 12v source, resistors 6 ohm, 3 ohm, 2 ohm, 4 ohm and 1.5a current source", "cccs_casual"),
        (2, "i have a current controlled current source circuit with 30v dc, r1 8r, r2 4r, r3 6r, r4 12r and i1 3a", "cccs_shorthand"),
        (2, "make pyspice code for cccs where i1 is 5a, v1 is 40v, and the four resistors are 12, 6, 4, 8 ohms", "cccs_reordered"),
        # Exp 3 VCVS variations
        (3, "vcvs circuit with 20v source, r1 10 ohm, r2 5 ohm, r3 4 ohm, r4 8 ohm, i1 2a and voltage gain 2.5", "vcvs_param_sub"),
        (3, "make pyspice code for experiment 3 vcvs with 15v supply, resistors 4, 2, 8, 6 ohms and 3a source", "vcvs_casual"),
        (3, "simulate voltage controlled voltage source circuit with V1=25V, R1=5, R2=5, R3=10, R4=10, I1=1A, E1 gain=2", "vcvs_explicit"),
        # Exp 4 RC Natural Response
        (4, "Simulate Experiment 4 natural response of RC circuit with 12V, 5kΩ and 2µF and plot capacitor voltage", "rc_nat_partial"),
        (4, "modify experiment 4 rc natural response with V1=20V, R1=5k, R2=16k, R3=120k, R4=30k, C1=1uF", "rc_nat_full"),
        # Exp 5 RC Step Response
        (5, "Simulate Experiment 5 step response of RC circuit with 20V, 50V, 10kΩ and 1µF and plot the capacitor voltage", "rc_step_partial"),
        (5, "make pyspice code for exp 5 rc step response with V1=30V, V2=60V, C1=0.5uF and show capacitor voltage waveform", "rc_step_plot"),
        # Exp 6 Pacemaker Circuit
        (6, "simulate experiment 6 cardiac pacemaker circuit with 5V source, 1k resistor and 100uF capacitor and plot output", "pacemaker_mod"),
        (6, "make pyspice code for pacemaker pulse shaping circuit from experiment 6", "pacemaker_std"),
        # Exp 7–10 Digital Logic Circuits
        (7, "generate python verification code and truth tables for basic logic gates in experiment 7", "logic_gates_std"),
        (8, "simulate half adder and full adder truth tables and boolean equations for experiment 8", "adder_std"),
        (9, "verify sum of products sop and product of sums pos boolean function in experiment 9", "sop_pos_std"),
        (10, "simulate minimum nand gate combinational logic realization for experiment 10", "nand_comb_std"),
        # Exp 11 Diode I-V Characteristics
        (11, "plot pn junction diode i-v characteristics for experiment 11 with 1k series resistor", "diode_iv_param_sub"),
        (11, "simulate forward bias diode curve with 470 ohm resistor sweeping voltage from 0 to 5V", "diode_iv_casual"),
        # Exp 12 Zener Diode Voltage Regulator
        (12, "simulate experiment 12 zener diode voltage regulator with 15v dc source, 470 ohm series resistor and 2.2k load resistor", "zener_param_sub"),
        (12, "put a zener diode across the 1k load resistor with a 330 ohm series resistor connected to a 12v dc source", "zener_nl"),
        # Exp 13 Half-Wave Rectifier
        (13, "half wave rectifier circuit with 24v peak 50hz ac source and 2.2k load resistor. plot output waveform", "hwr_param_sub"),
        (13, "simulate exp 13 half wave rectifier with 15v ac supply and 1k load resistor", "hwr_std"),
        # Exp 14 Full-Wave Bridge Rectifier
        (14, "full wave bridge rectifier with 15v peak 50hz ac supply and 1k load resistor. plot rectified output voltage", "fwr_param_sub"),
        (14, "connect four diodes as a bridge rectifier with 20v ac source and 4.7k resistor across the load", "fwr_nl"),
        # Generalized non-manual circuits & natural-language junction/branch descriptions
        (None, "make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages", "nl_junction_divider"),
        (None, "r1 and r2 in series and r3 connected from their junction to ground", "nl_designator_only"),
        (None, "12v dc source connected to r1 1k and r2 2.2k in series, with r3 4.7k in parallel with r2. find node voltages", "nl_parallel_branch"),
        (None, "voltage divider with 15v supply, r1 3.3k and r2 6.8k in series. calculate output voltage at the middle point", "nl_voltage_divider"),
        (None, "24v source with three resistors 1k, 2k, and 3k in series. calculate loop current and node voltages", "nl_three_series"),
        (None, "10v supply with r1 500 ohm, r2 1k, and r3 2k connected in parallel across the source. find branch currents", "nl_three_parallel"),
        (None, "Simple RC circuit with 12V, 5kΩ and 2µF and plot capacitor voltage", "nl_general_rc"),
        (None, "Series RLC circuit with 10V source, R1 = 100Ω, L1 = 10mH and C1 = 1µF", "nl_series_rlc"),
    ]

    for exp_id, prompt, tag in nl_prompts_spec:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt, experiment_context=exp_id)
        formatted_md = ProgressiveCircuitEngine.format_reconstruction_response(recon, prompt)
        records.append(
            _format_llama_entry(
                "natural_language_circuit",
                exp_id,
                prompt,
                formatted_md,
                {
                    "tag": tag,
                    "circuit_type": recon.get("circuit_type"),
                    "topology_classification": recon.get("topology_classification"),
                    "resolved_graph": recon.get("resolved_graph", []),
                },
            )
        )

    return records


def generate_topology_reasoning_dataset() -> List[Dict[str, Any]]:
    """Phase 5: Topology Reasoning Training (NL -> Explicit Relationships -> Resolved Graph -> Circuit IR)."""
    records: List[Dict[str, Any]] = []

    reasoning_prompts = [
        (
            "r1 and r2 in series and r3 connected from their junction to ground",
            "R1 connects from input node N1 to junction node N2 (`R1: N1 -> N2`). Because R1 and R2 are in series, R2 connects from the shared junction N2 to ground (`R2: N2 -> GND`). R3 connects from the junction of R1 and R2 (node N2) to ground (`R3: N2 -> GND`), placing R3 in parallel with R2.",
        ),
        (
            "make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages",
            "V1 (20V) drives node N1 with respect to GND. R1 (2kΩ) and R2 (1kΩ) form a series path from N1 through junction N2 to GND (`R1: N1 -> N2`, `R2: N2 -> GND`). R3 (3.3kΩ) branches from the junction of R1 and R2 (N2) to GND (`R3: N2 -> GND`). Thus R2 and R3 are in parallel (`R2 || R3 = 767.44 Ω`), and `V(N2) = 20 * 767.44 / (2000 + 767.44) = 5.5462 V`.",
        ),
        (
            "v1 12v connected to r1 1k and r2 2k in series, and r4 4k is parallel with r2",
            "R1 (1kΩ) connects between source node N1 and midpoint N2. R2 (2kΩ) connects between N2 and GND. Since R4 (4kΩ) is in parallel with R2, it shares the exact same node pair `(N2, GND)`.",
        ),
        (
            "15v source with r1 2.2k and r2 4.7k in series, and capacitor c1 10uF is across the load r2",
            "R1 and R2 form a divider with midpoint N2 (`R1: N1 -> N2`, `R2: N2 -> GND`). Placing C1 across the load resistor R2 connects C1 across the same nodes `(N2, GND)`.",
        ),
        (
            "r1 1k and r2 2k in series with the middle point connecting to c1 1uF to ground",
            "The phrase 'middle point' refers to the shared junction node N2 between series elements R1 and R2. C1 therefore connects from N2 to GND.",
        ),
        (
            "connect the four diodes as a bridge across a 12v ac source with a 1k load resistor",
            "A 4-diode full-wave bridge maps AC terminals to the DC rectified load resistor `R1` connected to `GND`.",
        ),
        (
            "connect the resistor r1 1k between the 5v source and diode d1 to ground",
            "Connecting R1 between the source V1 and diode D1 places R1 from source node N1 to intermediate node N2 (`R1: N1 -> N2`), and diode D1 from N2 to GND (`D1: N2 -> GND`).",
        ),
        (
            "put the zener diode across the 2.2k load resistor after a 470 ohm series resistor from a 15v supply",
            "Series current-limiting resistor R1 drops voltage from N1 to regulated node N2. Both load resistor R2 and Zener diode share node pair `(N2, GND)`.",
        ),
    ]

    for prompt, explanation in reasoning_prompts:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        ir = recon.get("selected_circuit_ir") or {}
        clauses = recon.get("user_connection_clauses") or []
        resolved = recon.get("resolved_graph") or []
        ans = (
            f"### Step 1: Extracted User Connection Clauses\n"
            + "\n".join(f"- `{c}`" for c in clauses)
            + f"\n\n### Step 2: Graph Resolution Reasoning\n{explanation}\n\n"
            f"### Step 3: Resolved Node Connections\n"
            + "\n".join(f"- `{r}`" for r in resolved)
            + f"\n\n### Step 4: Canonical Circuit IR\n```json\n{json.dumps(ir, indent=2)}\n```"
        )
        records.append(_format_llama_entry("topology_reasoning", None, prompt, ans, {"resolved_graph": resolved}))

    return records


def generate_code_generation_dataset(catalog: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Phase 6: Code Generation Training (Prompt -> Circuit IR -> Complete Verified Code with requested outputs)."""
    records: List[Dict[str, Any]] = []

    for num, exp in sorted(catalog.items()):
        title = exp["title"]
        recon = ProgressiveCircuitEngine.reconstruct_circuit(f"Simulate Experiment {num}", experiment_context=num)
        code = recon.get("generated_pyspice_code", "")
        prompt = f"Write the complete simulation code for Experiment {num}: {title} with default lab manual values."
        ans = (
            f"### Simulation Code — Experiment {num}: {title}\n\n"
            f"**Topology:** {exp['circuit_topology']} | **Simulation Type:** `{exp['simulation_type']}`\n\n"
            f"#### Component Connections\n"
            + "\n".join(f"- `{r}`" for r in exp["component_relationships"])
            + f"\n\n#### Complete Python / PySpice Code\n```python\n{code}\n```"
        )
        records.append(_format_llama_entry("code_generation_manual", num, prompt, ans))

    code_prompts = [
        "make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages",
        "can you make pyspice code for a cccs circuit with 24v supply, 10 ohm, 5 ohm, 3 ohm and 8 ohm resistors and a 2a current source",
        "Simple RC circuit with 12V, 5kΩ and 2µF and plot the capacitor voltage",
        "generate pyspice code for experiment 3 vcvs with 24V supply, R1=8, R2=4, R3=6, R4=12, I1=3A and gain=2",
        "plot the forward v-i curve of a PN junction diode with a 1k series resistor from 0 to 10V in pyspice",
        "write python code to generate the truth tables for half adder and full adder in experiment 8",
    ]
    for p in code_prompts:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(p)
        code = recon.get("generated_pyspice_code", "")
        req_outputs = recon.get("requested_outputs", {}).get("effective_outputs", [])
        resolved = recon.get("resolved_graph", [])
        ans = (
            f"### Verified Code Generation (`{recon.get('circuit_type')}`)\n\n"
            f"**Requested Outputs Fulfilled:** `{', '.join(req_outputs)}`\n\n"
            f"#### Resolved Connections\n"
            + "\n".join(f"- `{c}`" for c in resolved)
            + f"\n\n```python\n{code}\n```"
        )
        records.append(_format_llama_entry("code_generation_verified", recon.get("selected_experiment"), p, ans, {"requested_outputs": req_outputs}))

    return records


def generate_viva_dataset(catalog: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Phase 9: Student-level Viva Dataset across all 14 experiments (10 categories per experiment + multi-concept)."""
    records: List[Dict[str, Any]] = []

    for num, exp in sorted(catalog.items()):
        title = exp["title"]
        for v in exp["viva_concepts"]:
            q = v["q"]
            a = v["a"]
            vtype = v["category"]

            formatted_ans = (
                f"**Viva Answer (Experiment {num} — {title} | Category: `{vtype}`):**\n\n"
                f"{a}\n\n"
                f"*Key Reference Equation:* `{exp['equations'][0]}`"
            )
            records.append(_format_llama_entry(f"viva_{vtype}", num, q, formatted_ans, {"viva_type": vtype}))

            informal_q = f"in exp {num} ({title.lower()}), {q[0].lower() + q[1:]}"
            records.append(_format_llama_entry(f"viva_{vtype}_contextual", num, informal_q, formatted_ans, {"viva_type": vtype}))

        all_viva_md = f"### Top 10 Viva Questions & Answers — Experiment {num}: {title}\n\n" + "\n\n".join(
            f"**Q{idx+1} ({v['category'].upper()}): {v['q']}**\nA: {v['a']}"
            for idx, v in enumerate(exp["viva_concepts"])
        )
        records.append(
            _format_llama_entry(
                "viva_exam_sheet",
                num,
                f"Give me viva questions and answers for Experiment {num}: {title}.",
                all_viva_md,
            )
        )

    return records


def generate_ambiguity_and_safety_dataset() -> List[Dict[str, Any]]:
    """Phases 8, 12, 13, 14: Partial specification, Ambiguity handling, Manual vs Generalized routing, Negative/Safety training."""
    records: List[Dict[str, Any]] = []

    ambiguity_prompts = [
        "I have a 12V source and two resistors 2k and 4k. Generate the circuit.",
        "Use Experiment 4 with 12V, 5kΩ and 2µF.",
        "Simple RC circuit with 12V, 5kΩ and 2µF",
        "I have a 24V supply and two resistors 3.3k and 6.8k",
    ]
    for p in ambiguity_prompts:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(p)
        md = ProgressiveCircuitEngine.format_reconstruction_response(recon, p)
        records.append(_format_llama_entry("ambiguity_and_safety", recon.get("selected_experiment"), p, md))

    return records


def generate_error_diagnosis_dataset() -> List[Dict[str, Any]]:
    """Phases 10 & 11: Error Diagnosis & Tool-Grounded Troubleshooting Dataset."""
    records: List[Dict[str, Any]] = []

    error_cases = [
        (
            "My PySpice CCCS simulation for Experiment 2 fails with: `Error: unknown controlling source R2 in F1`. How do I fix it?",
            "### Diagnosis: Invalid Controlling Element in SPICE `F` (CCCS) Device\n\n"
            "#### Root Cause\n"
            "In ngspice / PySpice, a Current-Controlled Current Source (`F` element or `circuit.F(...)`) **cannot reference a resistor (`R2`) directly** as its current sensor. SPICE requires the controlling current to be measured through a **voltage source (`V` element)**.\n\n"
            "#### Fix\n"
            "Insert a **0V dummy ammeter voltage source (`Vtest`)** in series with `R2` (between node `2` and `circuit.gnd`), and pass `'Vtest'` as the controlling source to `circuit.F`:\n\n"
            "```python\n"
            "circuit.R(2, 1, 2, 5@u_Ohm)\n"
            "circuit.V('test', 2, circuit.gnd, 0@u_V)  # 0V ammeter in series with R2\n"
            "circuit.F(1, 3, 1, 'Vtest', 0.5)          # F1 controlled by I(Vtest)\n"
            "```",
        ),
        (
            "Why is ngspice giving `singular matrix: check nodes 3 and 4` when I simulate my circuit?",
            "### Diagnosis: Floating Node / Missing DC Path to Ground (`Singular Matrix`)\n\n"
            "#### Root Cause\n"
            "A `singular matrix` error occurs when the Modified Nodal Analysis (MNA) conductance matrix cannot be inverted. Common causes in student labs:\n"
            "1. **Missing `circuit.gnd` (`0` node)**: Every circuit must have at least one connection to `circuit.gnd`.\n"
            "2. **Floating Node**: A node connected only to capacitors in DC analysis or isolated by an open switch with infinite resistance.\n"
            "3. **Voltage Source / Inductor Loop**: Two voltage sources or inductors connected directly in parallel without series resistance (`R_off` or `R_series`).\n\n"
            "#### Fix\n"
            "- Ensure your reference node uses `circuit.gnd`.\n"
            "- When using voltage-controlled switches (`SW`), set a finite `off_resistance=1e9@u_Ohm` (as in Experiments 4–6) so nodes never float completely.",
        ),
        (
            "In Experiment 4 (RC natural response), my capacitor voltage plot is a flat 0V line during the entire transient simulation. Why?",
            "### Diagnosis: Missing Pre-Switching Charging Path or Incorrect Switch Control Pulse\n\n"
            "#### Root Cause\n"
            "In Experiment 4, `S1` must be ON (`Vpulse2 = +1V`) before `switchingtime = 20ms` so `V1` charges `C1` through `R1`, and at `t = 20ms`, `S1` opens and `S2` closes (`Vpulse3 = +1V`) so `C1` discharges through `R2, R3, R4`.",
        ),
        (
            "In Experiment 14 (Full-Wave Bridge Rectifier), why did one of my bridge diodes get shorted when I grounded both the AC source and load resistor?",
            "### Diagnosis: Ground Loop Short-Circuit in Bridge Rectifier\n\n"
            "#### Root Cause\n"
            "In a 4-diode full-wave bridge rectifier, the AC input terminals and the DC load output terminals cannot simultaneously share the same `GND` reference node without shorting out one of the lower bridge diodes. Keep the AC source across the bridge input nodes `(ac_pos, ac_neg)` and ground the negative DC load rail.",
        ),
    ]

    for prompt, ans in error_cases:
        records.append(_format_llama_entry("error_diagnosis", None, prompt, ans))

    return records


def generate_regression_dataset() -> List[Dict[str, Any]]:
    """Phase 16: Permanent Regression Training & Evaluation Dataset."""
    records: List[Dict[str, Any]] = []

    regression_prompts = [
        (
            "reg_01_junction_branch_divider",
            "make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages",
            {
                "expected_connections": ["V1: N1 -> GND", "R1: N1 -> N2", "R2: N2 -> GND", "R3: N2 -> GND"],
                "forbidden_connections": ["R2: N2 -> N3", "R3: N3 -> GND"],
                "expected_v_n2": 5.5462,
            },
        ),
        (
            "reg_02_designator_only_junction",
            "r1 and r2 in series and r3 connected from their junction to ground",
            {
                "expected_connections": ["R1: N1 -> N2", "R2: N2 -> GND", "R3: N2 -> GND"],
                "forbidden_connections": ["R2: N2 -> N3", "R3: N3 -> GND"],
            },
        ),
        (
            "reg_03_cccs_parameter_substitution",
            "can you make pyspice code for a cccs circuit with 24v supply, 10 ohm, 5 ohm, 3 ohm and 8 ohm resistors and a 2a current source",
            {
                "expected_circuit_type": "CCCS",
            },
        ),
        (
            "reg_04_exp4_preserve_manual_defaults",
            "Simulate Experiment 4 with 12V, 5kΩ and 2µF",
            {
                "expected_circuit_type": "RC_NATURAL_RESPONSE",
            },
        ),
        (
            "reg_05_rc_capacitor_plot_fulfillment",
            "Simple RC circuit with 12V, 5kΩ and 2µF and plot the capacitor voltage",
            {
                "expected_circuit_type": "GENERAL_RC",
                "must_contain_code": ["plt.plot", "plt.xlabel", "plt.ylabel"],
            },
        ),
        (
            "reg_06_parallel_branch_nl",
            "12v source with r1 1k and r2 2k in series, and r4 4k is parallel with r2",
            {
                "expected_connections": ["V1: N1 -> GND", "R1: N1 -> N2", "R2: N2 -> GND", "R4: N2 -> GND"],
            },
        ),
        (
            "reg_07_ambiguous_two_resistors",
            "I have a 10V source and two resistors 1k and 2k",
            {
                "expected_is_ambiguous": True,
            },
        ),
    ]

    for reg_id, prompt, expectations in regression_prompts:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        md = ProgressiveCircuitEngine.format_reconstruction_response(recon, prompt)
        records.append(
            _format_llama_entry(
                "regression_fixture",
                recon.get("selected_experiment"),
                prompt,
                md,
                {"regression_id": reg_id, "expectations": expectations, "resolved_graph": recon.get("resolved_graph", [])},
            )
        )

    return records


def write_jsonl(filepath: str, records: List[Dict[str, Any]]) -> int:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def build_all_training_datasets() -> Dict[str, int]:
    os.makedirs(TRAINING_DIR, exist_ok=True)
    catalog = get_structured_experiments_catalog()

    exp_knowledge = generate_experiment_knowledge_dataset(catalog)
    nl_circuits = generate_natural_language_circuits_dataset()
    topo_reasoning = generate_topology_reasoning_dataset()
    code_gen = generate_code_generation_dataset(catalog)
    viva = generate_viva_dataset(catalog)
    ambiguity = generate_ambiguity_and_safety_dataset()
    error_diag = generate_error_diagnosis_dataset()
    regression = generate_regression_dataset()

    counts = {
        "experiment_knowledge.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "experiment_knowledge.jsonl"), exp_knowledge),
        "natural_language_circuits.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "natural_language_circuits.jsonl"), nl_circuits),
        "topology_reasoning.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "topology_reasoning.jsonl"), topo_reasoning),
        "code_generation.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "code_generation.jsonl"), code_gen),
        "viva.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "viva.jsonl"), viva),
        "ambiguity.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "ambiguity.jsonl"), ambiguity),
        "error_diagnosis.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "error_diagnosis.jsonl"), error_diag),
        "regression.jsonl": write_jsonl(os.path.join(TRAINING_DIR, "regression.jsonl"), regression),
    }

    all_records = exp_knowledge + nl_circuits + topo_reasoning + code_gen + viva + ambiguity + error_diag + regression
    counts["simlab_sft_combined.jsonl"] = write_jsonl(os.path.join(TRAINING_DIR, "simlab_sft_combined.jsonl"), all_records)
    return counts


if __name__ == "__main__":
    stats = build_all_training_datasets()
    print(json.dumps(stats, indent=2))
