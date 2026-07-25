---
title: "EBS"
date: 2026-06-26
description: "掛在 EC2 instance 上的持久化區塊儲存（虛擬磁碟），支援 snapshot 快照備份，跟 instance 獨立生命週期"
weight: 38
tags: ["infra", "knowledge-cards"]
---

EBS（Elastic Block Store）是 AWS 提供的區塊儲存服務——可以把它理解為掛在 [EC2](/infra/knowledge-cards/ec2/) instance 上的虛擬硬碟。EBS volume 跟 EC2 instance 的生命週期獨立：instance 停止或終止時，EBS volume 上的資料不會消失（除非明確設定 `DeleteOnTermination`）。

## 概念位置

EBS 是 infra 系列中儲存面向的底層組件。RDS 的資料實際存在 EBS 上（由 AWS 代管）、EC2 的根磁碟和附加磁碟都是 EBS volume。接手維運時對 VM 做快照（[AMI](/infra/knowledge-cards/ami/)），背後就是在對 EBS volume 做 snapshot。

## 可觀察訊號

需要理解 EBS 的情境包括：EC2 instance 的磁碟快滿了需要擴容、要對 VM 做快照備份、評估磁碟效能（IOPS）是否足夠、或清理不再掛載的孤立 volume（殭屍 volume 持續計費）。

## 設計責任

| 設定                | 決定什麼                                   | 影響                                             |
| ------------------- | ------------------------------------------ | ------------------------------------------------ |
| Volume type         | gp3（通用）/ io2（高 IOPS）/ st1（高吞吐） | 效能與成本                                       |
| Size                | 磁碟容量（GB）                             | 線上擴容可行、但縮小不行                         |
| Encryption          | 是否加密                                   | 合規（建立後不可更改，要加密只能建新的複製過去） |
| Snapshot            | 快照備份                                   | EBS snapshot 是增量的（只存變更的區塊）          |
| DeleteOnTermination | instance 終止時是否跟著刪除                | 根磁碟預設 true、附加磁碟預設 false              |

跟 instance store 的差別：instance store 是 EC2 實體主機上的臨時磁碟，效能高但 instance 停止資料就消失。EBS 是持久化儲存，instance 停止資料仍在。

## 鄰卡

- [EC2](/infra/knowledge-cards/ec2/)
- [Deletion Protection](/infra/knowledge-cards/deletion-protection/)
