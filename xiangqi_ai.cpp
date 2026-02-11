#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <unordered_map>
#include <map>
#include <cstring>
#include <cmath>
#include <chrono>
#include <random>
#include <iomanip>
#include <cstdint>
#include <sstream>
#include <fstream>
std::ofstream logfile("engine_log.txt", std::ios::app);

// --- 全局配置 ---
const int USE_DEPTH = 0; // 是否使用固定深度
const int LONG_MAX_DEPTH = 8;
const int OPEN_NMP = 1;
const double LONG_MAX_TIME = 30.0;

const int ROWS = 10;
const int COLS = 9;
const int SCORE_INF = 30000;

// TT 标记
const int TT_EXACT = 0;
const int TT_ALPHA = 1;
const int TT_BETA = 2;

// 颜色定义
#define RESET   "\033[0m"
#define RED_TXT "\033[31m"
#define BLACK_TXT "\033[36m"
#define BOLD    "\033[1m"

// --- 基础结构 ---
struct Move {
    int r1, c1, r2, c2;
    
    bool operator==(const Move& other) const {
        return r1 == other.r1 && c1 == other.c1 && r2 == other.r2 && c2 == other.c2;
    }
    bool operator!=(const Move& other) const {
        return !(*this == other);
    }
    bool is_valid() const {
        return r1 != -1; // 简单标记无效移动
    }
};

const Move NO_MOVE = {-1, -1, -1, -1};

struct TTEntry {
    uint64_t hash;
    int depth;
    int flag;
    int score;
    Move best_move;
};

// --- 子力价值与 PST ---
// 注意：这里的 PST 数据直接来源于 Python 代码
// 稍后在 init_data 中会像 Python 代码一样执行 adjust_pst (减去基础价值)

std::map<char, int> PIECE_VALUES = {
    {'k', 10000}, {'r', 1000}, {'n', 450}, {'c', 450}, {'a', 250}, {'b', 250}, {'p', 100},
    {'K', 10000}, {'R', 1000}, {'N', 450}, {'C', 450}, {'A', 250}, {'B', 250}, {'P', 100}, {'.', 0}
};

// 原始 PST 数据 (Row 0-9, Row 9 是红方底线)
// 这里为了代码简洁，直接展开为一维数组或使用 vector
// 逻辑必须与 Python 一致：PST 是红方视角的
// 黑方使用时：table[r][c] -> table[9-r][c] (如果 r 是绝对坐标)

// 辅助函数：根据字符获取基础分
int get_base_value(char p) {
    auto it = PIECE_VALUES.find(p);
    return (it != PIECE_VALUES.end()) ? it->second : 0;
}

// PST 存储 (7种兵种, 10x9)
// k, r, n, c, a, b, p
int PST[256][10][9]; // 使用 char 的 ASCII 码作为索引

