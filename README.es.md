[🇫🇷 Français](README.md) | [🇬🇧 English](README.en.md) | 🇪🇸 Español

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

## Interfaz

- Trilingüe FR / EN / ES (botones de bandera, persistencia localStorage)
- Indicador de modelo en tiempo real: se actualiza al instante al cambiar de modelo o de modo
- Botón Stop funcional: cancela la conversión en el servidor al detectar la desconexión del cliente
- Vista previa Markdown renderizada o en fuente, descarga directa

---

## Modos de extracción

| Modo | LLM | Velocidad | Uso |
|---|---|---|---|
| **Síntesis detalladas** | Sí (Ollama) | 30-120s | Nota wiki completa con síntesis por sección |
| **Bruta estructurada** | No | < 1s | Contenido completo preservado, ideal para archivo o post-procesamiento |

**Síntesis detalladas** — cada sección H2 recibe un párrafo de síntesis en profundidad de 8 a 15 frases, y el resumen global alcanza 15 a 20 frases. El frontmatter YAML es totalmente compatible con Obsidian (tags en lista, marca de tiempo completa `YYYY-MM-DDTHH:MM:SS`).

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
[detallado] Ollama (LLM local)  →  estructuración, resumen, etiquetas, wikilinks
[bruto]     formateador directo →  instantáneo, sin LLM
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
