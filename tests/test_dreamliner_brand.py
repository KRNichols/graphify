"""Contracts for the Dreamliner user-facing brand.

Validation behavior stays in graphify.validate (assert_valid / validate_extraction).
The PyPI distribution remains graphifyy; dreamliner is the preferred CLI and
Codex skill invoke.
"""
from __future__ import annotations

from pathlib import Path

import tomllib

from graphify.validate import assert_valid, validate_extraction


REPO = Path(__file__).resolve().parent.parent


def test_validate_extraction_and_assert_valid_still_exist():
    """Brand rename must not remove or rename the extraction validators."""
    errors = validate_extraction({"nodes": [], "edges": []})
    assert errors == []
    assert_valid({"nodes": [], "edges": []})


def test_pyproject_exposes_dreamliner_scripts():
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["dreamliner"] == "graphify.__main__:main"
    assert scripts["graphify"] == "graphify.__main__:main"
    assert scripts["dreamliner-mcp"] == "graphify.serve:_main"
    assert "dreamliner" in data["project"]["keywords"]
    assert data["project"]["description"].startswith("Dreamliner")
    # Distribution name stays graphifyy so existing uv/pipx installs keep working.
    assert data["project"]["name"] == "graphifyy"


def test_codex_skill_is_dreamliner_not_claude_slash_graphify():
    skill = (REPO / "graphify" / "skill-codex.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: dreamliner\n")
    assert "# Dreamliner\n" in skill
    assert "$dreamliner" in skill
    assert "# /graphify" not in skill
    assert "/graphify" not in skill
    # Library contract is unchanged.
    assert "import graphify" in skill
    assert "graphify-out/" in skill


def test_agents_md_always_on_is_dreamliner():
    body = (REPO / "graphify" / "always_on" / "agents-md.md").read_text(encoding="utf-8")
    assert body.startswith("## Dreamliner\n")
    assert "$dreamliner" in body
    assert "dreamliner query" in body
    assert "/graphify" not in body


def test_agents_install_replaces_legacy_graphify_heading(tmp_path):
    """A pre-brand ``## graphify`` AGENTS.md section upgrades in place."""
    from graphify.install import _agents_install

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        "# Keep me\n\n## graphify\n\nALWAYS read GRAPH_REPORT.md first.\n",
        encoding="utf-8",
    )
    _agents_install(tmp_path, "codex")
    body = agents_md.read_text(encoding="utf-8")
    assert "# Keep me" in body
    assert "## Dreamliner" in body
    assert "dreamliner query" in body
    assert "ALWAYS read GRAPH_REPORT.md first." not in body
    assert not any(line.strip() == "## graphify" for line in body.splitlines())
