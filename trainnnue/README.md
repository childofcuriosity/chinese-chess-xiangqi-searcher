# Xiangqi NNUE: current training and historical experiments

[简体中文](README_zh.md) · [Current report](../docs/nnue_g006_20261106/REPORT.md) · [Frozen recipe](../docs/nnue_g006_20261106/recipe.json)

2026-11-06: external evaluation completed.

| Opponent | W / D / L | Score (95% CI) | Actual ms (ours / opponent) | Reference Elo (95% CI) |
|---|---:|---:|---:|---:|
| ElephantEye 3.1 (new) | 142 / 35 / 15 | 83.07% (78.91%–87.24%) | 149.089 / 148.672 | 2407 (2359–2464) |
| Tianqi V1.1.8 (new) | 126 / 42 / 24 | 76.56% (71.61%–81.51%) | 150.358 / 152.969 | 2636 (2591–2688) |
| Cyclone 2007C (reused observation) | 78 / 63 / 51 | 57.03% (52.08%–61.98%) | 144.366 / 142.902 | 2649 (2614–2685) |

The fixed three-anchor fit is **2601 reference Elo** (opening-pair bootstrap 95% CI 2574–2629). The point estimate is just above 2600, with its interval spanning 2600. The opponent-specific ratings range from about 2407 to 2649, so this is an approximately 2600 coordinate on the cited historical engine scale. The Cyclone 2600 anchor refers to top professional and grandmaster play in 2006–2007.

Both new matches passed independent 48-pair timing confirmation before 96 formal opening pairs. Each side's actual mean must be within 150ms ±5%, with time-ratio deviation at most 5%. Nominal budgets were frozen before formal play and were selected using timing only. Cyclone reuses the existing g006 observation, accepted under its original relative-only timing gate. The new matches use production engine `ad9a1567…99d5db`; Cyclone used experimental engine `e6f367…`. The model is identical, but this is not one newly run three-opponent production-engine tournament. Full identities and pure-win intervals are in the compact JSON and recipe.

## Current g006 method

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

## Historical experiments (published Iter2 route)

The following text preserves the previously published Iter2 experiments, architecture, loss, commands and figures. The current g006 route is described above.

[English](README.md) · [简体中文](README_zh.md)

This directory covers **NNUE evaluation** within the complete Xiangqi system. See the [root README](../README.md) for rules, search, clients, and the tutorial. `Iter2-NNUE-D3` scores **70.18%** against the PST baseline. Results against ElephantEye, Tianqi, and Cyclone place it around **2400 Elo on the cited reference scale**.

### 1. Results

#### External engines

