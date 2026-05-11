---
title: "Prefill"
date: 2026-05-11
description: "Prompt 首次處理時的計算階段：把整段輸入跑過模型、產生 KV cache"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Prefill 的核心概念是「[LLM 首次處理 prompt 時、把整段輸入跑過模型一次的計算階段](/llm/knowledge-cards/autoregressive/)」。Prefill 階段會為 prompt 中每個 [token](/llm/knowledge-cards/token/) 算出 attention 中間結果並存進 [KV cache](/llm/knowledge-cards/kv-cache/)，之後生成新 token 時可以直接讀 cache。

## 概念位置

Prefill 是 [TTFT](/llm/knowledge-cards/ttft/) 的主要構成部分。Prefill 結束後系統進入 decode 階段、開始一個一個生 token。兩階段的瓶頸不同：prefill 是「算力 bound」（並行處理整段 prompt）、decode 是「記憶體頻寬 bound」。

## 可觀察訊號與例子

短 prompt（500 tokens）：prefill 通常 < 1 秒、感覺不到。

中等 prompt（4K tokens）：M4 Max 跑 31B 模型約 3 ~ 8 秒、開始有感。

長 prompt（10K+ tokens）：本地 prefill 拉到 30 ~ 90 秒、是 coding agent 場景最痛的點。

雲端旗艦 prefill 速度快得多，因為 H100 / TPU 的算力遠高於 Apple Silicon，且常用大批次平行 prefill。

## 設計責任

判讀「為何本地 LLM 在塞長 context 時這麼慢」要追到 prefill 階段。緩解方法有三條：縮短 prompt（移除不必要 context）、用支援 prefix cache 的伺服器（如 oMLX 的 paged SSD KV cache 可重用之前 prefill 過的結果）、切到雲端旗艦（資料中心 prefill 算力遠高於 Mac）。
