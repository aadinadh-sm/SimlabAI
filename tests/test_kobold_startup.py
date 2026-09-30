import subprocess
import time
import urllib.request
import json
import os

model_path = r"D:\simlab-ai\models\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
kobold_bin = r"D:\simlab-ai\runtime\llama\koboldcpp.exe"

cmd = [
    kobold_bin,
    "--model", model_path,
    "--port", "5001",
    "--skiplauncher",
    "--threads", "6",
    "--contextsize", "2048",
    "--gpulayers", "0",
    "--smartcontext"
]

print("Launching koboldcpp test with model:", model_path)
proc = subprocess.Popen(cmd)

bound = False
for i in range(45):
    time.sleep(1)
    try:
        req = urllib.request.urlopen("http://127.0.0.1:5001/api/extra/version", timeout=1)
        if req.status == 200:
            print(f"koboldcpp bound in {i+1} seconds!")
            bound = True
            break
    except Exception:
        pass

if bound:
    print("Testing /v1/chat/completions...")
    payload = json.dumps({
        "model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M",
        "messages": [{"role": "user", "content": "Explain Ohm's Law in one sentence."}],
        "max_tokens": 50,
        "temperature": 0.2
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:5001/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode())
        print("Generated text:\n", res["choices"][0]["message"]["content"])

proc.terminate()
proc.wait()
print("Test completed successfully.")
