#!/bin/zsh
# Builds dist/YT Downloader.app and dist/YT-Downloader.dmg (Apple silicon).
# Needs Homebrew; installs python, ffmpeg and dylibbundler if missing.
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
SRC="$PWD"
# Build files live outside the project so iCloud doesn't try to sync them.
B="$HOME/.cache/yt-downloader-build"
APP_NAME="YT Downloader"
mkdir -p "$B" dist

for pkg in python ffmpeg quickjs dylibbundler; do
  brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg"
done

echo "→ Python environment"
[ -x "$B/venv/bin/python" ] || python3 -m venv "$B/venv"
"$B/venv/bin/pip" install -q -U -r requirements.txt pywebview pyinstaller pillow

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

echo "→ Building app"
"$B/venv/bin/pyinstaller" desktop.py --noconfirm --clean --windowed \
  --name "$APP_NAME" --icon "$B/icon.icns" \
  --osx-bundle-identifier com.kinshuk8.ytdownloader \
  --add-data "$SRC/static:static" \
  --collect-submodules yt_dlp --collect-all yt_dlp_ejs \
  --distpath "$B/dist" --workpath "$B/work" --specpath "$B" >/dev/null 2>&1

APP="$B/dist/$APP_NAME.app"
cp -R "$T" "$APP/Contents/MacOS/tools"
codesign --force --deep --sign - "$APP" 2>/dev/null

echo "→ Making DMG"
rm -rf "$B/dmg" && mkdir "$B/dmg"
cp -R "$APP" "$B/dmg/"
ln -s /Applications "$B/dmg/Applications"
rm -rf "dist/$APP_NAME.app" dist/YT-Downloader.dmg
hdiutil create -volname "$APP_NAME" -srcfolder "$B/dmg" -format UDZO -ov dist/YT-Downloader.dmg >/dev/null 2>&1

echo "Done: $SRC/dist/YT-Downloader.dmg ($(du -h dist/YT-Downloader.dmg | cut -f1))"
