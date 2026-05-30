# pdf2obsidiannoia Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer un dépôt GitHub autonome `pdf2obsidiannoia` — app web FastAPI (port 8001) qui convertit des PDF en Markdown Obsidian-compatible sans IA, via extraction structurelle + regex sémantiques.

**Architecture:** `extractor.py` (pymupdf + pdfplumber) → `converter.py` (4 passes : frontmatter, TOC, callouts, wikilinks) → `formatter.py` (assemblage + sauvegarde) → `app.py` (FastAPI) → `static/index.html` (UI drag & drop).

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, pymupdf, pdfplumber, pyyaml, pytest

---

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `app.py` | Serveur FastAPI — endpoints `/`, `/api/convert`, `/api/download/{filename}` |
| `extractor.py` | Extraction PDF → `PDFDocument` (sections, métadonnées, tableaux) |
| `callouts.py` | Détection regex callouts → `> [!TYPE]` Obsidian |
| `wikilinks.py` | Détection noms propres + phrases en gras → `[[wikilinks]]` |
| `converter.py` | Pipeline 4 passes : frontmatter → TOC → callouts → wikilinks |
| `formatter.py` | Assemblage `.md` final + sauvegarde vault |
| `config.yaml` | Configuration (port, output_dir, vault_path, etc.) |
| `requirements.txt` | Dépendances Python |
| `start.sh` | Script de démarrage (crée venv si absent) |
| `.gitignore` | Ignorer `.venv/`, `output/`, `__pycache__/` |
| `tests/__init__.py` | Rend `tests/` un package Python |
| `tests/test_extractor.py` | Tests des fonctions pures (pas de vrai PDF) |
| `tests/test_callouts.py` | Tests TDD callouts |
| `tests/test_wikilinks.py` | Tests TDD wikilinks |
| `tests/test_converter.py` | Tests TDD pipeline |
| `tests/test_formatter.py` | Tests TDD formatter |
| `static/index.html` | Interface web complète |

---

## Task 1: Scaffold du projet

**Files:**
- Create: `~/Documents/GitHub/pdf2obsidiannoia/` (nouveau dépôt)
- Create: `requirements.txt`, `config.yaml`, `start.sh`, `.gitignore`
- Create: `tests/__init__.py`, `static/`, `output/.gitkeep`

- [ ] **Step 1: Créer le répertoire et git init**

```bash
mkdir -p ~/Documents/GitHub/pdf2obsidiannoia
cd ~/Documents/GitHub/pdf2obsidiannoia
git init
mkdir -p tests static output
touch tests/__init__.py output/.gitkeep
```

- [ ] **Step 2: Créer `requirements.txt`**

```
fastapi
uvicorn[standard]
pymupdf
pdfplumber
pyyaml
pytest
```

- [ ] **Step 3: Créer `config.yaml`**

```yaml
port: 8001
output_dir: ./output
vault_path: null
language: fr
wikilinks: true
callouts: true
toc: true
```

- [ ] **Step 4: Créer `start.sh`**

```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -c "import sys; assert sys.version_info >= (3,11)" 2>/dev/null || {
    echo "Python 3.11+ requis"; exit 1
}

if [ ! -d ".venv" ]; then
    echo "Création de l'environnement virtuel…"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
    echo "Installation terminée."
fi

exec .venv/bin/python app.py
```

```bash
chmod +x start.sh
```

- [ ] **Step 5: Créer `.gitignore`**

```
.venv/
output/*.md
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
```

- [ ] **Step 6: Créer le venv et installer les dépendances**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -q
```

- [ ] **Step 7: Commit initial**

```bash
git add .
git commit -m "chore: scaffold pdf2obsidiannoia"
```

---

## Task 2: extractor.py

**Files:**
- Create: `extractor.py`
- Create: `tests/test_extractor.py`

- [ ] **Step 1: Écrire les tests (fonctions pures, pas de vrai PDF)**

Créer `tests/test_extractor.py` :

```python
from extractor import _clean, _detect_level, _table_to_md

def test_clean_multiple_spaces():
    assert _clean("hello   world") == "hello world"

def test_clean_strips():
    assert _clean("  hello  ") == "hello"

def test_detect_level_largest():
    assert _detect_level(18.0, [18.0, 14.0, 12.0]) == 1

def test_detect_level_second():
    assert _detect_level(14.0, [18.0, 14.0, 12.0]) == 2

def test_detect_level_third():
    assert _detect_level(12.0, [18.0, 14.0, 12.0]) == 3

def test_detect_level_body():
    assert _detect_level(10.0, [18.0, 14.0, 12.0]) == 0

def test_detect_level_empty_sizes():
    assert _detect_level(12.0, []) == 0

def test_table_to_md_basic():
    table = [["Col1", "Col2"], ["A", "B"]]
    result = _table_to_md(table)
    assert "| Col1 | Col2 |" in result
    assert "|---|---|" in result
    assert "| A | B |" in result

def test_table_to_md_empty():
    assert _table_to_md([]) == ""

def test_table_to_md_none_cells():
    table = [["A", None], ["B", "C"]]
    result = _table_to_md(table)
    assert "|" in result
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_extractor.py -v
```

Attendu : `ModuleNotFoundError: No module named 'extractor'`

- [ ] **Step 3: Créer `extractor.py`**

```python
from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import fitz
import pdfplumber


