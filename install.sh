#!/bin/sh
# Link this repo's tools into ~/.local/bin (no sudo). Run again any time; `git pull` updates them in place.
set -e
repo=$(cd "$(dirname "$0")" && pwd)
bin="$HOME/.local/bin"
mkdir -p "$bin"

for tool in "$repo"/bin/*; do
    name=$(basename "$tool")
    if [ -e "$bin/$name" ] && [ ! -L "$bin/$name" ]; then
        mv "$bin/$name" "$bin/$name.bak"
        echo "kept your old $bin/$name as $name.bak"
    fi
    ln -sfn "$tool" "$bin/$name"
    echo "linked $bin/$name -> $tool"
done

# Archived sessions from older versions (cc-archive) move to the current place.
new="${CCS_DIR:-$HOME/.local/share/ccs}"
for old in "$HOME/.claude/session-archive" "$HOME/.local/share/cc-archive"; do
    [ -d "$old" ] || continue
    mkdir -p "$new"
    for d in "$old"/* "$old"/.pending "$old"/.keep; do
        [ -d "$d" ] || continue
        mkdir -p "$new/$(basename "$d")"
        mv -n "$d"/* "$new/$(basename "$d")/" 2>/dev/null || true
        rmdir "$d" 2>/dev/null || true
    done
    rmdir "$old" 2>/dev/null && echo "moved old archive $old -> $new" || echo "check $old: some files were not moved"
done

case ":$PATH:" in
    *":$bin:"*) ;;
    *) echo "add to your ~/.zshrc or ~/.bashrc:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac
command -v python3 >/dev/null || echo "warning: python3 not found on PATH; ccs needs it"
