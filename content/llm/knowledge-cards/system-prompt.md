---
title: "System Prompt"
date: 2026-05-12
description: "LLM application 中由開發者預設、不直接顯示給使用者的指令層、定義模型的角色、行為規範、輸出格式"
weight: 1
tags: ["llm", "knowledge-cards", "application", "prompt-engineering"]
---

System prompt 的核心概念是「LLM application 中、由開發者預設、放在每次 conversation 最前面、不直接顯示給使用者的指令層」。常見用途包括設定模型角色（如「你是 senior Python engineer」）、規範輸出格式（如「always return JSON」）、加入 safety guideline。Chat-based LLM API（OpenAI、Anthropic 等）通常有專門的 `role: "system"` message type、由 [special tokens](/llm/knowledge-cards/special-tokens/) 標記這段訊息的邊界。

## 跟其他概念的關係

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

## 判斷條件與後果

System prompt 約束的是模型讀到的文字，它的效力取決於同一個 context 裡有沒有別的指令跟它競爭。同一個模型配上不同的 system prompt，角色、輸出格式與行為規範都跟著換，所以同一個模型在不同 LLM 應用裡表現出不同的「個性」。使用者輸入或 tool 回傳的內容帶著指令進入 context 時，模型可能照那些指令走，[prompt injection](/llm/knowledge-cards/prompt-injection/) 攻擊的目標就是讓模型不照 system prompt 走。行為出錯會造成損害的 application（模型能呼叫工具、輸出會送到外部系統）只靠 system prompt 時，一次成功的 injection 就直接變成一次有害的動作，原因是 system prompt 之後沒有任何檢查；所以這類行為在 application 層另加一層防護，例如 tool call 的權限白名單與輸出驗證。詳見 [6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)。
