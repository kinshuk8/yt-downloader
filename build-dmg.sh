#!/bin/zsh
# Builds dist/Snag.app and dist/Snag.dmg (Apple silicon).
# Also writes dist/THIRD-PARTY-NOTICES.txt and dist/snag-third-party-sources.tar.gz for the release.
# Needs Homebrew; installs python, ffmpeg, quickjs and dylibbundler if missing.
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
SRC="$PWD"
# Build files live outside the project so iCloud doesn't try to sync them.
B="$HOME/.cache/snag-build"
APP_NAME="Snag"
mkdir -p "$B" dist

for pkg in python ffmpeg quickjs dylibbundler; do
  brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg"
done

echo "→ Python environment"
[ -x "$B/venv/bin/python" ] || python3 -m venv "$B/venv"
"$B/venv/bin/pip" install -q -U -r requirements.txt pywebview pyinstaller pillow dmgbuild packaging
# mutagen (a yt-dlp extra) is GPL and not needed: ffmpeg embeds MP3 cover art. Keep it out of the app.
"$B/venv/bin/pip" uninstall -q -y mutagen 2>/dev/null || true

echo "→ Bundling ffmpeg + QuickJS"
# ffmpeg merges/converts; QuickJS solves YouTube's JS challenge (needed for most video formats).
T="$B/tools"
rm -rf "$T" && mkdir -p "$T"
for bin in ffmpeg ffprobe qjs; do cp "$(readlink -f "$(command -v $bin)")" "$T/$bin"; done
chmod u+w "$T/"*
# Copy their Homebrew libraries alongside them and point the binaries at the copies.
dylibbundler -cd -of -b -x "$T/ffmpeg" -x "$T/ffprobe" -x "$T/qjs" \
  -d "$T/libs" -p @executable_path/libs/ >/dev/null 2>&1

echo "→ Icon"
"$B/venv/bin/python" assets/make_icon.py "$B/icon.png" >/dev/null
rm -rf "$B/icon.iconset" && mkdir "$B/icon.iconset"
for s in 16 32 128 256 512; do
  sips -z $s $s "$B/icon.png" --out "$B/icon.iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s * 2)) $((s * 2)) "$B/icon.png" --out "$B/icon.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$B/icon.iconset" -o "$B/icon.icns"

echo "→ Licenses"
# THIRD-PARTY-NOTICES.txt ships inside the app; the GPL/LGPL sources are published with each release.
rm -rf "$B/notices"
"$B/venv/bin/python" assets/collect_notices.py "$T" "$B/notices" >/dev/null

echo "→ Building app"
"$B/venv/bin/pyinstaller" desktop.py --noconfirm --clean --windowed \
  --name "$APP_NAME" --icon "$B/icon.icns" \
  --osx-bundle-identifier com.kinshuk8.snag \
  --add-data "$SRC/static:static" \
  --add-data "$SRC/LICENSE:." --add-data "$B/notices/THIRD-PARTY-NOTICES.txt:." \
  --collect-submodules yt_dlp --collect-all yt_dlp_ejs --exclude-module mutagen \
  --distpath "$B/dist" --workpath "$B/work" --specpath "$B" >/dev/null 2>&1

APP="$B/dist/$APP_NAME.app"
cp -R "$T" "$APP/Contents/MacOS/tools"
codesign --force --deep --sign - "$APP" 2>/dev/null

echo "→ Making DMG"
# Installer window artwork, drawn in Geist; 1x + 2x combined into one HiDPI TIFF.
mkdir -p "$B/fonts"
for w in SemiBold Regular; do
  [ -f "$B/fonts/Geist-$w.ttf" ] ||
    curl -sfL -o "$B/fonts/Geist-$w.ttf" "https://cdn.jsdelivr.net/npm/geist@1.3.1/dist/fonts/geist-sans/Geist-$w.ttf"
done
"$B/venv/bin/python" assets/make_dmg_background.py "$B/dmgbg" "$B/fonts"
tiffutil -cathidpicheck "$B/dmgbg/dmg-bg.png" "$B/dmgbg/dmg-bg@2x.png" -out "$B/dmgbg/dmg-bg.tiff" >/dev/null 2>&1
rm -f dist/Snag.dmg
"$B/venv/bin/dmgbuild" -s assets/dmg_settings.py -D app="$APP" -D background="$B/dmgbg/dmg-bg.tiff" \
  "$APP_NAME" dist/Snag.dmg >/dev/null 2> >(grep -v "is deprecated" >&2)

echo "→ Release extras"
cp "$B/notices/THIRD-PARTY-NOTICES.txt" dist/
tar -czf dist/snag-third-party-sources.tar.gz -C "$B/notices" third-party-sources

echo "Done: $SRC/dist/Snag.dmg ($(du -h dist/Snag.dmg | cut -f1))"
echo "Attach to the GitHub release: Snag.dmg, THIRD-PARTY-NOTICES.txt, snag-third-party-sources.tar.gz"
