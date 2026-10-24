---
title: "雲端業者的帳號申請與主機維運"
date: 2026-10-24
description: "要向某一家雲端業者申請帳號、評估免費額度、建第一台主機或從本機用 CLI 管理它時，查各家帳號結構、登入方式、免費額度規則與實測過的建置紀錄"
weight: -5
tags: ["infra", "cloud-providers", "free-tier"]
---

這個模組收各家雲端業者自己的那一層：帳號與區域在申請當下就固定的設定、主控台與 CLI 的登入方式、免費額度的計算規則，以及在那一家實際建主機、走管理通道的紀錄。成熟度階梯（模組零到九）講的是 vendor 中立的地基，這裡放的是同一件事落到某一家時才會遇到的設定與陷阱。

模組是橫切的：任何一階實作時都可能需要先在某一家開帳號。概念文章裡已經附了 GCP 實作的那幾篇（[GCP IAP 的 SSH 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)、[GCP 帳單防護](/operations/08-cost-management/spend-protection-gcp-budget-killswitch/)）留在原模組，這裡只放跟概念無關、只屬於那一家的部分。

## 章節文章

| 文章                                                                                                  | 主題                                                            |
| ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)                        | 計費單位、免費額度的區域限制、試用結束後的處置、出站流量        |
| [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) | tenancy、home region 不能改、主控台登入的租用戶與使用者名稱欄位 |
| [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)          | session token 登入、時效與 refresh、API 簽章金鑰的取捨          |

## 業者子資料夾

- [Oracle Cloud](/infra/cloud-providers/oracle-cloud/)

新增一家業者時開一個子資料夾，並在收費比較那篇補上那一家的欄位。

## 跟其他模組的關係

- → [模組三：網路地基](/infra/03-network-foundation/)：管理通道的三層模型，各家實作的實測對照它
- → [運行期維運的成本管理](/operations/08-cost-management/)：預算警示與停損是 vendor 中立的設計，要不要建停損，依據是各家試用結束後會不會自動開始計費
- → [主機形態光譜](/going-live/hosting-spectrum/)：選 IaaS 之前先決定要管多少

## Backlog

| 項目                                                                      | 類型   | 前置條件                                          | 規模 |
| ------------------------------------------------------------------------- | ------ | ------------------------------------------------- | ---- |
| Oracle Cloud 的 Bastion 管理通道實測（private subnet、managed SSH、稽核） | 主章   | home region 的 A1 有容量（Batam 沒有 E2.1.Micro） | 中   |
| Home Region / Availability Domain / OCPU 知識卡                           | 知識卡 | 無                                                | 3    |
| 收費比較補上 AWS、GCP 以外業者（例如 Linode、Vultr）                      | vendor | 實際申請過或查到官方規則                          | 小   |
