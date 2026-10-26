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

## 子資料夾

- [Oracle Cloud 的實作紀錄](/infra/cloud-providers/oracle-cloud/hands-on/)：照著做就能重現的操作紀錄（建立 A1 主機與建立前的檢查、容量不足時的重送腳本、Bastion 工作階段逾時的排查、Run Command 補公鑰的嘗試、改用 Oracle Linux 並放公鑰重建後經由 port forwarding session 登入），概念寫在本層的文章，實作文章連回來

## Backlog

| 項目                                                                                                                                                                                                                                     | 類型 | 前置條件                                                                                                                                                           | 規模       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| Bastion 管理通道實作文章，放 `hands-on/`（managed SSH session 在 A1 加 Oracle Linux 上走一次、建工作階段需要的 IAM 政策、稽核紀錄）                                                                                                      | 主章 | 一台 A1 Oracle Linux 9 主機，建好先用 `plugin list` 確認有 Bastion（`available-plugins get` 查到 10 沒有、9 分不出）；`verify-a1` 已終止，A1 額度還有 1 OCPU、6 GB | 1 篇（中） |
| 〈Oracle Cloud 建立主機的實測紀錄〉的刪除資源順序實際跑一次                                                                                                                                                                              | 案例 | `verify-a1` 已終止；剩下的 `verify-a1-ol` 與網路等使用者決定刪除                                                                                                   | 小         |
| Run Command 寫回 `authorized_keys` 的實測：建立時用 cloud-init 放 `ocarun` 的 sudoers、再用 Run Command 寫公鑰，以及一般使用者送指令要的政策                                                                                             | 案例 | 政策那一半可以在 `verify-a1-ol` 上驗；sudoers 那一半要新建一台 A1（額度還有 1 OCPU）                                                                               | 小         |
| Ubuntu 平台映像在 Authorization header 開著（只允許中繼資料第二版）時，cloud-init 寫不寫得進公鑰；Oracle Linux 10.2 已在 2026-10-25 驗過寫得進                                                                                           | 案例 | 一台放了公鑰的 A1 Ubuntu 主機（額度還有 1 OCPU）                                                                                                                   | 小         |
| OCI 的最小權限：群組、限定 compartment 的 policy 範例（日常帳號、CI 專用使用者）；可併入 Bastion 那一篇                                                                                                                                  | 主章 | 先查官方 policy 範例                                                                                                                                               | 中         |
| Always Free 主機被閒置回收或試用結束停用之後的狀態與恢復                                                                                                                                                                                 | 案例 | 遇到一次實際回收或停用                                                                                                                                             | 小         |
| 主機的維護、暫停與恢復上線實測紀錄，放 `hands-on/`：照主機清單跑維護檢查、主控台停止主機、暫停期間的計費與 DNS 狀態、恢復上線的每一步與耗時；概念文章在 [模組九：單台主機的長期維護、服務暫停與恢復上線](/operations/09-host-lifecycle/) | 主章 | 2026-10-26 建的 `verify-origin`；邊緣安全事件實測收完基準流量、Bot Fight Mode 量測完成之後才停機（停機會中斷那邊的流量收集）                                       | 1 篇（中） |
| 2026-10-25 審查列出、還沒查證的登入替代做法：Cloud Shell 接私有網路直接 ssh、主控台建立頁依映像列出的可用 plugin、dynamic port forwarding（SOCKS5）session 的連線指令                                                                    | 案例 | `verify-a1-ol`；Cloud Shell 那一項要先查 Private Network 需要的政策                                                                                                | 小         |
