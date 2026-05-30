# Design Spec — pdf2obsidiannoia

**Date :** 2026-05-30
**Statut :** Approuvé

---

## Résumé

Application web locale standalone qui convertit des PDF en Markdown formatté selon les conventions Obsidian, sans recours à un LLM. Projet séparé du dépôt `pdf2md4llmwiki`, hébergé sous le nom GitHub `pdf2obsidiannoia`.

---

## Décisions prises

| Sujet | Décision |
|---|---|
| Interface | Web App locale (FastAPI + HTML) |
| Port | 8001 (coexistence avec pdf2md4llmwiki sur 8000) |
| IA | Aucune — conversion 100% déterministe |
| Fonctionnalités Obsidian | Frontmatter YAML, TOC, Callouts, Wikilinks |
| Détection wikilinks/callouts | Structurel + regex sémantiques (approche B) |
| Dépôt | Séparé, indépendant |

---

## Architecture

### Structure du projet

```
pdf2obsidiannoia/
├── app.py           # Serveur FastAPI, port 8001
├── extractor.py     # Extraction PDF → sections (pymupdf + pdfplumber)
├── converter.py     # Pipeline principal : 4 passes de transformation
├── wikilinks.py     # Détection noms propres + stop-list FR/EN
├── callouts.py      # Regex callouts → > [!TYPE]
├── formatter.py     # Assemblage final .md + sauvegarde vault
├── config.yaml      # Configuration
├── requirements.txt
├── start.sh
└── static/
    └── index.html   # Interface web
```

### Dépendances Python

```
fastapi
uvicorn
pymupdf        # extraction structurelle PDF
pdfplumber     # extraction tableaux
python-frontmatter
pyyaml
```

Pas de dépendance Ollama, pas de spaCy.

---

## Pipeline de conversion

Le pipeline `converter.py` exécute 4 passes séquentielles sur le contenu extrait :

### Passe 1 — Frontmatter YAML

Génère un bloc `---` Obsidian-compatible à partir des métadonnées PDF :

```yaml
---
title: "Titre du document"
author: Auteur
date: 2024-01-15
date_extraction: 2026-05-30T14:32:00
source: fichier.pdf
pages: 42
tags: []
mode: obsidian-noia
---
```

Les tags sont laissés vides (pas de LLM pour les inférer) mais la clé est présente pour que l'utilisateur puisse les remplir dans Obsidian.

### Passe 2 — Table des matières

Générée à partir de la hiérarchie H1/H2/H3 détectée par pymupdf (analyse des tailles de polices). Utilise la syntaxe Obsidian pour les liens internes :

```markdown
## Table des matières
- [[#Introduction]]
- [[#Chapitre 1 — Contexte]]
  - [[#1.1 Historique]]
- [[#Conclusion]]
```

Insérée immédiatement après le frontmatter.

### Passe 3 — Callouts

Scan de chaque paragraphe pour les mots-clés en début de ligne (insensible à la casse) :

| Mot-clé détecté | Type Obsidian |
|---|---|
| Note, Remarque, Info | `[!NOTE]` |
| Important, À retenir | `[!IMPORTANT]` |
| Attention, Avertissement, Warning, Danger | `[!WARNING]` |
| Exemple, Example | `[!EXAMPLE]` |
| Conseil, Tip | `[!TIP]` |

Transformation :

```
Avant : "Note : Ce point est crucial pour comprendre la suite."
Après :
> [!NOTE] Note
> Ce point est crucial pour comprendre la suite.
```

La détection est purement textuelle (regex sur le contenu des paragraphes).

### Passe 4 — Wikilinks

Deux sources de candidats :
1. **Texte en gras** (`flag & 16` dans pymupdf) — candidat direct si longueur < 80 chars
2. **Noms propres** — mot ou groupe de mots avec majuscule initiale, longueur ≥ 2 caractères

Filtrage par stop-list FR/EN (~80 mots) : `le, la, les, un, une, des, the, a, an, de, du, en, au, aux, et, ou, mais, donc, or, ni, car, ce, cet, cette, ces, il, elle, ils, elles, je, tu, nous, vous, on, que, qui, quand, où, comme, par, pour, avec, sans, sur, sous, dans, entre, vers, chez...`

Application : passe regex globale sur le corps du texte, **hors** frontmatter et blocs de code.

Résultat : `[[Jean Dupont]]`, `[[Intelligence Artificielle]]`, `[[Paris]]` — jamais `[[Le]]` ou `[[The]]`.

---

## Interface web

Layout 2 colonnes, port 8001 :

**Colonne gauche :**
- Zone drag & drop pour le PDF
- Options : langue (FR / EN / ES), toggles wikilinks / callouts / TOC, champ vault path (optionnel)
- Bouton "Convertir en Obsidian MD"

**Colonne droite :**
- Aperçu du Markdown généré (mode brut / rendu)
- Stats : pages, wikilinks ajoutés, callouts convertis
- Bouton téléchargement `.md`

---

## Configuration (`config.yaml`)

```yaml
port: 8001
output_dir: ./output
vault_path: null   # ex: ~/Documents/Obsidian/MyVault
language: fr
wikilinks: true
callouts: true
toc: true
```

---

## Gestion d'erreurs

| Cas | Comportement |
|---|---|
| Fichier non-PDF | Rejeté côté client avant upload |
| PDF protégé par mot de passe | Message clair dans l'UI, pas de crash |
| PDF scanné (image sans texte) | Avertissement "contenu non extractible, résultat limité" |
| Timeout extraction (> 30s) | HTTP 408 avec message explicite |
| Vault path inexistant | Warning dans la réponse, .md sauvegardé en local uniquement |

---

## Ce qui est hors scope

- Aucun LLM, aucune dépendance Ollama
- Pas de chunking RAG (fonctionnalité de pdf2md4llmwiki)
- Pas d'authentification HTTP Basic (usage local uniquement)
- Pas de pull de modèle
- Pas de support Windows/macOS (Linux uniquement, comme pdf2md4llmwiki)
