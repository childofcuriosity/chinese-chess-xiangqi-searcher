# 中国象棋 AI：从规则、评价到搜索与产品化

这是一个从零实现的中国象棋 AI 系统，而不只是一个搜索函数或单独的 NNUE 模型。项目覆盖棋盘与规则建模、增量状态、PST/NNUE 评价、Alpha-Beta 系列搜索、实验工具、桌面与网页交互，以及 Linux 一键部署。

[在线对弈](http://47.102.137.220:8100) · [完整教程](slides-formal-web-lite/index.html) · [运行与配置](docs/RUNNING.md) · [实验设计](docs/EXPERIMENTS.md) · [NNUE 专题](trainnnue/README.md)

## 研究问题

项目围绕一个具体问题展开：**怎样在普通 CPU 和有限思考时间下，做出一个规则正确、能解释、能实验、也能真正交付给用户的中国象棋引擎？**

它可以拆成四个相互依赖的问题：

1. 如何准确表示棋盘、生成着法，并保证每次试走和撤销后状态完全一致？
2. 如何把一个局面压缩成可比较的分数，同时兼顾表达能力与搜索速度？
3. 如何在指数增长的博弈树中，把时间优先花在最可能影响决策的分支上？
4. 如何用可复核实验判断修改是否真的更强，并把同一引擎接入桌面、网页和服务器？

## 系统骨架

根 README 采用 [`slides-formal-web-lite`](slides-formal-web-lite/index.html) 的教学骨架：先让棋走起来，再获得棋感，最后学会向前推演。

### 第一阶段：让棋走起来

核心实现位于 [`xiangqi_ai.cpp`](xiangqi_ai.cpp) 与 [`common.py`](common.py)。

- `board[10][9] + turn` 定义完整局面；大写为红方、小写为黑方。
- 七类棋子分别生成伪合法着，再通过 make → 查将 → undo 过滤成合法着。
- 棋子列表、将帅位置、PST分数、Zobrist hash 和重复历史都随走子增量维护。
- 吃子通过交换补洞保持棋子列表连续；undo 必须精确恢复棋盘和所有派生状态。
- 服务端再次验证人的着法，不能依赖浏览器前端保证规则正确。

这一层的价值不是“棋子终于会动”，而是为搜索、评价和实验提供可逆、可验证的状态机。

### 第二阶段：给局面一点棋感

项目同时保留两条评价路线，便于对照和回归：

- **自研 PST 引擎**：材料价值 + 中残局棋子位置表；走子时只更新起点、终点和被吃子贡献。
- **自研 NNUE 引擎**：在 PST 上叠加轻量神经网络残差；第一层同样通过 make/undo 增量维护，量化后由 CPU 整数推理。

最终 NNUE 是 `XQ-HalfKA-9x14x90 → H16 → CReLU → 阶段输出头`，模型363KB。它是评价模块的升级，不改变项目其他组件的地位。数据生成、训练、量化和比赛细节集中在 [`trainnnue/README.md`](trainnnue/README.md)。

### 第三阶段：向前推演

搜索从 Minimax 骨架逐步扩展为限时的选择性搜索：

- 迭代加深保证超时时仍有上一完整深度的答案。
- Alpha-Beta/PVS、期望窗口与内部迭代加深减少不必要的精确搜索。
- Zobrist hash + 置换表复用相同局面的深度、界类型和最佳着。
- Quiescence Search 与 SEE 降低在激烈交换中截断产生的地平线效应。
- 历史启发、杀手着、MVV-LVA 和 TT move 改善走法顺序。
- LMR、LMP、futility、razoring、reverse futility 和 null move 把预算集中到更可能改变结果的分支；关键失败路径允许重搜。
- 重复局面与简化长将判断直接进入搜索终止条件。

这些技术不是孤立技巧：评价越慢，可完成深度越低；排序越好，Alpha-Beta越有效；剪枝越激进，越需要固定开局和公平 A/B 测试控制风险。

### 工程层：把引擎做成可使用的系统

```text
pygame 桌面端 ─┐
               ├─ common.py / 自定义 stdio 协议 ─ PST 或 NNUE 搜索引擎
FastAPI 网页端 ─┘                 │
        │                         ├─ 本地搜索
        ├─ WebSocket 会话         └─ 可选 ChessDB 云开局库
        └─ 服务端规则校验

实验脚本 ─ 固定/随机开局 ─ 换先对战 ─ JSON结果 ─ 表格/曲线
部署脚本 ─ 上传 ─ 按哈希编译 ─ systemd重启 ─ HTTP验证
```

- [`gui.py`](gui.py)：pygame 桌面端。
- [`webapp.py`](webapp.py) + [`static/index.html`](static/index.html)：多人网页端，每局独立引擎进程，支持断线续局。
- [`pikafish_bridge.py`](pikafish_bridge.py)：在 Pikafish UCI 与本项目 stdio 协议之间转换。
- [`deploy/deploy.ps1`](deploy/deploy.ps1)：同步代码、编译三个引擎、上传 NNUE 模型、重启服务并验证 HTTP。
- [`slides-formal-web-lite`](slides-formal-web-lite/index.html)：从盘面表示一直讲到选择性搜索和 NNUE 的完整交互式教程。

| pygame桌面端 | 引擎计算日志 |
|---:|---:|
| ![桌面端棋盘](开局界面.png) | ![引擎计算日志](计算日志界面.png) |

## 核心发现

1. **正确的增量状态是整个系统的地基。** PST、Zobrist、棋子列表与 NNUE 都依赖 make/undo；任何一项不能精确恢复都会污染整棵搜索树。
2. **搜索优化必须成组理解。** 好的走法排序决定剪枝效率，静态搜索决定叶子质量，时间管理决定深度是否真正可用；单看某个启发式的节点数容易误判。
3. **评价模型必须和搜索预算共同设计。** 更复杂的网络可能降低MSE，却因每节点成本而少完成一层。最终选择 H16 是量化后等时比赛的结果，而不是只看离线损失。
4. **教师越深不一定越适合轻量学生。** 百万级、红黑平衡的 D3/D4 数据比少量更深 D5 标签更适合当前网络容量。
5. **公平实验需要换先、保留开局和成对统计。** 少量从初始局面开始的自对弈只能用于回归，不能支持稳定棋力结论。

## 核心成果（STAR）

| 情境 / 任务 | 我的行动 | 结果 | 可核验入口 |
|---|---|---|---|
| 从零建立可搜索的中国象棋状态机 | 实现着法、查将、终局、增量棋子列表与可逆 make/undo | 规则、评价、哈希和搜索共享同一套状态语义 | `xiangqi_ai.cpp`, `common.py`, `tests/` |
| 在普通CPU的有限时间内提高决策质量 | 组合迭代加深、PVS、TT、QS/SEE、排序、选择性剪枝和时间控制 | 形成完整限时搜索器，并能逐项做回归实验 | `xiangqi_ai.cpp`, 教程第4–5章 |
| PST表达有限，但复杂评价会挤占搜索深度 | 设计HalfKA残差NNUE、整数推理与增量累加器，并用D3→D4课程训练 | 最佳模型对PST的384盘等时得分率59.77% | `trainnnue/`, `direct_match_summary.json` |
| 小样本自对弈容易把先手和开局偏差当成提升 | 建立固定保留开局、逐开局换先、瑞士轮与配对bootstrap流程 | 模型选择同时有离线指标、直接对局和置信区间 | `docs/EXPERIMENTS.md`, `trainnnue/*match*.py` |
| 算法需要成为真正可用的产品 | 接入pygame、FastAPI/WebSocket、Pikafish桥接和ChessDB回退 | 同一规则/协议支持桌面、网页和三种引擎选项 | `gui.py`, `webapp.py`, `static/` |
| 本地成果需要可复现地交付 | 编写PowerShell部署、systemd配置、版本清单和全项目教程 | 可用统一脚本构建、部署、核验模型并复现关键表图 | `deploy/`, `docs/RUNNING.md`, `slides-formal-web-lite/` |

## 已验证结果

- NNUE 增量累加器通过 **822,487** 次随机 make/undo/null/rebuild 转换一致性检查。
- 最佳 D4-H16（D3初始化）量化模型在384盘固定保留开局、逐开局换先、单核等时测试中，对 PST 为 **172胜115和97负，得分率59.77%**，配对95% CI为 **[56.38%, 63.15%]**。
- 同条件直接对 D4-H8 为 **54.17%**，平均完成深度9.18 vs 9.24，说明 H16 的额外评价成本在本实现中可接受。
- 网页端已部署，PST、NNUE 与 Pikafish PST 三个选项走同一会话和规则接口。

关键 NNUE 表格和训练曲线不是手工维护：运行 `python trainnnue/report_results.py` 可由 JSON 结果重新生成 [`RESULTS.generated.md`](trainnnue/RESULTS.generated.md) 和 [`training_curve.svg`](trainnnue/training_curve.svg)。

## 运行与配置

完整环境、模型/数据版本、编译命令、环境变量和部署说明见 [`docs/RUNNING.md`](docs/RUNNING.md)。最短路径：

```powershell
python -m pip install -r requirements.txt
python webapp.py
# http://localhost:8000
```

网页默认选择自研 NNUE；也可切换自研 PST 或 Pikafish PST。桌面端运行 `python gui.py`。

## 核心实验脚本

| 目的 | 命令/入口 | 产物 |
|---|---|---|
| 引擎修改回归 | `python ab_selfplay.py baseline.exe candidate.exe` | 多时间档逐局日志与 `summary.json` |
| 对战 Pikafish | `python cross_arena.py --pairs 10 --seconds 1` | `cross_arena_summary.json` |
| NNUE直接换先赛 | `python trainnnue/engine_match.py ...` | 逐盘JSON与配对CI |
| 8模型瑞士轮 | `python trainnnue/swiss_tournament.py` | `swiss_8models_5rounds.json` |
| 生成关键表/图 | `python trainnnue/report_results.py` | Markdown结果表与SVG学习曲线 |
| 网页/云库测试 | `python -m pytest tests -q` | 单元与WebSocket端到端结果 |

更严格的 A/B 方法和解释边界见 [`AB_SELFPLAY.md`](AB_SELFPLAY.md)。

## 仓库结构

| 路径 | 职责 |
|---|---|
| `xiangqi_ai.cpp` | PST 评价的主搜索引擎 |
| `trainnnue/` | NNUE 数据、训练、量化、验证和比赛专题 |
| `common.py` | 客户端共享规则、云库与引擎进程通信 |
| `gui.py` | pygame 桌面端 |
| `webapp.py`, `static/` | FastAPI/WebSocket 网页端 |
| `selfplay.py`, `ab_selfplay.py`, `cross_arena.py` | 回归与外部引擎实验 |
| `tests/` | 规则、云库、会话与网页端测试 |
| `deploy/` | Linux服务器配置和一键部署 |
| `slides-formal-web-lite/` | 全项目正式教程 |

## 结果与局限

**已经验证：** 当前源码和模型的一致性、量化推理、指定开局与时间控制下 NNUE 对 PST 的优势、网页端三引擎接入与服务器部署。

**仍需扩大验证：** 384盘足以用于本项目工程验收，但不是跨机器、跨时间控制的大样本 Elo 标定；历史“可战胜固定深度7 Pikafish”的观察没有同等级保留开局与置信区间，因此不作为正式结果。

**已知边界：** 引擎实现普通重复局面和简化长将判断，尚未覆盖完整平台级长捉/长杀裁决；达到最大 ply 的对局按实验和棋处理；ChessDB是外部服务，失败时只能自动回退本地搜索；网页采用每局一个进程，默认并发上限16，不是大规模对弈平台架构。
