#!/usr/bin/env python3
"""Expose Pikafish through the line protocol used by xiangqi_ai.cpp."""

import os
import subprocess
import sys
from pathlib import Path


def xy_to_uci(r1, c1, r2, c2):
    return f"{chr(97 + c1)}{9 - r1}{chr(97 + c2)}{9 - r2}"


def uci_to_xy(move):
    if len(move) < 4:
        raise ValueError(f"invalid UCI move: {move!r}")
    return 9 - int(move[1]), ord(move[0]) - 97, 9 - int(move[3]), ord(move[2]) - 97


class Bridge:
    def __init__(self):
        here = Path(__file__).resolve().parent
        configured = os.environ.get("PIKAFISH_PST_PATH")
        if configured:
            executable = Path(configured)
        elif os.name == "nt":
            executable = here / "pikafish-pst" / "src" / "pikafish_pst.exe"
        else:
            executable = here / "pikafish_pst"
        executable = executable.resolve()
        self.process = subprocess.Popen(
            [str(executable)], cwd=str(executable.parent),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        self.moves = []
        seconds = float(os.environ.get("PIKAFISH_MOVE_TIME", "5"))
        self.movetime_ms = max(1, round(seconds * 1000))
        self._initialize()

    def send(self, line):
        if self.process.poll() is not None:
            raise RuntimeError("Pikafish process has exited")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def wait_for(self, prefix):
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError(f"Pikafish exited while waiting for {prefix}")
            line = line.strip()
            if line.startswith(prefix):
                return line

    def _initialize(self):
        self.send("uci")
        self.wait_for("uciok")
        self.send("setoption name Threads value 1")
        self.send("setoption name Hash value 128")
        self.send("setoption name Ponder value false")
        self.send("isready")
        self.wait_for("readyok")

    def search(self):
        suffix = " moves " + " ".join(self.moves) if self.moves else ""
        self.send("position startpos" + suffix)
        self.send(f"go movetime {self.movetime_ms}")
        score = None
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Pikafish exited during search")
            parts = line.strip().split()
            if parts and parts[0] == "info" and "score" in parts:
                index = parts.index("score")
                if index + 2 < len(parts) and parts[index + 1] in ("cp", "mate"):
                    try:
                        score = (parts[index + 1], int(parts[index + 2]))
                    except ValueError:
                        pass
            if parts and parts[0] == "bestmove":
                break
        if len(parts) < 2 or parts[1] in ("(none)", "none", "0000"):
            print("resign", flush=True)
            return
        move = parts[1]
        self.moves.append(move)
        output = "move {} {} {} {}".format(*uci_to_xy(move))
        if score is not None:
            output += f" score {score[0]} {score[1]}"
        print(output, flush=True)

    def run(self):
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
            elif command == "move" and len(parts) >= 5:
                self.moves.append(xy_to_uci(*[int(value) for value in parts[1:5]]))
            elif command == "search":
                self.search()
            elif command == "quit":
                break
            # side/forbid are accepted but need no action. Turn comes from history;
            # standard UCI has no single-forbidden-move setting.

    def close(self):
        if self.process.poll() is None:
            try:
                self.send("quit")
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()


def main():
    bridge = None
    try:
        bridge = Bridge()
        bridge.run()
    except Exception as exc:
        print(f"pikafish bridge error: {exc}", file=sys.stderr, flush=True)
        print("resign", flush=True)
        return 1
    finally:
        if bridge is not None:
            bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
