---
title: "TTFT"
date: 2026-05-11
description: "Time To First Token：送出 prompt 到第一個 token 出現的等待時間"
weight: 1
tags: ["llm", "knowledge-cards"]
---

TTFT（Time To First Token）的核心概念是「使用者送出 prompt 之後，等多久才看到第一個 [token](/llm/knowledge-cards/token/) 出現」。它包含 prompt 的 [prefill](/llm/knowledge-cards/prefill/) 時間、網路傳輸（雲端才有）、伺服器排隊與第一個 token 的生成。

## 概念位置

TTFT 跟 [tokens per second](/llm/knowledge-cards/tokens-per-second/)（生字速度）是兩個獨立指標。前者描述「開始講話前的停頓」，後者描述「開始講話後講多快」。長 [context](/llm/knowledge-cards/context-window/) 場景的 TTFT 由 prefill 主導，與 prompt 長度成正比。

## 可觀察訊號與例子

短 prompt（< 1K token）場景：

| 環境                     | TTFT       |
| ------------------------ | ---------- |
| Claude Sonnet 雲端       | 0.5 ~ 1 秒 |
| Gemma 4 31B MTP / M4 Max | 1 ~ 3 秒   |

長 prompt（10K+ token）場景：本地 TTFT 可能拉到 30 ~ 90 秒（每次都重新 prefill 整段 context）。雲端 TTFT 受影響較小，因為 H100 等資料中心 GPU 的 prefill 算力遠高於 Apple Silicon。

## 設計責任

寫 code 場景的 TTFT 痛點主要出現在 coding agent 模式（塞整個 repo 進 prompt）。對短 prompt 場景，TTFT 1 ~ 3 秒可接受；對長 context 場景，要評估特化伺服器（如 oMLX）的 [KV cache](/llm/knowledge-cards/kv-cache/) 重用方案。判讀 TTFT 報告時，務必確認 prompt 長度、否則數字無從比較。
