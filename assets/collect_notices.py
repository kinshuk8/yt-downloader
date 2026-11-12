"""Writes THIRD-PARTY-NOTICES.txt for the packaged app, and gathers the GPL/LGPL sources each release must publish.

usage: collect_notices.py TOOLS_DIR OUT_DIR [MANIFEST]
TOOLS_DIR is the bundled ffmpeg/QuickJS folder (binaries, plus libs/ on macOS).
On macOS the native components are looked up in Homebrew. Elsewhere (the Windows build) pass MANIFEST, a JSON
file describing them: {"intro": [...], "components": [{name, version, license, url, license_files}],
"sources": [paths], "sources_readme": "..."}.
Writes OUT_DIR/THIRD-PARTY-NOTICES.txt and OUT_DIR/third-party-sources/ (source tarballs + build recipes).
Run with the build venv's Python so the bundled Python packages are the ones listed.
"""
import importlib.metadata as md
import json
import re
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

tools, out = Path(sys.argv[1]), Path(sys.argv[2])
manifest = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if len(sys.argv) > 3 else None
root = Path(__file__).resolve().parent.parent
EXE = ".exe" if sys.platform == "win32" else ""
LICENSE_FILE = re.compile(r"^(licen[cs]e|copying|copyright|notice|ofl)[^/]*$", re.I)
COPYLEFT = re.compile(r"\b(L?GPL)", re.I)
# Packages left out of the app on purpose (mutagen is GPL and Snag doesn't need it).
EXCLUDED = {"mutagen"}


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def read(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def manifest_components():
    return [{**c, "source": None, "texts": [(Path(f).name, read(f)) for f in c.get("license_files", [])]}
            for c in manifest["components"]]


def native_components():
    """Homebrew formulas behind every binary and library bundled in TOOLS_DIR."""
    global CELLAR
    CELLAR = Path(sh("brew", "--cellar").strip())
    names = [p.name for p in tools.iterdir() if p.is_file()] + [p.name for p in (tools / "libs").iterdir()]
    formulas = {}
    for name in names:
        hit = next((p for p in CELLAR.glob(f"*/*/{'bin' if '.dylib' not in name else 'lib'}/{name}")), None)
        if hit:
            formula, version = hit.relative_to(CELLAR).parts[:2]
            formulas[formula] = version
    info = {f["name"]: f for f in json.loads(sh("brew", "info", "--json=v2", *formulas))["formulae"]}
    comps = []
    for formula, version in sorted(formulas.items()):
        meta = info[formula]
        keg = CELLAR / formula / version
        texts = [p for p in sorted(keg.rglob("*")) if p.is_file() and LICENSE_FILE.match(p.name)]
        license_ = meta.get("license") or "see below"
        if formula == "ffmpeg":  # Homebrew lists the base license; this build enables GPL v3 components
            license_ = "GPL-3.0-or-later (configured with --enable-gpl --enable-version3)"
        comps.append({
            "name": formula, "version": version, "license": license_,
            "url": meta.get("homepage"), "source": meta["urls"]["stable"]["url"],
            "texts": [(p.name, read(p)) for p in texts],
        })
    return comps


def project_url(meta):
    """Prefer a package's homepage or source repo over changelog/donate/chat links."""
    urls = [u.split(", ", 1) for u in meta.get_all("Project-URL") or [] if ", " in u]
    for want in ("homepage", "source", "source code", "repository", "documentation"):
        for label, url in urls:
            if label.strip().lower() == want:
                return url
    return urls[0][1] if urls else None


def python_components():
    """Python itself plus every package reachable from requirements.txt and pywebview."""
    env = default_environment()
    roots = [Requirement(line) for line in (root / "requirements.txt").read_text().split() if line]
    queue = [(r.name, set(r.extras)) for r in roots] + [("pywebview", set())]
    seen = {}
    while queue:
        name, extras = queue.pop()
        name = name.lower().replace("_", "-")
        if name in EXCLUDED:
            continue
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            continue  # optional dependency that isn't installed, so it isn't bundled either
        seen[name] = dist
        for req in dist.requires or []:
            r = Requirement(req)
            if r.name.lower() not in seen and (
                    r.marker is None or any(r.marker.evaluate({**env, "extra": e}) for e in extras | {""})):
                queue.append((r.name, set(r.extras)))

    comps = [{
        "name": "Python", "version": sys.version.split()[0], "license": "PSF-2.0",
        "url": "https://www.python.org", "source": None,
        "texts": [("LICENSE.txt", read(Path(sysconfig.get_paths()["stdlib"]) / "LICENSE.txt"))],
    }]
    for name, dist in sorted(seen.items()):
        meta = dist.metadata
        texts = [(f.name, read(f.locate()))
                 for f in (dist.files or []) if LICENSE_FILE.match(f.name)]
        license_ = meta.get("License-Expression") or next(iter((meta.get("License") or "").splitlines()), "")[:60]
        if not license_:  # older packages only declare it as a trove classifier
            license_ = next((c.split(" :: ")[-1] for c in meta.get_all("Classifier") or [] if c.startswith("License ::")), "see below")
        comps.append({
            "name": meta["Name"], "version": dist.version,
            "license": license_,
            "url": meta.get("Home-page") or project_url(meta),
            "source": None, "texts": texts,
        })
    return comps


def font_components():
    return [{"name": "Geist (font)", "version": "1.3.1", "license": "OFL-1.1", "url": "https://vercel.com/font",
             "source": None, "texts": [("OFL.txt", read(root / "static" / "fonts" / "OFL.txt"))]}]


def gather_sources(comps, dest):
    """Fetch the exact upstream source + Homebrew build recipe for every GPL/LGPL native component."""
    dest.mkdir(parents=True, exist_ok=True)
    for c in comps:
        if not COPYLEFT.search(c["license"]):
            continue
        subprocess.run(["brew", "fetch", "--quiet", "--build-from-source", c["name"]], check=True, capture_output=True)
        cached = Path(sh("brew", "--cache", "--build-from-source", c["name"]).strip())
        if cached.is_dir():  # formulas built from a git checkout (e.g. x264)
            shutil.make_archive(str(dest / f"{c['name']}-{c['version']}"), "gztar", cached.parent, cached.name)
        else:
            shutil.copy(cached, dest / cached.name.split("--", 1)[-1])
        (dest / f"{c['name']}.rb").write_text(sh("brew", "cat", c["name"]))
    (dest / "ffmpeg-configuration.txt").write_text(sh(str(tools / f"ffmpeg{EXE}"), "-hide_banner", "-buildconf"))
    (dest / "README.txt").write_text(
        "Corresponding source for the GPL/LGPL components bundled in Snag.\n\n"
        "Each tarball is the unmodified upstream source. The .rb files are the Homebrew build recipes\n"
        "(configure flags and patches) used to build them; ffmpeg-configuration.txt is FFmpeg's own\n"
        "record of how it was configured. The binaries were then copied into the app with dylibbundler,\n"
        "which only rewrites library load paths.\n")


def gather_manifest_sources(dest):
    """The Windows build downloads its sources itself; copy them in alongside FFmpeg's build record."""
    dest.mkdir(parents=True, exist_ok=True)
    for src in manifest["sources"]:
        shutil.copy(src, dest / Path(src).name)
    (dest / "ffmpeg-configuration.txt").write_text(
        sh(str(tools / f"ffmpeg{EXE}"), "-hide_banner", "-buildconf"), encoding="utf-8")
    (dest / "README.txt").write_text(manifest["sources_readme"], encoding="utf-8")


MAC_INTRO = [
    "FFmpeg in this app is licensed under the GPL-3.0-or-later and includes GPL (x264, x265) and LGPL",
    "(LAME, mpg123) components. FFmpeg and QuickJS run as separate programs; Snag does not link to them.",
    "The complete corresponding source code for every GPL/LGPL component, with the exact build recipes,",
    "is published with each release as snag-third-party-sources.tar.gz:",
]
native = manifest_components() if manifest else native_components()
comps = native + python_components() + font_components()
out.mkdir(parents=True, exist_ok=True)

lines = [
    "SNAG — THIRD-PARTY NOTICES",
    "=" * 26,
    "",
    "Snag's own code is MIT-licensed (see LICENSE). The app bundles the open-source software listed",
    "below, each under its own license. Full license texts follow the list.",
    "",
    *(manifest["intro"] if manifest else MAC_INTRO),
    "  https://github.com/kinshuk8/yt-downloader/releases",
    "",
    "The app is packaged with PyInstaller, whose bootloader is GPL-2.0 with an exception that permits",
    "this use.",
    "",
    "-" * 72,
]
for c in comps:
    lines.append(f"{c['name']} {c['version']}  —  {c['license']}" + (f"  —  {c['url']}" if c["url"] else ""))
lines += ["-" * 72, ""]
for c in comps:
    if not c["texts"]:
        continue
    lines += ["", "=" * 72, f"{c['name']} {c['version']}", "=" * 72]
    for fname, text in c["texts"]:
        lines += [f"--- {fname} ---", text.strip(), ""]
(out / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

if manifest:
    gather_manifest_sources(out / "third-party-sources")
else:
    gather_sources(native, out / "third-party-sources")
print(f"{len(comps)} components; notices and sources in {out}")
