"""Merge version-2 datasets and deduplicate positions by (game_id, ply)."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import numpy as np

import train


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    chunks = [train.load_records(path) for path in args.inputs]
    if any(chunk.dtype != train.RECORD_DTYPE_V2 for chunk in chunks):
        raise ValueError("merge_data requires version-2 records")
    combined = np.concatenate(chunks)
    key = (combined["game_id"].astype(np.uint64) << np.uint64(16)) \
        | combined["ply"].astype(np.uint64)
    _, first = np.unique(key, return_index=True)
    merged = combined[np.sort(first)]
    with args.output.open("wb") as stream:
        stream.write(struct.pack(
            "<8sII", b"XQNNUE2\0", 2, train.RECORD_DTYPE_V2.itemsize
        ))
        merged.tofile(stream)
    print({
        "inputs": [len(chunk) for chunk in chunks],
        "combined": len(combined),
        "deduplicated": len(merged),
        "duplicates_removed": len(combined) - len(merged),
    })


if __name__ == "__main__":
    main()
