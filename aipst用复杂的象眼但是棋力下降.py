import subprocess
import re
import sys
import os
import copy
import time
import random
import urllib.request
# --- 1. 配置与显示颜色 ---
USE_PIKAFISH=0  # 全局开关，是否使用皮卡鱼引擎进行评估
USE_DEPTH=1  # 是否使用固定深度搜索 (否则使用迭代加深)
LONG_MAX_DEPTH=6  # 非固定深度时的最大搜索深度
CLOUD_BOOK_ENABLED=0 # 是否启用云开局库查询
OPEN_NMP=1  # 是否启用空步裁剪 (Null Move Pruning)
LONG_MAX_TIME=75.0 # 非固定深度时的3步后默认最大思考时间 (秒)，可以根据需要调整

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

# --- 1. 修正后的基础子力价值 ---
# 逻辑：
# 1. 兵(未过河) = 60 ~ 80。过河后价值由 PST 决定(可达 150+)。
# 2. 车(1000) = 绝对主力。
# 3. 马/炮(450) = 约为车的 45%。
# 4. 士象(120) = 略高于未过河兵，防止 AI 为了贪吃弃士象（导致被杀）。

# --- 1. 基于 ElephantEye (象眼) 比例调整的子力价值 ---
# 解释：
# 1. 兵(100) 是基准。
# 2. 士/象(250) 必须很高！防止 AI 用士象去换对方的兵。丢士象=输一半。
# 3. 车(1000) 依然是王。
# 4. 马/炮(450) 保持标准。
PIECE_VALUES = {
    'k': 10000,     
    'r': 4, 
    'n': 3, 
    'c': 3, 
    'a': 2,  
    'b': 2,  
    'p': 1, 
    'K': 10000, 'R': 4, 'N': 3, 'C': 3, 'A': 2, 'B': 2, 'P': 1
}

# 1. 开中局、有进攻机会的帅(将)和兵(卒)
cucvlKingPawnMidgameAttacking = [
    [ 9,  9,  9, 11, 13, 11,  9,  9,  9],
    [39, 49, 69, 84, 89, 84, 69, 49, 39],
    [39, 49, 64, 74, 74, 74, 64, 49, 39],
    [39, 46, 54, 59, 61, 59, 54, 46, 39],
    [29, 37, 41, 54, 59, 54, 41, 37, 29],
    [ 7,  0, 13,  0, 16,  0, 13,  0,  7],
    [ 7,  0,  7,  0, 15,  0,  7,  0,  7],
    [ 0,  0,  0,  1,  1,  1,  0,  0,  0],
    [ 0,  0,  0,  2,  2,  2,  0,  0,  0],
    [ 0,  0,  0, 11, 15, 11,  0,  0,  0]
]

# 2. 开中局、没有进攻机会的帅(将)和兵(卒)
cucvlKingPawnMidgameAttackless = [
    [ 9,  9,  9, 11, 13, 11,  9,  9,  9],
    [19, 24, 34, 42, 44, 42, 34, 24, 19],
    [19, 24, 32, 37, 37, 37, 32, 24, 19],
    [19, 23, 27, 29, 30, 29, 27, 23, 19],
    [14, 18, 20, 27, 29, 27, 20, 18, 14],
    [ 7,  0, 13,  0, 16,  0, 13,  0,  7],
    [ 7,  0,  7,  0, 15,  0,  7,  0,  7],
    [ 0,  0,  0,  1,  1,  1,  0,  0,  0],
    [ 0,  0,  0,  2,  2,  2,  0,  0,  0],
    [ 0,  0,  0, 11, 15, 11,  0,  0,  0]
]

# 3. 残局、有进攻机会的帅(将)和兵(卒)
cucvlKingPawnEndgameAttacking = [
    [10, 10, 10, 15, 15, 15, 10, 10, 10],
    [50, 55, 60, 85,100, 85, 60, 55, 50],
    [65, 70, 70, 75, 75, 75, 70, 70, 65],
    [75, 80, 80, 80, 80, 80, 80, 80, 75],
    [70, 70, 65, 70, 70, 70, 65, 70, 70],
    [45,  0, 40, 45, 45, 45, 40,  0, 45],
    [40,  0, 35, 40, 40, 40, 35,  0, 40],
    [ 0,  0,  5,  5, 15,  5,  5,  0,  0],
    [ 0,  0,  3,  3, 13,  3,  3,  0,  0],
    [ 0,  0,  1,  1, 11,  1,  1,  0,  0]
]

# 4. 残局、没有进攻机会的帅(将)和兵(卒)
cucvlKingPawnEndgameAttackless = [
    [10, 10, 10, 15, 15, 15, 10, 10, 10],
    [10, 15, 20, 45, 60, 45, 20, 15, 10],
    [25, 30, 30, 35, 35, 35, 30, 30, 25],
    [35, 40, 40, 45, 45, 45, 40, 40, 35],
    [25, 30, 30, 35, 35, 35, 30, 30, 25],
    [25,  0, 25, 25, 25, 25, 25,  0, 25],
    [20,  0, 20, 20, 20, 20, 20,  0, 20],
    [ 0,  0,  5,  5, 13,  5,  5,  0,  0],
    [ 0,  0,  3,  3, 12,  3,  3,  0,  0],
    [ 0,  0,  1,  1, 11,  1,  1,  0,  0]
]

# 5. 没受威胁的仕(士)和相(象)
cucvlAdvisorBishopThreatless = [
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0, 20,  0,  0,  0, 20,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [18,  0,  0, 20, 23, 20,  0,  0, 18],
    [ 0,  0,  0,  0, 23,  0,  0,  0,  0],
    [ 0,  0, 20, 20,  0, 20, 20,  0,  0]
]


