#!/usr/bin/env python3
"""
gui.py
Pygame front-end for your Xiangqi AI.
"""

import pygame
import os
import urllib.request
import urllib.parse
import random

from common import LocalBoard, EngineClient, PIECE_CHARS, ROWS, COLS

# --- GUI 配置 ---

# --- 云库配置 (cpp 引擎不联网, 由 GUI 代查) ---
CLOUD_BOOK_ENABLED =0 #1    # 1=启用; 0=禁用
QUERY_SCORE_THRESHOLD = 20
CLOUD_TIMEOUT = 2.0

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 760   # 多出 40px 给禁招输入槽
BOARD_OFFSET_X = 50
BOARD_OFFSET_Y = 120
CELL_SIZE = 60
RADIUS = 26
ROWS = 10
COLS = 9

COLOR_BG = (238, 203, 149)
COLOR_LINE = (0, 0, 0)
COLOR_RED = (200, 0, 0)
COLOR_BLACK = (20, 20, 20)
COLOR_SELECT = (0, 200, 0)
COLOR_VALID_MOVE = (0, 180, 0)       # 合法落点: 空格小圆点
COLOR_VALID_CAPTURE = (220, 60, 0)   # 合法吃子: 橙红色圆圈
COLOR_UI = (40, 40, 40)
COLOR_BTN = (220, 220, 220)
COLOR_BTN_HOVER = (200, 200, 255)
COLOR_INPUT = (255, 255, 240)
COLOR_INPUT_FOCUS = (255, 240, 200)

# --- 云库查询 (gui 端代理) ---
_cloud_cache = {}
def query_cloud_book(fen, forbidden_move=None):
    if not CLOUD_BOOK_ENABLED:
        return None
    if forbidden_move is None and fen in _cloud_cache:
        return _cloud_cache[fen]
    encoded = urllib.parse.quote(fen)
    url = f"http://www.chessdb.cn/chessdb.php?action=queryall&learn=1&board={encoded}"
    try:
        with urllib.request.urlopen(url, timeout=CLOUD_TIMEOUT) as resp:
            data = resp.read().decode('utf-8')
        if "move:" not in data:
            if forbidden_move is None:
                _cloud_cache[fen] = None
            return None
        moves = []
        for line in data.split('|'):
            parts = {kv.split(':')[0]: kv.split(':')[1]
                     for kv in line.split(',') if ':' in kv}
            if 'move' in parts and 'score' in parts:
                moves.append((parts['move'], int(parts['score'])))
        if not moves:
            if forbidden_move is None:
                _cloud_cache[fen] = None
            return None
        max_s = moves[0][1]
        cands = [m for m in moves if m[1] >= max_s - QUERY_SCORE_THRESHOLD]
        if forbidden_move is not None:
            def _to_coords(uci):
                return ((9 - int(uci[1]), ord(uci[0]) - ord('a')),
                        (9 - int(uci[3]), ord(uci[2]) - ord('a')))
            cands = [m for m in cands if _to_coords(m[0]) != forbidden_move]
            if not cands:
                return None
        uci, sc = random.choice(cands)
        c1 = ord(uci[0]) - ord('a'); r1 = 9 - int(uci[1])
        c2 = ord(uci[2]) - ord('a'); r2 = 9 - int(uci[3])
        result = ((r1, c1), (r2, c2), sc)
        if forbidden_move is None:
            _cloud_cache[fen] = result
        return result
    except Exception as e:
        print("[云库] 查询失败:", e)
        if forbidden_move is None:
            _cloud_cache[fen] = None
        return None

# --- 小型 UI 组件 ---
class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        color = COLOR_BTN_HOVER if hover else COLOR_BTN
        pygame.draw.rect(surf, color, self.rect)
        pygame.draw.rect(surf, COLOR_UI, self.rect, 2)
        txt = self.font.render(self.text, True, COLOR_UI)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)

