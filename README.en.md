[🇫🇷 Français](README.md) | 🇬🇧 English | [🇪🇸 Español](README.es.md)

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

## Interface

- Trilingual FR / EN / ES (flag buttons, localStorage persistence)
- Live model badge: updates instantly when changing model or extraction mode
- Countdown timer with per-model time estimate
- Stop button to cancel an ongoing conversion
- Rendered or source Markdown preview, direct download

---

## Extraction Modes

| Mode | LLM | Speed | Use case |
|---|---|---|---|
| **Detailed syntheses** | Yes (Ollama) | 30-120s | Full wiki note with per-section synthesis |
| **Raw structured** | No | < 1s | Full content preserved, ideal for archiving or post-processing |

**Detailed syntheses** — every H2 section, even short ones, gets an in-depth synthesis paragraph of 8 to 15 sentences, and the global summary reaches 25 to 30 sentences. Optimized for LLMWiki or Obsidian vault ingestion.

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
[detailed] Ollama (local LLM)  →  structuring, summary, tags, wikilinks
[raw]      direct formatter    →  instant, no LLM
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
