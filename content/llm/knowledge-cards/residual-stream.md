---
title: "Residual Stream"
date: 2026-05-14
description: "Transformer block 之間持續傳遞與累積資訊的 hidden state 通道，常用於架構與 mechanistic interpretability 討論"
weight: 1
tags: ["llm", "knowledge-cards", "transformer"]
---

Residual stream 的核心概念是「**[Transformer](/llm/knowledge-cards/transformer/) block 之間持續傳遞、被各層逐步修改的 hidden state 通道**」。它是整個模型中資訊流動的主幹，涵蓋範圍超過單一殘差連接。

## 跟其他概念的關係

[Residual connection](/llm/knowledge-cards/residual-connection/) 是局部結構：把 layer input 加回 output。Residual stream 是整體視角：token representation 在每層 attention、FFN、normalization 作用後沿著主通道前進。

## 可觀察訊號與例子

讀 Transformer 架構或 mechanistic interpretability 文章看到「write to residual stream」「read from residual stream」「logit lens」時，討論的是各層如何在同一條 hidden state 通道上累積特徵。

## 判斷條件與後果

文章寫某一層「write to」或「read from」residual stream、或用 logit lens 讀中間層時，對象是跨所有 block 持續傳遞的那一條 hidden state 通道，各層的輸出在上面逐層累加；寫 skip connection 或 `output = layer(x) + x` 時，對象是單一 block 裡的那一次加法。把整條通道讀成單一 block 的加法，會把「某一層在通道上留下的特徵」讀成「某一個 block 的輸出」，看不出後面的層讀得到前面各層寫入的內容。一般使用者不直接調整 residual stream，這個分辨用在讀 Transformer 架構與 mechanistic interpretability 的文章。進一步閱讀可回到 [Transformer](/llm/knowledge-cards/transformer/) 與 [Residual Connection](/llm/knowledge-cards/residual-connection/)。
