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

- [Oracle Cloud 的實作紀錄](/infra/cloud-providers/oracle-cloud/hands-on/)：照著做就能重現的操作紀錄（建立 A1 主機與建立前的檢查、容量不足時的重送腳本、Bastion 工作階段逾時的排查、Run Command 補公鑰的嘗試），概念寫在本層的文章，實作文章連回來

## Backlog

| 項目                                                                                                                                                                                          | 類型 | 前置條件                                                              | 規模       |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------- | ---------- |
| Bastion 管理通道實作文章，放 `hands-on/`（private subnet、port forwarding session 用自己的公鑰登入、managed SSH session 在 A1 加 Oracle Linux 上走一次、建工作階段需要的 IAM 政策、稽核紀錄） | 主章 | 一台放了公鑰的 A1 主機，或一台 A1 Oracle Linux 主機（都要重新搶容量） | 1 篇（中） |
| 2026-10-25 那台 A1 Ubuntu 主機的去留：Run Command 已試過（`ocarun` 沒有 sudo），剩下自訂映像替換開機磁碟、開機磁碟掛到另一台主機或重建；結果補進〈Oracle Cloud 建立主機的實測紀錄〉           | 案例 | 使用者決定要不要重搶 A1 容量                                          | 小         |
| 用 Run Command 讀那台主機的代理程式版本（`snap list oracle-cloud-agent`）與 Bastion plugin 的日誌（`ocarun` 在 `adm` 群組），補進〈成因：A1 加 Ubuntu 是官方列出的不支援組合〉                | 案例 | CLI 重新登入                                                          | 小         |
| 〈Oracle Cloud 建立主機的實測紀錄〉補兩項：cloud-init 在 Authorization header 開著時寫公鑰、刪除資源的順序實際跑一次                                                                          | 案例 | 新建一台放了公鑰的 A1 主機；刪除排在上一列結案之後                    | 小         |
| Run Command 寫回 `authorized_keys` 的實測：建立時用 cloud-init 放 `ocarun` 的 sudoers、再用 Run Command 寫公鑰，以及一般使用者送指令要的政策                                                  | 案例 | 新建一台主機（A1 要重新搶容量）                                       | 小         |
| OCI 的最小權限：群組、限定 compartment 的 policy 範例（日常帳號、CI 專用使用者）；可併入 Bastion 那一篇                                                                                       | 主章 | 先查官方 policy 範例                                                  | 中         |
| Always Free 主機被閒置回收或試用結束停用之後的狀態與恢復                                                                                                                                      | 案例 | 遇到一次實際回收或停用                                                | 小         |
