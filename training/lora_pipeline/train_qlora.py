"""
SIMLAB AI — Phase 18: Offline QLoRA Training Script (Separate from GGUF Inference Runtime)
Trains a LoRA adapter on top of the non-quantized Meta-Llama-3.1-8B-Instruct base model
using the generated domain datasets in training/*.jsonl.

SAFETY GUARD:
Explicitly blocks any attempt to pass a .gguf file as the training base model.
"""

import os
import sys
import json
import argparse

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATASET = os.path.join(APP_ROOT, "training", "simlab_sft_combined.jsonl")
DEFAULT_OUTPUT = os.path.join(APP_ROOT, "training", "lora_pipeline", "checkpoints", "simlab-llama3.1-8b-lora")


def validate_base_model_not_gguf(base_model: str) -> None:
    if base_model.lower().endswith(".gguf") or "q4_k_m" in base_model.lower():
        raise ValueError(
            f"CRITICAL SAFETY ERROR: '{base_model}' is a quantized GGUF inference artifact. "
            "Never fine-tune Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf directly. "
            "Provide the non-quantized HuggingFace base model ID or directory (e.g. 'meta-llama/Meta-Llama-3.1-8B-Instruct')."
        )


def format_llama31_chat(messages: list) -> str:
    out = "<|begin_of_text|>"
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        out += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    return out


def run_qlora_training(base_model: str, dataset_path: str, output_dir: str, epochs: int = 3, dry_run: bool = False):
    validate_base_model_not_gguf(base_model)
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Training dataset not found: {dataset_path}. Run `simlab train-data` first.")

    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"[QLoRA Pipeline] Loaded {len(records)} domain-adaptation examples from {dataset_path}")
    print(f"[QLoRA Pipeline] Base Model (non-GGUF): {base_model}")
    print(f"[QLoRA Pipeline] Target Adapter Output: {output_dir}")

    if dry_run:
        sample_prompt = format_llama31_chat(records[0]["messages"])
        print("[QLoRA Pipeline] Dry-run verification passed. Sample formatted Llama-3.1 chat template:")
        print(sample_prompt[:450] + "...\n")
        return {"status": "dry_run_ok", "examples": len(records), "base_model": base_model}

    import torch
    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=32,
        lora_alpha=64,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)

    formatted_texts = [{"text": format_llama31_chat(r["messages"])} for r in records]
    hf_dataset = Dataset.from_list(formatted_texts)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=10,
        save_strategy="epoch",
        bf16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=hf_dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        tokenizer=tokenizer,
        args=training_args,
    )
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"[QLoRA Pipeline] Saved trained LoRA adapter to {output_dir}")
    return {"status": "trained", "output_dir": output_dir}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SIMLAB AI QLoRA Trainer")
    parser.add_argument("--base-model", default="meta-llama/Meta-Llama-3.1-8B-Instruct")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset & Llama-3.1 chat formatting without GPU training")
    args = parser.parse_args()
    run_qlora_training(args.base_model, args.dataset, args.output_dir, args.epochs, args.dry_run)
