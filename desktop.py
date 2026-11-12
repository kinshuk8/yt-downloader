"""Desktop entry point: runs the Flask backend in-process and shows it in a native window (macOS and Windows)."""
import sys
import threading

import updater

updater.activate()  # must run before anything imports yt_dlp

import webview  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import app  # noqa: E402

MAC = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"


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


def windows_dark_mode():
    """True when Windows apps are set to dark mode (Settings → Personalization → Colors)."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def dark_titlebar(window):
    """Windows draws a white title bar by default; match it to dark mode like built-in apps do."""
    import ctypes
    try:
        hwnd = window.native.Handle.ToInt64()
        on = ctypes.c_int(1)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(on), ctypes.sizeof(on))
    except Exception:
        pass  # older Windows without the attribute: keep the default title bar


def selftest(report_path):
    """Checks the packaged app without opening a window (used by CI). Writes a report; exit code 1 on failure."""
    import subprocess

    from app import EXE, TOOLS
    lines, ok = [], True

    def check(name, fn):
        nonlocal ok
        try:
            lines.append(f"PASS {name}: {fn()}")
        except Exception as e:
            ok = False
            lines.append(f"FAIL {name}: {e!r}")

    run = lambda *cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True).stdout  # noqa: E731
    client = app.test_client()
    check("ffmpeg", lambda: run(str(TOOLS / f"ffmpeg{EXE}"), "-hide_banner", "-version").splitlines()[0])
    check("ffprobe", lambda: run(str(TOOLS / f"ffprobe{EXE}"), "-hide_banner", "-version").splitlines()[0])
    check("quickjs", lambda: run(str(TOOLS / f"qjs{EXE}"), "-e", "console.log(6 * 7)").strip())
    check("yt-dlp", lambda: client.get("/api/version").get_json()["ytdlp"])
    check("page", lambda: f"{len(client.get('/').data)} bytes")
    check("licenses", lambda: "THIRD-PARTY NOTICES" in client.get("/licenses").get_data(as_text=True) or 1 / 0)
    # YouTube sometimes blocks cloud machines, so a failed lookup here is reported but doesn't fail the test.
    r = client.post("/api/info", json={"url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ"})
    lines.append(f"INFO youtube lookup: {r.status_code} {r.get_json().get('title') or r.get_json().get('error')}")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.exit(0 if ok else 1)


def main():
    if "--selftest" in sys.argv:
        return selftest(sys.argv[sys.argv.index("--selftest") + 1])

    server = make_server("127.0.0.1", 0, app, threaded=True)  # port 0 = any free port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    updater.check_in_background()

    dark = WINDOWS and windows_dark_mode()
    window = webview.create_window(
        "Snag",
        f"http://127.0.0.1:{server.server_port}/?app=1" + ("&glass=1" if MAC else ""),
        width=620,
        height=760,
        min_size=(440, 560),
        # Mac: native frosted-glass background with the page transparent over it.
        vibrancy=MAC,
        transparent=MAC,
        # Windows: paint the window in the page's colour so there's no white flash before it loads.
        background_color="#0e0e12" if dark else "#f3f3f6",
    )
    if MAC:
        window.events.shown += lambda: unify_titlebar(window)
    elif dark:
        window.events.shown += lambda: dark_titlebar(window)
    webview.start()


if __name__ == "__main__":
    main()
