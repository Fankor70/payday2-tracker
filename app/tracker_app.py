# -*- coding: utf-8 -*-
"""PAYDAY 2 Achievement Tracker -- standalone desktop application.

Owns its own native window through pywebview (WebView2), so it is a real program:
its own process, its own taskbar entry, no browser behind it. The local server runs
in-process on a free port and the window simply points at it.

Packaged with PyInstaller:
    pyinstaller --onefile --windowed --name "PAYDAY Tracker" \
        --icon app.ico --add-data "ui.html;." --add-data "data;data" tracker_app.py
"""
import os
import sys
import socket
import threading
import time

HERE = (os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__)))


def free_port(start=8899):
    for p in range(start, start + 60):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("не нашёл свободный порт")


def main():
    sys.path.insert(0, HERE)
    # sweep the leftovers of a self-update: the running exe was renamed to
    # .old before the swap, so the previous build lingers until this launch
    for junk in ("PAYDAY Tracker.exe.old", "PAYDAY Tracker.exe.update.bat"):
        p = os.path.join(HERE, junk)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    import server

    port = free_port()
    os.environ["PD2_PORT"] = str(port)

    threading.Thread(target=server.main, daemon=True).start()
    # give the socket a moment so the first paint is not an error page
    for _ in range(40):
        try:
            with socket.create_connection(("127.0.0.1", port), 0.4):
                break
        except OSError:
            time.sleep(0.15)

    url = "http://127.0.0.1:%d/" % port

    import webview
    webview.create_window(
        "PAYDAY 2 — Трекер достижений",
        url,
        width=1500, height=940, min_size=(900, 600),
        background_color="#0b0d10",
        frameless=False,
    )
    webview.start()


if __name__ == "__main__":
    main()