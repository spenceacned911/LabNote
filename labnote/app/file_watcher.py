from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable


class PollingFileWatcher:
    def __init__(self, on_change: Callable[[Path], None], interval: float = 1.1) -> None:
        self.on_change = on_change
        self.interval = interval
        self._mtimes: dict[Path, float] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="labnote-file-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def watch(self, path: Path) -> None:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return
        with self._lock:
            self._mtimes[path] = mtime

    def unwatch(self, path: Path) -> None:
        with self._lock:
            self._mtimes.pop(path, None)

    def clear(self) -> None:
        with self._lock:
            self._mtimes.clear()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            changed_paths: list[Path] = []
            with self._lock:
                watched_items = list(self._mtimes.items())
            for path, last_mtime in watched_items:
                try:
                    current_mtime = path.stat().st_mtime
                except OSError:
                    continue
                if current_mtime > last_mtime:
                    changed_paths.append(path)
                    with self._lock:
                        self._mtimes[path] = current_mtime
            for path in changed_paths:
                self.on_change(path)
            time.sleep(self.interval)
