---
title: "模組七：資安與資料保護"
date: 2026-04-23
description: "整理權限分級、伺服器防護、資料遮罩、傳輸保護、密鑰管理與稽核追蹤"
weight: 7
---

資安與資料保護模組的核心目標是把安全需求轉成可設計、可測試、可稽核的服務邊界。語言教材會處理 middleware、error response、資料模型、測試替身與輸入驗證；本模組負責 [authorization](../00-knowledge-cards/authorization/)、資料分級、[TLS / mTLS](../00-knowledge-cards/tls-mtls/)、[website certificate lifecycle](../00-knowledge-cards/website-certificate-lifecycle/)、[secret management](../00-knowledge-cards/secret-management/)、[data masking](../00-knowledge-cards/data-masking/)、[audit log](../00-knowledge-cards/audit-log/) 與伺服器防護的選型語意。

## 暫定分類

| 分類                 | 內容方向                                                                                                                                                                                                                                                                                                                                                                          |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity and access  | authentication、authorization、RBAC、ABAC、tenant boundary                                                                                                                                                                                                                                                                                                                        |
| Server protection    | rate limit、WAF、admin endpoint、upload boundary、webhook signature                                                                                                                                                                                                                                                                                                               |
| Data masking         | export masking、log redaction、test data anonymization、field-level policy                                                                                                                                                                                                                                                                                                        |
| Transport protection | [TLS / mTLS](../00-knowledge-cards/tls-mtls/)、signed request、[website certificate lifecycle](../00-knowledge-cards/website-certificate-lifecycle/)、[ACME automation](../00-knowledge-cards/acme-automation/)、[certificate rotation and renewal](../00-knowledge-cards/certificate-rotation-renewal/)、[certificate revocation](../00-knowledge-cards/certificate-revocation/) |
| Secrets management   | secret storage、key rotation、credential scope、revocation                                                                                                                                                                                                                                                                                                                        |
| Audit trail          | admin action、data export、permission change、compliance record                                                                                                                                                                                                                                                                                                                   |

## 選型入口

資安選型的核心判斷是先看資料等級、角色風險與暴露路徑。權限模型解決誰能操作什麼；伺服器防護解決入口如何降低攻擊面；資料遮罩解決敏感資訊如何在畫面、匯出、log 與測試資料中被控制；傳輸保護解決資料跨邊界流動；秘密管理解決 token、key 與 [website certificate lifecycle](../00-knowledge-cards/website-certificate-lifecycle/)；稽核追蹤解決高風險操作的事後責任判斷。

接近真實網路服務的例子包括客服查詢個資、管理員調整權限、使用者匯出訂單、第三方 webhook 進站、service-to-service 呼叫、API key 輪替、網站憑證 [rotation and renewal](../00-knowledge-cards/certificate-rotation-renewal/) 與高風險操作審核。這些場景的共同問題是資料與操作都需要被授權、保護、記錄與驗證。

## 與語言教材的分工

語言教材處理程式內如何表達安全邊界，例如 middleware、handler、policy interface、error mapping、資料遮罩 helper 與測試案例。Backend security 模組處理安全需求如何對應到身份、權限、網路入口、加密、秘密管理、資料匯出與稽核系統。

## 相關需求章節

- [後端服務選型：資安與資料保護需求](../00-service-selection/security-data-protection-requirements/)
- [後端服務選型：錯誤定位、觀測訊號與備援切換設計](../00-service-selection/failure-observability-design/)
- [可觀測性平台](../04-observability/)
- [部署平台與網路入口](../05-deployment-platform/)

## 章節列表

本模組先建立分類入口。後續章節會在需求討論完成後，再依權限模型、資料遮罩、傳輸保護、秘密管理、伺服器防護與稽核追蹤拆分。
