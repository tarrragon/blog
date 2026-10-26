---
title: "雲端業者的帳號申請與主機維運"
date: 2026-10-24
description: "要向某一家雲端業者申請帳號、評估免費額度、看懂建立主機頁上的各個欄位與主控台的管理領域，或從本機用 CLI 管理主機時，查 vendor 中立的選項說明、各家帳號結構、免費額度規則與實測過的建置紀錄"
weight: -5
tags: ["infra", "cloud-providers", "free-tier"]
---

這個模組收各家雲端業者自己的那一層：帳號與區域在申請當下就固定的設定、主控台與 CLI 的登入方式、免費額度的計算規則，以及在那一家實際建主機、走管理通道的紀錄。成熟度階梯（模組零到九）講的是 vendor 中立的地基，這裡放的是同一件事落到某一家時才會遇到的設定與陷阱。

模組是橫切的：任何一階實作時都可能需要先在某一家開帳號。內容的歸屬規則是：成熟度階梯的模組放 vendor 中立的概念，正文的範例以 AWS 為參考實作，但不收某一家的完整實作篇；這個模組的根目錄放跨業者、在主控台與帳號層操作的內容（建立主機的選項、主控台的管理領域、免費額度比較）；某一家的實作與實測紀錄放在業者子資料夾，例如管理通道在 GCP 上的 IAP 實作、帳單停損在 GCP 上的建置。概念文章連到業者子資料夾，業者子資料夾的每一篇連回它實作的那個概念。

## 章節文章

| 文章                                                                           | 主題                                                                                                         |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/) | 計費單位、免費額度的區域限制、試用結束後的處置、出站流量                                                     |
| [雲端主控台的管理領域](/infra/cloud-providers/console-areas/)                  | 身分、資源分組、運算、網路、儲存、費用、監控、稽核、安全服務與配額各管什麼，新帳號先看哪幾個，三家的選單名稱 |

## 子資料夾

依 weight 排列（list.html 先列子資料夾、再列文章，所以兩篇根目錄文章在列表頁排在子資料夾之後）：

- [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/)：vendor 中立，依功能分類一類一篇（位置、機型與映像檔、網路、登入、磁碟、代理程式與維護、安全開機）
- [Oracle Cloud](/infra/cloud-providers/oracle-cloud/)：主控台導覽、帳號結構與 home region、CLI 登入、建立主機的實測紀錄
- [Google Cloud](/infra/cloud-providers/gcp/)：IAP 管理通道、MIG 與 GKE 的管理存取、帳單停損開關，三個主題各有一篇概念文章與一篇實測紀錄

新增一家業者時開一個子資料夾，在收費比較那篇補上那一家的欄位，再用下面這條掃一次，把寫死成目前業者組合的句子、並列句與對照表一起更新。掃描對象不寫死業者數，所以加過一家之後下一次照樣有效：

```bash
rg -n "[一二三四五六七八九]家|其他兩家|另兩家|Google Cloud 與 AWS|AWS 與 Google Cloud|Oracle Cloud .*Google Cloud .*AWS" \
  content/infra/cloud-providers/ content/infra/knowledge-cards/availability-zone.md \
  content/infra/knowledge-cards/fault-domain.md content/infra/knowledge-cards/instance-metadata-service.md
```

## 跟其他模組的關係

- → [模組三：網路地基](/infra/03-network-foundation/)：管理通道的三層模型，各家實作的實測對照它
- → [運行期維運的成本管理](/operations/08-cost-management/)：成本監控與計費模型；預算警示的中立篇還在那個模組的 Backlog，要不要建停損，依據是各家試用結束後會不會自動開始計費
- → [接手維運](/infra/takeover/)：用主控台建好的資源要收進 IaC 時的匯入流程
- → [主機形態光譜](/going-live/hosting-spectrum/)：選 IaaS 之前先決定要管多少

## Backlog

