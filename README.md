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
| `xiangqi_ai.exe` | 编译好的引擎(仓库自带) |
| `common.py` | 棋盘规则 + 引擎进程通信,被 `gui.py` 和 `webapp.py` 共用 |
| `gui.py` | pygame 图形界面,通过 stdio 驱动引擎 |
| `webapp.py` | 网页版后端(FastAPI + WebSocket) |
| `static/index.html` | 网页版前端(canvas 棋盘) |
| `deploy/` | 一键部署脚本(服务器信息在 `secrets.env`,已 gitignore) |
| `tests/` | 网页版端到端测试(7 用例,含真实引擎对弈) |
| `cross_arena.py` | 对战皮卡鱼测试脚本 |
| `pikafish.exe` / `pikafish.nnue` | 皮卡鱼引擎及权重(测试用) |
| `selfplay.py` | 自对弈回归仲裁工具 |
| `simhei.ttf` | 界面字体 |

## 运行

1. 编译引擎(仓库已自带 `xiangqi_ai.exe`,不改引擎代码可跳过此步;需要 MSYS2 UCRT64 的 GCC):

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

## 网页版

浏览器在线对弈:[webapp.py](webapp.py)(FastAPI + WebSocket)+ [static/index.html](static/index.html)(canvas 棋盘)。服务端权威校验走法,每局一个独立引擎进程,多人可同时玩,刷新断线自动续局,手机也能玩。

本地运行:

```bash
pip install fastapi "uvicorn[standard]"
python webapp.py            # 浏览器打开 http://localhost:8000
```

部署到 Linux 服务器(一键脚本,服务器信息在 `deploy/secrets.env`,已被 gitignore 不上传):

```bash
cp deploy/secrets.env.example deploy/secrets.env   # 填入 ssh 别名/IP/端口
bash deploy/deploy.sh                              # 或 PowerShell:
                                                   # powershell -ExecutionPolicy Bypass -File deploy\deploy.ps1
```

脚本自动完成:上传代码 → 引擎源码有变化才 g++ 重编译 → 更新 systemd 服务并重启 → HTTP 验证。并发上限/空闲回收可用环境变量 `XQ_MAX_GAMES` / `XQ_IDLE_TIMEOUT` 调整(见 [webapp.py](webapp.py) 头部注释)。

## 引擎功能

- **搜索**:迭代加深 + PVS + Alpha-Beta 剪枝,置换表(800 万条目)+ Zobrist 哈希,空步裁剪,静态搜索,历史启发 + 杀手启发,MVV-LVA 着法排序
- **评估**:子力价值 + 中局/残局两套棋子位置表(PST,参考象眼)
- **着法生成**:位运算维护行列占位,快速生成与合法性判断

## 引擎协议(stdio)

gui.py / webapp.py 与引擎通过标准输入输出通信:

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

## 对战皮卡鱼

[cross_arena.py](cross_arena.py) 做协议翻译,让 xiangqi_ai.exe 与皮卡鱼对局:

```bash
python cross_arena.py                    # 单局: 我方执红 vs 皮卡鱼深度1
python cross_arena.py --pika-depth 7     # vs 深度7
python cross_arena.py --visualize        # 动态打印棋盘
python cross_arena.py --matrix 7         # 深度矩阵: 皮卡鱼深度1..7, 每档两局互换先手
```

皮卡鱼说 UCI 协议,我方引擎说自家 stdio 协议,脚本负责协议翻译和坐标转换。

## 自对弈测试

两个引擎互相对弈,检测吃王 / 长将 / 步数上限:

```bash
python selfplay.py <红方exe> <黑方exe> [最大步数=200]
```
