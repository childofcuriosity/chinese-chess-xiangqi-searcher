# Running, Configuration, and Versions

[English](RUNNING.md) · [简体中文](RUNNING_zh.md)

This guide covers repository-level entry points. See the [NNUE guide](../trainnnue/README.md) for training algorithms and experiments.

## 1. Environment

| Use case | Verified environment |
|---|---|
| Windows development / training | Windows 11, Python 3.12, MSYS2 UCRT64 GCC, PyTorch 2.6.0+cu124 |
| Linux web deployment | Python venv, C++17 GCC, systemd, x86-64 CPU |
| Engine protocol | UTF-8 text over stdio; PST and NNUE share commands |

Install application dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For tests:

```powershell
python -m pip install -r requirements-dev.txt
```

Training dependencies are separate so ordinary web users do not need PyTorch:

```powershell
python -m pip install -r trainnnue/requirements.txt
```

Install GPU PyTorch using the wheel index appropriate for your drivers. The requirements file does not pin a CUDA wheel. The original training environment used `.venv-gpu\python.exe`, Python 3.12.14, and PyTorch 2.6.0+cu124; it is local and excluded from Git. Check `torch.cuda.is_available()` before reproducing GPU training.

## 2. Build engines

### Project PST engine

Windows/MSYS2:

```powershell
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -fno-exceptions -fno-rtti -static -static-libgcc -static-libstdc++ `
  -o xiangqi_ai.exe xiangqi_ai.cpp
```

Linux:

```bash
g++ -O3 -std=c++17 -march=native -DNDEBUG -o xiangqi_ai xiangqi_ai.cpp
```

### Project NNUE engine

```powershell
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -o trainnnue/nnue_engine.exe trainnnue/nnue_engine.cpp

trainnnue/nnue_engine.exe `
  --nnue trainnnue/iter2_nnued3_h16_fromiter1_gpu.nnue `
  --nnue-blend 1
