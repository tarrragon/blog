---
title: "7.34 機器憑證的機制選型：秘密要不要在每次呼叫裡送出去"
date: 2026-07-29
description: "系統層確定要有獨立的機器身分之後，用來在 API key、共享密鑰簽章、mTLS 與 client credentials 之間決定"
weight: 109
tags: ["backend", "security", "Credential", "mTLS", "HMAC"]
---

對方的 API 文件只寫了「在 header 帶上你的 API key」，而這條整合要跑三年。這一步有沒有選擇的餘地，以及有餘地時該用什麼分。

本章的責任是把「這條整合要用哪一種機器憑證機制」拆成可判讀的選型問題，讓共享密鑰、API key、共享密鑰簽章、mTLS 與 client credentials 各自的暴露面、撤銷粒度與基礎建設成本清楚。

## 本章寫作邊界

本章聚焦系統層那一把憑證的機制選擇。呼叫方身分該不該分層、分幾層在 [7.29 API 認證的信任邊界分層](../api-authentication-trust-boundaries/)——那是本章的上游，機制選型只在確定系統層要有獨立身分之後才發生。選定之後憑證怎麼核發與交付在 [7.32 機器憑證的配發](../machine-credential-issuance/)，上線後的輪替與回收在 [7.6 秘密管理與機器憑證治理](../secrets-and-machine-credential-governance/)。各機制的實作細節（雙密過渡怎麼做、mTLS 的 nginx 設定、簽章素材怎麼對齊）在對應的實作文章，本章給的是選哪一個與為什麼。

## 本章 threat scope

**In-scope**：秘密隨請求送出而落在日誌與中繼 / 撤銷粒度與呼叫方數量不匹配 / 機制要求的基礎建設沒有跟上 / 換發憑證的那一跳成為單點。

**Out-of-scope**（路由到他章）：

- 呼叫方身分要分幾層 → [7.29](../api-authentication-trust-boundaries/)
- 選定之後憑證怎麼交到對方手上 → [7.32](../machine-credential-issuance/)
- 上線後的輪替、回收與事件收斂 → [7.6](../secrets-and-machine-credential-governance/)
- 這個機制屬於哪一類密碼學原語、金鑰放哪裡 → [7.28](../cryptographic-primitive-selection/)
- 憑證的信任鏈與續期節奏 → [7.5](../transport-trust-and-certificate-lifecycle/)
- 一個系統代表某個特定的人 → [7.33](../delegated-credential-selection/)

上列每一項在下方問題節點表都有對應的一列。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表「前置控制面」欄的連結進知識卡，看該控制的機制、邊界與適用條件。
- **Delivery**：「交接路由」欄位指向 [05 部署平台](/backend/05-deployment-platform/)、[06 可靠性](/backend/06-reliability/)、[08 事故處理](/backend/08-incident-response/)。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

## 先確認自己有沒有選擇權

多數整合在這一步沒有選擇權，而這件事要先確認再往下走。呼叫的是對方的 API 時，能用的機制由對方提供，文件寫什麼就是什麼；被呼叫的是自己的 API 時，選擇權在自己，但每一個既有的呼叫方都要跟著改。**選擇權在自己這邊的實際範圍，是「還沒有任何呼叫方的新介面」加上「呼叫方少到協調得動的既有介面」。**

沒有選擇權時本章其餘各節仍然有用，但用途不同：它給的是「照對方的方式接上去之後，我這邊還缺哪一塊」。對方只給一把長期 API key 時，暴露面與撤銷粒度都由那個選擇決定，自己能做的是在自己這一側補上日誌遮罩與存取隔離，並把差額記成已知風險。

## 兩個問題把選項分開

**問題一：這個秘密本身要不要在每次呼叫裡送出去。** 這一題決定它最後會留在哪些地方。

送出去的機制（共享密鑰、API key、client credentials 換 token 的那一次）把秘密交給整條傳輸路徑上的每一跳處理，而那些跳點各自有自己的記錄行為——反向代理的存取日誌、內容傳遞網路的邊緣節點、應用層的請求追蹤、以及對方那一側的同一組系統。秘密沒有洩漏，只是被記錄了，而記錄的保存期限與可讀範圍由那些系統各自的設定決定。放進網址參數是這一格最嚴重的形態，因為網址幾乎必然被完整記錄；放進 header 好一些，但請求追蹤工具的預設多半也會抓 header。

不送出去的機制（共享密鑰簽章、mTLS）只把秘密用來運算：網路上流的是簽章值或握手結果，秘密本身留在兩端的記憶體裡。代價是兩邊都要實作運算邏輯，而排錯比「比對一個字串」難得多——失敗時只會得到「對不起來」，看不出是哪一個欄位不一致。

**問題二：撤銷一把憑證要影響幾個呼叫方。** 這一題決定事件當天的處置範圍。

