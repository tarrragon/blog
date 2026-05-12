---
title: "Context Budget"
date: 2026-05-12
description: "Coding agent 的 context window 拆分配額：system prompt + tool schema + history + file content + reasoning + tool result 各佔多少、留多少 margin"
weight: 1
tags: ["llm", "knowledge-cards", "coding-agent", "context-window"]
---

Context budget 的核心概念是「**把 [context window](/llm/knowledge-cards/context-window/) 視為有限資源、明確規劃 system prompt / tool schema / history / file content / reasoning trace / tool result 各佔多少**」。coding agent 的最大失敗模式是「context 用爆 → 模型開始遺忘關鍵指令 → 行為飄」、預算化是 harness 設計的核心責任。

## 概念位置

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

## 設計責任

讀 coding agent 設計 / harness paper 看到「context budget」「context engineering」「token budgeting」就是這 framing。寫 code 場景的判讀：

1. **超出 budget 的訊號**：模型開始忽略 system prompt、回答跟前文重複、tool call 重複過去步驟、reasoning trace 截斷
2. **節省 budget 的策略**：用 [prompt cache](/llm/knowledge-cards/prompt-cache/) 把 system + tool schema 攤平、grep 取代全檔讀、tool result 限長度（如 head -100）、定期 summarize history
3. **跟 [lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 的關係**：context 用越多、中段內容 recall 越差、所以「能用 20K 解就別用 100K」、不是「能塞 200K 就塞滿」
4. **不同 task 不同 budget**：autocomplete 任務 budget 小（系統 prompt + 最近 50 行 code 就夠）；refactor 任務 budget 大（多檔案）；agent loop 任務 budget 動態（每步可能 grow）
