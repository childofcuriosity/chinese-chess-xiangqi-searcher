import sys
import os
import copy
import time
import random
import urllib.request
# --- 1. 配置与显示颜色 ---
USE_DEPTH=0  # 是否使用固定深度搜索 (否则使用迭代加深)
CLOUD_BOOK_ENABLED=1  # 是否启用云开局库查询
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
PIECE_VALUES = {
    'k': 10000, 'r': 900, 'n': 430, 'c': 450, 'a': 20, 'b': 20, 'p': 10,
    'K': 10000, 'R': 900, 'N': 430, 'C': 450, 'A': 20, 'B': 20, 'P': 10
}

# --- PST (Piece-Square Tables) 位置价值表 ---
# 所有的表都是基于红方视角 (Row 0是底线, Row 9是敌方底线)
# 黑方使用时，代码会自动翻转 (Row = 9 - Row)

# 兵：过河前无分，过河后逼近九宫格分数暴涨
pst_pawn = [
    [  0,  3,  6,  9, 12,  9,  6,  3,  0], # 9 (敌底)
    [ 18, 36, 56, 80,120, 80, 56, 36, 18],
    [ 14, 26, 42, 60, 80, 60, 42, 26, 14],
    [ 10, 20, 30, 34, 40, 34, 30, 20, 10], # 6 (卒林)
    [  6, 12, 18, 18, 20, 18, 18, 12,  6], # 5 (河界)
    [  2,  0,  8,  0,  8,  0,  8,  0,  2], # 4 (河界)
    [  0,  0, -2,  0,  4,  0, -2,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0]  # 0 (我底)
]

# 车：抢占要道，控制河界
pst_rook = [
    [ 14, 14, 12, 18, 16, 18, 12, 14, 14],
    [ 16, 20, 18, 24, 26, 24, 18, 20, 16],
    [ 12, 12, 12, 18, 18, 18, 12, 12, 12],
    [ 12, 18, 16, 22, 22, 22, 16, 18, 12],
    [ 12, 16, 14, 20, 20, 20, 14, 16, 12],
    [ 12, 16, 14, 20, 20, 20, 14, 16, 12],
    [  6, 10,  8, 14, 14, 14,  8, 10,  6],
    [  4,  8,  6, 14, 12, 14,  6,  8,  4],
    [  8,  4,  8, 16,  8, 16,  8,  4,  8],
    [ -6, 10,  4,  6,  2,  6,  4, 10, -6]
]

# 马：鼓励跳向中心，过河后占领卧槽/挂角位
pst_knight = [
    [  4,  8, 16, 12,  4, 12, 16,  8,  4],
    [  4, 10, 28, 16,  8, 16, 28, 10,  4],
    [ 12, 14, 16, 20, 18, 20, 16, 14, 12], # 7行 (卧槽)
    [  8, 24, 18, 24, 20, 24, 18, 24,  8],
    [  6, 16, 14, 18, 16, 18, 14, 16,  6],
    [  4, 12, 16, 14, 12, 14, 16, 12,  4],
    [  2,  6,  8,  6, 10,  6,  8,  6,  2],
    [  4,  2,  8,  8,  4,  8,  8,  2,  4], # 初始位置
    [  0,  2,  4,  4, -2,  4,  4,  2,  0],
    [  0, -4,  0,  0,  0,  0,  0, -4,  0]
]

# 炮：中炮(Col 4)加分，巡河炮(Row 5/4)加分
pst_cannon = [
    [  6,  4,  0, -10, -12, -10,  0,  4,  6],
    [  2,  2,  0, -4, -14, -4,  0,  2,  2],
    [  2,  2,  0, -10, -8, -10,  0,  2,  2],
    [  0,  0, -2,  4, 10,  4, -2,  0,  0],
    [  0,  0,  0,  2,  4,  2,  0,  0,  0],
    [ -2,  0,  4,  2,  6,  2,  4,  0, -2],
    [  0,  0,  0,  2,  0,  2,  0,  0,  0],
    [  4,  0,  8,  6, 10,  6,  8,  0,  4], # 2行 (炮架)
    [  0,  2,  4,  6,  6,  6,  4,  2,  0],
    [  0,  0,  2,  6,  6,  6,  2,  0,  0]
]

# 士相：保持阵型
pst_advisor = [[0]*9 for _ in range(10)]
pst_advisor[0] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
pst_advisor[1] = [0, 0, 0, -2, 0, -2, 0, 0, 0]
pst_advisor[2] = [0, 0, 0, 0, 2, 0, 0, 0, 0] # 归心

pst_bishop = [[0]*9 for _ in range(10)]
pst_bishop[0] = [0, 0, 2, 0, 0, 0, 2, 0, 0]
pst_bishop[2] = [0, 0, 0, 0, 2, 0, 0, 0, 0]
pst_bishop[4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]

PST_MAP = {
    'r': pst_rook,   'R': pst_rook,
    'n': pst_knight, 'N': pst_knight,
    'c': pst_cannon, 'C': pst_cannon,
    'p': pst_pawn,   'P': pst_pawn,
    'a': pst_advisor,'A': pst_advisor,
    'b': pst_bishop, 'B': pst_bishop
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

    def evaluate(self):
        """
        综合评估：基础子力 + PST位置分 + 机动性动态分
        """
        # 1. 基础分 (增量更新的)
        base_score = self.current_score
        
        # 2. 机动性分 (实时计算)
        # 注意：这里会稍微降低速度，但能显著提高棋力
        # mob_score = self.calculate_mobility(self.turn == 'red')
        
        return base_score #+ mob_score
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
        stand_pat = self.evaluate()
        
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
    def minimax(self, depth, alpha, beta, maximizing_player):
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
        if OPEN_NMP and depth >= 3 and not in_check:
            self.make_null_move()
            R = 2
            # 这里的递归必须保证 depth 减小
            val, _ = self.minimax(depth - 1 - R, beta - 1, beta, not maximizing_player)
            self.undo_null_move()
            
            if self.stop_search: return 0, None
            
            if maximizing_player:
                if val >= beta: return beta, None
            else:
                if val <= alpha: return alpha, None

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
            
            # --- PVS & LMR ---
            # 只有当不是被将军状态时，才敢大胆进行 LMR 裁剪
            do_lmr = (depth >= 3 and moves_count > 4 and 
                      captured == '.' and not in_check)
            
            if maximizing_player:
                if moves_count == 1:
                    score, _ = self.minimax(depth - 1, alpha, beta, False)
                else:
                    reduction = 1 if do_lmr else 0
                    if moves_count > 10 and do_lmr: reduction = 2
                    
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
                    MAX_TIME = 10.0 if  cnt<=3 else 60.0  # 每步最多思考 10 秒(仅在非固定深度时生效) 
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
                
                # 筛选规则：分数不低于最高分 10 分
                max_score = moves[0]['score']
                candidates = [m for m in moves if m['score'] >= max_score - 10]
                
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
                MAX_TIME = 10.0 if  cnt<=3 else 60.0 # 每步最多思考 10 秒(仅在非固定深度时生效) 
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


