---
title: "Jagged frontier"
date: 2026-05-14
description: "AI 能力分佈不規則的 framing：某些看似簡單的任務 AI 容易壞、某些看似複雜的任務 AI 反而做得好"
weight: 1
tags: ["llm", "knowledge-cards", "capability", "human-ai-collaboration"]
---

Jagged frontier（鋸齒狀邊界、HBS / UPenn / Wharton BCG 顧問研究、2023）是 AI 能力分佈的 framing，呼應 [capability spectrum](/llm/knowledge-cards/capability-spectrum/) 對能力光譜的刻畫：**「AI 能做的任務」呈鋸齒狀分佈，而非按人類直覺的難易連續排列**——某些看起來簡單的任務 AI 容易壞、某些看起來複雜的任務 AI 反而做得好。原因是能力分佈跟訓練資料 / tokenizer / 推論機制相關、不跟人類直覺的「難易」對齊。

## 跟其他概念的關係

典型對照（2024-2025 觀察、會隨模型升級漂移）：

| 看起來簡單但 AI 容易壞 | 看起來複雜但 AI 做得好 |
| ---------------------- | ---------------------- |
| 精確算術               | 寫風格指定的程式碼     |
| 計數                   | 翻譯複雜技術文章       |
| 嚴格遵守冷僻格式       | 從文字抽取關鍵 entity  |
| 引用真實 URL           | 解釋複雜概念           |

各失敗的機制各不相同：算術靠符號操作 + tokenizer 把數字切碎、計數跟 attention 機制不對盤、冷僻格式不在訓練分佈中、URL [hallucination](/llm/knowledge-cards/hallucination/) 是模型分辨不了「真實 vs 看起來合理」。Reasoning model + tool use 普及後 frontier 會移動、表的價值在 framing「不規則」、不是具體 4 個 case 當定論。

## 判斷條件與後果

Jagged frontier 的判斷看一個子任務位於 frontier 內還是外，以及這件事由什麼依據判定。

1. **用人類直覺的難易推測 AI 是否做得到時**，推測會在鋸齒處出錯：看起來簡單的精確算術與計數會失敗，看起來複雜的技術翻譯與程式碼生成反而做得好（上面的對照表），所以判定的依據是實際試跑的結果。
2. **系統設計成全自動、假設每個子任務都會成功時**，位於 frontier 外的子任務失敗了也沒有人或 tool 接手，原因是鋸齒狀分佈下總有子任務在 frontier 外；把「部分子任務會失敗」當成設計前提，那些位置才會預先放好人工介入或 tool。
3. **失敗的任務位於 frontier 外時**，反覆改 prompt 多半沒有效果，原因是失敗來自模型的能力邊界，prompt 寫法改變不了它；這對應 [prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/) 裡 systematic error 與 random error 的分辨。
4. **審查的人不分辨任務是否在 frontier 內、對 AI 結果一律低度審查時**（BCG 研究觀察到的 falling asleep at the wheel），frontier 外的錯誤跟 frontier 內的正確結果一起被放行。對應的做法是對團隊與使用者標出 frontier、frontier 外的任務強制人工審查（[HITL](/llm/knowledge-cards/human-in-the-loop/)），再用抽樣審查偵測 frontier 的移動。

完整人機協作 framing 見 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)。
