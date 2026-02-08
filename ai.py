import subprocess
import re
USE_PIKAFISH=True  # 全局开关，是否使用皮卡鱼引擎进行评估
class PikafishEvaluator:
    def __init__(self, engine_path="pikafish.exe"):
        # 启动进程，保持后台运行
        self.process = subprocess.Popen(
            engine_path,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1
        )
        # 初始化
        self.send("uci")
        self.wait_for("uciok")
        self.send("isready")
        self.wait_for("readyok")
        # 必须加载 NNUE 才能评估
        # self.send("setoption name EvalFile value pikafish.nnue") # 如果没有自动加载请取消注释
        
    def send(self, cmd):
        self.process.stdin.write(cmd + "\n")
        self.process.stdin.flush()

    def wait_for(self, target_str):
        while True:
            line = self.process.stdout.readline()
            if target_str in line:
                return

    def get_evaluation(self, fen):
        """
        发送 FEN 并获取静态评估分
        """
        self.send(f"position fen {fen}")
        self.send("eval")
        
        score = 0
        # 解析皮卡鱼的输出，寻找 "Final evaluation"
        # 典型输出: "Final evaluation: 0.35 (white side)"
        while True:
            line = self.process.stdout.readline().strip()
            # 皮卡鱼/Stockfish 的 eval 输出格式通常包含 "Final evaluation"
            if "Final evaluation" in line:
                # 提取数字
                match = re.search(r"Final evaluation\s+([+\-]?\d+(\.\d+)?)", line)
                if match:
                    # 皮卡鱼通常输出的是 "分数 (cp)"，比如 +0.55
                    # 我们需要将其转换为整数分 (0.55 -> 55)
                    val_float = float(match.group(1))
                    score = int(val_float * 100)
                break
            
            # 防止死循环（有些版本输出不同）
            if line == "" and self.process.poll() is not None:
                break
                
        return score

    def close(self):
        self.process.terminate()

import sys
import os
import copy
import time
import random
import urllib.request
# --- 1. 配置与显示颜色 ---
USE_DEPTH=0  # 是否使用固定深度搜索 (否则使用迭代加深)
CLOUD_BOOK_ENABLED=1 # 是否启用云开局库查询
OPEN_NMP=1  # 是否启用空步裁剪 (Null Move Pruning)
RESET = "\033[0m"
RED_TXT = "\033[31m"
BLACK_TXT = "\033[36m"
BOLD = "\033[1m"

ROWS = 10
COLS = 9

PIECE_CHARS = {
    'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅', 'C': '炮', 'P': '兵',
    'r': '车', 'n': '马', 'b': '象', 'a': '士', 'k': '将', 'c': '炮', 'p': '卒',
    '.': '．' 
}
SCORE_INF = 30000 


# --- 2. 核心参数 (基于成熟引擎标准) ---

# 基础子力价值 (车9马4.5炮4.5)
# --- 修正后的子力价值 ---
# 逻辑：
# 1. 兵(90) vs 马(450) = 1:5。过河后配合 PST 会达到 150-200，符合实战。
# 2. 士象(120) 略高于兵，防止 AI 为了贪吃一个兵把士象丢了导致后防空虚。
# 3. 车(900) 依然维持最高权重。
PIECE_VALUES = {
    'k': 10000, 
    'r': 900, 
    'n': 450, 
    'c': 450, 
    'a': 120, 
    'b': 120, 
    'p': 90, 
    'K': 10000, 'R': 900, 'N': 450, 'C': 450, 'A': 120, 'B': 120, 'P': 90
}

# --- PST (Piece-Square Tables) 位置价值表 ---
# 所有的表都是基于红方视角 (Row 0是底线, Row 9是敌方底线)
# 黑方使用时，代码会自动翻转 (Row = 9 - Row)
# --- 修正后的 PST (绝对坐标版) ---
# 此时：Row 9 是红方底线，Row 0 是红方要进攻的敌方底线
# 逻辑：红方棋子在 Row r 时，直接查 table[r]

# [兵]：
# Row 0~2: 敌方九宫/底线 (分数最高)
# Row 3/4: 敌方兵行线/河口 (高分)
# Row 5/6: 我方河口/兵行线 (还没过河，低分)
# Row 7-9: 家里 (0分)
pst_pawn = [
    [ 90, 90, 90,100,100,100, 90, 90, 90], # 0 (敌底)
    [ 90, 90, 90,100,100,100, 90, 90, 90], # 1 (敌宫心)
    [ 60, 80, 80, 90,100, 90, 80, 80, 60], # 2 (敌宫顶)
    [ 50, 60, 60, 60, 60, 60, 60, 60, 50], # 3 (敌兵林)
    [ 20, 20, 20, 20, 20, 20, 20, 20, 20], # 4 (敌河口 - 刚过河)
    [  0,  0,  0, 10, 10, 10,  0,  0,  0], # 5 (我河口 - 没过河，只有中兵稍微值钱)
    [  0,  0,  0,  0,  0,  0,  0,  0,  0], # 6 (我兵林 - 初始位置)
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0]  # 9 (我底)
]

# [车]：
# 喜欢 Row 0 (沉底), Row 4 (占敌河), Row 3/2 (压制)
pst_rook = [
    [ 10, 20, 20, 20, 20, 20, 20, 20, 10], # 0 (沉底车，好)
    [ 10, 20, 20, 20, 20, 20, 20, 20, 10], # 1 (二线车)
    [ 20, 30, 30, 40, 40, 40, 30, 30, 20], # 2 (扼守咽喉)
    [ 20, 30, 30, 40, 40, 40, 30, 30, 20], # 3 (卒林车)
    [ 20, 40, 40, 50, 50, 50, 40, 40, 20], # 4 (河口车 - 最好)
    [ 10, 20, 20, 30, 30, 30, 20, 20, 10], # 5 (守河车)
    [  0, 10,  0, 10,  0, 10,  0, 10,  0], # 6
    [  0,  5,  0, 10,  0, 10,  0,  5,  0], # 7
    [  0,  5,  0,  5,  0,  5,  0,  5,  0], # 8
    [ -5,  0,  5,  5,  0,  5,  5,  0, -5]  # 9 (窝心车不好)
]

# [马]：
# 喜欢 Row 2/3 (卧槽/挂角), 不喜欢 Row 9/0 的边角
pst_knight = [
    [ -5, -5, -5, -5, -5, -5, -5, -5, -5], # 0 (敌底 - 除非是挂角，否则一般)
    [ -5,  5,  5, 15,  5, 15,  5,  5, -5], # 1
    [ -5,  5, 20, 40, 30, 40, 20,  5, -5], # 2 (卧槽/挂角 High)
    [ -5, 10, 20, 30, 20, 30, 20, 10, -5], # 3 (占据要道)
    [ -5,  5, 15, 20, 20, 20, 15,  5, -5], # 4 (河口)
    [ -5,  5, 15, 20, 20, 20, 15,  5, -5], # 5 (河口)
    [ -5,  5,  5, 10,  5, 10,  5,  5, -5], # 6
    [ -5, 15, 10, 15, 15, 15, 10, 15, -5], # 7 (守中卒)
    [ -5,  5,  5,  5,  5,  5,  5,  5, -5], # 8
    [ -5, -5, -5, -5, -5, -5, -5, -5, -5]  # 9 (归心马 - 弱)
]

