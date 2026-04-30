---
title: "7.BM2 藍隊現場案例素材"
tags: ["Blue Team", "Field Cases", "Incident Learning"]
date: 2026-04-30
description: "定義藍隊現場案例的收錄規則，支援後續防守推演與控制面補強"
weight: 7252
---

藍隊現場案例素材的責任是補充防守方在真實事件中的壓力。這一層先保留收錄規則，後續再把來源可靠、細節足夠、能轉成防守決策的案例納入。

## 收錄欄位

| 欄位              | 責任                               |
| ----------------- | ---------------------------------- |
| Case source       | 來源與日期                         |
| Defender pressure | 防守方承受的可見度、時程或協調壓力 |
| Control gap       | 事件揭露的控制面缺口               |
| Detection route   | 可觀測訊號與升級路由               |
| Exercise hook     | 可轉成 tabletop 或 Game Day 的情境 |

## 收錄優先序

案例收錄優先看防守推演價值。能補足 identity、edge exposure、supply chain、data exfiltration 或 incident coordination 的案例，優先轉成情境卡與控制模式。

## Source-first 規則

現場案例卡的責任是保存可回溯的防守壓力。每張案例卡都要先有公開來源，再抽出 defender pressure、control gap、detection route、exercise hook 與 write-back target。

來源優先序為官方事件說明、政府或資安機構 advisory、受影響組織 postmortem、受委託調查報告與可信技術分析。若來源只能支撐部分欄位，案例卡需明確標示可引用範圍。

## 下一輪案例大綱

| 案例方向                         | 核心壓力                                        | 預計產出                                                                                                                                     | 回寫位置        |
| -------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| Identity abuse field case        | 身份驗證、支援流程與權限回收壓力                | [Okta support token case](/backend/07-security-data-protection/blue-team/materials/field-cases/okta-support-token-2023-identity-pressure/)   | `7.2` + `7.B12` |
| Edge exposure field case         | 對外入口曝險、修補窗口與偵測時差                | [Citrix Bleed edge case](/backend/07-security-data-protection/blue-team/materials/field-cases/citrix-bleed-2023-edge-session-pressure/)      | `7.3` + `7.B11` |
| Supply chain field case          | build、artifact、第三方工具與 release gate 壓力 | [3CX supply chain case](/backend/07-security-data-protection/blue-team/materials/field-cases/3cx-2023-supply-chain-artifact-pressure/)       | `7.12` + `7.22` |
| Data exfiltration field case     | 低頻匯出、資料範圍判讀與通報壓力                | [MOVEit exfiltration case](/backend/07-security-data-protection/blue-team/materials/field-cases/moveit-2023-mft-exfiltration-pressure/)      | `7.4` + `7.24`  |
| Incident coordination field case | 多團隊分級、owner、通訊與證據壓力               | [CISA GeoServer IR case](/backend/07-security-data-protection/blue-team/materials/field-cases/cisa-geoserver-2024-ir-coordination-pressure/) | `7.B6` + `08`   |

現場案例卡的完成條件是能支撐一張情境卡與一張控制模式卡。每張卡都要留下 detection route、exercise hook 與 write-back target。

## 變體案例（補強反向驗證）

依 [素材庫比例設計](/report/source-library-ratio-supports-scenario-validation/)，每個主情境背後維持 2-3 個來源。下列案例補強身份、邊界、供應鏈與資料外送的變體壓力。

| 主情境                | 變體案例                                                                                                                                                           | 補強角度                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| Identity              | [Storm-0558 cloud signing key](/backend/07-security-data-protection/blue-team/materials/field-cases/storm-0558-2023-cloud-signing-key-pressure/)                   | 雲端身份信任根、key rotation                   |
| Identity              | [MGM helpdesk pressure](/backend/07-security-data-protection/blue-team/materials/field-cases/mgm-2023-helpdesk-social-engineering-pressure/)                       | helpdesk 驗證與 IdP 高權限保護                 |
| Edge exposure         | [Ivanti Connect Secure mass exploitation](/backend/07-security-data-protection/blue-team/materials/field-cases/ivanti-connect-secure-2024-edge-mass-exploitation/) | 批量利用、emergency directive、integrity check |
| Supply chain          | [XZ Utils maintainer pressure](/backend/07-security-data-protection/blue-team/materials/field-cases/xz-utils-2024-open-source-maintainer-pressure/)                | 開源維護者信任、pre-release 偵測               |
| Data exfiltration     | [Snowflake credential reuse](/backend/07-security-data-protection/blue-team/materials/field-cases/snowflake-2024-credential-reuse-pressure/)                       | SaaS 平台 credential、MFA、network boundary    |
| Incident coordination | [Change Healthcare recovery](/backend/07-security-data-protection/blue-team/materials/field-cases/change-healthcare-2024-recovery-and-dependency-pressure/)        | 長時間復原、外部依賴、監管通報                 |
