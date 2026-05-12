---
title: "Scheduled Scaling"
date: 2026-05-12
description: "說明按已知時間表預先擴容的 autoscaler 模式"
weight: 231
---

Scheduled scaling 的核心概念是「按已知時間表預先擴容、不等流量上來才反應」。處理「已知時間點的可預期峰值」場景。可先對照 [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)。

## 概念位置

Scheduled scaling 適合：年度 / 季度活動（Prime Day、Black Friday、雙 11）、賽事（NFL Super Bowl、IPL 決賽）、行銷活動（產品發布、限量優惠）、內容發布（新片首映、新章節上線）。EC2 Auto Scaling 的 scheduled action、HPA 的 cron-based scaling、DynamoDB 的 scheduled capacity 都是實作。可先對照 [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)。

## 可觀察訊號與例子

需要 scheduled scaling 的訊號是「事件型流量上升速度比 autoscaler 反應快」。對應案例：[Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) 年增率 30-77% 提前算進容量；[Tixcraft 售票](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 開賣前 30-60 分鐘 pre-scale ELB / EC2。

## 設計責任

Scheduled scaling 必須 *提前足夠時間* 啟動、不是事件當下才擴。pre-warm window 通常 30 分鐘到 2 小時（取決於 instance boot time、cache warmup、connection pool 預熱）。事件結束後也要 *scheduled scale down*、避免長期 over-provision。跟 [predictive scaling](/backend/knowledge-cards/predictive-scaling/) 跟 reactive scaling 三層組合最穩。
