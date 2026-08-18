# 中国象棋 AI

传统搜索算法实现的中国象棋 AI:C++ 引擎 [xiangqi_ai.cpp](xiangqi_ai.cpp) + pygame 图形界面 [gui.py](gui.py)。

自测棋力可战胜固定深度 7 的皮卡鱼。

## 截图

| 开局界面 | 计算日志界面 |
| :---: | :---: |
| ![开局界面](开局界面.png) | ![计算日志界面](计算日志界面.png) |

## 目录结构

| 文件 | 说明 |
| :--- | :--- |
| `xiangqi_ai.cpp` | C++ 引擎源码(核心) |
| `gui.py` | pygame 图形界面,通过 stdio 驱动引擎 |
| `selfplay.py` | 自对弈回归仲裁工具 |
| `simhei.ttf` | 界面字体 |

## 运行

1. 编译引擎(需要 MSYS2 UCRT64 的 GCC):

   ```bash
   g++ -O3 -std=c++17 -march=native -DNDEBUG \
       -fno-exceptions -fno-rtti \
       -static -static-libgcc -static-libstdc++ \
       -o xiangqi_ai.exe xiangqi_ai.cpp
   ```

   `-static*` 是必须的:gui.py 用 subprocess 启动引擎时不带 MSYS2 的 PATH,动态链接的 DLL 找不到会静默启动失败。

2. 安装界面依赖:

   ```bash
   pip install pygame
   ```

3. 运行:

   ```bash
   python gui.py
   ```

## 引擎功能

- **搜索**:迭代加深 + PVS + Alpha-Beta 剪枝,置换表(800 万条目)+ Zobrist 哈希,空步裁剪,静态搜索,历史启发 + 杀手启发,MVV-LVA 着法排序
- **评估**:子力价值 + 中局/残局两套棋子位置表(PST,参考象眼)
- **着法生成**:位运算维护行列占位,快速生成与合法性判断

## 引擎协议(stdio)

gui.py 与引擎通过标准输入输出通信:

| 命令 | 说明 |
| :--- | :--- |
| `ready` | 引擎回复 `readyok` |
| `side red` / `side black` | 设置**人类**执子方,引擎自动执相反色。注意:`side black` 表示引擎执红 |
| `setboard <FEN>` | 设置局面 |
| `move r1 c1 r2 c2` | 告知引擎对手的着法 |
| `forbid r1 c1 r2 c2` | 设置禁手 |
| `search` | 引擎思考并走自己一步,输出 `move r1 c1 r2 c2` 或 `resign` |
| `print` | 输出当前棋盘 |
| `quit` | 退出 |

## 自对弈测试

两个引擎互相对弈,检测吃王 / 长将 / 步数上限:

```bash
python selfplay.py <红方exe> <黑方exe> [最大步数=200]
```
