---
title: "7.6 秘密管理與機器憑證治理"
date: 2026-04-24
description: "大綱稿：以問題驅動方式整理 secret、token、key 與機器身份治理"
weight: 76
---

本章的責任是定義秘密管理與機器憑證問題節點，讓機器身份風險能以分域語言被清楚治理。

## 本章寫作邊界

本章聚焦分域策略、生命周期一致性與事件收斂節奏。案例在問題觸發時作為證據參考。

## 大綱（待填充）

1. 憑證分類與責任分層
2. 分域策略（用途、環境、權限）
3. 輪替、撤銷、淘汰節奏
4. 供應商事件傳導治理
5. 機器身份盤點與收斂
6. 交接路由到 05/06/08

## 問題節點（案例觸發式）

| 問題節點             | 判讀訊號                 | 風險後果                 | 前置控制面                                                                                                   | 交接路由  |
| -------------------- | ------------------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------ | --------- |
| token 分域不足       | 高權限 token 使用面過寬  | 外部事件可快速傳導       | [token-revocation](../knowledge-cards/token-revocation/)、[authorization](../knowledge-cards/authorization/) | `08`      |
| CI secrets 集中      | 單一節點承載大量憑證     | 輪替成本與中斷風險上升   | [secret-management](../knowledge-cards/secret-management/)、[ci-pipeline](../knowledge-cards/ci-pipeline/)   | `05 + 06` |
| 憑證生命周期失衡     | 發放、更新、撤銷節奏分離 | 可用憑證存量高於收斂速度 | [credential](../knowledge-cards/credential/)、[containment](../knowledge-cards/containment/)                 | `06 + 08` |
| 供應商事件傳導未收斂 | 外部事件後內部憑證仍活躍 | 內部風險延長停留         | [incident-timeline](../knowledge-cards/incident-timeline/)、[impact-scope](../knowledge-cards/impact-scope/) | `08`      |

## 下一步路由

- 交付與執行環境：`05-deployment-platform`
- 輪替與回退演練：`06-reliability`
- 事件收斂與通報：`08-incident-response`
