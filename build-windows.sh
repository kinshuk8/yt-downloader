#!/usr/bin/env bash
# Builds dist/Snag-Setup.exe on Windows. Run from Git Bash with Python 3 and Inno Setup 6 installed;
# GitHub Actions runs it for every release (.github/workflows/windows.yml).
# Also writes dist/THIRD-PARTY-NOTICES-windows.txt and dist/snag-windows-third-party-sources.tar.gz.
set -euo pipefail
cd "$(dirname "$0")"
SRC="$PWD"
B="$SRC/build-win"
VERSION="${SNAG_VERSION:-0.0.0}"
VERSION="${VERSION#v}"
W() { cygpath -w "$1"; }  # Windows-style path for Windows programs

# Pinned third-party builds. ffmpeg is the LGPL build: Snag only copies streams and encodes MP3,
# so it needs none of the GPL encoders.
FFMPEG_TAG=autobuild-2026-11-11-12-39
FFMPEG_BUILD=ffmpeg-n9.0.2-49-gc179411bbb-win64-lgpl-shared-9.0
QJS_TAG=v0.18.0

rm -rf "$B" && mkdir -p "$B/tools" "$B/src" "$B/lic" dist

echo "→ Python packages"
python -m pip install -q -U -r requirements.txt pywebview pyinstaller pillow packaging
# mutagen (a yt-dlp extra) is GPL and not needed: ffmpeg embeds MP3 cover art. Keep it out of the app.
python -m pip uninstall -q -y mutagen || true

