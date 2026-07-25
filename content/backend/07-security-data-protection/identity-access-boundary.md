---
title: "7.2 身分與授權邊界"
date: 2026-04-24
description: "以問題驅動方式整理身分、授權、會話與供應商身分鏈"
weight: 72
tags: ["backend", "security"]
---

本章的責任是把「誰可以做什麼」拆成可驗證的邊界模型，讓團隊在功能上線前就能判讀身分擴散與授權濫用風險。

## 本章寫作邊界

本章聚焦概念層判讀，主體是問題節點、訊號、風險與路由條件。案例在問題被觸發時提供證據參考，不作章節主體。

## 讀者路由

個人自架工具場景（從 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) 導過來）直接看[單人裝置認證模型](#單人裝置認證模型)段。多人 SaaS 場景從[身分與授權邊界模型](#身分與授權邊界模型)段開始。

## 本章 threat scope

**In-scope**：credential brute force / credential stuffing / phishing 與 MFA fatigue / privilege escalation / session hijacking / 供應商身分鏈傳導 / insider abuse / 過寬授權範圍 / 單人裝置認證邊界轉移。

**Out-of-scope**（路由到他章）：

- 入口暴露面 → [7.3](../entrypoint-and-server-protection/)
- 資料外洩 → [7.4](../data-protection-and-masking-governance/)
- 傳輸 / 憑證信任 → [7.5](../transport-trust-and-certificate-lifecycle/)
- 機器憑證 → [7.6](../secrets-and-machine-credential-governance/)
- [workload identity](/backend/knowledge-cards/workload-identity/) → [7.10](../workload-identity-and-federated-trust/)
- 偵測訊號 → [7.13](../detection-coverage-and-signal-governance/)
- 偵測平台 → `04-observability`、實作交付 → `05` / `06` / `08`

Reader 對 in-scope 列表的 specific threat 應該能反向 trace 到本章問題節點；out-of-scope 議題請直接跳到對應章節、不在本章 audit 範圍。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[authentication]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「交接路由」欄位指向 `05-deployment-platform / 06-reliability / 08-incident-response`、接配置 / 驗證 / 處置交付。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

## 身分與授權邊界模型

身分邊界的核心責任是定義「登入主體是否可信」，授權邊界的核心責任是定義「可信主體可以觸及哪些能力」。兩者需要分開治理，才能避免認證成功就直接等於高權限存取。

1. 身分層：驗證主體真實性與登入情境風險，重點是強認證、裝置信任、異常行為判讀。
2. 授權層：驗證操作是否符合最小權限，重點是 scope、角色、資源邊界與操作條件。
3. 授權有時間邊界 — 會話層驗證授權是否在有效時窗內，重點是 token 壽命、失效節奏與事件後收斂。
4. 信任不止內部 — 供應商層驗證第三方身分鏈是否可控，重點是外部事件後的內部權限收斂能力。

## 判讀流程

判讀流程的責任是把「身分異常」快速轉成「控制面動作」。

1. 先判斷異常發生在身分層、授權層、會話層或供應商層。
2. 再判斷是單點異常還是可擴散異常。
3. 接著啟動對應收斂動作：限制登入、縮權、失效會話、停用外部 token。
4. 最後交接到部署、可靠性與 incident workflow，讓處置可追蹤且可驗證。

## 問題節點（案例觸發式）

| 問題節點             | 判讀訊號                                                          | 風險後果                                 | 前置控制面                                                                                                                             | 交接路由               |
| -------------------- | ----------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| 登入驗證節奏失衡     | 異常驗證密度、異常地理切換、連續高風險操作                        | 身分擴散速度提升                         | [authentication](/backend/knowledge-cards/authentication/)、[incident-severity](/backend/knowledge-cards/incident-severity/)           | `08 incident response` |
| 授權範圍擴張過快     | 高權限操作集中、代理操作鏈過長                                    | 權限濫用影響面擴大                       | [authorization](/backend/knowledge-cards/authorization/)、[least-privilege](/backend/knowledge-cards/least-privilege/)                 | `08 incident response` |
| 會話失效節奏落後     | 修補後異常 session 持續、token 存續過久                           | 事件關閉時間延長                         | [session-invalidation](/backend/knowledge-cards/session-invalidation/)、[token-revocation](/backend/knowledge-cards/token-revocation/) | `08 + 05`              |
| 供應商身分鏈傳導     | 外部事件後內部憑證存續比例偏高                                    | 內部信任邊界承受外部衝擊                 | [credential](/backend/knowledge-cards/credential/)、[containment](/backend/knowledge-cards/containment/)                               | `08 + 06`              |
| 單人裝置認證邊界轉移 | device 失竊後生物辨識可繞過、共享密鑰存本機、無中央會話可遠端失效 | 認證邊界落在 device 層、單點失效即全失效 | [authentication](/backend/knowledge-cards/authentication/)、裝置綁定 + 共享密鑰                                                        | `05 + 08`              |

## 跨章 SSoT：供應商身分鏈傳導

本章「供應商身分鏈傳導」問題節點是跨章 SSoT——其他章節從不同 layer 補同議題的 specific 訊號：

- [7.5 第三方信任重評估延遲](../transport-trust-and-certificate-lifecycle/)：傳輸層的 specific 訊號（憑證收斂滯後）
- [7.6 供應商事件傳導未收斂](../secrets-and-machine-credential-governance/)：機器憑證層的 specific 訊號（憑證仍活躍）
- [7.10 第三方授權範圍跟事件傳導半徑](../workload-identity-and-federated-trust/#第三方授權範圍跟事件傳導半徑)：workload identity 層的 specific 訊號（[federation](/backend/knowledge-cards/federation/) token scope 過寬）

本章視角聚焦客戶側人類身分鏈收斂責任；workload identity 層的 federation token scope 視角見 7.10。跨章 audit 時、本條為 canonical 定義（threat scope / mitigation chain），其他章補 layer 視角差異。

## MFA fatigue 與 step-up 驗證

MFA fatigue 是身分層擴散風險的代表機制：登入挑戰可被使用者連續同意，攻擊者把「使用者誤點」當成唯一所需的人類動作。要解這個機制要拉開兩層判讀，登入層放強認證、操作層放 [step-up](/backend/knowledge-cards/step-up-authentication/) 驗證，避免認證成功直接等於高權限存取。

對應 [Uber 2022](../red-team/cases/identity-access/uber-2022-mfa-fatigue/)：揭露三個失效控制面 — 高風險登入路徑缺 step-up、內部工具授權邊界不足（初始落點可快速擴散）、身分異常事件與值班告警串接不足。案例的「可落地檢查點」段把對應 mechanism 標明為 phishing-resistant 強認證（WebAuthn / passkey）+ 裝置信任綁定（managed device / posture check）、屬於案例直接可引用範圍。

以下基於通用工程知識補充：強認證跟裝置綁定是 mechanism 雙軌、缺一不可。只做強認證不綁裝置、攻擊者仍可在受感染端點繼承會話；只綁裝置不強化認證、社交工程仍可繞過。判讀升級條件是「短時間 MFA 請求密度異常」要走 [on-call](/backend/knowledge-cards/on-call/) 升級、不是當一般使用者支援處理。

## 高權限工具的會話收斂節奏

身分被取得後、token 撤銷跟 session kill 的時間窗口直接決定攻擊者可觸及的資產面積、是初始落點橫向擴散的關鍵節流點。這層治理跟登入驗證是兩條獨立 chain，前者管「入場」、後者管「停留」。會話收斂節奏的 canonical 在 [7.5 § 會話重放跟全域失效](../transport-trust-and-certificate-lifecycle/#會話重放跟全域失效canonical)、本節從身分層補 token 撤銷窗口的 specific 訊號。

對應 [Slack 2022](../red-team/cases/identity-access/slack-2022-token-compromise/)：揭露三層失效控制面 — 員工身分遭濫用後的隔離速度不足、token 範圍與用途邊界定義不夠細緻、程式碼資產存取異常訊號未快速匯流。本段聚焦的會話收斂視角直接對應前兩層、訊號匯流層放 [7.7 audit-trail](../audit-trail-and-accountability-boundary/) 處理。案例「可落地檢查點」列出 mechanism 為「管理 token 分域並限制到最小權限、依用途切 audience」，並標明前提是「token 有 inventory 可查 issuer / scope」。

以下基於通用工程知識補充：token 分域要看可達的 trust boundary、權限等級只是其中一個維度。同樣是「管理 token」、跨多敏感系統的單一 token 跟限定單一 audience 的 token、[blast radius](/backend/knowledge-cards/blast-radius/) 差兩個數量級。日常治理要建立 token inventory（issuer / scope / blast radius 標籤）、事件時可直接按 blast radius 降序撤銷；inventory 缺位時排序退回 ad-hoc 判斷、容易把可用性跟風險同時打斷。

## 第三方身分鏈的內部收斂責任

第三方身分鏈傳導的控制責任由客戶側承擔。當供應商公開事件、內部要有獨立 runbook 讓「閱讀公告」直接 trigger「全域 token 盤點 + 分批輪替」、停留在資訊接收層會把外部風險變成內部事故。這個收斂節奏的快慢、決定供應商事件能維持在「外部新聞」、或升級成「內部事故」。

對應 [Okta + Cloudflare 2023](../red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)：揭露支援工作流層三層失效控制面 — 支援資料流沒被視為高敏感資產、憑證或會話資料生命周期管理不足、供應商事件到客戶內部輪替流程沒有強制觸發。同事件鏈的 [Cloudflare 2023 follow-through](../red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/) 從客戶側補另外三層 — 供應商事件觸發條件與內部 runbook 連動不足、高權限 token 失效與輪替策略準備度不足、受影響資產盤點與證據保存流程分離。CF follow-through 案例「可落地檢查點」標明 mechanism 是讓供應商公告直接 trigger 內部盤點，並要求「輪替能力涵蓋第三方授權 token、不只內部 session」。

以下基於通用工程知識補充：第三方事件的判讀盲點是把控制責任當成廠商的事。廠商只能處理供應商側、客戶側的 token / session / 憑證仍是各組織自己的責任面。內部 runbook 要把「廠商公告」「客戶側盤點」「依範圍輪替」綁成一條 chain、不分先後執行；如果三件事都要等「下一步指引」、控制節奏會比攻擊節奏慢。

## 單人裝置認證模型

單人自用工具（遠端操控自己的主機、家庭自動化、個人備份）的認證不走 web-auth 光譜。沒有中央使用者資料庫、沒有 SSO、主體就是持有裝置的所有者，認證拆成兩層獨立 mechanism：

1. 裝置層：裝置原生生物辨識（Face ID / BiometricPrompt）認「人」、防的是裝置遺失後被他人直接操作。這一層沒有「異常驗證密度」「地理切換」的概念 — 判讀對象是裝置是否仍由所有者持有、不是 login anomaly。
2. 連線層：app 與服務端共享密鑰認「連線」、防的是拿到入口位址的外人。密鑰存裝置安全儲存（Keychain / Keystore）、不硬寫進 app（反編譯可挖）、配對走實體隔離通道（不經網路、改用 QR 掃描等實體方式傳輸密鑰）。

失效模型跟多人 SaaS 的「會話失效」不同。裝置失竊等於認證邊界整個失效（生物辨識可被繞過、共享密鑰就在本機）、且沒有中央會話可以遠端 kill;唯一的收斂手段是服務端輪替密鑰版本、讓舊裝置的密鑰失效（強迫重新配對）。所以前置控制面是「密鑰版本可遠端輪替」加「裝置清單」、而不是 session TTL。交接到 `05`（部署要支援密鑰版本變更的同步）與 `08`（事故時的裝置清查）。

這個模型的 tripwire 是使用者數從一變多。共享密鑰無法分辨是哪個使用者、生物辨識綁在單一裝置、沒有帳號就無法個別撤銷;第一個要分享存取的對象出現時、認證模型要升級回帳號系統。應用場景的判斷見 [0.21 個人自架工具](/backend/00-service-selection/delivery-mode-selection/#個人自架工具常駐本機無對外服務)。

## 常見風險邊界

風險邊界的責任是界定何時需要從一般維運升級到事件處置。

| 條件                                           | 應視為             |
| ---------------------------------------------- | ------------------ |
| 同一身分在短時間跨區、跨裝置、跨高權限路徑操作 | 可擴散事件         |
| 高權限代理操作沒有獨立審核或時間限制           | 授權模型失衡       |
| 修補或公告後仍有舊 token 持續可用              | 會話收斂失敗       |
| 供應商事件後內部權限沒有分域回收               | 外部風險傳導未隔離 |

## 案例觸發參考

案例觸發的責任是提供反向驗證，確認控制面是否足夠。

- MFA 疲勞與內部工具擴散： [Uber 2022](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)
- 第三方身分鏈事件： [Okta + Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- token 事件後橫向擴散： [Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/)

## 下一步路由

**多人 SaaS 場景**：

- 入口與平台實體：[05 部署平台](/backend/05-deployment-platform/)
- 驗證與回復節奏：[06 可靠性](/backend/06-reliability/)
- 事件分級與收斂：[08 事故回應](/backend/08-incident-response/)

**個人自架工具場景**：

- 回 [5.10 Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/) 確認 tunnel 之後的認證疊法
- 進 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 做入口威脅建模
- 判斷服務形態：回 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)
