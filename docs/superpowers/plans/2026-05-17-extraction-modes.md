# Extraction Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter deux modes d'extraction dans l'interface — "Brute structurée" (sans LLM, instantané) et "Synthèses détaillées" (LLM avec synthèse obligatoire par section).

**Architecture:** Un paramètre `mode` (`raw` | `detailed`) est ajouté à `/api/convert`. En mode `raw`, `format_raw()` reconstruit le Markdown directement depuis les sections extraites. En mode `detailed`, le nouveau `PROMPT_DETAILED` (avec `num_predict=8192`) force une synthèse pour chaque section H2. L'UI ajoute deux boutons radio et adapte le timer.

**Tech Stack:** Python 3.10+, FastAPI, python-frontmatter, HTML/JS vanilla

---

## Fichiers modifiés

| Fichier | Rôle |
|---|---|
| `llm_client.py` | Nouveau `PROMPT_DETAILED`, nouvelle `format_raw()`, `num_predict` 4096→8192 |
| `app.py` | Paramètre `mode`, branchement conditionnel |
| `static/index.html` | Boutons radio, timer adapté mode raw |
| `README.md` | Documentation des deux modes |
| `tests/test_format_raw.py` | Tests unitaires `format_raw()` |

---

### Task 1 : Créer `format_raw()` dans `llm_client.py` (avec tests)

**Files:**
- Modify: `llm_client.py`
- Create: `tests/test_format_raw.py`

- [ ] **Step 1 : Créer le dossier tests et écrire le test qui échoue**

```bash
mkdir -p tests
touch tests/__init__.py
```

Contenu de `tests/test_format_raw.py` :
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from extractor import PDFSection, PDFDocument
from llm_client import format_raw


def _make_doc(sections):
    return PDFDocument(
        title="Test Doc", author="Auteur", subject="", pages=3,
        sections=sections,
    )


