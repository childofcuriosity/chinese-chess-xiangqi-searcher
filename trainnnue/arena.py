"""Sequential, paired, single-core arena for the PST and NNUE engines."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import subprocess
import time
from pathlib import Path


def parse_fen(fen: str):
    placement, side, *_ = fen.split()
    board = []
    for row in placement.split('/'):
        expanded = []
        for ch in row:
            if ch.isdigit():
                expanded.extend('.' * int(ch))
            else:
                expanded.append(ch)
        if len(expanded) != 9:
            raise ValueError(f"bad FEN row: {row}")
        board.append(expanded)
    if len(board) != 10:
        raise ValueError(f"bad FEN: {fen}")
    return board, 0 if side.lower().startswith('w') else 1


class Engine:
    def __init__(self, executable: Path, nnue: Path | None, blend: float,
                 cpu_index: int):
        command = [str(executable.resolve())]
        if nnue is not None:
            command += ["--nnue", str(nnue.resolve()), "--nnue-blend", str(blend)]
        env = os.environ.copy()
        env.pop("XQ_NNUE_BLEND", None)
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            env[key] = "1"
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
            bufsize=1, env=env,
        )
        # The experiment contract is one logical CPU.  The engines themselves
        # are single-threaded; pinning also prevents migration between cores.
        if os.name == "nt":
            if not ctypes.windll.kernel32.SetProcessAffinityMask(
                int(self.process._handle), 1 << cpu_index
            ):
                raise OSError("SetProcessAffinityMask failed")
        elif hasattr(os, "sched_setaffinity"):
            allowed = sorted(os.sched_getaffinity(0))
            os.sched_setaffinity(
                self.process.pid, {allowed[cpu_index % len(allowed)]}
            )
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
            line = line.strip()
            if line.startswith(prefix):
                return line

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
                raise RuntimeError("engine exited while searching")
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


def play_game(pst: Path, candidate: Path, model: Path, fen: str,
              candidate_red: bool, seconds: float, max_plies: int, blend: float,
              fixed_depth: int, cpu_index: int):
    board, side = parse_fen(fen)
    base = Engine(pst, None, blend, cpu_index)
    nnue = Engine(candidate, model, blend, cpu_index)
    base.setup(fen, not candidate_red, seconds, fixed_depth)
    nnue.setup(fen, candidate_red, seconds, fixed_depth)
    red_engine = nnue if candidate_red else base
    black_engine = base if candidate_red else nnue
    engines = [red_engine, black_engine]
    elapsed = {"pst": 0.0, "nnue": 0.0}
    node_count = {"pst": 0, "nnue": 0}
    depth_sum = {"pst": 0, "nnue": 0}
    searches = {"pst": 0, "nnue": 0}
    fallback_count = {"pst": 0, "nnue": 0}
    timeout_count = {"pst": 0, "nnue": 0}
    plies = 0
    result = 0.5
    reason = "max_plies"
    try:
        for plies in range(1, max_plies + 1):
            engine = engines[side]
            move, used, meta = engine.search()
            key = "nnue" if engine is nnue else "pst"
            elapsed[key] += used
            searches[key] += 1
            node_count[key] += meta.get("nodes", 0)
            depth_sum[key] += meta.get("depth", 0)
            fallback_count[key] += meta.get("depth", 1) == 0
            timeout_count[key] += meta.get("timeout", 0)
            if move is None:
                winner = side ^ 1
                result = 1.0 if winner == (0 if candidate_red else 1) else 0.0
                reason = "resign"
                break
            r1, c1, r2, c2 = move
            if not all((0 <= r1 < 10, 0 <= r2 < 10, 0 <= c1 < 9, 0 <= c2 < 9)):
                winner = side ^ 1
                result = 1.0 if winner == (0 if candidate_red else 1) else 0.0
                reason = "bad_move"
                break
            captured = board[r2][c2]
            board[r2][c2] = board[r1][c1]
            board[r1][c1] = '.'
            engines[side ^ 1].play(move)
            if captured in ("K", "k"):
                winner = side
                result = 1.0 if winner == (0 if candidate_red else 1) else 0.0
                reason = "general_captured"
                break
            side ^= 1
    finally:
        base.close()
        nnue.close()
    return {
        "score": result, "candidate_red": candidate_red, "plies": plies,
        "reason": reason, "pst_seconds": elapsed["pst"], "nnue_seconds": elapsed["nnue"],
        "pst_nodes": node_count["pst"], "nnue_nodes": node_count["nnue"],
        "pst_searches": searches["pst"], "nnue_searches": searches["nnue"],
        "pst_depth_sum": depth_sum["pst"], "nnue_depth_sum": depth_sum["nnue"],
        "pst_fallbacks": fallback_count["pst"], "nnue_fallbacks": fallback_count["nnue"],
        "pst_timeouts": timeout_count["pst"], "nnue_timeouts": timeout_count["nnue"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pst", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--openings", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=0.05)
    parser.add_argument("--max-plies", type=int, default=160)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--blend", type=float, default=1.0)
    parser.add_argument("--fixed-depth", type=int, default=0)
    parser.add_argument("--cpu-index", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cpu_count = os.cpu_count() or 1
    if not (0 <= args.cpu_index < cpu_count):
        parser.error(f"--cpu-index must be in [0, {cpu_count - 1}]")
    openings = [line.strip() for line in args.openings.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit > 0:
        openings = openings[:args.limit]
    games = []
    for index, fen in enumerate(openings):
        for candidate_red in (True, False):
            game = play_game(args.pst, args.candidate, args.model, fen,
                             candidate_red, args.seconds, args.max_plies, args.blend,
                             args.fixed_depth, args.cpu_index)
            game.update({"opening": index, "fen": fen})
            games.append(game)
            print(f"opening={index} candidate_red={candidate_red} score={game['score']} "
                  f"plies={game['plies']} reason={game['reason']}", flush=True)
    scores = [g["score"] for g in games]
    pair_scores = [games[i]["score"] + games[i + 1]["score"]
                   for i in range(0, len(games), 2)]
    rng = random.Random(20260921)
    bootstrap = []
    if pair_scores:
        for _ in range(20000):
            sample = sum(pair_scores[rng.randrange(len(pair_scores))]
                         for _ in pair_scores)
            bootstrap.append(50.0 * sample / len(pair_scores))
        bootstrap.sort()
        ci95 = [bootstrap[int(0.025 * len(bootstrap))],
                bootstrap[int(0.975 * len(bootstrap))]]
    else:
        ci95 = [0.0, 0.0]
    summary = {
        "pst": str(args.pst), "candidate": str(args.candidate), "model": str(args.model),
        "seconds": args.seconds, "max_plies": args.max_plies,
        "cpu_affinity": "single logical CPU",
        "cpu_index": args.cpu_index,
        "nnue_blend": args.blend,
        "fixed_depth": args.fixed_depth,
        "opening_pairs": len(openings), "games": games,
        "candidate_score": sum(scores),
        "candidate_score_percent": 100.0 * sum(scores) / len(scores) if scores else 0.0,
        "paired_bootstrap_ci95_percent": ci95,
        "wins": sum(s == 1.0 for s in scores),
        "draws": sum(s == 0.5 for s in scores),
        "losses": sum(s == 0.0 for s in scores),
        "pst_wall_seconds": sum(g["pst_seconds"] for g in games),
        "nnue_wall_seconds": sum(g["nnue_seconds"] for g in games),
        "pst_nodes": sum(g["pst_nodes"] for g in games),
        "nnue_nodes": sum(g["nnue_nodes"] for g in games),
        "pst_mean_depth": (sum(g["pst_depth_sum"] for g in games)
                           / max(1, sum(g["pst_searches"] for g in games))),
        "nnue_mean_depth": (sum(g["nnue_depth_sum"] for g in games)
                            / max(1, sum(g["nnue_searches"] for g in games))),
        "pst_fallbacks": sum(g["pst_fallbacks"] for g in games),
        "nnue_fallbacks": sum(g["nnue_fallbacks"] for g in games),
        "pst_timeouts": sum(g["pst_timeouts"] for g in games),
        "nnue_timeouts": sum(g["nnue_timeouts"] for g in games),
    }
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "games"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
