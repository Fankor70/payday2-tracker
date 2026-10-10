# -*- coding: utf-8 -*-
"""PAYDAY 2 achievement tracker -- local app server.

Standard library only, so it runs anywhere the game runs with no install step.

  GET  /                    the UI
  GET  /api/data            achievements + heists (built by the pipeline)
  GET  /api/progress        current progress
  POST /api/toggle          {id, done}
  POST /api/import/steam    {url}   -- scrape a public Steam profile
  POST /api/import/mod      {}      -- pick up the companion mod's dump
  POST /api/reset
  GET  /api/events          SSE stream: the browser learns about new unlocks

The companion SuperBLT mod writes <save>/pd2tracker.json. The server watches
that file, so an achievement earned in game shows up in the open page without a
refresh. Everything funnels through one Store, so the counts cannot drift.
"""
import html, json, os, re, sys, time, threading, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from store import Store
from steam_watch import SteamWatcher, POLL_SECONDS
import version as _ver

UPDATE_EXE = "PAYDAY Tracker.exe"


def _app_dir():
    """Folder next to the exe -- where WRITABLE state (progress) belongs.

    Bundled read-only data (ui.html, data/) is unpacked into PyInstaller's
    temp dir, so resources and saves must not look in the same place.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _resource_dir():
    """Folder with bundled read-only assets."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

HERE = _app_dir()
RES = _resource_dir()
STORE = Store()
FEEDS = []                       # live queues for SSE subscribers
DATA_CACHE = {"mtime": None, "payload": None}

# Optional: point PD2_DIR at the game folder and the app can also read a
# progress dump left there by an external tool. Not required -- the tracker
# works entirely from Steam import and manual ticking.
GAME_DIR = os.environ.get("PD2_DIR", r"E:\SteamLibrary\steamapps\common\PAYDAY 2")
MOD_DUMP = os.path.join(GAME_DIR, "mods", "saves", "pd2tracker.json")