@dataclass
class PDFSection:
    level: int        # 1=H1, 2=H2, 3=H3, 0=paragraphe
    text: str
    page: int
    is_table: bool = False
    is_bold: bool = False


@dataclass
class PDFDocument:
    title: str
    author: str
    subject: str
    pages: int
    sections: list[PDFSection] = field(default_factory=list)
    raw_text: str = ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _detect_level(span_size: float, sizes: list[float]) -> int:
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


def _table_to_md(table: list[list[Optional[str]]]) -> str:
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(c or "").replace("\n", " ").strip() for c in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


def extract(pdf_path: str | Path) -> PDFDocument:
    pdf_path = Path(pdf_path)
    doc_fitz = fitz.open(str(pdf_path))
    meta = doc_fitz.metadata or {}
    pdf_doc = PDFDocument(
        title=meta.get("title") or pdf_path.stem,
        author=meta.get("author") or "",
        subject=meta.get("subject") or "",
        pages=len(doc_fitz),
    )

    all_sizes: list[float] = []
    for page in doc_fitz:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("flags", 0) & 16 or span.get("size", 0) > 11:
                        all_sizes.append(round(span["size"], 1))

    size_freq = Counter(all_sizes)
    top_sizes = [s for s, _ in size_freq.most_common(4)]

    raw_parts: list[str] = []
    for page_num, page in enumerate(doc_fitz, start=1):
        for block in page.get_text("dict")["blocks"]:
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
                level = _detect_level(line_size, top_sizes)
                if is_bold and level == 0 and len(line_text) < 120:
                    level = 3
                pdf_doc.sections.append(
                    PDFSection(level=level, text=line_text, page=page_num, is_bold=is_bold)
                )

    doc_fitz.close()

    with pdfplumber.open(str(pdf_path)) as plumb:
        for page_num, page in enumerate(plumb.pages, start=1):
            for table in page.extract_tables():
                if not table:
                    continue
                pdf_doc.sections.append(
                    PDFSection(level=0, text=_table_to_md(table), page=page_num, is_table=True)
                )

    pdf_doc.raw_text = "\n".join(raw_parts)
    return pdf_doc
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_extractor.py -v
```

Attendu : tous PASSED

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: extractor PDF → PDFDocument (pymupdf + pdfplumber)"
```

---

## Task 3: callouts.py

**Files:**
- Create: `callouts.py`
- Create: `tests/test_callouts.py`

- [ ] **Step 1: Écrire les tests**

Créer `tests/test_callouts.py` :

```python
from callouts import detect_callouts

def test_note_callout():
    result = detect_callouts("Note: Ce point est important.")
    assert "> [!NOTE] Note" in result
    assert "> Ce point est important." in result

def test_remarque_callout():
    result = detect_callouts("Remarque: À ne pas oublier.")
    assert "> [!NOTE] Remarque" in result

def test_warning_callout():
    result = detect_callouts("Attention: Procédure irréversible.")
    assert "> [!WARNING] Attention" in result

def test_danger_callout():
    result = detect_callouts("Danger: Risque élevé.")
    assert "> [!WARNING] Danger" in result

def test_important_callout():
    result = detect_callouts("Important: Lire attentivement.")
    assert "> [!IMPORTANT] Important" in result

def test_example_callout():
    result = detect_callouts("Exemple: Voici un cas pratique.")
    assert "> [!EXAMPLE] Exemple" in result

def test_tip_callout():
    result = detect_callouts("Conseil: Utiliser un bon outil.")
    assert "> [!TIP] Conseil" in result

def test_case_insensitive():
    result = detect_callouts("NOTE: Texte.")
    assert "> [!NOTE]" in result

def test_no_callout_unchanged():
    text = "Ceci est un paragraphe normal sans callout."
    assert detect_callouts(text) == text

def test_heading_not_converted():
    text = "## Note sur la méthode"
    assert detect_callouts(text) == text

def test_multiline_callout_continuation():
    text = "Note: Première ligne.\nSuite du texte.\n\nParagraphe suivant."
    result = detect_callouts(text)
    assert "> Suite du texte." in result
    assert "Paragraphe suivant." in result
    assert "> [!NOTE]" in result

def test_multiple_callouts():
    text = "Note: Premier.\n\nAttention: Deuxième."
    result = detect_callouts(text)
    assert "> [!NOTE]" in result
    assert "> [!WARNING]" in result
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_callouts.py -v
```

Attendu : `ModuleNotFoundError: No module named 'callouts'`

- [ ] **Step 3: Créer `callouts.py`**

```python
from __future__ import annotations
import re

_CALLOUT_MAP: list[tuple[str, str]] = [
    (r"note|remarque|info", "NOTE"),
    (r"important|à retenir|a retenir", "IMPORTANT"),
    (r"attention|avertissement|warning|danger", "WARNING"),
    (r"exemple|example", "EXAMPLE"),
    (r"conseil|tip", "TIP"),
]

_COMBINED = "|".join(p for p, _ in _CALLOUT_MAP)
_PATTERN = re.compile(rf"^({_COMBINED})\s*:\s*(.*)$", re.IGNORECASE)


def _type_for(keyword: str) -> str:
    kw = keyword.lower()
    for pattern, callout_type in _CALLOUT_MAP:
        if re.fullmatch(pattern, kw, re.IGNORECASE):
            return callout_type
    return "NOTE"


def detect_callouts(text: str) -> str:
    """Converts 'Keyword: text' paragraphs into Obsidian callout blocks."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#+\s", line):
            result.append(line)
            i += 1
            continue
        m = _PATTERN.match(line)
        if m:
            keyword, rest = m.group(1), m.group(2).strip()
            callout_type = _type_for(keyword)
            result.append(f"> [!{callout_type}] {keyword.capitalize()}")
            if rest:
                result.append(f"> {rest}")
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^#+\s", lines[i]):
                result.append(f"> {lines[i]}")
                i += 1
        else:
            result.append(line)
            i += 1
    return "\n".join(result)
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_callouts.py -v
```

