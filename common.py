#!/usr/bin/env python3
"""
common.py
棋盘规则 (LocalBoard) 与引擎进程通信 (EngineClient)。
被 gui.py (pygame 桌面版) 和 webapp.py (网页版) 共用。
本模块不依赖 pygame，可在服务器上直接 import。
"""

import subprocess
import threading
import queue

ROWS = 10
COLS = 9

PIECE_CHARS = {
    'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅', 'C': '炮', 'P': '兵',
    'r': '车', 'n': '马', 'b': '象', 'a': '士', 'k': '将', 'c': '炮', 'p': '卒',
    '.': '．'
}


# --- 简单的本地 Board 类 ---
class LocalBoard:
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
        self.turn = 'red'

    def move(self, r1, c1, r2, c2):
        p = self.board[r1][c1]
        self.board[r2][c2] = p
        self.board[r1][c1] = '.'
        self.turn = 'black' if self.turn == 'red' else 'red'

    def is_red(self, p):
        return p.isupper()

    def in_board(self, r, c):
        return 0 <= r < ROWS and 0 <= c < COLS

    # ------------------------------------------------------------------
    # 走法生成（从 ai.py 移植，完整规则）
    # ------------------------------------------------------------------
    def get_valid_moves(self, r, c):
        """返回 (r, c) 处棋子所有合法目标格列表，不含送将步。"""
        piece = self.board[r][c]
        if piece == '.':
            return []
        is_red_piece = self.is_red(piece)
        raw = self._pseudo_moves(r, c, piece, is_red_piece)
        # 过滤送将
        legal = []
        for nr, nc in raw:
            captured = self.board[nr][nc]
            self.board[nr][nc] = piece
            self.board[r][c] = '.'
            if not self._is_in_check(is_red_piece):
                legal.append((nr, nc))
            self.board[r][c] = piece
            self.board[nr][nc] = captured
        return legal

    def _pseudo_moves(self, r, c, piece, is_red_piece):
        moves = []

        def is_teammate(nr, nc):
            p = self.board[nr][nc]
            return p != '.' and self.is_red(p) == is_red_piece

        lp = piece.lower()

        # 车
        if lp == 'r':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                while self.in_board(nr, nc):
                    if self.board[nr][nc] == '.':
                        moves.append((nr, nc))
                    else:
                        if not is_teammate(nr, nc):
                            moves.append((nr, nc))
                        break
                    nr, nc = nr+dr, nc+dc

        # 马
        elif lp == 'n':
            for dr, dc, lr, lc in [(-2,-1,-1,0),(-2,1,-1,0),(2,-1,1,0),(2,1,1,0),
                                    (-1,-2,0,-1),(1,-2,0,-1),(-1,2,0,1),(1,2,0,1)]:
                nr, nc, legr, legc = r+dr, c+dc, r+lr, c+lc
                if (self.in_board(nr, nc) and self.in_board(legr, legc)
                        and self.board[legr][legc] == '.' and not is_teammate(nr, nc)):
                    moves.append((nr, nc))

        # 炮
        elif lp == 'c':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                platform = False
                while self.in_board(nr, nc):
                    if self.board[nr][nc] == '.':
                        if not platform:
                            moves.append((nr, nc))
                    else:
                        if not platform:
                            platform = True
                        else:
                            if not is_teammate(nr, nc):
                                moves.append((nr, nc))
                            break
                    nr, nc = nr+dr, nc+dc

        # 相/象
        elif lp == 'b':
            for dr, dc, er, ec in [(-2,-2,-1,-1),(-2,2,-1,1),(2,-2,1,-1),(2,2,1,1)]:
                nr, nc, er, ec = r+dr, c+dc, r+er, c+ec
                if self.in_board(nr, nc) and self.board[er][ec] == '.' and not is_teammate(nr, nc):
                    if (is_red_piece and nr >= 5) or (not is_red_piece and nr <= 4):
                        moves.append((nr, nc))

        # 士/仕
        elif lp == 'a':
            for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nr, nc = r+dr, c+dc
                if self.in_board(nr, nc) and 3 <= nc <= 5 and not is_teammate(nr, nc):
                    if (is_red_piece and 7 <= nr <= 9) or (not is_red_piece and 0 <= nr <= 2):
                        moves.append((nr, nc))

        # 帅/将
        elif lp == 'k':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                if self.in_board(nr, nc) and 3 <= nc <= 5 and not is_teammate(nr, nc):
                    if (is_red_piece and 7 <= nr <= 9) or (not is_red_piece and 0 <= nr <= 2):
                        moves.append((nr, nc))
            # 飞将
            direction = -1 if is_red_piece else 1
            check_r = r + direction
            while 0 <= check_r < ROWS:
                tp = self.board[check_r][c]
                if tp != '.':
                    enemy_king = 'k' if is_red_piece else 'K'
                    if tp == enemy_king:
                        moves.append((check_r, c))
                    break
                check_r += direction

        # 兵/卒
        elif lp == 'p':
            dr = -1 if is_red_piece else 1
            if self.in_board(r+dr, c) and not is_teammate(r+dr, c):
                moves.append((r+dr, c))
            if (is_red_piece and r <= 4) or (not is_red_piece and r >= 5):
                for dc in [-1, 1]:
                    if self.in_board(r, c+dc) and not is_teammate(r, c+dc):
                        moves.append((r, c+dc))

        return moves

    def _find_king(self, is_red_king):
        target = 'K' if is_red_king else 'k'
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == target:
                    return r, c
        return None

    def _is_in_check(self, is_red_turn):
        """判断 is_red_turn 方是否被将军（在伪走法过滤中调用）。"""
        kp = self._find_king(is_red_turn)
        if not kp:
            return True
        kr, kc = kp

        # 车/将 / 炮 扫描
        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
            nr, nc = kr+dr, kc+dc
            first = None
            while self.in_board(nr, nc):
                p = self.board[nr][nc]
                if p != '.':
                    if first is None:
                        first = p
                        if self.is_red(p) != is_red_turn and p.lower() in ('r','k'):
                            return True
                    else:
                        if self.is_red(p) != is_red_turn and p.lower() == 'c':
                            return True
                        break
                nr, nc = nr+dr, nc+dc

        # 马 (已修正马腿相对于老将的偏移量)
        for dr, dc, lr, lc in[(-2,-1,-1,-1), (-2,1,-1,1), (2,-1,1,-1), (2,1,1,1),
                               (-1,-2,-1,-1), (1,-2,1,-1), (-1,2,-1,1), (1,2,1,1)]:
            nr, nc, legr, legc = kr+dr, kc+dc, kr+lr, kc+lc
            if self.in_board(nr, nc) and self.in_board(legr, legc):
                p = self.board[nr][nc]
                if p != '.' and self.is_red(p) != is_red_turn and p.lower() == 'n':
                    if self.board[legr][legc] == '.':
                        return True

        # 兵/卒
        pawn_char = 'p' if is_red_turn else 'P'
        pawn_dir  = 1   if is_red_turn else -1
        if self.in_board(kr - pawn_dir, kc) and self.board[kr - pawn_dir][kc] == pawn_char:
            return True
        for dc in [-1, 1]:
            if self.in_board(kr, kc+dc) and self.board[kr][kc+dc] == pawn_char:
                return True

        return False

    def to_fen(self):
        fen_rows = []
        for r in range(ROWS):
            empty = 0
            row_str = ""
            for cc in range(COLS):
                p = self.board[r][cc]
                if p == '.':
                    empty += 1
                else:
                    if empty > 0:
                        row_str += str(empty); empty = 0
                    row_str += p
            if empty > 0:
                row_str += str(empty)
            fen_rows.append(row_str)
        side = 'w' if self.turn == 'red' else 'b'
        return "/".join(fen_rows) + f" {side} - - 0 1"


