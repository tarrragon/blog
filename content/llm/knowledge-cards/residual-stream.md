---
title: "Residual Stream"
date: 2026-05-14
description: "Transformer block 之間持續傳遞與累積資訊的 hidden state 通道，常用於架構與 mechanistic interpretability 討論"
weight: 1
tags: ["llm", "knowledge-cards", "transformer"]
---

Residual stream 的核心概念是「**[Transformer](/llm/knowledge-cards/transformer/) block 之間持續傳遞、被各層逐步修改的 hidden state 通道**」。它是整個模型中資訊流動的主幹，涵蓋範圍超過單一殘差連接。

## 概念位置

[Residual connection](/llm/knowledge-cards/residual-connection/) 是局部結構：把 layer input 加回 output。Residual stream 是整體視角：token representation 在每層 attention、FFN、normalization 作用後沿著主通道前進。

## 可觀察訊號與例子

讀 Transformer 架構或 mechanistic interpretability 文章看到「write to residual stream」「read from residual stream」「logit lens」時，討論的是各層如何在同一條 hidden state 通道上累積特徵。

## 設計責任

一般使用者不用調 residual stream，但理解它能幫助區分 layer、block、hidden state 與 residual connection。進一步閱讀可回到 [Transformer](/llm/knowledge-cards/transformer/) 與 [Residual Connection](/llm/knowledge-cards/residual-connection/)。
