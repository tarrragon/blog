---
title: "7.29 API 認證的信任邊界分層"
date: 2026-07-27
description: "一個請求同時牽涉人、呼叫系統與跨系統身分對應時，用來判斷各層該用哪種憑證、混層後會失去什麼、以及規模不足時哪幾層可以合併"
weight: 104
tags: ["backend", "security"]
---

本章的責任是把 API 認證拆成獨立的身分維度，讓每一層的憑證機制、洩漏後果與撤銷粒度各自清楚。

## 本章寫作邊界

本章聚焦身分維度的分層判讀與混層失效訊號。各層憑證的格式、儲存與生命週期實作屬於下游，案例用於檢驗分層在真實事件下是否維持區辨力。

## 本章 threat scope

**In-scope**：層級混用導致撤銷粒度失控 / 系統憑證下放到客戶端 / 跨系統身分對應的依賴順序未定義 / 第三方授權範圍過寬。

**Out-of-scope**（路由到他章）：

- 人類身分的權限分級與 [authorization](/backend/knowledge-cards/authorization/) → [7.2](../identity-access-boundary/)
- 機器憑證的輪替與收斂節奏 → [7.6](../secrets-and-machine-credential-governance/)
- 憑證機制本身的選型 → [7.28](../cryptographic-primitive-selection/)
- 跨系統工作負載之間的信任建立（workload federation） → [7.10](../workload-identity-and-federated-trust/)
- 傳輸層信任 → [7.5](../transport-trust-and-certificate-lifecycle/)

Reader 對 in-scope 列表的 specific threat 應該能反向 trace 到本章問題節點；out-of-scope 議題請直接跳到對應章節。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[token-revocation]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「交接路由」欄位指向 `05-deployment-platform / 06-reliability / 08-incident-response`。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

## 身分維度分層模型

分層的核心責任是讓每個身分問題有獨立的憑證與撤銷路徑。單一 API request 看似只問「這個呼叫合法嗎」，實際同時牽涉三個彼此獨立的問題。

1. **使用者層**：發起這個請求的人是誰。對應 [Authentication](/backend/knowledge-cards/authentication/) 與可個別撤銷的 [Token Revocation](/backend/knowledge-cards/token-revocation/)。
2. **系統層**：把這個請求送過來的系統是誰。對應共享密鑰或 [Message Authentication](/backend/knowledge-cards/message-authentication/)、[mTLS](/backend/knowledge-cards/tls-mtls/) 等機器身分機制。
3. **跨系統對應層**：這個人在另一個系統有沒有對應身分。這一層是一套流程而非新的信任邊界，產出的是身分映射與其建立時機。

三層的關鍵差異在**撤銷粒度**。使用者層可以撤銷單一 session 而不影響他人；系統層的憑證由所有呼叫共用，撤銷等於中斷整條整合；對應層沒有可撤銷的憑證，處理的是映射資料的一致性。

這三維針對的是呼叫鏈上的單一請求。裝置粒度（撤銷單一裝置而保留該使用者其他 session）屬使用者層的細分，租戶維度屬授權範圍、路由到 [7.2](../identity-access-boundary/)。另有一種形態落在三維之外：委任型憑證由單一 token 同時承載代理方與被代理方（OAuth token exchange 的 actor 與 subject），它的撤銷粒度是「哪個系統代表哪個使用者」這個組合，三層各自的粒度都對不上它。

## 判讀流程

判讀流程的責任是把「這個請求該怎麼驗」轉成「哪一層在承擔什麼」。

1. 先拆出這個端點實際牽涉哪幾個身分維度。
2. 再確認每一層各自用什麼憑證，以及該憑證的撤銷會影響誰。
3. 接著確認層與層之間沒有互相代理 —— 一層的憑證不應該能通過另一層的驗證。例外是憑證格式明確承載兩個主體、且兩個主體各自可獨立撤銷的委任型設計：它同時滿足兩層並非混層，因為身分關係寫在憑證裡而非靠推定。判別方式是問這張憑證被撤銷時，失效的是哪一個主體。
4. 最後把跨系統對應的建立時機與依賴順序寫成文件，路由到部署面與事故處置。

這四步是針對單一端點的。要對整個系統跑一次盤點時，直接把下方問題節點表的四個判讀訊號當成欄位，對每個整合對象逐一問過去，答案就是這條整合的分層現況。

## 問題節點（案例觸發式）

| 問題節點             | 判讀訊號                               | 風險後果                           | 前置控制面                                                                                                                 | 交接路由  |
| -------------------- | -------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------- |
| 使用者憑證代理系統層 | 用使用者 token 驗證呼叫方系統身分      | 撤銷單一使用者會中斷整條整合       | [authentication](/backend/knowledge-cards/authentication/)、[token-revocation](/backend/knowledge-cards/token-revocation/) | `06 + 08` |
| 系統憑證下放客戶端   | 共享密鑰隨前端或行動應用發佈           | 任何取得程式的人可冒充該系統       | [secret-management](/backend/knowledge-cards/secret-management/)、[credential](/backend/knowledge-cards/credential/)       | `05 + 06` |
| 第三方授權範圍過寬   | 整合取得的權限超過該整合實際使用的範圍 | 第三方事件直接放大成內部資料暴露   | [authorization](/backend/knowledge-cards/authorization/)、[blast-radius](/backend/knowledge-cards/blast-radius/)           | `08`      |
| 跨系統對應順序未定義 | 身分映射的建立時機隱含在呼叫順序裡     | 首次呼叫失敗且錯誤訊息指向錯誤的層 | [api-contract](/backend/knowledge-cards/api-contract/)                                                                     | `05 + 06` |

## 跨章議題交叉引用

