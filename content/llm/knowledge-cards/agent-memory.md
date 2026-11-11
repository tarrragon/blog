---
title: "Agent Memory"
date: 2026-05-12
description: "Agent 在 context window 之外管理長期狀態的設計、五個層次：working / short-term / long-term episodic / semantic / procedural"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "memory"]
---

Agent memory 的核心概念是「**agent 在 [context window](/llm/knowledge-cards/context-window/) 之外管理長期狀態的設計**」、把使用者偏好、過去任務、知識、操作流程等持久化、跨 session 重用。借鑒人類認知科學的五個層次：working memory（context 本身）、short-term（session scratchpad）、long-term episodic（過去事件）、long-term semantic（事實 / 知識）、long-term procedural（流程 / 技能）。

## 跟其他概念的關係

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

## 判斷條件與後果

讀 agent paper、設計文件或 framework docs 看到「agent memory」「memory store」「mem0 / Letta」「episodic / semantic memory」，指的就是這個分類。一個 agent 需要哪幾層，看任務的狀態要保留多久：autocomplete 每次請求互不相關，working memory 就夠；對話式 IDE assistant 的狀態在一個 session 內累積，用到 working 與 session；長期 coding agent 要沿用上週的決定與專案慣例，才需要 long-term。多加的每一層都帶來寫入、retrieval 與過期管理的工作，任務用不到那一層時，這些工作只增加成本與出錯的位置。

Long-term memory 的兩種實作差在 memory 什麼時候進 context。retrieval-on-demand（vector store + similarity search，見 [RAG](/llm/knowledge-cards/rag/)）每次只取回相關的片段，量大、每次只用到一小部分的 memory 適合它；injection-on-startup 在啟動時把 memory 編進 system prompt，佔掉的 context 隨 memory 量成長，所以只適合小量、穩定的 procedural memory。

長期存放的 memory 有四種失效形態，每一種都讓 agent 依據錯的狀態行動：memory drift（舊 memory 過時而仍被 retrieve，agent 照過期的事實做事）、PII 寫入（使用者不知情時個資被持久化）、context 污染（不相關的 memory 被 inject 進 working memory，佔掉 context 並把模型導向無關的內容）、跟 [hallucination](/llm/knowledge-cards/hallucination/) 互相放大（模型的錯誤輸出被寫成 memory，之後被當成事實 retrieve 回來）。寫入時機、retrieval 設計與這幾種失效的緩解在 [4.19 agent memory 章節](/llm/04-applications/agent-memory-architecture/)，本卡只做分類定義。
