"""Local YouTube downloader: Flask backend wrapping yt-dlp + ffmpeg."""
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import yt_dlp
from flask import Flask, jsonify, request, send_file, send_from_directory

DOWNLOAD_DIR = Path.home() / "Downloads" / "YouTube"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Inside the packaged .app, bundled files live next to the executable / in sys._MEIPASS.
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
# ffmpeg (merging/MP3) and QuickJS (YouTube's JS challenge) ship inside the .app.
TOOLS = Path(sys.executable).parent / "tools"

app = Flask(__name__, static_folder=str(BASE / "static"), static_url_path="")
jobs = {}  # job_id -> dict(status, percent, speed, eta, filepath, error, title)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/version")
def version():
    return jsonify(ytdlp=yt_dlp.version.__version__)


@app.post("/api/info")
def info():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify(error="Please paste a URL."), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True, "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify(error=_clean(e)), 400

    heights = sorted(
        {f["height"] for f in data.get("formats", []) if f.get("height") and f.get("vcodec") != "none"},
        reverse=True,
    )
    return jsonify(
        title=data.get("title"),
        channel=data.get("uploader") or data.get("channel"),
        duration=data.get("duration"),
        thumbnail=data.get("thumbnail"),
        heights=heights,
    )


@app.post("/api/download")
def download():
    body = request.json or {}
    url = body.get("url", "").strip()
    if not url:
        return jsonify(error="Missing URL."), 400
    job_id = uuid.uuid4().hex
    jobs[job_id] = {"status": "starting", "percent": 0}
    threading.Thread(target=_run, args=(job_id, url, body), daemon=True).start()
    return jsonify(job=job_id)


@app.get("/api/progress/<job_id>")
def progress(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="Unknown job."), 404
    out = {k: v for k, v in job.items() if k != "filepath"}
    if job.get("filepath"):
        out["filename"] = Path(job["filepath"]).name
        out["folder"] = str(DOWNLOAD_DIR)
    return jsonify(out)


@app.get("/api/file/<job_id>")
def file(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("filepath"):
        return jsonify(error="File not ready."), 404
    return send_file(job["filepath"], as_attachment=True)


@app.post("/api/reveal/<job_id>")
def reveal(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("filepath"):
        return jsonify(error="File not ready."), 404
    subprocess.run(["open", "-R", job["filepath"]])
    return jsonify(ok=True)


@app.post("/api/quit")
def quit_app():
    # Give the response a moment to reach the browser before exiting.
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return jsonify(ok=True)


def _options(body, job_id):
    def hook(d):
        job = jobs[job_id]
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            # Video + audio are fetched as separate streams; track which part we're on.
            part = d.get("info_dict", {}).get("vcodec") == "none" and "audio" or "video"
            job.update(
                status=f"downloading {part}" if body.get("mode") == "video" else "downloading",
                percent=round(d.get("downloaded_bytes", 0) / total * 100, 1) if total else job["percent"],
                speed=d.get("_speed_str", "").strip(),
                eta=d.get("_eta_str", "").strip(),
            )
        elif d["status"] == "finished":
            job.update(status="processing", percent=100)

    opts = {
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s [%(id)s].%(ext)s"),
        "windowsfilenames": True,
    }
    if (TOOLS / "ffmpeg").exists():
        opts["ffmpeg_location"] = str(TOOLS)
    if (TOOLS / "qjs").exists():
        opts["js_runtimes"] = {"quickjs": {"path": str(TOOLS / "qjs")}}

    if body.get("mode") == "audio":
        opts.update(
            format="bestaudio/best",
            writethumbnail=True,
            postprocessors=[
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                 "preferredquality": str(body.get("bitrate", "320"))},
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
        )
    else:
        quality = str(body.get("quality", "best"))
        container = body.get("container", "mp4")
        cap = "" if quality == "best" else f"[height<={int(quality)}]"
        opts.update(
            format=f"bv*{cap}+ba/b{cap}",
            # Highest resolution first; among equals prefer codecs that play everywhere.
            format_sort=["res", "fps", "vcodec:avc1", "acodec:m4a"] if container == "mp4" else ["res", "fps"],
            merge_output_format=container,
            postprocessors=[{"key": "FFmpegMetadata"}],
        )
    return opts


def _run(job_id, url, body):
    try:
        with yt_dlp.YoutubeDL(_options(body, job_id)) as ydl:
            data = ydl.extract_info(url, download=True)
        jobs[job_id].update(
            status="done",
            percent=100,
            title=data.get("title"),
            filepath=data["requested_downloads"][0]["filepath"],
        )
    except Exception as e:
        jobs[job_id].update(status="error", error=_clean(e))


def _clean(e):
    return str(e).replace("ERROR: ", "").split("\n")[0]


if __name__ == "__main__":
    print(f"Saving downloads to {DOWNLOAD_DIR}")
    print("Open http://127.0.0.1:5055")
    app.run(host="127.0.0.1", port=5055, threaded=True)
