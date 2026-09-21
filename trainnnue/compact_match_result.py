"""Create a reviewable Git-sized match record from a full move-audit JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    result = json.loads(args.input.read_text(encoding="utf-8"))
    games = result.get("games", [])
    result["move_audit"] = {
        "plies_checked": sum(len(game.get("moves", [])) for game in games),
        "illegal_moves": sum(
            game.get("reason") in {"illegal_move", "bad_move"} for game in games
        ),
        "engine_exits": sum(game.get("reason") == "engine_exit" for game in games),
        "full_result_sha256": sha256(args.input),
        "note": "Full move lists are reproducible with the checked-in runner and are omitted here for Git size.",
    }
    for game in games:
        game.pop("moves", None)

    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
