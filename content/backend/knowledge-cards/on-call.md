---
title: "On-Call"
tags: ["值班機制", "On-Call"]
date: 2026-04-23
description: "說明值班制度如何承接告警、事故分級與升級流程"
weight: 161
---

On-call 的核心概念是「在指定時段由明確責任角色承接運行事件」。它把告警回應、事故分級、升級決策與交接責任固定化，讓事故處理不依賴臨時找人。

## 概念位置

On-call 是 [alert](../alert/)、[incident severity](../incident-severity/) 與 [escalation policy](../escalation-policy/) 的執行入口。值班制度決定誰先收到訊號、誰有權啟動 incident 流程。

## 可觀察訊號與例子

系統需要 on-call 制度的訊號是事故常在非上班時間發生，或跨區團隊需要連續處理。付款 API 夜間故障時，若沒有清楚值班安排，回復時間通常被人員定位延遲拉長。

## 設計責任

On-call 設計要定義排班、回應時限、交接格式、升級路徑與支援角色。制度需要和 [runbook](../runbook/) 與演練一起維護，避免值班只剩 pager 通知而沒有可執行流程。
