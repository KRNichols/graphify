"""Scope regression tests for Codex uninstall (#2215)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from graphify.install import _project_uninstall, _remove_skill_file


def _plant_skill_tree(root: Path) -> Path:
    skill_dir = root / ".codex" / "skills" / "graphify"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# graphify skill\n", encoding="utf-8")
    (skill_dir / "references" / "x.md").write_text("ref\n", encoding="utf-8")
    (skill_dir / ".graphify_version").write_text("0.0.0-test", encoding="utf-8")
    return skill_dir


def test_project_uninstall_never_touches_global(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    proj_dir = tmp_path / "proj"
    global_tree = _plant_skill_tree(home)
    project_tree = _plant_skill_tree(proj_dir)
    monkeypatch.chdir(proj_dir)
    with patch("graphify.install.Path.home", return_value=home):
        _project_uninstall("codex", proj_dir)

    assert (global_tree / "SKILL.md").exists()
    assert (global_tree / "references" / "x.md").exists()
    assert not (project_tree / "SKILL.md").exists()


def test_global_remove_still_clears_user_skill(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    global_tree = _plant_skill_tree(home)
    monkeypatch.chdir(tmp_path)
    with patch("graphify.install.Path.home", return_value=home):
        removed = _remove_skill_file("codex", project=False)
    assert removed
    assert not (global_tree / "SKILL.md").exists()