| 項目                                                                                                                                                                                                                                                                                                                                          | 類型   | 前置條件                                                                                   | 規模           |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------ | -------------- |
| 管理通道模型在 AWS 上的實作篇（SSM Session Manager、EC2 Instance Connect），產出放 `cloud-providers/aws/`                                                                                                                                                                                                                                     | 主章   | 有可建 EC2 與 IAM role 的 AWS 測試帳號，篇內指令實跑過才寫                                 | 1 篇（中）     |
| AWS Systems Manager Session Manager 知識卡（代理程式反向連線的代表實作）                                                                                                                                                                                                                                                                      | 知識卡 | 無                                                                                         | 1 張卡（小）   |
| Home Region / OCPU 知識卡（OCPU 卡一併涵蓋 vCPU 與超執行緒的換算）                                                                                                                                                                                                                                                                            | 知識卡 | 無                                                                                         | 2 張卡（小）   |
| Tenancy、Compartment 與 OCID 知識卡（行內定義已在五篇以上重複）                                                                                                                                                                                                                                                                               | 知識卡 | 無                                                                                         | 1–2 張卡（小） |
| 業者代理程式（guest agent）、cloud-init、Service Quota、Spot／Preemptible、業者私有連線（service gateway、VPC endpoint、Private Google Access）知識卡                                                                                                                                                                                         | 知識卡 | 無                                                                                         | 5 張卡（中）   |
| 自架 VPN 的用途對照：出口 IP 的國家、閒置回收、流量額度、VPN port 在雲端與作業系統兩道防火牆都要放行，串起散在 pricing、account、networking 的判斷                                                                                                                                                                                            | 主章   | 無                                                                                         | 1 篇（小）     |
| 收費比較補上 AWS、GCP 以外業者（例如 Linode、Vultr）                                                                                                                                                                                                                                                                                          | vendor | 實際申請過或查到官方規則                                                                   | 小             |
| Egress（出站流量）與 MFA（多因素驗證）知識卡：本模組的 pricing、account、console-areas 與 operations 的 billing-models 都用到，全站沒有卡；卡放 `infra/knowledge-cards/` 或 `backend/knowledge-cards/`，建好之後回填各篇第一次出現的位置                                                                                                      | 知識卡 | 無                                                                                         | 2 張卡（小）   |
| Terraform Provider 知識卡（Terraform 操作某一類資源的外掛、`required_providers` 與 `terraform init` 下載的關係）：全站約 25 篇把 Terraform 與 provider 寫在一起，沒有卡；卡放 `infra/knowledge-cards/`，建好之後回填各篇第一次出現的位置（含 operations 模組九的多台主機實作紀錄）                                                            | 知識卡 | 無                                                                                         | 1 張卡（小）   |
| 模組標題「雲端業者的帳號申請與主機維運」與內容對齊：模組實際收的是建立主機的欄位、主控台的管理領域、免費額度比較，以及各家的帳號結構、CLI 登入與建置實測，標題的「主機維運」讀起來涵蓋開機之後的日常維運；改標題時同一次改 `infra/_index.md`、`infra/03-network-foundation/_index.md` 與 `operations/08-cost-management/_index.md` 的連結文字 | 跨模組 | 先定新標題                                                                                 | 小             |
| vm-options/shape-and-image〈停止主機時的計費〉：在作業系統裡下 `shutdown` 之後 Oracle Cloud 主控台顯示的主機狀態，以及計費依據是業者那一端記錄的主機狀態這條機制，補成「習慣在主機裡關機 → 帳單照樣計費 → 改從主控台停止」的情境                                                                                                              | 主章   | 讀到 Oracle Cloud 官方原文寫出 OS 內關機後的主機狀態與計費依據；讀不到就只補機制以外的部分 | 小             |
| vm-options/placement〈故障域（fault domain）：同一棟裡的哪一組硬體〉與 Fault Domain 卡：兩台主機都用預設「讓業者選」時，Oracle Cloud 是否自動把它們放進不同的故障域；不保證的話寫明兩台要手動指定不同的故障域                                                                                                                                 | 主章   | 讀到 Oracle Cloud 官方原文                                                                 | 小             |
