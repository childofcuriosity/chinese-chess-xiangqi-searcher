# g006 NNUE training and evaluation

[简体中文](REPORT_zh.md) · [Frozen recipe](recipe.json) · [Compact opening-pair evidence](matches.compact.json)

Both new generation-six public-engine matches are complete. This report covers the training chain, matches and historical reference ratings.

The deployed model is **g006, an H128 NNUE with int8 feature weights, int16 accumulators and fixed-E20 QAT**, from a self-training chain restarted from pure PST. It passed all six scheduled historical-opponent matches and was then explicitly approved for deployment. Generation g007 scored 48.6979% against g005 and 47.6562% against g006; after completing all seven scheduled comparisons, the chain stopped and retained g006.

All training data comes from this project's PST and historical NNUE models. At each move, exploration selects the first, second or third same-depth root move with probabilities 50%, 30% and 20%; the label always retains the teacher's single-PV best score. PST plays and labels at D4 in the first generation. Later generations use the parent NNUE at D3 to label two million newly generated valid positions against each historical source, including PST and every promoted NNUE. The seven datasets contain 2M, 4M, 6M, 8M, 10M, 12M and 14M positions. Each dataset is split by complete game into 98% training, 1% validation and 1% calibration, with source and side-to-move quotas retained.

Each H128 starts from random parameters. Features index the friendly king square, piece type, relative side and piece square. Three mirrored pairs of king buckets share weights with the piece square mirrored at the same time; the three central king buckets remain independent. This gives 7,560 independent 128-dimensional vectors. Export expands them to the existing 11,340-row representation, adding no inference-time mirror lookup. CReLU and phase-specific output heads combine the two perspective accumulators into a PST residual.

Training minimizes the squared normalized residual error, with target `clip(S_i−PST(B_i), −250, 250)` and fixed scale `K=65.38910923790853`. Outcome labels and a probability loss are absent. Floating training is followed by selection of the largest safe integer feature scale E and fixed-E QAT fine-tuning. The forward pass simulates actual integer rounding, activation and residual clipping; exported scores are checked exactly against native C++ inference. Accumulator safety includes weights, bias and intermediate cache updates.

Playing strength determines promotion. Each opponent receives 96 color-swapped opening pairs, or 192 games, after independent actual-time calibration and budget freezing. Formal matches require each side’s actual mean within 150 ms ±5%, and the deviation of their actual-time ratio from 1 at most 5%. Every historical matchup must score strictly above 50%; after a failure, the remaining scheduled matchups still finish before the next generation is stopped. Score is `(wins + 0.5*draws)/games`; pure win rate is `wins/games`, with opening-pair bootstrap 95% intervals. The chain completed 28 mainline comparisons and 5,376 games; the additional 192-game H1024 test and 1,536 external observation games are reported separately. External engines supply evaluation results, not training data, labels or promotion decisions.

The complete experiment record retains a known representation mismatch: teacher labels can depend on pre-root game history, whereas NNUE features and the deduplication key omit it. All 17 g005 conflict groups were reproduced. An isolated canonical-label fix was tested separately and was not used to generate this chain's data or results.

```text
L = mean_i[((r_theta(B_i) - clip(S_i-PST(B_i), -250, 250)) / K)^2]
```

Here `B_i` is the sample’s board and side to move; `S_i` is its saved teacher single-PV best search score, including the actual pre-root history used for that sample. `K=65.38910923790853` is fixed.


Here E is the integer scale per real-valued unit: a feature weight is quantized as `q = round(E*w)`, and integer CReLU clips to `[0,E]`. g006 uses E=20. Inference uses int8 feature weights and int16 accumulators; the compatible v3 model file retains int16 slots for those feature values. The model file is 2,904,632 bytes. This separates runtime arithmetic precision from file storage.

### Generation-six training settings

Training used a local NVIDIA GeForce GTX 1650 Ti with AdamW and weight decay `1e-6`. An effective batch of 8192 accumulates gradients from 2048-position microbatches. All training indices are reshuffled every epoch; samples receive horizontal mirror augmentation with probability 50%, and the gradient norm is clipped to 1. The cosine learning-rate schedule uses the stage's maximum epoch count as `T_max` and 3% of its initial learning rate as `eta_min`.

| Stage | Initial learning rate | Maximum / minimum epochs | Early-stop patience | Minimum validation improvement |
|---|---:|---:|---:|---:|
| Randomly initialized floating training | 0.003 | 150 / 25 | 15 | 1e-5 |
| Fixed-E QAT fine-tuning | 0.0003 | 30 / 5 | 8 | 1e-7 |

