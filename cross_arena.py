#!/usr/bin/env python3
"""
cross_arena.py
xiangqi_ai.exe vs 皮卡鱼 对战测试。

我方引擎说自家 stdio 协议 (ready/side/move/search),
皮卡鱼说 UCI (uci/isready/position/go), 本脚本做协议翻译和坐标转换。

用法:
  python cross_arena.py                          # 单局: 我方执红 vs 皮卡鱼深度1
  python cross_arena.py --pika-depth 7           # 单局: vs 深度7
  python cross_arena.py --visualize              # 单局: 动态打印棋盘
  python cross_arena.py --matrix 7               # 深度矩阵: 皮卡鱼深度1..7, 每档两局互换先手
"""
import subprocess
import sys
import time
import argparse
import os

# --- 配置 ---
MY_EXE = './xiangqi_ai.exe'      # 我方引擎 (先编译 xiangqi_ai.cpp)
PIKAFISH_EXEC = './pikafish.exe' # 皮卡鱼 (同目录需有 pikafish.nnue)
MAX_MOVES = 200                  # 最大回合数

# --- 坐标转换: 我方(r,c) ↔ UCI(file+rank) ---
def xy_to_uci(r1, c1, r2, c2):
    # 我方坐标: r0-9(上到下), c0-8(左到右)
    # UCI坐标: rank0-9(下到上), file a-i(左到右)
    f1 = chr(ord('a') + c1)
    rank1 = str(9 - r1)
    f2 = chr(ord('a') + c2)
    rank2 = str(9 - r2)
    return f"{f1}{rank1}{f2}{rank2}"

def uci_to_xy(uci_str):
    if not uci_str or len(uci_str) < 4: return 0, 0, 0, 0
    c1 = ord(uci_str[0]) - ord('a')
    r1 = 9 - int(uci_str[1])
    c2 = ord(uci_str[2]) - ord('a')
    r2 = 9 - int(uci_str[3])
    return r1, c1, r2, c2

