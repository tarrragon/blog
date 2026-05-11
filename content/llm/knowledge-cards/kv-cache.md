---
title: "KV Cache"
date: 2026-05-11
description: "已處理 token 的 attention 中間結果暫存：避免重算、加速後續生成"
weight: 1
tags: ["llm", "knowledge-cards"]
---

KV Cache 的核心概念是「LLM 推論過程中、把已處理過的 [token](/llm/knowledge-cards/token/) 的 attention key / value 暫存起來、後續 token 生成時直接讀」。它讓「已 [prefill](/llm/knowledge-cards/prefill/) 過的 prompt」省下重複計算，是 [autoregressive](/llm/knowledge-cards/autoregressive/) 模型能跑得起來的關鍵優化。

## 概念位置

KV cache 存在於記憶體中，大小跟 prompt 長度線性增加。它跟模型權重一起佔用記憶體預算；長 [context window](/llm/knowledge-cards/context-window/) 場景的 KV cache 可能比模型權重本身還大。

## 可觀察訊號與例子

Gemma 4 31B（Q4 量化）的 KV cache 估算：

| Context 長度 | KV Cache 估算 | 加上模型權重總和            |
| ------------ | ------------- | --------------------------- |
| 1K tokens    | ~0.5 GB       | 18.5 GB                     |
| 4K tokens    | ~2 GB         | 20 GB                       |
| 16K tokens   | ~8 GB         | 26 GB                       |
| 32K tokens   | ~16 GB        | 34 GB（32GB Mac 開始 swap） |

32GB Mac 跑 31B 模型實際可用 context 大約 8 ~ 16K tokens；超過就需要 swap、速度崩潰。

## 設計責任

理解 KV cache 後可以解釋兩個現象：為何長 context 不只 TTFT 高、還會吃爆記憶體；為何 oMLX 的「paged SSD KV cache」對 coding agent 場景很有用（把 cache 推到 SSD，跨 session 復用同前綴的 prefill 結果）。設定本地伺服器時，留意 context 長度與記憶體預算的乘積、避免無意間踩到 swap。
