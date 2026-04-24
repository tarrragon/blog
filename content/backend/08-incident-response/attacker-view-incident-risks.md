---
title: "8.7 攻擊者視角（紅隊）事故弱點判讀"
date: 2026-04-24
description: "從擴散路徑、回復瓶頸與交接斷點，盤點 incident response 的主要弱點"
weight: 7
---

事故流程的攻擊者視角（紅隊）判讀目標是確認「事件如何被放大、如何拖長、如何失去控制」。這裡的重點不是漏洞利用細節，而是反向檢查事故流程是否能在壓力下維持決策品質。

## 【情境】哪些團隊要先做事故弱點盤點

下列情境出現時，事故流程弱點通常先暴露：

- 事故跨服務、跨團隊，責任邊界不清楚
- 告警很多，但升級與分級節奏不一致
- 回復流程依賴少數關鍵人員記憶
- 值班輪替頻繁，交接內容不穩定

## 【判讀流程】事故弱點檢查順序

1. 看啟動面：檢查 [incident severity](../knowledge-cards/incident-severity/) 與啟動門檻是否一致。
2. 看指揮面：檢查 [incident command system](../knowledge-cards/incident-command-system/) 與 [escalation policy](../knowledge-cards/escalation-policy/) 是否能快速收斂決策。
3. 看回復面：檢查 [rollback strategy](../knowledge-cards/rollback-strategy/)、[failover](../knowledge-cards/failover/) 與 [runbook](../knowledge-cards/runbook/) 是否可在時限內執行。
4. 看交接面：檢查 [incident timeline](../knowledge-cards/incident-timeline/) 與 [handover protocol](../knowledge-cards/handover-protocol/) 是否支援輪班接續。

## 【風險代價】流程弱點會把小事件放大

事故流程缺口常把可控故障擴大成長時間中斷。分級不一致會延遲啟動；指揮責任模糊會造成重複操作；交接斷點會讓已完成資訊遺失。這些問題會直接拉長 [MTTR](../knowledge-cards/mttr/) 並增加次生事故風險。

## 【設計取捨】標準化流程與現場彈性

流程越標準化，交接與演練越穩定；同時需要更多前置維護。較穩定的做法是保留固定骨架（分級、角色、通訊、停損），把現場彈性放在策略選擇，而不是放在流程定義。

## 【最低控制面】進入實作前要先定義

- 分級啟動與升級條件
- 指揮角色、責任與交接格式
- 止血、回復、回滾的停損判準
- 復盤關閉條件與追蹤機制
