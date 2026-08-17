---
title: "模組七：資安與資料保護"
tags: ["資安", "資料保護", "Security", "Data Protection"]
date: 2026-04-24
description: "以問題驅動方式擴充資安知識網：先定義服務環節問題，再以案例作為觸發式參考"
weight: 7
---

本模組的責任是把資安議題拆成可重用的問題節點。章節先定義問題、判讀訊號、風險邊界與路由條件，再由案例在需要時提供證據參考。

## 從需求進入

從需求面進入本模組、從 [0.8 資安與資料保護需求](/backend/00-service-selection/security-data-protection-requirements/) 開始——該章節定義六議題（權限分級 / 伺服器防護 / 資料遮罩 / 傳輸保護 / 密鑰與秘密 / 稽核追蹤）、各別 link 到本模組對應章節（7.2-7.7）。本模組是該六議題的 implementation-ready 層、提供問題節點、判讀訊號、風險邊界與交接路由。

## 模組方法

問題驅動方法的核心是讓案例退到證據角色，讓知識網以服務環節問題為主體。

1. 先定義服務環節問題與責任邊界。
2. 再定義判讀訊號與風險後果。
3. 接著定義交接路由與前置控制面。
4. 最後在問題觸發時引用對應案例。

## 模組分工定位

本模組提供觀念、判讀與路由。實作細節由對應模組承接，確保概念層與實作層分工清晰。

- `backend/04-observability`：偵測、稽核訊號、證據鏈與 alert / dashboard 實作。
- `backend/05-deployment-platform`：入口、部署與平台邊界實作。
- `backend/06-reliability`：驗證、回復與變更節奏實作。
- `backend/08-incident-response`：分級、指揮、通報與復盤實作。

## 案例驅動讀法

資安案例的核心讀法是先判斷事件發生在 identity、credential 還是 network [control plane](/backend/knowledge-cards/control-plane/)，再選擇對應治理控制。

