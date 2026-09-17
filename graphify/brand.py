"""Dreamliner user-facing brand constants.

The Python import path remains ``graphify`` (and the PyPI name remains
``graphifyy``) so AST extraction, validation, and existing graphs keep working.
Everything an end user types or reads — CLI, skill invoke, AGENTS.md, install
UX — is Dreamliner / ``dreamliner`` / ``$dreamliner``.
"""

from __future__ import annotations

PRODUCT = "Dreamliner"
CLI = "dreamliner"
SKILL = "dreamliner"
INVOKE = "$dreamliner"
# Leftover internal identifiers — called out in the PR, not renamed this pass.
PYPI_PACKAGE = "graphifyy"
MODULE = "graphify"
OUT_DIR = "graphify-out"

# First-class host for this variant. Other historical installers stay in
# graphify.install for uninstall-of-old-copies and internal tests, but are
# gated on the Dreamliner CLI surface.
FIRST_CLASS_PLATFORMS = frozenset({"codex"})


def cli_name(argv0: str | None = None) -> str:
    """Prefer the actual launcher name when it is already ``dreamliner``."""
    if argv0:
        base = argv0.replace("\\", "/").rsplit("/", 1)[-1]
        if base.startswith("dreamliner"):
            return "dreamliner"
    return CLI
