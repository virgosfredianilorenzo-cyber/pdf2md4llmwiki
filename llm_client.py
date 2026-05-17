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


PROMPT_DETAILED = """\
Tu es un expert en knowledge management, synthèse documentaire et RAG (Retrieval Augmented Generation).
Ta mission : produire une note Markdown de HAUTE QUALITÉ à partir du contenu extrait d'un PDF,
optimisée pour un LLMWiki (style Karpathy) ou un vault Obsidian.

EXIGENCE PRINCIPALE : la qualité et la richesse du contenu priment sur la concision.
Ne résume pas, ne survole pas — développe, explique, contextualise.

=== CONTENU DU DOCUMENT ===
Titre : {title}
Auteur : {author}
Pages : {pages}

{content}

=== INSTRUCTIONS ===
Génère une note Markdown structurée avec :

1. Un bloc frontmatter YAML Obsidian-compatible entre --- :
   - Champs : title, author, date_extraction ({date_extraction}), source, tags, résumé_court
   - tags DOIT être une liste YAML entre crochets : tags: [mot1, mot2, mot3]
   - Encadrer de guillemets doubles toute valeur contenant ':' (ex: title, résumé_court)

2. Un résumé global (section ## Résumé) de 15 à 20 phrases couvrant :
   - Le sujet principal et son contexte historique ou disciplinaire
   - Les arguments ou thèses centraux, développés en détail
   - Les méthodes, approches ou cadres théoriques employés
   - Les résultats, données ou exemples concrets présentés
   - Les conclusions ou apports clés du document
   - Les limites, nuances ou points de débat soulevés
   - La pertinence et les applications pratiques pour un LLMWiki ou vault Obsidian

3. Le contenu restructuré en sections H2/H3 :
   - CHAQUE section H2, même courte, DOIT commencer par un paragraphe de synthèse approfondie
     de 8 à 15 phrases minimum. Ce paragraphe doit :
     * Expliquer le sujet de la section et son importance
     * Développer les idées principales avec des détails et des exemples
     * Contextualiser par rapport aux autres sections
     * Dégager les implications, nuances ou points de vigilance
     * Ne jamais se contenter de paraphraser — enrichir, interpréter, relier
   - Suivi du contenu structuré (listes, tableaux, sous-sections H3)

4. Des [[wikilinks]] pour TOUS les concepts importants (noms propres, termes techniques, entités)

5. Une section ## Concepts clés avec chaque terme défini en 3-5 phrases (pas juste une ligne)

6. Une section ## Références si des sources sont citées dans le doc

Règles absolues :
- Langue de rédaction : {language}
- Tags : {max_tags} mots-clés en minuscules avec tirets
- Chaque H2 doit être compréhensible de façon autonome (optimisé RAG)
- Supprime le bruit (numéros de page, en-têtes répétitifs, artefacts)
- Préserve les tableaux en Markdown
- NE génère PAS de commentaires méta sur ta démarche
- NE tronque PAS — si le contenu est long, développe-le entièrement

Commence directement par ---
"""


def format_raw(pdf_doc: PDFDocument, pdf_filename: str) -> str:
    """
    Formate les sections extraites en Markdown sans appel LLM.
    Génère un frontmatter minimal et préserve la structure H1/H2/H3.
    """
    from datetime import datetime
    lines: list[str] = []

    lines.append("---")
    lines.append(f'title: "{pdf_doc.title}"')
    lines.append(f"source: {pdf_filename}")
    lines.append(f"date_extraction: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
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


def list_models() -> list[str]:
    """Retourne la liste des modèles installés dans Ollama."""
    try:
        result = ollama.list()
        return [m.model for m in result.models]
    except Exception:
        return []


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
    from datetime import datetime
    content = sections_to_text(pdf_doc.sections, max_chars=6000)
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    prompt = PROMPT_DETAILED.format(
        title=pdf_doc.title,
        author=pdf_doc.author or "inconnu",
        pages=pdf_doc.pages,
        content=content,
        language=language,
        max_tags=max_tags,
        date_extraction=now,
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": temperature,
            "num_predict": 8192,
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
