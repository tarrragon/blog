---
title: "Security Group"
date: 2026-06-26
description: "掛在資源網卡層級的有狀態防火牆，逐埠決定哪些來源能連進這個資源"
weight: 6
tags: ["infra", "knowledge-cards", "security-group", "network"]
---

Security group 是掛在資源網卡（ENI）層級的有狀態防火牆，規則描述的是「哪些來源能連到這個資源的哪個埠」。「有狀態」的意思是放行一條入站連線後，對應的回應出站自動允許——規則只需描述入站方向想開放什麼。

設計原則是最小開放：每條規則只開「這個服務確實需要被誰連的那個埠」。資料庫的 security group 入站只允許來自應用層 security group 的資料庫埠（如 5432），而不是某個 IP 範圍。用 security group 互相引用（source 指向另一個 group 而非 CIDR）讓規則跟著成員身分走、不跟著位址走——應用節點會隨擴縮而換 IP，引用 group 不會因此失效。

## 概念位置

Security group 是[模組三：網路地基](/infra/03-network-foundation/vpc-subnet-security-group/)的最內層邊界——貼著服務的最後一道網路防線。即使封包順著 route table 抵達了 private [subnet](/infra/knowledge-cards/subnet/)，security group 仍能逐埠決定放不放行。[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)用 tfsec / checkov 在 CI 攔截 `0.0.0.0/0` 全開的規則。

## 可觀察訊號

Security group 需要收斂的訊號：入站來源是 `0.0.0.0/0`（允許全網連入），且目標埠是資料庫（5432、3306、6379）或管理埠（22、3389）——合理出現 `0.0.0.0/0` 的位置只有對外負載平衡器的 80 / 443。盤點方式是列出所有 source 為 `0.0.0.0/0` 的規則，逐條問「這個埠需要全世界都連得到嗎」。

## 設計責任

設計 security group 時要決定：

- 引用方式：用 group 互相引用（推薦）vs 用 CIDR 限定範圍
- 開放範圍：只開需要的埠與來源，`0.0.0.0/0` 只給對外 LB
- 管理埠存取：SSH（22）改用 SSM Session Manager 取代，從公網清單上拿掉
- 與 NACL 的分工：security group 是主力（有狀態、group 引用），NACL 留給少數需要 subnet 層顯式 deny 的情境

## 鄰卡

- [VPC](/infra/knowledge-cards/vpc/) — security group 依附的網路容器
- [Subnet](/infra/knowledge-cards/subnet/) — security group 與 subnet 各守不同層級的邊界