| 案例                                                                                                                | 先看章節                                                                                                                                                                        | 回寫目標                                         |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [7.C1 Cloudflare：2026 Route Leak](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/)          | [7.14](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)、[7.3](/backend/07-security-data-protection/entrypoint-and-server-protection/)         | 把路由自動化風險轉成變更前守門與 tripwire        |
| [7.C2 Cloudflare：2023 Token 事件](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/) | [7.6](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[7.12](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) | 把 token 事件回寫到 machine credential lifecycle |
| [7.C3 Azure AD：2021 控制面事件](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)  | [7.2](/backend/07-security-data-protection/identity-access-boundary/)、[7.13](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)                   | 把身份控制面故障轉成依賴隔離與恢復優先序治理     |

反例與規模對照入口： [7.C9 反例](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) / [7.C10 對照](/backend/07-security-data-protection/cases/contrast-identity-governance-by-scale/)。

回退判讀寫法見 [0.C4 回退判讀寫法](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/#回退判讀寫法)，資安案例要優先保留身份作用域、憑證輪替、例外權限與控制面擴散條件。

## 從問題進入

進入點由手上的問題決定，各條路線的第一站與收尾的交接目標都不同。

**要做登入功能**：從 [7.31 認證方式選型](/backend/07-security-data-protection/authentication-approach-selection/) 起步，它決定身分自己管還是交給外部、以及自己管的話拿什麼驗證使用者。之後依答案分三條——自建加密碼接 [7.30 使用者密碼儲存](/backend/07-security-data-protection/password-storage-and-work-factor/)；用 passkey、安全金鑰或智慧卡接 [7.39 使用者持有型憑證](/backend/07-security-data-protection/user-held-credential-carrier/)；委派給外部身分提供者接 [7.38 外部身分與本地紀錄](/backend/07-security-data-protection/external-identity-local-record-lifecycle/)，而每個客戶各帶一組的 B2B 形態再接 [7.40 B2B 多租戶的身分接入](/backend/07-security-data-protection/multi-tenant-identity-onboarding/)。三條路徑共同的下一站有兩個：[7.36 憑證在請求中怎麼帶](/backend/07-security-data-protection/credential-transport-in-request/)（登入之後每個請求靠什麼帶身分）與 [7.42 密碼重設流程](/backend/07-security-data-protection/password-reset-flow/)（進不來的人怎麼回來）。兩題不論上面選了什麼都要答，而後者決定整個帳號的安全上限。

**要自己定一個對外介面**：先讀 [7.28 密碼學原語選型](/backend/07-security-data-protection/cryptographic-primitive-selection/) 判斷手上的機制擋得住誰，再讀 [7.29 API 認證的信任邊界分層](/backend/07-security-data-protection/api-authentication-trust-boundaries/) 確認呼叫方身分落在哪一層。判到系統層之後接 [7.34 機器憑證的機制選型](/backend/07-security-data-protection/machine-credential-mechanism-selection/) 決定用哪一種，再分兩條分支：那把憑證怎麼交到對方手上走 [7.32 機器憑證的配發](/backend/07-security-data-protection/machine-credential-issuance/)，而請求是「某個系統代表某個特定的人」時走 [7.33 委任型憑證](/backend/07-security-data-protection/delegated-credential-selection/)。最後依判斷結果路由到 7.6 的憑證治理或 7.2 的權限分級。

這條路線在純系統對系統的整合上可以跳過 7.28 的前半：它的五格金鑰位置有四格是客戶端應用與端對端加密的形態，這一類只落在「在雙方服務端」那一格，直接從 7.29 或 7.34 起步即可，要判斷原語類別時再回頭。

**要接第三方的 API**：順序與上一條相反，因為機制多半由對方的文件決定。先讀 [7.34 的「先確認自己有沒有選擇權」](/backend/07-security-data-protection/machine-credential-mechanism-selection/#先確認自己有沒有選擇權) 確認沒得選、以及沒得選時自己這一側還缺哪一塊，再讀 [7.32](/backend/07-security-data-protection/machine-credential-issuance/) 處理 key 怎麼拿到手——key 由對方後台自助取得時 7.32 只取登記那一段，交付通道那幾條不適用。要接對方的 webhook 推送時接著讀 [7.35 簽章對接的驗證收斂](/backend/07-security-data-protection/signature-integration-verification/)。7.29 只在請求同時牽涉多個身分維度時才進入。

**從對接失敗或原語誤用進入**：先在 [7.28](/backend/07-security-data-protection/cryptographic-primitive-selection/) 確認手上這個機制解的是哪一類問題（誤把訊息驗證當加密是最常見的一種），簽章對接本身對不起來的走 [7.35](/backend/07-security-data-protection/signature-integration-verification/)，撤銷或身分層次不對的走 [7.29](/backend/07-security-data-protection/api-authentication-trust-boundaries/)。

**外洩已經發生**：先分這是一個帳號還是一批。單一帳號被接管（有人來說登不進去、或系統偵測到異常）走 [7.41 單一帳號被接管](/backend/07-security-data-protection/single-account-takeover-response/)，它的困難在於求助者的身分本身待證。一批帳號這一側從 [7.37 密碼外洩之後](/backend/07-security-data-protection/credential-breach-response/) 起步——它處理的是範圍查不出來時怎麼分層定重設對象、撤銷與重設的先後，以及通知門檻要交付哪些事實。要判斷手上的密碼儲存撐不撐得住，接 [7.30 的升級路徑段](/backend/07-security-data-protection/password-storage-and-work-factor/#升級路徑)——它的第二條路徑是止血速度不由使用者回訪決定的那一條。憑證與 token 的止血範圍走 [7.6](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 的生命週期段——它回答的是能不能在時限內完成撤銷與替換。這件事要不要當事故啟動、算哪一級，判準在 [8.1 事故分級與啟動條件](/backend/08-incident-response/incident-severity-trigger/)；對外要不要通知、什麼時候通知在 [8.10 Stakeholder 通訊與外部狀態頁](/backend/08-incident-response/stakeholder-communication/)。

## 從章節到實作的 chain

各章節交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)、那層展開機制 / 邊界 / context-dependence。例：`[authentication]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組——`04-observability`（偵測 / 稽核 / 證據訊號）/ `05-deployment-platform`（入口 / 配置 / 平台邊界）/ `06-reliability`（驗證 / 回退 / 演練）/ `08-incident-response`（分級 / 指揮 / 通報 / 復盤）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

各章節在「從本章到實作」段給該章的具體 control-name 例子跟交接路由 list、本段是模組級的共用規格。

## Vendor / Platform 清單

資安控制服務見 [vendors](/backend/07-security-data-protection/vendors/) — 先以 index 大綱規劃身份、IAM、Secrets、KMS、WAF、PKI、供應鏈、SIEM 與 DLP 服務頁。這層目前只做服務頁教學大綱，不展開個別服務正文。

Deep article（vendor 自身的配置、故障、容量）跟 migration playbook（跨 vendor 遷移流程）的撰寫進度見 [vendors/](/backend/07-security-data-protection/vendors/) 的「內容覆蓋進度」段。

## 章節列表

| 章節                                                                                                                                        | 主題                                              | 核心責任                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| [7.1 攻擊者視角（紅隊）與攻擊面驗證](/backend/07-security-data-protection/red-team/)                                                        | 攻擊者判讀語言                                    | 把攻擊路徑轉成服務問題語言                                                                            |
| [7.B 防守者視角（藍隊）與控制面驗證](/backend/07-security-data-protection/blue-team/)                                                       | 防守者判讀語言                                    | 把資安風險轉成控制面、訊號與驗證流程                                                                  |
| [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)                                                        | Identity & Access                                 | 定義身份擴散、授權濫用、會話收斂問題                                                                  |
| [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)                                          | Entrypoint & Server                               | 定義入口暴露、管理面與修補窗口問題                                                                    |
| [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)                                      | Data Protection                                   | 定義資料暴露、匯出、備份與跨界交換問題                                                                |
| [7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)                               | Transport Trust                                   | 定義信任鏈、會話完整性與憑證節奏問題                                                                  |
| [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)                               | Secrets & Credentials                             | 定義 secret/token/key 的分域與收斂問題                                                                |
| [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)                                     | Audit & Accountability                            | 定義證據模型、責任鏈與可回查問題                                                                      |
| [7.8 模組路由：問題到服務實作](/backend/07-security-data-protection/security-routing-from-case-to-service/)                                 | Routing                                           | 定義概念層到實作層的交接規則                                                                          |
| [7.9 服務生命週期的資安風險節奏](/backend/07-security-data-protection/security-lifecycle-risk-cadence/)                                     | Lifecycle Risk Cadence                            | 定義設計到復盤五段的資安節奏問題                                                                      |
| [7.10 Workload Identity 與聯邦信任邊界](/backend/07-security-data-protection/workload-identity-and-federated-trust/)                        | Workload Identity & Federation                    | 定義非人類身份與跨平台信任問題                                                                        |
| [7.11 資料駐留、刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)                             | Data Residency & Deletion Evidence                | 定義資料位置、刪除閉環與證據可驗證問題                                                                |
| [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                        | Supply Chain Integrity                            | 定義 build 與 artifact 信任鏈問題                                                                     |
| [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)                                 | Detection & Signal Governance                     | 定義偵測覆蓋、訊號品質與誤報成本問題                                                                  |
| [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)                            | Governance Exception & Tripwire                   | 定義例外決策期限、補償控制與重評估觸發器                                                              |
| [7.15 資安作為風險路由系統](/backend/07-security-data-protection/security-as-risk-routing-system/)                                          | Risk Routing Essay                                | 把 07 主章串成風險路由導讀                                                                            |
| [7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)                                   | Case to Workflow                                  | 說明事故案例如何回寫控制面與工作流                                                                    |
| [7.17 例外、凍結與 Tripwire](/backend/07-security-data-protection/security-exception-freeze-tripwire/)                                      | Exception & Freeze Essay                          | 說明例外與凍結決策如何避免過期                                                                        |
| [7.18 資安控制面如何交接到部署與事故流程](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/)          | Control Handoff                                   | 定義資安控制面如何交接到 05/06/08                                                                     |
| [7.19 資安演練：從 Abuse Case 到 Game Day](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/)             | Security Exercise                                 | 定義 problem card 如何轉成演練與回寫                                                                  |
| [7.20 資安成熟度模型：從人工判斷到可稽核閉環](/backend/07-security-data-protection/security-maturity-from-manual-review-to-auditable-loop/) | Maturity Model                                    | 定義資安治理成熟度與提升路由                                                                          |
| [7.21 資安如何成為服務設計輸入](/backend/07-security-data-protection/security-as-service-design-input/)                                     | Security as Design Input                          | 把資安需求前移到設計評審與服務契約                                                                    |
| [7.22 資安風險如何進入 Release Gate](/backend/07-security-data-protection/security-risk-in-release-gate/)                                   | Risk in Release Gate                              | 把變更風險分級、必備控制與證據納入放行判準                                                            |
| [7.23 資安與可靠性的共同控制面](/backend/07-security-data-protection/security-and-reliability-shared-controls/)                             | Shared Controls                                   | 整合 rollback、containment、degradation                                                               |
| [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)           | Incident Write-Back                               | 把事故教訓回寫到產品、架構與控制流程                                                                  |
| [7.25 資安成熟度的組織節奏](/backend/07-security-data-protection/security-maturity-organization-cadence/)                                   | Organization Cadence                              | 把成熟度提升轉成固定節奏與指標                                                                        |
| [7.26 資安素材庫如何支援工程推演](/backend/07-security-data-protection/security-material-library-for-engineering-simulation/)               | Materials for Simulation                          | 把來源、案例、情境與模式組成推演流程                                                                  |
| [7.27](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                                                           | Credential Rotation with Scoped Evidence 實作示範 | 以 webhook/API credential 為基線、用控制面 token 與 CI 平台壓測場景示範 scope map、證據欄位與回退窗口 |
| [LLM Deployment 供應鏈完整性](/backend/07-security-data-protection/llm-deployment-supply-chain/)                                            | LLM Supply Chain                                  | 把模型權重、推論伺服器、第三方 plugin 三條供應鏈納入既有 artifact trust 框架                          |
| [LLM 多租戶推論隔離](/backend/07-security-data-protection/llm-multi-tenant-isolation/)                                                      | LLM Tenant Isolation                              | KV cache 不共享、log 與 model artifact 隔離、跨用戶 prompt 洩漏面                                     |
| [LLM Agent Prompt Injection 後果治理](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)                                  | LLM Agent Blast Radius                            | tool spec 設計、agent loop 限制、review checkpoint 與 incident workflow 的接合                        |
| [LLM Log 與 PII 治理](/backend/07-security-data-protection/llm-log-and-pii-governance/)                                                     | LLM Log Governance                                | prompt log 累積、PII 偵測與過濾、保留期限與合規對齊                                                   |
| [LLM Service 偵測訊號覆蓋](/backend/07-security-data-protection/llm-as-service-detection-coverage/)                                         | LLM Detection Coverage                            | tool call 異常、injection 觸發徵兆、abuse 模式與既有 detection-coverage 框架的接合                    |
| [7.28 密碼學原語選型：金鑰位置決定威脅模型](/backend/07-security-data-protection/cryptographic-primitive-selection/)                        | Cryptographic Primitive Selection                 | 定義加密、訊息驗證與可逆編碼的責任分界與金鑰位置判讀                                                  |
| [7.29 API 認證的信任邊界分層](/backend/07-security-data-protection/api-authentication-trust-boundaries/)                                    | API Auth Trust Boundaries                         | 定義使用者、系統與跨系統對應三層的憑證與撤銷粒度                                                      |
| [7.30 使用者密碼儲存：參數會過期的那一類原語](/backend/07-security-data-protection/password-storage-and-work-factor/)                       | Password Storage                                  | 定義密碼雜湊選型、work factor 定法、合規約束的判別與大帳號庫的升級路徑                                |
| [7.31 認證方式選型：可離線猜測的材料最後落在哪裡](/backend/07-security-data-protection/authentication-approach-selection/)                  | Authentication Approach                           | 定義自建、委派身分、passkey 與不做登入之間的取捨                                                      |
| [7.32 機器憑證的配發：這個交付動作能不能免掉](/backend/07-security-data-protection/machine-credential-issuance/)                            | Machine Credential Issuance                       | 定義配發能不能免掉、核發與審批要看什麼、初次交付與登記的條件                                          |
| [7.33 委任型憑證：關係寫進憑證，還是留給驗證方拼湊](/backend/07-security-data-protection/delegated-credential-selection/)                   | Delegated Credential Selection                    | 定義委任關係由誰確認、委任與冒用的差別、撤銷粒度與驗證方檢查項                                        |
| [7.34 機器憑證的機制選型：秘密要不要在每次呼叫裡送出去](/backend/07-security-data-protection/machine-credential-mechanism-selection/)       | Credential Mechanism Selection                    | 定義選擇權在誰、秘密送不送得起、撤銷粒度與基礎建設成本                                                |
| [7.35 簽章對接的驗證收斂：驗簽通過之後還缺哪一塊](/backend/07-security-data-protection/signature-integration-verification/)                 | Signature Integration                             | 定義驗證素材的對齊成本、重放窗口的收斂條件與比對方式                                                  |
| [7.36 憑證在請求中怎麼帶：附上的決定由誰做](/backend/07-security-data-protection/credential-transport-in-request/)                          | Credential Transport                              | 定義 cookie 自動附上與 header 明確附上各自要求攻擊者先做到什麼、各層防護的缺口                        |
| [7.37 密碼外洩之後：範圍判不出來的時候怎麼定處置](/backend/07-security-data-protection/credential-breach-response/)                         | Credential Breach Response                        | 定義三層重設範圍、撤銷與重設的先後、通知門檻要交付的事實                                              |
| [7.38 外部身分與本地紀錄：兩條生命週期在哪裡分岔](/backend/07-security-data-protection/external-identity-local-record-lifecycle/)           | External Identity Lifecycle                       | 定義停用同步的反向通道、離開後的資料歸屬與多來源帳號對應                                              |
| [7.39 使用者持有型憑證：那把憑證能不能離開它的載體](/backend/07-security-data-protection/user-held-credential-carrier/)                     | User-Held Credential Carrier                      | 定義憑證離不離得開載體、註冊起點的強度上限與補發路徑的取捨                                            |
| [7.40 B2B 多租戶的身分接入：這個人屬於哪個租戶由誰說了算](/backend/07-security-data-protection/multi-tenant-identity-onboarding/)           | Multi-Tenant Identity Onboarding                  | 定義租戶歸屬的主張與驗證、自助設定的範圍、每租戶設定的生命週期                                        |
| [7.41 單一帳號被接管：求助的人是誰本身待證](/backend/07-security-data-protection/single-account-takeover-response/)                         | Account Takeover Response                         | 定義控制權動作的分類、核身的判準與攻擊者留置的還原                                                    |
| [7.42 密碼重設流程：與登入平行的另一道入口](/backend/07-security-data-protection/password-reset-flow/)                                      | Password Reset Flow                               | 定義重設路徑的證據判準、權杖的五項性質與完成後的收尾                                                  |
| [7.C 資安案例正文](/backend/07-security-data-protection/cases/)                                                                             | Security Cases                                    | 把控制面事件轉成可回寫治理控制與路由                                                                  |
| [7.C11 選型：單人遠端 Shell](/backend/07-security-data-protection/cases/remote-shell-access-tailscale-vs-cloudflare-tunnel/)                | Tailscale vs Cloudflare Tunnel                    | 單人遠端 Shell 情境下的 tunnel 選型判讀與裝置綁定認證                                                 |

## 模組完成狀態

主章分三層：問題節點與責任邊界（7.2-7.7）、判讀與治理節奏（7.8-7.9、7.15-7.26），以及選型層（7.28-7.42）。選型層承接的是問題節點判讀完成之後要下的具體決定——手上的機制解哪一類問題、呼叫方身分落在哪一層、密碼怎麼存、登入怎麼做、登入之後每個請求靠什麼帶身分、外洩之後要讓誰重設、身分交給外部之後本地那筆紀錄怎麼走、使用者手上的實體選哪一種載體、每個客戶各帶身分提供者時要做成幾組設定，以及機器憑證的機制、交付與代理關係。章節列表末段的五篇 LLM 專題屬延伸章節帶、不佔主章編號：把供應鏈完整性、多租戶隔離、log 治理與偵測覆蓋這些主章已建立的控制面，接到 LLM 服務的 production 形態上。

素材庫已完成 11 張 field cases、4 張 scenarios 與 7 張 control patterns，並回寫到 `7.B1`、`7.B9`、`7.B12` 與 `7.24`。比例設計依 [素材庫比例支撐主情境的反向驗證](/report/source-library-ratio-supports-scenario-validation/)，文章主情境保持 4-5 個、素材庫保留 2-3 倍來源做反向驗證。

主章的覆蓋仍有缺口，清單見下方 Backlog。進入穩定維護狀態的條件是那些缺口收斂到只剩 vendor 層與案例層——其中讀者路線已經會撞到的是既有整合的盤點形態與發行方自助發放憑證的流程，兩項的前置條件都已備齊。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                                                               | 類型   | 前置條件                                               | 規模        |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------ | ----------- |
| 既有對外整合的盤點形態（每條整合的規格作者、秘密送不送得出去、撤銷粒度、上次換是什麼時候、素材有沒有書面規格——五欄分散在 7.34 / 7.35 / 7.6 三章，而稽核問與接手既有整合都要的是併成一張表的形態）                                                                                                  | 主章   | 無（三章各有一欄、7.32 已定義登記載體）                | 中          |
| 發行方自助發放憑證的流程（誰能開、範圍怎麼選、只顯示一次、自助輪替——7.32 整章是「交給合作廠商」的先有雞先有蛋框架，對平台自助發放不適用）                                                                                                                                                          | 主章   | 無（7.32 / 7.34 兩處讀者路線都會撞到）                 | 中          |
| 資產盤點（對外入口 / 憑證 / 信任錨 / token 的分母怎麼建與怎麼維持）                                                                                                                                                                                                                                | 主章   | 無（7.3 / 7.5 已給三份來源對帳的最小做法）             | 中          |
| 微案例第三拍的素材替換（7.5 / 7.28 / 7.30 / 7.31 / 7.32 / 7.33 / 7.34 / 7.35 各則已判定為機制推導，依據是各則第三拍都能從既有觀測機制的觀測對象集合推出「該事件不落在集合內」；其餘各則的來源尚未逐則判定）                                                                                        | 案例   | 該形態的案例庫新增任一則                               | 小          |
| 管理平面與業務平面的隔離設定落點（入口路由 / 管理端點可達來源）                                                                                                                                                                                                                                    | 主章   | 無（7.3 已定義路由需求）                               | 小          |
| 前端的輸出處理與內容安全政策（頁面怎麼避免執行到別人的程式碼——7.36 把它宣告為前端責任面而排除，全站無章承接；`cross-site-scripting` 卡的設計責任段目前是唯一落點）                                                                                                                                 | 主章   | 無（7.36 邊界段指過來、卡片已給最小判準）              | 中          |
| 7.35「驗證素材定義不一致」的微案例（後果不直觀而該節寫的是成本結構、是分析不是場面；隨 7.28 拆章一併移過來、7.28 那一半已於補寫時完成）                                                                                                                                                            | 案例   | 該形態的案例庫新增任一則（與微案例第三拍那一列同缺口） | 小          |
| 多方分持的金鑰形態（持有者不是單一方，7.28 的金鑰位置主軸涵蓋不到；與端對端加密備援的多方分持選項是同一個機制的兩個用途）                                                                                                                                                                          | 主章   | 無（7.28 已給最小判準）                                | 中          |
| 端對端加密的金鑰備援設計（復原碼 / 服務端包裝副本 / 多方分持各自把金鑰位置移到哪一格）                                                                                                                                                                                                             | 主章   | 無（7.28 已給三種形態與最小判準）                      | 中          |
| 四段 meta 開場的 register 整理（threat scope 樣板句中英混雜且對讀者祈使、「從本章到實作」向後引用尚未出現的表欄、交接路由欄的裸模組編號無對照），以及形態段「N 個節點裡 / 其餘四個」這種分母在表、被減數在另一段的計數（7.2 / 7.3 / 7.4 / 7.5 仍有；7.28 / 7.34 / 7.35 已改成不帶數字）            | 主章   | 無（本模組多輪審查指出、為主章共用樣板）               | 中          |
| 授權模型選型（角色邊界 vs 資源邊界的取捨、角色累積之後的收斂路徑）                                                                                                                                                                                                                                 | 主章   | 無（7.2 的代理操作段已定義路由需求）                   | 中          |
| 樣板叢集的容器改寫（「本篇的責任是 + 核心論點 + 完稿判準」這組樣板剩下的主章 9 篇與藍隊 12 篇：每節一句、表格格是既有卡的壓縮 gloss、路由欄是裸模組編號。7.21 / 7.22 / 7.25 已作為拆卡試點改寫完成，逐列判定與處置分診見 [#262](/report/content-pressure-resolves-by-expansion-not-compression/)） | 主章   | 無（試點已完成、改寫標準已確立）                       | 21 篇（大） |
| 51 個 vendor 服務頁的 deep article 與 migration playbook                                                                                                                                                                                                                                           | vendor | 無                                                     | 51 頁（大） |
| 藍隊現場案例卡與推演情境卡                                                                                                                                                                                                                                                                         | 案例   | 需先從真實事故抽防守壓力                               | 大          |
| 控制模式卡與事故回寫路由                                                                                                                                                                                                                                                                           | 案例   | 依賴上一項的案例卡與情境卡產出                         | 中          |

### 下一輪推演大綱

| 階段 | 產出           | 責任                                              | 回寫位置          |
| ---- | -------------- | ------------------------------------------------- | ----------------- |
| 1    | 藍隊現場案例卡 | 從真實事故抽出防守壓力、控制缺口與升級路由        | `7.B12` + `7.BM2` |
| 2    | 推演情境卡     | 把案例轉成可重播 tabletop 與 Game Day 情境        | `7.B9` + `7.BM3`  |
| 3    | 控制模式卡     | 把重複防守做法抽成可搬運欄位與驗證模式            | `7.B1` + `7.BM4`  |
| 4    | 事故回寫路由   | 把演練結果接回產品、架構、runbook 與 release gate | `7.24` + `7.18`   |

推演資產化的完成條件是讓讀者能從一個事故壓力出發，依序找到案例卡、情境卡、控制模式與回寫章節。

### 本模組的立項判定

主章項目的判定用的是讀者會拿去搜尋的問句落不落得到一篇聚焦的文章上，而不是主題有沒有被提到過。「這把 key 上次換是什麼時候」「這個租戶的設定誰改過」這幾類問句目前在全站只能在其他章節的段落裡零星碰到，落不到一篇上，因此各自成為表中一列。同一個判定先前產出過 7.36 與 7.30——「cookie 要設哪些屬性」「CSRF 怎麼防」當時也落不到一篇上。

判定時要分開「有落點」與「有這個角度的落點」。狀態放伺服器還是放 token 已經有落點——[Session 處理](/operations/02-horizontal-scaling/session-handling/) 從水平擴展的角度寫完了三種途徑與撤銷成本；缺的是同一個機制的資安判讀，而它由 [7.36](/backend/07-security-data-protection/credential-transport-in-request/) 從另一條軸承接。這個分界在表中以括號註記標示，補的時候要沿著各自的判讀軸走，不共用 7.28 的金鑰位置主軸。

入門讀者密度高於其餘項目的那幾列排在 vendor 層與案例層之前，理由是既有章節都預設讀者已經跨過那一層。憑證在請求中怎麼帶（[7.36](/backend/07-security-data-protection/credential-transport-in-request/)）與密碼儲存的完整版（[7.30](/backend/07-security-data-protection/password-storage-and-work-factor/)）都已依這個理由完成，表中剩下的各列改由前置條件與讀者路線的撞擊點決定順序。

## 跨分類引用

- → [infra 模組二：身分與憑證地基](/infra/02-identity-credentials/)：IAM role / policy、OIDC 短期憑證與權限邊界設計，是本模組 secret management 與 credential rotation 的地基層
- → [infra 模組八：治理好習慣](/infra/08-governance-habits/)：secrets 不進 code 的儲存與引用模式、密鑰命名規範
