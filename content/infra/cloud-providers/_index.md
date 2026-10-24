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
- [Google Cloud](/infra/cloud-providers/gcp/)：IAP 管理通道、MIG 與 GKE 的管理存取、帳單停損開關

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

| 項目                                                                                                                                                  | 類型   | 前置條件                                                   | 規模           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------- | -------------- |
| 管理通道模型在 AWS 上的實作篇（SSM Session Manager、EC2 Instance Connect），產出放 `cloud-providers/aws/`                                             | 主章   | 有可建 EC2 與 IAM role 的 AWS 測試帳號，篇內指令實跑過才寫 | 1 篇（中）     |
| AWS Systems Manager Session Manager 知識卡（代理程式反向連線的代表實作）                                                                              | 知識卡 | 無                                                         | 1 張卡（小）   |
| Home Region / OCPU 知識卡（OCPU 卡一併涵蓋 vCPU 與超執行緒的換算）                                                                                    | 知識卡 | 無                                                         | 2 張卡（小）   |
| Tenancy、Compartment 與 OCID 知識卡（行內定義已在五篇以上重複）                                                                                       | 知識卡 | 無                                                         | 1–2 張卡（小） |
| 業者代理程式（guest agent）、cloud-init、Service Quota、Spot／Preemptible、業者私有連線（service gateway、VPC endpoint、Private Google Access）知識卡 | 知識卡 | 無                                                         | 5 張卡（中）   |
| 自架 VPN 的用途對照：出口 IP 的國家、閒置回收、流量額度、VPN port 在雲端與作業系統兩道防火牆都要放行，串起散在 pricing、account、networking 的判斷    | 主章   | 無                                                         | 1 篇（小）     |
| 收費比較補上 AWS、GCP 以外業者（例如 Linode、Vultr）                                                                                                  | vendor | 實際申請過或查到官方規則                                   | 小             |