Attendu : tous PASSED

- [ ] **Step 5: Commit**

```bash
git add callouts.py tests/test_callouts.py
git commit -m "feat: callouts.py — regex Note/Important/Attention → [!TYPE] Obsidian"
```

---

## Task 4: wikilinks.py

**Files:**
- Create: `wikilinks.py`
- Create: `tests/test_wikilinks.py`

- [ ] **Step 1: Écrire les tests**

Créer `tests/test_wikilinks.py` :

```python
from wikilinks import add_wikilinks, _is_proper_noun_candidate, STOP_LIST

def test_stop_list_words_rejected():
    assert not _is_proper_noun_candidate("Le")
    assert not _is_proper_noun_candidate("La")
    assert not _is_proper_noun_candidate("The")
    assert not _is_proper_noun_candidate("Ces")

def test_proper_noun_accepted():
    assert _is_proper_noun_candidate("Paris")
    assert _is_proper_noun_candidate("Dupont")
    assert _is_proper_noun_candidate("Microsoft")

def test_allcaps_rejected():
    assert not _is_proper_noun_candidate("NATO")
    assert not _is_proper_noun_candidate("PDF")

def test_proper_noun_linked():
    text = "---\ntitle: test\n---\n\nLe rapport concerne Paris et Lyon."
    result = add_wikilinks(text, set())
    assert "[[Paris]]" in result
    assert "[[Lyon]]" in result

def test_bold_phrase_linked():
    text = "---\ntitle: test\n---\n\nLe rapport de Jean Dupont est disponible."
    result = add_wikilinks(text, {"Jean Dupont"})
    assert "[[Jean Dupont]]" in result

def test_frontmatter_untouched():
    text = "---\ntitle: Paris\nauthor: Jean\n---\n\nContenu."
    result = add_wikilinks(text, set())
    fm_end = result.index("---", 3) + 3
    frontmatter = result[:fm_end]
    assert "[[" not in frontmatter

def test_code_block_untouched():
    text = "---\ntitle: test\n---\n\n```python\nParis = 'city'\n```"
    result = add_wikilinks(text, set())
    assert "[[Paris]]" not in result

def test_no_double_wrapping():
    text = "---\ntitle: test\n---\n\n[[Paris]] est une ville."
    result = add_wikilinks(text, set())
    assert "[[[[Paris]]]]" not in result
    assert result.count("[[Paris]]") == 1

def test_toc_line_untouched():
    text = "---\ntitle: t\n---\n\n- [[#Introduction]]\n"
    result = add_wikilinks(text, set())
    assert "[[[[#Introduction]]]]" not in result

def test_no_text_means_no_change():
    text = "---\ntitle: t\n---\n\naucun nom propre ici."
    result = add_wikilinks(text, set())
    assert "[[" not in result.split("---\n\n", 1)[1]
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_wikilinks.py -v
```

Attendu : `ModuleNotFoundError: No module named 'wikilinks'`

- [ ] **Step 3: Créer `wikilinks.py`**

```python
from __future__ import annotations
import re

STOP_LIST: frozenset[str] = frozenset({
    "le", "la", "les", "l", "un", "une", "des", "du", "the", "a", "an",
    "de", "en", "au", "aux", "et", "ou", "mais", "donc", "or", "ni",
    "car", "ce", "cet", "cette", "ces", "il", "elle", "ils", "elles",
    "je", "tu", "nous", "vous", "on", "que", "qui", "quand", "où",
    "comme", "par", "pour", "avec", "sans", "sur", "sous", "dans",
    "entre", "vers", "chez", "se", "si", "ne", "pas", "plus", "très",
    "bien", "aussi", "même", "tout", "tous", "toute", "toutes",
    "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta", "tes",
    "leur", "leurs", "its", "his", "her", "our", "your", "their",
    "this", "that", "these", "those", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "not", "no", "nor", "also", "from", "with", "into", "then", "than",
    "when", "dont", "lequel", "laquelle", "lesquels",
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
    "août", "septembre", "octobre", "novembre", "décembre",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
})

_PROPER_NOUN_RE = re.compile(r"(?<!\[)\b([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜÇ][a-zà-ÿ]{1,})\b(?!\])")
_CODE_BLOCK_RE = re.compile(r"(```[\s\S]*?```)", re.DOTALL)


def _is_proper_noun_candidate(word: str) -> bool:
    return (
        len(word) >= 2
        and word[0].isupper()
        and not word.isupper()
        and word.lower() not in STOP_LIST
    )


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    return text[: end + 4], text[end + 4:]


def add_wikilinks(text: str, bold_phrases: set[str]) -> str:
    """Adds [[wikilinks]] to body text. Frontmatter and code blocks are untouched."""
    frontmatter, body = _split_frontmatter(text)
    parts = _CODE_BLOCK_RE.split(body)

    processed: list[str] = []
    for part in parts:
        if part.startswith("```"):
            processed.append(part)
            continue

        for phrase in sorted(bold_phrases, key=len, reverse=True):
            phrase = phrase.strip()
            if not phrase or len(phrase) >= 80:
                continue
            escaped = re.escape(phrase)
            part = re.sub(rf"(?<!\[)\b{escaped}\b(?!\])", f"[[{phrase}]]", part)

        result_lines: list[str] = []
        for line in part.split("\n"):
            if re.match(r"^#+\s", line) or re.match(r"\s*-\s+\[\[#", line) or line.startswith(">"):
                result_lines.append(line)
                continue
            line = _PROPER_NOUN_RE.sub(
                lambda m: f"[[{m.group(0)}]]" if _is_proper_noun_candidate(m.group(0)) else m.group(0),
                line,
            )
            result_lines.append(line)

        processed.append("\n".join(result_lines))

    return frontmatter + "".join(processed)
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_wikilinks.py -v
```

Attendu : tous PASSED

- [ ] **Step 5: Commit**

```bash
git add wikilinks.py tests/test_wikilinks.py
git commit -m "feat: wikilinks.py — noms propres + phrases gras → [[wikilinks]]"
```

---

## Task 5: converter.py

**Files:**
- Create: `converter.py`
- Create: `tests/test_converter.py`

- [ ] **Step 1: Écrire les tests**

Créer `tests/test_converter.py` :

```python
from extractor import PDFDocument, PDFSection
from converter import build_frontmatter, build_toc, build_body, convert


