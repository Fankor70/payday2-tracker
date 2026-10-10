# -*- coding: utf-8 -*-
"""Build and publish a release: bump version, rebuild data + exe, push, release.

Run from anywhere:
    python make_release.py 1.0.2 --notes "что нового"

Steps:
  1. write the version into app/version.py
  2. rebuild the dataset and the page (pipeline.py, from the workspace root --
     its stage paths are repo-relative)
  3. build the onefile exe with PyInstaller
  4. copy the exe into app/share/ (the folder that goes to people)
  5. commit, tag vX.Y.Z, push
  6. create the GitHub release with the exe + instruction file attached

Requires: gh authorised (gh auth login), git credentials for push.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
PARENT = os.path.dirname(HERE)                     # the pipeline's CWD
EXE = os.path.join(APP, "dist", "PAYDAY Tracker.exe")
SHARE = os.path.join(APP, "share", "PAYDAY Tracker")

BUILD = ["--onefile", "--windowed", "--name", "PAYDAY Tracker",
         "--icon", os.path.join(APP, "app.ico"),
         "--add-data", "ui.html;.", "--add-data", "data;data",
         "--hidden-import", "webview.platforms.edgechromium",
         "--hidden-import", "webview.platforms.winforms",
         "--hidden-import", "clr",
         "--collect-submodules", "webview",
         "--clean", "--noconfirm", "tracker_app.py"]


def run(cmd, cwd=None):
    print("+", " ".join(os.path.basename(str(c)) if i == 0 else str(c)
                        for i, c in enumerate(cmd)), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        sys.exit("шаг упал: %s" % cmd[0])


def set_version(v):
    p = os.path.join(APP, "version.py")
    s = io.open(p, encoding="utf-8").read()
    s = re.sub(r'VERSION = "[^"]*"', 'VERSION = "%s"' % v, s)
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version", help="например 1.0.2")
    ap.add_argument("--notes", default="", help="текст релиза")
    args = ap.parse_args()
    v = args.version.lstrip("v")

    set_version(v)
    run([sys.executable, os.path.join(HERE, "pipeline.py")], cwd=PARENT)
    run([sys.executable, "-m", "PyInstaller"] + BUILD, cwd=APP)
    os.makedirs(SHARE, exist_ok=True)
    shutil.copy2(EXE, os.path.join(SHARE, "PAYDAY Tracker.exe"))

    run(["git", "add", "-A"], cwd=HERE)
    run(["git", "commit", "-m", "v%s" % v], cwd=HERE)
    run(["git", "tag", "v%s" % v], cwd=HERE)
    run(["git", "push", "origin", "main", "--tags"], cwd=HERE)

    exe_asset = os.path.join(SHARE, "PAYDAY Tracker.exe")
    txt = os.path.join(SHARE, "Как пользоваться.txt")
    assets = [exe_asset] + ([txt] if os.path.exists(txt) else [])
    notes = args.notes or "Сборка v%s" % v
    run(["gh", "release", "create", "v%s" % v, "--title", "v%s" % v,
         "--notes", notes] + assets, cwd=HERE)
    print("\nрелиз v%s опубликован" % v)


if __name__ == "__main__":
    main()
