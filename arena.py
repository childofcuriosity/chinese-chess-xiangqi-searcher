#!/usr/bin/env python3
import subprocess
import sys
import threading
import queue
import time
import argparse

# --- 配置 ---
# 如果你安装了 pypy3，建议这里填 'pypy3'，否则填 'python'
PYTHON_EXEC = 'pypy3' 
MAX_MOVES = 200  # 超过这个回合数算和棋 (防止死循环)

# 棋盘辅助，用于判断将军死/吃老将
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
        """执行移动并返回被吃掉的棋子(如果没有则是'.')"""
        captured = self.board[r2][c2]
        piece = self.board[r1][c1]
        self.board[r2][c2] = piece
        self.board[r1][c1] = '.'
        return captured

    def is_game_over(self):
        """简单判断：如果帅/将没了，游戏结束"""
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

class EngineProcess:
    def __init__(self, cmd, name):
        self.name = name
        self.cmd = cmd
        self.process = None
        self.alive = False

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, # 忽略 stderr 防止刷屏
                text=True,
                bufsize=1
            )
            self.alive = True
        except FileNotFoundError:
            print(f"Error: 找不到执行命令 {self.cmd}")
            sys.exit(1)

    def send(self, msg):
        if self.alive:
            try:
                self.process.stdin.write(msg + "\n")
                self.process.stdin.flush()
            except BrokenPipeError:
                self.alive = False

    def read_line(self):
        if not self.alive: return None
        try:
            return self.process.stdout.readline().strip()
        except Exception:
            self.alive = False
            return None

    def close(self):
        if self.alive:
            self.send("quit")
            self.process.terminate()
            self.alive = False

def play_one_game(red_engine_cmd, black_engine_cmd, game_id,depth_limit):
    """
    进行一局游戏
    red_engine_cmd: 红方引擎命令 (列表)
    black_engine_cmd: 黑方引擎命令 (列表)
    """
    board = ArenaBoard()
    
    # 启动引擎
    p_red = EngineProcess(red_engine_cmd, "RED")
    p_black = EngineProcess(black_engine_cmd, "BLACK")
    
    p_red.start()
    p_black.start()

    # 初始化阵营
    p_red.send("side red")
    p_black.send("side black")
    
    # 稍微等待初始化
    time.sleep(0.1)

    turn = 'red'
    move_count = 0
    winner = None
    result_reason = ""

    print(f"Game {game_id} Start: {red_engine_cmd[1]} (Red) vs {black_engine_cmd[1]} (Black)")
    while move_count < MAX_MOVES:
        current_p = p_red if turn == 'red' else p_black
        opponent_p = p_black if turn == 'red' else p_red
        
        # 1. 告诉当前方：开始思考
        current_p.send("search")
        
        # 2. 读取招法
        resp = current_p.read_line()
        if resp=='ready':
            resp = current_p.read_line()
        
        if not resp:
            winner = 'black' if turn == 'red' else 'red'
            result_reason = f"{turn} engine crashed"
            break
            
        parts = resp.split()
        if not parts: continue

        if parts[0] == 'resign':
            winner = 'black' if turn == 'red' else 'red'
            result_reason = f"{turn} resigned"
            break
        
        if parts[0] == 'move':
            try:
                r1, c1, r2, c2 = map(int, parts[1:5])
            except ValueError:
                winner = 'black' if turn == 'red' else 'red'
                result_reason = f"{turn} sent invalid format: {resp}"
                break
            
            # 3. 在内部棋盘执行移动，检查是否吃将
            captured = board.move(r1, c1, r2, c2)
            
            # 检查胜负 (被吃的是将帅)
            game_status = board.is_game_over()
            if game_status == 'red_win':
                winner = 'red'; result_reason = "King captured"
                break
            elif game_status == 'black_win':
                winner = 'black'; result_reason = "King captured"
                break

            # 4. 把招法发送给对方
            opponent_p.send(f"move {r1} {c1} {r2} {c2}")

            # 切换回合
            turn = 'black' if turn == 'red' else 'red'
            move_count += 1
        else:
            # 未知指令，判负
            winner = 'black' if turn == 'red' else 'red'
            result_reason = f"Unknown command from {turn}: {resp}"
            break

    p_red.close()
    p_black.close()

    if winner is None:
        return 'draw', f"Max moves {MAX_MOVES} reached"
    
    return winner, result_reason

def main():
    parser = argparse.ArgumentParser(description="Xiangqi AI Arena")
    parser.add_argument('--new', default='ai.py', help='New AI file path')
    parser.add_argument('--old', default='aiold.py', help='Old AI file path')
    parser.add_argument('--games', type=int, default=10, help='Number of games to play')
    parser.add_argument('--max_depth_limit', type=int, default=6, help='Max depth limit for engines')
    args = parser.parse_args()


    stats = {
        'new_win': 0,
        'old_win': 0,
        'draw': 0
    }
    for depth_limit in range(1, args.max_depth_limit+1):
        print(f"Depth Limit {depth_limit} Test Start")
        print(f"=== 开始对战: {args.new} vs {args.old} ===")
        print(f"总场次: {args.games}, 换边策略: 每局轮换")
        print("-" * 50)
        engine_new = [PYTHON_EXEC, args.new, str(depth_limit)]
        engine_old = [PYTHON_EXEC, args.old,   str(depth_limit)]

        for i in range(1, args.games + 1):
            # 轮流执红
            if i % 2 != 0:
                # 奇数局: New(红) vs Old(黑)
                red_cmd = engine_new
                black_cmd = engine_old
                p1_label = "NEW"
                p2_label = "OLD"
            else:
                # 偶数局: Old(红) vs New(黑)
                red_cmd = engine_old
                black_cmd = engine_new
                p1_label = "OLD"
                p2_label = "NEW"

            winner, reason = play_one_game(red_cmd, black_cmd, i,depth_limit)

            # 统计结果
            final_res = "DRAW"
            if winner == 'red':
                if p1_label == "NEW":
                    stats['new_win'] += 1
                    final_res = "NEW WIN"
                else:
                    stats['old_win'] += 1
                    final_res = "OLD WIN"
            elif winner == 'black':
                if p2_label == "NEW":
                    stats['new_win'] += 1
                    final_res = "NEW WIN"
                else:
                    stats['old_win'] += 1
                    final_res = "OLD WIN"
            else:
                stats['draw'] += 1

            print(f"Result: {final_res} ({reason})")
            print(f"Current Score -> NEW: {stats['new_win']} | OLD: {stats['old_win']} | DRAW: {stats['draw']}")
            print("-" * 50)

    # 最终总结
    total = args.games
    new_rate = (stats['new_win'] / total) * 100
    old_rate = (stats['old_win'] / total) * 100
    draw_rate = (stats['draw'] / total) * 100
    
    print("\n=== 最终结果 ===")
    print(f"AI (New): {stats['new_win']} ({new_rate:.1f}%)")
    print(f"AI (Old): {stats['old_win']} ({old_rate:.1f}%)")
    print(f"Draws   : {stats['draw']} ({draw_rate:.1f}%)")

    if stats['new_win'] > stats['old_win']:
        print("结论: 新版 AI 更强！")
    elif stats['old_win'] > stats['new_win']:
        print("结论: 旧版 AI 更强（或者新版有 Bug）。")
    else:
        print("结论: 势均力敌。")

if __name__ == "__main__":
    main()


# === 最终结果 ===
# AI (New): 4 (200.0%)
# AI (Old): 7 (350.0%)
# Draws   : 3 (150.0%)
# 结论: 旧版 AI 更强（或者新版有 Bug）。