def _doc():
    doc = PDFDocument(title="Rapport Test", author="Jean Dupont", subject="", pages=5)
    doc.sections = [
        PDFSection(level=1, text="Introduction", page=1),
        PDFSection(level=2, text="Contexte", page=1),
        PDFSection(level=0, text="Note: Ce point est crucial.", page=1),
        PDFSection(level=0, text="Texte normal ici.", page=2, is_bold=False),
        PDFSection(level=0, text="Tableau ci-dessous.", page=2, is_table=True),
    ]
    return doc


def test_frontmatter_has_title():
    fm = build_frontmatter(_doc(), "test.pdf")
    assert 'title: "Rapport Test"' in fm

def test_frontmatter_has_source():
    fm = build_frontmatter(_doc(), "test.pdf")
    assert "source: test.pdf" in fm

def test_frontmatter_has_pages():
    fm = build_frontmatter(_doc(), "test.pdf")
    assert "pages: 5" in fm

def test_frontmatter_has_mode():
    fm = build_frontmatter(_doc(), "test.pdf")
    assert "mode: obsidian-noia" in fm

def test_frontmatter_wrapped_in_dashes():
    fm = build_frontmatter(_doc(), "test.pdf")
    assert fm.startswith("---")
    assert fm.endswith("---")

def test_toc_has_table_header():
    toc = build_toc(_doc().sections)
    assert "## Table des matières" in toc

def test_toc_h1_present():
    toc = build_toc(_doc().sections)
    assert "[[#Introduction]]" in toc

def test_toc_h2_indented():
    toc = build_toc(_doc().sections)
    lines = toc.split("\n")
    h2_line = next(l for l in lines if "Contexte" in l)
    assert h2_line.startswith("  ")

def test_toc_empty_when_no_headings():
    doc = PDFDocument(title="T", author="", subject="", pages=1)
    doc.sections = [PDFSection(level=0, text="Texte.", page=1)]
    assert build_toc(doc.sections) == ""

def test_build_body_has_h1_prefix():
    body = build_body(_doc().sections)
    assert "# Introduction" in body

def test_build_body_has_h2_prefix():
    body = build_body(_doc().sections)
    assert "## Contexte" in body

def test_convert_starts_with_frontmatter():
    result = convert(_doc(), "test.pdf")
    assert result.startswith("---")

def test_convert_callouts_on():
    result = convert(_doc(), "test.pdf", enable_callouts=True)
    assert "> [!NOTE]" in result

def test_convert_callouts_off():
    result = convert(_doc(), "test.pdf", enable_callouts=False)
    assert "> [!NOTE]" not in result

def test_convert_toc_on():
    result = convert(_doc(), "test.pdf", enable_toc=True)
    assert "## Table des matières" in result

def test_convert_toc_off():
    result = convert(_doc(), "test.pdf", enable_toc=False)
    assert "## Table des matières" not in result

def test_convert_wikilinks_off():
    result = convert(_doc(), "test.pdf", enable_wikilinks=False)
    body = result.split("---\n\n", 1)[-1]
    assert "[[Jean" not in body
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_converter.py -v
```

Attendu : `ModuleNotFoundError: No module named 'converter'`

- [ ] **Step 3: Créer `converter.py`**

```python
from __future__ import annotations
from datetime import datetime
from extractor import PDFDocument, PDFSection
from callouts import detect_callouts
from wikilinks import add_wikilinks


def build_frontmatter(doc: PDFDocument, source_filename: str) -> str:
    title = doc.title.replace('"', '\\"')
    lines = [
        "---",
        f'title: "{title}"',
    ]
    if doc.author:
        lines.append(f"author: {doc.author}")
    lines += [
        f"date_extraction: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        f"source: {source_filename}",
        f"pages: {doc.pages}",
        "tags: []",
        "mode: obsidian-noia",
        "---",
    ]
    return "\n".join(lines)