# [炮]：
# 喜欢 Row 2 (沉底炮/闷宫), Row 4 (巡河)
pst_cannon = [
    [  0,  0,  5, 10, 10, 10,  5,  0,  0], # 0 (进底)
    [  0,  5,  5, 10, 10, 10,  5,  5,  0], # 1
    [  0, 10, 20, 30, 30, 30, 20, 10,  0], # 2 (控制线)
    [  0,  0,  0, 10, 10, 10,  0,  0,  0], # 3
    [ 10, 10, 20, 20, 20, 20, 20, 10, 10], # 4 (巡河炮)
    [  0,  0, 10, 10, 10, 10, 10,  0,  0], # 5 (守河)
    [  0,  0,  0,  0,  0,  0,  0,  0,  0], # 6
    [  0, 10, 10, 20, 20, 20, 10, 10,  0], # 7 (沿河/自家炮架)
    [  0,  5,  0,  5,  0,  5,  0,  5,  0], # 8
    [  0,  0,  0,  0,  0,  0,  0,  0,  0]  # 9
]

# [士]：只在自家九宫格有分 (Row 7,8,9)
pst_advisor = [[0]*9 for _ in range(10)]
pst_advisor[9] = [0, 0, 0, 20,  0, 20, 0, 0, 0] # 9行底士 (9,3) (9,5)
pst_advisor[8] = [0, 0, 0,  0, 20,  0, 0, 0, 0] # 8行中士 (8,4)
pst_advisor[7] = [0, 0, 0, -5,  0, -5, 0, 0, 0] # 7行高士 (危险)

# [相]：只在自家半场 (Row 5,7,9)
pst_bishop = [[0]*9 for _ in range(10)]
pst_bishop[9] = [0, 0, 20, 0,  0, 0, 20, 0, 0] # 9行底相
pst_bishop[7] = [0, 0,  0, 0, 20, 0,  0, 0, 0] # 7行中相
pst_bishop[5] = [0, 0, -5, 0,  0, 0, -5, 0, 0] # 5行河口相

# [帅]：只在自家九宫格 (Row 7,8,9)，且 9行最好
pst_king = [[0]*9 for _ in range(10)]
pst_king[9] = [0, 0, 0, 20, 30, 20, 0, 0, 0] # 9行：安稳
pst_king[8] = [0, 0, 0, 10, 10, 10, 0, 0, 0] # 8行：稍差
pst_king[7] = [0, 0, 0, -10,-10,-10, 0, 0, 0] # 7行：危险
PST_MAP = {
    'k': pst_king,   'K': pst_king,
    'r': pst_rook,   'R': pst_rook,
    'n': pst_knight, 'N': pst_knight,
    'c': pst_cannon, 'C': pst_cannon,
    'p': pst_pawn,   'P': pst_pawn,
    'a': pst_advisor,'A': pst_advisor,
    'b': pst_bishop, 'B': pst_bishop
}


# --- 评估权重配置 (基于 Eleeye 简化) ---
# 棋形分
EV_HOLLOW_CANNON = 450    # 空头炮 (非常危险)
EV_CENTRAL_CANNON = 50    # 中炮 (镇中)
EV_LINKED_PAWNS = 30      # 连兵 (过河兵相连)
EV_ROOK_TRAPPED = -50     # 车被困 (低机动性)
EV_FULL_GUARDS = 40       # 士象全 (防守加分)

# 威胁分
EV_ATTACK_KING = 20       # 每一个攻击老将区域的大子

# 机动性 (每多一个控制点加的分)
EV_MOBILITY = {
    'r': 6,  'n': 12, 'c': 6, # 车马炮的灵活性价值
    'R': 6,  'N': 12, 'C': 6
}
# --- 3. 主逻辑类 ---
# --- TT 表标记 ---
TT_EXACT = 0   # 精确值
TT_ALPHA = 1   # 上界 (最多这么多分，也就是 Fail Low)
TT_BETA  = 2   # 下界 (至少这么多分，也就是 Fail High)