共享密鑰是一把服務全部，撤銷等於中斷整條整合，這條約束的實際份量見 [7.29 系統層的撤銷](../api-authentication-trust-boundaries/#身分維度分層模型)。API key 與 mTLS 憑證是一個呼叫方一把，撤銷影響單一對象。client credentials 撤的是長期 secret，而已經換出去的短期 token 要等它自己過期——這一格的殘留窗口等於 token 的有效期。

## 五種機制的對照

| 機制                     | 秘密要不要送出去           | 撤銷粒度                         | 要有的基礎建設                     |
| ------------------------ | -------------------------- | -------------------------------- | ---------------------------------- |
| 共享密鑰                 | 要                         | 全部呼叫方                       | 無                                 |
| API key                  | 要                         | 單一呼叫方                       | 對照表與發放介面                   |
| 共享密鑰簽章             | 不要                       | 單一密鑰                         | 兩端的簽章實作與素材規格           |
| mTLS                     | 不要                       | 撤該張憑證                       | CA、簽發與續期、撤銷清單或線上查詢 |
| OAuth client credentials | 第一次要，之後帶短期 token | 撤長期 secret，短 token 自然過期 | token 端點與它的可用性             |

表格右欄最容易被低估。前兩種的基礎建設成本接近零，後三種各自要一組配套，而那組配套的維護成本在整合數量少的時候看起來可以吸收——直到它到期或故障。

**共享密鑰**適合內部固定夥伴、呼叫方只有一個、變更頻率低的情形。它的成本全部落在日後：多一個呼叫方就要重新評估，而重新評估的時機通常是事件當天。

**API key** 是對外開放與多租戶的預設。它比共享密鑰多的那張對照表，正是「撤一把只影響一個」這個能力的載體。

**共享密鑰簽章**適合秘密不想經過網路、或需要同時防篡改與重放的情形，webhook 的接收端多半落在這裡。它引進的是另一組問題（進入計算的素材要雙方一致、時間戳與識別值要被檢查），判讀見 [7.35 簽章對接的驗證收斂](../signature-integration-verification/)。

**mTLS** 適合合規要求或零信任網路。選它之前要先確認 CA 的簽發、續期與撤銷是自動的——這一項的判讀在 [7.5 傳輸信任與憑證生命週期](../transport-trust-and-certificate-lifecycle/)，而它是本章最常被跳過的前置。

**OAuth client credentials** 適合跨組織且需要細權限的情形，範圍表達見 [authorization scope](/backend/knowledge-cards/authorization-scope/)。它把長期秘密的暴露窗口壓到只有換發那一次，代價是換發端點成為每次呼叫的前置依賴。

## 判讀流程

1. 先確認選擇權在誰。在對方那邊時跳到第 5 步。
2. 再問這個秘密送不送得起：傳輸路徑上有幾跳會記錄請求、那些記錄的保存期限與可讀範圍是什麼。答不出來時預設它會被記錄，選不送出去的那一類。
3. 接著數呼叫方。只有一個且短期內不會變時共享密鑰可以接受，並把「出現第二個呼叫方」寫成重新評估的觸發條件；兩個以上直接要 per-caller 的粒度。
4. 再確認選中的機制要的基礎建設現在就有。mTLS 要問憑證續期是不是自動的、client credentials 要問 token 端點掛掉時呼叫方怎麼辦。沒有的話這一項的建置要與整合本身一起排，而不是排在它之後。
5. 最後把選定的機制與上面四題的答案一起登記，接到 [7.32 機器憑證的配發](../machine-credential-issuance/) 的核發與交付。沒有選擇權的整合同樣要登記，記的是「由對方決定」與差額風險。

## 問題節點（案例觸發式）

| 問題節點               | 判讀訊號                                    | 風險後果                                   | 前置控制面                                                                                                                                           | 交接路由  |
| ---------------------- | ------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| 秘密隨請求落進紀錄     | 憑證出現在網址參數，或請求追蹤抓完整 header | 憑證的可讀範圍等於各跳點紀錄的保存範圍     | [secret-management](/backend/knowledge-cards/secret-management/)、[audit-log](/backend/knowledge-cards/audit-log/)                                   | `04 + 06` |
| 撤銷粒度與呼叫方不匹配 | 一把憑證服務兩個以上的呼叫方                | 撤銷單一對象要中斷全部                     | [token-revocation](/backend/knowledge-cards/token-revocation/)、[credential](/backend/knowledge-cards/credential/)                                   | `06 + 08` |
| 基礎建設沒有跟上       | 選了 mTLS 而簽發與續期是手動                | 同批簽發的憑證同時到期，整合同時中斷       | [certificate-rotation-renewal](/backend/knowledge-cards/certificate-rotation-renewal/)、[acme-automation](/backend/knowledge-cards/acme-automation/) | `05 + 06` |
| 換發那一跳成為單點     | token 端點故障時呼叫方沒有降級路徑          | 長期秘密仍然有效，而所有呼叫方同時失去存取 | [fallback](/backend/knowledge-cards/fallback/)、[circuit-breaker](/backend/knowledge-cards/circuit-breaker/)                                         | `06`      |

## 問題節點出現在什麼樣的系統

上表的訊號要等機制上線才量得到。設計階段對照的是下面這幾種形態。

**秘密隨請求落進紀錄**出現在把憑證當成一般參數處理的整合。網址參數這一種多半來自「先讓它通」的除錯階段，通了之後沒有人回頭改；header 那一種則是被工具帶進來的——請求追蹤與錯誤回報服務的預設多半抓完整 header，而那個預設在導入時沒有人逐項看過。識別動作是拿一段時間的存取紀錄搜尋自己的憑證前綴。

**撤銷粒度與呼叫方不匹配**出現在憑證比呼叫方先存在的系統。第一條整合開了一把密鑰，第二條來的時候那把已經能用，於是沿用——這與 [7.6 token 分域不足](../secrets-and-machine-credential-governance/#問題節點出現在什麼樣的系統) 是同一個機制在機制選型層的形態。識別特徵是問得出「這把憑證現在有誰在用」的人只有一位。

**基礎建設沒有跟上**出現在安全評審把機制選對、而維運能力沒有一起評估的組織。選 mTLS 的決定在設計階段做，憑證續期的痛在一年後才發生，兩者中間隔著一次交接。

**換發那一跳成為單點**出現在剛從長期憑證換到 client credentials 的系統。換過去的動機是壓縮暴露窗口，而那個動機不會帶出「這個端點掛掉會怎樣」這個問題。

基礎建設沒有跟上的後果在這張表裡最不直觀：選對了機制、上線正常、稽核也過。它的失敗長這樣：合規要求對外整合走 mTLS，團隊建了一個內部 CA、為當時的兩個對接方各簽了一張一年期憑證，上線順利。一年後兩張憑證在同一週到期，兩條整合同時斷，而那一週沒有任何人在等這件事發生。

沒有被提前發現，是因為憑證到期不產生漸進訊號：到期前一秒的連線與平常完全相同，監控盯的連線成功率在到期當下垂直落下、沒有前兆。「還剩多久到期」要主動去查才有，而查它的動作在自動續期尚未建立的環境裡沒有承載者——它不屬於任何一個既有的排程。

止血要重新簽發並在兩端同時換，而對方那一側要人工配合，於是中斷時間由對方的排期決定。真正的修法在選型當下：把續期自動化當成選 mTLS 的前置條件而非後續工作，路徑見 [acme-automation](/backend/knowledge-cards/acme-automation/) 與 [7.5 傳輸信任與憑證生命週期](../transport-trust-and-certificate-lifecycle/)。

## 常見風險邊界

- 憑證出現在網址參數時，代表它的可讀範圍已經無法界定——各跳點的紀錄保存期限不由自己決定，處置要連同輪替一起做。
- 同一把憑證服務兩個以上的呼叫方，而其中任一個是外部組織時，撤銷粒度的缺口會在事件當天變成「要中斷幾條整合」這個沒有好答案的問題。
- 選定的機制要求的基礎建設由人工承擔時，這條整合的可用性上限由那個人的排程決定，這超出工程修復能承擔的範圍。
- 換發端點沒有獨立的可用性目標時，代表所有依賴它的整合共用一個沒有人負責的單點。
- 對方只提供一種機制而那一種不符合自己的合規要求時，處置要往合約層或架構層走：要求對方支援、在中間加一層自己控制的代理、或接受並記錄例外，例外的期限與重評估條件見 [7.14 資安治理例外與 Tripwire](../security-governance-exception-and-tripwire/)。

## 案例觸發參考

- 硬編碼憑證被檢索重用： [USAHERDS 2021](../red-team/cases/edge-exposure/usaherds-cve-2021-44207-hardcoded-credential/)
- 憑證集中與輪替排序壓力： [CircleCI 2023](../red-team/cases/supply-chain/circleci-2023-secrets-rotation/)
- 第三方 token 成為內部入口： [GitHub OAuth 2022](../red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/)
- 輪替的作用域與證據欄位示範： [7.27 Credential Rotation with Scoped Evidence](../credential-rotation-scoped-evidence/)

## 下一步路由

- 上游（要不要有獨立的系統層身分）：[7.29 API 認證的信任邊界分層](../api-authentication-trust-boundaries/)
- 選定之後憑證怎麼核發、交付與登記：[7.32 機器憑證的配發](../machine-credential-issuance/)
- 選了共享密鑰簽章之後的素材對齊與重放收斂：[7.35 簽章對接的驗證收斂](../signature-integration-verification/)
- 這個機制屬於哪一類原語、金鑰放在哪一格：[7.28 密碼學原語選型](../cryptographic-primitive-selection/)
- mTLS 的憑證生命週期判讀：[7.5 傳輸信任與憑證生命週期](../transport-trust-and-certificate-lifecycle/)
- 上線後的輪替、回收與事件收斂：[7.6 秘密管理與機器憑證治理](../secrets-and-machine-credential-governance/)
- 各機制的實作細節（雙密過渡、mTLS 部署、簽章實作）：[API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) 的「Layer 2：系統層」一節與它列出的各篇
- 例外的期限與重評估：[7.14 資安治理例外與 Tripwire](../security-governance-exception-and-tripwire/)