Checkpoint selection uses validation residual MSE, including epoch 0. g006 ran 37 floating epochs and selected epoch 22, then ran 9 QAT epochs and selected epoch 1. The stage seeds were 20261032 and 2026110191. The recipe JSON retains full parameters and source hashes.

## Training by generation

Validation sets follow each generation’s teacher distribution; losses do not directly rank playing strength across generations. Epoch indices follow the saved training records.

|Generation|Valid positions|Float best epoch / validation loss|QAT best epoch / validation loss|E|Promoted|
|---|---:|---:|---:|---:|---|
|g001|2,000,000|5 / 0.502582|2 / 0.500343|103|True|
|g002|4,000,000|6 / 0.421933|2 / 0.415408|72|True|
|g003|6,000,000|6 / 0.438848|2 / 0.429674|60|True|
|g004|8,000,000|13 / 0.454822|1 / 0.446560|35|True|
|g005|10,000,000|14 / 0.474702|2 / 0.466302|33|True|
|g006|12,000,000|22 / 0.491871|1 / 0.488677|20|True|
|g007|14,000,000|26 / 0.510102|1 / 0.511295|13|False|

## All 28 formal historical comparisons

W/D/L are from the candidate’s perspective. Each comparison has 192 games; intervals use an opening-pair bootstrap.

|Candidate / opponent|W / D / L|Pure wins|Score [95% CI]|Actual ms (candidate / opponent)|
|---|---:|---:|---:|---:|
|g001 / pst|110 / 54 / 28|57.29%|71.35% [66.41%, 76.30%]|148.969 / 150.296|
|g002 / pst|138 / 31 / 23|71.88%|79.95% [75.52%, 84.38%]|154.206 / 153.087|
|g002 / g001|99 / 52 / 41|51.56%|65.10% [60.42%, 69.53%]|148.241 / 155.344|
|g003 / pst|145 / 37 / 10|75.52%|85.16% [81.51%, 88.54%]|150.617 / 151.035|
|g003 / g001|118 / 54 / 20|61.46%|75.52% [71.09%, 79.69%]|150.556 / 153.549|
|g003 / g002|70 / 80 / 42|36.46%|57.29% [52.34%, 61.98%]|153.992 / 153.884|
|g004 / pst|156 / 25 / 11|81.25%|87.76% [84.11%, 91.15%]|154.114 / 151.752|
|g004 / g001|117 / 57 / 18|60.94%|75.78% [71.88%, 79.69%]|146.279 / 146.892|
|g004 / g002|90 / 64 / 38|46.88%|63.54% [58.85%, 67.97%]|155.818 / 155.993|
|g004 / g003|71 / 66 / 55|36.98%|54.17% [50.00%, 58.33%]|149.688 / 149.740|
|g005 / pst|162 / 26 / 4|84.38%|91.15% [88.28%, 94.01%]|147.127 / 146.625|
|g005 / g001|131 / 47 / 14|68.23%|80.47% [76.82%, 84.11%]|152.531 / 152.156|
|g005 / g002|91 / 68 / 33|47.40%|65.10% [61.20%, 69.01%]|151.475 / 150.568|
|g005 / g003|76 / 79 / 37|39.58%|60.16% [55.99%, 64.32%]|151.600 / 150.946|
|g005 / g004|65 / 83 / 44|33.85%|55.47% [51.82%, 59.38%]|150.830 / 149.241|
|g006 / pst|163 / 22 / 7|84.90%|90.62% [87.50%, 93.49%]|149.359 / 150.835|
|g006 / g001|139 / 34 / 19|72.40%|81.25% [76.82%, 85.42%]|150.624 / 150.577|
|g006 / g002|96 / 66 / 30|50.00%|67.19% [62.76%, 71.61%]|152.535 / 154.232|
|g006 / g003|77 / 71 / 44|40.10%|58.59% [54.43%, 62.76%]|155.837 / 156.090|
|g006 / g004|63 / 81 / 48|32.81%|53.91% [49.48%, 58.33%]|147.955 / 151.038|
|g006 / g005|56 / 92 / 44|29.17%|53.12% [48.96%, 57.29%]|149.524 / 149.305|
|g007 / pst|161 / 25 / 6|83.85%|90.36% [87.24%, 93.23%]|149.122 / 147.254|
|g007 / g001|135 / 45 / 12|70.31%|82.03% [78.12%, 85.94%]|148.809 / 151.311|
|g007 / g002|100 / 65 / 27|52.08%|69.01% [64.32%, 73.70%]|156.347 / 152.711|
|g007 / g003|85 / 60 / 47|44.27%|59.90% [55.21%, 64.58%]|149.587 / 150.691|
|g007 / g004|60 / 86 / 46|31.25%|53.65% [49.48%, 58.07%]|150.646 / 152.089|
|g007 / g005|49 / 89 / 54|25.52%|48.70% [45.05%, 52.60%]|149.298 / 148.476|
|g007 / g006|47 / 89 / 56|24.48%|47.66% [43.75%, 51.56%]|148.515 / 146.976|

