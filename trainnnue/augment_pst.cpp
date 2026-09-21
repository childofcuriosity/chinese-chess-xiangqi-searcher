#define XQ_NO_MAIN
#include "teacher.cpp"

#pragma pack(push, 1)
struct Header { char magic[8]; uint32_t version; uint32_t record_size; };
struct RecordV1 {
    char board[90]; int16_t score_red; uint32_t nodes; uint32_t game_id;
    uint16_t ply; uint8_t stm; uint8_t teacher_depth; uint8_t flags;
    int8_t outcome_red;
};
struct RecordV2 {
    char board[90]; int16_t score_red; uint32_t nodes; uint32_t game_id;
    uint16_t ply; uint8_t stm; uint8_t teacher_depth; uint8_t flags;
    int8_t outcome_red; int16_t pst_red;
};
#pragma pack(pop)

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: augment_pst INPUT_V1 OUTPUT_V2\n";
        return 2;
    }
    init_piece_values(); init_pst_raw(); init_zobrist(); init_lmr(); init_attack_tables();
    std::ifstream in(argv[1], std::ios::binary);
    std::ofstream out(argv[2], std::ios::binary | std::ios::trunc);
    Header old_header{};
    in.read(reinterpret_cast<char*>(&old_header), sizeof(old_header));
    if (!in || std::memcmp(old_header.magic, "XQNNUE1", 7) != 0
        || old_header.version != 1 || old_header.record_size != sizeof(RecordV1)) {
        std::cerr << "invalid v1 data file\n";
        return 1;
    }
    Header new_header{{'X','Q','N','N','U','E','2','\0'}, 2u,
                      static_cast<uint32_t>(sizeof(RecordV2))};
    out.write(reinterpret_cast<const char*>(&new_header), sizeof(new_header));
    XiangqiEngine engine;
    RecordV1 source{};
    uint64_t count = 0;
    while (in.read(reinterpret_cast<char*>(&source), sizeof(source))) {
        for (int sq = 0; sq < 90; ++sq) engine.board[sq / 9][sq % 9] = source.board[sq];
        engine.turn = source.stm;
        engine.init_score_and_hash();
        RecordV2 target{};
        std::memcpy(&target, &source, sizeof(source));
        target.pst_red = static_cast<int16_t>(std::max(-19999, std::min(19999, engine.current_score)));
        out.write(reinterpret_cast<const char*>(&target), sizeof(target));
        ++count;
    }
    std::cerr << "augmented records=" << count << "\n";
    return out ? 0 : 1;
}