# --- 引擎进程客户端 ---
class EngineClient:
    """启动 xiangqi_ai 引擎子进程并通信（行协议，有状态，每局一个进程）。

    协议（与 gui.py 桌面版相同）：
      发送: side <red|black>  (填人类执子方，引擎下对面)
            move <r1> <c1> <r2> <c2>  (同步引擎内部棋盘)
            search  (阻塞算一步)
      接收: move <r1> <c1> <r2> <c2>  /  resign
    """
    def __init__(self, engine_cmd, log_dir=None):
        self.engine_cmd = engine_cmd
        self.log_dir = log_dir
        self.process = None
        self.msg_queue = queue.Queue()
        self.running = False
        self.t = None
        self.cmd_log = None

    def connect(self):
        try:
            self.process = subprocess.Popen(
                self.engine_cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1
            )
        except FileNotFoundError:
            raise RuntimeError(f"找不到引擎可执行文件: {self.engine_cmd}") from None
        except OSError as e:
            raise RuntimeError(f"启动引擎失败: {e}") from None

        self.running = True
        self.t = threading.Thread(target=self._reader_thread, daemon=True)
        self.t.start()

        if self.log_dir:
            import datetime, os
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(self.log_dir, exist_ok=True)
            self.cmd_log = open(os.path.join(self.log_dir, f"engine_cmds_{ts}.log"),
                                "w", encoding="utf-8")

    def _reader_thread(self):
        while self.running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.msg_queue.put(line.strip())
            except Exception:
                break

    def send(self, cmd):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
                if self.cmd_log:
                    self.cmd_log.write(cmd + "\n")
                    self.cmd_log.flush()
            except Exception:
                pass

    def get_message(self):
        try:
            return self.msg_queue.get_nowait()
        except queue.Empty:
            return None

    def alive(self):
        return self.process is not None and self.process.poll() is None

    def close(self):
        self.running = False
        if self.process and self.process.poll() is None:
            try:
                self.send("quit")
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception:
                pass
        if self.cmd_log:
            try:
                self.cmd_log.close()
            except Exception:
                pass
            self.cmd_log = None
