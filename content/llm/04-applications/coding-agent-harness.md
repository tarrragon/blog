---
title: "4.12 Coding agent harness：scaffold / context engineering / subagent"
date: 2026-05-12
description: "Coding agent 的內部設計：scaffold vs harness 分層、context budget 25% 規則、subagent 拓樸、跟 Claude Code / Cursor / Aider 的 mapping"
tags: ["llm", "applications", "coding-agent", "harness", "scaffold", "context-engineering"]
weight: 12
---

教材整體 framing 是「LLM 寫 code 工程實務」、模組四前面 11 章寫的是**通用 LLM 應用層原理**（RAG / tool use / agent / VLM 等）。本章補上「coding agent 怎麼設計」這層 — 為什麼 Claude Code / Cursor / Aider / Codex 這類工具長那樣、scaffold 跟 harness 怎麼分、context budget 怎麼配。本章把這些設計取捨從特定產品抽出來、寫成跨工具世代不變的工程原理。

## 本章目標

讀完本章後、你應該能：

1. 用 [scaffold vs harness](/llm/knowledge-cards/scaffold-vs-harness/) 分層拆解任何 coding agent。
2. 對自己工作流計算 [context budget](/llm/knowledge-cards/context-budget/)、看到 budget 超標訊號時知道怎麼修。
3. 判斷何時值得拆 [subagent](/llm/knowledge-cards/subagent/)、何時用 single agent。
4. 看 Claude Code / Cursor / Aider 等 coding agent 的設計差異、能對應到本章 framing。

## Scaffold vs Harness 分層

Coding agent 的內部結構分兩層：

```text
Scaffold（建構時靜態結構、編譯 / 載入時就決定）：
  - System prompt 模板（agent 角色、輸出約束、錯誤處理 policy）
  - Tool schema 註冊（read_file / write_file / run_bash / web_fetch 等 spec）
  - Subagent 拓樸（main agent + 子 agent 關係）
  - Skill / playbook 註冊（特定任務的 known recipe）
  - 安全 policy（permission boundary、要 confirm 的動作清單）

Harness（runtime 動態運作、每個 query / loop iteration 跑）：
  - Tool dispatch（接 LLM tool call、call function、回 result）
  - Context budget 管理（剪裁 history、塞新內容、避免超 budget）
  - Safety / 中斷（confirm UI、permission check、可逆性判斷）
  - Error recovery（tool failed → retry / fallback / escalate）
  - Telemetry（trace / metrics / cost、見 [4.15 OTel tracing](/llm/04-applications/llm-tracing-and-observability/)）
```

不同 coding agent 的 scaffold / harness 比較：

| 工具         | Scaffold 特點                                          | Harness 特點                                        |
| ------------ | ------------------------------------------------------ | --------------------------------------------------- |
| Claude Code  | Skill registry、subagent system、structured permission | 強 context budget 管理、explicit handoff、trace     |
| Cursor       | Composer + chat + tab、tool list 較簡                  | IDE-integrated、tool dispatch 在 client + server 切 |
| Aider        | 跟 git 緊密、edit-format spec                          | Repl-style、自動 commit、線性 loop                  |
| Codex CLI    | 跟 OpenAI assistants API 對齊                          | Stream-based、tool call 即時執行                    |
| Continue.dev | Plugin-style、provider 抽象                            | 較輕量、tool dispatch 在 plugin host                |

關鍵理解：所有 coding agent 都遵循這個 framing、差異在「scaffold 多複雜」「harness 多強」、不是有沒有這兩層。

## Context Budget 工程實務

[Context budget](/llm/knowledge-cards/context-budget/) 是 coding agent harness 的核心責任。實務拆分（以 200K context 模型為例）：

| 元件                                  | 預算 % | 內容                                          |
| ------------------------------------- | ------ | --------------------------------------------- |
| System prompt + tool schema           | 5-15%  | Agent 角色、輸出約束、tool spec               |
| Conversation history                  | 10-30% | 過去回合的 user query + assistant + tool call |
| Current task file context             | 30-50% | 開啟檔案、grep 結果、@-mention                |
| Tool result（current step）           | 0-20%  | file read / bash output / test result         |
| Reasoning trace（若 reasoning model） | 0-15%  | `<think>...</think>` 段                       |
| Margin / safety buffer                | 10-20% | Generation 階段不被 context limit 截斷        |

