---
title: "模組七：資安與資料保護"
date: 2026-04-24
description: "以問題驅動方式擴充資安知識網：先定義服務環節問題，再以案例作為觸發式參考"
weight: 7
---

本模組的責任是把資安議題拆成可重用的問題節點。章節先定義問題、判讀訊號、風險邊界與路由條件，再由案例在需要時提供證據參考。

## 模組方法

問題驅動方法的核心是讓案例退到證據角色，讓知識網以服務環節問題為主體。

1. 先定義服務環節問題與責任邊界。
2. 再定義判讀訊號與風險後果。
3. 接著定義交接路由與前置控制面。
4. 最後在問題觸發時引用對應案例。

## 模組分工定位

本模組提供觀念、判讀與路由。實作細節由對應模組承接，確保概念層與實作層分工清晰。

- `backend/05-deployment-platform`：入口、部署與平台邊界實作。
- `backend/06-reliability`：驗證、回復與變更節奏實作。
- `backend/08-incident-response`：分級、指揮、通報與復盤實作。

## 章節列表（大綱階段）

| 章節                                                                            | 主題                               | 核心責任                                 |
| ------------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------- |
| [7.1 攻擊者視角（紅隊）與攻擊面驗證](red-team/)                                 | 攻擊者判讀語言                     | 把攻擊路徑轉成服務問題語言               |
| [7.2 身分與授權邊界](identity-access-boundary/)                                 | Identity & Access                  | 定義身份擴散、授權濫用、會話收斂問題     |
| [7.3 入口治理與伺服器防護](entrypoint-and-server-protection/)                   | Entrypoint & Server                | 定義入口暴露、管理面與修補窗口問題       |
| [7.4 資料保護與遮罩治理](data-protection-and-masking-governance/)               | Data Protection                    | 定義資料暴露、匯出、備份與跨界交換問題   |
| [7.5 傳輸信任與憑證生命週期](transport-trust-and-certificate-lifecycle/)        | Transport Trust                    | 定義信任鏈、會話完整性與憑證節奏問題     |
| [7.6 秘密管理與機器憑證治理](secrets-and-machine-credential-governance/)        | Secrets & Credentials              | 定義 secret/token/key 的分域與收斂問題   |
| [7.7 稽核追蹤與責任邊界](audit-trail-and-accountability-boundary/)              | Audit & Accountability             | 定義證據模型、責任鏈與可回查問題         |
| [7.8 模組路由：問題到服務實作](security-routing-from-case-to-service/)          | Routing                            | 定義概念層到實作層的交接規則             |
| [7.9 服務生命週期的資安風險節奏](security-lifecycle-risk-cadence/)              | Lifecycle Risk Cadence             | 定義設計到復盤五段的資安節奏問題         |
| [7.10 Workload Identity 與聯邦信任邊界](workload-identity-and-federated-trust/) | Workload Identity & Federation     | 定義非人類身份與跨平台信任問題           |
| [7.11 資料駐留、刪除與證據鏈](data-residency-deletion-and-evidence-chain/)      | Data Residency & Deletion Evidence | 定義資料位置、刪除閉環與證據可驗證問題   |
| [7.12 供應鏈完整性與 Artifact 信任](supply-chain-integrity-and-artifact-trust/) | Supply Chain Integrity             | 定義 build 與 artifact 信任鏈問題        |
| [7.13 偵測覆蓋率與訊號治理](detection-coverage-and-signal-governance/)          | Detection & Signal Governance      | 定義偵測覆蓋、訊號品質與誤報成本問題     |
| [7.14 資安治理例外與 Tripwire](security-governance-exception-and-tripwire/)     | Governance Exception & Tripwire    | 定義例外決策期限、補償控制與重評估觸發器 |

## 本輪輸出

本輪只完成章節大綱與問題骨架。後續填充會依章節逐步展開判讀細節與案例觸發條件。