def test_format_raw_contains_title_in_frontmatter():
    doc = _make_doc([PDFSection(level=1, text="Introduction", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "title: Test Doc" in md


def test_format_raw_h1_section():
    doc = _make_doc([PDFSection(level=1, text="Mon Titre", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "# Mon Titre" in md


def test_format_raw_h2_section():
    doc = _make_doc([PDFSection(level=2, text="Sous-titre", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "## Sous-titre" in md


def test_format_raw_paragraph():
    doc = _make_doc([PDFSection(level=0, text="Du texte brut.", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "Du texte brut." in md


def test_format_raw_no_llm_content():
    doc = _make_doc([PDFSection(level=2, text="Sec", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "Résumé" not in md
    assert "Concepts clés" not in md
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /home/ljc/Documents/GitHub/pdf2md4llmwiki
python -m pytest tests/test_format_raw.py -v 2>&1 | head -30
```

Résultat attendu : `ImportError: cannot import name 'format_raw'`

- [ ] **Step 3 : Implémenter `format_raw()` dans `llm_client.py`**

Ajouter après les imports existants, avant `check_ollama_running` :

```python
def format_raw(pdf_doc: PDFDocument, pdf_filename: str) -> str:
    """
    Formate les sections extraites en Markdown sans appel LLM.
    Génère un frontmatter minimal et préserve la structure H1/H2/H3.
    """
    from datetime import date
    lines: list[str] = []

    # Frontmatter minimal
    lines.append("---")
    lines.append(f"title: {pdf_doc.title}")
    lines.append(f"source: {pdf_filename}")
    lines.append(f"date_extraction: {date.today().isoformat()}")
    lines.append(f"pages: {pdf_doc.pages}")
    lines.append("tags: []")
    lines.append("mode: brute")
    lines.append("---")
    lines.append("")

    prefix_map = {1: "# ", 2: "## ", 3: "### ", 0: ""}
    for section in pdf_doc.sections:
        if section.is_table:
            lines.append(section.text)
        else:
            prefix = prefix_map.get(section.level, "")
            lines.append(prefix + section.text)
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4 : Lancer les tests**

```bash
python -m pytest tests/test_format_raw.py -v
```

Résultat attendu : 5 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add llm_client.py tests/
git commit -m "feat: add format_raw() for LLM-free extraction mode"
```

---

### Task 2 : Mettre à jour `PROMPT_TEMPLATE` → `PROMPT_DETAILED` et `num_predict`

**Files:**
- Modify: `llm_client.py`

- [ ] **Step 1 : Renommer `PROMPT_TEMPLATE` en `PROMPT_DETAILED` et renforcer l'instruction synthèse**

Remplacer le bloc `PROMPT_TEMPLATE = """..."""` dans `llm_client.py` par :

```python
PROMPT_DETAILED = """\
Tu es un assistant expert en knowledge management et en RAG (Retrieval Augmented Generation).
Ta mission : transformer le contenu extrait d'un PDF en une note Markdown atomique,
optimisée pour un LLMWiki (style Karpathy) ou un vault Obsidian.

=== CONTENU DU DOCUMENT ===
Titre : {title}
Auteur : {author}
Pages : {pages}

{content}

=== INSTRUCTIONS ===
Génère une note Markdown structurée avec :

1. Un bloc frontmatter YAML entre --- (titre, auteur, date_extraction, tags, source, résumé_court)
2. Un résumé de 2-3 phrases (section ## Résumé)
3. Le contenu restructuré en sections atomiques H2/H3 claires :
   - CHAQUE section H2, même courte, doit commencer par un paragraphe de synthèse détaillée
     (minimum 3-5 phrases expliquant l'essentiel, le contexte et les implications)
   - Suivi du contenu détaillé (points clés, listes, tableaux)
4. Des [[wikilinks]] pour les concepts importants (noms propres, termes techniques)
5. Une section ## Concepts clés avec les termes définis brièvement
6. Une section ## Références si des sources sont citées dans le doc

Règles :
- Langue : {language}
- Tags : liste de {max_tags} mots-clés simples, en minuscules, sans espaces (utilise des tirets)
- Chunks atomiques : chaque H2 doit être compréhensible indépendamment (optimisé RAG)
- Supprime le bruit (numéros de page, en-têtes répétitifs, artefacts d'extraction)
- Préserve les tableaux en Markdown
- NE génère PAS de commentaires sur ta démarche, SEULEMENT le Markdown final

Commence directement par ---
"""
```

- [ ] **Step 2 : Mettre à jour la référence dans `structure_document()` et augmenter `num_predict`**

Dans `structure_document()`, remplacer :
```python
    prompt = PROMPT_TEMPLATE.format(
```
par :
```python
    prompt = PROMPT_DETAILED.format(
```

Et remplacer :
```python
            "num_predict": 4096,
```
par :
```python
            "num_predict": 8192,
```

- [ ] **Step 3 : Vérifier qu'aucun test ne casse**

```bash
python -m pytest tests/ -v
```

Résultat attendu : 5 tests PASSED

- [ ] **Step 4 : Commit**

```bash
git add llm_client.py
git commit -m "feat: rename PROMPT_TEMPLATE to PROMPT_DETAILED, enforce per-section synthesis, increase num_predict to 8192"
```

---

### Task 3 : Ajouter le paramètre `mode` dans `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Importer `format_raw` et ajouter le paramètre `mode`**

Modifier la ligne d'import dans `app.py` :
```python
from llm_client import check_ollama_running, chunk_for_rag, format_raw, structure_document
```

Ajouter `mode` aux paramètres de l'endpoint `convert` :
```python
async def convert(
    file: UploadFile = File(...),
    model: str = Form(None),
    language: str = Form(None),
    max_tags: int = Form(None),
    add_chunks: bool = Form(False),
    mode: str = Form("detailed"),
):
```

- [ ] **Step 2 : Ajouter le branchement conditionnel**

Remplacer le bloc :
```python
        # Étape 2 : Structuration LLM
        raw_md = structure_document(
            pdf_doc,
            model=model,
            language=language,
            max_tags=max_tags,
            temperature=CONFIG.get("temperature", 0.2),
            timeout=CONFIG.get("ollama_timeout", 120),
        )
```
par :
```python
        # Étape 2 : Structuration
        if mode == "raw":
            raw_md = format_raw(pdf_doc, file.filename)
            model = "— (mode brut)"
        else:
            raw_md = structure_document(
                pdf_doc,
                model=model,
                language=language,
                max_tags=max_tags,
                temperature=CONFIG.get("temperature", 0.2),
                timeout=CONFIG.get("ollama_timeout", 120),
            )
```

- [ ] **Step 3 : Ajouter `mode` dans la réponse JSON**

Dans le `return JSONResponse(...)`, ajouter après `"model_used": model,` :
```python
            "mode": mode,
```

- [ ] **Step 4 : Tester manuellement que le serveur démarre**

```bash
cd /home/ljc/Documents/GitHub/pdf2md4llmwiki
python app.py &
sleep 2
curl -s http://localhost:8000/api/status | python3 -m json.tool
kill %1
```

Résultat attendu : JSON avec `"ollama": true/false` sans erreur.

- [ ] **Step 5 : Commit**

```bash
git add app.py
git commit -m "feat: add mode parameter to /api/convert, branch raw vs detailed"
```

---

### Task 4 : Mettre à jour l'interface `static/index.html`

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1 : Ajouter le CSS pour les boutons radio**

Dans le bloc `<style>`, ajouter avant la fermeture `</style>` :

```css
  .mode-selector {
    display: flex;
    gap: 8px;
  }
  .mode-btn {
    flex: 1;
    padding: 8px 10px;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 12px;
    color: var(--muted);
    cursor: pointer;
    text-align: center;
    transition: border-color .2s, color .2s, background .2s;
    user-select: none;
  }
  .mode-btn.selected {
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(108,142,247,.08);
  }
```

- [ ] **Step 2 : Ajouter les boutons radio dans le panneau Options**

Dans le panneau Options (div `.opts`), ajouter en premier élément avant le `<div class="field">` du modèle :

```html
        <div class="field">
          <label>Mode d'extraction</label>
          <div class="mode-selector">
            <div class="mode-btn selected" id="modeDetailed" onclick="setMode('detailed')">
              ✦ Synthèses détaillées
            </div>
            <div class="mode-btn" id="modeRaw" onclick="setMode('raw')">
              ≡ Brute structurée
            </div>
          </div>
        </div>
```

- [ ] **Step 3 : Ajouter la fonction `setMode()` et la variable `currentMode` dans le JS**

Après `let lastModelUsed = null;`, ajouter :
```javascript
let currentMode = 'detailed';

function setMode(mode) {
  currentMode = mode;
  document.getElementById('modeDetailed').classList.toggle('selected', mode === 'detailed');
  document.getElementById('modeRaw').classList.toggle('selected', mode === 'raw');
}
```

- [ ] **Step 4 : Transmettre `mode` dans le FormData**

Dans `startConvert()`, après `formData.append('add_chunks', ...)`, ajouter :
```javascript
    formData.append('mode', currentMode);
```

- [ ] **Step 5 : Adapter le timer pour le mode `raw`**

Remplacer le bloc du timer dans `startConvert()` :
```javascript
  document.getElementById('timerRemaining').style.color = 'var(--warn)';
  const modelEstimates = { ... };
  const selectedModel = document.getElementById('optModel').value;
  startTimer(modelEstimates[selectedModel] ?? 90);
```
par :
```javascript
  document.getElementById('timerRemaining').style.color = 'var(--warn)';
  if (currentMode === 'raw') {
    startTimer(0);
    document.getElementById('timerRemaining').textContent = 'instantané';
  } else {
    const modelEstimates = {
      '': 60, 'qwen2.5:7b': 60, 'llama3.2:3b': 30,
      'mistral:7b': 120, 'mistral:7b-instruct-q4_K_M': 90,
    };
    const selectedModel = document.getElementById('optModel').value;
    startTimer(modelEstimates[selectedModel] ?? 90);
  }
```

- [ ] **Step 6 : Masquer le sélecteur de modèle en mode `raw`**

Dans `setMode()`, ajouter après la mise à jour des classes :
```javascript
  const modelField = document.getElementById('optModel').closest('.field');
  modelField.style.display = mode === 'raw' ? 'none' : '';
```

- [ ] **Step 7 : Commit**

```bash
git add static/index.html
git commit -m "feat: add mode selector UI, hide model selector in raw mode, adapt timer"
```

---

### Task 5 : Mettre à jour `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1 : Ajouter une section "Modes d'extraction"**

Ajouter après la section `## Configuration` et avant `### Modèles recommandés` :

```markdown
## Modes d'extraction

| Mode | LLM | Vitesse | Usage |
|---|---|---|---|
| **Synthèses détaillées** | Oui (Ollama) | 30-120s | Note wiki complète avec synthèse par section |
| **Brute structurée** | Non | < 1s | Contenu complet préservé, idéal pour archivage ou post-traitement |

**Synthèses détaillées** — chaque section H2, même courte, reçoit un paragraphe de synthèse de 3-5 phrases. Optimisé pour l'alimentation d'un LLMWiki ou vault Obsidian.

**Brute structurée** — extraction pure sans appel réseau. La hiérarchie du document (titres H1/H2/H3, paragraphes, tableaux) est préservée telle quelle dans le Markdown. Aucune modification du contenu.
```

- [ ] **Step 2 : Commit**

```bash
git add README.md
git commit -m "docs: document extraction modes in README"
```

---

### Task 6 : READMEs multilingues (EN et ES) avec drapeaux

**Files:**
- Create: `README.en.md`
- Create: `README.es.md`
- Modify: `README.md` (ajout liens vers les autres langues)

- [ ] **Step 1 : Ajouter les liens de langue en tête du README.md existant**

En tout début de `README.md`, avant `# PDF2LLMWiki`, ajouter :

```markdown
🇫🇷 Français | [🇬🇧 English](README.en.md) | [🇪🇸 Español](README.es.md)

---

```

- [ ] **Step 2 : Créer `README.en.md`**

Contenu complet :

```markdown
🇫🇷 [Français](README.md) | 🇬🇧 English | [🇪🇸 Español](README.es.md)

---

# PDF2LLMWiki

Converts PDFs into structured Markdown notes for your **Obsidian** vault or a **Karpathy-style LLMWiki**.

Fully local · zero external network · browser interface · Linux / macOS / Windows.

---

## Quick Start

### Linux / macOS
```bash
unzip pdf2llmwiki.zip && cd pdf2llmwiki && bash start.sh
```

### Windows
```
1. Extract the zip
2. Double-click start.bat
   — or in cmd: cd pdf2llmwiki && start.bat
```

The script handles everything automatically:
- checks Python 3.10+
- creates and activates the venv
- installs pip dependencies
- installs Ollama if missing
- starts the Ollama daemon
- downloads the LLM model if missing (~4 GB, one-time)
- launches the server and opens the browser

Subsequent launches take 2-3 seconds.

---

## Extraction Modes

| Mode | LLM | Speed | Use case |
|---|---|---|---|
| **Detailed syntheses** | Yes (Ollama) | 30-120s | Full wiki note with per-section synthesis |
| **Raw structured** | No | < 1s | Full content preserved, ideal for archiving or post-processing |

**Detailed syntheses** — every H2 section, even short ones, gets a 3-5 sentence synthesis paragraph. Optimized for LLMWiki or Obsidian vault ingestion.

**Raw structured** — pure extraction with no network call. Document hierarchy (H1/H2/H3 headings, paragraphs, tables) is preserved as-is in Markdown.

---

## Architecture

```
PDF (browser upload)
  ↓
FastAPI local (app.py)  ←  http://localhost:8000
  ↓
pymupdf + pdfplumber   →  text, H1/H2/H3 structure, tables
  ↓
[detailed mode] Ollama (local LLM) → structuring, summary, tags, wikilinks
[raw mode]      direct formatter   → instant, no LLM
  ↓
Formatter              →  YAML frontmatter, Obsidian naming
  ↓
output/note.md         →  optional copy to vault
```

---

## Configuration

Edit `config.yaml` before launching:

```yaml
model: qwen2.5:7b               # Ollama model
vault_path: ~/Obsidian/MyVault  # vault path, or null
language: fr
max_tags: 8
chunk_size: 400
port: 8000
```

### Recommended models

| Model | RAM | FR Quality | Speed |
|-------|-----|-----------|-------|
| `qwen2.5:7b` | 4 GB | ⭐⭐⭐⭐⭐ | ★★★★ |
| `mistral:7b` | 4 GB | ⭐⭐⭐⭐ | ★★★★ |
| `llama3.2:3b` | 2 GB | ⭐⭐⭐ | ★★★★★ |
| `mistral:7b-instruct-q4_K_M` | 2.5 GB | ⭐⭐⭐⭐ | ★★★★★ |

---

## System Requirements

| | Linux | macOS | Windows |
|--|-------|-------|---------|
| Python | `sudo apt install python3.11` | `brew install python@3.11` | [python.org](https://python.org/downloads) — check "Add to PATH" |
| Ollama | auto via start.sh | auto via start.sh | auto via start.bat |
| RAM | 4 GB min | 4 GB min | 4 GB min |

---

## Support the project

<a href="https://ko-fi.com/lorenzovirgosfrediani" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi"></a>

---

## MIT License
```

- [ ] **Step 3 : Créer `README.es.md`**

Contenu complet :

```markdown
🇫🇷 [Français](README.md) | [🇬🇧 English](README.en.md) | 🇪🇸 Español

---

# PDF2LLMWiki

Convierte PDFs en notas Markdown estructuradas para tu vault **Obsidian** o un **LLMWiki estilo Karpathy**.

100% local · sin red externa · interfaz en navegador · Linux / macOS / Windows.

---

## Inicio rápido

### Linux / macOS
```bash
unzip pdf2llmwiki.zip && cd pdf2llmwiki && bash start.sh
```

### Windows
```
1. Extraer el zip
2. Hacer doble clic en start.bat
   — o en cmd: cd pdf2llmwiki && start.bat
```

El script se encarga de todo automáticamente:
- verifica Python 3.10+
- crea y activa el entorno virtual
- instala las dependencias pip
- instala Ollama si no está presente
- inicia el daemon de Ollama
- descarga el modelo LLM si falta (~4 GB, una sola vez)
- lanza el servidor y abre el navegador

Los lanzamientos siguientes tardan 2-3 segundos.

---

## Modos de extracción

| Modo | LLM | Velocidad | Uso |
|---|---|---|---|
| **Síntesis detalladas** | Sí (Ollama) | 30-120s | Nota wiki completa con síntesis por sección |
| **Bruta estructurada** | No | < 1s | Contenido completo preservado, ideal para archivo o post-procesamiento |

**Síntesis detalladas** — cada sección H2, aunque sea corta, recibe un párrafo de síntesis de 3-5 frases. Optimizado para LLMWiki o vault Obsidian.

**Bruta estructurada** — extracción pura sin llamada de red. La jerarquía del documento (títulos H1/H2/H3, párrafos, tablas) se conserva tal cual en Markdown.

---

## Arquitectura

```
PDF (carga desde navegador)
  ↓
FastAPI local (app.py)  ←  http://localhost:8000
  ↓
pymupdf + pdfplumber   →  texto, estructura H1/H2/H3, tablas
  ↓
[modo detallado] Ollama (LLM local) → estructuración, resumen, etiquetas, wikilinks
[modo bruto]     formateador directo → instantáneo, sin LLM
  ↓
Formateador            →  frontmatter YAML, nomenclatura Obsidian
  ↓
output/nota.md         →  copia opcional al vault
```

---

## Configuración

Edita `config.yaml` antes de lanzar:

```yaml
model: qwen2.5:7b               # modelo Ollama
vault_path: ~/Obsidian/MyVault  # ruta del vault, o null
language: fr
max_tags: 8
chunk_size: 400
port: 8000
```

### Modelos recomendados

| Modelo | RAM | Calidad FR | Velocidad |
|--------|-----|-----------|---------|
| `qwen2.5:7b` | 4 GB | ⭐⭐⭐⭐⭐ | ★★★★ |
| `mistral:7b` | 4 GB | ⭐⭐⭐⭐ | ★★★★ |
| `llama3.2:3b` | 2 GB | ⭐⭐⭐ | ★★★★★ |
| `mistral:7b-instruct-q4_K_M` | 2.5 GB | ⭐⭐⭐⭐ | ★★★★★ |

---

## Requisitos del sistema

| | Linux | macOS | Windows |
|--|-------|-------|---------|
| Python | `sudo apt install python3.11` | `brew install python@3.11` | [python.org](https://python.org/downloads) — marcar "Add to PATH" |
| Ollama | auto vía start.sh | auto vía start.sh | auto vía start.bat |
| RAM | 4 GB mín | 4 GB mín | 4 GB mín |

---

## Apoyar el proyecto

<a href="https://ko-fi.com/lorenzovirgosfrediani" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi"></a>

---

## Licencia MIT
```

- [ ] **Step 4 : Commit**

```bash
git add README.md README.en.md README.es.md
git commit -m "docs: add English and Spanish READMEs with language flags"
```

---

### Task 8 : Push final

- [ ] **Step 1 : Vérifier l'état git**

```bash
git log --oneline -6
git status
```

- [ ] **Step 2 : Push**

```bash
git push origin main
```
