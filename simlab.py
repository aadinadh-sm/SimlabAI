#!/usr/bin/env python3
"""
SIMLAB AI — Unified CLI (`simlab`)
Supports:
  simlab train-data     Build structured manual knowledge, canonical Circuit IRs,
                        JSONL training datasets, regression fixtures, SQLite FTS5 index,
                        and run the 140-prompt domain evaluation benchmark.
  simlab benchmark      Run the 140-prompt domain evaluation benchmark suite.
  simlab qlora-dry-run  Validate the separate QLoRA training & GGUF export pipeline.
"""

import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.join(APP_ROOT, "packages", "knowledge-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "knowledge-core", "src"))
if os.path.join(APP_ROOT, "packages", "circuit-core", "src") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "packages", "circuit-core", "src"))
if os.path.join(APP_ROOT, "tests") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "tests"))
if os.path.join(APP_ROOT, "training", "lora_pipeline") not in sys.path:
    sys.path.insert(0, os.path.join(APP_ROOT, "training", "lora_pipeline"))

from domain_knowledge_builder import build_and_save_structured_domain_knowledge
from dataset_generator import build_all_training_datasets
from domain_retriever import index_domain_knowledge_to_sqlite
from benchmark_domain_suite import run_benchmark_suite


def cmd_train_data():
    t0 = time.time()
    print("=" * 72)
    print("SIMLAB AI — DOMAIN ADAPTATION & KNOWLEDGE PIPELINE (`simlab train-data`)")
    print("=" * 72)

    # Phase 1 & 2: Structured Experiment Knowledge & Canonical Circuit IR Templates
    print("\n[Phase 1 & 2] Building structured experiment catalog & canonical Circuit IR templates...")
    cat, tpls = build_and_save_structured_domain_knowledge()
    viva_total = sum(len(exp.get("viva_concepts", [])) for exp in cat.values())
    print(f"  -> Experiments built:       {len(cat)} (knowledge/experiments/exp1..14.json)")
    print(f"  -> Canonical circuits:      {len(tpls)} (knowledge/circuits/*.json)")
    print(f"  -> Categorized Viva Q&As:   {viva_total}")

    # Phases 3–16: Training Datasets
    print("\n[Phases 3–16] Generating domain-adaptation JSONL training datasets...")
    ds_stats = build_all_training_datasets()
    for fname, count in ds_stats.items():
        print(f"  -> training/{fname:<32} : {count:>4} examples")

    # Phase 17: SQLite + FTS5 Domain Index
    print("\n[Phase 17] Indexing structured knowledge, circuits, viva, and examples into SQLite FTS5...")
    db_stats = index_domain_knowledge_to_sqlite()
    for table_name, count in db_stats.items():
        print(f"  -> SQLite {table_name:<25} : {count:>4} rows")

    # Phase 19: Evaluation Benchmark Suite
    print("\n[Phase 19] Running 140-prompt Domain Evaluation Benchmark Suite...")
    bench = run_benchmark_suite()
    print(f"  -> Total Prompts Evaluated:          {bench['total_prompts']}")
    print(f"  -> Intent Classification Accuracy:   {bench['intent_accuracy']}")
    print(f"  -> Value Extraction Accuracy:        {bench['value_extraction_accuracy']}")
    print(f"  -> Topology Reconstruction Accuracy: {bench['topology_reconstruction_accuracy']}")
    print(f"  -> Code Generation Accuracy:         {bench['code_generation_accuracy']}")
    print(f"  -> Zero Contamination Rate:          {bench['zero_contamination_rate']}")
    print(f"  -> Domain Retrieval Accuracy:        {bench['domain_retrieval_accuracy']}")

    elapsed = time.time() - t0
    print("\n" + "=" * 72)
    print(f"COMPLETED `simlab train-data` in {elapsed:.2f}s (Failures: {bench['failure_count']})")
    print("=" * 72)

    if bench["failure_count"] > 0:
        print("\nFailures detected:")
        print(json.dumps(bench["failures"], indent=2, ensure_ascii=False))
        sys.exit(1)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("train-data", "train_data"):
        cmd_train_data()
    elif sys.argv[1] == "benchmark":
        report = run_benchmark_suite()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif sys.argv[1] == "qlora-dry-run":
        from train_qlora import run_qlora_training, DEFAULT_DATASET, DEFAULT_OUTPUT
        from export_gguf import merge_and_export_gguf
        run_qlora_training("meta-llama/Meta-Llama-3.1-8B-Instruct", DEFAULT_DATASET, DEFAULT_OUTPUT, dry_run=True)
        merge_and_export_gguf(
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            DEFAULT_OUTPUT,
            os.path.join(APP_ROOT, "training", "lora_pipeline", "checkpoints", "simlab-llama3.1-8b-merged"),
            os.path.join(APP_ROOT, "models", "SimLab-Llama-3.1-8B-Instruct-Q4_K_M.gguf"),
            dry_run=True,
        )
    else:
        print(f"Unknown command: {sys.argv[1]}. Use: train-data | benchmark | qlora-dry-run")
        sys.exit(1)


if __name__ == "__main__":
    main()
