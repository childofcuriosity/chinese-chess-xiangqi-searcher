#!/usr/bin/env python3
"""Expose ElephantEye 3.1 (UCCI) through the project's line protocol."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


def xy_to_iccs(r1: int, c1: int, r2: int, c2: int) -> str:
    return f"{chr(97 + c1)}{9 - r1}{chr(97 + c2)}{9 - r2}"


def iccs_to_xy(move: str) -> tuple[int, int, int, int]:
    if len(move) < 4:
        raise ValueError(f"invalid ICCS move: {move!r}")
    return 9 - int(move[1]), ord(move[0]) - 97, 9 - int(move[3]), ord(move[2]) - 97


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
        configured = os.environ.get("ELEEYE_PATH", r"E:\ElephantEye\BIN\ELEEYE.EXE")
        executable = Path(configured).resolve()
        if not executable.is_file():
            raise FileNotFoundError(f"ElephantEye executable not found: {executable}")
        self.process = subprocess.Popen(
            [str(executable)], cwd=str(executable.parent),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, encoding="gb18030", errors="replace", bufsize=1,
        )
        self.position = "startpos"
        self.moves: list[str] = []
        seconds = float(os.environ.get("ELEEYE_MOVE_TIME", "0.1"))
        self.movetime_ms = max(1, round(seconds * 1000))
        self._initialize()

    def send(self, line: str) -> None:
        if self.process.poll() is not None:
            raise RuntimeError("ElephantEye process has exited")
        assert self.process.stdin is not None
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def wait_for(self, prefix: str) -> str:
        assert self.process.stdout is not None
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError(f"ElephantEye exited while waiting for {prefix}")
            line = line.strip()
            if line.startswith(prefix):
                return line

    def _initialize(self) -> None:
        self.send("ucci")
        self.wait_for("ucciok")
        self.send("setoption usemillisec true")
        self.send("setoption usebook false")
        self.send("setoption ponder false")
        self.send("setoption batch true")
        self.send("setoption hashsize 128")
        self.send("setoption randomness none")
        self.send("setoption newgame")

    def search(self) -> None:
        suffix = " moves " + " ".join(self.moves) if self.moves else ""
        self.send(f"position {self.position}" + suffix)
        self.send(f"go time {self.movetime_ms} movestogo 1")
        depth = 0
        nodes = 0
        assert self.process.stdout is not None
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("ElephantEye exited while searching")
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
            if parts and parts[0] in ("bestmove", "nobestmove"):
                break
        if parts[0] == "nobestmove" or len(parts) < 2 or parts[1] in ("none", "0000"):
            print("resign", flush=True)
            return
        move = parts[1]
        self.moves.append(move)
        print("move {} {} {} {} depth {} nodes {}".format(
            *iccs_to_xy(move), depth, nodes), flush=True)

    def run(self) -> None:
        for raw in sys.stdin:
            parts = raw.strip().split()
            if not parts:
                continue
            command = parts[0].lower()
            if command == "ready":
                print("readyok", flush=True)
            elif command == "time" and len(parts) >= 2:
                self.movetime_ms = max(1, round(float(parts[1]) * 1000))
            elif command == "setboard" and len(parts) >= 3:
                self.position = "fen " + " ".join(parts[1:])
                self.moves.clear()
                self.send("setoption newgame")
            elif command == "move" and len(parts) >= 5:
                self.moves.append(xy_to_iccs(*[int(value) for value in parts[1:5]]))
            elif command == "search":
                self.search()
            elif command == "quit":
                break
            # side/depth/forbid are accepted for compatibility. The FEN and
            # move list determine the side to move; this match uses time mode.

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
        print(f"ElephantEye bridge error: {exc}", file=sys.stderr, flush=True)
        print("resign", flush=True)
        return 1
    finally:
        if bridge is not None:
            bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
