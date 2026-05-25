---
title: "serena：把 LSP 包成 agent-first MCP 的 symbol-level 編輯方案"
date: 2026-05-25
draft: false
description: "serena MCP 的設計拆解：直接整合各語言 LSP、symbol-level atomic edit（replace_symbol_body / insert_after_symbol / rename）、per-session project activation、跨 session memory。重點在 LSP 路線的型別精度可信度與 per-session 沒持久化的取捨。"
tags: ["MCP", "AI協作心得", "工具評估", "Claude Code"]
---

## 這個 MCP 解什麼問題

serena 的核心定位是「**把現成 LSP 生態包成適合 agent 用的高階抽象**」。它不自建 type system、不自寫 parser，直接 spawn 各語言對應的 language server（Dart 用 `dart analysis_server`、TS 用 `tsserver`、Rust 用 `rust-analyzer` 等），把 LSP 的能力轉成 MCP tool。

設計哲學是 README 自己歸納的「agent-first tool design」：

> Involves robust high-level abstractions, distinguishing it from approaches that rely on low-level concepts like line numbers or primitive search patterns.

換言之，serena 的所有編輯都是 **symbol-level**——讓 agent 直接用 symbol 語意操作（「把 X function 的 body 整個換掉」、「在 Y class 後面插一段」、「rename Z」），跳過 line number 跟 text patch 這層 raw text 處理。對應的是 LSP 路線本來就有的 symbol 結構與 reference 追蹤。

跟 tree-sitter 路線的本質分野：tree-sitter 只給結構、不給型別；LSP 給的是「IDE 等級的真型別系統」。代價是 LSP 要每個語言裝對應 language server、執行期 spawn process、per-session 維護狀態。

## 部署形態：兩個 backend、執行期 spawn LSP

serena 提供兩個 backend：

| Backend          | 適用情境                          | 取捨                                    |
| ---------------- | --------------------------------- | --------------------------------------- |
| Language Server  | 預設、開源、跨平台                | 要對應語言的 language server 在環境內   |
| JetBrains Plugin | 已用 JetBrains IDE 的 paid 使用者 | 借用 IDE 完整能力（debug / breakpoint） |

Language Server backend 是 OSS 用戶會接觸的路線。serena 透過 LSP 抽象涵蓋 40+ 語言、實際能力依各語言 LSP 成熟度而定——Python / TypeScript / Go / Rust / Java / C# / Dart 等主流語言由 serena 內建 bootstrap 自動下載 server、冷門語言（如 Liquid / Pascal）需要使用者自己準備 server binary、無 server 的語言視同 fallback 到純文字工具。判讀訊號：跑 `activate_project` 後若 serena 沒在背景 spawn 對應 LSP、表示該語言走 fallback 路線、`find_referencing_symbols` 等型別敏感 tool 不可用。

對 Dart 而言：serena 啟動時 spawn `dart analysis_server`、跟 Flutter SDK 內附的同一隻。所以 serena 對 Dart 的能力等同 `dart analysis_server` 暴露的能力——比 tree-sitter 路線高一個量級。

## Per-session 模型與 activate_project

serena 的 LSP backend 是 **per-session** 的：

- 沒有持久化 graph DB（不像 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) / [codegraph]({{< relref "mcp-codegraph-deep-dive.md" >}}) 把結果寫進 SQLite）
- 每個 session 啟動時要 `activate_project`、spawn 對應 language server、warm up index
- Session 結束 server 也跟著 terminate，下次重來

`activate_project` 的角色是告訴 serena「這個 session 接下來要分析哪個 project root」，serena 才知道要 spawn 哪幾個 language server、index 哪個 workspace。一個 session 內可以切多次 project，但同時只 active 一個。

這個模型的取捨很清楚：

- **好處**：永遠拿到當下最新狀態（不會有 stale index 問題）、不必管 watcher / debounce
- **代價**：每次 session warm-up 有秒級至分鐘級延遲（大專案 LSP indexing 慢）、跨 session 不能重用結果

判讀訊號：第一次查詢回得慢、之後快——這是 LSP indexing warm-up。若每次查都慢、檢查 LSP 是否因記憶體不足重啟。

## Symbol-level atomic edit 的價值

serena 的 editing tool 都是 symbol-level：

- `replace_symbol_body`：取代某個 function / method / class 的 body
- `insert_after_symbol` / `insert_before_symbol`：在指定 symbol 前後插入內容
- `safe_delete_symbol`：刪除 symbol 並檢查 reference
- `rename_symbol`：rename symbol、自動更新所有 reference（LS backend 限 symbol 範圍、JetBrains backend 額外支援 file / directory 層級重命名）

對比 `Edit` tool 用「old_string / new_string」做 text-level patch：

