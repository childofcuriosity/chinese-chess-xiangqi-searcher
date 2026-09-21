"""Five-round Swiss tournament for the eight trained evaluation models."""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import subprocess
import sys
from pathlib import Path


def all_pairings(items):
    if not items:
        yield []
        return
    first = items[0]
    for i in range(1, len(items)):
        second = items[i]
        rest = items[1:i] + items[i + 1:]
        for tail in all_pairings(rest):
            yield [(first, second)] + tail


def buchholz(players):
    scores = {p["id"]: p["game_points"] for p in players}
    return {p["id"]: sum(scores[o] for o in p["opponents"]) for p in players}


def standings(players):
    bh = buchholz(players)
    return sorted(players, key=lambda p: (-p["game_points"], -bh[p["id"]],
                                          -p["wins"], p["seed"]))


def choose_pairings(players, round_no):
    ordered = standings(players)
    if round_no == 1:
        ids = [p["id"] for p in ordered]
        random.Random(20260921).shuffle(ids)
        return list(zip(ids[:4], ids[4:]))
    rank = {p["id"]: i for i, p in enumerate(ordered)}
    by_id = {p["id"]: p for p in players}
    best = None
    for pairs in all_pairings([p["id"] for p in ordered]):
        repeats = sum(b in by_id[a]["opponents"] for a, b in pairs)
        score_gap = sum(abs(by_id[a]["game_points"] - by_id[b]["game_points"])
                        for a, b in pairs)
        rank_gap = sum(abs(rank[a] - rank[b]) for a, b in pairs)
        key = (repeats, score_gap, rank_gap, tuple(sorted(tuple(sorted(x)) for x in pairs)))
        if best is None or key < best[0]:
            best = (key, pairs)
    return best[1]


