# 引擎修改 A/B 自对弈测试

这套工具用于比较只相差一项修改的两个引擎：`baseline`（修改前）与
`candidate`（修改后）。测试会在多个每步时间档分别换先，并并行运行。

## 1. 构建两个版本

必须保证两个二进制使用完全相同的编译器和参数，唯一差异是待测试修改。
正式测试不要启用 `ENABLE_PROFILING`。

示例编译参数：

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

建议在开始修改前先编译并保留 `baseline.exe`，然后修改源码并编译
`candidate.exe`。不要拿不同优化参数、不同网络或包含其他改动的版本比较。

## 2. 运行并行换先赛

```powershell
python ab_selfplay.py baseline.exe candidate.exe
```

默认设置：

- 每步时间：0.5、0.75、1.0、1.5、2.0 秒；
- 每个时间档两局，候选版与基线版各执红一次；
- 每局最多 160 ply；
- 并行数为逻辑处理器数量减 2。

自定义示例：

```powershell
python ab_selfplay.py baseline.exe candidate.exe `
  --times 0.25,0.5,1,2 `
  --max-plies 200 `
  --repeats 2 `
  --jobs 10 `
  --output ab_results/my_change
```

一局内双方轮流搜索，因此单线程引擎的一局通常只占用一个逻辑处理器。
不要把 `--jobs` 设置得明显高于逻辑处理器数量；墙钟时间控制下，严重超卖
CPU 会增加调度噪声。

## 3. 输出

工具会实时打印每局结果，并在输出目录生成：

- 每局完整对局日志；
- `summary.json`，包含胜和负、候选版得分率、时间档、先后手和日志路径。

候选版得分按以下方式计算：

```text
胜 = 1 分，和 = 0.5 分，负 = 0 分
```

必须同时检查：

- 总胜/和/负；
- 候选执红与执黑的表现；
- 不同时间档是否方向一致；
- 是否有崩溃、超时或异常认输；
- 和棋是否只是达到 `max_plies`。

## 4. 如何解释结果

固定初始局面的引擎通常具有较强确定性。改变时间档可以让迭代加深停在不同
深度，从而产生不同对局，但这些对局仍不是严格独立样本。

因此：

- 少量对局只能用于回归检查和淘汰明显退步；
- `0 胜、若干和、数负` 足以警告该修改不应直接合入；
- 接近 50% 的结果不能证明两者等强；
- 若要估算 Elo，需要随机合法开局、大量换先对局和置信区间；
- 达到最大步数的“和棋”不等同于完整规则裁定的和棋。

性能优化还应额外核对固定局面的节点数、分数和最佳走法。纯等价优化原则上
不应改变节点数；棋力修改则允许改变搜索树，但必须通过对局验证收益。

## 5. 单局工具

`selfplay.py` 仍可单独使用：

```powershell
python selfplay.py red.exe black.exe 160 1.0
```

参数依次为红方引擎、黑方引擎、最大 ply、每步秒数。省略每步秒数时，引擎
使用自身默认时间配置。

