"""Merge V2 shards into an exactly side-balanced, position-deduplicated dataset."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import numpy as np

from train import RECORD_DTYPE_V2, load_records, split_masks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--per-side", type=int, default=500_000)
    parser.add_argument("--seed", type=int, default=74003)
    args = parser.parse_args()

    chunks = [load_records(path) for path in args.inputs]
    if any(chunk.dtype != RECORD_DTYPE_V2 for chunk in chunks):
        raise ValueError("all input shards must be augmented V2 records")
    records = np.concatenate(chunks)
    raw = len(records)

    # Match train.py's unconditional validity filtering so the delivered file
    # contains one million records that are actually usable for training.
    valid = np.abs(records["score_red"].astype(np.int32)) < 19999
    valid &= (records["flags"] & 1) == 0
    records = records[valid]
    filtered = len(records)

    # NNUE cannot observe repetition history.  Deduplicate by exactly what it
    # can observe: board plus side to move.  Keeping one representative also
    # prevents identical positions leaking across game-based data splits.
    key_bytes = np.empty((len(records), 91), dtype=np.uint8)
    key_bytes[:, :90] = records["board"].view(np.uint8).reshape(-1, 90)
    key_bytes[:, 90] = records["stm"]
    keys = key_bytes.view(np.dtype((np.void, 91))).reshape(-1)
    _, first, inverse = np.unique(keys, return_index=True, return_inverse=True)
    groups = len(first)
    score_min = np.full(groups, np.iinfo(np.int16).max, dtype=np.int16)
    score_max = np.full(groups, np.iinfo(np.int16).min, dtype=np.int16)
    pst_min = np.full(groups, np.iinfo(np.int16).max, dtype=np.int16)
    pst_max = np.full(groups, np.iinfo(np.int16).min, dtype=np.int16)
    outcome_min = np.full(groups, np.iinfo(np.int8).max, dtype=np.int8)
    outcome_max = np.full(groups, np.iinfo(np.int8).min, dtype=np.int8)
    np.minimum.at(score_min, inverse, records["score_red"])
    np.maximum.at(score_max, inverse, records["score_red"])
    np.minimum.at(pst_min, inverse, records["pst_red"])
    np.maximum.at(pst_max, inverse, records["pst_red"])
    np.minimum.at(outcome_min, inverse, records["outcome_red"])
    np.maximum.at(outcome_max, inverse, records["outcome_red"])
    teacher_conflict_mask = score_min != score_max
    pst_conflict_mask = pst_min != pst_max
    consistent = ~teacher_conflict_mask & ~pst_conflict_mask

    # A zero mixed with one otherwise-consistent non-zero score is commonly a
    # history-dependent repetition result.  Prefer the observable normal score
    # in that narrow case.  Never choose arbitrarily between two different
    # non-zero teacher scores, and never repair a PST conflict.
    nonzero = records["score_red"] != 0
    nz_min = np.full(groups, np.iinfo(np.int16).max, dtype=np.int16)
    nz_max = np.full(groups, np.iinfo(np.int16).min, dtype=np.int16)
    nz_first = np.full(groups, len(records), dtype=np.int64)
    nz_indices = np.flatnonzero(nonzero)
    np.minimum.at(nz_min, inverse[nonzero], records["score_red"][nonzero])
    np.maximum.at(nz_max, inverse[nonzero], records["score_red"][nonzero])
    np.minimum.at(nz_first, inverse[nonzero], nz_indices)
    resolved_zero_history = (teacher_conflict_mask & ~pst_conflict_mask
                             & (nz_first < len(records)) & (nz_min == nz_max))
    keep_mask = consistent | resolved_zero_history
    conflicting_groups = int(np.sum(~keep_mask))
    kept_groups = np.flatnonzero(keep_mask)
    representatives = first[kept_groups].copy()
    repaired = resolved_zero_history[kept_groups]
    representatives[repaired] = nz_first[kept_groups[repaired]]
    records = records[representatives].copy()
    # A final game result is stochastic from a static position.  If duplicate
    # occurrences disagree, retain the deterministic search label but suppress
    # the small result-loss component for that position.
    outcome_conflict = outcome_min[kept_groups] != outcome_max[kept_groups]
    records["outcome_red"][outcome_conflict] = -1
    unique = len(records)

    rng = np.random.default_rng(args.seed)
    selected = []
    available = {}
    split_names = ("train", "validation", "calibration")
    split_masks_values = split_masks(records["game_id"].astype(np.int64))
    # Preserve the existing 70/15/15 game split while making each split itself
    # exactly side-balanced.  With the one-million target this is 350k/75k/75k
    # per side, respectively.
    split_targets = (int(args.per_side * 0.70),
                     int(args.per_side * 0.15),
                     args.per_side - int(args.per_side * 0.70)
                     - int(args.per_side * 0.15))
    for split_name, split_mask, target in zip(
            split_names, split_masks_values, split_targets):
        for side in (0, 1):
            idx = np.flatnonzero(split_mask & (records["stm"] == side))
            available[f"{split_name}_{side}"] = len(idx)
            if len(idx) < target:
                raise ValueError(
                    f"only {len(idx)} unique valid records for {split_name}, "
                    f"stm={side}; need {target}"
                )
            rng.shuffle(idx)
            selected.append(idx[:target])
    keep = np.concatenate(selected)
    rng.shuffle(keep)
    records = records[keep]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as out:
        out.write(struct.pack("<8sII", b"XQNNUE2\0", 2, RECORD_DTYPE_V2.itemsize))
        records.tofile(out)

    print({
        "raw": raw,
        "valid_noncheck": filtered,
        "unique_board_stm": unique,
        "discarded_conflicting_groups": conflicting_groups,
        "teacher_conflicting_groups": int(np.sum(teacher_conflict_mask)),
        "pst_conflicting_groups": int(np.sum(pst_conflict_mask)),
        "zero_history_groups_resolved": int(np.sum(resolved_zero_history)),
        "outcome_conflicts_set_unknown": int(np.sum(outcome_conflict)),
        "available_by_split_side": available,
        "written": len(records),
        "written_red": int(np.sum(records["stm"] == 0)),
        "written_black": int(np.sum(records["stm"] == 1)),
        "games": int(len(np.unique(records["game_id"]))),
        "output": str(args.output),
    })


if __name__ == "__main__":
    main()
