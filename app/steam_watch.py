# -*- coding: utf-8 -*-
"""Poll the public Steam profile and push new achievements to the open page.

No game mod needed: PAYDAY 2 mirrors every achievement to Steam, so the profile
page is the ground truth. The server re-reads it on a timer and merges whatever
it finds -- merging, never replacing, because a profile can briefly render fewer
rows and that must never wipe a tick.
"""
import json, os, re, threading, time, urllib.request

POLL_SECONDS = 180          # 3 minutes: often enough while playing, polite to Steam
MIN_INTERVAL = 60


class SteamWatcher(threading.Thread):
    def __init__(self, store, scrape_fn, broadcast_fn):
        super().__init__(daemon=True)
        self.store = store
        self.scrape = scrape_fn
        self.broadcast = broadcast_fn
        self.url = store.meta.get("steam_url") or ""
        self.enabled = bool(self.url)
        self.status = {
            "enabled": self.enabled,
            "last_check": None,
            "last_ok": None,
            "last_error": None,
            "found": 0,
            "interval": POLL_SECONDS,
            "checks": 0,
            "fails": 0,
        }
        self._wake = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------- control
    def configure(self, url, enable=True):
        with self._lock:
            self.url = url or ""
            self.enabled = bool(self.url) and enable
        self.status.update({"enabled": self.enabled, "last_error": None})
        if self.enabled:
            self.poll_now()
        return self.status

    def poll_now(self):
        self._wake.set()

    # --------------------------------------------------------------- loop
    def run(self):
        while True:
            if self.enabled:
                self._check()
            # sleep in slices so poll_now() is responsive
            waited = 0.0
            while waited < (MIN_INTERVAL if not self.enabled else POLL_SECONDS):
                if self._wake.wait(2):
                    self._wake.clear()
                    break
                waited += 2

    def _check(self):
        self.status["checks"] += 1
        self.status["last_check"] = time.time()
        try:
            ids, _unknown, total = self.scrape(self.url)
        except Exception as e:                          # noqa: BLE001
            self.status["last_error"] = str(e)
            self.status["fails"] += 1
            # back off when Steam refuses, so a bad URL does not hammer it
            if self.status["fails"] >= 5:
                self.enabled = False
                self.status["enabled"] = False
                self.status["last_error"] += " (автообновление выключено)"
            self.broadcast("steam", self.status)
            return

        self.status["fails"] = 0
        self.status["last_error"] = None
        self.status["last_ok"] = time.time()
        self.status["found"] = len(ids)
        added, _removed = self.store.merge(ids, source="steam-auto")
        if added:
            self.broadcast("progress", {"added": added, "total": len(self.store.done),
                                        "source": "steam-auto"})
            self.broadcast("steam", self.status)
        elif self.status.get("_announced") is not False:
            self.broadcast("steam", self.status)
            self.status["_announced"] = True