---
title: "Memory Bandwidth"
date: 2026-05-11
description: "記憶體每秒能讀寫多少 bytes：決定本地 LLM 生字速度的真正瓶頸"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Memory Bandwidth（記憶體頻寬）的核心概念是「每秒能從記憶體讀寫多少 bytes」。對 LLM 推論而言、它是「真正的瓶頸」、決定 [tokens per second](/llm/knowledge-cards/tokens-per-second/) 的理論上限；CPU / GPU 算力反而很少成為瓶頸。

## 概念位置

[Autoregressive](/llm/knowledge-cards/autoregressive/) 模型每生一個 token 都要把整個模型權重從記憶體讀到處理器一次。模型多大、頻寬多快、決定每秒能讀過幾次完整權重、也就決定每秒生幾個 token。

## 可觀察訊號與例子

各代 Apple Silicon 的記憶體頻寬：

| 晶片          | 頻寬       |
| ------------- | ---------- |
| M2 / M3       | 100 GB/s   |
| M2 Pro        | 200 GB/s   |
| M4 Max        | 546 GB/s   |
| M2 / M3 Ultra | 800+ GB/s  |
| H100（雲端）  | 3,300 GB/s |

理論上限算式：`頻寬 / 模型大小 = 最大 tok/s`。M4 Max 跑 Q4 量化的 31B 模型（約 18GB）、理論上限約 546 / 18 ≈ 30 tok/s。實際值會比理論低 30 ~ 50%（[KV cache](/llm/knowledge-cards/kv-cache/) 讀寫、attention 中間結果等開銷）。

H100 頻寬是 M4 Max 的 6 倍、這就是雲端旗艦速度比本地快這麼多的根本原因。

## 設計責任

評估「換更快 Mac 能加速多少」要看頻寬而不是 CPU 核心數。M2 升 M4 Max 對 LLM 推論的速度收益主要來自頻寬升級（200 → 546 GB/s）、約 2.7 倍。看到「N 倍加速」報導時、把頻寬與模型大小代進公式對一下、能識破不合理的數字。
