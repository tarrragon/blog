---
title: "網路地基 — VPC、subnet 分層與 security group 設計"
date: 2026-06-26
description: "VPC CIDR 規劃、public / private subnet 切分、route table 與 NAT 的可用性成本取捨、security group 最小開放設計，以及 NACL 的定位"
weight: 1
tags: ["infra", "network", "vpc", "security-group"]
---

網路地基要先於核心服務存在。VPC、subnet、route table 與 security group 構成一張「服務能落在哪、誰能跟誰講話」的地圖，資料庫、運算節點與對外入口都得落在這張地圖規劃好的格子裡。先把邊界畫清楚，後面每個核心服務上線時只需要選一塊已經定義好安全等級的位置，而不是邊開服務邊補洞。

這篇文章建立四層邊界：最外層的 VPC 隔離、中層的 public / private subnet 切分、流量進出的 route table 與 NAT、以及最貼近服務的 security group。每一層解決的問題不同，疊起來才是一個可審計、可收斂的網路。

## VPC：網路隔離的最外層邊界

VPC（Virtual Private Cloud）先圈定整個系統的網路地址空間 — 一塊邏輯隔離的私有網段，是其餘所有網路切分的起點。在 VPC 裡開出來的所有資源預設只看得到同一個 VPC 內的成員，與其他 VPC、與其他帳號的網路天然隔離。它是後面所有切分動作的容器 — 沒有 VPC，subnet 與 security group 無處依附。

### CIDR 規劃：一次決定、事後難改

建立 VPC 時最關鍵的決策是 CIDR 區塊的大小。這個範圍要一次規劃足夠大，因為事後擴張地址空間在多數雲上是麻煩且容易出錯的操作。AWS 雖然允許在 VPC 上追加 secondary CIDR，但追加的網段不能與原有的重疊，也不是所有服務都能自然使用跨 CIDR 的 subnet，routing 的複雜度會因此上升。

CIDR 規劃要同時考慮三件事。第一是容量：`/16` 提供約六萬五千個位址，對多數單一環境的 VPC 足夠寬裕，切成 `/24` 的 subnet 也有 256 個可用子網。第二是不重疊：未來若要透過 VPC peering、Transit Gateway 或 VPN 把這個 VPC 接回地端機房或其他環境，重疊的 CIDR 會讓路由無法解析。三個環境各自是 `10.0.0.0/16`，在彼此不需要互連時不是問題，但一旦要開 peering 就會撞車 — 這時候改 CIDR 的代價是重建整個 VPC。第三是預留：如果公司同時有多個 VPC（不同環境或不同產品線），用連續但不重疊的大段分配（如 dev `10.0.0.0/16`、staging `10.1.0.0/16`、prod `10.2.0.0/16`）讓路由表更乾淨。

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "platform-prod"
    Environment = "production"
  }
}
```

`enable_dns_support` 和 `enable_dns_hostnames` 在多數場景都該開啟。沒開 DNS hostname 時，EC2 instance 不會拿到可解析的 hostname，某些服務依賴 DNS 尋址而非 IP（如 VPC endpoint 的 private DNS），關著會讓它們靜靜失敗而不報錯。

判讀訊號：規劃 CIDR 時先問「這個環境三年後會有幾個 subnet、跨幾個可用區、要不要跟其他 VPC 或地端互連」。風險集中在地址耗盡與網段衝突 — 兩者都得在開第一個 subnet 之前定案。VPC 只負責隔離與定址，它不決定哪個服務能對外，那是 subnet 與 security group 的工作。環境之間的 VPC 該怎麼分，是[模組四：環境分離與模組化](/infra/04-environment-separation/)的主題。

## public 與 private subnet 的切分原則

一塊資源對外暴露到什麼程度，取決於它被放進哪個 subnet。VPC 內部按可用區與暴露程度切出來的子網段，決定資源有沒有一條通往網際網路的路徑。判斷一個資源該放 public 還是 private，問題只有一個：它需不需要被網際網路直接定址。

### 兩類 subnet 的定位

public subnet 放的是必須接收外部入站流量的元件 — 對外的負載平衡器、NAT Gateway、堡壘主機（bastion）。這些資源透過 route table 連到 Internet Gateway，因此能被外部 IP 直接觸及。private subnet 放的是只該在內網被存取的元件 — 應用伺服器、資料庫、快取、內部佇列。它們沒有通往 Internet Gateway 的路由，外部無法主動連入，需要對外時才透過 NAT 出去。

| Subnet 類型 | 典型住戶                      | 對外路徑                    |
| ----------- | ----------------------------- | --------------------------- |
| public      | 對外 LB、NAT Gateway、bastion | 經 Internet Gateway 雙向    |
| private     | 應用節點、資料庫、快取、佇列  | 僅經 NAT 單向出站、不可入站 |

public subnet 的真實樣貌是「薄薄一層」：它通常只住負載平衡器與 NAT 這類入口設施，而不是業務邏輯。常見陷阱是為了 SSH 方便把應用伺服器直接開在 public subnet 並配公網 IP，等於把每一台業務主機的管理埠暴露在掃描流量下 — 全球的 bot 會在秒級頻率對公網 IP 的 22 埠嘗試登入。private subnet 的住戶反而是系統的主體 — 資料庫放這裡是因為它一旦能被外網定址，攻擊面就從「打穿入口層」變成「直接連資料庫埠試密碼」。

### 跨可用區冗餘

每個 subnet 綁定單一可用區（Availability Zone）。高可用設計通常是每種角色跨至少兩個可用區各開一個 subnet：兩個 public、兩個 private，讓單一可用區故障時另一區的同類 subnet 還能承接。subnet 的 CIDR 切法要留足空間 — 如果 VPC 是 `/16`，每個 subnet 用 `/20`（約四千個位址）可以在三個可用區各開 public + private 共六個 subnet，還有大量空間留給未來擴展。

```hcl
locals {
  azs = ["ap-northeast-1a", "ap-northeast-1c", "ap-northeast-1d"]
}

