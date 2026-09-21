#define XQ_NO_MAIN
#include "nnue_engine.cpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>

#pragma pack(push, 1)
struct ValidationHeader {
    char magic[8];
    uint32_t version;
    uint32_t record_size;
};
struct ValidationRecord {
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

static uint64_t splitmix64(uint64_t value) {
    value += 0x9E3779B97F4A7C15ULL;
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9ULL;
    value = (value ^ (value >> 27)) * 0x94D049BB133111EBULL;
    return value ^ (value >> 31);
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "usage: validate_quant MODEL DATA_V2 [LIMIT=10000]\n";
        return 2;
    }
    const uint64_t limit = argc > 3 ? std::strtoull(argv[3], nullptr, 10) : 10000;
    init_piece_values();
    init_pst_raw();
    init_zobrist();
    init_lmr();
    init_attack_tables();
    if (!NNUE.load(argv[1])) {
        std::cerr << NNUE.error << "\n";
        return 1;
    }
    std::ifstream input(argv[2], std::ios::binary);
    ValidationHeader header{};
    input.read(reinterpret_cast<char*>(&header), sizeof(header));
    if (!input || std::memcmp(header.magic, "XQNNUE2", 7) != 0
        || header.version != 2 || header.record_size != sizeof(ValidationRecord)) {
        std::cerr << "unsupported validation data\n";
        return 1;
    }

    XiangqiEngine engine;
    ValidationRecord record{};
    uint64_t count = 0, pst_mismatch = 0, sign_ok = 0, sign_total = 0;
    long double absolute_error = 0.0, squared_error = 0.0;
    long double sx = 0.0, sy = 0.0, sxx = 0.0, syy = 0.0, sxy = 0.0;
    int max_abs_prediction = 0;
    while (count < limit && input.read(reinterpret_cast<char*>(&record), sizeof(record))) {
        uint64_t bucket = splitmix64(record.game_id) % 20;
        if (bucket < 3 || bucket >= 6 || (record.flags & 1)
            || std::abs(static_cast<int>(record.score_red)) >= 19999) continue;
        int offset = 0;
        for (int r = 0; r < 10; ++r)
            for (int c = 0; c < 9; ++c)
                engine.board[r][c] = record.board[offset++];
        engine.turn = record.stm;
        engine.forbidden_move = NO_MOVE;
        engine.game_over = false;
        engine.init_score_and_hash();
        if (engine.current_score != record.pst_red) ++pst_mismatch;
        const int prediction_red = engine.evaluate();
        const int x = prediction_red - record.pst_red;
        const int y = record.score_red - record.pst_red;
        const long double error = static_cast<long double>(x - y);
        absolute_error += std::abs(error);
        squared_error += error * error;
        sx += x; sy += y; sxx += static_cast<long double>(x) * x;
        syy += static_cast<long double>(y) * y;
        sxy += static_cast<long double>(x) * y;
        max_abs_prediction = std::max(max_abs_prediction, std::abs(x));
        if (std::abs(y) >= 20) {
            ++sign_total;
            if ((x > 0) == (y > 0) && x != 0) ++sign_ok;
        }
        ++count;
    }
    const long double n = std::max<uint64_t>(1, count);
    const long double covariance = sxy - sx * sy / n;
    const long double variance_x = sxx - sx * sx / n;
    const long double variance_y = syy - sy * sy / n;
    const long double correlation = variance_x > 0 && variance_y > 0
        ? covariance / std::sqrt(variance_x * variance_y) : 0.0;
    const long double slope = sxx > 0 ? sxy / sxx : 1.0;
    std::cout << "{\"positions\":" << count
              << ",\"pst_mismatch\":" << pst_mismatch
              << ",\"mae_cp\":" << static_cast<double>(absolute_error / n)
              << ",\"rmse_cp\":" << static_cast<double>(std::sqrt(squared_error / n))
              << ",\"correlation\":" << static_cast<double>(correlation)
              << ",\"sign_accuracy_abs20\":"
              << (sign_total ? static_cast<double>(sign_ok) / sign_total : 0.0)
              << ",\"zero_intercept_slope\":" << static_cast<double>(slope)
              << ",\"max_abs_prediction_cp\":" << max_abs_prediction
              << "}\n";
    return 0;
}
