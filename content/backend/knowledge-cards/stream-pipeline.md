---
title: "Stream Pipeline"
date: 2026-04-23
description: "說明連續資料流經多個處理階段時如何管理吞吐、順序與 backpressure "
weight: 129
---

Stream pipeline 的核心概念是「資料連續流經多個處理階段」。每個階段讀取輸入、處理資料、送到下一階段；整體吞吐取決於最慢階段與階段之間的 buffer。 可先對照 [Change Data Capture](/backend/knowledge-cards/change-data-capture/)。

## 跟其他概念的關係

Stream pipeline 常出現在 event stream、log processing、[CDC](/backend/knowledge-cards/change-data-capture/)、ETL、即時分析、IoT readings 與訊息轉換流程。它需要處理 ordering、[partition](/backend/knowledge-cards/partition/)、[checkpoint](/backend/knowledge-cards/checkpoint/)、[backpressure](/backend/knowledge-cards/backpressure/)、[retry](/backend/knowledge-cards/retry-policy/) 與資料完整性。

## 可觀察訊號與例子

系統需要 stream pipeline 設計的訊號是資料會持續進入，且需要多步驟加工。訂單事件先做清洗，再寫入搜尋索引與報表系統；任一階段變慢，都會讓上游 lag 擴大。

## 判斷條件與後果

Stream pipeline 的吞吐由最慢的階段決定，階段邊界與階段之間的 [buffer](/backend/knowledge-cards/buffer/) 決定一個階段變慢時影響傳到多遠：沒有 buffer 時，下游一變慢，上游跟著停；buffer 沒有上限時，積壓一直增加到記憶體或磁碟用完。沒有 checkpoint 時，階段重啟後只能從頭處理或跳過中斷的位置，前者產生重複、後者遺漏資料。錯誤沒有隔離時，一筆格式錯誤的資料讓整個階段停下，後面的資料全部卡住；沒有[重放](/backend/knowledge-cards/replay-runbook/)的手段時，錯誤修好之後，已經處理錯的資料無法重算。lag 指標只看整條 pipeline 的總量時，看得出變慢、看不出是哪一段，所以每個階段各自觀測與限速，限速才能只套在瓶頸那一段。[correctness check](/backend/knowledge-cards/correctness-check/) 比對輸入與輸出，沒有它時，資料在某一段被丟掉，lag 指標仍然正常。
