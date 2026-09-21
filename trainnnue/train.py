"""Single-core CPU trainer for the compact Xiangqi HalfKA network.

The calibration temperature K is fitted first from held-out games and is then
treated as immutable.  It is deliberately not a torch Parameter.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import struct
import time
from dataclasses import dataclass
from pathlib import Path

# This experiment has a hard one-core contract.  Override inherited values as
# well as missing ones so a parent shell cannot silently give BLAS more cores.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
import torch
from torch import nn

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

MAGIC = b"XQNNUE1\0"
NUM_FEATURES = 9 * 14 * 90
PADDING_IDX = NUM_FEATURES
MAX_PIECES = 32
PIECE_TYPES = {"p": 0, "c": 1, "n": 2, "b": 3, "a": 4, "r": 5, "k": 6}
PIECE_INFO = {
    ord(piece): (piece_type, 0 if piece.isupper() else 1)
    for piece_type, lower in enumerate(("p", "c", "n", "b", "a", "r", "k"))
    for piece in (lower, lower.upper())
}

RECORD_DTYPE = np.dtype(
    [
        ("board", "S1", (90,)),
        ("score_red", "<i2"),
        ("nodes", "<u4"),
        ("game_id", "<u4"),
        ("ply", "<u2"),
        ("stm", "u1"),
        ("teacher_depth", "u1"),
        ("flags", "u1"),
        ("outcome_red", "i1"),
    ],
    align=False,
)
RECORD_DTYPE_V2 = np.dtype(RECORD_DTYPE.descr + [("pst_red", "<i2")], align=False)


@dataclass
class DatasetArrays:
    red: np.ndarray
    black: np.ndarray
    red_mirror: np.ndarray
    black_mirror: np.ndarray
    stm: np.ndarray
    score_stm: np.ndarray
    pst_stm: np.ndarray
    outcome_stm: np.ndarray
    game_id: np.ndarray
    depth: int


def load_records(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        header = f.read(16)
    if len(header) != 16:
        raise ValueError(f"short data header in {path}")
    magic, version, record_size = struct.unpack("<8sII", header)
    if magic == b"XQNNUE2\0" and version == 2 and record_size == RECORD_DTYPE_V2.itemsize:
        dtype = RECORD_DTYPE_V2
    elif magic == MAGIC and version == 1 and record_size == RECORD_DTYPE.itemsize:
        dtype = RECORD_DTYPE
    else:
        raise ValueError(
            f"unsupported data file {path}: magic={magic!r}, version={version}, "
            f"record_size={record_size}"
        )
    return np.fromfile(path, dtype=dtype, offset=16)


def orient_square(square: int, perspective: int, mirror: bool) -> int:
    r, c = divmod(square, 9)
    if perspective == 1:
        r, c = 9 - r, 8 - c
    if mirror:
        c = 8 - c
    return r * 9 + c


def feature_row(board: np.ndarray, perspective: int, mirror: bool) -> np.ndarray:
    chars = [x.decode("ascii") for x in board]
    own_general = "K" if perspective == 0 else "k"
    try:
        general_square = chars.index(own_general)
    except ValueError as exc:
        raise ValueError("position without both generals cannot be trained") from exc
    oriented_general = orient_square(general_square, perspective, mirror)
    gr, gc = divmod(oriented_general, 9)
    if not (7 <= gr <= 9 and 3 <= gc <= 5):
        raise ValueError(f"general outside palace: perspective={perspective}, square={general_square}")
    king_bucket = (gr - 7) * 3 + (gc - 3)

    result = np.full(MAX_PIECES, PADDING_IDX, dtype=np.int64)
    active = 0
    for square, piece in enumerate(chars):
        if piece == ".":
            continue
        piece_type = PIECE_TYPES[piece.lower()]
        piece_side = 0 if piece.isupper() else 1
        relative_side = 0 if piece_side == perspective else 1
        piece_class = piece_type * 2 + relative_side
        oriented_piece = orient_square(square, perspective, mirror)
        result[active] = (king_bucket * 14 + piece_class) * 90 + oriented_piece
        active += 1
    return result


def feature_rows(board: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build both perspectives and their mirrors with one board scan."""
    raw = board.tobytes()
    general_squares = (raw.find(b"K"), raw.find(b"k"))
    if general_squares[0] < 0 or general_squares[1] < 0:
        raise ValueError("position without both generals cannot be trained")

    buckets: list[tuple[int, int]] = []
    for perspective, square in enumerate(general_squares):
        r, c = divmod(square, 9)
        if perspective == 1:
            r, c = 9 - r, 8 - c
        if not (7 <= r <= 9 and 3 <= c <= 5):
            raise ValueError(
                f"general outside palace: perspective={perspective}, square={square}"
            )
        buckets.append(((r - 7) * 3 + (c - 3), (r - 7) * 3 + (5 - c)))

    rows = tuple(
        np.full(MAX_PIECES, PADDING_IDX, dtype=np.int64) for _ in range(4)
    )
    active = 0
    for square, piece in enumerate(raw):
        info = PIECE_INFO.get(piece)
        if info is None:
            continue
        piece_type, piece_side = info
        r, c = divmod(square, 9)
        for perspective in (0, 1):
            if perspective == 0:
                oriented_r, oriented_c = r, c
            else:
                oriented_r, oriented_c = 9 - r, 8 - c
            piece_class = piece_type * 2 + (piece_side != perspective)
            base = perspective
            rows[base][active] = (
                (buckets[perspective][0] * 14 + piece_class) * 90
                + oriented_r * 9 + oriented_c
            )
            rows[base + 2][active] = (
                (buckets[perspective][1] * 14 + piece_class) * 90
                + oriented_r * 9 + (8 - oriented_c)
            )
        active += 1
    return rows


