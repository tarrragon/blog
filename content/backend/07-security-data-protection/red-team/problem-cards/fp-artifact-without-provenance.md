---
title: "7.R11.P16 產物缺少來源證據"
tags: ["Artifact Provenance", "供應鏈完整性", "Release Gate", "Red Team"]
date: 2026-04-30
description: "說明 artifact 缺乏可驗證 provenance 時如何放大供應鏈污染風險"
weight: 7246
---

這個失效樣式的核心問題是部署產物與來源提交無法完整對應。當 artifact 缺少 provenance 證據，污染產物會更容易穿越 [release gate](/backend/knowledge-cards/release-gate/)。

## 常見形成條件

- build metadata 與來源提交缺少可回查關聯。
- 產物簽署驗證未納入 [release gate](/backend/knowledge-cards/release-gate/)。
- 供應鏈事件後缺少受影響 artifact 快速盤點機制。

## 判讀訊號

- 同版本 artifact 的來源紀錄不一致或不可追溯。
- 發佈關卡通過但缺少簽署驗證證據。
- 事件發生後無法快速定位受影響部署批次，導致 [impact scope](/backend/knowledge-cards/impact-scope/) 判讀延後。

## 案例觸發參考

- [SolarWinds 2020](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)
- [3CX 2023](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/)
- [XZ 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)

## 來源主題章節

- [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- [7.R8 控制面失效樣式](/backend/07-security-data-protection/red-team/control-failure-patterns/)

## 下一步路由

本失效樣式對應的實作 chain：

**控制面（mitigation 在這裡定義）**：

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)

**演練 / 控制落地（轉成欄位）**：

- [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/)
- [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/)
