# SIMLAB AI: Your Offline Simulation Lab Copilot

**SIMLAB AI** is an offline, production-grade desktop engineering copilot designed around the official **"23EEP20B - SIMULATION LAB MANUAL"** (APJ Abdul Kalam Technological University).

It runs completely offline from a USB pendrive on Windows PCs without cloud APIs, telemetry, accounts, or pre-installed developer runtimes.

---

## Key Capabilities

1. **Authoritative 14-Experiment Knowledge Base**:
   - Every experiment from the manual is indexed chunk-by-chunk in a local **SQLite FTS5** database.
   - Exact aims, apparatus, theoretical derivations, PySpice/Multisim/Simulink procedures, and results.
   - High-resolution scans of official manual diagrams and schematics rendered locally.

2. **Offline Local AI (Llama 3.1 8B Instruct Q4_K_M)**:
   - Self-contained inference via `runtime/llama/koboldcpp.exe` (llama.cpp engine).
   - Real-time streaming chat with strict grounding in manual excerpts.
   - Automatic citations formatted as: `Source: Simulation Lab Manual · Experiment <X> · <Section> · Page <Y>`.
   - Never fabricates unsimulated values.

3. **Deterministic Separation of Concerns**:
   - Numerical simulations, Boolean algebra, truth tables, and circuit topology validation are executed by deterministic engines, NOT by LLM guesswork.

4. **Digital Logic Engine (Multisim Equivalent)**:
   - Evaluates AND, OR, NOT, NAND, NOR, XOR, XNOR gates with live logic switches and LEDs.
   - Verified truth table generation.
   - Models Half Adder, Full Adder (Exp 8), SOP $\Sigma(1,3,6)$ (Exp 9), and NAND-only majority logic $F = AB + BC + AC$ (Exp 10).

5. **Analog & Waveform Simulator (PySpice & Simulink Equivalent)**:
   - Interactive parameter tuning: Resistance ($R$), Capacitance ($C$), Voltage ($V_{in}$), Frequency ($f$), and Diode filters.
   - Real-time canvas waveforms for RC natural response, step response, Half-wave rectifier, Full-wave bridge rectifier, Diode I-V curves, and Zener regulators.

6. **Interactive Viva Engine**:
   - Question banks for all 14 experiments.
   - Semantic concept extraction and assessment ("Correct", "Partially correct", "Review needed").
   - Highlights covered concepts and identifies missing technical points.

7. **Lab Record & Report Generator**:
   - Generates full academic lab records with Aim, Theory, Procedure, Circuit parameters, and Results.
   - Exports directly to Markdown (`.md`) or printable format.

---

## Directory Layout (USB Portable)

```
SIMLAB_AI/
├── apps/
│   └── desktop/               # React 18 + TypeScript + Tailwind CSS Frontend
├── knowledge/
│   ├── experiments/           # Structured JSON for experiments 1-14
│   ├── viva/                  # Viva question banks
│   ├── images/                # 42 manual scan diagrams (pages 1-42)
│   ├── manual_db.sqlite       # SQLite FTS5 database
│   ├── Manual complete.pdf    # Authoritative PDF
│   └── Manual complete.txt    # Extracted text source
├── models/
│   └── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
├── packages/
│   ├── circuit-core/          # Circuit IR & topology validation
│   ├── digital-engine/        # Deterministic Boolean logic engine
│   └── simulation-core/       # Numerical solvers
├── runtime/
│   ├── llama/
│   │   └── koboldcpp.exe      # Portable llama.cpp Windows runner
│   └── server.py              # Offline FastAPI local core
├── scripts/
│   └── ingest_manual.py       # Ingestion & SQLite FTS5 builder
├── tests/
│   └── golden_suite.py        # Automated golden test suite
└── start.bat                  # One-click portable launcher
```

---

## Running the Application

### Quick Start (USB Plug & Play)
Double-click `start.bat` on the root of the USB drive:
```bat
start.bat
```
This automatically:
1. Verifies the SQLite FTS5 database (auto-builds if missing).
2. Starts the local core server on `127.0.0.1:8000`.
3. Opens the desktop application.

### Running Golden Tests
```bash
python tests/golden_suite.py
```
Validates all 14 experiments, SQLite FTS5 queries, Boolean gate truth tables, Half/Full adders, and NAND implementations.

---
*SIMLAB AI · Autonomous Offline Simulation Lab Copilot*
