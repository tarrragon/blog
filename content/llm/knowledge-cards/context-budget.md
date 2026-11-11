---
title: "Context Budget"
date: 2026-05-12
description: "Coding agent 的 context window 拆分配額：system prompt + tool schema + history + file content + reasoning + tool result 各佔多少、留多少 margin"
weight: 1
tags: ["llm", "knowledge-cards", "coding-agent", "context-window"]
---

Context budget 的核心概念是「**把 [context window](/llm/knowledge-cards/context-window/) 視為有限資源、明確規劃 system prompt / tool schema / history / file content / reasoning trace / tool result 各佔多少**」。coding agent 的最大失敗模式是「context 用爆 → 模型開始遺忘關鍵指令 → 行為飄」、預算化是 harness 設計的核心責任。

## 跟其他概念的關係

典型 coding agent 的 context 構成（以 200K 模型為例）：

```text
[1. System prompt + tool schema]：     固定 ~10K-30K
   - agent 角色、輸出規則、tool 列表 + spec、subagent 路由
   - 經常用 prompt cache 加速、見 [prompt cache 卡]

[2. 工作歷史 / conversation history]：  動態 0-60K
   - 過去回合的 user query + assistant answer + tool calls
   - 越長越貴、harness 要決定何時 summarize / trim

[3. 當前任務 file context]：           動態 0-100K
   - 開啟的檔案、grep 結果、@-mention 帶入的內容

[4. Reasoning trace（若 reasoning model）]：  動態 1K-10K / step
   - <think>...</think> 段、每次推論都會佔 context

[5. Tool result]：                    動態 0-50K
   - file read 結果、bash output、test result

[6. Margin / safety buffer]：         保留 20-30K
   - 防止 generation 階段碰到 context limit
```

主流 coding agent 的 25% 規則（[context engineering 慣例](/llm/04-applications/coding-agent-harness/)）：

| 規則                         | 直覺                                                                                               |
| ---------------------------- | -------------------------------------------------------------------------------------------------- |
| Scaffold 部分（1+2） ≤ 25%   | 留 75% 給「當下任務」、避免 lost-in-the-middle 把指令吃掉                                          |
| File content ≤ 50%           | 不全載入大檔、用 grep / chunked read 替代                                                          |
| Margin ≥ 10%                 | Generation 階段才不會被 context limit 截斷                                                         |
| Reasoning trace 配長 context | Reasoning model 至少配 64K context、見 [reasoning-model 卡](/llm/knowledge-cards/reasoning-model/) |

## 判斷條件與後果

讀 coding agent 設計文件或 harness paper 看到「context budget」「context engineering」「token budgeting」，指的就是這個 framing。budget 超了沒有、該怎麼分，看下面幾個條件：

1. **context 用量超出 budget 時**：模型開始忽略 system prompt、回答跟前文重複、tool call 重複過去的步驟、reasoning trace 被截斷。這些行為代表關鍵指令被大量內容稀釋，或 generation 撞上了 context 上限。
2. **budget 吃緊時**：各區塊的省法代價不同。[prompt cache](/llm/knowledge-cards/prompt-cache/) 讓固定的 system prompt 與 tool schema 不必每次重算，省的是延遲與費用，佔用的 context 不變；grep 取代整檔讀取、tool result 限制長度（如 `head -100`）省下 context，代價是沒取到的內容模型看不到；定期 summarize history 省下歷史區，代價是細節在摘要時遺失。
3. **context 用得越多時**：中段內容的 recall 越差（[lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/)），所以 20K 解得了的任務塞到 100K，換到的是更差的 recall 與更高的成本；200K 的上限是容量，不是目標用量。
4. **任務類型不同時**：budget 的大小跟著變。autocomplete 的 budget 小，system prompt 加最近 50 行 code 就夠；refactor 要讀多個檔案，budget 大；agent loop 每一步都可能增加 tool result 與 history，budget 隨步數成長。
