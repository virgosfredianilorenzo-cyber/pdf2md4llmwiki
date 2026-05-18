[🇫🇷 Français](README.md) | 🇬🇧 English | [🇪🇸 Español](README.es.md)

---

# PDF2LLMWiki

Converts PDFs into structured Markdown notes for your **Obsidian** vault or a **Karpathy-style LLMWiki**.

**Fully local · zero external network · browser interface · Linux / macOS / Windows**

[![Release](https://img.shields.io/github/v/release/virgosfredianilorenzo-cyber/pdf2md4llmwiki)](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/latest) · [Changelog](CHANGELOG.md)

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

## Architecture

```
PDF (browser upload)
  ↓
FastAPI local (app.py)  ←  http://localhost:8000
  ↓
pymupdf + pdfplumber   →  text, H1/H2/H3 structure, tables
  ↓
[Detailed syntheses]  Ollama (local LLM)  →  structuring, summary, wikilinks, tags
[Raw structured]      direct formatter    →  instant, no LLM
  ↓
formatter.py          →  Obsidian YAML frontmatter, tag normalisation, wikilinks
  ↓
output/note.md        →  optional copy to Obsidian vault
```

---

## Extraction Modes

| Mode | LLM | Speed | Use case |
|---|---|---|---|
| **Detailed syntheses** | Yes (Ollama) | 30-120s | Full wiki note with per-section synthesis |
| **Raw structured** | No | < 1s | Full content preserved, ideal for archiving or post-processing |

**Detailed syntheses** — the LLM produces:
- a global summary of **15 to 20 sentences** covering context, theses, methods, results and limitations
- an in-depth synthesis paragraph of **8 to 15 sentences** for every H2 section
- `[[wikilinks]]` on all key concepts
- a **Key concepts** section with developed definitions
- fully Obsidian-compatible YAML frontmatter (tags as list, timestamp `YYYY-MM-DDTHH:MM:SS`)

**Raw structured** — pure extraction with no network call. Document hierarchy (H1/H2/H3, paragraphs, tables) is preserved as-is in Markdown.

---

## Interface

- **Trilingual FR / EN / ES** — flag buttons, `localStorage` persistence
- **Live model badge** — updates instantly when changing model or extraction mode
- **Dynamic model dropdown** — shows only installed Ollama models
- **Model install from UI** — ⊕ section with real-time SSE progress bar
- **Stop button** — cancels conversion server-side on client disconnect
- **Animated confirmation modal** — before overwriting a result (blurred backdrop, Esc/Enter, click-outside)
- **Triple preview** — Markdown source, rendered HTML, RAG chunks
- **Copy & download** — of the generated `.md` file
- **Post-conversion stats** — pages, sections, characters, RAG chunks

---

## Configuration

Edit `config.yaml` before launching:

```yaml
model: qwen2.5:7b               # default Ollama model
vault_path: null                 # Obsidian vault path, or null
output_dir: ./output             # local output directory
language: fr                     # note writing language
max_tags: 8                      # max number of generated tags
chunk_size: 400                  # RAG chunk size (approx. tokens)
temperature: 0.2                 # LLM creativity (0.0 = deterministic)
ollama_timeout: 120              # Ollama timeout in seconds
port: 8000                       # local server port
auth_username: null              # HTTP Basic username (null = disabled)
auth_password: null              # HTTP Basic password (null = disabled)
```

> Model, language and tags can also be changed directly from the interface.

---

## Security

The server listens **only on `127.0.0.1`** (localhost) — it is not reachable from the local network or the internet.

### Authentication (optional)

To protect access on a shared machine, enable HTTP Basic Auth in `config.yaml`:

```yaml
auth_username: admin
auth_password: mysecret
```

The browser will then show a native login dialog on the first visit. Leave both fields as `null` to disable auth (default behaviour).

---

## Ollama Models

### Installation

Models can be installed two ways:

**From the interface** (recommended) — click ⊕ Install a model in the UI, enter the model name and click Download.

**Command line**:
```bash
ollama pull qwen2.5:7b
```

### Recommended Models

| Model | RAM | Quality | Speed |
|-------|-----|---------|-------|
| `qwen2.5:7b` | 4 GB | ⭐⭐⭐⭐⭐ | ★★★★ |
| `mistral:7b` | 4 GB | ⭐⭐⭐⭐ | ★★★★ |
| `llama3.2:3b` | 2 GB | ⭐⭐⭐ | ★★★★★ |
| `mistral:7b-instruct-q4_K_M` | 2.5 GB | ⭐⭐⭐⭐ | ★★★★★ |
| `gemma3:4b` | 3 GB | ⭐⭐⭐⭐ | ★★★★★ |

---

## System Requirements

| | Linux | macOS | Windows |
|--|-------|-------|---------|
| Python | `sudo apt install python3.11` | `brew install python@3.11` | [python.org](https://python.org/downloads) — check "Add to PATH" |
| Ollama | auto via start.sh | auto via start.sh | auto via start.bat |
| RAM | 4 GB min (7B) · 2 GB (3B) | same | same |

---

## Support the Project

<a href="https://ko-fi.com/lorenzovirgosfrediani" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi"></a>

---

## MIT License
