---
title: "模組七：資安與資料保護"
date: 2026-04-23
description: "整理權限分級、伺服器防護、紅隊驗證、資料遮罩、傳輸保護、密鑰管理與稽核追蹤"
weight: 7
---

資安與資料保護模組的核心目標是把安全需求轉成可設計、可測試、可稽核的服務邊界。語言教材會處理 [Request Middleware](../knowledge-cards/middleware/)、error response、資料模型、測試替身與輸入驗證；本模組負責 [authorization](../knowledge-cards/authorization/)、資料分級、[TLS / mTLS](../knowledge-cards/tls-mtls/)、[website certificate lifecycle](../knowledge-cards/website-certificate-lifecycle/)、[secret management](../knowledge-cards/secret-management/)、[data masking](../knowledge-cards/data-masking/)、[audit log](../knowledge-cards/audit-log/) 與伺服器防護、紅隊驗證的選型語意。

## 暫定分類

| 分類                 | 內容方向                                                                                                                                                                                                                                                                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Identity and access  | [authentication](../knowledge-cards/authentication/)、[authorization](../knowledge-cards/authorization/)、[tenant boundary](../knowledge-cards/tenant-boundary/)                                                                                                                                                                                                                                                                                                         |
| Server protection    | [rate limit](../knowledge-cards/rate-limit/)、[WAF](../knowledge-cards/waf/)、[Admin Endpoint](../knowledge-cards/admin-endpoint/)、upload boundary、[webhook](../knowledge-cards/webhook) signature                                                                                                                                                                                                                                                                                                |
| [Red team validation](red-team/)  | [Attack Surface](../knowledge-cards/attack-surface/)、[Trust Boundary](../knowledge-cards/trust-boundary/)、[Abuse Case](../knowledge-cards/abuse-case/)、exposure path、resource abuse                                                                                                                                                                                                                                                                                                         |
| [Data masking](../knowledge-cards/data-masking)         | export masking、[log](../knowledge-cards/log) redaction、test data anonymization、field-level policy                                                                                                                                                                                                                                                                                         |
| Transport protection | [TLS / mTLS](../knowledge-cards/tls-mtls/)、signed request、[website certificate lifecycle](../knowledge-cards/website-certificate-lifecycle/)、[ACME automation](../knowledge-cards/acme-automation/)、[certificate rotation and renewal](../knowledge-cards/certificate-rotation-renewal/)、[certificate revocation](../knowledge-cards/certificate-revocation/) |
| Secrets management   | secret storage、key rotation、[credential](../knowledge-cards/credential/) scope、revocation                                                                                                                                                                                                                                                                                                         |
| Audit trail          | admin action、data export、permission change、compliance record                                                                                                                                                                                                                                                                                                    |

## 選型入口

資安選型的核心判斷是先看資料等級、角色風險與暴露路徑。權限模型解決誰能操作什麼；伺服器防護解決入口如何降低攻擊面；資料遮罩解決敏感資訊如何在畫面、匯出、log 與測試資料中被控制；傳輸保護解決資料跨邊界流動；秘密管理解決 token、key 與 [website certificate lifecycle](../knowledge-cards/website-certificate-lifecycle/)；稽核追蹤解決高風險操作的事後責任判斷。

接近真實網路服務的例子包括客服查詢個資、管理員調整權限、使用者匯出訂單、第三方 webhook 進站、service-to-service 呼叫、API key 輪替、網站憑證 [rotation and renewal](../knowledge-cards/certificate-rotation-renewal/) 與高風險操作審核。這些場景的共同問題是資料與操作都需要被授權、保護、記錄與驗證。

從紅隊角度看，這些場景還要再反問一次：哪個入口最容易被枚舉、哪個邊界最容易被跨越、哪個流程最容易被合法功能包裝成濫用、哪個資料流最容易被帶出系統。這一層會先放在紅隊子分類裡處理。

## 與語言教材的分工

語言教材處理程式內如何表達安全邊界，例如 [Request Middleware](../knowledge-cards/middleware/)、handler、policy interface、error mapping、資料遮罩 helper 與測試案例。Backend security 模組處理安全需求如何對應到身份、權限、網路入口、加密、秘密管理、資料匯出與稽核系統。

## 相關需求章節

- [後端服務選型：資安與資料保護需求](../00-service-selection/security-data-protection-requirements/)
- [後端服務選型：錯誤定位、觀測訊號與備援切換設計](../00-service-selection/failure-observability-design/)
- [可觀測性平台](../04-observability/)
- [部署平台與網路入口](../05-deployment-platform/)

## 紅隊子分類

- [7.1 紅隊與攻擊面驗證](red-team/)

## 章節列表

本模組先建立分類入口。後續章節會在需求討論完成後，再依權限模型、資料遮罩、傳輸保護、秘密管理、伺服器防護、紅隊驗證與稽核追蹤拆分。
