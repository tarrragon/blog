---
title: "8.1 事故分級與啟動條件"
date: 2026-04-23
description: "建立統一分級標準與事故啟動門檻"
weight: 1
---

## 大綱

- severity criteria
- user impact signals
- trigger thresholds
- escalation handoff

## 判讀訊號

- 事故啟動延遲於擴散、影響面已擴大才升級
- severity 分級靠 IC 直覺、無 user impact 量化
- 升級條件不清、跨團隊重複 page 同事故
- 同類事件不同 IC 給不同 severity
- 啟動門檻過高（漏判）或過低（噪音）、無校準流程

## 交接路由

- 04.6 SLI/SLO：burn rate 對應 severity 門檻
- 08.14 multi-incident：跨事故優先序判準
- 08.17 security vs operational：分流影響 severity 計算
