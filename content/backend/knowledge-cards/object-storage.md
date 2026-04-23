---
title: "Object Storage"
date: 2026-04-23
description: "說明大型非結構化檔案的保存、存取與生命週期管理"
weight: 147
---

Object storage 的核心概念是「用 object key 管理大型檔案內容」。它適合圖片、影片、附件、匯出檔與備份，不適合承擔複雜交易查詢。

## 概念位置

常見做法是把檔案 metadata 放在資料庫，內容放在 object storage，並用 key 連結兩者。

## 可觀察訊號與例子

例如使用者上傳附件、報表匯出、備份封存，通常都會走 object storage 路徑。

## 設計責任

設計時要定義存取權限、下載時效、版本策略、保留期限與刪除流程，避免檔案生命週期失控。