```

Without `--nnue`, the executable falls back to PST evaluation. `XQ_NNUE_FILE` and `XQ_NNUE_BLEND` also configure it.

### Pikafish PST

The repository includes experimental Pikafish binaries, a network, and [pikafish_bridge.py](../pikafish_bridge.py). Windows starts the Python bridge directly; Linux deployment builds `pikafish-pst` and installs the bridge entry point.

## 3. Run

### Web application

```powershell
python webapp.py
# Open http://localhost:8000
```

Choose the project NNUE engine (default), project PST engine, or Pikafish PST. Each game gets a separate engine process; the server maintains board state, move legality, and sessions.

### pygame desktop client

```powershell
python gui.py
```

The desktop client defaults to the root PST engine, `xiangqi_ai`.

### Tutorial

Open the [English interactive tutorial](../slides-formal-web-lite/index.html), [Chinese tutorial](../slides-formal-web-lite_zh/index.html), or [English PDF](../slides-formal-web-lite/xiangqi-engine-tutorial.pdf). To serve the English version locally:

```powershell
python -m http.server 8080 --directory slides-formal-web-lite
# http://localhost:8080
```

The tutorial progresses from legal moves to evaluation and forward search.

## 4. Web environment variables

| Variable | Default | Meaning |
|---|---|---|
| `XQ_PORT` | `8000` | Listening port |
| `XQ_MAX_GAMES` | `16` | Maximum concurrent games |
| `XQ_IDLE_TIMEOUT` | `1800` | Idle session lifetime in seconds |
| `XQ_REAP_INTERVAL` | `60` | Session cleanup interval in seconds |
| `XQ_DEFAULT_SEARCH_TIME` | `5` | Default thinking seconds per move |
| `XQ_CUSTOM_ENGINE_PATH` | `./xiangqi_ai` | Project PST executable |
| `XQ_CUSTOM_NNUE_ENGINE_PATH` | `./xiangqi_nnue` | Project NNUE executable |
| `XQ_CUSTOM_NNUE_MODEL_PATH` | `./xiangqi_nnue_best.nnue` | Web NNUE weights |
| `XQ_PIKAFISH_PST_ENGINE_PATH` | `./pikafish_pst_bridge` | Pikafish bridge entry point |
| `XQ_CLOUD_BOOK_ENABLED` | `0` | Enable ChessDB for new games |
| `XQ_CLOUD_BOOK_TIMEOUT` | `2` | ChessDB timeout in seconds |
| `XQ_CLOUD_BOOK_SCORE_THRESHOLD` | `20` | Maximum score gap from the best book move |
| `XQ_CLOUD_BOOK_URL` | Public ChessDB API | Override cloud-book endpoint |

PowerShell example:

```powershell
$env:XQ_DEFAULT_SEARCH_TIME = "1"
$env:XQ_CLOUD_BOOK_ENABLED = "1"
python webapp.py
```

## 5. Model and data versions

The machine-readable manifest is [artifacts.json](../trainnnue/artifacts.json).

| Artifact | Version / size | Distributed in Git | SHA-256 |
|---|---|---|---|
| Initial D4 NNUE | v3, HalfKA, H16, 363,128 bytes | Yes; historical baseline | `E677DAA6…ED65990` |
| Balanced D3 data | 1,000,000 × 108-byte records | No | `918EA99E…0C0F9E` |
| Balanced D4 data | 1,000,000 × 108-byte records | No | `079C403D…C492D2` |
| Iteration 1 data | 1,000,000 × 108-byte records | No | `F61D6FF6…EDCF6` |
| Iteration 1 NNUE | H16, 363,128 bytes | Yes; not deployed | `93969CDE…DC56` |
| Iteration 2 data | 1,000,000 × 108-byte records | No | `60E70768…D16D2` |
| Iteration 2 best NNUE | H16, 363,128 bytes | Yes; deployed on the web | `FCBBF451…85CB3` |
| Iteration 3 data | 1,000,000 × 108-byte records | No | `BE054B40…1ED54` |
| Iteration 3 plateau probe | H16, 363,128 bytes | Yes; not selected | `3E71A79C…759FE` |

Each dataset is about 108 MB and can be regenerated with `generate_data.cpp` and `build_balanced_dataset.py`. Model metadata records training parameters, per-epoch loss, K, quantization scales, and validation metrics.

## 6. Experiments

### Two-version regression

```powershell
python ab_selfplay.py baseline.exe candidate.exe `
  --times 0.25,0.5,1,2 --repeats 2 --jobs 6
```

This detects obvious regressions. Small samples from one initial position do not support Elo estimates. See the [A/B guide](../AB_SELFPLAY.md).

### Play against Pikafish

```powershell
python cross_arena.py --pairs 10 --seconds 1 `
  --summary cross_arena_summary.json
```

### Regenerate NNUE results and curves

```powershell
python trainnnue/report_results.py --check-artifacts
```

The standard-library-only script builds `RESULTS.generated.md` and SVG figures from committed JSON.

### Tests

```powershell
python -m pytest tests -q
```

WebSocket tests involving real engine searches take longer than ordinary unit tests.

## 7. Deployment

Copy and fill in server configuration:

```powershell
Copy-Item deploy/secrets.env.example deploy/secrets.env
```

Then use the standard deployment entry point:

```powershell
deploy\deploy.ps1
```

It uploads Python and frontend files, uses MD5 comparisons to decide whether to rebuild PST/NNUE/Pikafish, uploads the selected model, updates systemd, and checks for an `active` service and HTTP 200 response.

## 8. stdio protocol

| Command | Behavior |
|---|---|
| `ready` | Reply `readyok` |
| `side red\|black` | Set the human side; the engine takes the opposite side |
| `setboard <FEN>` | Set a position |
| `time <seconds>` | Set thinking time per move |
| `depth <n>` | Set fixed depth; 0 selects timed iterative deepening |
| `move r1 c1 r2 c2` | Synchronize the opponent move |
| `forbid r1 c1 r2 c2` | Exclude a root move |
| `search` | Output `move ...` or `resign` |
| `quit` | Exit |
