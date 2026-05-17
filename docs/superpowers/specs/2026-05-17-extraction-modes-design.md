# Design : Modes d'extraction PDF

**Date :** 2026-05-17
**Statut :** Approuvé

---

## Contexte

L'outil convertit actuellement les PDFs en Markdown via un unique flux LLM (Ollama). L'utilisateur souhaite deux modes distincts selon son besoin :

1. **Brute structurée** — extraction pure sans LLM, instantanée, contenu complet préservé
2. **Synthèses détaillées** — flux LLM avec synthèse obligatoire pour chaque section, même courte

---

## Architecture

### Paramètre `mode`

`/api/convert` accepte un nouveau champ de formulaire :
- `mode=raw` → branche sans LLM
- `mode=detailed` → branche LLM (défaut)

### Branche `raw` — `format_raw(pdf_doc: PDFDocument) -> str`

Nouvelle fonction dans `llm_client.py` :
- Reconstruit le Markdown directement depuis `pdf_doc.sections`
- Préserve les niveaux H1/H2/H3 détectés par l'extracteur
- Génère un frontmatter minimal (titre, source, date_extraction, tags vide)
- Aucun appel réseau — résultat instantané
- `process_markdown()` de `formatter.py` s'applique ensuite normalement

### Branche `detailed` — nouveau `PROMPT_DETAILED`

Remplace `PROMPT_TEMPLATE` dans `llm_client.py` :
- Instruction explicite : chaque section H2, quelle que soit sa taille, commence par un paragraphe de synthèse détaillée (minimum 3-5 phrases)
- `num_predict` passe de 4096 à 8192 pour les documents longs
- Température inchangée (0.2)

---

## Interface utilisateur

Deux boutons radio dans le panneau **Options**, au-dessus du bouton Convertir :

```
Mode d'extraction
  ◉ Synthèses détaillées   (défaut)
  ○ Brute structurée
```

Le timer s'adapte :
- `raw` → affiche "instantané" sans décompte
- `detailed` → décompte habituel selon le modèle

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `llm_client.py` | Nouveau `PROMPT_DETAILED`, nouvelle fonction `format_raw()`, renommage `PROMPT_TEMPLATE` → `PROMPT_DETAILED` |
| `app.py` | Paramètre `mode`, branchement conditionnel |
| `static/index.html` | Boutons radio, logique timer adaptée |
| `README.md` | Documentation des deux modes |

---

## Hors périmètre

- Pas de troisième mode "résumé court"
- Pas de modification de l'extracteur PDF
- `formatter.py` inchangé
