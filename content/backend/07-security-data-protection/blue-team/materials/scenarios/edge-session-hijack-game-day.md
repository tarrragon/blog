---
title: "Edge Session Hijack Game Day"
tags: ["Blue Team", "Scenario", "Edge Exposure", "Game Day"]
date: 2026-04-30
description: "以入口設備 session disclosure 風險設計 edge exposure game day"
weight: 72532
---

本情境的責任是演練入口設備修補後的 session 收斂。它以 [Citrix Bleed 2023 edge session case](/backend/07-security-data-protection/blue-team/materials/field-cases/citrix-bleed-2023-edge-session-pressure/) 為來源，轉成通用 edge gateway game day。

## Scenario Trigger

外部 advisory 指出 edge gateway 存在已被利用的 session disclosure vulnerability。平台團隊已完成 patch，但 SOC 仍看到部分高權限 session 在異常來源延續。

## Initial Hypothesis

| 假設                          | 驗證資料                                 |
| ----------------------------- | ---------------------------------------- |
| vulnerability 已被利用        | edge access log、IOC、exploit trace      |
| patch 已完成但 session 仍有效 | patch record、session store、gateway log |
| downstream service 已受影響   | API access log、admin action、audit log  |

## Control Surface

控制面包含 public entrypoint、patch management、[session invalidation](/backend/knowledge-cards/session-invalidation/)、containment、hunting 與 incident severity。

## Response Route

1. Observed：確認 CVE、暴露資產與 patch 狀態。
2. Assessed：比對 IOC、session activity 與 high-risk account。
3. Mitigated：限縮 gateway access、撤銷 session、提升監控。
4. Validated：確認新 session policy、log coverage 與 downstream audit。
5. Closed：更新 vulnerability response 與 edge runbook。

## Evidence Target

| 證據                        | 用途                         |
| --------------------------- | ---------------------------- |
| patch record                | 證明曝險窗口                 |
| gateway access log          | 判斷 session disclosure 範圍 |
| session invalidation record | 證明 containment 完成        |
| downstream audit log        | 判斷服務影響                 |

## Write-back Target

- [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- [7.B11 Vulnerability Response State Machine](/backend/07-security-data-protection/blue-team/vulnerability-response-state-machine/)
- [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/)
- [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/)
