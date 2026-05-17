"""
extractor.py — Extraction structurée depuis PDF
Utilise pymupdf pour la hiérarchie titres/corps
et pdfplumber pour les tableaux complexes.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import fitz  # pymupdf
import pdfplumber


@dataclass
class PDFSection:
    level: int        # 1=H1, 2=H2, 3=H3, 0=paragraphe
    text: str
    page: int
    is_table: bool = False


@dataclass
class PDFDocument:
    title: str
    author: str
    subject: str
    pages: int
    sections: list[PDFSection] = field(default_factory=list)
    raw_text: str = ""


def _clean(text: str) -> str:
    """Supprime les espaces multiples et les lignes vides excédentaires."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _detect_level(span_size: float, sizes: list[float]) -> int:
    """
    Déduit le niveau de titre H1/H2/H3 à partir de la taille de police.
    Taille relative aux tailles détectées dans le document.
    """
    if not sizes:
        return 0
    sorted_sizes = sorted(set(sizes), reverse=True)
    if span_size >= sorted_sizes[0] * 0.95:
        return 1
    if len(sorted_sizes) > 1 and span_size >= sorted_sizes[1] * 0.95:
        return 2
    if len(sorted_sizes) > 2 and span_size >= sorted_sizes[2] * 0.95:
        return 3
    return 0


def extract(pdf_path: str | Path) -> PDFDocument:
    """Point d'entrée principal. Retourne un PDFDocument structuré."""
    pdf_path = Path(pdf_path)

    # --- Métadonnées ---
    doc_fitz = fitz.open(str(pdf_path))
    meta = doc_fitz.metadata or {}
    pdf_doc = PDFDocument(
        title=meta.get("title") or pdf_path.stem,
        author=meta.get("author") or "",
        subject=meta.get("subject") or "",
        pages=len(doc_fitz),
    )

    # --- Tailles de polices pour détecter les titres ---
    all_sizes: list[float] = []
    for page in doc_fitz:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("flags", 0) & 16 or span.get("size", 0) > 11:
                        all_sizes.append(round(span["size"], 1))

    # Garde les 4 tailles les plus fréquentes (titre candidats)
    from collections import Counter
    size_freq = Counter(all_sizes)
    top_sizes = [s for s, _ in size_freq.most_common(4)]

    # --- Extraction bloc par bloc ---
    raw_parts: list[str] = []
    for page_num, page in enumerate(doc_fitz, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_text = ""
                line_size = 0.0
                is_bold = False
                for span in line.get("spans", []):
                    t = _clean(span.get("text", ""))
                    if not t:
                        continue
                    line_text += t + " "
                    line_size = max(line_size, span.get("size", 0))
                    if span.get("flags", 0) & 16:
                        is_bold = True
                line_text = line_text.strip()
                if not line_text or len(line_text) < 2:
                    continue
                raw_parts.append(line_text)

                # Détermine le niveau
                level = _detect_level(line_size, top_sizes)
                if is_bold and level == 0 and len(line_text) < 120:
                    level = 3  # texte gras court → probable sous-titre
                pdf_doc.sections.append(
                    PDFSection(level=level, text=line_text, page=page_num)
                )

    doc_fitz.close()

    # --- Tableaux avec pdfplumber ---
    with pdfplumber.open(str(pdf_path)) as plumb:
        for page_num, page in enumerate(plumb.pages, start=1):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                md_table = _table_to_md(table)
                pdf_doc.sections.append(
                    PDFSection(level=0, text=md_table, page=page_num, is_table=True)
                )

    pdf_doc.raw_text = "\n".join(raw_parts)
    return pdf_doc


def _table_to_md(table: list[list[Optional[str]]]) -> str:
    """Convertit un tableau extrait par pdfplumber en Markdown."""
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(c or "").replace("\n", " ").strip() for c in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


def sections_to_text(sections: list[PDFSection], max_chars: int = 8000) -> str:
    """
    Sérialise les sections en texte brut pour le LLM.
    Respecte un budget de tokens (approximatif).
    """
    parts: list[str] = []
    total = 0
    for s in sections:
        prefix = {1: "# ", 2: "## ", 3: "### ", 0: ""}.get(s.level, "")
        chunk = prefix + s.text
        total += len(chunk)
        if total > max_chars:
            parts.append("...[tronqué pour respecter le contexte LLM]")
            break
        parts.append(chunk)
    return "\n\n".join(parts)
