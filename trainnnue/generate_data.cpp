#define NNUE_TEACHER
#define XQ_NO_MAIN
#include "teacher.cpp"

#include <array>
#include <limits>

#pragma pack(push, 1)
struct DataHeader {
    char magic[8];
    uint32_t version;
    uint32_t record_size;
};

struct DataRecord {
    char board[90];
    int16_t score_red;
    uint32_t nodes;
    uint32_t game_id;
    uint16_t ply;
    uint8_t stm;
    uint8_t teacher_depth;
    uint8_t flags;       // bit 0: in check, bit 1: teacher best move captures
    int8_t outcome_red;  // 0 black win, 1 draw, 2 red win, -1 unknown
};
#pragma pack(pop)

static void reset_start_position(XiangqiEngine& e) {
    static const char* initial[10] = {
        "rnbakabnr", ".........", ".c.....c.", "p.p.p.p.p", ".........",
        ".........", "P.P.P.P.P", ".C.....C.", ".........", "RNBAKABNR"
    };
    for (int r = 0; r < 10; ++r)
        for (int c = 0; c < 9; ++c)
            e.board[r][c] = initial[r][c];
    e.turn = 0;
    e.forbidden_move = NO_MOVE;
    e.game_over = false;
    e.init_score_and_hash();
}

static void reset_path_after_capture(XiangqiEngine& e) {
    e.path_len = 0;
    e.path_hashes[0] = e.current_hash;
    e.path_moves[0] = NO_MOVE;
    e.path_gave_check[0] = false;
    e.path_len = 1;
}

static XiangqiEngine::SearchResult fixed_depth_search(XiangqiEngine& e, int depth) {
    e.start_tp = std::chrono::steady_clock::now();
    e.time_limit = 1.0e12;
    e.stop_search = false;
    e.nodes = 0;
    e.tt_age++;
    const bool red_to_move = e.turn == 0;
    return e.minimax(depth, -SCORE_INF - 1, SCORE_INF + 1,
                     red_to_move, true, -1, true, 0);
}

static bool choose_random_legal(XiangqiEngine& e, std::mt19937_64& rng, Move& selected) {
    Move pseudo[128];
    Move legal[128];
    const bool red_to_move = e.turn == 0;
    int n = e.gen_all_moves(red_to_move, false, pseudo);
    int legal_n = 0;
    for (int i = 0; i < n; ++i) {
        char cap = e.make_move(pseudo[i]);
        bool ok = !e.is_in_check(red_to_move);
        e.undo_move(pseudo[i], cap);
        if (ok) legal[legal_n++] = pseudo[i];
    }
    if (legal_n == 0) return false;
    selected = legal[std::uniform_int_distribution<int>(0, legal_n - 1)(rng)];
    return true;
}

