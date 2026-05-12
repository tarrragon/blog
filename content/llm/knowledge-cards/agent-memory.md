---
title: "Agent Memory"
date: 2026-05-12
description: "Agent 在 context window 之外管理長期狀態的設計、五個層次：working / short-term / long-term episodic / semantic / procedural"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "memory"]
---

Agent memory 的核心概念是「**agent 在 [context window](/llm/knowledge-cards/context-window/) 之外管理長期狀態的設計**」、把使用者偏好、過去任務、知識、操作流程等持久化、跨 session 重用。借鑒人類認知科學的五個層次：working memory（context 本身）、short-term（session scratchpad）、long-term episodic（過去事件）、long-term semantic（事實 / 知識）、long-term procedural（流程 / 技能）。

## 概念位置

五個層次的對比：

| 層                          | 範圍                      | 存放位置                                                             | 典型內容                                                      |
| --------------------------- | ------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------- |
| Working memory              | 當前 query / forward pass | [Context window](/llm/knowledge-cards/context-window/) 本身          | 當下對話、tool result、reasoning trace                        |
| Short-term / session memory | 單一 session（小時級）    | Scratchpad 物件 / [prompt cache](/llm/knowledge-cards/prompt-cache/) | Session 內累積的中間結果、用過的策略                          |
| Long-term episodic memory   | 跨 session（永久）        | DB / vector store / file system                                      | 「上週 alice 問過 X」「上個 sprint 解過 Y bug」               |
| Long-term semantic memory   | 跨 session（永久）        | DB / vector store / KG                                               | 「user 偏好 markdown 輸出」「專案用 React 18」「Python 3.11」 |
| Long-term procedural memory | 跨 session（永久）        | Skill registry / playbook                                            | 「跑測試前先 npm install」「commit 前要 lint」                |

跟其他相關概念的關係：

| 概念                                                   | 跟 agent memory 的關係                                         |
| ------------------------------------------------------ | -------------------------------------------------------------- |
| [RAG](/llm/knowledge-cards/rag/)                       | Long-term semantic memory 的常見實作（vector store retrieval） |
| [Context window](/llm/knowledge-cards/context-window/) | Working memory 的物理上限                                      |
| [System prompt](/llm/knowledge-cards/system-prompt/)   | 把 semantic / procedural memory 編碼進 scaffold 的方式         |
| [Subagent](/llm/knowledge-cards/subagent/)             | 用 subagent 分隔不同 specialty 的 memory                       |

## 設計責任

讀 agent paper / 設計 / framework docs 看到「agent memory」「memory store」「mem0 / Letta」「episodic / semantic memory」就是這 framing。寫 code 場景的判讀：

1. **不是每個 agent 都需要五個層次都用**：autocomplete 只要 working memory；對話 IDE assistant 多用 working + session；長期 coding agent 才需要 long-term
2. **Long-term memory 的兩條實作路線**：(a) retrieval-on-demand（vector store + similarity search、見 [RAG](/llm/knowledge-cards/rag/)）、(b) injection-on-startup（把關鍵 memory 編進 system prompt、適合小量穩定的 procedural）
3. **失敗模式**：memory drift（舊 memory 過時但仍被 retrieve）、PII 寫入（user 不知情下被存）、context 污染（不相關 memory 被 inject 進 working）、跟 [hallucination](/llm/knowledge-cards/hallucination/) 互相 boost
4. **跟 [4.14 agent memory 章節](/llm/04-applications/agent-memory-architecture/) 的關係**：本卡是分類定義、章節是工程實務（寫入時機、retrieval 設計、失敗模式緩解）
