---
title: "Oracle Cloud 的實作紀錄"
date: 2026-10-25
description: "要在 Oracle Cloud 照著建一台 Always Free 的 A1 主機、在容量不足時重送建立請求，或排查 Bastion managed SSH session 建立逾時時，查實際跑過的指令、輸出與除錯過程"
weight: 10
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "hands-on"]
---

這個資料夾收在 Oracle Cloud 上實際操作的紀錄：前置條件、每一步的指令與輸出、遇到的錯誤與除錯過程、量到的值。觀念與判斷依據寫在上一層的概念文章與 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/)，這裡的文章連回去，不重寫。

## 章節文章

| 文章                                                                                                         | 主題                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) | 建立前的檢查、前置網路、主控台各分頁的取值與替代做法、等效 CLI 指令、容量不足與重送腳本、Bastion 工作階段逾時的排查、Run Command 補公鑰的嘗試、刪除資源的順序 |