## External reference and conclusion

| Opponent | W / D / L | Score (95% CI) | Actual ms (ours / opponent) | Reference Elo (95% CI) |
|---|---:|---:|---:|---:|
| ElephantEye 3.1 (new) | 142 / 35 / 15 | 83.07% (78.91%–87.24%) | 149.089 / 148.672 | 2407 (2359–2464) |
| Tianqi V1.1.8 (new) | 126 / 42 / 24 | 76.56% (71.61%–81.51%) | 150.358 / 152.969 | 2636 (2591–2688) |
| Cyclone 2007C (reused observation) | 78 / 63 / 51 | 57.03% (52.08%–61.98%) | 144.366 / 142.902 | 2649 (2614–2685) |

The fixed three-anchor fit is **2601 reference Elo** (opening-pair bootstrap 95% CI 2574–2629). The point estimate is just above 2600, with its interval spanning 2600. The opponent-specific ratings range from about 2407 to 2649, so this is an approximately 2600 coordinate on the cited historical engine scale. The Cyclone 2600 anchor refers to top professional and grandmaster play in 2006–2007.

Reference anchors are ElephantEye 2130.2, Tianqi 2430 and Cyclone 2600, from the [rating-list author's 2026-10-09 table](https://bbs.pikafish.org/forum.php?mod=viewthread&tid=179&extra=page%3D1). The author relates Cyclone 2600 to top professional and grandmaster human–engine matches in 2006–2007. That is a historical reference, rather than an official human rating. The source list uses four cores and 60s+0.6s, with different openings and rules; these tests use one logical CPU and approximately 150ms actual search time.

Score is `(W+D/2)/N`; pure win rate is `W/N`. Per-opponent `ΔElo=400*log10(S/(1-S))`, and reference Elo adds its fixed anchor. The common fit solves `sum_i N_i*(S_i-1/(1+10^((r_i-R)/400)))=0`, rather than averaging transformed ratings. 10,000 bootstrap draws retain both colors of each opening; the two new matches share openings and are resampled together, while Cyclone is resampled independently. Intervals measure opening-pair sampling uncertainty, with anchors held fixed; they omit anchor, hardware, time-control, rule and engine-artifact uncertainty. The large differences between opponent-specific ratings limit the common rating's interpretation.

Both new matches passed independent 48-pair timing confirmation before 96 formal opening pairs. Each side's actual mean must be within 150ms ±5%, with time-ratio deviation at most 5%. Nominal budgets were frozen before formal play and were selected using timing only. Cyclone reuses the existing g006 observation, accepted under its original relative-only timing gate. The new matches use production engine `ad9a1567…99d5db`; Cyclone used experimental engine `e6f367…`. The model is identical, but this is not one newly run three-opponent production-engine tournament. Full identities and pure-win intervals are in the compact JSON and recipe.

| Match | Accepted formal search seconds (ours / opponent) | Formal-stage elapsed seconds |
|---|---:|---:|
| ElephantEye 3.1 (new) | 1355.368 / 1341.619 | 2925.407 |
| Tianqi V1.1.8 (new) | 1473.960 / 1491.294 | 3285.499 |
| Cyclone 2007C (reused observation) | 1660.640 / 1642.235 | Not recorded |

Search wall time and phase elapsed are separate measurements. Calibration, startup and resource waits remain in local receipts and are excluded from accepted formal results. These are neither CPU time nor total experiment cost.

The first-generation width selection used identical data: H128 scored 110/54/28 (71.35%) against PST; H1024 scored 93/60/39 (64.06%). Each had 192 games at approximately 150 ms actual time. H128 therefore continued the chain. The mainline comprises 28 comparisons / 5,376 games; H1024 adds 192 games. Eight Cyclone observations add 1,536 games. Observation budgets differ across generations, so their scores do not form a direct cross-generation strength ranking.

**The final selection is g006; the chain stops at g007 with no g008.** Deployment of g006 was explicitly approved; g007 was not deployed. Confidence intervals describe sampling uncertainty. The per-opponent point-score gate does not establish statistically significant improvement on every opponent.

Recorded nonoverlapping g007 intervals total 21.222421 hours. This is partial project accounting; historical records contain 127 missing duration fields. It is not presented as the total project cost.

This documentation release provides methods, artifact identities and compact match evidence. Full datasets, move protocols, checkpoints and training implementation remain local; a complete retraining package is not included. Older `trainnnue/RESULTS.generated*` files and SVGs describe historical Iter2 experiments and belong to the old report generator.
