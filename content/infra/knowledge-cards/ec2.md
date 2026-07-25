---
title: "EC2"
date: 2026-06-26
description: "AWS 的虛擬機器服務，提供可隨時啟停的運算實例，組成包含 AMI、instance type、EBS、security group 與 IAM role"
weight: 37
tags: ["infra", "knowledge-cards"]
---

EC2（Elastic Compute Cloud）是 AWS 提供的虛擬機器服務。每一台 EC2 instance 是一台完整的虛擬伺服器——有自己的 OS、CPU、記憶體、磁碟和網路介面。使用者可以 [SSH](/infra/knowledge-cards/ssh/) 進去、安裝軟體、跑應用程式，跟操作一台實體伺服器的體驗相似。

## 概念位置

EC2 是 infra 系列中「運算」面向的基礎單位。容器服務（[ECS](/infra/knowledge-cards/ecs/)、EKS）底層也跑在 EC2 上（除非用 Fargate）。模組五（核心服務）的運算段落、接手維運（雲端篇）的 VM 快照、升級模組的 OS 遷移都以 EC2 為操作對象。

## 可觀察訊號

需要理解 EC2 的情境包括：接手一個跑在 VM 上的應用程式、評估容器化 vs VM 部署、設定 auto-scaling、或建立 AMI 快照作為備份。

## 設計責任

一台 EC2 instance 由五個組件構成：

| 組件           | 角色                                       | 選型判準                    |
| -------------- | ------------------------------------------ | --------------------------- |
| AMI            | 作業系統映像（Ubuntu、Amazon Linux 等）    | OS 偏好、軟體預裝需求       |
| Instance type  | CPU / 記憶體規格（t3.micro、m6i.large 等） | 工作負載的 CPU 和記憶體需求 |
| EBS            | 持久化磁碟                                 | 容量、IOPS、是否需要加密    |
| Security group | 網路防火牆規則                             | 哪些 port 開放、來源限制    |
| IAM role       | instance 的雲端權限                        | 需要存取哪些 AWS 服務       |

跟容器（ECS / EKS）的差別：EC2 管整台 VM（含 OS 更新、安全性修補、磁碟管理），容器只管應用程式及其依賴。EC2 的運維負擔較高、但控制粒度也較高。

## 鄰卡

- [AMI](/infra/knowledge-cards/ami/)
- [ECS](/infra/knowledge-cards/ecs/)
- [Subnet](/infra/knowledge-cards/subnet/)
- [Security Group](/infra/knowledge-cards/security-group/)
