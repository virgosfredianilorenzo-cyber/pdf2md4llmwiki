"""
formatter.py — Post-traitement du Markdown et écriture dans le vault.
Garantit la conformité frontmatter + wikilinks + nommage Obsidian.
"""
from __future__ import annotations
import re
import shutil
from datetime import datetime
from pathlib import Path
import frontmatter  # python-frontmatter


def sanitize_filename(name: str) -> str:
    """Transforme un titre en nom de fichier Obsidian-compatible."""
    name = re.sub(r"[^\w\s\-àâäéèêëîïôùûüç]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:80] or "document"


def ensure_frontmatter(md_text: str, pdf_filename: str) -> str:
    """
    S'assure que le frontmatter YAML est présent et complet.
    Complète les champs manquants avec des valeurs par défaut.
    """
    try:
        post = frontmatter.loads(md_text)
    except Exception:
        post = frontmatter.Post(md_text)

    meta = post.metadata

    # Valeurs par défaut si le LLM a oublié certains champs
    meta.setdefault("title", Path(pdf_filename).stem)
    meta.setdefault("source", pdf_filename)
    meta.setdefault("date_extraction", datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    meta.setdefault("tags", [])
    meta.setdefault("resume_court", "")

    # Normalise les tags : minuscules, sans espaces
    if isinstance(meta.get("tags"), str):
        meta["tags"] = [t.strip() for t in meta["tags"].split(",")]
    meta["tags"] = [
        re.sub(r"\s+", "-", str(t).lower().strip())
        for t in meta["tags"]
        if t
    ]

    post.metadata = meta
    return frontmatter.dumps(post)


def fix_wikilinks(md_text: str) -> str:
    """
    Vérifie que les wikilinks [[concept]] ne contiennent pas
    de caractères invalides pour Obsidian.
    """
    def clean_link(m: re.Match) -> str:
        inner = m.group(1).strip()
        inner = re.sub(r"[#\[\]\|\\\/]", "", inner)
        return f"[[{inner}]]"
    return re.sub(r"\[\[([^\]]+)\]\]", clean_link, md_text)


def save_markdown(
    md_text: str,
    pdf_filename: str,
    output_dir: str | Path,
    vault_path: str | Path | None = None,
) -> dict:
    """
    Sauvegarde le fichier .md dans output_dir et,
    si vault_path est défini, le copie dans le vault Obsidian.
    Retourne un dict avec les chemins et infos.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Nom du fichier à partir du titre dans le frontmatter
    try:
        post = frontmatter.loads(md_text)
        title = post.metadata.get("title") or Path(pdf_filename).stem
    except Exception:
        title = Path(pdf_filename).stem

    filename = sanitize_filename(title) + ".md"
    output_path = output_dir / filename

    output_path.write_text(md_text, encoding="utf-8")

    result = {
        "filename": filename,
        "output_path": str(output_path),
        "vault_path": None,
        "chars": len(md_text),
        "lines": md_text.count("\n"),
    }

    # Copie vers le vault si configuré
    if vault_path:
        vault = Path(vault_path).expanduser()
        if vault.exists():
            dest = vault / filename
            shutil.copy2(output_path, dest)
            result["vault_path"] = str(dest)

    return result


def process_markdown(md_text: str, pdf_filename: str) -> str:
    """Pipeline complet de post-traitement."""
    md_text = ensure_frontmatter(md_text, pdf_filename)
    md_text = fix_wikilinks(md_text)
    return md_text
