---
title: "Scheduled Scaling"
date: 2026-05-12
description: "說明按已知時間表預先擴容的 autoscaler 模式"
weight: 232
---

Scheduled scaling 的核心概念是「按已知時間表預先擴容、不等流量上來才反應」。處理「已知時間點的可預期峰值」場景。可先對照 [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)。

## 跟其他概念的關係

Scheduled scaling 適合：年度 / 季度活動（Prime Day、Black Friday、雙 11）、賽事（NFL Super Bowl、IPL 決賽）、行銷活動（產品發布、限量優惠）、內容發布（新片首映、新章節上線）。EC2 Auto Scaling 的 scheduled action、HPA 的 cron-based scaling、DynamoDB 的 scheduled capacity 都是實作。可先對照 [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)。

## 可觀察訊號與例子

需要 scheduled scaling 的訊號是「事件型流量上升速度比 autoscaler 反應快」。對應案例：[Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) 年增率 30-77% 提前算進容量；[Tixcraft 售票](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 開賣前 30-60 分鐘 pre-scale ELB / EC2。

## 判斷條件與後果

Scheduled scaling 的觸發時間點離事件開始多遠，決定擴出來的容量在峰值到來時是否已經可以處理流量。擴容在事件當下才觸發時，新 instance 還在開機、cache 還沒暖、connection pool 還沒建好，峰值的前段仍由原有容量處理，延遲與錯誤的情形跟沒有排程時相同；所以排程提前一段 pre-warm window 觸發，長度取決於 instance boot time、cache warmup 與 connection pool 預熱的總和，通常 30 分鐘到 2 小時。事件結束後沒有排定 scale down 時，峰值容量一直留著，系統處在長期 over-provision，代價是事件之後每一小時的閒置費用。排程只涵蓋已知時間表上的峰值，時間表外的流量變化由 [predictive scaling](/backend/knowledge-cards/predictive-scaling/) 與 reactive scaling 處理，三者並用時，排程管已知事件，另外兩種處理排程沒有預料到的流量。
