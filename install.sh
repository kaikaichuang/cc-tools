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

# Sessions archived by cc-archive 0.1 lived under ~/.claude; move them to the new place.
old="$HOME/.claude/session-archive"
new="${CC_ARCHIVE_DIR:-$HOME/.local/share/cc-archive}"
if [ -d "$old" ]; then
    mkdir -p "$new"
    for d in "$old"/*/; do
        [ -d "$d" ] || continue
        mkdir -p "$new/$(basename "$d")"
        mv -n "$d"* "$new/$(basename "$d")/" 2>/dev/null || true
        rmdir "$d" 2>/dev/null || true
    done
    rmdir "$old" 2>/dev/null && echo "moved old archive $old -> $new" || echo "check $old: some files were not moved"
fi

case ":$PATH:" in
    *":$bin:"*) ;;
    *) echo "add to your ~/.zshrc or ~/.bashrc:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac
command -v python3 >/dev/null || echo "warning: python3 not found on PATH; cc-archive needs it"