# 6. 受到威胁的仕(士)和相(象)
cucvlAdvisorBishopThreatened = [
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0, 40,  0,  0,  0, 40,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [38,  0,  0, 40, 43, 40,  0,  0, 38],
    [ 0,  0,  0,  0, 43,  0,  0,  0,  0],
    [ 0,  0, 40, 40,  0, 40, 40,  0,  0]
]

# 7. 开中局的马
cucvlKnightMidgame = [
    [90, 90, 90, 96, 90, 96, 90, 90, 90],
    [90, 96,103, 97, 94, 97,103, 96, 90],
    [92, 98, 99,103, 99,103, 99, 98, 92],
    [93,108,100,107,100,107,100,108, 93],
    [90,100, 99,103,104,103, 99,100, 90],
    [90, 98,101,102,103,102,101, 98, 90],
    [92, 94, 98, 95, 98, 95, 98, 94, 92],
    [93, 92, 94, 95, 92, 95, 94, 92, 93],
    [85, 90, 92, 93, 78, 93, 92, 90, 85],
    [88, 85, 90, 88, 90, 88, 90, 85, 88]
]

# 8. 残局的马
cucvlKnightEndgame = [
    [92, 94, 96, 96, 96, 96, 96, 94, 92],
    [94, 96, 98, 98, 98, 98, 98, 96, 94],
    [96, 98,100,100,100,100,100, 98, 96],
    [96, 98,100,100,100,100,100, 98, 96],
    [96, 98,100,100,100,100,100, 98, 96],
    [94, 96, 98, 98, 98, 98, 98, 96, 94],
    [94, 96, 98, 98, 98, 98, 98, 96, 94],
    [92, 94, 96, 96, 96, 96, 96, 94, 92],
    [90, 92, 94, 92, 92, 92, 94, 92, 90],
    [88, 90, 92, 90, 90, 90, 92, 90, 88]
]

# 9. 开中局的车
cucvlRookMidgame = [
    [206,208,207,213,214,213,207,208,206],
    [206,212,209,216,233,216,209,212,206],
    [206,208,207,214,216,214,207,208,206],
    [206,213,213,216,216,216,213,213,206],
    [208,211,211,214,215,214,211,211,208],
    [208,212,212,214,215,214,212,212,208],
    [204,209,204,212,214,212,204,209,204],
    [198,208,204,212,212,212,204,208,198],
    [200,208,206,212,200,212,206,208,200],
    [194,206,204,212,200,212,204,206,194]
]

# 10. 残局的车
cucvlRookEndgame = [
    [182,182,182,184,186,184,182,182,182],
    [184,184,184,186,190,186,184,184,184],
    [182,182,182,184,186,184,182,182,182],
    [180,180,180,182,184,182,180,180,180],
    [180,180,180,182,184,182,180,180,180],
    [180,180,180,182,184,182,180,180,180],
    [180,180,180,182,184,182,180,180,180],
    [180,180,180,182,184,182,180,180,180],
    [180,180,180,182,184,182,180,180,180],
    [180,180,180,182,184,182,180,180,180]
]

# 11. 开中局的炮
cucvlCannonMidgame = [
    [100,100, 96, 91, 90, 91, 96,100,100],
    [ 98, 98, 96, 92, 89, 92, 96, 98, 98],
    [ 97, 97, 96, 91, 92, 91, 96, 97, 97],
    [ 96, 99, 99, 98,100, 98, 99, 99, 96],
    [ 96, 96, 96, 96,100, 96, 96, 96, 96],
    [ 95, 96, 99, 96,100, 96, 99, 96, 95],
    [ 96, 96, 96, 96, 96, 96, 96, 96, 96],
    [ 97, 96,100, 99,101, 99,100, 96, 97],
    [ 96, 97, 98, 98, 98, 98, 98, 97, 96],
    [ 96, 96, 97, 99, 99, 99, 97, 96, 96]
]

# 12. 残局的炮
cucvlCannonEndgame = [
    [100,100,100,100,100,100,100,100,100],
    [100,100,100,100,100,100,100,100,100],
    [100,100,100,100,100,100,100,100,100],
    [100,100,100,102,104,102,100,100,100],
    [100,100,100,102,104,102,100,100,100],
    [100,100,100,102,104,102,100,100,100],
    [100,100,100,102,104,102,100,100,100],
    [100,100,100,102,104,102,100,100,100],
    [100,100,100,104,106,104,100,100,100],
    [100,100,100,104,106,104,100,100,100]
]

