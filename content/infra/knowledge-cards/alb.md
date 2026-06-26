---
title: "ALB"
date: 2026-06-26
description: "Application Load Balancer — 流量進入系統的第一站，負責 listener 路由、健康檢查與 TLS 終結"
weight: 12
tags: ["infra", "knowledge-cards", "alb", "load-balancer"]
---

ALB（Application Load Balancer）的核心職責是接收外部流量、根據規則（path、host header）把請求路由到後端的 target group，並用健康檢查持續驗證後端是否能服務。它是系統對外的第一個接觸點，跑在 public subnet 裡。

## 概念位置

ALB 在核心服務層裡的角色是「入口設施」。它掛在 public subnet 的 security group 上（入站允許 80/443），把流量導向 private subnet 裡的 ECS task 或 EC2 instance。ALB 本身是 stateless 的 — 重建一個 ALB 不會遺失資料，但會換掉它的 DNS 名稱，所以對外服務通常在 ALB 前面掛一個穩定的 Route 53 alias record。

TLS 終結是 ALB 的標準職責：HTTPS listener 引用 ACM（AWS Certificate Manager）簽發的憑證，ALB 處理加解密，後端收到的是 HTTP 明文。憑證由 ACM 自動續期，IaC 用 DNS 驗證方式描述憑證 — 讓「憑證存在、續期、掛載」整條鏈都進版本控制。

## 可觀察訊號

以下狀況指向 ALB 相關問題：

- 使用者看到 502 — ALB 轉發請求但後端回應異常（健康檢查可能通過但實際請求處理失敗），查 target group 的健康狀態和後端 log
- 使用者看到 503 — target group 裡沒有健康的後端，通常是部署期間所有舊 task 停了但新 task 還沒通過健康檢查
- HTTPS 憑證過期警告 — 如果用 ACM 搭配 DNS 驗證，憑證自動續期；看到過期警告代表 DNS 驗證記錄被刪了或 ACM 服務異常

## 設計責任

使用 ALB 時要決定：

- **健康檢查參數**：檢查路徑（用應用層的 health endpoint、不用根路徑）、間隔、閾值。閾值太寬鬆會把壞掉的後端留在輪替裡，太嚴格會在部署瞬間誤判
- **HTTP → HTTPS redirect**：port 80 的 listener 設定固定回應 301 redirect 到 443，確保所有流量走加密
- **TLS 憑證**：用 ACM 搭配 DNS 驗證，讓憑證的簽發和續期自動化
- **穩定 DNS**：ALB 前面掛 Route 53 alias record，對外暴露的是自己的 domain name 而非 ALB 的隨機 hostname

## 鄰卡

- [Subnet](/infra/knowledge-cards/subnet/) — ALB 跑在 public subnet，後端跑在 private subnet
- [Security Group](/infra/knowledge-cards/security-group/) — ALB 的 security group 是系統對外唯一合理開放 0.0.0.0/0 的位置（僅限 80/443）
- [ECS](/infra/knowledge-cards/ecs/) — ALB 透過 target group 把流量導向 ECS task
