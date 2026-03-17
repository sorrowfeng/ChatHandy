"""TCP socket IPC client — communicates with hand/server.py."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


def _app_root() -> Path:
    """返回应用根目录：打包后为 _internal（_MEIPASS），源码时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


def _python_exe() -> Path:
    """找可用的 python.exe：打包后从系统 PATH 查找，源码时用当前解释器。"""
    if getattr(sys, "frozen", False):
        # 打包后 sys.executable 是 ChatHandy.exe，需要找系统 Python
        found = shutil.which("python") or shutil.which("python3")
        if found:
            return Path(found)
        # 回退：尝试 exe 同级目录有没有 python.exe（便携版 Python）
        candidate = Path(sys.executable).parent / "python.exe"
        if candidate.exists():
            return candidate
        raise RuntimeError(
            "未找到 Python 解释器，请确认系统已安装 Python 并加入 PATH。"
        )
    # 源码运行：用当前解释器，pythonw → python
    exe = Path(sys.executable)
    candidate = exe.parent / "python.exe"
    return candidate if candidate.exists() else exe


def _free_port() -> int:
    """Ask the OS for a free ephemeral port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class CommandRunner:
    _SERVER = _app_root() / "hand" / "server.py"

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._sock: socket.socket | None = None
        self._rfile = None
        self._wfile = None
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def start_hand(self) -> tuple[bool, str]:
        if self.hand_running:
            return False, "灵巧手已在运行中"

        port = _free_port()

        # CREATE_NEW_CONSOLE：新控制台窗口，无管道，stdout/stderr 可见
        self._proc = subprocess.Popen(
            [str(_python_exe()), "-u", str(self._SERVER), str(port)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        # 连接 socket（重试，等待 server 完成 bind+listen）
        try:
            self._sock = self._connect(port, timeout=10)
        except TimeoutError as exc:
            self._proc.kill()
            self._proc = None
            return False, str(exc)

        self._sock.settimeout(30.0)   # 最多等 30 s 做硬件初始化
        self._rfile = self._sock.makefile("rb")
        self._wfile = self._sock.makefile("wb")

        # 等待初始化完成（含回零，约 5–6 s）
        try:
            resp = self._read_json_line()
            if resp.get("status") != "ok":
                self._cleanup()
                return False, resp.get("msg", "连接失败")
            self._sock.settimeout(None)   # 初始化成功后取消超时
            return True, resp.get("msg", "就绪")
        except Exception as exc:
            self._cleanup()
            return False, f"启动异常：{exc}"

    def stop_hand(self) -> tuple[bool, str]:
        if not self.hand_running:
            return False, "灵巧手未在运行"
        try:
            self._send({"cmd": "quit"}, wait_reply=False)
            self._proc.wait(timeout=4)          # type: ignore[union-attr]
        except Exception:
            self._proc.kill()                   # type: ignore[union-attr]
        finally:
            self._cleanup()
        return True, "灵巧手已停止"

    def move(
        self,
        positions: list[int],
        velocity: int = 20000,
        max_current: int = 1000,
    ) -> tuple[bool, str]:
        if not self.hand_running:
            return False, "灵巧手未启动，请先说「启动灵巧手」"
        resp = self._send({
            "cmd":         "move",
            "positions":   positions,
            "velocity":    velocity,
            "max_current": max_current,
        })
        return resp.get("status") == "ok", resp.get("msg", "")

    @property
    def hand_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _connect(port: int, timeout: float = 10) -> socket.socket:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                s = socket.socket()
                s.connect(("127.0.0.1", port))
                return s
            except (ConnectionRefusedError, OSError):
                time.sleep(0.2)
        raise TimeoutError("无法连接到手控服务（端口未就绪）")

    def _read_json_line(self) -> dict:
        while True:
            raw = self._rfile.readline()
            if not raw:
                return {"status": "error", "msg": "服务器已关闭"}
            line = raw.decode("utf-8", errors="replace").strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

    def _write_cmd(self, cmd: dict) -> None:
        data = (json.dumps(cmd) + "\n").encode("utf-8")
        self._wfile.write(data)
        self._wfile.flush()

    def _send(self, cmd: dict, wait_reply: bool = True) -> dict:
        with self._lock:
            try:
                self._write_cmd(cmd)
                if wait_reply:
                    return self._read_json_line()
            except Exception as exc:
                return {"status": "error", "msg": str(exc)}
        return {}

    def _cleanup(self) -> None:
        for obj in (self._rfile, self._wfile, self._sock):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        self._rfile = self._wfile = self._sock = None
        self._proc = None
