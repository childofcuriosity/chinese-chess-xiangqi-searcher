"""Parallel paired A/B self-play for two Xiangqi engine executables."""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
from pathlib import Path


RESULT_RE = re.compile(r"^Result:\s*(.+)$", re.MULTILINE)


def game_outcome(result, candidate_red):
    text = result.lower()
    if text.startswith("draw"):
        return "draw"
    if text.startswith("red wins"):
        return "win" if candidate_red else "loss"
    if text.startswith("black wins"):
        return "loss" if candidate_red else "win"
    return "error"


def run_game(task, selfplay, baseline, candidate, max_plies, output_dir):
    seconds, candidate_red, repeat = task
    red = candidate if candidate_red else baseline
    black = baseline if candidate_red else candidate
    color_tag = "candidate_red" if candidate_red else "baseline_red"
    time_tag = str(seconds).replace(".", "p")
    stem = f"{time_tag}s_{color_tag}_r{repeat + 1}"
    out_path = output_dir / f"{stem}.txt"

    cmd = [
        sys.executable,
        str(selfplay),
        str(red),
        str(black),
        str(max_plies),
        str(seconds),
    ]
    timeout = max(120.0, max_plies * seconds * 4.0 + 60.0)
    try:
        completed = subprocess.run(
            cmd,
            cwd=selfplay.parent,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout
        out_path.write_text(output, encoding="utf-8")
        match = RESULT_RE.search(output)
        result = match.group(1).strip() if match else "missing result"
        outcome = game_outcome(result, candidate_red)
        if completed.returncode != 0:
            outcome = "error"
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        out_path.write_text(output + "\nTIMEOUT\n", encoding="utf-8")
        result, outcome = "timeout", "error"

    return {
        "seconds": seconds,
        "candidate_color": "red" if candidate_red else "black",
        "repeat": repeat + 1,
        "result": result,
        "candidate_outcome": outcome,
        "log": str(out_path),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run paired, parallel self-play between baseline and candidate engines."
    )
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--times", default="0.5,0.75,1.0,1.5,2.0",
        help="comma-separated seconds per move",
    )
    parser.add_argument("--max-plies", type=int, default=160)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2),
        help="parallel games; one game normally occupies one logical CPU",
    )
    parser.add_argument("--output", type=Path, default=Path("ab_selfplay_results"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    selfplay = root / "selfplay.py"
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    if not baseline.is_file() or not candidate.is_file():
        parser.error("baseline and candidate executables must exist")

    try:
        times = [float(value) for value in args.times.split(",")]
    except ValueError:
        parser.error("--times must contain comma-separated numbers")
    if not times or any(value <= 0 for value in times):
        parser.error("all time controls must be positive")

    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        (seconds, candidate_red, repeat)
        for seconds in times
        for repeat in range(args.repeats)
        for candidate_red in (True, False)
    ]
    jobs = min(max(1, args.jobs), len(tasks))
    print(f"Running {len(tasks)} games with {jobs} parallel jobs")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [
            pool.submit(
                run_game, task, selfplay, baseline, candidate,
                args.max_plies, output_dir,
            )
            for task in tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"{result['seconds']:>5g}s candidate-{result['candidate_color']:<5} "
                f"{result['candidate_outcome']:<5} ({result['result']})"
            )

    order = {"win": 0, "draw": 1, "loss": 2, "error": 3}
    results.sort(key=lambda item: (item["seconds"], item["repeat"], item["candidate_color"]))
    totals = {name: sum(r["candidate_outcome"] == name for r in results) for name in order}
    decided = totals["win"] + totals["draw"] + totals["loss"]
    score = totals["win"] + 0.5 * totals["draw"]
    score_pct = 100.0 * score / decided if decided else 0.0
    summary = {
        "baseline": str(baseline),
        "candidate": str(candidate),
        "times": times,
        "max_plies": args.max_plies,
        "repeats": args.repeats,
        "jobs": jobs,
        "totals": totals,
        "candidate_score": score,
        "candidate_score_percent": score_pct,
        "games": results,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("-" * 60)
    print(
        f"Candidate: {totals['win']}W {totals['draw']}D {totals['loss']}L "
        f"({score:.1f}/{decided}, {score_pct:.1f}%), errors={totals['error']}"
    )
    print(f"Summary: {summary_path}")

    return 1 if totals["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
