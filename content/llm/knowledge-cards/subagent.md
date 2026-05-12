---
title: "Subagent"
date: 2026-05-12
description: "Coding agent 中把特定責任拆給專門子 agent 的設計模式、各 subagent 有獨立 context、由 main agent 透過 handoff 調度"
weight: 1
tags: ["llm", "knowledge-cards", "coding-agent", "agent-architecture"]
---

Subagent 的核心概念是「**把 coding agent 切成多個專責子 agent、每個有獨立 [context window](/llm/knowledge-cards/context-window/) 跟 system prompt、由 main agent 透過 handoff 機制調度**」。代表設計：Claude Code 的 Task agent、OpenAI Agents SDK 的 handoff、Anthropic multi-agent research。是「context budget 不夠 + 任務跨多個 specialty」場景的工程選擇。

## 概念位置

Single agent vs subagent 架構的對比：

```text
Single agent（無 subagent）：
  Main agent context：
    [system prompt + tool schema + 跨所有 specialty 的 history + 所有 file content]
    ↓ 容易爆 context、specialty 互相干擾

Subagent 架構：
  Main agent context（路由 + 高階決策）：
    [main system prompt + handoff tool spec + 高階任務歷史]
       ↓ 路由到 subagent

  Subagent A context（如「跑測試」專家）：
    [test-runner system prompt + 測試 tool + 測試相關 file]

  Subagent B context（如「寫 docs」專家）：
    [docs system prompt + 寫 docs tool + 相關 docs 檔案]
```

主要好處：

1. **Context budget 隔離**：每個 subagent 只看自己 specialty 相關 context、不被別的 specialty 污染
2. **System prompt 專門化**：寫 docs 的 system prompt 跟跑測試的 system prompt 不同、各自最佳化
3. **Specialty 路由**：main agent 只決定「這個任務該交給哪個 subagent」、不直接做 specialty 工作

主要挑戰：

1. **Handoff 設計**：main agent 要怎麼選 subagent、怎麼傳 context、怎麼接 result
2. **跨 subagent 共享狀態**：codebase 知識、history、要避免重複 work
3. **失敗模式**：subagent 之間互相 deadlock、main agent 失去 high-level view、subagent 邊界劃錯

## 設計責任

讀 multi-agent / subagent paper / coding agent docs 看到「subagent」「handoff」「Task tool」「specialist agent」就是這 framing。寫 code 場景的判讀：

1. **何時用 subagent**：單一 agent context 不夠用、specialty 邊界清楚（如 search / coding / testing / documentation）、main agent 的 system prompt 已太長
2. **何時不用**：任務簡單、specialty 邊界模糊（強行拆會增加 handoff overhead）、本地小模型（handoff 機制對小模型不穩）
3. **跟 [agent loop](/llm/knowledge-cards/agent-loop/) 的關係**：每個 subagent 內部仍是 agent loop（perceive / reason / act / observe / terminate）、只是 loop 範圍縮窄
4. **跟 [scaffold vs harness](/llm/knowledge-cards/scaffold-vs-harness/) 的關係**：subagent 註冊在 scaffold（建構時）、handoff 在 harness（runtime）執行
