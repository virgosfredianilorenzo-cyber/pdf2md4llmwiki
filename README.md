# PDF2LLMWiki

Transforme des PDFs en notes Markdown structurées pour ton vault **Obsidian** ou un **LLMWiki** style Karpathy.

Full local · zéro réseau externe · interface navigateur · Linux / macOS / Windows.

---

## Démarrage en une commande

### Linux / macOS
```bash
unzip pdf2llmwiki.zip && cd pdf2llmwiki && bash start.sh
```

### Windows
```
1. Extraire le zip
2. Double-cliquer sur  start.bat
   — ou dans cmd : cd pdf2llmwiki && start.bat
```

Le script fait tout automatiquement :
- vérifie Python 3.10+
- crée et active le venv
- installe les dépendances pip
- installe Ollama si absent
- démarre le daemon Ollama
- télécharge le modèle LLM si absent (~4 Go, une seule fois)
- lance le serveur et ouvre le navigateur

Les relances suivantes prennent 2-3 secondes.

---

## Architecture

```
PDF (upload navigateur)
  ↓
FastAPI local (app.py)  ←  http://localhost:8000
  ↓
pymupdf + pdfplumber   →  texte, structure H1/H2/H3, tableaux
  ↓
Ollama (LLM local)     →  structuration, résumé, tags, wikilinks
  ↓
Formatter              →  frontmatter YAML, nommage Obsidian
  ↓
output/note.md         →  copie optionnelle dans le vault
```

---

## Configuration

Édite `config.yaml` avant de lancer :

```yaml
model: qwen2.5:7b               # modèle Ollama
vault_path: ~/Obsidian/MyVault  # chemin vault, ou null
language: fr
max_tags: 8
chunk_size: 400
port: 8000
```

### Modèles recommandés

| Modèle | RAM | Qualité FR | Vitesse |
|--------|-----|-----------|---------|
| `qwen2.5:7b` | 4 Go | ⭐⭐⭐⭐⭐ | ★★★★ |
| `mistral:7b` | 4 Go | ⭐⭐⭐⭐ | ★★★★ |
| `llama3.2:3b` | 2 Go | ⭐⭐⭐ | ★★★★★ |
| `mistral:7b-instruct-q4_K_M` | 2.5 Go | ⭐⭐⭐⭐ | ★★★★★ |

---

## Pré-requis système

| | Linux | macOS | Windows |
|--|-------|-------|---------|
| Python | `sudo apt install python3.11` | `brew install python@3.11` | [python.org](https://python.org/downloads) — coche "Add to PATH" |
| Ollama | auto par start.sh | auto par start.sh | auto par start.bat |
| RAM | 4 Go min | 4 Go min | 4 Go min |

---

## Soutenir le projet

Si cet outil t'est utile, tu peux soutenir son développement sur Ko-fi :

<a href="https://ko-fi.com/lorenzovirgosfrediani" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi"></a>

---

## Licence MIT
