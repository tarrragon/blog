---
title: "Atlassian"
date: 2026-05-01
description: "Atlassian 多租戶事故時間線與架構脈絡"
weight: 5
---

Atlassian 2022 的 14 天事故是多租戶誤刪 + 跨團隊協作的教學標竿。事故 post-mortem 公開度極高、揭露 IR 內部運作細節（incident commander 輪值、跨團隊溝通、客戶補償政策），是少數能完整看到大型事故 IR 流程的公開素材。

## 規劃重點

- 多租戶資料模型：跨產品 tenant ID 的 cascading delete 風險
- Recovery 順序：885 個 tenants 為何不能平行恢復、需要排序
- 跨團隊協作：incident commander 輪值、24x7 支援、客戶溝通分軌
- Stakeholder 通訊：customer impact 量化、補償政策、合約衝擊
- Postmortem 文化：Atlassian Incident Management Handbook 公開內容

## 預計收錄事故

| 年份 | 事故            | 教學重點                                |
| ---- | --------------- | --------------------------------------- |
| 2022 | 14 天多租戶誤刪 | 大規模 IR 協作、長尾 recovery、客戶溝通 |
| 待補 | 較小規模事故    | 對比 14 天事故的 IR 流程演化            |

## 引用源

待補（Atlassian post-incident review、Incident Management Handbook）。
