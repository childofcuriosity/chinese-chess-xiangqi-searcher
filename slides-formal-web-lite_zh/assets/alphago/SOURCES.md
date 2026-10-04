# AlphaGo 图示来源

`alphago-policy-value-search.svg` 是为本讲稿重绘的中文教学图，不直接复制论文图片像素。

结构依据：David Silver 等，*Mastering the game of Go with deep neural networks and tree search*，Nature 529 (2016)，Fig. 1b 与 Fig. 3：

- 论文 PDF：https://deepmind-media.storage.googleapis.com/alphago/AlphaGoNaturePaper.pdf
- DOI：https://doi.org/10.1038/nature16961

图中保留原始 AlphaGo 的关键关系：策略网络给出走法先验，价值网络评价新叶，树搜索回传结果；2016 版本的叶子评价还混合快速走子模拟。SVG 中的中文说明、布局和配色为本课件自行制作。
