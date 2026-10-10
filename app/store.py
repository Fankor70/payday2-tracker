# -*- coding: utf-8 -*-
"""Progress store: one source of truth, written atomically, never double-counted.

Rules that keep the numbers right:
  * progress is a set of achievement ids -- merging is a union, never an append
  * every write goes to a temp file then os.replace, so a crash mid-write cannot
    leave a half-written progress file
  * each update is stamped and appended to a small history so the UI can show
    what changed rather than guessing
  * unknown ids are kept but reported, so a mismatch between game data versions
    is visible instead of silently shrinking the count
"""
import json, os, time, threading, sys


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


class Store:
    def __init__(self, path=None):
        self.path = path or os.path.join(HERE, "progress.json")
        self.lock = threading.RLock()
        self.subscribers = []
        self.done = set()
        self.meta = {"updated": None, "sources": [], "unknown": []}
        self.history = []
        self.goal = {}          # {"id": int, "count": int} -- the pinned one
        self.counts = {}        # {id: number} -- every counter achievement
        self._mtime = None
        self.load()

    def refresh(self):
        """Pick up a change written by another process (or by hand).

        Two server instances sharing one file used to overwrite each other and
        silently reset the progress, so every read re-checks the file first.
        """
        with self.lock:
            try:
                m = os.path.getmtime(self.path)
            except OSError:
                return False
            if self._mtime is not None and m == self._mtime:
                return False
            self.load()
            return True

    # ------------------------------------------------------------------ io
    def load(self):
        with self.lock:
            if not os.path.exists(self.path):
                return
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                self.done = set(int(x) for x in d.get("done", []))
                self.meta = d.get("meta") or self.meta
                self.history = d.get("history") or []
                self.goal = d.get("goal") or {}
                self.counts = {int(k): int(v)
                               for k, v in (d.get("counts") or {}).items()}
                # an older file kept the number only inside goal; do not lose it
                if self.goal.get("id") is not None:
                    self.counts.setdefault(int(self.goal["id"]),
                                           int(self.goal.get("count", 0)))
                self._mtime = os.path.getmtime(self.path)
            except Exception as e:                      # noqa: BLE001
                print("store: не прочитан прошлый файл:", e)

    def _save(self):
        payload = {
            "done": sorted(self.done),
            "meta": self.meta,
            "history": self.history[-200:],
            "goal": self.goal,
            "counts": {str(k): v for k, v in self.counts.items()},
            "saved_at": time.time(),
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)                      # atomic on Windows too
        self._mtime = os.path.getmtime(self.path)

    # ---------------------------------------------------------------- merge
    def merge(self, ids, source="manual", replace=False):
        """Union a set of ids into the progress. Returns (added, removed)."""
        incoming = {int(x) for x in ids}
        with self.lock:
            before = set(self.done)
            if replace:
                self.done = incoming
            else:
                self.done |= incoming
            added = sorted(self.done - before)
            removed = sorted(before - self.done) if replace else []
            srcs = self.meta.setdefault("sources", [])
            if source not in srcs:
                srcs.append(source)
            self.meta["updated"] = time.time()
            if added or removed:
                self.history.append({
                    "t": time.time(), "source": source,
                    "added": added[:50], "removed": removed[:50],
                    "total": len(self.done),
                })
                self._save()
            return added, removed

    def set_one(self, ach_id, done, source="manual"):
        with self.lock:
            before = len(self.done)
            if done:
                self.done.add(int(ach_id))
            else:
                self.done.discard(int(ach_id))
            if before != len(self.done):
                self.history.append({"t": time.time(), "source": source,
                                     "toggle": int(ach_id), "done": bool(done),
                                     "total": len(self.done)})
                self.meta["updated"] = time.time()
                self._save()
                return True
            return False

    def forget(self):
        """Drop the file entirely -- a clean slate for a fresh import."""
        with self.lock:
            self.done.clear()
            self.meta = {"updated": None, "sources": [], "unknown": []}
            self.history = []
            self.counts = {}
            if os.path.exists(self.path):
                os.remove(self.path)
            return True

    def set_goal(self, ach_id=None, count=None):
        """Pin a cumulative achievement as the main goal, with its live counter."""
        with self.lock:
            if ach_id is None:
                self.goal = {}
            else:
                ach_id = int(ach_id)
                if count is not None:
                    self.counts[ach_id] = max(0, int(count))
                else:
                    self.counts.setdefault(ach_id, 0)
                self.goal = {"id": ach_id, "count": self.counts.get(ach_id, 0)}
            self._save()
            return dict(self.goal)

    def set_counts(self, mapping):
        """Write several counters at once; saves only if something changed."""
        with self.lock:
            changed = False
            for k, v in mapping.items():
                k = int(k)
                if self.counts.get(k) != int(v):
                    self.counts[k] = int(v)
                    changed = True
            if changed:
                self._save()
            return changed

    def bump_count(self, ach_id, delta=None, value=None):
        """Move any counter achievement's number, pinned or not."""
        with self.lock:
            ach_id = int(ach_id)
            cur = int(self.counts.get(ach_id, 0))
            if value is not None:
                nxt = int(value)
            else:
                nxt = cur + int(delta or 1)
            self.counts[ach_id] = max(0, nxt)
            if self.goal.get("id") == ach_id:
                self.goal["count"] = self.counts[ach_id]
            self._save()
            return self.counts[ach_id]

    def bump_goal(self, delta=None, value=None):
        with self.lock:
            if "id" not in self.goal:
                return dict(self.goal)
            self.counts[self.goal["id"]] = max(
                0, int(value) if value is not None
                else self.counts.get(self.goal["id"], 0) + int(delta or 1))
            self.goal["count"] = self.counts[self.goal["id"]]
            self._save()
            return dict(self.goal)

    def reset(self, source="manual"):
        with self.lock:
            n = len(self.done)
            self.done.clear()
            self.history.append({"t": time.time(), "source": source,
                                 "reset": True, "total": 0})
            self.meta["updated"] = time.time()
            self._save()
            return n

    def snapshot(self):
        with self.lock:
            return {"done": sorted(self.done), "total": len(self.done),
                    "meta": self.meta, "history": self.history[-30:],
                    "goal": dict(self.goal), "counts": dict(self.counts)}

    # ------------------------------------------------------------ live feed
    def notify(self, payload):
        for q in list(self.subscribers):
            try:
                q.append(payload)
            except Exception:                           # noqa: BLE001
                pass