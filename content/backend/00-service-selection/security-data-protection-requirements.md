---
title: "0.8 資安與資料保護需求"
date: 2026-04-23
description: "從權限分級、伺服器防護、資料遮罩、傳輸保護與稽核設計安全邊界"
weight: 8
---

資安需求分析的核心原則是先定義安全邊界，再選擇安全工具。權限分級、伺服器防護、資料匯出遮罩、傳輸加密、稽核紀錄與密鑰管理都服務同一個目標：讓資料與操作只在被授權、可追蹤、可控的路徑中流動。

## 本章目標

學完本章後，你將能夠：

1. 用資料分級與角色分級描述安全需求
2. 判斷服務入口、內部通訊與資料匯出需要哪些保護
3. 區分權限控制、資料遮罩、傳輸保護、伺服器防護與稽核需求
4. 把資安需求連到後續安全與資料保護模組

---

## 【觀察】資安需求來自資料、角色與路徑

資安設計的第一個問題是「誰在什麼路徑上接觸什麼資料」。同一個系統可能同時有使用者、客服、營運、工程師、背景 worker、外部合作方與管理員；每個角色需要的資料、操作與稽核等級都不同。

| 需求類型   | 核心問題                                                                          | 常見情境                                                                                                                                                     |
| ---------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 權限分級   | 誰能看、改、匯出、審核或管理資料                                                  | [authorization](../knowledge-cards/authorization/)、[tenant boundary](../knowledge-cards/tenant-boundary/)                                                   |
| 伺服器防護 | 哪些入口要限制來源、速率與攻擊面                                                  | [Admin Endpoint](../knowledge-cards/admin-endpoint/)、upload、[webhook](../knowledge-cards/webhook/)、[WAF](../knowledge-cards/waf/)                         |
| 資料遮罩   | 匯出、[log](../knowledge-cards/log)、客服畫面要顯示多少敏感資訊                   | email、電話、身分證、付款資訊                                                                                                                                |
| 傳輸保護   | 資料在 client、service、[queue](../knowledge-cards/queue)、storage 之間如何被保護 | [TLS / mTLS](../knowledge-cards/tls-mtls/)、signed request、[certificate chain and trust root](../knowledge-cards/certificate-chain-trust/)                  |
| 密鑰與秘密 | token、API key、憑證如何保存、輪替與撤銷                                          | [Secret Management](../knowledge-cards/secret-management/)、[Website Certificate Lifecycle](../knowledge-cards/website-certificate-lifecycle/)、key rotation |
| 稽核追蹤   | 高風險操作是否能被追蹤與事後審查                                                  | [audit log](../knowledge-cards/audit-log)、approval、admin action                                                                                            |

這張表是需求索引。資安討論要先定義資料與操作的保護等級，再決定具體平台、服務或產品。

## 【判讀】權限分級要從角色與資料責任開始

權限分級的核心責任是控制角色能執行哪些操作。常見模型包括依角色授權、依屬性授權、依 tenant 隔離與依資源 owner 判斷；選型前要先定義資料責任與操作風險。

接近真實網路服務的例子包括：

- 客服可以查看訂單狀態與配送資訊，但付款敏感欄位只顯示遮罩版本。
- 營運可以調整活動商品，但價格變更需要主管審核。
- 企業 [SaaS](../knowledge-cards/tenant-boundary/) 中，workspace admin 可以管理成員，普通 member 只能操作自己有權限的 project。

這類需求的陷阱是只用「是否登入」表示授權。登入代表身份已被確認；授權要回答這個身份能否操作特定資源、特定欄位與特定動作。權限規則也要能被測試、稽核與解釋。

下一步可讀：[資安與資料保護](../07-security-data-protection/)。

## 【判讀】伺服器防護要先找暴露入口

伺服器防護的核心責任是降低服務入口的攻擊面。Public API、[Admin Endpoint](../knowledge-cards/admin-endpoint/)、[webhook](../knowledge-cards/webhook/)、file upload、public asset、[Diagnostic Endpoint](../knowledge-cards/diagnostic-endpoint/) 與 [Internal Endpoint](../knowledge-cards/internal-endpoint/) 都有不同暴露程度。

接近真實網路服務的例子包括：

- [webhook](../knowledge-cards/webhook/) 需要驗證來源簽章、限制重放時間窗，並記錄來源系統。
- [Admin Endpoint](../knowledge-cards/admin-endpoint/) 需要更高權限、來源限制與操作稽核。
- file upload 需要限制大小、型別、掃描結果與後續存取權限。

這類需求的陷阱是把所有 HTTP 入口視為同一種入口。公開 API、內部 API、診斷 API、管理 API 與第三方 callback 的風險不同；防護策略要依入口用途分級。

下一步可讀：[部署平台與網路入口](../05-deployment-platform/) 與 [資安與資料保護](../07-security-data-protection/)。

## 【判讀】資料遮罩要依使用情境分級

資料遮罩的核心責任是讓使用者完成工作，同時降低敏感資料暴露。遮罩可能發生在客服畫面、匯出報表、log、debug payload、analytics dataset、測試資料與外部分享檔案。

