"""
SIMLAB AI - Desktop Application Entry Point
Launches the native Windows WebView2 desktop shell and local backend services.
100% Offline · Portable USB Execution.
"""

import os
import sys
import runpy
import threading
import subprocess
import time
import urllib.request
import webview

# Ensure PyInstaller bundles all dependencies needed by runtime/server.py & circuit-core
import sqlite3
import json
import re
import psutil
import numpy
import fastapi
import fastapi.middleware.cors
import fastapi.responses
import fastapi.staticfiles
import starlette.staticfiles
import pydantic
import uvicorn

if getattr(sys, "frozen", False):
    APP_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Allow `SimLabAI.exe <script.py> [args...]` to act as a portable Python runner on any PC
if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    script_arg = sys.argv[1]
    script_path = script_arg if os.path.isabs(script_arg) else os.path.join(APP_ROOT, script_arg)
    sys.path.insert(0, os.path.dirname(os.path.abspath(script_path)))
    sys.path.insert(0, APP_ROOT)
    sys.argv = sys.argv[1:]
    runpy.run_path(script_path, run_name="__main__")
    sys.exit(0)

SERVER_SCRIPT = os.path.join(APP_ROOT, "runtime", "server.py")
KOBOLD_BIN = os.path.join(APP_ROOT, "runtime", "llama", "koboldcpp.exe")
MODEL_PATH = os.path.join(APP_ROOT, "models", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")


def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    """Polls until the server actively responds with HTTP 200."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.urlopen(url, timeout=1.0)
            if req.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def start_inprocess_server():
    """Starts runtime/server.py inside a daemon thread when running as standalone SimLabAI.exe."""
    runtime_dir = os.path.join(APP_ROOT, "runtime")
    if runtime_dir not in sys.path:
        sys.path.insert(0, runtime_dir)
    if APP_ROOT not in sys.path:
        sys.path.insert(0, APP_ROOT)
    import importlib.util
    spec = importlib.util.spec_from_file_location("simlab_runtime_server", SERVER_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    uvicorn.run(mod.app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    print("========================================================")
    print(" SIMLAB AI - Your Offline Simulation Lab Copilot")
    print(f" Root:  {APP_ROOT}")
    print(f" Model: {MODEL_PATH}")
    print("========================================================")

    server_proc = None
    health_url = "http://127.0.0.1:8000/api/system/status"

    # 1. Launch offline core server if not already listening on :8000
    if wait_for_server(health_url, timeout=0.8):
        print("[1/3] Local core server already running on http://127.0.0.1:8000")
    elif getattr(sys, "frozen", False):
        print("[1/3] Starting embedded core server on http://127.0.0.1:8000 ...")
        srv_thread = threading.Thread(target=start_inprocess_server, daemon=True)
        srv_thread.start()
    else:
        print("[1/3] Starting local core server on http://127.0.0.1:8000 ...")
        server_proc = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            cwd=APP_ROOT
        )

    kobold_proc = None
    # 2. Launch local LLM engine in background if binary & model exist
    if os.path.exists(KOBOLD_BIN) and os.path.exists(MODEL_PATH):
        try:
            print("[2/3] Initializing local Llama 3.1 8B inference engine (:5001)...")
            log_dir = os.path.join(APP_ROOT, "workspace", "logs")
            os.makedirs(log_dir, exist_ok=True)
            klog = open(os.path.join(log_dir, "koboldcpp.log"), "w", encoding="utf-8")
            kcmd = [
                KOBOLD_BIN,
                "--model", MODEL_PATH,
                "--port", "5001",
                "--skiplauncher",
                "--threads", "6",
                "--contextsize", "2048",
                "--gpulayers", "0",
                "--smartcontext"
            ]
            kobold_proc = subprocess.Popen(kcmd, stdout=klog, stderr=subprocess.STDOUT, cwd=os.path.dirname(KOBOLD_BIN))
        except Exception as e:
            print("[!] Could not auto-launch koboldcpp:", e)
    else:
        print("[*] Local GGUF model or kobold binary not present, continuing in deterministic offline mode.")

    try:
        # 3. Wait until server actively responds
        ready = wait_for_server(health_url, timeout=12.0)
        if ready:
            print("[3/3] Core server is online! Launching desktop window...")
        else:
            print("[!] Warning: Server readiness check timed out. Launching window anyway...")

        # 4. Create native Windows desktop window
        frontend_url = "http://127.0.0.1:8000/"
        window = webview.create_window(
            title="SIMLAB AI - Your Offline Simulation Lab Copilot (23EEP20B)",
            url=frontend_url,
            width=1280,
            height=820,
            min_size=(960, 600),
            background_color="#09090b"
        )
        webview.start(debug=False)

    finally:
        print("[*] Shutting down background processes...")
        if server_proc:
            try:
                server_proc.terminate()
                server_proc.wait(timeout=3)
            except Exception:
                server_proc.kill()

        if kobold_proc:
            try:
                kobold_proc.terminate()
                kobold_proc.wait(timeout=3)
            except Exception:
                kobold_proc.kill()

if __name__ == "__main__":
    main()