def report(players):
    bh = buchholz(players)
    rows = []
    for rank, p in enumerate(standings(players), 1):
        games = p["games"]
        rows.append({"rank": rank, "id": p["id"], "name": p["name"],
                     "game_points": p["game_points"], "games": games,
                     "score_percent": 100 * p["game_points"] / max(1, games),
                     "wins": p["wins"], "draws": p["draws"], "losses": p["losses"],
                     "buchholz_game_points": bh[p["id"]],
                     "opponents": p["opponents"]})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=float, default=.1)
    p.add_argument("--pairs-per-match", type=int, default=24)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--max-plies", type=int, default=160)
    p.add_argument("--output", type=Path, default=Path("trainnnue/swiss_8models_5rounds.json"))
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    nnue_exe = root / "nnue_engine.exe"
    pst_exe = root / "xiangqi_pst_fair.exe"
    specs = [
        ("pst", "PST baseline", pst_exe, None),
        ("d5h8", "D5 H8 (old best)", nnue_exe, root / "best.nnue"),
        ("d3h8", "D3 1M H8", nnue_exe, root / "d3_balanced1m_h8_full100_gpu.nnue"),
        ("d3h16", "D3 1M H16", nnue_exe, root / "d3_balanced1m_h16_full100_gpu.nnue"),
        ("d4h8r", "D4 H8 random-init", nnue_exe, root / "d4_balanced1m_h8_random_full100_gpu.nnue"),
        ("d4h8d3", "D4 H8 D3-init", nnue_exe, root / "d4_balanced1m_h8_fromd3_full100_gpu.nnue"),
        ("d4h16r", "D4 H16 random-init", nnue_exe, root / "d4_balanced1m_h16_random_full100_gpu.nnue"),
        ("d4h16d3", "D4 H16 D3-init", nnue_exe, root / "d4_balanced1m_h16_fromd3_full100_gpu.nnue"),
    ]
    for _, _, exe, model in specs:
        if not exe.exists() or (model is not None and not model.exists()):
            p.error(f"missing participant file: {model or exe}")
    players = [{"id": ident, "name": name, "exe": str(exe),
                "model": str(model) if model else None, "seed": i,
                "game_points": 0.0, "games": 0, "wins": 0, "draws": 0,
                "losses": 0, "opponents": [], "pair_scores": []}
               for i, (ident, name, exe, model) in enumerate(specs)]
    by_id = {x["id"]: x for x in players}
    cpus = [x for x in (0, 2, 4, 6) if x < (os.cpu_count() or 1)]
    if len(cpus) < 4:
        cpus = list(range(min(4, os.cpu_count() or 1)))
    if len(cpus) < 4:
        p.error("four logical CPUs are required")
    out_dir = root / "swiss_rounds"
    out_dir.mkdir(exist_ok=True)
    rounds = []
    for round_no in range(1, args.rounds + 1):
        pairs = choose_pairings(players, round_no)
        print(f"ROUND {round_no} PAIRINGS " + ", ".join(f"{a}-{b}" for a, b in pairs), flush=True)
        running = []
        for match_no, ((a_id, b_id), cpu) in enumerate(zip(pairs, cpus), 1):
            a, b = by_id[a_id], by_id[b_id]
            result_path = out_dir / f"round{round_no}_match{match_no}.json"
            log_path = out_dir / f"round{round_no}_match{match_no}.log"
            cmd = [sys.executable, str(root / "engine_match.py"),
                   "--a-exe", a["exe"], "--b-exe", b["exe"],
                   "--a-name", a["name"], "--b-name", b["name"],
                   "--openings", str(root / "openings_final2_192.fen"),
                   "--opening-start", str((round_no - 1) * args.pairs_per_match),
                   "--limit", str(args.pairs_per_match), "--seconds", str(args.seconds),
                   "--max-plies", str(args.max_plies), "--cpu-index", str(cpu),
                   "--output", str(result_path)]
            if a["model"]:
                cmd += ["--a-model", a["model"]]
            if b["model"]:
                cmd += ["--b-model", b["model"]]
            log = log_path.open("w", encoding="utf-8")
            running.append((a_id, b_id, result_path, log,
                            subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)))
        round_matches = []
        for a_id, b_id, result_path, log, proc in running:
            code = proc.wait()
            log.close()
            if code:
                raise RuntimeError(f"match {a_id}-{b_id} failed; see {result_path.with_suffix('.log')}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            a, b = by_id[a_id], by_id[b_id]
            n = len(result["games"])
            a_score, b_score = result["a_score"], result["b_score"]
            a["game_points"] += a_score; b["game_points"] += b_score
            a["games"] += n; b["games"] += n
            a["wins"] += result["a_wins"]; b["wins"] += result["a_losses"]
            a["draws"] += result["draws"]; b["draws"] += result["draws"]
            a["losses"] += result["a_losses"]; b["losses"] += result["a_wins"]
            a["opponents"].append(b_id); b["opponents"].append(a_id)
            a["pair_scores"].extend(result["pair_scores_a"])
            b["pair_scores"].extend([2 - x for x in result["pair_scores_a"]])
            round_matches.append({"a": a_id, "b": b_id, "a_score": a_score,
                                  "b_score": b_score, "games": n,
                                  "result_file": str(result_path)})
            print(f"ROUND {round_no} RESULT {a_id} {a_score:g}-{b_score:g} {b_id}", flush=True)
        rounds.append({"round": round_no, "opening_start": (round_no - 1) * args.pairs_per_match,
                       "matches": round_matches, "standings": report(players)})
        payload = {"format": "Swiss pairings; ranking by total game points (win=1, draw=0.5)",
                   "settings": vars(args) | {"output": str(args.output), "cpu_indices": cpus},
                   "participants": [{k: v for k, v in x.items() if k != "pair_scores"} for x in players],
                   "rounds": rounds, "current_standings": report(players)}
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("STANDINGS " + " | ".join(f"{x['rank']}:{x['id']} {x['score_percent']:.2f}%" for x in report(players)), flush=True)


if __name__ == "__main__":
    main()
