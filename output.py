import subprocess
import re
import sys
import os
import copy
import time
import random
import urllib.request
                    
CLOUD_BOOK_ENABLED=1             
USE_DEPTH=0                                   
LONG_MAX_DEPTH=6                 
OPEN_NMP=1                                
LONG_MAX_TIME=75.0                                  


ROWS = 10
COLS = 9



PIECE_CHARS = {
    'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅', 'C': '炮', 'P': '兵',
    'r': '车', 'n': '马', 'b': '象', 'a': '士', 'k': '将', 'c': '炮', 'p': '卒',
    '.': '．' 
}
SCORE_INF = 30000 


                            

                       
     
                                             
                    
                         
                                           

                                          
     
                
                                           
                  
                   
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
                                        
                                         
                                     
                               
                          
                                  
                               
                                 
                                
                                
                       

         
        
        
        
       
      
        
        

            
                         
                                              
pst_pawn = [
    [ 9,  9,  9, 11, 13, 11,  9,  9,  9,],                 
    [ 39, 49, 69, 84, 89, 84, 69, 49, 39, ],                      
    [ 39, 49, 64, 74, 74, 74, 64, 49, 39, ],             
    [39, 46, 54, 59, 61, 59, 54, 46, 39,],             
    [29, 37, 41, 54, 59, 54, 41, 37, 29,],                  
    [ 7,  0, 13,  0, 16,  0, 13,  0,  7, ],             
    [  7,  0,  7,  0, 15,  0,  7,  0,  7, ],             
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],        
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],        
    [  0,  0,  0,  0,  0,  0,  0,  0,  0]         
]

for i in range(len(pst_pawn)):
    for j in range(len(pst_pawn[i])):
        pst_pawn[i][j] += 10    

              
                      
                      
                      
               

            
          
                                           
pst_king = [
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,   1,  1,  1,  0,  0,  0],            
    [  0,  0,  0,   2,  2,  2,  0,  0,  0],            
    [  0,  0,  0,  11, 15, 11,  0,  0,  0]             
]

               
                                          
              
pst_advisor = [
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0, 30,  0, 30,  0,  0,  0],             
    [  0,  0,  0,  0, 33,  0,  0,  0,  0],            
    [  0,  0,  0, 30,  0, 30,  0,  0,  0]             
]

              
                          
                               
pst_bishop = [
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0, 30,  0,  0,  0, 30,  0,  0],             
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 28,  0,  0,  0, 33,  0,  0,  0, 28],               
    [  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0, 30,  0,  0,  0, 30,  0,  0]             
]

            
            
                                 
pst_knight = [
    [  90, 90, 90, 96, 90, 96, 90, 90, 90,],            
    [  90, 96,103, 97, 94, 97,103, 96, 90,],               
    [92, 98, 99,103, 99,103, 99, 98, 92, ],             
    [  93,108,100,107,100,107,100,108, 93,],             
    [ 93, 99, 99,101,102,101, 99, 99, 93],             
    [  90,100, 99,103,104,103, 99,100, 90, ],             
    [ 90, 98,101,102,103,102,101, 98, 90, ],            
    [92, 94, 98, 95, 98, 95, 98, 94, 92,],            
    [  85, 90, 92, 93, 78, 93, 92, 90, 85, ],        
    [  88, 85, 90, 88, 90, 88, 90, 85, 88,]                
]

          
            
                              
pst_rook = [
    [206,208,207,213,214,213,207,208,206,],                 
    [206,212,209,216,233,216,209,212,206, ],              
    [206,208,207,214,216,214,207,208,206, ],        
    [206,213,213,216,216,216,213,213,206,],               
    [208,211,211,214,215,214,211,211,208,],                   
    [208,212,212,214,215,214,212,212,208,],             
    [204,209,204,212,214,212,204,209,204,],        
    [198,208,204,212,212,212,204,208,198,],        
    [200,208,206,212,200,212,206,208,200,],        
    [194,206,204,212,200,212,204,206,194,]             
]

            
            
                                  
pst_cannon = [
    [100,100, 96, 91, 90, 91, 96,100,100, ],            
    [98, 98, 96, 92, 89, 92, 96, 98, 98,],        
    [ 97, 97, 96, 91, 92, 91, 96, 97, 97, ],             
    [ 96, 99, 99, 98,100, 98, 99, 99, 96,],        
    [ 96, 96, 96, 96,100, 96, 96, 96, 96, ],             
    [ 95, 96, 99, 96,100, 96, 99, 96, 95, ],             
    [ 96, 96, 96, 96, 96, 96, 96, 96, 96, ],        
    [97, 96,100, 99,101, 99,100, 96, 97,],               
    [96, 97, 98, 98, 98, 98, 98, 97, 96,],        
    [ 96, 96, 97, 99, 99, 99, 97, 96, 96,]                   
]

