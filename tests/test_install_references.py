"""Tests for the Codex progressive-disclosure references/ sidecar."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import graphify
import graphify.__main__ as mainmod


PKG_DIR = Path(graphify.__file__).parent


@pytest.fixture()
def fake_bundle():
    """Stage a fake references/ bundle in Codex's slot, then restore the real one."""
    platform = "codex"
    bundle = mainmod._PLATFORM_CONFIG[platform]["skill_refs"]
    skills_root = PKG_DIR / "skills"
    bundle_dir = skills_root / bundle
    refs_dir = bundle_dir / "references"

    created_root = not skills_root.exists()
    backup_dir = None
    if bundle_dir.exists():
        backup_dir = Path(tempfile.mkdtemp()) / "bundle_backup"
        shutil.move(str(bundle_dir), str(backup_dir))

    refs_dir.mkdir(parents=True, exist_ok=True)
    (refs_dir / "extraction-spec.md").write_text("# extraction spec fragment\n", encoding="utf-8")
    (refs_dir / "query.md").write_text("# query fragment\n", encoding="utf-8")
    try:
        yield platform
    finally:
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir, ignore_errors=True)
        if backup_dir is not None:
            shutil.move(str(backup_dir), str(bundle_dir))
            shutil.rmtree(backup_dir.parent, ignore_errors=True)
        elif created_root:
            shutil.rmtree(skills_root, ignore_errors=True)


def _install(tmp_path, platform):
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with patch("graphify.__main__.Path.home", return_value=tmp_path):
            mainmod.install(platform=platform)
    finally:
        os.chdir(old_cwd)


def test_install_stages_references_sidecar(tmp_path, fake_bundle):
    platform = fake_bundle
    _install(tmp_path, platform)
    skill_dir = tmp_path / ".codex" / "skills" / "graphify"
    assert (skill_dir / "SKILL.md").exists()
    refs = skill_dir / "references"
    assert refs.is_dir()
    assert (refs / "extraction-spec.md").read_text() == "# extraction spec fragment\n"
    assert (refs / "query.md").read_text() == "# query fragment\n"
    assert not (skill_dir / "references.tmp").exists()


def test_single_version_stamp_covers_skill_and_references(tmp_path, fake_bundle):
    platform = fake_bundle
    _install(tmp_path, platform)
    skill_dir = tmp_path / ".codex" / "skills" / "graphify"
    stamps = list(skill_dir.rglob(".graphify_version"))
    assert len(stamps) == 1
    assert stamps[0] == skill_dir / ".graphify_version"
    assert stamps[0].read_text() == mainmod.__version__


def test_reinstall_replaces_references_atomically(tmp_path, fake_bundle):
    platform = fake_bundle
    _install(tmp_path, platform)
    skill_dir = tmp_path / ".codex" / "skills" / "graphify"
    refs = skill_dir / "references"
    (refs / "stale-old.md").write_text("stale\n", encoding="utf-8")
    _install(tmp_path, platform)
    assert not (refs / "stale-old.md").exists()
    assert (refs / "extraction-spec.md").exists()
    assert (refs / "query.md").exists()


def test_uninstall_removes_references_then_walks_dirs(tmp_path, fake_bundle):
    platform = fake_bundle
    _install(tmp_path, platform)
    skill_dir = tmp_path / ".codex" / "skills" / "graphify"
    assert (skill_dir / "references").is_dir()
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        removed = mainmod._remove_skill_file(platform)
    assert removed
    assert not skill_dir.exists()
    assert not (tmp_path / ".codex" / "skills").exists()


def test_check_skill_version_warns_on_missing_references(tmp_path, fake_bundle, capsys):
    platform = fake_bundle
    _install(tmp_path, platform)
    skill_dir = tmp_path / ".codex" / "skills" / "graphify"
    skill = skill_dir / "SKILL.md"
    skill.write_text("See references/extraction-spec.md for the schema.\n", encoding="utf-8")
    shutil.rmtree(skill_dir / "references")
    mainmod._check_skill_version(skill)
    err = capsys.readouterr().err
    assert "references/ sidecar is missing" in err


def test_hard_fail_when_bundle_dir_present_but_references_missing(tmp_path, monkeypatch):
    platform = "codex"
    bundle = mainmod._PLATFORM_CONFIG[platform]["skill_refs"]
    skills_root = PKG_DIR / "skills"
    bundle_dir = skills_root / bundle
    backup_dir = None
    if bundle_dir.exists():
        backup_dir = Path(tempfile.mkdtemp()) / "bundle_backup"
        shutil.move(str(bundle_dir), str(backup_dir))
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "SKILL.md").write_text("body\n", encoding="utf-8")
    try:
        with pytest.raises(SystemExit) as exc:
            with patch("graphify.__main__.Path.home", return_value=tmp_path):
                monkeypatch.chdir(tmp_path)
                mainmod._copy_skill_file("codex")
        assert exc.value.code == 1
    finally:
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir, ignore_errors=True)
        if backup_dir is not None:
            shutil.move(str(backup_dir), str(bundle_dir))
            shutil.rmtree(backup_dir.parent, ignore_errors=True)


def test_codex_install_ships_lean_core_and_references(tmp_path):
    skills_codex = PKG_DIR / "skills" / "codex" / "references"
    assert skills_codex.is_dir(), "codex bundle must ship in this build"
    _install(tmp_path, "codex")
    skill_dir = tmp_path / ".codex" / "skills" / "graphify"
    skill = skill_dir / "SKILL.md"
    refs = skill_dir / "references"
    assert skill.exists()
    assert refs.is_dir()
    body = skill.read_text(encoding="utf-8")
    assert body == (PKG_DIR / "skill-codex.md").read_text(encoding="utf-8")
    assert "references/extraction-spec.md" in body
    assert '"file_type":"code|document|paper|image|rationale|concept"' not in body
    assert len(body.splitlines()) < 800
    assert (skill_dir / ".graphify_version").read_text() == mainmod.__version__
    names = sorted(p.name for p in refs.glob("*.md"))
    assert names == [
        "add-watch.md",
        "exports.md",
        "extraction-spec.md",
        "github-and-merge.md",
        "hooks.md",
        "query.md",
        "transcribe.md",
        "update.md",
    ]


def test_pyproject_declares_codex_package_data():
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    pyproject = PKG_DIR.parent / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("pyproject.toml not adjacent to package (installed wheel)")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    pkg_data = data["tool"]["setuptools"]["package-data"]["graphify"]
    assert "skill-codex.md" in pkg_data
    assert "skills/codex/references/*.md" in pkg_data
    assert "always_on/agents-md.md" in pkg_data
    assert "skills/*/SKILL.md" not in pkg_data


def test_codex_references_resolve(tmp_path):
    import re

    _install(tmp_path, "codex")
    skill = tmp_path / ".codex" / "skills" / "graphify" / "SKILL.md"
    assert skill.exists()
    refdir = skill.parent / "references"
    assert refdir.is_dir()
    pointers = set(re.findall(r"references/([a-z-]+\.md)", skill.read_text(encoding="utf-8")))
    assert pointers
    missing = [p for p in pointers if not (refdir / p).is_file()]
    assert not missing, f"dead reference pointers in Codex install: {missing}"
