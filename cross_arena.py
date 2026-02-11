#!/usr/bin/env python3
import subprocess
import sys
import time
import argparse
import os

# --- 配置 ---
PYTHON_EXEC = 'python'    # Windows下通常是python，如果安装了pypy3请改为 'pypy3'
PIKAFISH_EXEC = './pikafish.exe' # 请确保路径正确
MAX_MOVES = 200           # 最大回合数

# --- 坐标转换工具 (保持不变) ---
def xy_to_uci(r1, c1, r2, c2):
    # AI坐标: r0-9(上到下), c0-8(左到右)
    # UCI坐标: rank0-9(下到上), file a-i(左到右)
    f1 = chr(ord('a') + c1)
    rank1 = str(9 - r1)
    f2 = chr(ord('a') + c2)
    rank2 = str(9 - r2)
    return f"{f1}{rank1}{f2}{rank2}"

def uci_to_xy(uci_str):
    if not uci_str or len(uci_str) < 4: return 0,0,0,0
    c1 = ord(uci_str[0]) - ord('a')
    r1 = 9 - int(uci_str[1])
    c2 = ord(uci_str[2]) - ord('a')
    r2 = 9 - int(uci_str[3])
    return r1, c1, r2, c2

# --- 棋盘逻辑 (保持不变) ---
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

# --- 增强的引擎封装 (修复 Windows Error 22) ---

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

    def close(self):
        if self.process:
            # 1. 尝试发送 quit
            self.send("quit")
            
            # 2. 关闭流，防止 ResourceWarning 和 Errno 22
            try:
                if self.process.stdin: self.process.stdin.close()
                if self.process.stdout: self.process.stdout.close()
            except (OSError, ValueError):
                pass
            
            # 3. 终止进程并等待
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None

class MyAIEngine(BaseEngine):
    def __init__(self, script_path, depth):
        super().__init__([PYTHON_EXEC, script_path, str(depth)])

class PikafishEngine(BaseEngine):
    def __init__(self, exec_path, depth):
        super().__init__([exec_path])
        self.depth = depth

    def initialize(self):
        self.send("uci")
        # 简单等待 uciok，防止死锁
        start = time.time()
        while time.time() - start < 5:
            line = self.read()
            if line and "uciok" in line: break
        
        self.send("isready")
        start = time.time()
        while time.time() - start < 5:
            line = self.read()
            if line and "readyok" in line: break

    def get_move(self, history_moves):
        # 构建 moves 字符串
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

# def play_game(my_ai_depth, pika_depth, my_ai_is_red):
#     board = ArenaBoard()
    
#     # 检查文件是否存在
#     if not os.path.exists('ai.py'):
#         print("错误: 找不到 ai.py")
#         return 'error'
#     if not os.path.exists(PIKAFISH_EXEC):
#         print(f"错误: 找不到 {PIKAFISH_EXEC}")
#         return 'error'

#     my_ai = MyAIEngine('ai.py', my_ai_depth)
#     pika = PikafishEngine(PIKAFISH_EXEC, pika_depth)
    
#     try:
#         my_ai.start()
#         pika.start()
#         pika.initialize() # 皮卡鱼需要初始化 UCI

#         # 初始化 MyAI
#         if my_ai_is_red:
#             my_ai.send("side black")
#             current_turn = 'my_ai'
#         else:
#             my_ai.send("side red")
#             current_turn = 'pika'

#         move_history_uci = []
#         winner = None
#         moves_count = 0

#         while moves_count < MAX_MOVES:
#             # 1. 判据
#             status = board.is_game_over()
#             if status == 'red_win':
#                 winner = 'my_ai' if my_ai_is_red else 'pika'
#                 break
#             elif status == 'black_win':
#                 winner = 'pika' if my_ai_is_red else 'my_ai'
#                 break

#             move_uci = ""
#             r1, c1, r2, c2 = 0, 0, 0, 0

#             # 2. 走棋
#             if current_turn == 'my_ai':
#                 my_ai.send("search")
#                 # 读取直到获取 move 指令 (忽略 debug 信息)
#                 while True:
#                     resp = my_ai.read()
#                     if not resp: break # 进程死了
#                     if resp.startswith('move') or resp.startswith('resign'): break
                
#                 if not resp or 'resign' in resp:
#                     winner = 'pika'
#                     break
                
#                 parts = resp.split()
#                 if parts[0] == 'move':
#                     try:
#                         r1, c1, r2, c2 = map(int, parts[1:5])
#                         move_uci = xy_to_uci(r1, c1, r2, c2)
#                     except:
#                         winner = 'pika'; break
#                 else:
#                     winner = 'pika'; break
            
#             else:
#                 # Pika turn
#                 move_uci = pika.get_move(move_history_uci)
#                 if not move_uci or move_uci == '(none)' or move_uci == '0000':
#                     winner = 'my_ai'
#                     break
#                 r1, c1, r2, c2 = uci_to_xy(move_uci)
            