# ----------------------------------------------------------------- helpers
def achievement_images():
    """Icon URL per achievement name, from the Steam scrape.

    The pipeline output carries no icons -- they live in steam_parsed.json and
    only ever got baked into the static page. The app replaced that data with the
    API response, so every card lost its picture; the server has to send them.
    """
    path = os.path.join(RES, "data", "steam_images.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def load_data():
    """Achievement + heist data produced by the build pipeline."""
    path = os.path.join(RES, "data", "app_data.json")
    mtime = os.path.getmtime(path)
    if DATA_CACHE["mtime"] == mtime and DATA_CACHE["payload"]:
        return DATA_CACHE["payload"]
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    images = achievement_images()
    payload = {
        "achievements": [{
            "i": a["id"], "n": a["name"], "nr": a.get("name_ru"),
            "d": a["desc"], "dr": a.get("desc_ru"), "p": a.get("pct"),
            "img": a.get("img") or images.get(a["name"], ""),
            "h": a.get("heists") or [],
            "df": a.get("difficulties") or [], "r": a.get("rewards") or {},
            "c": a.get("category"), "sc": a.get("scope"),
            "dy": a.get("day"), "dp": a.get("deps") or [],
            "fit": a.get("fit"), "crew4": bool(a.get("crew4")),
            "tg": a.get("target"),
            "pc": a.get("plan_cat") or "ladder",
        } for a in d["achievements"]],
        "heists": d["heists"],
        "parallel": d.get("parallel", {}),
        "global_ids": d.get("global_ids", []),
        "category_labels": d["category_labels"],
        "category_priority": d["category_priority"],
        "route_meta": d.get("route_meta") or {},
    }
    DATA_CACHE["mtime"] = DATA_CACHE["payload"] = payload
    return payload


_TARGETS = {}


def targets():
    """Achievement id -> numeric target, built once from the pipeline data."""
    if not _TARGETS:
        for a in load_data()["achievements"]:
            if a.get("tg"):
                _TARGETS[a["i"]] = a["tg"]
    return _TARGETS


def sync_counters():
    """An earned achievement IS its counter at 100 %.

    Steam reports whether a row was unlocked, never the intermediate number, so
    the two can disagree: "Pump-Action" ticked off next to "0 / 666" is a state
    the game cannot be in. Every unlocked target-bearing achievement therefore
    has its counter pinned to the target -- which also means the number fills
    itself the moment Steam reports the unlock.

    One-way only. The counter is cumulative: the kills are still kills after the
    tick is removed, so it is never lowered here. That is also the honest
    reading -- "Pump-Action" wants 666 kills *with the Jackal*, so un-ticking it
    while 666 Interceptors stay dead is a real state, not a contradiction.
    """
    tg = targets()
    want = {i: t for i, t in tg.items()
            if i in STORE.done and STORE.counts.get(i, 0) != t}
    if want:
        STORE.set_counts(want)
    return len(want)


def snapshot():
    """STORE.snapshot() with the counters reconciled against the ticks first."""
    sync_counters()
    return STORE.snapshot()


# ------------------------------------------------------------------ updater
# The app is one self-contained exe: data files and the page are bundled inside
# it, so "update" means "replace the exe". GitHub Releases holds the fresh exe;
# the swap uses the Windows quirk that a RUNNING exe can be renamed (just not
# deleted or overwritten): rename the old one away, move the new one in, start
# it, exit. A leftover .old.exe is swept on the next launch.
def _version_tuple(s):
    return tuple(int(x) for x in re.findall(r"\d+", s or "0")[:4]) or (0,)


def _gh_api(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "pd2-tracker",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def update_check():
    """Compare the running version with the latest GitHub release."""
    cur = _ver.VERSION
    try:
        rel = _gh_api("https://api.github.com/repos/%s/releases/latest" % _ver.REPO)
    except Exception as e:
        return {"current": cur, "error": "не смог спросить GitHub: %s" % e,
                "has_update": False}
    latest = (rel.get("tag_name") or "").lstrip("v")
    asset = next((a for a in (rel.get("assets") or [])
                  if a.get("name") == UPDATE_EXE), None)
    return {
        "current": cur, "latest": latest,
        "has_update": bool(latest) and _version_tuple(latest) > _version_tuple(cur),
        "notes": (rel.get("body") or "")[:2000],
        "published": rel.get("published_at"),
        "asset_url": asset.get("browser_download_url") if asset else None,
        "error": None if asset else
                 "в релизе нет файла %s" % UPDATE_EXE if latest else None,
    }


def _update_swap(exe_path):
    """Replace the running exe and start the fresh one."""
    old = exe_path + ".old"
    new = exe_path + ".update"
    import subprocess
    try:
        if os.path.exists(old):
            os.remove(old)
    except OSError:
        pass
    try:
        os.rename(exe_path, old)
        os.rename(new, exe_path)
    except OSError:
        # rename refused -- fall back to a batch that swaps after we exit
        bat = exe_path + ".update.bat"
        with open(bat, "w", encoding="utf-8") as f:
            f.write('@echo off\r\n'
                    'timeout /t 2 /nobreak >nul\r\n'
                    'del "%s"\r\n'
                    'move /y "%s" "%s"\r\n'
                    'start "" "%s"\r\n'
                    'del "%%~f0"\r\n' % (old, new, exe_path, exe_path))
        subprocess.Popen(["cmd", "/c", bat], cwd=os.path.dirname(exe_path),
                         creationflags=0x08000000)          # CREATE_NO_WINDOW
        return "batch"
    subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path),
                     creationflags=0x00000008 | 0x00000200)  # DETACHED | NEW_GROUP
    return "inline"


