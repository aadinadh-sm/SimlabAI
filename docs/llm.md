# SIMLAB AI: Local LLM Engine Architecture

## Model Overview
- **Model**: `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`
- **Parameter Count**: 8.03 Billion parameters
- **Quantization**: 4-bit medium K-quant (`Q4_K_M`)
- **Memory Footprint**: ~4.58 GB RAM / VRAM
- **Inference Server**: `koboldcpp.exe` (portable llama.cpp distribution)

## Orchestration & Streaming Pipeline
1. When launched, `runtime/server.py` communicates with `http://127.0.0.1:5001/v1/chat/completions`.
2. The user's query triggers a retrieval step against SQLite FTS5.
3. Relevant manual excerpts, page citations, and experiment metadata are bound into the system prompt.
4. Response tokens stream via Server-Sent Events (SSE) directly to the desktop frontend.

## Hardware Adaptation Profiles
- **LOW PROFILE**:
  - Arguments: `--threads 4 --gpulayers 0 --contextsize 4096`
  - RAM requirement: 8 GB
  - Designed for CPU-only laptops and older desktops.
- **BALANCED PROFILE**:
  - Arguments: `--threads 6 --gpulayers 16 --contextsize 4096`
  - RAM requirement: 16 GB with moderate GPU VRAM (4 GB+).
- **PERFORMANCE PROFILE**:
  - Arguments: `--threads 8 --gpulayers 33 --contextsize 8192`
  - Offloads all 33 layers into VRAM for instant token generation.