# --- 棋盘逻辑 (判断吃王) ---
class ArenaBoard:
    def __init__(self):
        self.board = [
            ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
            ['.', '.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', 'c', '.', '.', '.', '.', '.', 'c', '.'],
            ['p', '.', 'p', '.', 'p', '.', 'p', '.', 'p'],
            ['.', '.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.', '.'],
            ['P', '.', 'P', '.', 'P', '.', 'P', '.', 'P'],
            ['.', 'C', '.', '.', '.', '.', '.', 'C', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.', '.'],
            ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R']
        ]

    def move(self, r1, c1, r2, c2):
        if not (0<=r1<10 and 0<=c1<9 and 0<=r2<10 and 0<=c2<9): return None
        captured = self.board[r2][c2]
        self.board[r2][c2] = self.board[r1][c1]
        self.board[r1][c1] = '.'
        return captured

    def is_game_over(self):
        red_k = False
        black_k = False
        for r in range(10):
            for c in range(9):
                p = self.board[r][c]
                if p == 'K': red_k = True
                if p == 'k': black_k = True
        if not red_k: return 'black_win'
        if not black_k: return 'red_win'
        return None

# --- 引擎封装 ---
class BaseEngine:
    def __init__(self, cmd_list):
        self.cmd = cmd_list
        self.process = None

    def start(self):
        try:
            # 使用 utf-8 避免 cp936 编码错误
            self.process = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding='utf-8',
                bufsize=1
            )
        except Exception as e:
            print(f"无法启动引擎 {self.cmd}: {e}")
            sys.exit(1)

    def send(self, msg):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(msg + "\n")
                self.process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def read(self):
        if self.process and self.process.poll() is None:
            try:
                return self.process.stdout.readline().strip()
            except (OSError, ValueError):
                return None
        return None

    def wait_for(self, token, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            line = self.read()
            if line and token in line:
                return line
        return None

    def close(self):
        if self.process:
            self.send("quit")
            try:
                if self.process.stdin: self.process.stdin.close()
                if self.process.stdout: self.process.stdout.close()
            except (OSError, ValueError):
                pass
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None

class XqEngine(BaseEngine):
    """我方 C++ 引擎, 协议: ready/side/move/search/quit"""
    def __init__(self):
        super().__init__([os.path.abspath(MY_EXE)])

    def initialize(self):
        self.send("ready")
        return self.wait_for("readyok")

class PikafishEngine(BaseEngine):
    def __init__(self, exec_path, depth):
        super().__init__([os.path.abspath(exec_path)])
        self.depth = depth

    def initialize(self):
        self.send("uci")
        if not self.wait_for("uciok"):
            return False
        self.send("isready")
        return self.wait_for("readyok") is not None

    def get_move(self, history_moves):
        moves_str = " ".join(history_moves)
        self.send(f"position startpos moves {moves_str}")
        self.send(f"go depth {self.depth}")

        best_move = None
        while True:
            line = self.read()
            if not line: break
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    best_move = parts[1]
                break
        return best_move

# --- 对战逻辑 ---
def play_game(pika_depth, my_ai_is_red, visualize=False):
    """
    visualize: 如果为 True，将在命令行动态打印棋盘
    """
    board = ArenaBoard()

    # 简单的检查
    if not os.path.exists(MY_EXE):
        print("错误: 找不到 xiangqi_ai.exe (先编译 xiangqi_ai.cpp)")
        return 'error'
    if not os.path.exists(PIKAFISH_EXEC):
        print(f"错误: 找不到 {PIKAFISH_EXEC}")
        return 'error'

    my_ai = XqEngine()
    pika = PikafishEngine(PIKAFISH_EXEC, pika_depth)

    try:
        my_ai.start()
        pika.start()
        if not pika.initialize():
            print("皮卡鱼初始化失败")
            return 'error'
        if not my_ai.initialize():
            print("xiangqi_ai 初始化失败")
            return 'error'

        # side 语义: 给"人类方", 引擎执反色
        # 我方执红 -> 人类执黑 -> side black
        if my_ai_is_red:
            my_ai.send("side black")
            current_turn = 'my_ai'
        else:
            my_ai.send("side red")
            current_turn = 'pika'

        move_history_uci = []
        winner = None
        moves_count = 0

        while moves_count < MAX_MOVES:
            # 1. 判胜负
            status = board.is_game_over()
            if status == 'red_win':
                winner = 'my_ai' if my_ai_is_red else 'pika'
                break
            elif status == 'black_win':
                winner = 'pika' if my_ai_is_red else 'my_ai'
                break

            move_uci = ""
            r1, c1, r2, c2 = 0, 0, 0, 0

            # 2. 获取招法
            if current_turn == 'my_ai':
                my_ai.send("search")
                while True:
                    resp = my_ai.read()
                    if not resp: break
                    if resp.startswith('move') or resp.startswith('resign'): break

                if not resp or 'resign' in resp:
                    winner = 'pika'; break

                parts = resp.split()
                if parts[0] == 'move':
                    try:
                        r1, c1, r2, c2 = map(int, parts[1:5])
                        move_uci = xy_to_uci(r1, c1, r2, c2)
                    except:
                        winner = 'pika'; break
                else:
                    winner = 'pika'; break

            else:
                # 皮卡鱼
                move_uci = pika.get_move(move_history_uci)
                if not move_uci or move_uci == '(none)' or move_uci == '0000':
                    winner = 'my_ai'
                    break
                r1, c1, r2, c2 = uci_to_xy(move_uci)

            # 3. 执行移动
            board.move(r1, c1, r2, c2)
            move_history_uci.append(move_uci)

            # --- 可视化输出 ---
            if visualize:
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"=== Round {moves_count + 1} ===")
                print(f"Who: {'XqAI' if current_turn == 'my_ai' else 'Pikafish'} | Move: {xy_to_uci(r1,c1,r2,c2)}")
                print("   0 1 2 3 4 5 6 7 8")
                print("  " + "-" * 19)
                for r_idx, row in enumerate(board.board):
                    line_str = " ".join(row)
                    print(f"{r_idx} |{line_str}|")
                print("  " + "-" * 19)
                time.sleep(0.5)
            # ------------------

            # 4. 同步给我方引擎
            if current_turn == 'pika':
                my_ai.send(f"move {r1} {c1} {r2} {c2}")

            # 切换回合
            current_turn = 'pika' if current_turn == 'my_ai' else 'my_ai'
            moves_count += 1

        if not winner: winner = 'draw'

    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\nGame Error: {e}")
        winner = 'draw'
    finally:
        my_ai.close()
        pika.close()

    return winner

def main():
    parser = argparse.ArgumentParser(description="xiangqi_ai.exe vs 皮卡鱼对战测试")
    parser.add_argument('--pika-depth', type=int, default=1, help='皮卡鱼搜索深度 (单局模式, 默认1)')
    parser.add_argument('--matrix', type=int, default=0, help='深度矩阵: 皮卡鱼深度1..N, 每档两局互换先手')
    parser.add_argument('--visualize', action='store_true', help='单局模式: 动态打印棋盘')
    args = parser.parse_args()

    if args.matrix:
        print(f"=== xiangqi_ai vs Pikafish(1-{args.matrix}) Matrix ===")
        for d in range(1, args.matrix + 1):
            res1 = play_game(d, True)   # 我方执红
            res2 = play_game(d, False)  # 我方执黑
            score = 0
            for r in (res1, res2):
                if r == 'my_ai': score += 1
                elif r == 'draw': score += 0.5
            print(f"Pika D{d}: 得分 {score}/2  (红: {res1}, 黑: {res2})")
    else:
        print(f"单局: xiangqi_ai vs Pikafish 深度{args.pika_depth}, 我方执红")
        result = play_game(args.pika_depth, True, visualize=args.visualize)
        print(f"获胜者: {result}")

if __name__ == "__main__":
    main()
