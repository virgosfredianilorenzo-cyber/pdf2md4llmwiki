"""
llm_client.py — Interface Ollama pour la structuration LLMWiki.
Zéro appel réseau externe : tout passe par l'API locale Ollama.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import ollama
from extractor import PDFDocument, sections_to_text


PROMPT_TEMPLATE = """\
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
   - Chaque section H2 doit commencer par un paragraphe de synthèse (2-4 phrases) qui résume l'essentiel de cette partie
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


def format_raw(pdf_doc: PDFDocument, pdf_filename: str) -> str:
    """
    Formate les sections extraites en Markdown sans appel LLM.
    Génère un frontmatter minimal et préserve la structure H1/H2/H3.
    """
    from datetime import date
    lines: list[str] = []

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


def check_ollama_running() -> tuple[bool, str]:
    """Vérifie qu'Ollama est accessible et liste les modèles."""
    try:
        models = ollama.list()
        names = [m.model for m in models.models]
        return True, ", ".join(names) if names else "aucun modèle installé"
    except Exception as e:
        return False, str(e)


def structure_document(
    pdf_doc: PDFDocument,
    model: str,
    language: str = "fr",
    max_tags: int = 8,
    temperature: float = 0.2,
    timeout: int = 120,
) -> str:
    """
    Envoie le contenu extrait à Ollama et récupère le Markdown structuré.
    Retourne la chaîne Markdown complète.
    """
    content = sections_to_text(pdf_doc.sections, max_chars=6000)

    prompt = PROMPT_TEMPLATE.format(
        title=pdf_doc.title,
        author=pdf_doc.author or "inconnu",
        pages=pdf_doc.pages,
        content=content,
        language=language,
        max_tags=max_tags,
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": temperature,
            "num_predict": 4096,
        },
    )

    raw = response.message.content.strip()

    # Nettoyage : retire les balises de code Markdown si le LLM les ajoute
    raw = re.sub(r"^```(?:markdown|md)?\n?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\n?```$", "", raw)

    return raw


def chunk_for_rag(markdown_text: str, chunk_size: int = 400) -> list[dict]:
    """
    Découpe le Markdown en chunks RAG-ready.
    Chaque chunk = dict {"section": str, "content": str, "chars": int}
    Respecte les frontières de sections H2.
    """
    chunks: list[dict] = []
    current_section = "intro"
    current_parts: list[str] = []
    current_len = 0

    for line in markdown_text.split("\n"):
        if line.startswith("## "):
            if current_parts:
                chunks.append({
                    "section": current_section,
                    "content": "\n".join(current_parts).strip(),
                    "chars": current_len,
                })
            current_section = line.lstrip("# ").strip()
            current_parts = [line]
            current_len = len(line)
        else:
            current_parts.append(line)
            current_len += len(line)
            # Force une coupure si le chunk dépasse la taille cible
            if current_len >= chunk_size * 4:  # ~4 chars/token
                chunks.append({
                    "section": current_section,
                    "content": "\n".join(current_parts).strip(),
                    "chars": current_len,
                })
                current_parts = []
                current_len = 0

    if current_parts:
        chunks.append({
            "section": current_section,
            "content": "\n".join(current_parts).strip(),
            "chars": current_len,
        })

    return [c for c in chunks if c["content"].strip()]
