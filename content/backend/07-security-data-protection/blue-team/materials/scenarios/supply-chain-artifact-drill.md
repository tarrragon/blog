---
title: "Supply Chain Artifact Drill"
tags: ["Blue Team", "Scenario", "Supply Chain", "Artifact"]
date: 2026-04-30
description: "以 artifact provenance 偏移設計供應鏈 release gate 與 rollback 演練"
weight: 72533
---

本情境的責任是演練 artifact provenance 與 release gate。它以 [3CX 2023 supply chain case](/backend/07-security-data-protection/blue-team/materials/field-cases/3cx-2023-supply-chain-artifact-pressure/) 為來源，轉成通用軟體供應鏈 artifact drill。

## Scenario Trigger

客戶回報桌面客戶端或 agent 版本觸發 EDR alert。內部比對發現公開下載 artifact、build record 與簽章證據之間存在偏移。

## Initial Hypothesis

| 假設                               | 驗證資料                                           |
| ---------------------------------- | -------------------------------------------------- |
| artifact 在 build 後被替換         | checksum、registry log、publish log                |
| build environment 受影響           | CI log、runner image、credential use               |
| upstream dependency 或工具引入污染 | dependency provenance、developer endpoint evidence |

## Control Surface

控制面包含 [artifact provenance](/backend/knowledge-cards/artifact-provenance/)、CI pipeline、release gate、release freeze、rollback 與 customer advisory。

## Response Route

1. Freeze：暫停 affected artifact 發佈與自動更新。
2. Scope：比對 artifact hash、download log、customer version distribution。
3. Validate：重建 clean build、驗證簽章與 provenance。
4. Rollback：提供 clean artifact、uninstall 或 rollback route。
5. Write-back：更新 release gate、build isolation 與 artifact evidence policy。

## Evidence Target

| 證據                    | 用途                     |
| ----------------------- | ------------------------ |
| build provenance record | 判斷 artifact 是否可追溯 |
| signing log             | 判斷簽章流程是否被濫用   |
| customer download log   | 判斷 downstream impact   |
| release freeze record   | 證明風險放行被暫停       |

## Write-back Target

- [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- [7.22 資安風險如何進入 Release Gate](/backend/07-security-data-protection/security-risk-in-release-gate/)
- [Detection lifecycle pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/detection-lifecycle-pattern/)
- [Exercise write-back pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/exercise-write-back-pattern/)
