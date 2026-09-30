"""
SIMLAB AI — Phase 17: Local Domain Knowledge Indexer & Structured Retriever
Indexes structured experiment knowledge, canonical circuit templates, categorized viva Q&As,
and domain adaptation few-shot examples into SQLite (with FTS5) and provides targeted retrieval
for the local Llama 3.1 8B inference pipeline.
"""

import os
import sys
import json
import re
import sqlite3
from typing import Dict, List, Any, Optional

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KNOWLEDGE_DIR = os.path.join(APP_ROOT, "knowledge")
TRAINING_DIR = os.path.join(APP_ROOT, "training")
DB_PATH = os.path.join(KNOWLEDGE_DIR, "manual_db.sqlite")

if os.path.join(APP_ROOT, "packages", "knowledge-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "knowledge-core", "src"))

from domain_knowledge_builder import get_structured_experiments_catalog, build_canonical_circuit_templates
from progressive_reconstruction import ProgressiveCircuitEngine


def index_domain_knowledge_to_sqlite(db_path: str = DB_PATH) -> Dict[str, int]:
    """Indexes Phase 1 structured experiments, Phase 2 canonical circuits, viva Q&As, and training examples into SQLite."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS domain_experiments;
        DROP TABLE IF EXISTS domain_experiments_fts;
        DROP TABLE IF EXISTS canonical_circuits;
        DROP TABLE IF EXISTS domain_viva;
        DROP TABLE IF EXISTS domain_viva_fts;
        DROP TABLE IF EXISTS domain_examples;
        DROP TABLE IF EXISTS domain_examples_fts;

        CREATE TABLE domain_experiments (
            exp_number INTEGER PRIMARY KEY,
            title TEXT,
            aim TEXT,
            simulation_type TEXT,
            circuit_topology TEXT,
            theory TEXT,
            equations_json TEXT,
            apparatus_json TEXT,
            relationships_json TEXT,
            procedure_text TEXT,
            code TEXT,
            observations_text TEXT,
            result TEXT,
            common_mistakes_json TEXT,
            terminology_json TEXT,
            related_json TEXT
        );

        CREATE VIRTUAL TABLE domain_experiments_fts USING fts5(
            exp_number UNINDEXED,
            title,
            aim,
            circuit_topology,
            theory,
            terminology,
            common_mistakes
        );

        CREATE TABLE canonical_circuits (
            circuit_id TEXT PRIMARY KEY,
            exp_number INTEGER,
            title TEXT,
            topology TEXT,
            analysis_type TEXT,
            circuit_ir_json TEXT
        );

        CREATE TABLE domain_viva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exp_number INTEGER,
            viva_type TEXT,
            question TEXT,
            answer TEXT
        );

        CREATE VIRTUAL TABLE domain_viva_fts USING fts5(
            exp_number UNINDEXED,
            viva_type,
            question,
            answer
        );

        CREATE TABLE domain_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            exp_id INTEGER,
            instruction TEXT,
            output TEXT,
            metadata_json TEXT
        );

        CREATE VIRTUAL TABLE domain_examples_fts USING fts5(
            category,
            instruction,
            output
        );
        """
    )

    catalog = get_structured_experiments_catalog()
    circuits = build_canonical_circuit_templates()

    exp_count = 0
    viva_count = 0
    for num, exp in sorted(catalog.items()):
        recon = ProgressiveCircuitEngine.reconstruct_circuit(f"Simulate Experiment {num}", experiment_context=num)
        code_str = recon.get("generated_pyspice_code", "")
        proc_str = exp["procedure"] if isinstance(exp["procedure"], str) else "\n".join(exp["procedure"])
        obs_str = exp["expected_observations"] if isinstance(exp["expected_observations"], str) else "\n".join(exp["expected_observations"])

        cur.execute(
            """
            INSERT INTO domain_experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                num,
                exp["title"],
                exp["aim"],
                exp["simulation_type"],
                exp["circuit_topology"],
                exp["theory"],
                json.dumps(exp["equations"], ensure_ascii=False),
                json.dumps(exp["apparatus_components"], ensure_ascii=False),
                json.dumps(exp["component_relationships"], ensure_ascii=False),
                proc_str,
                code_str,
                obs_str,
                exp["result"],
                json.dumps(exp["common_mistakes"], ensure_ascii=False),
                json.dumps(exp["important_terminology"], ensure_ascii=False),
                json.dumps(exp["related_experiments"], ensure_ascii=False),
            ),
        )
        cur.execute(
            """
            INSERT INTO domain_experiments_fts VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(num),
                exp["title"],
                exp["aim"],
                exp["circuit_topology"],
                exp["theory"],
                " ".join(exp["important_terminology"]),
                " ".join(exp["common_mistakes"]),
            ),
        )
        exp_count += 1

        for v in exp["viva_concepts"]:
            cur.execute(
                "INSERT INTO domain_viva (exp_number, viva_type, question, answer) VALUES (?, ?, ?, ?)",
                (num, v["category"], v["q"], v["a"]),
            )
            cur.execute(
                "INSERT INTO domain_viva_fts VALUES (?, ?, ?, ?)",
                (str(num), v["category"], v["q"], v["a"]),
            )
            viva_count += 1

    circuit_count = 0
    for cid, cir in circuits.items():
        cur.execute(
            "INSERT INTO canonical_circuits VALUES (?, ?, ?, ?, ?, ?)",
            (
                cid,
                cir.get("experiment_number"),
                cir.get("name", cid),
                cir.get("circuit_type", ""),
                cir.get("analysis_type", ""),
                json.dumps(cir, ensure_ascii=False),
            ),
        )
        circuit_count += 1

    example_count = 0
    combined_jsonl = os.path.join(TRAINING_DIR, "simlab_sft_combined.jsonl")
    if os.path.exists(combined_jsonl):
        with open(combined_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                cur.execute(
                    "INSERT INTO domain_examples (category, exp_id, instruction, output, metadata_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        rec.get("category", ""),
                        rec.get("exp_id"),
                        rec.get("instruction", ""),
                        rec.get("output", ""),
                        json.dumps(rec.get("metadata", {}), ensure_ascii=False),
                    ),
                )
                cur.execute(
                    "INSERT INTO domain_examples_fts VALUES (?, ?, ?)",
                    (rec.get("category", ""), rec.get("instruction", ""), rec.get("output", "")),
                )
                example_count += 1

    conn.commit()
    conn.close()
    return {
        "domain_experiments": exp_count,
        "canonical_circuits": circuit_count,
        "domain_viva": viva_count,
        "domain_examples": example_count,
    }


