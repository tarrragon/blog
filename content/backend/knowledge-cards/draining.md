---
title: "Draining"
tags: ["排空", "Draining"]
date: 2026-04-24
description: "說明服務如何先停止接收新流量，再讓既有工作完成"
weight: 132
---

Draining 的核心概念是「先把新的 request 停掉，再讓已經進來的工作在期限內完成或交回」。它是負載切換與停止流程中的保護動作，常出現在 rolling update、縮容、故障切換與 graceful shutdown。 可先對照 [Dual Write](/backend/knowledge-cards/dual-write/)。

## 跟其他概念的關係

Draining 位在 load balancer、deployment platform、application 與 in-flight work 之間。它介於流量入口與工作完成之間，目標是避免切換瞬間把正在處理的請求硬切掉。 可先對照 [Dual Write](/backend/knowledge-cards/dual-write/)。

## 可觀察訊號

系統需要 draining 的訊號是：

- instance 要下線或被替換
- 長連線或背景工作不能被直接中斷
- 切流時需要避免新請求進入舊實例

## 接近真實網路服務的例子

Kubernetes rolling update 前先讓 instance 進入 draining、load balancer 在切流前停止導入新連線、worker 停止接收新 job 但完成目前處理，都是 draining 的應用。

## 判斷條件與後果

Draining 的期限在兩種風險之間取捨。沒有期限、一直等到 in-flight 工作做完時，一條不結束的長連線或一個不 ack 的 consumer 讓 instance 一直下不了線，rolling update 與縮容停在半途，原因是 draining 什麼時候結束取決於最慢的那一件工作；期限太短時，正在處理的 request 被強制中斷，又回到 draining 想避免的狀態。Instance 停止接新工作的時點早於 load balancer 停止導流時，新 request 仍被導到這台已經在收尾的 instance 而失敗。超時之後怎麼強制終止沒有定義時，未完成的工作是被交回還是遺失沒有答案。In-flight request 數、consumer ack 與長連線狀態看不到時，分不出 draining 是正常收尾還是卡住了，所以這三項在 draining 期間要觀察得到。
