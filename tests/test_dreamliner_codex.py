"""Dreamliner Codex-only install/run path."""
from pathlib import Path
from unittest.mock import patch

import pytest


def test_cli_install_defaults_to_codex(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["graphify", "install"])
    with patch("graphify.__main__.Path.home", return_value=home):
        with patch("graphify.install.Path.home", return_value=home):
            main()
    assert (home / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
    assert not (home / ".claude" / "skills" / "graphify" / "SKILL.md").exists()


def test_cli_install_platform_claude_is_gated(tmp_path, monkeypatch, capsys):
    from graphify.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["graphify", "install", "--platform", "claude"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Dreamliner is Codex-only" in err
    assert "graphify install --platform codex" in err


def test_cli_cursor_install_is_gated(tmp_path, monkeypatch, capsys):
    from graphify.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["graphify", "cursor", "install"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert "Dreamliner is Codex-only" in capsys.readouterr().err


def test_help_is_codex_only(capsys):
    from graphify.__main__ import main
    import sys

    with patch.object(sys, "argv", ["graphify", "--help"]):
        main()
    out = capsys.readouterr().out
    assert "Dreamliner" in out
    assert "$dreamliner" in out
    assert "graphify install --platform codex" in out
    assert "claude install" not in out
    assert "cursor install" not in out
    assert "gemini install" not in out


def test_check_codex_prerequisites_missing_cli(monkeypatch):
    from graphify.install import check_codex_prerequisites

    monkeypatch.setattr("graphify.install.shutil.which", lambda _name: None)
    problems = check_codex_prerequisites()
    assert problems
    assert "Codex CLI not found" in problems[0]
    assert "codex --version" in problems[0]


def test_check_codex_prerequisites_bad_config(tmp_path, monkeypatch):
    from graphify.install import check_codex_prerequisites

    home = tmp_path / "home"
    cfg = home / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[features]\nmulti_agent = false\n", encoding="utf-8")
    monkeypatch.setattr("graphify.install.shutil.which", lambda _name: "/usr/bin/codex")
    monkeypatch.setattr("graphify.install.Path.home", lambda: home)
    problems = check_codex_prerequisites()
    assert any("multi_agent" in p for p in problems)
    assert any("[features]" in p for p in problems)


def test_check_codex_prerequisites_ok(tmp_path, monkeypatch):
    from graphify.install import check_codex_prerequisites

    home = tmp_path / "home"
    cfg = home / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[features]\nmulti_agent = true\n", encoding="utf-8")
    monkeypatch.setattr("graphify.install.shutil.which", lambda _name: "/usr/bin/codex")
    monkeypatch.setattr("graphify.install.Path.home", lambda: home)
    assert check_codex_prerequisites() == []


def test_refuse_to_modify_hooks_json_is_actionable(tmp_path, capsys):
    from graphify.install import _install_codex_hook

    hooks = tmp_path / ".codex" / "hooks.json"
    hooks.parent.mkdir(parents=True)
    hooks.write_text("not-json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _install_codex_hook(tmp_path)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Dreamliner will not overwrite" in err
    assert "not valid JSON" in err
    assert "graphify install --platform codex" in err


def test_format_validation_failure_is_actionable():
    from graphify.validate import format_validation_failure, validate_extraction

    errors = validate_extraction({"nodes": "bad"})
    assert errors
    msg = format_validation_failure(errors)
    assert msg.startswith("error: Dreamliner validation failed")
    assert "nodes[]" in msg
    assert "re-run" in msg
    assert "•" in msg


def test_assert_valid_behavior_unchanged():
    from graphify.validate import assert_valid, validate_extraction

    valid = {
        "nodes": [
            {"id": "a", "label": "A", "file_type": "code", "source_file": "a.py"},
        ],
        "edges": [
            {
                "source": "a",
                "target": "a",
                "relation": "mentions",
                "confidence": "EXTRACTED",
                "source_file": "a.py",
            }
        ],
    }
    assert validate_extraction(valid) == []
    assert_valid(valid)
    with pytest.raises(ValueError, match="Extraction JSON has"):
        assert_valid({"nodes": "bad"})


def test_codex_config_parser_features_table():
    from graphify.install import _codex_multi_agent_enabled

    assert _codex_multi_agent_enabled("[features]\nmulti_agent = true\n")
    assert not _codex_multi_agent_enabled("[features]\nmulti_agent = false\n")
    assert not _codex_multi_agent_enabled("[other]\nmulti_agent = true\n")
