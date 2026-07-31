---
title: "7.2 身分與授權邊界"
date: 2026-04-24
description: "以問題驅動方式整理身分、授權、會話與供應商身分鏈"
weight: 72
tags: ["backend", "security"]
---

本章的責任是把「誰可以做什麼」拆成可驗證的邊界模型，讓團隊在功能上線前就能判讀身分擴散與授權濫用風險。

## 本章涵蓋與不涵蓋

本章聚焦概念層判讀，主體是問題節點、訊號、風險與路由條件。案例在問題被觸發時提供證據參考，不作章節主體。

## 讀者路由

個人自架工具場景（從 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) 導過來）直接看[單人裝置認證模型](#單人裝置認證模型)段。多人 SaaS 場景從[身分與授權邊界模型](#身分與授權邊界模型)段開始。

## 本章 threat scope

**In-scope**：credential brute force / [credential stuffing](/backend/knowledge-cards/credential-stuffing/) / phishing 與 MFA fatigue / privilege escalation / session hijacking / 供應商身分鏈傳導 / insider abuse / 過寬授權範圍 / 單人裝置認證邊界轉移。

**Out-of-scope**（路由到他章）：

- 入口暴露面 → [7.3](../entrypoint-and-server-protection/)
- 資料外洩 → [7.4](../data-protection-and-masking-governance/)
- 傳輸 / 憑證信任 → [7.5](../transport-trust-and-certificate-lifecycle/)
- 機器憑證 → [7.6](../secrets-and-machine-credential-governance/)
- [workload identity](/backend/knowledge-cards/workload-identity/) → [7.10](../workload-identity-and-federated-trust/)
- 偵測訊號 → [7.13](../detection-coverage-and-signal-governance/)
- 偵測平台 → [04 可觀測性](/backend/04-observability/)、實作交付 → [05 部署平台](/backend/05-deployment-platform/) / [06 可靠性](/backend/06-reliability/) / [08 事故處理](/backend/08-incident-response/)

Reader 對 in-scope 列表的 specific threat 應該能反向 trace 到本章問題節點；out-of-scope 議題請直接跳到對應章節、不在本章 audit 範圍。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[authentication]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「交接路由」欄位指向 [05 部署平台](/backend/05-deployment-platform/)、[06 可靠性](/backend/06-reliability/)、[08 事故處理](/backend/08-incident-response/)、接配置 / 驗證 / 處置交付。

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

| 問題節點               | 判讀訊號                                                          | 風險後果                                               | 前置控制面                                                                                                                             | 交接路由               |
| ---------------------- | ----------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| 登入驗證節奏失衡       | 異常驗證密度、異常地理切換、連續高風險操作                        | 身分擴散速度提升                                       | [authentication](/backend/knowledge-cards/authentication/)、[incident-severity](/backend/knowledge-cards/incident-severity/)           | `08 incident response` |
| 授權範圍擴張過快       | 高權限操作集中、代理操作鏈過長                                    | 權限濫用影響面擴大                                     | [authorization](/backend/knowledge-cards/authorization/)、[least-privilege](/backend/knowledge-cards/least-privilege/)                 | `08 incident response` |
| 會話失效節奏落後       | 修補後異常 session 持續、token 存續過久                           | 事件關閉時間延長                                       | [session-invalidation](/backend/knowledge-cards/session-invalidation/)、[token-revocation](/backend/knowledge-cards/token-revocation/) | `08 + 05`              |
| 供應商身分鏈傳導       | 外部事件後內部憑證存續比例偏高                                    | 內部信任邊界承受外部衝擊                               | [credential](/backend/knowledge-cards/credential/)、[containment](/backend/knowledge-cards/containment/)                               | `08 + 06`              |
| 單人裝置認證邊界轉移   | device 失竊後生物辨識可繞過、共享密鑰存本機、無中央會話可遠端失效 | 認證邊界落在 device 層、單點失效即全失效               | [authentication](/backend/knowledge-cards/authentication/)、裝置綁定 + 共享密鑰                                                        | `05 + 08`              |
| 終端使用者登入節奏失控 | 整體登入失敗率上升而個別帳號的失敗次數都在門檻之下                | 別處外洩的帳密可直接登入成功、按帳號計數的防護看不到它 | [credential stuffing](/backend/knowledge-cards/credential-stuffing/)、[authentication](/backend/knowledge-cards/authentication/)       | `08 + 05`              |

## 問題節點出現在什麼樣的系統

本章問題節點表的「判讀訊號」欄要等系統已經在跑才觀察得到，設計階段還沒有密度、沒有地理切換、沒有存續比例可看。這一節補登入驗證節奏失衡、授權範圍擴張過快、會話失效節奏落後、供應商身分鏈傳導、終端使用者登入節奏失控這五個節點的系統形態；單人裝置認證邊界轉移的形態、失效模型與 tripwire 見下方[單人裝置認證模型](#單人裝置認證模型)段。

**登入驗證節奏失衡**的種子埋在導入第二因子的那一刻。當時的評估重點是採用率，而推送核准在這一項上贏過所有需要輸入的方案——手機跳出「是不是你在登入」、按一下同意就完成。風險要等組織長到有專職 IT 支援、員工習慣「系統偶爾會跳出東西要按」的階段才成形，而那時推送核准已經佈滿全公司。識別特徵是核准動作不需要任何來自登入端的資訊：沒有數字配對、沒有裝置綁定，同意與否只取決於當事人當下怎麼想。

**授權範圍擴張過快**出現在長出代理操作能力的內部工具：客服要能替使用者查訂單、營運要能替商家改設定、管理後台要能切換身分重現問題。這些能力各自都有正當理由，而權限模型多半用角色承接，於是角色隨功能一路累積。識別特徵是系統裡有一個叫「管理員」的角色，而沒有人說得出它現在能做什麼——那份清單只存在於程式碼的判斷式裡。

**會話失效節奏落後**出現在身分憑證有多個發行方的系統：SSO 發一種、API 金鑰是另一種、個人存取權杖第三種、裝了的 OAuth 應用各自持有第四種。每一種在導入當下都有清楚的用途，累積起來卻沒有任何地方記錄這個人總共握有幾種身分憑證。識別的檢查動作是挑一個離職超過半年的帳號，把各個發行方的紀錄逐一調出來對帳——只要有任何一方還留著有效的材料，這一格就成立。

**終端使用者登入節奏失控**出現在面向一般消費者、而使用者自己設密碼的服務。成因不在自己這邊——使用者在數十個服務用同一組密碼，其中任何一家外洩，這裡的登入端點就多了一批可以直接試的真密碼。使用者群體與大型外洩事件的重疊度決定這一格的深淺，面向一般消費者的服務重疊度最高。識別的檢查動作是把登入失敗率拆兩層看：整體失敗率上升而個別帳號的失敗次數都在鎖定門檻之下時，這一格已經成形——按帳號計數的防護結構上看不到它。

**供應商身分鏈傳導**在什麼都自己做的系統上不成立，而那樣的系統幾乎不存在——登入交給 SSO 供應商、支援工單走第三方平台、CI 服務持有原始碼倉庫的存取權，每一項都是理性的外包決定。所以這一格的問題是深淺而非有無，而深淺與組織規模成反比：越小的組織外包比例越高。識別特徵是存在一個外部系統，它那邊的帳號被盜之後自己這邊會發生事情，而那條因果鏈通常沒有寫在任何一份自己的文件裡。

五個節點裡會話失效的後果最不直觀——「事件關閉時間延長」聽起來像流程指標而非風險。其餘四個不另寫：登入驗證與授權擴張的後果欄已經把話講完（誤點一次就進來、影響面擴大），供應商身分鏈傳導與終端使用者登入節奏在下方各有一節展開，前者還帶兩個真實案例。它的失敗長這樣：某位員工的帳號被回報異常，處置照著手冊跑完——密碼重設、SSO 的 session 全部踢掉、當事人確認登不進去了，事件就此關閉。幾週後同一個帳號的個人存取權杖仍在拉取倉庫內容，因為那把權杖是幾年前為了跑一次資料匯出而開的，它不經過 SSO、不受密碼重設影響，發行紀錄只留在當時的一則對話裡。查不出來的原因是撤銷動作分散在各個發行方，每一方都正確地完成了自己那一份並回報完成，而沒有任何一方負責回答「這個人還剩下什麼」。補起來要先建出身分憑證的清單，而清單本身要靠翻遍各系統的後台才生得出來。清單的欄位與維持方式走 [7.6 秘密管理與機器憑證治理](../secrets-and-machine-credential-governance/)（機器那一側的 inventory 與這一份是同一套欄位），撤銷動作本身的分工見下方[高權限工具的會話收斂節奏](#高權限工具的會話收斂節奏)。

## 終端使用者的登入節奏

這一節承接的是面向外部使用者的登入端點，主體與本章其他節點不同——那些處理員工、內部工具與高權限操作，這裡的主體是自己控制不了的一群人，以及他們在別處設過的密碼。

這一格的判讀重點是**限速的計數單位**。按帳號計數的防護對它結構上失明——攻擊者對每個帳號只試一兩次，門檻永遠碰不到，而整體失敗率已經翻了幾倍。計數單位要換成來源與行為特徵，這一步換掉之後其餘防護才有意義。可用的機制與它們各自擋掉哪一段見 [credential stuffing](/backend/knowledge-cards/credential-stuffing/)。

比對外洩密碼清單的時點也要判：註冊與變更密碼時比對擋得住新設的那些，而既有帳號的密碼是在設定之後才外洩的，那一批要靠成功登入當下再比對一次才接得住。

第二因子讓密碼正確也不足以登入，是成本最高、擋掉的比例也最高的一層，觸發條件見 [step-up 驗證](/backend/knowledge-cards/step-up-authentication/)——它與上方 MFA fatigue 那一節共用同一組訊號，差別在那裡的主體是員工。

這一格的上游是登入方式本身——改用 passkey 或委派身分之後，可離線猜測的材料會移到別的位置而不是消失，見 [7.31 認證方式選型](../authentication-approach-selection/)；密碼確實自己存時的參數與升級走 [7.30 使用者密碼儲存](../password-storage-and-work-factor/)。

## 跨章 SSoT：供應商身分鏈傳導

本章「供應商身分鏈傳導」問題節點是跨章 SSoT——其他章節從不同 layer 補同議題的 specific 訊號：

- [7.5 第三方信任重評估延遲](../transport-trust-and-certificate-lifecycle/)：傳輸層的 specific 訊號（憑證收斂滯後）
- [7.6 供應商事件傳導未收斂](../secrets-and-machine-credential-governance/)：機器憑證層的 specific 訊號（憑證仍活躍）
- [7.10 第三方授權範圍跟事件傳導半徑](../workload-identity-and-federated-trust/#第三方授權範圍跟事件傳導半徑)：workload identity 層的 specific 訊號（[federation](/backend/knowledge-cards/federation/) token scope 過寬）
- [7.29 第三方授權範圍過寬](../api-authentication-trust-boundaries/#跨章議題交叉引用)：API 整合層的 specific 訊號（授權當下的 scope 決定事件發生時的暴露面）

本章視角聚焦客戶側人類身分鏈收斂責任；workload identity 層的 federation token scope 視角見 7.10。本條處理的是對方出事之後這邊怎麼收斂，而對方沒出事、只是把帳號停用而這邊收不到事件，是同一條線的另一半，見 [7.38 外部身分與本地紀錄](../external-identity-local-record-lifecycle/)。跨章 audit 時、本條為 canonical 定義（threat scope / mitigation chain），其他章補 layer 視角差異。

## MFA fatigue 與 step-up 驗證

MFA fatigue 是身分層擴散風險的代表機制：登入挑戰可被使用者連續同意，攻擊者把「使用者誤點」當成唯一所需的人類動作。要解這個機制要拉開兩層判讀，登入層放強認證、操作層放 [step-up](/backend/knowledge-cards/step-up-authentication/) 驗證，避免認證成功直接等於高權限存取。

對應 [Uber 2022](../red-team/cases/identity-access/uber-2022-mfa-fatigue/)：揭露三個失效控制面 — 高風險登入路徑缺 step-up、內部工具授權邊界不足（初始落點可快速擴散）、身分異常事件與值班告警串接不足。案例的「可落地檢查點」段把對應 mechanism 標明為 phishing-resistant 強認證（WebAuthn / passkey）+ 裝置信任綁定（managed device / posture check）、屬於案例直接可引用範圍。

以下基於通用工程知識補充：強認證跟裝置綁定是 mechanism 雙軌、缺一不可。只做強認證不綁裝置、攻擊者仍可在受感染端點繼承會話；只綁裝置不強化認證、社交工程仍可繞過。判讀升級條件是「短時間 MFA 請求密度異常」要走 [on-call](/backend/knowledge-cards/on-call/) 升級、不是當一般使用者支援處理。

## 代理操作的授權邊界

授權範圍擴張過快的收斂點是把代理操作與直接操作分成兩種授權，而不是定期清理權限。客服「能查訂單」與客服「能以某位使用者的身分查訂單」是不同的能力：前者的資源邊界由操作類型決定（訂單這一類資料），後者的資源邊界由被代理的對象決定（那位使用者看得到的一切）。用角色承接時兩者長得一樣——都是角色上的一個項目——所以角色沿著功能一路長大，而每一次擴張在當下都有正當理由。

判讀軸是問這個操作的資源邊界由什麼決定。由操作類型決定的放角色，因為它的範圍是靜態的、可以列舉；由被代理對象決定的要另外一層，那一層帶三樣角色層沒有的東西：發起的理由、有效時窗、以及紀錄裡的雙重歸屬（哪個員工、以誰的身分）。缺這三樣時，[稽核紀錄](/backend/knowledge-cards/audit-log/)只看得到「某位使用者做了什麼」，看不到那其實是客服代做的。

這個結構與身分層的 [step-up 驗證](/backend/knowledge-cards/step-up-authentication/) 同形而不同層：step-up 把「登入成功」與「執行高風險操作」拆開、提高的是認證強度；代理授權把「持有這個角色」與「現在要代理某人」拆開、加的是有範圍與時窗的臨時授予，相鄰形態是 [break-glass access](/backend/knowledge-cards/break-glass-access/)。兩層獨立成立——身分層做了 step-up 而授權層沒拆時，攻擊者取得的是一個已經通過強認證、且能代理任何人的會話。

收斂的第一步是讓權限變成可列舉的資料。角色清單答不出來的原因通常是判斷寫在程式碼的條件式裡，而條件式無法被盤點——沒有東西可以審，也就沒有東西可以縮。這一步的成本由條件式散落的程度決定，而不是由權限的數量決定：權限多但集中在一處的系統，收斂起來比權限少卻散在各處的系統便宜。估算縮權要多久時，基準是前者。

判讀訊號裡的「代理操作鏈過長」指的是多跳代理——某個員工以 B 的身分操作，而 B 本身也是一個代理身分。多跳本身有正當形態（廠商工程師經合作夥伴帳號、自動化代理處理已在代理狀態的租戶），問題出在歸屬：每一跳讓歸屬多一層轉換，而稽核紀錄多半只留最後一跳。

收斂條件因此掛在紀錄能力上，而不是一律禁止：紀錄承載得了整條鏈時多跳可以開放，承載不了時代理不可遞移。既有標準有對應的表達方式：OAuth 2.0 Token Exchange 用 `act` claim 記錄「誰代表誰」，而這個欄位支援巢狀，正是為了保留完整的委任鏈。這種憑證的形態與最小判準見 [7.29 身分維度分層模型](../api-authentication-trust-boundaries/#身分維度分層模型) 的委任型段落；機制選型（交換流程、兩端各自的撤銷路徑、驗證方要檢查哪些欄位）見 [7.33 委任型憑證](../delegated-credential-selection/)。

對應失效樣式 [代理操作濫用](../red-team/problem-cards/delegated-operation-abuse/) 與 [代理會話上下文混層](../red-team/problem-cards/fp-delegated-session-context-bleed/)。完整的授權模型選型（角色邊界與資源邊界的取捨、角色累積之後的收斂路徑）本模組尚無對應章節，已列入 backlog；在那之前，最小權限的判準見 [least-privilege](/backend/knowledge-cards/least-privilege/)，緊急高權限存取的形態見 [break-glass-access](/backend/knowledge-cards/break-glass-access/)。

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

這個模型的 tripwire 是使用者數從一變多。共享密鑰無法分辨是哪個使用者、生物辨識綁在單一裝置、沒有帳號就無法個別撤銷;第一個要分享存取的對象出現時、認證模型要升級回帳號系統。應用場景的判斷見 [0.21 個人自架工具](/backend/00-service-selection/delivery-mode-selection/#個人自架工具常駐本機無對外服務)。升級回帳號系統之後，使用者手上那個實體要選哪一種載體、以及它掉了怎麼補發，走 [7.39 使用者持有型憑證](../user-held-credential-carrier/)。

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

- 登入方式本身的選型（自建 / 委派 / passkey）：[7.31 認證方式選型](../authentication-approach-selection/)
- 入口與平台實體：[05 部署平台](/backend/05-deployment-platform/)
- 驗證與回復節奏：[06 可靠性](/backend/06-reliability/)
- 事件分級與收斂：[08 事故回應](/backend/08-incident-response/)

**個人自架工具場景**：

- 回 [5.10 Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/) 確認 tunnel 之後的認證疊法
- 進 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 做入口威脅建模
- 判斷服務形態：回 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)