def build_toc(sections: list[PDFSection]) -> str:
    headings = [s for s in sections if s.level in (1, 2, 3) and not s.is_table]
    if not headings:
        return ""
    lines = ["## Table des matières"]
    for s in headings:
        indent = "  " * (s.level - 1)
        lines.append(f"{indent}- [[#{s.text.strip()}]]")
    return "\n".join(lines)


def build_body(sections: list[PDFSection]) -> str:
    prefix_map = {1: "# ", 2: "## ", 3: "### ", 0: ""}
    parts: list[str] = []
    for s in sections:
        prefix = prefix_map.get(s.level, "") if not s.is_table else ""
        parts.append(prefix + s.text)
    return "\n\n".join(parts)


def convert(
    doc: PDFDocument,
    source_filename: str,
    enable_wikilinks: bool = True,
    enable_callouts: bool = True,
    enable_toc: bool = True,
) -> str:
    frontmatter = build_frontmatter(doc, source_filename)
    toc = build_toc(doc.sections) if enable_toc else ""
    body = build_body(doc.sections)

    if enable_callouts:
        body = detect_callouts(body)

    parts = [frontmatter]
    if toc:
        parts.append(toc)
    parts.append(body)
    full_text = "\n\n".join(parts)

    if enable_wikilinks:
        bold_phrases = {
            s.text.strip()
            for s in doc.sections
            if s.is_bold and s.level == 0 and len(s.text) < 80
        }
        full_text = add_wikilinks(full_text, bold_phrases)

    return full_text
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_converter.py -v
```

Attendu : tous PASSED

- [ ] **Step 5: Commit**

```bash
git add converter.py tests/test_converter.py
git commit -m "feat: converter.py — pipeline 4 passes frontmatter/TOC/callouts/wikilinks"
```

---

## Task 6: formatter.py

**Files:**
- Create: `formatter.py`
- Create: `tests/test_formatter.py`

- [ ] **Step 1: Écrire les tests**

Créer `tests/test_formatter.py` :

```python
import tempfile
from pathlib import Path
from formatter import sanitize_filename, save_markdown


def test_sanitize_basic():
    assert sanitize_filename("Mon Document") == "Mon_Document"

def test_sanitize_removes_special():
    result = sanitize_filename("Rapport: 2024!")
    assert ":" not in result
    assert "!" not in result

def test_sanitize_empty_returns_document():
    assert sanitize_filename("") == "document"

def test_sanitize_truncates_at_80():
    result = sanitize_filename("A" * 100)
    assert len(result) <= 80

def test_save_creates_file():
    with tempfile.TemporaryDirectory() as d:
        result = save_markdown("# Hello", "Test Doc", d)
        assert Path(result["output_path"]).exists()

def test_save_filename_ends_with_md():
    with tempfile.TemporaryDirectory() as d:
        result = save_markdown("# Hello", "Test", d)
        assert result["filename"].endswith(".md")

def test_save_returns_stats():
    with tempfile.TemporaryDirectory() as d:
        result = save_markdown("# Hello\nWorld", "Test", d)
        assert result["chars"] > 0
        assert result["lines"] > 0

def test_save_vault_missing_returns_warning(tmp_path):
    result = save_markdown("# Hello", "Test", str(tmp_path), "/nonexistent/vault")
    assert result["vault_path"] is None
    assert "vault_warning" in result

def test_save_vault_exists_copies_file(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    out = tmp_path / "output"
    result = save_markdown("# Hello", "Test", str(out), str(vault))
    assert result["vault_path"] is not None
    assert Path(result["vault_path"]).exists()
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_formatter.py -v
```

Attendu : `ModuleNotFoundError: No module named 'formatter'`

- [ ] **Step 3: Créer `formatter.py`**

```python
from __future__ import annotations
import re
import shutil
from pathlib import Path


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\s\-àâäéèêëîïôùûüç]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:80] or "document"


def save_markdown(
    md_text: str,
    title: str,
    output_dir: str | Path,
    vault_path: str | Path | None = None,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(title) + ".md"
    output_path = output_dir / filename
    output_path.write_text(md_text, encoding="utf-8")

    result: dict = {
        "filename": filename,
        "output_path": str(output_path),
        "vault_path": None,
        "chars": len(md_text),
        "lines": md_text.count("\n"),
    }

    if vault_path:
        vault = Path(vault_path).expanduser()
        if vault.exists():
            dest = vault / filename
            shutil.copy2(output_path, dest)
            result["vault_path"] = str(dest)
        else:
            result["vault_warning"] = f"Vault introuvable : {vault_path}"

    return result
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_formatter.py -v
```

Attendu : tous PASSED

- [ ] **Step 5: Lancer tous les tests**

```bash
.venv/bin/pytest tests/ -v
```

Attendu : tous PASSED (tests extractor + callouts + wikilinks + converter + formatter)

- [ ] **Step 6: Commit**

```bash
git add formatter.py tests/test_formatter.py
git commit -m "feat: formatter.py — sanitize_filename + save_markdown + copie vault"
```

---

## Task 7: app.py

**Files:**
- Create: `app.py`

Pas de test unitaire ici — couvert par le smoke test (Task 9).

- [ ] **Step 1: Créer `app.py`**

```python
from __future__ import annotations
import logging
import re
import tempfile
from pathlib import Path

import fitz
import uvicorn
import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from converter import convert
from extractor import extract
from formatter import save_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, encoding="utf-8") as _f:
    CONFIG = yaml.safe_load(_f)

