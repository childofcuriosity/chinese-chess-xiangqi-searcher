# Xiangqi Engine Tutorial

[English interactive tutorial](index.html) · [Download PDF](xiangqi-engine-tutorial.pdf) · [Chinese tutorial](../slides-formal-web-lite_zh/index.html)

Open `index.html` directly, or serve this folder:

```powershell
python -m http.server 8080 --directory slides-formal-web-lite
```

Open http://localhost:8080. Arrow keys reveal steps and navigate; **M** opens the chapter map; **S** opens speaker view. All scripts, styles, and figures are local, so the tutorial works offline.

The English edition retains all 108 teaching slides, board positions, formulas, and result data. Speaker notes are concise English teaching prompts. The original Chinese presentation, including full speaker notes, is preserved as a standalone sibling directory.

The PDF contains a cover and all 108 slides, with every reveal visible. Text and diagrams remain vector-based and searchable. Animation, navigation, and speaker view are available in the HTML edition.

## Rebuild the PDF

From the repository root:

```powershell
npm install --no-save playwright
npx playwright install chromium
node slides-formal-web-lite/export_pdf.mjs
```

The exporter waits for local assets/fonts, enables the print layout, and writes `xiangqi-engine-tutorial.pdf`. Source acknowledgments are in [NNUE sources](assets/nnue/SOURCES.md) and [AlphaGo sources](assets/alphago/SOURCES.md).
