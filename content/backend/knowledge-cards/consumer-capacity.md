---
title: "Consumer Capacity"
date: 2026-04-23
description: "說明 consumer 群組每秒能穩定處理多少工作"
weight: 70
---

Consumer capacity 的核心概念是「consumer 群組在穩定條件下能處理的工作量」。它取決於 consumer 數量、handler 耗時、prefetch、下游容量、錯誤率與重試量。

## 概念位置

Consumer capacity 是 queue sizing 與容量規劃的基礎。Producer rate 高於 consumer capacity 時，queue depth 與 lag 會上升；consumer capacity 高於下游容量時，壓力會轉移到資料庫或 API。

## 可觀察訊號與例子

系統需要估算 consumer capacity 的訊號是活動前要確認 queue 能否消化尖峰。通知服務每秒進入 5,000 筆任務，而 consumer 群組只能穩定處理 2,000 筆，lag 會持續累積。

## 設計責任

Capacity 設計要看平均耗時、p95 耗時、重試比例、下游限制與擴容速度。Runbook 應說明擴 consumer、調 prefetch、降級 producer 或暫停低優先訊息的條件。