| 操作                         | text-level edit                 | symbol-level edit                          |
| ---------------------------- | ------------------------------- | ------------------------------------------ |
| 改 method body               | 要 match 整個 body 含縮排與空白 | 指定 method 名、給新 body                  |
| Method body 內某行有特殊字元 | 容易 escape 錯、match fail      | 不受影響、agent 不處理 raw text            |
| 同名 method 在多個 class     | 要 match 含 class 名上下文      | 用 `ClassName/methodName` 路徑唯一定位     |
| Rename 跨檔                  | 要全 repo grep + 逐檔 patch     | 一次 call 完成 + LSP 保證 reference 全更新 |

實務上的價值：**type-sensitive refactor 的事故率大幅降低**。改 method 不會手抖把 indentation 改錯、rename 不會漏改 reference。代價是 symbol 路徑必須寫成包含父層的完整形式（`ClassName/methodName`）。

判讀訊號：寫 `replace_symbol_body` 後若 LSP 報 syntax error、先 `get_diagnostics_for_file` 看具體錯在哪、別直接 retry 同個 patch。

## find_referencing_symbols：LSP 路線的型別精確 caller 來源

對 Dart / Swift / Kotlin 這類 tree-sitter 工具支援薄弱的語言，`find_referencing_symbols` 是少數能拿到「**型別精確的 caller 清單**」的 MCP tool。

實測對 Dart `Money.multiplyByRate`（某商業專案、`Money` 是 extension type）：

```text
serena find_referencing_symbols → 4 個檔案、9 個 callsite
codegraph callers              → 3 個 caller symbol（漏 3 個 callsite）
cbm trace_call_path            → 0 callers（Dart 不在 hybrid resolution 名單）
```

差距來源就是型別解析：`samplePrice.multiplyByRate(...)` 這種 receiver 是 local variable 的 callsite，要知道 `samplePrice` 的型別是 `Money` 才能 dispatch 到正確 method。LSP 走 `dart analysis_server` 拿到完整型別資訊，所以這層 dispatch 是精確的。

下一步路由：對照數字與 5 個實測實驗見 [三 MCP 工作流與 Dart 實測]({{< relref "mcp-three-way-workflow-and-dart-experiment.md" >}})。

## 30+ MCP tool 的分類

serena 的 tool 數量比 cbm / codegraph 都多、覆蓋更廣的工作流：

| 類別           | Tool                                                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 檢索           | `find_symbol`、`get_symbols_overview`、`find_referencing_symbols`、`find_declaration`、`find_implementations`、`get_diagnostics_for_file` |
| 編輯（symbol） | `replace_symbol_body`、`insert_after_symbol`、`insert_before_symbol`、`safe_delete_symbol`、`rename_symbol`                               |
| 編輯（text）   | `replace_content`、`search_for_pattern`                                                                                                   |
| 檔案 / 目錄    | `list_dir`、`find_file`、`read_file`、`create_text_file`                                                                                  |
| 執行           | `execute_shell_command`                                                                                                                   |
| Memory         | `write_memory`、`read_memory`、`list_memories`、`delete_memory`、`rename_memory`、`edit_memory`                                           |
| Project        | `activate_project`、`get_current_config`、`onboarding`、`initial_instructions`                                                            |
| Debug          | （僅 JetBrains backend）breakpoint、variable inspection、expression eval                                                                  |

幾個值得單獨展開的類別：

**檢索類**是 serena 跟 LSP 黏最緊的入口——`find_symbol` / `find_declaration` / `find_implementations` 走 LSP 的 textDocument 命令、`find_referencing_symbols` 是 LSP `references` 的 wrapper。這層是 serena 不可替代的核心、所有需要型別精確的查詢都從這走。

**`get_diagnostics_for_file`** 是把 LSP 的編譯診斷直接暴露給 agent。改完 code 不必跑 build 就能知道有沒有 type error / unused import / missing await。對 type-sensitive refactor 是必備。

**Symbol-level edit vs text-level edit 的選用**：symbol-level（`replace_symbol_body` / `insert_after_symbol` / `safe_delete_symbol` / `rename_symbol`）對「有明確 symbol 邊界的修改」最穩、不會踩到 indentation 或 escape 問題；text-level（`replace_content` / `search_for_pattern`）保留給「跨 symbol 邊界、或非 code 內容」的場合（如改 markdown、config、log 字串）。判讀訊號：要動的內容能不能用「ClassName/methodName」這種 symbol path 定位？能就走 symbol-level、不能就 text-level。

**`execute_shell_command`** 是 LSP-only 工具裡的「逃生門」——LSP 本身不執行命令、但實務上 agent 需要跑 test / build / git status / 任意 CLI 工具來驗證自己的修改。這條等於把 LSP-based 工具補成「能 query 又能執行」的完整 workflow 工具。安全考量：因為它能跑任意 shell command、Claude Code 對 serena 的 trust level 要跟 Bash tool 對齊看待、不要假設它「只是讀取工具」。

