#!/usr/bin/env python3
"""
common.py
棋盘规则 (LocalBoard)、ChessDB 云开局库与引擎进程通信 (EngineClient)。
被 gui.py (pygame 桌面版) 和 webapp.py (网页版) 共用。
本模块不依赖 pygame，可在服务器上直接 import。
"""

import logging
import os
import queue
import random
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict

ROWS = 10
COLS = 9

PIECE_CHARS = {
    'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅', 'C': '炮', 'P': '兵',
    'r': '车', 'n': '马', 'b': '象', 'a': '士', 'k': '将', 'c': '炮', 'p': '卒',
    '.': '．'
}


# --- ChessDB 云开局库 ---
def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_number(name, default, converter):
    try:
        return converter(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


CLOUD_BOOK_ENABLED = _env_flag("XQ_CLOUD_BOOK_ENABLED", False)
QUERY_SCORE_THRESHOLD = _env_number("XQ_CLOUD_BOOK_SCORE_THRESHOLD", 20, int)
CLOUD_TIMEOUT = _env_number("XQ_CLOUD_BOOK_TIMEOUT", 2.0, float)
CLOUD_BOOK_URL = os.environ.get(
    "XQ_CLOUD_BOOK_URL", "http://www.chessdb.cn/chessdb.php"
)

_logger = logging.getLogger(__name__)


def uci_move_to_coords(move):
    """将 ChessDB/UCI 坐标（如 h2e2）转换为本项目的行列坐标。"""
    if not isinstance(move, str):
        return None
    move = move.strip().lower()
    if (len(move) != 4
            or move[0] < 'a' or move[0] > 'i'
            or move[2] < 'a' or move[2] > 'i'
            or move[1] < '0' or move[1] > '9'
            or move[3] < '0' or move[3] > '9'):
        return None
    return (
        (9 - int(move[1]), ord(move[0]) - ord('a')),
        (9 - int(move[3]), ord(move[2]) - ord('a')),
    )


def _fen_side_material_balance(fen):
    """按车=2、马=1、炮=1，返回 FEN 当前行棋方相对对手的子力差。"""
    try:
        placement, side, *_ = fen.split()
    except (AttributeError, ValueError):
        return None

    ranks = placement.split('/')
    if len(ranks) != ROWS or side not in {'w', 'b'}:
        return None

    values = {'R': 2, 'N': 1, 'C': 1}
    red_score = 0
    black_score = 0
    valid_pieces = set('RNBAKCP')
    for rank in ranks:
        width = 0
        for char in rank:
            if '1' <= char <= '9':
                width += int(char)
                continue
            if char.upper() not in valid_pieces:
                return None
            width += 1
            value = values.get(char.upper(), 0)
            if char.isupper():
                red_score += value
            else:
                black_score += value
        if width != COLS:
            return None

    if side == 'w':
        return red_score - black_score
    return black_score - red_score


class CloudOpeningBook:
    """线程安全的 ChessDB 云开局库客户端。

    缓存的是服务端返回的候选着，而不是一次随机选择的结果；缓存有容量
    上限和过期时间，网络错误不会写入缓存。
    """

    def __init__(self, enabled=True, score_threshold=20, timeout=2.0,
                 endpoint=CLOUD_BOOK_URL, opener=None, rng=None,
                 cache_ttl=600.0, max_cache_entries=2048):
        self.enabled = bool(enabled)
        self.score_threshold = max(0, int(score_threshold))
        self.timeout = max(0.01, float(timeout))
        self.endpoint = endpoint
        self._opener = opener
        self._rng = rng or random
        self.cache_ttl = max(0.0, float(cache_ttl))
        self.max_cache_entries = max(0, int(max_cache_entries))
        self._cache = OrderedDict()
        self._inflight = {}
        self._cache_lock = threading.Lock()

    @staticmethod
    def _parse_response(data):
        moves = []
        for record in data.split('|'):
            fields = {}
            for item in record.split(','):
                key, sep, value = item.partition(':')
                if sep:
                    fields[key.strip().lower()] = value.strip()
            coords = uci_move_to_coords(fields.get('move'))
            if coords is None:
                continue
            try:
                score = int(fields['score'])
            except (KeyError, TypeError, ValueError):
                continue
            moves.append((coords, score))
        return tuple(moves)

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def _load_moves(self, fen):
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(fen)
            if cached is not None:
                expires_at, moves = cached
                if expires_at > now:
                    self._cache.move_to_end(fen)
                    return moves
                del self._cache[fen]
            flight = self._inflight.get(fen)
            if flight is None:
                flight = {"event": threading.Event(), "result": None}
                self._inflight[fen] = flight
                is_leader = True
            else:
                is_leader = False

        if not is_leader:
            if flight["event"].wait(timeout=self.timeout + 1.0):
                return flight["result"]
            return None

        query = urllib.parse.urlencode({
            "action": "queryall",
            "learn": 1,
            "board": fen,
        })
        url = f"{self.endpoint}?{query}"
        moves = None
        try:
            opener = self._opener or urllib.request.urlopen
            with opener(url, timeout=self.timeout) as response:
                data = response.read().decode('utf-8', errors='replace')
            moves = self._parse_response(data)
        except Exception as exc:
            _logger.warning("云开局库查询失败: %s", exc)

        with self._cache_lock:
            if (moves is not None and self.cache_ttl > 0
                    and self.max_cache_entries > 0):
                self._cache[fen] = (time.monotonic() + self.cache_ttl, moves)
                self._cache.move_to_end(fen)
                while len(self._cache) > self.max_cache_entries:
                    self._cache.popitem(last=False)
            flight["result"] = moves
            if self._inflight.get(fen) is flight:
                del self._inflight[fen]
            flight["event"].set()
        return moves

    def query(self, fen, forbidden_move=None):
        """返回 ``((r1,c1), (r2,c2), score)``，无可用着时返回 None。"""
        if not self.enabled or not isinstance(fen, str) or not fen.strip():
            return None

        moves = self._load_moves(fen)
        if not moves:
            return None

        if forbidden_move is not None:
            moves = tuple(item for item in moves if item[0] != forbidden_move)
            if not moves:
                return None

        best_score = max(score for _, score in moves)
        candidates = [
            item for item in moves
            if item[1] >= best_score - self.score_threshold
        ]
        # 子力相等或领先时，不进入只有一个云库续着的冷门飞刀；如果已经
        # 因前面的库着少子，则继续跟随这唯一续着，避免半途转交引擎而干亏。
        if len(candidates) == 1:
            material_balance = _fen_side_material_balance(fen)
            if material_balance is None or material_balance >= 0:
                return None

        coords, score = self._rng.choice(candidates)
        return coords[0], coords[1], score


_default_cloud_book = CloudOpeningBook(
    enabled=True,
    score_threshold=QUERY_SCORE_THRESHOLD,
    timeout=CLOUD_TIMEOUT,
)


def query_cloud_book(fen, forbidden_move=None, *, enabled=None):
    """查询共享云开局库；默认由 ``XQ_CLOUD_BOOK_ENABLED`` 控制开关。"""
    if enabled is None:
        enabled = CLOUD_BOOK_ENABLED
    if not enabled:
        return None
    return _default_cloud_book.query(fen, forbidden_move=forbidden_move)


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

    def is_legal_move(self, r1, c1, r2, c2):
        """校验当前行棋方的一步，不改变棋盘。"""
        if not all(isinstance(value, int) for value in (r1, c1, r2, c2)):
            return False
        if not self.in_board(r1, c1) or not self.in_board(r2, c2):
            return False
        piece = self.board[r1][c1]
        if piece == '.' or self.is_red(piece) != (self.turn == 'red'):
            return False
        return (r2, c2) in self.get_valid_moves(r1, c1)

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
