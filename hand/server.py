#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LHandPro 手控服务 — TCP socket 协议

用法: python server.py <port>

协议（JSON 行，UTF-8）:
  客户端 → 服务端:  {"cmd": "move",  "positions":[...], "velocity":N, "max_current":N}
                    {"cmd": "quit"}
  服务端 → 客户端:  {"status": "ok"|"error", "msg": "..."}
  第一行 = 连接初始化结果（含回零，约 5 s）

stdout/stderr 保持原样输出到控制台，供用户观察。
"""
import json
import socket
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent / "LHandProLib_CANFD_Test_python"
sys.path.insert(0, str(_LIB_DIR))

from lhandpro_controller import LHandProController  # noqa: E402


def _make_io(conn: socket.socket):
    """返回 (读文件, 写文件) 二进制对。"""
    return conn.makefile("rb"), conn.makefile("wb")


def _emit(wfile, obj: dict) -> None:
    data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    wfile.write(data)
    wfile.flush()


def _read_cmd(rfile) -> dict | None:
    raw = rfile.readline()
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace").strip())
    except json.JSONDecodeError:
        return {"cmd": "invalid"}


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python server.py <port>", flush=True)
        sys.exit(1)

    port = int(sys.argv[1])

    # ── 1. 先监听，让 runner 可以立即连接 ──────────────────────────────────
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    print(f"[server] 监听 127.0.0.1:{port} ...", flush=True)

    conn, _ = srv.accept()
    srv.close()
    rfile, wfile = _make_io(conn)
    print("[server] runner 已连接，开始初始化灵巧手...", flush=True)

    # ── 2. 初始化控制器 ────────────────────────────────────────────────────
    try:
        with LHandProController(communication_mode="CANFD") as controller:
            connected = controller.connect(
                enable_motors=True,
                home_motors=True,
                home_wait_time=5.0,
                canfd_nom_baudrate=1000000,
                canfd_dat_baudrate=5000000,
            )

            if not connected:
                _emit(wfile, {"status": "error", "msg": "CANFD 设备连接失败"})
                return

            _emit(wfile, {"status": "ok", "msg": "灵巧手已就绪"})
            print("[server] 初始化完成，等待指令...", flush=True)

            # ── 3. 指令循环 ────────────────────────────────────────────────
            while True:
                cmd = _read_cmd(rfile)
                if cmd is None:
                    print("[server] 连接断开，退出", flush=True)
                    break

                action = cmd.get("cmd")

                if action == "quit":
                    print("[server] 收到 quit 指令，退出", flush=True)
                    break

                elif action == "move":
                    positions   = cmd.get("positions",   [0] * 6)
                    velocity    = cmd.get("velocity",    20000)
                    max_current = cmd.get("max_current", 1000)
                    print(f"[server] move → {positions}", flush=True)
                    success = controller.move_to_positions(
                        positions=positions,
                        velocity=velocity,
                        max_current=max_current,
                        wait_time=0,
                    )
                    _emit(wfile, {
                        "status": "ok" if success else "error",
                        "msg":    "运动完成" if success else "运动失败",
                    })

                else:
                    _emit(wfile, {"status": "error", "msg": f"未知指令: {action}"})

    except Exception as exc:
        print(f"[server] 异常: {exc}", flush=True)
        try:
            _emit(wfile, {"status": "error", "msg": str(exc)})
        except Exception:
            pass
    finally:
        try:
            controller.stop_motors()  # type: ignore[union-attr]
            print("[server] 电机已停止", flush=True)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
