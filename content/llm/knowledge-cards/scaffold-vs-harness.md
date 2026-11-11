---
title: "Scaffold vs Harness"
date: 2026-05-12
description: "Coding agent 的兩個工程層次：scaffold 是建構時靜態結構、harness 是 runtime 的 tool dispatch + context management + safety"
weight: 1
tags: ["llm", "knowledge-cards", "coding-agent", "architecture"]
---

Scaffold 跟 harness 的核心概念是「**把 coding agent 拆成『建構時靜態結構』跟『runtime 動態邏輯』兩層**」。Scaffold 是建構時就決定的：[system prompt](/llm/knowledge-cards/system-prompt/) 模板、tool schema 註冊、subagent 拓樸；harness 是 runtime 動態運作：tool dispatch、context budget 管理、safety / 中斷、handoff。Claude Code、Cursor、Aider、Codex 這類 coding agent 的內部設計都遵循這個分層。

## 跟其他概念的關係

兩層的職責劃分：

```text
Scaffold（建構時、static）：
  ├── System prompt 模板（角色、約束、輸出格式）
  ├── Tool schema 註冊（read_file / write_file / run_bash 等的 spec）
  ├── Subagent 拓樸（main agent + 子 agent 的調用關係）
  ├── Skill / playbook 註冊
  └── 安全 policy（什麼可寫、什麼要 confirm）

   ↓ 編譯 / 載入

Harness（runtime、dynamic）：
  ├── Tool dispatch（接 LLM tool call、執行、回 result）
  ├── Context budget 管理（剪裁歷史、塞新內容、不超 25% 規則）
  ├── Safety / 中斷（confirm UI、permission boundary、可逆性檢查）
  ├── Error recovery（tool failed → retry / fallback / escalate）
  └── Telemetry（trace / metrics / cost）
```

跟既有概念的關係：

| 概念                                                       | 跟 scaffold / harness 的關係                                         |
| ---------------------------------------------------------- | -------------------------------------------------------------------- |
| [System prompt](/llm/knowledge-cards/system-prompt/)       | Scaffold 的核心元件、定義 agent 角色                                 |
| [Tool use](/llm/knowledge-cards/tool-use/)                 | Scaffold 註冊 tool spec、Harness 在 runtime dispatch                 |
| [Agent loop](/llm/knowledge-cards/agent-loop/)             | Harness 的核心 loop（perceive / reason / act / observe / terminate） |
| [Function calling](/llm/knowledge-cards/function-calling/) | Tool spec 的具體 protocol                                            |

## 判斷條件與後果

Scaffold 在建構時決定，harness 在 runtime 執行，所以比較兩個 coding agent 或修改一個 agent 時，差異發生在哪一層，決定了該讀或該改的是 scaffold 還是 harness：

- **比較兩個 coding agent 時**，scaffold（system prompt、tool list、subagent 結構）的差異是設計上給了模型什麼，harness（context 怎麼裁、tool 怎麼 dispatch、安全怎麼擋）的差異是 runtime 怎麼處理模型的輸出。只比 system prompt，會漏掉 context 剪裁或 error recovery 造成的行為差異。
- **修改 agent 時**，改 system prompt 或 tool schema 動的是 scaffold，改變模型每一輪看到的內容；改 tool 的執行邏輯、retry 或 permission 檢查動的是 harness，改變模型的輸出怎麼被執行。想擋住某一類危險操作而只改 system prompt 時，模型仍可能發出那個 tool call，原因是執行與攔截都發生在 harness。

本卡是定義，coding 場景的工程實務（context budget、scaffold 模式、harness pattern）在 [4.17 coding-agent harness](/llm/04-applications/coding-agent-harness/)。
