# NNUE Diagram Sources

[English](SOURCES.md) · [简体中文](SOURCES_zh.md)

Downloaded: 2026-09-17.

These diagrams come from official Stockfish `nnue-pytorch` documentation. They illustrate **chess NNUE**, while the tutorial uses Xiangqi examples to explain the shared ideas. Their feature counts and network dimensions are not the dimensions of this project's engine.

## Files

### stockfish-a-features-network.svg

- Original: `A-768-8-8-1.svg`, 771 × 732, about 85 KB after making it self-contained.
- [Official documentation](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html)
- [Pinned original](https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/docs/img/A-768-8-8-1.svg)
- Use as a main diagram: simpler than HalfKP, with legible input, hidden/output layers, and matrix operations on 16:9 slides.
- Suggested layout: 48%–55% page width, at most 68vh. Explain sparse features → accumulator → small fully connected layers → score alongside it, avoiding dense overlays.

### stockfish-halfkp-network.svg

- Original: `HalfKP-40960-4x2-8-1.svg`, 781 × 682, about 77 KB after making it self-contained.
- [Official documentation](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html)
- [Pinned original](https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/docs/img/HalfKP-40960-4x2-8-1.svg)
- Use for the advanced explanation of separate perspective features/accumulators. Dense upper connections make it less suitable as the first NNUE introduction.
- Suggested layout: 58%–64% width with two or three short notes; present at least at 1600×900.

### stockfish-sparse-matrix-vector.svg

- Original: `mvs.svg`, 216 × 216, about 23 KB.
- [Official documentation](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html)
- [Pinned original](https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/docs/img/mvs.svg)
- Shows that sparse inputs activate few columns, so matrix multiplication becomes a sum of those columns.
- Suggested display width: 300–380 px. Add a Xiangqi example: a rook moving a9→a8 removes its old feature column and adds the new one.

## Offline preparation

The two original network diagrams referenced four external icons through `xlink:href`. Local copies replace plus/equal/ellipsis icons with equivalent inline SVG symbols and remove the diagrams.net external troubleshooting link. Network structure, labels, nodes, edges, and numbers are unchanged. The original preparation opened all three in Chromium and checked screenshots.

SVG/XML namespace declarations such as `http://www.w3.org/...` identify formats; they are not runtime resource requests. These files contain no HTTP(S) `href` or CSS `url(...)` resource dependencies.

## License and attribution

The original figures reside in `official-stockfish/nnue-pytorch/docs/img/`, verified at commit `9f72946529c4187d3679014036cd22c3be419716`. The root license text is **GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007**. An unchanged offline [LICENSE](LICENSE) from the same commit is included; see the [pinned upstream license](https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/LICENSE).

This records the source and actual license file without extending its terms. Retain attribution and comply with applicable GPLv3 requirements when presenting or redistributing these assets.
