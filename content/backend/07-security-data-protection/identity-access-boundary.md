---
title: "7.2 身分與授權邊界"
date: 2026-04-24
description: "大綱稿：以問題驅動方式整理身份、授權、會話與供應商身分鏈"
weight: 72
---

本章的責任是定義身分與授權問題節點，讓團隊先對齊判讀語言，再進入服務實體設計。

## 本章寫作邊界

本章聚焦概念層判讀，主體是問題節點、訊號、風險與路由條件。案例在問題被觸發時提供證據參考，不作章節主體。

## 大綱（待填充）

1. 身分邊界模型
2. 授權邊界模型
3. 會話與 token 收斂節奏
4. 第三方身分傳導風險
5. 問題節點判讀流程
6. 交接路由到 05/06/08

## 問題節點（案例觸發式）

| 問題節點         | 判讀訊號                                   | 風險後果                 | 前置控制面                                                                                                                       | 交接路由               |
| ---------------- | ------------------------------------------ | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| 登入驗證節奏失衡 | 異常驗證密度、異常地理切換、連續高風險操作 | 身分擴散速度提升         | [authentication](../../knowledge-cards/authentication/)、[incident-severity](../../knowledge-cards/incident-severity/)           | `08 incident response` |
| 授權範圍擴張過快 | 高權限操作集中、代理操作鏈過長             | 權限濫用影響面擴大       | [authorization](../../knowledge-cards/authorization/)、[least-privilege](../../knowledge-cards/least-privilege/)                 | `08 incident response` |
| 會話失效節奏落後 | 修補後異常 session 持續、token 存續過久    | 事件關閉時間延長         | [session-invalidation](../../knowledge-cards/session-invalidation/)、[token-revocation](../../knowledge-cards/token-revocation/) | `08 + 05`              |
| 供應商身分鏈傳導 | 外部事件後內部憑證存續比例偏高             | 內部信任邊界承受外部衝擊 | [credential](../../knowledge-cards/credential/)、[containment](../../knowledge-cards/containment/)                               | `08 + 06`              |

## 下一步路由

- 入口與平台實體：`05-deployment-platform`
- 驗證與回復節奏：`06-reliability`
- 事件分級與收斂：`08-incident-response`