// 原始数据填充 (复制自 Python)
void init_pst_raw() {
    // 兵 (P)
    int raw_p[10][9] = {
        { 9,  9,  9, 11, 13, 11,  9,  9,  9},
        {39, 49, 69, 84, 89, 84, 69, 49, 39},
        {39, 49, 64, 74, 74, 74, 64, 49, 39},
        {39, 46, 54, 59, 61, 59, 54, 46, 39},
        {29, 37, 41, 54, 59, 54, 41, 37, 29},
        { 7,  0, 13,  0, 16,  0, 13,  0,  7},
        { 7,  0,  7,  0, 15,  0,  7,  0,  7},
        { 0,  0,  0,  0,  0,  0,  0,  0,  0},
        { 0,  0,  0,  0,  0,  0,  0,  0,  0},
        { 0,  0,  0,  0,  0,  0,  0,  0,  0}
    };
    // 帅 (K)
    int raw_k[10][9] = {
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, 
        {0,0,0, 1, 1, 1,0,0,0}, {0,0,0, 2, 2, 2,0,0,0}, {0,0,0,11,15,11,0,0,0}
    };
    // 士 (A)
    int raw_a[10][9] = {
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, 
        {0,0,0,30, 0,30,0,0,0}, {0,0,0, 0,33, 0,0,0,0}, {0,0,0,30, 0,30,0,0,0}
    };
    // 相 (B)
    int raw_b[10][9] = {
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,30,0,0,0,30,0,0}, {0,0,0,0,0,0,0,0,0}, {28,0,0,0,33,0,0,0,28}, {0,0,0,0,0,0,0,0,0}, {0,0,30,0,0,0,30,0,0}
    };
    // 马 (N)
    int raw_n[10][9] = {
        {90, 90, 90, 96, 90, 96, 90, 90, 90},
        {90, 96,103, 97, 94, 97,103, 96, 90},
        {92, 98, 99,103, 99,103, 99, 98, 92},
        {93,108,100,107,100,107,100,108, 93},
        {93, 99, 99,101,102,101, 99, 99, 93},
        {90,100, 99,103,104,103, 99,100, 90},
        {90, 98,101,102,103,102,101, 98, 90},
        {92, 94, 98, 95, 98, 95, 98, 94, 92},
        {85, 90, 92, 93, 73, 93, 92, 90, 85},
        {88, 85, 90, 88, 90, 88, 90, 85, 88}
    };
    // 车 (R)
    int raw_r[10][9] = {
        {208,210,209,215,216,215,209,210,208},
        {206,212,209,216,233,216,209,212,206},
        {206,208,207,214,216,214,207,208,206},
        {206,213,213,216,216,216,213,213,206},
        {208,211,211,214,215,214,211,211,208},
        {208,212,212,214,215,214,212,212,208},
        {204,209,204,212,214,212,204,209,204},
        {198,208,204,212,212,212,204,208,198},
        {200,208,206,212,200,212,206,208,200},
        {194,206,204,212,200,212,204,206,194}
    };
    // 炮 (C)
    int raw_c[10][9] = {
        {103,103, 99, 91, 90, 91, 99,103,103},
        {98, 98, 96, 92, 89, 92, 96, 98, 98},
        {97, 97, 96, 91, 92, 91, 96, 97, 97},
        {96, 99, 99, 98,100, 98, 99, 99, 96},
        {96, 96, 96, 96,100, 96, 96, 96, 96},
        {95, 96, 99, 96,100, 96, 99, 96, 95},
        {96, 96, 96, 96, 96, 96, 96, 96, 96},
        {97, 96,100, 99,101, 99,100, 96, 97},
        {96, 97, 98, 98, 98, 98, 98, 97, 96},
        {96, 96, 97, 99, 99, 99, 97, 96, 96}
    };

    // 复制并执行 adjust_pst (Val - BaseVal)
    auto apply = [](int dest[10][9], int src[10][9], char p) {
        int base = get_base_value(p);
        for(int i=0; i<10; ++i)
            for(int j=0; j<9; ++j)
                dest[i][j] = src[i][j] - base;
    };

    apply(PST['p'], raw_p, 'p'); apply(PST['P'], raw_p, 'P');
    apply(PST['k'], raw_k, 'k'); apply(PST['K'], raw_k, 'K');
    apply(PST['a'], raw_a, 'a'); apply(PST['A'], raw_a, 'A');
    apply(PST['b'], raw_b, 'b'); apply(PST['B'], raw_b, 'B');
    apply(PST['n'], raw_n, 'n'); apply(PST['N'], raw_n, 'N');
    apply(PST['r'], raw_r, 'r'); apply(PST['R'], raw_r, 'R');
    apply(PST['c'], raw_c, 'c'); apply(PST['C'], raw_c, 'C');
}

// --- Zobrist ---
uint64_t ZOBRIST_TABLE[10][9][256];
uint64_t ZOBRIST_TURN;

void init_zobrist() {
    std::mt19937_64 rng(12345); // 固定种子保证复现
    for(int i=0; i<10; ++i)
        for(int j=0; j<9; ++j)
            for(int k=0; k<256; ++k)
                ZOBRIST_TABLE[i][j][k] = rng();
    ZOBRIST_TURN = rng();
}

// --- 类定义 ---
class XiangqiEngine {
public:
    char board[10][9];
    std::string turn; // "red" or "black"
    std::string player_side;
    bool game_over;
    int current_score;
    std::pair<int, int> king_pos[2]; // 0: Red King, 1: Black King
    
    // Zobrist
    uint64_t current_hash;
    std::unordered_map<uint64_t, int> hash_count;

    // Search Structures
    std::vector<TTEntry> tt;
    size_t tt_size;
    int history_table[10][9][10][9];
    Move killer_moves[64][2];
    
    // Stats
    long long nodes;
    double start_time;
    double time_limit;
    bool stop_search;

    XiangqiEngine() {
        // Init Board
        const char* initial[10] = {
            "rnbakabnr",
            ".........",
            ".c.....c.",
            "p.p.p.p.p",
            ".........",
            ".........",
            "P.P.P.P.P",
            ".C.....C.",
            ".........",
            "RNBAKABNR"
        };
        for(int i=0; i<10; ++i)
            for(int j=0; j<9; ++j)
                board[i][j] = initial[i][j];

        turn = "red";
        player_side = "red"; // default
        game_over = false;
        
        tt_size = 1000003;
        tt.resize(tt_size);
        for(auto& e : tt) e.flag = -1; // invalid

        std::memset(history_table, 0, sizeof(history_table));
        // killer moves init to valid=false by default constructor

        init_score_and_hash();
    }

