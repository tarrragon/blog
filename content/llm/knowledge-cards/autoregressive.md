---
title: "Autoregressive"
date: 2026-05-11
description: "LLM 一次生成一個 token、把已生成內容作為下一次輸入的架構"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Autoregressive（自回歸）的核心概念是「下一個 [token](/llm/knowledge-cards/token/) 的生成需要看到前面所有 token」。LLM 每生一個 token 都要把目前的完整序列（prompt + 已生成部分）丟進神經網路跑一次，得到下一個 token 的機率分佈，挑一個輸出，再循環。

## 概念位置

Autoregressive 是 [Transformer](/llm/knowledge-cards/transformer/) 模型用於文字生成的運作方式。它跟生成式架構的另一條路線 [Diffusion](/llm/knowledge-cards/diffusion/) 形成對比：Diffusion 一次處理整張圖、autoregressive 一個 token 一個 token 接龍。寫 code 用的 LLM 都是 autoregressive。

## 可觀察訊號與例子

寫 code 場景的 streaming 輸出就是 autoregressive 的直接體現：你看到回答「邊想邊出現」，實際是每個 token 各跑一次 forward pass 後即時顯示。`寫 fibonacci function` 的回答經過「`def` → `def fib` → `def fib(` → ...」這樣逐 token 推進；模型回答越長等越久，跟雲端旗艦一樣，差別只在每次 forward pass 跑得多快。

## 設計責任

理解 autoregressive 後可以判讀幾件事：streaming 只是把已產出的 token 即時顯示、跟生成速度本身無關；回答長度直接影響等待時間；任何「一次生多個 token」的加速技巧（[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[MTP](/llm/knowledge-cards/mtp/)）都是針對 autoregressive 的優化、而非取代。
