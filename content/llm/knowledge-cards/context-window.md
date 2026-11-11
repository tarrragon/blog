---
title: "Context Window"
date: 2026-05-11
description: "模型一次能處理的最大 token 數量：prompt 加生成的總和上限"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Context Window 的核心概念是「模型一次能處理的最大 [token](/llm/knowledge-cards/token/) 序列長度」，包含 prompt 與生成內容的總和。超過上限時，較早的 token 會被截掉、模型「看不到」前面的對話。

## 跟其他概念的關係

Context window 是模型訓練時決定的硬性限制，跟 [KV cache](/llm/knowledge-cards/kv-cache/) 共同決定推論時的記憶體佔用。較大的 context window 讓模型能讀整個 repo 或長對話，但代價是 [TTFT](/llm/knowledge-cards/ttft/) 升高與記憶體吃緊。

## 可觀察訊號與例子

2026 年 5 月各模型典型 context window：

| 模型                      | Context Window |
| ------------------------- | -------------- |
| Gemma 4 31B               | 256K tokens    |
| Qwen3-Coder 30B           | 256K tokens    |
| Llama 3.3 70B             | 128K tokens    |
| Claude Sonnet 4.6（雲端） | 1M tokens      |
| GPT-5（雲端）             | 400K tokens    |

「支援 128K」跟「實用 128K」是兩件事。本地跑長 context 時 KV cache 會吃掉大量記憶體，例如 32GB Mac 跑 31B 模型實用 context 大約 8 ~ 16K tokens；硬塞 128K 會 swap、跑成蝸牛。

## 判斷條件與後果

整個 repo 是否放得進 prompt，由三個上限裡最小的那一個決定：模型聲稱的 context window、機器記憶體放得下的 KV cache、可接受的 [TTFT](/llm/knowledge-cards/ttft/)。只看聲稱值時，本地跑長 context 會先碰到記憶體的上限，上面 32GB Mac 跑 31B 模型的例子實用範圍只有 8K 到 16K tokens，超過就開始 swap，生成速度大幅下降；TTFT 也隨 prompt 長度增加，因為模型要先處理完整段輸入才吐出第一個 token。寫 prompt 時反覆碰到上限，代表內容超過了這個最小值，可走的兩條路是移除不必要的 context，或改用 context 更大的雲端模型。