接近真實網路服務的例子包括：

- 客服查會員資料時，只顯示電話末三碼與 email 部分字元。
- 匯出訂單報表時，付款識別碼保留交易對帳所需欄位，個資欄位轉為遮罩值。
- 開發環境使用脫敏資料集，保留資料形狀與關聯，但移除真實身份資訊。

這類需求的陷阱是把遮罩視為顯示層問題。資料可能流入匯出、log、queue、搜尋索引、分析資料集與備份；遮罩策略要定義在資料流路徑上，而非只套在單一頁面。

下一步可讀：[資安與資料保護](../07-security-data-protection/) 與 [可觀測性平台](../04-observability/)。

## 【判讀】傳輸保護要覆蓋跨邊界流動

傳輸保護的核心責任是保護資料跨越邊界時的機密性、完整性與來源可信度。邊界可能是 client 到 API、service 到 service、worker 到 [broker](../knowledge-cards/broker)、service 到 [database](../knowledge-cards/database)、系統到第三方。

接近真實網路服務的例子包括：

- client 到 API 使用 [TLS](../knowledge-cards/tls-mtls/)，避免帳號資料在網路中被竊聽。
- service 到 service 使用 [mTLS](../knowledge-cards/tls-mtls/) 或 signed request，確認呼叫來源與訊息完整性。
- [webhook](../knowledge-cards/webhook/) callback 驗證簽章與 timestamp，降低偽造與重放風險。

這類需求的陷阱是只保護公開入口。內部網路、queue message、[object storage](../knowledge-cards/object-storage/) link、backup transfer 與第三方 callback 都是資料流動路徑；傳輸保護要依邊界與資料等級設定。

下一步可讀：[部署平台與網路入口](../05-deployment-platform/) 與 [資安與資料保護](../07-security-data-protection/)。

## 【判讀】密鑰與秘密管理要設計生命週期

密鑰與秘密管理的核心責任是控制 token、API key、private key、database [Credential](../knowledge-cards/credential/)、session secret 與加密 key 的產生、保存、使用、輪替與撤銷，並把網站憑證納入 [Website Certificate Lifecycle](../knowledge-cards/website-certificate-lifecycle/)。

接近真實網路服務的例子包括：

- 第三方 API key 需要分環境保存，並能在外洩時快速撤銷。
- database [credential](../knowledge-cards/credential/) 需要依服務分離，避免單一 [credential](../knowledge-cards/credential/) 擁有過大權限。
- 簽章密鑰需要支援輪替期，讓新舊 key 在過渡期間都能驗證。
- 公網站點憑證需要有 [ACME automation](../knowledge-cards/acme-automation/) 或明確續期流程，並具備 [certificate revocation](../knowledge-cards/certificate-revocation/) 設計。

這類需求的陷阱是把秘密寫進設定檔、log、測試資料或部署指令。秘密管理要同時包含保存位置、存取權限、輪替流程、撤銷流程、憑證續期流程與稽核紀錄。

下一步可讀：[資安與資料保護](../07-security-data-protection/)。

## 【判讀】稽核追蹤要服務事後責任判斷

稽核追蹤的核心責任是回答「誰在何時對哪個資源做了什麼，理由與結果是什麼」。高風險操作、管理員操作、資料匯出、權限變更、金流狀態修改都需要清楚 [audit log](../knowledge-cards/audit-log/)。

接近真實網路服務的例子包括：

- 管理員修改使用者角色時，記錄操作者、目標使用者、舊角色、新角色與工單 ID。
- 客服匯出訂單資料時，記錄查詢條件、匯出欄位、資料量與核准者。
- 系統輪替 API key 時，記錄 key id、使用服務、輪替時間與生效狀態。

這類需求的陷阱是把 audit log 和 debug log 混在一起。debug log 服務排障，audit log 服務責任判斷；audit log 需要更穩定的 schema、保存策略、存取權限與完整性保護。

下一步可讀：[資安與資料保護](../07-security-data-protection/) 與 [可觀測性平台](../04-observability/)。

## 【檢查】進入實作前的概念邊界清單

當以下問題都能回答時，代表本章的概念層已完成，可以進入資安與資料保護實作章節：

1. 資料分級與角色責任是否明確（誰可讀、可改、可匯出）
2. 資料流路徑是否明確（client、service、queue、storage）
3. 秘密與憑證生命週期是否明確（保存、輪替、撤銷、續期）
4. 稽核與事故追蹤要求是否明確（audit 欄位、保存、查核流程）

下一步建議路由：

- [07-security-data-protection](../07-security-data-protection/)
- [08-incident-response](../08-incident-response/)

## 小結

資安與資料保護要從資料、角色與路徑開始。權限分級控制誰能操作什麼，伺服器防護降低暴露入口風險，資料遮罩降低敏感資訊外流，傳輸保護保障跨邊界流動，密鑰管理控制秘密生命週期，稽核追蹤支援事後責任判斷。這些需求清楚後，後續才進入具體安全服務與平台能力。
