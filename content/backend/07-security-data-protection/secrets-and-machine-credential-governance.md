---
title: "7.6 秘密管理與機器憑證治理"
date: 2026-04-24
description: "以問題驅動方式整理 secret、token、key 與機器身份治理"
weight: 76
tags: ["backend", "security"]
---

本章的責任是把機器身份與憑證風險拆成分域治理模型，讓 secret、token、key 的生命周期可以被一致驗證。

## 本章寫作邊界

本章聚焦分域策略、生命周期一致性與事件收斂節奏。案例在問題觸發時作為證據參考。

## 本章 threat scope

**In-scope**：token 分域不足 / CI secrets 集中 / 憑證生命週期失衡 / 供應商事件傳導未收斂。

**Out-of-scope**（路由到他章）：

- 人類身分 → [7.2](../identity-access-boundary/)
- 入口暴露 → [7.3](../entrypoint-and-server-protection/)
- 傳輸 / 憑證輪替 → [7.5](../transport-trust-and-certificate-lifecycle/)
- workload [federation](/backend/knowledge-cards/federation/) → [7.10](../workload-identity-and-federated-trust/)
- build provenance → [7.12](../supply-chain-integrity-and-artifact-trust/)
- 偵測平台 → [04 可觀測性](/backend/04-observability/)、實作交付 → [05 部署平台](/backend/05-deployment-platform/) / [06 可靠性](/backend/06-reliability/) / [08 事故處理](/backend/08-incident-response/)

Reader 對 in-scope 列表的 specific threat 應該能反向 trace 到本章問題節點；out-of-scope 議題請直接跳到對應章節、不在本章 audit 範圍。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[token-revocation]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「交接路由」欄位指向 [05 部署平台](/backend/05-deployment-platform/)、[06 可靠性](/backend/06-reliability/)、[08 事故處理](/backend/08-incident-response/)、接配置 / 驗證 / 處置交付。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

## 憑證治理模型

憑證治理的核心責任是讓每一種機器憑證都有清楚的用途邊界與收斂節奏。

1. 類型分層：區分應用程式 secret、存取 token、簽章 key、部署憑證。
2. 用途分域：區分讀取、寫入、管理操作的權限邊界。
3. 環境分域：區分開發、測試、正式環境，避免跨環境共用憑證。
4. 生命周期：定義發放、輪替、撤銷、淘汰的責任與時窗。本章承接憑證已經在流通之後的三段；發放那一段（這個交付動作能不能免掉、核發與審批要看什麼、初次交付與登記）見 [7.32 機器憑證的配發](../machine-credential-issuance/)。
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

## 問題節點出現在什麼樣的系統

本章問題節點表的「判讀訊號」欄要等憑證已經在流通才觀察得到，設計階段沒有使用面、沒有存量、沒有節奏可量。這一節補 token 分域不足、CI secrets 集中、憑證生命周期失衡、供應商事件傳導未收斂這四個節點各自的系統形態。

**token 分域不足**出現在憑證跟著整合一個一個長出來的系統。第一個對外整合上線時開了一把 token，權限給滿是因為當下還不確定它需要什麼；第二個整合來的時候那把 token 已經能用了，於是沿用。識別特徵是有一把憑證的名字是泛稱——「服務」「整合」「自動化」「內部用」——而不是某個具體用途；名字取不具體，通常代表開它的時候就沒有界定範圍。

**CI secrets 集中**出現在部署自動化做得完整的系統。部署這個動作本身要跨資料庫、雲端帳號、第三方 API 與監控平台，所以能自動部署的 CI 會集中持有這些系統的存取能力，而多數團隊用的形式是把憑證直接存在 CI 裡——集中在一處看起來也比散在各人筆電上安全。識別的檢查動作是把 CI 的憑證清單與單一服務自己持有的並列：CI 那一邊涵蓋了多個服務各自的憑證時，這一格成形。這一類的形態成因與其他三個不同：它是自動化程度的副產品。前提是用長期 secret 承接部署授權——在這條路徑上自動化越完整，集中度越高。換一條路徑則相反：部署改用每次執行動態換發的短效憑證時，自動化提升會拆掉這一格而不是加深它，那條路徑見 [7.10 Workload Identity 與聯邦信任邊界](../workload-identity-and-federated-trust/)。

**憑證生命周期失衡**出現在發放有流程、回收沒有流程的組織。申請憑證要填單、要核准、有人追；憑證不用了之後沒有任何一方會主動提起，因為停用它對誰都沒有立即好處。識別的檢查動作是往回追最近三次憑證申請的下場：用完之後停用了嗎、由誰停的、紀錄在哪裡。三次都追不到停用紀錄時，這一格已經成形。