# --- GUI 主程序 ---
class XiangqiGUI:
    def __init__(self):
        pygame.init()
        font_path = r"simhei.ttf"
        self.font = pygame.font.Font(font_path, 28)
        self.small_font = pygame.font.Font(font_path, 20)
        self.title_font = pygame.font.Font(font_path, 36)
        self.title_font.set_bold(True)

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Python 象棋 (GUI)")

        self.board = LocalBoard()
        self.ai = None

        self.selected = None
        self.valid_moves_cache = []   # 当前选中棋子的合法落点
        self.player_side = 'red'
        self.flip_view = False
        self.game_over = False
        self.ai_thinking = False
        self.running = True

        # 代替AI 调试开关
        self.replace_ai_mode = False
        self.replace_ai_pending = False
        self.btn_replace_ai = Button((SCREEN_WIDTH - 170, 60, 150, 36), "代替AI: 关", self.small_font)
        # self.btn_print_engine = Button((SCREEN_WIDTH - 170, 100, 150, 36), "每步打印: 关", self.small_font)
        # self.auto_print_engine = False

        # 禁招输入槽
        self.forbid_text = "1 1 1 1"
        self.forbid_focused = False
        self.forbid_rect = pygame.Rect(20, SCREEN_HEIGHT - 50, 280, 36)

        self.start_buttons = []
        self.choice_side = 'red'
        self.choice_red_bottom = True
        self.build_start_ui()

    def build_start_ui(self):
        w = 220; h = 48
        cx = SCREEN_WIDTH // 2
        self.btn_play_red = Button((cx - w - 10, 260, w, h), "Play as Red (move first)", self.font)
        self.btn_play_black = Button((cx + 10, 260, w, h), "Play as Black (move second)", self.font)
        self.btn_toggle_orient = Button((cx - w//2, 340, w, h), "Red at bottom (toggle)", self.font)
        self.btn_start = Button((cx - 110, 420, 220, 56), "Start Game", self.title_font)

    def trans_coord(self, r, c):
        effective_r, effective_c = r, c
        if self.flip_view:
            effective_r = ROWS - 1 - r
            effective_c = COLS - 1 - c
        x = BOARD_OFFSET_X + effective_c * CELL_SIZE
        y = BOARD_OFFSET_Y + effective_r * CELL_SIZE
        return x, y

    def get_click_coord(self, pos):
        x, y = pos
        c = round((x - BOARD_OFFSET_X) / CELL_SIZE)
        r = round((y - BOARD_OFFSET_Y) / CELL_SIZE)
        if self.flip_view:
            r = ROWS - 1 - r
            c = COLS - 1 - c
        if 0 <= r < ROWS and 0 <= c < COLS:
            return r, c
        return None

    def parse_forbid(self):
        try:
            nums = [int(x) for x in self.forbid_text.split()]
            if len(nums) != 4:
                return None
            r1, c1, r2, c2 = nums
            if (r1, c1) == (r2, c2):
                return None
            if not (0 <= r1 < ROWS and 0 <= r2 < ROWS and 0 <= c1 < COLS and 0 <= c2 < COLS):
                return None
            return ((r1, c1), (r2, c2))
        except Exception:
            return None

    def draw_board(self):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("中国象棋 (GUI)", True, COLOR_UI)
        self.screen.blit(title, (20, 18))

        for r in range(ROWS):
            p1 = self.trans_coord(r, 0)
            p2 = self.trans_coord(r, COLS - 1)
            pygame.draw.line(self.screen, COLOR_LINE, p1, p2, 2)
        for c in range(COLS):
            p1 = self.trans_coord(0, c)
            p2 = self.trans_coord(4, c)
            pygame.draw.line(self.screen, COLOR_LINE, p1, p2, 2)
            p3 = self.trans_coord(5, c)
            p4 = self.trans_coord(9, c)
            pygame.draw.line(self.screen, COLOR_LINE, p3, p4, 2)
        advisors = [(0, 3), (2, 5), (0, 5), (2, 3), (7, 3), (9, 5), (7, 5), (9, 3)]
        for i in range(0, len(advisors), 2):
            p1 = self.trans_coord(*advisors[i])
            p2 = self.trans_coord(*advisors[i+1])
            pygame.draw.line(self.screen, COLOR_LINE, p1, p2, 2)

        # ---- 合法落点高亮（在棋子之前画，不会遮住棋子）----
        for nr, nc in self.valid_moves_cache:
            x, y = self.trans_coord(nr, nc)
            if self.board.board[nr][nc] != '.':
                # 有敌子可吃：橙红色空心圆框
                pygame.draw.circle(self.screen, COLOR_VALID_CAPTURE, (x, y), RADIUS, 4)
            else:
                # 空格：小绿点
                pygame.draw.circle(self.screen, COLOR_VALID_MOVE, (x, y), 10)

        # 选中框
        if self.selected:
            cx, cy = self.trans_coord(*self.selected)
            pygame.draw.rect(self.screen, COLOR_SELECT, (cx - 30, cy - 30, 60, 60), 4)

        for r in range(ROWS):
            for c in range(COLS):
                piece = self.board.board[r][c]
                if piece != '.':
                    x, y = self.trans_coord(r, c)
                    is_red = self.board.is_red(piece)
                    color = COLOR_RED if is_red else COLOR_BLACK
                    pygame.draw.circle(self.screen, (250, 220, 180), (x, y), RADIUS)
                    pygame.draw.circle(self.screen, color, (x, y), RADIUS, 2)
                    text = self.font.render(PIECE_CHARS[piece], True, color)
                    rect = text.get_rect(center=(x, y))
                    self.screen.blit(text, rect)

        if self.ai_thinking:
            txt = self.font.render("AI 思考中...", True, (0,0,255))
            self.screen.blit(txt, (20, 80))

        if self.replace_ai_pending:
            txt = self.font.render("请代替AI落子...", True, (255, 0, 0))
            self.screen.blit(txt, (20, 80))

        # 代替AI 按钮
        self.btn_replace_ai.draw(self.screen, pygame.mouse.get_pos())
        # self.btn_print_engine.draw(self.screen, pygame.mouse.get_pos())

        turn_txt = f"当前回合: {'红' if self.board.turn=='red' else '黑'}"
        ttxt = self.font.render(turn_txt, True, COLOR_UI)
        self.screen.blit(ttxt, (SCREEN_WIDTH - 220, 18))

        # 禁招输入槽
        label = self.small_font.render("cpponly禁招(r1 c1 r2 c2):", True, COLOR_UI)
        self.screen.blit(label, (20, SCREEN_HEIGHT - 78))
        bg_color = COLOR_INPUT_FOCUS if self.forbid_focused else COLOR_INPUT
        pygame.draw.rect(self.screen, bg_color, self.forbid_rect)
        pygame.draw.rect(self.screen, COLOR_UI, self.forbid_rect, 2)
        txt = self.font.render(self.forbid_text, True, COLOR_UI)
        self.screen.blit(txt, (self.forbid_rect.x + 8, self.forbid_rect.y + 4))
        fb = self.parse_forbid()
        if fb:
            (r1, c1), (r2, c2) = fb
            tip = self.small_font.render(f"已禁: ({r1},{c1})->({r2},{c2})", True, (160, 0, 0))
        else:
            tip = self.small_font.render("无禁招 (默认 1 1 1 1)", True, (80, 80, 80))
        self.screen.blit(tip, (self.forbid_rect.right + 12, SCREEN_HEIGHT - 44))

    def draw_start_menu(self):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("开始 - 请选择执子与摆放", True, COLOR_UI)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 40))

        mouse_pos = pygame.mouse.get_pos()
        self.btn_play_red.draw(self.screen, mouse_pos)
        self.btn_play_black.draw(self.screen, mouse_pos)

        choice_text = self.font.render(f"当前选择: Play as {'Red' if self.choice_side=='red' else 'Black'}", True, COLOR_UI)
        self.screen.blit(choice_text, (SCREEN_WIDTH//2 - choice_text.get_width()//2, 220))

        orient_label = "Red at bottom" if self.choice_red_bottom else "Red at top"
        self.btn_toggle_orient.text = orient_label + " (click to toggle)"
        self.btn_toggle_orient.draw(self.screen, mouse_pos)

        self.btn_start.draw(self.screen, mouse_pos)

        self.btn_replace_ai.draw(self.screen, mouse_pos)

        hint = self.font.render("点击格子选择棋子，再点击目的地下子。", True, COLOR_UI)
        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 80))

    def _maybe_print_engine(self, label=""):
        # if self.auto_print_engine and self.ai:
        #     self.ai.send("print")
        #     print(f"[每步打印] {label}")
        pass

    def request_ai_move(self):
        # 代替AI模式：跳过云库和引擎，等人手动落子
        if self.replace_ai_mode:
            self.replace_ai_pending = True
            return

        fen = self.board.to_fen()
        forbid = self.parse_forbid()

        cloud = query_cloud_book(fen, forbidden_move=forbid)
        if cloud is not None:
            (r1, c1), (r2, c2), sc = cloud
            print(f"[云库] 命中: ({r1},{c1})->({r2},{c2})  score={sc}")
            self.board.move(r1, c1, r2, c2)
            self.ai.send(f"move {r1} {c1} {r2} {c2}")
            # self._maybe_print_engine(f"云库: {r1},{c1}->{r2},{c2}")
            self.ai_thinking = False
            return

        if forbid:
            (fr, fc), (tr, tc) = forbid
            self.ai.send(f"forbid {fr} {fc} {tr} {tc}")
        self.ai.send("search")
        self.ai_thinking = True

    def start_ai_and_wait_ready(self):
        self.ai = EngineClient(['./xiangqi_ai'], log_dir='logs')
        self.ai.connect()
        pygame.time.wait(300)
        self.ai.send(f"side {self.player_side}")

    def handle_forbid_key(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.forbid_text = self.forbid_text[:-1]
        elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
            self.forbid_focused = False
        else:
            ch = event.unicode
            if ch and (ch.isdigit() or ch == ' ') and len(self.forbid_text) < 16:
                self.forbid_text += ch

    # ------------------------------------------------------------------
    # 棋盘点击核心逻辑（含合规检测）
    # ------------------------------------------------------------------
    def handle_board_click(self, coord):
        r, c = coord
        piece = self.board.board[r][c]

        # 代替AI模式：允许点击AI方的棋子
        allow_enemy = self.replace_ai_pending
        can_select = piece != '.' and (
            self.board.is_red(piece) == (self.player_side == 'red') or allow_enemy
        )

        # 情况 A: 点了己方棋子（或代替AI时点AI方棋子）→ 切换选中
        if can_select:
            self.selected = (r, c)
            self.valid_moves_cache = self.board.get_valid_moves(r, c)
            return

        # 情况 B: 已选中棋子，点了目标格
        if self.selected:
            r1, c1 = self.selected
            # 检查目标是否在合法落点列表里
            if (r, c) in self.valid_moves_cache:
                self.board.move(r1, c1, r, c)
                self.selected = None
                self.valid_moves_cache = []
                self.ai.send(f"move {r1} {c1} {r} {c}")
                # self._maybe_print_engine(f"人走: {r1},{c1}->{r},{c}")
                if self.replace_ai_pending:
                    self.replace_ai_pending = False
                else:
                    self.request_ai_move()
            else:
                # 非法目标：取消选中（点空地或点到禁止格）
                self.selected = None
                self.valid_moves_cache = []

    def run(self):
        clock = pygame.time.Clock()
        in_start_menu = True

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if in_start_menu:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        pos = event.pos
                        if self.btn_play_red.clicked(pos):
                            self.choice_side = 'red'
                        elif self.btn_play_black.clicked(pos):
                            self.choice_side = 'black'
                        elif self.btn_toggle_orient.clicked(pos):
                            self.choice_red_bottom = not self.choice_red_bottom
                        elif self.btn_replace_ai.clicked(pos):
                            self.replace_ai_mode = not self.replace_ai_mode
                            self.btn_replace_ai.text = "代替AI: 开" if self.replace_ai_mode else "代替AI: 关"
                        elif self.btn_start.clicked(pos):
                            self.player_side = self.choice_side
                            self.flip_view = not self.choice_red_bottom
                            self.start_ai_and_wait_ready()
                            if self.player_side == 'black':
                                self.request_ai_move()
                            in_start_menu = False
                else:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.forbid_rect.collidepoint(event.pos):
                            self.forbid_focused = True
                        elif self.btn_replace_ai.clicked(event.pos):
                            self.replace_ai_mode = not self.replace_ai_mode
                            self.btn_replace_ai.text = "代替AI: 开" if self.replace_ai_mode else "代替AI: 关"
                            self.replace_ai_pending = False
                        # elif self.btn_print_engine.clicked(event.pos):
                        #     self.auto_print_engine = not self.auto_print_engine
                        #     self.btn_print_engine.text = "每步打印: 开" if self.auto_print_engine else "每步打印: 关"
                        else:
                            self.forbid_focused = False

                    if self.forbid_focused and event.type == pygame.KEYDOWN:
                        self.handle_forbid_key(event)
                        continue

                    if not self.game_over and not self.ai_thinking:
                        human_can_move = (self.board.turn == self.player_side) or self.replace_ai_pending
                        if human_can_move:
                            if event.type == pygame.MOUSEBUTTONDOWN:
                                coord = self.get_click_coord(event.pos)
                                if coord:
                                    self.handle_board_click(coord)

            # 处理 AI 消息
            if not in_start_menu and self.ai:
                while True:
                    msg = self.ai.get_message()
                    if not msg: break
                    print("收到 AI:", msg)
                    parts = msg.split()
                    if parts[0] == "move":
                        try:
                            r1, c1, r2, c2 = map(int, parts[1:5])
                            self.board.move(r1, c1, r2, c2)
                            # self._maybe_print_engine(f"引擎走: {r1},{c1}->{r2},{c2}")
                        except Exception as e:
                            print("解析 bestmove 错误:", e)
                        self.ai_thinking = False
                    elif parts[0] == "resign":
                        print("AI 认输")
                        self.game_over = True
                        self.ai_thinking = False

            if in_start_menu:
                self.draw_start_menu()
            else:
                self.draw_board()

            pygame.display.flip()
            clock.tick(30)

        if self.ai:
            self.ai.close()
        pygame.quit()


if __name__ == "__main__":
    gui = XiangqiGUI()
    gui.run()