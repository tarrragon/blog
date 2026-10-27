---
title: "Google Cloud 的實作紀錄"
date: 2026-10-25
description: "要在 GCP 專案上照著把 SSH 與 RDP 改走 IAP、把同樣的設定套到 MIG 與 GKE，或建預算警示與停損開關時，查實際跑過的指令、輸出，以及每一步換一種做法的結果"
weight: 10
tags: ["infra", "cloud-providers", "gcp", "hands-on"]
aliases: ["/infra/cloud-providers/gcp/hands-on/"]
---

這個資料夾收在 Google Cloud 上實際操作的紀錄：前置條件、每一步的指令與輸出、遇到的錯誤、量到的值，以及每一步沒做或換一種做法時的結果。機制與判斷依據寫在上一層的概念文章，這裡的文章連回去，不重寫。

## 章節文章

| 文章                                                                                                                  | 對應的概念文章                                                                                           | 主題                                                                                                     |
| --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/devops/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) | [GCP VM 的 SSH 與 RDP 管理通道](/devops/infra/cloud-providers/gcp/gcp-iap-ssh-access/)                   | 盤點、救援入口、IAP 規則與 IAM、停用舊規則驗證、刪除與收斂舊規則、OS Login 啟用、Cloud NAT 與移除外部 IP |
| [GCP 上 MIG 與 GKE 管理存取的實測紀錄](/devops/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/)        | [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/devops/infra/cloud-providers/gcp/gke-mig-management-access/) | 新 template 與 canary、重建與主機金鑰、退回 template、除錯 namespace、node pool 設定、控制平面端點切換   |
| [GCP 預算警示與停損開關的實測紀錄](/devops/infra/cloud-providers/gcp/hands-on/budget-killswitch-walkthrough/)         | [GCP 上的雲端費用失控防護](/devops/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)    | 預算、主題、服務帳號、函式與觸發器、分段驗收、心跳監看、停用後的恢復                                     |