#             # 3. 执行 & 记录
#             board.move(r1, c1, r2, c2)
#             move_history_uci.append(move_uci)

#             # 4. 同步
#             if current_turn == 'pika':
#                 my_ai.send(f"move {r1} {c1} {r2} {c2}")

#             current_turn = 'pika' if current_turn == 'my_ai' else 'my_ai'
#             moves_count += 1
            
#             # 简单的进度显示
#             # print(f".", end="", flush=True)

#         if not winner: winner = 'draw'

#     except KeyboardInterrupt:
#         print("\n用户中断")
#         sys.exit(0)
#     except Exception as e:
#         print(f"\nGame Error: {e}")
#         winner = 'draw'
#     finally:
#         # 确保无论如何都关闭进程
#         my_ai.close()
#         pika.close()

#     return winner
def play_game(my_ai_depth, pika_depth, my_ai_is_red, visualize=False):
    """
    visualize: 如果为 True，将在命令行动态打印棋盘
    """
    board = ArenaBoard()
    
    # 简单的检查
    if not os.path.exists('ai.py'):
        print("错误: 找不到 ai.py")
        return 'error'
    if not os.path.exists(PIKAFISH_EXEC):
        print(f"错误: 找不到 {PIKAFISH_EXEC}")
        return 'error'

    my_ai = MyAIEngine('ai.py', my_ai_depth)
    pika = PikafishEngine(PIKAFISH_EXEC, pika_depth)
    
    try:
        my_ai.start()
        pika.start()
        pika.initialize() # 皮卡鱼初始化

        # --- 用户指定的逻辑修正 ---
        # 如果 MyAI 是红方(先手)，告诉它对手是 Black (或者它自己是Red，取决于你ai.py的协议定义，这里按你要求改)
        if my_ai_is_red:
            my_ai.send("side black") 
            current_turn = 'my_ai'
        else:
            my_ai.send("side red")
            current_turn = 'pika'
        # ------------------------

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
                # 清屏 (Windows用cls, Mac/Linux用clear)
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"=== Round {moves_count + 1} ===")
                print(f"Who: {'MyAI' if current_turn == 'my_ai' else 'Pikafish'} | Move: {xy_to_uci(r1,c1,r2,c2)}")
                print("   0 1 2 3 4 5 6 7 8")
                print("  " + "-" * 19)
                for r_idx, row in enumerate(board.board):
                    line_str = " ".join(row)
                    # 简单高亮最后一步的落子点 (可选)
                    # line_str = line_str.replace(row[c2], f"[{row[c2]}]") 
                    print(f"{r_idx} |{line_str}|")
                print("  " + "-" * 19)
                time.sleep(0.5) # 暂停0.5秒让你看清楚
            # ------------------

            # 4. 同步给对方
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_ai_depth', type=int, default=3)
    parser.add_argument('--max_pika_depth', type=int, default=3)
    args = parser.parse_args()

    # 表头
    pika_depths = list(range(1, args.max_pika_depth + 1))
    ai_depths = list(range(1, args.max_ai_depth + 1))

    print(f"=== AI(1-{args.max_ai_depth}) vs Pikafish(1-{args.max_pika_depth}) Matrix ===")
    print("Scores: 1 (AI win 2/2 or big advantage), 0 (Draw/Even), -1 (AI lose)")
    
    # 打印列标题
    header = "AI\\PF | " + " | ".join([f"D{d}" for d in pika_depths])
    print(header)
    print("-" * len(header))

    for ai_d in ai_depths:
        row_str = f" D{ai_d:<4} | "
        for pika_d in pika_depths:
            # 局 1: AI 红
            res1 = play_game(ai_d, pika_d, True)
            # 局 2: AI 黑
            res2 = play_game(ai_d, pika_d, False)

            # 计算分数
            score = 0
            if res1 == 'my_ai': score += 1
            elif res1 == 'draw': score += 0.5
            
            if res2 == 'my_ai': score += 1
            elif res2 == 'draw': score += 0.5
            
            # 格式化
            if score > 1: cell = " 1 "
            elif score < 1: cell = "-1 "
            else: cell = " 0 "

            row_str += f"{cell} | "
            sys.stdout.flush() # 刷新缓冲区
        print(row_str)

# if __name__ == "__main__":
#     main()
if __name__ == "__main__":
    # 单局测试模式：MyAI深度3 vs 皮卡鱼深度1，MyAI执红，开启可视化
    print("开始可视化测试...")
    result = play_game(my_ai_depth=3, pika_depth=1, my_ai_is_red=True, visualize=True)
    print(f"测试结束，获胜者: {result}")
    
    # 原来的代码先注释掉...
    # main()