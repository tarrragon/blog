---
title: "7.6 秘密管理與機器憑證治理"
date: 2026-04-24
description: "以問題驅動方式整理 secret、token、key 與機器身份治理"
weight: 76
---

本章的責任是把機器身份與憑證風險拆成分域治理模型，讓 secret、token、key 的生命周期可以被一致驗證。

## 本章寫作邊界

本章聚焦分域策略、生命周期一致性與事件收斂節奏。案例在問題觸發時作為證據參考。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[token-revocation]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「交接路由」欄位指向 `05-deployment-platform / 06-reliability / 08-incident-response`、接配置 / 驗證 / 處置交付。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

## 憑證治理模型

憑證治理的核心責任是讓每一種機器憑證都有清楚的用途邊界與收斂節奏。

1. 類型分層：區分應用程式 secret、存取 token、簽章 key、部署憑證。
2. 用途分域：區分讀取、寫入、管理操作的權限邊界。
3. 環境分域：區分開發、測試、正式環境，避免跨環境共用憑證。
4. 生命周期：定義發放、輪替、撤銷、淘汰的責任與時窗。
5. 事件收斂：定義外部事件後的內部權限回收與驗證流程。

## 判讀流程

判讀流程的責任是把「可用憑證」轉成「可控憑證」。

1. 先盤點憑證是否與服務邊界一致。
2. 再判讀憑證是否存在過寬 scope、過長 TTL 或過多共享。
3. 接著判讀事件發生後是否能在時限內完成撤銷與替換。
4. 最後把缺口路由到部署面、可靠性演練與 incident workflow。

## 問題節點（案例觸發式）

| 問題節點             | 判讀訊號                 | 風險後果                 | 前置控制面                                                                                                               | 交接路由  |
| -------------------- | ------------------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------------------ | --------- |
| token 分域不足       | 高權限 token 使用面過寬  | 外部事件可快速傳導       | [token-revocation](/backend/knowledge-cards/token-revocation/)、[authorization](/backend/knowledge-cards/authorization/) | `08`      |
| CI secrets 集中      | 單一節點承載大量憑證     | 輪替成本與中斷風險上升   | [secret-management](/backend/knowledge-cards/secret-management/)、[ci-pipeline](/backend/knowledge-cards/ci-pipeline/)   | `05 + 06` |
| 憑證生命周期失衡     | 發放、更新、撤銷節奏分離 | 可用憑證存量高於收斂速度 | [credential](/backend/knowledge-cards/credential/)、[containment](/backend/knowledge-cards/containment/)                 | `06 + 08` |
| 供應商事件傳導未收斂 | 外部事件後內部憑證仍活躍 | 內部風險延長停留         | [incident-timeline](/backend/knowledge-cards/incident-timeline/)、[impact-scope](/backend/knowledge-cards/impact-scope/) | `08`      |

## 常見風險邊界

風險邊界的責任是定義何時要把憑證管理從日常維運升級成事件處置。

- 同一 token 在多服務、多環境長期可用時，代表分域策略已鬆動。
- CI 節點可同時取得大量正式環境 secrets 時，代表供應鏈傳導半徑過大。
- 事件公告後舊憑證仍可持續使用時，代表撤銷節奏落後於攻擊節奏。
- 憑證輪替缺乏回退驗證時，代表可用性與安全性同時承壓。

## 案例觸發參考

案例觸發的責任是檢查憑證治理是否具備現實抗壓能力。

- CI secrets 事件與輪替壓力： [CircleCI 2023](/backend/07-security-data-protection/red-team/cases/supply-chain/circleci-2023-secrets-rotation/)
- 第三方身分鏈導致內部風險傳導： [Okta + Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- 開源供應鏈長期滲透壓力： [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)

## 下一步路由

- 交付與執行環境：`05-deployment-platform`
- 輪替與回退演練：`06-reliability`
- 事件收斂與通報：`08-incident-response`