# --- 评估权重配置 (基于 Eleeye 简化) ---
USE_RELATION=0  # 是否启用关系与阵型评估
#可能不用才是好的，因为慢，且有hack二阶更加不准，并且pst有一阶的棋形功能了
# 棋形分
EV_HOLLOW_CANNON = 200    # 空头炮 (非常危险)
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
        self.current_score = 0#只维护子力了
        self.type_score = [
            [
                [
                    [0,0],
                    [0,0]
                ],
                [
                    [0,0],
                    [0,0]
                ],
                ],
            [
                    [0,0],
                    [0,0]
                ],
            [0,0]
            ] #帅兵，士象，车马炮的位置价值分，对称为0
        self.TOTAL_ATTACK_VALUE = 8
        self.ROOK_MIDGAME_VALUE = 6
        self.KNIGHT_CANNON_MIDGAME_VALUE = 3
        self.OTHER_MIDGAME_VALUE = 1 # 除了帅
        self.TOTAL_MIDGAME_VALUE= self.ROOK_MIDGAME_VALUE * 4 + self.KNIGHT_CANNON_MIDGAME_VALUE * 8 + self.OTHER_MIDGAME_VALUE * 18
        self.state_value = [self.TOTAL_MIDGAME_VALUE, [0, 0],0]
        # 现在是符合开局但是还是要重新置下，兼容调试局面。
        
        self.ADVISOR_BISHOP_ATTACKLESS_VALUE = 80;
        self.init_score()

        # --- 在类的 __init__ 中修改 ---
        self.tt_size = 1000003  # 一个足够大的素数
        # 每个条目存储: [zobrist_hash, depth, flag, score, best_move]
        # 初始化为 None 或固定长度列表以节省分配开销
        self.tt = [None] * self.tt_size
        # --- Zobrist 与 置换表 初始化 ---
        self.zobrist_table = {} # 存储每个棋子在每个位置的随机数
        self.zobrist_turn = random.getrandbits(64) # 轮到黑方走棋的随机数
        self.current_hash = 0
        # --- 新增：历史局面 Hash 表 ---
        self.history = [] 
        self.init_zobrist() # 生成随机数表
        self.init_hash() # 计算初始分数和初始Hash

        self.start_time = 0
        self.time_limit = float('inf') # 默认无限制，实际使用时会设置为具体秒数
        self.stop_search = False  # 中断标志
        self.nodes = 0           # 统计搜索量

        self.history_table = [[[[0]*9 for _ in range(10)] for _ in range(9)] for _ in range(10)]
        self.killer_moves = [[None, None] for _ in range(64)]


        
        # 1. 启动皮卡鱼 (确保 exe 在同级目录)
        try:
            self.pikafish = PikafishEvaluator("pikafish.exe")
            # print("成功连接皮卡鱼引擎用于评估！")
        except Exception as e:
            print(f"无法启动皮卡鱼: {e}")
            self.pikafish = None

        # 2. 添加一个评估缓存 (非常重要！否则太慢)
        self.eval_cache = {} 
        
    def init_score(self):
        self.current_score = 0
        # 1. 初始化分数结构
        # type_score:
        # [0] 帅兵: [0红,1黑][0中,1残][0有攻,1无攻]
        # [1] 士象: [0红,1黑][0无威胁,1有威胁]
        # [2] 车马炮: [0中,1残] (红减黑的净值)
        self.type_score = [
            [[[0, 0], [0, 0]], [[0, 0], [0, 0]]], 
            [[0, 0], [0, 0]], 
            [0, 0] 
        ]

        # state_value: [中局材力总分, [红进攻分, 黑进攻分], 车2马炮1威胁子分]
        self.state_value = [0, [0, 0],0]

        # --- 局部统计变量 (不存入 self) ---
        # 用于计算进攻分数
        red_crossing_attack = 0   # 红方过河子力分
        black_crossing_attack = 0 # 黑方过河子力分
        
        # 简易轻子分 (车=2, 马炮=1), 用于计算两方轻子差
        red_simple_value = 0
        black_simple_value = 0
        # 2. 遍历棋盘
        for r in range(10):
            for c in range(9):
                piece = self.board[r][c]
                if piece == '.':
                    continue
                self.current_score+=self.get_piece_value(piece)
                ptype = piece.lower()
                is_red = piece.isupper()
                side_idx = 0 if is_red else 1
                
                # 查表坐标：红方不变，黑方翻转行
                table_r = r if is_red else 9 - r
                table_c = c

                # --- A. 累加中局材力总分 (state_value[0]) ---
                # 依据: ROOK=6, N/C=3, OTHER=1 (帅除外)
                mat_val = 0
                if ptype == 'r':
                    mat_val = self.ROOK_MIDGAME_VALUE
                elif ptype in ['n', 'c']:
                    mat_val = self.KNIGHT_CANNON_MIDGAME_VALUE
                elif ptype != 'k': # 兵士象
                    mat_val = self.OTHER_MIDGAME_VALUE
                self.state_value[0] += mat_val

                # --- B. 统计进攻相关数据 (过河 & 轻子) ---
                # 这里的棋盘定义通常是: 0-4为上方(通常黑方基地), 5-9为下方(通常红方基地)
                # 红方过河: 行号 < 5; 黑方过河: 行号 > 4
                
                # 1. 过河子力分 (车马=2, 炮兵=1)
                river_val = 0
                if ptype in ['r', 'n']: 
                    river_val = 2
                elif ptype in ['c', 'p']: 
                    river_val = 1
                
                if is_red and r <= 4:
                    red_crossing_attack += river_val
                elif not is_red and r >= 5:
                    black_crossing_attack += river_val

                # 2. 轻子价值 (车=2, 马炮=1)
                simple_val = 0
                if ptype == 'r':
                    simple_val = 2
                elif ptype in ['n', 'c']:
                    simple_val = 1
                
                if is_red:
                    red_simple_value += simple_val
                else:
                    black_simple_value += simple_val

                # --- C. 查表填充 type_score ---
                # 1. 帅(将) 和 兵(卒)
                if ptype == 'k' or ptype == 'p':
                    # [side][0中/1残][0有攻/1无攻]
                    self.type_score[0][side_idx][0][0] += cucvlKingPawnMidgameAttacking[table_r][table_c]
                    self.type_score[0][side_idx][0][1] += cucvlKingPawnMidgameAttackless[table_r][table_c]
                    self.type_score[0][side_idx][1][0] += cucvlKingPawnEndgameAttacking[table_r][table_c]
                    self.type_score[0][side_idx][1][1] += cucvlKingPawnEndgameAttackless[table_r][table_c]

                # 2. 仕(士) 和 相(象)
                elif ptype == 'a' or ptype == 'b':
                    # [side][0无威胁/1有威胁]
                    self.type_score[1][side_idx][0] += cucvlAdvisorBishopThreatless[table_r][table_c]
                    self.type_score[1][side_idx][1] += cucvlAdvisorBishopThreatened[table_r][table_c]

                # 3. 车、马、炮
                elif ptype in ['r', 'n', 'c']:
                    mid_v = 0
                    end_v = 0
                    if ptype == 'r':
                        mid_v = cucvlRookMidgame[table_r][table_c]
                        end_v = cucvlRookEndgame[table_r][table_c]
                    elif ptype == 'n':
                        mid_v = cucvlKnightMidgame[table_r][table_c]
                        end_v = cucvlKnightEndgame[table_r][table_c]
                    elif ptype == 'c':
                        mid_v = cucvlCannonMidgame[table_r][table_c]
                        end_v = cucvlCannonEndgame[table_r][table_c]
                    
                    # 这里的 type_score[2] 存净分 (红 - 黑)
                    if is_red:
                        self.type_score[2][0] += mid_v
                        self.type_score[2][1] += end_v
                    else:
                        self.type_score[2][0] -= mid_v
                        self.type_score[2][1] -= end_v
        self.state_value[2]= red_simple_value - black_simple_value
        # 3. 结算进攻状态分 (state_value[1])
        # 规则: 如果本方轻子数比对方多，那么每多一个轻子(车算2个)威胁值加2
        red_bonus = 0
        black_bonus = 0
        
        if red_simple_value > black_simple_value:
            red_bonus = self.state_value[2] * 2
        elif black_simple_value > red_simple_value:
            black_bonus =self.state_value[2] * 2
            
        self.state_value[1][0] = red_crossing_attack + red_bonus
        self.state_value[1][1] = black_crossing_attack + black_bonus

    def evaluate(self):
        """
        使用皮卡鱼进行静态评估
        """
        # 如果皮卡鱼没启动，回退到原来的逻辑（或者直接返回0）
        if not USE_PIKAFISH:
            # 1. 计算中局/残局 权重 (Phase Weight)
            # 限制范围在 [0, 1] 之间，防止特殊情况溢出
            mid_val = self.state_value[0]
            mid_val = (2*self.TOTAL_MIDGAME_VALUE-mid_val)*mid_val/(self.TOTAL_MIDGAME_VALUE)#使用二次函数，子力很少时才认为接近残局
            ratio_mid = mid_val / self.TOTAL_MIDGAME_VALUE
            ratio_end = 1.0 - ratio_mid

            # 2. 计算进攻/威胁 权重 (Attack/Threat Factors)
            # 限制最大威胁值为 8
            # red_att_ratio: 红方进攻系数 (用于算红帅兵进攻分、黑士象受威胁分)
            # black_att_ratio: 黑方进攻系数 (用于算黑帅兵进攻分、红士象受威胁分)
            
            r_att_score = self.state_value[1][0]
            b_att_score = self.state_value[1][1]

            if r_att_score > self.TOTAL_ATTACK_VALUE : r_att_score = self.TOTAL_ATTACK_VALUE  # 其实要这步因为bonus
            if b_att_score > self.TOTAL_ATTACK_VALUE : b_att_score = self.TOTAL_ATTACK_VALUE 

            red_att_ratio = r_att_score / self.TOTAL_ATTACK_VALUE 
            red_no_att_ratio = 1.0 - red_att_ratio

            black_att_ratio = b_att_score / self.TOTAL_ATTACK_VALUE 
            black_no_att_ratio = 1.0 - black_att_ratio

            # ---------------------------------------------------------
            # 3. 计算各兵种位置分 (Position Scores)
            # ---------------------------------------------------------

            # A. 帅(将) 和 兵(卒) - type_score[0]
            # 结构: [side][phase][0:有攻, 1:无攻]
            # 逻辑: 先对"进攻状态"插值，再对"中残局"插值
            
            # 红方帅兵分
            # 中局 = (有攻 * 进攻系数) + (无攻 * 无攻系数)
            r_kp_mid = (self.type_score[0][0][0][0] * red_att_ratio + 
                        self.type_score[0][0][0][1] * red_no_att_ratio)
            # 残局
            r_kp_end = (self.type_score[0][0][1][0] * red_att_ratio + 
                        self.type_score[0][0][1][1] * red_no_att_ratio)
            # 最终红方KP = 中局 * 中局比 + 残局 * 残局比
            r_kp_final = r_kp_mid * ratio_mid + r_kp_end * ratio_end

            # 黑方帅兵分
            b_kp_mid = (self.type_score[0][1][0][0] * black_att_ratio + 
                        self.type_score[0][1][0][1] * black_no_att_ratio)
            b_kp_end = (self.type_score[0][1][1][0] * black_att_ratio + 
                        self.type_score[0][1][1][1] * black_no_att_ratio)
            b_kp_final = b_kp_mid * ratio_mid + b_kp_end * ratio_end

            # B. 仕(士) 和 相(象) - type_score[1]
            # 结构: [side][0:无威胁, 1:有威胁]
            # 逻辑: 取决于**对方**的进攻系数
            
            # 红方士象分 (受黑方威胁程度影响)
            # 如果黑方进攻强，取 index 1 (Threatened) 的比重就大
            r_ab_final = (self.type_score[1][0][1] * black_att_ratio + 
                        self.type_score[1][0][0] * black_no_att_ratio)

            # 黑方士象分 (受红方威胁程度影响)
            b_ab_final = (self.type_score[1][1][1] * red_att_ratio + 
                        self.type_score[1][1][0] * red_no_att_ratio)

            # C. 车、马、炮 - type_score[2]
            # 结构: [0:中局, 1:残局] (已存储为 红 - 黑 的净值)
            rnc_final = (self.type_score[2][0] * ratio_mid + 
                        self.type_score[2][1] * ratio_end)

            # ---------------------------------------------------------
            # 4. 汇总总分
            # ---------------------------------------------------------
            # 基础子力分 + (红帅兵 - 黑帅兵) + (红士象 - 黑士象) + 车马炮净分
            total_eval = (self.current_score + 
                        (r_kp_final - b_kp_final) + 
                        (r_ab_final - b_ab_final) + 
                        rnc_final)
            #  // 调整不受威胁方少掉的仕(士)相(象)分值
            r_vl= self.ADVISOR_BISHOP_ATTACKLESS_VALUE * (self.TOTAL_ATTACK_VALUE - b_att_score) / self.TOTAL_ATTACK_VALUE
            b_vl= self.ADVISOR_BISHOP_ATTACKLESS_VALUE * (self.TOTAL_ATTACK_VALUE - r_att_score) / self.TOTAL_ATTACK_VALUE
            total_eval += r_vl - b_vl

            return int(total_eval)
            
        
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


    def get_piece_value(self, piece, r=None, c=None):
        """辅助函数：获取单个棋子的分数"""
        if piece == '.': return 0
        
        val = PIECE_VALUES.get(piece, 0)
        total = val 
        return total if self.is_red(piece) else -total
    
    def init_hash(self):
        """初始化计算 分数 和 Hash"""
        self.current_hash = 0
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p != '.':
                    self.current_hash ^= self.zobrist_table[(r, c, p)]
        
        # 如果初始是黑方走，需要异或 turn 的随机数（通常开局是红方，不做处理）
        if self.turn == 'black':
            self.current_hash ^= self.zobrist_turn
        self.history = [self.current_hash]    
    def _get_piece_info(self, piece, r, c):
        """
        辅助函数：获取一个棋子在(r,c)处的所有评估属性
        返回: (mid_val, crossing_val, simple_val, type_updates)
        """
        if piece == '.':
            return 0, 0, 0, []

        ptype = piece.lower()
        is_red = piece.isupper()
        side_idx = 0 if is_red else 1
        
        # 查表坐标转换
        table_r = r if is_red else 9 - r
        table_c = c

        # 1. 中局材力分 (state_value[0])
        mid_val = 0
        if ptype == 'r': mid_val = self.ROOK_MIDGAME_VALUE
        elif ptype in ['n', 'c']: mid_val = self.KNIGHT_CANNON_MIDGAME_VALUE
        elif ptype != 'k': mid_val = self.OTHER_MIDGAME_VALUE

        # 2. 进攻分组件 (state_value[1] 的基础过河分部分)
        crossing_val = 0
        if is_red and r <= 4: # 红过河
            if ptype in ['r', 'n']: crossing_val = 2
            elif ptype in ['c', 'p']: crossing_val = 1
        elif not is_red and r >= 5: # 黑过河
            if ptype in ['r', 'n']: crossing_val = 2
            elif ptype in ['c', 'p']: crossing_val = 1
            
        # 3. 轻子分 (用于维护 state_value[2])
        simple_val = 0
        if ptype == 'r': simple_val = 2
        elif ptype in ['n', 'c']: simple_val = 1

        # 4. 位置分更新列表 (type_score)
        type_updates = []
        
        if ptype == 'k' or ptype == 'p':
            v1 = cucvlKingPawnMidgameAttacking[table_r][table_c]
            v2 = cucvlKingPawnMidgameAttackless[table_r][table_c]
            v3 = cucvlKingPawnEndgameAttacking[table_r][table_c]
            v4 = cucvlKingPawnEndgameAttackless[table_r][table_c]
            # (类别, side, phase, attack_flag, value)
            type_updates.append((0, side_idx, 0, 0, v1))
            type_updates.append((0, side_idx, 0, 1, v2))
            type_updates.append((0, side_idx, 1, 0, v3))
            type_updates.append((0, side_idx, 1, 1, v4))
            
        elif ptype == 'a' or ptype == 'b':
            v1 = cucvlAdvisorBishopThreatless[table_r][table_c]
            v2 = cucvlAdvisorBishopThreatened[table_r][table_c]
            # (类别, side, threatened_flag, value)
            type_updates.append((1, side_idx, 0, v1))
            type_updates.append((1, side_idx, 1, v2))

        elif ptype in ['r', 'n', 'c']:
            mid_v = 0
            end_v = 0
            if ptype == 'r':
                mid_v = cucvlRookMidgame[table_r][table_c]
                end_v = cucvlRookEndgame[table_r][table_c]
            elif ptype == 'n':
                mid_v = cucvlKnightMidgame[table_r][table_c]
                end_v = cucvlKnightEndgame[table_r][table_c]
            elif ptype == 'c':
                mid_v = cucvlCannonMidgame[table_r][table_c]
                end_v = cucvlCannonEndgame[table_r][table_c]
            
            # 红加黑减
            sign = 1 if is_red else -1
            # (类别, phase, value)
            type_updates.append((2, 0, sign * mid_v))
            type_updates.append((2, 1, sign * end_v))

        return mid_val, crossing_val, simple_val, type_updates

    def _apply_type_updates(self, updates, sign):
        """
        应用位置分更新
        sign: -1 表示移出(减分), 1 表示移入(加分)
        """
        for entry in updates:
            category = entry[0]
            if category == 0: # 帅兵
                _, side, ph, att, val = entry
                self.type_score[0][side][ph][att] += sign * val
            elif category == 1: # 士象
                _, side, threat, val = entry
                self.type_score[1][side][threat] += sign * val
            elif category == 2: # 车马炮
                _, ph, val = entry
                self.type_score[2][ph] += sign * val

    def make_move(self, start, end):
        r1, c1 = start
        r2, c2 = end
        moving_piece = self.board[r1][c1]
        captured_piece = self.board[r2][c2]

        # -----------------------------------------------------
        # 1. 剥离旧的轻子差 Bonus
        # -----------------------------------------------------
        # 此时 state_value[2] 是移动前的 (红轻 - 黑轻)
        diff = self.state_value[2]
        if diff > 0:
            self.state_value[1][0] -= diff * 2 # 红多，减去红的加分
        elif diff < 0:
            self.state_value[1][1] -= (-diff) * 2 # 黑多，减去黑的加分

        # -----------------------------------------------------
        # 2. 获取增量信息
        # -----------------------------------------------------
        # 移出起点
        m_mid, m_cross, m_simp, m_updates = self._get_piece_info(moving_piece, r1, c1)
        # 移出被吃子
        c_mid, c_cross, c_simp, c_updates = self._get_piece_info(captured_piece, r2, c2)
        # 移入终点
        m_dest_mid, m_dest_cross, m_dest_simp, m_dest_updates = self._get_piece_info(moving_piece, r2, c2)

        # -----------------------------------------------------
        # 3. 更新各项分数
        # -----------------------------------------------------
        
        # A. Current Score (基础子力)
        self.current_score -= self.get_piece_value(moving_piece, r1, c1)
        if captured_piece != '.':
            self.current_score -= self.get_piece_value(captured_piece, r2, c2)
        self.current_score += self.get_piece_value(moving_piece, r2, c2)

        # B. state_value[0] (中局材力分)
        # 移动子：减起点加终点(值一样抵消)；被吃子：减被吃
        # 写全为了逻辑清晰，实际上 m_mid == m_dest_mid
        self.state_value[0] = self.state_value[0] - m_mid - c_mid + m_dest_mid

        # C. state_value[1] (过河威胁分 - 基础部分)
        is_red_move = moving_piece.isupper()
        if is_red_move: 
            self.state_value[1][0] += (m_dest_cross - m_cross)
        else:           
            self.state_value[1][1] += (m_dest_cross - m_cross)
            
        if captured_piece != '.':
            if captured_piece.isupper(): 
                self.state_value[1][0] -= c_cross
            else:                        
                self.state_value[1][1] -= c_cross

        # D. type_score (位置分)
        self._apply_type_updates(m_updates, -1)
        if captured_piece != '.':
            self._apply_type_updates(c_updates, -1)
        self._apply_type_updates(m_dest_updates, 1)

        # E. state_value[2] (轻子净分 Red - Black)
        # 移动本身不改变数量，只有吃子改变数量
        if captured_piece != '.':
            if captured_piece.isupper(): # 红被吃
                self.state_value[2] -= c_simp
            else:                        # 黑被吃
                self.state_value[2] += c_simp # (Red - (Black - val)) = diff + val

        # -----------------------------------------------------
        # 4. 应用新的轻子差 Bonus
        # -----------------------------------------------------
        new_diff = self.state_value[2]
        if new_diff > 0:
            self.state_value[1][0] += new_diff * 2
        elif new_diff < 0:
            self.state_value[1][1] += (-new_diff) * 2

        # -----------------------------------------------------
        # 5. 棋盘与Hash操作
        # -----------------------------------------------------
        self.current_hash ^= self.zobrist_table[(r1, c1, moving_piece)]
        if captured_piece != '.':
            self.current_hash ^= self.zobrist_table[(r2, c2, captured_piece)]
        self.current_hash ^= self.zobrist_table[(r2, c2, moving_piece)]
        self.current_hash ^= self.zobrist_turn

        self.board[r2][c2] = moving_piece
        self.board[r1][c1] = '.'
        self.turn = 'black' if self.turn == 'red' else 'red'
        
        self.history.append(self.current_hash)
        return captured_piece

    def undo_move(self, start, end, captured):
        self.history.pop()
        r1, c1 = start
        r2, c2 = end
        moved_piece = self.board[r2][c2] # 此时棋子在终点

        # -----------------------------------------------------
        # 1. 剥离当前(Undo前)的轻子差 Bonus
        # -----------------------------------------------------
        diff = self.state_value[2]
        if diff > 0:
            self.state_value[1][0] -= diff * 2
        elif diff < 0:
            self.state_value[1][1] -= (-diff) * 2

        # -----------------------------------------------------
        # 2. 获取增量信息 (对称操作)
        # -----------------------------------------------------
        m_dest_mid, m_dest_cross, m_dest_simp, m_dest_updates = self._get_piece_info(moved_piece, r2, c2)
        m_src_mid, m_src_cross, m_src_simp, m_src_updates = self._get_piece_info(moved_piece, r1, c1)
        c_mid, c_cross, c_simp, c_updates = self._get_piece_info(captured, r2, c2)

        # -----------------------------------------------------
        # 3. 还原各项分数
        # -----------------------------------------------------
        
        # A. Current Score
        self.current_score -= self.get_piece_value(moved_piece, r2, c2)
        self.current_score += self.get_piece_value(moved_piece, r1, c1)
        if captured != '.':
            self.current_score += self.get_piece_value(captured, r2, c2)

        # B. state_value[0]
        self.state_value[0] = self.state_value[0] - m_dest_mid + m_src_mid + c_mid

        # C. state_value[1] (过河分)
        is_red = moved_piece.isupper()
        # 撤销移动的过河分变化
        if is_red:
            self.state_value[1][0] -= (m_dest_cross - m_src_cross)
        else:
            self.state_value[1][1] -= (m_dest_cross - m_src_cross)
        
        # 恢复被吃子的过河分
        if captured != '.':
            if captured.isupper():
                self.state_value[1][0] += c_cross
            else:
                self.state_value[1][1] += c_cross

        # D. type_score
        self._apply_type_updates(m_dest_updates, -1) # 移出当前
        self._apply_type_updates(m_src_updates, 1)   # 回到起点
        if captured != '.':
            self._apply_type_updates(c_updates, 1)   # 复活被吃

        # E. state_value[2] (轻子净分) - 逆向操作
        if captured != '.':
            if captured.isupper(): # 恢复红子
                self.state_value[2] += c_simp
            else:                  # 恢复黑子
                self.state_value[2] -= c_simp

        # -----------------------------------------------------
        # 4. 加回旧的(Undo后)轻子差 Bonus
        # -----------------------------------------------------
        prev_diff = self.state_value[2]
        if prev_diff > 0:
            self.state_value[1][0] += prev_diff * 2
        elif prev_diff < 0:
            self.state_value[1][1] += (-prev_diff) * 2

        # -----------------------------------------------------
        # 5. 还原棋盘与Hash
        # -----------------------------------------------------
        self.current_hash ^= self.zobrist_turn
        self.current_hash ^= self.zobrist_table[(r2, c2, moved_piece)]
        if captured != '.':
            self.current_hash ^= self.zobrist_table[(r2, c2, captured)]
        self.current_hash ^= self.zobrist_table[(r1, c1, moved_piece)]

        self.board[r1][c1] = moved_piece
        self.board[r2][c2] = captured
        self.turn = 'black' if self.turn == 'red' else 'red'
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
                    # 检查左右是否有友军只检查一侧即可
                    if c > 0 and self.board[r][c-1] == 'P': score += EV_LINKED_PAWNS
                elif p == 'p' and r >= 5: # 黑卒过河
                    if c > 0 and self.board[r][c-1] == 'p': score -= EV_LINKED_PAWNS

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
                    low, high = min(mid_pieces[c_idx][0], black_king[0]), max(mid_pieces[c_idx][0], black_king[0])
                    for check_r in range(low + 1, high):
                        if self.board[check_r][4] != '.': blockers += 1
                    
                    if blockers == 0: score += EV_HOLLOW_CANNON  # 空头炮！致命
                    elif blockers <=2: score += EV_CENTRAL_CANNON # 中炮
        
        # 黑方中炮/空头炮
        if mid_info['B_cannon'] > 0:
            c_idx = -1
            for i, (r, p) in enumerate(mid_pieces):
                if p == 'c': c_idx = i; break
            
            if c_idx != -1:
                if red_king and red_king[1] == 4:
                    blockers = 0
                    # 统计炮和黑将之间的子
                    low, high = min(mid_pieces[c_idx][0], red_king[0]), max(mid_pieces[c_idx][0], red_king[0])
                    for check_r in range(low + 1, high):
                        if self.board[check_r][4] != '.': blockers += 1
                    
                    if blockers == 0: score -= EV_HOLLOW_CANNON
                    elif blockers <=2: score -= EV_CENTRAL_CANNON

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
    def quiescence_search(self, alpha, beta, maximizing_player, qs_depth=0):
        # 1. 检查是否被将军 (这是 QS 中最昂贵但也最必要的操作，部分引擎会从外部传入状态以优化)
        in_check = self.is_in_check(maximizing_player)

        # 2. Stand Pat (静止评估)
        # 只有在【不被将军】的情况下，才有资格选择“不走棋”
        if not in_check:
            score = self.evaluate() # 建议统一用 evaluate，保证分数标准统一
            
            if maximizing_player:
                if score >= beta: return beta
                if score > alpha: alpha = score
            else:
                if score <= alpha: return alpha
                if score < beta: beta = score
        
        # 3. 深度限制防止爆炸
        # 如果搜太深，强制返回。注意：如果被将军且无路可走，这里返回评估分可能不准，
        # 但为了防止死循环只能妥协。通常 10 层 QS 已经极深了。
        if qs_depth > 10:
            return self.evaluate()

        # 4. 生成着法
        # 优化：通常引擎会有 generate_capture_moves() 和 generate_all_moves() 两个方法
        if in_check:
            # 被将军：必须生成所有逃生步（包括不吃子的移动）
            # 这里的 get_all_moves 必须包含挡将、躲将
            moves = self.get_all_moves(maximizing_player)
        else:
            # 未被将军：只生成吃子步
            # 这里建议优化你的底层代码，不要生成所有步再过滤，直接只生成吃子步效率高很多
            all_moves = self.get_all_moves(maximizing_player)
            moves = []
            for start, end in all_moves:
                # 目标格有子 = 吃子
                if self.board[end[0]][end[1]] != '.':
                    moves.append((start, end))

        # MVV-LVA 排序
        moves.sort(key=lambda m: PIECE_VALUES.get(self.board[m[1][0]][m[1][1]], 0), reverse=True)

        # 5. 遍历着法
        has_legal_move = False
        
        for start, end in moves:
            # 模拟走棋
            captured = self.make_move(start, end)
            
            # 【重要】走完之后检查自己是否还在被将军（处理非法的逃生步）
            # 如果你的 get_all_moves 已经是伪合法的（可能包含送将），需要这一步
            # 如果你的 get_all_moves 严格保证合法，这步可省略，但在 QS 中通常是伪合法生成
            if self.is_in_check(maximizing_player):
                self.undo_move(start, end, captured)
                continue
            
            has_legal_move = True
            
            score = self.quiescence_search(alpha, beta, not maximizing_player, qs_depth + 1)
            
            self.undo_move(start, end, captured)
            
            if maximizing_player:
                if score >= beta: return beta
                if score > alpha: alpha = score
            else:
                if score <= alpha: return alpha
                if score < beta: beta = score

        # 6. 处理被将军但无棋可走的情况 (Checkmate)
        if in_check and not has_legal_move:
            # 这是一个绝杀局面
            # 返回一个极小值 (注意层数调整，越早被杀分越低)
            return -SCORE_INF + qs_depth if maximizing_player else SCORE_INF - qs_depth

        # 如果不是被将军，只是没有吃子步了，或者所有吃子步都亏，
        # alpha (max) 或 beta (min) 已经保留了 stand_pat 的值，直接返回即可
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
        self.history.append(self.current_hash) # 新增

    def undo_null_move(self):
        """撤销空步：操作完全一样"""
        self.history.pop() # 新增
        self.turn = 'black' if self.turn == 'red' else 'red'
        self.current_hash ^= self.zobrist_turn
    def minimax(self, depth, alpha, beta, maximizing_player, allow_null=True):
        self.nodes += 1
        # --- 新增：检测重复局面 ---
        # 如果当前 Hash 在历史列表中出现的次数大于1（包含刚才 make_move 加入的那次），说明重复了
        # 这意味着：如果走了这一步，局面与之前的某个时候一模一样
        if self.history.count(self.current_hash) > 1:
            # 这是一个重复局面。
            # 通常判为和棋 (0分)。如果AI发现 0分 比输棋(-10000)好，它就会选择重复（长将保命）。
            # 如果AI有赢棋走法(+100)，它就不会走这一步。
            # 这样既避免了死循环，又符合象棋规则逻辑。
            return 0, None
        # 0. 检查超时
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
        if not kings[0]: return -SCORE_INF + depth, None 
        if not kings[1]: return SCORE_INF - depth, None 

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
            return (-SCORE_INF if maximizing_player else SCORE_INF), None

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

        moves.sort(key=move_sorter, reverse=True)#5 8在第12

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
                    if moves_count > 15 and do_lmr: reduction = 2
                    
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
            if elapsed > max_time * 0.16: break # 剩余时间预警

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
                                        captured_piece = self.make_move((r1,c1),(r2,c2))
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
                        DEPTH =2
                    else:
                        DEPTH = LONG_MAX_DEPTH # 中后期加深到6层
                    print(f">>> AI 正在思考 (深度 {DEPTH})...")
                    val, best = self.minimax(DEPTH, -float(SCORE_INF ), float(SCORE_INF ), is_ai_red)
                else:
                    MAX_TIME = 10.0 if  cnt<=3 else LONG_MAX_TIME  # 每步最多思考 10 秒(仅在非固定深度时生效) 
                    print(f">>> AI 正在思考 (限时 {MAX_TIME} 秒)...")
                    val, best = self.search_main(MAX_TIME, is_ai_red)
                
                
                print(f"思考耗时: {time.time()-t0:.2f}s, 评估分: {val}")
                
                if best:
                    captured_piece = self.make_move(best[0], best[1])
                    # AI 走完稍微暂停一下让人看清
                    time.sleep(1)
                else:
                    print("AI 认输 (被绝杀或无棋可走)")
                    self.game_over = True
            if captured_piece != '.':
                self.history = [self.current_hash]
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
def start_engine(long_max_depth=LONG_MAX_DEPTH):
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
            captured_piece = engine.make_move((int(r1),int(c1)), (int(r2),int(c2)))
            if captured_piece != '.':
                engine.history = [engine.current_hash]

        elif cmd.startswith("search"):
            t0 = time.time()
            cnt+=1
            is_ai_red = (engine.player_side == 'black')
            if USE_DEPTH:
                if cnt<=3:
                    DEPTH = 5
                else:
                    DEPTH = long_max_depth # 中后期加深到6层
                val, best = engine.minimax(DEPTH, -float(SCORE_INF ), float(SCORE_INF ), is_ai_red)
            else:
                MAX_TIME = 10.0 if  cnt<=3 else LONG_MAX_TIME # 每步最多思考 10 秒(仅在非固定深度时生效) 
                print(f">>> AI 正在思考 (限时 {MAX_TIME} 秒)...")
                val, best = engine.search_main(MAX_TIME, is_ai_red)

            if best:
                (r1,c1),(r2,c2) = best
                captured_piece=engine.make_move(best[0], best[1])
                if captured_piece != '.':
                    engine.history = [engine.current_hash]
                print(f"move {r1} {c1} {r2} {c2}", flush=True)
            else:
                print("resign", flush=True)
            with open("log.txt", "a", encoding="utf-8") as f:
                print(f"思考耗时: {time.time()-t0:.2f}s, 评估分: {val} ", file=f)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        XiangqiCLI().start_game()
    elif len(sys.argv) > 1:
        start_engine(int(sys.argv[1]))
    else:
        start_engine()


