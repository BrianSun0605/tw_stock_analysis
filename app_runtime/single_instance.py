"""Cross-platform single-instance file lock with a small discovery record."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class SingleInstance:
    def __init__(self, data_root: str):
        self.root = Path(data_root).resolve()
        self.lock_path = self.root / "app.lock"
        self.state_path = self.root / "instance.json"
        self._handle = None
        self._locked = False

    def acquire(self) -> bool:
        self.root.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, "a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self._handle = handle
        self._locked = True
        return True

    def write_state(self, *, port: int, version: str) -> None:
        if not self._locked:
            raise RuntimeError("instance lock is not held")
        payload = {
            "pid": os.getpid(),
            "port": int(port),
            "version": str(version),
        }
        temp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.root,
                prefix=".instance-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = handle.name
            os.replace(temp_path, self.state_path)
            temp_path = None
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def read_state(self) -> Dict[str, Any]:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            port = int(payload.get("port", 0))
            if not 1 <= port <= 65535:
                return {}
            return payload
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {}

    def release(self) -> None:
        if not self._locked or self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
            self._locked = False
            try:
                self.state_path.unlink(missing_ok=True)
            except OSError:
                pass

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("another instance is already running")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.release()
