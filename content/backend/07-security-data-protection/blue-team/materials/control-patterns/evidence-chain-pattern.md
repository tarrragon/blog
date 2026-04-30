---
title: "Evidence Chain Pattern"
tags: ["Blue Team", "Control Pattern", "Evidence"]
date: 2026-04-30
description: "定義事故與演練需要保存的訊號、決策、artifact、timeline 與 retention 證據"
weight: 72542
---

Evidence chain pattern 的責任是讓防守決策可回查。它把 signal、decision record、artifact、timeline 與 retention 串成同一條證據鏈，支撐 triage、通報、復盤與控制面回寫。

## 支撐素材

| 素材                                                                                                                                         | 可支撐論點                                                   |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [MOVEit exfiltration case](/backend/07-security-data-protection/blue-team/materials/field-cases/moveit-2023-mft-exfiltration-pressure/)      | data scope、customer mapping 與通報需要可回查資料            |
| [Citrix Bleed edge case](/backend/07-security-data-protection/blue-team/materials/field-cases/citrix-bleed-2023-edge-session-pressure/)      | patch、session invalidation 與 downstream audit 需要共同保存 |
| [CISA GeoServer IR case](/backend/07-security-data-protection/blue-team/materials/field-cases/cisa-geoserver-2024-ir-coordination-pressure/) | centralized logging 與 timeline 支撐事故調查                 |

## 欄位

| 欄位            | 責任                                         |
| --------------- | -------------------------------------------- |
| Signal          | 記錄第一個可觀測觸發                         |
| Decision record | 記錄分級、接受風險與凍結決策                 |
| Artifact        | 保存 build、log、file、IOC 或 forensic image |
| Timeline        | 串接觸發、處置、通報與復原時間               |
| Retention       | 定義證據保存期限與查詢責任                   |

## 判讀訊號

| 訊號                               | 代表需求                                  |
| ---------------------------------- | ----------------------------------------- |
| 事故復盤只能重述事件，缺少證據連結 | 需要 evidence chain                       |
| 資料外送範圍判讀依賴人工回憶       | 需要 data access 與 customer mapping 證據 |
| release 或 patch 決策缺少紀錄      | 需要 decision record 與 timeline          |

## 適用邊界

此模式適合有通報、法務、客戶影響或跨系統回查需求的事件。低風險操作可以只保留 signal 與 owner，但要保留升級條件。

## 下一步路由

- [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
- [Low-frequency exfiltration tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/)
- [Edge session hijack game day](/backend/07-security-data-protection/blue-team/materials/scenarios/edge-session-hijack-game-day/)
