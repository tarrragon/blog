---
title: "LSP 優先：語意操作不用文字搜尋"
slug: "lsp-first-development-methodology"
date: 2026-03-04
draft: false
description: "查一個符號的引用要人工過濾字串字面值與註解、或重構前抓不準影響範圍時，用來判斷哪些操作該交給 LSP、哪些才輪到文字搜尋"
tags: ["LSP", "開發策略", "語意搜尋", "程式碼操作", "開發工具"]
---

追蹤一個介面的所有實作位置時，`grep -r "implements SomeInterface"` 與 LSP 的 `goToImplementation` 回答的是兩個不同的問題：前者回答「這串文字出現在哪」，後者回答「哪些型別實作了這個介面」。第一個問題的答案裡混著字串字面值、註解與測試假資料，要人工過濾；第二個問題的答案可以直接使用。

多數程式碼操作問的是第二種問題，而習慣打的是第一種指令。

<!--more-->

## 文字搜尋的根本問題

`grep` 不理解語意，只做字串匹配。問題有三個：

結果包含噪音。`BookRepository` 這個名稱會出現在程式碼、字串字面值、文件、測試 mock、JSON 設定檔——grep 全部回傳，過濾的工作留給呼叫它的人。

結果缺乏結構。拿到的是一行行文字，不是符號的定義位置、型別資訊或呼叫關係，還要再做一次解析。

它很慢。大型 Codebase 裡全域搜尋很容易超過幾十秒。

LSP 真正理解程式碼的語義結構。問「這個函式在哪裡被呼叫」，它給出的是精確的呼叫位置，不是字串匹配的猜測結果。

## 核心原則：LSP 能做的，不要用 grep

每次操作程式碼之前先分類：**這是語意操作，還是文字操作。**

語意操作包括：找定義、追引用、理解型別、分析呼叫鏈。這些用 LSP 或對應的語言 MCP 工具。文字搜尋是最後備援，不是第一選項。

決策流程很直接：

- 分析誰呼叫了某個函式 → `callHierarchy` / `incomingCalls`
- 找介面的所有實作 → `goToImplementation`
- 追蹤符號定義來源 → `goToDefinition` 或 `resolve_workspace_symbol`
- 查型別簽名和文件 → `hover` / `mcp__dart__hover`
- 重構前影響分析 → `findReferences`

只有 LSP 工具無法使用，或需要搜尋非程式碼內容（設定檔、文件、log），才退回 Grep 或 Glob。

## 差距來自兩種做法的複雜度

LSP 的查找走的是語言伺服器已經建好的符號索引，成本接近一次查表；grep 走的是全檔案掃描，成本隨 codebase 的大小線性成長。兩者的量級差在小專案上看不出來，在中大型 codebase 上是毫秒對上數秒到數十秒。

用 AI 工具輔助開發時還有第二個面向：token 消耗。LSP 的 `findReferences` 輸出是結構化的位置列表，長度由引用數決定；同一個查詢用 grep，輸出裡包含所有命中行的內容與噪音，兩者送進 context 的量不同一個量級。

速度、成本與結果的可信度三件事同向——它們都來自「查的是符號還是字串」這個差別。

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

## 落地成一個檢查點

打 `grep` 之前先過一次這四個問題：

- 追蹤符號定義 → 有沒有先用定義跳轉？
- 做重構 → 有沒有先用 `findReferences` 分析影響範圍？
- 查型別或文件 → 有沒有用 `hover`？
- 分析呼叫關係 → 有沒有用 `callHierarchy`？

四個問題都指向同一件事：這次要找的是符號還是字串。

文字搜尋給的是「字串在哪裡出現」，LSP 給的是「這個符號在語意上跟什麼相關」。重構前的影響範圍分析要用的是後者——前者的結果需要被懷疑，而懷疑的工作由人做。

LSP 路線與其他 code intelligence 路線（索引式知識圖譜、語意搜尋）的取捨，走 [三 MCP 工作流與 Dart 實測](../mcp-three-way-workflow-and-dart-experiment/)。
