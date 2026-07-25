---
title: "入口上 IaC — ALB、TLS 與健康檢查"
date: 2026-06-26
description: "Application Load Balancer 的 listener、target group、健康檢查閾值設計，以及用 ACM 把 TLS 憑證的簽發、驗證與掛載整條鏈寫進版本控制"
weight: 4
tags: ["infra", "iac", "alb", "tls", "load-balancer"]
---

ALB（Application Load Balancer）描述流量進入系統的第一站。它在 IaC 裡的接線責任是把三個層次釘清楚：listener 決定監聽哪些 port 與協定、target group 決定流量導向哪些運算後端、health check 決定後端是否健康到可以接流量。ALB 本身是 stateless 的 — 重建不會遺失資料，但會換掉它的 DNS 名稱，所以對外服務通常在它前面再掛一層穩定的 DNS 記錄（Route 53 alias 或 CNAME），讓使用者看到的網域不隨 ALB 重建而改變。

ALB 掛在 public subnet、引用專屬的 security group，security group 的入站通常只開 80 和 443 對 `0.0.0.0/0`（這是少數合理出現全開的位置，因為 ALB 的工作本來就是接收公開流量）。後端運算節點住在 private subnet，它們的 security group 入站只允許來自 ALB security group 的流量 — 這個 group-to-group 引用讓規則跟著成員身分走，不跟著 IP 走（見[模組三：網路地基](/infra/03-network-foundation/)）。

## ALB 與 listener 設定

ALB 資源本身描述的是它掛在哪些 subnet、用哪個 security group、是對外（`internal = false`）還是內部。Listener 則是掛在 ALB 上的監聽端點，每個 listener 綁定一個 port + protocol 的組合。

```hcl
resource "aws_lb" "api" {
  name               = "api-${var.env}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for s in aws_subnet.public : s.id]
}
```

### HTTP 到 HTTPS 的強制跳轉

正式服務通常同時建兩個 listener：port 443 接受 HTTPS 流量並轉發到後端，port 80 接收 HTTP 流量後直接回一個 301 redirect 到 HTTPS — 確保使用者即使用 `http://` 開頭訪問也會被導到加密連線。

