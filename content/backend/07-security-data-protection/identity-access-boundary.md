---
title: "7.2 身分與授權邊界"
date: 2026-04-24
description: "以問題驅動方式整理身份、授權、會話與供應商身分鏈"
weight: 72
---

本章的責任是把「誰可以做什麼」拆成可驗證的邊界模型，讓團隊在功能上線前就能判讀身份擴散與授權濫用風險。

## 本章寫作邊界

本章聚焦概念層判讀，主體是問題節點、訊號、風險與路由條件。案例在問題被觸發時提供證據參考，不作章節主體。

## 身分與授權邊界模型

身分邊界的核心責任是定義「登入主體是否可信」，授權邊界的核心責任是定義「可信主體可以觸及哪些能力」。兩者需要分開治理，才能避免認證成功就直接等於高權限存取。

1. 身分層：驗證主體真實性與登入情境風險，重點是強認證、裝置信任、異常行為判讀。
2. 授權層：驗證操作是否符合最小權限，重點是 scope、角色、資源邊界與操作條件。
3. 會話層：驗證授權是否在有效時窗內，重點是 token 壽命、失效節奏與事件後收斂。
4. 供應商層：驗證第三方身分鏈是否可控，重點是外部事件後的內部權限收斂能力。

## 判讀流程

判讀流程的責任是把「身份異常」快速轉成「控制面動作」。

1. 先判斷異常發生在身分層、授權層、會話層或供應商層。
2. 再判斷是單點異常還是可擴散異常。
3. 接著啟動對應收斂動作：限制登入、縮權、失效會話、停用外部 token。
4. 最後交接到部署、可靠性與 incident workflow，讓處置可追蹤且可驗證。

## 問題節點（案例觸發式）

| 問題節點         | 判讀訊號                                   | 風險後果                 | 前置控制面                                                                                                                             | 交接路由               |
| ---------------- | ------------------------------------------ | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| 登入驗證節奏失衡 | 異常驗證密度、異常地理切換、連續高風險操作 | 身分擴散速度提升         | [authentication](/backend/knowledge-cards/authentication/)、[incident-severity](/backend/knowledge-cards/incident-severity/)           | `08 incident response` |
| 授權範圍擴張過快 | 高權限操作集中、代理操作鏈過長             | 權限濫用影響面擴大       | [authorization](/backend/knowledge-cards/authorization/)、[least-privilege](/backend/knowledge-cards/least-privilege/)                 | `08 incident response` |
| 會話失效節奏落後 | 修補後異常 session 持續、token 存續過久    | 事件關閉時間延長         | [session-invalidation](/backend/knowledge-cards/session-invalidation/)、[token-revocation](/backend/knowledge-cards/token-revocation/) | `08 + 05`              |
| 供應商身分鏈傳導 | 外部事件後內部憑證存續比例偏高             | 內部信任邊界承受外部衝擊 | [credential](/backend/knowledge-cards/credential/)、[containment](/backend/knowledge-cards/containment/)                               | `08 + 06`              |

## 常見風險邊界

風險邊界的責任是界定何時需要從一般維運升級到事件處置。

- 同一身分在短時間跨區、跨裝置、跨高權限路徑操作時，應視為可擴散事件。
- 高權限代理操作沒有獨立審核或時間限制時，應視為授權模型失衡。
- 修補或公告後仍有舊 token 持續可用時，應視為會話收斂失敗。
- 供應商事件後內部權限沒有分域回收時，應視為外部風險傳導未隔離。

## 案例觸發參考

案例觸發的責任是提供反向驗證，確認控制面是否足夠。

- MFA 疲勞與內部工具擴散： [Uber 2022](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)
- 第三方身分鏈事件： [Okta + Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- token 事件後橫向擴散： [Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/)

## 下一步路由

- 入口與平台實體：`05-deployment-platform`
- 驗證與回復節奏：`06-reliability`
- 事件分級與收斂：`08-incident-response`
