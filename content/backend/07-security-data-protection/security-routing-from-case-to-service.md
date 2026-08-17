---
title: "7.8 模組路由：問題到服務實作"
date: 2026-04-24
description: "一份資安交接單要填哪些欄位，以及一個問題該交給部署、可靠性還是事故處理"
weight: 78
tags: ["backend", "security"]
---

本章的責任是把問題節點轉成跨模組交接規則。核心輸出是交接條件與責任切分，讓概念層與實作層保持同一條決策路徑。

要寫一份交接單的話，九個欄位與各欄的判準在下方的[交接模板](#交接模板)段——那是本模組交接欄位的定義處，其餘各篇沿用它。

## 路由基線

路由基線的責任是維持章節分工穩定。07 模組先完成問題判讀，再把實作交接到 05/06/08。

1. 先判斷問題節點與影響面。
2. 再確認判讀訊號與風險等級。
3. 接著建立收斂順序與責任鏈。
4. 最後交接到對應實作章節。

## 主題路由表（問題驅動）

| 問題主題                                                  | 概念入口                                                                                 | 交接章節                                                                                                                                |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 身分擴散與授權濫用                                        | [7.2](/backend/07-security-data-protection/identity-access-boundary/)                    | [08 事故回應](/backend/08-incident-response/)                                                                                           |
| 入口暴露與管理面風險                                      | [7.3](/backend/07-security-data-protection/entrypoint-and-server-protection/)            | [05 部署平台](/backend/05-deployment-platform/) + [08 事故回應](/backend/08-incident-response/)                                         |
| 資料暴露與交換責任鏈                                      | [7.4](/backend/07-security-data-protection/data-protection-and-masking-governance/)      | [05 部署平台](/backend/05-deployment-platform/) + [08 事故回應](/backend/08-incident-response/)                                         |
| 信任鏈與憑證節奏                                          | [7.5](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)   | [05 部署平台](/backend/05-deployment-platform/) + [06 可靠性](/backend/06-reliability/)                                                 |
| 秘密治理與機器身份                                        | [7.6](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)   | [05 部署平台](/backend/05-deployment-platform/) + [06 可靠性](/backend/06-reliability/) + [08 事故回應](/backend/08-incident-response/) |
| 稽核證據與責任切分                                        | [7.7](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)     | [08 事故回應](/backend/08-incident-response/)                                                                                           |
| 服務生命週期風險節奏                                      | [7.9](/backend/07-security-data-protection/security-lifecycle-risk-cadence/)             | [06 可靠性](/backend/06-reliability/) + [08 事故回應](/backend/08-incident-response/)                                                   |
| Workload 聯邦信任                                         | [7.10](/backend/07-security-data-protection/workload-identity-and-federated-trust/)      | [05 部署平台](/backend/05-deployment-platform/) + [06 可靠性](/backend/06-reliability/) + [08 事故回應](/backend/08-incident-response/) |
| 資料駐留與刪除證據鏈                                      | [7.11](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/) | [06 可靠性](/backend/06-reliability/) + [08 事故回應](/backend/08-incident-response/)                                                   |
| 供應鏈與 artifact 信任                                    | [7.12](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)  | [05 部署平台](/backend/05-deployment-platform/) + [06 可靠性](/backend/06-reliability/) + [08 事故回應](/backend/08-incident-response/) |
| 偵測覆蓋與訊號治理                                        | [7.13](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)   | [04 可觀測性](/backend/04-observability/) + [08 事故回應](/backend/08-incident-response/)                                               |
| 例外治理與 [tripwire](/backend/knowledge-cards/tripwire/) | [7.14](/backend/07-security-data-protection/security-governance-exception-and-tripwire/) | [06 可靠性](/backend/06-reliability/) + [08 事故回應](/backend/08-incident-response/)                                                   |

## 章節交接條件

章節交接條件的責任是讓概念層輸出可以被實作層直接使用。

1. 交接前輸出：問題節點、判讀訊號、風險邊界、責任角色。
2. 交接中輸出：控制面優先序、驗證節奏、回退條件。
3. 交接後輸出：觀測指標、復盤入口、重新評估觸發器。

## 路由決策流程

路由流程的責任是避免章節重複、避免控制面遺漏。

1. 先確認問題是否已超過單一模組可處理範圍。
2. 再確認優先處理的是入口風險、驗證風險或事故節奏風險。
3. 接著把問題切成[部署平台](/backend/05-deployment-platform/)、[可靠性](/backend/06-reliability/)與[事故回應](/backend/08-incident-response/)的可執行項。
4. 最後定義回寫點，確保 07 的判讀語言會被下一輪更新。

## 交接模板

交接模板的責任是讓不同章節用同一種輸入輸出格式合作。這九項是本模組交接欄位的定義處，其他章節沿用這組名稱：

- 問題摘要：一句話描述失效樣式與影響面。
- 判讀訊號：列出可觀測事件與觸發閾值。
- 風險邊界：列出升級條件與停止條件。
- 控制面優先序：列出先做、後做、可延後動作。
- 承接範圍：這條風險的後續工作落在哪個模組或哪個團隊的範圍內。它回答的是範圍歸屬、不是課責。
- 主責與協作角色：範圍裡具名的人或角色——交接的另一端要有人接。範圍指得出來而角色點不出名字時，交接沒有完成，因為模組不會自己讀交接單。
- 驗證與回退：列出驗證指標、觀察時窗與回退條件。
- 這一輪的完成條件：接手方憑什麼判斷自己接完了。它與風險邊界的停止條件不同——停止條件講的是何時該中止，完成條件講的是何時可以結案並把責任交回。少了它，交接會停在「已經交出去」而沒有人宣告收到並完成。
- 回寫規則：列出要更新的章節、卡片與案例索引。

沿用這組名稱的有四處，各自的軸不同：[7.B1 防守控制面地圖](../blue-team/defense-control-map/) 的每筆映射（軸是哪個控制面主責）、[7.16 從公開事故到工程 Workflow](../incident-case-to-control-workflow/) 的 workflow 任務（軸是案例回寫的第幾步）、[7.18 資安控制面如何交接到部署與事故流程](../security-control-handoff-to-delivery-and-incident/) 的交接契約（軸是模組之間的責任順序），以及 [7.21 資安如何成為服務設計輸入](../security-as-service-design-input/) 的交接路由欄（軸是設計評審那個時點的填法）。

四處各只填其中一部分，而**省略要說得出理由、不是照份量砍**。可省的理由只有三種：那一項已經被同一份產物的其他結構承載（地圖的每一列就是一個風險節點，問題摘要與風險邊界寫在列標題與判讀欄裡、控制面優先序由控制面分組表達）、那一項在交接發生前就已經在上游定案且住址在別章（7.18 的模組交接接的是判讀完成之後的風險，判讀訊號與風險邊界的落點是主控制面那幾章）、那一項在這個時點還不可知（設計評審還沒有可觀測的訊號與驗證數據，所以 7.21 把判讀訊號與驗證回退留給實作階段）。三種理由的共同形式是「這一項的內容有別的落點或還不存在」，而「這次先不填」不在其中。判準之外的省略要當成缺口處理，而有兩項幾乎不會落在判準之內。**主責與協作角色在四處都要填**——沒有任何結構能替它承載，交接的另一端要有人接。**這一輪的完成條件在交接是一次有邊界的移交時要填**（7.18 的三輪、7.21 的設計評審通過），而地圖那種常態維護的產物沒有「這一輪」可言，它的對應問題由驗證與回退承接。兩者是最常被省掉的欄位，因為省掉的當下沒有人會抗議。

## 文件邊界

文件邊界的責任是維持模組分工穩定。

- `07`：定義問題語言、判讀訊號、風險邊界與路由規則。
- `05`：落地入口、網路、部署與平台控制面。
- `06`：落地驗證、演練、回退與可靠性節奏。
- `08`：落地分級、指揮、通報、收斂與復盤閉環。
