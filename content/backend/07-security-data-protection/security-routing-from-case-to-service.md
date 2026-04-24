---
title: "7.8 模組路由：案例到服務實作"
date: 2026-04-24
description: "整理案例判讀如何路由到部署、可靠性與事故處理章節"
weight: 78
---

本章的責任是把案例判讀轉成跨章節路由規則。核心輸出是引用順序、責任切分與交接邊界，讓觀念層與實作層在同一條流程上對齊。

## 路由基線

路由基線的責任是維持章節分工穩定。每個主題先在 07 模組完成問題判讀，再交由 05/06/08 模組做服務實體落地。

1. 先選服務環節問題。
2. 再引用對應紅隊案例。
3. 接著定義事件節奏與責任邊界。
4. 最後交接到服務章節實作。

## 主題路由表

| 問題主題 | 先引用章節 | 交接章節 |
| --- | --- | --- |
| 身分與授權擴散 | [7.2](identity-access-boundary/) + `red-team/identity-access` | [8.8](../08-incident-response/incident-report-to-workflow/) |
| 邊界入口與管理面 | [7.3](entrypoint-and-server-protection/) + `red-team/edge-exposure` | [5.x](../05-deployment-platform/) + [8.3](../08-incident-response/containment-recovery-strategy/) |
| 資料外送與備份鏈 | [7.4](data-protection-and-masking-governance/) + `red-team/data-exfiltration` | [6.x](../06-reliability/) + [8.4](../08-incident-response/incident-communication/) |
| 供應鏈與交付信任 | [7.6](secrets-and-machine-credential-governance/) + `red-team/supply-chain` | [5.x](../05-deployment-platform/) + [8.8](../08-incident-response/incident-report-to-workflow/) |
| 稽核與責任邊界 | [7.7](audit-trail-and-accountability-boundary/) + `red-team/cases` | [8.5](../08-incident-response/post-incident-review/) |

## 到實作前的最後一層

本模組的最終輸出是「問題模型 + 案例證據 + 交接條件」。當章節討論進入平台設定值、程式策略或工具配置時，就代表已越過概念邊界，應切到 05/06/08 對應章節。

## 大綱

- 路由基線：先案例判讀，再服務章節落地
- 身分/入口/資料/供應鏈四類路由模板
- 章節責任切分：07 模組與 05/06/08 模組
- workflow 串接：案例段落到 runbook 條目
