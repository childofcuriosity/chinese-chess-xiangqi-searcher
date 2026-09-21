"""Paired match between any two Xiangqi engines, pinned to one logical CPU."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import LocalBoard


def parse_fen(fen: str):
    placement, side, *_ = fen.split()
    board = []
    for row in placement.split("/"):
        expanded = []
        for ch in row:
            expanded.extend("." * int(ch) if ch.isdigit() else ch)
        if len(expanded) != 9:
            raise ValueError(f"bad FEN row: {row}")
        board.append(expanded)
    if len(board) != 10:
        raise ValueError(f"bad FEN: {fen}")
    return board, 0 if side.lower().startswith("w") else 1


class Engine:
    def __init__(self, executable: Path, extra_args: list[str],
                 nnue: Path | None, blend: float, cpu_index: int):
        command = [str(executable.resolve()), *extra_args]
        if nnue is not None:
            command += ["--nnue", str(nnue.resolve()), "--nnue-blend", str(blend)]
        env = os.environ.copy()
        env.pop("XQ_NNUE_BLEND", None)
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            env[key] = "1"
        env["XQ_CPU_INDEX"] = str(cpu_index)
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", bufsize=1, env=env,
        )
        if os.name == "nt":
            if not ctypes.windll.kernel32.SetProcessAffinityMask(
                    int(self.process._handle), 1 << cpu_index):
                raise OSError("SetProcessAffinityMask failed")
        elif hasattr(os, "sched_setaffinity"):
            allowed = sorted(os.sched_getaffinity(0))
            os.sched_setaffinity(self.process.pid,
                                 {allowed[cpu_index % len(allowed)]})
        self.send("ready")
        self.wait_prefix("readyok")

    def send(self, line: str):
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def wait_prefix(self, prefix: str):
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("engine exited")
            if line.strip().startswith(prefix):
                return

    def setup(self, fen: str, plays_red: bool, seconds: float, fixed_depth: int):
        self.send(f"setboard {fen}")
        self.send("side black" if plays_red else "side red")
        self.send(f"time {seconds}")
        self.send(f"depth {fixed_depth}")

    def search(self):
        start = time.perf_counter()
        self.send("search")
        while True:
            line = self.process.stdout.readline()
            if not line:
                return (None, time.perf_counter() - start,
                        {"engine_exit": 1})
            fields = line.strip().split()
            if fields and fields[0] == "move" and len(fields) >= 5:
                meta = {}
                for name in ("depth", "nodes", "timeout"):
                    if name in fields:
                        meta[name] = int(fields[fields.index(name) + 1])
                return tuple(map(int, fields[1:5])), time.perf_counter() - start, meta
            if fields and fields[0] == "resign":
                return None, time.perf_counter() - start, {}

    def play(self, move):
        self.send("move " + " ".join(map(str, move)))

    def close(self):
        try:
            self.send("quit")
            self.process.wait(timeout=2)
        except Exception:
            self.process.kill()


def play_game(a_exe: Path, a_args: list[str], a_model: Path | None,
              b_exe: Path, b_args: list[str], b_model: Path | None,
              fen: str, a_red: bool,
              a_seconds: float, b_seconds: float, max_plies: int, blend: float,
              fixed_depth: int, cpu_index: int):
    board, side = parse_fen(fen)
    rules = LocalBoard()
    rules.board = [row[:] for row in board]
    rules.turn = "red" if side == 0 else "black"
    a = Engine(a_exe, a_args, a_model, blend, cpu_index)
    b = Engine(b_exe, b_args, b_model, blend, cpu_index)
    a.setup(fen, a_red, a_seconds, fixed_depth)
    b.setup(fen, not a_red, b_seconds, fixed_depth)
    engines = [a if a_red else b, b if a_red else a]
    stats = {"a": {"seconds": 0.0, "nodes": 0, "depth_sum": 0, "searches": 0,
                    "fallbacks": 0, "timeouts": 0, "engine_exits": 0},
             "b": {"seconds": 0.0, "nodes": 0, "depth_sum": 0, "searches": 0,
                    "fallbacks": 0, "timeouts": 0, "engine_exits": 0}}
    result, reason, plies = 0.5, "max_plies", 0
    moves = []
    try:
        for plies in range(1, max_plies + 1):
            engine = engines[side]
            move, used, meta = engine.search()
            key = "a" if engine is a else "b"
            st = stats[key]
            st["seconds"] += used
            st["nodes"] += meta.get("nodes", 0)
            st["depth_sum"] += meta.get("depth", 0)
            st["searches"] += 1
            st["fallbacks"] += meta.get("depth", 1) == 0
            st["timeouts"] += meta.get("timeout", 0)
            st["engine_exits"] += meta.get("engine_exit", 0)
            if move is None:
                winner = side ^ 1
                result = 1.0 if winner == (0 if a_red else 1) else 0.0
                reason = "engine_exit" if meta.get("engine_exit") else "resign"
                break
            r1, c1, r2, c2 = move
            if not all((0 <= r1 < 10, 0 <= r2 < 10, 0 <= c1 < 9, 0 <= c2 < 9)):
                winner = side ^ 1
                result = 1.0 if winner == (0 if a_red else 1) else 0.0
                reason = "bad_move"
                break
            move_record = {
                "ply": plies,
                "side": "red" if side == 0 else "black",
                "engine": key,
                "move": list(move),
                "seconds": used,
                **meta,
            }
            moves.append(move_record)
            if not rules.is_legal_move(r1, c1, r2, c2):
                winner = side ^ 1
                result = 1.0 if winner == (0 if a_red else 1) else 0.0
                reason = "illegal_move"
                move_record["piece"] = rules.board[r1][c1]
                move_record["target"] = rules.board[r2][c2]
                break
            captured = board[r2][c2]
            board[r2][c2] = board[r1][c1]
            board[r1][c1] = "."
            rules.move(r1, c1, r2, c2)
            engines[side ^ 1].play(move)
            if captured in ("K", "k"):
                result = 1.0 if side == (0 if a_red else 1) else 0.0
                reason = "general_captured"
                break
            side ^= 1
    finally:
        a.close()
        b.close()
    return {"a_score": result, "a_red": a_red, "plies": plies,
            "reason": reason, "moves": moves,
            "a_stats": stats["a"], "b_stats": stats["b"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a-exe", type=Path, required=True)
    p.add_argument("--a-arg", action="append", default=[])
    p.add_argument("--a-model", type=Path)
    p.add_argument("--b-exe", type=Path, required=True)
    p.add_argument("--b-arg", action="append", default=[])
    p.add_argument("--b-model", type=Path)
    p.add_argument("--a-name", required=True)
    p.add_argument("--b-name", required=True)
    p.add_argument("--openings", type=Path, required=True)
    p.add_argument("--opening-start", type=int, default=0)
    p.add_argument("--limit", type=int, default=24)
    p.add_argument("--seconds", type=float, default=0.1)
    p.add_argument("--a-seconds", type=float)
    p.add_argument("--b-seconds", type=float)
    p.add_argument("--max-plies", type=int, default=160)
    p.add_argument("--blend", type=float, default=1.0)
    p.add_argument("--fixed-depth", type=int, default=0)
    p.add_argument("--cpu-index", type=int, default=0)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    a_seconds = args.a_seconds if args.a_seconds is not None else args.seconds
    b_seconds = args.b_seconds if args.b_seconds is not None else args.seconds
    if a_seconds <= 0 or b_seconds <= 0:
        p.error("engine time controls must be positive")
    if not 0 <= args.cpu_index < (os.cpu_count() or 1):
        p.error("invalid --cpu-index")
    all_openings = [x.strip() for x in args.openings.read_text(encoding="utf-8").splitlines() if x.strip()]
    openings = all_openings[args.opening_start:args.opening_start + args.limit]
    if len(openings) != args.limit:
        p.error("not enough openings for requested slice")
    games = []
    for local_index, fen in enumerate(openings):
        for a_red in (True, False):
            game = play_game(args.a_exe, args.a_arg, args.a_model,
                             args.b_exe, args.b_arg, args.b_model,
                             fen, a_red, a_seconds, b_seconds, args.max_plies,
                             args.blend, args.fixed_depth, args.cpu_index)
            game.update({"opening": args.opening_start + local_index, "fen": fen})
            games.append(game)
            print(f"opening={args.opening_start + local_index} a_red={a_red} "
                  f"score={game['a_score']} plies={game['plies']} "
                  f"reason={game['reason']}", flush=True)
    scores = [g["a_score"] for g in games]
    pair_scores = [scores[i] + scores[i + 1] for i in range(0, len(scores), 2)]
    rng, bootstrap = random.Random(20260921), []
    for _ in range(20000):
        sample = sum(pair_scores[rng.randrange(len(pair_scores))] for _ in pair_scores)
        bootstrap.append(50.0 * sample / len(pair_scores))
    bootstrap.sort()
    summary = {
        "a_name": args.a_name, "b_name": args.b_name,
        "a_exe": str(args.a_exe), "a_args": args.a_arg,
        "a_model": str(args.a_model) if args.a_model else None,
        "b_exe": str(args.b_exe), "b_args": args.b_arg,
        "b_model": str(args.b_model) if args.b_model else None,
        "opening_start": args.opening_start, "opening_pairs": len(openings),
        "seconds": args.seconds,
        "a_seconds_per_move": a_seconds,
        "b_seconds_per_move": b_seconds,
        "max_plies": args.max_plies,
        "fixed_depth": args.fixed_depth, "cpu_index": args.cpu_index,
        "games": games, "pair_scores_a": pair_scores,
        "a_score": sum(scores), "b_score": len(scores) - sum(scores),
        "a_score_percent": 100.0 * sum(scores) / len(scores),
        "a_ci95_percent": [bootstrap[int(.025 * len(bootstrap))],
                           bootstrap[int(.975 * len(bootstrap))]],
        "a_wins": sum(x == 1 for x in scores),
        "draws": sum(x == .5 for x in scores),
        "a_losses": sum(x == 0 for x in scores),
    }
    for key in ("a", "b"):
        summary[f"{key}_nodes"] = sum(g[f"{key}_stats"]["nodes"] for g in games)
        searches = sum(g[f"{key}_stats"]["searches"] for g in games)
        used_seconds = sum(g[f"{key}_stats"]["seconds"] for g in games)
        summary[f"{key}_searches"] = searches
        summary[f"{key}_seconds"] = used_seconds
        summary[f"{key}_mean_seconds_per_search"] = used_seconds / max(1, searches)
        configured_seconds = a_seconds if key == "a" else b_seconds
        summary[f"{key}_time_utilization_percent"] = (
            100.0 * used_seconds / max(configured_seconds,
                                       searches * configured_seconds))
        summary[f"{key}_mean_depth"] = sum(g[f"{key}_stats"]["depth_sum"] for g in games) / max(1, searches)
        summary[f"{key}_engine_exits"] = sum(
            g[f"{key}_stats"].get("engine_exits", 0) for g in games)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("games", "pair_scores_a")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
