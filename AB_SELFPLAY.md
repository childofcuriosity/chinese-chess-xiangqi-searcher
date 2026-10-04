# A/B Engine Self-Play

[English](AB_SELFPLAY.md) · [简体中文](AB_SELFPLAY_zh.md)

Compare two engines differing by one change: `baseline` (before) and `candidate` (after). Games run in parallel across multiple per-move time controls, with colors swapped.

## 1. Build both versions

Use exactly the same compiler and flags. The tested change must be the only difference. Disable `ENABLE_PROFILING` for formal matches.

```powershell
g++ -O3 -std=c++17 -march=native -mtune=native -funroll-loops `
  -fno-exceptions -fno-rtti -flto -DNDEBUG `
  -static -static-libgcc -static-libstdc++ `
  -o baseline.exe baseline.cpp

g++ -O3 -std=c++17 -march=native -mtune=native -funroll-loops `
  -fno-exceptions -fno-rtti -flto -DNDEBUG `
  -static -static-libgcc -static-libstdc++ `
  -o candidate.exe xiangqi_ai.cpp
```

Build and retain `baseline.exe` before editing, then build `candidate.exe`. Keep optimization flags, networks, and unrelated changes identical.

## 2. Run paired matches

```powershell
python ab_selfplay.py baseline.exe candidate.exe
```

Defaults:

- 0.5, 0.75, 1.0, 1.5, and 2.0 seconds per move.
- Two games per time control, each engine playing Red once.
- At most 160 plies per game.
- Parallel jobs equal to the logical processor count minus two.

Custom example:

```powershell
python ab_selfplay.py baseline.exe candidate.exe `
  --times 0.25,0.5,1,2 `
  --max-plies 200 `
  --repeats 2 `
  --jobs 10 `
  --output ab_results/my_change
```

The engines take turns searching, so a game between single-threaded engines generally occupies one logical processor. Keep `--jobs` within available CPU capacity: oversubscription adds scheduling noise under wall-clock limits.

## 3. Output

The tool prints completed results and writes full game logs plus `summary.json`, including W/D/L, candidate score rate, time controls, colors, and log paths.

```text
Win = 1 point; draw = 0.5 points; loss = 0 points
```

Inspect total W/D/L, performance with each color, consistency across time controls, crashes/timeouts/unexpected resignations, and whether draws simply reached `max_plies`.

## 4. Interpretation

Engines starting from a fixed position are often highly deterministic. Different time controls can stop iterative deepening at different depths and produce different games, but these samples remain correlated.

- Small matches support regression screening and rejection of obvious losses.
- Zero wins, several draws, and several losses warn against merging directly.
- A result near 50% does not establish equal strength.
- Elo estimation requires varied legal openings, many color-swapped games, and confidence intervals.
- A move-limit draw is distinct from adjudication under complete competition rules.

For equivalent performance optimizations, also compare nodes, scores, and best moves on fixed positions. Such optimizations should generally preserve node counts. Strength changes may alter the tree, but their benefits require match evidence.

## 5. Single-game tool

```powershell
python selfplay.py red.exe black.exe 160 1.0
```

Arguments are Red engine, Black engine, maximum plies, and seconds per move. Omit the last argument to use each engine's default time configuration.
