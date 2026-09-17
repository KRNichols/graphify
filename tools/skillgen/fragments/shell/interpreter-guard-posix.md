```bash
if [ ! -f graphify-out/.graphify_python ]; then
    DREAMLINER_BIN=$(command -v dreamliner 2>/dev/null || command -v graphify 2>/dev/null)
    if [ -n "$DREAMLINER_BIN" ]; then
        PYTHON=$(head -1 "$DREAMLINER_BIN" | tr -d '#!')
        case "$PYTHON" in *[!a-zA-Z0-9/_.@-]*) PYTHON="python3" ;; esac
    else
        PYTHON="python3"
    fi
    if ! "$PYTHON" -c "import graphify" 2>/dev/null; then
        echo "ERROR: Dreamliner is not installed (cannot import graphify)."
        echo "Install this fork: uv tool install git+https://github.com/KRNichols/graphify"
        echo "Then run: dreamliner install"
        exit 1
    fi
    mkdir -p graphify-out
    "$PYTHON" -c "import sys; open('graphify-out/.graphify_python', 'w', encoding='utf-8').write(sys.executable)"
fi
```
