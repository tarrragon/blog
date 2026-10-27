---
title: "RDS"
date: 2026-06-26
description: "AWS 的受管關聯式資料庫服務，代管備份、更新與 failover，讓使用者專注在 schema 和查詢"
weight: 35
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/rds/"]
---

RDS（Relational Database Service）是 AWS 提供的受管關聯式資料庫服務。它在 [EC2](/devops/infra/knowledge-cards/ec2/) instance 上跑資料庫引擎（MySQL、PostgreSQL、MariaDB、Oracle、SQL Server），但把作業系統更新、自動備份、跨可用區 failover、磁碟擴容這些運維工作交給 AWS 代管。使用者操作的是資料庫層級的設定（schema、query、parameter group），不需要 SSH 進機器管 OS。

## 概念位置

RDS 是 infra 系列中 stateful 資源的代表。它持有不可重建的資料，所以它的 IaC 描述、備份策略、[刪除保護](/devops/infra/knowledge-cards/deletion-protection/)、變更審查都比 stateless 資源（如 EC2 web server）嚴格。模組五（核心服務）和接手維運模組的資料庫相關段落都以 RDS 為主要範例。

## 可觀察訊號

需要理解 RDS 的情境包括：接手一個已經在跑的 production 資料庫、評估要不要從自建 MySQL 遷移到 RDS、設定資料庫的備份和高可用、或在 IaC 裡描述資料庫資源。

## 設計責任

RDS 持有無法重建的資料，下表的設定設錯時代價依項目不同：backup retention 與 deletion protection 設錯，損失的是救不回來的資料；instance class、engine version 與部分 parameter group 參數事後調整，代價是重開機或一段停機窗口。

| 設定                | 決定什麼                             | 影響                                        |
| ------------------- | ------------------------------------ | ------------------------------------------- |
| instance class      | CPU / 記憶體規格                     | 效能與成本                                  |
| multi-AZ            | 是否跨可用區部署 standby             | 可用性（failover 分鐘級）vs 成本（約 2 倍） |
| backup retention    | 自動備份保留天數（1-35）             | 可回溯的時間窗口                            |
| deletion protection | 是否允許刪除                         | 防誤刪（production 必開）                   |
| parameter group     | 資料庫引擎參數（max_connections 等） | 效能調校                                    |
| engine version      | 資料庫版本                           | 功能與相容性                                |

跟自建 MySQL on EC2 的取捨：RDS 省去 OS 層運維，但 parameter group 和 option group 的可調整範圍比直接操作 my.cnf 窄。需要完全控制 OS 層（如自訂 plugin、特殊檔案系統）時，自建較合理。

## 鄰卡

- [MySQL](/devops/infra/knowledge-cards/mysql/)
- [Deletion Protection](/devops/infra/knowledge-cards/deletion-protection/)
- [Subnet](/devops/infra/knowledge-cards/subnet/)
