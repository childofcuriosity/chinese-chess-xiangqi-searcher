# AlphaGo Diagram Sources

[English](SOURCES.md) · [简体中文](SOURCES_zh.md)

`alphago-policy-value-search.svg` is an original teaching redraw, rather than a pixel copy of a paper figure. The English edition translates the labels; the original Chinese diagram is preserved in `slides-formal-web-lite_zh/`.

Structure: David Silver et al., *Mastering the game of Go with deep neural networks and tree search*, Nature 529 (2016), Figs. 1b and 3.

- [Paper PDF](https://deepmind-media.storage.googleapis.com/alphago/AlphaGoNaturePaper.pdf)
- [DOI](https://doi.org/10.1038/nature16961)

The diagram preserves the original AlphaGo relationships: policy priors guide moves, value evaluates new leaves, and tree search backs up results. The 2016 version also combines value estimates with fast rollouts. Explanations, layout, and colors were created for this tutorial.
