---
title: "Google Cloud（GCP）"
date: 2026-10-24
description: "在 GCP 專案上要把 VM 的 SSH 改走 IAP、管理 MIG 與 GKE 節點的登入，或建預算警示與自動停用帳單的停損開關時，查實作指令與實測紀錄"
weight: 5
tags: ["infra", "cloud-providers", "gcp"]
---

這個資料夾放 vendor 中立的概念落到 Google Cloud 上的實作，每一篇都對應一篇概念文章：管理通道的三層模型在 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)，預算警示與停損的概念目前還寫在 GCP 那一篇裡（反應時間、兩種處置的判斷），vendor 中立的版本要從它抽出來放回 [運行期維運的成本管理](/operations/08-cost-management/)，記在那個模組的 Backlog。三篇的指令都在 GCP 測試專案上實跑過，實跑日期與未實跑的段落寫在各篇裡。

## 章節文章

| 文章                                                                                                                     | 對應的概念 | 主題                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------- |
| [GCP VM 的 SSH 與 RDP 管理通道：從預設的全開規則改走 IAP TCP forwarding](/infra/cloud-providers/gcp/gcp-iap-ssh-access/) | 管理通道   | default 網路自帶規則、IAP 的連線路徑與指令、切換與停用舊規則、連不上時的依層判讀、OS Login、稽核  |
| [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/)                        | 管理通道   | instance template 與 node pool、MIG 用重建取代登入救援、kubectl debug node 的權限邊界、控制層存取 |
| [GCP 上的雲端費用失控防護](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)                           | 成本管理   | 預算警示、強制執行支出上限、由預算通知觸發的停損開關的建置、驗收與恢復                            |

## Backlog

| 項目                                                                                                                                                                                                                                                                                                                                                                                                                 | 類型 | 前置條件                                                                                                          | 規模 |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------- | ---- |
| IAP 與 MIG、GKE 兩篇在 2026-10-24 實跑時還沒驗到的段落：IAP 篇的組織層級護欄（Organization Policy 的 `skipDefaultNetworkCreation`、`vmExternalIpAccess`、`requireOsLogin`、`disableSerialPortAccess`，以及階層式防火牆政策的 `goto_next` 與拒絕規則）、組織外帳號的 `roles/compute.osLoginExternalUser`、Windows VM 的序列主控台（SAC）登入；GKE 篇從未設定 `gcpPublicCidrsAccessEnabled` 的叢集是否放行 GCP 外部 IP | 主章 | 有一個 Organization 資源（Cloud Identity 加自有網域）與其下的 GCP 測試專案；SAC 與 GCP 外部 IP 兩項只需要測試專案 | 中   |
| 〈GCP 上的雲端費用失控防護〉剩下的未實跑部分：組織政策限制 API 與機型（要有組織節點）、只停止花錢的資源對 MIG 與 GKE node pool 的處置與它們需要的角色、`gcloud beta monitoring channels list`、帳單停用超過一分鐘之後同專案函式是否還執行                                                                                                                                                                            | 主章 | 有組織節點的測試帳號；GKE 叢集                                                                                    | 小   |