app = FastAPI(title="pdf2obsidiannoia", version="1.0.0")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=(static_dir / "index.html").read_text(encoding="utf-8"))


@app.post("/api/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    language: str = Form("fr"),
    enable_wikilinks: bool = Form(True),
    enable_callouts: bool = Form(True),
    enable_toc: bool = Form(True),
    vault_path: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis")

    output_dir = CONFIG.get("output_dir", "./output")
    vault = vault_path.strip() or CONFIG.get("vault_path") or None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        doc_check = fitz.open(tmp_path)
        if doc_check.needs_pass:
            doc_check.close()
            raise HTTPException(status_code=400, detail="PDF protégé par mot de passe")
        is_scanned = all(not page.get_text().strip() for page in doc_check)
        doc_check.close()

        pdf_doc = extract(tmp_path)
        warnings: list[str] = []
        if is_scanned:
            warnings.append("PDF scanné détecté — contenu texte limité ou absent")

        md_text = convert(
            pdf_doc,
            source_filename=file.filename,
            enable_wikilinks=enable_wikilinks,
            enable_callouts=enable_callouts,
            enable_toc=enable_toc,
        )

        save_info = save_markdown(md_text, title=pdf_doc.title, output_dir=output_dir, vault_path=vault)
        if "vault_warning" in save_info:
            warnings.append(save_info["vault_warning"])

        wikilink_count = len(re.findall(r"\[\[(?!#)[^\]]+\]\]", md_text))
        callout_count = len(re.findall(r"^> \[!", md_text, re.MULTILINE))

        return JSONResponse({
            "success": True,
            "filename": save_info["filename"],
            "output_path": save_info["output_path"],
            "vault_path": save_info.get("vault_path"),
            "markdown": md_text,
            "warnings": warnings,
            "stats": {
                "pages": pdf_doc.pages,
                "sections": len(pdf_doc.sections),
                "wikilinks": wikilink_count,
                "callouts": callout_count,
                "chars": save_info["chars"],
                "lines": save_info["lines"],
            },
        })

    except HTTPException:
        raise
    except Exception:
        logging.exception("Erreur conversion")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/download/{filename}")
async def download(filename: str):
    output_dir = Path(CONFIG.get("output_dir", "./output")).resolve()
    file_path = (output_dir / filename).resolve()
    if not str(file_path).startswith(str(output_dir) + "/"):
        raise HTTPException(status_code=400, detail="Accès refusé")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(str(file_path), media_type="text/markdown", filename=file_path.name)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", CONFIG.get("port", 8001)))
    print(f"\n  pdf2obsidiannoia — http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: app.py — FastAPI port 8001, /api/convert + /api/download"
```

---

## Task 8: static/index.html

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Créer `static/index.html`**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>pdf2obsidiannoia</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #1e1e2e; --surface: #313244; --surface2: #181825;
      --text: #cdd6f4; --sub: #585b70; --blue: #89b4fa;
      --green: #a6e3a1; --red: #f38ba8; --yellow: #f9e2af; --mauve: #cba6f7;
    }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; background: var(--surface2); border-bottom: 1px solid var(--surface); }
    header .title { font-weight: 700; color: var(--blue); font-size: 15px; }
    header .hint { font-size: 11px; color: var(--sub); }
    main { flex: 1; display: grid; grid-template-columns: 340px 1fr; gap: 16px; padding: 16px; }
    .left { display: flex; flex-direction: column; gap: 12px; }
    .drop-zone { border: 2px dashed var(--blue); border-radius: 10px; padding: 32px 20px; text-align: center; cursor: pointer; background: var(--surface2); transition: background .2s; }
    .drop-zone:hover, .drop-zone.over { background: #2a2a45; }
    .drop-zone.ready { border-color: var(--green); }
    .drop-zone .icon { font-size: 28px; margin-bottom: 8px; }
    .drop-zone .lbl { color: var(--blue); font-weight: 600; }
    .drop-zone.ready .lbl { color: var(--green); }
    .drop-zone .hint { font-size: 11px; color: var(--sub); margin-top: 4px; }
    .panel { background: var(--surface2); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
    .panel-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--blue); padding-bottom: 6px; border-bottom: 1px solid var(--surface); }
    .row { display: flex; align-items: center; justify-content: space-between; font-size: 13px; }
    .row select { background: var(--surface); color: var(--text); border: none; border-radius: 5px; padding: 4px 8px; font-size: 12px; }
    .toggle { position: relative; width: 36px; height: 20px; flex-shrink: 0; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .track { position: absolute; inset: 0; background: var(--surface); border-radius: 20px; cursor: pointer; transition: background .2s; }
    .toggle input:checked + .track { background: var(--green); }
    .track::after { content: ''; position: absolute; width: 14px; height: 14px; background: white; border-radius: 50%; top: 3px; left: 3px; transition: transform .2s; }
    .toggle input:checked + .track::after { transform: translateX(16px); }
    .vault-wrap { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
    .vault-wrap input { background: var(--surface); color: var(--text); border: none; border-radius: 5px; padding: 6px 8px; font-size: 11px; width: 100%; }
    .vault-wrap input::placeholder { color: var(--sub); }
    #convertBtn { background: var(--blue); color: var(--bg); border: none; border-radius: 10px; padding: 12px; font-size: 14px; font-weight: 700; cursor: pointer; width: 100%; transition: opacity .2s; }
    #convertBtn:disabled { opacity: .4; cursor: not-allowed; }
    #convertBtn:hover:not(:disabled) { opacity: .85; }
    .progress { height: 4px; background: var(--surface); border-radius: 2px; overflow: hidden; display: none; }
    .progress.on { display: block; }
    .progress-fill { height: 100%; background: var(--blue); animation: slide 1.5s infinite; width: 60%; }
    @keyframes slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(270%); } }
    .alert { padding: 8px 12px; border-radius: 6px; font-size: 12px; display: none; }
    .alert.err { background: #3d1a1f; color: var(--red); display: block; }
    .alert.warn { background: #3d2e1a; color: var(--yellow); display: block; }
    .right { display: flex; flex-direction: column; gap: 10px; background: var(--surface2); border-radius: 10px; padding: 14px; }
    .prev-header { display: flex; align-items: center; justify-content: space-between; }
    .prev-header .lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--blue); }
    .vtoggle { display: flex; gap: 4px; }
    .vtoggle button { background: var(--surface); color: var(--sub); border: none; border-radius: 5px; padding: 3px 10px; font-size: 11px; cursor: pointer; }
    .vtoggle button.on { background: var(--blue); color: var(--bg); }
    #preview { flex: 1; background: var(--surface2); border: 1px solid var(--surface); border-radius: 6px; padding: 12px; overflow: auto; min-height: 300px; font-family: monospace; font-size: 12px; line-height: 1.7; white-space: pre-wrap; }
    #preview.rendered { font-family: system-ui; white-space: normal; }
    #preview.empty { display: flex; align-items: center; justify-content: center; color: var(--sub); font-style: italic; }
    .stats-bar { display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: var(--sub); min-height: 28px; }
    #dlBtn { background: var(--green); color: var(--bg); border: none; border-radius: 6px; padding: 5px 12px; font-size: 12px; font-weight: 600; cursor: pointer; }
  </style>
</head>
<body>
<header>
  <span class="title">📄 pdf2obsidiannoia</span>
  <span class="hint">sans IA · Obsidian MD · v1.0</span>
</header>
<main>
  <div class="left">
    <div class="drop-zone" id="dz">
      <div class="icon">📂</div>
      <div class="lbl" id="dzLbl">Glisser un PDF ici</div>
      <div class="hint">ou cliquer pour choisir</div>
      <input type="file" id="fi" accept=".pdf" hidden />
    </div>
    <div class="panel">
      <div class="panel-title">Options</div>
      <div class="row">
        <label>Langue</label>
        <select id="lang"><option value="fr">FR</option><option value="en">EN</option><option value="es">ES</option></select>
      </div>
      <div class="row">
        <label>Wikilinks [[…]]</label>
        <label class="toggle"><input type="checkbox" id="wiki" checked /><span class="track"></span></label>
      </div>
      <div class="row">
        <label>Callouts [!TYPE]</label>
        <label class="toggle"><input type="checkbox" id="calls" checked /><span class="track"></span></label>
      </div>
      <div class="row">
        <label>Table des matières</label>
        <label class="toggle"><input type="checkbox" id="toc" checked /><span class="track"></span></label>
      </div>
      <div class="vault-wrap">
        <label>Vault Obsidian <span style="color:var(--sub)">(optionnel)</span></label>
        <input type="text" id="vault" placeholder="~/Documents/Obsidian/MyVault" />
      </div>
    </div>
    <div class="progress" id="prog"><div class="progress-fill"></div></div>
    <button id="convertBtn" disabled>▶ Convertir en Obsidian MD</button>
    <div class="alert" id="alert"></div>
  </div>
  <div class="right">
    <div class="prev-header">
      <span class="lbl">Aperçu</span>
      <div class="vtoggle">
        <button id="bRaw" class="on" onclick="setView('raw')">Brut</button>
        <button id="bRend" onclick="setView('rendered')">Rendu</button>
      </div>
    </div>
    <div id="preview" class="empty">En attente d'un PDF…</div>
    <div class="stats-bar">
      <span id="stats"></span>
      <button id="dlBtn" style="display:none" onclick="dl()">⬇ Télécharger .md</button>
    </div>
  </div>
</main>
<script>
  let file = null, md = '', fname = '', view = 'raw';
  const dz = document.getElementById('dz');
  const fi = document.getElementById('fi');
  const btn = document.getElementById('convertBtn');
  const prev = document.getElementById('preview');
  const statsEl = document.getElementById('stats');
  const dlBtn = document.getElementById('dlBtn');
  const alertEl = document.getElementById('alert');
  const prog = document.getElementById('prog');

  dz.addEventListener('click', () => fi.click());
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('over'); pick(e.dataTransfer.files[0]); });
  fi.addEventListener('change', () => pick(fi.files[0]));

  function pick(f) {
    if (!f || !f.name.endsWith('.pdf')) return;
    file = f;
    document.getElementById('dzLbl').textContent = f.name;
    dz.classList.add('ready');
    btn.disabled = false;
    clearAlert();
  }

  function clearAlert() { alertEl.className = 'alert'; alertEl.textContent = ''; }
  function showAlert(msg, type = 'err') { alertEl.className = `alert ${type}`; alertEl.textContent = msg; }

  function setView(v) {
    view = v;
    document.getElementById('bRaw').classList.toggle('on', v === 'raw');
    document.getElementById('bRend').classList.toggle('on', v === 'rendered');
    render();
  }

  function render() {
    if (!md) return;
    prev.classList.remove('empty');
    if (view === 'raw') {
      prev.classList.remove('rendered');
      prev.textContent = md;
    } else {
      prev.classList.add('rendered');
      prev.innerHTML = toHtml(md);
    }
  }

  function toHtml(s) {
    const esc = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    return esc.split('\n').map(l => {
      if (l.startsWith('# ')) return `<h1>${l.slice(2)}</h1>`;
      if (l.startsWith('## ')) return `<h2>${l.slice(3)}</h2>`;
      if (l.startsWith('### ')) return `<h3>${l.slice(4)}</h3>`;
      const cm = l.match(/^&gt; \[!(\w+)\] (.*)$/);
      if (cm) return `<blockquote style="border-left:3px solid var(--blue);padding-left:8px"><strong>[!${cm[1]}]</strong> ${cm[2]}</blockquote>`;
      if (l.startsWith('&gt; ')) return `<blockquote style="border-left:3px solid var(--blue);padding-left:8px">${l.slice(5)}</blockquote>`;
      if (l === '---') return '<hr style="border-color:var(--surface)">';
      return `<p>${l.replace(/\[\[([^\]]+)\]\]/g,'<span style="color:var(--mauve)">[[<a href="#">$1</a>]]</span>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')}</p>`;
    }).join('');
  }

  btn.addEventListener('click', async () => {
    if (!file) return;
    clearAlert(); btn.disabled = true; prog.classList.add('on');
    prev.className = 'empty'; prev.textContent = 'Conversion en cours…';
    statsEl.textContent = ''; dlBtn.style.display = 'none'; md = '';

    const fd = new FormData();
    fd.append('file', file);
    fd.append('language', document.getElementById('lang').value);
    fd.append('enable_wikilinks', document.getElementById('wiki').checked);
    fd.append('enable_callouts', document.getElementById('calls').checked);
    fd.append('enable_toc', document.getElementById('toc').checked);
    fd.append('vault_path', document.getElementById('vault').value);

    try {
      const r = await fetch('/api/convert', { method: 'POST', body: fd });
      const data = await r.json();
      if (!r.ok) { showAlert(data.detail || 'Erreur'); return; }
      md = data.markdown; fname = data.filename;
      render();
      const s = data.stats;
      statsEl.textContent = `${s.pages} pages · ${s.wikilinks} wikilinks · ${s.callouts} callouts · ${s.chars} chars`;
      dlBtn.style.display = 'inline-block';
      if (data.warnings?.length) showAlert(data.warnings.join(' | '), 'warn');
    } catch (e) {
      showAlert('Erreur réseau : ' + e.message);
    } finally {
      btn.disabled = false; prog.classList.remove('on');
    }
  });

  function dl() { if (fname) window.location.href = `/api/download/${encodeURIComponent(fname)}`; }
</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add static/index.html
git commit -m "feat: static/index.html — UI drag&drop, aperçu brut/rendu, stats"
```

---

## Task 9: Smoke test & finalisation

**Files:**
- Aucun nouveau fichier

- [ ] **Step 1: Lancer tous les tests unitaires**

```bash
.venv/bin/pytest tests/ -v
```

Attendu : tous PASSED (test_extractor + test_callouts + test_wikilinks + test_converter + test_formatter)

- [ ] **Step 2: Démarrer l'application**

```bash
.venv/bin/python app.py
```

Attendu dans le terminal :
```
  pdf2obsidiannoia — http://localhost:8001
```

- [ ] **Step 3: Vérifier que l'interface s'affiche**

Ouvrir http://localhost:8001 dans un navigateur.  
Attendu : page avec zone drag & drop, options (Langue, Wikilinks, Callouts, TOC, Vault), bouton "Convertir".

- [ ] **Step 4: Test de conversion avec un vrai PDF**

Glisser n'importe quel PDF dans la zone de drop, cliquer "Convertir".  
Attendu :
- Le panneau droit affiche du Markdown avec frontmatter `---`, TOC `[[#...]]`, et (si le PDF contient "Note:" ou similaire) des callouts `> [!NOTE]`
- Les stats affichent le nombre de pages, wikilinks et callouts
- Le bouton "Télécharger .md" est visible

- [ ] **Step 5: Vérifier le fichier téléchargé**

Cliquer "Télécharger .md", ouvrir le fichier dans un éditeur.  
Vérifier que :
- Il commence par `---` (frontmatter YAML valide)
- Il contient `mode: obsidian-noia`
- Il contient `## Table des matières` (si le PDF a des titres)

- [ ] **Step 6: Commit final**

```bash
git add .
git commit -m "chore: smoke test validé — pdf2obsidiannoia v1.0 opérationnel"
```

- [ ] **Step 7: Créer le dépôt GitHub et pousser**

```bash
gh repo create pdf2obsidiannoia --public --description "PDF → Obsidian MD, sans IA" --source=. --remote=origin --push
```

Si `gh` n'est pas disponible, créer manuellement sur github.com puis :
```bash
git remote add origin https://github.com/<ton-username>/pdf2obsidiannoia.git
git push -u origin main
```