PST_MAP = {
    'k': pst_king,   'K': pst_king,
    'r': pst_rook,   'R': pst_rook,
    'n': pst_knight, 'N': pst_knight,
    'c': pst_cannon, 'C': pst_cannon,
    'p': pst_pawn,   'P': pst_pawn,
    'a': pst_advisor,'A': pst_advisor,
    'b': pst_bishop, 'B': pst_bishop
}


                               
USE_RELATION=0               
                                         
     
EV_HOLLOW_CANNON = 200                
EV_CENTRAL_CANNON = 50             
EV_LINKED_PAWNS = 30                  
EV_ROOK_TRAPPED = -50                 
EV_FULL_GUARDS = 40                   

     
EV_ATTACK_KING = 20                     

                  
EV_MOBILITY = {
    'r': 6,  'n': 12, 'c': 6,            
    'R': 6,  'N': 12, 'C': 6
}
                 
                
TT_EXACT = 0        
TT_ALPHA = 1                             
TT_BETA  = 2                              

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
        

                                  
        self.tt_size = 1000003            
                                                               
                                  
        self.tt = [None] * self.tt_size
                                   
        self.zobrist_table = {}                  
        self.zobrist_turn = random.getrandbits(64)             
        self.current_hash = 0
                                
        self.history = [] 
        self.init_zobrist()         
        self.init_score_and_hash()                

        self.start_time = 0
        self.time_limit = float('inf')                      
        self.stop_search = False        
        self.nodes = 0                  

        self.history_table = [[[[0]*9 for _ in range(10)] for _ in range(9)] for _ in range(10)]
        self.killer_moves = [[None, None] for _ in range(64)]


        

                                 
        self.eval_cache = {} 
                         
             
                  
             
                                
                                   
        
                            
                                               
                                              
        
                                 
        
                                      
                                                   
                                               
                                                                 
                                  
        
                      
                         
    def evaluate(self):
        base = self.current_score
        total = base
        
        
        return total
        
                       
    def get_history_score(self, move):
        start, end = move
        return self.history_table[start[0]][start[1]][end[0]][end[1]]

    def is_time_up(self):
        """检查是否超时"""
                                    
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
                pst_val = table[9-r][c]       
        
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
        
                                               
        if self.turn == 'black':
            self.current_hash ^= self.zobrist_turn
        self.history = [self.current_hash]    

    def make_move(self, start, end):
        r1, c1 = start
        r2, c2 = end
        moving_piece = self.board[r1][c1]
        captured_piece = self.board[r2][c2]

                      
        self.current_score -= self.get_piece_value(moving_piece, r1, c1)
        if captured_piece != '.':
            self.current_score -= self.get_piece_value(captured_piece, r2, c2)
        self.current_score += self.get_piece_value(moving_piece, r2, c2)

                                     
                
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
        moved_piece = self.board[r2][c2]

                 
        self.current_score -= self.get_piece_value(moved_piece, r2, c2)
        self.current_score += self.get_piece_value(moved_piece, r1, c1)
        if captured != '.':
            self.current_score += self.get_piece_value(captured, r2, c2)

                             
        self.current_hash ^= self.zobrist_turn           
        self.current_hash ^= self.zobrist_table[(r2, c2, moved_piece)]       
        if captured != '.':
            self.current_hash ^= self.zobrist_table[(r2, c2, captured)]        
        self.current_hash ^= self.zobrist_table[(r1, c1, moved_piece)]       

                 
        self.board[r1][c1] = moved_piece
        self.board[r2][c2] = captured
        self.turn = 'black' if self.turn == 'red' else 'red'

    def is_red(self, piece):
        return piece.isupper()

    def in_board(self, r, c):
        return 0 <= r < ROWS and 0 <= c < COLS

                         
    def get_valid_moves(self, r, c):
        piece = self.board[r][c]
        moves = []
        if piece == '.': return moves
        is_red_piece = self.is_red(piece)
        
        def is_teammate(nr, nc):
            p = self.board[nr][nc]
            return p != '.' and self.is_red(p) == is_red_piece

           
        if piece.lower() == 'r':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                while self.in_board(nr, nc):
                    if self.board[nr][nc] == '.': moves.append((nr, nc))
                    else:
                        if not is_teammate(nr, nc): moves.append((nr, nc))
                        break
                    nr, nc = nr+dr, nc+dc
                 
        elif piece.lower() == 'n':
            for dr, dc, lr, lc in [(-2,-1,-1,0), (-2,1,-1,0), (2,-1,1,0), (2,1,1,0),
                                   (-1,-2,0,-1), (1,-2,0,-1), (-1,2,0,1), (1,2,0,1)]:
                nr, nc, lr, lc = r+dr, c+dc, r+lr, c+lc
                if self.in_board(nr, nc) and self.board[lr][lc] == '.' and not is_teammate(nr, nc):
                    moves.append((nr, nc))
           
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
             
        elif piece.lower() == 'b':
            for dr, dc, er, ec in [(-2,-2,-1,-1), (-2,2,-1,1), (2,-2,1,-1), (2,2,1,1)]:
                nr, nc, er, ec = r+dr, c+dc, r+er, c+ec
                if self.in_board(nr, nc) and self.board[er][ec] == '.' and not is_teammate(nr, nc):
                    if (is_red_piece and nr>=5) or (not is_red_piece and nr<=4):
                        moves.append((nr, nc))
             
        elif piece.lower() == 'a':
            for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nr, nc = r+dr, c+dc
                if self.in_board(nr, nc) and 3<=nc<=5 and not is_teammate(nr, nc):
                    if (is_red_piece and 7<=nr<=9) or (not is_red_piece and 0<=nr<=2):
                        moves.append((nr, nc))
             
        elif piece.lower() == 'k':
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                if self.in_board(nr, nc) and 3<=nc<=5 and not is_teammate(nr, nc):
                    if (is_red_piece and 7<=nr<=9) or (not is_red_piece and 0<=nr<=2):
                        moves.append((nr, nc))
                                        
                                 
            direction = -1 if is_red_piece else 1
            check_r = r + direction
            
            while 0 <= check_r < ROWS:
                target_piece = self.board[check_r][c]
                if target_piece == '.':
                                 
                    check_r += direction
                else:
                           
                                          
                    enemy_king = 'k' if is_red_piece else 'K'
                    if target_piece == enemy_king:
                        moves.append((check_r, c))
                                             
                                           
                    break
             
        elif piece.lower() == 'p':
            dr = -1 if is_red_piece else 1
            if self.in_board(r+dr, c) and not is_teammate(r+dr, c): moves.append((r+dr, c))
            if (is_red_piece and r<=4) or (not is_red_piece and r>=5):          
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


                                     
    def quiescence_search(self, alpha, beta, maximizing_player, qs_depth=0):
                                                         
        in_check = self.is_in_check(maximizing_player)

                             
                                   
        if not in_check:
            score = self.evaluate()                          
            
            if maximizing_player:
                if score >= beta: return beta
                if score > alpha: alpha = score
            else:
                if score <= alpha: return alpha
                if score < beta: beta = score
        
                     
                                               
                                        
        if qs_depth > 10:
            return self.evaluate()

                 
                                                                        
        if in_check:
                                     
                                         
            moves = self.get_all_moves(maximizing_player)
        else:
                         
                                                   
            all_moves = self.get_all_moves(maximizing_player)
            moves = []
            for start, end in all_moves:
                            
                if self.board[end[0]][end[1]] != '.':
                    moves.append((start, end))

                    
        moves.sort(key=lambda m: PIECE_VALUES.get(self.board[m[1][0]][m[1][1]], 0), reverse=True)

                 
        has_legal_move = False
        
        for start, end in moves:
                  
            captured = self.make_move(start, end)
            
                                           
                                                      
                                                             
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

                                      
        if in_check and not has_legal_move:
                      
                                      
            return -SCORE_INF + qs_depth if maximizing_player else SCORE_INF - qs_depth

                                     
                                                            
        return alpha if maximizing_player else beta

                                
    def find_king(self, is_red_king):
        target = 'K' if is_red_king else 'k'
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == target:
                    return r, c
        return None

    def is_in_check(self, is_red_turn):
        """判断当前行动方是否被将军（简化版检测，用于NMP安全检查）"""
                
        king_pos = self.find_king(is_red_turn)
        if not king_pos: return True                
        kr, kc = king_pos
        
                              
                                        
        
                         
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = kr + dr, kc + dc
            first_piece = None
            while self.in_board(nr, nc):
                p = self.board[nr][nc]
                if p != '.':
                    if first_piece is None:
                        first_piece = p
                                  
                        if self.is_red(p) != is_red_turn:
                            if p.lower() in ['r', 'k']: return True
                    else:
                             
                        if self.is_red(p) != is_red_turn:
                            if p.lower() == 'c': return True
                        break           
                nr, nc = nr + dr, nc + dc
        
                
        knight_checks = [(-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2)]
        knight_legs   = [(-1, 0), (-1, 0), (1, 0), (1, 0), (0, -1), (0, 1), (0, -1), (0, 1)]
        for (dr, dc), (lr, lc) in zip(knight_checks, knight_legs):
            nr, nc = kr + dr, kc + dc
            lr, lc = kr + lr, kc + lc
            if self.in_board(nr, nc) and self.in_board(lr, lc):
                p = self.board[nr][nc]
                if p != '.' and self.is_red(p) != is_red_turn and p.lower() == 'n':
                    if self.board[lr][lc] == '.':        
                        return True
                        
                                    
        pawn_char = 'p' if is_red_turn else 'P'         
        pawn_dir = 1 if is_red_turn else -1                                
                                    
        check_r = kr - pawn_dir
        if self.in_board(check_r, kc) and self.board[check_r][kc] == pawn_char: return True       
        for dc in [-1, 1]:      
            if self.in_board(kr, kc+dc) and self.board[kr][kc+dc] == pawn_char: return True

        return False

    def make_null_move(self):
        """执行空步：只交换出子权和Hash"""
        self.turn = 'black' if self.turn == 'red' else 'red'
        self.current_hash ^= self.zobrist_turn
        self.history.append(self.current_hash)     

    def undo_null_move(self):
        """撤销空步：操作完全一样"""
        self.history.pop()     
        self.turn = 'black' if self.turn == 'red' else 'red'
        self.current_hash ^= self.zobrist_turn
    def minimax(self, depth, alpha, beta, maximizing_player, allow_null=True):
        self.nodes += 1
                           
                                                              
                                     
        if self.history.count(self.current_hash) > 1:
                       
                                                               
                                       
                                  
            return 0, None
                 
        if self.is_time_up():
            return 0, None

                           
        original_alpha = alpha
        idx = self.current_hash % self.tt_size
        tt_entry = self.tt[idx]
        tt_move = None
        
        if tt_entry is not None and tt_entry[0] == self.current_hash:
            tt_hash, tt_depth, tt_flag, tt_score, tt_move = tt_entry
                                       
            if tt_depth >= depth:
                if tt_flag == TT_EXACT:
                    return tt_score, tt_move
                elif tt_flag == TT_ALPHA and tt_score <= alpha:
                    return tt_score, tt_move
                elif tt_flag == TT_BETA and tt_score >= beta:
                    return tt_score, tt_move

                   
                            
        if depth <= 0:
            val = self.quiescence_search(alpha, beta, maximizing_player)
            return val, None

                            
        kings = [False, False]
                                         
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == 'K': kings[0] = True
                if self.board[r][c] == 'k': kings[1] = True
        if not kings[0]: return -SCORE_INF + depth, None 
        if not kings[1]: return SCORE_INF - depth, None 

        in_check = self.is_in_check(maximizing_player)
        
                                          
                                              
                                   
                                                                    

                                          
                                           
        if OPEN_NMP and depth >= 3 and not in_check and allow_null:
            self.make_null_move()
            
                             
            if depth > 6:
                R = 3
            else:
                R = 2
            
                          
            next_depth = max(0, depth - 1 - R)
            
                            
            if maximizing_player:
                                              
                                            
                val, _ = self.minimax(next_depth, beta - 1, beta, False, allow_null=False)
                self.undo_null_move()       
                
                if self.stop_search: return 0, None
                if val >= beta and val < 20000: 
                    return beta, None
            else:
                                               
                                              
                val, _ = self.minimax(next_depth, alpha, alpha + 1, True, allow_null=False)
                self.undo_null_move()       

                if self.stop_search: return 0, None
                if val <= alpha and val > -20000: 
                    return alpha, None
                            

                 
        moves = self.get_all_moves(maximizing_player)
        if not moves:
                                                       
            return (-SCORE_INF if maximizing_player else SCORE_INF), None

            
        killers = self.killer_moves[depth] if depth < 64 else [None, None]
        def move_sorter(m):
            start, end = m
            if tt_move and (start, end) == tt_move: return 2000000          
            
            victim = self.board[end[0]][end[1]]
            if victim != '.':          
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
        
               
        for start, end in moves:
            moves_count += 1
            captured = self.make_move(start, end)
            
            score = 0
            is_killer = ((start, end) == killers[0] or (start, end) == killers[1])
            
                               
                                       
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
                                                                
                    if search_depth < 0: search_depth = 0

                                
                    score, _ = self.minimax(search_depth, alpha, alpha + 1, False)
                    
                                                                  
                    if score > alpha:
                        if do_lmr:         
                            score, _ = self.minimax(depth - 1, alpha, alpha + 1, False)
                        if score > alpha and score < beta:        
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

               
        flag = TT_EXACT
        if best_score <= original_alpha: flag = TT_ALPHA
        elif best_score >= beta: flag = TT_BETA
        
        if tt_entry is None or depth >= tt_entry[1]:
            self.tt[idx] = (self.current_hash, depth, flag, best_score, best_move)

        return best_score, best_move
    def search_main(self, max_time, is_ai_red):
        cloud_data = self.query_cloud_book()
        if cloud_data:
            book_move, book_score = cloud_data           
            with open("log.txt", "a", encoding="utf-8") as f:
                print(f"使用云库走法: {book_move}, 云库分数: {book_score}", file=f)
            return book_score, book_move             
        self.start_time = time.time()
        self.time_limit = max_time
        self.stop_search = False
        
                             
        last_completed_move = None
        last_completed_val = 0
        
        for depth in range(1, 64):
                      
            current_val, current_move = self.minimax(depth, -float(SCORE_INF), float(SCORE_INF), is_ai_red)
            
                            
            if self.stop_search or current_move is None:
                                               
                break 
            
                                       
            last_completed_move = current_move
            last_completed_val = current_val
            
                  
            elapsed = time.time() - self.start_time
            with open("log.txt", "a", encoding="utf-8") as f:
                print(f"完成深度 {depth} | 耗时 {elapsed:.2f}s | 评估 {last_completed_val}", file=f)

            if abs(last_completed_val) > 20000: break       
            if elapsed > max_time * 0.2: break         

                                      
        return last_completed_val, last_completed_move
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
                
                                   
                max_score = moves[0]['score']
                candidates = [m for m in moves if m['score'] >= max_score - 5]
                
                           
                selected = random.choice(candidates)
                move_coords = self.uci_to_move(selected['move'])
                
                                 
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
                                   
            _, s = cmd.split()
            engine.player_side = s

        elif cmd.startswith("move"):
                              
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
                    DEPTH = long_max_depth           
                val, best = engine.minimax(DEPTH, -float(SCORE_INF ), float(SCORE_INF ), is_ai_red)
            else:
                MAX_TIME = 10.0 if  cnt<=3 else LONG_MAX_TIME                           
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
    if len(sys.argv) > 1:
        start_engine(int(sys.argv[1]))
    else:
        start_engine()

