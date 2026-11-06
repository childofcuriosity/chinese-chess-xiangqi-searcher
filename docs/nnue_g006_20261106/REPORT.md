# g006: Label Fit and Playing-Strength Evaluation

[简体中文](REPORT_zh.md) · [System and method](../../README.md) · [NNUE computation](../../trainnnue/README.md) · [Machine-readable recipe](recipe.json) · [Opening-pair evidence](matches.compact.json)

The deployed **g006** model uses H128, mirrored side-king parameter sharing, int8 feature weights, int16 accumulators, and fixed-E20 QAT fine-tuning. It passed the point-score promotion rule against six internal opponents. Its scores against ElephantEye, Tianqi and Cyclone were 83.07%, 76.56% and 57.03%. This report describes the tested model, time controls and conclusions supported by those measurements.

## 1. Model and training configuration

g006 was trained from random parameters on 12 million fresh positions. g005 acted as both the common labeling teacher and one player, facing PST and g001–g005 for two million valid positions per source. The PST opponent selected moves at D4; NNUE players used D3. Every label came from g005's independent single-PV D3 best search. Exploration sampled root ranks 1/2/3 with probabilities 50%/30%/20%, while supervision retained the best score. External engines supplied evaluation only.

The network sums shared feature vectors from Red and Black views, then uses CReLU and a phase-dependent linear head to predict a correction to PST. Three pairs of side-king positions share parameters with the piece squares mirrored as well. The 7,560 independent H128 vectors are copied into 11,340 rows at export. Runtime uses feature scale E20, output scale O128 and integer arithmetic with checked overflow bounds. [Complete computation and training definition](../../trainnnue/README.md)

Training minimizes only normalized search-residual MSE:

$$
d_i=\operatorname{clip}(S_i-P_i,-250,250),\qquad
L=\frac1N\sum_i\left(\frac{r_i-d_i}{K}\right)^2,
\quad K=65.38910923790853.
$$

$S_i$ and $P_i$ are the teacher's best search score and PST score in side-to-move units; $N$ is the number of positions and $r_i$ the predicted residual. Floating training uses $r_i=Kz_i$, where $z_i$ is the network's linear output; QAT uses the integer total evaluation minus PST, including runtime clipping. Game outcomes do not enter the loss. Teacher search carries game history, whereas network inputs contain only board and side to move; this limits the information available to the network.

Whole-game splitting produced 11,760,000 training, 120,000 validation and 120,000 held-out positions. Training used a GTX 1650 Ti, AdamW, effective batch size 8192, microbatches of 2048, weight decay $10^{-6}$, gradient-norm clipping at 1, epoch-wise global shuffling and 50% horizontal mirroring. Initial learning rates were 0.003 for floating training and 0.0003 for QAT. The best floating checkpoint determined the largest safe feature scale E, which stayed fixed during QAT. [Settings and source hashes](recipe.json)

| Computation | Selected / completed epoch | Residual MSE on the same 120,000 validation positions |
|---|---:|---:|
| Floating model | 22 / 37 | 0.4918713882 |
| Direct integer quantization (PTQ) | — | 0.4975802947 |
| QAT integer export | 1 / 9 | 0.4886772009 |

QAT reduced fitting error under deployed integer computation. Matches below measure playing strength of the complete network-and-search system; this loss comparison specifically establishes improved label fit.

## 2. Match and statistical protocol

Each formal comparison used 96 openings, playing both colors from each opening, for 192 games. All wins/draws/losses below are from g006's perspective. Pure win rate is $W/N$ and score rate is $S=(W+D/2)/N$. The 95% intervals use 10,000 opening-pair bootstrap samples, keeping both games from each opening together. Displayed percentages use half-up rounding to two decimals; [compact evidence](matches.compact.json) retains the underlying values.

Time comparisons use measured mean search time. Nominal budgets were selected using independent calibration openings and frozen before formal play; adjustments depended only on timing. The six internal comparisons and the new ElephantEye/Tianqi matches required each side's formal mean to fall within 150 ms ±5%, with the actual-time ratio within 5% of equality. The two new public matches used 12 pairs per calibration stage and an independent 48-pair timing confirmation before 96 separate formal pairs. These two matches used one logical CPU and a 160-ply game limit.

Cyclone reuses a retained observation of the same g006 model, accepted under its original relative-time rule: the two sides' mean-time ratio had to be within 5% of equality. It and the internal matches used an experimental build; the two new public matches used the production build. Artifact identities appear below, and each table reports actual time.

## 3. Six internal comparisons

PST and g001–g005 are the opponents of the tested g006 model. Each row has 192 games, totaling 1,152.

