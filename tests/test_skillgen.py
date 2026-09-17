"""Tests for the Codex-only skillgen surface."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.skillgen import gen  # noqa: E402


UNIFIED_DESCRIPTION = (
    "Use for any question about a codebase, its architecture, file relationships, "
    "or project content — especially when graphify-out/ exists, where the question "
    "should be treated as a graphify query first. Turns any input (code, docs, "
    "papers, images, videos) into a persistent knowledge graph with god nodes, "
    "community detection, and query/path/explain tools."
)


def _codex_artifacts():
    platforms = gen.load_platforms()
    arts = gen.render_all(platforms, only="codex")
    core = next(a for a in arts if a.path == "graphify/skill-codex.md")
    refs = {a.path.rsplit("/", 1)[-1]: a.content for a in arts if a.path != "graphify/skill-codex.md"}
    return core.content, refs


def test_only_codex_platform_is_registered():
    platforms = gen.load_platforms()
    assert list(platforms) == ["codex"]


def test_audit_coverage_passes():
    platforms = gen.load_platforms()
    problems = gen.audit_coverage(platforms["codex"])
    assert problems == [], "\n".join(problems)


def test_check_passes():
    platforms = gen.load_platforms()
    artifacts = gen.render_all(platforms, only="codex")
    problems = gen.check(artifacts)
    assert problems == [], "\n".join(problems)


def test_full_check_includes_agents_md_only():
    platforms = gen.load_platforms()
    artifacts = gen.render_all(platforms)
    problems = gen.check(artifacts)
    assert problems == [], "\n".join(problems)
    paths = {a.path for a in artifacts}
    assert "graphify/always_on/agents-md.md" in paths
    assert "graphify/always_on/claude-md.md" not in paths


def test_render_is_idempotent():
    platforms = gen.load_platforms()
    first = gen.render_all(platforms, only="codex")
    second = gen.render_all(platforms, only="codex")
    assert [(a.path, a.content) for a in first] == [(a.path, a.content) for a in second]


def test_render_output_is_lf_only():
    platforms = gen.load_platforms()
    for art in gen.render_all(platforms, only="codex"):
        assert "\r" not in art.content, art.path
        assert art.content.endswith("\n"), art.path
        assert not art.content.endswith("\n\n"), art.path


def test_no_version_or_timestamp_in_output():
    from graphify.__main__ import __version__

    platforms = gen.load_platforms()
    for art in gen.render_all(platforms, only="codex"):
        assert __version__ not in art.content, f"{art.path} leaked a version string"


def test_descriptions_are_unified():
    expected_line = f'description: "{UNIFIED_DESCRIPTION}"'
    platforms = gen.load_platforms()
    for key, platform in platforms.items():
        body = gen.render(platform)[0].content
        assert expected_line in body, f"[{key}] missing the unified description line"


def test_codex_dispatch_is_agenttask_and_collects_in_memory():
    core, _ = _codex_artifacts()
    assert "spawn_agent" in core
    assert "wait_agent" in core
    assert "close_agent" in core
    assert "multi_agent = true" in core
    assert "Codex collects in memory" in core
    b2 = core[core.index("**Step B2"):core.index("**Step B3")]
    assert "Concrete example for 3 chunks" not in b2
    assert "Agent tool call 1" not in b2


def test_codex_uses_compact_extraction_and_six_value_enum():
    _, refs = _codex_artifacts()
    spec = refs["extraction-spec.md"]
    assert "(compact)" in spec
    assert "`code`, `document`, `paper`, `image`, `rationale`, `concept`" in spec
    assert '"file_type":"code|document|paper|image|rationale|concept"' in spec
    for body in refs.values():
        assert '"file_type":"code|document|paper|image"' not in body


def test_codex_hooks_are_agents_md():
    core, refs = _codex_artifacts()
    assert "native AGENTS.md integration" in core
    assert "native CLAUDE.md integration" not in core
    hooks = refs["hooks.md"]
    assert "AGENTS.md" in hooks
    assert "graphify install --project" in hooks
    assert "graphify claude install" not in hooks
    assert "CLAUDE.md" not in hooks


def test_always_on_blocks_are_agents_md_only():
    assert list(gen.ALWAYS_ON_BLOCKS) == ["agents-md"]


def test_schema_singleton_passes():
    platforms = gen.load_platforms()
    problems = gen.schema_singleton(platforms)
    assert problems == [], "\n".join(problems)


def test_monolith_roundtrip_is_empty_without_monoliths():
    platforms = gen.load_platforms()
    assert all(p.bucket != "monolith" for p in platforms.values())
    problems = []
    for platform in platforms.values():
        problems.extend(gen.monolith_roundtrip(platform))
    assert problems == []
