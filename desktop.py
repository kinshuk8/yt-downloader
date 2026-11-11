"""Desktop entry point: runs the Flask backend in-process and shows it in a native window."""
import threading

import updater

updater.activate()  # must run before anything imports yt_dlp

import webview  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import app  # noqa: E402


def unify_titlebar(window):
    """Let the page run up behind the traffic lights, like modern Mac apps, instead of a separate grey bar."""
    from AppKit import NSWindowStyleMaskFullSizeContentView, NSWindowTitleHidden
    from PyObjCTools import AppHelper

    def apply():
        w = window.native
        w.setTitlebarAppearsTransparent_(True)
        w.setTitleVisibility_(NSWindowTitleHidden)
        w.setStyleMask_(w.styleMask() | NSWindowStyleMaskFullSizeContentView)
        # The web view and blur view were laid out before the change; stretch them into the old title bar area.
        content = w.contentView()
        for view in content.subviews():
            view.setFrame_(content.bounds())

    AppHelper.callAfter(apply)  # AppKit calls must run on the main thread


def main():
    server = make_server("127.0.0.1", 0, app, threaded=True)  # port 0 = any free port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    updater.check_in_background()

    window = webview.create_window(
        "YT Downloader",
        f"http://127.0.0.1:{server.server_port}/?app=1",
        width=620,
        height=760,
        min_size=(440, 560),
        vibrancy=True,  # native frosted-glass background; the page is transparent over it
        transparent=True,
    )
    window.events.shown += lambda: unify_titlebar(window)
    webview.start()


if __name__ == "__main__":
    main()
