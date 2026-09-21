"""Merge disjoint engine_match.py slices and recompute paired statistics."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()

    shards = [json.loads(path.read_text(encoding="utf-8")) for path in args.inputs]
    if not shards:
        parser.error("at least one input is required")
    reference = shards[0]
    invariant = ("a_name", "b_name", "a_exe", "a_model", "b_exe", "b_model",
                 "seconds", "max_plies", "fixed_depth")
    for shard in shards[1:]:
        for key in invariant:
            if shard[key] != reference[key]:
                raise ValueError(f"incompatible shard field {key}: {shard[key]!r}")

    games = [game for shard in shards for game in shard["games"]]
    by_opening: dict[int, list[dict]] = {}
    for game in games:
        by_opening.setdefault(game["opening"], []).append(game)
    for opening, pair in by_opening.items():
        if len(pair) != 2 or {game["a_red"] for game in pair} != {True, False}:
            raise ValueError(f"opening {opening} does not contain one complete color pair")
    if len(games) != 2 * len(by_opening):
        raise ValueError("duplicate or incomplete games")

    games.sort(key=lambda game: (game["opening"], not game["a_red"]))
    scores = [game["a_score"] for game in games]
    pair_scores = [sum(game["a_score"] for game in by_opening[opening])
                   for opening in sorted(by_opening)]
    rng = random.Random(20260921)
    bootstrap = []
    for _ in range(20_000):
        sample = sum(pair_scores[rng.randrange(len(pair_scores))]
                     for _ in pair_scores)
        bootstrap.append(50.0 * sample / len(pair_scores))
    bootstrap.sort()

    result = {key: reference[key] for key in invariant}
    result.update({
        "shards": [str(path) for path in args.inputs],
        "opening_pairs": len(by_opening),
        "games": games,
        "pair_scores_a": pair_scores,
        "a_score": sum(scores),
        "b_score": len(scores) - sum(scores),
        "a_score_percent": 100.0 * sum(scores) / len(scores),
        "a_ci95_percent": [bootstrap[int(.025 * len(bootstrap))],
                           bootstrap[int(.975 * len(bootstrap))]],
        "a_wins": sum(score == 1 for score in scores),
        "draws": sum(score == .5 for score in scores),
        "a_losses": sum(score == 0 for score in scores),
    })
    for side in ("a", "b"):
        result[f"{side}_nodes"] = sum(
            game[f"{side}_stats"]["nodes"] for game in games)
        searches = sum(game[f"{side}_stats"]["searches"] for game in games)
        result[f"{side}_mean_depth"] = sum(
            game[f"{side}_stats"]["depth_sum"] for game in games) / max(1, searches)

    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    summary_keys = ("a_name", "b_name", "opening_pairs", "a_score", "b_score",
                    "a_score_percent", "a_ci95_percent", "a_wins", "draws",
                    "a_losses", "a_mean_depth", "b_mean_depth")
    print(json.dumps({key: result[key] for key in summary_keys},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
