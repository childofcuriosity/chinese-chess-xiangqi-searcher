#define NNUE_TEACHER
#define XQ_NO_MAIN
#include "teacher.cpp"

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>

#pragma pack(push, 1)
struct DataHeader {
    char magic[8];
    uint32_t version;
    uint32_t record_size;
};

struct DataRecordV2 {
    char board[90];
    int16_t score_red;
    uint32_t nodes;
    uint32_t game_id;
    uint16_t ply;
    uint8_t stm;
    uint8_t teacher_depth;
    uint8_t flags;
    int8_t outcome_red;
    int16_t pst_red;
};
#pragma pack(pop)

static XiangqiEngine::SearchResult fixed_depth_search(XiangqiEngine& e, int depth) {
    e.start_tp = std::chrono::steady_clock::now();
    e.time_limit = 1.0e12;
    e.stop_search = false;
    e.nodes = 0;
    ++e.tt_age;
    return e.minimax(depth, -SCORE_INF - 1, SCORE_INF + 1,
                     e.turn == 0, true, -1, true, 0);
}

static uint32_t selection_hash(const DataRecordV2& record, uint32_t seed) {
    uint32_t value = record.game_id * 0x9e3779b9u;
    value ^= static_cast<uint32_t>(record.ply) * 0x85ebca6bu;
    value ^= seed + 0xc2b2ae35u;
    value ^= value >> 16;
    value *= 0x7feb352du;
    value ^= value >> 15;
    value *= 0x846ca68bu;
    return value ^ (value >> 16);
}

int main(int argc, char** argv) {
    if (argc < 6) {
        std::cerr << "usage: relabel_data INPUT_V2 OUTPUT_V2 DEPTH MODULO SEED [LIMIT=0]\n";
        return 2;
    }
    const std::string input = argv[1];
    const std::string output = argv[2];
    const int depth = std::max(1, std::atoi(argv[3]));
    const uint32_t modulo = static_cast<uint32_t>(std::max(1, std::atoi(argv[4])));
    const uint32_t seed = static_cast<uint32_t>(std::strtoul(argv[5], nullptr, 10));
    const uint64_t limit = argc > 6 ? std::strtoull(argv[6], nullptr, 10) : 0;

    std::ifstream in(input, std::ios::binary);
    DataHeader header{};
    in.read(reinterpret_cast<char*>(&header), sizeof(header));
    if (!in || std::memcmp(header.magic, "XQNNUE2", 7) != 0 || header.version != 2
        || header.record_size != sizeof(DataRecordV2)) {
        std::cerr << "unsupported input dataset\n";
        return 1;
    }
    std::ofstream out(output, std::ios::binary | std::ios::trunc);
    if (!out) {
        std::cerr << "cannot create output dataset\n";
        return 1;
    }
    out.write(reinterpret_cast<const char*>(&header), sizeof(header));

    init_piece_values();
    init_pst_raw();
    init_zobrist();
    init_lmr();
    init_attack_tables();
    XiangqiEngine engine;
    DataRecordV2 record{};
    uint64_t seen = 0, written = 0, total_nodes = 0;
    const auto started = std::chrono::steady_clock::now();
    while (in.read(reinterpret_cast<char*>(&record), sizeof(record))) {
        ++seen;
        if (selection_hash(record, seed) % modulo != 0) continue;
        if (limit && written >= limit) break;
        int offset = 0;
        for (int r = 0; r < 10; ++r)
            for (int c = 0; c < 9; ++c)
                engine.board[r][c] = record.board[offset++];
        engine.turn = record.stm;
        engine.forbidden_move = NO_MOVE;
        engine.game_over = false;
        engine.path_len = 0;
        engine.init_score_and_hash();
        const auto result = fixed_depth_search(engine, depth);
        int score = std::max(-19999, std::min(19999, result.score));
        record.score_red = static_cast<int16_t>(score);
        record.nodes = static_cast<uint32_t>(std::min<long long>(
            engine.nodes, std::numeric_limits<uint32_t>::max()));
        record.teacher_depth = static_cast<uint8_t>(depth);
        const bool in_check = engine.is_in_check(engine.turn == 0);
        const bool capture = result.move.is_valid()
                          && engine.board[result.move.r2][result.move.c2] != '.';
        record.flags = static_cast<uint8_t>((in_check ? 1 : 0) | (capture ? 2 : 0));
        out.write(reinterpret_cast<const char*>(&record), sizeof(record));
        total_nodes += engine.nodes;
        ++written;
        if (written % 1000 == 0) {
            const double elapsed = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - started).count();
            std::cerr << "written=" << written << " nodes=" << total_nodes
                      << " elapsed=" << elapsed << "s nps="
                      << static_cast<uint64_t>(total_nodes / std::max(1.0, elapsed)) << "\n";
        }
    }
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started).count();
    std::cerr << "done seen=" << seen << " written=" << written
              << " nodes=" << total_nodes << " elapsed=" << elapsed << "s\n";
    return out ? 0 : 1;
}
