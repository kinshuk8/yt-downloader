"""Desktop entry point: runs the Flask backend in-process and shows it in a native window."""
import threading

import updater

updater.activate()  # must run before anything imports yt_dlp

import webview  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import app  # noqa: E402


def main():
    server = make_server("127.0.0.1", 0, app, threaded=True)  # port 0 = any free port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    updater.check_in_background()

    webview.create_window(
        "YT Downloader",
        f"http://127.0.0.1:{server.server_port}/?app=1",
        width=720,
        height=780,
        min_size=(420, 560),
    )
    webview.start()


if __name__ == "__main__":
    main()