```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.api.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.api.arn
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

`ssl_policy` 決定 ALB 接受哪些 TLS 版本與密碼套件。選擇以安全與相容性為取捨 — `ELBSecurityPolicy-TLS13-1-2-2021-06` 只接受 TLS 1.2 和 1.3，能阻擋過時協定的降級攻擊，但會拒絕仍在使用 TLS 1.0/1.1 的極舊用戶端。對面向公眾的 API 或網站，TLS 1.2 以上是合理的底線；如果有明確的舊用戶端需求（例如嵌入式設備），再往下調但要知道代價。

### 多服務共用 ALB

一個 ALB 可以掛多個 listener rule，用 host header 或 path 把流量分到不同的 target group。這讓多個微服務共用一個 ALB（省成本），而不需要每個服務各開一個：

```hcl
resource "aws_lb_listener_rule" "auth" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  condition {
    path_pattern { values = ["/auth/*"] }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.auth.arn
  }
}
```

一個常見的收斂機會：如果每個服務都各自開了一個 ALB，但流量都從同一個入口進來、只是路徑不同，可以收斂成一個 ALB 加 listener rule。每個 ALB 有固定的小時費，少開幾個月費就少幾筆。反過來，當不同服務的安全等級或流量特性差異大到需要獨立的 security group 和 WAF 規則時，分開 ALB 才合理。

## target group 與健康檢查

Target group 定義一組接收流量的後端（ECS task、EC2 instance 或 IP），以及判斷這些後端是否健康的檢查邏輯。它是 ALB 和實際運算之間的橋樑。

```hcl
resource "aws_lb_target_group" "api" {
  name        = "api-${var.env}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/healthz"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    matcher             = "200"
  }
}
```

### 健康檢查的閾值設計

健康檢查的路徑與閾值是最常被忽略的判讀點。各參數之間的交互作用決定了兩個時間窗口：新後端多久後開始接流量、壞後端多久後被移出。

`healthy_threshold = 2` 配 `interval = 15` 代表一個新啟動的後端要等 30 秒（兩次通過）才開始接流量。`unhealthy_threshold = 3` 代表連續三次失敗（45 秒）才被移出。閾值太寬鬆會把壞掉的後端留在輪替裡，讓部分使用者持續收到錯誤；太嚴格會在部署瞬間 — 新容器啟動、應用還在初始化 — 就判定不健康，反覆移出移入，使用者看到間歇性失敗。

| 參數                  | 過小的風險                     | 過大的風險               | 起點建議 |
| --------------------- | ------------------------------ | ------------------------ | -------- |
| `interval`            | ALB 對後端造成額外負擔         | 壞後端被偵測到的延遲增加 | 15-30 秒 |
| `healthy_threshold`   | 還沒完全就緒就接流量           | 部署後等太久才開始分流   | 2-3 次   |
| `unhealthy_threshold` | 暫時性波動導致健康的後端被移出 | 壞後端繼續收流量太久     | 2-3 次   |
| `timeout`             | 正常但偏慢的回應被誤判為失敗   | 確實掛了卻要等很久才確認 | 5 秒     |

### 健康檢查路徑的選擇

`path` 指向的端點應該能反映應用是否確實能服務請求，而不只是 process 還活著。一個只回 200 的空端點（所謂 liveness check）證明 HTTP server 在跑，但不代表它能連到資料庫、能讀到必要的 config。較合理的做法是讓 `/healthz` 至少檢查核心依賴的連線（例如 ping 一下 DB），失敗時回 503。代價是健康檢查會跟著核心依賴一起報不健康 — 如果 DB 暫時斷了，所有後端都會被判定不健康，ALB 會回 503 給使用者。這是正確的行為：如果應用確實無法服務請求，把它標成不健康比假裝健康好。

判讀方式：部署後觀察 target group 裡的 healthy / unhealthy 轉換次數。如果每次部署都看到新 target 在 healthy 與 unhealthy 之間跳動，代表初始等待不夠 — 應用的啟動時間超出 `healthy_threshold * interval`，考慮加大 `healthy_threshold` 或設定 ECS 的 `startPeriod`（啟動寬限期）讓健康檢查在應用初始化期間暫停。

## TLS 憑證：ACM 簽發、DNS 驗證與自動續期

HTTPS listener 引用的 TLS 憑證也屬於 ALB 的接線。用 ACM（AWS Certificate Manager）簽發的憑證在 IaC 裡完整描述 — 涵蓋網域與 DNS 驗證方式 — 讓「憑證存在、驗證、掛載」整條鏈都進版本控制，而非在 Console 手動上傳一份會過期沒人盯的憑證。

ACM 簽發的憑證使用 DNS 驗證時，ACM 要求在指定的 DNS 記錄上放一段驗證值。Terraform 可以自動建立這段記錄並等待驗證通過：

```hcl
resource "aws_acm_certificate" "api" {
  domain_name       = "api.${var.domain}"
  validation_method = "DNS"

  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => dvo
  }
  zone_id = data.aws_route53_zone.main.zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}
