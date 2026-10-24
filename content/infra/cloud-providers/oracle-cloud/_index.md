---
title: "Oracle Cloud（OCI）"
date: 2026-10-24
description: "申請了 Oracle Cloud 免費帳號、要在 Always Free 額度內建主機並從本機管理時，查帳號結構、CLI 登入與實測紀錄"
weight: 3
tags: ["infra", "cloud-providers", "oracle-cloud", "oci"]
---

Oracle Cloud Infrastructure（OCI）的免費方案分成 30 天的試用金與沒有期限的 Always Free 資源，Always Free 資源綁在申請時選的 home region。這個資料夾的文章都在一個 Free Tier 帳號上實際操作過，實測日期寫在各篇裡。

## 章節文章

| 文章                                                                                                  | 主題                                                       |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) | tenancy 與 home region、Always Free 的範圍、主控台登入欄位 |
| [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)          | `oci session authenticate`、token 時效、API 簽章金鑰       |
| [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/)   | 主控台各分頁的取值、等效 CLI 指令、容量不足                |

## Backlog

| 項目                     | 類型 | 前置條件                         | 規模 |
| ------------------------ | ---- | -------------------------------- | ---- |
| Bastion 管理通道實測文章 | 主章 | home region 有可用的免費機型容量 | 中   |
