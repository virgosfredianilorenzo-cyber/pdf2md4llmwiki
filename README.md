🇫🇷 Français | [🇬🇧 English](README.en.md) | [🇪🇸 Español](README.es.md)

---

# PDF2LLMWiki

Transforme des PDFs en notes Markdown structurées pour ton vault **Obsidian** ou un **LLMWiki** style Karpathy.

**Full local · zéro réseau externe · interface navigateur · Linux / macOS / Windows**

[![Release](https://img.shields.io/github/v/release/virgosfredianilorenzo-cyber/pdf2md4llmwiki)](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/latest)

---

## Démarrage en une commande

### Linux / macOS
```bash
unzip pdf2llmwiki.zip && cd pdf2llmwiki && bash start.sh
```

### Windows
```
1. Extraire le zip
2. Double-cliquer sur start.bat
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
[Synthèses détaillées]  Ollama (LLM local)  →  structuration, résumé, wikilinks, tags
[Brute structurée]      formateur direct    →  instantané, zéro LLM
  ↓
formatter.py           →  frontmatter YAML Obsidian, normalisation tags, wikilinks
  ↓
output/note.md         →  copie optionnelle dans le vault Obsidian
```

---

## Modes d'extraction

| Mode | LLM | Vitesse | Usage |
|---|---|---|---|
| **Synthèses détaillées** | Oui (Ollama) | 30-120s | Note wiki complète avec synthèse par section |
| **Brute structurée** | Non | < 1s | Contenu complet préservé, idéal pour archivage ou post-traitement |

**Synthèses détaillées** — le LLM produit :
- un résumé global de **15 à 20 phrases** couvrant contexte, thèses, méthodes, résultats et limites
- un paragraphe de synthèse approfondie de **8 à 15 phrases** pour chaque section H2
- des `[[wikilinks]]` sur tous les concepts clés
- une section **Concepts clés** avec définitions développées
- un frontmatter YAML entièrement compatible Obsidian (tags en liste, horodatage `YYYY-MM-DDTHH:MM:SS`)

**Brute structurée** — extraction pure sans appel réseau. La hiérarchie du document (H1/H2/H3, paragraphes, tableaux) est préservée telle quelle en Markdown.

---

## Interface

- **Trilingue FR / EN / ES** — boutons drapeau, persistance `localStorage`
- **Badge modèle en temps réel** — se met à jour instantanément au changement de modèle ou de mode
- **Dropdown dynamique** — affiche uniquement les modèles Ollama installés
- **Installation de modèles depuis l'UI** — section ⊕ avec barre de progression SSE en temps réel
- **Bouton Stop** — annule la conversion côté serveur dès la déconnexion du client
- **Modal de confirmation animé** — avant d'écraser un résultat (fond flouté, Échap/Entrée, clic extérieur)
- **Aperçu triple** — source Markdown, rendu HTML, chunks RAG
- **Copie & téléchargement** — du fichier `.md` généré
- **Stats post-conversion** — pages, sections, caractères, chunks RAG

---

## Configuration

Édite `config.yaml` avant de lancer :

```yaml
model: qwen2.5:7b               # modèle Ollama par défaut
vault_path: null                 # chemin vault Obsidian, ou null
output_dir: ./output             # dossier de sortie local
language: fr                     # langue de rédaction de la note
max_tags: 8                      # nombre max de tags générés
chunk_size: 400                  # taille des chunks RAG (tokens approx.)
temperature: 0.2                 # créativité LLM (0.0 = déterministe)
ollama_timeout: 120              # timeout Ollama en secondes
port: 8000                       # port du serveur local
auth_username: null              # identifiant HTTP Basic (null = désactivé)
auth_password: null              # mot de passe HTTP Basic (null = désactivé)
```

> Les options modèle, langue et tags peuvent aussi être changées directement depuis l'interface.

---

## Sécurité

Le serveur écoute **uniquement sur `127.0.0.1`** (localhost) — il n'est pas accessible depuis le réseau local ou internet.

### Authentification (optionnelle)

Pour protéger l'accès sur une machine partagée, active l'authentification HTTP Basic dans `config.yaml` :

```yaml
auth_username: admin
auth_password: monsecret
```

Le navigateur affiche alors une boîte de dialogue native à la première visite. Laisse les deux champs à `null` pour désactiver l'auth (comportement par défaut).

---

## Modèles Ollama

### Installation

Les modèles peuvent être installés de deux façons :

**Depuis l'interface** (recommandé) — cliquer sur ⊕ Installer un modèle dans l'UI, saisir le nom du modèle et cliquer sur Télécharger.

**En ligne de commande** :
```bash
ollama pull qwen2.5:7b
```

### Modèles recommandés

| Modèle | RAM | Qualité FR | Vitesse |
|--------|-----|-----------|---------|
| `qwen2.5:7b` | 4 Go | ⭐⭐⭐⭐⭐ | ★★★★ |
| `mistral:7b` | 4 Go | ⭐⭐⭐⭐ | ★★★★ |
| `llama3.2:3b` | 2 Go | ⭐⭐⭐ | ★★★★★ |
| `mistral:7b-instruct-q4_K_M` | 2.5 Go | ⭐⭐⭐⭐ | ★★★★★ |
| `gemma3:4b` | 3 Go | ⭐⭐⭐⭐ | ★★★★★ |

---

## Pré-requis système

| | Linux | macOS | Windows |
|--|-------|-------|---------|
| Python | `sudo apt install python3.11` | `brew install python@3.11` | [python.org](https://python.org/downloads) — cocher "Add to PATH" |
| Ollama | auto via start.sh | auto via start.sh | auto via start.bat |
| RAM | 4 Go min (7B) · 2 Go (3B) | idem | idem |

---

## Soutenir le projet

Si cet outil t'est utile, tu peux soutenir son développement sur Ko-fi :

<a href="https://ko-fi.com/lorenzovirgosfrediani" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi"></a>

---

## Licence MIT
