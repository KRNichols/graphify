"""Regression test for #2694 (version-stamp half) on the Codex-only surface."""
from __future__ import annotations

from unittest.mock import patch

import graphify.__main__ as mainmod

_STALE_STAMP = "0.0.1-old"


def test_gated_install_does_not_bump_codex_stamp(tmp_path, monkeypatch):
    """A rejected non-Codex install must not advance the Codex version stamp."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mainmod, "_check_skill_version", lambda _: None)

    with patch("graphify.__main__.Path.home", return_value=home):
        codex_skill = mainmod._platform_skill_destination("codex", project=False)
        codex_skill.parent.mkdir(parents=True, exist_ok=True)
        codex_skill.write_text("stale skill body", encoding="utf-8")
        codex_stamp = codex_skill.parent / ".graphify_version"
        codex_stamp.write_text(_STALE_STAMP, encoding="utf-8")

        try:
            mainmod.install("claude")
        except SystemExit:
            pass

        assert codex_stamp.read_text() == _STALE_STAMP


def test_stale_codex_skill_still_emits_warning(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    real_check = mainmod._check_skill_version

    with patch("graphify.__main__.Path.home", return_value=home):
        codex_skill = mainmod._platform_skill_destination("codex", project=False)
        codex_skill.parent.mkdir(parents=True, exist_ok=True)
        codex_skill.write_text("stale skill body", encoding="utf-8")
        (codex_skill.parent / ".graphify_version").write_text(_STALE_STAMP, encoding="utf-8")

        capsys.readouterr()
        real_check(codex_skill)

    err = capsys.readouterr().err
    assert _STALE_STAMP in err and "update" in err