class DomainRetriever:
    """Retrieves targeted structured experiment knowledge, canonical circuits, viva Q&As, and few-shot examples."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _sanitize_fts_query(self, query: str) -> str:
        stop_words = {
            "what", "is", "the", "in", "of", "for", "and", "to", "a", "an", "how", "why",
            "can", "you", "make", "give", "me", "explain", "show", "write", "code", "circuit",
            "with", "from", "by", "on", "at", "use", "using", "simulate", "simulation",
        }
        tokens = re.findall(r"[a-zA-Z0-9_]+", query.lower())
        meaningful = [t for t in tokens if t not in stop_words and len(t) >= 2]
        if not meaningful:
            meaningful = tokens[:5]
        return " OR ".join(meaningful[:10])

    def detect_experiment_number(self, query: str, fallback_exp_id: Optional[int] = None) -> Optional[int]:
        if fallback_exp_id and 1 <= int(fallback_exp_id) <= 14:
            return int(fallback_exp_id)
        m = re.search(r"\b(?:experiment|exp\.?)\s*(\d{1,2})\b", query, re.I)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 14:
                return val
        q_low = query.lower()
        keyword_map = [
            (1, ["resistor bridge", "wheatstone"]),
            (2, ["cccs", "current controlled current source"]),
            (3, ["vcvs", "voltage controlled voltage source"]),
            (4, ["natural response of an rc", "natural response of rc", "rc natural"]),
            (5, ["step response of an rc", "step response of rc", "rc step"]),
            (6, ["pacemaker"]),
            (7, ["truth tables of logic gates", "basic logic gates"]),
            (8, ["half adder", "full adder"]),
            (9, ["sop", "pos", "sum of products", "product of sums"]),
            (10, ["minimum nand", "nand combinational"]),
            (11, ["diode i-v", "diode v-i", "pn-junction diode", "pn junction diode"]),
            (12, ["zener", "voltage regulator"]),
            (13, ["half wave rectifier", "half-wave rectifier"]),
            (14, ["full wave rectifier", "full-wave rectifier", "bridge rectifier"]),
        ]
        for exp_id, kw_list in keyword_map:
            if any(k in q_low for k in kw_list):
                return exp_id
        return None

    def retrieve(
        self,
        query: str,
        exp_id: Optional[int] = None,
        topology_intent: Optional[str] = None,
        max_viva: int = 3,
        max_examples: int = 2,
    ) -> Dict[str, Any]:
        if not os.path.exists(self.db_path):
            return {"experiment": None, "canonical_circuit": None, "viva": [], "examples": [], "formatted_context": ""}

        resolved_exp = self.detect_experiment_number(query, exp_id)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        exp_data = None
        if resolved_exp:
            row = cur.execute("SELECT * FROM domain_experiments WHERE exp_number = ?", (resolved_exp,)).fetchone()
            if row:
                exp_data = dict(row)

        canonical_circuit = None
        if resolved_exp:
            crow = cur.execute("SELECT * FROM canonical_circuits WHERE exp_number = ? LIMIT 1", (resolved_exp,)).fetchone()
            if crow:
                canonical_circuit = json.loads(crow["circuit_ir_json"])
        elif topology_intent:
            crow = cur.execute("SELECT * FROM canonical_circuits WHERE topology = ? LIMIT 1", (topology_intent,)).fetchone()
            if crow:
                canonical_circuit = json.loads(crow["circuit_ir_json"])

        fts_q = self._sanitize_fts_query(query)
        viva_matches = []
        if fts_q:
            try:
                if resolved_exp:
                    vrows = cur.execute(
                        "SELECT exp_number, viva_type, question, answer FROM domain_viva_fts WHERE domain_viva_fts MATCH ? AND exp_number = ? LIMIT ?",
                        (fts_q, str(resolved_exp), max_viva),
                    ).fetchall()
                else:
                    vrows = cur.execute(
                        "SELECT exp_number, viva_type, question, answer FROM domain_viva_fts WHERE domain_viva_fts MATCH ? LIMIT ?",
                        (fts_q, max_viva),
                    ).fetchall()
                viva_matches = [dict(r) for r in vrows]
            except Exception:
                viva_matches = []

        if resolved_exp and not viva_matches:
            vrows = cur.execute(
                "SELECT exp_number, viva_type, question, answer FROM domain_viva WHERE exp_number = ? LIMIT ?",
                (resolved_exp, max_viva),
            ).fetchall()
            viva_matches = [dict(r) for r in vrows]

        example_matches = []
        if fts_q:
            try:
                erows = cur.execute(
                    "SELECT category, instruction, output FROM domain_examples_fts WHERE domain_examples_fts MATCH ? LIMIT ?",
                    (fts_q, max_examples),
                ).fetchall()
                example_matches = [dict(r) for r in erows]
            except Exception:
                example_matches = []

        conn.close()

        ctx_parts = []
        if exp_data:
            eqs = json.loads(exp_data["equations_json"])
            rels = json.loads(exp_data["relationships_json"])
            mistakes = json.loads(exp_data["common_mistakes_json"])
            ctx_parts.append(
                f"=== AUTHORITATIVE LAB MANUAL CONTEXT (Experiment {exp_data['exp_number']}: {exp_data['title']}) ===\n"
                f"Aim: {exp_data['aim']}\n"
                f"Topology Template: {exp_data['circuit_topology']} ({exp_data['simulation_type']})\n"
                f"Theory: {exp_data['theory']}\n"
                f"Equations: {'; '.join(eqs)}\n"
                f"Canonical Connections: {'; '.join(rels)}\n"
                f"Common Mistakes to Avoid: {'; '.join(mistakes)}\n"
                f"IMPORTANT RULE: Use this manual topology/theory as reference, NEVER overwrite user-supplied component values from the latest user prompt."
            )

        if viva_matches:
            viva_lines = [f"- Q ({v['viva_type']}): {v['question']}\n  A: {v['answer']}" for v in viva_matches]
            ctx_parts.append("=== RELEVANT LAB VIVA KNOWLEDGE ===\n" + "\n".join(viva_lines))

        return {
            "experiment": exp_data,
            "canonical_circuit": canonical_circuit,
            "viva": viva_matches,
            "examples": example_matches,
            "formatted_context": "\n\n".join(ctx_parts),
        }


if __name__ == "__main__":
    stats = index_domain_knowledge_to_sqlite()
    print("Indexed domain knowledge into SQLite:", json.dumps(stats, indent=2))
