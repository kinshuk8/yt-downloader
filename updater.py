"""Keeps yt-dlp current inside the packaged app, where pip isn't available.

yt-dlp publishes each release as a zipapp. We cache the newest one in Application Support
and put it first on sys.path, so `import yt_dlp` picks it up instead of the bundled copy.
"""
import hashlib
import json
import sys
import threading
import urllib.request
from pathlib import Path

CACHE = Path.home() / "Library" / "Application Support" / "YT Downloader"
ZIP = CACHE / "yt-dlp.zip"
RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"


def activate():
    """Call before importing yt_dlp."""
    if ZIP.exists():
        sys.path.insert(0, str(ZIP))


def check_in_background():
    """Download a newer yt-dlp if one exists; it's used from the next launch."""
    threading.Thread(target=_update, daemon=True).start()


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "yt-downloader"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _update():
    try:
        import yt_dlp

        release = json.loads(_get(RELEASE_API))
        if release["tag_name"] == yt_dlp.version.__version__:
            return
        assets = {a["name"]: a["browser_download_url"] for a in release["assets"]}
        data = _get(assets["yt-dlp"])
        sums = _get(assets["SHA2-256SUMS"]).decode()
        expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1] == "yt-dlp")
        if hashlib.sha256(data).hexdigest() != expected:
            return
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = ZIP.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(ZIP)
    except Exception:
        pass  # Offline or GitHub hiccup; try again next launch.