static DataRecord snapshot(const XiangqiEngine& e, int depth, int score,
                           uint32_t game_id, uint16_t ply, uint32_t nodes,
                           bool in_check, bool best_is_capture) {
    DataRecord rec{};
    int k = 0;
    for (int r = 0; r < 10; ++r)
        for (int c = 0; c < 9; ++c)
            rec.board[k++] = e.board[r][c];
    score = std::max(-19999, std::min(19999, score));
    rec.score_red = static_cast<int16_t>(score);
    rec.nodes = nodes;
    rec.game_id = game_id;
    rec.ply = ply;
    rec.stm = static_cast<uint8_t>(e.turn);
    rec.teacher_depth = static_cast<uint8_t>(depth);
    rec.flags = static_cast<uint8_t>((in_check ? 1 : 0) | (best_is_capture ? 2 : 0));
    rec.outcome_red = -1;
    return rec;
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "usage: generate_data OUTPUT GAMES DEPTH SEED [MAX_PLIES=120]"
                     " [SAMPLE_STRIDE=2] [RANDOM_PLIES=4]"
                     " [BALANCE_SIDES=0] [GAME_ID_OFFSET=0]\n";
        return 2;
    }
    const std::string output = argv[1];
    const int games = std::max(1, std::atoi(argv[2]));
    const int depth = std::max(1, std::atoi(argv[3]));
    const uint64_t seed = static_cast<uint64_t>(std::strtoull(argv[4], nullptr, 10));
    const int max_plies = argc > 5 ? std::max(10, std::atoi(argv[5])) : 120;
    const int sample_stride = argc > 6 ? std::max(1, std::atoi(argv[6])) : 2;
    const int random_plies = argc > 7 ? std::max(0, std::atoi(argv[7])) : 4;
    const bool balance_sides = argc > 8 && std::atoi(argv[8]) != 0;
    const uint32_t game_id_offset = argc > 9
        ? static_cast<uint32_t>(std::strtoul(argv[9], nullptr, 10)) : 0u;

    init_piece_values();
    init_pst_raw();
    init_zobrist();
    init_lmr();
    init_attack_tables();

    std::ofstream out(output, std::ios::binary | std::ios::trunc);
    if (!out) {
        std::cerr << "cannot open output: " << output << "\n";
        return 1;
    }
    DataHeader header{{'X','Q','N','N','U','E','1','\0'}, 1u,
                      static_cast<uint32_t>(sizeof(DataRecord))};
    out.write(reinterpret_cast<const char*>(&header), sizeof(header));

    XiangqiEngine engine;
    std::mt19937_64 rng(seed);
    uint64_t written = 0;
    uint64_t searched_nodes = 0;
    auto begin = std::chrono::steady_clock::now();

    for (int game = 0; game < games; ++game) {
        const uint32_t game_id = game_id_offset + static_cast<uint32_t>(game);
        reset_start_position(engine);
        std::vector<DataRecord> pending;
        int8_t outcome = -1;

        for (int ply = 0; ply < max_plies; ++ply) {
            bool repeated = false;
            int rv = engine.repetition_verdict(repeated);
            if (rv != 0) {
                int winner = rv > 0 ? engine.turn : (engine.turn ^ 1);
                outcome = winner == 0 ? 2 : 0;
                break;
            }
            if (repeated) {
                outcome = 1;
                break;
            }

            Move move = NO_MOVE;
            int score = 0;
            uint32_t nodes = 0;
            const int sample_phase = balance_sides && sample_stride > 1
                ? static_cast<int>(game_id % static_cast<uint32_t>(sample_stride)) : 0;
            bool label_position = ply >= random_plies &&
                                  ((ply - random_plies) % sample_stride == sample_phase);

            if (ply < random_plies) {
                if (!choose_random_legal(engine, rng, move)) {
                    outcome = engine.turn == 0 ? 0 : 2;
                    break;
                }
            } else {
                auto result = fixed_depth_search(engine, depth);
                move = result.move;
                score = result.score;
                nodes = static_cast<uint32_t>(std::min<long long>(
                    engine.nodes, std::numeric_limits<uint32_t>::max()));
                searched_nodes += engine.nodes;
                if (!move.is_valid()) {
                    outcome = engine.turn == 0 ? 0 : 2;
                    break;
                }
            }

            if (label_position) {
                bool in_check = engine.is_in_check(engine.turn == 0);
                bool best_capture = engine.board[move.r2][move.c2] != '.';
                pending.push_back(snapshot(engine, depth, score,
                                           game_id,
                                           static_cast<uint16_t>(ply), nodes,
                                           in_check, best_capture));
            }

            char captured = engine.make_move(move);
            if (captured == 'k') {
                outcome = 2;
                break;
            }
            if (captured == 'K') {
                outcome = 0;
                break;
            }
            if (captured != '.') reset_path_after_capture(engine);
        }

        for (auto& rec : pending) {
            rec.outcome_red = outcome;
            out.write(reinterpret_cast<const char*>(&rec), sizeof(rec));
            ++written;
        }

        if ((game + 1) % 10 == 0 || game + 1 == games) {
            double sec = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - begin).count();
            std::cerr << "games=" << (game + 1) << "/" << games
                      << " records=" << written
                      << " nodes=" << searched_nodes
                      << " nps=" << (sec > 0 ? static_cast<uint64_t>(searched_nodes / sec) : 0)
                      << " elapsed=" << sec << "s\n";
        }
    }

    return out ? 0 : 1;
}
