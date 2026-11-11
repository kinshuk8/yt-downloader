"""Captures README screenshots of the real app window.

usage: screenshots.py OUT_DIR light|dark
Writes OUT_DIR/app-<appearance>.png (video options) and OUT_DIR/done-<appearance>.png (finished MP3).
Uses Big Buck Bunny (CC BY, Blender Foundation) so the screenshots can be shared freely.
"""
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import webview  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import DOWNLOAD_DIR, app  # noqa: E402
from desktop import unify_titlebar  # noqa: E402

VIDEO = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
out, appearance = Path(sys.argv[1]), sys.argv[2]
out.mkdir(parents=True, exist_ok=True)


def on_main(fn):
    from PyObjCTools import AppHelper
    done = threading.Event()
    AppHelper.callAfter(lambda: (fn(), done.set()))
    done.wait()


def wait_for(window, js, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        if window.evaluate_js(js):
            return
        time.sleep(0.5)
    raise TimeoutError(js)


def capture(window, name):
    window.evaluate_js("document.activeElement && document.activeElement.blur()")
    time.sleep(0.8)  # let transitions settle
    wid = window.native.windowNumber()
    path = out / f"{name}-{appearance}.png"
    subprocess.run(["screencapture", "-x", f"-l{wid}", str(path)], check=True)
    print(f"saved {path}", flush=True)


def run(window):
    try:
        steps(window)
    finally:
        window.destroy()


def steps(window):
    from AppKit import NSApp, NSAppearance
    name = "NSAppearanceNameAqua" if appearance == "light" else "NSAppearanceNameDarkAqua"
    from AppKit import NSWindowStyleMaskFullSizeContentView

    def set_appearance():
        # Changing appearance rebuilds the title bar; toggle full-size content so it is merged into the page again.
        NSApp.setAppearance_(NSAppearance.appearanceNamed_(name))
        w = window.native
        w.setStyleMask_(w.styleMask() & ~NSWindowStyleMaskFullSizeContentView)
    on_main(set_appearance)
    unify_titlebar(window)
    time.sleep(0.5)

    wait_for(window, "document.readyState === 'complete' && !!document.getElementById('url')")
    window.evaluate_js(f"document.getElementById('url').value = '{VIDEO}'; fetchInfo()")
    wait_for(window, "!document.getElementById('optsCard').classList.contains('hidden')")
    wait_for(window, "document.getElementById('thumb').complete")
    capture(window, "app")

    before = set(DOWNLOAD_DIR.glob("*aqz-KE-bpKQ*"))
    window.evaluate_js("document.querySelector('#mode button[data-mode=audio]').click()")
    wait_for(window, "state.mode === 'audio'", timeout=10)  # never fall through to a multi-GB 4K download
    window.evaluate_js("document.getElementById('dlBtn').click()")
    wait_for(window, "!document.getElementById('recent').classList.contains('hidden')", timeout=300)
    capture(window, "done")
    for f in set(DOWNLOAD_DIR.glob("*aqz-KE-bpKQ*")) - before:
        f.unlink()  # don't leave the test download behind


server = make_server("127.0.0.1", 0, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
window = webview.create_window("YT Downloader", f"http://127.0.0.1:{server.server_port}/?app=1",
                               width=620, height=720, vibrancy=True, transparent=True)
window.events.shown += lambda: unify_titlebar(window)
webview.start(run, window)
