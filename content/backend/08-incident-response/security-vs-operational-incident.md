---
title: "8.17 Security Incident vs Operational Incident 分流"
date: 2026-05-01
description: "把資安事故跟可用性事故的 IR 流程分支點明確化"
weight: 17
---

## 大綱

- 為何需要分流：兩類事故的決策模型、責任、通報、證據要求都不同
- 分支判讀：影響類型（資料 / 可用性 / 機密）、是否有外部 actor、是否觸發法規通報
- 平行 vs 切換：同事故可能同時是 operational + security（如 ransomware 同時影響可用性 + 資料）
- 證據保全的優先序差異：operational 重 forensic-light、security 重 chain of custody
- 通報差異：operational 對客戶 / 內部、security 還要法規 / 執法 / 律師
- 跟 [07 資安](/backend/07-security-data-protection/) 的交接：07 提供 security IR 的概念基底、08 提供 operational IR 的流程主幹
- 跟 [8.3 containment](/backend/08-incident-response/containment-recovery-strategy/) 的整合：security 事故的止血優先序跟 operational 不同（隔離 vs 復原）
- 跟 [8.10 stakeholder](/backend/08-incident-response/stakeholder-communication/) 的整合：security 事故對外通訊邊界更嚴
- 反模式：security 事故走 operational 流程、證據被 IR 操作覆蓋；operational 套 security 流程、復原速度被法務拖慢

## 判讀訊號

- 事故啟動時無人能說「這是 ops 還是 security」
- security 事故 IR 操作覆蓋了 forensic 證據
- operational 事故法務介入過多、復原拖慢
- 兼具兩類性質的事故（如 ransomware）流程冗餘 / 衝突
- IC 角色 vs Security IC（CISO 線）責任邊界不清

## 交接路由

- 07 資安：security IR 的概念框架
- 08.1 severity：分流影響 severity 計算
- 08.3 containment：止血策略差異
- 08.5 postmortem：證據保全與 RCA 範圍
- 08.10 stakeholder：對外通訊的法規邊界
- 04.12 audit log：證據鏈來源
