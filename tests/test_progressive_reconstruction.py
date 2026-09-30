"""
Automated Verification Suite for SIMLAB AI 8-Stage Deterministic Circuit Pipeline
Verifies:
1. Strict single-turn entity extraction (no R6-R21 invention, no cross-turn leakage)
2. Exact CCCS extraction and Experiment 2 routing
3. Pre-retrieval classification across all 14 syllabus experiments
4. Non-defaulting rule: never defaults to Experiment 1 when topology is unspecified
5. Topology source accuracy ('manual_template' vs 'ai_inferred')
6. User confirmation accuracy ('user_confirmed: false' unless confirmed)
7. Separate lifecycle flags (TOPOLOGY_RECONSTRUCTED, TOPOLOGY_VALIDATED, SIMULATION_EXECUTED, SIMULATION_SUCCESSFUL)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "circuit-core", "src"))
from progressive_reconstruction import ProgressiveCircuitEngine


class TestDeterministicCircuitPipeline(unittest.TestCase):

    def test_01_exact_cccs_extraction_and_routing(self):
        prompt = "CCCS circuit with 24V source, 10Ω, 5Ω, 3Ω, 8Ω resistors and 2A current source"
        entities = ProgressiveCircuitEngine.extract_entities(prompt)

        expected = {
            "circuit_type": "CCCS",
            "voltage_sources": [{"value": 24, "unit": "V", "user_supplied": True, "id": "V1"}],
            "resistors": [
                {"value": 10, "unit": "ohm", "user_supplied": True, "id": "R1"},
                {"value": 5, "unit": "ohm", "user_supplied": True, "id": "R2"},
                {"value": 3, "unit": "ohm", "user_supplied": True, "id": "R3"},
                {"value": 8, "unit": "ohm", "user_supplied": True, "id": "R4"},
            ],
            "current_sources": [{"value": 2, "unit": "A", "user_supplied": True, "id": "I1"}],
        }
        self.assertEqual(entities, expected)

        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        self.assertEqual(recon["circuit_type"], "CCCS")
        self.assertEqual(recon["selected_experiment"], 2)
        self.assertEqual(recon["topology_source"], "manual_template")
        self.assertFalse(recon["user_confirmed"])

        # Ensure no R5-R21 invented
        ir_comps = recon["selected_circuit_ir"]["components"]
        r_ids = [c["id"] for c in ir_comps if c["type"] == "resistor"]
        self.assertEqual(r_ids, ["R1", "R2", "R3", "R4"])

        # Verify lifecycle flags
        lf = recon["lifecycle"]
        self.assertTrue(lf["TOPOLOGY_RECONSTRUCTED"])
        self.assertTrue(lf["TOPOLOGY_VALIDATED"])
        self.assertTrue(lf["SIMULATION_EXECUTED"])
        self.assertTrue(lf["SIMULATION_SUCCESSFUL"])

    def test_02_all_14_experiments_routing(self):
        cases = [
            ("resistor bridge circuit with 10V", 1, "RESISTOR_BRIDGE"),
            ("CCCS circuit with 24V source", 2, "CCCS"),
            ("current controlled current source circuit", 2, "CCCS"),
            ("VCVS circuit with 65V source", 3, "VCVS"),
            ("voltage controlled voltage source circuit", 3, "VCVS"),
            ("natural response RC circuit", 4, "RC_NATURAL_RESPONSE"),
            ("step response RC circuit", 5, "RC_STEP_RESPONSE"),
            ("pacemaker circuit with 70 BPM", 6, "PACEMAKER"),
            ("logic gate truth table verification", 7, "LOGIC_GATES_TRUTH_TABLE"),
            ("half adder and full adder circuit", 8, "HALF_FULL_ADDER"),
            ("Boolean function in SOP and POS form", 9, "BOOLEAN_SOP_POS"),
            ("combinational circuit using NAND gates", 10, "NAND_COMBINATIONAL"),
            ("diode I-V characteristics", 11, "DIODE_IV_CHARACTERISTICS"),
            ("Zener regulator circuit", 12, "ZENER_REGULATOR"),
            ("half-wave rectifier circuit", 13, "HALF_WAVE_RECTIFIER"),
            ("full-wave rectifier circuit", 14, "FULL_WAVE_RECTIFIER"),
        ]
        for prompt, expected_exp, expected_type in cases:
            recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
            self.assertEqual(
                recon["selected_experiment"],
                expected_exp,
                f"Failed routing for '{prompt}': got Exp {recon['selected_experiment']}, expected Exp {expected_exp}"
            )
            self.assertEqual(recon["circuit_type"], expected_type)
            self.assertEqual(recon["topology_source"], "manual_template")
            self.assertFalse(recon["user_confirmed"])

    def test_03_never_defaults_to_exp1_on_unspecified_resistors(self):
        prompt = "I have a 12V source and resistors 10Ω, 20Ω, 30Ω. Generate PySpice code."
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        self.assertIsNone(recon["selected_experiment"])
        self.assertTrue(recon["is_ambiguous"])
        self.assertEqual(recon["circuit_type"], "AMBIGUOUS_UNSPECIFIED")
        self.assertIsNone(recon["selected_circuit_ir"])
        self.assertFalse(recon["lifecycle"]["TOPOLOGY_RECONSTRUCTED"])
        self.assertFalse(recon["lifecycle"]["SIMULATION_EXECUTED"])
        self.assertFalse(recon["lifecycle"]["SIMULATION_SUCCESSFUL"])

    def test_04_candidate_confirmation_workflow(self):
        prev_user = "I have a 15V source and three resistors: 10Ω, 20Ω, 30Ω"
        latest_user = "Confirm Candidate A"
        recon = ProgressiveCircuitEngine.reconstruct_circuit(latest_user, previous_user_message=prev_user)
        self.assertFalse(recon["is_ambiguous"])
        self.assertTrue(recon["user_confirmed"])
        self.assertEqual(recon["topology_source"], "ai_inferred")
        self.assertIsNone(recon["selected_experiment"])
        ir_resistors = [c["value"] for c in recon["selected_circuit_ir"]["components"] if c["type"] == "resistor"]
        self.assertEqual(ir_resistors, [10.0, 20.0, 30.0])
        self.assertTrue(recon["lifecycle"]["SIMULATION_SUCCESSFUL"])

    def test_05_exp3_vcvs_topology_preview_single_source_of_truth(self):
        """
        Regression test for Experiment 3 VCVS topology preview:
        Ensures Circuit IR -> Topology Graph -> Preview is a single source of truth.
        Specifically, V1 is N2 -> N1 and must NEVER be rendered as (N1 -- GND) in the ASCII preview.
        """
        prompt = "Simulate the Experiment 3 VCVS circuit with a 25V source"
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        self.assertEqual(recon["circuit_type"], "VCVS")
        self.assertEqual(recon["selected_experiment"], 3)

        ir = recon["selected_circuit_ir"]
        self.assertIsNotNone(ir)
        comps = {c["id"]: c for c in ir["components"]}
        self.assertEqual(comps["V1"]["nodes"], ["2", "1"])
        self.assertEqual(comps["R1"]["nodes"], ["3", "GND"])
        self.assertEqual(comps["R2"]["nodes"], ["1", "GND"])
        self.assertEqual(comps["R3"]["nodes"], ["2", "3"])
        self.assertEqual(comps["R4"]["nodes"], ["3", "4"])
        self.assertEqual(comps["R5"]["nodes"], ["5", "GND"])
        self.assertEqual(comps["E1"]["nodes"], ["4", "5"])
        self.assertEqual(comps["E1"]["control_nodes"], ["2", "3"])

        preview = recon["topology_preview"]
        ascii_diag = preview["ascii_diagram"]
        formatted = preview["formatted_preview"]
        edge_lines = preview["edge_list_lines"]

        # V1 must be rendered as N2 -> N1 in both ASCII diagram and edge list, never N1 -- GND
        self.assertIn("[V1 = 25 V] (N2 → N1)", ascii_diag)
        self.assertNotIn("N1 ── GND", ascii_diag)
        self.assertNotIn("[V1 = 25 V] (N1", ascii_diag)

        expected_edges = [
            "V1: N2 → N1",
            "R1: N3 → GND",
            "R2: N1 → GND",
            "R3: N2 → N3",
            "R4: N3 → N4",
            "R5: N5 → GND",
            "E1: N4 → N5",
        ]
        self.assertEqual(edge_lines, expected_edges)
        for edge_str in expected_edges:
            self.assertIn(edge_str, formatted)
            cid, nodes_part = edge_str.split(": ")
            self.assertIn(nodes_part, ascii_diag, f"Component {cid} connection '{nodes_part}' missing from ASCII diagram")

    def test_06_exp6_pacemaker_simulation_verification_and_provenance(self):
        """
        Regression test for Experiment 6 Pacemaker simulation verification, unit validation,
        step/stop consistency, and lifecycle separation:
        - Vs=5V, C=22uF, H=80BPM -> R1 ≈ 29.919 kΩ, T = 0.75 s, tau ≈ 0.6582 s, 5 cycles = 3.75 s
        - Unit validation: never generates @u_s (e.g. 3.75@u_s or 60@u_s) for seconds; validates every time quantity
        - Step/Stop consistency: 1 ms is never silently used for a 60 us simulation; step_time <= end_time verified
        - Lifecycle separation: numerically successful 60 us diagnostic window is NOT reported as full task completion
        - Preserves EXPECTED / THEORETICAL, CALCULATED, SIMULATED, USER OBSERVED provenance separation
        """
        # 1. Direct unit validator checks: 3.75@u_s != 3.75 seconds, 60@u_s != 60 seconds
        check_375_bad = ProgressiveCircuitEngine.validate_time_quantity("3.75@u_s", "3.75 seconds")
        self.assertFalse(check_375_bad["is_valid"])
        self.assertEqual(check_375_bad["corrected_expr"], "3.75@u_time_s")

        check_60_bad = ProgressiveCircuitEngine.validate_time_quantity("60@u_s", "60 seconds")
        self.assertFalse(check_60_bad["is_valid"])
        self.assertEqual(check_60_bad["corrected_expr"], "60@u_time_s")

        check_375_ok = ProgressiveCircuitEngine.validate_time_quantity("3.75@u_time_s", "3.75 seconds")
        self.assertTrue(check_375_ok["is_valid"])
        self.assertAlmostEqual(check_375_ok["code_seconds"], 3.75, places=6)

        # 2. Reconstruct 80 BPM pacemaker prompt
        prompt = "Pacemaker circuit with Vs=5V, C=22uF, H=80BPM"
        recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
        md = ProgressiveCircuitEngine.format_reconstruction_response(recon, prompt)
        code = recon["generated_pyspice_code"]

        self.assertEqual(recon["circuit_type"], "PACEMAKER")
        self.assertEqual(recon["selected_experiment"], 6)

        # Never emit ambiguous @u_s token anywhere in generated PySpice code
        self.assertNotIn("3.75@u_s", code)
        self.assertNotIn("60@u_s", code)
        self.assertNotIn("@u_s", code)
        self.assertIn("u_time_s = UnitValueShorcut(U_s)", code)
        self.assertIn("end_time = 3.75@u_time_s", code)
        self.assertIn("step_time = 1@u_ms", code)

        ir = recon["selected_circuit_ir"]
        comps = {c["id"]: c for c in ir["components"]}
        self.assertAlmostEqual(comps["V1"]["value"], 5.0, places=4)
        self.assertAlmostEqual(comps["C1"]["value"], 22e-6, places=9)
        self.assertAlmostEqual(comps["R1"]["value"], 29919.15, places=1)

        # Target period T = 60 / 80 = 0.75 s, 5 cycles = 3.75 s, RC tau ≈ 0.6582 s
        params_meta = ir["metadata"]["parameters"]
        self.assertAlmostEqual(params_meta["target_period_s"], 0.75, places=4)
        self.assertAlmostEqual(params_meta["recommended_5_cycle_duration_s"], 3.75, places=4)
        self.assertAlmostEqual(params_meta["rc_tau_s"], 0.658223, places=4)

        # Step/stop consistency check: 1 ms was NOT silently used for 60 us simulation; corrected to 1@u_us <= 60@u_us
        analysis_ir = ir["analysis"]
        self.assertGreater(analysis_ir["step"], 0.0)
        self.assertGreater(analysis_ir["stop"], 0.0)
        self.assertLessEqual(analysis_ir["step"], analysis_ir["stop"])
        self.assertEqual(analysis_ir["step_code_expr"], "1@u_us")
        self.assertEqual(analysis_ir["stop_code_expr"], "60@u_us")
        self.assertEqual(analysis_ir["recommended_step_code_expr"], "1@u_ms")
        self.assertEqual(analysis_ir["recommended_stop_code_expr"], "3.75@u_time_s")
        self.assertTrue(analysis_ir["step_stop_consistency"]["was_adjusted"])

        sim = recon["simulation_results"]
        self.assertFalse(sim["window_sufficient"])
        self.assertFalse(sim["threshold_reached"])
        self.assertEqual(sim["pulses_observed"], 0)
        self.assertTrue(sim["unit_mismatch_detected"])
        self.assertEqual(
            sim["simulation_warning"],
            "Simulation window is insufficient to observe the requested behavior."
        )
        self.assertIn("Simulation window is insufficient to observe the requested behavior.", md)

        # Lifecycle separation check: numerically successful simulation with insufficient window != TASK_COMPLETED
        lf = recon["lifecycle"]
        self.assertTrue(lf["SIMULATION_EXECUTED"])
        self.assertTrue(lf["SIMULATION_NUMERICALLY_SUCCESSFUL"])
        self.assertFalse(lf["WINDOW_SUFFICIENT"])
        self.assertFalse(lf["REQUESTED_BEHAVIOR_OBSERVED"])
        self.assertTrue(lf["REQUESTED_OUTPUTS_FULFILLED"])
        self.assertEqual(lf["TASK_COMPLETION_STATUS"], "INCOMPLETE_INSUFFICIENT_SIMULATION_WINDOW")
        self.assertFalse(lf["TASK_COMPLETED"])

        # Simulated capacitor and output voltages in 60 us must NOT be 3.4 V
        nv = sim["node_voltages"]
        sim_cap_v = [v for k, v in nv.items() if k.startswith("control")][0]
        sim_out_v = [v for k, v in nv.items() if k.startswith("out")][0]
        self.assertLess(sim_cap_v, 0.001)  # ~0.000456 V in 60 us, NOT 3.4 V
        self.assertAlmostEqual(sim_out_v, 0.0, places=5)  # 0 V in 60 us, NOT 3.4 V

        # Provenance separation check (must not regress)
        prov = sim["provenance"]
        self.assertIn("EXPECTED_THEORETICAL", prov)
        self.assertIn("CALCULATED", prov)
        self.assertIn("SIMULATED", prov)
        self.assertIn("USER_OBSERVED", prov)
        for header in ("EXPECTED / THEORETICAL", "CALCULATED", "SIMULATED", "USER OBSERVED"):
            self.assertIn(header, md)

        # Branch current must NOT be claimed as numerically extracted; must be labeled as calculated load current
        self.assertEqual(sim["branch_currents"], {})
        self.assertTrue(len(sim["calculated_load_currents"]) > 0)
        self.assertIn("calculated_load_current", recon["requested_outputs"]["effective_outputs"])
        self.assertNotIn("branch_current", recon["requested_outputs"]["effective_outputs"])

        # 3. Verify that when a 5-cycle 3.75 seconds window is explicitly requested, all 5 cycles are observed and TASK_COMPLETED=True
        prompt_5cycles = "Pacemaker circuit with Vs=5V, C=22uF, H=80BPM, end_time=3.75s, step_time=1ms"
        recon_5c = ProgressiveCircuitEngine.reconstruct_circuit(prompt_5cycles)
        lf_5c = recon_5c["lifecycle"]
        sim_5c = recon_5c["simulation_results"]
        self.assertTrue(lf_5c["SIMULATION_EXECUTED"])
        self.assertTrue(lf_5c["SIMULATION_NUMERICALLY_SUCCESSFUL"])
        self.assertTrue(lf_5c["WINDOW_SUFFICIENT"])
        self.assertTrue(lf_5c["REQUESTED_BEHAVIOR_OBSERVED"])
        self.assertTrue(lf_5c["REQUESTED_OUTPUTS_FULFILLED"])
        self.assertEqual(lf_5c["TASK_COMPLETION_STATUS"], "COMPLETED")
        self.assertTrue(lf_5c["TASK_COMPLETED"])
        self.assertGreaterEqual(sim_5c["pulses_observed"], 4)

    def test_07_nl_persistent_junction_resolution(self):
        """
        Regression test for natural-language topology parser persistent junction node (J1) & zero clause loss:
        Verifies that when a junction is introduced, it is assigned internal node ID 'J1' and
        all subsequent references ('the junction', 'that junction', 'the same junction',
        'their junction', 'middle point', 'middle node', 'node between R1 and R2', 'same node',
        'that node', 'this node') resolve to that SAME node J1, producing:
            V1: N1 -> GND
            R1: N1 -> J1
            R2: J1 -> GND
            R3: J1 -> GND
        Explicitly rejects the old buggy parse 'R1 connects from junction(R1,R2) to GND'.
        """
        required_graph = [
            "V1: N1 -> GND",
            "R1: N1 -> J1",
            "R2: J1 -> GND",
            "R3: J1 -> GND",
        ]

        prompts = [
            # Bug report prompt with explicit values (single line)
            "R1 is 4k from the source to a junction, R2 is 2k from that junction to ground, and R3 is 6k also from the same junction to ground.",
            # Bug report prompt with line wrap inside clause ("from that junction to\nground")
            "R1 is 4k from the source to a junction, R2 is 2k from that junction to\nground, and R3 is 6k also from the same junction to ground.",
            # Regression case 1
            "R1 from source to a junction, R2 from that junction to ground, R3 also from the same junction to ground",
            # Regression case 2
            "R1 and R2 are series, R3 from their junction to ground",
            # Regression case 3
            "R1 and R2 meet at the middle node, R3 also connects to that node",
            # Additional supported reference variations ("the junction", "middle point", "node between R1 and R2", "same node", "this node")
            "R1 from the source to the middle point, R2 from the node between R1 and R2 to ground, and R3 from this node to ground",
        ]

        for idx, prompt in enumerate(prompts):
            recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
            md = ProgressiveCircuitEngine.format_reconstruction_response(recon, prompt)
            self.assertFalse(recon["is_ambiguous"], f"Prompt #{idx+1} should not be ambiguous: {prompt}")
            self.assertEqual(recon["candidates"], [], f"Prompt #{idx+1} must not infer series/parallel candidates")
            self.assertEqual(recon["resolved_graph"], required_graph, f"Graph mismatch for prompt #{idx+1}: {prompt}")
            self.assertTrue(len(recon["resolved_graph"]) > 0)

            # Explicitly reject the old incorrect parse ("R1 connects from junction(R1,R2) to GND")
            self.assertNotIn("R1 connects from junction(R1,R2) to GND", recon["user_connection_clauses"])
            self.assertNotIn("R1 connects from junction(R1,R2) to GND", md)
            self.assertNotIn("R1: J1 -> GND", recon["resolved_graph"])
            self.assertNotIn("R1: N1 -> GND", recon["resolved_graph"])

            ir = recon["selected_circuit_ir"]
            self.assertIsNotNone(ir)
            comps = {c["id"]: c for c in ir["components"]}
            for req_id in ("V1", "R1", "R2", "R3"):
                self.assertIn(req_id, comps, f"Component {req_id} missing from graph for prompt #{idx+1}")
            self.assertEqual(comps["V1"]["nodes"], ["1", "GND"])
            self.assertEqual(comps["R1"]["nodes"], ["1", "J1"])
            self.assertEqual(comps["R2"]["nodes"], ["J1", "GND"])
            self.assertEqual(comps["R3"]["nodes"], ["J1", "GND"])

            # Every component must have two valid distinct endpoints before simulation
            for c in ir["components"]:
                self.assertEqual(len(c["nodes"]), 2, f"Component {c['id']} must have 2 endpoints")
                self.assertTrue(bool(c["nodes"][0]) and bool(c["nodes"][1]))
                self.assertNotEqual(c["nodes"][0], c["nodes"][1])

            if idx in (0, 1):
                self.assertAlmostEqual(comps["R1"]["value"], 4000.0, places=3)
                self.assertAlmostEqual(comps["R2"]["value"], 2000.0, places=3)
                self.assertAlmostEqual(comps["R3"]["value"], 6000.0, places=3)
                self.assertEqual(
                    recon["user_connection_clauses"],
                    [
                        "R1 connects from N1 to J1",
                        "R2 connects from J1 to GND",
                        "R3 connects from J1 to GND",
                    ],
                )

            self.assertTrue(recon["lifecycle"]["TOPOLOGY_RECONSTRUCTED"])
            self.assertTrue(recon["lifecycle"]["TOPOLOGY_VALIDATED"])
            self.assertTrue(recon["lifecycle"]["SIMULATION_EXECUTED"])
            self.assertTrue(recon["lifecycle"]["SIMULATION_SUCCESSFUL"])

    def test_08_student_lab_question_topology_and_code_only_mode(self):
        """
        Regression test for natural student-style lab-question topology extraction:
        - Unnamed value-qualified components ("A 4 kΩ resistor", "a 2 kΩ resistor", "a 6 kΩ resistor")
        - Connection statements ("from the positive terminal of the source to a junction",
          "From that junction, a 2 kΩ resistor and a 6 kΩ resistor are connected separately to ground")
        - Must NOT classify as AMBIGUOUS_UNSPECIFIED
        - Must resolve:
            V1: N1 -> GND
            R1: N1 -> J1
            R2: J1 -> GND
            R3: J1 -> GND
        - Must obey "Generate the PySpice code only" by returning ONLY executable PySpice code
          in the final response while preserving internal diagnostics in `recon`.
        """
        student_prompt = (
            "I have a 12 V DC source. A 4 kΩ resistor is connected from the positive\n"
            "terminal of the source to a junction. From that junction, a 2 kΩ resistor\n"
            "and a 6 kΩ resistor are connected separately to ground. I need to calculate\n"
            "the DC voltage at the junction."
        )

        recon = ProgressiveCircuitEngine.reconstruct_circuit(student_prompt)
        self.assertFalse(recon["is_ambiguous"])
        self.assertNotEqual(recon["circuit_type"], "AMBIGUOUS_UNSPECIFIED")
        self.assertEqual(recon["circuit_type"], "CUSTOM_NL_TOPOLOGY")
        self.assertEqual(
            recon["resolved_graph"],
            [
                "V1: N1 -> GND",
                "R1: N1 -> J1",
                "R2: J1 -> GND",
                "R3: J1 -> GND",
            ],
        )
        self.assertEqual(
            recon["user_connection_clauses"],
            [
                "R1 connects from N1 to J1",
                "R2 connects from J1 to GND",
                "R3 connects from J1 to GND",
            ],
        )

        # Verify DC nodal voltage at junction J1:
        # R_eq = (2k || 6k) = 1.5k; V(J1) = 12 * 1.5k / (4k + 1.5k) = 18 / 5.5 = 3.272727 V
        sim = recon["simulation_results"]
        self.assertIsNotNone(sim)
        self.assertAlmostEqual(sim["node_voltages"]["J1"], 12.0 * 1500.0 / 5500.0, places=4)

        # Verify "Generate the PySpice code only" obeys output constraint
        code_only_prompt = student_prompt + "\nGenerate the PySpice code only"
        recon_code_only = ProgressiveCircuitEngine.reconstruct_circuit(code_only_prompt)
        final_response = ProgressiveCircuitEngine.format_reconstruction_response(recon_code_only, code_only_prompt)

        # Final response must be ONLY executable Python/PySpice code (no markdown fences or diagnostic sections)
        self.assertNotIn("### 1.", final_response)
        self.assertNotIn("```", final_response)
        self.assertTrue(final_response.startswith(("import ", "from PySpice")))
        self.assertIn("from PySpice.Spice.Netlist import Circuit", final_response)
        compile(final_response, "<generated_pyspice_code>", "exec")
        # Internal diagnostics remain stored in recon_code_only
        self.assertIn("internal_diagnostic_report", recon_code_only)
        self.assertIn("### 1. [USER-PROVIDED VALUES", recon_code_only["internal_diagnostic_report"])


if __name__ == "__main__":
    unittest.main()


