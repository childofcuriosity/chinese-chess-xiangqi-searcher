# 实验设计与证据等级

本项目把“代码正确”“性能等价”“棋力更强”和“产品可用”分开验证。一个测试通过，不能自动替代其他层面的证据。

## 1. 四类问题

| 问题 | 首选方法 | 典型产物 |
|---|---|---|
| 状态和规则是否正确？ | 单元测试、随机make/undo一致性、非法着测试 | pytest结果、转换计数 |
| 纯优化是否等价？ | 固定局面/深度比较着法、分数、节点数 | 控制组日志 |
| 评价或搜索修改是否更强？ | 固定开局逐一换先、相同时间、配对统计 | 逐盘JSON、W/D/L、CI |
| 网页与部署是否可用？ | WebSocket端到端、真实引擎进程、HTTP健康检查 | 测试结果、systemd状态 |

## 2. 脚本分工

### `selfplay.py`

最小单局仲裁器。适合快速观察两个 stdio 引擎是否能完整走完一局，不适合作为统计棋力结论。

### `ab_selfplay.py`

在多个时间档并行运行候选版与基线版并交换先后手。适合发现崩溃、异常认输和明显回退。它默认从初始局面开始，因此结果高度相关；解释要求见 [`../AB_SELFPLAY.md`](../AB_SELFPLAY.md)。

### `cross_arena.py`

通过协议桥接让自研引擎与官方 Pikafish 对战，可设置多个时间档和换先组数。它从初始局面启动，主要用于协议与功能回归。

### `trainnnue/engine_match.py`

正式的任意双引擎配对工具：从固定FEN切片读取开局，每个开局交换红黑，记录节点、深度、实际搜索时间，并按开局对 bootstrap。可通过额外进程参数接入官方 Pikafish 桥接器。

### `trainnnue/run_external_match.ps1`

官方 Pikafish NNUE 外部基准流水线。每个分片占用独立 CPU，每盘内双方固定同一逻辑核；结果保存官方二进制、网络和自研模型 SHA-256。前12个开局用于时间倍率与 `UCI_LimitStrength` 档位校准，剩余180个开局用于360盘正式换先赛。

### `trainnnue/swiss_tournament.py`

8模型、5轮瑞士制。配对按累计盘分接近且避免重复对手；每轮4场占用独立CPU并行。瑞士轮用于候选排序，最终第一、第二与PST仍需直接对抗确认。

### `trainnnue/report_results.py`

从模型元数据、离线比较、瑞士轮和直接对抗JSON生成Markdown表和SVG学习曲线。它不重新估计或润色数字，只做确定性汇总。

## 3. 正式对战控制变量

- 双方使用相同搜索实现、编译优化和协议；评价模型是目标变量。
- 192个保留开局不参与训练和开发筛选。
- 每个开局各执红、黑一局，抵消先后手与单一开局偏差。
- 双方每步0.10秒、最长160 ply；对局进程固定CPU。
- 置信区间以开局对为聚类单位，不把换先两盘误当完全独立样本。
- 对局开始前冻结候选；不根据正式测试结果继续调该候选。

外部 Pikafish 比赛额外控制：官方版本为 `Pikafish 2026-01-31`；`Threads=1`、`Ponder=false`、`Move Overhead=0`；自研名义时限0.25秒、Pikafish名义时限0.10秒。该倍率来自12个校准开局，用于适配自研引擎只提交完整迭代深度的停止策略。正式1900档比赛实际平均搜索时间为76.2 / 101.3ms，满强比赛为86.9 / 91.4ms。

## 4. 当前结果

机器可读来源：

- [`../trainnnue/direct_match_summary.json`](../trainnnue/direct_match_summary.json)
- [`../trainnnue/swiss_8models_5rounds.json`](../trainnnue/swiss_8models_5rounds.json)
- [`../trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue.json`](../trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue.json)
- [`../trainnnue/iter1_experiment.json`](../trainnnue/iter1_experiment.json)
- [`../trainnnue/iter2_experiment.json`](../trainnnue/iter2_experiment.json)
- [`../trainnnue/iter3_experiment.json`](../trainnnue/iter3_experiment.json)
- [`../trainnnue/iter2_vs_pikafish_elo1900_180pairs.json`](../trainnnue/iter2_vs_pikafish_elo1900_180pairs.json)
- [`../trainnnue/iter2_vs_pikafish_official_180pairs.json`](../trainnnue/iter2_vs_pikafish_official_180pairs.json)

确定性生成的展示结果：[`../trainnnue/RESULTS.generated.md`](../trainnnue/RESULTS.generated.md)。

正式直接测试中，D4-H16-D3init 对 PST 得分率59.77%，配对95% CI为56.38%–63.15%；对D4-H8-D3init为54.17%，CI为50.26%–58.07%。

官方 Pikafish 外部测试中，Iter2 对内置 `UCI_Elo=1900` 档为169胜68和123负，得分率56.39%，配对95% CI为51.94%–60.83%；对满强版本为6胜44和310负，得分率7.78%，CI为5.69%–10.00%。

第一次教师迭代中，D4-H16-D3init加D3无风险搜索生成新的百万数据。量化学生对原D4-H16得分率60.94%，配对95% CI为57.16%–64.71%；对PST得分率63.28%，CI为59.51%–66.93%。原D4-H16对PST为59.77%，因此本轮没有观察到自举偏差导致的PST退化；该结论不能外推到后续无限迭代。

第二次教师迭代中，教师和初始化都改用Iter1-NNUE-D3，并重新生成一百万条独立数据。Iter2对Iter1得分率55.08%，配对95% CI为51.43%–58.72%；对PST得分率70.18%，CI为66.80%–73.44%。相较Iter1对PST的63.28%继续提高6.90个百分点，因此第二轮仍未观察到自举回退；但两轮结果不能确定渐近上限，也不保证第三轮继续提升。

第三次迭代继续用上一代同时作为教师与初始化。Iter3对Iter2得分率52.86%，CI为49.35%–56.38%；对PST为70.05%，CI为66.67%–73.44%。对PST点估计比Iter2低0.13个百分点，满足预先约定的“第一次点估计回落即停止”规则，因此当前选择Iter2。区间高度重叠，证据只支持“进入平台”，不支持“Iter3真实更弱”的强结论。

单轮完整流水线已固化为 [`../trainnnue/run_teacher_iteration.ps1`](../trainnnue/run_teacher_iteration.ps1)，连续迭代与停止规则由 [`../trainnnue/run_until_regression.ps1`](../trainnnue/run_until_regression.ps1) 执行。每轮保留独立数据、K、checkpoint、量化验证和两组正式比赛。

## 5. 结果解释

- 内部 PST 比赛量化 NNUE 评价升级；官方 Pikafish 比赛提供外部强度坐标。
- `UCI_Elo=1900` 是 Pikafish 内置限强刻度；跨平台等级映射需要对应平台的定级对局。
- 瑞士轮用于候选排序，直接换先赛用于最终模型判断。
- 当前仲裁以160 ply作为实验终止点，后续规则实验将加入完整长捉、长杀裁决。

## 6. 下一步证据

若要给出稳定Elo估计，应预先登记模型与时间控制，扩展到数千盘独立开局对，在不同机器上重复，并补充完整长捉/长杀裁判。任何新调参都应使用新的开发集，不能回看正式保留集继续优化。
