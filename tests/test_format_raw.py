import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from extractor import PDFSection, PDFDocument
from llm_client import format_raw


def _make_doc(sections):
    return PDFDocument(
        title="Test Doc", author="Auteur", subject="", pages=3,
        sections=sections,
    )


def test_format_raw_contains_title_in_frontmatter():
    doc = _make_doc([PDFSection(level=1, text="Introduction", page=1)])
    md = format_raw(doc, "test.pdf")
    assert 'title: "Test Doc"' in md


def test_format_raw_h1_section():
    doc = _make_doc([PDFSection(level=1, text="Mon Titre", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "# Mon Titre" in md


def test_format_raw_h2_section():
    doc = _make_doc([PDFSection(level=2, text="Sous-titre", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "## Sous-titre" in md


def test_format_raw_paragraph():
    doc = _make_doc([PDFSection(level=0, text="Du texte brut.", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "Du texte brut." in md


def test_format_raw_no_llm_content():
    doc = _make_doc([PDFSection(level=2, text="Sec", page=1)])
    md = format_raw(doc, "test.pdf")
    assert "Résumé" not in md
    assert "Concepts clés" not in md
