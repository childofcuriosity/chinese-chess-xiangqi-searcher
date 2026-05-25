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
#include <tuple>

std::ofstream logfile("engine_log.txt", std::ios::app);

// ============================================================
// 全局配置
// ============================================================
const int USE_DEPTH = 0;
const int LONG_MAX_DEPTH = 8;
const int OPEN_NMP = 1;
const double LONG_MAX_TIME = 5.0;

const int ROWS = 10;
const int COLS = 9;
const int SCORE_INF = 30000;
const int MATE_BOUND = 20000;          // 绝对值 > 此 即视为杀棋分

const int TT_EXACT = 0;
const int TT_ALPHA = 1;
const int TT_BETA = 2;
const int TT_INVALID = -1;

const size_t TT_BITS = 21;             // 2M 项, 约 80MB
const size_t TT_SIZE = (size_t)1 << TT_BITS;
const size_t TT_MASK = TT_SIZE - 1;

#define RESET   "\033[0m"
#define RED_TXT "\033[31m"
#define BLACK_TXT "\033[36m"
#define BOLD    "\033[1m"

struct Move {
    int r1, c1, r2, c2;
    bool operator==(const Move& o) const { return r1==o.r1 && c1==o.c1 && r2==o.r2 && c2==o.c2; }
    bool operator!=(const Move& o) const { return !(*this == o); }
    bool is_valid() const { return r1 != -1; }
};
const Move NO_MOVE = {-1, -1, -1, -1};

struct TTEntry {
    uint64_t hash;
    int depth;
    int flag;
    int score;
    Move best_move;
    int age;
};

std::map<char, int> PIECE_VALUES = {
    {'k', 10000}, {'r', 1000}, {'n', 450}, {'c', 450}, {'a', 120}, {'b', 120}, {'p', 100},
    {'K', 10000}, {'R', 1000}, {'N', 450}, {'C', 450}, {'A', 120}, {'B', 120}, {'P', 100}, {'.', 0}
};

int get_base_value(char p) {
    auto it = PIECE_VALUES.find(p);
    return (it != PIECE_VALUES.end()) ? it->second : 0;
}

int PST[256][10][9];

void init_pst_raw() {
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
    int raw_k[10][9] = {
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,0, 1, 1, 1,0,0,0}, {0,0,0, 2, 2, 2,0,0,0}, {0,0,0,11,15,11,0,0,0}
    };
    int raw_a[10][9] = {
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,0,25, 0,25,0,0,0}, {0,0,0, 0,28, 0,0,0,0}, {0,0,0,25, 0,25,0,0,0}
    };
    int raw_b[10][9] = {
        {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0}, {0,0,0,0,0,0,0,0,0},
        {0,0,25,0,0,0,25,0,0}, {0,0,0,0,0,0,0,0,0}, {23,0,0,0,28,0,0,0,23}, {0,0,0,0,0,0,0,0,0}, {0,0,25,0,0,0,25,0,0}
    };
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

uint64_t ZOBRIST_TABLE[10][9][256];
uint64_t ZOBRIST_TURN;

void init_zobrist() {
    std::mt19937_64 rng(12345);
    for(int i=0; i<10; ++i)
        for(int j=0; j<9; ++j)
            for(int k=0; k<256; ++k)
                ZOBRIST_TABLE[i][j][k] = rng();
    ZOBRIST_TURN = rng();
}

int LMR_TABLE[64][64];
void init_lmr() {
    for (int d = 0; d < 64; ++d) {
        for (int m = 0; m < 64; ++m) {
            if (d <= 0 || m <= 0) LMR_TABLE[d][m] = 0;
            else LMR_TABLE[d][m] = (int)(0.5 + std::log((double)d) * std::log((double)m) / 2.5);
        }
    }
}

class XiangqiEngine {
public:
    Move forbidden_move;
    char board[10][9];
    std::string turn;
    std::string player_side;
    bool game_over;
    int current_score;
    std::pair<int,int> king_pos[2];
    uint64_t current_hash;

    static const int PATH_CAP = 2048;
    uint64_t path_hashes[PATH_CAP];
    Move     path_moves[PATH_CAP];
    int      path_len;

    std::vector<TTEntry> tt;
    int tt_age;

    int  history_table[10][9][10][9];
    Move killer_moves[64][2];
    Move counter_move[10][9][10][9];

    long long nodes;
    std::chrono::steady_clock::time_point start_tp;
    double time_limit;
    bool stop_search;

    XiangqiEngine() {
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
        player_side = "red";
        forbidden_move = NO_MOVE;
        game_over = false;

        tt.resize(TT_SIZE);
        for(auto& e : tt) { e.flag = TT_INVALID; e.age = 0; }
        tt_age = 0;

        std::memset(history_table, 0, sizeof(history_table));
        for (int d = 0; d < 64; ++d) {
            killer_moves[d][0] = NO_MOVE;
            killer_moves[d][1] = NO_MOVE;
        }
        for (int a=0; a<10; ++a)
            for (int b=0; b<9; ++b)
                for (int c=0; c<10; ++c)
                    for (int d=0; d<9; ++d)
                        counter_move[a][b][c][d] = NO_MOVE;

        path_len = 0;
        init_score_and_hash();
    }