本章「第三方授權範圍過寬」是 [7.2 供應商身分鏈傳導](../identity-access-boundary/#跨章-ssot供應商身分鏈傳導) 在 API 整合層的展現；canonical SSoT 在 7.2，本條補「授權當下的 scope 決定事件發生時的暴露面」這個前置訊號。

## 混層之後失去什麼

層級混用的代價不會在功能測試裡出現 —— 請求照常通過，問題在事件發生時才顯現。三種混法各自失去不同的能力。

**使用者憑證代理系統層**時，失去的是撤銷粒度。系統之間的整合掛在某個使用者的 token 上，該使用者離職或密碼重設就會中斷整條整合；反過來要撤銷這條整合，只能停用那個使用者。兩個本來獨立的生命週期被綁在一起。

**系統憑證下放到客戶端**時，失去的是「呼叫方系統」這個身分本身的意義。共享密鑰隨程式發佈之後，任何取得程式的人都能冒充該系統發出請求 —— 這與 [7.28 金鑰位置決定對抗對象](../cryptographic-primitive-selection/#金鑰位置決定對抗對象) 是同一個機制問題在認證分層上的展現。

**跨系統對應順序未定義**時，失去的是排障路由。身分映射若在首次呼叫時隱式建立，缺映射的錯誤會以認證失敗的形式出現，讓排查方向指向憑證而非資料。

後兩個問題節點的判讀訊號需要主動收集才看得到。授權範圍是否過寬，比對的是整合被授予的權限清單與它實際呼叫過的端點 —— 資料在 API 的存取日誌裡，取一段時間的呼叫記錄按端點去重，沒被呼叫過的權限就是超出實際使用的部分。對應順序是否隱式，看的是身分映射的寫入點：映射由明確的開通動作（provisioning）建立時順序是定義好的，由業務端點在找不到映射時順帶建立則屬於隱式，判別方式是查該資料表的寫入來源有幾處。

[GitHub OAuth 2022](../red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/) 展示授予範圍如何決定暴露面：整合持有的 token 權限過寬，第三方事件因此直接通往下游客戶的資產。[Okta 與 Cloudflare 2023](../red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) 展示同一層的另一條傳導路徑 —— 承載身分材料的是支援流程本身，收斂點落在資料分級與供應商事件觸發的輪替，而非授權當下給了多少權限。

以下基於通用工程知識補充：授權當下是 scope 收斂成本最低的時機。整合上線後縮小權限需要協調對方調整程式碼，這道協調成本讓「先給寬鬆權限之後再收」的收斂動作缺少發動的時機 —— 沒有任何一方的既定工作會自然帶出它。成本次低的窗口是重新授權與供應商事件觸發的強制輪替，那時雙方本來就要動 token，順手收斂不額外增加協調成本。

## 何時可以合併層級

分層的成本落在自己團隊的部分是憑證配發、輪替與各層監控，這些可以排進迭代。真正決定時程的是另一項：既有整合對象要改自己的程式碼才能配合新的分層，而他們的排期不歸你控制。估算補分層要多久時，基準是這一項而非自己的實作工作量 —— 這也是「先上線再收斂」在認證分層上很少發生的原因。規模與整合數量不足時，合併層級是合理的選擇，前提是明確知道放棄了什麼。

單一前端搭配單一後端、沒有第三方整合時，系統層的獨立憑證帶來的區辨力有限 —— 呼叫方只有一個，「是誰呼叫的」這個問題沒有分歧。此時把驗證集中在使用者層可以接受，代價是日後新增第二個呼叫方時要補上分層。

跨系統對應層在雙方使用者體系一致（例如同一個 IdP）時可以省略。身分映射由 [federation](/backend/knowledge-cards/federation/) 承擔，路由到 [7.10](../workload-identity-and-federated-trust/)。

判斷是否該補回分層的訊號：出現第二個呼叫方系統、整合對象是外部組織、或撤銷單一憑證會影響到非預期的對象。

## 常見風險邊界

風險邊界的責任是定義何時要把認證設計從功能議題升級成治理議題。

- 撤銷單一憑證必須先跟外部團隊協調排程時，事件處置的時間已經由對方的行事曆決定，這超出工程修復能承擔的範圍。
- 客戶端產出物中存在能通過系統層驗證的憑證時，代表該層的身分保證已經失效。
- 第三方整合的權限範圍無法對應到它實際使用的端點時，代表暴露面超過需求。
- 同一個認證錯誤碼在兩個模組的處置手冊指向不同動作時，代表分層的語意沒有跨團隊對齊，排障路由會依接手的人而分岔。

## 案例觸發參考

案例觸發的責任是檢查分層設計在真實事件下是否維持區辨力。

- 第三方 token 成為內部入口： [GitHub OAuth 2022](../red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/)
- 支援系統身分鏈傳導： [Okta 與 Cloudflare 2023](../red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- token 洩漏後的存取延續： [Slack 2022](../red-team/cases/identity-access/slack-2022-token-compromise/)
- 授權範圍過寬的反例： [過寬的第三方 token 授權](../red-team/problem-cards/fp-overscoped-third-party-token-grant/)

## 下一步路由

- 憑證機制選型：[7.28 密碼學原語選型](../cryptographic-primitive-selection/)
- 人類身分與權限分級：[7.2 身分與授權邊界](../identity-access-boundary/)
- 機器憑證生命週期：[7.6 秘密管理與機器憑證治理](../secrets-and-machine-credential-governance/)
- 各層憑證的格式、儲存與開通策略實作：[API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/)。盤點與設計評審用本章的問題節點表，落到各層要用哪種憑證、怎麼儲存、開通流程怎麼設計時走那一篇
- 配置與部署：`05-deployment-platform`
- 撤銷演練：`06-reliability`
- 事件收斂：`08-incident-response`
