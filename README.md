# 中国象棋 AI：从 PST 搜索引擎到增量 NNUE

一个完整可运行的中国象棋 AI 项目：C++ 搜索引擎、PST/NNUE 两套评价、GPU 训练流水线、CPU 定点推理、公平对战工具，以及 FastAPI + WebSocket 网页端。

在线试玩：<http://47.102.137.220:8100>（默认选择自研 NNUE 引擎）

## NNUE 成果（STAR）

- **Situation**：原引擎依赖手工 PST 评价；直接换成神经网络会显著降低单核搜索深度，而且深层搜索标签昂贵、难拟合。
- **Task**：在保留原搜索框架的前提下，完成可增量更新、可量化、能在单核等时条件下稳定战胜 PST 的轻量 NNUE。
- **Action**：实现 `XQ-HalfKA-9x14x90` 双视角特征和 make/undo 增量累加器；并行生成 D3/D4 各 100 万条、红黑待走平衡且全局去重的数据；独立统计 sigmoid 温度 K；比较 H8/H16、随机/D3 初始化；将最佳模型量化为纯整数 C++ 推理并接入网页。
- **Result**：最终 **D4-H16（D3 初始化）**模型仅 **363KB**。在 192 个固定保留开局逐一换先的 384 盘单核等时测试中，对 PST 取得 **172胜115和97负，得分率59.77%**，配对 bootstrap 95% CI 为 **[56.38%, 63.15%]**；对并列候选 D4-H8 取得 **54.17%**。

> 这里的“得分率”按胜=1、和=0.5、负=0计算。测试为 0.10 秒/步、最长160 ply，双方使用相同搜索代码与 CPU 限制。

## 技术方案

```text
局面 → 双视角 HalfKA 稀疏特征 → H16 增量累加器 → CReLU
     → 待走方/对方拼接 → 阶段输出头 → NNUE 残差 + PST → 搜索评价
```

- **搜索**：迭代加深、PVS/Alpha-Beta、置换表、静态搜索、空步裁剪、LMR、SEE、历史/杀手启发。
- **NNUE**：11,340 个 HalfKA 特征，H=16，无隐藏层；普通走子/吃子/撤销增量更新，将帅移动仅重建受影响视角。
- **训练**：PST 无风险剪枝教师；D3→D4 课程初始化；概率损失 + cp 残差 SmoothL1；K 在 calibration 集独立拟合后冻结。
- **部署**：特征变换 Q12、输出定点量化，C++ 热路径无 sigmoid；网页可切换“自研NNUE引擎 / 自研PST引擎 / Pikafish PST”。

完整的数据规则、网络结构、训练矩阵、正确性验证和比赛结果见 [trainnnue/README.md](trainnnue/README.md)。

## 项目入口

| 路径 | 说明 |
|---|---|
| [`xiangqi_ai.cpp`](xiangqi_ai.cpp) | 原始 PST 搜索引擎 |
| [`trainnnue/nnue_engine.cpp`](trainnnue/nnue_engine.cpp) | 增量、定点 NNUE 搜索引擎 |
| [`trainnnue/train.py`](trainnnue/train.py) | GPU/CPU 训练、独立 K 校准与模型导出 |
| [`trainnnue/generate_data.cpp`](trainnnue/generate_data.cpp) | 多深度教师数据生成 |
| [`trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue`](trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue) | 当前最佳量化模型 |
| [`webapp.py`](webapp.py) / [`static/index.html`](static/index.html) | FastAPI + WebSocket 网页端 |
| [`deploy/deploy.ps1`](deploy/deploy.ps1) | 上传、编译、重启与 HTTP 验证的一键部署 |
| [`slides-formal-web-lite/index.html`](slides-formal-web-lite/index.html) | 中国象棋搜索与 NNUE 的交互式教程 |

## 快速运行

### 网页版

```powershell
pip install fastapi "uvicorn[standard]"
python webapp.py
# 打开 http://localhost:8000
```

网页端每局使用独立引擎进程，服务端校验合法着，支持断线续局、思考时间调整和可选 ChessDB 云开局库。

### PST 桌面版

```powershell
pip install pygame
python gui.py
```

### NNUE 引擎协议

```powershell
g++ -O3 -std=c++17 -march=native -DNDEBUG `
  -o trainnnue/nnue_engine.exe trainnnue/nnue_engine.cpp

trainnnue/nnue_engine.exe `
  --nnue trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue `
  --nnue-blend 1
```

引擎通过标准输入输出接受 `ready`、`setboard`、`side`、`time`、`move`、`search`、`forbid` 和 `quit`。

## 部署

将服务器信息写入已忽略的 `deploy/secrets.env`，之后统一运行：

```powershell
deploy\deploy.ps1
```

脚本会同步网页文件、按源码哈希决定是否重编译 PST/NNUE/Pikafish、上传最佳 NNUE 权重、重启 systemd 并检查 HTTP 200。

## 教程

[`slides-formal-web-lite`](slides-formal-web-lite/index.html) 是随仓库提供的交互式教程，覆盖棋盘建模、手工评价、Alpha-Beta/PVS、选择性剪枝以及 NNUE 特征与增量推理。直接用浏览器打开 `index.html` 即可离线阅读。

## 结果边界

当前结论来自固定保留开局和 384 盘配对测试，足以支持本项目的工程验收，但不是大规模 Elo 标定。引擎保留原有重复局面与简化长将判断，尚未实现完整平台级长捉/长杀裁决。
