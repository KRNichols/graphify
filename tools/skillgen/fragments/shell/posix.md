```bash
# Detect the correct Python interpreter (handles uv tool, pipx, venv, system installs)
PYTHON=""
DREAMLINER_BIN=$(command -v dreamliner 2>/dev/null || command -v graphify 2>/dev/null)
# 1. uv tool installs — most reliable on modern Mac/Linux
if [ -z "$PYTHON" ] && command -v uv >/dev/null 2>&1; then
    _UV_PY=$(uv tool run --from dreamliner python -c "import sys; print(sys.executable)" 2>/dev/null)
    if [ -z "$_UV_PY" ]; then
        _UV_PY=$(uv tool run --from git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833 python -c "import sys; print(sys.executable)" 2>/dev/null)
    fi
    if [ -n "$_UV_PY" ]; then PYTHON="$_UV_PY"; fi
fi
# 2. Read shebang from dreamliner/graphify binary (pipx and direct pip installs)
if [ -z "$PYTHON" ] && [ -n "$DREAMLINER_BIN" ]; then
    _SHEBANG=$(head -1 "$DREAMLINER_BIN" | tr -d '#!')
    case "$_SHEBANG" in
        *[!a-zA-Z0-9/_.@-]*) ;;
        *) "$_SHEBANG" -c "import graphify" 2>/dev/null && PYTHON="$_SHEBANG" ;;
    esac
fi
# 3. Fall back to python3
if [ -z "$PYTHON" ]; then PYTHON="python3"; fi
if ! "$PYTHON" -c "import graphify" 2>/dev/null; then
    if command -v uv >/dev/null 2>&1; then
        uv tool install --upgrade git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833 -q 2>&1 | tail -3 \
          || uv tool install --upgrade dreamliner -q 2>&1 | tail -3
        _UV_PY=$(uv tool run --from dreamliner python -c "import sys; print(sys.executable)" 2>/dev/null)
        if [ -z "$_UV_PY" ]; then
            _UV_PY=$(uv tool run --from git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833 python -c "import sys; print(sys.executable)" 2>/dev/null)
        fi
        if [ -n "$_UV_PY" ]; then PYTHON="$_UV_PY"; fi
    else
        "$PYTHON" -m pip install -e . -q 2>/dev/null \
          || "$PYTHON" -m pip install dreamliner -q 2>/dev/null \
          || "$PYTHON" -m pip install dreamliner -q --break-system-packages 2>&1 | tail -3
    fi
fi
if ! "$PYTHON" -c "import graphify" 2>/dev/null; then
    echo "ERROR: Dreamliner is not installed in this environment (cannot import graphify)."
    echo "Install this fork, then retry:"
    echo "  uv tool install git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833"
    echo "  # or from a clone: pip install -e ."
    echo "Then run: dreamliner install"
    echo "and restart Codex."
    exit 1
fi
# Write interpreter path for all subsequent steps (persists across invocations)
mkdir -p graphify-out
"$PYTHON" -c "import sys; open('graphify-out/.graphify_python', 'w', encoding='utf-8').write(sys.executable)"
# Save scan root so `dreamliner update` (no args) knows where to look next time
if ! ROOT_DIR="$(cd INPUT_PATH && pwd)"; then
    echo "ERROR: Dreamliner cannot open INPUT_PATH. Check that the path exists and is a directory."
    exit 1
fi
echo "$ROOT_DIR" > graphify-out/.graphify_root
```

If the import succeeds, print nothing and move straight to Step 2. If the block printed `ERROR:` and exited, stop and show that message to the user — do not continue.

**In every subsequent bash block, replace `python3` with `$(cat graphify-out/.graphify_python)` to use the correct interpreter.**