**Memory system** 採用「跨 session 的 markdown 筆記檔」形式、屬於自由格式存儲。用途接近 agent 的本地長期記憶——存「這個專案的 setup 注意事項」、「上次 refactor 的決策紀錄」、「常用的 codebase pattern」。跟 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 的 `manage_adr`（結構化 ADR）走相反取向：serena 把 schema 留給使用者自定、manage_adr 給定 ADR 欄位結構。

**Project 類**（`activate_project` / `get_current_config` / `onboarding` / `initial_instructions`）是 serena 對「agent 第一次接觸新專案要先讀什麼」的明確協議。`onboarding` 讓 agent 主動 read 專案 onboarding doc、`initial_instructions` 給 agent 一份 serena 自己的使用手冊、`activate_project` 切 project root、`get_current_config` 暴露當前 session 的配置給 agent debug。這層降低盲目探索成本、是把 serena 從「LSP wrapper」抬升到「agent-first」的關鍵。

## Per-session 與持久化 graph 的搭配問題

serena 的 per-session 模型在「**單純查 caller / refactor**」工作流很合適，但對「**自然語言搜尋 / 跨 session 累積 graph context**」就不夠。

實際差距：

- 想用「金額顯示相關」這種概念性 query 找 symbol → serena 沒有 BM25 / 11-signal scoring、只有 `search_for_pattern`（regex / literal）跟 `find_symbol`（exact name match）
- 想跨 session 累積「這個 codebase 有哪些 module」的整體 inventory → serena 每次重 index、沒有持久化的 graph 可查
- 想做跨 service HTTP_CALLS 鏈接 → serena 沒有這層

判讀訊號：搜尋需求若是「我知道某個 symbol 的精確名稱、要找它的 references」就用 serena；若是「我不知道精確名稱、用概念找」要配合 cbm。

## 安裝行為

serena 在 Claude Code 是 plugin 形式：在 plugin marketplace enable 即可，不需要單獨 `npm i`。Plugin 啟動時 serena 會 spawn LSP，第一次 activate 某個 project 時 indexing 完成才能跑 query。

跟 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) / [codegraph]({{< relref "mcp-codegraph-deep-dive.md" >}}) 的差異：

- **不寫 PreToolUse hook**、不攔截既有 grep / glob 行為
- **不在 `~/.claude.json` 直接加 mcpServers**（plugin 機制管理）
- **每個 project 要顯式 activate**——第一次 session 進新 project 時 agent 要主動跑 `activate_project` 或在 plugin config 預設 project root

要注意的點：

**Language server 缺失時的失敗模式**。對冷門語言（如 Liquid / Pascal）若環境沒裝 language server、`activate_project` 會回失敗但不會主動裝。需要使用者自己準備 server binary。Dart / TS / Python / Go / Rust 等主流語言 serena 會 bootstrap 處理。

**JetBrains backend 是付費**。OSS 用戶只能用 LS backend、得不到 debug 整合那組能力。

## 適用 / 不適用情境的判讀

**適用情境**：

- 主力語言有成熟 LSP（Dart / TS / Python / Go / Rust / Java / C# 等）
- 型別敏感的 refactor 場景（rename / extract method / 跨檔 reference 更新）
- 要編譯 diagnostic 即時反饋（取代 build / test cycle 的部分功能）
- Symbol-level atomic edit 的可靠性比 graph 持久化重要

**不適用情境**：

- 主力語言 LSP 不成熟或不存在（serena 沒得借力）
- 需要概念性 / 自然語言搜尋（用 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 的 11-signal scoring）
- 需要跨 session 累積的 graph context（serena per-session、不持久化）
- 需要跨 service HTTP/RPC 鏈接（serena 沒這層）

**搭配建議**：serena 是「**型別精確 + 編輯出口**」的角色。在它擅長的語言上做 caller 追蹤 / refactor、把概念性搜尋讓給 cbm、把日常結構查詢讓給 codegraph。三者怎麼分工見 [三 MCP 工作流與 Dart 實測]({{< relref "mcp-three-way-workflow-and-dart-experiment.md" >}})。

## 結論

serena 的核心價值在三件事：**直接借 LSP 拿型別精確的 reference**、**symbol-level atomic edit 的可靠性**、**編譯 diagnostic 即時整合**。前兩件對任何成熟 LSP 語言都成立，第三件對「改完 code 想立刻驗 type error」的工作流特別重要。

它的能力上限取決於「**目標語言 LSP 成熟度**」——LSP 強的語言上 serena 是強工具、LSP 弱的語言上 serena 也跟著弱。它的能力下限取決於「**持久化 graph 與自然語言搜尋**」這兩層空白——這兩層要靠別的 MCP 補齊。
