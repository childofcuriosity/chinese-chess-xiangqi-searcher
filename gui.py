#!/usr/bin/env python3
"""
gui.py
Pygame front-end for your Xiangqi AI. Features:
- Start screen to choose side (Red/Black) and orientation (Red on bottom/top)
- Starts AI process after selection and waits for "ready"
- Properly handles AI-first vs human-first
- Keeps coordinate mapping consistent with engine (engine expects Red on bottom by default)

Run: python gui.py
Make sure ai.py is next to this file and adjust `pypy_path` if needed.
"""

import pygame
import sys
import subprocess
import threading
import queue
import os

# --- GUI 配置 ---
ENGINE_TYPE = 'cpp'  # 'python' or 'cpp'

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 720
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
COLOR_UI = (40, 40, 40)
COLOR_BTN = (220, 220, 220)
COLOR_BTN_HOVER = (200, 200, 255)

PIECE_CHARS = {
    'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅', 'C': '炮', 'P': '兵',
    'r': '车', 'n': '马', 'b': '象', 'a': '士', 'k': '将', 'c': '炮', 'p': '卒',
    '.': '．' 
}

# --- 简单的本地 Board 类 (仅用于显示与本地移动) ---
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

# --- AI 客户端类 (子进程通信) ---
class AIClient:
    def __init__(self, pypy_path='pypy3', ai_filename='ai.py'):
        # 延迟启动 (现在只记录参数)，真正启动在 connect()
        self.pypy_path = pypy_path
        self.ai_filename = ai_filename
        self.process = None
        self.msg_queue = queue.Queue()
        self.running = False
        self.t = None

    def connect(self):
        try:
            if ENGINE_TYPE == "python":
                self.process = subprocess.Popen(
                    [self.pypy_path, self.ai_filename],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    bufsize=1
                )
            elif ENGINE_TYPE == "cpp":
                self.process = subprocess.Popen(
                    ['./xiangqi_ai'],  # Assuming the C++ engine is compiled to this executable
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    bufsize=1
                )
        except FileNotFoundError:
            print(f"错误: 找不到命令 '{self.pypy_path}'。请确保已安装 PyPy3 或更改为 'python'。")
            sys.exit(1)

        self.running = True
        self.t = threading.Thread(target=self._reader_thread, daemon=True)
        self.t.start()

    def _reader_thread(self):
        while self.running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.msg_queue.put(line.strip())
            except Exception as e:
                print(f"Reader Error: {e}")
                break

    def send(self, cmd):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
            except Exception as e:
                print("Send error:", e)

    def get_message(self):
        try:
            return self.msg_queue.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        self.running = False
        if self.process and self.process.poll() is None:
            try:
                self.send("quit")
                self.process.terminate()
            except Exception:
                pass

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
        self.font = pygame.font.SysFont(['simhei', 'microsoftyahei', 'arial'], 28)
        self.title_font = pygame.font.SysFont(['simhei', 'arial'], 36, bold=True)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Python 象棋 (GUI)")

        self.board = LocalBoard()
        self.ai = None

        self.selected = None
        self.player_side = 'red' # will be set in start menu
        self.flip_view = False   # whether flip the display (red on top)
        self.game_over = False
        self.ai_thinking = False
        self.running = True

        # start screen UI
        self.start_buttons = []
        self.choice_side = 'red'  # 'red' or 'black'
        self.choice_red_bottom = True
        self.build_start_ui()

        # AI settings (adjust if needed)
        self.pypy_path = 'pypy3'  # change to 'python' if you don't have pypy3
        self.ai_filename = 'ai.py'

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

    def draw_board(self):
        # 背景
        self.screen.fill(COLOR_BG)
        # 标题
        title = self.title_font.render("中国象棋 (GUI)", True, COLOR_UI)
        self.screen.blit(title, (20, 18))

        # 画线
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
        # 斜线 (仕/士)
        advisors = [(0, 3), (2, 5), (0, 5), (2, 3), (7, 3), (9, 5), (7, 5), (9, 3)]
        for i in range(0, len(advisors), 2):
            p1 = self.trans_coord(*advisors[i])
            p2 = self.trans_coord(*advisors[i+1])
            pygame.draw.line(self.screen, COLOR_LINE, p1, p2, 2)

        # 选中框
        if self.selected:
            cx, cy = self.trans_coord(*self.selected)
            pygame.draw.rect(self.screen, COLOR_SELECT, (cx - 30, cy - 30, 60, 60), 4)

        # 棋子
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

        # AI 状态
        if self.ai_thinking:
            txt = self.font.render("AI 思考中...", True, (0,0,255))
            self.screen.blit(txt, (20, 80))

        # 当前回合
        turn_txt = f"当前回合: {'红' if self.board.turn=='red' else '黑'}"
        ttxt = self.font.render(turn_txt, True, COLOR_UI)
        self.screen.blit(ttxt, (SCREEN_WIDTH - 220, 18))

    def draw_start_menu(self):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("开始 - 请选择执子与摆放", True, COLOR_UI)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 40))

        mouse_pos = pygame.mouse.get_pos()
        # Draw side buttons
        self.btn_play_red.draw(self.screen, mouse_pos)
        self.btn_play_black.draw(self.screen, mouse_pos)

        # highlight current choice
        choice_text = self.font.render(f"当前选择: Play as {'Red' if self.choice_side=='red' else 'Black'}", True, COLOR_UI)
        self.screen.blit(choice_text, (SCREEN_WIDTH//2 - choice_text.get_width()//2, 220))

        # orientation toggle
        orient_label = "Red at bottom" if self.choice_red_bottom else "Red at top"
        self.btn_toggle_orient.text = orient_label + " (click to toggle)"
        self.btn_toggle_orient.draw(self.screen, mouse_pos)

        self.btn_start.draw(self.screen, mouse_pos)

        hint = self.font.render("点击格子选择棋子，再点击目的地下子。GUI 会把移动发送到 AI。", True, COLOR_UI)
        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 60))

    def start_ai_and_wait_ready(self):
        # 启动 AI 子进程（协议模式，不再等待 ready/init）
        self.ai = AIClient(pypy_path=self.pypy_path, ai_filename=self.ai_filename)
        self.ai.connect()
        # 稍等片刻确保进程已启动
        pygame.time.wait(300)
        # 告诉 AI 玩家执子
        self.ai.send(f"side {self.player_side}")

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
                        elif self.btn_start.clicked(pos):
                            # commit choices
                            self.player_side = self.choice_side
                            # flip_view True means we show red on top (inverse of engine default)
                            self.flip_view = not self.choice_red_bottom

                            # initialize ai process now that we know side
                            self.start_ai_and_wait_ready()

                            # tell AI who is playing? (engine here only needs board moves)
                            # If player is black, AI (red) should move first
                            if self.player_side == 'black':
                                # ask AI to search and move
                                self.ai.send(f"search")
                                self.ai_thinking = True

                            in_start_menu = False

                else:
                    # normal gameplay events
                    if not self.game_over and not self.ai_thinking and self.board.turn == self.player_side:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            coord = self.get_click_coord(event.pos)
                            if coord:
                                r, c = coord
                                piece = self.board.board[r][c]
                                # 选中自己的棋子
                                if piece != '.' and self.board.is_red(piece) == (self.player_side == 'red'):
                                    self.selected = (r, c)
                                elif self.selected:
                                    r1, c1 = self.selected
                                    # 直接做本地落子并发送给 AI
                                    self.board.move(r1, c1, r, c)
                                    self.selected = None
                                    # inform ai of move in engine coords
                                    self.ai.send(f"move {r1} {c1} {r} {c}")
                                    # tell ai to search for reply
                                    self.ai.send(f"search")
                                    self.ai_thinking = True

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
                        except Exception as e:
                            print("解析 bestmove 错误:", e)
                        self.ai_thinking = False
                    elif parts[0] == "resign":
                        print("AI 认输")
                        self.game_over = True
                        self.ai_thinking = False

            # 绘制界面
            if in_start_menu:
                self.draw_start_menu()
            else:
                self.draw_board()

            pygame.display.flip()
            clock.tick(30)

        # 退出清理
        if self.ai:
            self.ai.close()
        pygame.quit()


if __name__ == "__main__":
    gui = XiangqiGUI()
    gui.run()
