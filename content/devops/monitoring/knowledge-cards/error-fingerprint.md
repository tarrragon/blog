---
title: "Error Fingerprint"
date: 2026-06-24
description: "從 error 事件的 type、normalized message、stack trace 計算 hash，把相同根因的 error 歸為同一 error group"
weight: 5
tags: ["monitoring", "error", "fingerprint", "knowledge-card"]
aliases: ["/monitoring/knowledge-cards/error-fingerprint/"]
---

Error fingerprint 的核心概念是「從 error 事件中提取關鍵欄位計算 hash，相同 hash 的事件歸為同一 error group」。沒有 fingerprint 時，1000 筆同因 error 在 dashboard 上是 1000 行；有 fingerprint 後歸為 1 組，顯示 count / first_seen / last_seen / affected_sessions。可先對照 [redaction](/devops/monitoring/knowledge-cards/redaction/)（事件送出前的資料脫敏）和 [funnel analysis](/devops/monitoring/knowledge-cards/funnel-analysis/)（行為事件的轉換率分析）。

## 跟其他概念的關係

Error fingerprint 位在 collector 收到 error 事件之後、寫入 storage 之前。它的輸入是通過 schema validation 的 error 事件，輸出是附加了 `_fingerprint` 欄位的事件和更新後的 error_groups 摘要表。Fingerprint 只作用於 `type: "error"` 的事件 — 其他三類事件（event / metric / lifecycle）不需要去重分群。與 [redaction](/devops/monitoring/knowledge-cards/redaction/) 同樣運作在事件寫入 storage 之前，但目的不同——redaction 處理欄位內容的隱私、fingerprint 處理事件的分群鍵。

## 可觀察訊號與例子

需要 fingerprint 的訊號是「dashboard 的 error 列表中，同一個 bug 因為 error message 包含動態值（user ID、timestamp、IP）而分裂成多個不同的行」。例如 `"User 12345 not found"` 和 `"User 67890 not found"` 是同一個 bug，但 name-based grouping（`GROUP BY name`）把它們歸為同一行時，丟失了 message 中的動態值資訊；而沒有 normalization 的 message-based grouping 會把它們分裂成兩行。

## 判斷條件與後果

計算 fingerprint 時取哪些欄位，決定兩筆 error 事件會不會歸成同一組。只用 error type 計算時，fingerprint 過粗，拋出同一種 error type 的不同 bug 混進同一組，這一組的 count 與 affected_sessions 加總了好幾個 bug，修掉其中一個之後這一組照樣持續出現。用含動態值（user ID、timestamp、IP）的完整 message 計算時，fingerprint 過細，同一個 bug 依動態值分裂成多組，列表被同因錯誤佔滿，每一組的 count 都低，看不出這個 bug 影響了多少人。兩種情形的原因相同：hash 只比對輸入的欄位是否逐字相同，欄位裡的動態值每變一次，hash 就變一次；所以 message 先把動態值正規化（`User 12345 not found` 換成 `User <id> not found`）再進 hash。

## 自架 vs 商業方案

自架方案用規則做 fingerprint — regex normalize message（替換數字 / UUID / email / IP 等動態值）+ stack trace top N frames 做 hash。Sentry 在規則之上加了 in-app frame 過濾（忽略 framework / library frame）、source map 反解（minified JS → 原始碼位置）、和 ML-based grouping（語意相同但結構不同的 error 歸組）。差距主要在 minified / obfuscated 環境和 ML — 明文 stack trace 的場景下兩者效果相當。

## 完整章節

Fingerprint 演算法（基礎 / 進階 / Sentry / 自定義）、message normalization 的替換規則和風險、error_groups 表的 DDL 和 UPSERT 流程、dashboard 整合、自架方案的務實邊界 → [Error Fingerprint 與去重分群](/devops/monitoring/04-collector/error-fingerprint/)。
