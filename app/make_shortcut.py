# -*- coding: utf-8 -*-
"""Put a shortcut for the tracker on the Desktop."""
import os
import sys

try:
    import win32com.client as win32          # pywin32
    HAVE_WIN32 = True
except ImportError:
    HAVE_WIN32 = False

EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "dist", "PAYDAY Tracker.exe")
ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
LNK = os.path.join(DESKTOP, "PAYDAY Tracker.lnk")

if not os.path.exists(EXE):
    print("нет .exe:", EXE)
    sys.exit(1)

if HAVE_WIN32:
    shell = win32.Dispatch("WScript.Shell")
    sc = shell.CreateShortCut(LNK)
    sc.Targetpath = EXE
    sc.WorkingDirectory = os.path.dirname(EXE)
    sc.IconLocation = EXE + ",0"
    sc.Description = "PAYDAY 2 - Трекер достижений"
    sc.save()
    print("ярлык создан:", LNK)
else:
    print("pywin32 недоступен — создаю .url как запасной вариант")
    with open(LNK.replace(".lnk", ".url"), "w", encoding="utf-8") as f:
        f.write("[InternetShortcut]\nURL=file:///%s\nIconFile=%s\nIconIndex=0\n"
                % (EXE.replace("\\", "/"), ICON))
    print("создано:", LNK.replace(".lnk", ".url"))