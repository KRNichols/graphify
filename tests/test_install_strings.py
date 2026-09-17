"""Regression tests for Codex install-time instruction strings."""
from __future__ import annotations

from graphify.__main__ import (
    _AGENTS_MD_SECTION,
    _READ_NUDGE,
    _SEARCH_NUDGE,
    _skill_registration,
)


_INSTALL_TEXTS = {
    "_SEARCH_NUDGE": _SEARCH_NUDGE,
    "_READ_NUDGE": _READ_NUDGE,
    "_AGENTS_MD_SECTION": _AGENTS_MD_SECTION,
}


def test_every_install_surface_recommends_graphify_query():
    missing = [name for name, text in _INSTALL_TEXTS.items() if "graphify query" not in text]
    assert not missing, f"these install surfaces no longer mention `graphify query`: {missing}"


def test_no_install_surface_demands_reading_the_full_report_first():
    import re

    banned = [
        re.compile(r"read[^.\n]{0,80}GRAPH_REPORT\.md[^.\n]{0,80}before", re.IGNORECASE),
        re.compile(r"first\s+tool\s+call[^.\n]{0,80}GRAPH_REPORT", re.IGNORECASE),
        re.compile(r"always\s+read[^.\n]{0,80}GRAPH_REPORT", re.IGNORECASE),
    ]
    hits = []
    for name, text in _INSTALL_TEXTS.items():
        for pattern in banned:
            match = pattern.search(text)
            if match:
                hits.append((name, match.group(0)))
    assert not hits, f"banned report-first phrasing reappeared: {hits}"


def test_report_is_still_referenced_as_fallback():
    assert "GRAPH_REPORT.md" in _AGENTS_MD_SECTION


def test_agents_section_does_not_skip_dirty_graph_output():
    assert "Dirty graphify-out/ files are expected" in _AGENTS_MD_SECTION
    assert "not a reason to skip graphify" in _AGENTS_MD_SECTION


def test_agents_section_uses_generic_graphify_instruction():
    assert "`skill` tool" not in _AGENTS_MD_SECTION
    assert 'skill: "graphify"' not in _AGENTS_MD_SECTION
    assert "use the installed graphify skill" in _AGENTS_MD_SECTION


def test_skill_registration_uses_host_generic_instruction():
    reg = _skill_registration()
    assert 'skill: "graphify"' not in reg
    assert "Skill tool" not in reg
    assert "use the installed graphify skill or instructions" in reg


def test_how_it_works_clarifies_code_only_semantic_extraction():
    from pathlib import Path

    doc = (Path(__file__).parent.parent / "docs" / "how-it-works.md").read_text(encoding="utf-8")
    assert "Code files are not sent to the LLM semantic extractor" in doc
    assert "code files, Pass 3 is skipped entirely" in doc
    assert "docs, papers, images, and transcripts" in doc
