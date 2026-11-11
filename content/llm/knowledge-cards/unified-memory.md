---
title: "Unified Memory Architecture"
date: 2026-05-11
description: "Apple Silicon 讓 CPU / GPU / NE 共用同一塊記憶體：跑大模型的優勢來源"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Unified Memory Architecture（UMA、統一記憶體架構）的核心概念是「Apple Silicon 把 CPU、GPU、Neural Engine 接在同一塊記憶體上」、共用同一份位址空間。傳統 PC 把系統記憶體跟 [VRAM](/llm/knowledge-cards/vram/) 分開、模型權重要塞進 VRAM 才能用 GPU 跑、跨 PCIe 搬資料很慢。Mac 的統一記憶體避開這個限制。

## 跟其他概念的關係

UMA 是 Apple Silicon 在「能跑多大模型」上佔優勢的硬體基礎。32GB 統一記憶體可以幾乎全部給模型用（留 8GB 給系統）；同等價位的 PC + NVIDIA 配置通常只有 12 ~ 24GB VRAM。能跑得動 vs 跑得快是兩件事：UMA 解前者、[memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 才決定後者。

## 可觀察訊號與例子

32GB Mac 跑 [Q4 量化](/llm/knowledge-cards/quantization/) 的 Gemma 4 31B 模型順暢（佔 18GB）、同等價位 PC（16GB VRAM 等級）跑不動同一模型、要降到 14B Q4 才行。70B 模型在 64GB Mac 上可行、PC 需要兩張 24GB VRAM GPU 配 NVLink、成本高得多。

## 判斷條件與後果

Mac 能跑多大的模型由統一記憶體的容量決定，原因是 GPU 直接讀同一塊記憶體，模型權重不必另外放進 VRAM；CPU 規格與儲存空間不改變這個上限，所以買 Mac 跑本地 LLM 時，記憶體容量排在兩者之前。容量對應的情境：32GB 扣掉留給系統的部分，跑得起 Gemma 4 31B MTP，涵蓋寫 code 的常見需求；48 ~ 64GB 跑得起 70B，或同時跑兩個模型；96GB 以上在寫 code 的情境多半用不滿，多出的容量沒有對應的模型需求。容量只決定跑不跑得動，生字速度由 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 決定。MLX 等 framework 與 Metal backend 利用 UMA 的方式略有差異，但對使用者都透明，選 inference server 時不必比較這一層。
