#define XQ_NO_MAIN
#include "nnue_engine.cpp"

#include <array>

static bool verify_acc(XiangqiEngine& e, const char* where) {
    int32_t before[2][NNUEModel::MAX_WIDTH]{};
    bool valid[2] = {e.nnue_valid[0], e.nnue_valid[1]};
    std::memcpy(before, e.nnue_acc, sizeof(before));
    int eval_before = e.evaluate();
    e.rebuild_nnue();
    if (valid[0] != e.nnue_valid[0] || valid[1] != e.nnue_valid[1]) {
        std::cerr << "validity mismatch at " << where << "\n";
        return false;
    }
    for (int view = 0; view < 2; ++view)
        for (int i = 0; i < NNUE.width; ++i)
            if (before[view][i] != e.nnue_acc[view][i]) {
                std::cerr << "acc mismatch at " << where << " view=" << view
                          << " dim=" << i << " incremental=" << before[view][i]
                          << " rebuilt=" << e.nnue_acc[view][i] << "\n";
                return false;
            }
    if (eval_before != e.evaluate()) {
        std::cerr << "eval mismatch at " << where << "\n";
        return false;
    }
    return true;
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
    e.forbidden_move = NO_MOVE;
    e.init_score_and_hash();
}

static bool verify_rotation(XiangqiEngine& source, XiangqiEngine& rotated) {
    for (int r = 0; r < 10; ++r) {
        for (int c = 0; c < 9; ++c) {
            char piece = source.board[9 - r][8 - c];
            if (piece >= 'a' && piece <= 'z') piece = static_cast<char>(piece - 'a' + 'A');
            else if (piece >= 'A' && piece <= 'Z') piece = static_cast<char>(piece - 'A' + 'a');
            rotated.board[r][c] = piece;
        }
    }
    rotated.turn = source.turn ^ 1;
    rotated.forbidden_move = NO_MOVE;
    rotated.init_score_and_hash();
    if (source.evaluate() != -rotated.evaluate()) {
        std::cerr << "rotation/color symmetry mismatch: original=" << source.evaluate()
                  << " transformed=" << rotated.evaluate() << "\n";
        return false;
    }
    return true;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: verify_nnue MODEL\n";
        return 2;
    }
    init_piece_values();
    init_pst_raw();
    init_zobrist();
    init_lmr();
    init_attack_tables();
    if (!NNUE.load(argv[1])) {
        std::cerr << NNUE.error << "\n";
        return 2;
    }
    XiangqiEngine e;
    XiangqiEngine rotated;
    std::mt19937_64 rng(0x6e6e7565ULL);
    uint64_t transitions_checked = 0;

    for (int trial = 0; trial < 200; ++trial) {
        reset_start(e);
        if (!verify_acc(e, "initial")) return 1;

        for (int ply = 0; ply < 100; ++ply) {
            Move pseudo[128], legal[128];
            bool red = e.turn == 0;
            int n = e.gen_all_moves(red, false, pseudo), ln = 0;
            for (int i = 0; i < n; ++i) {
                char cap = e.make_move(pseudo[i]);
                ++transitions_checked;
                bool ok = !e.is_in_check(red);
                e.undo_move(pseudo[i], cap);
                if (!verify_acc(e, "probe undo")) return 1;
                if (ok) legal[ln++] = pseudo[i];
            }
            if (ln == 0) break;

            Move m = legal[std::uniform_int_distribution<int>(0, ln - 1)(rng)];
            char board_before[10][9];
            std::memcpy(board_before, e.board, sizeof(board_before));
            int32_t acc_before[2][NNUEModel::MAX_WIDTH];
            std::memcpy(acc_before, e.nnue_acc, sizeof(acc_before));
            uint64_t hash_before = e.current_hash;
            int score_before = e.current_score;
            int turn_before = e.turn;
            int eval_before = e.evaluate();

            char cap = e.make_move(m);
            ++transitions_checked;
            if (!verify_acc(e, "after make")) return 1;
            e.undo_move(m, cap);
            if (!verify_acc(e, "after undo")) return 1;
            if (std::memcmp(board_before, e.board, sizeof(board_before)) != 0
                || std::memcmp(acc_before, e.nnue_acc, sizeof(acc_before)) != 0
                || hash_before != e.current_hash || score_before != e.current_score
                || turn_before != e.turn || eval_before != e.evaluate()) {
                std::cerr << "state did not restore at trial=" << trial << " ply=" << ply << "\n";
                return 1;
            }

            cap = e.make_move(m);
            ++transitions_checked;
            if (!verify_acc(e, "committed make")) return 1;
            if (cap == 'K' || cap == 'k') break;
        }

        int32_t before_null[2][NNUEModel::MAX_WIDTH];
        std::memcpy(before_null, e.nnue_acc, sizeof(before_null));
        int turn_before = e.turn;
        e.make_null_move();
        e.undo_null_move();
        if (turn_before != e.turn
            || std::memcmp(before_null, e.nnue_acc, sizeof(before_null)) != 0
            || !verify_acc(e, "null roundtrip")) return 1;
        if (!verify_rotation(e, rotated)) return 1;
    }
    if (transitions_checked < 100000) {
        std::cerr << "insufficient transition coverage: " << transitions_checked << "\n";
        return 1;
    }
    std::cout << "NNUE accumulator verification passed transitions="
              << transitions_checked << "\n";
    return 0;
}
