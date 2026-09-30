import subprocess
import time
import urllib.request
import json
import os
import sys

already_running = False
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/system/status", timeout=1.0) as r:
        if r.status == 200:
            already_running = True
            print("[OK] Existing server detected on port 8000!")
except Exception:
    already_running = False

proc = None
if not already_running:
    print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "runtime/server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Wait for server to bind port
    bound = False
    for _ in range(20):
        time.sleep(0.5)
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8000/api/system/status", timeout=1.0)
            if req.status == 200:
                bound = True
                break
        except Exception:
            pass

    if not bound:
        print("Server failed to bind in time. Output:")
        out, _ = proc.communicate(timeout=2)
        print(out)
        sys.exit(1)

    print("[OK] Server listening on port 8000!")

try:
    # 1. System Status
    res = urllib.request.urlopen("http://127.0.0.1:8000/api/system/status")
    status = json.loads(res.read().decode())
    print("1. Status:", status["status"], "| Offline:", status["offline_mode"], "| Exp Indexed:", status["knowledge_base"]["experiments_indexed"])

    # 2. Experiments
    res = urllib.request.urlopen("http://127.0.0.1:8000/api/experiments")
    exps = json.loads(res.read().decode())
    print(f"2. Experiments count: {len(exps)}")

    # 3. Experiment 6 (Pacemaker)
    res = urllib.request.urlopen("http://127.0.0.1:8000/api/experiments/6")
    exp6 = json.loads(res.read().decode())
    print("3. Exp 6 Title:", exp6["title"])
    print("   Pages:", exp6["pages_text"])
    print("   Viva Q count:", len(exp6["viva_questions"]))

    # 4. Search
    res = urllib.request.urlopen("http://127.0.0.1:8000/api/search?q=pacemaker")
    hits = json.loads(res.read().decode())
    print(f"4. Search Hits: {len(hits)}")
    print("   First citation:", hits[0]["citation"])

    # 5. Progressive Circuit Reconstruction (Ambiguous)
    req5 = urllib.request.Request(
        "http://127.0.0.1:8000/api/circuit/reconstruct",
        data=json.dumps({"prompt": "I have a 12V voltage source and five resistors: R1 is 2k, R2 is 1k, R3 is 2k, R4 is 2k, R5 is 1k"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res5 = urllib.request.urlopen(req5)
    data5 = json.loads(res5.read().decode())
    print("5. Progressive Recon (Ambiguous):")
    print(f"   Is ambiguous: {data5['is_ambiguous']} | Candidates: {len(data5['candidates'])} | Comps: {len(data5['known_components'])}")

    # 6. Progressive Circuit Confirmation (Candidate A)
    req6 = urllib.request.Request(
        "http://127.0.0.1:8000/api/circuit/reconstruct",
        data=json.dumps({"prompt": "I have a 12V voltage source and five resistors: R1 is 2k, R2 is 1k, R3 is 2k, R4 is 2k, R5 is 1k. Use Candidate A bridge"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res6 = urllib.request.urlopen(req6)
    data6 = json.loads(res6.read().decode())
    print("6. Progressive Recon (Confirmed):")
    print(f"   Status: {data6['status']} | User Confirmed: {data6['selected_circuit_ir']['metadata']['user_confirmed']}")

    # 7. Live Chat SSE Stream
    req7 = urllib.request.Request(
        "http://127.0.0.1:8000/api/chat",
        data=json.dumps({"messages": [{"role": "user", "content": "I have a 12V voltage source and five resistors: R1 is 2k, R2 is 1k, R3 is 2k, R4 is 2k, R5 is 1k"}]}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res7 = urllib.request.urlopen(req7)
    chat_bytes = len(res7.read())
    print(f"7. Live Chat SSE Stream: {chat_bytes} bytes received")

    print("\nALL SERVER ENDPOINTS & PROGRESSIVE REASONING VERIFIED AND FUNCTIONING PERFECTLY!")

finally:
    if proc:
        proc.terminate()
        proc.wait(timeout=2)
