[🇫🇷 Français](README.md) | [🇬🇧 English](README.en.md) | 🇪🇸 Español

---

# PDF2LLMWiki

Convierte PDFs en notas Markdown estructuradas para tu vault **Obsidian** o un **LLMWiki estilo Karpathy**.

**100% local · sin red externa · interfaz en navegador · Linux**

[![Release](https://img.shields.io/github/v/release/virgosfredianilorenzo-cyber/pdf2md4llmwiki)](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/latest) · [Changelog](CHANGELOG.md)

---

## Inicio rápido

```bash
unzip pdf2llmwiki.zip && cd pdf2llmwiki && bash start.sh
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

## Arquitectura

```
PDF (carga desde navegador)
  ↓
FastAPI local (app.py)  ←  http://localhost:8000
  ↓
pymupdf + pdfplumber   →  texto, estructura H1/H2/H3, tablas
  ↓
[Síntesis detalladas]  Ollama (LLM local)  →  estructuración, resumen, wikilinks, etiquetas
[Bruta estructurada]   formateador directo →  instantáneo, sin LLM
  ↓
formatter.py           →  frontmatter YAML Obsidian, normalización etiquetas, wikilinks
  ↓
output/nota.md         →  copia opcional al vault Obsidian
```

---

## Modos de extracción

| Modo | LLM | Velocidad | Uso |
|---|---|---|---|
| **Síntesis detalladas** | Sí (Ollama) | 30-120s | Nota wiki completa con síntesis por sección |
| **Bruta estructurada** | No | < 1s | Contenido completo preservado, ideal para archivo o post-procesamiento |

**Síntesis detalladas** — el LLM produce:
- un resumen global de **15 a 20 frases** que cubre contexto, tesis, métodos, resultados y límites
- un párrafo de síntesis en profundidad de **8 a 15 frases** para cada sección H2
- `[[wikilinks]]` sobre todos los conceptos clave
- una sección **Conceptos clave** con definiciones desarrolladas
- frontmatter YAML totalmente compatible con Obsidian (tags en lista, marca de tiempo `YYYY-MM-DDTHH:MM:SS`)

**Bruta estructurada** — extracción pura sin llamada de red. La jerarquía del documento (H1/H2/H3, párrafos, tablas) se conserva tal cual en Markdown.

---

## Interfaz

- **Trilingüe FR / EN / ES** — botones de bandera, persistencia `localStorage`
- **Indicador de modelo en tiempo real** — se actualiza al instante al cambiar de modelo o de modo
- **Lista de modelos dinámica** — muestra solo los modelos Ollama instalados
- **Instalación de modelos desde la UI** — sección ⊕ con barra de progreso SSE en tiempo real
- **Botón Stop** — cancela la conversión en el servidor al detectar la desconexión del cliente
- **Modal de confirmación animado** — antes de sobrescribir un resultado (fondo difuminado, Esc/Enter, clic exterior)
- **Vista previa triple** — fuente Markdown, HTML renderizado, chunks RAG
- **Copiar y descargar** — el archivo `.md` generado
- **Estadísticas post-conversión** — páginas, secciones, caracteres, chunks RAG

---

## Configuración

Edita `config.yaml` antes de lanzar:

```yaml
model: qwen2.5:7b               # modelo Ollama por defecto
vault_path: null                 # ruta del vault Obsidian, o null
output_dir: ./output             # carpeta de salida local
language: fr                     # idioma de redacción de la nota
max_tags: 8                      # número máximo de etiquetas generadas
chunk_size: 400                  # tamaño de chunks RAG (tokens aprox.)
temperature: 0.2                 # creatividad del LLM (0.0 = determinista)
ollama_timeout: 120              # timeout de Ollama en segundos
port: 8000                       # puerto del servidor local
auth_username: null              # usuario HTTP Basic (null = desactivado)
auth_password: null              # contraseña HTTP Basic (null = desactivado)
```

> El modelo, el idioma y las etiquetas también se pueden cambiar directamente desde la interfaz.

---

## Seguridad

El servidor escucha **únicamente en `127.0.0.1`** (localhost) — no es accesible desde la red local ni desde internet.

### Autenticación (opcional)

Para proteger el acceso en una máquina compartida, activa la autenticación HTTP Basic en `config.yaml`:

```yaml
auth_username: admin
auth_password: micontraseña
```

El navegador mostrará un cuadro de diálogo nativo en la primera visita. Deja ambos campos en `null` para desactivar la autenticación (comportamiento por defecto).

---

## Modelos Ollama

### Instalación

Los modelos se pueden instalar de dos formas:

**Desde la interfaz** (recomendado) — hacer clic en ⊕ Instalar un modelo en la UI, introducir el nombre del modelo y pulsar Descargar.

**Línea de comandos**:
```bash
ollama pull qwen2.5:7b
```

### Modelos recomendados

| Modelo | RAM | Calidad | Velocidad |
|--------|-----|---------|-----------|
| `qwen2.5:7b` | 4 GB | ⭐⭐⭐⭐⭐ | ★★★★ |
| `mistral:7b` | 4 GB | ⭐⭐⭐⭐ | ★★★★ |
| `llama3.2:3b` | 2 GB | ⭐⭐⭐ | ★★★★★ |
| `mistral:7b-instruct-q4_K_M` | 2.5 GB | ⭐⭐⭐⭐ | ★★★★★ |
| `gemma3:4b` | 3 GB | ⭐⭐⭐⭐ | ★★★★★ |

---

## Requisitos del sistema

- **Python 3.10+** — `sudo apt install python3.11`
- **Ollama** — instalado automáticamente por `start.sh`
- **RAM** — 4 GB mín (modelo 7B) · 2 GB (modelo 3B)

---

## Changelog

### [v1.2.0](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.2.0) — 2026-05-23
- Solo **Linux** — soporte para Windows y macOS eliminado
- `start.bat` eliminado

### [v1.1.0](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.1.0) — 2026-05-18
- Correcciones de seguridad (path traversal, XSS, binding de red)
- Autenticación HTTP Basic opcional

### [v1.0.0](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.0.0) — 2026-05-17
- Versión inicial

[Changelog completo →](CHANGELOG.md)

---

## Apoyar el proyecto

<a href="https://ko-fi.com/lorenzovirgosfrediani" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi"></a>

---

## Licencia MIT