關鍵 25% 規則：**Scaffold 部分（system prompt + tool schema + conversation history）合計不超過 25% context**。剩 75% 給「當下任務」、避免 [lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 把指令吃掉。

超標訊號跟對應策略：

| 超標訊號                        | 緩解策略                                                                    |
| ------------------------------- | --------------------------------------------------------------------------- |
| 模型開始忽略 system prompt 指令 | 用 [prompt cache](/llm/knowledge-cards/prompt-cache/) 把 system prompt 攤平 |
| Tool call 重複過去步驟          | History 過長、需要 summarize 舊回合                                         |
| 回答跟前文重複 / 矛盾           | 中段 lost-in-the-middle、reorder 重要內容到末尾                             |
| Generation 被截斷               | Margin 不夠、降低 file content 或 history                                   |
| Reasoning trace 截斷            | 換更長 context 模型、或拆任務                                               |

實作概要：

```text
每個 turn 開始時、harness 算：
  available_input = context_window - reserve_margin
  used = len(system + tool_schema + history + new_content)

  if used > available_input × 0.75：
    觸發 summarize：把舊 history 壓縮成 1 段摘要
    或觸發 dispatch：交給 subagent 處理特定子任務、回主 agent 時只帶 summary
```

## Subagent 設計

[Subagent](/llm/knowledge-cards/subagent/) 把單一大 agent 拆成多個專責子 agent、各自有獨立 context。何時用：

| 情境                                                    | 用 subagent？              |
| ------------------------------------------------------- | -------------------------- |
| Single agent context 撐不住任務複雜度                   | 是                         |
| Specialty 邊界清楚（test / docs / refactor 各自有專家） | 是                         |
| 任務簡單（autocomplete、單行修改）                      | 否                         |
| Specialty 邊界模糊（強行拆增加 handoff overhead）       | 否                         |
| 本地小模型（< 14B）                                     | 否（handoff 對小模型不穩） |

主流 subagent 模式：

### 1. Search subagent

**Specialty**：在大 codebase 找相關片段、不污染 main agent context
**Tool**：grep / find / semantic search
**Output**：top-K 相關段落 + 摘要、main agent 不需要看完整 grep 結果

### 2. Test runner subagent

**Specialty**：跑測試、解讀失敗、提出 fix 建議
**Tool**：run_bash（pytest / jest 等）+ read failed test
**Output**：「測試結果 + 失敗根因 + 建議 fix」、不是完整 test log

### 3. Docs writer subagent

**Specialty**：寫 docstring / README / commit message
**System prompt**：強化「寫作風格、語言、長度」、跟 main coding agent 完全不同的 system prompt
**Output**：寫好的 docs 文字

### 4. Code review subagent

**Specialty**：對 PR diff 做 review、檢查 style / bug / security
**Tool**：git diff / grep
**Output**：comments 列表

### 5. Long-running task subagent

**Specialty**：跑可能持續數分鐘的任務（如 large-scale refactor）、main agent 不阻塞
**Tool**：背景 process management
**Output**：階段性進度回報 + 最終結果

主 agent 對 subagent 的 handoff 設計：

```text
main agent 收到任務
   ↓ 判斷 specialty
   ↓ 用 dispatch_subagent tool 呼叫
   tool spec：{name, task_brief, expected_output_format}
   ↓
Subagent 在自己 context 內跑完
   ↓ 回 summary（不是完整 trace）
   ↓
main agent 拿到 summary、繼續推進
```

## 跟既有概念的關係

| 既有章節                                                                | 跟本章的關係                                                   |
| ----------------------------------------------------------------------- | -------------------------------------------------------------- |
| [4.1 Tool use](/llm/04-applications/tool-use-principles/)               | Tool spec 是 scaffold 的核心、tool dispatch 在 harness         |
| [4.2 Agent 架構](/llm/04-applications/agent-architecture/)              | Agent loop 是 harness 的內部執行迴圈                           |
| [4.3 應用層協議](/llm/04-applications/application-protocols/)           | Function calling / MCP 是 tool 跟 subagent 之間的協議          |
| [4.7 Long context](/llm/04-applications/long-context-engineering/)      | Context budget 是 long context 的工程實務面                    |
| [4.13 Prompt caching](/llm/04-applications/prompt-caching-engineering/) | 是 scaffold 部分（system + tool schema）的 cost / latency 優化 |
| [4.14 Agent memory](/llm/04-applications/agent-memory-architecture/)    | History 跟 long-term memory 是 harness 跟 storage 的界面       |

## 跟具體 coding agent 的 mapping

讀者實際用 / 想客製某個 coding agent 時、用本章的 framing 拆解：

### Claude Code

**Scaffold**：CLAUDE.md（system prompt 入口）、Skills registry、SubagentTypes、tool schema
**Harness**：context budget management、Task tool（dispatch subagent）、permission system、trace
**特色**：完整 scaffold-harness 分層、強 subagent system、explicit context budget

### Cursor

**Scaffold**：System prompt 較固定、tool list 較簡、Composer mode 是 scaffold variant
**Harness**：IDE 整合度高、tool dispatch 跨 client / server、streaming response
**特色**：產品優化重於可客製、scaffold 半開放

### Aider

**Scaffold**：edit-format（diff / udiff / whole）+ git integration、tool 較少（read / edit / run）
**Harness**：repl-style loop、自動 commit、線性對話
**特色**：CLI-first、scaffold 簡單、harness 圍繞 git 設計

### Continue.dev（搭本地 LLM）

**Scaffold**：Provider-agnostic、tool list 由 plugin 註冊
**Harness**：較輕量、tool dispatch 在 VS Code extension host
**特色**：適合本地 LLM、scaffold / harness 都相對開放

## 失敗模式跟緩解

Coding agent 常見失敗：

| 失敗                         | 根因                                 | 緩解                                                                                                                             |
| ---------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| Context 用爆、模型失憶       | Budget 設計不當                      | 25% 規則、prompt cache、subagent 分擔                                                                                            |
| Tool call infinite loop      | Harness 沒設 step 上限或 cost cap    | 加 max_steps / max_cost、定期讓 user check                                                                                       |
| Subagent 答錯仍被 main 採用  | Main agent 沒 verify subagent output | 加 verification step、let main 看 subagent trace                                                                                 |
| 修改檔案後 test 沒跑         | Scaffold 沒強制「先 test 後 commit」 | System prompt 加 explicit checklist、harness 加 hook                                                                             |
| Reasoning model 配短 context | Reasoning trace 擠壓任務 context     | 配 64K+ context、或拆任務                                                                                                        |
| Permission boundary 不夠細   | Scaffold 安全 policy 太寬            | 副作用類 tool 拆細、加 confirm UI（見 [hands-on permission-boundary](/llm/01-local-llm-services/hands-on/permission-boundary/)） |

## 本地小模型跑 coding agent 的限制

本地 < 14B 模型跑完整 coding agent 通常不穩、根因（跟 [3.8 reasoning-models](/llm/03-theoretical-foundations/reasoning-models/) / [4.2 agent-architecture](/llm/04-applications/agent-architecture/) 已述）：

1. **Tool use 不穩**：小模型 function calling 訓練不足、tool call 格式錯誤率高
2. **Long context 退化**：< 14B 模型 effective context 通常 < 16K、coding agent 場景容易撞 budget
3. **Reasoning 弱**：multi-step planning、failure recovery 都需要 reasoning 能力
4. **Subagent handoff 失敗**：小模型對「該 handoff 給誰」的判斷不穩

實務組合：

- **Autocomplete + 簡單 chat**：本地 7B-14B coder（Qwen3-Coder / Gemma 4 coder）可勝任
- **完整 coding agent**：30B+ 本地模型或雲端旗艦
- **混用**：本地小模型當 autocomplete + 雲端旗艦當 agent

## 何時過時 / 何時不過時

**不會過時的部分**：

- Scaffold vs harness 分層 framing
- Context budget 配額概念跟 25% 規則
- Subagent 設計原則跟 handoff 機制
- 失敗模式分類（context 爆、infinite loop、permission 邊界）
- 本地小模型限制

**會變的部分**：

- 具體 coding agent（Claude Code / Cursor / Aider 等持續演化）
- Subagent registry 標準化（目前各家不同）
- Tool schema 標準化（MCP 是其中一條路）
- 本地小模型的 agent 能力（會逐步追上）

## 小結

Coding agent = scaffold（建構時靜態結構：system prompt / tool schema / subagent 拓樸）+ harness（runtime 動態運作：dispatch / budget / safety / recovery）。Context budget 25% 規則是核心工程實務、超標訊號要立刻處理。Subagent 是 budget 不夠 + specialty 邊界清楚時的合理選擇、不是萬靈丹。具體 coding agent（Claude Code / Cursor / Aider / Continue.dev）都遵循這 framing、差異在 scaffold 多複雜跟 harness 多強。

下一章：[4.13 Prompt caching 工程實務](/llm/04-applications/prompt-caching-engineering/)、看 scaffold 部分的 cost / latency 優化。