resource "aws_subnet" "public" {
  for_each          = toset(local.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 4, index(local.azs, each.key))
  availability_zone = each.key

  tags = { Name = "public-${each.key}" }
}

resource "aws_subnet" "private" {
  for_each          = toset(local.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 4, index(local.azs, each.key) + length(local.azs))
  availability_zone = each.key

  tags = { Name = "private-${each.key}" }
}
```

`cidrsubnet` 函式自動切分子網段，避免手動計算 CIDR。第二個參數 `4` 表示在 `/16` 基礎上加 4 bit 得到 `/20`，第三個參數是序號。public 與 private 各佔不同序號區間，保證不重疊。

對外入口怎麼把流量分到跨可用區的 private 後端，是 devops 層負載平衡的範圍。這裡只要確保 subnet 的地圖在多 AZ 下對稱。

## route table 與 NAT：流量的進出路徑

離開一個 subnet 的封包往哪走，逐條寫在 route table 這組轉送規則裡 — 它掛在 subnet 上，是封包出口方向的依據。一個 subnet 是 public 還是 private，技術上的差別就在它關聯的 route table 裡有沒有一條指向 Internet Gateway 的預設路由。subnet 的對外性質由它關聯的 route table 賦予，而非寫在 subnet 自身的屬性。

### public 與 private 的路由差異

public subnet 的 route table 有一條 `0.0.0.0/0 → Internet Gateway`，讓未知目的地的流量直接出網、也讓外部可達。private subnet 的 route table 則把 `0.0.0.0/0` 指向 NAT Gateway。

NAT（Network Address Translation）解決的問題是：private subnet 的資源需要主動對外（拉套件、呼叫第三方 API、抓 OS 更新），但不能因此變得可被外部入站連入。NAT 讓出站流量借用一個公網位址出去、把回應導回原請求者，同時不開放任何外部主動發起的連線。

### 每 AZ 一個 NAT vs 共享 NAT 的取捨

NAT Gateway 是綁定單一可用區的資源 — 一個 NAT Gateway 活在某一個 public subnet，也就活在那個可用區裡。這帶來一個架構取捨：

**共享 NAT（成本優先）**：全部 private subnet 的 route table 都指向同一個 NAT。用一份 NAT 成本服務整個 VPC，代價是把 NAT 所在的可用區變成出站方向的單點 — 該可用區故障時，所有 private subnet 的對外連線同時中斷，即使其他可用區的節點本身健康。

**每 AZ 一個 NAT（可用性優先）**：每個可用區各放一個 NAT Gateway，並讓每一區的 private subnet route table 指向同區的 NAT。出站路徑與 subnet 的跨可用區冗餘對齊，單一 AZ 故障只影響該區。每個 NAT Gateway 的固定月費約 $32 加流量費 $0.045/GB 處理量。三個可用區各一個就是三倍固定費。這筆成本與業務對出站中斷的容忍度對齊——如果單一可用區故障導致全部出站中斷可接受（例如有重試機制），共享 NAT 的成本效益較高。

```hcl
resource "aws_eip" "nat" {
  for_each = toset(local.azs)
  domain   = "vpc"
  tags     = { Name = "nat-${each.key}" }
}

