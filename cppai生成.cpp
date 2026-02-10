#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <map>

// ==========================================
// 全局定义与常量
// ==========================================

using namespace std;

typedef unsigned long long U64;
typedef int Move;

const int MATE_SCORE = 30000;
const int INF = 32000;
const int MAX_DEPTH = 64;

// 棋盘表示：使用 16x16 扩展数组 (256大小)，中间存放 9x10 棋盘
// 有效位置：0x33 (row 3, col 3) 到 0x3b ... 直到 row 12
const int BOARD_SIZE = 256;

// 棋子定义
// 红: 8-14 (KABNRCP), 黑: 16-22 (kabnrcp)
// 空: 0
enum PieceType {
    EMPTY = 0,
    R_KING = 8, R_ADV, R_ELE, R_HORSE, R_ROOK, R_CANNON, R_PAWN,
    B_KING = 16, B_ADV, B_ELE, B_HORSE, B_ROOK, B_CANNON, B_PAWN
};

// 颜色掩码
const int COLOR_RED = 8;
const int COLOR_BLACK = 16;
const int COLOR_MASK = 24;

// 初始棋盘 FEN 布局
const int STARTUP_BOARD[256] = {
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 12, 11, 10, 9, 8, 9, 10, 11, 12, 0, 0, 0, 0, // Row 0
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,       // Row 1
    0, 0, 0, 0, 13, 0, 0, 0, 0, 0, 13, 0, 0, 0, 0, 0,     // Row 2
    0, 0, 0, 14, 0, 14, 0, 14, 0, 14, 0, 14, 0, 0, 0, 0,  // Row 3
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,       // Row 4
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,       // Row 5
    0, 0, 0, 7, 0, 7, 0, 7, 0, 7, 0, 7, 0, 0, 0, 0,       // Row 6
    0, 0, 0, 0, 6, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0, 0,       // Row 7
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,       // Row 8
    0, 0, 0, 5, 4, 3, 2, 1, 2, 3, 4, 5, 0, 0, 0, 0,       // Row 9
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

// 棋子价值
const int PIECE_VALUES[24] = {
    0, 0, 0, 0, 0, 0, 0, 0,
    10000, 200, 200, 450, 900, 450, 100, 0, // Red
    10000, 200, 200, 450, 900, 450, 100, 0  // Black
};

// 置换表
struct TTEntry {
    U64 key;
    int score;
    int depth;
    int flag; // 0: None, 1: Exact, 2: Alpha, 3: Beta
    Move best_move;
};
const int TT_SIZE = 1 << 20; // 1MB entries ~ 24MB RAM
TTEntry TT[TT_SIZE];

// 历史表与杀手走法
int HistoryTable[256][256];
Move KillerMoves[MAX_DEPTH][2];

// Zobrist Keys
U64 ZobristBoard[256][24];
U64 ZobristSide;

// 辅助宏
inline int SRC(Move m) { return (m >> 8) & 0xFF; }
inline int DST(Move m) { return m & 0xFF; }
inline Move MAKE_MOVE(int src, int dst) { return (src << 8) | dst; }
inline bool IN_BOARD(int sq) { return (sq & 0x88) == 0 && sq >= 0x33 && sq <= 0xCb; } // Check boundary inside 16x16
inline bool IS_RED(int p) { return p & COLOR_RED; }
inline bool IS_BLACK(int p) { return p & COLOR_BLACK; }
inline bool SAME_COLOR(int p1, int p2) { return (p1 & COLOR_MASK) == (p2 & COLOR_MASK) && p1 != 0 && p2 != 0; }

// ==========================================
// 引擎类
// ==========================================

class XiangqiEngine {
public:
    int board[256];
    int side; // 当前走棋方: 0=Red, 1=Black
    U64 zobrist_key;
    long long nodes;
    long long start_time_ms;
    long long time_limit_ms;
    bool stop_search;

    XiangqiEngine() {
        InitZobrist();
        Reset();
    }

    void InitZobrist() {
        // 简单伪随机生成
        U64 seed = 1070372;
        for (int i = 0; i < 256; i++) {
            for (int j = 0; j < 24; j++) {
                seed = seed * 6364136223846793005ULL + 1442695040888963407ULL;
                ZobristBoard[i][j] = seed;
            }
        }
        ZobristSide = seed * 6364136223846793005ULL + 1442695040888963407ULL;
    }

    void Reset() {
        memcpy(board, STARTUP_BOARD, sizeof(board));
        side = 0; // Red first
        zobrist_key = 0;
        for(int i=0; i<256; i++) {
            if(board[i]) zobrist_key ^= ZobristBoard[i][board[i]];
        }
        memset(TT, 0, sizeof(TT));
        memset(HistoryTable, 0, sizeof(HistoryTable));
        memset(KillerMoves, 0, sizeof(KillerMoves));
    }

    // 坐标转换 (外部协议 0-9 行, 0-8 列) -> 内部 16x16
    int CoordToIdx(int r, int c) {
        return (r + 3) * 16 + (c + 3);
    }

    // 内部 -> 外部
    void IdxToCoord(int idx, int &r, int &c) {
        r = (idx / 16) - 3;
        c = (idx % 16) - 3;
    }

    bool MakeMove(Move m) {
        int src = SRC(m);
        int dst = DST(m);
        int p = board[src];
        int cap = board[dst];

        // 更新 Zobrist
        zobrist_key ^= ZobristBoard[src][p];
        zobrist_key ^= ZobristBoard[dst][p]; // Move piece
        if (cap) zobrist_key ^= ZobristBoard[dst][cap]; // Remove captured
        zobrist_key ^= ZobristSide;

        board[dst] = p;
        board[src] = 0;
        side ^= 1;

        // 检查是否自杀 (被将军)
        if (IsChecked(side ^ 1)) {
            // 撤销移动
            side ^= 1;
            board[src] = p;
            board[dst] = cap;
            
            zobrist_key ^= ZobristSide;
            if (cap) zobrist_key ^= ZobristBoard[dst][cap];
            zobrist_key ^= ZobristBoard[dst][p];
            zobrist_key ^= ZobristBoard[src][p];
            return false;
        }
        return true;
    }

    void UnmakeMove(Move m, int captured) {
        int src = SRC(m);
        int dst = DST(m);
        int p = board[dst];

        side ^= 1;
        board[src] = p;
        board[dst] = captured;

        zobrist_key ^= ZobristSide;
        if (captured) zobrist_key ^= ZobristBoard[dst][captured];
        zobrist_key ^= ZobristBoard[dst][p];
        zobrist_key ^= ZobristBoard[src][p];
    }

    // 生成走法
    void GenerateMoves(vector<Move>& moves) {
        // 简化版：遍历棋盘。速度稍慢但逻辑清晰。
        // 高性能版会使用棋子列表。
        for (int i = 0x33; i <= 0xCb; i++) {
            if (!IN_BOARD(i)) continue;
            int p = board[i];
            if (!p) continue;
            
            bool is_red = IS_RED(p);
            if ((side == 0 && !is_red) || (side == 1 && is_red)) continue;

            int p_type = is_red ? p : p - 8; // Normalize to 8..14
            
            switch (p_type) {
                case R_KING: GenKingMoves(moves, i); break;
                case R_ADV:  GenAdvisorMoves(moves, i); break;
                case R_ELE:  GenElephantMoves(moves, i); break;
                case R_HORSE: GenHorseMoves(moves, i); break;
                case R_ROOK:  GenRookMoves(moves, i); break;
                case R_CANNON: GenCannonMoves(moves, i); break;
                case R_PAWN:  GenPawnMoves(moves, i); break;
            }
        }
    }

    void AddMove(vector<Move>& moves, int src, int dst) {
        if (!IN_BOARD(dst)) return;
        int p = board[dst];
        if (p && SAME_COLOR(board[src], p)) return;
        moves.push_back(MAKE_MOVE(src, dst));
    }

    void GenKingMoves(vector<Move>& moves, int src) {
        int deltas[] = {-16, -1, 1, 16};
        bool is_red = IS_RED(board[src]);
        for (int d : deltas) {
            int dst = src + d;
            if (!IN_BOARD(dst)) continue;
            // 九宫格限制
            int c = dst % 16;
            int r = dst / 16;
            if (c < 6 || c > 8) continue;
            if (is_red) { if (r < 10 || r > 12) continue; }
            else        { if (r < 3 || r > 5) continue; }
            AddMove(moves, src, dst);
        }
    }

    void GenAdvisorMoves(vector<Move>& moves, int src) {
        int deltas[] = {-17, -15, 15, 17};
        bool is_red = IS_RED(board[src]);
        for (int d : deltas) {
            int dst = src + d;
            if (!IN_BOARD(dst)) continue;
            int c = dst % 16;
            int r = dst / 16;
            if (c < 6 || c > 8) continue;
            if (is_red) { if (r < 10 || r > 12) continue; }
            else        { if (r < 3 || r > 5) continue; }
            AddMove(moves, src, dst);
        }
    }

    void GenElephantMoves(vector<Move>& moves, int src) {
        int deltas[] = {-34, -30, 30, 34}; // Elephant jumps 2
        int eyes[]   = {-17, -15, 15, 17};
        bool is_red = IS_RED(board[src]);
        for (int i=0; i<4; i++) {
            int dst = src + deltas[i];
            int eye = src + eyes[i];
            if (!IN_BOARD(dst)) continue;
            if (board[eye] != EMPTY) continue; // Blocked eye
            
            // Cannot cross river
            int r = dst / 16;
            if (is_red) { if (r < 8) continue; }
            else        { if (r > 7) continue; }
            
            AddMove(moves, src, dst);
        }
    }

    void GenHorseMoves(vector<Move>& moves, int src) {
        int deltas[] = {-33, -31, -18, 14, 31, 33, 18, -14};
        int legs[]   = {-16, -16, -1, 1, 16, 16, 1, -1};
        for (int i=0; i<8; i++) {
            int dst = src + deltas[i];
            int leg = src + legs[i];
            if (!IN_BOARD(dst)) continue;
            if (board[leg] != EMPTY) continue; // Blocked leg
            AddMove(moves, src, dst);
        }
    }

    void GenRookMoves(vector<Move>& moves, int src) {
        int deltas[] = {-16, -1, 1, 16};
        for (int d : deltas) {
            int dst = src + d;
            while (IN_BOARD(dst)) {
                if (board[dst] == EMPTY) {
                    AddMove(moves, src, dst);
                } else {
                    AddMove(moves, src, dst); // Capture
                    break;
                }
                dst += d;
            }
        }
    }

    void GenCannonMoves(vector<Move>& moves, int src) {
        int deltas[] = {-16, -1, 1, 16};
        for (int d : deltas) {
            int dst = src + d;
            bool jumped = false;
            while (IN_BOARD(dst)) {
                if (board[dst] == EMPTY) {
                    if (!jumped) AddMove(moves, src, dst);
                } else {
                    if (jumped) {
                        AddMove(moves, src, dst); // Capture
                        break;
                    }
                    jumped = true;
                }
                dst += d;
            }
        }
    }

    void GenPawnMoves(vector<Move>& moves, int src) {
        bool is_red = IS_RED(board[src]);
        int r = src / 16;
        int forward = is_red ? -16 : 16;
        
        // Forward
        AddMove(moves, src, src + forward);
        
        // Horizontal (cross river)
        bool crossed = is_red ? (r <= 7) : (r >= 8);
        if (crossed) {
            AddMove(moves, src, src - 1);
            AddMove(moves, src, src + 1);
        }
    }

    int FindKing(bool red) {
        int target = red ? R_KING : B_KING;
        for (int i = 0x33; i <= 0xCb; i++) {
            if (board[i] == target) return i;
        }
        return 0;
    }

    bool IsChecked(int side_checking) {
        // 简单实现：找到将帅，看是否被攻击
        // side_checking: 谁被将军？
        bool red_king = (side_checking == 0);
        int king_pos = FindKing(red_king);
        
        // 1. Check Flying King
        int enemy_king = FindKing(!red_king);
        if (king_pos % 16 == enemy_king % 16) {
            bool blocked = false;
            int step = (king_pos < enemy_king) ? 16 : -16;
            for (int p = king_pos + step; p != enemy_king; p += step) {
                if (board[p] != EMPTY) { blocked = true; break; }
            }
            if (!blocked) return true;
        }

        // 2. Simple attacks check (reverse logic)
        // 检查是否有敌方棋子能走到 king_pos
        // 为提高速度，这里只做简单的反向探测
        // ... (为保证代码简洁，直接生成对方所有走法看是否吃将)
        
        // 优化：只生成攻击类的走法
        // 但最稳健的方法是生成对手所有走法
        // 注意：这里需要传入 "对手视角"
        
        // 性能权衡：这里写反向检测太长，我们暂时用"生成对方所有步"来判断，
        // 虽然慢一点，但写在一个文件里不容易出错。
        // *更好的做法* 是 IsAttacked(sq, by_side)
        
        return IsAttacked(king_pos, !red_king);
    }

    bool IsAttacked(int sq, bool by_red) {
        // 检查 sq 是否被 by_red 一方攻击
        // Pawn
        int forward = by_red ? 16 : -16; // 兵是向前走的，所以反向检查要反过来... 不对，是检查是否有兵在攻击位置
        // 敌方兵在 (sq - forward) 或者 左右
        int pawn = by_red ? R_PAWN : B_PAWN;
        if (IN_BOARD(sq - forward) && board[sq - forward] == pawn) return true;
        // 过河兵左右
        int r = sq / 16;
        bool crossed = by_red ? (r >= 8) : (r <= 7); // 这里的 r 是 sq 的行
        // 注意逻辑：如果 sq 在己方半场，敌方兵还没过河，不能横走。
        // 如果 sq 在敌方半场（对方的半场），敌方兵已过河。
        // 这里的逻辑有点绕，改用标准遍历：
        
        // 遍历整个棋盘寻找攻击者 (虽然笨拙，但绝对正确且不依赖复杂逻辑)
        // 对于高性能引擎，应使用位棋盘或预计算攻击表。
        for (int i = 0x33; i <= 0xCb; i++) {
            if (!IN_BOARD(i)) continue;
            int p = board[i];
            if (!p) continue;
            if (IS_RED(p) != by_red) continue; // 不是攻击方

            int type = by_red ? p : p - 8;
            
            // 快速预判
            if (type == R_ROOK || type == R_CANNON || type == R_PAWN || type == R_HORSE || type == R_KING) {
                // 检查这个棋子是否攻击 sq
                // 为了代码简洁，利用之前的 GenMoves 逻辑的变体
                // 这里手写几个关键的
            } else {
                continue; 
            }

            // ROOK / KING (Flying)
            if (type == R_ROOK || type == R_KING) {
                if (i % 16 == sq % 16) { // 同列
                     bool blocked = false;
                     int step = (i < sq) ? 16 : -16;
                     for(int k=i+step; k!=sq; k+=step) if(board[k]) { blocked=true; break; }
                     if (!blocked) return true;
                }
                if (type == R_ROOK && (i / 16 == sq / 16)) { // 同行
                     bool blocked = false;
                     int step = (i < sq) ? 1 : -1;
                     for(int k=i+step; k!=sq; k+=step) if(board[k]) { blocked=true; break; }
                     if (!blocked) return true;
                }
            }
            // HORSE
            if (type == R_HORSE) {
                 int diff = sq - i;
                 // 8个方向
                 int abs_diff = abs(diff);
                 if (abs_diff == 33 || abs_diff == 31 || abs_diff == 18 || abs_diff == 14) {
                     // check leg
                     int leg = 0;
                     if (abs(diff) == 33 || abs(diff) == 31) leg = i + (diff > 0 ? 16 : -16);
                     else leg = i + (diff > 0 ? 1 : -1);
                     if (board[leg] == EMPTY) return true;
                 }
            }
            // CANNON
            if (type == R_CANNON) {
                if (i % 16 == sq % 16) {
                    int cnt = 0;
                    int step = (i < sq) ? 16 : -16;
                    for(int k=i+step; k!=sq; k+=step) if(board[k]) cnt++;
                    if (cnt == 1) return true;
                }
                if (i / 16 == sq / 16) {
                    int cnt = 0;
                    int step = (i < sq) ? 1 : -1;
                    for(int k=i+step; k!=sq; k+=step) if(board[k]) cnt++;
                    if (cnt == 1) return true;
                }
            }
            // PAWN
            if (type == R_PAWN) {
                int dist = sq - i;
                if (by_red) {
                    if (dist == -16) return true; // Forward
                    if (i / 16 <= 7 && abs(dist) == 1) return true; // Crossed river
                } else {
                    if (dist == 16) return true;
                    if (i / 16 >= 8 && abs(dist) == 1) return true;
                }
            }
        }
        return false;
    }

    // 静态评估
    int Evaluate() {
        // 基础子力
        int score = 0;
        for (int i = 0x33; i <= 0xCb; i++) {
            if (!IN_BOARD(i)) continue;
            int p = board[i];
            if (!p) continue;
            
            // 位置分 (简化版 PST)
            int val = PIECE_VALUES[p];
            
            // 简单位置加分
            int r = (i / 16) - 3; 
            int c = (i % 16) - 3;
            // 翻转黑方行
            int r_rel = IS_RED(p) ? r : 9 - r;

            // 兵过河加分
            if ((p == R_PAWN || p == B_PAWN)) {
                if (r_rel >= 3) val += 30; // 过河
                if (r_rel >= 6) val += 20; // 逼近九宫
            }
            // 中炮加分
            if ((p == R_CANNON || p == B_CANNON) && c == 4) val += 20;

            if (IS_RED(p)) score += val;
            else score -= val;
        }
        
        // 简单的机动性：车
        // (省略以保持速度，可以在这里加更多逻辑)
        
        return (side == 0) ? score : -score;
    }

    // 简单的快排比较器
    static bool CompareMoves(const Move& a, const Move& b) {
        // 这里的排序需要在 Search 内部结合 History/Killer 做，
        // 但 vector sort 需要上下文。
        // 我们在 Search 内部打分排序。
        return false; 
    }

    int Quiescence(int alpha, int beta) {
        if ((nodes & 2047) == 0) {
            long long now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
            if (now - start_time_ms > time_limit_ms) stop_search = true;
        }
        if (stop_search) return 0;
        nodes++;

        int val = Evaluate();
        if (val >= beta) return beta;
        if (val > alpha) alpha = val;

        vector<Move> moves;
        // 只生成吃子走法
        GenerateMoves(moves); 
        
        // 简单排序：MVVLVA (最有价值受害者 - 最低价值攻击者)
        // 这里简化：只看吃掉了什么
        vector<pair<int, Move>> sorted_moves;
        for (Move m : moves) {
            int dst = DST(m);
            if (board[dst] != EMPTY) { // 必须是吃子
                 int victim = PIECE_VALUES[board[dst]];
                 int attacker = PIECE_VALUES[board[SRC(m)]];
                 sorted_moves.push_back({victim * 10 - attacker, m});
            }
        }
        sort(sorted_moves.rbegin(), sorted_moves.rend());

        for (auto& pair : sorted_moves) {
            Move m = pair.second;
            int cap = board[DST(m)];
            
            if (!MakeMove(m)) continue;
            int score = -Quiescence(-beta, -alpha);
            UnmakeMove(m, cap);

            if (stop_search) return 0;

            if (score >= beta) return beta;
            if (score > alpha) alpha = score;
        }
        return alpha;
    }

    int AlphaBeta(int depth, int alpha, int beta, bool allow_null) {
        if ((nodes & 2047) == 0) {
            long long now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
            if (now - start_time_ms > time_limit_ms) stop_search = true;
        }
        if (stop_search) return 0;

        // 检查重复局面 (简化: 不查)
        
        if (depth <= 0) return Quiescence(alpha, beta);

        nodes++;

        // 置换表查找
        int tt_idx = zobrist_key % TT_SIZE;
        if (TT[tt_idx].key == zobrist_key && TT[tt_idx].depth >= depth) {
            if (TT[tt_idx].flag == 1) return TT[tt_idx].score;
            if (TT[tt_idx].flag == 2 && TT[tt_idx].score <= alpha) return alpha;
            if (TT[tt_idx].flag == 3 && TT[tt_idx].score >= beta) return beta;
        }

        // 空步裁剪 (Null Move Pruning)
        bool in_check = IsChecked(side);
        if (allow_null && !in_check && depth >= 3 && Evaluate() >= beta) {
            side ^= 1;
            zobrist_key ^= ZobristSide;
            // R=2 or 3
            int R = 2;
            if (depth > 6) R = 3;
            int val = -AlphaBeta(depth - 1 - R, -beta, -beta + 1, false);
            side ^= 1;
            zobrist_key ^= ZobristSide;
            
            if (stop_search) return 0;
            if (val >= beta) return beta;
        }

        vector<Move> moves;
        GenerateMoves(moves);
        
        // Move Ordering
        vector<pair<int, Move>> sorted_moves;
        for (Move m : moves) {
            int score = 0;
            if (m == TT[tt_idx].best_move) score = 1000000;
            else if (board[DST(m)]) score = PIECE_VALUES[board[DST(m)]] * 10 - PIECE_VALUES[board[SRC(m)]] + 100000;
            else if (m == KillerMoves[depth][0]) score = 90000;
            else if (m == KillerMoves[depth][1]) score = 80000;
            else score = HistoryTable[SRC(m)][DST(m)];
            
            sorted_moves.push_back({score, m});
        }
        sort(sorted_moves.rbegin(), sorted_moves.rend());

        int flag = 2; // Alpha
        int best_score = -INF;
        Move best_move = 0;
        int moves_searched = 0;

        for (auto& pair : sorted_moves) {
            Move m = pair.second;
            int cap = board[DST(m)];

            if (!MakeMove(m)) continue;
            
            int score;
            if (moves_searched == 0) {
                score = -AlphaBeta(depth - 1, -beta, -alpha, true);
            } else {
                // LMR (Late Move Reduction)
                if (moves_searched >= 4 && depth >= 3 && !in_check && cap == 0) {
                    score = -AlphaBeta(depth - 2, -alpha - 1, -alpha, true);
                    if (score > alpha) score = -AlphaBeta(depth - 1, -beta, -alpha, true);
                } else {
                    score = -AlphaBeta(depth - 1, -beta, -alpha, true);
                }
            }

            UnmakeMove(m, cap);
            moves_searched++;

            if (stop_search) return 0;

            if (score > best_score) {
                best_score = score;
                best_move = m;
            }

            if (score > alpha) {
                alpha = score;
                flag = 1; // Exact
                if (alpha >= beta) {
                    flag = 3; // Beta
                    if (!cap) {
                        KillerMoves[depth][1] = KillerMoves[depth][0];
                        KillerMoves[depth][0] = m;
                        HistoryTable[SRC(m)][DST(m)] += depth * depth;
                    }
                    break;
                }
            }
        }

        if (moves_searched == 0) {
            if (in_check) return -MATE_SCORE + (MAX_DEPTH - depth); // Mate
            else return 0; // Stalemate
        }

        // Store TT
        TT[tt_idx].key = zobrist_key;
        TT[tt_idx].depth = depth;
        TT[tt_idx].score = best_score;
        TT[tt_idx].flag = flag;
        TT[tt_idx].best_move = best_move;

        return best_score;
    }

    Move Search(double time_seconds) {
        start_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
        time_limit_ms = (long long)(time_seconds * 1000);
        stop_search = false;
        nodes = 0;

        Move best_move = 0;
        int score = 0;

        for (int d = 1; d <= MAX_DEPTH; d++) {
            int val = AlphaBeta(d, -INF, INF, true);
            
            if (stop_search) break;
            
            // 从 TT 获取当前深度的最佳走法
            int tt_idx = zobrist_key % TT_SIZE;
            if (TT[tt_idx].key == zobrist_key) {
                best_move = TT[tt_idx].best_move;
                score = val;
            }
            
            // 输出信息用于调试 (可选)
            // cout << "Info depth " << d << " score " << score << " nodes " << nodes << endl;

            if (score > MATE_SCORE - 100 || score < -MATE_SCORE + 100) break; // 已分胜负
        }
        return best_move;
    }
};

// ==========================================
// 主程序 / 协议处理
// ==========================================

int main() {
    XiangqiEngine engine;
    string cmd;
    
    // 关闭 IO 缓冲，确保 Python 能实时读取
    cout.setf(ios::unitbuf);

    cout << "ready" << endl;

    while (cin >> cmd) {
        if (cmd == "quit") break;
        
        if (cmd == "side") {
            string color;
            cin >> color;
            // 引擎本身无状态记录"自己"是哪方，它只知道当前轮到谁走
            // 协议层面由 Python 脚本控制，这里仅接收但不强制影响逻辑
        } 
        else if (cmd == "move") {
            int r1, c1, r2, c2;
            cin >> r1 >> c1 >> r2 >> c2;
            int src = engine.CoordToIdx(r1, c1);
            int dst = engine.CoordToIdx(r2, c2);
            engine.MakeMove(MAKE_MOVE(src, dst));
        } 
        else if (cmd == "search") {
            // 默认搜索 5 秒，或者根据之前的 Python 设置
            // 简单起见，设定为 4.0 秒
            Move m = engine.Search(4.0);
            
            if (m == 0) {
                cout << "resign" << endl;
            } else {
                int r1, c1, r2, c2;
                engine.IdxToCoord(SRC(m), r1, c1);
                engine.IdxToCoord(DST(m), r2, c2);
                cout << "move " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
                
                // 此时引擎内部其实已经走了这一步？
                // 不，通常 Search 应该是不改变内部状态的。
                // 但上面的 AlphaBeta 实际上是恢复了状态的。
                // 只有 MakeMove 会改变。
                // 按照协议，输出 move 后，引擎应当等待外界确认 move？
                // 大多数 UCI 类似协议是：搜索 -> 输出 bestmove -> GUI 输入 move ...
                // 但根据你的 Python 脚本逻辑，它输出 move 后，自己也得 MakeMove 保持同步。
                engine.MakeMove(m);
            }
        }
    }
    return 0;
}