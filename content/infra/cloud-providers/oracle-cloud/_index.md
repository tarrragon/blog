---
title: "Oracle Cloud（OCI）"
date: 2026-10-24
description: "準備申請或已經申請了 Oracle Cloud 免費帳號（home region 要在送出申請之前選）、要在 Always Free 額度內建主機並從本機管理時，查帳號結構、CLI 登入與實測紀錄"
weight: 4
tags: ["infra", "cloud-providers", "oracle-cloud", "oci"]
---

Oracle Cloud Infrastructure（OCI）的免費方案分成 30 天的試用金與沒有期限的 Always Free 資源，Always Free 資源綁在申請時選的 home region。這個資料夾的文章都在一個 Free Tier 帳號上實際操作過，實測日期寫在各篇裡。

## 章節文章

| 文章                                                                                                  | 主題                                                       |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Oracle Cloud 主控台導覽](/infra/cloud-providers/oracle-cloud/console-navigation/)                    | 頂端列、導覽選單、compartment 篩選器、常用頁面路徑         |
| [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) | tenancy 與 home region、Always Free 的範圍、主控台登入欄位 |
| [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)          | `oci session authenticate`、token 時效、API 簽章金鑰       |
| [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/)   | 主控台各分頁的取值、等效 CLI 指令、容量不足                |

## Backlog

| 項目                                                                                                                                                                                                                                                                    | 類型 | 前置條件                                                | 規模       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------- | ---------- |
| Bastion 管理通道實測文章（private subnet、managed SSH session、port forwarding session 用自己的公鑰登入、建工作階段需要的 IAM 政策、稽核紀錄）                                                                                                                          | 主章 | home region 的 A1 建立請求成功（Batam 沒有 E2.1.Micro） | 1 篇（中） |
| A1 建成之後把結果補進〈Oracle Cloud 建立主機的實測紀錄〉：Authorization header 開著時 Ubuntu 上 managed SSH session 能否經由 Bastion plugin 建立、代理程式讀中繼資料是否正常（這台選 No SSH keys）；cloud-init 寫公鑰要另一台放了公鑰的主機驗；刪除資源的順序實際跑一次 | 案例 | A1 建立請求成功                                         | 小         |
| Run Command 寫回 `authorized_keys` 的實測（`ocarun` 的 sudo 設定、送指令的政策）                                                                                                                                                                                        | 案例 | A1 建立請求成功                                         | 小         |
| OCI 的最小權限：群組、限定 compartment 的 policy 範例（日常帳號、CI 專用使用者）；可併入 Bastion 那一篇                                                                                                                                                                 | 主章 | 先查官方 policy 範例                                    | 中         |
| Always Free 主機被閒置回收或試用結束停用之後的狀態與恢復                                                                                                                                                                                                                | 案例 | 遇到一次實際回收或停用                                  | 小         |
