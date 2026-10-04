# Experiment Design and Evidence

[English](EXPERIMENTS.md) · [简体中文](EXPERIMENTS_zh.md)

The project separately evaluates correctness, performance equivalence, playing strength, and application reliability. Each requires its own evidence.

## 1. Four questions

| Question | Preferred method | Evidence |
|---|---|---|
| Are state and rules correct? | Unit tests, randomized make/undo checks, illegal moves | pytest results, transition counts |
| Is an optimization equivalent? | Compare moves, scores, and nodes at fixed positions/depths | Controlled logs |
| Is evaluation or search stronger? | Fixed openings, swapped colors, equal time, paired statistics | Game JSON, W/D/L, CI |
| Do the web app and deployment work? | WebSocket end-to-end, real processes, HTTP checks | Tests and systemd status |

## 2. Tools

`selfplay.py` is a minimal single-game arbiter for checking whether two stdio engines can complete a game. One game is insufficient for statistical strength conclusions.

`ab_selfplay.py` runs baseline/candidate pairs across time controls in parallel. It detects crashes, unexpected resignations, and obvious regressions. Its default initial position produces correlated samples; see the [A/B guide](../AB_SELFPLAY.md).

`cross_arena.py` bridges the project engine to official Pikafish, with configurable time controls and paired repetitions. It starts from the initial position and primarily supports protocol/function regression.

`trainnnue/engine_match.py` is the formal arbitrary-engine match runner. It reads a fixed FEN slice, swaps colors per opening, records nodes/depth/actual time, and bootstraps opening pairs. Additional process arguments allow official Pikafish bridges.

`trainnnue/run_external_match.ps1` runs the official Pikafish NNUE benchmark. Shards use separate CPUs; both engines in a game share one logical core. Records include official executable, network, and project model hashes. Twelve calibration openings freeze time multipliers and strength settings; 180 remaining openings produce the formal 360 games.

Historical-engine pipelines reuse fixed openings, color swaps, affinity, wall-clock statistics, and paired bootstrap. The match runner validates each move and saves audit records:

- `run_eleeye_match.ps1`: ElephantEye 3.1 through UCCI.
- `run_cyclone_match.ps1`: Cyclone 2007C through its early `fen ...` UCI dialect.
- `run_tianqi_match.ps1`: Tianqi V1.1.8 through standard UCI.

`trainnnue/swiss_tournament.py` ranks eight models over five rounds, pairing similar cumulative scores while avoiding rematches. Four concurrent matches use separate CPUs. Finalists and PST still require direct matches.

`trainnnue/report_results.py` deterministically generates Markdown and SVG from model metadata, offline comparisons, Swiss results, and direct-match JSON. It preserves recorded values.

## 3. Formal controls

- Internal comparisons share search implementation, compiler optimization, and protocol; evaluation is the target variable.
- The 192 held-out openings are excluded from training and development selection.
- Each opening is played with both colors.
- Each engine gets 0.10 seconds per move, at most 160 plies, with fixed CPU affinity.
- Confidence intervals cluster by opening pair, preserving within-pair correlation.
- Freeze candidates before matches; subsequent tuning requires fresh development data.

External Pikafish uses version `2026-01-31`, `Threads=1`, `Ponder=false`, and `Move Overhead=0`. Nominal times are 0.25 s for our engine and 0.10 s for Pikafish. The multiplier, calibrated on 12 openings, accounts for our completed-iteration stopping strategy. Formal measured means are 76.2 / 101.3 ms at UCI Elo 1900 and 86.9 / 91.4 ms at full strength.

## 4. Results and sources

The [generated results](../trainnnue/RESULTS.generated.md) summarize these machine-readable records:

- [Direct matches](../trainnnue/direct_match_summary.json) and [Swiss tournament](../trainnnue/swiss_8models_5rounds.json).
- [D4 model metadata](../trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue.json).
- [Iteration 1](../trainnnue/iter1_experiment.json), [iteration 2](../trainnnue/iter2_experiment.json), [iteration 3](../trainnnue/iter3_experiment.json).
- [Pikafish 1900](../trainnnue/iter2_vs_pikafish_elo1900_180pairs.json) and [full strength](../trainnnue/iter2_vs_pikafish_official_180pairs.json).
- [ElephantEye](../trainnnue/iter2_vs_eleeye31_180pairs.json), [Cyclone](../trainnnue/iter2_vs_cyclone2007c_180pairs.compact.json), [Tianqi](../trainnnue/iter2_vs_tianqi118_180pairs.compact.json).

D4-H16-D3init scores **59.77%** against PST (95% CI **56.38%–63.15%**) and **54.17%** against D4-H8-D3init (**50.26%–58.07%**).

Iter2 scores **169/68/123**, or **56.39%**, against Pikafish's built-in 1900 setting (CI **51.94%–60.83%**). Against full strength: **6/44/310**, **7.78%** (CI **5.69%–10.00%**).

Historical matches yield **290/31/39 (84.86%)** against ElephantEye, **109/79/172 (41.25%)** against Tianqi, and **60/95/205 (29.86%)** against Cyclone. With reference anchors **2130.4 / 2430 / 2600** from the [public rating list](https://zhuanlan.zhihu.com/p/2072972857840350627), implied ratings are about **2430 / 2369 / 2452 Elo**, near **2400, or human-master level on that scale**. Cyclone used 89.9 ms on average versus our 112.4 ms; the result retains this condition.

**Iteration 1:** D4-H16 plus D3 teacher search generates a fresh million positions. The student scores **60.94%** against its predecessor (CI **57.16%–64.71%**) and **63.28%** against PST (**59.51%–66.93%**), compared with the predecessor's 59.77%. This round shows improvement under the shared benchmark; later iterations require their own tests.

**Iteration 2:** Iter1 supplies teacher and initialization for another million positions. Iter2 scores **55.08%** against Iter1 (**51.43%–58.72%**) and **70.18%** against PST (**66.80%–73.44%**), a **6.90-point** increase. Two successful rounds establish these gains, while the asymptotic limit remains open.

**Iteration 3:** Iter2 supplies both roles. Iter3 scores **52.86%** against Iter2 (**49.35%–56.38%**) and **70.05%** against PST (**66.67%–73.44%**). The PST estimate declines **0.13 points**, triggering the predeclared first-decline stopping rule. Iter2 remains selected. Overlapping intervals support a plateau, not a statistically established loss of strength.

[run_teacher_iteration.ps1](../trainnnue/run_teacher_iteration.ps1) implements one complete round; [run_until_regression.ps1](../trainnnue/run_until_regression.ps1) repeats rounds with the stopping rule. Each preserves independent data, K, checkpoints, quantization checks, and both formal match sets.

## 5. Interpretation

Internal PST matches measure neural-evaluation gains; official Pikafish provides an external comparison. `UCI_Elo=1900` is Pikafish's internal scale; platform ratings require placement matches on that platform. Swiss tournaments rank candidates, while direct paired matches determine selection. Current adjudication includes a 160-ply experimental cutoff; complete perpetual-chase and perpetual-mating-threat rules remain future work.

## 6. Further evidence

A stable Elo estimate requires preregistered models/time controls, thousands of independent opening pairs, repetition across machines, and complete repetition adjudication. New tuning must use new development data rather than repeatedly optimizing against the formal held-out set.
