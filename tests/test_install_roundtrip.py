"""Codex install + uninstall round-trip."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import graphify
import graphify.__main__ as mainmod


PKG_DIR = Path(graphify.__file__).parent


def test_codex_skill_roundtrip_user_and_project(tmp_path, monkeypatch):
    home = tmp_path / "home"
    project_dir = tmp_path / "proj"
    home.mkdir()
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    with patch("graphify.__main__.Path.home", return_value=home):
        for project in (False, True):
            dst = mainmod._platform_skill_destination(
                "codex", project=project, project_dir=project_dir
            )
            if project:
                assert str(dst).startswith(str(project_dir))
            else:
                assert str(dst).startswith(str(home))

            returned = mainmod._copy_skill_file(
                "codex", project=project, project_dir=project_dir
            )
            assert returned == dst
            assert dst.exists()
            assert (dst.parent / ".graphify_version").read_text() == mainmod.__version__
            refs = dst.parent / "references"
            assert refs.is_dir()
            assert (refs / "extraction-spec.md").exists()

            removed = mainmod._remove_skill_file(
                "codex", project=project, project_dir=project_dir
            )
            assert removed
            assert not dst.exists()
            assert not (dst.parent / ".graphify_version").exists()
            assert not refs.exists()


def test_install_entrypoint_roundtrip_codex(tmp_path):
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with patch("graphify.__main__.Path.home", return_value=tmp_path):
            mainmod.install(platform="codex")
            skill_dir = tmp_path / ".codex" / "skills" / "graphify"
            assert (skill_dir / "SKILL.md").exists()
            assert (skill_dir / "references").is_dir()
            mainmod._remove_skill_file("codex")
            assert not (skill_dir / "SKILL.md").exists()
    finally:
        os.chdir(old_cwd)