class XiangqiCLI:

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
        self.player_side = None
        self.game_over = False
        self.current_score = 0
        

        # --- 在类的 __init__ 中修改 ---
        self.tt_size = 1000003  # 一个足够大的素数
        # 每个条目存储: [zobrist_hash, depth, flag, score, best_move]
        # 初始化为 None 或固定长度列表以节省分配开销
        self.tt = [None] * self.tt_size
        # --- Zobrist 与 置换表 初始化 ---
        self.zobrist_table = {} # 存储每个棋子在每个位置的随机数
        self.zobrist_turn = random.getrandbits(64) # 轮到黑方走棋的随机数
        self.current_hash = 0
        
        self.init_zobrist() # 生成随机数表
        self.init_score_and_hash() # 计算初始分数和初始Hash

        self.start_time = 0
        self.time_limit = 0
        self.stop_search = False  # 中断标志
        self.nodes = 0           # 统计搜索量

        self.history_table = [[[[0]*9 for _ in range(10)] for _ in range(9)] for _ in range(10)]
        self.killer_moves = [[None, None] for _ in range(64)]


        
        # 1. 启动皮卡鱼 (确保 exe 在同级目录)
        try:
            self.pikafish = PikafishEvaluator("pikafish.exe")
            print("成功连接皮卡鱼引擎用于评估！")
        except Exception as e:
            print(f"无法启动皮卡鱼: {e}")
            self.pikafish = None

        # 2. 添加一个评估缓存 (非常重要！否则太慢)
        self.eval_cache = {} 

    # 3. 彻底替换 evaluate 函数
    def evaluate(self):
        """
        使用皮卡鱼进行静态评估
        """
        # 如果皮卡鱼没启动，回退到原来的逻辑（或者直接返回0）
        if not USE_PIKAFISH:
            return self.current_score # 回退到旧的子力分数
        
        # 1. 生成 FEN
        # 为了提高缓存命中率，只取 FEN 的前两部分 (棋盘布局 + 轮谁走)
        # 忽略回合数等无关信息
        full_fen = self.to_fen()
        fen_key = " ".join(full_fen.split()[:2])
        
        # 2. 查缓存
        if fen_key in self.eval_cache:
            return self.eval_cache[fen_key]

        # 3. 调用皮卡鱼 (最耗时的一步)
        # 注意：皮卡鱼的评估是相对于“当前行动方”的
        # 也就是：如果是红方走，正分代表红优；如果是黑方走，正分代表黑优。
        # 你的 minimax 逻辑看起来是基于 "红方为正，黑方为负" 的绝对分数体系。
        # 我们需要转换一下。
        
        score = self.pikafish.get_evaluation(full_fen)
        
        # 皮卡鱼返回的分数通常是 "当前视角分"
        # 如果当前轮到黑方 (self.turn == 'black')，且皮卡鱼说 +100 (黑优)，
        # 那么在你的绝对分数体系里，这应该是 -100 (红劣)。
        if self.turn == 'black':
            final_score = -score
        else:
            final_score = score

        # 4. 存缓存
        # 限制缓存大小，防止内存爆炸
        if len(self.eval_cache) > 100000:
            self.eval_cache.clear()
        self.eval_cache[fen_key] = final_score
        
        return final_score
    
    # 记得在程序退出时关闭进程，比如加个析构函数或者在 quit 时调用
    def close(self):
        if self.pikafish:
            self.pikafish.close()
    # 2. 辅助函数：获取移动的历史得分
    def get_history_score(self, move):
        start, end = move
        return self.history_table[start[0]][start[1]][end[0]][end[1]]

    def is_time_up(self):
        """检查是否超时"""
        # 每隔 1024 个节点检查一次时间，减少系统调用开销
        if self.nodes & 1023 == 0:
            if time.time() - self.start_time > self.time_limit:
                self.stop_search = True
        return self.stop_search
    
    def init_zobrist(self):
        """为每个格子上的每种棋子生成一个唯一的 64位 随机整数"""
        pieces = PIECE_CHARS.keys()
        for r in range(ROWS):
            for c in range(COLS):
                for p in pieces:
                    if p != '.':
                        self.zobrist_table[(r, c, p)] = random.getrandbits(64)


    def get_piece_value(self, piece, r, c):
        """辅助函数：获取单个棋子在特定位置的分数（包含子力+PST）"""
        if piece == '.': return 0
        
        val = PIECE_VALUES.get(piece, 0)
        pst_val = 0
        if piece in PST_MAP:
            table = PST_MAP[piece]
            if self.is_red(piece):
                pst_val = table[r][c]
            else:
                pst_val = table[9-r][c] # 黑方翻转
        
        total = val + pst_val
        return total if self.is_red(piece) else -total

    def init_score_and_hash(self):
        """初始化计算 分数 和 Hash"""
        self.current_score = 0
        self.current_hash = 0
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p != '.':
                    self.current_score += self.get_piece_value(p, r, c)
                    self.current_hash ^= self.zobrist_table[(r, c, p)]
        
        # 如果初始是黑方走，需要异或 turn 的随机数（通常开局是红方，不做处理）
        if self.turn == 'black':
            self.current_hash ^= self.zobrist_turn
            

    def make_move(self, start, end):
        r1, c1 = start
        r2, c2 = end
        moving_piece = self.board[r1][c1]
        captured_piece = self.board[r2][c2]

        # 1. 更新分数 (增量)
        self.current_score -= self.get_piece_value(moving_piece, r1, c1)
        if captured_piece != '.':
            self.current_score -= self.get_piece_value(captured_piece, r2, c2)
        self.current_score += self.get_piece_value(moving_piece, r2, c2)

        # 2. 更新 Hash (核心优化: XOR 是可逆的)
        # 移出起点棋子
        self.current_hash ^= self.zobrist_table[(r1, c1, moving_piece)]
        # 如果终点有子，移出被吃棋子
        if captured_piece != '.':
            self.current_hash ^= self.zobrist_table[(r2, c2, captured_piece)]
        # 移入终点棋子
        self.current_hash ^= self.zobrist_table[(r2, c2, moving_piece)]
        # 切换行动方 Hash
        self.current_hash ^= self.zobrist_turn

        # 3. 执行移动
        self.board[r2][c2] = moving_piece
        self.board[r1][c1] = '.'
        self.turn = 'black' if self.turn == 'red' else 'red'
        
        return captured_piece

    def undo_move(self, start, end, captured):
        r1, c1 = start
        r2, c2 = end
        moved_piece = self.board[r2][c2]

        # 1. 还原分数
        self.current_score -= self.get_piece_value(moved_piece, r2, c2)
        self.current_score += self.get_piece_value(moved_piece, r1, c1)
        if captured != '.':
            self.current_score += self.get_piece_value(captured, r2, c2)

        # 2. 还原 Hash (操作完全对称)
        self.current_hash ^= self.zobrist_turn # 换回原来的行动方
        self.current_hash ^= self.zobrist_table[(r2, c2, moved_piece)] # 移出终点
        if captured != '.':
            self.current_hash ^= self.zobrist_table[(r2, c2, captured)] # 加回被吃子
        self.current_hash ^= self.zobrist_table[(r1, c1, moved_piece)] # 加回起点

        # 3. 还原棋盘
        self.board[r1][c1] = moved_piece
        self.board[r2][c2] = captured
        self.turn = 'black' if self.turn == 'red' else 'red'
    def calculate_mobility(self, is_red_turn):
        """
        计算盘面机动性加分（只在 evaluate 中调用）
        针对车、马进行机动性评估
        """
        mobility_score = 0
        
        # 预计算马的 8 个跳跃方向和对应的蹩腿位置
        # (马跳dr, dc), (蹩腿lr, lc)
        knight_moves = [
            (-2, -1, -1, 0), (-2, 1, -1, 0),  # 上跳 (蹩腿在上)
            (2, -1, 1, 0),   (2, 1, 1, 0),    # 下跳 (蹩腿在下)
            (-1, -2, 0, -1), (1, -2, 0, -1),  # 左跳 (蹩腿在左)
            (-1, 2, 0, 1),   (1, 2, 0, 1)     # 右跳 (蹩腿在右)
        ]
        
        # 车的 4 个方向
        rook_dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for r in range(ROWS):
            for c in range(COLS):
                piece = self.board[r][c]
                if piece == '.': continue
                
                # 区分红黑，用来决定加分还是减分
                is_red_piece = self.is_red(piece)
                factor = 1 if is_red_piece else -1
                
                p_lower = piece.lower()
                
                # --- 1. 车的机动性 ---
                if p_lower == 'r':
                    # 车每控制一个点 +1 分，稍微增加一些权重
                    # 如果车被憋在角落，分就低
                    move_cnt = 0
                    for dr, dc in rook_dirs:
                        nr, nc = r + dr, c + dc
                        # 简单的射线扫描
                        while 0 <= nr < ROWS and 0 <= nc < COLS:
                            move_cnt += 1
                            if self.board[nr][nc] != '.':
                                break
                            nr += dr
                            nc += dc
                    # 车的机动性价值较高
                    mobility_score += (move_cnt * 3) * factor

                # --- 2. 马的机动性 ---
                elif p_lower == 'n':
                    # 马每有一个合法跳点 +4 分 (鼓励马跳出)
                    # 重点检查蹩腿
                    move_cnt = 0
                    for dr, dc, lr, lc in knight_moves:
                        nr, nc = r + dr, c + dc
                        leg_r, leg_c = r + lr, c + lc
                        
                        # 检查边界
                        if 0 <= nr < ROWS and 0 <= nc < COLS:
                            # 检查蹩腿点必须为空
                            if self.board[leg_r][leg_c] == '.':
                                # 检查落点（要么是空，要么是敌子，不能是队友）
                                target = self.board[nr][nc]
                                if target == '.' or self.is_red(target) != is_red_piece:
                                    move_cnt += 1
                    
                    mobility_score += (move_cnt * 5) * factor
        
        # 返回总分（相对于红方视角）
        return mobility_score
    def get_relation_score(self):
        """
        核心重构：计算棋形、关系、威胁和防守
        """
        score = 0
        
        # 1. 寻找双方老将位置
        red_king = self.find_king(True)
        black_king = self.find_king(False)
        
        # 临时统计：[红方计数, 黑方计数]
        # 士/象的数量
        guards = {'a': 0, 'b': 0, 'A': 0, 'B': 0}
        # 攻击老将的大子数量
        attack_units = [0, 0] # red_attackers, black_attackers

        # 2. 全局扫描 (为了性能，尽量在一个循环内完成)
        # 我们按列扫描，这样容易判断“空头炮”和“兵及其阻挡”
        
        # 用于记录每一列是否有红/黑的炮、兵
        cols_summary = [ {'R_cannon':0, 'B_cannon':0, 'pieces':[]} for _ in range(COLS) ]

        for c in range(COLS):
            col_pieces = []
            for r in range(ROWS):
                p = self.board[r][c]
                if p != '.':
                    col_pieces.append((r, p))
                    # 统计士象数量
                    if p in guards: guards[p] += 1
            
            cols_summary[c]['pieces'] = col_pieces
            
            # 分析每一列的特殊棋形
            for idx, (r, p) in enumerate(col_pieces):
                # --- A. 连兵判断 (过河兵) ---
                if p == 'P' and r <= 4: # 红兵过河
                    # 检查左右是否有友军
                    if c > 0 and self.board[r][c-1] == 'P': score += EV_LINKED_PAWNS
                    if c < 8 and self.board[r][c+1] == 'P': score += EV_LINKED_PAWNS
                elif p == 'p' and r >= 5: # 黑卒过河
                    if c > 0 and self.board[r][c-1] == 'p': score -= EV_LINKED_PAWNS
                    if c < 8 and self.board[r][c+1] == 'p': score -= EV_LINKED_PAWNS

                # --- B. 记录炮的位置，用于后续空头炮判断 ---
                if p == 'C': cols_summary[c]['R_cannon'] += 1
                if p == 'c': cols_summary[c]['B_cannon'] += 1

        # 3. 详细阵型判断
        
        # --- C. 空头炮与中炮 (Central & Hollow Cannon) ---
        # 检查中路 (Col 4)
        mid_info = cols_summary[4]
        mid_pieces = mid_info['pieces']
        
        # 红方中炮/空头炮
        if mid_info['R_cannon'] > 0:
            # 找到红炮位置
            c_idx = -1
            for i, (r, p) in enumerate(mid_pieces):
                if p == 'C': c_idx = i; break
            
            if c_idx != -1:
                # 检查红炮前方是否有阻碍 (黑将之前的阻碍)
                # 简单近似：如果黑将也在中路
                if black_king and black_king[1] == 4:
                    blockers = 0
                    # 统计炮和黑将之间的子
                    for check_r in range(mid_pieces[c_idx][0] + 1, black_king[0]):
                        if self.board[check_r][4] != '.': blockers += 1
                    
                    if blockers == 0: score += EV_HOLLOW_CANNON  # 空头炮！致命
                    elif blockers == 1: score += EV_CENTRAL_CANNON # 中炮
        
        # 黑方中炮/空头炮
        if mid_info['B_cannon'] > 0:
            c_idx = -1
            for i, (r, p) in enumerate(mid_pieces):
                if p == 'c': c_idx = i; break
            
            if c_idx != -1:
                if red_king and red_king[1] == 4:
                    blockers = 0
                    for check_r in range(red_king[0] + 1, mid_pieces[c_idx][0]):
                        if self.board[check_r][4] != '.': blockers += 1
                    
                    if blockers == 0: score -= EV_HOLLOW_CANNON
                    elif blockers == 1: score -= EV_CENTRAL_CANNON

        # --- D. 士象全 (Full Guards) ---
        if guards['A'] == 2 and guards['B'] == 2: score += EV_FULL_GUARDS
        if guards['a'] == 2 and guards['b'] == 2: score -= EV_FULL_GUARDS

        # 4. 机动性 (Mobility) 与 局部威胁
        # 这一步比较耗时，我们简化计算：只计算车马炮
        # 并且只计算"有多少个合法的落子点"
        
        # 遍历棋盘大子
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p == '.': continue
                
                low_p = p.lower()
                if low_p not in ['r', 'n', 'c']: continue
                
                is_red_p = self.is_red(p)
                factor = 1 if is_red_p else -1
                
                # 4.1 简单的机动性计算
                moves_cnt = 0
                
                # 车：沿直线扫描
                if low_p == 'r':
                    for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
                        tr, tc = r+dr, c+dc
                        while 0 <= tr < ROWS and 0 <= tc < COLS:
                            moves_cnt += 1
                            if self.board[tr][tc] != '.': break
                            tr, tc = tr+dr, tc+dc
                    
                    # 惩罚：如果车被困在角落且不动 (例如没得动)
                    if moves_cnt < 2: score += (EV_ROOK_TRAPPED * factor)

                # 马：由 get_valid_moves 逻辑简化
                elif low_p == 'n':
                    for dr, dc, lr, lc in [(-2,-1,-1,0), (-2,1,-1,0), (2,-1,1,0), (2,1,1,0),
                                           (-1,-2,0,-1), (1,-2,0,-1), (-1,2,0,1), (1,2,0,1)]:
                        nr, nc, leg_r, leg_c = r+dr, c+dc, r+lr, c+lc
                        if 0<=nr<ROWS and 0<=nc<COLS and self.board[leg_r][leg_c] == '.':
                            # 如果落点是友军，虽不能走，但算作保护，机动性算一半
                            target = self.board[nr][nc]
                            if target == '.' or self.is_red(target) != is_red_p:
                                moves_cnt += 1
                
                # 炮：
                elif low_p == 'c':
                    # 炮的机动性稍微低一点权重，更多看位置
                    for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
                        tr, tc = r+dr, c+dc
                        while 0 <= tr < ROWS and 0 <= tc < COLS:
                            if self.board[tr][tc] == '.': moves_cnt += 1
                            else: break # 炮主要看移动，吃子另算
                            tr, tc = tr+dr, tc+dc

                score += moves_cnt * EV_MOBILITY[low_p] * factor
                
                # 4.2 将帅安全 (King Safety)
                # 如果这个大子在敌方老将附近的“九宫扩展区”内，加分
                if is_red_p and black_king:
                    kr, kc = black_king
                    if abs(r - kr) + abs(c - kc) <= 3: # 曼哈顿距离小于3
                        score += EV_ATTACK_KING
                elif not is_red_p and red_king:
                    kr, kc = red_king
                    if abs(r - kr) + abs(c - kc) <= 3:
                        score -= EV_ATTACK_KING

        return score

    # def evaluate(self):
    #     """
    #     新的综合评估入口
    #     """
    #     # 1. 基础分 (增量维护的子力+PST)
    #     base = self.current_score
        
    #     # 2. 关系与阵型分 (实时计算)
    #     # 注意：这里如果太慢，可以考虑只在 depth > X 时调用，或者简化
    #     relation = self.get_relation_score()
        
    #     total = base + relation
        
    #     # 如果当前轮到黑方走，minimax 视角需要取反吗？
    #     # 注意：你的 minimax 实现中，maximize_player 是布尔值。
    #     # 如果你的 current_score 已经是 "红优则正，黑优则负"，
    #     # 那么这里直接返回 total 即可。minimax 内部会根据 maximizing_player 处理。
    #     # 这里假设 total 是相对于红方的净胜分。
        
    #     return total
    def is_red(self, piece):
        return piece.isupper()

    def in_board(self, r, c):
        return 0 <= r < ROWS and 0 <= c < COLS

    # --- 走法生成 (标准逻辑) ---
    def get_valid_moves(self, r, c):
        piece = self.board[r][c]
        moves = []
        if piece == '.': return moves
        is_red_piece = self.is_red(piece)
        
        def is_teammate(nr, nc):
            p = self.board[nr][nc]
            return p != '.' and self.is_red(p) == is_red_piece

        # 车
        if piece.lower() == 'r':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                while self.in_board(nr, nc):
                    if self.board[nr][nc] == '.': moves.append((nr, nc))
                    else:
                        if not is_teammate(nr, nc): moves.append((nr, nc))
                        break
                    nr, nc = nr+dr, nc+dc
        # 马 (带撇脚)
        elif piece.lower() == 'n':
            for dr, dc, lr, lc in [(-2,-1,-1,0), (-2,1,-1,0), (2,-1,1,0), (2,1,1,0),
                                   (-1,-2,0,-1), (1,-2,0,-1), (-1,2,0,1), (1,2,0,1)]:
                nr, nc, lr, lc = r+dr, c+dc, r+lr, c+lc
                if self.in_board(nr, nc) and self.board[lr][lc] == '.' and not is_teammate(nr, nc):
                    moves.append((nr, nc))
        # 炮
        elif piece.lower() == 'c':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                platform = False
                while self.in_board(nr, nc):
                    if self.board[nr][nc] == '.':
                        if not platform: moves.append((nr, nc))
                    else:
                        if not platform: platform = True
                        else:
                            if not is_teammate(nr, nc): moves.append((nr, nc))
                            break
                    nr, nc = nr+dr, nc+dc
        # 相/象
        elif piece.lower() == 'b':
            for dr, dc, er, ec in [(-2,-2,-1,-1), (-2,2,-1,1), (2,-2,1,-1), (2,2,1,1)]:
                nr, nc, er, ec = r+dr, c+dc, r+er, c+ec
                if self.in_board(nr, nc) and self.board[er][ec] == '.' and not is_teammate(nr, nc):
                    if (is_red_piece and nr>=5) or (not is_red_piece and nr<=4):
                        moves.append((nr, nc))
        # 士/仕
        elif piece.lower() == 'a':
            for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nr, nc = r+dr, c+dc
                if self.in_board(nr, nc) and 3<=nc<=5 and not is_teammate(nr, nc):
                    if (is_red_piece and 7<=nr<=9) or (not is_red_piece and 0<=nr<=2):
                        moves.append((nr, nc))
        # 帅/将
        elif piece.lower() == 'k':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                if self.in_board(nr, nc) and 3<=nc<=5 and not is_teammate(nr, nc):
                    if (is_red_piece and 7<=nr<=9) or (not is_red_piece and 0<=nr<=2):
                        moves.append((nr, nc))
            # 2. 飞将逻辑 (King Facing King)
            # 红方向上找(-1)，黑方向下找(+1)
            direction = -1 if is_red_piece else 1
            check_r = r + direction
            
            while 0 <= check_r < ROWS:
                target_piece = self.board[check_r][c]
                if target_piece == '.':
                    # 如果是空地，继续往前看
                    check_r += direction
                else:
                    # 碰到棋子了
                    # 如果碰到的是敌方的将/帅，说明可以飞将！
                    enemy_king = 'k' if is_red_piece else 'K'
                    if target_piece == enemy_king:
                        moves.append((check_r, c))
                    # 无论碰到什么子（不管是敌是友，还是敌方老将），
                    # 只要中间有阻隔或已经找到了老将，搜索就结束
                    break
        # 兵/卒
        elif piece.lower() == 'p':
            dr = -1 if is_red_piece else 1
            if self.in_board(r+dr, c) and not is_teammate(r+dr, c): moves.append((r+dr, c))
            if (is_red_piece and r<=4) or (not is_red_piece and r>=5): # 过河后允许平移
                for dc in [-1, 1]:
                    if self.in_board(r, c+dc) and not is_teammate(r, c+dc): moves.append((r, c+dc))
        return moves

    def get_all_moves(self, is_red_turn):
        moves = []
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p != '.' and self.is_red(p) == is_red_turn:
                    ms = self.get_valid_moves(r, c)
                    for m in ms: moves.append(((r,c), m))
        return moves



    # --- 5. 静态搜索 (Quiescence Search) ---
    # 作用：搜索到底层时，如果还在吃子，就继续搜，防止“假吃”
    def quiescence_search(self, alpha, beta, maximizing_player, qs_depth=0):
        if qs_depth == 0:
            stand_pat = self.evaluate()
        else:
            # 深入 QS 后，为了速度只用基础分
            stand_pat = self.current_score
        
        if maximizing_player:
            if stand_pat >= beta: return beta
            if alpha < stand_pat: alpha = stand_pat
        else:
            if stand_pat <= alpha: return alpha
            if beta > stand_pat: beta = stand_pat
        # --- 关键修改 1: 限制 QS 处理将军的深度 ---
        # 如果在 QS 里连续处理逃生步超过 2 层，就强制停止，防止卡死
        if qs_depth > 10:
            return stand_pat
        in_check = self.is_in_check(maximizing_player)
        # 只生成吃子步
        moves = self.get_all_moves(maximizing_player)
        capture_moves = []
        for start, end in moves:
            # 如果正在被将军，必须搜所有逃生步！
            if in_check or self.board[end[0]][end[1]] != '.':
                capture_moves.append((start, end))
        
        # MVV-LVA 排序 (优先吃大子)
        capture_moves.sort(key=lambda m: PIECE_VALUES.get(self.board[m[1][0]][m[1][1]], 0), reverse=True)

        for start, end in capture_moves:
            captured = self.make_move(start, end)
            
            score = self.quiescence_search(alpha, beta, not maximizing_player, qs_depth + 1)
            
            self.undo_move(start, end, captured)
            
            if maximizing_player:
                if score >= beta: return beta
                if score > alpha: alpha = score
            else:
                if score <= alpha: return alpha
                if score < beta: beta = score   
                
        return alpha if maximizing_player else beta

    # --- 新增：判断是否允许空步裁剪的辅助函数 ---
    def find_king(self, is_red_king):
        target = 'K' if is_red_king else 'k'
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == target:
                    return r, c
        return None

    def is_in_check(self, is_red_turn):
        """判断当前行动方是否被将军（简化版检测，用于NMP安全检查）"""
        # 找到己方老将
        king_pos = self.find_king(is_red_turn)
        if not king_pos: return True # 如果老将被吃，视为最差情况
        kr, kc = king_pos
        
        # 简单扫描：检查车、炮、马、兵是否攻击老将
        # 这是一个耗时操作，但在NMP中是必要的，否则会导致严重的漏杀
        
        # 1. 检查同行同列的车/炮/帅
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = kr + dr, kc + dc
            first_piece = None
            while self.in_board(nr, nc):
                p = self.board[nr][nc]
                if p != '.':
                    if first_piece is None:
                        first_piece = p
                        # 车或老将直接照面
                        if self.is_red(p) != is_red_turn:
                            if p.lower() in ['r', 'k']: return True
                    else:
                        # 翻山炮
                        if self.is_red(p) != is_red_turn:
                            if p.lower() == 'c': return True
                        break # 隔两个子以上无效
                nr, nc = nr + dr, nc + dc
        
        # 2. 检查马
        knight_checks = [(-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2)]
        knight_legs   = [(-1, 0), (-1, 0), (1, 0), (1, 0), (0, -1), (0, 1), (0, -1), (0, 1)]
        for (dr, dc), (lr, lc) in zip(knight_checks, knight_legs):
            nr, nc = kr + dr, kc + dc
            lr, lc = kr + lr, kc + lc
            if self.in_board(nr, nc) and self.in_board(lr, lc):
                p = self.board[nr][nc]
                if p != '.' and self.is_red(p) != is_red_turn and p.lower() == 'n':
                    if self.board[lr][lc] == '.': # 必须无蹩脚
                        return True
                        
        # 3. 检查兵/卒 (老将只在九宫，只看周围一步即可)
        pawn_char = 'p' if is_red_turn else 'P' # 敌方兵的字符
        pawn_dir = 1 if is_red_turn else -1     # 敌兵进攻方向（相对于敌方是前进，相对于己方是后退）
        # 也就是检查 kr - pawn_dir 行是否有敌兵
        check_r = kr - pawn_dir
        if self.in_board(check_r, kc) and self.board[check_r][kc] == pawn_char: return True # 迎面冲来
        for dc in [-1, 1]: # 左右兵
            if self.in_board(kr, kc+dc) and self.board[kr][kc+dc] == pawn_char: return True

        return False

    def make_null_move(self):
        """执行空步：只交换出子权和Hash"""
        self.turn = 'black' if self.turn == 'red' else 'red'
        self.current_hash ^= self.zobrist_turn

    def undo_null_move(self):
        """撤销空步：操作完全一样"""
        self.turn = 'black' if self.turn == 'red' else 'red'
        self.current_hash ^= self.zobrist_turn
    def minimax(self, depth, alpha, beta, maximizing_player, allow_null=True):
        self.nodes += 1
        
        # 0. 检查超时 (每 2048 个节点检查一次)
        if self.nodes & 2047 == 0:
            if self.is_time_up():
                return 0, None

        # 1. 查表 (TT Lookup)
        original_alpha = alpha
        idx = self.current_hash % self.tt_size
        tt_entry = self.tt[idx]
        tt_move = None
        
        if tt_entry is not None and tt_entry[0] == self.current_hash:
            tt_hash, tt_depth, tt_flag, tt_score, tt_move = tt_entry
            # 只有当表里的深度比当前要求更深或相等时，结果才可靠
            if tt_depth >= depth:
                if tt_flag == TT_EXACT:
                    return tt_score, tt_move
                elif tt_flag == TT_ALPHA and tt_score <= alpha:
                    return tt_score, tt_move
                elif tt_flag == TT_BETA and tt_score >= beta:
                    return tt_score, tt_move

        # 2. 基础结束条件
        # 如果深度耗尽，进入静态搜索 (QS)
        if depth <= 0:
            val = self.quiescence_search(alpha, beta, maximizing_player)
            return val, None

        # 3. 检查胜负 (防止绝杀时死循环)
        kings = [False, False]
        # 这一步其实比较耗时，但在 Python 简易引擎中为了安全保留
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == 'K': kings[0] = True
                if self.board[r][c] == 'k': kings[1] = True
        if not kings[0]: return -30000 + depth, None 
        if not kings[1]: return 30000 - depth, None 

        in_check = self.is_in_check(maximizing_player)
        
        # --- 移除死循环风险的 Check Extension ---
        # 原来的 if in_check: depth += 1 会导致无限递归。
        # 这里改为：如果被将军，我们不做空步裁剪(NMP)，
        # 并且依靠 QS 在 depth=0 时处理将军，或者仅在 depth 较小时才极少量延伸(这里为了稳定，暂不延伸)。

        # --- Null Move Pruning (空步裁剪) ---
        # 只有在：没被将军 + 深度足够 + 没到残局(简单判断) 时才启用
        if OPEN_NMP and depth >= 3 and not in_check and allow_null:
            self.make_null_move()
            
            # 动态 R 值计算 (保持不变)
            if depth > 6:
                R = 3
            else:
                R = 2
            
            # 确保剩下的深度至少为 0
            next_depth = max(0, depth - 1 - R)
            
            # --- 逻辑修正开始 ---
            if maximizing_player:
                # 当前是红方：希望证明 即使空步，局势依然 >= beta
                # 交给黑方搜，使用 (beta-1, beta) 窗口
                val, _ = self.minimax(next_depth, beta - 1, beta, False, allow_null=False)
                self.undo_null_move() # 记得恢复
                
                if self.stop_search: return 0, None
                if val >= beta and val < 20000: 
                    return beta, None
            else:
                # 当前是黑方：希望证明 即使空步，局势依然 <= alpha
                # 交给红方搜，使用 (alpha, alpha+1) 窗口
                val, _ = self.minimax(next_depth, alpha, alpha + 1, True, allow_null=False)
                self.undo_null_move() # 记得恢复

                if self.stop_search: return 0, None
                if val <= alpha and val > -20000: 
                    return alpha, None
            # --- 逻辑修正结束 ---

        # 4. 生成着法
        moves = self.get_all_moves(maximizing_player)
        if not moves:
            # 无棋可走：如果是被将军，就是输了；如果没被将军，是困毙(算和棋或输，这里简化为输)
            return (-30000 if maximizing_player else 30000), None

        # 排序
        killers = self.killer_moves[depth] if depth < 64 else [None, None]
        def move_sorter(m):
            start, end = m
            if tt_move and (start, end) == tt_move: return 2000000 # TT Move
            
            victim = self.board[end[0]][end[1]]
            if victim != '.': # MVV-LVA
                val = PIECE_VALUES.get(victim, 0)
                attacker = self.board[start[0]][start[1]]
                attacker_val = PIECE_VALUES.get(attacker, 0)
                return 100000 + val * 10 - attacker_val
            
            if m == killers[0]: return 90000
            if m == killers[1]: return 80000
            return self.history_table[start[0]][start[1]][end[0]][end[1]]

        moves.sort(key=move_sorter, reverse=True)

        best_move = moves[0]
        best_score = -float(SCORE_INF) if maximizing_player else float(SCORE_INF)
        moves_count = 0
        
        # 5. 遍历
        for start, end in moves:
            moves_count += 1
            captured = self.make_move(start, end)
            
            score = 0
            is_killer = ((start, end) == killers[0] or (start, end) == killers[1])
            
            # --- PVS & LMR ---
            # 只有当不是被将军状态时，才敢大胆进行 LMR 裁剪
            do_lmr = (depth >= 3 and moves_count > 4 and 
                      captured == '.' and not in_check and 
                      not is_killer)
            
            if maximizing_player:
                if moves_count == 1:
                    score, _ = self.minimax(depth - 1, alpha, beta, False)
                else:
                    reduction = 1 if do_lmr else 0
                    if moves_count > 15 and do_lmr: reduction = 2
                    
                    search_depth = depth - 1 - reduction
                    # 确保深度不会变成负数导致逻辑混乱(虽然 minimax 入口有判断，但保持清醒很好)
                    if search_depth < 0: search_depth = 0

                    # 1. 尝试零窗口搜索
                    score, _ = self.minimax(search_depth, alpha, alpha + 1, False)
                    
                    # 2. 如果 Fail High (在这个深度居然比 alpha 好)，说明可能过度剪枝了
                    if score > alpha:
                        if do_lmr: # 恢复深度重搜
                            score, _ = self.minimax(depth - 1, alpha, alpha + 1, False)
                        if score > alpha and score < beta: # 全窗口重搜
                            score, _ = self.minimax(depth - 1, alpha, beta, False)
            else:
                if moves_count == 1:
                    score, _ = self.minimax(depth - 1, alpha, beta, True)
                else:
                    reduction = 1 if do_lmr else 0
                    if moves_count > 10 and do_lmr: reduction = 2
                    
                    search_depth = depth - 1 - reduction
                    if search_depth < 0: search_depth = 0

                    score, _ = self.minimax(search_depth, beta - 1, beta, True)
                    
                    if score < beta:
                        if do_lmr:
                            score, _ = self.minimax(depth - 1, beta - 1, beta, True)
                        if score < beta and score > alpha:
                            score, _ = self.minimax(depth - 1, alpha, beta, True)

            self.undo_move(start, end, captured)
            
            if self.stop_search: return 0, None

            # 更新 Alpha/Beta
            if maximizing_player:
                if score > best_score:
                    best_score = score
                    best_move = (start, end)
                    if best_score > alpha:
                        alpha = best_score
                        if alpha >= beta:
                            if captured == '.':
                                self.history_table[start[0]][start[1]][end[0]][end[1]] += depth * depth
                                if self.killer_moves[depth][0] != (start, end):
                                    self.killer_moves[depth][1] = self.killer_moves[depth][0]
                                    self.killer_moves[depth][0] = (start, end)
                            break
            else:
                if score < best_score:
                    best_score = score
                    best_move = (start, end)
                    if best_score < beta:
                        beta = best_score
                        if beta <= alpha:
                            if captured == '.':
                                self.history_table[start[0]][start[1]][end[0]][end[1]] += depth * depth
                                if self.killer_moves[depth][0] != (start, end):
                                    self.killer_moves[depth][1] = self.killer_moves[depth][0]
                                    self.killer_moves[depth][0] = (start, end)
                            break

        # 6. 存表
        flag = TT_EXACT
        if best_score <= original_alpha: flag = TT_ALPHA
        elif best_score >= beta: flag = TT_BETA
        
        if tt_entry is None or depth >= tt_entry[1]:
            self.tt[idx] = (self.current_hash, depth, flag, best_score, best_move)

        return best_score, best_move
    def search_main(self, max_time, is_ai_red):
        cloud_data = self.query_cloud_book()
        if cloud_data:
            book_move, book_score = cloud_data # 解构获取真实分数
            with open("log.txt", "a", encoding="utf-8") as f:
                print(f"使用云库走法: {book_move}, 云库分数: {book_score}", file=f)
            return book_score, book_move # 返回真实的分数和走法
        self.start_time = time.time()
        self.time_limit = max_time
        self.stop_search = False
        
        # 这两个变量存储【上一次完整深度】的结果
        last_completed_move = None
        last_completed_val = 0
        
        for depth in range(1, 64):
            # 尝试搜索当前深度
            current_val, current_move = self.minimax(depth, -float(SCORE_INF), float(SCORE_INF), is_ai_red)
            
            # 检查是否是因为超时导致的返回
            if self.stop_search or current_move is None:
                # 如果深度 6 搜了一半断了，我们依然有深度 5 的保底走法
                break 
            
            # 走到这里，说明当前深度【完全搜完了】，结果是可信的
            last_completed_move = current_move
            last_completed_val = current_val
            
            # 打印日志
            elapsed = time.time() - self.start_time
            with open("log.txt", "a", encoding="utf-8") as f:
                print(f"完成深度 {depth} | 耗时 {elapsed:.2f}s | 评估 {last_completed_val}", file=f)

            if abs(last_completed_val) > 20000: break # 发现绝杀
            if elapsed > max_time * 0.3: break # 剩余时间预警

        # 哪怕深度 6 失败了，我们返回的也是深度 5 的最佳走法
        return last_completed_val, last_completed_move
    def print_board(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n      {BOLD}Python 中国象棋 AI (Zobrist + TT 加速版){RESET}\n")
        print("     " + "  ".join([str(i) for i in range(COLS)]))
        print("     " + "-" * 25)
        for r in range(ROWS):
            line_str = f" {r} | "
            for c in range(COLS):
                piece = self.board[r][c]
                char = PIECE_CHARS.get(piece, piece)
                if piece == '.': color = "\033[90m"
                elif self.is_red(piece): color = RED_TXT
                else: color = BLACK_TXT
                line_str += f"{color}{char}{RESET} "
            print(line_str)
            if r == 4: print("   | " + "=" * 25 + " |")
        print(f"\n   当前回合: {RED_TXT + '红方' if self.turn == 'red' else BLACK_TXT + '黑方'}{RESET}")
        print(f"   TT 缓存条目数: {len(self.tt)}")
    
    def start_game(self):
        print("欢迎来到中国象棋！AI 采用经典位置价值算法。")
        while True:
            c = input("选边 (r:自己先走, b:自己后走): ").strip().lower()
            if c in ['r', 'b']:
                self.player_side = 'red' if c == 'r' else 'black'
                break
        cnt=0
        while not self.game_over:
            self.print_board()
            
            if self.turn == self.player_side:
                # --- 玩家回合 ---
                move_ok = False
                while not move_ok:
                    cmd = input(">>> 请输入移动 (例如 9 1 7 2) 或 q 退出: ").strip()
                    if cmd == 'q': return
                    try:
                        coords = list(map(int, cmd.split()))
                        if len(coords)==4:
                            r1,c1,r2,c2 = coords
                            if self.in_board(r1,c1) and self.in_board(r2,c2):
                                if self.is_red(self.board[r1][c1]) == (self.player_side=='red'):
                                    valid_moves = self.get_valid_moves(r1,c1)
                                    if (r2,c2) in valid_moves:
                                        self.make_move((r1,c1),(r2,c2))
                                        move_ok = True
                                    else: print("违规移动：不符合走法规则")
                                else: print("违规：这不是你的棋子")
                            else: print("违规：坐标越界")
                    except ValueError: pass
            
            else:
                # --- AI 回合 ---
                cnt+=1
                t0 = time.time()
                is_ai_red = (self.player_side == 'black')
                if USE_DEPTH:
                    if cnt<=3:
                        DEPTH = 5
                    else:
                        DEPTH = 6 # 中后期加深到6层
                    print(f">>> AI 正在思考 (深度 {DEPTH})...")
                    val, best = self.minimax(DEPTH, -float(SCORE_INF ), float(SCORE_INF ), is_ai_red)
                else:
                    MAX_TIME = 10.0 if  cnt<=3 else 30.0  # 每步最多思考 10 秒(仅在非固定深度时生效) 
                    print(f">>> AI 正在思考 (限时 {MAX_TIME} 秒)...")
                    val, best = self.search_main(MAX_TIME, is_ai_red)
                
                
                print(f"思考耗时: {time.time()-t0:.2f}s, 评估分: {val}")
                
                if best:
                    self.make_move(best[0], best[1])
                    # AI 走完稍微暂停一下让人看清
                    time.sleep(1)
                else:
                    print("AI 认输 (被绝杀或无棋可走)")
                    self.game_over = True

            # 简单的胜负检查
            ks = [0,0]
            for r in range(ROWS):
                for c in range(COLS):
                    if self.board[r][c]=='K': ks[0]=1
                    elif self.board[r][c]=='k': ks[1]=1
            if sum(ks)<2:
                self.print_board()
                winner = "红方" if ks[0] else "黑方"
                print(f"\n游戏结束，{winner}获胜！")
                self.game_over=True


    def to_fen(self):
        """将当前棋盘转换为 FEN 字符串"""
        fen_rows = []
        for r in range(ROWS):
            empty = 0
            row_str = ""
            for c in range(COLS):
                p = self.board[r][c]
                if p == '.':
                    empty += 1
                else:
                    if empty > 0:
                        row_str += str(empty)
                        empty = 0
                    row_str += p
            if empty > 0:
                row_str += str(empty)
            fen_rows.append(row_str)
        
        side = 'w' if self.turn == 'red' else 'b'
        # 简化版 FEN，对于云库查询足够了
        return "/".join(fen_rows) + f" {side} - - 0 1"

    def uci_to_move(self, uci):
        """将 UCI (如 'h2e2') 转换为坐标 ((r1,c1), (r2,c2))"""
        # UCI 列: a-i (0-8), 行: 0-9 (红方底线是0)
        # 注意：engine 内部数组 row 0 是黑方底线，需映射
        try:
            c1 = ord(uci[0]) - ord('a')
            r1 = 9 - int(uci[1])
            c2 = ord(uci[2]) - ord('a')
            r2 = 9 - int(uci[3])
            return (r1, c1), (r2, c2)
        except:
            return None
    def query_cloud_book(self):
        if not CLOUD_BOOK_ENABLED:
            return None
        """查询象棋云库并返回候选走法及分数"""
        fen = self.to_fen()
        encoded_fen = urllib.parse.quote(fen)
        url = f"http://www.chessdb.cn/chessdb.php?action=queryall&learn=1&board={encoded_fen}"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = response.read().decode('utf-8')
                if "move:" not in data:
                    return None
                
                moves = []
                for line in data.split('|'):
                    parts = {item.split(':')[0]: item.split(':')[1] for item in line.split(',') if ':' in item}
                    if 'move' in parts and 'score' in parts:
                        moves.append({
                            'move': parts['move'],
                            'score': int(parts['score'])
                        })
                
                if not moves: return None
                
                # 筛选规则：分数不低于最高分 5 分
                max_score = moves[0]['score']
                candidates = [m for m in moves if m['score'] >= max_score - 5]
                
                # 随机选一个高分走法
                selected = random.choice(candidates)
                move_coords = self.uci_to_move(selected['move'])
                
                # 返回坐标和该走法对应的真实分数
                return move_coords, selected['score']
        except Exception as e:
            with open("log.txt", "a") as f:
                print(f"云库查询失败: {e}", file=f)
            return None
def start_engine():
    engine = XiangqiCLI()

    print("ready", flush=True)
    cnt=0
    while True:
        try:
            cmd = input().strip()
        except EOFError:
            break

        if cmd == "quit":
            break

        if cmd.startswith("side"):
            # side red / side black
            _, s = cmd.split()
            engine.player_side = s

        elif cmd.startswith("move"):
            # move r1 c1 r2 c2
            _, r1, c1, r2, c2 = cmd.split()
            engine.make_move((int(r1),int(c1)), (int(r2),int(c2)))

        elif cmd.startswith("search"):
            t0 = time.time()
            cnt+=1
            is_ai_red = (engine.player_side == 'black')
            if USE_DEPTH:
                if cnt<=3:
                    DEPTH = 5
                else:
                    DEPTH = 6 # 中后期加深到6层
                val, best = engine.minimax(DEPTH, -float(SCORE_INF ), float(SCORE_INF ), is_ai_red)
            else:
                MAX_TIME = 10.0 if  cnt<=3 else 30.0 # 每步最多思考 10 秒(仅在非固定深度时生效) 
                print(f">>> AI 正在思考 (限时 {MAX_TIME} 秒)...")
                val, best = engine.search_main(MAX_TIME, is_ai_red)

            if best:
                (r1,c1),(r2,c2) = best
                engine.make_move(best[0], best[1])
                print(f"move {r1} {c1} {r2} {c2}", flush=True)
            else:
                print("resign", flush=True)
            with open("log.txt", "a", encoding="utf-8") as f:
                print(f"思考耗时: {time.time()-t0:.2f}s, 评估分: {val} ", file=f)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        XiangqiCLI().start_game()
    else:
        start_engine()


