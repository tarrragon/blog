---
title: "Object Storage"
date: 2026-04-23
description: "說明大型非結構化檔案的保存、存取與生命週期管理"
weight: 148
---

Object storage 的核心概念是「用 object key 管理大型檔案內容」。它適合圖片、影片、附件、匯出檔與備份，不適合承擔複雜交易查詢。 可先對照 [Observability Middleware](/backend/knowledge-cards/observability-middleware/)。

## 跟其他概念的關係

常見做法是把檔案 metadata 放在資料庫，內容放在 object storage，並用 key 連結兩者。 可先對照 [Observability Middleware](/backend/knowledge-cards/observability-middleware/)。

## 可觀察訊號與例子

例如使用者上傳附件、報表匯出、備份封存，通常都會走 object storage 路徑。

## 判斷條件與後果

Object storage 裡的檔案在上傳之後一直存在，直到有規則把它刪掉，所以檔案的生命週期由存取權限、下載時效、版本策略、保留期限與刪除流程共同決定。存取權限設成公開時，知道 object key 的人都下載得到附件與匯出檔；下載連結沒有時效時，連結被轉傳之後一直有效。沒有版本策略時，覆寫同一個 key 就失去舊內容；開了版本而沒有保留期限時，舊版本持續累積儲存費用。刪除流程只刪資料庫裡的 metadata、沒有刪 object 時，檔案留在 object storage 裡而沒有任何紀錄指向它，既佔空間，也無法在使用者要求刪除時確認已經清除。