**供應商事件傳導未收斂**在機器憑證層的形態是憑證跨過了組織邊界：第三方服務的憑證存在自己這邊，或自己的憑證存在第三方那邊（CI 服務持有雲端帳號、監控平台持有資料庫唯讀權限、支援工具持有 API key）。識別特徵是列得出「對方出事的話，我這邊有哪些東西要換」這份清單的人，通常只有當初做整合的那一位。人類身分層的同議題見 [7.2 供應商身分鏈傳導](../identity-access-boundary/#跨章-ssot供應商身分鏈傳導)。

憑證生命周期失衡是這張表裡後果最不直觀的一格——「可用憑證存量高於收斂速度」是一句統計描述，讀者從它想像不出任何具體場面。它的失敗長這樣：某次資安盤點要求列出所有還有效的機器憑證，清單拉出來七十幾把，其中三分之一沒有人認得——申請單找得到、用途欄寫著早就結束的專案名稱、申請人有幾位已經離職。沒有人在這期間做錯任何事：憑證一直能用，所以沒有任何錯誤訊息、沒有任何監控會亮；停用是「少做一件事」而不是「做錯一件事」，而少做的事不產生訊號。清理要逐把確認還有沒有人在用，而確認的方法是停掉它然後等有沒有人來抱怨——這個代價由「不確定的憑證有幾把」決定，也就是由沒有回收的那幾年決定。

CI secrets 集中的後果雖然在風險後果欄就寫著「輪替成本上升」，仍值得補一則，因為那句話讀起來像日常維運的量級、而實際的量級是事件當天要協調多少個團隊。其餘兩個節點不另寫：token 分域不足的後果由下方兩個節點的收斂動作段承接，供應商事件傳導在 7.2 有 canonical 與兩個真實案例。它的失敗長這樣：CI 平台公告自家環境遭入侵，建議所有客戶輪替全部憑證。輪替本身不難，難的是排序——團隊想先換影響最大的那幾把，於是要回答「哪些 secret 還在被用、被哪些流程用」，而這個問題沒有現成答案：CI 平台記錄的是有哪些 secret，不是誰在用它們。清單裡有一部分是幾年前某個已經刪掉的流程留下的，看不出來能不能安全刪；另一部分的擁有者已經離職。分界在憑證怎麼交到流程手上——注入式（存成環境變數，平台只知道有哪些）答不出使用者，取用式（執行期向 secrets 管理服務取用）由那一端的稽核日誌回答得出誰在什麼時候取了哪一把，而這個差別就是這一格可不可查的分界。最後只能全部輪替，而每換一把都要協調對應服務重新部署並確認沒壞——那幾天的工作量由憑證數量乘上牽涉的服務數決定，兩者都是集中化本身推高的。集中化當初省下的是日常管理成本，付出的是事件當天的協調成本，而這兩筆帳從來不會被放在一起比較。要把後者壓下來，動作在事件之前：先建 secrets 清單與擁有者對照（見下方 [CI secrets 集中化跟 blast radius](#ci-secrets-集中化跟-blast-radius)），再把部署授權從長期憑證換成每次執行動態換發的短效憑證（見 [7.10 Workload Identity 與聯邦信任邊界](../workload-identity-and-federated-trust/)）。

## 其餘節點的收斂動作

CI secrets 集中與簽章金鑰的收斂各有專節（見下方），其餘節點的路徑較短，收在這裡。

**token 分域不足**的收斂是把一把泛稱憑證拆成數把具名憑證，拆的依據是可達的信任邊界，而權限等級只是其中一個維度——跨多個敏感系統的單一 token 與限定單一用途的 token，事件當下的暴露面差距由邊界數量決定。拆分順序從最舊的那一把開始，因為泛稱憑證的年齡與它累積的用途成正比。人類身分那一側的同型處置見 [7.2 高權限工具的會話收斂節奏](../identity-access-boundary/#高權限工具的會話收斂節奏)。

**憑證生命周期失衡**的收斂是給回收一個發動時機。這一格缺的是觸發者而非流程——停用的步驟通常寫得出來，只是沒有任何事件會讓誰去執行它。可用的時機有三種：發放時就寫下預計的停用條件（用途結束、專案結束、對接終止）、把憑證綁在申請者的在職狀態上、或設定到期日讓不續期等於自動回收。前兩種的材料在配發當下產生——用途與擁有者這兩欄填得出來，停用條件與通知對象才有依據，那兩欄的定義見 [7.32 配發躲不掉時要定什麼](../machine-credential-issuance/#配發躲不掉時要定什麼)。第三種最省人力，代價是續期本身要能自動化，否則到期會變成事故來源——輪替與回退的演練設計走 [6.x DR 與 rollback 演練](/backend/06-reliability/dr-rollback-rehearsal/)。

## 跨章議題交叉引用

本章「供應商事件傳導未收斂」是 [7.2 供應商身分鏈傳導](../identity-access-boundary/#跨章-ssot供應商身分鏈傳導) 在機器憑證層的展現；canonical SSoT 在 7.2、本條補憑證仍活躍的 specific 訊號。

## CI secrets 集中化跟 [blast radius](/backend/knowledge-cards/blast-radius/)

CI secrets 集中化的核心風險是把 *單一節點承載的憑證數量* 跟 *事件期間需要輪替的範圍* 綁在一起。當 CI 平台被入侵、可暴露的範圍就是該平台所有 secrets 的集合；治理層要在事件發生前把這個集合切小、不是事件後試圖縮範圍。

[CircleCI 2023](../red-team/cases/supply-chain/circleci-2023-secrets-rotation/) 揭露三條互相強化的失效訊號 — CI secrets 集中化且缺少分域隔離、輪替流程成本高（導致執行延遲）、客戶端難以快速判斷最小必要輪替範圍。案例「可落地檢查點」直接列出 mechanism「定義 secrets 分級與依賴地圖、依 blast radius 分層、不只依名稱」屬可引用範圍、前提條件是事先有 secrets inventory 跟 owner mapping。

以下基於通用工程知識補充：secrets 分級的工程意義是讓事件期間的輪替能按風險排序、不靠 ad-hoc 判斷。缺分級時、組織要在壓力下做全面輪替、容易造成服務中斷或遺漏。日常演練要包含「假設整個 CI vendor 受損」的 fire drill、確認輪替路徑能在 vendor 失能時仍可執行，這是 7.6 跟 [6.x reliability](/backend/06-reliability/) 演練面的共同訴求。

## 簽章金鑰跟長期信任根

簽章金鑰是憑證治理的最高層信任根、生命週期治理要跟一般 token 分開。簽章金鑰一旦失守、攻擊者能偽造 *可被驗證* 的 token、繞過所有依賴該 issuer 的下游驗證；這跟一般 token 洩漏（仍受 token 自身 scope 限制）是不同層級的失效。

本節是簽章金鑰治理的 canonical（含 material 保護跟 lifecycle 視角）；驗證路徑層的 specific 訊號（fleet 層級 issuer 熱抽換）見 [7.5 簽章金鑰失效時的驗證路徑收斂](../transport-trust-and-certificate-lifecycle/#簽章金鑰失效時的驗證路徑收斂)。選型階段的入口訊號（何時該把簽發金鑰與一般 secret 分層）見 [7.28 密碼學原語選型](../cryptographic-primitive-selection/#跨章議題交叉引用)。

對應 [Microsoft Storm-0558 2023](../red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/)：揭露三層失效控制面 — 簽章金鑰生命週期治理與隔離策略不足、權杖驗證邊界缺少跨服務一致性檢查、高風險身分事件追查與升級節奏偏慢。本章聚焦第一層 material 保護、第二層 validation 路徑由 7.5 處理。案例「可落地檢查點」標明 mechanism 為「把簽章金鑰納入硬體保護與輪替節奏（HSM-bound、不可導出、強制輪替週期）」。

以下基於通用工程知識補充：簽章金鑰治理由材料保護跟驗證路徑兩條 chain 構成 — *材料保護* 用 HSM-bound（不可導出 + 強制輪替）處理金鑰本體（本章責任）、*驗證路徑* 用 fleet 層級熱抽換能力處理 issuer 切換（7.5 責任）。兩條 chain 構成單一信任根的雙重防線、任一邊失能會把另一邊的工程投資清零（材料外洩時若 issuer 無法熱抽換、攻擊窗口會延長到所有 fleet 完成 deploy；驗證路徑可熱抽換但金鑰可被導出時、攻擊者仍能離線濫用）。實作層的具體選型（[HSM](/backend/knowledge-cards/hsm/) 廠商 / 雲託管 KMS）屬於 [5.x deployment platform](/backend/05-deployment-platform/) 範圍、本章不展開。

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

- 憑證進入流通之前的核發、初次交付與登記：[7.32 機器憑證的配發](../machine-credential-issuance/)
- 交付與執行環境：[05 部署平台](/backend/05-deployment-platform/)（tunnel 憑證的保管與輪替見 [5.10 Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/)）
- 輪替與回退演練：[06 可靠性](/backend/06-reliability/)
- 事件收斂與通報：[08 事故處理](/backend/08-incident-response/)