resource "aws_nat_gateway" "per_az" {
  for_each      = aws_subnet.public
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = each.value.id
  tags          = { Name = "nat-${each.key}" }
}

resource "aws_route_table" "private" {
  for_each = aws_subnet.private
  vpc_id   = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.per_az[each.key].id
  }

  tags = { Name = "private-rt-${each.key}" }
}

resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}
```

判讀訊號：private subnet 的服務拉不到外部套件、或第三方 API 全部逾時，先查它關聯的 route table 有沒有指向健康的 NAT；若只有某一個可用區的節點受影響，多半是那一區的 NAT 或其所在 subnet 出狀況。

### NAT 的成本邊界

NAT Gateway 按處理流量計費（每 GB 一個費率），把大量出站流量長期走 NAT 會讓帳單可觀。常見的高流量場景包括：備份上傳到 S3、跨區資料同步、大量 API 呼叫。對於走向 AWS 自家服務的流量，成本效益較好的做法是用 VPC Endpoint（Gateway 型或 Interface 型）讓流量直連服務、繞過 NAT。S3 與 DynamoDB 的 Gateway Endpoint 是免費的，光是把 S3 備份流量從 NAT 改走 Gateway Endpoint 就能在流量大的環境省下可觀的費用。

```hcl
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.ap-northeast-1.s3"

  route_table_ids = [for rt in aws_route_table.private : rt.id]

  tags = { Name = "s3-gateway-endpoint" }
}
```

NAT 的數量取捨與出站成本的更完整討論在 [devops 模組八：成本管理](/devops/08-cost-management/)。route table 與 NAT 只管「能不能出去、走哪條路」，至於某個埠允不允許連，是 security group 的職責。

## security group 設計：最小開放

一條連線究竟能不能打到某個埠，由 security group 逐埠拍板 — 它是掛在資源網卡（ENI）層級的有狀態防火牆，規則描述的是哪些來源連得進這個資源。它是貼著服務的最後一道網路邊界 — 即使封包順著 route table 抵達了 private subnet，security group 仍能逐埠決定放不放行。「有狀態」的意思是：放行一條入站連線後，對應的回應出站自動允許，規則只需描述入站方向想開放什麼。

### 用 group 引用取代 IP 範圍

設計原則是最小開放：每條規則只開「這個服務確實需要被誰連的那個埠」。資料庫的 security group 入站只允許來自應用層 security group 的資料庫埠，而不是某個 IP 範圍。用 security group 互相引用、而非寫死網段，是因為應用節點會隨擴縮而換 IP — 引用來源 group 讓規則跟著成員身分走、不跟著位址走。

```hcl
resource "aws_security_group" "app" {
  name_prefix = "app-"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "app-sg" }
}

resource "aws_security_group" "database" {
  name_prefix = "db-"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "db-sg" }
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.database.id
  source_security_group_id = aws_security_group.app.id
}
```

這條規則表達的語意是「資料庫只接受來自 app group 成員的 5432 連線」。app 的 instance 數量從 2 台增長到 20 台時，規則本身不需要改 — 新 instance 只要也掛了 `app` 的 security group 就自動被允許。

### 0.0.0.0/0 的盤點紀律

把入站來源設成 `0.0.0.0/0` 等於允許整個網際網路連這個埠。對資料庫埠（5432、3306、6379）或管理埠（22、3389）這麼做，會讓服務暴露在持續性的自動掃描與暴力嘗試下。

合理出現 `0.0.0.0/0` 的位置只有對外負載平衡器的 80 / 443 入站 — 因為它的工作本來就是接收公開流量。其餘所有 `0.0.0.0/0` 都該被質疑。

盤點的做法：列出所有 security group，過濾 source 是 `0.0.0.0/0` 的 ingress rule，逐條問「這個埠確實需要全世界都連得到嗎」。在 CLI 上可以用一條查詢掃：

```bash
aws ec2 describe-security-groups \
  --query 'SecurityGroups[].{
    ID:GroupId,
    Name:GroupName,
    OpenPorts:IpPermissions[?IpRanges[?CidrIp==`0.0.0.0/0`]].[FromPort,ToPort]
  }' \
  --output table
