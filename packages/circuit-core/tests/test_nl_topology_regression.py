"""
Regression Test Suite for Graph-Based Natural-Language Topology Reconstruction
Specifically guards against the reproduced bug where inline component values
("r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground")
caused the parser to drop the junction clause and collapse into SERIES_RESISTORS.
"""

import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from progressive_reconstruction import ProgressiveCircuitEngine


def test_reproducer_inline_values_junction_to_ground():
    """
    Exact reproduced test case from bug report:
    'make pyspice code for a 20v source with r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground. calculate the dc node voltages'
    """
    prompt = (
        "make pyspice code for a 20v source with r1 2k and r2 1k in series, "
        "and r3 3.3k connected from the junction of r1 and r2 to ground. "
        "calculate the dc node voltages"
    )
    recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)

    # Must NOT collapse into SERIES_RESISTORS
    assert recon["circuit_type"] == "CUSTOM_NL_TOPOLOGY", f"Expected CUSTOM_NL_TOPOLOGY, got {recon['circuit_type']}"
    assert recon["is_ambiguous"] is False

    # Verify resolved graph
    assert recon["resolved_graph"] == [
        "R1: N1 → N2",
        "R2: N2 → GND",
        "R3: N2 → GND",
    ], f"Unexpected resolved_graph: {recon['resolved_graph']}"

    # Verify Circuit IR component nodes
    ir = recon["selected_circuit_ir"]
    assert ir is not None
    comp_nodes = {c["id"]: c["nodes"] for c in ir["components"]}
    assert comp_nodes["V1"] == ["1", "GND"]
    assert comp_nodes["R1"] == ["1", "2"]
    assert comp_nodes["R2"] == ["2", "GND"]
    assert comp_nodes["R3"] == ["2", "GND"]
    assert "3" not in ir["nodes"], "Node 3 must not exist; R2 and R3 both connect from Node 2 to GND"

    # Verify numerical simulation results match analytical solution:
    # R2 || R3 = (1000 * 3300) / (1000 + 3300) = 767.4419 ohm
    # V(N2) = 20 * 767.4419 / (2000 + 767.4419) = 5.5462 V
    sim = recon["simulation_results"]
    assert sim is not None and sim["converged"] is True
    nv = sim["node_voltages"]
    bc = sim["branch_currents"]

    assert math.isclose(nv["1"], 20.0, abs_tol=1e-4)
    assert math.isclose(nv["2"], 5.5462, abs_tol=1e-4), f"Expected Node 2 = 5.5462 V, got {nv['2']}"
    assert not math.isclose(nv["2"], 13.6508, abs_tol=1e-2), "Bug regression: R1-R2-R3 treated as 3-resistor series chain!"

    assert math.isclose(bc["I(R1)"], 0.007227, abs_tol=1e-5)
    assert math.isclose(bc["I(R2)"], 0.005546, abs_tol=1e-5)
    assert math.isclose(bc["I(R3)"], 0.001681, abs_tol=1e-5)

    # Verify formatted markdown response contains Topology Preview, [Confirm & Simulate], [Edit Circuit],
    # USER CONNECTION CLAUSES, and RESOLVED GRAPH
    md = ProgressiveCircuitEngine.format_reconstruction_response(recon, prompt)
    assert "### [TOPOLOGY PREVIEW BEFORE SIMULATION]" in md
    assert "● N2" in md
    assert "├── R2 1 kΩ ── GND" in md
    assert "└── R3 3.3 kΩ ── GND" in md
    assert "V1: N1 → GND" in md
    assert "R1: N1 → N2" in md
    assert "R2: N2 → GND" in md
    assert "R3: N2 → GND" in md
    assert "`[Confirm & Simulate]`" in md
    assert "`[Edit Circuit]`" in md
    assert "USER CONNECTION CLAUSES" in md
    assert "RESOLVED GRAPH" in md


def test_all_natural_language_junction_and_parallel_phrases():
    """
    Verifies all required natural-language connection phrases resolve to the exact
    same topology graph: R1: N1 -> N2, R2: N2 -> GND, R3: N2 -> GND.
    """
    phrase_prompts = [
        # junction between R1 and R2
        "20V source with R1 2k and R2 1k in series, and R3 3.3k connected from the junction between R1 and R2 to ground",
        # middle point
        "20V source, R1=2k and R2=1k in series, R3=3.3k connected from the middle point to ground",
        # branch at the midpoint
        "20V source with R1 2k and R2 1k in series, and R3 3.3k as a branch at the midpoint to ground",
        # common node / common junction
        "20V source with R1 2k and R2 1k in series, R3 3.3k connected from their common junction to ground",
        "20V source with R1 2k and R2 1k in series, R3 3.3k connected from the common node to ground",
        # branch from the junction / branch connected to the junction
        "20V source with R1 2k and R2 1k in series, R3 3.3k branches from the junction of R1 and R2 to ground",
        # connected across R2
        "20V source with R1 2k and R2 1k in series, and R3 3.3k connected across R2",
        # connected in parallel with R2
        "20V source with R1 2k and R2 1k in series, and R3 3.3k connected in parallel with R2",
        # one end connected to the junction, other end connected to ground
        "20V source with R1 2k and R2 1k in series. One end of R3 3.3k connected to the junction of R1 and R2, other end connected to ground",
        # connected between the same two nodes as R2
        "20V source with R1 2k and R2 1k in series, and R3 3.3k connected between the same two nodes as R2",
        # connected to the same point / both connected to ground
        "20V source with R1 2k and R2 1k in series, and R3 3.3k connected to the same point and to ground",
    ]

    for p in phrase_prompts:
        recon = ProgressiveCircuitEngine.reconstruct_circuit(p)
        assert recon["circuit_type"] == "CUSTOM_NL_TOPOLOGY", f"Failed on prompt: {p} -> got {recon['circuit_type']}"
        assert recon["resolved_graph"] == [
            "R1: N1 → N2",
            "R2: N2 → GND",
            "R3: N2 → GND",
        ], f"Failed graph on prompt: {p} -> got {recon['resolved_graph']}"
        nv = recon["simulation_results"]["node_voltages"]
        assert math.isclose(nv["2"], 5.5462, abs_tol=1e-4), f"Failed V(N2) on prompt: {p} -> got {nv}"


def test_incomplete_nl_topology_never_guesses_series_chain():
    """
    If R1 and R2 are in series, and R3 is mentioned WITHOUT specifying how R3 is connected,
    the parser must NOT silently chain R3 in series (SERIES_RESISTORS).
    It must classify as AMBIGUOUS_UNSPECIFIED and ask for clarification.
    """
    prompt = "20V source with R1 2k and R2 1k in series, and we also have R3 3.3k"
    recon = ProgressiveCircuitEngine.reconstruct_circuit(prompt)
    assert recon["circuit_type"] == "AMBIGUOUS_UNSPECIFIED", (
        f"Expected AMBIGUOUS_UNSPECIFIED when R3 connection is missing, got {recon['circuit_type']}"
    )
    assert recon["is_ambiguous"] is True


if __name__ == "__main__":
    test_reproducer_inline_values_junction_to_ground()
    print("[PASS] test_reproducer_inline_values_junction_to_ground")
    test_all_natural_language_junction_and_parallel_phrases()
    print("[PASS] test_all_natural_language_junction_and_parallel_phrases")
    test_incomplete_nl_topology_never_guesses_series_chain()
    print("[PASS] test_incomplete_nl_topology_never_guesses_series_chain")
    print("ALL NL TOPOLOGY REGRESSION TESTS PASSED!")