    // 辅助: 判断红方
    bool is_red(char p) {
        return p >= 'A' && p <= 'Z';
    }
    bool in_board(int r, int c) {
        return r >= 0 && r < 10 && c >= 0 && c < 9;
    }

    // 计算单个棋子的价值 (Val + PST)
    int get_piece_value(char piece, int r, int c) {
        if (piece == '.') return 0;
        int val = PIECE_VALUES[piece];
        int pst_val = 0;
        
        // 确保索引合法
        if (PST[(unsigned char)piece][0][0] != 0 || val > 0) { // check if valid piece
             if (is_red(piece)) {
                 pst_val = PST[(unsigned char)piece][r][c];
             } else {
                 pst_val = PST[(unsigned char)piece][9-r][c];
             }
        }
        
        int total = val + pst_val;
        return is_red(piece) ? total : -total;
    }

    void init_score_and_hash() {
        current_score = 0;
        current_hash = 0;
        king_pos[0] = {-1, -1};
        king_pos[1] = {-1, -1};

        for(int r=0; r<10; ++r) {
            for(int c=0; c<9; ++c) {
                char p = board[r][c];
                if (p != '.') {
                    current_score += get_piece_value(p, r, c);
                    current_hash ^= ZOBRIST_TABLE[r][c][(unsigned char)p];
                    if (p == 'K') king_pos[0] = {r, c};
                    else if (p == 'k') king_pos[1] = {r, c};
                }
            }
        }
        if (turn == "black") current_hash ^= ZOBRIST_TURN;
        hash_count[current_hash] = 1;
    }