```

資料庫埠、SSH、內部 API 出現在這份清單上就是該收斂的目標。管理埠的存取更安全的替代方案是 SSM Session Manager — 它讓你透過 IAM 權限建立 shell session，完全不需要開 22 埠，連線經由 Systems Manager 的控制通道走、不走公網，同時自動留下 session log。誰能透過 IAM 改動這些規則，銜接[模組二：身分與憑證地基](/infra/02-identity-credentials/)。

在 CI 層面，[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)用 tfsec / checkov 做靜態掃描，自動攔截「敏感埠 + 全開 CIDR」的組合，把 security group 的盤點從人工定期做變成每次 PR 自動做。

邊界設備漏洞帶來的教訓同樣適用於 security group 設計。[Check Point CVE-2024-24919](/backend/07-security-data-protection/red-team/cases/edge-exposure/check-point-cve-2024-24919-vpn-info-disclosure/) 事件顯示 VPN 邊界設備的資訊外洩漏洞可以直接轉為憑證與會話濫用，攻擊路徑是「邊界入口 → 會話竊取 → 內部橫向擴散」。[Citrix Bleed 2023](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/) 則是邊界設備的會話資料外洩導致重放攻擊。這兩個案例的 infra 層教訓是：邊界設備（VPN concentrator、ADC、bastion）的 security group 只開必要的管理埠，且事件後需要全域 session/token 失效流程。

網路控制面的自動化也有風險。[Cloudflare 2026 Route Leak](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/) 事件中，自動化路由政策配置的錯誤導致流量擁塞。infra 層的教訓是：路由與 security group 規則的自動化變更需要 pre-check 與影響範圍評估，且要有快速撤回機制——這正是 [infra 走 PR 流程](/infra/07-infra-as-pr/)的 plan → review → apply 流程要擋的。

## NACL 與 security group 的分工

subnet 這一層還有另一道防火牆 — network ACL（NACL），它與 security group 分工在兩個層級。

| 屬性      | Security Group         | NACL                     |
| --------- | ---------------------- | ------------------------ |
| 掛在哪裡  | 資源網卡（ENI）        | Subnet                   |
| 狀態      | 有狀態（回程自動放行） | 無狀態（回程要另寫規則） |
| 規則方向  | 只寫入站               | 入站與出站各寫           |
| 能否 deny | 只能列允許清單         | 支援顯式 deny            |
| 評估順序  | 所有規則一起評估       | 按規則編號順序，命中即停 |

NACL 的特點是無狀態與支援顯式 deny。無狀態意味著放行了入站不代表回應的出站自動放行，回程封包得自己對得上另一條出站規則 — 這讓 NACL 的維護比 security group 複雜。支援顯式 deny 則是它獨有的能力：security group 只能說「誰可以進」，NACL 能說「誰一定不能進」，這在需要 subnet 邊界封鎖特定已知惡意網段時有用。

多數設計的主力是 security group：它貼著服務、用 group 互相引用就能表達「誰能連誰」，已經涵蓋大部分最小開放需求。NACL 留給少數情境 — 需要在 subnet 邊界擋掉一整段已知惡意網段、或要對某類流量做顯式 deny 時才展開。多數環境讓 NACL 維持預設全通、把存取控制集中在 security group，是可以接受的選擇。重點是知道這一層存在、在需要 subnet 層粗篩時記得它。

## 為什麼網路要先於核心服務鋪好

網路地基先行，是因為核心服務的安全位置由網路拓樸決定，而不是反過來。資料庫該落在哪個 private subnet、它的 security group 只接受哪個來源、它的出站走不走 NAT — 這些都是服務「出生時」就該確定的屬性。

先有規劃好的 subnet 與 security group，新服務上線只是挑一塊已定義安全等級的位置放進去。網路還沒鋪就先開服務，則往往落在預設 VPC 與寬鬆規則上。預設 VPC 是所有人共享的、CIDR 不可控的、security group 預設全通的 — 把正式服務放在這裡，等於跳過了所有隔離設計。事後再回頭收斂，要在服務已經有流量、有依賴的情況下改網段與防火牆，風險和協調成本都高得多。

這也呼應[模組零：infra 是什麼](/infra/00-infra-mindset/)的 day-1 鐵律：邊界與隔離屬於一開始就該存在的地基，不是長出問題後才補的修補。網路規劃好之後，照「從零建置」路線下一步先進[模組四：環境分離與模組化](/infra/04-environment-separation/)確定環境怎麼切，再讓核心服務落進這些 subnet（見[模組五：核心服務上 IaC](/infra/05-core-services/)）。

## 跨分類引用

- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：誰有權改動 security group 與路由表
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：環境之間的 VPC 怎麼分
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：核心服務怎麼落進規劃好的 subnet
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：tfsec / checkov 自動攔截 security group 全開
- → [devops 模組八：成本管理](/devops/08-cost-management/)：NAT 與出站流量的成本取捨
- → [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：SG 規則盤點、未使用 SG 識別、清理工作流
