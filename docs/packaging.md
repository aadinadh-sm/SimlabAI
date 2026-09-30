# SIMLAB AI: Portable USB Packaging Specification

## Zero-Dependency USB Distribution
The target distribution package runs directly off any USB flash drive formatted as exFAT or NTFS on Windows 10/11:

```
[USB Drive Root]:\
└── SIMLAB_AI/
    ├── SimLabAI.exe           # Standalone native desktop executable
    ├── start.bat              # One-click shell launcher
    ├── SimLabAI.bat           # Direct script runner
    ├── models/
    │   └── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
    ├── knowledge/
    │   ├── manual_db.sqlite   # Pre-built SQLite FTS5 database
    │   ├── experiments/       # 14 Experiment JSON definitions
    │   ├── viva/              # Viva question banks
    │   └── images/            # Scanned circuit diagram pages 1-42
    ├── runtime/
    │   ├── llama/
    │   │   └── koboldcpp.exe  # Standalone llama.cpp engine
    │   └── server.py          # Core local API
    └── workspace/
        └── logs/              # Local runtime logs
```

## Runtime Principles
1. **Dynamic Path Anchoring**: `APP_ROOT` is resolved from `%~dp0` (batch) or `os.path.dirname(__file__)` (Python/executable).
2. **Zero Hardcoded Paths**: No references to `C:\`, `%APPDATA%`, or user profile directories.
3. **No Target PC Prerequisites**: The target machine does NOT require Node.js, Python, Git, or administrative privileges.