    bool is_red(char p) { return p >= 'A' && p <= 'Z'; }
    bool in_board(int r, int c) { return r >= 0 && r < 10 && c >= 0 && c < 9; }

    int get_piece_value(char piece, int r, int c) {
        if (piece == '.') return 0;
        int val = PIECE_VALUES[piece];
        int pst_val = 0;
        if (PST[(unsigned char)piece][0][0] != 0 || val > 0) {
            if (is_red(piece)) pst_val = PST[(unsigned char)piece][r][c];
            else               pst_val = PST[(unsigned char)piece][9-r][c];
        }
        int total = val + pst_val;
        return is_red(piece) ? total : -total;
    }

    void init_score_and_hash() {
        current_score = 0;
        current_hash = 0;
        king_pos[0] = {-1,-1};
        king_pos[1] = {-1,-1};
        for(int r=0; r<10; ++r) {
            for(int c=0; c<9; ++c) {
                char p = board[r][c];
                if (p != '.') {
                    current_score += get_piece_value(p, r, c);
                    current_hash ^= ZOBRIST_TABLE[r][c][(unsigned char)p];
                    if (p == 'K') king_pos[0] = {r,c};
                    else if (p == 'k') king_pos[1] = {r,c};
                }
            }
        }
        if (turn == "black") current_hash ^= ZOBRIST_TURN;
        path_len = 0;
        path_hashes[path_len] = current_hash;
        path_moves[path_len]  = NO_MOVE;
        path_len++;
    }