| Opponent | Wins / draws / losses | Pure win rate (95% interval) | Score rate (95% interval) | Actual ms/move: g006 / opponent |
|---|---:|---:|---:|---:|
| PST | 163 / 22 / 7 | 84.90% (80.21–89.06%) | 90.63% (87.50–93.49%) | 149.359 / 150.835 |
| g001 | 139 / 34 / 19 | 72.40% (66.67–78.13%) | 81.25% (76.82–85.42%) | 150.624 / 150.577 |
| g002 | 96 / 66 / 30 | 50.00% (44.27–56.25%) | 67.19% (62.76–71.61%) | 152.535 / 154.232 |
| g003 | 77 / 71 / 44 | 40.10% (34.38–45.83%) | 58.59% (54.43–62.76%) | 155.837 / 156.090 |
| g004 | 63 / 81 / 48 | 32.81% (27.08–38.54%) | 53.91% (49.48–58.33%) | 147.955 / 151.038 |
| g005 | 56 / 92 / 44 | 29.17% (23.44–34.90%) | 53.13% (48.96–57.29%) | 149.524 / 149.305 |

Every point score exceeds 50%, so g006 passed the prescribed promotion rule. Intervals against g004 and g005 contain 50%; these samples have not statistically resolved those two advantages. The [g006 comparison records](matches.compact.json) retain the results, model identities, openings and timing evidence.

## 4. Three public-engine opponents

Each row has 192 games, totaling 576. ElephantEye and Tianqi are new production-build matches; Cyclone is the retained experimental-build observation.

| Opponent | Wins / draws / losses | Pure win rate (95% interval) | Score rate (95% interval) | Actual ms/move: g006 / opponent |
|---|---:|---:|---:|---:|
| ElephantEye 3.1 | 142 / 35 / 15 | 73.96% (68.23–79.69%) | 83.07% (78.91–87.24%) | 149.089 / 148.672 |
| Tianqi V1.1.8 | 126 / 42 / 24 | 65.63% (58.85–72.40%) | 76.56% (71.61–81.51%) | 150.358 / 152.969 |
| Cyclone 2007C | 78 / 63 / 51 | 40.63% (33.85–46.88%) | 57.03% (52.08–61.98%) | 144.366 / 142.902 |

All three score intervals lie above 50%, supporting an advantage under each match's recorded conditions. The Chinese name “巫师象眼3.1” identifies ElephantEye 3.1 here; no result against Xiangqi Wizard 5.44 is included. Public opponents supplied neither training labels nor internal promotion decisions. [External settings and summaries](recipe.json)

## 5. Computing the reference Elo

The fixed anchors are ElephantEye 2130.2, Tianqi 2430 and Cyclone 2600 from the [2026-10-09 public engine list](https://bbs.pikafish.org/forum.php?mod=viewthread&tid=179&extra=page%3D1). An individual opponent gives

$$R_i=r_i+400\log_{10}\frac{S_i}{1-S_i},$$

where $r_i$ is its fixed anchor and $S_i$ is g006's measured score against it.

| Opponent anchor | Implied g006 reference Elo (95% interval) |
|---|---:|
| ElephantEye 2130.2 | 2406.55 (2359.38–2464.14) |
| Tianqi 2430 | 2635.64 (2590.76–2687.71) |
| Cyclone 2600 | 2649.18 (2614.48–2684.89) |

The joint rating fits all three matches. Let $\ell_i(R)=1/(1+10^{(r_i-R)/400})$ be the Elo model's expected score. The fractional-score logistic maximum-likelihood objective yields

$$\sum_i N_i\left[S_i-\ell_i(R)\right]=0.$$

Solving this equation gives **2600.874, with a 95% interval of 2573.758–2629.235**. This is a joint fit to 576 games, not the mean of three transformed ratings. Its interval uses 10,000 opening-pair bootstrap draws with seed 2026110623. ElephantEye and Tianqi share their formal opening set, so their openings are resampled together; Cyclone is resampled independently. Every draw refits R with the opponent anchors fixed.

The individual estimates span roughly 2407–2649, showing that one Elo value does not fully describe all opponent relationships. The joint estimate provides a reference coordinate for these short-time-control results. Its interval includes opening-pair sampling uncertainty, but excludes uncertainty in anchors, hardware, time control, rules and engine-build differences.

The source list relates Cyclone's 2600 anchor to top human professional play in 2006–2007. Its tests used four EPYC-9654 cores, 60 seconds plus 0.6 seconds per move, and Asian rules. Here, one logical CPU searches for approximately 150 ms per move. A human-rating comparison would require additional evidence under comparable conditions. [Source methodology](https://bbs.pikafish.org/forum.php?mod=viewthread&tid=179&extra=page%3D1)

## 6. Artifact identities and evidence

| Artifact | SHA-256 |
|---|---|
| g006 model used in every table | `746e930533cddf7907c85545659605b7477bf32bdb0335a6ca0b3b743455af5e` |
| Windows production engine: new ElephantEye/Tianqi matches | `ad9a1567129b6d461573ee22f1fce36f4981775259eebe05d8e9ef872d99d5db` |
| Experimental engine: six internal matches and Cyclone observation | `e6f367414e9b3152db27d25bdbeac183173c5d519141b79c17302183c3a5ca9e` |
| Current online Linux production engine | `1758f48584e5be8bcfe8ef41b2da5a15eab2afc0b3362938e93aea70b1071f8f` |

The [recipe](recipe.json) preserves training settings, source and result hashes, external-match configuration and the joint Elo output. The [opening-pair evidence](matches.compact.json) records openings, both colors' outcomes, search counts and times, and model/build identities. This report presents g006's results; the complete original experiment records remain preserved.