def make_arrays(records: np.ndarray, quiet_only: bool) -> DatasetArrays:
    if len(records) == 0:
        raise ValueError("empty dataset")
    depths = np.unique(records["teacher_depth"])
    if len(depths) != 1:
        raise ValueError(f"one training run must use one teacher depth, got {depths}")

    valid = np.ones(len(records), dtype=bool)
    valid &= np.abs(records["score_red"].astype(np.int32)) < 19999
    valid &= (records["flags"] & 1) == 0  # never train checked positions
    if quiet_only:
        valid &= (records["flags"] & 2) == 0
    records = records[valid]

    red = np.empty((len(records), MAX_PIECES), dtype=np.int64)
    black = np.empty_like(red)
    red_m = np.empty_like(red)
    black_m = np.empty_like(red)
    for i, board in enumerate(records["board"]):
        red[i], black[i], red_m[i], black_m[i] = feature_rows(board)

    stm = records["stm"].astype(np.int64)
    score_red = records["score_red"].astype(np.float32)
    score_stm = np.where(stm == 0, score_red, -score_red).astype(np.float32)
    if "pst_red" in records.dtype.names:
        pst_red = records["pst_red"].astype(np.float32)
        pst_stm = np.where(stm == 0, pst_red, -pst_red).astype(np.float32)
    else:
        pst_stm = np.zeros(len(records), dtype=np.float32)
    outcome_red = records["outcome_red"].astype(np.float32)
    known = outcome_red >= 0
    outcome_red[known] *= 0.5
    outcome_stm = np.where(stm == 0, outcome_red, 1.0 - outcome_red)
    outcome_stm[~known] = np.nan
    return DatasetArrays(
        red, black, red_m, black_m, stm, score_stm, pst_stm,
        outcome_stm.astype(np.float32),
        records["game_id"].astype(np.int64), int(depths[0])
    )


