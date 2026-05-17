"""
app.py — Serveur FastAPI local PDF2LLMWiki
Lance avec : python app.py
Puis ouvre  : http://localhost:8000
"""
from __future__ import annotations
import asyncio
import json
import tempfile
from pathlib import Path
import yaml
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from extractor import extract
from llm_client import check_ollama_running, chunk_for_rag, structure_document
from formatter import process_markdown, save_markdown


# --- Chargement config ---
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

app = FastAPI(title="PDF2LLMWiki", version="1.0.0")

# Sert les fichiers statiques (interface navigateur)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Sert l'interface principale."""
    html_path = static_dir / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/status")
async def status():
    """Vérifie qu'Ollama est disponible et liste les modèles."""
    ok, info = check_ollama_running()
    return {
        "ollama": ok,
        "models": info,
        "current_model": CONFIG.get("model"),
        "output_dir": CONFIG.get("output_dir"),
        "vault_path": CONFIG.get("vault_path"),
    }


@app.post("/api/convert")
async def convert(
    file: UploadFile = File(...),
    model: str = Form(None),
    language: str = Form(None),
    max_tags: int = Form(None),
    add_chunks: bool = Form(False),
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

        # Étape 2 : Structuration LLM
        raw_md = structure_document(
            pdf_doc,
            model=model,
            language=language,
            max_tags=max_tags,
            temperature=CONFIG.get("temperature", 0.2),
            timeout=CONFIG.get("ollama_timeout", 120),
        )

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
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/download/{filename}")
async def download(filename: str):
    """Télécharge un fichier MD généré."""
    output_dir = Path(CONFIG.get("output_dir", "./output"))
    file_path = output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(
        str(file_path),
        media_type="text/markdown",
        filename=filename,
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", CONFIG.get("port", 8000)))
    print(f"\n  PDF2LLMWiki — http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
