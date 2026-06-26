---
title: "ACM 憑證、DNS 與 HTTPS 設定"
date: 2026-06-26
description: "從 Route 53 hosted zone 到 ACM 憑證申請、DNS 驗證、ALB HTTPS listener 與 HTTP 重導的完整設定流程"
weight: 6
tags: ["infra", "tls", "acm", "dns", "route53"]
---

HTTPS 的運作需要三個元件配合：一個管理網域記錄的 DNS zone、一張證明網域所有權的 TLS 憑證、以及一個用這張憑證終結 TLS 連線的入口（ALB listener）。這三者在 IaC 裡各自是獨立資源，但建立順序有依賴——zone 先存在、憑證才能用 DNS 驗證、驗證通過才能掛到 listener。把這條鏈路寫進 Terraform，讓憑證的申請、驗證與續期都在版本控制裡，是避免「憑證過期才發現沒人盯」的結構性做法。

## Route 53 Hosted Zone

Hosted zone 是 Route 53 用來管理某個網域的 DNS 記錄集合。建立 zone 後，Route 53 會分配一組 NS（Name Server）記錄，網域的 DNS 解析就由這組 NS 負責。

### Public vs Private Zone

Public hosted zone 對應的是可從網際網路解析的網域（如 `example.com`），用於對外服務的 A / CNAME / MX 記錄。Private hosted zone 只在指定的 VPC 內可解析，用於內部服務發現（如 `db.internal.example.com` 解析到 RDS 的 private IP）。多數專案兩者都需要：public zone 給對外流量、private zone 給內部服務互連。

```hcl
resource "aws_route53_zone" "public" {
  name = "example.com"
  tags = { Environment = "production" }
}

resource "aws_route53_zone" "private" {
  name = "internal.example.com"

  vpc {
    vpc_id = aws_vpc.main.id
  }

  tags = { Environment = "production" }
}
```

### 子網域 delegation

當 dev / staging / prod 各用獨立帳號時，每個帳號建自己的 hosted zone 管理子網域（如 `dev.example.com`）。父網域的 zone 需要加一組 NS 記錄指向子網域的 zone，這個動作叫 delegation。

```hcl
resource "aws_route53_record" "dev_ns" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "dev.example.com"
  type    = "NS"
  ttl     = 300
  records = aws_route53_zone.dev.name_servers
}
```

delegation 的 NS 記錄指向子帳號 zone 的 name server。子帳號內的所有 DNS 記錄（如 `api.dev.example.com`）由子帳號的 zone 管理，父帳號不需要逐條設定。跨帳號 delegation 需要兩邊的 Terraform 各自管理自己的 zone，NS 記錄在父帳號的 state 裡。

判讀設定是否正確：用 `dig dev.example.com NS` 查回的 name server 應該是子帳號 zone 的 NS，不是父帳號的。如果查回父帳號的 NS，代表 delegation 沒生效，子網域的 DNS 記錄不會被解析。

## ACM 憑證申請與 DNS 驗證

AWS Certificate Manager（ACM）提供免費的 TLS 憑證，條件是透過 DNS 或 email 驗證網域所有權。DNS 驗證是 IaC 友善的方式——ACM 要求在指定網域下建一條 CNAME 記錄，記錄值由 ACM 提供，驗證通過後憑證自動簽發。

```hcl
resource "aws_acm_certificate" "main" {
  domain_name               = "example.com"
  subject_alternative_names = ["*.example.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = { Environment = "production" }
}
```

`subject_alternative_names` 加 `*.example.com` 讓同一張憑證涵蓋所有子網域（如 `api.example.com`、`admin.example.com`），省去為每個子網域各申請一張。

### DNS 驗證記錄

ACM 簽發後會產出一組驗證用的 CNAME 記錄。用 Terraform 自動在 Route 53 建立這些記錄，讓驗證流程不需要手動操作：

```hcl
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = aws_route53_zone.public.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 300
  records = [each.value.record]

  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}
```

`aws_acm_certificate_validation` 資源會等到 ACM 確認驗證通過才算 apply 成功。如果 DNS 記錄設錯或 zone 的 NS delegation 有問題，這個資源會卡住直到 timeout——排查方向是先確認驗證 CNAME 記錄能被公網 DNS 解析。

### create_before_destroy

`lifecycle { create_before_destroy = true }` 在憑證需要替換時（如增加 SAN、更換網域），讓 Terraform 先建新憑證、再刪舊憑證。沒有這個設定，預設行為是先刪後建——刪除的瞬間 ALB listener 失去憑證，HTTPS 連線全部中斷直到新憑證驗證通過（可能要幾分鐘到幾十分鐘）。

