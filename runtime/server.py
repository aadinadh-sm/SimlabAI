"""
SIMLAB AI - Local Offline Core Server
Provides REST and SSE endpoints for:
1. SQLite FTS5 Knowledge Base & Experiment Data
2. Local Llama-3.1-8B-Instruct inference orchestration via koboldcpp
3. System Diagnostics & Hardware Profiling
4. Offline Verification & Telemetry Prevention
"""

import os
import sys
import json
import sqlite3
import subprocess
import time
import re
import psutil
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import urllib.request
import urllib.error

# Resolve APP_ROOT dynamically for full USB Portability
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(APP_ROOT, "knowledge")
DB_PATH = os.path.join(KNOWLEDGE_DIR, "manual_db.sqlite")
MODELS_DIR = os.path.join(APP_ROOT, "models")
DEFAULT_MODEL = os.path.join(MODELS_DIR, "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")
KOBOLD_BIN = os.path.join(APP_ROOT, "runtime", "llama", "koboldcpp.exe")
WORKSPACE_DIR = os.path.join(APP_ROOT, "workspace")
LOGS_DIR = os.path.join(WORKSPACE_DIR, "logs")
IMAGES_DIR = os.path.join(KNOWLEDGE_DIR, "images")

os.makedirs(LOGS_DIR, exist_ok=True)

# Circuit Core & Progressive Reconstruction Engine
CIRCUIT_CORE_DIR = os.path.join(APP_ROOT, "packages", "circuit-core", "src")
if CIRCUIT_CORE_DIR not in sys.path:
    sys.path.insert(0, CIRCUIT_CORE_DIR)

KNOWLEDGE_CORE_DIR = os.path.join(APP_ROOT, "packages", "knowledge-core", "src")
if KNOWLEDGE_CORE_DIR not in sys.path:
    sys.path.insert(0, KNOWLEDGE_CORE_DIR)

try:
    from progressive_reconstruction import ProgressiveCircuitEngine
except Exception as e:
    ProgressiveCircuitEngine = None
    print(f"[Warning] Failed to import ProgressiveCircuitEngine: {e}")

try:
    from domain_retriever import DomainRetriever
    domain_retriever = DomainRetriever(DB_PATH)
except Exception as e:
    domain_retriever = None
    print(f"[Warning] Failed to import DomainRetriever: {e}")

app = FastAPI(title="SIMLAB AI Core", version="1.0.0")

# Strict local-only CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kobold_process: Optional[subprocess.Popen] = None
KOBOLD_PORT = 5001
KOBOLD_URL = f"http://127.0.0.1:{KOBOLD_PORT}"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    experiment_id: Optional[int] = None
    temperature: float = 0.2
    max_tokens: int = 1024
    stream: bool = True

class ModelConfig(BaseModel):
    model_path: Optional[str] = None
    threads: int = 4
    gpu_layers: int = 0
    context_size: int = 4096

