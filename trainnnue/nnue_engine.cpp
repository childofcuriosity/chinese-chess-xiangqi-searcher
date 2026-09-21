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
#include <cstdlib>
#if defined(__AVX2__)
#include <immintrin.h>
#endif
 int debug[10];

std::ofstream logfile("engine_log.txt", std::ios::app);
//int debugflag = 0; // 临时调试标志
//int cnt=0;
// ============================================================
// 全局配置
// ============================================================
const int USE_DEPTH = 0;
const int LONG_MAX_DEPTH = 8;
const int OPEN_NMP = 1;
const double LONG_MAX_TIME = 15.0;

const int ROWS = 10;
const int COLS = 9;
const int SCORE_INF = 30000;
const int MATE_BOUND = 20000;          // 绝对分值超过此阈值即视为杀棋分

const int TT_EXACT = 0;
const int TT_ALPHA = 1;
const int TT_BETA = 2;
const int TT_INVALID = -1;

const size_t TT_BITS = 23;             // 8M 个条目；实际内存占用由 sizeof(TTEntry) 决定。
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

#ifdef ENABLE_PROFILING
// Sample one call in every 256 to reduce steady_clock overhead.
struct ScopedProf {
    double* acc;
    long long* cnt;
    bool active;
    std::chrono::steady_clock::time_point t0;
    ScopedProf(double* a, long long* c) : acc(a), cnt(c) {
        ++*cnt;
        active = (*cnt & 255) == 0;
        if (active) t0 = std::chrono::steady_clock::now();
    }
    ~ScopedProf() {
        if (active) {
            *acc += std::chrono::duration<double, std::milli>(
                        std::chrono::steady_clock::now() - t0).count() * 256.0;
        }
    }
};
// Rare paths such as an anchor refresh are timed on every invocation. Sampling
// them at 1/256 would frequently report zero and hide the exact cost we want to
// measure.
struct AlwaysScopedProf {
    double* acc;
    std::chrono::steady_clock::time_point t0;
    explicit AlwaysScopedProf(double* a) : acc(a), t0(std::chrono::steady_clock::now()) {}
    ~AlwaysScopedProf() {
        *acc += std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - t0).count();
    }
};
#define PROFILE_SCOPE(name, acc, cnt) ScopedProf name(acc, cnt)
#define PROFILE_ALWAYS(name, acc) AlwaysScopedProf name(acc)
#else
#define PROFILE_SCOPE(name, acc, cnt) ((void)0)
#define PROFILE_ALWAYS(name, acc) ((void)0)
#endif

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

// 转为小写（仅用于 ASCII 字母）：等价于 std::tolower，但没有 locale 开销。
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
    // 调整车、马、炮的位置价值权重。
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
// RankMask 攻击表（车/炮）
// ============================================================
// 行表：[源列 0..8][9 位行占位] -> 9 位攻击掩码（该方向可达列）
// 列表：[源行 0..9][10 位列占位] -> 10 位攻击掩码
uint16_t ROOK_ROW_ATT[9][512];
uint16_t ROOK_COL_ATT[10][1024];
uint16_t CANNON_ROW_ATT[9][512];
uint16_t CANNON_COL_ATT[10][1024];

