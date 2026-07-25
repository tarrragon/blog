---
title: "System Prompt"
date: 2026-05-12
description: "LLM application 中由開發者預設、不直接顯示給使用者的指令層、定義模型的角色、行為規範、輸出格式"
weight: 1
tags: ["llm", "knowledge-cards", "application", "prompt-engineering"]
---

System prompt 的核心概念是「LLM application 中、由開發者預設、放在每次 conversation 最前面、不直接顯示給使用者的指令層」。常見用途包括設定模型角色（如「你是 senior Python engineer」）、規範輸出格式（如「always return JSON」）、加入 safety guideline。Chat-based LLM API（OpenAI、Anthropic 等）通常有專門的 `role: "system"` message type、由 [special tokens](/llm/knowledge-cards/special-tokens/) 標記這段訊息的邊界。

## 概念位置

LLM API call 的訊息結構：

```text
messages = [
  {role: "system", content: "你是專業 code reviewer..."},  ← system prompt
  {role: "user",   content: "請 review 這段 code: ..."},
  {role: "assistant", content: "..."},  ← 模型回答
  {role: "user",   content: "..."},     ← 後續對話
  ...
]
```

System prompt 在 application 設計中的角色：

| 用途                                           | 例子                                                  |
| ---------------------------------------------- | ----------------------------------------------------- |
| 角色定義                                       | "你是 senior Python engineer、專長 async / typing"    |
| 輸出格式約束                                   | "always return JSON with keys: title, body, tags"     |
| 行為規範                                       | "若不確定、明確說『我不知道』、不要編造"              |
| [工具使用](/llm/knowledge-cards/tool-use/)指引 | "When user asks about weather, call get_weather tool" |
| 安全約束                                       | "Do not generate executable shell commands"           |
| 上下文注入                                     | "Current date: 2026-05-12; User language: zh-TW"      |

> **事實查核註**：不同 LLM vendor 對 system prompt 的處理機制不同（如部分模型把 system 跟 user 視為相同優先級、部分模型有特殊訓練讓 system 較高優先）、具體行為以該模型的[官方文件](https://platform.openai.com/docs/api-reference/chat)為準。

## 設計責任

理解 system prompt 後可以解釋兩個現象：為什麼同一個模型在不同 LLM 應用中的「個性」差很多（system prompt 不同）、為什麼 [prompt injection](/llm/knowledge-cards/prompt-injection/) 的主要目標是繞過 system prompt 的約束（攻擊者想讓模型不照原本指令走）。

實務上、設計 LLM application 時、system prompt 是行為約束的第一層、但不是唯一防線（容易被 injection 繞過）；critical 行為應該在 application 層（如 tool call 的權限白名單、輸出驗證）加第二層防護。詳見 [6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)。