    // --- 核心：走子与撤销 ---
    char make_move(const Move& m) {
        char moving_piece = board[m.r1][m.c1];
        char captured_piece = board[m.r2][m.c2];

        // Update King Pos
        if (moving_piece == 'K') king_pos[0] = {m.r2, m.c2};
        else if (moving_piece == 'k') king_pos[1] = {m.r2, m.c2};
        if (captured_piece == 'K') king_pos[0] = {-1, -1};
        else if (captured_piece == 'k') king_pos[1] = {-1, -1};

        // Update Score (Incremental)
        current_score -= get_piece_value(moving_piece, m.r1, m.c1);
        if (captured_piece != '.') {
            current_score -= get_piece_value(captured_piece, m.r2, m.c2);
        }
        current_score += get_piece_value(moving_piece, m.r2, m.c2);

        // Update Hash
        current_hash ^= ZOBRIST_TABLE[m.r1][m.c1][(unsigned char)moving_piece];
        if (captured_piece != '.') {
            current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)captured_piece];
        }
        current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)moving_piece];
        current_hash ^= ZOBRIST_TURN;

        // Perform Move
        board[m.r2][m.c2] = moving_piece;
        board[m.r1][m.c1] = '.';
        turn = (turn == "red" ? "black" : "red");
        
        hash_count[current_hash]++;

        return captured_piece;
    }

    void undo_move(const Move& m, char captured) {
        hash_count[current_hash]--;
        
        char moved_piece = board[m.r2][m.c2];
        
        // Restore King Pos
        if (moved_piece == 'K') king_pos[0] = {m.r1, m.c1};
        else if (moved_piece == 'k') king_pos[1] = {m.r1, m.c1};
        if (captured == 'K') king_pos[0] = {m.r2, m.c2};
        else if (captured == 'k') king_pos[1] = {m.r2, m.c2};

        // Restore Score
        current_score -= get_piece_value(moved_piece, m.r2, m.c2);
        current_score += get_piece_value(moved_piece, m.r1, m.c1);
        if (captured != '.') {
            current_score += get_piece_value(captured, m.r2, m.c2);
        }

        // Restore Hash
        current_hash ^= ZOBRIST_TURN;
        current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)moved_piece];
        if (captured != '.') {
            current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)captured];
        }
        current_hash ^= ZOBRIST_TABLE[m.r1][m.c1][(unsigned char)moved_piece];

        // Restore Board
        board[m.r1][m.c1] = moved_piece;
        board[m.r2][m.c2] = captured;
        turn = (turn == "red" ? "black" : "red");
    }

    void make_null_move() {
        turn = (turn == "red" ? "black" : "red");
        current_hash ^= ZOBRIST_TURN;
        hash_count[current_hash]++;
    }

    void undo_null_move() {
        hash_count[current_hash]--;
        turn = (turn == "red" ? "black" : "red");
        current_hash ^= ZOBRIST_TURN;
    }

    // --- 走法生成 ---
    // 检查是否是队友
    bool is_teammate(int r, int c, bool is_red_piece) {
        char p = board[r][c];
        if (p == '.') return false;
        return is_red(p) == is_red_piece;
    }

    std::vector<Move> get_valid_moves(int r, int c) {
        std::vector<Move> moves;
        char p = board[r][c];
        if (p == '.') return moves;
        bool red_turn = is_red(p);
        char lower_p = std::tolower(p);

        if (lower_p == 'r') { // Rook
            int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                while(in_board(nr, nc)) {
                    if (board[nr][nc] == '.') {
                        moves.push_back({r, c, nr, nc});
                    } else {
                        if (!is_teammate(nr, nc, red_turn)) {
                            moves.push_back({r, c, nr, nc});
                        }
                        break;
                    }
                    nr += dr[i]; nc += dc[i];
                }
            }
        } else if (lower_p == 'n') { // Knight
            int dr[] = {-2, -2, 2, 2, -1, 1, -1, 1};
            int dc[] = {-1, 1, -1, 1, -2, -2, 2, 2};
            int lr[] = {-1, -1, 1, 1, 0, 0, 0, 0}; // Leg row
            int lc[] = {0, 0, 0, 0, -1, -1, 1, 1}; // Leg col
            for(int i=0; i<8; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                int leg_r = r + lr[i], leg_c = c + lc[i];
                if (in_board(nr, nc) && board[leg_r][leg_c] == '.' && !is_teammate(nr, nc, red_turn)) {
                    moves.push_back({r, c, nr, nc});
                }
            }
        } else if (lower_p == 'c') { // Cannon
             int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                bool platform = false;
                while(in_board(nr, nc)) {
                    if (board[nr][nc] == '.') {
                        if (!platform) moves.push_back({r, c, nr, nc});
                    } else {
                        if (!platform) platform = true;
                        else {
                            if (!is_teammate(nr, nc, red_turn)) {
                                moves.push_back({r, c, nr, nc});
                            }
                            break;
                        }
                    }
                    nr += dr[i]; nc += dc[i];
                }
            }
        } else if (lower_p == 'b') { // Bishop (Elephant)
            int dr[] = {-2, -2, 2, 2};
            int dc[] = {-2, 2, -2, 2};
            int er[] = {-1, -1, 1, 1}; // Eye
            int ec[] = {-1, 1, -1, 1};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                int eye_r = r + er[i], eye_c = c + ec[i];
                if (in_board(nr, nc) && board[eye_r][eye_c] == '.' && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 5) || (!red_turn && nr <= 4)) {
                        moves.push_back({r, c, nr, nc});
                    }
                }
            }
        } else if (lower_p == 'a') { // Advisor
            int dr[] = {-1, -1, 1, 1};
            int dc[] = {-1, 1, -1, 1};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                if (in_board(nr, nc) && nc >= 3 && nc <= 5 && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 7) || (!red_turn && nr <= 2)) {
                        moves.push_back({r, c, nr, nc});
                    }
                }
            }
        } else if (lower_p == 'k') { // King
            int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                if (in_board(nr, nc) && nc >= 3 && nc <= 5 && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 7) || (!red_turn && nr <= 2)) {
                        moves.push_back({r, c, nr, nc});
                    }
                }
            }
            // 飞将
            int direction = red_turn ? -1 : 1;
            int check_r = r + direction;
            while (check_r >= 0 && check_r < ROWS) {
                char target = board[check_r][c];
                if (target == '.') {
                    check_r += direction;
                } else {
                    char enemy_king = red_turn ? 'k' : 'K';
                    if (target == enemy_king) {
                        moves.push_back({r, c, check_r, c});
                    }
                    break;
                }
            }
        } else if (lower_p == 'p') { // Pawn
            int dr = red_turn ? -1 : 1;
            int nr = r + dr;
            if (in_board(nr, c) && !is_teammate(nr, c, red_turn)) {
                moves.push_back({r, c, nr, c});
            }
            if ((red_turn && r <= 4) || (!red_turn && r >= 5)) { // 过河
                if (in_board(r, c-1) && !is_teammate(r, c-1, red_turn)) moves.push_back({r, c, r, c-1});
                if (in_board(r, c+1) && !is_teammate(r, c+1, red_turn)) moves.push_back({r, c, r, c+1});
            }
        }
        return moves;
    }

    std::vector<Move> get_all_moves(bool is_red_turn, bool only_captures = false) {
        std::vector<Move> moves;
        // 为了提高效率，这里遍历棋盘。虽然 Python 代码用了 piece_places 优化，
        // 但C++遍历整个数组也很快。为了保持逻辑严格一致，如果 Python 仅对存在的棋子生成，
        // 这里遍历整个棋盘找到棋子是一样的效果。
        for(int r=0; r<ROWS; ++r) {
            for(int c=0; c<COLS; ++c) {
                char p = board[r][c];
                if (p != '.' && is_red(p) == is_red_turn) {
                    std::vector<Move> ms = get_valid_moves(r, c);
                    for(const auto& m : ms) {
                        if (!only_captures || board[m.r2][m.c2] != '.') {
                            moves.push_back(m);
                        }
                    }
                }
            }
        }
        return moves;
    }

    // --- 评估与检查 ---
    int evaluate() {
        return current_score;
    }

    // 检查将军 (NMP 必须)
    bool is_in_check(bool is_red_turn) {
        int kr = king_pos[is_red_turn ? 0 : 1].first;
        int kc = king_pos[is_red_turn ? 0 : 1].second;
        if (kr == -1) return true; // 王没了

        // 1. 车炮将
        int drs[] = {0, 0, 1, -1};
        int dcs[] = {1, -1, 0, 0};
        for(int i=0; i<4; ++i) {
            int nr = kr + drs[i], nc = kc + dcs[i];
            char first = 0;
            while(in_board(nr, nc)) {
                char p = board[nr][nc];
                if (p != '.') {
                    if (first == 0) {
                        first = p;
                        if (is_red(p) != is_red_turn) {
                            char lp = std::tolower(p);
                            if (lp == 'r' || lp == 'k') return true;
                        }
                    } else {
                        if (is_red(p) != is_red_turn && std::tolower(p) == 'c') return true;
                        break;
                    }
                }
                nr += drs[i]; nc += dcs[i];
            }
        }

        // 2. 马
        int ndr[] = {-2, -2, 2, 2, -1, 1, -1, 1};
        int ndc[] = {-1, 1, -1, 1, -2, -2, 2, 2};
        int nlr[] = {-1, -1, 1, 1, -1, 1, -1, 1}; // 修正后的马脚，参考 Python 代码注释中的修正
        // Python 代码虽然注释里写了修正，但实际使用的 knight_legs 对应于对帅的相对坐标
        // (-1, -1), (-1, 1) ...
        // 实际上 Python 中的 knight_checks 是目标位置相对于帅的偏移。
        // knight_legs 是马腿相对于帅的偏移。
        // Python code:
        // checks: (-2, -1), leg: (-1, -1) => Leg pos = King + (-1, -1). 
        // Logic: The leg is at midpoint diagonally.
        int leg_check_r[] = {-1, -1, 1, 1, -1, 1, -1, 1};
        int leg_check_c[] = {-1, 1, -1, 1, -1, -1, 1, 1};
        
        for(int i=0; i<8; ++i) {
             int nr = kr + ndr[i], nc = kc + ndc[i];
             int lr = kr + leg_check_r[i], lc = kc + leg_check_c[i];
             if (in_board(nr, nc) && in_board(lr, lc)) {
                 char p = board[nr][nc];
                 if (p != '.' && is_red(p) != is_red_turn && std::tolower(p) == 'n') {
                     if (board[lr][lc] == '.') return true;
                 }
             }
        }

        // 3. 兵
        char enemy_pawn = is_red_turn ? 'p' : 'P';
        int forward = is_red_turn ? -1 : 1; // 敌方兵的前进方向是相对于敌方的，对红帅来说，黑兵向下(+1)是前进
        // Python: pawn_dir = 1 if is_red else -1. check_r = kr - pawn_dir.
        // If Red (turn), pawn_dir=1. Enemy is Black. Black pawn moves +1. 
        // Check r = kr - 1. (Up). Logic: Check if pawn is at (kr-1, kc) attacking down.
        // Wait, Python logic: `pawn_dir = 1 if is_red_turn else -1`. 
        // `check_r = kr - pawn_dir`. 
        // If red turn, check `kr - 1`. Correct, black pawn attacks from above? No, black pawn attacks downwards to larger row index.
        // Red king is at bottom (row 9). Black pawn comes from 0.
        // If Red king at 9, pawn at 8 attacks it. 
        // Python: `pawn_dir = 1`. `check_r = 9 - 1 = 8`. `board[8][kc] == 'p'`. Correct.
        int p_dir = is_red_turn ? 1 : -1;
        int check_r = kr - p_dir;
        if (in_board(check_r, kc) && board[check_r][kc] == enemy_pawn) return true;
        if (in_board(kr, kc-1) && board[kr][kc-1] == enemy_pawn) return true;
        if (in_board(kr, kc+1) && board[kr][kc+1] == enemy_pawn) return true;

        return false;
    }

    // --- Search ---
    
    // 检查时间
    bool is_time_up() {
        if ((nodes & 1023) == 0) {
            auto now = std::chrono::steady_clock::now();
            std::chrono::duration<double> elapsed = now - std::chrono::steady_clock::time_point(std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(start_time)));
            // 由于 start_time 是 double (time.time()), 这里做转换比较麻烦，建议直接用 clock
            // 简单处理: 我们假设外部传入的是秒
            // 重新实现：
            // start_time 在 search_main 里初始化为 chrono timestamp
        }
        return stop_search; 
    }
    
    // 实际的时间检查逻辑在 search loop 里更新 stop_search

    int quiescence_search(int alpha, int beta, bool maximizing_player, int qs_depth = 0) {
        bool in_check = is_in_check(maximizing_player);

        if (!in_check) {
            int score = evaluate();
            if (maximizing_player) {
                if (score >= beta) return beta;
                if (score > alpha) alpha = score;
            } else {
                if (score <= alpha) return alpha;
                if (score < beta) beta = score;
            }
        }
        
        if (qs_depth > 6) return evaluate(); // Python limit

        std::vector<Move> moves;
        if (in_check) moves = get_all_moves(maximizing_player, false);
        else moves = get_all_moves(maximizing_player, true);

        // MVV-LVA Sort
        std::sort(moves.begin(), moves.end(), [&](const Move& a, const Move& b) {
            int val_a = PIECE_VALUES[board[a.r2][a.c2]];
            int val_b = PIECE_VALUES[board[b.r2][b.c2]];
            return val_a > val_b;
        });

        bool has_legal = false;
        for (const auto& m : moves) {
            char captured = make_move(m);
            if (is_in_check(maximizing_player)) {
                undo_move(m, captured);
                continue;
            }
            has_legal = true;
            
            int score = quiescence_search(alpha, beta, !maximizing_player, qs_depth + 1);
            undo_move(m, captured);

            if (maximizing_player) {
                if (score >= beta) return beta;
                if (score > alpha) alpha = score;
            } else {
                if (score <= alpha) return alpha;
                if (score < beta) beta = score;
            }
        }

        if (in_check && !has_legal) {
            return maximizing_player ? -SCORE_INF + qs_depth : SCORE_INF - qs_depth;
        }

        return maximizing_player ? alpha : beta;
    }

    struct SearchResult {
        int score;
        Move move;
    };

    SearchResult minimax(int depth, int alpha, int beta, bool maximizing_player, bool allow_null = true, int check_ext_left = 1) {
        nodes++;
        
        // Repetition check
        if (hash_count[current_hash] > 1) {
            return {0, NO_MOVE};
        }

        if (stop_search) return {0, NO_MOVE};
        if ((nodes & 2047) == 0) {
             auto now = std::chrono::steady_clock::now();
             double elapsed = std::chrono::duration<double>(now - std::chrono::time_point<std::chrono::steady_clock>(std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(start_time)))).count();
             if (elapsed > time_limit) stop_search = true;
        }

        bool in_check = is_in_check(maximizing_player);
        int ext = 0;
        if (check_ext_left > 0 && in_check) ext = 1;

        if (depth + ext <= 0) {
            int val = quiescence_search(alpha, beta, maximizing_player);
            return {val, NO_MOVE};
        }

        // TT Lookup
        int idx = current_hash % tt_size;
        TTEntry& tte = tt[idx];
        Move tt_move = NO_MOVE;
        if (tte.flag != -1 && tte.hash == current_hash) {
            if (tte.depth >= depth) {
                if (tte.flag == TT_EXACT) return {tte.score, tte.best_move};
                if (tte.flag == TT_ALPHA && tte.score <= alpha) return {tte.score, tte.best_move};
                if (tte.flag == TT_BETA && tte.score >= beta) return {tte.score, tte.best_move};
            }
            tt_move = tte.best_move;
        }

        if (king_pos[0].first == -1) return {-SCORE_INF + depth, NO_MOVE};
        if (king_pos[1].first == -1) return {SCORE_INF - depth, NO_MOVE};

        // NMP
        if (OPEN_NMP && depth >= 3 && !in_check && allow_null) {
            make_null_move();
            int R = (depth > 6) ? 3 : 2;
            int next_depth = std::max(0, depth - 1 - R);
            
            int val;
            if (maximizing_player) {
                // Search with black window (beta-1, beta) -> Black tries to prove < beta
                SearchResult res = minimax(next_depth, beta - 1, beta, false, false, 0);
                val = res.score;
            } else {
                SearchResult res = minimax(next_depth, alpha, alpha + 1, true, false, 0);
                val = res.score;
            }
            undo_null_move();

            if (stop_search) return {0, NO_MOVE};

            if (maximizing_player) {
                if (val >= beta && val < 20000) return {beta, NO_MOVE};
            } else {
                if (val <= alpha && val > -20000) return {alpha, NO_MOVE};
            }
        }

        // Generate Moves
        std::vector<Move> moves = get_all_moves(maximizing_player);
        if (moves.empty()) {
            return {maximizing_player ? -SCORE_INF : SCORE_INF, NO_MOVE};
        }

        // Sort
        Move k1 = killer_moves[depth][0];
        Move k2 = killer_moves[depth][1];
        
        std::sort(moves.begin(), moves.end(), [&](const Move& a, const Move& b) {
            if (tt_move.is_valid() && a == tt_move) return true;
            if (tt_move.is_valid() && b == tt_move) return false;
            
            // Capture
            int val_a = 0, val_b = 0;
            if (board[a.r2][a.c2] != '.') val_a = PIECE_VALUES[board[a.r2][a.c2]] * 10 - PIECE_VALUES[board[a.r1][a.c1]];
            if (board[b.r2][b.c2] != '.') val_b = PIECE_VALUES[board[b.r2][b.c2]] * 10 - PIECE_VALUES[board[b.r1][b.c1]];
            
            if (val_a != val_b) return val_a > val_b;

            // Killer
            bool a_k = (a == k1 || a == k2);
            bool b_k = (b == k1 || b == k2);
            if (a_k != b_k) return a_k;

            // History
            return history_table[a.r1][a.c1][a.r2][a.c2] > history_table[b.r1][b.c1][b.r2][b.c2];
        });

        Move best_move = moves[0];
        int best_score = maximizing_player ? -SCORE_INF - 100 : SCORE_INF + 100;
        int moves_count = 0;
        int original_alpha = alpha;

        for (const auto& m : moves) {
            moves_count++;
            char captured = make_move(m);
            
            if (is_in_check(maximizing_player)) {
                undo_move(m, captured);
                continue;
            }

            int score;
            bool is_killer = (m == k1 || m == k2);
            bool do_lmr = (depth >= 3 && moves_count > 4 && captured == '.' && !in_check && !is_killer);

            if (maximizing_player) {
                if (moves_count == 1) {
                    score = minimax(depth - 1 + ext, alpha, beta, false, true, check_ext_left - ext).score;
                } else {
                    int reduction = do_lmr ? 1 : 0;
                    if (moves_count > 10 && do_lmr) reduction = 2;
                    if (moves_count > 20 && do_lmr) reduction = 3;
                    
                    int s_depth = std::max(0, depth - 1 - reduction);
                    
                    score = minimax(s_depth + ext, alpha, alpha + 1, false, true, check_ext_left - ext).score;
                    if (score > alpha) {
                         if (do_lmr) {
                             score = minimax(depth - 1 + ext, alpha, alpha + 1, false, true, check_ext_left - ext).score;
                         }
                         if (score > alpha && score < beta) {
                             score = minimax(depth - 1 + ext, alpha, beta, false, true, check_ext_left - ext).score;
                         }
                    }
                }
            } else {
                if (moves_count == 1) {
                    score = minimax(depth - 1 + ext, alpha, beta, true, true, check_ext_left - ext).score;
                } else {
                     int reduction = do_lmr ? 1 : 0;
                    if (moves_count > 10 && do_lmr) reduction = 2;
                    if (moves_count > 20 && do_lmr) reduction = 3;
                    
                    int s_depth = std::max(0, depth - 1 - reduction);

                    score = minimax(s_depth + ext, beta - 1, beta, true, true, check_ext_left - ext).score;
                    if (score < beta) {
                        if (do_lmr) {
                             score = minimax(depth - 1 + ext, beta - 1, beta, true, true, check_ext_left - ext).score;
                        }
                        if (score < beta && score > alpha) {
                            score = minimax(depth - 1 + ext, alpha, beta, true, true, check_ext_left - ext).score;
                        }
                    }
                }
            }

            undo_move(m, captured);
            if (stop_search) return {0, NO_MOVE};

            if (maximizing_player) {
                if (score > best_score) {
                    best_score = score;
                    best_move = m;
                    if (best_score > alpha) {
                        alpha = best_score;
                        if (alpha >= beta) {
                            if (captured == '.') {
                                history_table[m.r1][m.c1][m.r2][m.c2] += depth * depth;
                                if (killer_moves[depth][0] != m) {
                                    killer_moves[depth][1] = killer_moves[depth][0];
                                    killer_moves[depth][0] = m;
                                }
                            }
                            break;
                        }
                    }
                }
            } else {
                if (score < best_score) {
                    best_score = score;
                    best_move = m;
                    if (best_score < beta) {
                        beta = best_score;
                        if (beta <= alpha) {
                            if (captured == '.') {
                                history_table[m.r1][m.c1][m.r2][m.c2] += depth * depth;
                                if (killer_moves[depth][0] != m) {
                                    killer_moves[depth][1] = killer_moves[depth][0];
                                    killer_moves[depth][0] = m;
                                }
                            }
                            break;
                        }
                    }
                }
            }
        }
        
        // Store TT
        int flag = TT_EXACT;
        if (best_score <= original_alpha) flag = TT_ALPHA;
        else if (best_score >= beta) flag = TT_BETA;
        
        tte.hash = current_hash;
        tte.depth = depth;
        tte.flag = flag;
        tte.score = best_score;
        tte.best_move = best_move;

        return {best_score, best_move};
    }
    
    // Iterative Deepening
    SearchResult search_main(double max_time, bool is_ai_red) {
        start_time = std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); // Hacky but functional for logic
        time_limit = max_time;
        stop_search = false;
        
        SearchResult last_res = {0, NO_MOVE};
        
        for (int depth = 1; depth < 64; ++depth) {
            SearchResult res = minimax(depth, -SCORE_INF - 1, SCORE_INF + 1, is_ai_red);
            
            if (stop_search) break;
            
            last_res = res;
            
            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(now - std::chrono::time_point<std::chrono::steady_clock>(std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(start_time)))).count();
            
            logfile << "info depth " << depth
                << " score " << res.score
                << " time " << (int)(elapsed * 1000)
                << " nodes " << nodes
                << std::endl;

            if (std::abs(res.score) > 20000) break;
            if (elapsed > max_time * 0.16 && depth >= 4) break; // simple logic from python
        }
        return last_res;
    }
};