void init_attack_tables() {
    static const int dirs[2] = {-1, +1};
    // 行表（长度 9）
    for (int sc = 0; sc < 9; ++sc) {
        for (int occ = 0; occ < 512; ++occ) {
            int rk = 0, cn = 0;
            for (int di = 0; di < 2; ++di) {
                int d = dirs[di];
                // 车：滑到第一个阻挡子（含）为止。
                int nc = sc + d;
                while (nc >= 0 && nc < 9) {
                    rk |= 1 << nc;
                    if ((occ >> nc) & 1) break;
                    nc += d;
                }
                // 炮阶段 1：滑过空格，这些位置可生成非吃子着法。
                nc = sc + d;
                while (nc >= 0 && nc < 9 && !((occ >> nc) & 1)) {
                    cn |= 1 << nc;
                    nc += d;
                }
                // 炮阶段 2：越过炮架，找到第二个棋子作为吃子目标。
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
    // 列表（长度 10）
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

// ============================================================
// Compact CPU NNUE model (XQ-HalfKA 9x14x90)
// ============================================================
class NNUEModel {
public:
    static const int FEATURES = 9 * 14 * 90;
    static const int MAX_WIDTH = 128;

    bool loaded = false;
    bool residual = false;
    bool fixed_point = false;
    bool screlu = false;
    bool phase_heads = false;
    int width = 0;
    int hidden = 0;
    float k = 1.0f;
    float embedding_scale = 1.0f;
    float fc1_scale = 1.0f;
    float fc2_scale = 1.0f;
    float output_scale = 1.0f;
    std::vector<int32_t> feature_bias;
    std::vector<int16_t> embedding;
    std::vector<int32_t> fc1_bias;
    std::vector<int16_t> fc1_weight;
    std::vector<int32_t> fc2_bias;
    std::vector<int16_t> fc2_weight;
    std::vector<int32_t> output_bias;
    std::vector<int16_t> output_weight;
    std::string error;

    template<typename T>
    bool read_array(std::ifstream& f, std::vector<T>& out, size_t count) {
        out.resize(count);
        if (count == 0) return true;
        f.read(reinterpret_cast<char*>(out.data()),
               static_cast<std::streamsize>(count * sizeof(T)));
        return static_cast<bool>(f);
    }

    bool load(const std::string& path) {
        loaded = false;
        error.clear();
        std::ifstream f(path, std::ios::binary);
        if (!f) { error = "cannot open NNUE file: " + path; return false; }

        char magic[8]{};
        uint32_t version = 0, w = 0, h = 0, features = 0, flags = 0;
        f.read(magic, sizeof(magic));
        f.read(reinterpret_cast<char*>(&version), sizeof(version));
        f.read(reinterpret_cast<char*>(&w), sizeof(w));
        f.read(reinterpret_cast<char*>(&h), sizeof(h));
        f.read(reinterpret_cast<char*>(&features), sizeof(features));
        if (version >= 2) f.read(reinterpret_cast<char*>(&flags), sizeof(flags));
        f.read(reinterpret_cast<char*>(&k), sizeof(k));
        f.read(reinterpret_cast<char*>(&embedding_scale), sizeof(embedding_scale));
        f.read(reinterpret_cast<char*>(&fc1_scale), sizeof(fc1_scale));
        f.read(reinterpret_cast<char*>(&fc2_scale), sizeof(fc2_scale));
        f.read(reinterpret_cast<char*>(&output_scale), sizeof(output_scale));
        if (!f || std::memcmp(magic, "XQNNUE1", 7) != 0
            || (version != 1 && version != 2 && version != 3)
            || features != FEATURES || w == 0 || w > MAX_WIDTH
            || h > 32 || (version == 3 && h != 0)
            || embedding_scale <= 0 || output_scale <= 0) {
            error = "invalid or incompatible NNUE header: " + path;
            return false;
        }
        width = static_cast<int>(w);
        hidden = static_cast<int>(h);
        residual = (flags & 1u) != 0;
        screlu = (flags & 2u) != 0;
        phase_heads = (flags & 4u) != 0;
        fixed_point = version >= 3;
        const size_t output_heads = phase_heads ? 2u : 1u;
        if (!read_array(f, feature_bias, width)
            || !read_array(f, embedding, static_cast<size_t>(FEATURES) * width)
            || !read_array(f, fc1_bias, hidden)
            || !read_array(f, fc1_weight, static_cast<size_t>(hidden) * width * 2)
            || !read_array(f, fc2_bias, hidden)
            || !read_array(f, fc2_weight, static_cast<size_t>(hidden) * hidden)
            || !read_array(f, output_bias, output_heads)
            || !read_array(f, output_weight,
                           output_heads * (hidden > 0 ? static_cast<size_t>(hidden)
                                                     : static_cast<size_t>(width) * 2))) {
            error = "truncated NNUE payload: " + path;
            return false;
        }
        char extra;
        if (f.read(&extra, 1)) {
            error = "unexpected bytes after NNUE payload: " + path;
            return false;
        }
        loaded = true;
        return true;
    }

    inline int activation_from_acc(int32_t value) const {
        if (fixed_point) {
            const int limit = static_cast<int>(embedding_scale);
            int activation = std::max(0, std::min(limit, static_cast<int>(value)));
            if (screlu)
                activation = limit == 4096
                    ? static_cast<int>((static_cast<int64_t>(activation) * activation + 2048) >> 12)
                    : static_cast<int>((static_cast<int64_t>(activation) * activation
                                      + limit / 2) / limit);
            return activation;
        }
        if (value <= 0) return 0;
        if (value >= embedding_scale) return 127;
        return std::max(0, std::min(127,
            static_cast<int>(std::lround(value * 127.0 / embedding_scale))));
    }

    inline int dense_activation(int64_t value, float scale) const {
        return std::max(0, std::min(127,
            static_cast<int>(std::lround(value / scale))));
    }

    int evaluate(const int32_t* stm_acc, const int32_t* opp_acc, int phase = 0) const {
        int input[2 * MAX_WIDTH];
        if (fixed_point && (width == 8 || width == 16)) {
            const int limit = static_cast<int>(embedding_scale);
#if defined(__GNUC__)
#pragma GCC unroll 16
#endif
            for (int i = 0; i < width; ++i) {
                input[i] = std::max(0, std::min(limit, static_cast<int>(stm_acc[i])));
                input[width + i] = std::max(0, std::min(limit, static_cast<int>(opp_acc[i])));
                if (screlu) {
                    if (limit == 4096) {
                        input[i] = static_cast<int>((
                            static_cast<int64_t>(input[i]) * input[i] + 2048) >> 12);
                        input[width + i] = static_cast<int>((
                            static_cast<int64_t>(input[width + i]) * input[width + i]
                            + 2048) >> 12);
                    } else {
                        input[i] = static_cast<int>((static_cast<int64_t>(input[i]) * input[i]
                                                   + limit / 2) / limit);
                        input[width + i] = static_cast<int>((
                            static_cast<int64_t>(input[width + i]) * input[width + i]
                            + limit / 2) / limit);
                    }
                }
            }
        } else {
            for (int i = 0; i < width; ++i) {
                input[i] = activation_from_acc(stm_acc[i]);
                input[width + i] = activation_from_acc(opp_acc[i]);
            }
        }

        const int head = phase_heads ? std::max(0, std::min(1, phase)) : 0;
        const int output_inputs = hidden > 0 ? hidden : width * 2;
        const int16_t* selected_output = output_weight.data()
                                       + static_cast<size_t>(head) * output_inputs;
        int64_t sum = output_bias[head];
        if (hidden == 0) {
#if defined(__GNUC__)
#pragma GCC unroll 32
#endif
            for (int i = 0; i < width * 2; ++i)
                sum += static_cast<int64_t>(input[i]) * selected_output[i];
        } else {
            int layer1[32];
            int layer2[32];
            for (int o = 0; o < hidden; ++o) {
                int64_t v = fc1_bias[o];
                const int16_t* weights = &fc1_weight[static_cast<size_t>(o) * width * 2];
                for (int i = 0; i < width * 2; ++i)
                    v += static_cast<int64_t>(input[i]) * weights[i];
                layer1[o] = dense_activation(v, fc1_scale);
            }
            for (int o = 0; o < hidden; ++o) {
                int64_t v = fc2_bias[o];
                const int16_t* weights = &fc2_weight[static_cast<size_t>(o) * hidden];
                for (int i = 0; i < hidden; ++i)
                    v += static_cast<int64_t>(layer1[i]) * weights[i];
                layer2[o] = dense_activation(v, fc2_scale);
            }
            for (int i = 0; i < hidden; ++i)
                sum += static_cast<int64_t>(layer2[i]) * selected_output[i];
        }
        int score;
        if (fixed_point) {
            const int64_t denominator = static_cast<int64_t>(embedding_scale)
                                      * static_cast<int64_t>(output_scale);
            score = static_cast<int>(sum >= 0
                  ? (sum + denominator / 2) / denominator
                  : -((-sum + denominator / 2) / denominator));
        } else {
            double logit = sum / (127.0 * output_scale);
            score = static_cast<int>(std::lround(logit * k));
        }
        const int limit = residual ? 300 : MATE_BOUND - 1;
        return std::max(-limit, std::min(limit, score));
    }
};

NNUEModel NNUE;
double NNUE_BLEND = 1.0;
// Benchmark-only switch: execute the NNUE output head but return the PST score,
// keeping the searched tree identical to the PST/blend=0 controls.
#ifdef ENABLE_BENCHMARK_MODES
bool NNUE_BENCH_EVAL_DISCARD = false;
bool NNUE_BENCH_SKIP_KING_REBUILD = false;
bool NNUE_BENCH_SKIP_ALL_MAINTENANCE = false;
volatile int NNUE_BENCH_SINK = 0;
#else
constexpr bool NNUE_BENCH_EVAL_DISCARD = false;
constexpr bool NNUE_BENCH_SKIP_KING_REBUILD = false;
constexpr bool NNUE_BENCH_SKIP_ALL_MAINTENANCE = false;
#endif

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
    alignas(64) int32_t nnue_acc[2][NNUEModel::MAX_WIDTH];
    bool nnue_valid[2];

    static const int PATH_CAP = 2048;
    uint64_t path_hashes[PATH_CAP];
    Move     path_moves[PATH_CAP];
    bool     path_gave_check[PATH_CAP];
    int      path_len;

    // 增量棋子列表：side 0=红，1=黑；方格编码 sq = r*9 + c。
    int piece_sq[2][16];
    int npieces[2];
    int piece_idx[10][9];          // -1 表示空格
    // 吃子撤销栈
    int undo_cap_idx[PATH_CAP];
    int undo_top;

    // 行/列占位（用于 RankMask）
    uint16_t row_occ[10];           // bit c = 该行第 c 列有子
    uint16_t col_occ[9];            // bit r = 该列第 r 行有子
    uint16_t side_row_occ[2][10];   // 按阵营记录行占位
    uint16_t side_col_occ[2][9];

    std::vector<TTEntry> tt;
    int tt_age;

    int  history_table[10][9][10][9];
    Move killer_moves[64][2];
    Move counter_move[10][9][10][9];

    long long nodes;
    int last_completed_depth = 0;
    bool last_search_timed_out = false;

    double t_is_in_check = 0, t_attackers_to = 0, t_see = 0, t_qs_sort = 0,
           t_make_move = 0, t_undo_move = 0, t_quiescence = 0,
           t_repetition_verdict = 0, t_movegen = 0,
           t_nnue_eval = 0, t_nnue_add_normal = 0,
           t_nnue_add_rebuild = 0, t_nnue_rebuild = 0;
    long long n_is_in_check = 0, n_attackers_to = 0, n_see = 0, n_qs_sort = 0,
              n_make_move = 0, n_undo_move = 0, n_quiescence = 0,
              n_movegen = 0, n_nnue_eval = 0,
              n_nnue_add_normal = 0, n_nnue_add_rebuild = 0,
              n_nnue_rebuild = 0, n_nnue_rebuild_pieces = 0,
              n_nnue_king_make = 0, n_nnue_king_undo = 0;
    long long n_repetition_verdict = 0, n_repetition_scan_steps = 0;
    long long n_first_pass_attempts = 0, n_second_pass_attempts = 0,
              n_second_pass_repeat_attempts = 0,
              n_second_pass_recursive_researches = 0;
#ifdef ENABLE_PROFILING
    bool prof_nnue_rebuilding = false;
#endif

    void reset_prof() {
        t_is_in_check = t_attackers_to = t_see = t_qs_sort = t_make_move =
        t_undo_move = t_quiescence = t_repetition_verdict = t_movegen = 0;
        t_nnue_eval = t_nnue_add_normal = t_nnue_add_rebuild = t_nnue_rebuild = 0;
        n_is_in_check = n_attackers_to = n_see = n_qs_sort = n_make_move =
        n_undo_move = n_quiescence = n_movegen = n_nnue_eval = 0;
        n_nnue_add_normal = n_nnue_add_rebuild = n_nnue_rebuild = 0;
        n_nnue_rebuild_pieces = n_nnue_king_make = n_nnue_king_undo = 0;
        n_repetition_verdict = n_repetition_scan_steps = 0;
        n_first_pass_attempts = n_second_pass_attempts = 0;
        n_second_pass_repeat_attempts = n_second_pass_recursive_researches = 0;
    }

    void print_prof(double total_ms) {
        std::ostringstream os;
        os << std::fixed << std::setprecision(2);
        auto line = [&](const char* name, double ms, long long calls) {
            os << "[prof] " << name << ": " << ms << " ms, " << calls << " calls";
            if (calls) os << ", avg " << (ms * 1000.0 / calls) << " us";
            os << "\n";
        };
        line("make_move", t_make_move, n_make_move);
        line("undo_move", t_undo_move, n_undo_move);
        line("is_in_check", t_is_in_check, n_is_in_check);
        line("attackers_to", t_attackers_to, n_attackers_to);
        line("see", t_see, n_see);
        line("qs std::sort", t_qs_sort, n_qs_sort);
        line("quiescence", t_quiescence, n_quiescence);
        line("repetition_verdict", t_repetition_verdict, n_repetition_verdict);
        line("movegen", t_movegen, n_movegen);
        line("nnue output", t_nnue_eval, n_nnue_eval);
        line("nnue feature add normal", t_nnue_add_normal, n_nnue_add_normal);
        line("nnue feature add rebuild", t_nnue_add_rebuild, n_nnue_add_rebuild);
        line("nnue rebuild view", t_nnue_rebuild, n_nnue_rebuild);
        os << "[prof] nnue king moves: make " << n_nnue_king_make
           << ", undo " << n_nnue_king_undo
           << ", rebuild pieces " << n_nnue_rebuild_pieces << "\n";
        os << "[prof] repetition: verdict " << n_repetition_verdict
           << " calls, " << n_repetition_scan_steps << " hash comparisons\n";
        os << "[prof] two-pass: first " << n_first_pass_attempts
           << " attempts, second " << n_second_pass_attempts
           << " attempts, repeated attempts " << n_second_pass_repeat_attempts
           << ", repeated recursive searches " << n_second_pass_recursive_researches
           << "\n";
        double accounted = t_make_move + t_undo_move + t_is_in_check +
                           t_attackers_to + t_see + t_qs_sort + t_quiescence +
                           t_repetition_verdict;
        os << "[prof] search total: " << total_ms << " ms, nodes " << nodes << "\n";
        os << "[prof] sampled timers total: " << accounted << " ms = "
           << (total_ms > 0 ? accounted / total_ms * 100.0 : 0.0)
           << "% (nested timers overlap)\n";
        std::string s = os.str();
        logfile << s << std::flush;
        std::cerr << s;
    }

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

    static inline int nnue_piece_type(char p) {
        switch (to_lower_ascii(p)) {
            case 'p': return 0;
            case 'c': return 1;
            case 'n': return 2;
            case 'b': return 3;
            case 'a': return 4;
            case 'r': return 5;
            case 'k': return 6;
            default: return -1;
        }
    }

    inline int nnue_orient_square(int view, int r, int c) const {
        if (view == 1) { r = 9 - r; c = 8 - c; }
        return r * 9 + c;
    }

    int nnue_feature(int view, char piece, int r, int c) const {
        if (!NNUE.loaded || piece == '.') return -1;
        int kr = king_pos[view].first;
        int kc = king_pos[view].second;
        if (!in_board(kr, kc)) return -1;
        int oriented_king = nnue_orient_square(view, kr, kc);
        int okr = oriented_king / 9;
        int okc = oriented_king % 9;
        if (okr < 7 || okr > 9 || okc < 3 || okc > 5) return -1;
        int bucket = (okr - 7) * 3 + (okc - 3);
        int type = nnue_piece_type(piece);
        if (type < 0) return -1;
        int side = is_red(piece) ? 0 : 1;
        int relative_side = side == view ? 0 : 1;
        int piece_class = type * 2 + relative_side;
        int square = nnue_orient_square(view, r, c);
        return (bucket * 14 + piece_class) * 90 + square;
    }

    inline void nnue_add_feature(int view, int feature, int sign) {
#ifdef ENABLE_PROFILING
        ScopedProf _pnnue_add(
            prof_nnue_rebuilding ? &t_nnue_add_rebuild : &t_nnue_add_normal,
            prof_nnue_rebuilding ? &n_nnue_add_rebuild : &n_nnue_add_normal);
#endif
        if (!nnue_valid[view] || feature < 0 || feature >= NNUEModel::FEATURES) return;
        const int16_t* weights = &NNUE.embedding[static_cast<size_t>(feature) * NNUE.width];
#if defined(__AVX2__)
        if (NNUE.width == 8) {
            __m256i w = _mm256_cvtepi16_epi32(
                _mm_loadu_si128(reinterpret_cast<const __m128i*>(weights)));
            __m256i a = _mm256_load_si256(
                reinterpret_cast<const __m256i*>(nnue_acc[view]));
            a = sign > 0 ? _mm256_add_epi32(a, w) : _mm256_sub_epi32(a, w);
            _mm256_store_si256(reinterpret_cast<__m256i*>(nnue_acc[view]), a);
            return;
        }
#endif
        if (NNUE.width == 16) {
#if defined(__AVX2__)
            __m256i w0 = _mm256_cvtepi16_epi32(
                _mm_loadu_si128(reinterpret_cast<const __m128i*>(weights)));
            __m256i w1 = _mm256_cvtepi16_epi32(
                _mm_loadu_si128(reinterpret_cast<const __m128i*>(weights + 8)));
            __m256i a0 = _mm256_load_si256(
                reinterpret_cast<const __m256i*>(nnue_acc[view]));
            __m256i a1 = _mm256_load_si256(
                reinterpret_cast<const __m256i*>(nnue_acc[view] + 8));
            a0 = sign > 0 ? _mm256_add_epi32(a0, w0) : _mm256_sub_epi32(a0, w0);
            a1 = sign > 0 ? _mm256_add_epi32(a1, w1) : _mm256_sub_epi32(a1, w1);
            _mm256_store_si256(reinterpret_cast<__m256i*>(nnue_acc[view]), a0);
            _mm256_store_si256(reinterpret_cast<__m256i*>(nnue_acc[view] + 8), a1);
#else
#if defined(__GNUC__)
#pragma GCC unroll 16
#endif
            for (int i = 0; i < 16; ++i)
                nnue_acc[view][i] += sign * static_cast<int32_t>(weights[i]);
#endif
            return;
        }
        for (int i = 0; i < NNUE.width; ++i)
            nnue_acc[view][i] += sign * static_cast<int32_t>(weights[i]);
    }

    void rebuild_nnue_view(int view) {
#ifdef ENABLE_PROFILING
        ++n_nnue_rebuild;
        PROFILE_ALWAYS(_pnnue_rebuild, &t_nnue_rebuild);
        const bool previous_rebuild_state = prof_nnue_rebuilding;
        prof_nnue_rebuilding = true;
#endif
        nnue_valid[view] = false;
        if (!NNUE.loaded || !in_board(king_pos[view].first, king_pos[view].second)) {
#ifdef ENABLE_PROFILING
            prof_nnue_rebuilding = previous_rebuild_state;
#endif
            return;
        }
        for (int i = 0; i < NNUE.width; ++i) nnue_acc[view][i] = NNUE.feature_bias[i];
        nnue_valid[view] = true;
        for (int r = 0; r < 10; ++r) {
            for (int c = 0; c < 9; ++c) {
                char p = board[r][c];
                if (p == '.') continue;
#ifdef ENABLE_PROFILING
                ++n_nnue_rebuild_pieces;
#endif
                int feature = nnue_feature(view, p, r, c);
                if (feature < 0) {
                    nnue_valid[view] = false;
#ifdef ENABLE_PROFILING
                    prof_nnue_rebuilding = previous_rebuild_state;
#endif
                    return;
                }
                nnue_add_feature(view, feature, +1);
            }
        }
#ifdef ENABLE_PROFILING
        prof_nnue_rebuilding = previous_rebuild_state;
#endif
    }

    void rebuild_nnue() {
        if (!NNUE.loaded) { nnue_valid[0] = nnue_valid[1] = false; return; }
        rebuild_nnue_view(0);
        rebuild_nnue_view(1);
    }

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
        rebuild_nnue();
    }

    char make_move(const Move& m) {
        PROFILE_SCOPE(_p, &t_make_move, &n_make_move);
        char moving_piece = board[m.r1][m.c1];
        char captured_piece = board[m.r2][m.c2];
#ifdef ENABLE_PROFILING
        if (moving_piece == 'K' || moving_piece == 'k') ++n_nnue_king_make;
#endif

        bool nnue_refresh[2] = {false, false};
        bool nnue_invalidate[2] = {false, false};
        if (NNUE.loaded && !NNUE_BENCH_SKIP_ALL_MAINTENANCE) {
            for (int view = 0; view < 2; ++view) {
                char own_general = view == 0 ? 'K' : 'k';
                nnue_refresh[view] = moving_piece == own_general;
                nnue_invalidate[view] = captured_piece == own_general;
                if (nnue_refresh[view] || nnue_invalidate[view] || !nnue_valid[view]) continue;
                nnue_add_feature(view, nnue_feature(view, moving_piece, m.r1, m.c1), -1);
                nnue_add_feature(view, nnue_feature(view, moving_piece, m.r2, m.c2), +1);
                if (captured_piece != '.')
                    nnue_add_feature(view, nnue_feature(view, captured_piece, m.r2, m.c2), -1);
            }
        }

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

        // 增量维护棋子列表。
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
            // 清除对方在目标格的阵营占位；总占位不变，因为走子方会占据该格。
            side_row_occ[opp][m.r2] &= (uint16_t)~(1 << m.c2);
            side_col_occ[opp][m.c2] &= (uint16_t)~(1 << m.r2);
        } else {
            // 非吃子：目标格原本为空，需要设置总占位。
            row_occ[m.r2] |= (uint16_t)(1 << m.c2);
            col_occ[m.c2] |= (uint16_t)(1 << m.r2);
        }
        int idx_m = piece_idx[m.r1][m.c1];
        piece_sq[mover_side][idx_m] = m.r2 * 9 + m.c2;
        piece_idx[m.r1][m.c1] = -1;
        piece_idx[m.r2][m.c2] = idx_m;
        // 清除源格占位，并更新走子方的阵营占位。
        row_occ[m.r1] &= (uint16_t)~(1 << m.c1);
        col_occ[m.c1] &= (uint16_t)~(1 << m.r1);
        side_row_occ[mover_side][m.r1] &= (uint16_t)~(1 << m.c1);
        side_col_occ[mover_side][m.c1] &= (uint16_t)~(1 << m.r1);
        side_row_occ[mover_side][m.r2] |= (uint16_t)(1 << m.c2);
        side_col_occ[mover_side][m.c2] |= (uint16_t)(1 << m.r2);

        board[m.r2][m.c2] = moving_piece;
        board[m.r1][m.c1] = '.';
        turn ^= 1;

        if (NNUE.loaded && !NNUE_BENCH_SKIP_ALL_MAINTENANCE) {
            for (int view = 0; view < 2; ++view) {
                if (nnue_invalidate[view]) nnue_valid[view] = false;
                else if (nnue_refresh[view] && !NNUE_BENCH_SKIP_KING_REBUILD)
                    rebuild_nnue_view(view);
            }
        }

        if (path_len < PATH_CAP) {
            path_hashes[path_len] = current_hash;
            path_moves[path_len]  = m;
            // turn 已切换为对方；若对方此时被将，则刚才的着法造成了将军。
            path_gave_check[path_len] = is_in_check(turn == 0);
            path_len++;
        }
        return captured_piece;
    }

    void undo_move(const Move& m, char captured) {
        PROFILE_SCOPE(_p, &t_undo_move, &n_undo_move);
        if (path_len > 0) path_len--;
        char moved_piece = board[m.r2][m.c2];
#ifdef ENABLE_PROFILING
        if (moved_piece == 'K' || moved_piece == 'k') ++n_nnue_king_undo;
#endif

        bool nnue_rebuild[2] = {false, false};
        if (NNUE.loaded && !NNUE_BENCH_SKIP_ALL_MAINTENANCE) {
            for (int view = 0; view < 2; ++view) {
                char own_general = view == 0 ? 'K' : 'k';
                nnue_rebuild[view] = moved_piece == own_general || captured == own_general;
                if (nnue_rebuild[view] || !nnue_valid[view]) continue;
                nnue_add_feature(view, nnue_feature(view, moved_piece, m.r2, m.c2), -1);
                nnue_add_feature(view, nnue_feature(view, moved_piece, m.r1, m.c1), +1);
                if (captured != '.')
                    nnue_add_feature(view, nnue_feature(view, captured, m.r2, m.c2), +1);
            }
        }

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

        // 撤销棋子列表的增量更新。
        int mover_side = is_red(moved_piece) ? 0 : 1;
        int idx_m = piece_idx[m.r2][m.c2];
        piece_sq[mover_side][idx_m] = m.r1 * 9 + m.c1;
        piece_idx[m.r2][m.c2] = -1;
        piece_idx[m.r1][m.c1] = idx_m;
        // 撤销行列占位更新。
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
            // 恢复对方阵营占位；总占位始终为 set，无需修改。
            side_row_occ[opp][m.r2] |= (uint16_t)(1 << m.c2);
            side_col_occ[opp][m.c2] |= (uint16_t)(1 << m.r2);
            // 吃子时用 swap-pop 填补了 cap_idx；撤销时先把该棋子搬回数组末尾。
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
        if (NNUE.loaded && !NNUE_BENCH_SKIP_ALL_MAINTENANCE) {
            for (int view = 0; view < 2; ++view)
                if (nnue_rebuild[view] && !NNUE_BENCH_SKIP_KING_REBUILD)
                    rebuild_nnue_view(view);
        }
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

    // 天天象棋（亚洲规则）长将判负的简化实现：
    //   返回 0：无循环，或循环应判和；
    //   返回 +1：对手在循环中步步将军，对手判负，当前待走方胜；
    //   返回 -1：当前待走方在循环中步步将军，当前待走方判负。
    // 暂不处理长捉、长杀、根节点分析等扩展规则。
    int repetition_verdict(bool& repeated) {
        PROFILE_SCOPE(_p, &t_repetition_verdict, &n_repetition_verdict);
        repeated = false;
        int found = -1;
        for (int i = path_len - 3; i >= 0; i -= 2) {
#ifdef ENABLE_PROFILING
            n_repetition_scan_steps++;
#endif
            if (path_hashes[i] == current_hash) { found = i; break; }
        }
        if (found < 0) return 0;
        repeated = true;
        // 循环内的着法：path_moves[found+1 .. path_len-1]。
        // 最后一着的走子方为 turn ^ 1，因为 turn 表示当前待走方。
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
        if (perp0 == perp1) return 0; // 双方都长将或都不长将，判和。
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

    // 将走法写入 out 并返回数量；调用方需保证 out 至少可容纳 128 项。
    int gen_all_moves(bool is_red_turn, bool only_captures, Move* out) {
        PROFILE_SCOPE(_pmovegen, &t_movegen, &n_movegen);
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

    int evaluate() {
        if (NNUE.loaded && nnue_valid[0] && nnue_valid[1]) {
            if (NNUE_BLEND == 0.0 && !NNUE_BENCH_EVAL_DISCARD) return current_score;
            PROFILE_SCOPE(_pnnue_eval, &t_nnue_eval, &n_nnue_eval);
            int phase = (npieces[0] + npieces[1] <= 20) ? 1 : 0;
            int stm_score = NNUE.evaluate(nnue_acc[turn], nnue_acc[turn ^ 1], phase);
            if (NNUE_BENCH_EVAL_DISCARD) {
#ifdef ENABLE_BENCHMARK_MODES
                NNUE_BENCH_SINK = stm_score;
#endif
                return current_score;
            }
            int red_value = turn == 0 ? stm_score : -stm_score;
            if (NNUE.residual && NNUE_BLEND == 1.0)
                return std::max(-MATE_BOUND + 1,
                       std::min(MATE_BOUND - 1, current_score + red_value));
            int value = NNUE.residual
                      ? current_score + static_cast<int>(std::lround(NNUE_BLEND * red_value))
                      : static_cast<int>(std::lround(
                            current_score + NNUE_BLEND * (red_value - current_score)));
            return std::max(-MATE_BOUND + 1, std::min(MATE_BOUND - 1, value));
        }
        return current_score;
    }

    bool is_in_check(bool is_red_turn) {
        PROFILE_SCOPE(_p, &t_is_in_check, &n_is_in_check);
        int kr = king_pos[is_red_turn ? 0 : 1].first;
        int kc = king_pos[is_red_turn ? 0 : 1].second;
        if (kr == -1) return true;

        // 使用 RankMask 检查车、将帅照面和炮的直线攻击。
        int enemy_side = is_red_turn ? 1 : 0;
        // 检查同行的敌车；将帅照面只可能发生在同列。
        uint16_t row_hit = (uint16_t)(ROOK_ROW_ATT[kc][row_occ[kr]] & side_row_occ[enemy_side][kr]);
        while (row_hit) {
            int nc = __builtin_ctz(row_hit); row_hit &= (uint16_t)(row_hit - 1);
            if (to_lower_ascii(board[kr][nc]) == 'r') return true;
        }
        // 检查同列的敌车或敌将。
        uint16_t col_hit = (uint16_t)(ROOK_COL_ATT[kr][col_occ[kc]] & side_col_occ[enemy_side][kc]);
        while (col_hit) {
            int nr = __builtin_ctz(col_hit); col_hit &= (uint16_t)(col_hit - 1);
            char lp = to_lower_ascii(board[nr][kc]);
            if (lp == 'r' || lp == 'k') return true;
        }
        // 检查同行、同列的敌炮：从将位反向查炮，命中的就是攻击该位置的炮。
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

    // make_move() records whether the new side to move is in check.
    // Reuse that result only when it is provably for the requested side/state.
    inline bool cached_is_in_check(bool is_red_side) {
        if (is_red_side == (turn == 0) && path_len > 0 &&
            path_hashes[path_len - 1] == current_hash &&
            path_moves[path_len - 1].is_valid()) {
            return path_gave_check[path_len - 1];
        }
        return is_in_check(is_red_side);
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
    // 将攻击者写入 out 并返回数量；调用方需保证 out 至少可容纳 17 项。
    int attackers_to(int tr, int tc, bool by_red, Attacker* out,
                     uint16_t see_row_occ, uint16_t see_col_occ) {
        PROFILE_SCOPE(_p, &t_attackers_to, &n_attackers_to);
        int n = 0;
        auto add_ray = [&](uint16_t ray, bool row, bool positive) {
            if (!ray) return;
            int first = positive ? __builtin_ctz((unsigned)ray)
                                 : 31 - __builtin_clz((unsigned)ray);
            ray &= (uint16_t)~(1u << first);
            int fr = row ? tr : first, fc = row ? first : tc;
            char p = board[fr][fc];
            if (is_red(p) == by_red) {
                char lp = to_lower_ascii(p);
                if (lp == 'r') out[n++] = {fr, fc, p};
                else if (lp == 'k' && std::abs(fr - tr) + std::abs(fc - tc) == 1)
                    out[n++] = {fr, fc, p};
            }
            if (!ray) return;
            int second = positive ? __builtin_ctz((unsigned)ray)
                                  : 31 - __builtin_clz((unsigned)ray);
            int sr = row ? tr : second, sc = row ? second : tc;
            p = board[sr][sc];
            if (is_red(p) == by_red && to_lower_ascii(p) == 'c')
                out[n++] = {sr, sc, p};
        };
        add_ray((uint16_t)(see_row_occ & ~((1u << (tc + 1)) - 1)), true, true);
        add_ray((uint16_t)(see_row_occ & ((1u << tc) - 1)), true, false);
        add_ray((uint16_t)(see_col_occ & ~((1u << (tr + 1)) - 1)), false, true);
        add_ray((uint16_t)(see_col_occ & ((1u << tr) - 1)), false, false);
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
        PROFILE_SCOPE(_p, &t_see, &n_see);
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
        uint16_t see_row_occ = row_occ[tr];
        uint16_t see_col_occ = col_occ[tc];
        if (sr == tr) see_row_occ &= (uint16_t)~(1u << sc);
        if (sc == tc) see_col_occ &= (uint16_t)~(1u << sr);
        int on_sq = see_value(attacker);
        bool side = !attacker_is_red;

        Attacker atk_buf[20];
        while (true) {
            int an = attackers_to(tr, tc, side, atk_buf, see_row_occ, see_col_occ);
			/* SEE 历史问题的复现局面（走子前）：
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

走子后：
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

			用于检查连续交换过程中攻击者集合和占位掩码是否正确更新。
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
                if (ar == tr) see_row_occ &= (uint16_t)~(1u << ac);
                if (ac == tc) see_col_occ &= (uint16_t)~(1u << ar);
                Attacker chk[20];
                int cn = attackers_to(tr, tc, !side, chk, see_row_occ, see_col_occ);
                if (cn > 0) {
                    Rem t = removed[--rn];
                    board[t.r][t.c] = t.p;
                    if (ar == tr) see_row_occ |= (uint16_t)(1u << ac);
                    if (ac == tc) see_col_occ |= (uint16_t)(1u << ar);
                    break;
                }
                gain[gn] = on_sq - gain[gn-1]; gn++;
                on_sq = see_value(ap);
                side = !side;
                break;
            }
            removed[rn++] = {ar, ac, board[ar][ac]};
            board[ar][ac] = '.';
            if (ar == tr) see_row_occ &= (uint16_t)~(1u << ac);
            if (ac == tc) see_col_occ &= (uint16_t)~(1u << ar);
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
        PROFILE_SCOPE(_pq, &t_quiescence, &n_quiescence);
        bool in_check = cached_is_in_check(maximizing_player);

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
            if (qs_depth > 3) {
                bool repeated = false;
                int rv = repetition_verdict(repeated);
                if (rv != 0) {
                    int winner = (rv > 0) ? turn : (turn ^ 1);
                    return (winner == 0) ? (SCORE_INF - qs_depth)
                                         : (-SCORE_INF + qs_depth);
                }
                if (repeated) return 0;

                int evasions = gen_all_moves(maximizing_player, false, moves);
                for (int i = 0; i < evasions; ++i) {
                    char captured = make_move(moves[i]);
                    bool legal = !is_in_check(maximizing_player);
                    undo_move(moves[i], captured);
                    if (legal) return evaluate();
                }
                return maximizing_player ? -SCORE_INF + qs_depth
                                         :  SCORE_INF - qs_depth;
            }
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

        { PROFILE_SCOPE(_ps, &t_qs_sort, &n_qs_sort);
          std::sort(moves, moves + nm, [&](const Move& a, const Move& b) {
              int val_a = PIECE_VALUES[(unsigned char)board[a.r2][a.c2]];
              int val_b = PIECE_VALUES[(unsigned char)board[b.r2][b.c2]];
              return val_a > val_b;
          });
        }

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
            bool repeated = false;
            int rv = repetition_verdict(repeated);
            if (rv != 0) {
                // 当前待走方为 turn。rv=+1 表示对手（turn^1）长将判负，即 turn 方胜。
                // 分数采用绝对视角：红方为正，黑方为负。
                int winner = (rv > 0) ? turn : (turn ^ 1);
                int sc = (winner == 0) ? (SCORE_INF - ply) : (-SCORE_INF + ply);
                return {sc, NO_MOVE};
            }
            if (repeated) return {0, NO_MOVE};
        }

        if (stop_search) return {0, NO_MOVE};
        if ((nodes & 2047) == 0) {
            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(now - start_tp).count();
            if (elapsed > time_limit) stop_search = true;
        }
        bool in_check = cached_is_in_check(maximizing_player);
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
        // 同步对 moves[] 和 mscore[] 按分数降序排序；nm 通常小于 50，使用插入排序。
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
#ifdef ENABLE_PROFILING
        bool attempted_first_pass[128] = {};
        bool searched_first_pass[128] = {};
#endif
        for (int pass = 0; pass < 2; ++pass) {
            bool allow_pruning = (pass == 0);

            // 即使第一步合法，也不能仅凭一个接近杀棋的异常分数跳过第二遍搜索。

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
#ifdef ENABLE_PROFILING
            if (pass == 0) {
                n_first_pass_attempts++;
                attempted_first_pass[mi] = true;
            } else {
                n_second_pass_attempts++;
                if (attempted_first_pass[mi]) n_second_pass_repeat_attempts++;
            }
#endif
            if (is_in_check(maximizing_player)) {
                undo_move(m, cap);
                continue;
            }
            legal_count++;

#ifdef ENABLE_PROFILING
            if (pass == 0) {
                searched_first_pass[mi] = true;
            } else if (searched_first_pass[mi]) {
                n_second_pass_recursive_researches++;
            }
#endif

            bool gives_check = cached_is_in_check(!maximizing_player);
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
            // 不能只因为已经找到合法着法就结束第二遍；还需确保没有遗漏被剪枝的候选。
//            if (!allow_pruning && legal_count) break;
        }
        }
        // 所有伪合法着法都会导致己方被将：判负。象棋中的困毙也按负处理。
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

        SearchResult last_res = {evaluate(), NO_MOVE};
        last_completed_depth = 0;
        last_search_timed_out = false;
        // A hard time cutoff before depth one used to surface as "resign".
        // Prepare a legal root fallback so timeout and true terminal states
        // remain distinct without extending the clock budget.
        Move fallback_moves[128];
        int fallback_count = gen_all_moves(is_ai_red, false, fallback_moves);
        for (int i = 0; i < fallback_count; ++i) {
            Move candidate = fallback_moves[i];
            if (candidate == forbidden_move) continue;
            char captured = make_move(candidate);
            bool legal = !is_in_check(is_ai_red);
            undo_move(candidate, captured);
            if (legal) { last_res.move = candidate; break; }
        }
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

            if (stop_search) { last_search_timed_out = true; break; }
            last_res = res;
            last_completed_depth = depth;
            prev_score = res.score;

            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(now - start_tp).count();
            // 发现全有pass1的。
#ifdef XQ_SEARCH_LOG
           logfile << "info depth " << depth
                   << " score " << res.score
                   << " time " << (int)(elapsed * 1000)
                   << " nodes " << nodes
                   << std::endl;
#endif
            // printf("%d %d\n",debug[0],debug[1]);

            if (std::abs(res.score) > MATE_BOUND) break;
            // Keep iterating while there is meaningful time left. The recursive
            // search still enforces the full hard limit and, if interrupted,
            // search_main returns the last fully completed iteration.
            if (elapsed > max_time * 0.16 && depth >= 4) break;
        }
        return last_res;
    }
};

#ifndef XQ_NO_MAIN
int main(int argc, char** argv) {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    init_piece_values();
    init_pst_raw();
    init_zobrist();
    init_lmr();
    init_attack_tables();

    std::string nnue_path;
    std::string debug_path;
    if (const char* env_path = std::getenv("XQ_NNUE_FILE")) nnue_path = env_path;
    if (const char* blend = std::getenv("XQ_NNUE_BLEND"))
        NNUE_BLEND = std::max(0.0, std::min(2.0, std::atof(blend)));
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--nnue" && i + 1 < argc) nnue_path = argv[++i];
        else if (arg == "--nnue-blend" && i + 1 < argc)
            NNUE_BLEND = std::max(0.0, std::min(2.0, std::atof(argv[++i])));
#ifdef ENABLE_BENCHMARK_MODES
        else if (arg == "--benchmark-eval-discard") NNUE_BENCH_EVAL_DISCARD = true;
        else if (arg == "--benchmark-skip-king-rebuild") NNUE_BENCH_SKIP_KING_REBUILD = true;
#endif
        else debug_path = arg;
    }
    if (!nnue_path.empty()) {
        if (!NNUE.load(nnue_path)) {
            std::cerr << "NNUE load failed: " << NNUE.error << std::endl;
            return 2;
        }
        std::cerr << "NNUE loaded: " << nnue_path << " width=" << NNUE.width
                  << " hidden=" << NNUE.hidden << " K=" << NNUE.k
                  << " residual=" << NNUE.residual
                  << " fixed=" << NNUE.fixed_point
                  << " screlu=" << NNUE.screlu
                  << " phase_heads=" << NNUE.phase_heads
                  << " blend=" << NNUE_BLEND << std::endl;
    }

    XiangqiEngine engine;
    std::string line;
    int cnt = 0;
    double search_time_override = 0.0;
    int fixed_depth_override = 0;

    // 调试用: 加一个文件参数则从文件读命令, 方便 IDE 单步调试
    // 例: xiangqi_ai_debug.exe engine_cmds_20260812_225910.log
    std::ifstream debug_in;
    std::istream* in = &std::cin;
    if (!debug_path.empty()) {
        debug_in.open(debug_path);
        if (!debug_in) { std::cerr << "cannot open " << debug_path << std::endl; return 1; }
        in = &debug_in;
    }

    while (std::getline(*in, line)) {
        if (line == "quit") break;
        if (line == "ready") std::cout << "readyok" << std::endl;

#ifdef ENABLE_BENCHMARK_MODES
        if (line.substr(0, 14) == "benchmark_mode") {
            std::stringstream ss(line);
            std::string command, mode;
            ss >> command >> mode;
            NNUE_BENCH_SKIP_ALL_MAINTENANCE = mode == "pst";
            NNUE_BENCH_SKIP_KING_REBUILD = mode == "incremental";
            NNUE_BENCH_EVAL_DISCARD = mode == "eval";
            NNUE_BLEND = mode == "full" ? 1.0 : 0.0;
        }
        else if (line.substr(0, 4) == "side") {
#else
        if (line.substr(0, 4) == "side") {
#endif
            if (line.find("red") != std::string::npos) engine.player_side = "red";
            else engine.player_side = "black";
        }
        else if (line.substr(0, 4) == "time") {
            std::stringstream ss(line);
            std::string cmd;
            double seconds;
            if (ss >> cmd >> seconds && seconds > 0.0)
                search_time_override = seconds;
        }
        else if (line.substr(0, 5) == "depth") {
            std::stringstream ss(line);
            std::string cmd;
            int depth;
            if (ss >> cmd >> depth) fixed_depth_override = std::max(0, depth);
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
#ifdef ENABLE_PROFILING
            engine.reset_prof();
            auto prof_t0 = std::chrono::steady_clock::now();
#endif
            bool is_ai_red = (engine.player_side == "black");

            XiangqiEngine::SearchResult res;
            if (USE_DEPTH || fixed_depth_override > 0) {
                int depth = fixed_depth_override > 0 ? fixed_depth_override : LONG_MAX_DEPTH;
                engine.start_tp = std::chrono::steady_clock::now();
                engine.time_limit = 1.0e12;
                engine.stop_search = false;
                ++engine.tt_age;
                res = engine.minimax(depth, -SCORE_INF - 1, SCORE_INF + 1,
                                     is_ai_red, true, -1, true, 0);
                engine.last_completed_depth = depth;
                engine.last_search_timed_out = false;
            } else {
                double search_time = search_time_override > 0.0
                                   ? search_time_override
                                   : ((cnt <= 3) ? 15.0 : LONG_MAX_TIME);
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
                int engine_score = is_ai_red ? res.score : -res.score;
                std::cout << "move " << best.r1 << " " << best.c1 << " "
                          << best.r2 << " " << best.c2;
                if (std::abs(engine_score) > MATE_BOUND) {
                    int mate_plies = std::max(1, SCORE_INF - std::abs(engine_score));
                    int mate_moves = (mate_plies + 1) / 2;
                    std::cout << " score mate "
                              << (engine_score >= 0 ? mate_moves : -mate_moves);
                } else {
                    // PIECE_VALUES 中兵=100，直接作为 centipawn 输出。
                    std::cout << " score cp " << engine_score;
                }
                std::cout << " depth " << engine.last_completed_depth
                          << " nodes " << engine.nodes
                          << " timeout " << engine.last_search_timed_out;
                std::cout << std::endl;
            } else {
                std::cout << "resign" << std::endl;
            }
            engine.forbidden_move = NO_MOVE;
#ifdef ENABLE_PROFILING
            double prof_ms = std::chrono::duration<double, std::milli>(
                                 std::chrono::steady_clock::now() - prof_t0).count();
            engine.print_prof(prof_ms);
#endif
        }
        else if (line == "print") {
            for(int r=0; r<10; ++r) {
                for(int c=0; c<9; ++c) std::cout << engine.board[r][c] << " ";
                std::cout << std::endl;
            }
        }
        else if (line == "eval") {
            int nnue_value = engine.evaluate();
            std::cout << "eval nnue " << nnue_value
                      << " pst " << engine.current_score << std::endl;
        }
        else if (line.substr(0, 8) == "setboard") {
            // setboard <fen-rows> <side>      (side: 'w' or 'b'，默认为 'w')
            // 示例：setboard 1cbakabr1/3RR4/9/p1p1C3p/6p2/2P6/P3P1ncP/4B1r2/1C2A4/4KAB2 b
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

            // 重置搜索相关状态。
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
#endif

/*
g++ -O3 -std=c++17 -march=native -mtune=native -funroll-loops -fno-exceptions -fno-rtti -flto -DNDEBUG -static -static-libgcc -static-libstdc++ -o xiangqi_ai.exe xiangqi_ai.cpp
调试
g++ -g -O0 -std=c++17 -march=native -static -static-libgcc -static-libstdc++ -o xiangqi_ai_debug.exe xiangqi_ai.cpp

./xiangqi_ai
setboard 3ak4/4a4/2n4PC/9/4R4/9/1p2C4/4r4/1n2A4/4KA3 b
side red
search
(测试局面)
https://sachess.com/zh-cn/xiangqi-photo-to-fen/ 图片转 FEN


*/
