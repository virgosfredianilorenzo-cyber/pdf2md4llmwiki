"""
app.py — Serveur FastAPI local PDF2LLMWiki
Lance avec : python app.py
Puis ouvre  : http://localhost:8000
"""
from __future__ import annotations
import asyncio
import json
import logging
import secrets
import tempfile
import threading
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from extractor import extract
from llm_client import check_ollama_running, chunk_for_rag, format_raw, list_models, pull_model_stream, structure_document
from formatter import process_markdown, save_markdown


# --- Chargement config ---
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

_http_basic = HTTPBasic(auto_error=False)

def _check_auth(credentials: HTTPBasicCredentials = Depends(_http_basic)) -> None:
    cfg_user = CONFIG.get("auth_username")
    cfg_pass = CONFIG.get("auth_password")
    if not cfg_user or not cfg_pass:
        return
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Basic"},
        )
    ok_user = secrets.compare_digest(credentials.username.encode(), str(cfg_user).encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), str(cfg_pass).encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )

app = FastAPI(title="PDF2LLMWiki", version="1.0.0", dependencies=[Depends(_check_auth)])

# Sert les fichiers statiques (interface navigateur)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Sert l'interface principale."""
    html_path = static_dir / "index.html"
    return HTMLResponse(
        content=html_path.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/api/status")
async def status():
    """Vérifie qu'Ollama est disponible et liste les modèles."""
    ok, info = check_ollama_running()
    return {
        "ollama": ok,
        "models": info,
        "model_list": list_models(),
        "current_model": CONFIG.get("model"),
        "output_dir": CONFIG.get("output_dir"),
        "vault_path": CONFIG.get("vault_path"),
    }


@app.post("/api/convert")
async def convert(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(None),
    language: str = Form(None),
    max_tags: int = Form(None),
    add_chunks: bool = Form(False),
    mode: str = Form("detailed"),
):
    """
    Endpoint principal :
    1. Reçoit le PDF
    2. Extrait le texte et la structure
    3. Appelle Ollama pour structuration
    4. Retourne le Markdown + infos
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis")

    # Paramètres avec fallback config
    model = model or CONFIG.get("model", "qwen2.5:7b")
    language = language or CONFIG.get("language", "fr")
    max_tags = max_tags or CONFIG.get("max_tags", 8)
    chunk_size = CONFIG.get("chunk_size", 400)
    output_dir = CONFIG.get("output_dir", "./output")
    vault_path = CONFIG.get("vault_path")

    # Sauvegarde temporaire du PDF uploadé
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Étape 1 : Extraction
        pdf_doc = extract(tmp_path)

        # Étape 2 : Structuration
        if mode == "raw":
            raw_md = format_raw(pdf_doc, file.filename)
            model = "— (mode brut)"
        else:
            llm_task = asyncio.create_task(
                asyncio.to_thread(
                    structure_document,
                    pdf_doc,
                    model=model,
                    language=language,
                    max_tags=max_tags,
                    temperature=CONFIG.get("temperature", 0.2),
                    timeout=CONFIG.get("ollama_timeout", 120),
                )
            )
            while not llm_task.done():
                if await request.is_disconnected():
                    llm_task.cancel()
                    raise HTTPException(status_code=499, detail="Annulé par le client")
                await asyncio.sleep(0.5)
            raw_md = llm_task.result()

        # Étape 3 : Post-traitement
        final_md = process_markdown(raw_md, file.filename)

        # Étape 4 : Sauvegarde
        save_info = save_markdown(
            final_md,
            pdf_filename=file.filename,
            output_dir=output_dir,
            vault_path=vault_path,
        )

        # Chunks RAG optionnels
        chunks = []
        if add_chunks:
            chunks = chunk_for_rag(final_md, chunk_size=chunk_size)

        return JSONResponse({
            "success": True,
            "filename": save_info["filename"],
            "output_path": save_info["output_path"],
            "vault_path": save_info["vault_path"],
            "markdown": final_md,
            "model_used": model,
            "mode": mode,
            "stats": {
                "pages": pdf_doc.pages,
                "sections_extracted": len(pdf_doc.sections),
                "md_chars": save_info["chars"],
                "md_lines": save_info["lines"],
                "chunks": len(chunks),
            },
            "chunks": chunks,
        })

    except Exception as e:
        logging.exception("Erreur lors de la conversion")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/pull")
async def pull_model(model: str = Form(...)):
    """Télécharge un modèle Ollama et streame la progression (SSE)."""
    loop = asyncio.get_event_loop()

    async def _generate():
        q: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for d in pull_model_stream(model):
                    asyncio.run_coroutine_threadsafe(q.put(d), loop)
                asyncio.run_coroutine_threadsafe(q.put({"done": True}), loop)
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(q.put({"error": str(exc)}), loop)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            item = await q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("done") or item.get("error"):
                break

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.get("/api/download/{filename}")
async def download(filename: str):
    """Télécharge un fichier MD généré."""
    output_dir = Path(CONFIG.get("output_dir", "./output")).resolve()
    file_path = (output_dir / filename).resolve()
    if not str(file_path).startswith(str(output_dir) + "/"):
        raise HTTPException(status_code=400, detail="Accès refusé")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(
        str(file_path),
        media_type="text/markdown",
        filename=file_path.name,
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", CONFIG.get("port", 8000)))
    print(f"\n  PDF2LLMWiki — http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
