# NNUE 图示来源

下载日期：2026-09-17。

这些图来自 Stockfish 官方 `nnue-pytorch` 文档。它们是**国际象棋 NNUE 教学示意**；本分享只借用算法结构，并用我们自己的中国象棋例子演算，不能把图中的棋盘特征数量或网络尺寸说成当前自写象棋引擎的实现。

## 文件

### `stockfish-a-features-network.svg`

- 原图名称：`A-768-8-8-1.svg`
- 尺寸：771 × 732，约 85 KB（本地化后）。
- 官方说明页：https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html
- 官方仓库原文件：https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/docs/img/A-768-8-8-1.svg
- 适用：大屏主图。结构比 HalfKP 图简单，输入、隐藏层、输出和矩阵运算在 16:9 页面中更容易读。
- 布局建议：图宽约占页面 48%–55%，高度不超过 68vh；右侧用中文分四步解释“稀疏棋子特征 → 第一层累加器 → 小型全连接层 → 一个局面分数”。不要在图内叠加大段中文。

### `stockfish-halfkp-network.svg`

- 原图名称：`HalfKP-40960-4x2-8-1.svg`
- 尺寸：781 × 682，约 77 KB（本地化后）。
- 官方说明页：https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html
- 官方仓库原文件：https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/docs/img/HalfKP-40960-4x2-8-1.svg
- 适用：讲“双方视角各有一组特征与累加器”时作为进阶图。顶部连接较密，不建议在第一次介绍 NNUE 时单独铺满一页。
- 布局建议：若使用，宽度约 58%–64%，旁边只保留两三条短注释；至少在 1600×900 播放，避免再缩小图中文字。

### `stockfish-sparse-matrix-vector.svg`

- 原图名称：`mvs.svg`
- 尺寸：216 × 216，约 23 KB。
- 官方说明页：https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html
- 官方仓库原文件：https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/docs/img/mvs.svg
- 适用：说明稀疏输入只激活少数列，矩阵乘法等价于把相应列加进累加器。
- 布局建议：作为局部放大图使用，显示宽度 300–380 px；旁边配中国象棋例子，例如“红车从 a9 到 a8：移除旧格特征列，加上新格特征列”。

## 离线处理

官方两个网络图原先通过 `xlink:href` 引用了四个外部小图标。为保证离线播放，本地副本把这些“加号、等号、省略号”替换为等义的内嵌简单 SVG 符号，并移除了 diagrams.net 的外部故障说明链接。网络结构、文字、节点、连线和数值均未改动。三个文件已用本地 Chromium 直接打开并截图检查。

文件中仍会出现 `http://www.w3.org/...` 的 SVG/XML 命名空间声明；它们是格式标识，不是运行时外部资源。文件内没有 `http(s)` 的 `href` 或 CSS `url(...)` 资源依赖。

## 许可与归属

- 上述原图实际存在于 Stockfish 官方 `official-stockfish/nnue-pytorch` 仓库的 `docs/img/`，本次核对提交为 `9f72946529c4187d3679014036cd22c3be419716`。
- 该仓库根目录 `LICENSE` 的实际文本标题是 **GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007**。本目录已保存来自同一固定提交、未经修改的离线副本 [`LICENSE`](LICENSE)；官方固定提交原文：https://github.com/official-stockfish/nnue-pytorch/blob/9f72946529c4187d3679014036cd22c3be419716/LICENSE
- 这里仅记录仓库中的实际许可文件和素材归属，不进一步推断超出许可证文本的权利范围。演示及再分发时保留本来源说明，并按 GPLv3 原文履行适用义务。
