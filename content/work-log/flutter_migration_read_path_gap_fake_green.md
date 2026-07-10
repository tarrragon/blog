---
title: "遷移計畫有寫入、有消費、缺讀出 — read-path 缺口與 fixture 假綠"
date: 2026-07-10
draft: false
description: "資料模型遷移的通路要三段齊：寫入 backfill、讀取路徑、消費端 API。缺讀出那段時，新 API 拿到的永遠是空集合——而消費端測試的 fixture 自己建物件、不走真實讀取路徑，測試全綠掩蓋 runtime 靜默失效。依賴圖只列「誰先做」不列語意前提時，dashboard 的 ready 是假訊號。"
tags: ["flutter", "dart", "migration", "testing", "planning", "repository", "sqlite"]
---

> **觸發場景**：Book entity 換成 tag-based 結構後（Deprecated Getter Facade 那次），接下來要派發消費端遷移的 ticket——把 `book.author` 改成 `book.getPrimaryTag("author")`。派發前的設計一致性檢查攔下了它：這個改動上線後，enrichment、export、CSV 全部會靜默失效
> **疑問來源**：facade 遷移做完了、資料 backfill 的 ticket 也排了，消費端遷移為什麼還是危險的？缺了什麼？
> **整理目的**：記下資料遷移的「三段通路」檢查、fixture 假綠的機制、以及依賴圖作為推導訊號的失效方式
> **本文邊界**：素材是該專案 v0.32 的分析 ticket（含獨立重驗的證據鏈）；被攔下的事故沒有真的發生——這是一次派發前攔截的記錄

---

## 缺口：新 API 的資料從哪來？

檢查的起點是一個樸素的問題：消費端改用 `getPrimaryTag("author")` 之後，這個方法讀的 `bookTags` 集合、內容從哪來？grep 的答案是**不從任何地方來**——repository 的 `_mapToBook` 建構 Book 時完全沒提 `bookTags`，欄位恆為預設 `const []`。從 SQLite 載入的每一本書，tag API 都回空。

而計畫裡確實有兩張看起來相關的 ticket，逐一確認 scope 後都不覆蓋這個缺口：

| Ticket   | Scope                                    | 覆蓋 bookTags 注入？   |
| -------- | ---------------------------------------- | ---------------------- |
| W1-003   | DB migration：把舊欄位資料寫入 tag 表    | 否——只有寫入方向       |
| W3-001   | 重寫 search 的 SQL、JOIN tag 表          | 部分——只有搜尋查詢路徑 |
| **缺口** | 重寫 `_mapToBook`、一般讀取路徑填充 tags | **無人認領**           |

資料模型遷移的通路有三段：**寫入**（backfill 讓新結構有資料）、**讀出**（讀取路徑把新結構載進物件）、**消費**（呼叫端改用新 API）。這個計畫排了第一段跟第三段、第二段整段缺席——不是排錯順序、是**沒有任何 ticket 認領它**。缺口安靜的原因跟[持久層靜默丟欄位](/work-log/flutter_feature_complete_never_persisted/)同構：每張存在的 ticket 都會被檢視、不存在的 ticket 沒有形狀可供檢視。

## 假綠機制：fixture 不走真實資料通路

更危險的是這個缺口**測試抓不到**。消費端的 unit test fixture 自己 `Book(...)` 建物件——遷移後 fixture 跟著改、建的時候直接帶上 `bookTags`，於是 `getPrimaryTag` 在測試裡有資料、斷言全過。真實環境的 Book 從 SQLite 經 `_mapToBook` 載入、`bookTags` 恆空——**測試世界跟真實世界走不同的資料通路**，測試通過證明的只是「如果資料有進來、邏輯是對的」，而資料沒進來。

這是假綠家族裡最結構性的一種：不是 mock 遮蔽、不是斷言過時，是 fixture 的建構方式繞過了真實系統的組裝路徑。守住它的測試必須走完整通路——寫進 SQLite、經 repository 讀出、斷言 tags 存在——也就是整合層的 roundtrip，unit fixture 結構上無能為力。

## 依賴圖是推導、ready 是推導的推導

第二個結構性缺陷在計畫層。盤點八張消費端遷移 ticket 的 `blockedBy`：五張只列了 W1-002（entity 重寫）——它們的「前提」只記錄了**時序直覺**（core entity 要先改），沒記錄**語意前提**（我改用的 API 要真的有資料）。而 dashboard 判定 W2-008「ready 可派發」，依據就是這張不完整的 blockedBy。

訊號鏈是這樣失真的：語意前提沒被列進 blockedBy → blockedBy 齊了 → ready 亮綠燈 → 派發。每一步推導都正確、第一步的輸入就缺了。這跟 [#221 規則存在 vs 規則涵蓋](/report/lint-scope-must-be-explicit-fact/)同構：ready 訊號的可信度上限是依賴圖的完整性，圖不完整時 ready 的綠跟「沒檢查」的綠長一樣。修正也對準這裡：補建 read-path ticket、七張 ticket 的 blockedBy 補上資料通路前提、wave 重排序（讓 tag API 回真資料的工作先於所有消費端遷移）。

流程上還有一筆值得記：這次分析被要求**獨立重驗**——「勿盲信 PM 行號、重跑 grep / 讀檔」，五項證據全部重新驗證。攔截的品質靠的不是第一個發現者的正確、是第二雙眼睛用自己的指令重跑一遍。

## 判讀徵兆

- 遷移計畫的 ticket 清單裡，寫入（backfill / migration script）跟消費（API 呼叫端改寫）都有、讀取路徑（mapper / repository 載入）沒有獨立條目——逐段問「新結構的資料怎麼進物件」
- 新 API 在測試全綠、實機回空值 / 預設值——查 fixture 的建構方式是否繞過真實組裝路徑
- `blockedBy` 全是「結構上游」（entity、schema）而沒有「資料上游」（backfill、注入）——依賴圖記了時序、沒記語意
- grep 新欄位名在 repository / mapper 檔案零命中——讀取路徑還不知道這個欄位存在，消費端遷移是空中樓閣

## 相關閱讀

- 上一章：[Deprecated Getter Facade](/work-log/flutter_deprecated_getter_facade_entity_migration/)——facade 讓編譯過了，本文是「編譯過了之後、資料通路要自己驗證」的實錄
- 同構的持久化盲區：[功能完成卻從未持久化](/work-log/flutter_feature_complete_never_persisted/)——那篇缺寫入段、本文缺讀出段，三段通路各有各的靜默缺法
- 原則層：[#163 多階段流程的 artifact 欄位契約](/report/pipeline-artifact-field-contract/)——「下游宣稱以上游為輸入」要欄位層級可推導，blockedBy 的語意前提就是 ticket 系統的欄位契約
