"""
SIMLAB AI — Phase 18: Merge LoRA Adapter & Export Quantized GGUF
Merges the trained LoRA adapter into the non-quantized Llama-3.1-8B-Instruct base model,
converts the merged model to FP16 GGUF, and quantizes to Q4_K_M without touching
the original models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf file.
"""

import os
import subprocess
import argparse

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROTECTED_GGUF = os.path.normpath(os.path.join(APP_ROOT, "models", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"))


def merge_and_export_gguf(
    base_model: str,
    adapter_dir: str,
    merged_dir: str,
    output_gguf: str,
    llama_cpp_dir: str = "llama.cpp",
    dry_run: bool = False,
):
    if os.path.normpath(os.path.abspath(output_gguf)).lower() == PROTECTED_GGUF.lower():
        raise ValueError(
            "CRITICAL SAFETY ERROR: Cannot overwrite protected inference model "
            f"{PROTECTED_GGUF}. Export to a distinct filename such as models/SimLab-Llama-3.1-8B-Instruct-Q4_K_M.gguf."
        )

    steps = [
        f"1. Merge PEFT LoRA adapter '{adapter_dir}' into base model '{base_model}' -> '{merged_dir}'",
        f"2. Run `{llama_cpp_dir}/convert_hf_to_gguf.py {merged_dir} --outfile {merged_dir}/model-f16.gguf --outtype f16`",
        f"3. Run `{llama_cpp_dir}/llama-quantize {merged_dir}/model-f16.gguf {output_gguf} Q4_K_M`",
    ]
    print("[GGUF Export Pipeline] Planned steps:")
    for s in steps:
        print("  ", s)

    if dry_run:
        return {"status": "dry_run_ok", "steps": steps, "protected_model_untouched": True}

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    base = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.float16, device_map="cpu")
    merged = PeftModel.from_pretrained(base, adapter_dir)
    merged = merged.merge_and_unload()
    os.makedirs(merged_dir, exist_ok=True)
    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)

    f16_gguf = os.path.join(merged_dir, "model-f16.gguf")
    subprocess.run(
        ["python", os.path.join(llama_cpp_dir, "convert_hf_to_gguf.py"), merged_dir, "--outfile", f16_gguf, "--outtype", "f16"],
        check=True,
    )
    subprocess.run(
        [os.path.join(llama_cpp_dir, "llama-quantize"), f16_gguf, output_gguf, "Q4_K_M"],
        check=True,
    )
    return {"status": "exported", "output_gguf": output_gguf}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge LoRA Adapter and Export to Q4_K_M GGUF")
    parser.add_argument("--base-model", default="meta-llama/Meta-Llama-3.1-8B-Instruct")
    parser.add_argument("--adapter-dir", default=os.path.join(APP_ROOT, "training", "lora_pipeline", "checkpoints", "simlab-llama3.1-8b-lora"))
    parser.add_argument("--merged-dir", default=os.path.join(APP_ROOT, "training", "lora_pipeline", "checkpoints", "simlab-llama3.1-8b-merged"))
    parser.add_argument("--output-gguf", default=os.path.join(APP_ROOT, "models", "SimLab-Llama-3.1-8B-Instruct-Q4_K_M.gguf"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    merge_and_export_gguf(args.base_model, args.adapter_dir, args.merged_dir, args.output_gguf, dry_run=args.dry_run)
