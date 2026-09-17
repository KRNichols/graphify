"""Dreamliner Codex-only branding, install gating, and CLI failure modes."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from graphify.brand import (
    CLI,
    PRODUCT,
    SKILL,
    TRIGGER,
    empty_graph_message,
    missing_binary_message,
    missing_codex_cli_message,
    missing_graph_message,
    unsupported_host_message,
)


def test_brand_constants():
    assert PRODUCT == "Dreamliner"
    assert SKILL == "dreamliner"
    assert CLI == "dreamliner"
    assert TRIGGER == "$dreamliner"


def test_user_facing_error_copy_is_actionable():
    missing = missing_graph_message("/tmp/graphify-out/graph.json")
    assert "Dreamliner" in missing
    assert "$dreamliner" in missing or "dreamliner extract" in missing
    empty = empty_graph_message("/tmp/graph.json")
    assert "empty" in empty
    assert "rebuild" in empty.lower() or "extract" in empty
    binary = missing_binary_message()
    assert "uv tool install" in binary
    host = unsupported_host_message("claude")
    assert "Codex-only" in host
    assert "claude" in host


def _install(tmp_path, platform="codex", **kwargs):
    from graphify.install import install

    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        with patch("graphify.install.Path.home", return_value=tmp_path):
            install(platform=platform, **kwargs)
    finally:
        os.chdir(old)


def test_install_default_is_codex_dreamliner(tmp_path):
    _install(tmp_path)
    skill = tmp_path / ".codex" / "skills" / "dreamliner" / "SKILL.md"
    assert skill.exists()
    body = skill.read_text(encoding="utf-8")
    assert body.startswith("---\nname: dreamliner\n")
    assert "$dreamliner" in body
    assert "name: dreamliner" in body
    assert "Claude Code, Cursor, Gemini CLI" not in body
    refs = tmp_path / ".codex" / "skills" / "dreamliner" / "references"
    assert (refs / "query.md").exists()
    agents = tmp_path / "AGENTS.md"
    assert agents.exists()
    assert "## Dreamliner" in agents.read_text(encoding="utf-8")


def test_install_rejects_claude_cursor_gemini(tmp_path, capsys):
    from graphify.install import install

    for host in ("claude", "cursor", "gemini", "windows"):
        with pytest.raises(SystemExit) as exc:
            _install(tmp_path, platform=host)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "Codex-only" in err
        assert host in err
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".cursor").exists()
    assert not (tmp_path / ".gemini").exists()


def test_cli_install_defaults_to_codex(tmp_path, monkeypatch, capsys):
    import graphify.__main__ as mainmod

    monkeypatch.setattr(mainmod, "_check_skill_version", lambda *a, **k: None)
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        with patch("graphify.install.Path.home", return_value=tmp_path):
            monkeypatch.setattr(mainmod.sys, "argv", ["dreamliner", "install"])
            mainmod.main()
    finally:
        os.chdir(old)
    assert (tmp_path / ".codex" / "skills" / "dreamliner" / "SKILL.md").exists()
    out = capsys.readouterr().out
    assert "$dreamliner" in out


def test_cli_rejects_claude_install(tmp_path, monkeypatch, capsys):
    import graphify.__main__ as mainmod

    monkeypatch.setattr(mainmod, "_check_skill_version", lambda *a, **k: None)
    monkeypatch.setattr(mainmod.sys, "argv", ["dreamliner", "claude", "install"])
    with pytest.raises(SystemExit) as exc:
        mainmod.main()
    assert exc.value.code == 1
    assert "Codex-only" in capsys.readouterr().err


def _run_cli(monkeypatch, argv):
    import graphify.__main__ as mainmod

    monkeypatch.setattr(mainmod, "_check_skill_version", lambda *a, **k: None)
    monkeypatch.setattr(mainmod.sys, "argv", argv)
    mainmod.main()


def test_query_missing_graph_is_actionable(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "nope.json"
    with pytest.raises(SystemExit) as exc:
        _run_cli(monkeypatch, ["dreamliner", "query", "auth", "--graph", str(missing)])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "no Dreamliner graph found" in err
    assert "dreamliner" in err


def test_query_empty_graph_is_actionable(monkeypatch, tmp_path, capsys):
    gp = tmp_path / "graph.json"
    gp.write_text(json.dumps({"directed": False, "nodes": [], "links": []}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _run_cli(monkeypatch, ["dreamliner", "query", "auth", "--graph", str(gp)])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "empty" in err
    assert "Dreamliner" in err


def test_query_corrupt_graph_is_actionable(monkeypatch, tmp_path, capsys):
    gp = tmp_path / "graph.json"
    gp.write_text("{not-json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _run_cli(monkeypatch, ["dreamliner", "query", "auth", "--graph", str(gp)])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "could not load graph" in err
    assert "Dreamliner" in err
    assert "rebuild" in err.lower() or "force" in err


def test_cli_help_is_codex_only(monkeypatch, capsys):
    import graphify.__main__ as mainmod

    monkeypatch.setattr(mainmod, "_check_skill_version", lambda *a, **k: None)
    monkeypatch.setattr(mainmod.sys, "argv", ["dreamliner", "--help"])
    mainmod.main()
    out = capsys.readouterr().out
    assert "Usage: dreamliner" in out
    assert "Codex Dreamliner skill" in out
    assert "claude|windows" not in out
    assert "$dreamliner" in out or "dreamliner" in out
    assert "Claude Code" not in out
    assert "Gemini CLI" not in out
    assert "cursor install" not in out


def test_skill_codex_has_no_multi_host_leftovers():
    skill = Path(__file__).resolve().parents[1] / "graphify" / "skill-codex.md"
    text = skill.read_text(encoding="utf-8")
    assert "name: dreamliner" in text
    assert "$dreamliner" in text
    assert "Claude Code" not in text
    assert "Gemini CLI" not in text
    assert "GEMINI_API_KEY" not in text
    assert "graphifyy[gemini]" not in text
    assert "graphify cursor install" not in text
    assert "graphify gemini install" not in text
    assert "Works in" not in text
    assert "ERROR: Dreamliner is not installed" in text
    assert "multi_agent = true" in text
    assert "### Step 1 - Ensure Dreamliner is installed" in text
    assert "### Step 1 - Ensure graphify is installed" not in text
    assert "uv tool run --from graphifyy" not in text
    assert "pip install graphifyy" not in text
    assert "pip install dreamliner" not in text
    assert "uv tool install --upgrade dreamliner" not in text
    assert "git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833" in text
    leftover = Path(__file__).resolve().parents[1] / "graphify" / "command-kilo.md"
    assert not leftover.exists()


def test_readme_has_clean_machine_runbook():
    readme = Path(__file__).resolve().parents[1] / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "# Dreamliner" in text
    assert "Clean machine (copy-paste)" in text
    assert "dreamliner doctor" in text
    assert "codex --version" in text
    assert "multi_agent = true" in text
    assert "$dreamliner" in text
    assert "/graphify ." not in text
    assert "Claude Code, Cursor, Gemini CLI" in text  # named only as unsupported
    assert "git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833" in text
    assert "uv tool install git+https://github.com/KRNichols/graphify\n" not in text


def test_doctor_fails_on_missing_codex_and_bad_config(tmp_path, capsys):
    from graphify.doctor import doctor

    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml").write_text("[[[not toml", encoding="utf-8")
    with patch("graphify.doctor.shutil.which", return_value=None):
        rc = doctor(home=tmp_path, cwd=tmp_path, require_graph=False)
    assert rc == 1
    err = capsys.readouterr().err
    assert "Codex CLI not found" in err
    assert "invalid" in err.lower() or "TOML" in err
    assert "Dreamliner is not ready" in err


def test_doctor_passes_when_codex_skill_and_config_exist(tmp_path, capsys):
    from graphify.doctor import doctor

    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir()
    cfg.write_text("[features]\nmulti_agent = true\n", encoding="utf-8")
    skill = tmp_path / ".codex" / "skills" / "dreamliner" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: dreamliner\n---\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "codex").write_text("", encoding="utf-8")
    (fake_bin / "dreamliner").write_text("", encoding="utf-8")

    def _which(name):
        if name in ("codex", "dreamliner", "graphify"):
            return str(fake_bin / name)
        return None

    with patch("graphify.doctor.shutil.which", side_effect=_which):
        rc = doctor(home=tmp_path, cwd=tmp_path, require_graph=False)
    assert rc == 0
    err = capsys.readouterr().err
    assert "Dreamliner is ready" in err
    assert "multi_agent = true" in err


def test_doctor_graph_flag_fails_on_empty_graph(tmp_path, capsys):
    from graphify.doctor import doctor

    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir()
    cfg.write_text("[features]\nmulti_agent = true\n", encoding="utf-8")
    skill = tmp_path / ".codex" / "skills" / "dreamliner" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("ok", encoding="utf-8")
    gout = tmp_path / "graphify-out"
    gout.mkdir()
    (gout / "graph.json").write_text('{"nodes":[],"links":[]}', encoding="utf-8")

    def _which(name):
        return f"/tmp/{name}"

    with patch("graphify.doctor.shutil.which", side_effect=_which):
        rc = doctor(home=tmp_path, cwd=tmp_path, require_graph=True)
    assert rc == 1
    assert "empty" in capsys.readouterr().err


def test_missing_codex_cli_message_is_actionable():
    msg = missing_codex_cli_message()
    assert "codex" in msg.lower()
    assert "openai.com/codex" in msg


def test_cli_doctor_command(monkeypatch, tmp_path, capsys):
    import graphify.__main__ as mainmod

    monkeypatch.setattr(mainmod, "_check_skill_version", lambda *a, **k: None)
    monkeypatch.setattr(mainmod.sys, "argv", ["dreamliner", "doctor"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("graphify.doctor._home", lambda: tmp_path)
    monkeypatch.setattr("graphify.doctor.shutil.which", lambda name: None)
    with pytest.raises(SystemExit) as exc:
        mainmod.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Dreamliner doctor" in err
    assert "codex-cli" in err
