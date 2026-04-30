---
title: "7.BM4 藍隊控制模式素材"
tags: ["Blue Team", "Control Pattern", "Validation"]
date: 2026-04-30
description: "定義藍隊控制模式分類，支援 release gate、偵測驗證與事故交接"
weight: 7254
---

藍隊控制模式素材的責任是把反覆出現的防守做法整理成可搬運模式。控制模式介於來源卡與文章之間，負責把專業來源轉成服務可操作欄位。

## 模式分類

| 模式                           | 責任                                                                   | 承接章節    |
| ------------------------------ | ---------------------------------------------------------------------- | ----------- |
| Control owner pattern          | 明確主責、協作與升級角色                                               | 7.B1 / 08   |
| Evidence chain pattern         | 保留判讀、驗證、回復與通報證據                                         | 7.B3 / 7.7  |
| Detection lifecycle pattern    | 管理規則來源、測試、誤報與退場                                         | 7.B2 / 7.13 |
| Vulnerability response pattern | 管理曝險、緩解、修補與驗證                                             | 7.B2 / 05   |
| Exercise write-back pattern    | 把演練結果回寫到 [runbook](/backend/knowledge-cards/runbook/) 與控制面 | 7.B4 / 7.19 |

## 使用原則

控制模式的使用原則是先定義判讀欄位，再交給章節發展情境。模式卡提供可搬運骨架，文章負責說明它在真實服務中的取捨、風險與下一步路由。

## Source-first 規則

控制模式卡的責任是從多個來源案例中抽出可搬運做法。每張模式卡至少要引用一張 field case 或 professional source，並說明這個模式支撐哪一類 scenario。

模式卡可以比單一案例更抽象，抽象後仍要保留判讀訊號、證據欄位、適用邊界與回寫位置。這個要求讓控制模式能服務工程實作，並保持可交接的操作語意。

## 下一輪模式大綱

| 模式卡                                                                                                                                      | 核心欄位                                                                                       | 使用情境                                | 回寫位置        |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------- | --------------- |
| [Control owner pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/control-owner-pattern/)                   | owner、collaborator、decision maker、escalation path                                           | 高風險控制面需要明確接手                | `7.B1` + `08`   |
| [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/)                 | signal、decision record、artifact、timeline、retention                                         | 演練與事故需要可回查證據                | `7.7` + `7.B3`  |
| [Detection lifecycle pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/detection-lifecycle-pattern/)       | source、logic、test event、false positive、retirement                                          | 偵測規則需要維護節奏                    | `7.B5` + `7.13` |
| [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/) | observed、assessed、mitigated、patched、validated、closed                                      | 漏洞事件需要狀態交接                    | `7.B11` + `05`  |
| [Exercise write-back pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/exercise-write-back-pattern/)       | finding、control update、runbook update、owner、tripwire                                       | 演練結果需要轉成工程任務                | `7.B4` + `7.24` |
| [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/)         | MFA enforcement、rotation、reset workflow、exposure monitoring、network boundary               | credential、token、session 需要共同基線 | `7.2` + `7.B12` |
| [Recovery readiness pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/recovery-readiness-pattern/)         | recovery objective、backup access、restore verification、dependency map、communication cadence | 長時間 outage 與外部依賴需要事前準備    | `7.24` + `08`   |

控制模式卡的完成條件是能被 field case 與 scenario 同時引用。每張卡都要提供判讀訊號、適用邊界、驗證方法與下一步路由。