```

### create_before_destroy 的必要性

`create_before_destroy = true` 確保憑證更新（例如加 SAN 或續期觸發重建）時先建新的再刪舊的，避免 listener 在交接期間沒有可用憑證。Terraform 預設行為是先刪後建，會造成一個短暫的 HTTPS 中斷窗口 — listener 找不到憑證、所有 HTTPS 連線失敗直到新憑證簽發並驗證完畢。

ACM 簽發的憑證自動續期：只要 DNS 驗證記錄還在（由 Terraform 管理，所以會一直在），ACM 在到期前 60 天自動續期。這是把憑證管理成本降到接近零的做法 — 不需要排程提醒、不需要手動下載上傳。判讀訊號：如果 CloudWatch 出現 `DaysToExpiry` 降到 30 以下的 alarm，代表自動續期失敗，通常是 DNS 驗證記錄被手動刪了或 Route 53 zone 變了。

### 多網域憑證（SAN）

一張 ACM 憑證可以涵蓋多個網域（Subject Alternative Names），例如 `api.example.com` 和 `admin.example.com` 共用一張。在 IaC 裡用 `subject_alternative_names` 列舉：

```hcl
resource "aws_acm_certificate" "multi" {
  domain_name               = "api.${var.domain}"
  subject_alternative_names = ["admin.${var.domain}", "*.internal.${var.domain}"]
  validation_method         = "DNS"

  lifecycle { create_before_destroy = true }
}
```

共用一張還是分開簽取決於生命週期：如果這幾個網域總是一起上下線、一起變更，共用一張省維護；如果各自獨立演進，分開簽讓變更範圍更小。

## DNS zone 管理與 ALB 的銜接

### Hosted zone：DNS 記錄的容器

Route 53 的 hosted zone 是一個網域下所有 DNS 記錄的容器。public hosted zone 管理對外可見的網域（如 `example.com`），private hosted zone 管理只在 VPC 內可解析的內部網域（如 `internal.example.com`），讓服務之間用 DNS 名稱互連而不靠 IP。

多環境的 DNS 管理常用子網域 delegation：production 用 `example.com`（主 zone），dev 和 staging 各用 `dev.example.com` 和 `staging.example.com`（子 zone）。子 zone 可以放在不同帳號、由不同團隊管理，主 zone 只需要一組 NS 記錄指向子 zone。這讓環境之間的 DNS 邊界跟帳號邊界對齊。

```hcl
resource "aws_route53_zone" "main" {
  name = var.domain
}

resource "aws_route53_zone" "staging" {
  name = "staging.${var.domain}"
}

resource "aws_route53_record" "staging_ns" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "staging.${var.domain}"
  type    = "NS"
  ttl     = 300
  records = aws_route53_zone.staging.name_servers
}
```

hosted zone 也是 ACM 憑證 DNS 驗證的依賴 — ACM 簽發憑證時需要在對應的 zone 寫入一條驗證記錄，zone 不存在或不在同帳號就接不上。把 zone 的建立排在 ACM 之前，讓依賴圖自然正確。

### ALB 的穩定 DNS 記錄

ALB 重建後 DNS 名稱會改變。穩定對外的方式是在 Route 53 建一條 alias 記錄指向 ALB，使用者連的是 `api.example.com`，DNS 自動解析到 ALB 目前的位址：

```hcl
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "api.${var.domain}"
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}
```

`evaluate_target_health = true` 讓 Route 53 在 ALB 所有 target 都不健康時把這條記錄標為不健康。如果有多個 region 的 ALB 做了 failover routing，這個設定能讓 DNS 層自動切換到健康的 region — 屬於跨區域容災的地基，在 運維 模組展開。

## WAF 與下一步

ALB 支援掛載 AWS WAF（Web Application Firewall），在流量進到應用之前先過一層規則 — 擋已知惡意 IP、防 SQL injection / XSS 的常見模式、限制單一 IP 的請求速率。WAF 的規則也可以寫進 IaC，讓「哪些流量被擋」成為可審查的程式碼而非 Console 上的設定。WAF 的詳細設計屬於安全層的範圍（見 [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)），這裡只確認它的掛載點是 ALB。

四類核心服務的 IaC 描述到此完成。下一步是讓這些服務可被觀測——log、metric、alarm 跟資源同生命週期建立，見[模組六：可觀測性與 log](/infra/06-observability-logging/)。

## 跨分類引用

- → [模組三：網路地基](/infra/03-network-foundation/)：ALB 的 security group 設計，group-to-group 引用
- → [模組三：流量入口層](/infra/03-network-foundation/traffic-entry-layer/)：ALB 作為 L7 入口在請求責任鏈的位置、跟單機 nginx 的選擇條件（本篇 IaC 是那個決策落地的一端）
- → [模組五：stateful 資源的保護策略](/infra/05-core-services/stateful-protection-dependency/)：ALB 是 stateless，但它引用的 ACM 憑證和 DNS 記錄有自己的生命週期考量
- → [運維 模組一：負載平衡](/operations/01-load-balancing/)：ALB 的運行期調校 — 跨 AZ 流量分配、connection draining、sticky session
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：WAF 規則設計