echo "→ ffmpeg + QuickJS-ng"
curl -fsSL -o "$B/ffmpeg.zip" "https://github.com/BtbN/FFmpeg-Builds/releases/download/$FFMPEG_TAG/$FFMPEG_BUILD.zip"
unzip -q "$B/ffmpeg.zip" -d "$B"
cp "$B/$FFMPEG_BUILD"/bin/ffmpeg.exe "$B/$FFMPEG_BUILD"/bin/ffprobe.exe "$B/$FFMPEG_BUILD"/bin/*.dll "$B/tools/"
cp "$B/$FFMPEG_BUILD/LICENSE.txt" "$B/lic/FFmpeg-LICENSE.txt"
curl -fsSL -o "$B/tools/qjs.exe" "https://github.com/quickjs-ng/quickjs/releases/download/$QJS_TAG/qjs-windows-x86_64.exe"
curl -fsSL -o "$B/lic/QuickJS-ng-LICENSE.txt" "https://raw.githubusercontent.com/quickjs-ng/quickjs/$QJS_TAG/LICENSE"

echo "→ Third-party sources"
# Exact FFmpeg source for this build, plus the FFmpeg-Builds scripts that pin every library it includes.
FFMPEG_SHA="${FFMPEG_BUILD#*-g}"
FFMPEG_SHA="${FFMPEG_SHA%%-*}"
curl -fsSL -o "$B/src/FFmpeg-$FFMPEG_SHA.tar.gz" "https://github.com/FFmpeg/FFmpeg/archive/$FFMPEG_SHA.tar.gz"
curl -fsSL -o "$B/src/FFmpeg-Builds-$FFMPEG_TAG.tar.gz" "https://github.com/BtbN/FFmpeg-Builds/archive/refs/tags/$FFMPEG_TAG.tar.gz"

echo "→ Licenses"
FFMPEG_TAG="$FFMPEG_TAG" FFMPEG_BUILD="$FFMPEG_BUILD" QJS_TAG="$QJS_TAG" B="$B" python - <<'EOF'
import json, os
from pathlib import Path
b = Path(os.environ["B"])
tag, build, qjs = os.environ["FFMPEG_TAG"], os.environ["FFMPEG_BUILD"], os.environ["QJS_TAG"]
manifest = {
    "intro": [
        f"FFmpeg in this app is the LGPL build {build} from BtbN/FFmpeg-Builds ({tag}),",
        "licensed under the LGPL-2.1-or-later. It includes other open-source libraries whose exact versions",
        "and licenses are pinned in the FFmpeg-Builds scripts shipped with the sources below. FFmpeg and",
        "QuickJS-ng run as separate programs; Snag does not link to them. The complete corresponding source",
        "code is published with each release as snag-windows-third-party-sources.tar.gz:",
    ],
    "components": [
        {"name": "FFmpeg", "version": build.split("-win64")[0].removeprefix("ffmpeg-"), "license": "LGPL-2.1-or-later",
         "url": "https://ffmpeg.org", "license_files": [str(b / "lic" / "FFmpeg-LICENSE.txt")]},
        {"name": "QuickJS-ng", "version": qjs, "license": "MIT", "url": "https://github.com/quickjs-ng/quickjs",
         "license_files": [str(b / "lic" / "QuickJS-ng-LICENSE.txt")]},
    ],
    "sources": [str(p) for p in sorted((b / "src").iterdir())],
    "sources_readme": (
        "Corresponding source for the LGPL FFmpeg bundled in Snag for Windows.\n\n"
        f"FFmpeg-*.tar.gz is the FFmpeg source at the exact commit of this build. FFmpeg-Builds-{tag}.tar.gz\n"
        "holds the build scripts that produced it; they pin the source and version of every library it\n"
        "includes. ffmpeg-configuration.txt is FFmpeg's own record of how it was configured.\n"),
}
(b / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
EOF
python assets/collect_notices.py "$(W "$B/tools")" "$(W "$B/notices")" "$(W "$B/manifest.json")"

echo "→ Icon"
python assets/make_icon.py "$(W "$B/icon.png")" >/dev/null
python -c "import sys; from PIL import Image; Image.open(sys.argv[1]).save(sys.argv[2], sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])" \
  "$(W "$B/icon.png")" "$(W "$B/icon.ico")"

echo "→ Building app"
python -m PyInstaller desktop.py --noconfirm --clean --windowed \
  --name Snag --icon "$(W "$B/icon.ico")" \
  --add-data "$(W "$SRC/static");static" \
  --add-data "$(W "$SRC/LICENSE");." --add-data "$(W "$B/notices/THIRD-PARTY-NOTICES.txt");." \
  --collect-submodules yt_dlp --collect-all yt_dlp_ejs --exclude-module mutagen \
  --distpath "$(W "$B/dist")" --workpath "$(W "$B/work")" --specpath "$(W "$B")"
cp -r "$B/tools" "$B/dist/Snag/tools"

echo "→ Self-test"
status=0
"$B/dist/Snag/Snag.exe" --selftest "$(W "$B/selftest.txt")" || status=$?
cat "$B/selftest.txt" 2>/dev/null || echo "(no report written)"
[ "$status" -eq 0 ] || { echo "Self-test failed"; exit 1; }

echo "→ Installer"
# Microsoft's WebView2 bootstrapper (redistributable); the installer runs it only on PCs without WebView2.
curl -fsSL -o windows/MicrosoftEdgeWebview2Setup.exe "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
# MSYS_NO_PATHCONV: keep Git Bash from rewriting Inno Setup's /D... switches as paths.
MSYS_NO_PATHCONV=1 "/c/Program Files (x86)/Inno Setup 6/ISCC.exe" /Q \
  "/DAppVersion=$VERSION" "/DSourceDir=$(W "$B/dist/Snag")" "/DIconFile=$(W "$B/icon.ico")" \
  "/O$(W "$SRC/dist")" "$(W "$SRC/windows/snag.iss")"

echo "→ Release extras"
cp "$B/notices/THIRD-PARTY-NOTICES.txt" dist/THIRD-PARTY-NOTICES-windows.txt
tar -czf dist/snag-windows-third-party-sources.tar.gz -C "$B/notices" third-party-sources

ls -la dist
