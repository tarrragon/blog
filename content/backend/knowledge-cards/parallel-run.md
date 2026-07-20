---
title: "Parallel Run（並行期）"
date: 2026-06-11
description: "說明舊系統維持 source of truth、新系統以單向同步加唯讀驗證運轉的遷移共存階段、與雙寫的寫入路徑控制權差異"
weight: 374
---

並行期（parallel run）的核心概念是讓新舊系統共存一段時間、用真實資料驗證新系統的正確性、再執行切換：舊系統維持 [source of truth](/backend/knowledge-cards/source-of-truth/)、變更透過同步管道單向流入新系統、新系統以唯讀角色運轉並接受比對。它跟 [dual write](/backend/knowledge-cards/dual-write/) 的分界在寫入路徑的控制權：寫入發生在自己的程式碼裡、可以雙寫；寫入發生在外部系統（託管平台、第三方服務）內部、插不進那條路徑、就只能單向同步 — 並行期是後者的標準驗證形態。

## 概念位置

並行期屬於遷移驗證的形態家族：[dual write](/backend/knowledge-cards/dual-write/) 與 [shadow read](/backend/knowledge-cards/shadow-read/) 適用於寫入路徑可控的自建系統之間、並行期適用於來源系統不可改的情境。驗證手段共用 [data reconciliation](/backend/knowledge-cards/data-reconciliation/) — 定期比對兩邊的筆數、金額與關鍵彙總；結束點是一段 [cutover window](/backend/knowledge-cards/cutover-window/)、由收斂且穩定的對帳差異率觸發排程。

## 可觀察訊號與例子

一個跑在託管電商平台上的店、決定遷往自建：webhook 與排程匯出把平台的新訂單持續餵進自建資料庫、對帳 job 每天比對兩邊的訂單數與金額總和、內部報表與客服查詢先改走新系統 — 顧客仍在平台下單、新系統用真實流量驗證資料轉換。健康訊號是對帳差異率逐週收斂並穩定；反向訊號是並行期拖過原定窗口仍未排 cutover — 雙系統維運、平台月費與同步管道的持有成本持續累積、並行是驗證階段、長期共存要當成明確決策而非慣性。

## 設計責任

進入並行期的設計責任有四件：同步管道的完整性（漏事件直接變成對帳差異、來源限流與重試要先設計）、對帳 job 與差異率門檻（沒有量化門檻就沒有「收斂」可言）、內部流量先行（報表、後台查詢先走新系統、讓驗證涵蓋真實讀取模式）、明確的結束條件 — 差異率達標後排 cutover、或在成本反轉時承認部分共存為長期形態並記錄重評條件。
