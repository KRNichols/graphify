"""Upgrade-in-place tests for the Codex AGENTS.md always-on block."""
from __future__ import annotations

import graphify.__main__ as mainmod


_OLD_AGENTS_SECTION = """\
## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
"""


def test_agents_install_upgrades_stale_section(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# Project agents\n\n" + _OLD_AGENTS_SECTION, encoding="utf-8")
    monkeypatch.setattr(mainmod, "_check_skill_version", lambda _: None)

    mainmod._agents_install(tmp_path, platform="codex")

    after = agents_md.read_text(encoding="utf-8")
    assert "ALWAYS read graphify-out/GRAPH_REPORT.md" not in after
    assert "graphify query" in after
    assert "# Project agents" in after
