"""Regression test for #2694 (version-stamp half).

`graphify install --platform X` must only advance `.graphify_version` for the
platform whose skill content it actually (re)writes. Previously it also bumped
the stamp of every *other* already-installed platform, so a platform whose
SKILL.md was left untouched carried a current stamp and its "skill is from
graphify A, package is B" staleness warning was suppressed even though the
content really was stale.
"""
from __future__ import annotations

from unittest.mock import patch

import graphify.__main__ as mainmod

# A prior graphify version stamped into an unrelated, not-reinstalled platform.
_STALE_STAMP = "0.0.1-old"


def test_install_does_not_bump_other_platforms_stamp(tmp_path, monkeypatch):
    """Installing one platform must leave a different, already-installed
    platform's `.graphify_version` untouched, so its staleness warning stays
    truthful (#2694)."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mainmod, "_check_skill_version", lambda _: None)

    with patch("pathlib.Path.home", return_value=home):
        leftover = home / ".claude" / "skills" / "graphify"
        leftover.mkdir(parents=True, exist_ok=True)
        leftover_stamp = leftover / ".graphify_version"
        leftover_stamp.write_text(_STALE_STAMP, encoding="utf-8")
        (leftover / "SKILL.md").write_text("leftover non-Codex skill", encoding="utf-8")

        # This variant only installs Codex. A leftover host dir must keep
        # its stale stamp so its refresh warning still fires (#2694).
        mainmod.install("codex")

        installed = mainmod._platform_skill_destination("codex", project=False)
        assert (installed.parent / ".graphify_version").read_text() == mainmod.__version__
        assert leftover_stamp.read_text() == _STALE_STAMP, (
            "installing Codex must not advance a leftover host's version stamp (#2694)"
        )


def test_stale_untouched_platform_still_emits_warning(tmp_path, monkeypatch, capsys):
    """End-to-end (#2694): after installing one platform, a different stale
    platform must actually EMIT the staleness warning — the behavior the
    over-stamping bug suppressed."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    real_check = mainmod._check_skill_version  # keep the real warner for the assertion

    with patch("pathlib.Path.home", return_value=home):
        stale_skill = mainmod._platform_skill_destination("codex", project=False)
        stale_skill.parent.mkdir(parents=True, exist_ok=True)
        stale_skill.write_text("stale skill body", encoding="utf-8")
        (stale_skill.parent / ".graphify_version").write_text(_STALE_STAMP, encoding="utf-8")

        # Fresh install overwrites the skill but we re-stamp the old
        # version to simulate an untouched leftover copy, then warn.
        with patch.object(mainmod, "_check_skill_version", lambda _: None):
            mainmod.install("codex")
        (stale_skill.parent / ".graphify_version").write_text(_STALE_STAMP, encoding="utf-8")

        capsys.readouterr()  # drop install output
        real_check(stale_skill)

    err = capsys.readouterr().err
    assert _STALE_STAMP in err and "update" in err, (
        f"stale codex platform should warn, got stderr: {err!r}"
    )