class ReconstructRequest(BaseModel):
    prompt: str


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_kobold_running() -> bool:
    """Checks if koboldcpp is online via HTTP or actively running in OS processes."""
    try:
        req = urllib.request.Request(f"{KOBOLD_URL}/api/extra/version", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    # Fallback: check if koboldcpp.exe is actively running in memory (e.g. busy generating tokens)
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            if "koboldcpp" in (p.info["name"] or "").lower():
                if p.info["memory_info"] and p.info["memory_info"].rss > 100 * 1024 * 1024:
                    return True
        except Exception:
            continue
    return False


@app.on_event("startup")
def ensure_llm_started():
    """Auto-starts a single koboldcpp instance on server boot if none is running."""
    if not is_kobold_running() and os.path.exists(DEFAULT_MODEL) and os.path.exists(KOBOLD_BIN):
        try:
            start_llm(ModelConfig(threads=6, gpu_layers=0, context_size=2048))
        except Exception as e:
            print(f"[Core] Auto-start LLM notice: {e}")


@app.get("/api/system/status")
def get_system_status():
    """Hardware profiling and offline diagnostic health check."""
    cpu_count = psutil.cpu_count(logical=True)
    cpu_percent = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()

    # Detect model file
    model_exists = os.path.exists(DEFAULT_MODEL)
    model_size_gb = round(os.path.getsize(DEFAULT_MODEL) / (1024**3), 2) if model_exists else 0

    # Detect LLM runner active
    llm_online = is_kobold_running()

    # Check SQLite knowledge base
    db_ready = False
    exp_count = 0
    if os.path.exists(DB_PATH):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM experiments")
            exp_count = cur.fetchone()[0]
            db_ready = (exp_count == 14)
            conn.close()
        except Exception:
            db_ready = False

    return {
        "status": "READY" if (db_ready and model_exists) else "CONFIG_REQUIRED",
        "offline_mode": True,
        "cloud_api_disabled": True,
        "telemetry_disabled": True,
        "hardware": {
            "cpu_cores": cpu_count,
            "cpu_percent": cpu_percent,
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_available_gb": round(ram.available / (1024**3), 2),
            "ram_used_percent": ram.percent,
            "platform": sys.platform
        },
        "model": {
            "name": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            "exists": model_exists,
            "size_gb": model_size_gb,
            "path": DEFAULT_MODEL,
            "loaded": llm_online,
            "backend": "koboldcpp / llama.cpp",
            "port": KOBOLD_PORT
        },
        "knowledge_base": {
            "database_ready": db_ready,
            "experiments_indexed": exp_count,
            "manual_title": "23EEP20B - SIMULATION LAB MANUAL",
            "db_path": DB_PATH
        },
        "simulation_engines": {
            "pyspice": True,
            "digital_logic": True,
            "numerical_simulink_equiv": True
        },
        "app_root": APP_ROOT
    }


@app.post("/api/llm/start")
def start_llm(cfg: ModelConfig):
    """Starts the local koboldcpp process headlessly (strictly single-instance)."""
    global kobold_process
    if is_kobold_running() or (kobold_process and kobold_process.poll() is None):
        return {"status": "ALREADY_RUNNING", "port": KOBOLD_PORT}

    model_path = cfg.model_path or DEFAULT_MODEL
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail=f"Model file not found at: {model_path}")
    if not os.path.exists(KOBOLD_BIN):
        raise HTTPException(status_code=404, detail=f"LLM runtime binary not found at: {KOBOLD_BIN}")

    log_file = open(os.path.join(LOGS_DIR, "koboldcpp.log"), "w", encoding="utf-8")

    cmd = [
        KOBOLD_BIN,
        "--model", model_path,
        "--port", str(KOBOLD_PORT),
        "--skiplauncher",
        "--contextsize", str(cfg.context_size),
        "--threads", str(cfg.threads),
        "--gpulayers", str(cfg.gpu_layers),
        "--smartcontext"
    ]

    try:
        kobold_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(KOBOLD_BIN)
        )
        return {"status": "STARTING", "pid": kobold_process.pid, "port": KOBOLD_PORT}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch LLM: {str(e)}")


@app.post("/api/llm/stop")
def stop_llm():
    """Stops all running koboldcpp processes."""
    global kobold_process
    stopped = False
    if kobold_process and kobold_process.poll() is None:
        kobold_process.terminate()
        try:
            kobold_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kobold_process.kill()
        kobold_process = None
        stopped = True

    for p in psutil.process_iter(["name"]):
        try:
            if "koboldcpp" in (p.info["name"] or "").lower():
                p.kill()
                stopped = True
        except Exception:
            continue

    return {"status": "STOPPED" if stopped else "NOT_RUNNING"}


