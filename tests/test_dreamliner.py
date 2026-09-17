"""Dreamliner Codex-only surface: brand, install default, host gate, doctor, validate."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from graphify.brand import CLI, FIRST_CLASS_PLATFORMS, INVOKE, PRODUCT
from graphify.doctor import (
    DreamlinerError,
    _toml_has_multi_agent,
    check_codex_config,
    check_codex_ready,
    require_usable_graph,
    run_doctor,
)
from graphify.validate import assert_valid, validate_extraction


def test_brand_constants():
    assert PRODUCT == "Dreamliner"
    assert CLI == "dreamliner"
    assert INVOKE == "$dreamliner"
    assert FIRST_CLASS_PLATFORMS == frozenset({"codex"})


def test_install_default_platform_is_codex():
    import inspect
    from graphify.install import install

    assert inspect.signature(install).parameters["platform"].default == "codex"


@pytest.mark.parametrize("argv", [
    ["dreamliner", "install", "--platform", "claude"],
    ["dreamliner", "install", "--platform", "cursor"],
    ["dreamliner", "install", "--platform", "gemini"],
    ["dreamliner", "claude", "install"],
    ["dreamliner", "cursor", "install"],
    ["dreamliner", "gemini", "install"],
])
def test_cli_gates_legacy_hosts(tmp_path, monkeypatch, argv):
    from graphify.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".cursor").exists()
    assert not (tmp_path / ".gemini").exists()


def test_cli_install_help_is_codex_only(tmp_path, monkeypatch, capsys):
    from graphify.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["dreamliner", "install", "--help"])
    main()
    out = capsys.readouterr().out
    assert "Usage: dreamliner install" in out
    assert "codex" in out
    assert "Claude Code" in out or "not first-class" in out


def test_toml_multi_agent_parser():
    assert _toml_has_multi_agent("[features]\nmulti_agent = true\n")
    assert _toml_has_multi_agent("[features]\n# comment\nmulti_agent = true\n")
    assert not _toml_has_multi_agent("[features]\nmulti_agent = false\n")
    assert not _toml_has_multi_agent("[other]\nmulti_agent = true\n")
    assert not _toml_has_multi_agent("")


def test_check_codex_config_missing_and_incomplete(tmp_path):
    problems = check_codex_config(home=tmp_path)
    assert problems
    assert "multi_agent = true" in problems[0]

    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[features]\nfoo = 1\n", encoding="utf-8")
    problems = check_codex_config(home=tmp_path)
    assert problems
    assert "multi_agent = true" in problems[0]

    cfg.write_text("[features]\nmulti_agent = true\n", encoding="utf-8")
    assert check_codex_config(home=tmp_path) == []


def test_check_codex_ready_missing_cli(tmp_path, monkeypatch):
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[features]\nmulti_agent = true\n", encoding="utf-8")
    monkeypatch.setattr("graphify.doctor.find_codex_cli", lambda: None)
    problems = check_codex_ready(home=tmp_path, require_cli=True)
    assert any("Codex CLI not found" in p for p in problems)


def test_require_usable_graph_missing_empty_invalid(tmp_path):
    missing = tmp_path / "graphify-out" / "graph.json"
    with pytest.raises(DreamlinerError):
        require_usable_graph(missing)

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
    with pytest.raises(DreamlinerError):
        require_usable_graph(empty)

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(DreamlinerError):
        require_usable_graph(bad)


def test_require_usable_graph_ok(tmp_path):
    graph = tmp_path / "graph.json"
    payload = {
        "nodes": [{"id": "n1", "label": "N", "file_type": "code", "source_file": "a.py"}],
        "edges": [],
    }
    graph.write_text(json.dumps(payload), encoding="utf-8")
    loaded = require_usable_graph(graph)
    assert loaded["nodes"][0]["id"] == "n1"


def test_validate_extraction_api_unchanged():
    good = {
        "nodes": [{"id": "n1", "label": "N", "file_type": "code", "source_file": "a.py"}],
        "edges": [{
            "source": "n1",
            "target": "n1",
            "relation": "defines",
            "confidence": "EXTRACTED",
            "source_file": "a.py",
        }],
    }
    assert validate_extraction(good) == []
    assert_valid(good)

    bad = {"nodes": [{"id": "n1"}], "edges": []}
    errors = validate_extraction(bad)
    assert errors
    with pytest.raises(ValueError):
        assert_valid(bad)


def test_validate_cli_ok_and_missing(tmp_path, monkeypatch, capsys):
    from graphify.__main__ import main

    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({
        "nodes": [{"id": "n1", "label": "N", "file_type": "code", "source_file": "a.py"}],
        "edges": [],
    }), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["dreamliner", "validate", str(graph)])
    main()
    assert "validation OK" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["dreamliner", "validate", str(tmp_path / "nope.json")])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "nothing to validate" in err
    assert "Dreamliner" in err


def test_doctor_reports_missing_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("graphify.doctor.find_codex_cli", lambda: "/usr/bin/codex")
    monkeypatch.chdir(tmp_path)
    code = run_doctor(home=tmp_path, graph=tmp_path / "graphify-out" / "graph.json")
    assert code == 1
    err = capsys.readouterr().err
    assert "multi_agent = true" in err


def test_query_empty_graph_is_actionable(tmp_path, monkeypatch, capsys):
    from graphify.__main__ import main

    out = tmp_path / "graphify-out"
    out.mkdir()
    (out / "graph.json").write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["dreamliner", "query", "how does install work?"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "empty" in err.lower() or "no nodes" in err.lower()
    assert "Dreamliner" in err
    assert "Traceback" not in err


def test_help_branding(monkeypatch, capsys):
    from graphify.__main__ import main

    monkeypatch.setattr(sys, "argv", ["dreamliner", "--help"])
    main()
    out = capsys.readouterr().out
    assert "Dreamliner" in out
    assert "doctor" in out
    assert "validate" in out
    assert "codex install" in out
    assert "$dreamliner" in out or "dreamliner" in out