def update_install():
    """Download the release exe beside this one, swap, restart. Threaded."""
    info = update_check()
    if info.get("error") or not info.get("has_update") or not info.get("asset_url"):
        broadcast("update", {"stage": "error", "error": info.get("error")
                             or "обновление не требуется"})
        return False
    exe_path = os.path.join(_app_dir(), UPDATE_EXE)
    new = exe_path + ".update"
    try:
        req = urllib.request.Request(info["asset_url"], headers={
            "User-Agent": "pd2-tracker"})
        with urllib.request.urlopen(req, timeout=600) as r, \
                open(new, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(131072)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    broadcast("update", {"stage": "downloading",
                                         "pct": round(done / total * 100)})
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        broadcast("update", {"stage": "error",
                             "error": "скачивание не удалось: %s" % e})
        return False
    broadcast("update", {"stage": "swapping"})
    mode = _update_swap(exe_path)
    broadcast("update", {"stage": "restarting", "mode": mode,
                         "version": info["latest"]})
    threading.Timer(1.5, lambda: os._exit(0)).start()
    return True


def update_install_async():
    threading.Thread(target=update_install, daemon=True).start()
    return {"started": True}


def _norm_key(s):
    """Normalise a name for matching: lowercase, no punctuation.

    Achievement names are not always words -- one is literally ";)" -- so an
    empty result falls back to the whitespace-stripped original, otherwise such
    names could never be matched against an import.
    """
    s = html.unescape((s or "").strip()).lower()
    k = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()
    return k or s.strip()


HIDDEN_ROW = re.compile(r"^\d+\s+hidden achievement", re.I)


def name_index():
    """Normalised achievement name -> id, for matching imports."""
    out = {}
    for a in load_data()["achievements"]:
        for key in (a["n"], a.get("nr") or ""):
            k = _norm_key(key)
            if k:
                out.setdefault(k, a["i"])
    return out


def steam_achievements_url(raw):
    """Build the achievements URL from whatever the user pasted.

    Steam has two profile forms and they are NOT interchangeable:
      /profiles/76561198093257608  -> numeric id, keep that path
      /id/Fanik-/                   -> vanity name, must STAY on /id/, because
                                        /profiles/<vanity> is not a valid route
    A bare SteamID64 or a bare vanity name is accepted too.
    """
    s = (raw or "").strip().strip('"').strip("'")
    if not s:
        raise ValueError("пустая ссылка")
    if not s.startswith("http"):
        s = ("https://steamcommunity.com/profiles/" + s if s.isdigit()
             else "https://steamcommunity.com/id/" + s)

    m = re.search(r"steamcommunity\.com/(?:profiles/(\d{17})|id/([A-Za-z0-9._-]+))",
                  s, re.I)
    if not m:
        raise ValueError("не похоже на ссылку на профиль Steam")

    if m.group(1):
        base = "https://steamcommunity.com/profiles/" + m.group(1)
    else:
        base = "https://steamcommunity.com/id/" + m.group(2)

    tail = s[m.end():]
    base += tail if "/stats" in tail else "/stats/218620/achievements"
    if "l=" not in tail:
        base += ("&" if "?" in base else "?") + "l=english"
    return base


def scrape_steam(url):
    """Pull the unlocked achievement names off a public Steam profile page."""
    url = steam_achievements_url(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        html = r.read().decode("utf-8", "replace")

    # NB: the profile page renders <h3 class="ellipsis">, the global-stats page a
    # bare <h3> -- the tag therefore must allow attributes.
    rows = re.findall(r'<div class="achieveTxt">\s*<h3[^>]*>(.*?)</h3>', html, re.S)
    if not rows:
        raise ValueError("страница профиля не вернула список достижений")

    def clean(x):
        return re.sub(r"<[^>]+>", "", x).replace("&amp;", "&").strip()

    # A bare "Unlocked" is NOT proof of an unlock: "Megalo-Mania" alone reads
    # "using a fully unlocked Maniac perk deck", and Steam adds a service row
    # reading "1 hidden achievement remaining". Require the real marker.
    unlocked = set()
    for block in re.split(r'<div[^>]*class="achieveRow', html)[1:]:
        h3 = re.search(r'<div class="achieveTxt">\s*<h3[^>]*>(.*?)</h3>', block, re.S)
        if not h3:
            continue
        earned = (re.search(r'class="achieveUnlockTime"', block)
                  or re.search(r"Unlocked\s+\d", block))
        if earned:
            unlocked.add(clean(h3.group(1)))

    idx = name_index()
    ids, unknown, hidden = set(), [], 0
    for nm in unlocked:
        if HIDDEN_ROW.match(nm):
            hidden += 1
            continue
        k = _norm_key(nm)
        if k in idx:
            ids.add(idx[k])
        else:
            unknown.append(nm)
    return ids, unknown, len(unlocked) - hidden


def read_mod_dump():
    """The companion mod's progress file, if present."""
    if not os.path.exists(MOD_DUMP):
        return None, "файл мода не найден: " + MOD_DUMP
    try:
        with open(MOD_DUMP, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:                              # noqa: BLE001
        return None, "не прочитан файл мода: %s" % e

    names = d.get("unlocked") or d.get("done") or []
    if d.get("ids"):
        return {int(x) for x in d["ids"]}, None
    idx = name_index()
    ids = set()
    for nm in names:
        k = _norm_key(str(nm))
        if k in idx:
            ids.add(idx[k])
    return ids, None


def broadcast(event, payload):
    for q in FEEDS:
        q.append((event, payload))


def _unused_watch_mod():
    """Poll the mod's dump; push anything new to open browsers."""
    last = None
    while True:
        try:
            if os.path.exists(MOD_DUMP):
                m = os.path.getmtime(MOD_DUMP)
                if last is not None and m != last:
                    ids, err = read_mod_dump()
                    if ids:
                        added, _ = STORE.merge(ids, source="mod")
                        if added:
                            broadcast("progress", {"added": added,
                                                   "total": len(STORE.done)})
                    last = m
            time.sleep(1.5)
        except Exception as e:                          # noqa: BLE001
            print("watch_mod:", e)
            time.sleep(3)


# ----------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, rel, ctype):
        p = os.path.join(RES, rel)
        if not os.path.exists(p):
            return self._send(404, {"error": "not found: " + rel})
        with open(p, "rb") as f:
            return self._send(200, f.read(), ctype)

    # GET
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._file("ui.html", "text/html; charset=utf-8")
        if path == "/api/data":
            return self._send(200, load_data())
        if path == "/api/progress":
            STORE.refresh()
            snap = snapshot()
            snap["steam"] = WATCHER.status if WATCHER else {"enabled": False}
            snap["goal"] = dict(STORE.goal)
            return self._send(200, snap)
        if path == "/api/reconcile":
            # Drop progress Steam does not know about -- but only when the scrape
            # looks COMPLETE, because a partial page must never delete anything.
            STORE.refresh()
            url = (body.get("url") or "").strip() or STORE.meta.get("steam_url") or ""
            if not url:
                return self._send(400, {"error": "не задан профиль Steam"})
            try:
                ids, _u, _t = scrape_steam(url)
            except Exception as e:                      # noqa: BLE001
                return self._send(400, {"error": str(e)})
            done = set(STORE.done)
            extra = sorted(done - ids)
            trust = len(ids) >= 0.9 * len(done) if done else False
            if not trust:
                return self._send(200, {"trusted": False, "extra": len(extra),
                                        "kept": len(extra),
                                        "total": len(done),
                                        "note": "страница Steam выглядит неполной, "
                                                "лишние оставлены как есть"})
            for i in extra:
                STORE.set_one(i, False, source="reconcile")
            return self._send(200, {"trusted": True, "removed": len(extra),
                                    "total": len(STORE.done)})

        if path == "/api/goal":
            if WATCHER:
                WATCHER.poll_now()
            return self._send(200, dict(STORE.goal))

        if path == "/api/steam/status":
            return self._send(200, WATCHER.status if WATCHER else {"enabled": False})

        if path == "/api/health":
            return self._send(200, {"ok": True,
                                    "version": _ver.VERSION,
                                    "progress_file": STORE.path,
                                    "done": len(STORE.done)})

        if path == "/api/update/check":
            return self._send(200, update_check())

        if path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = []
            FEEDS.append(q)
            try:
                self.wfile.write(b"retry: 3000\n\n")
                self.wfile.flush()
                last_ping = time.time()
                while True:
                    if q:
                        ev, data = q.pop(0)
                        msg = ("event: %s\ndata: %s\n\n"
                               % (ev, json.dumps(data, ensure_ascii=False)))
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    elif time.time() - last_ping > 20:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        last_ping = time.time()
                    time.sleep(0.5)
            except Exception:                          # noqa: BLE001
                pass
            finally:
                if q in FEEDS:
                    FEEDS.remove(q)
            return
        return self._send(404, {"error": "no route"})

    # POST
    def _merge_names(self, names, source="paste"):
        idx = name_index()
        ids, unknown = set(), []
        for nm in names:
            if HIDDEN_ROW.match(nm):
                continue
            k = _norm_key(nm)
            if k in idx:
                ids.add(idx[k])
            elif k.lstrip("-0123456789 "):
                unknown.append(nm)
        added, _ = STORE.merge(ids, source=source)
        snap = snapshot()
        broadcast("progress", {"added": added, "total": snap["total"]})
        return {"imported": len(ids), "added": len(added),
                "unknown": unknown[:25], **snap}

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:                              # noqa: BLE001
            body = {}

        if path == "/api/toggle":
            STORE.refresh()
            changed = STORE.set_one(int(body["id"]), bool(body.get("done")))
            snap = snapshot()
            broadcast("progress", {"toggled": int(body["id"]),
                                   "done": bool(body.get("done")),
                                   "total": snap["total"]})
            return self._send(200, {"changed": changed, **snap})

        if path == "/api/import/steam":
            try:
                ids, unknown, total = scrape_steam(body.get("url", ""))
            except Exception as e:                      # noqa: BLE001
                return self._send(400, {"error": str(e)})
            added, _ = STORE.merge(ids, source="steam")
            snap = snapshot()
            broadcast("progress", {"added": added, "total": snap["total"]})
            return self._send(200, {"imported": len(ids), "added": len(added),
                                    "steam_total": total,
                                    "unknown": unknown[:20], **snap})

        if path == "/api/import/file":
            # a local file left anywhere on disk, by path
            src = (body.get("path") or "").strip()
            if not src:
                return self._send(400, {"error": "не указан путь к файлу"})
            src = os.path.expandvars(os.path.expanduser(src))
            if not os.path.isfile(src):
                return self._send(400, {"error": "файл не найден: " + src})
            try:
                with open(src, encoding="utf-8") as f:
                    raw = f.read()
                try:
                    obj = json.loads(raw)
                except Exception:                       # noqa: BLE001
                    obj = [x.strip() for x in raw.splitlines()]
            except Exception as e:                      # noqa: BLE001
                return self._send(400, {"error": "не прочитан файл: %s" % e})
            if isinstance(obj, dict):
                obj = obj.get("done") or obj.get("unlocked") or obj.get("names") or []
            r = self._merge_names([str(x) for x in obj], source="file")
            return self._send(200, r)

        if path == "/api/import/names":
            names = body.get("names") or []
            return self._send(200, self._merge_names([str(x) for x in names],
                                                    source="paste"))

        if path == "/api/steam":
            if WATCHER is None:
                return self._send(503, {"error": "автообновление не запущено"})
            url = (body.get("url") or "").strip() or STORE.meta.get("steam_url") or ""
            enable = body.get("enable", True)
            st = WATCHER.configure(url, enable)
            STORE.meta["steam_url"] = url
            STORE.meta["steam_auto"] = bool(enable and url)
            STORE._save()
            return self._send(200, st)

        if path == "/api/reconcile":
            # Drop progress Steam does not know about -- but only when the scrape
            # looks COMPLETE, because a partial page must never delete anything.
            STORE.refresh()
            url = (body.get("url") or "").strip() or STORE.meta.get("steam_url") or ""
            if not url:
                return self._send(400, {"error": "не задан профиль Steam"})
            try:
                ids, _u, _t = scrape_steam(url)
            except Exception as e:                      # noqa: BLE001
                return self._send(400, {"error": str(e)})
            done = set(STORE.done)
            extra = sorted(done - ids)
            trust = (len(ids) >= 0.9 * len(done)) if done else False
            if not trust:
                return self._send(200, {"trusted": False, "kept": len(extra),
                                        "total": len(done),
                                        "note": "страница Steam выглядит неполной, "
                                                "лишние оставлены как есть"})
            for i in extra:
                STORE.set_one(i, False, source="reconcile")
            return self._send(200, {"trusted": True, "removed": len(extra),
                                    "total": len(STORE.done)})

        if path == "/api/goal":
            if "id" in body and body["id"] is not None:
                g = STORE.set_goal(int(body["id"]), body.get("count"))
            else:
                g = STORE.set_goal(None)
            broadcast("goal", g)
            return self._send(200, g)

        if path == "/api/goal/bump":
            g = STORE.bump_goal(body.get("delta"), body.get("value"))
            # reaching the target marks the achievement earned
            data = load_data()
            tg = next((a["tg"] for a in data["achievements"] if a["i"] == g.get("id")), None)
            if tg and g.get("count", 0) >= tg:
                STORE.set_one(g["id"], True, source="goal")
            broadcast("goal", g)
            broadcast("progress", {"toggled": g.get("id"), "done": True,
                                   "total": len(STORE.done)})
            return self._send(200, g)

        if path == "/api/count":
            # any counter achievement, pinned or not
            aid = int(body["id"])
            n = STORE.bump_count(aid, body.get("delta"), body.get("value"))
            data = load_data()
            tg = next((a["tg"] for a in data["achievements"] if a["i"] == aid), None)
            if tg and n >= tg:
                STORE.set_one(aid, True, source="goal")
            out = {"id": aid, "count": n, "target": tg,
                   "goal": dict(STORE.goal), "counts": dict(STORE.counts),
                   "total": len(STORE.done)}
            broadcast("count", out)
            return self._send(200, out)

        if path == "/api/update/install":
            return self._send(200, update_install_async())

        if path == "/api/verify":
            import verify as _v
            R = _v.run(set(STORE.done))
            return self._send(200, {"ok": R.ok(), "facts": R.facts,
                                    "problems": R.problems[:50],
                                    "warnings": R.warnings[:50]})

        if path == "/api/reset":
            STORE.refresh()
            n = STORE.reset()
            if body.get("wipe"):
                STORE.forget()
            broadcast("progress", {"total": 0, "reset": True})
            return self._send(200, {"cleared": n, "wiped": bool(body.get("wipe")),
                                    **snapshot()})

        return self._send(404, {"error": "no route"})


WATCHER = None


def main():
    port = int(os.environ.get("PD2_PORT", "8899"))
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print("\n  Порт %d уже занят — сервер там уже запущен." % port)
        print("  Просто открой http://127.0.0.1:%d" % port)
        print("  Если он не отвечает, закрой старый через Task Manager и запусти снова.\n")
        return
    srv.daemon_threads = True
    global WATCHER
    WATCHER = SteamWatcher(STORE, scrape_steam, broadcast)
    WATCHER.start()
    if WATCHER.enabled:
        print("автообновление из Steam: каждые %d сек" % POLL_SECONDS)
    else:
        print("автообновление выключено — включи кнопкой в приложении")

    print("PAYDAY 2 tracker  ->  http://127.0.0.1:%d" % port)
    print("игра:            %s" % GAME_DIR)
    print("прогресс:        %s (%d)" % (STORE.path, len(STORE.done)))
    print("Ctrl+C — выход")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nостановлено")


if __name__ == "__main__":
    main()