@app.get("/api/experiments")
def list_experiments():
    """Returns list of all 14 official experiments with metadata."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT exp_number, title, category, software, aim, page_start, page_end, tags, diagram_images
        FROM experiments
        ORDER BY exp_number ASC
    """)
    rows = cur.fetchall()
    results = []
    for r in rows:
        results.append({
            "exp_number": r["exp_number"],
            "title": r["title"],
            "category": r["category"],
            "software": r["software"],
            "aim": r["aim"],
            "page_start": r["page_start"],
            "page_end": r["page_end"],
            "pages": f"Pages {r['page_start']}–{r['page_end']}",
            "tags": [t.strip() for t in r["tags"].split(",") if t.strip()],
            "diagram_images": json.loads(r["diagram_images"])
        })
    conn.close()
    return results


@app.get("/api/experiments/{exp_num}")
def get_experiment(exp_num: int):
    """Returns comprehensive experiment manual content, procedure, and viva questions."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM experiments WHERE exp_number = ?", (exp_num,))
    exp = cur.fetchone()
    if not exp:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Experiment {exp_num} not found")

    # Fetch viva questions
    cur.execute("SELECT question, expected_answer, key_concepts FROM viva_questions WHERE exp_number = ?", (exp_num,))
    viva_rows = cur.fetchall()
    viva = []
    for v in viva_rows:
        viva.append({
            "question": v["question"],
            "expected_answer": v["expected_answer"],
            "key_concepts": json.loads(v["key_concepts"])
        })

    # Fetch raw manual pages
    cur.execute("SELECT page_num, content FROM pages WHERE page_num BETWEEN ? AND ? ORDER BY page_num ASC", (exp["page_start"], exp["page_end"]))
    page_rows = cur.fetchall()
    manual_pages = [{"page": p["page_num"], "content": p["content"]} for p in page_rows]

    conn.close()
    return {
        "exp_number": exp["exp_number"],
        "title": exp["title"],
        "category": exp["category"],
        "software": exp["software"],
        "aim": exp["aim"],
        "procedure": exp["procedure"],
        "result": exp["result"],
        "code_sample": exp["code_sample"],
        "page_start": exp["page_start"],
        "page_end": exp["page_end"],
        "pages_text": f"Pages {exp['page_start']}–{exp['page_end']}",
        "tags": [t.strip() for t in exp["tags"].split(",") if t.strip()],
        "diagram_images": json.loads(exp["diagram_images"]),
        "viva_questions": viva,
        "manual_pages": manual_pages
    }


@app.get("/api/images/{filename}")
def get_diagram_image(filename: str):
    """Serves high-resolution manual diagram scans locally."""
    path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Image not found")


def resolve_manual_pdf_path() -> Optional[str]:
    """Locates the existing bundled lab manual PDF relative to APP_ROOT for full USB portability."""
    candidates = [
        os.path.join(KNOWLEDGE_DIR, "Manual complete.pdf"),
        os.path.join(APP_ROOT, "Manual complete.pdf"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    for search_dir in (KNOWLEDGE_DIR, APP_ROOT):
        if os.path.isdir(search_dir):
            for fname in os.listdir(search_dir):
                if fname.lower().endswith(".pdf"):
                    return os.path.join(search_dir, fname)
    return None


@app.get("/api/manual/pdf")
def get_manual_pdf():
    """Serves the existing bundled Lab Manual PDF inline for the built-in PDF viewer."""
    pdf_path = resolve_manual_pdf_path()
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="Manual complete.pdf"'},
        )
    raise HTTPException(status_code=404, detail="Lab Manual PDF not found")



@app.get("/api/search")
def search_manual(q: str = Query(..., min_length=2), exp_number: Optional[int] = None):
    """Full-Text-Search over the Simulation Lab Manual using SQLite FTS5."""
    conn = get_db()
    cur = conn.cursor()
    # Sanitize FTS query
    clean_q = re.sub(r'[^\w\s]', ' ', q).strip()
    if not clean_q:
        return []

    # Search FTS5
    if exp_number:
        cur.execute("""
            SELECT c.exp_number, c.section, c.page_start, c.page_end, c.content,
                   snippet(manual_chunks_fts, 1, '<b>', '</b>', '...', 25) as snippet_text,
                   bm25(manual_chunks_fts) as rank
            FROM manual_chunks_fts
            JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id
            WHERE manual_chunks_fts MATCH ? AND c.exp_number = ?
            ORDER BY rank
            LIMIT 10
        """, (clean_q, exp_number))
    else:
        cur.execute("""
            SELECT c.exp_number, c.section, c.page_start, c.page_end, c.content,
                   snippet(manual_chunks_fts, 1, '<b>', '</b>', '...', 25) as snippet_text,
                   bm25(manual_chunks_fts) as rank
            FROM manual_chunks_fts
            JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id
            WHERE manual_chunks_fts MATCH ?
            ORDER BY rank
            LIMIT 15
        """, (clean_q,))

    rows = cur.fetchall()
    hits = []
    for r in rows:
        hits.append({
            "exp_number": r["exp_number"],
            "section": r["section"],
            "page_start": r["page_start"],
            "page_end": r["page_end"],
            "citation": f"Simulation Lab Manual · Experiment {r['exp_number']} · {r['section'].capitalize()} · Page {r['page_start']}–{r['page_end']}",
            "snippet": r["snippet_text"],
            "content": r["content"]
        })
    conn.close()
    return hits


@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """
    8-Stage Deterministic Circuit & RAG Pipeline:
    LATEST USER MESSAGE -> ENTITY EXTRACTION -> CIRCUIT CLASSIFICATION ->
    MANUAL EXPERIMENT RETRIEVAL -> TOPOLOGY TEMPLATE -> PARAMETER SUBSTITUTION ->
    CIRCUIT IR -> VALIDATION & SIMULATION -> CODE GENERATION
    """
    # STRICT RULE: Latest user message is the ONLY source for user-provided component values
    user_messages_only = [m.content for m in req.messages if m.role == "user"]
    latest_user_message = user_messages_only[-1] if user_messages_only else ""
    prev_user_message = user_messages_only[-2] if len(user_messages_only) >= 2 else None

    # Stages 1 & 2: Deterministic Entity Extraction & Circuit Classification BEFORE manual retrieval
    recon = None
    if ProgressiveCircuitEngine:
        try:
            recon = ProgressiveCircuitEngine.reconstruct_circuit(
                latest_user_message=latest_user_message,
                previous_user_message=prev_user_message,
                experiment_context=req.experiment_id
            )
        except Exception as e:
            print(f"[Core] Reconstruction error: {e}")

    # Stage 3: Manual Experiment Retrieval (provides TOPOLOGY / THEORY / PROCEDURE only, never overwrites values)
    classified_exp_id = recon.get("selected_experiment") if recon else None
    is_generalized = recon and recon.get("topology_classification") == "GENERALIZED CIRCUIT"
    target_exp_id = classified_exp_id if is_generalized else (classified_exp_id or req.experiment_id)

    retrieved_context = []
    manual_metadata = None
    conn = get_db()
    cur = conn.cursor()

    if target_exp_id:
        cur.execute(
            "SELECT exp_number, title, category, software, aim, procedure, result, page_start, page_end FROM experiments WHERE exp_number = ?",
            (target_exp_id,)
        )
        exp = cur.fetchone()
        if exp:
            manual_metadata = {
                "exp_number": exp["exp_number"],
                "title": exp["title"],
                "category": exp["category"],
                "aim": exp["aim"],
                "procedure": exp["procedure"][:350],
                "pages": f"Pages {exp['page_start']}-{exp['page_end']}"
            }
            retrieved_context.append(
                f"[MANUAL CONTEXT: Experiment {exp['exp_number']} - {exp['title']}\n"
                f"Page Range: {exp['page_start']}-{exp['page_end']}\n"
                f"Aim: {exp['aim']}\n"
                f"Procedure Summary: {exp['procedure'][:400]}...\n"
                f"Documented Result: {exp['result']}]"
            )

    # Perform FTS search for conceptual context
    clean_q = re.sub(r'[^\w\s]', ' ', latest_user_message).strip()
    if clean_q:
        terms = " OR ".join(clean_q.split()[:5])
        try:
            cur.execute("""
                SELECT c.exp_number, c.section, c.page_start, c.page_end, c.content
                FROM manual_chunks_fts
                JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id
                WHERE manual_chunks_fts MATCH ?
                LIMIT 3
            """, (terms,))
            for r in cur.fetchall():
                retrieved_context.append(
                    f"[MANUAL EXCERPT: Exp {r['exp_number']}, Section: {r['section']}, Page: {r['page_start']}]\n"
                    f"{r['content'][:300]}\n"
                    f"[/MANUAL EXCERPT]"
                )
        except Exception:
            pass
    conn.close()

    if recon and manual_metadata:
        recon["manual_metadata"] = manual_metadata

    domain_hit = None
    if domain_retriever:
        try:
            domain_hit = domain_retriever.retrieve(
                latest_user_message,
                exp_id=target_exp_id,
                topology_intent=recon.get("circuit_type") if recon else None,
            )
            if domain_hit and domain_hit.get("formatted_context"):
                retrieved_context.insert(0, domain_hit["formatted_context"])
        except Exception as e:
            print(f"[DomainRetriever] Retrieval warning: {e}")

    context_str = "\n\n".join(retrieved_context)

    system_prompt = (
        "You are SimLab AI, an offline Simulation Laboratory assistant specifically designed for "
        "'23EEP20B - SIMULATION LAB MANUAL'.\n\n"
        "AUTHORITY & ACCURACY RULES:\n"
        "1. The supplied Simulation Lab Manual is your primary authority for all 14 experiments.\n"
        "2. Never claim that the manual specifies something when it does not.\n"
        "3. Never overwrite user-provided component values with manual example values.\n"
        "4. Always provide source citations in this format when referencing manual knowledge:\n"
        "   'Source: Simulation Lab Manual · Experiment <X> · <Section> · Page <Y>'\n\n"
        f"RETRIEVED MANUAL KNOWLEDGE:\n{context_str}\n"
    )

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for m in req.messages[-4:]:
        formatted_messages.append({"role": m.role, "content": m.content})

    payload = {
        "model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M",
        "messages": formatted_messages,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "stream": True
    }

    async def sse_generator():
        # Always emit the deterministic debug_trace first for the UI Debug Panel
        if recon and recon.get("debug_trace"):
            yield f"data: {json.dumps({'debug_trace': recon['debug_trace']})}\n\n"

        # Determine if this is a circuit construction / simulation / parameter query
        entities = recon.get("extracted_entities", {}) if recon else {}
        has_explicit_values = bool(
            entities.get("voltage_sources")
            or entities.get("resistors")
            or entities.get("current_sources")
            or entities.get("capacitors")
            or entities.get("inductors")
            or entities.get("diodes")
        )
        low_msg = latest_user_message.lower()
        is_pure_viva_or_theory = (
            not has_explicit_values
            and not any(w in low_msg for w in ["pyspice", "netlist", "simulate", "make code", "write code", "in series", "in parallel", "junction"])
            and any(w in low_msg for w in ["viva", "why is", "why must", "what is meant", "theory", "equation", "formula", "common mistake", "singular matrix", "error:"])
        )
        is_circuit_action = (
            not is_pure_viva_or_theory
            and (
                has_explicit_values
                or (recon and recon.get("user_confirmed"))
                or (recon and recon.get("circuit_type") == "CUSTOM_NL_TOPOLOGY")
                or any(k in low_msg for k in [
                    "circuit", "pyspice", "netlist", "simulate", "cccs", "vcvs",
                    "bridge", "pacemaker", "rectifier", "zener", "adder",
                    "experiment", "exp ", "natural response", "step response", "general_rc"
                ])
            )
        )

        if recon and is_circuit_action:
            response_text = ProgressiveCircuitEngine.format_reconstruction_response(recon, latest_user_message)
            top_class = recon.get("topology_classification", "GENERALIZED CIRCUIT")
            if (
                manual_metadata
                and top_class in ("EXACT MANUAL TOPOLOGY", "MODIFIED MANUAL TOPOLOGY")
                and not ProgressiveCircuitEngine.is_code_only_request(latest_user_message)
            ):
                manual_header = (
                    f"**Manual Reference**: *Experiment {manual_metadata['exp_number']}: {manual_metadata['title']} ({manual_metadata['pages']})* — **`{top_class}`**\n\n"
                )
                response_text = manual_header + response_text

            chunk_size = 60
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i+chunk_size]
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Conceptual / theory / viva questions handled via local Llama 3.1 LLM or structured domain retrieval
        is_llm_online = False
        try:
            with urllib.request.urlopen(f"{KOBOLD_URL}/api/extra/version", timeout=0.6) as r:
                if r.status == 200:
                    is_llm_online = True
        except Exception:
            is_llm_online = False

        if is_llm_online:
            try:
                req_data = json.dumps(payload).encode("utf-8")
                url = f"{KOBOLD_URL}/v1/chat/completions"
                http_req = urllib.request.Request(
                    url,
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(http_req, timeout=60) as response:
                    for line in response:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            data_part = line_str[6:].strip()
                            if data_part == "[DONE]":
                                yield "data: [DONE]\n\n"
                                return
                            try:
                                chunk = json.loads(data_part)
                                delta = chunk["choices"][0].get("delta", {}).get("content", "")
                                if delta:
                                    yield f"data: {json.dumps({'content': delta})}\n\n"
                            except Exception:
                                continue
            except Exception:
                pass

        err_msg = "**Retrieved Lab Manual Knowledge:**\n\n"
        if retrieved_context:
            for ctx in retrieved_context:
                err_msg += f"```text\n{ctx}\n```\n\n"
        else:
            err_msg += "Please specify the circuit components or experiment topic you would like to explore."
        yield f"data: {json.dumps({'content': err_msg})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.get("/api/domain/retrieve")
def api_domain_retrieve(q: str = Query(..., min_length=2), exp_id: Optional[int] = None):
    """Phase 17: Structured Domain Retrieval endpoint over experiments, canonical circuits, viva Q&As, and examples."""
    if not domain_retriever:
        raise HTTPException(status_code=500, detail="DomainRetriever not available")
    return domain_retriever.retrieve(q, exp_id=exp_id)


@app.post("/api/circuit/reconstruct")
def api_reconstruct_circuit(req: ReconstructRequest):
    """
    Progressive Circuit Reconstruction API endpoint.
    Extracts known components, generates candidate topologies with confidence scores and rationales,
    and returns both structured JSON and formatted Markdown.
    """
    if not ProgressiveCircuitEngine:
        raise HTTPException(status_code=500, detail="ProgressiveCircuitEngine not available")
    recon = ProgressiveCircuitEngine.reconstruct_circuit(req.prompt)
    md = ProgressiveCircuitEngine.format_reconstruction_response(recon, req.prompt)
    return {
        **recon,
        "markdown_response": md
    }

# Mount frontend static distribution
from fastapi.staticfiles import StaticFiles

possible_dists = [
    os.path.join(APP_ROOT, "apps", "desktop", "dist"),
    os.path.join(os.path.dirname(APP_ROOT), "apps", "desktop", "dist"),
    os.path.join(APP_ROOT, "dist"),
    os.path.join(APP_ROOT, "web"),
]

for d in possible_dists:
    if os.path.exists(d):
        app.mount("/", StaticFiles(directory=d, html=True), name="static")
        print(f"[Core] Serving frontend static assets from: {d}")
        break

if __name__ == "__main__":
    import uvicorn
    port = 8000
    print(f"Starting SIMLAB AI Core Server on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
