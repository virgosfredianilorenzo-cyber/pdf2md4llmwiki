# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [Unreleased]

---

## [1.2.0] — 2026-05-23 · [Release](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.2.0)

### Supprimé
- Support Windows et macOS — l'outil est désormais **Linux uniquement**
- `start.bat` supprimé du dépôt
- Branches Darwin/macOS dans `start.sh` et `install_ollama.sh`

### Documentation
- READMEs (FR/EN/ES) : suppression sections Windows, colonnes macOS/Windows, sous-titres plateforme ; pré-requis en liste simple
- Badge release dynamique dans les trois READMEs (FR/EN/ES)
- Lien vers le CHANGELOG dans les trois READMEs
- Lien release GitHub sur l'entrée v1.1.0 du CHANGELOG

### Corrigé
- Favicon manquant — ajout d'une icône SVG inline pour supprimer le 404 `/favicon.ico` dans les logs

---

## [1.1.0] — 2026-05-18 · [Release](https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.1.0)

### Sécurité
- **Path traversal** — endpoint `/api/download/{filename}` : ajout de `.resolve()` et vérification de préfixe pour bloquer les séquences `../`
- **Exposition réseau** — binding restreint de `0.0.0.0` à `127.0.0.1` (localhost uniquement)
- **XSS frontmatter** — échappement HTML des lignes YAML avant injection dans `innerHTML`
- **Info disclosure** — exceptions Python masquées côté client, loguées côté serveur
- **Supply chain** — remplacement du pattern `curl | sh` par téléchargement dans fichier temporaire aléatoire (`start.sh`, `install_ollama.sh`)

### Ajouté
- Authentification HTTP Basic optionnelle via `config.yaml` (`auth_username` / `auth_password`)
- Logging structuré des erreurs serveur (`logging.basicConfig`)

---

## [1.0.0] — 2026-05-17

### Ajouté
- Interface trilingue FR / EN / ES avec persistance `localStorage`
- Dropdown dynamique des modèles Ollama installés
- Installation de modèles depuis l'UI avec barre de progression SSE en temps réel
- Bouton Stop — annulation de la conversion côté serveur
- Modal de confirmation animé avant écrasement d'un résultat
- Aperçu triple : source Markdown, rendu HTML, chunks RAG
- Mode **Synthèses détaillées** — résumé global (15-20 phrases) + synthèse par section H2 (8-15 phrases) + wikilinks + tags
- Mode **Brute structurée** — extraction directe sans LLM (< 1s)
- Frontmatter YAML compatible Obsidian (tags en liste, horodatage ISO)
- Copie automatique optionnelle vers vault Obsidian (`vault_path`)
- Chunks RAG optionnels avec taille configurable
- Stats post-conversion (pages, sections, caractères, chunks)
- Badge modèle mis à jour en temps réel
- Script de démarrage automatisé (`start.sh`)
- Support Ko-fi

[1.2.0]: https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.2.0
[1.1.0]: https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.1.0
[1.0.0]: https://github.com/virgosfredianilorenzo-cyber/pdf2md4llmwiki/releases/tag/v1.0.0