## ALB HTTPS Listener

憑證驗證通過後，把它掛到 ALB 的 HTTPS listener：

```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

`ssl_policy` 決定 TLS 版本與加密套件。`ELBSecurityPolicy-TLS13-1-2-2021-06` 支援 TLS 1.2 和 1.3、停用已知不安全的舊版協定。選型判準是相容性與安全性的平衡——TLS 1.3-only policy 最安全但可能排除舊版客戶端，多數場景用 1.2+1.3 的組合。

`certificate_arn` 引用的是 `aws_acm_certificate_validation` 而非直接引用 `aws_acm_certificate`，確保 listener 只在憑證驗證通過後才建立。

### HTTP → HTTPS 重導

同時建立一個 HTTP listener，把所有 80 埠流量重導到 443：

```hcl
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

301 永久重導讓瀏覽器記住後續直接走 HTTPS。security group 仍然需要開放 80 埠入站，否則重導不會發生——client 連 80 埠被擋、收到的是連線失敗而非重導回應。

## 多網域與 SAN 憑證

一張 ACM 憑證最多支援 10 個 SAN（Subject Alternative Name）。多數場景用主網域 + wildcard（`example.com` + `*.example.com`）就夠用。如果有多個不同根網域（如 `example.com` 和 `example-app.com`），可以加進同一張憑證：

```hcl
resource "aws_acm_certificate" "multi_domain" {
  domain_name               = "example.com"
  subject_alternative_names = [
    "*.example.com",
    "example-app.com",
    "*.example-app.com",
  ]
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}
```

每個 SAN 網域都需要獨立的 DNS 驗證記錄。如果不同網域在不同的 hosted zone 裡，驗證記錄的建立要分別指向各自的 zone。

當 SAN 數量超過 10、或不同網域的憑證需要獨立管理（不同 team 負責不同網域），改用 `aws_lb_listener_certificate` 額外掛載：

```hcl
resource "aws_lb_listener_certificate" "additional" {
  listener_arn    = aws_lb_listener.https.arn
  certificate_arn = aws_acm_certificate.other_domain.arn
}
```

ALB 會根據 SNI（Server Name Indication）自動選擇匹配的憑證。

## 穩定的 DNS 別名記錄

ALB 重建後 DNS 名稱會改變，對外服務不應該直接用 ALB 的 DNS 名稱。用 Route 53 的 alias record 把穩定的網域名指向 ALB：

```hcl
resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "api.example.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
```

alias record 不收費（一般的 A/CNAME 記錄每百萬次查詢 $0.40，alias 到 AWS 資源免費），且支援 zone apex（如 `example.com`，一般 CNAME 不支援 zone apex）。`evaluate_target_health = true` 讓 Route 53 在 ALB 不健康時停止回應該記錄，配合 failover routing 使用。

## 憑證續期監控

ACM 的 DNS 驗證憑證會自動續期——條件是驗證用的 CNAME 記錄仍然存在且可解析。只要那條記錄沒被刪掉，憑證到期前 60 天 ACM 會自動續期。

自動續期失敗的常見原因：驗證 CNAME 記錄被手動刪除、hosted zone 的 NS delegation 失效、或 zone 本身被刪除重建導致 NS 改變。用 CloudWatch alarm 監控憑證到期日，在自動續期失敗時提前收到通知：

```hcl
resource "aws_cloudwatch_metric_alarm" "cert_expiry" {
  alarm_name          = "acm-cert-expiry-${aws_acm_certificate.main.domain_name}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DaysToExpiry"
  namespace           = "AWS/CertificateManager"
  period              = 86400
  statistic           = "Minimum"
  threshold           = 30
  alarm_actions       = [aws_sns_topic.oncall.arn]

  dimensions = {
    CertificateArn = aws_acm_certificate.main.arn
  }
}
```

這個 alarm 在憑證距離到期不足 30 天時觸發。正常情況下 ACM 在到期前 60 天就會完成續期，收到 30 天警報代表自動續期失敗了、需要人工介入確認驗證記錄。

## 跨分類引用

- → [入口上 IaC — ALB](/infra/05-core-services/loadbalancer-alb/)：ALB listener、target group、健康檢查的完整設定
- → [模組三：網路地基](/infra/03-network-foundation/)：ALB 所在的 public subnet 與 security group 設計
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：憑證與 DNS 變更走 PR review
