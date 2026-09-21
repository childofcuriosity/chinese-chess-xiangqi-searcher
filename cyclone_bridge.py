#!/usr/bin/env python3
"""Expose Cyclone 2007C (UCI) through the project's line protocol."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


def xy_to_uci(r1: int, c1: int, r2: int, c2: int) -> str:
    return f"{chr(97 + c1)}{9 - r1}{chr(97 + c2)}{9 - r2}"


def uci_to_xy(move: str) -> tuple[int, int, int, int]:
    if len(move) < 4:
        raise ValueError(f"invalid UCI move: {move!r}")
    return 9 - int(move[1]), ord(move[0]) - 97, 9 - int(move[3]), ord(move[2]) - 97


def normalize_fen(fen: str) -> str:
    """Expand the project's two-field FEN for older UCI parsers."""
    fields = fen.split()
    if len(fields) == 2:
        fields.extend(["-", "-", "0", "1"])
    if len(fields) != 6:
        raise ValueError(f"expected 2- or 6-field FEN, got {len(fields)}: {fen!r}")
    return " ".join(fields)


def pin_current_process(cpu_index: int) -> None:
    if os.name == "nt":
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        kernel32.SetProcessAffinityMask.restype = ctypes.c_int
        handle = kernel32.GetCurrentProcess()
        if not kernel32.SetProcessAffinityMask(handle, ctypes.c_size_t(1 << cpu_index)):
            raise OSError("SetProcessAffinityMask failed")
    elif hasattr(os, "sched_setaffinity"):
        allowed = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {allowed[cpu_index % len(allowed)]})


class Bridge:
    def __init__(self) -> None:
        cpu_index = int(os.environ.get("XQ_CPU_INDEX", "0"))
        pin_current_process(cpu_index)
        configured = os.environ.get("CYCLONE_PATH")
        if not configured:
            raise RuntimeError("CYCLONE_PATH is not set")
        executable = Path(configured).resolve()
        if not executable.is_file():
            raise FileNotFoundError(f"Cyclone executable not found: {executable}")
        self.process = subprocess.Popen(
            [str(executable)], cwd=str(executable.parent),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, encoding="gb18030", errors="replace", bufsize=1,
        )
        self.moves: list[str] = []
        self.position = "fen rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        seconds = float(os.environ.get("CYCLONE_MOVE_TIME", "0.1"))
        self.movetime_ms = max(1, round(seconds * 1000))
        self._initialize()

    def send(self, line: str) -> None:
        if self.process.poll() is not None:
            raise RuntimeError("Cyclone process has exited")
        assert self.process.stdin is not None
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def wait_for(self, prefix: str) -> str:
        assert self.process.stdout is not None
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError(f"Cyclone exited while waiting for {prefix}")
            line = line.strip()
            if line.startswith(prefix):
                return line

    def _initialize(self) -> None:
        self.send("uci")
        self.wait_for("uciok")
        self.send("setoption name Threads value 1")
        self.send("setoption name Hash value 128")
        self.send("setoption name Ponder value false")
        self.send("setoption name OwnBook value false")
        self.send("isready")
        self.wait_for("readyok")

    def search(self) -> None:
        suffix = " moves " + " ".join(self.moves) if self.moves else ""
        # Cyclone's pre-UCCI dialect uses `fen ...`, not `position fen ...`.
        self.send(self.position + suffix)
        self.send(f"go movetime {self.movetime_ms}")
        depth = 0
        nodes = 0
        assert self.process.stdout is not None
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Cyclone exited while searching")
            parts = line.strip().split()
            if parts and parts[0] == "info":
                for name in ("depth", "nodes"):
                    if name in parts:
                        try:
                            value = int(parts[parts.index(name) + 1])
                            if name == "depth":
                                depth = value
                            else:
                                nodes = value
                        except (ValueError, IndexError):
                            pass
            if parts and parts[0] == "bestmove":
                break
        if len(parts) < 2 or parts[1] in ("(none)", "none", "0000"):
            print("resign", flush=True)
            return
        move = parts[1]
        self.moves.append(move)
        print("move {} {} {} {} depth {} nodes {}".format(
            *uci_to_xy(move), depth, nodes), flush=True)

    def run(self) -> None:
        for raw in sys.stdin:
            parts = raw.strip().split()
            if not parts:
                continue
            command = parts[0].lower()
            if command == "ready":
                self.send("isready")
                self.wait_for("readyok")
                print("readyok", flush=True)
            elif command == "time" and len(parts) >= 2:
                self.movetime_ms = max(1, round(float(parts[1]) * 1000))
            elif command == "setboard" and len(parts) >= 3:
                self.position = "fen " + normalize_fen(" ".join(parts[1:]))
                self.moves.clear()
                self.send("ucinewgame")
            elif command == "move" and len(parts) >= 5:
                self.moves.append(xy_to_uci(*[int(value) for value in parts[1:5]]))
            elif command == "search":
                self.search()
            elif command == "quit":
                break
            # side/depth/forbid are accepted for compatibility. The FEN and
            # move list determine the side to move; this match uses movetime.

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                self.send("quit")
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()


def main() -> int:
    bridge = None
    try:
        bridge = Bridge()
        bridge.run()
    except Exception as exc:
        print(f"Cyclone bridge error: {exc}", file=sys.stderr, flush=True)
        print("resign", flush=True)
        return 1
    finally:
        if bridge is not None:
            bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
