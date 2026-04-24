---
title: "LSP 優先開發策略方法論 - 語意化程式碼操作的最佳實踐"
date: 2026-03-04
draft: false
description: "優先使用 Language Server Protocol 進行程式碼操作，取代傳統文字搜尋和手動編輯，提升開發精確度"
tags: ["LSP", "開發策略", "語意搜尋", "程式碼操作", "開發工具"]
---

有一次我們在追蹤一個介面的所有實作位置，習慣性地用 `grep -r "implements SomeInterface"` 搜整個專案。等了大約 45 秒，拿到一堆夾雜字串字面值、註解、測試假資料的結果，還需要手動過濾。

後來改用 LSP 的 `goToImplementation`，不到 50 毫秒，精確乾淨。

那個體驗讓我們開始想：我們平時到底在做什麼？

<!--more-->

## 文字搜尋的根本問題

`grep` 不理解語意，只做字串匹配。問題有三個：

結果包含噪音。`BookRepository` 這個名稱會出現在程式碼、字串字面值、文件、測試 mock、JSON 設定檔——grep 全部回傳，你自己過濾。

結果缺乏結構。你拿到的是一行行文字，不是符號的定義位置、型別資訊或呼叫關係，需要再做二次處理。

它很慢。大型 Codebase 裡全域搜尋很容易超過幾十秒。

LSP 真正理解程式碼的語義結構。問「這個函式在哪裡被呼叫」，它給出的是精確的呼叫位置，不是字串匹配的猜測結果。

## 核心原則：LSP 能做的，不要用 grep

每次操作程式碼之前，先問自己：**這是語意操作，還是文字操作？**

語意操作包括：找定義、追引用、理解型別、分析呼叫鏈。這些用 LSP 或對應的語言 MCP 工具。文字搜尋是最後備援，不是第一選項。

決策流程很直接：

- 分析誰呼叫了某個函式 → `callHierarchy` / `incomingCalls`
- 找介面的所有實作 → `goToImplementation`
- 追蹤符號定義來源 → `goToDefinition` 或 `resolve_workspace_symbol`
- 查型別簽名和文件 → `hover` / `mcp__dart__hover`
- 重構前影響分析 → `findReferences`

只有 LSP 工具無法使用，或需要搜尋非程式碼內容（設定檔、文件、log），才退回 Grep 或 Glob。

## 效能差距有多大

我們實際測量過：

- 查找引用：LSP 約 50ms，grep 約 45 秒（900 倍差距）
- 跳轉到定義：LSP 約 10ms，文字搜尋約 5 秒
- 符號概覽：LSP 約 20ms，手動解析約 10 秒

用 AI 工具輔助開發時還有另一個面向：token 消耗。LSP 的 `findReferences` 輸出是結構化位置列表，大約 100 到 500 個 token。同一個查詢用 grep，可能消耗 3000 到 10000 個 token。

速度、成本、結果的清晰度，全都差這麼多。

## 工具對應

以 Dart/Flutter 環境為例：

| 需求             | 工具                                  |
| ---------------- | ------------------------------------- |
| 懸停查看型別     | `mcp__dart__hover`                    |
| 工作區尋找符號   | `mcp__dart__resolve_workspace_symbol` |
| 查看函式簽名     | `mcp__dart__signature_help`           |
| 整個專案靜態分析 | `mcp__dart__analyze_files`            |

Dart MCP 無法使用時，退到 Serena MCP：`get_symbols_overview`、`find_symbol`、`find_referencing_symbols`。Serena 輸出更豐富，但消耗更多 token。

Grep 和 Glob 是最後備援，用在搜尋非程式碼內容，或完全沒有 LSP/MCP 的環境。

## 一個實踐範例

重構 `BookMetadataService`，想知道修改 `fetchMetadata` 方法會影響哪些地方。

文字搜尋：`grep -r "fetchMetadata" lib/`，結果包含真實呼叫、字串常數、測試 stub，手動過濾後才能確認影響範圍，大約一兩分鐘。

LSP：對 `fetchMetadata` 的定義位置執行 `findReferences`，50 毫秒內拿到所有真實呼叫位置，每個結果附帶精確檔案路徑和行號，沒有噪音。

不只是快，更重要的是對結果的信心不同。文字搜尋的結果需要懷疑，LSP 的結果可以直接信任。

## 落地這個習慣

每次伸手去打 `grep` 之前，先停一秒問自己：

- 追蹤符號定義 → 有沒有先用定義跳轉？
- 做重構 → 有沒有先用 `findReferences` 分析影響範圍？
- 查型別或文件 → 有沒有用 `hover`？
- 分析呼叫關係 → 有沒有用 `callHierarchy`？

這不是流程負擔，就是一個習慣檢查點。

## 結論

文字搜尋給我們的是「字串在哪裡出現」，LSP 給我們的是「這個符號語義上與什麼相關」。

這個差異在小專案不明顯。但在中大型 Codebase 裡，它決定了重構的安全性，也決定了每天工作有多流暢。

讓語言伺服器做它擅長的事，認知資源才能留給真正需要思考的問題。
