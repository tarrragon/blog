---
title: "VPC（Virtual Private Cloud）"
date: 2026-06-26
description: "雲端帳號內的一塊邏輯隔離私有網段，是所有網路切分的起點與容器"
weight: 4
tags: ["infra", "knowledge-cards", "vpc", "network"]
---

VPC（Virtual Private Cloud）是雲端帳號內的一塊邏輯隔離私有網段，是其餘所有網路切分的起點。在 VPC 裡開出來的所有資源預設只看得到同一個 VPC 內的成員，與其他 VPC、與其他帳號的網路天然隔離。沒有 VPC，[subnet](/infra/knowledge-cards/subnet/) 與 [security group](/infra/knowledge-cards/security-group/) 無處依附。

VPC 用 [CIDR](/infra/knowledge-cards/cidr/) 區塊定義地址空間。建立時的 CIDR 大小是一次性決策——事後擴張地址空間在多數雲端平台上是麻煩且容易出錯的操作（AWS 允許追加 secondary CIDR，但追加的網段在 routing 與服務相容性上有限制）。

## 概念位置

VPC 是[模組三：網路地基](/infra/03-network-foundation/vpc-subnet-security-group/)的最外層邊界。Infra 系列的網路設計從 VPC 開始：先圈定地址空間，再往內切 [subnet](/infra/knowledge-cards/subnet/)、掛 route table、設 security group。環境之間的 VPC 怎麼分（每個環境一個 VPC），屬於[模組四：環境分離](/infra/04-environment-separation/directory-module-parameterization/)的設計決策。

## 可觀察訊號

VPC 設計需要關注的訊號：CIDR 空間快用完（subnet 切不出新的子網段）、需要跟其他 VPC 或地端互連時發現 CIDR 重疊（peering 無法建立）、服務被放在預設 VPC 裡（預設 VPC 是所有人共享的、CIDR 不可控的、security group 預設全通的）。

## 設計責任

規劃 VPC 時要決定：

- CIDR 大小：`/16` 提供約六萬五千個位址，對多數單一環境足夠
- 不重疊：多個 VPC（不同環境或產品線）用連續但不重疊的大段分配
- DNS 設定：`enable_dns_support` 和 `enable_dns_hostnames` 在多數場景都該開啟
- 預設 VPC 的處理：正式服務不該放在預設 VPC，新帳號的預設 VPC 可以刪除或保留唯讀

## 鄰卡

- [Subnet](/infra/knowledge-cards/subnet/) — VPC 內按可用區與暴露程度切出的子網段
- [Security Group](/infra/knowledge-cards/security-group/) — 掛在資源上的有狀態防火牆
- [CIDR](/infra/knowledge-cards/cidr/) — VPC 的地址空間定義方式
- [NAT](/infra/knowledge-cards/nat/) — 讓 private subnet 出站的地址轉換機制
