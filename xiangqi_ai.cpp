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
 int debug[10];

std::ofstream logfile("engine_log.txt", std::ios::app);
//int debugflag = 0; //��ʱ�ĵ���flag 
//int cnt=0;
// ============================================================
// ȫ������
// ============================================================
const int USE_DEPTH = 0;
const int LONG_MAX_DEPTH = 8;
const int OPEN_NMP = 1;
const double LONG_MAX_TIME = 5.0;

const int ROWS = 10;
const int COLS = 9;
const int SCORE_INF = 30000;
const int MATE_BOUND = 20000;          // ����??> ??����Ϊɱ���?

const int TT_EXACT = 0;
const int TT_ALPHA = 1;
const int TT_BETA = 2;
const int TT_INVALID = -1;

const size_t TT_BITS = 23;             // 8M?? ??80MB
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

int PIECE_VALUES[256];

void init_piece_values() {
    for (int i = 0; i < 256; ++i) PIECE_VALUES[i] = 0;
    PIECE_VALUES[(unsigned char)'k'] = PIECE_VALUES[(unsigned char)'K'] = 10000;
    PIECE_VALUES[(unsigned char)'r'] = PIECE_VALUES[(unsigned char)'R'] = 1000;
    PIECE_VALUES[(unsigned char)'n'] = PIECE_VALUES[(unsigned char)'N'] = 450;
    PIECE_VALUES[(unsigned char)'c'] = PIECE_VALUES[(unsigned char)'C'] = 450;
    PIECE_VALUES[(unsigned char)'a'] = PIECE_VALUES[(unsigned char)'A'] = 120;
    PIECE_VALUES[(unsigned char)'b'] = PIECE_VALUES[(unsigned char)'B'] = 120;
    PIECE_VALUES[(unsigned char)'p'] = PIECE_VALUES[(unsigned char)'P'] = 100;
}

inline int get_base_value(char p) {
    return PIECE_VALUES[(unsigned char)p];
}

// Сд??(����??ASCII ��ĸ): �ȼ� std::tolower ���� locale ����
static inline char to_lower_ascii(char p) { return (char)(p | 0x20); }

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
        {90, 96,109, 97, 94, 97,109, 96, 90},
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
    //����
    for(int i=0; i<10; ++i)
        for(int j=0; j<9; ++j){
            raw_c[i][j] *=1.1;
            raw_n[i][j] *=1.1;
            raw_r[i][j] *=1.1;
        }

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

// ============================================================
// RankMask ������ (��/��)
// ============================================================
// �б�: [Դ�� 0..8][9λ��ռλ] -> 9λ�������� (�÷���ɴ���?)
// �б�: [Դ�� 0..9][10λ��ռλ] -> 10λ��������
uint16_t ROOK_ROW_ATT[9][512];
uint16_t ROOK_COL_ATT[10][1024];
uint16_t CANNON_ROW_ATT[9][512];
uint16_t CANNON_COL_ATT[10][1024];

