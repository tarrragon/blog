---
title: "Control Owner Pattern"
tags: ["Blue Team", "Control Pattern", "Ownership"]
date: 2026-04-30
description: "定義高風險控制面如何配置 owner、協作角色、決策角色與升級路徑"
weight: 72541
---

Control owner pattern 的責任是把高風險控制面固定到可執行角色。它讓 incident triage、vulnerability response 與 tabletop 演練都能快速判斷誰主責、誰協作、誰做決策。

## 支撐素材

| 素材                                                                                                                                         | 可支撐論點                                                           |
| -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [Okta support token case](/backend/07-security-data-protection/blue-team/materials/field-cases/okta-support-token-2023-identity-pressure/)   | support owner、identity owner 與 customer communication 需要共同協作 |
| [CISA GeoServer IR case](/backend/07-security-data-protection/blue-team/materials/field-cases/cisa-geoserver-2024-ir-coordination-pressure/) | IR plan 需要包含第三方支援與工具 access procedure                    |
| [NIST SP 800-61r3](/backend/07-security-data-protection/blue-team/materials/professional-sources/nist-sp-800-61r3-incident-response/)        | incident response 是跨治理、偵測、回應與復原的風險管理能力           |

## 欄位

| 欄位            | 責任                         |
| --------------- | ---------------------------- |
| Control owner   | 對控制面結果負責             |
| Collaborator    | 提供資料、操作或驗證         |
| Decision maker  | 對風險接受、凍結或升級做決策 |
| Escalation path | 定義分級上升與跨團隊接手路徑 |
| Exit condition  | 定義何時完成處置或轉入復盤   |

## 判讀訊號

| 訊號                         | 代表需求                       |
| ---------------------------- | ------------------------------ |
| 同一事件在多個團隊間反覆轉手 | 需要明確 owner 與 collaborator |
| 分級結果有人執行但沒有人決策 | 需要 decision maker 欄位       |
| 第三方支援需要臨時授權       | 需要預先定義 escalation path   |

## 適用邊界

此模式適合 identity、entrypoint、MFT、artifact 與 vulnerability response 這類跨團隊控制面。單一服務內部的小型修補可以使用較輕量的 owner 欄位。

## 下一步路由

- [Ownership](/backend/knowledge-cards/ownership/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [Identity support token tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/identity-support-token-tabletop/)
