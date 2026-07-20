---
title: "Jagged frontier"
date: 2026-05-14
description: "AI 能力分佈不規則的 framing：某些看似簡單的任務 AI 容易壞、某些看似複雜的任務 AI 反而做得好"
weight: 1
tags: ["llm", "knowledge-cards", "capability", "human-ai-collaboration"]
---

Jagged frontier（鋸齒狀邊界、HBS / UPenn / Wharton BCG 顧問研究、2023）是 AI 能力分佈的 framing，呼應 [capability spectrum](/llm/knowledge-cards/capability-spectrum/) 對能力光譜的刻畫：**「AI 能做的任務」呈鋸齒狀分佈，而非按人類直覺的難易連續排列**——某些看起來簡單的任務 AI 容易壞、某些看起來複雜的任務 AI 反而做得好。原因是能力分佈跟訓練資料 / tokenizer / 推論機制相關、不跟人類直覺的「難易」對齊。

## 概念位置

典型對照（2024-2025 觀察、會隨模型升級漂移）：

| 看起來簡單但 AI 容易壞 | 看起來複雜但 AI 做得好 |
| ---------------------- | ---------------------- |
| 精確算術               | 寫風格指定的程式碼     |
| 計數                   | 翻譯複雜技術文章       |
| 嚴格遵守冷僻格式       | 從文字抽取關鍵 entity  |
| 引用真實 URL           | 解釋複雜概念           |

各失敗的機制各不相同：算術靠符號操作 + tokenizer 把數字切碎、計數跟 attention 機制不對盤、冷僻格式不在訓練分佈中、URL [hallucination](/llm/knowledge-cards/hallucination/) 是模型分辨不了「真實 vs 看起來合理」。Reasoning model + tool use 普及後 frontier 會移動、表的價值在 framing「不規則」、不是具體 4 個 case 當定論。

## 設計責任

讀 AI 應用設計文章看到「jagged frontier」「AI capability boundary」「falling asleep at the wheel」就是這個 framing。設計判讀：

1. **不要用人類直覺難易推測 AI 能力**：試跑、看結果、不要預判。
2. **「全自動」是 over-trust 假設**：frontier 鋸齒、總有些子任務落 frontier 外、需要人介入或 tool 補。設計時假設「有部分子任務 AI 會失敗」、不是「都會成功」。
3. **失敗在 frontier 外加 prompt iteration 通常無效**：那是模型能力邊界問題、不是 prompt 問題。對應 [prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/) 的 systematic vs random error 診斷。
4. **Falling asleep at the wheel**：BCG 研究觀察到的人類行為——傾向不分辨任務是否在 frontier 內、對 AI 結果一律低度審查。緩解：對團隊 / user 明確標 frontier、frontier 外任務強制人類審查（HITL）、抽樣審查偵測 frontier 漂移。

完整人機協作 framing 見 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)。