void init_attack_tables() {
    static const int dirs[2] = {-1, +1};
    // �б� (���� 9)
    for (int sc = 0; sc < 9; ++sc) {
        for (int occ = 0; occ < 512; ++occ) {
            int rk = 0, cn = 0;
            for (int di = 0; di < 2; ++di) {
                int d = dirs[di];
                // ��: ������һ���赲��(��)Ϊֹ
                int nc = sc + d;
                while (nc >= 0 && nc < 9) {
                    rk |= 1 << nc;
                    if ((occ >> nc) & 1) break;
                    nc += d;
                }
                // ��: �׶�1 �����ո� (��Щ�� quiet)
                nc = sc + d;
                while (nc >= 0 && nc < 9 && !((occ >> nc) & 1)) {
                    cn |= 1 << nc;
                    nc += d;
                }
                // �׶�2: �����ڼ�, �ҵڶ�������Ϊ����Ŀ��
                if (nc >= 0 && nc < 9) {
                    nc += d;
                    while (nc >= 0 && nc < 9 && !((occ >> nc) & 1)) nc += d;
                    if (nc >= 0 && nc < 9) cn |= 1 << nc;
                }
            }
            ROOK_ROW_ATT[sc][occ]   = (uint16_t)rk;
            CANNON_ROW_ATT[sc][occ] = (uint16_t)cn;
        }
    }
    // �б� (���� 10)
    for (int sr = 0; sr < 10; ++sr) {
        for (int occ = 0; occ < 1024; ++occ) {
            int rk = 0, cn = 0;
            for (int di = 0; di < 2; ++di) {
                int d = dirs[di];
                int nr = sr + d;
                while (nr >= 0 && nr < 10) {
                    rk |= 1 << nr;
                    if ((occ >> nr) & 1) break;
                    nr += d;
                }
                nr = sr + d;
                while (nr >= 0 && nr < 10 && !((occ >> nr) & 1)) {
                    cn |= 1 << nr;
                    nr += d;
                }
                if (nr >= 0 && nr < 10) {
                    nr += d;
                    while (nr >= 0 && nr < 10 && !((occ >> nr) & 1)) nr += d;
                    if (nr >= 0 && nr < 10) cn |= 1 << nr;
                }
            }
            ROOK_COL_ATT[sr][occ]   = (uint16_t)rk;
            CANNON_COL_ATT[sr][occ] = (uint16_t)cn;
        }
    }
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
    int  turn;            // 0=red, 1=black
    std::string player_side;
    bool game_over;
    int current_score;
    std::pair<int,int> king_pos[2];
    uint64_t current_hash;

    static const int PATH_CAP = 2048;
    uint64_t path_hashes[PATH_CAP];
    Move     path_moves[PATH_CAP];
    bool     path_gave_check[PATH_CAP];
    int      path_len;

    // ���������б�: side 0=?? 1=?? �������? sq = r*9 + c
    int piece_sq[2][16];
    int npieces[2];
    int piece_idx[10][9];          // -1 ��ʾ�ո�
    // ������ջ
    int undo_cap_idx[PATH_CAP];
    int undo_top;

    // ��/��ռλ (���� RankMask)
    uint16_t row_occ[10];           // bit c = ���� c ������
    uint16_t col_occ[9];            // bit r = ���� r ������
    uint16_t side_row_occ[2][10];   // ������ɫ
    uint16_t side_col_occ[2][9];

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

        turn = 0;
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

    inline bool is_red(char p) const { return p >= 'A' && p <= 'Z'; }
    inline bool in_board(int r, int c) const { return (unsigned)r < 10u && (unsigned)c < 9u; }

    inline int get_piece_value(char piece, int r, int c) const {
        if (piece == '.') return 0;
        bool red = (piece >= 'A' && piece <= 'Z');
        int val = PIECE_VALUES[(unsigned char)piece];
        int pst_val = red ? PST[(unsigned char)piece][r][c]
                          : PST[(unsigned char)piece][9-r][c];
        int total = val + pst_val;
        return red ? total : -total;
    }

    void init_score_and_hash() {
        current_score = 0;
        current_hash = 0;
        king_pos[0] = {-1,-1};
        king_pos[1] = {-1,-1};
        npieces[0] = npieces[1] = 0;
        for (int r = 0; r < 10; ++r) for (int c = 0; c < 9; ++c) piece_idx[r][c] = -1;
        undo_top = 0;
        for (int r = 0; r < 10; ++r) row_occ[r] = 0;
        for (int c = 0; c < 9; ++c) col_occ[c] = 0;
        for (int s = 0; s < 2; ++s) {
            for (int r = 0; r < 10; ++r) side_row_occ[s][r] = 0;
            for (int c = 0; c < 9; ++c) side_col_occ[s][c] = 0;
        }
        for(int r=0; r<10; ++r) {
            for(int c=0; c<9; ++c) {
                char p = board[r][c];
                if (p != '.') {
                    current_score += get_piece_value(p, r, c);
                    current_hash ^= ZOBRIST_TABLE[r][c][(unsigned char)p];
                    if (p == 'K') king_pos[0] = {r,c};
                    else if (p == 'k') king_pos[1] = {r,c};
                    int side = is_red(p) ? 0 : 1;
                    int idx = npieces[side]++;
                    piece_sq[side][idx] = r * 9 + c;
                    piece_idx[r][c] = idx;
                    row_occ[r] |= (uint16_t)(1 << c);
                    col_occ[c] |= (uint16_t)(1 << r);
                    side_row_occ[side][r] |= (uint16_t)(1 << c);
                    side_col_occ[side][c] |= (uint16_t)(1 << r);
                }
            }
        }
        if (turn == 1) current_hash ^= ZOBRIST_TURN;
        path_len = 0;
        path_hashes[path_len] = current_hash;
        path_moves[path_len]  = NO_MOVE;
        path_gave_check[path_len] = false;
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

        // ���������б�ά��
        int mover_side = is_red(moving_piece) ? 0 : 1;
        if (captured_piece != '.') {
            int opp = mover_side ^ 1;
            int cap_idx = piece_idx[m.r2][m.c2];
            undo_cap_idx[undo_top++] = cap_idx;
            int last = --npieces[opp];
            if (cap_idx != last) {
                int last_sq = piece_sq[opp][last];
                piece_sq[opp][cap_idx] = last_sq;
                piece_idx[last_sq / 9][last_sq % 9] = cap_idx;
            }
            // ռλ: ����Է���Ŀ�����? (��ռλ row/col_occ ��λ��Ȼ�� mover ռ��)
            side_row_occ[opp][m.r2] &= (uint16_t)~(1 << m.c2);
            side_col_occ[opp][m.c2] &= (uint16_t)~(1 << m.r2);
        } else {
            // �ǳ���: ��ռλ r2,c2 ֮ǰΪ��, ����λ
            row_occ[m.r2] |= (uint16_t)(1 << m.c2);
            col_occ[m.c2] |= (uint16_t)(1 << m.r2);
        }
        int idx_m = piece_idx[m.r1][m.c1];
        piece_sq[mover_side][idx_m] = m.r2 * 9 + m.c2;
        piece_idx[m.r1][m.c1] = -1;
        piece_idx[m.r2][m.c2] = idx_m;
        // ռλ: Դ�����?, mover ��ɫ����
        row_occ[m.r1] &= (uint16_t)~(1 << m.c1);
        col_occ[m.c1] &= (uint16_t)~(1 << m.r1);
        side_row_occ[mover_side][m.r1] &= (uint16_t)~(1 << m.c1);
        side_col_occ[mover_side][m.c1] &= (uint16_t)~(1 << m.r1);
        side_row_occ[mover_side][m.r2] |= (uint16_t)(1 << m.c2);
        side_col_occ[mover_side][m.c2] |= (uint16_t)(1 << m.r2);

        board[m.r2][m.c2] = moving_piece;
        board[m.r1][m.c1] = '.';
        turn ^= 1;

        if (path_len < PATH_CAP) {
            path_hashes[path_len] = current_hash;
            path_moves[path_len]  = m;
            // turn �ѷ�תΪ�Է�; ���Է�(�����ӷ�)�Ƿ񱻽�, �������Ƿ񽫾�
            path_gave_check[path_len] = is_in_check(turn == 0);
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

        // ���������б�����
        int mover_side = is_red(moved_piece) ? 0 : 1;
        int idx_m = piece_idx[m.r2][m.c2];
        piece_sq[mover_side][idx_m] = m.r1 * 9 + m.c1;
        piece_idx[m.r2][m.c2] = -1;
        piece_idx[m.r1][m.c1] = idx_m;
        // ռλ����
        row_occ[m.r1] |= (uint16_t)(1 << m.c1);
        col_occ[m.c1] |= (uint16_t)(1 << m.r1);
        side_row_occ[mover_side][m.r1] |= (uint16_t)(1 << m.c1);
        side_col_occ[mover_side][m.c1] |= (uint16_t)(1 << m.r1);
        side_row_occ[mover_side][m.r2] &= (uint16_t)~(1 << m.c2);
        side_col_occ[mover_side][m.c2] &= (uint16_t)~(1 << m.r2);
        if (captured != '.') {
            int opp = mover_side ^ 1;
            int cap_idx = undo_cap_idx[--undo_top];
            int cur = npieces[opp]++;
            // �ָ��Է�ռλ (��ռλ�� set, ����)
            side_row_occ[opp][m.r2] |= (uint16_t)(1 << m.c2);
            side_col_occ[opp][m.c2] |= (uint16_t)(1 << m.r2);
            // ����??swap-pop ??last_sq �ŵ�??cap_idx λ��, ���Ȱ���???
            if (cap_idx != cur) {
                int moved_pos = piece_sq[opp][cap_idx];
                piece_sq[opp][cur] = moved_pos;
                piece_idx[moved_pos / 9][moved_pos % 9] = cur;
            }
            piece_sq[opp][cap_idx] = m.r2 * 9 + m.c2;
            piece_idx[m.r2][m.c2] = cap_idx;
        } else {
            row_occ[m.r2] &= (uint16_t)~(1 << m.c2);
            col_occ[m.c2] &= (uint16_t)~(1 << m.r2);
        }

        board[m.r1][m.c1] = moved_piece;
        board[m.r2][m.c2] = captured;
        turn ^= 1;
    }

    void make_null_move() {
        turn ^= 1;
        current_hash ^= ZOBRIST_TURN;
        if (path_len < PATH_CAP) {
            path_hashes[path_len] = current_hash;
            path_moves[path_len]  = NO_MOVE;
            path_gave_check[path_len] = false;
            path_len++;
        }
    }

    void undo_null_move() {
        if (path_len > 0) path_len--;
        turn ^= 1;
        current_hash ^= ZOBRIST_TURN;
    }

    bool is_repetition() const {
        for (int i = path_len - 3; i >= 0; i -= 2) {
            if (path_hashes[i] == current_hash) return true;
        }
        return false;
    }

    // ��������(���޹���) �����и��ļ�ʵ��:
    //   ���� 0 ��ʾ��ѭ������������ѭ��;
    //   ���� +1 ��ʾ������ѭ���в�������(�����и�, ��ǰ���ӷ�ʤ);
    //   ���� -1 ��ʾ������ѭ���в�������(�����и�).
    // ��������׽/��ɱ/����������չ����.
    int repetition_verdict() const {
        int found = -1;
        for (int i = path_len - 3; i >= 0; i -= 2) {
            if (path_hashes[i] == current_hash) { found = i; break; }
        }
        if (found < 0) return 0;
        // ѭ���ڵ��ŷ�: path_moves[found+1 .. path_len-1]
        // ���һ�ŵ����ӷ�? = turn ^ 1 (turn �ǵ�ǰ���߷�)
        int last_mover = turn ^ 1;
        int moves_cnt[2] = {0, 0};
        int check_cnt[2] = {0, 0};
        for (int k = path_len - 1; k >= found + 1; --k) {
            int steps_from_last = (path_len - 1) - k; // 0,1,2,...
            int mover = last_mover ^ (steps_from_last & 1);
            moves_cnt[mover]++;
            if (path_gave_check[k]) check_cnt[mover]++;
        }
        bool perp0 = moves_cnt[0] > 0 && check_cnt[0] == moves_cnt[0];
        bool perp1 = moves_cnt[1] > 0 && check_cnt[1] == moves_cnt[1];
        if (perp0 == perp1) return 0; // ˫�������� or �������� -> ��
        int loser = perp0 ? 0 : 1;
        return (loser == turn) ? -1 : +1;
    }

    inline bool is_teammate(int r, int c, bool is_red_piece) const {
        char p = board[r][c];
        if (p == '.') return false;
        return is_red(p) == is_red_piece;
    }

    int gen_moves_for(int r, int c, Move* out) {
        int n = 0;
        char p = board[r][c];
        if (p == '.') return 0;
        bool red_turn = is_red(p);
        char lower_p = to_lower_ascii(p);
        #define ADDM(R1,C1,R2,C2) out[n++] = {R1,C1,R2,C2}

        if (lower_p == 'r') {
            int side = red_turn ? 0 : 1;
            uint16_t row_att = (uint16_t)(ROOK_ROW_ATT[c][row_occ[r]] & ~side_row_occ[side][r]);
            while (row_att) {
                int nc = __builtin_ctz(row_att); row_att &= (uint16_t)(row_att - 1);
                ADDM(r, c, r, nc);
            }
            uint16_t col_att = (uint16_t)(ROOK_COL_ATT[r][col_occ[c]] & ~side_col_occ[side][c]);
            while (col_att) {
                int nr = __builtin_ctz(col_att); col_att &= (uint16_t)(col_att - 1);
                ADDM(r, c, nr, c);
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
                    ADDM(r, c, nr, nc);
            }
        } else if (lower_p == 'c') {
            int side = red_turn ? 0 : 1;
            uint16_t row_att = (uint16_t)(CANNON_ROW_ATT[c][row_occ[r]] & ~side_row_occ[side][r]);
            while (row_att) {
                int nc = __builtin_ctz(row_att); row_att &= (uint16_t)(row_att - 1);
                ADDM(r, c, r, nc);
            }
            uint16_t col_att = (uint16_t)(CANNON_COL_ATT[r][col_occ[c]] & ~side_col_occ[side][c]);
            while (col_att) {
                int nr = __builtin_ctz(col_att); col_att &= (uint16_t)(col_att - 1);
                ADDM(r, c, nr, c);
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
                        ADDM(r, c, nr, nc);
                }
            }
        } else if (lower_p == 'a') {
            int dr[] = {-1, -1, 1, 1};
            int dc[] = {-1, 1, -1, 1};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                if (in_board(nr, nc) && nc >= 3 && nc <= 5 && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 7) || (!red_turn && nr <= 2))
                        ADDM(r, c, nr, nc);
                }
            }
        } else if (lower_p == 'k') {
            int dr[] = {0, 0, 1, -1};
            int dc[] = {1, -1, 0, 0};
            for(int i=0; i<4; ++i) {
                int nr = r + dr[i], nc = c + dc[i];
                if (in_board(nr, nc) && nc >= 3 && nc <= 5 && !is_teammate(nr, nc, red_turn)) {
                    if ((red_turn && nr >= 7) || (!red_turn && nr <= 2))
                        ADDM(r, c, nr, nc);
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
                    if (target == enemy_king) ADDM(r, c, check_r, c);
                    break;
                }
            }
        } else if (lower_p == 'p') {
            int dr = red_turn ? -1 : 1;
            int nr = r + dr;
            if (in_board(nr, c) && !is_teammate(nr, c, red_turn))
                ADDM(r, c, nr, c);
            if ((red_turn && r <= 4) || (!red_turn && r >= 5)) {
                if (in_board(r, c-1) && !is_teammate(r, c-1, red_turn)) ADDM(r, c, r, c-1);
                if (in_board(r, c+1) && !is_teammate(r, c+1, red_turn)) ADDM(r, c, r, c+1);
            }
        }
        #undef ADDM
        return n;
    }

    // д�� out, ��������; out ��������??128 ??
    int gen_all_moves(bool is_red_turn, bool only_captures, Move* out) {
        int n = 0;
        Move tmp[32];
        int side = is_red_turn ? 0 : 1;
        int np = npieces[side];
        for (int i = 0; i < np; ++i) {
            int sq = piece_sq[side][i];
            int r = sq / 9, c = sq - r * 9;
            int k = gen_moves_for(r, c, tmp);
            if (only_captures) {
                for (int j = 0; j < k; ++j)
                    if (board[tmp[j].r2][tmp[j].c2] != '.') out[n++] = tmp[j];
            } else {
                for (int j = 0; j < k; ++j) out[n++] = tmp[j];
            }
        }
        return n;
    }

    int evaluate() { return current_score; }

    bool is_in_check(bool is_red_turn) {
        int kr = king_pos[is_red_turn ? 0 : 1].first;
        int kc = king_pos[is_red_turn ? 0 : 1].second;
        if (kr == -1) return true;

        // ��/�������?/��: �� RankMask
        int enemy_side = is_red_turn ? 1 : 0;
        // �з����ϵĳ� (�������ֻ��ͬ��?, �з��򲻼��? king)
        uint16_t row_hit = (uint16_t)(ROOK_ROW_ATT[kc][row_occ[kr]] & side_row_occ[enemy_side][kr]);
        while (row_hit) {
            int nc = __builtin_ctz(row_hit); row_hit &= (uint16_t)(row_hit - 1);
            if (to_lower_ascii(board[kr][nc]) == 'r') return true;
        }
        // �з����ϵĳ��� (�������?)
        uint16_t col_hit = (uint16_t)(ROOK_COL_ATT[kr][col_occ[kc]] & side_col_occ[enemy_side][kc]);
        while (col_hit) {
            int nr = __builtin_ctz(col_hit); col_hit &= (uint16_t)(col_hit - 1);
            char lp = to_lower_ascii(board[nr][kc]);
            if (lp == 'r' || lp == 'k') return true;
        }
        // ��/���ϵ��� (�Գ���: �ӽ�λ�����������еľ��ǹ������ĵ���)
        uint16_t crow = (uint16_t)(CANNON_ROW_ATT[kc][row_occ[kr]] & side_row_occ[enemy_side][kr]);
        while (crow) {
            int nc = __builtin_ctz(crow); crow &= (uint16_t)(crow - 1);
            if (to_lower_ascii(board[kr][nc]) == 'c') return true;
        }
        uint16_t ccol = (uint16_t)(CANNON_COL_ATT[kr][col_occ[kc]] & side_col_occ[enemy_side][kc]);
        while (ccol) {
            int nr = __builtin_ctz(ccol); ccol &= (uint16_t)(ccol - 1);
            if (to_lower_ascii(board[nr][kc]) == 'c') return true;
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
                if (p != '.' && is_red(p) != is_red_turn && to_lower_ascii(p) == 'n') {
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

    struct Attacker { int r, c; char p; };
    // д�� out, ��������; out �������� 17 ??
    int attackers_to(int tr, int tc, bool by_red, Attacker* out) {
        int n = 0;
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
                            char lp = to_lower_ascii(p);
                            if (lp == 'r') out[n++] = {nr, nc, p};
                            else if (lp == 'k' && std::abs(nr - tr) + std::abs(nc - tc) == 1)
                                out[n++] = {nr, nc, p};
                        }
                        seen = 1;
                    } else {
                        if (is_red(p) == by_red && to_lower_ascii(p) == 'c')
                            out[n++] = {nr, nc, p};
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
                if (p != '.' && is_red(p) == by_red && to_lower_ascii(p) == 'n' && board[lr][lc] == '.')
                    out[n++] = {nr, nc, p};
            }
        }
        char pawn = by_red ? 'P' : 'p';
        int fwd = by_red ? 1 : -1;
        int rfront = tr + fwd;
        if (in_board(rfront, tc) && board[rfront][tc] == pawn)
            out[n++] = {rfront, tc, pawn};
        bool pawn_crossed_at_tr = by_red ? (tr <= 4) : (tr >= 5);
        if (pawn_crossed_at_tr) {
            if (in_board(tr, tc-1) && board[tr][tc-1] == pawn) out[n++] = {tr, tc-1, pawn};
            if (in_board(tr, tc+1) && board[tr][tc+1] == pawn) out[n++] = {tr, tc+1, pawn};
        }
        return n;
    }

    int see(const Move& mv) {
        char attacker = board[mv.r1][mv.c1];
        char victim   = board[mv.r2][mv.c2];
        if (attacker == '.') return 0;
        bool attacker_is_red = is_red(attacker);
        int tr = mv.r2, tc = mv.c2;
        int sr = mv.r1, sc = mv.c1;

        int gain[40]; int gn = 0;
        gain[gn++] = see_value(victim);
        struct Rem { int r, c; char p; };
        Rem removed[40]; int rn = 0;
        removed[rn++] = {sr, sc, board[sr][sc]};
        board[sr][sc] = '.';
        int on_sq = see_value(attacker);
        bool side = !attacker_is_red;

        Attacker atk_buf[20];
        while (true) {
            int an = attackers_to(tr, tc, side, atk_buf);
			/*���﷢�������⣺ 
�� 
. . b a k a b . .
. . . . n . . . .
. . n . c . . . .
p . p . p . P . p
c r . . . . . . .
C . P . . N . . .
P . . . P r . C P
. . N . B . . . .
. . . . . . . . .
R . . A K A B R .

���? 
. . b a k a b . .
. . . . n . . . .
. . n . c . . . .
p . p . p . P . p
. r . . . . . . . 
. . P . . C . . . 
P . . . P . . C P 
. . N . B . . . .
. . . . . . . . .
c . . A K A B R .

�����������еĶ����ü������Ե�������Ϊû�п��ߵĶ����� 


			*/
            if (an == 0) break;
            int best = 0;
            int best_v = see_value(atk_buf[0].p);
            for (int i = 1; i < an; ++i) {
                int v = see_value(atk_buf[i].p);
                if (v < best_v) { best_v = v; best = i; }
            }
            int ar = atk_buf[best].r;
            int ac = atk_buf[best].c;
            char ap = atk_buf[best].p;
            if (to_lower_ascii(ap) == 'k') {
                removed[rn++] = {ar, ac, board[ar][ac]};
                board[ar][ac] = '.';
                Attacker chk[20];
                int cn = attackers_to(tr, tc, !side, chk);
                if (cn > 0) {
                    Rem t = removed[--rn];
                    board[t.r][t.c] = t.p;
                    break;
                }
                gain[gn] = on_sq - gain[gn-1]; gn++;
                on_sq = see_value(ap);
                side = !side;
                break;
            }
            removed[rn++] = {ar, ac, board[ar][ac]};
            board[ar][ac] = '.';
            gain[gn] = on_sq - gain[gn-1]; gn++;
            on_sq = see_value(ap);
            side = !side;
        }
        for (int i = rn - 1; i >= 0; --i)
            board[removed[i].r][removed[i].c] = removed[i].p;

        int d = gn - 1;
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

        Move moves[128];
        int nm = 0;
        if (in_check) {
            if (qs_depth > 3) return evaluate();
            nm = gen_all_moves(maximizing_player, false, moves);
        } else {
            Move raw[128];
            int rn = gen_all_moves(maximizing_player, true, raw);
            for (int i = 0; i < rn; ++i) {
                const Move& m = raw[i];
                char victim = board[m.r2][m.c2];
                char atk = board[m.r1][m.c1];
                int vv = PIECE_VALUES[(unsigned char)victim];
                int av = PIECE_VALUES[(unsigned char)atk];
                if (vv >= av) moves[nm++] = m;
                else if (see(m) >= 0) moves[nm++] = m;
            }
        }

        std::sort(moves, moves + nm, [&](const Move& a, const Move& b) {
            int val_a = PIECE_VALUES[(unsigned char)board[a.r2][a.c2]];
            int val_b = PIECE_VALUES[(unsigned char)board[b.r2][b.c2]];
            return val_a > val_b;
        });

        bool has_legal = false;
        for (int mi = 0; mi < nm; ++mi) {
            const Move& m = moves[mi];
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
        if (!is_root) {
            int rv = repetition_verdict();
            if (rv != 0) {
                // ��ǰ���߷�=turn. rv=+1 ��ʾ����(turn^1)�����и�, �� turn һ��ʤ.
                // �������þ����ӽ�: �����ڸ�.
                int winner = (rv > 0) ? turn : (turn ^ 1);
                int sc = (winner == 0) ? (SCORE_INF - ply) : (-SCORE_INF + ply);
                return {sc, NO_MOVE};
            }
            if (is_repetition()) return {0, NO_MOVE};
        }

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

        Move moves[128];
        int nm = gen_all_moves(maximizing_player, false, moves);
        if (nm == 0) {
            return {maximizing_player ? -SCORE_INF + ply : SCORE_INF - ply, NO_MOVE};
        }

        if (is_root && forbidden_move.is_valid()) {
            int w = 0;
            for (int i = 0; i < nm; ++i)
                if (!(moves[i] == forbidden_move)) moves[w++] = moves[i];
            if (w > 0) nm = w;
        }

        Move prev_played = NO_MOVE;
        if (path_len >= 2) prev_played = path_moves[path_len - 1];
        Move cm = NO_MOVE;
        if (prev_played.is_valid())
            cm = counter_move[prev_played.r1][prev_played.c1][prev_played.r2][prev_played.c2];

        Move k1 = killer_moves[ply][0];
        Move k2 = killer_moves[ply][1];
        int mscore[128];
        for (int i = 0; i < nm; ++i) {
            const Move& m = moves[i];
            int sc;
            if (tt_move.is_valid() && m == tt_move) {
                sc = 300000000;
            } else {
                char victim = board[m.r2][m.c2];
                if (victim != '.') {
                    int vv = PIECE_VALUES[(unsigned char)victim];
                    int av = PIECE_VALUES[(unsigned char)board[m.r1][m.c1]];
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
        // ͬ��??moves[] ??mscore[] ���������������� (��������, nm ͨ�� < 50)
        for (int i = 1; i < nm; ++i) {
            int s = mscore[i]; Move mv = moves[i]; int j = i - 1;
            while (j >= 0 && mscore[j] < s) { mscore[j+1] = mscore[j]; moves[j+1] = moves[j]; --j; }
            mscore[j+1] = s; moves[j+1] = mv;
        }

        Move best_move = moves[0];
        int best_score = maximizing_player ? -SCORE_INF - 100 : SCORE_INF + 100;
        int moves_count = 0;
        int original_alpha = alpha;
        int original_beta  = beta;

        Move quiet_tried[128];
        int qt_n = 0;
        int legal_count = 0;
        bool pruned_any = false;
        for (int pass = 0; pass < 2; ++pass) {
            bool allow_pruning = (pass == 0);
            
            //��һ�������⣺�����һ���Ϸ�����29999�ˡ������ǲ�ok����breakҪ����
            //有一个大问题：如果第一步合法但分29999了。。。那不ok不能break要再找

            if (( maximizing_player ? best_score>=-MATE_BOUND : best_score<=MATE_BOUND)&&pass == 1 && (legal_count > 0 || !pruned_any)) break;
            // debug[pass]++; 千分之一不到的pass==1
			for (int mi = 0; mi < nm; ++mi) {
            	
                const Move& m = moves[mi];
//					printf("\n%d\t%d\t%d\t%d\t%d\t",mi,m.r1,m.c1,m.r2,m.c2);



                moves_count++;
            char captured = board[m.r2][m.c2];
            bool is_capture = (captured != '.');
            bool is_killer = (m == k1 || m == k2);

            // LMP
            if (allow_pruning && !is_root && depth <= 8 && !in_check && !is_capture && !is_killer
                && best_score > -MATE_BOUND
                && moves_count > 3 + depth * depth) {
                pruned_any = true;
                continue;
            }

            // Futility
            if (allow_pruning && !is_root && depth <= 6 && !in_check && !is_capture
                && moves_count > 1
                && best_score > -MATE_BOUND && best_score < MATE_BOUND) {
                int fmargin = 100 + 100 * depth;
                if (maximizing_player && eval + fmargin <= alpha) {
                    pruned_any = true;
                    continue;
                }
                if (!maximizing_player && eval - fmargin >= beta) {
                    pruned_any = true;
                    continue;
                }
            }
//			if (debugflag==2){
//				cnt++;
//			}
            // SEE pruning
            if (allow_pruning && !is_root && depth <= 4 && is_capture && !in_check) {
                int vv = PIECE_VALUES[(unsigned char)captured];
                int av = PIECE_VALUES[(unsigned char)board[m.r1][m.c1]];
                if (vv < av && see(m) < -50) {
                    pruned_any = true;
                    continue;
                }
            }
            char cap = make_move(m);
            if (is_in_check(maximizing_player)) {
                undo_move(m, cap);
                continue;
            }
            legal_count++;

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

            if (!is_capture) quiet_tried[qt_n++] = m;
            
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
                                for (int i = 0; i + 1 < qt_n; ++i) {
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
                                for (int i = 0; i + 1 < qt_n; ++i) {
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
            //这句话要删除也是仅仅合法不够。
//            if (!allow_pruning && legal_count) break;
        }
        }
        // ����α�Ϸ��߷����Խ� = ɱ�� (������ stalemate Ҳ���䴦��)
        if (legal_count == 0) {
            return {maximizing_player ? -SCORE_INF + ply : SCORE_INF - ply, NO_MOVE};
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
            // 发现全有pass1的。
           logfile << "info depth " << depth
                   << " score " << res.score
                   << " time " << (int)(elapsed * 1000)
                   << " nodes " << nodes
                   << std::endl;
            printf("%d %d\n",debug[0],debug[1]);

            if (std::abs(res.score) > MATE_BOUND) break;
            if (elapsed > max_time * 0.16 && depth >= 4) break;
        }
        return last_res;
    }
};

int main(int argc, char** argv) {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    init_piece_values();
    init_pst_raw();
    init_zobrist();
    init_lmr();
    init_attack_tables();

    XiangqiEngine engine;
    std::string line;
    int cnt = 0;

    // 调试用: 加一个文件参数则从文件读命令, 方便 IDE 单步调试
    // 例: xiangqi_ai_debug.exe engine_cmds_20260812_225910.log
    std::ifstream debug_in;
    std::istream* in = &std::cin;
    if (argc > 1) {
        debug_in.open(argv[1]);
        if (!debug_in) { std::cerr << "cannot open " << argv[1] << std::endl; return 1; }
        in = &debug_in;
    }

    while (std::getline(*in, line)) {
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
        else if (line.substr(0, 8) == "setboard") {
            // setboard <fen-rows> <side>      (side: 'w' or 'b'; Ĭ�� 'w')
            // ��: setboard 1cbakabr1/3RR4/9/p1p1C3p/6p2/2P6/P3P1ncP/4B1r2/1C2A4/4KAB2 b
            std::string rest = line.size() > 8 ? line.substr(9) : "";
            for (int r = 0; r < 10; ++r)
                for (int c = 0; c < 9; ++c)
                    engine.board[r][c] = '.';
            int r = 0, c = 0;
            size_t i = 0;
            while (i < rest.size() && rest[i] != ' ') {
                char ch = rest[i++];
                if (ch == '/')                      { r++; c = 0; }
                else if (ch >= '1' && ch <= '9')    { c += (ch - '0'); }
                else if (r < 10 && c < 9)           { engine.board[r][c++] = ch; }
            }
            engine.turn = 0;
            while (i < rest.size() && rest[i] == ' ') i++;
            if (i < rest.size() && (rest[i] == 'b' || rest[i] == 'B')) engine.turn = 1;

            // ������������״̬
            engine.forbidden_move = NO_MOVE;
            engine.game_over = false;
            for (auto& e : engine.tt) { e.flag = TT_INVALID; e.age = 0; }
            engine.tt_age = 0;
            std::memset(engine.history_table, 0, sizeof(engine.history_table));
            for (int d = 0; d < 64; ++d) {
                engine.killer_moves[d][0] = NO_MOVE;
                engine.killer_moves[d][1] = NO_MOVE;
            }
            for (int a = 0; a < 10; ++a)
                for (int b = 0; b < 9; ++b)
                    for (int cc = 0; cc < 10; ++cc)
                        for (int d = 0; d < 9; ++d)
                            engine.counter_move[a][b][cc][d] = NO_MOVE;

            engine.init_score_and_hash();
        }
    }
    return 0;
}

/*
g++ -O3 -std=c++17 -march=native -mtune=native -funroll-loops -fno-exceptions -fno-rtti -flto -DNDEBUG -static -static-libgcc -static-libstdc++ -o xiangqi_ai.exe xiangqi_ai.cpp
调试
g++ -g -O0 -std=c++17 -march=native -static -static-libgcc -static-libstdc++ -o xiangqi_ai_debug.exe xiangqi_ai.cpp

./xiangqi_ai 
setboard 3ak4/4a4/2n4PC/9/4R4/9/1p2C4/4r4/1n2A4/4KA3 b
side red
search
(���Ժ�)
https://sachess.com/zh-cn/xiangqi-photo-to-fen/ ͼƬת��fen


*/
