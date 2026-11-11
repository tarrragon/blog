---
title: "Local Worker"
date: 2026-04-23
description: "說明同一個 process 內的背景工作模型與其生命週期邊界"
weight: 149
---

Local worker 的核心概念是「背景工作仍留在同一個 application process」。它可降低 request 等待時間，但不提供跨 process 的持久可靠保證。 可先對照 [In-Process Channel](/backend/knowledge-cards/in-process-channel/)。

## 跟其他概念的關係

Local worker 常搭配 [in-process channel](/backend/knowledge-cards/in-process-channel/) 與 [worker pool](/backend/knowledge-cards/worker-pool/)；若需求轉向跨節點可靠處理，通常要改用 [durable queue](/backend/knowledge-cards/durable-queue/)。

## 可觀察訊號與例子

例如非關鍵通知、短週期快取刷新、定時清理記憶體資料，可先由 local worker 承擔。

## 判斷條件與後果

Local worker 的任務只存在於 application process 的記憶體裡，process 停止時，還沒處理的任務跟著消失。沒有定義停止行為與 shutdown 合約時，每一次部署或重啟都會丟掉當下排隊的任務，而且沒有紀錄顯示丟了哪些，原因是任務從來沒有寫到 process 以外的地方。隊列沒有上限時，產生速度超過處理速度的期間，積壓的任務持續佔用記憶體，直到 process 因記憶體不足被終止，一次丟掉全部積壓。錯誤處理沒有定義時，失敗的任務不會重試，也不會被記成待補。任務遺失會造成產品後果時，這類工作改用 [durable queue](/backend/knowledge-cards/durable-queue/)，因為只有寫到 process 之外的任務在重啟之後還在。
