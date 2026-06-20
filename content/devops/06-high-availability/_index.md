---
title: "模組六：高可用與災難復原"
date: 2026-06-20
description: "一個節點掛了服務怎麼不中斷 — 冗餘設計、failover 機制、disaster recovery 策略"
weight: 6
tags: ["devops", "high-availability", "failover", "disaster-recovery", "redundancy"]
---

回答「一個節點掛了服務怎麼不中斷」。高可用的核心是冗餘 — 每個單點故障都有替代路徑。

## 待寫章節

- [ ] 單點故障盤點（服務實例 / DB / LB / DNS — 哪些掛了整個系統就掛）
- [ ] 冗餘設計模式（active-passive / active-active / multi-region）
- [ ] Failover 機制（自動 vs 手動、failover 時間、資料一致性）
- [ ] Disaster recovery 策略（RPO / RTO 目標、備份恢復演練）
- [ ] 高可用的成本（冗餘 = 至少 2x 資源成本 — 值不值得）

## 跨分類引用

- → [backend 可靠性](/backend/06-reliability/)：Backend 的可靠性設計
- → [devops 模組四 服務探活](/devops/04-service-health/)：探活是 failover 的觸發條件