Each match uses 180 color-swapped opening pairs (360 games), with both engines pinned to the same logical CPU per game. Implied ratings use `opponent reference Elo + 400 × log10(score / (1 − score))`, with anchors from a [public Xiangqi engine rating list](https://zhuanlan.zhihu.com/p/2072972857840350627).

| Opponent | Our W / D / L (score rate) | Implied Elo |
|---|---:|---:|
| [ElephantEye 3.1](iter2_vs_eleeye31_180pairs.json) | 290 / 31 / 39 (84.86%) | ≈2430 |
| [Tianqi V1.1.8](iter2_vs_tianqi118_180pairs.compact.json) | 109 / 79 / 172 (41.25%) | ≈2369 |
| [Cyclone 2007C](iter2_vs_cyclone2007c_180pairs.compact.json) | 60 / 95 / 205 (29.86%) | ≈2452 |
| [Pikafish 2026-01-31 · UCI_Elo=1900](iter2_vs_pikafish_elo1900_180pairs.json) | 169 / 68 / 123 (56.39%) | ≈1945 (limited-strength scale) |
| [Pikafish 2026-01-31 · full strength](iter2_vs_pikafish_official_180pairs.json) | 6 / 44 / 310 (7.78%) | ≈3573 (cross-generation comparison) |

![Official Pikafish reference](external_benchmark.svg)

The historical opponents imply **2369–2452 Elo**, around human-master level on the reference scale. Pikafish provides modern limited-strength and full-strength comparisons. Mean measured times (ours / opponent): ElephantEye 104.0 / 119.4 ms; Tianqi 155.0 / 159.6 ms; Cyclone 112.4 / 89.9 ms; Pikafish 1900 76.2 / 101.3 ms; full strength 86.9 / 91.4 ms. Our engine used about 25% more time against Cyclone.

Reproduce with [ElephantEye](run_eleeye_match.ps1), [Tianqi](run_tianqi_match.ps1), [Cyclone](run_cyclone_match.ps1), and [Pikafish](run_external_match.ps1) pipelines. Per-game JSON preserves openings, colors, outcomes, search statistics, hashes, and paired bootstrap intervals. [compact_match_result.py](compact_match_result.py) condenses the full Cyclone/Tianqi legality audits into committed records.

#### Internal comparisons

All comparisons use 192 held-out openings, colors swapped (384 games), 0.10 seconds per move, a 160-ply limit, and one logical CPU per game process. Confidence intervals resample opening pairs.

| Match | W / D / L | Score rate | Paired 95% CI |
|---|---:|---:|---:|
| Iter3 vs Iter2 | 132 / 142 / 110 | 52.86% | 49.35%–56.38% |
| Iter3 vs PST | 224 / 90 / 70 | 70.05% | 66.67%–73.44% |
| Iter2 vs Iter1 | 143 / 137 / 104 | 55.08% | 51.43%–58.72% |
| **Iter2 vs PST** | **218 / 103 / 63** | **70.18%** | **66.80%–73.44%** |
| Iter1 vs D4-H16-D3init | 174 / 120 / 90 | 60.94% | 57.16%–64.71% |
| Iter1 vs PST | 188 / 110 / 86 | 63.28% | 59.51%–66.93% |
| D4-H16-D3init vs PST | 172 / 115 / 97 | 59.77% | 56.38%–63.15% |
| D4-H16-D3init vs D4-H8-D3init | 149 / 118 / 117 | 54.17% | 50.26%–58.07% |

See [direct summaries](direct_match_summary.json), the [eight-model, five-round Swiss tournament](swiss_8models_5rounds.json), and the [generated report](RESULTS.generated.md).

![D4-H16-D3init training](training_curve.svg)
![Iteration 1 training](iter1_training_curve.svg)
![Iteration 2 training](iter2_training_curve.svg)
![Iteration 3 training](iter3_training_curve.svg)
![PST and four model generations](iteration_vs_pst.svg)

PST is the 50% baseline. Generations 1–4 score 59.77%, 63.28%, 70.18%, and 70.05% under the same protocol. Generation 1 uses one million positions each from PST D3 and D4; generations 2–4 each use one million from previous-NNUE D3 search. The observed peak is generation 3, named Iter2 in filenames.

### 2. Architecture

The network predicts a centipawn residual relative to PST:

```text
XQ-HalfKA-9x14x90 (11,340 sparse features)
  → shared 11,340×16 feature table for Red/Black perspectives
  → two H16 accumulators
  → CReLU
  → concat[side-to-move perspective, opponent perspective]
  → one selected middlegame/endgame linear output head
  → clamp(residual, ±300cp) + PST
```

Dimensions: 9 palace king anchors, 14 channels (seven types × friendly/enemy), and 90 squares. Black's view rotates 180 degrees. Both perspectives share weights. A 20-piece threshold selects a phase head; only one head runs per evaluation.

Moves, captures, and undo add/subtract feature rows. King moves rebuild the affected perspective; null moves leave accumulators unchanged. There is no additional hidden layer: H16 with a direct head gave the best observed strength/speed balance.

### 3. Teachers and datasets

Teachers use frozen PST or specified quantized NNUE. Both retain alpha-beta/PVS, valid beta cutoffs, ordering, check extensions, and quiescence. Label generation disables TT score cutoffs, reverse futility, razoring, null move, late-move/futility/SEE pruning, LMR, and negative-SEE filtering in quiescence.

Depth is a hyperparameter: D3 is cheaper and easier to fit; D4 gives stronger, costlier labels. Historical D5 is retained for comparison but excluded from the selected model. Use `--teacher pst|nnue`; PST is the compatible default. NNUE also requires `--nnue MODEL`.

Each D3, D4, Iter1, Iter2, and Iter3 dataset has **1,000,000** positions: Red 500k / Black 500k, split **700k / 150k / 150k** for training / validation / calibration. Deduplicate globally by `board + side-to-move` and split by game ID. Keep a duplicate group's unique normal nonzero, non-mate score; discard groups with conflicting normal scores. Each dataset is about 108 MB and is regenerated rather than committed.

| Dataset | Raw | Valid | Unique | Discarded conflict groups |
|---|---:|---:|---:|---:|
| D3 | 1,111,298 | 1,041,008 | 1,040,044 | 119 |
| D4 | 1,178,220 | 1,045,306 | 1,044,346 | 46 |
| Iter1 | 1,194,941 | 1,102,045 | 1,101,430 | 12 |
| Iter2 | 1,181,556 | 1,058,557 | 1,057,865 | 15 |
| Iter3 | 1,200,622 | 1,091,222 | 1,090,445 | 19 |

Iter3 also resolves two historical zero-score conflicts using the unique normal score.

### 4. Objective and training

Calibrate sigmoid temperature K separately, then freeze it: D3 **60.943546**, D4 **56.343903**, Iter1 **60.667468**, Iter2 **54.708417**, Iter3 **61.309585**. It is not jointly optimized with network weights.

Learn `teacher − PST` with fixed-K probability error plus centipawn SmoothL1 loss, avoiding near-zero residuals caused by sigmoid saturation at large scores.

| Parameter | D4-H16-D3init |
|---|---|
| Width / hidden | 16 / 0 |
| Activation | CReLU |
| Epochs / best epoch | 100 / 26; export best validation checkpoint |
| Batch | 8192 |
| Optimizer | AdamW + cosine schedule |
| Initial LR | 0.003 |
| Search / result lambda | 0.95 / 0.05 |
| Delta weight | 0.25 |
| Delta clip / Huber beta | 250 / 25 cp |
| Seed | 79808 |
| Initialization | Best D3-H16 checkpoint; rescale output by K ratio |

| Model | Probability MSE | Teacher MAE (cp) | Residual correlation |
|---|---:|---:|---:|
| D3-H8 | 0.007843 | 18.67 | 0.345 |
| D3-H16 | 0.007707 | 18.60 | 0.366 |
| D4-H8 random | 0.010372 | 22.16 | 0.446 |
| D4-H8 D3-init | 0.010630 | 22.12 | 0.411 |
| D4-H16 random | 0.010042 | 22.17 | 0.467 |
| D4-H16 D3-init | 0.009906 | 22.08 | 0.473 |
| D4 PST-only | 0.012926 | 24.73 | — |

Source: [model_comparison.json](model_comparison.json). Offline metrics screen candidates; quantized equal-time paired matches determine selection.

**Iter1** starts from D4-H16; maximum 150 epochs, minimum 25, patience 15. Best validation: epoch 4; early stop: 25. Validation probability MSE 0.007689, MAE 20.60 cp, correlation 0.643. Quantized MAE on 30k positions: 20.45 cp.

**Iter2** uses Iter1 as teacher and initialization. Best epoch 5, stop at 25. Validation MSE 0.009012, MAE 21.78 cp, correlation 0.711. Quantized 30k-position MAE 21.63 cp, correlation 0.726.

**Iter3** uses Iter2 for both roles. Minimum observed objective: epoch 2; `min_delta=1e-5` selects the nearly identical epoch-1 checkpoint. Stop at 25. Quantized 30k-position MAE 22.78 cp, correlation 0.751.

Iter3 scores 52.86% against Iter2 with an interval spanning 50%. Against PST it scores 70.05%, down 0.13 points. The predeclared rule stops at the first decline in the PST point estimate: no Iter4, retain Iter2. Overlapping intervals support a plateau, not a statistically established strength loss.

### 5. Fixed-point inference

Feature weights/biases use Q12 with int32 accumulators. Output weights fold in K and use a safe power-of-two scale (128 for the final model). Dot products/biases use int64 and one signed fixed-point division. No sigmoid runs in the C++ hot path.

Files include magic, version, dimensions, and metadata. Invalid loads report errors; running without a model falls back to PST. The initial D4 quantized model's 30k validation metrics: MAE 22.01 cp, RMSE 41.19 cp, correlation 0.493, and 81.5% sign accuracy for `|target|>=20`. These describe fit; paired games determine selection.

### 6. Findings

1. Million-position, side-balanced D3/D4 data improves on the old 150k one-sided setup.
2. Deeper teachers can produce weaker students: historical D5-H8 scored 48.13% in the Swiss tournament.
3. D3 initialization benefits D4 matches despite modest offline differences.
4. H16 earns its cost: 54.17% against H8, mean depth 9.18 vs 9.24.
5. Quantized equal-time matches include inference costs that offline MSE misses.
6. Iteration reaches a plateau: 59.77% → 63.28% → 70.18% → 70.05% against PST. Iter2 is the observed peak; the final small decline meets the stopping rule without establishing a true regression.

### 7. Key files

| File | Purpose |
|---|---|
| [nnue_engine.cpp](nnue_engine.cpp) | Features, accumulators, inference, protocol |
| [train.py](train.py) | K calibration, training, initialization, v3 export |
| [generate_data.cpp](generate_data.cpp) | Teacher self-play |
| [build_balanced_dataset.py](build_balanced_dataset.py) | Deduplication, conflicts, balance, splits |
| [verify_nnue.cpp](verify_nnue.cpp) | Incremental state and symmetry |
| [validate_quant.cpp](validate_quant.cpp) | Python/C++ quantization checks |
| [engine_match.py](engine_match.py) | Paired matches |
| [swiss_tournament.py](swiss_tournament.py) | Eight-model Swiss tournament |
| [openings_final2_192.fen](openings_final2_192.fen) | Held-out openings |
| [artifacts.json](artifacts.json) | Versions and SHA-256 |
| [report_results.py](report_results.py) | Tables and SVG plots |
| [merge_match_shards.py](merge_match_shards.py) | Merge shards and recompute CI |
| [iter1_experiment.json](iter1_experiment.json) | First iteration summary |
| [iter2_experiment.json](iter2_experiment.json) | Second iteration summary |
| [iter3_experiment.json](iter3_experiment.json) | Stopping evidence |
| [d4_balanced1m_h16_fromd3_full100_gpu.nnue](d4_balanced1m_h16_fromd3_full100_gpu.nnue) | Historical D4 baseline |
| [iter1_nnued3_h16_fromd4_gpu.nnue](iter1_nnued3_h16_fromd4_gpu.nnue) | Iter1 model |
| [iter2_nnued3_h16_fromiter1_gpu.nnue](iter2_nnued3_h16_fromiter1_gpu.nnue) | Model selected for deployment in that historical experiment |
| [iter3_nnued3_h16_fromiter2_gpu.nnue](iter3_nnued3_h16_fromiter2_gpu.nnue) | Plateau probe |
| [run_teacher_iteration.ps1](run_teacher_iteration.ps1) | Resumable generation, training, validation, matches |
| [run_until_regression.ps1](run_until_regression.ps1) | Repeated iterations with stopping rule |

### 8. Build and reproduce

Historical commands: build the engine and correctness checker, then start the Iter2 model:

```powershell
# Engine
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -o trainnnue/nnue_engine.exe trainnnue/nnue_engine.cpp

# Correctness checker
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -o trainnnue/verify_nnue.exe trainnnue/verify_nnue.cpp

trainnnue/verify_nnue.exe `
  trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue

# Historical command: start Iter2
trainnnue/nnue_engine.exe `
  --nnue trainnnue/iter2_nnued3_h16_fromiter1_gpu.nnue `
  --nnue-blend 1
```

Train after regenerating the dataset:

```powershell
python trainnnue/train.py trainnnue/train_depth4_balanced_1m_v2.bin `
  --output trainnnue/model.nnue --device cuda `
  --width 16 --hidden 0 --activation crelu --phase-heads `
  --epochs 100 --batch-size 8192 --learning-rate 0.003 `
  --lambda 0.95 --residual --delta-weight 0.25 `
  --delta-clip 250 --delta-beta 25 --seed 79808 `
  --init-nnue trainnnue/d3_balanced1m_h16_full100_gpu.nnue
```

Select a teacher (PST remains the default):

```powershell
# Original PST teacher
trainnnue/generate_data.exe shard.bin 1000 3 83000 120 2 6 1 8000000

# Quantized NNUE teacher with D3 search
trainnnue/generate_data.exe shard.bin 1000 3 83000 120 2 6 1 8000000 `
  --teacher nnue --nnue trainnnue/iter1_nnued3_h16_fromd4_gpu.nnue
```

Run external engines you have supplied locally:

```powershell
trainnnue/run_eleeye_match.ps1 `
  -EleeyePath "D:\engines\ElephantEye31\ELEEYE.EXE" -Force

trainnnue/run_cyclone_match.ps1 `
  -CyclonePath "D:\engines\Cyclone2007C\cyclone.exe" `
  -XqSecondsPerMove 0.31 -CycloneSecondsPerMove 0.10 -Force

trainnnue/run_tianqi_match.ps1 `
  -TianqiPath "D:\engines\Tianqi118\Tianqi.exe" `
  -OpeningPairs 180 -OpeningStart 12 `
  -XqSecondsPerMove 0.46 -TianqiSecondsPerMove 0.10 -Force
```

Regenerate committed tables and figures:

```powershell
python trainnnue/report_results.py
git diff --exit-code -- trainnnue/RESULTS.generated.md `
  trainnnue/training_curve.svg trainnnue/iter1_training_curve.svg `
  trainnnue/iter2_training_curve.svg trainnnue/iter3_training_curve.svg `
  trainnnue/iteration_vs_pst.svg trainnnue/external_benchmark.svg
```

Cyclone 2007C uses the early `fen ...` UCI dialect; ElephantEye 3.1 uses UCCI; Tianqi V1.1.8 uses standard UCI. The runner validates every move and bootstraps opening pairs for 95% intervals. Reporting uses only the Python standard library; regenerate outputs whenever result JSON changes.

### 9. Scope and next steps

Results apply to the recorded single-threaded setup, opening set, 160-ply limit, and then-current repetition rules. Pikafish 1900 is its built-in UCI scale. The historical plan was to repeat multiple time controls and extend perpetual-chase and perpetual-mating-threat adjudication.