def split_masks(game_id: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Whole games remain together.  SplitMix64 avoids the accidental identity
    # modulo 20 of the old multiplicative expression.
    mixed = game_id.astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15)
    mixed = (mixed ^ (mixed >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    mixed = (mixed ^ (mixed >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    mixed ^= mixed >> np.uint64(31)
    bucket = (mixed % np.uint64(20)).astype(np.int64)
    calibration = bucket < 3
    validation = (bucket >= 3) & (bucket < 6)
    training = ~(calibration | validation)
    return training, validation, calibration


def bce_for_k(k: float, scores: np.ndarray, outcomes: np.ndarray,
              weights: np.ndarray) -> float:
    x = np.clip(scores / k, -40.0, 40.0)
    p = 1.0 / (1.0 + np.exp(-x))
    eps = 1.0e-12
    losses = -(outcomes * np.log(p + eps) + (1.0 - outcomes) * np.log(1.0 - p + eps))
    return float(np.sum(weights * losses) / np.sum(weights))


def fit_k(scores: np.ndarray, outcomes: np.ndarray,
          game_ids: np.ndarray) -> tuple[float, float]:
    known = np.isfinite(outcomes)
    scores = scores[known].astype(np.float64)
    outcomes = outcomes[known].astype(np.float64)
    game_ids = game_ids[known]
    if len(scores) < 50:
        raise ValueError(f"need at least 50 calibration positions with outcomes, got {len(scores)}")

    _, inverse, counts = np.unique(game_ids, return_inverse=True, return_counts=True)
    weights = 1.0 / counts[inverse].astype(np.float64)

    # Golden-section search is a deterministic one-dimensional statistic.  No
    # network weight or optimizer participates in this fit.
    lo, hi = 20.0, 2000.0
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - ratio * (hi - lo)
    d = lo + ratio * (hi - lo)
    fc, fd = bce_for_k(c, scores, outcomes, weights), bce_for_k(d, scores, outcomes, weights)
    for _ in range(80):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - ratio * (hi - lo)
            fc = bce_for_k(c, scores, outcomes, weights)
        else:
            lo, c, fc = c, d, fd
            d = lo + ratio * (hi - lo)
            fd = bce_for_k(d, scores, outcomes, weights)
    k = (lo + hi) * 0.5
    return k, bce_for_k(k, scores, outcomes, weights)


class HalfKANet(nn.Module):
    def __init__(self, width: int, hidden: int, activation: str = "crelu",
                 phase_heads: bool = False):
        super().__init__()
        self.width = width
        self.hidden = hidden
        self.activation = activation
        self.phase_heads = phase_heads
        self.embedding = nn.Embedding(NUM_FEATURES + 1, width, padding_idx=PADDING_IDX)
        self.feature_bias = nn.Parameter(torch.zeros(width))
        if hidden > 0:
            self.fc1 = nn.Linear(width * 2, hidden)
            self.fc2 = nn.Linear(hidden, hidden)
            self.output = nn.Linear(hidden, 2 if phase_heads else 1)
        else:
            self.output = nn.Linear(width * 2, 2 if phase_heads else 1)
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.01)
        with torch.no_grad():
            self.embedding.weight[PADDING_IDX].zero_()

    def activate(self, x: torch.Tensor) -> torch.Tensor:
        clipped = torch.clamp(x, 0.0, 1.0)
        return clipped * clipped if self.activation == "screlu" else clipped

    def forward(self, red: torch.Tensor, black: torch.Tensor, stm: torch.Tensor) -> torch.Tensor:
        ar = self.embedding(red).sum(dim=1) + self.feature_bias
        ab = self.embedding(black).sum(dim=1) + self.feature_bias
        first = torch.where(stm[:, None] == 0, ar, ab)
        second = torch.where(stm[:, None] == 0, ab, ar)
        x = self.activate(torch.cat((first, second), dim=1))
        if self.hidden > 0:
            x = self.activate(self.fc1(x))
            x = self.activate(self.fc2(x))
        values = self.output(x)
        if self.phase_heads:
            phase = ((red != PADDING_IDX).sum(dim=1) <= 20).to(torch.int64)
            return values.gather(1, phase[:, None]).squeeze(1)
        return values.squeeze(1)


def evaluate_loss(model: HalfKANet, arrays: DatasetArrays, mask: np.ndarray,
                  k: float, lambda_: float, batch_size: int, residual: bool,
                  delta_weight: float, delta_clip: float,
                  delta_beta: float) -> float:
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return float("nan")
    total = 0.0
    count = 0
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        for start in range(0, len(idx), batch_size):
            j = idx[start:start + batch_size]
            red = torch.from_numpy(arrays.red[j]).to(device)
            black = torch.from_numpy(arrays.black[j]).to(device)
            stm = torch.from_numpy(arrays.stm[j]).to(device)
            score = torch.from_numpy(arrays.score_stm[j]).to(device)
            pst = torch.from_numpy(arrays.pst_stm[j]).to(device)
            outcome = torch.from_numpy(arrays.outcome_stm[j]).to(device)
            # The network emits a dimensionless logit.  K is applied only
            # when converting that logit back to engine score units during
            # export/inference, so it remains an independently fitted scalar.
            logit = model(red, black, stm)
            pred = torch.sigmoid(logit + (pst / k if residual else 0.0))
            teacher = torch.sigmoid(torch.clamp(score, -2000.0, 2000.0) / k)
            known = torch.isfinite(outcome)
            target = teacher.clone()
            target[known] = lambda_ * teacher[known] + (1.0 - lambda_) * outcome[known]
            losses = (pred - target) ** 2
            if residual and delta_weight > 0.0:
                delta_target = torch.clamp(score - pst, -delta_clip, delta_clip) / k
                losses = losses + delta_weight * torch.nn.functional.smooth_l1_loss(
                    logit, delta_target, beta=delta_beta / k, reduction="none"
                )
            total += torch.sum(losses).item()
            count += len(j)
    return total / count


def train_epoch(model: HalfKANet, optimizer: torch.optim.Optimizer,
                arrays: DatasetArrays, indices: np.ndarray, k: float,
                lambda_: float, batch_size: int, residual: bool,
                delta_weight: float, delta_clip: float,
                delta_beta: float) -> float:
    model.train()
    np.random.shuffle(indices)
    running = 0.0
    seen = 0
    device = next(model.parameters()).device
    for start in range(0, len(indices), batch_size):
        j = indices[start:start + batch_size]
        use_mirror = np.random.random(len(j)) < 0.5
        red_np = arrays.red[j].copy()
        black_np = arrays.black[j].copy()
        red_np[use_mirror] = arrays.red_mirror[j[use_mirror]]
        black_np[use_mirror] = arrays.black_mirror[j[use_mirror]]
        red = torch.from_numpy(red_np).to(device)
        black = torch.from_numpy(black_np).to(device)
        stm = torch.from_numpy(arrays.stm[j]).to(device)
        score = torch.from_numpy(arrays.score_stm[j]).to(device)
        pst = torch.from_numpy(arrays.pst_stm[j]).to(device)
        outcome = torch.from_numpy(arrays.outcome_stm[j]).to(device)

        teacher = torch.sigmoid(torch.clamp(score, -2000.0, 2000.0) / k)
        known = torch.isfinite(outcome)
        target = teacher.clone()
        target[known] = lambda_ * teacher[known] + (1.0 - lambda_) * outcome[known]
        logit = model(red, black, stm)
        prediction = torch.sigmoid(logit + (pst / k if residual else 0.0))
        losses = (prediction - target) ** 2
        if residual and delta_weight > 0.0:
            delta_target = torch.clamp(score - pst, -delta_clip, delta_clip) / k
            losses = losses + delta_weight * torch.nn.functional.smooth_l1_loss(
                logit, delta_target, beta=delta_beta / k, reduction="none"
            )
        loss = torch.mean(losses)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        with torch.no_grad():
            model.embedding.weight[PADDING_IDX].zero_()
        running += loss.item() * len(j)
        seen += len(j)
    return running / max(1, seen)


def residual_metrics(model: HalfKANet, arrays: DatasetArrays, mask: np.ndarray,
                     k: float, lambda_: float, batch_size: int) -> dict:
    idx = np.flatnonzero(mask)
    predicted_parts = []
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        for start in range(0, len(idx), batch_size):
            j = idx[start:start + batch_size]
            predicted_parts.append((model(
                torch.from_numpy(arrays.red[j]).to(device),
                torch.from_numpy(arrays.black[j]).to(device),
                torch.from_numpy(arrays.stm[j]).to(device),
            ) * k).cpu().numpy())
    predicted = np.concatenate(predicted_parts).astype(np.float64)
    target = (arrays.score_stm[idx] - arrays.pst_stm[idx]).astype(np.float64)
    clipped = np.clip(target, -2000.0, 2000.0)
    teacher_prob = 1.0 / (1.0 + np.exp(-np.clip(arrays.score_stm[idx] / k, -40, 40)))
    outcomes = arrays.outcome_stm[idx].astype(np.float64)
    known = np.isfinite(outcomes)
    targets = teacher_prob.copy()
    targets[known] = lambda_ * teacher_prob[known] + (1.0 - lambda_) * outcomes[known]
    pst_prob = 1.0 / (1.0 + np.exp(-np.clip(arrays.pst_stm[idx] / k, -40, 40)))
    model_prob = 1.0 / (1.0 + np.exp(-np.clip(
        (arrays.pst_stm[idx] + predicted) / k, -40, 40
    )))
    denominator = float(np.dot(predicted, predicted))
    slope = float(np.dot(predicted, target) / denominator) if denominator > 0 else 1.0
    correlation = float(np.corrcoef(predicted, target)[0, 1]) \
        if np.std(predicted) > 0 and np.std(target) > 0 else 0.0
    decisive = np.abs(target) >= 20.0
    sign_accuracy = float(np.mean(np.sign(predicted[decisive]) == np.sign(target[decisive]))) \
        if np.any(decisive) else 0.0
    return {
        "validation_positions": int(len(idx)),
        "pst_only_probability_mse": float(np.mean((pst_prob - targets) ** 2)),
        "model_probability_mse": float(np.mean((model_prob - targets) ** 2)),
        "pst_teacher_mae_cp": float(np.mean(np.abs(target))),
        "model_teacher_mae_cp": float(np.mean(np.abs(predicted - target))),
        "model_teacher_rmse_cp": float(np.sqrt(np.mean((predicted - target) ** 2))),
        "residual_correlation": correlation,
        "residual_sign_accuracy_abs20": sign_accuracy,
        "residual_pred_abs_p99_cp": float(np.quantile(np.abs(predicted), 0.99)),
        "residual_pred_abs_max_cp": float(np.max(np.abs(predicted))),
        "validation_zero_intercept_slope": slope,
    }


def quantize_symmetric(array: np.ndarray, limit: int = 32767) -> tuple[np.ndarray, float]:
    maximum = float(np.max(np.abs(array)))
    scale = limit / maximum if maximum > 0 else 1.0
    quantized = np.clip(np.rint(array * scale), -limit, limit).astype(np.int16)
    return quantized, scale


def quantize_fixed(array: np.ndarray, scale: float, dtype, name: str) -> np.ndarray:
    rounded = np.rint(array * scale)
    limits = np.iinfo(dtype)
    if np.any(rounded < limits.min) or np.any(rounded > limits.max):
        raise OverflowError(
            f"{name} exceeds {np.dtype(dtype).name} at fixed scale {scale}: "
            f"range=({rounded.min()}, {rounded.max()})"
        )
    return rounded.astype(dtype)


def load_v3_initialization(model: HalfKANet, path: Path, target_k: float) -> float:
    """Load a quantized no-hidden v3 NNUE and preserve its cp-scale output."""
    data = path.read_bytes()
    header_format = "<8sIIIIIfffff"
    header_size = struct.calcsize(header_format)
    if len(data) < header_size:
        raise ValueError(f"short NNUE model: {path}")
    (magic, version, width, hidden, num_features, flags, source_k,
     embedding_scale, fc1_scale, fc2_scale, output_scale) = struct.unpack_from(
        header_format, data, 0
    )
    expected_flags = 1 | (2 if model.activation == "screlu" else 0) \
        | (4 if model.phase_heads else 0)
    if magic != b"XQNNUE1\0" or version != 3:
        raise ValueError(f"--init-nnue requires a v3 model, got magic={magic!r} version={version}")
    if (width != model.width or hidden != 0 or model.hidden != 0
            or num_features != NUM_FEATURES or flags != expected_flags):
        raise ValueError(
            "initial model architecture mismatch: "
            f"file=(width={width}, hidden={hidden}, features={num_features}, flags={flags}) "
            f"requested=(width={model.width}, hidden={model.hidden}, "
            f"features={NUM_FEATURES}, flags={expected_flags})"
        )
    if embedding_scale <= 0 or output_scale <= 0 or source_k <= 0 or target_k <= 0:
        raise ValueError("invalid scale in initial NNUE model")

    outputs = 2 if model.phase_heads else 1
    offset = header_size
    def take(dtype, count: int) -> np.ndarray:
        nonlocal offset
        itemsize = np.dtype(dtype).itemsize
        end = offset + count * itemsize
        if end > len(data):
            raise ValueError(f"truncated NNUE payload in {path}")
        result = np.frombuffer(data, dtype=dtype, count=count, offset=offset).copy()
        offset = end
        return result

    feature_bias_q = take("<i4", width)
    embedding_q = take("<i2", NUM_FEATURES * width).reshape(NUM_FEATURES, width)
    output_bias_q = take("<i4", outputs)
    output_q = take("<i2", outputs * width * 2).reshape(outputs, width * 2)
    if offset != len(data):
        raise ValueError(f"unexpected trailing bytes in {path}: {len(data) - offset}")

    cp_preserving_scale = source_k / target_k
    with torch.no_grad():
        model.embedding.weight.zero_()
        model.embedding.weight[:NUM_FEATURES].copy_(torch.from_numpy(
            embedding_q.astype(np.float32) / embedding_scale
        ))
        model.feature_bias.copy_(torch.from_numpy(
            feature_bias_q.astype(np.float32) / embedding_scale
        ))
        model.output.weight.copy_(torch.from_numpy(
            output_q.astype(np.float32) / (source_k * output_scale)
            * cp_preserving_scale
        ))
        model.output.bias.copy_(torch.from_numpy(
            output_bias_q.astype(np.float32)
            / (source_k * embedding_scale * output_scale)
            * cp_preserving_scale
        ))
    return float(source_k)


def export_model(model: HalfKANet, output: Path, k: float, metadata: dict,
                 residual: bool) -> None:
    state = {name: value.detach().cpu().numpy() for name, value in model.state_dict().items()}
    fixed_point = model.hidden == 0
    if fixed_point:
        # Version 3 has a pure-integer hot path. Activations remain in Q12;
        # output weights already include the independently fitted K and Q8.
        embedding_scale = 4096.0
        output_scale = 256.0
        embedding_q = quantize_fixed(
            state["embedding.weight"][:NUM_FEATURES], embedding_scale,
            np.int16, "embedding"
        )
        feature_bias_q = quantize_fixed(
            state["feature_bias"], embedding_scale, np.int32, "feature_bias"
        )
    else:
        embedding_q, embedding_scale = quantize_symmetric(
            state["embedding.weight"][:NUM_FEATURES]
        )
        feature_bias_q = np.rint(
            state["feature_bias"] * embedding_scale
        ).astype(np.int32)

    if model.hidden > 0:
        fc1_q, fc1_scale = quantize_symmetric(state["fc1.weight"])
        fc1_bias_q = np.rint(state["fc1.bias"] * (127.0 * fc1_scale)).astype(np.int32)
        fc2_q, fc2_scale = quantize_symmetric(state["fc2.weight"])
        fc2_bias_q = np.rint(state["fc2.bias"] * (127.0 * fc2_scale)).astype(np.int32)
    else:
        fc1_q = np.empty((0,), dtype=np.int16)
        fc1_bias_q = np.empty((0,), dtype=np.int32)
        fc2_q = np.empty((0,), dtype=np.int16)
        fc2_bias_q = np.empty((0,), dtype=np.int32)
        fc1_scale = fc2_scale = 1.0
    if fixed_point:
        # Keep the v3 hot path purely integral without silently saturating a
        # learned model.  Q8 is preferred, but deeper/noisier teachers can
        # produce an occasional output coefficient that needs Q7 (or lower).
        # A power-of-two scale retains cheap exact division opportunities in
        # C++ while the scale stored in the file keeps the format general.
        preferred_output_scale = 256.0
        max_weight_cp = float(np.max(np.abs(state["output.weight"]))) * k
        max_bias_units = (float(np.max(np.abs(state["output.bias"]))) * k
                          * embedding_scale)
        safe_scale = preferred_output_scale
        if max_weight_cp > 0:
            safe_scale = min(safe_scale, np.iinfo(np.int16).max / max_weight_cp)
        if max_bias_units > 0:
            safe_scale = min(safe_scale, np.iinfo(np.int32).max / max_bias_units)
        if safe_scale < 1.0:
            raise OverflowError(
                f"output layer cannot fit fixed-point payload even at Q0: "
                f"safe_scale={safe_scale}"
            )
        output_scale = float(2 ** math.floor(math.log2(safe_scale)))
        output_q = quantize_fixed(
            state["output.weight"], k * output_scale,
            np.int16, "output_weight"
        )
        output_bias_q = quantize_fixed(
            state["output.bias"], k * embedding_scale * output_scale,
            np.int32, "output_bias"
        )
        version = 3
    else:
        output_q, output_scale = quantize_symmetric(state["output.weight"])
        output_bias_q = np.rint(
            state["output.bias"] * (127.0 * output_scale)
        ).astype(np.int32)
        version = 2

    with output.open("wb") as f:
        f.write(struct.pack(
            "<8sIIIIIffff",
            b"XQNNUE1\0", version, model.width, model.hidden, NUM_FEATURES,
            (1 if residual else 0)
            | (2 if model.activation == "screlu" else 0)
            | (4 if model.phase_heads else 0),
            float(k), float(embedding_scale), float(fc1_scale), float(fc2_scale),
        ))
        f.write(struct.pack("<f", float(output_scale)))
        for array in (
            feature_bias_q, embedding_q, fc1_bias_q, fc1_q,
            fc2_bias_q, fc2_q, output_bias_q, output_q,
        ):
            f.write(np.ascontiguousarray(array).tobytes())

    metadata = dict(metadata)
    metadata.update(
        {
            "model_file": str(output),
            "k": k,
            "embedding_scale": embedding_scale,
            "fc1_scale": fc1_scale,
            "fc2_scale": fc2_scale,
            "output_scale": output_scale,
            "residual": residual,
            "model_format_version": version,
            "integer_hot_path": fixed_point,
            "activation": model.activation,
            "phase_heads": model.phase_heads,
            "phase_cutoff_pieces": 20 if model.phase_heads else None,
        }
    )
    output.with_suffix(output.suffix + ".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, choices=(4, 8, 16, 32, 64, 96, 128), default=32)
    parser.add_argument("--hidden", type=int, choices=(0, 8, 16, 32), default=0)
    parser.add_argument("--activation", choices=("crelu", "screlu"), default="crelu")
    parser.add_argument("--phase-heads", action="store_true")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--lambda", dest="lambda_", type=float, default=0.85)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--quiet-only", action="store_true")
    parser.add_argument("--residual", action="store_true")
    parser.add_argument("--pretrain-data", type=Path)
    parser.add_argument("--pretrain-epochs", type=int, default=0)
    parser.add_argument("--pretrain-learning-rate", type=float, default=3.0e-3)
    parser.add_argument("--delta-weight", type=float, default=0.0)
    parser.add_argument("--delta-clip", type=float, default=250.0)
    parser.add_argument("--delta-beta", type=float, default=25.0)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--init-nnue", type=Path)
    parser.add_argument("--early-stop-patience", type=int, default=0)
    parser.add_argument("--early-stop-min-delta", type=float, default=0.0)
    parser.add_argument("--min-epochs", type=int, default=1)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    started = time.monotonic()
    records = load_records(args.data)
    arrays = make_arrays(records, args.quiet_only)
    training, validation, calibration = split_masks(arrays.game_id)
    known_calibration = calibration & np.isfinite(arrays.outcome_stm)
    k, calibration_bce = fit_k(
        arrays.score_stm[known_calibration], arrays.outcome_stm[known_calibration],
        arrays.game_id[known_calibration]
    )
    print(json.dumps({
        "records_raw": len(records), "records_filtered": len(arrays.stm),
        "train": int(training.sum()), "validation": int(validation.sum()),
        "calibration": int(calibration.sum()), "calibration_known": int(known_calibration.sum()),
        "teacher_depth": arrays.depth, "k": k, "calibration_bce": calibration_bce,
    }))

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but CUDA is unavailable")
    selected_device = ("cuda" if torch.cuda.is_available() else "cpu") \
        if args.device == "auto" else args.device
    device = torch.device(selected_device)
    model = HalfKANet(args.width, args.hidden, args.activation, args.phase_heads).to(device)
    if args.residual:
        # A fresh residual model is exactly the PST evaluator.  This avoids a
        # random score perturbation before the first useful gradient step.
        nn.init.zeros_(model.output.weight)
        nn.init.zeros_(model.output.bias)
    init_source_k = None
    if args.init_nnue is not None:
        if not args.residual:
            raise ValueError("--init-nnue currently requires --residual")
        init_source_k = load_v3_initialization(model, args.init_nnue, k)
        model.to(device)
        print(json.dumps({
            "init_nnue": str(args.init_nnue), "init_source_k": init_source_k,
            "init_target_k": k, "output_rescale": init_source_k / k,
        }))
    train_idx = np.flatnonzero(training)
    best_loss = float("inf")
    best_state = None
    pretrain_k = None

    if args.pretrain_data is not None and args.pretrain_epochs > 0:
        pre_records = load_records(args.pretrain_data)
        pre_arrays = make_arrays(pre_records, args.quiet_only)
        pre_training, _, pre_calibration = split_masks(pre_arrays.game_id)
        pre_known = pre_calibration & np.isfinite(pre_arrays.outcome_stm)
        pretrain_k, pretrain_bce = fit_k(
            pre_arrays.score_stm[pre_known], pre_arrays.outcome_stm[pre_known],
            pre_arrays.game_id[pre_known]
        )
        pre_idx = np.flatnonzero(pre_training)
        pre_optimizer = torch.optim.AdamW(
            model.parameters(), lr=args.pretrain_learning_rate, weight_decay=1.0e-6
        )
        pre_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            pre_optimizer, T_max=max(1, args.pretrain_epochs),
            eta_min=args.pretrain_learning_rate * 0.1
        )
        print(json.dumps({
            "pretrain_data": str(args.pretrain_data),
            "pretrain_depth": pre_arrays.depth,
            "pretrain_k": pretrain_k,
            "pretrain_calibration_bce": pretrain_bce,
            "pretrain_records": len(pre_arrays.stm),
        }))
        for epoch in range(args.pretrain_epochs):
            train_loss = train_epoch(
                model, pre_optimizer, pre_arrays, pre_idx, pretrain_k, args.lambda_,
                args.batch_size, args.residual, args.delta_weight,
                args.delta_clip, args.delta_beta
            )
            pre_scheduler.step()
            print(f"pretrain_epoch={epoch + 1} train_mse={train_loss:.8f} "
                  f"lr={pre_scheduler.get_last_lr()[0]:.3g}")

    # Reset optimizer state at the teacher-depth boundary.  The target K and
    # learning-rate schedule also switch here and remain frozen for fine-tune.
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-6)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, args.epochs), eta_min=args.learning_rate * 0.03
    )

    epochs_without_improvement = 0
    epochs_completed = 0
    history = []
    for epoch in range(args.epochs):
        train_loss = train_epoch(
            model, optimizer, arrays, train_idx, k, args.lambda_,
            args.batch_size, args.residual, args.delta_weight,
            args.delta_clip, args.delta_beta
        )
        scheduler.step()
        val_loss = evaluate_loss(
            model, arrays, validation, k, args.lambda_, args.batch_size,
            args.residual, args.delta_weight, args.delta_clip, args.delta_beta
        )
        print(f"epoch={epoch + 1} train_mse={train_loss:.8f} "
              f"val_mse={val_loss:.8f} lr={scheduler.get_last_lr()[0]:.3g}")
        history.append({
            "epoch": epoch + 1,
            "train_objective": train_loss,
            "validation_objective": val_loss,
            "learning_rate": scheduler.get_last_lr()[0],
        })
        epochs_completed = epoch + 1
        if val_loss < best_loss - args.early_stop_min_delta:
            best_loss = val_loss
            best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if (args.early_stop_patience > 0 and epoch + 1 >= args.min_epochs
                and epochs_without_improvement >= args.early_stop_patience):
            print(f"early_stop_epoch={epoch + 1} best_val_mse={best_loss:.8f}")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    diagnostics = residual_metrics(
        model, arrays, validation, k, args.lambda_, args.batch_size
    ) if args.residual else {}
    training_diagnostics = residual_metrics(
        model, arrays, training, k, args.lambda_, args.batch_size
    ) if args.residual else {}
    metadata = {
        "data": str(args.data), "teacher_depth": arrays.depth,
        "width": args.width, "hidden": args.hidden, "epochs": args.epochs,
        "activation": args.activation,
        "phase_heads": args.phase_heads,
        "batch_size": args.batch_size, "learning_rate": args.learning_rate,
        "lambda": args.lambda_, "seed": args.seed, "quiet_only": args.quiet_only,
        "validation_mse": best_loss, "calibration_bce": calibration_bce,
        "elapsed_seconds": time.monotonic() - started,
        "cpu_threads": torch.get_num_threads(),
        "device": str(device),
        "init_nnue": str(args.init_nnue) if args.init_nnue is not None else None,
        "init_source_k": init_source_k,
        "epochs_completed": epochs_completed,
        "history": history,
        "training_diagnostics": training_diagnostics,
        "residual": args.residual,
        "pretrain_data": str(args.pretrain_data) if args.pretrain_data else None,
        "pretrain_epochs": args.pretrain_epochs,
        "pretrain_learning_rate": args.pretrain_learning_rate,
        "pretrain_k": pretrain_k,
        "delta_weight": args.delta_weight,
        "delta_clip": args.delta_clip,
        "delta_beta": args.delta_beta,
        **diagnostics,
    }
    export_model(model, args.output, k, metadata, args.residual)
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
