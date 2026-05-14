---
title: "Positional Encoding"
date: 2026-05-14
description: "把 token 位置資訊注入 Transformer 的機制，讓 attention 能分辨順序與距離"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "attention"]
---

Positional encoding（位置編碼）的核心概念是「**把序列中的位置資訊提供給 Transformer**」。純 [attention](/llm/knowledge-cards/attention/) 對 token 集合本身近似不帶順序感，位置編碼讓模型能分辨 `cat bites dog` 與 `dog bites cat`。

## 概念位置

位置資訊通常在 embedding 進入 Transformer block 前或 attention 計算中注入。常見路線包含 sinusoidal positional encoding、learned positional embedding、[RoPE](/llm/knowledge-cards/rope/) 與 ALiBi；現代 decoder-only LLM 多使用 RoPE 或其長 context scaling 變體。

## 可觀察訊號與例子

讀 model architecture 看到 `max_position_embeddings`、RoPE base、RoPE scaling、ALiBi、YaRN、NTK-aware scaling，就是位置編碼相關設定。長 context 擴展常卡在位置編碼外推能力，而不是只把 context window 數字調大。

## 設計責任

評估長 context 模型時，要分清楚「宣稱 context 長度」與「位置編碼在該長度仍可靠」。超過訓練長度太多時，即使能載入，模型對遠距關係也可能退化。完整章節見 [Transformer architecture](/llm/03-theoretical-foundations/transformer-architecture/)。
