#define XQ_NO_MAIN
#include "teacher.cpp"

static std::string fen(const XiangqiEngine& e) {
    std::ostringstream out;
    for (int r = 0; r < 10; ++r) {
        if (r) out << '/';
        int empty = 0;
        for (int c = 0; c < 9; ++c) {
            char p = e.board[r][c];
            if (p == '.') ++empty;
            else {
                if (empty) { out << empty; empty = 0; }
                out << p;
            }
        }
        if (empty) out << empty;
    }
    out << (e.turn == 0 ? " w" : " b");
    return out.str();
}

static void reset_start(XiangqiEngine& e) {
    static const char* initial[10] = {
        "rnbakabnr", ".........", ".c.....c.", "p.p.p.p.p", ".........",
        ".........", "P.P.P.P.P", ".C.....C.", ".........", "RNBAKABNR"
    };
    for (int r = 0; r < 10; ++r)
        for (int c = 0; c < 9; ++c)
            e.board[r][c] = initial[r][c];
    e.turn = 0;
    e.init_score_and_hash();
}

int main(int argc, char** argv) {
    if (argc < 4) {
        std::cerr << "usage: make_openings COUNT SEED OUTPUT [MIN_PLIES=4] [MAX_PLIES=10]\n";
        return 2;
    }
    int count = std::max(1, std::atoi(argv[1]));
    uint64_t seed = std::strtoull(argv[2], nullptr, 10);
    std::string output = argv[3];
    int min_plies = argc > 4 ? std::max(0, std::atoi(argv[4])) : 4;
    int max_plies = argc > 5 ? std::max(min_plies, std::atoi(argv[5])) : 10;
    init_piece_values(); init_pst_raw(); init_zobrist(); init_lmr(); init_attack_tables();
    XiangqiEngine e;
    std::mt19937_64 rng(seed);
    std::ofstream out(output);
    if (!out) return 1;

    for (int opening = 0; opening < count; ++opening) {
        reset_start(e);
        int target = std::uniform_int_distribution<int>(min_plies, max_plies)(rng);
        bool valid = true;
        for (int ply = 0; ply < target; ++ply) {
            Move pseudo[128], legal[128];
            bool red = e.turn == 0;
            int n = e.gen_all_moves(red, false, pseudo), ln = 0;
            for (int i = 0; i < n; ++i) {
                // Keep opening randomization non-capturing; this produces a
                // diverse but recognizable opening distribution.
                if (e.board[pseudo[i].r2][pseudo[i].c2] != '.') continue;
                char cap = e.make_move(pseudo[i]);
                bool ok = !e.is_in_check(red);
                e.undo_move(pseudo[i], cap);
                if (ok) legal[ln++] = pseudo[i];
            }
            if (ln == 0) { valid = false; break; }
            Move m = legal[std::uniform_int_distribution<int>(0, ln - 1)(rng)];
            e.make_move(m);
        }
        if (!valid || e.is_in_check(e.turn == 0)) { --opening; continue; }
        out << fen(e) << '\n';
    }
    return 0;
}
