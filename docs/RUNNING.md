# 运行、配置与版本说明

本文档给出仓库级运行入口。NNUE训练算法与实验解释见 [`../trainnnue/README.md`](../trainnnue/README.md)。

## 1. 环境

已验证环境：

| 场景 | 环境 |
|---|---|
| Windows开发/训练 | Windows 11，Python 3.12，MSYS2 UCRT64 GCC，PyTorch 2.6.0+cu124 |
| Linux网页部署 | Python venv，C++17 GCC，systemd，x86-64 CPU |
| 引擎协议 | UTF-8文本 stdio；PST/NNUE 共用同一命令集合 |

基础依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

测试依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

NNUE训练依赖单独安装，避免普通网页用户下载 PyTorch：

```powershell
python -m pip install -r trainnnue/requirements.txt
```

GPU版 PyTorch 应按显卡驱动和官方 wheel 索引安装；`requirements.txt` 不固定 CUDA wheel。

## 2. 构建引擎

### 自研 PST 引擎

Windows/MSYS2：

```powershell
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -fno-exceptions -fno-rtti -static -static-libgcc -static-libstdc++ `
  -o xiangqi_ai.exe xiangqi_ai.cpp
```

Linux：

```bash
g++ -O3 -std=c++17 -march=native -DNDEBUG -o xiangqi_ai xiangqi_ai.cpp
```

### 自研 NNUE 引擎

```powershell
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -o trainnnue/nnue_engine.exe trainnnue/nnue_engine.cpp

trainnnue/nnue_engine.exe `
  --nnue trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue `
  --nnue-blend 1
```

未提供 `--nnue` 时，NNUE可执行文件安全回退为 PST 评价。也可通过 `XQ_NNUE_FILE` 和 `XQ_NNUE_BLEND` 配置。

### Pikafish PST

仓库包含用于实验的 Pikafish 二进制、网络和 [`pikafish_bridge.py`](../pikafish_bridge.py)。网页在 Windows 下直接启动 Python bridge；Linux部署脚本会编译 `pikafish-pst` 并安装桥接入口。

## 3. 运行入口

### 网页端

```powershell
python webapp.py
# 浏览器打开 http://localhost:8000
```

下拉框可选择：

1. 自研NNUE引擎（默认）；
2. 自研PST引擎；
3. Pikafish PST。

每局创建独立引擎进程；棋盘、走法合法性和会话状态由服务端维护。

### pygame桌面端

```powershell
python gui.py
```

桌面端当前默认连接根目录的 PST `xiangqi_ai`。

### 正式教程

直接打开 [`../slides-formal-web-lite/index.html`](../slides-formal-web-lite/index.html)，或启动静态服务器：

```powershell
python -m http.server 8080 --directory slides-formal-web-lite
# http://localhost:8080
```

教程按“让棋走起来 → 给局面一点棋感 → 向前推演”的顺序覆盖整个系统。

## 4. 网页环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `XQ_PORT` | `8000` | 本地监听端口 |
| `XQ_MAX_GAMES` | `16` | 最大并发对局数 |
| `XQ_IDLE_TIMEOUT` | `1800` | 空闲会话回收秒数 |
| `XQ_REAP_INTERVAL` | `60` | 会话回收扫描间隔 |
| `XQ_DEFAULT_SEARCH_TIME` | `5` | 新对局每步默认思考秒数 |
| `XQ_CUSTOM_ENGINE_PATH` | `./xiangqi_ai` | 自研PST引擎路径 |
| `XQ_CUSTOM_NNUE_ENGINE_PATH` | `./xiangqi_nnue` | 自研NNUE引擎路径 |
| `XQ_CUSTOM_NNUE_MODEL_PATH` | `./xiangqi_nnue_best.nnue` | 网页使用的NNUE权重 |
| `XQ_PIKAFISH_PST_ENGINE_PATH` | `./pikafish_pst_bridge` | Pikafish桥接入口 |
| `XQ_CLOUD_BOOK_ENABLED` | `0` | 新对局默认启用ChessDB |
| `XQ_CLOUD_BOOK_TIMEOUT` | `2` | ChessDB查询超时秒数 |
| `XQ_CLOUD_BOOK_SCORE_THRESHOLD` | `20` | 随机候选相对最佳着最大分差 |
| `XQ_CLOUD_BOOK_URL` | ChessDB公开接口 | 可替换的云库地址 |

PowerShell示例：

```powershell
$env:XQ_DEFAULT_SEARCH_TIME = "1"
$env:XQ_CLOUD_BOOK_ENABLED = "1"
python webapp.py
```

## 5. 模型与数据版本

机器可读清单位于 [`../trainnnue/artifacts.json`](../trainnnue/artifacts.json)。

| Artifact | 版本/规模 | 是否随Git分发 | SHA-256 |
|---|---|---:|---|
| 最佳NNUE | v3, HalfKA, H16, 363,128 bytes | 是 | `E677DAA6…ED65990` |
| D3平衡数据 | 1,000,000 × 108-byte record | 否 | `918EA99E…0C0F9E` |
| D4平衡数据 | 1,000,000 × 108-byte record | 否 | `079C403D…C492D2` |

数据集不进 Git：每份约108MB，可由 `generate_data.cpp` 与 `build_balanced_dataset.py` 重建。模型元数据文件记录训练参数、每轮损失、K、量化尺度和验证指标。

## 6. 实验命令

### 两版本回归

```powershell
python ab_selfplay.py baseline.exe candidate.exe `
  --times 0.25,0.5,1,2 --repeats 2 --jobs 6
```

该工具适合发现明显回退；固定初始局面的小样本结果不用于 Elo 结论。详见 [`../AB_SELFPLAY.md`](../AB_SELFPLAY.md)。

### 对战Pikafish

```powershell
python cross_arena.py --pairs 10 --seconds 1 `
  --summary cross_arena_summary.json
```

### 生成NNUE结果表和学习曲线

```powershell
python trainnnue/report_results.py --check-artifacts
```

脚本只使用Python标准库，从已提交JSON生成 `RESULTS.generated.md` 和 `training_curve.svg`。

### 测试

```powershell
python -m pytest tests -q
```

涉及真实引擎思考的WebSocket测试比普通单元测试慢。

## 7. 部署

复制并填写服务器配置：

```powershell
Copy-Item deploy/secrets.env.example deploy/secrets.env
```

之后统一运行：

```powershell
deploy\deploy.ps1
```

脚本上传Python和前端文件，按MD5决定是否重编译PST、NNUE和Pikafish，上传最佳NNUE模型，更新systemd服务，最后检查服务为 `active` 且HTTP返回200。

## 8. stdio协议

| 命令 | 行为 |
|---|---|
| `ready` | 回复 `readyok` |
| `side red|black` | 设置人类执子方；引擎执相反方 |
| `setboard <FEN>` | 设置局面 |
| `time <seconds>` | 设置每步思考时间 |
| `depth <n>` | 设置固定深度；0表示限时迭代加深 |
| `move r1 c1 r2 c2` | 同步对手着法 |
| `forbid r1 c1 r2 c2` | 禁止一个根着法 |
| `search` | 输出 `move ...` 或 `resign` |
| `quit` | 退出进程 |