    char make_move(const Move& m) {
        char moving_piece = board[m.r1][m.c1];
        char captured_piece = board[m.r2][m.c2];

        if (moving_piece == 'K') king_pos[0] = {m.r2, m.c2};
        else if (moving_piece == 'k') king_pos[1] = {m.r2, m.c2};
        if (captured_piece == 'K') king_pos[0] = {-1,-1};
        else if (captured_piece == 'k') king_pos[1] = {-1,-1};

        current_score -= get_piece_value(moving_piece, m.r1, m.c1);
        if (captured_piece != '.')
            current_score -= get_piece_value(captured_piece, m.r2, m.c2);
        current_score += get_piece_value(moving_piece, m.r2, m.c2);

        current_hash ^= ZOBRIST_TABLE[m.r1][m.c1][(unsigned char)moving_piece];
        if (captured_piece != '.')
            current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)captured_piece];
        current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)moving_piece];
        current_hash ^= ZOBRIST_TURN;

        board[m.r2][m.c2] = moving_piece;
        board[m.r1][m.c1] = '.';
        turn = (turn == "red" ? "black" : "red");

        if (path_len < PATH_CAP) {
            path_hashes[path_len] = current_hash;
            path_moves[path_len]  = m;
            path_len++;
        }
        return captured_piece;
    }

    void undo_move(const Move& m, char captured) {
        if (path_len > 0) path_len--;
        char moved_piece = board[m.r2][m.c2];

        if (moved_piece == 'K') king_pos[0] = {m.r1, m.c1};
        else if (moved_piece == 'k') king_pos[1] = {m.r1, m.c1};
        if (captured == 'K') king_pos[0] = {m.r2, m.c2};
        else if (captured == 'k') king_pos[1] = {m.r2, m.c2};

        current_score -= get_piece_value(moved_piece, m.r2, m.c2);
        current_score += get_piece_value(moved_piece, m.r1, m.c1);
        if (captured != '.')
            current_score += get_piece_value(captured, m.r2, m.c2);

        current_hash ^= ZOBRIST_TURN;
        current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)moved_piece];
        if (captured != '.')
            current_hash ^= ZOBRIST_TABLE[m.r2][m.c2][(unsigned char)captured];
        current_hash ^= ZOBRIST_TABLE[m.r1][m.c1][(unsigned char)moved_piece];

        board[m.r1][m.c1] = moved_piece;
        board[m.r2][m.c2] = captured;
        turn = (turn == "red" ? "black" : "red");
    }

    void make_null_move() {
        turn = (turn == "red" ? "black" : "red");
        current_hash ^= ZOBRIST_TURN;
        if (path_len < PATH_CAP) {
            path_hashes[path_len] = current_hash;
            path_moves[path_len]  = NO_MOVE;
            path_len++;
        }
    }

    void undo_null_move() {
        if (path_len > 0) path_len--;
        turn = (turn == "red" ? "black" : "red");
        current_hash ^= ZOBRIST_TURN;
    }

    bool is_repetition() const {
        for (int i = path_len - 3; i >= 0; i -= 2) {
            if (path_hashes[i] == current_hash) return true;
        }
        return false;
    }

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

        if (lower_p == 'r') {
            int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                while(in_board(nr, nc)) {
                    if (board[nr][nc] == '.') {
                        moves.push_back({r, c, nr, nc});
                    } else {
                        if (!is_teammate(nr, nc, red_turn))
                            moves.push_back({r, c, nr, nc});
                        break;
                    }
                    nr += dr[i]; nc += dc[i];
                }
            }
        } else if (lower_p == 'n') {
            int dr[] = {-2, -2, 2, 2, -1, 1, -1, 1};
            int dc[] = {-1, 1, -1, 1, -2, -2, 2, 2};
            int lr[] = {-1, -1, 1, 1, 0, 0, 0, 0};
            int lc[] = {0, 0, 0, 0, -1, -1, 1, 1};
            for(int i=0; i<8; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                int leg_r = r + lr[i], leg_c = c + lc[i];
                if (in_board(nr, nc) && board[leg_r][leg_c] == '.' && !is_teammate(nr, nc, red_turn))
                    moves.push_back({r, c, nr, nc});
            }
        } else if (lower_p == 'c') {
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
                            if (!is_teammate(nr, nc, red_turn))
                                moves.push_back({r, c, nr, nc});
                            break;
                        }
                    }
                    nr += dr[i]; nc += dc[i];
                }
            }
        } else if (lower_p == 'b') {
            int dr[] = {-2, -2, 2, 2};
            int dc[] = {-2, 2, -2, 2};
            int er[] = {-1, -1, 1, 1};
            int ec[] = {-1, 1, -1, 1};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                int eye_r = r + er[i], eye_c = c + ec[i];
                if (in_board(nr, nc) && board[eye_r][eye_c] == '.' && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 5) || (!red_turn && nr <= 4))
                        moves.push_back({r, c, nr, nc});
                }
            }
        } else if (lower_p == 'a') {
            int dr[] = {-1, -1, 1, 1};
            int dc[] = {-1, 1, -1, 1};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                if (in_board(nr, nc) && nc >= 3 && nc <= 5 && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 7) || (!red_turn && nr <= 2))
                        moves.push_back({r, c, nr, nc});
                }
            }
        } else if (lower_p == 'k') {
            int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                if (in_board(nr, nc) && nc >= 3 && nc <= 5 && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 7) || (!red_turn && nr <= 2))
                        moves.push_back({r, c, nr, nc});
                }
            }
            int direction = red_turn ? -1 : 1;
            int check_r = r + direction;
            while (check_r >= 0 && check_r < ROWS) {
                char target = board[check_r][c];
                if (target == '.') {
                    check_r += direction;
                } else {
                    char enemy_king = red_turn ? 'k' : 'K';
                    if (target == enemy_king) moves.push_back({r, c, check_r, c});
                    break;
                }
            }
        } else if (lower_p == 'p') {
            int dr = red_turn ? -1 : 1;
            int nr = r + dr;
            if (in_board(nr, c) && !is_teammate(nr, c, red_turn))
                moves.push_back({r, c, nr, c});
            if ((red_turn && r <= 4) || (!red_turn && r >= 5)) {
                if (in_board(r, c-1) && !is_teammate(r, c-1, red_turn)) moves.push_back({r, c, r, c-1});
                if (in_board(r, c+1) && !is_teammate(r, c+1, red_turn)) moves.push_back({r, c, r, c+1});
            }
        }
        return moves;
    }

    std::vector<Move> get_all_moves(bool is_red_turn, bool only_captures = false) {
        std::vector<Move> moves;
        for(int r=0; r<ROWS; ++r) {
            for(int c=0; c<COLS; ++c) {
                char p = board[r][c];
                if (p != '.' && is_red(p) == is_red_turn) {
                    std::vector<Move> ms = get_valid_moves(r, c);
                    for(const auto& m : ms) {
                        if (!only_captures || board[m.r2][m.c2] != '.')
                            moves.push_back(m);
                    }
                }
            }
        }
        return moves;
    }

    int evaluate() { return current_score; }

    bool is_in_check(bool is_red_turn) {
        int kr = king_pos[is_red_turn ? 0 : 1].first;
        int kc = king_pos[is_red_turn ? 0 : 1].second;
        if (kr == -1) return true;

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

        int ndr[] = {-2, -2, 2, 2, -1, 1, -1, 1};
        int ndc[] = {-1, 1, -1, 1, -2, -2, 2, 2};
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

        char enemy_pawn = is_red_turn ? 'p' : 'P';
        int p_dir = is_red_turn ? 1 : -1;
        int check_r = kr - p_dir;
        if (in_board(check_r, kc) && board[check_r][kc] == enemy_pawn) return true;
        if (in_board(kr, kc-1) && board[kr][kc-1] == enemy_pawn) return true;
        if (in_board(kr, kc+1) && board[kr][kc+1] == enemy_pawn) return true;

        return false;
    }

    int see_value(char p) {
        switch (p) {
            case 'k': case 'K': return 10000;
            case 'r': case 'R': return 900;
            case 'n': case 'N': case 'c': case 'C': return 400;
            case 'a': case 'A': case 'b': case 'B': return 120;
            case 'p': case 'P': return 100;
            default: return 0;
        }
    }

    void attackers_to(int tr, int tc, bool by_red, std::vector<std::tuple<int,int,char>>& out) {
        out.clear();
        int drs[4] = {0,0,1,-1};
        int dcs[4] = {1,-1,0,0};
        for (int i = 0; i < 4; ++i) {
            int nr = tr + drs[i], nc = tc + dcs[i];
            int seen = 0;
            while (in_board(nr, nc)) {
                char p = board[nr][nc];
                if (p != '.') {
                    if (seen == 0) {
                        if (is_red(p) == by_red) {
                            char lp = std::tolower(p);
                            if (lp == 'r') out.push_back(std::make_tuple(nr, nc, p));
                            else if (lp == 'k' && std::abs(nr - tr) + std::abs(nc - tc) == 1)
                                out.push_back(std::make_tuple(nr, nc, p));
                        }
                        seen = 1;
                    } else {
                        if (is_red(p) == by_red && std::tolower(p) == 'c')
                            out.push_back(std::make_tuple(nr, nc, p));
                        break;
                    }
                }
                nr += drs[i]; nc += dcs[i];
            }
        }
        int kfrom[8][4] = {
            {-2,-1,-1,0},{-2,1,-1,0},{2,-1,1,0},{2,1,1,0},
            {-1,-2,0,-1},{1,-2,0,-1},{-1,2,0,1},{1,2,0,1}
        };
        for (int i = 0; i < 8; ++i) {
            int nr = tr + kfrom[i][0], nc = tc + kfrom[i][1];
            int lr = tr + kfrom[i][2], lc = tc + kfrom[i][3];
            if (in_board(nr,nc) && in_board(lr,lc)) {
                char p = board[nr][nc];
                if (p != '.' && is_red(p) == by_red && std::tolower(p) == 'n' && board[lr][lc] == '.')
                    out.push_back(std::make_tuple(nr, nc, p));
            }
        }
        char pawn = by_red ? 'P' : 'p';
        int fwd = by_red ? 1 : -1;
        int rfront = tr + fwd;
        if (in_board(rfront, tc) && board[rfront][tc] == pawn)
            out.push_back(std::make_tuple(rfront, tc, pawn));
        bool pawn_crossed_at_tr = by_red ? (tr <= 4) : (tr >= 5);
        if (pawn_crossed_at_tr) {
            if (in_board(tr, tc-1) && board[tr][tc-1] == pawn) out.push_back(std::make_tuple(tr, tc-1, pawn));
            if (in_board(tr, tc+1) && board[tr][tc+1] == pawn) out.push_back(std::make_tuple(tr, tc+1, pawn));
        }
    }

    int see(const Move& mv) {
        char attacker = board[mv.r1][mv.c1];
        char victim   = board[mv.r2][mv.c2];
        if (attacker == '.') return 0;
        bool attacker_is_red = is_red(attacker);
        int tr = mv.r2, tc = mv.c2;
        int sr = mv.r1, sc = mv.c1;

        std::vector<int> gain;
        gain.push_back(see_value(victim));
        std::vector<std::tuple<int,int,char>> removed;
        removed.push_back(std::make_tuple(sr, sc, board[sr][sc]));
        board[sr][sc] = '.';
        int on_sq = see_value(attacker);
        bool side = !attacker_is_red;

        std::vector<std::tuple<int,int,char>> atk_buf;
        while (true) {
            attackers_to(tr, tc, side, atk_buf);
            if (atk_buf.empty()) break;
            int best = 0;
            int best_v = see_value(std::get<2>(atk_buf[0]));
            for (size_t i = 1; i < atk_buf.size(); ++i) {
                int v = see_value(std::get<2>(atk_buf[i]));
                if (v < best_v) { best_v = v; best = (int)i; }
            }
            int ar = std::get<0>(atk_buf[best]);
            int ac = std::get<1>(atk_buf[best]);
            char ap = std::get<2>(atk_buf[best]);
            if (std::tolower(ap) == 'k') {
                removed.push_back(std::make_tuple(ar, ac, board[ar][ac]));
                board[ar][ac] = '.';
                std::vector<std::tuple<int,int,char>> chk;
                attackers_to(tr, tc, !side, chk);
                if (!chk.empty()) {
                    auto t = removed.back(); removed.pop_back();
                    board[std::get<0>(t)][std::get<1>(t)] = std::get<2>(t);
                    break;
                }
                gain.push_back(on_sq - gain.back());
                on_sq = see_value(ap);
                side = !side;
                break;
            }
            removed.push_back(std::make_tuple(ar, ac, board[ar][ac]));
            board[ar][ac] = '.';
            gain.push_back(on_sq - gain.back());
            on_sq = see_value(ap);
            side = !side;
        }
        for (auto it = removed.rbegin(); it != removed.rend(); ++it)
            board[std::get<0>(*it)][std::get<1>(*it)] = std::get<2>(*it);

        int d = (int)gain.size() - 1;
        while (d > 0) {
            gain[d-1] = -std::max(-gain[d-1], gain[d]);
            d--;
        }
        return gain[0];
    }

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

        if (qs_depth > 6) return evaluate();

        std::vector<Move> moves;
        if (in_check) {
            if (qs_depth > 3) return evaluate();
            moves = get_all_moves(maximizing_player, false);
        } else {
            moves = get_all_moves(maximizing_player, true);
            std::vector<Move> filtered;
            filtered.reserve(moves.size());
            for (const auto& m : moves) {
                char victim = board[m.r2][m.c2];
                char atk = board[m.r1][m.c1];
                int vv = PIECE_VALUES[victim];
                int av = PIECE_VALUES[atk];
                if (vv >= av) filtered.push_back(m);
                else if (see(m) >= 0) filtered.push_back(m);
            }
            moves = std::move(filtered);
        }

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

        if (in_check && !has_legal)
            return maximizing_player ? -SCORE_INF + qs_depth : SCORE_INF - qs_depth;

        return maximizing_player ? alpha : beta;
    }

    struct SearchResult { int score; Move move; };

    SearchResult minimax(int depth, int alpha, int beta, bool maximizing_player,
                         bool allow_null = true, int check_ext_left = -1,
                         bool is_root = false, int ply = 0) {
        if (check_ext_left < 0) check_ext_left = std::max(1, depth / 2);
        nodes++;

        if (!is_root && is_repetition()) return {0, NO_MOVE};

        if (stop_search) return {0, NO_MOVE};
        if ((nodes & 2047) == 0) {
            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(now - start_tp).count();
            if (elapsed > time_limit) stop_search = true;
        }

        bool in_check = is_in_check(maximizing_player);
        int ext = (check_ext_left > 0 && in_check) ? 1 : 0;

        if (depth + ext <= 0) {
            int val = quiescence_search(alpha, beta, maximizing_player);
            return {val, NO_MOVE};
        }

        size_t idx = current_hash & TT_MASK;
        TTEntry& tte = tt[idx];
        Move tt_move = NO_MOVE;
        if (tte.flag != TT_INVALID && tte.hash == current_hash) {
            int tt_score = tte.score;
            if (tt_score >  MATE_BOUND) tt_score -= ply;
            else if (tt_score < -MATE_BOUND) tt_score += ply;

            if (!is_root && tte.depth >= depth) {
                if (tte.flag == TT_EXACT) return {tt_score, tte.best_move};
                if (tte.flag == TT_ALPHA && tt_score <= alpha) return {tt_score, tte.best_move};
                if (tte.flag == TT_BETA  && tt_score >= beta)  return {tt_score, tte.best_move};
            }
            tt_move = tte.best_move;
        }

        if (king_pos[0].first == -1) return {-SCORE_INF + ply, NO_MOVE};
        if (king_pos[1].first == -1) return { SCORE_INF - ply, NO_MOVE};

        int eval = evaluate();

        // Reverse Futility Pruning
        if (!is_root && depth <= 7 && !in_check
            && std::abs(beta) < MATE_BOUND && std::abs(alpha) < MATE_BOUND) {
            int margin = 80 * depth;
            if (maximizing_player) {
                if (eval - margin >= beta) return {eval - margin, NO_MOVE};
            } else {
                if (eval + margin <= alpha) return {eval + margin, NO_MOVE};
            }
        }

        // Razoring
        if (!is_root && depth <= 3 && !in_check
            && std::abs(alpha) < MATE_BOUND && std::abs(beta) < MATE_BOUND) {
            int margin = 200 * depth;
            if (maximizing_player && eval + margin <= alpha) {
                int q = quiescence_search(alpha, beta, true);
                if (q <= alpha) return {q, NO_MOVE};
            } else if (!maximizing_player && eval - margin >= beta) {
                int q = quiescence_search(alpha, beta, false);
                if (q >= beta) return {q, NO_MOVE};
            }
        }

        // NMP
        if (OPEN_NMP && !is_root && depth >= 3 && !in_check && allow_null
            && std::abs(beta) < MATE_BOUND && std::abs(alpha) < MATE_BOUND) {
            int R = 3 + depth / 6;
            if (maximizing_player)
                R += std::min(3, std::max(0, (eval - beta) / 200));
            else
                R += std::min(3, std::max(0, (alpha - eval) / 200));
            int next_depth = std::max(0, depth - 1 - R);

            make_null_move();
            int val;
            if (maximizing_player)
                val = minimax(next_depth, beta - 1, beta, false, false, 0, false, ply + 1).score;
            else
                val = minimax(next_depth, alpha, alpha + 1, true, false, 0, false, ply + 1).score;
            undo_null_move();

            if (stop_search) return {0, NO_MOVE};

            bool cutoff = maximizing_player
                ? (val >= beta && std::abs(val) < MATE_BOUND)
                : (val <= alpha && std::abs(val) < MATE_BOUND);
            if (cutoff) {
                if (depth >= 10) {
                    int verify_d = depth - R;
                    int v;
                    if (maximizing_player) {
                        v = minimax(verify_d, beta - 1, beta, true, false, check_ext_left, false, ply).score;
                        if (v >= beta) return {beta, NO_MOVE};
                    } else {
                        v = minimax(verify_d, alpha, alpha + 1, false, false, check_ext_left, false, ply).score;
                        if (v <= alpha) return {alpha, NO_MOVE};
                    }
                } else {
                    return {maximizing_player ? beta : alpha, NO_MOVE};
                }
            }
        }

        // IID
        if (!tt_move.is_valid() && depth >= 6) {
            int iid_d = depth - 4;
            SearchResult iid = minimax(iid_d, alpha, beta, maximizing_player, false, check_ext_left, false, ply);
            tt_move = iid.move;
            if (stop_search) return {0, NO_MOVE};
        }

        std::vector<Move> moves = get_all_moves(maximizing_player);
        if (moves.empty()) {
            return {maximizing_player ? -SCORE_INF + ply : SCORE_INF - ply, NO_MOVE};
        }

        if (is_root && forbidden_move.is_valid()) {
            std::vector<Move> filtered;
            filtered.reserve(moves.size());
            for (const auto& mv : moves)
                if (!(mv == forbidden_move)) filtered.push_back(mv);
            if (!filtered.empty()) moves = std::move(filtered);
        }

        Move prev_played = NO_MOVE;
        if (path_len >= 2) prev_played = path_moves[path_len - 1];
        Move cm = NO_MOVE;
        if (prev_played.is_valid())
            cm = counter_move[prev_played.r1][prev_played.c1][prev_played.r2][prev_played.c2];

        Move k1 = killer_moves[ply][0];
        Move k2 = killer_moves[ply][1];
        std::vector<int> mscore(moves.size(), 0);
        for (size_t i = 0; i < moves.size(); ++i) {
            const Move& m = moves[i];
            int sc;
            if (tt_move.is_valid() && m == tt_move) {
                sc = 300000000;
            } else {
                char victim = board[m.r2][m.c2];
                if (victim != '.') {
                    int vv = PIECE_VALUES[victim];
                    int av = PIECE_VALUES[board[m.r1][m.c1]];
                    if (vv < av && see(m) < 0)
                        sc = 1000000 + vv * 10 - av;
                    else
                        sc = 10000000 + vv * 10 - av;
                } else if (m == k1) {
                    sc = 9000000;
                } else if (m == k2) {
                    sc = 8000000;
                } else if (cm.is_valid() && m == cm) {
                    sc = 7000000;
                } else {
                    sc = history_table[m.r1][m.c1][m.r2][m.c2];
                }
            }
            mscore[i] = sc;
        }
        std::vector<size_t> order(moves.size());
        for (size_t i = 0; i < order.size(); ++i) order[i] = i;
        std::sort(order.begin(), order.end(),
                  [&](size_t a, size_t b) { return mscore[a] > mscore[b]; });
        std::vector<Move> sorted_moves;
        sorted_moves.reserve(moves.size());
        for (size_t i : order) sorted_moves.push_back(moves[i]);
        moves = std::move(sorted_moves);

        Move best_move = moves[0];
        int best_score = maximizing_player ? -SCORE_INF - 100 : SCORE_INF + 100;
        int moves_count = 0;
        int original_alpha = alpha;
        int original_beta  = beta;

        std::vector<Move> quiet_tried;

        for (const auto& m : moves) {
            moves_count++;
            char captured = board[m.r2][m.c2];
            bool is_capture = (captured != '.');
            bool is_killer = (m == k1 || m == k2);

            // LMP
            if (!is_root && depth <= 8 && !in_check && !is_capture && !is_killer
                && best_score > -MATE_BOUND
                && moves_count > 3 + depth * depth) {
                continue;
            }

            // Futility
            if (!is_root && depth <= 6 && !in_check && !is_capture
                && moves_count > 1
                && best_score > -MATE_BOUND && best_score < MATE_BOUND) {
                int fmargin = 100 + 100 * depth;
                if (maximizing_player && eval + fmargin <= alpha) continue;
                if (!maximizing_player && eval - fmargin >= beta) continue;
            }

            // SEE pruning
            if (!is_root && depth <= 4 && is_capture && !in_check) {
                int vv = PIECE_VALUES[captured];
                int av = PIECE_VALUES[board[m.r1][m.c1]];
                if (vv < av && see(m) < -50) continue;
            }

            char cap = make_move(m);
            if (is_in_check(maximizing_player)) {
                undo_move(m, cap);
                continue;
            }

            bool gives_check = is_in_check(!maximizing_player);
            bool do_lmr = (depth >= 3 && moves_count > 3 && !is_capture && !in_check
                           && !is_killer && !gives_check);
            int reduction = 0;
            if (do_lmr) {
                int dd = std::min(depth, 63);
                int mm = std::min(moves_count, 63);
                reduction = LMR_TABLE[dd][mm];
                int h = history_table[m.r1][m.c1][m.r2][m.c2];
                if (h >  4096) reduction--;
                if (h < -4096) reduction++;
                reduction = std::max(0, std::min(reduction, depth - 2));
            }

            int score;
            if (maximizing_player) {
                if (moves_count == 1) {
                    score = minimax(depth - 1 + ext, alpha, beta, false, true,
                                    check_ext_left - ext, false, ply + 1).score;
                } else {
                    int s_depth = std::max(0, depth - 1 - reduction);
                    score = minimax(s_depth + ext, alpha, alpha + 1, false, true,
                                    check_ext_left - ext, false, ply + 1).score;
                    if (score > alpha && reduction > 0) {
                        score = minimax(depth - 1 + ext, alpha, alpha + 1, false, true,
                                        check_ext_left - ext, false, ply + 1).score;
                    }
                    if (score > alpha && score < beta) {
                        score = minimax(depth - 1 + ext, alpha, beta, false, true,
                                        check_ext_left - ext, false, ply + 1).score;
                    }
                }
            } else {
                if (moves_count == 1) {
                    score = minimax(depth - 1 + ext, alpha, beta, true, true,
                                    check_ext_left - ext, false, ply + 1).score;
                } else {
                    int s_depth = std::max(0, depth - 1 - reduction);
                    score = minimax(s_depth + ext, beta - 1, beta, true, true,
                                    check_ext_left - ext, false, ply + 1).score;
                    if (score < beta && reduction > 0) {
                        score = minimax(depth - 1 + ext, beta - 1, beta, true, true,
                                        check_ext_left - ext, false, ply + 1).score;
                    }
                    if (score < beta && score > alpha) {
                        score = minimax(depth - 1 + ext, alpha, beta, true, true,
                                        check_ext_left - ext, false, ply + 1).score;
                    }
                }
            }

            undo_move(m, cap);
            if (stop_search) return {0, NO_MOVE};

            if (!is_capture) quiet_tried.push_back(m);

            if (maximizing_player) {
                if (score > best_score) {
                    best_score = score;
                    best_move = m;
                    if (best_score > alpha) {
                        alpha = best_score;
                        if (alpha >= beta) {
                            if (!is_capture) {
                                int bonus = depth * depth;
                                int& h = history_table[m.r1][m.c1][m.r2][m.c2];
                                h += bonus;
                                if (h > (1 << 20)) h = (1 << 20);
                                if (killer_moves[ply][0] != m) {
                                    killer_moves[ply][1] = killer_moves[ply][0];
                                    killer_moves[ply][0] = m;
                                }
                                if (prev_played.is_valid())
                                    counter_move[prev_played.r1][prev_played.c1]
                                                [prev_played.r2][prev_played.c2] = m;
                                for (size_t i = 0; i + 1 < quiet_tried.size(); ++i) {
                                    const Move& q = quiet_tried[i];
                                    int& hq = history_table[q.r1][q.c1][q.r2][q.c2];
                                    hq -= bonus;
                                    if (hq < -(1 << 20)) hq = -(1 << 20);
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
                            if (!is_capture) {
                                int bonus = depth * depth;
                                int& h = history_table[m.r1][m.c1][m.r2][m.c2];
                                h += bonus;
                                if (h > (1 << 20)) h = (1 << 20);
                                if (killer_moves[ply][0] != m) {
                                    killer_moves[ply][1] = killer_moves[ply][0];
                                    killer_moves[ply][0] = m;
                                }
                                if (prev_played.is_valid())
                                    counter_move[prev_played.r1][prev_played.c1]
                                                [prev_played.r2][prev_played.c2] = m;
                                for (size_t i = 0; i + 1 < quiet_tried.size(); ++i) {
                                    const Move& q = quiet_tried[i];
                                    int& hq = history_table[q.r1][q.c1][q.r2][q.c2];
                                    hq -= bonus;
                                    if (hq < -(1 << 20)) hq = -(1 << 20);
                                }
                            }
                            break;
                        }
                    }
                }
            }
        }

        int flag;
        if (best_score <= original_alpha)      flag = TT_ALPHA;
        else if (best_score >= original_beta)  flag = TT_BETA;
        else                                   flag = TT_EXACT;

        bool replace = (tte.flag == TT_INVALID)
                    || (tte.hash == current_hash)
                    || (tte.age != tt_age)
                    || (depth >= tte.depth);
        if (replace) {
            int store_score = best_score;
            if (store_score >  MATE_BOUND) store_score += ply;
            else if (store_score < -MATE_BOUND) store_score -= ply;

            tte.hash = current_hash;
            tte.depth = depth;
            tte.flag = flag;
            tte.score = store_score;
            tte.best_move = best_move;
            tte.age = tt_age;
        }

        return {best_score, best_move};
    }

    SearchResult search_main(double max_time, bool is_ai_red) {
        start_tp = std::chrono::steady_clock::now();
        time_limit = max_time;
        stop_search = false;
        tt_age++;

        SearchResult last_res = {0, NO_MOVE};
        int prev_score = 0;

        for (int depth = 1; depth < 64; ++depth) {
            SearchResult res;

            if (depth < 4) {
                res = minimax(depth, -SCORE_INF - 1, SCORE_INF + 1,
                              is_ai_red, true, -1, true, 0);
            } else {
                int delta = 30;
                int alpha = std::max(prev_score - delta, -SCORE_INF - 1);
                int beta  = std::min(prev_score + delta,  SCORE_INF + 1);

                while (true) {
                    res = minimax(depth, alpha, beta, is_ai_red, true, -1, true, 0);
                    if (stop_search) break;

                    if (res.score <= alpha) {
                        beta = (alpha + beta) / 2;
                        alpha = std::max(res.score - delta, -SCORE_INF - 1);
                        delta += delta / 2;
                    } else if (res.score >= beta) {
                        beta = std::min(res.score + delta, SCORE_INF + 1);
                        delta += delta / 2;
                    } else {
                        break;
                    }
                    if (delta > 1000) {
                        alpha = -SCORE_INF - 1;
                        beta  =  SCORE_INF + 1;
                    }
                }
            }

            if (stop_search) break;
            last_res = res;
            prev_score = res.score;

            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(now - start_tp).count();

            logfile << "info depth " << depth
                    << " score " << res.score
                    << " time " << (int)(elapsed * 1000)
                    << " nodes " << nodes
                    << std::endl;

            if (std::abs(res.score) > MATE_BOUND) break;
            if (elapsed > max_time * 0.16 && depth >= 4) break;
        }
        return last_res;
    }
};

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    init_pst_raw();
    init_zobrist();
    init_lmr();

    XiangqiEngine engine;
    std::string line;
    int cnt = 0;

    while (std::getline(std::cin, line)) {
        if (line == "quit") break;
        if (line == "ready") std::cout << "readyok" << std::endl;

        if (line.substr(0, 4) == "side") {
            if (line.find("red") != std::string::npos) engine.player_side = "red";
            else engine.player_side = "black";
        }
        else if (line.substr(0, 4) == "move") {
            std::stringstream ss(line);
            std::string cmd;
            int r1, c1, r2, c2;
            ss >> cmd >> r1 >> c1 >> r2 >> c2;
            Move m = {r1, c1, r2, c2};
            char cap = engine.make_move(m);
            if (cap != '.') {
                engine.path_len = 0;
                engine.path_hashes[engine.path_len] = engine.current_hash;
                engine.path_moves[engine.path_len]  = NO_MOVE;
                engine.path_len++;
            }
        }
        else if (line.substr(0, 6) == "forbid") {
            std::stringstream ss(line);
            std::string cmd;
            int r1, c1, r2, c2;
            ss >> cmd >> r1 >> c1 >> r2 >> c2;
            engine.forbidden_move = {r1, c1, r2, c2};
        }
        else if (line.substr(0, 6) == "search") {
            cnt++;
            engine.nodes = 0;
            bool is_ai_red = (engine.player_side == "black");

            XiangqiEngine::SearchResult res;
            if (USE_DEPTH) {
                res = engine.minimax(LONG_MAX_DEPTH, -SCORE_INF - 1, SCORE_INF + 1,
                                     is_ai_red, true, -1, true, 0);
            } else {
                double search_time = (cnt <= 3) ? 15.0 : LONG_MAX_TIME;
                res = engine.search_main(search_time, is_ai_red);
            }

            if (res.move.is_valid()) {
                Move best = res.move;
                char cap = engine.make_move(best);
                if (cap != '.') {
                    engine.path_len = 0;
                    engine.path_hashes[engine.path_len] = engine.current_hash;
                    engine.path_moves[engine.path_len]  = NO_MOVE;
                    engine.path_len++;
                }
                std::cout << "move " << best.r1 << " " << best.c1 << " "
                          << best.r2 << " " << best.c2 << std::endl;
            } else {
                std::cout << "resign" << std::endl;
            }
            engine.forbidden_move = NO_MOVE;
        }
        else if (line == "print") {
            for(int r=0; r<10; ++r) {
                for(int c=0; c<9; ++c) std::cout << engine.board[r][c] << " ";
                std::cout << std::endl;
            }
        }
    }
    return 0;
}
// g++ -O3 -std=c++11 -o xiangqi_ai xiangqi_ai_v2.cpp