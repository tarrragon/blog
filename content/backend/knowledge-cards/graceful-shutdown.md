---
title: "Graceful Shutdown"
date: 2026-04-23
description: "說明服務停止前如何排空流量、完成工作與保存狀態"
weight: 12
---

Graceful shutdown 的核心概念是「instance 收到停止訊號後，以可控流程結束服務」。它會先停止接收新工作，再讓正在處理的 request、長連線、consumer 或背景任務在期限內完成、保存狀態或交回 broker。 可先對照 [Draining](/backend/knowledge-cards/draining/)。

## 跟其他概念的關係

Graceful shutdown 是 application 與部署平台的停止合約。平台負責送出停止訊號、移出流量與設定期限；application 負責停止入口、排空處理中工作、釋放連線、提交 checkpoint、送出最後 log 與 metrics。 可先對照 [Draining](/backend/knowledge-cards/draining/)。

## 可觀察訊號

系統需要 graceful shutdown 的訊號是部署、擴容縮容或主機維護時出現 request 中斷、訊息重複、長連線突斷、資料寫入半途失敗或 worker 遺失進度。這些現象表示停止流程與工作生命週期沒有對齊。

## 接近真實網路服務的例子

背景 worker 正在處理影片轉檔時收到部署停止訊號。Graceful shutdown 應停止取得新工作，讓目前轉檔在期限內完成；若超過期限，worker 需要保存進度或讓 broker 重新投遞，並留下可追蹤的狀態。

## 判斷條件與後果

Graceful shutdown 的判斷條件是停止期間每一種進行中的工作是否都有結束的方式。沒有 timeout 時，一個不結束的請求或轉檔讓 instance 停不下來，平台最後強制終止，結果跟沒有 graceful shutdown 相同；沒有先做 [draining](/backend/knowledge-cards/draining/) 時，instance 一邊排空、一邊還收到新請求。consumer 被強制終止時，還沒 ack 的訊息由 broker 重新投遞，處理端沒有 idempotency 就把同一筆訊息處理兩次。長連線不會因為 instance 停止而自己結束，要等 [idle timeout](/backend/knowledge-cards/idle-timeout/) 或停止流程主動關閉，兩者都沒趕在期限之前發生時，期限一到連線被強制切斷，client 看到連線突斷。停止期間的 in-flight request、consumer ack、長連線數、錯誤率與強制終止次數有觀測時，部署中出現的中斷可以定位到是哪一種工作沒有在期限內結束。
