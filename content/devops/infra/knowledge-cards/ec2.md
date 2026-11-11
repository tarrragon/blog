---
title: "EC2"
date: 2026-06-26
description: "AWS 的虛擬機器服務，提供可隨時啟停的運算實例，組成包含 AMI、instance type、EBS、security group 與 IAM role"
weight: 37
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/ec2/"]
---

EC2（Elastic Compute Cloud）是 AWS 提供的虛擬機器服務。每一台 EC2 instance 是一台完整的虛擬伺服器——有自己的 OS、CPU、記憶體、磁碟和網路介面。使用者可以 [SSH](/devops/infra/knowledge-cards/ssh/) 進去、安裝軟體、跑應用程式，跟操作一台實體伺服器的體驗相似。

## 跟其他概念的關係

EC2 是 infra 系列中「運算」面向的基礎單位。容器服務（[ECS](/devops/infra/knowledge-cards/ecs/)、EKS）底層也跑在 EC2 上（除非用 Fargate）。模組五（核心服務）的運算段落、接手維運（雲端篇）的 VM 快照、升級模組的 OS 遷移都以 EC2 為操作對象。

## 可觀察訊號

需要理解 EC2 的情境包括：接手一個跑在 VM 上的應用程式、評估容器化 vs VM 部署、設定 auto-scaling、或建立 AMI 快照作為備份。

## 判斷條件與後果

一台 EC2 instance 由五個組件構成：

| 組件           | 角色                                       | 選型標準                    |
| -------------- | ------------------------------------------ | --------------------------- |
| AMI            | 作業系統映像（Ubuntu、Amazon Linux 等）    | OS 偏好、軟體預裝需求       |
| Instance type  | CPU / 記憶體規格（t3.micro、m6i.large 等） | 工作負載的 CPU 和記憶體需求 |
| EBS            | 持久化磁碟                                 | 容量、IOPS、是否需要加密    |
| Security group | 網路防火牆規則                             | 哪些 port 開放、來源限制    |
| IAM role       | instance 的雲端權限                        | 需要存取哪些 AWS 服務       |

跟容器（ECS / EKS）的差別：EC2 管整台 VM（含 OS 更新、安全性修補、磁碟管理），容器只管應用程式及其依賴。EC2 的運維負擔較高、但控制粒度也較高。

五個組件在 instance 建立之後的可改程度不同，選錯時付出的代價也不同。Security group 與 IAM role 可以在 instance 執行中修改，改了立即生效，選錯的代價是修改前那段時間的暴露範圍或權限。Instance type 要先停止 instance 才能換，選錯的代價是一次停機。AMI 決定了根磁碟的初始內容，換 AMI 要換掉整顆根磁碟，原本根磁碟上手動裝的軟體與設定要重新做一次，這也是為什麼裝好的機器要另外做成 [AMI](/devops/infra/knowledge-cards/ami/) 快照才重建得出來。跟容器比較時，判斷的條件是團隊是否有人負責 OS 的更新與修補：選 EC2 時這些工作由團隊自己做，沒有人做時 OS 的已知漏洞會一直留在機器上。

## 鄰卡

- [AMI](/devops/infra/knowledge-cards/ami/)
- [ECS](/devops/infra/knowledge-cards/ecs/)
- [Subnet](/devops/infra/knowledge-cards/subnet/)
- [Security Group](/devops/infra/knowledge-cards/security-group/)
- [Availability Zone（可用區）](/devops/infra/knowledge-cards/availability-zone/)
- [Instance Metadata Service（實例中繼資料服務）](/devops/infra/knowledge-cards/instance-metadata-service/)