// --- Main Protocol Loop ---

int main() {
    // IO opt
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    init_pst_raw();
    init_zobrist();
    
    XiangqiEngine engine;
    std::string line;

    int cnt = 0; // Count search commands for simple time management logic
    
    while (std::getline(std::cin, line)) {
        if (line == "quit") break;
        if (line == "ready") std::cout << "readyok" << std::endl;
        
        if (line.substr(0, 4) == "side") {
            if (line.find("red") != std::string::npos) engine.player_side = "red";
            else engine.player_side = "black";
        }
        else if (line.substr(0, 4) == "move") {
            // move r1 c1 r2 c2
            std::stringstream ss(line);
            std::string cmd;
            int r1, c1, r2, c2;
            ss >> cmd >> r1 >> c1 >> r2 >> c2;
            Move m = {r1, c1, r2, c2};
            if (engine.make_move(m) != '.') {
                engine.hash_count.clear(); // Clear history if capture
                engine.hash_count[engine.current_hash] = 1;
            }
        }
        else if (line.substr(0, 6) == "search") {
            cnt++;
            // search [time] or defaults
            engine.nodes = 0;
            bool is_ai_red = (engine.player_side == "black");
            
            int depth = LONG_MAX_DEPTH;
            double max_time = LONG_MAX_TIME;
            
            // Parsing simple search depth/time command if needed (not strictly required by prompt but good to have)
             // The python code has conditional logic for early game vs late game
             // Here we just replicate the main branch logic
            
            XiangqiEngine::SearchResult res;
            if (USE_DEPTH) {
                res = engine.minimax(LONG_MAX_DEPTH, -SCORE_INF - 1, SCORE_INF + 1, is_ai_red);
            } else {
                double search_time = cnt <= 3? 15.0 : LONG_MAX_TIME; // Simple logic: first 3 moves use shorter time, then switch to longer time
                res = engine.search_main(search_time, is_ai_red);
            }
            
            if (res.move.is_valid()) {
                Move best = res.move;
                char cap = engine.make_move(best);
                if (cap != '.') {
                     engine.hash_count.clear();
                     engine.hash_count[engine.current_hash] = 1;
                }
                std::cout << "move " << best.r1 << " " << best.c1 << " " << best.r2 << " " << best.c2 << std::endl;
            } else {
                std::cout << "resign" << std::endl;
            }
        }
        else if (line == "print") {
            // Simple visualizer
             for(int r=0; r<10; ++r) {
                 for(int c=0; c<9; ++c) {
                     std::cout << engine.board[r][c] << " ";
                 }
                 std::cout << std::endl;
             }
        }
    }
    
    return 0;
}
//  g++ -O3 -std=c++11 -o xiangqi_ai xiangqi_ai.cpp