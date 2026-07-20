---
title: "模組三：網路地基 — VPC 與分層"
date: 2026-06-26
description: "VPC、public / private subnet 切分、route table、NAT、security group 設計"
weight: 3
tags: ["infra", "network", "vpc", "security-group"]
---

網路地基要先於核心服務存在。VPC、subnet、route table 與 security group 構成一張「服務能落在哪、誰能跟誰講話」的地圖，資料庫、運算節點與對外入口都得落在這張地圖規劃好的格子裡。先把邊界畫清楚，後面每個核心服務上線時只需要選一塊已經定義好安全等級的位置，而不是邊開服務邊補洞。

這一章建立四層邊界：最外層的 VPC 隔離、中層的 public / private subnet 切分、流量進出的 route table 與 NAT、以及最貼近服務的 security group。每一層解決的問題不同，疊起來才是一個可審計、可收斂的網路。

## VPC：網路隔離的最外層邊界

VPC（Virtual Private Cloud）先圈定整個系統的網路地址空間 — 一塊邏輯隔離的私有網段，是其餘所有網路切分的起點。在 VPC 裡開出來的所有資源預設只看得到同一個 VPC 內的成員，與其他 VPC、與其他帳號的網路天然隔離。它是後面所有切分動作的容器 — 沒有 VPC，subnet 與 security group 無處依附。

建立 VPC 時最關鍵的決策是 CIDR 區塊的大小，例如 `10.0.0.0/16` 提供約六萬五千個位址。這個範圍要一次規劃足夠大，因為事後擴張地址空間在多數雲上是麻煩且容易出錯的操作。同時要避免與公司其他網段重疊：未來若要透過 VPC peering、Transit Gateway 或 VPN 把這個 VPC 接回地端機房或其他環境，重疊的 CIDR 會讓路由無法解析。

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "platform-main"
    Environment = "production"
  }
}
```

判讀訊號：規劃 CIDR 時先問「這個環境三年後會有幾個 subnet、跨幾個可用區、要不要接地端」。風險集中在地址耗盡與網段衝突 — 兩者都得在開第一個 subnet 之前定案。邊界是：VPC 只負責隔離與定址，它不決定哪個服務能對外，那是 subnet 與 security group 的工作。環境之間的 VPC 該怎麼分，是「模組四：環境分離與模組化」的主題，這裡只先確保單一 VPC 的地址規劃站得住。

## public 與 private subnet 的切分原則

一塊資源對外暴露到什麼程度，取決於它被放進哪個 subnet — VPC 內部按可用區與暴露程度切出來的子網段，決定資源有沒有一條通往網際網路的路徑。判斷一個資源該放 public 還是 private，問題只有一個：它需不需要被網際網路直接定址。

public subnet 放的是必須接收外部入站流量的元件 — 對外的負載平衡器、需要公開的 NAT Gateway、堡壘主機（bastion）。這些資源透過 route table 連到 Internet Gateway，因此能被外部 IP 直接觸及。private subnet 放的是只該在內網被存取的元件 — 應用伺服器、資料庫、快取、內部佇列。它們沒有通往 Internet Gateway 的路由，外部無法主動連入，需要對外時才透過 NAT 出去。

| Subnet 類型 | 典型住戶                      | 對外路徑                    |
| ----------- | ----------------------------- | --------------------------- |
| public      | 對外 LB、NAT Gateway、bastion | 經 Internet Gateway 雙向    |
| private     | 應用節點、資料庫、快取、佇列  | 僅經 NAT 單向出站、不可入站 |

public subnet 的真實樣貌是「薄薄一層」：它通常只住負載平衡器與 NAT 這類入口設施，而不是業務邏輯。常見陷阱是為了 SSH 方便把應用伺服器直接開在 public subnet 並配公網 IP，等於把每一台業務主機的管理埠暴露在掃描流量下。private subnet 的住戶反而是系統的主體 — 資料庫放這裡是因為它一旦能被外網定址，攻擊面就從「打穿入口層」變成「直接連資料庫埠試密碼」。

每個 subnet 綁定單一可用區，所以高可用設計通常是每種角色跨至少兩個可用區各開一個 subnet：兩個 public、兩個 private，讓單一可用區故障時另一區的同類 subnet 還能承接。對外入口怎麼把流量分到跨可用區的 private 後端，是「運維 模組一：負載平衡」的範圍。

## route table 與 NAT：流量的進出路徑

離開一個 subnet 的封包往哪走，逐條寫在 route table 這組轉送規則裡 — 它掛在 subnet 上，是封包出口方向的依據。一個 subnet 是 public 還是 private，技術上的差別就在它關聯的 route table 裡有沒有一條指向 Internet Gateway 的預設路由。換句話說，subnet 的對外性質由它關聯的 route table 賦予，而非寫在 subnet 自身。

public subnet 的 route table 有一條 `0.0.0.0/0 → Internet Gateway`，讓未知目的地的流量直接出網、也讓外部可達。private subnet 的 route table 則把 `0.0.0.0/0` 指向 NAT Gateway。NAT（Network Address Translation）解決的問題是：private subnet 的資源需要主動對外（拉套件、呼叫第三方 API、抓 OS 更新），但不能因此變得可被外部入站連入。NAT 讓出站流量借用一個公網位址出去、把回應導回原請求者，同時不開放任何外部主動發起的連線。

NAT Gateway 的核心取捨是成本與可用性。它是綁定單一可用區的資源 — 一個 NAT Gateway 活在某一個 public subnet、也就活在那個可用區裡。若全部 private subnet 的 route table 都指向同一個 NAT，這個設計用一份 NAT 成本服務整個 VPC，代價是把 NAT 所在的可用區變成出站方向的單點：該可用區故障時，所有 private subnet 的對外連線同時中斷，即使其他可用區的節點本身健康。要讓出站路徑與 subnet 的跨可用區冗餘對齊，做法是每個可用區各放一個 NAT Gateway，並讓每一區的 private subnet route table 指向同區的 NAT。下面用 `for_each` 在每個可用區建立一個 NAT，再讓每個 private subnet 的 route table 走本區出口。

```hcl
resource "aws_nat_gateway" "per_az" {
  for_each      = aws_subnet.public
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = each.value.id
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
```

每個可用區一個 NAT 是可用性優先的版本；若環境對成本敏感、且能接受出站在單一可用區故障時短暫中斷，也可以退回單一 NAT，但要把它當成明示的取捨、而非預設。判讀訊號：private subnet 的服務拉不到外部套件、或第三方 API 全部逾時（逾時指向可達性層、跟「被拒=服務層」「解析失敗=resolver 層」是相反的除錯方向，通用判別見 [連線逾時 vs 連線被拒](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/)），先查它關聯的 route table 有沒有指向健康的 NAT；若只有某一個可用區的節點受影響，多半是那一區的 NAT 或其所在 subnet 出狀況。風險與成本在這裡交會 — NAT Gateway 按處理流量計費，把大量出站流量（例如備份上傳、跨區同步）長期走 NAT 會讓帳單可觀，這類流量較划算的做法是改走 VPC Endpoint 直連雲服務、繞過 NAT。NAT 的數量取捨與出站成本在「運維 模組八：成本管理」有更完整的討論。邊界是：route table 與 NAT 只管「能不能出去、走哪條路」，至於某個埠允不允許連，是 security group 的職責。

## security group 設計：最小開放

一條連線究竟能不能打到某個埠，由 security group 逐埠拍板 — 它是掛在資源網卡層級的有狀態防火牆，規則描述的是哪些來源連得進這個資源。它是貼著服務的最後一道網路邊界 — 即使封包順著 route table 抵達了 private subnet，security group 仍能逐埠決定放不放行。它有狀態的意思是：放行一條入站連線後，對應的回應出站自動允許，規則只需描述入站方向想開放什麼。

設計原則是最小開放：每條規則只開「這個服務確實需要被誰連的那個埠」。資料庫的 security group 入站只允許來自應用層 security group 的資料庫埠，而不是某個 IP 範圍。用 security group 互相引用、而非寫死網段，是因為應用節點會隨擴縮而換 IP，引用來源 group 讓規則跟著成員身分走、不跟著位址走。

```hcl
resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.database.id
  source_security_group_id = aws_security_group.app.id
}
```

要特別防的是 `0.0.0.0/0` 全開。把入站來源設成 `0.0.0.0/0` 等於允許整個網際網路連這個埠，對資料庫埠（5432、3306、6379）或管理埠（22、3389）這麼做，會讓服務暴露在持續性的自動掃描與暴力嘗試下。合理出現 `0.0.0.0/0` 的位置只有對外負載平衡器的 80 / 443 入站 — 因為它的工作本來就是接收公開流量。判讀訊號：盤點所有 security group，列出 source 是 `0.0.0.0/0` 的規則，逐條問「這個埠真的需要全世界都連得到嗎」；資料庫埠、SSH、內部 API 出現在這份清單上就是該收斂的目標。管理埠的存取較划算的替代方案是 SSM Session Manager 或堡壘主機，把 22 埠從公網清單上拿掉。誰能透過 IAM 改動這些規則，銜接「模組二：身分與憑證地基」。

subnet 這一層還有另一道防火牆 — network ACL（NACL），它與 security group 分工在兩個層級。NACL 掛在 subnet 上、作用於進出整個 subnet 的流量，而且是無狀態的：入站與出站要各寫一條規則，放行了入站不代表回應的出站自動放行，回程封包得自己對得上另一條規則。security group 則掛在資源網卡（ENI）層、有狀態，放行入站後對應回應自動允許。兩者的另一個差別是 NACL 支援顯式 deny、security group 只能列允許清單，所以 NACL 適合做 subnet 層的粗篩或針對特定來源的明確封鎖。實務上多數設計的主力是 security group：它貼著服務、用 group 互相引用就能表達「誰能連誰」，已經涵蓋大部分最小開放需求。NACL 留給少數情境 — 需要在 subnet 邊界擋掉一整段已知惡意網段、或要對某類流量做顯式 deny 時才展開；多數環境讓 NACL 維持預設全通、把存取控制集中在 security group，是可以接受的選擇，重點是知道這一層存在、在需要 subnet 層粗篩時記得它。

## 為什麼網路要先於核心服務鋪好

網路地基先行，是因為核心服務的安全位置由網路拓樸決定，而不是反過來。資料庫該落在哪個 private subnet、它的 security group 只接受哪個來源、它的出站走不走 NAT — 這些都是服務「出生時」就該確定的屬性。先有規劃好的 subnet 與 security group，新服務上線只是挑一塊已定義安全等級的位置放進去；網路還沒鋪就先開服務，則往往落在預設 VPC 與寬鬆規則上，事後再回頭收斂，要在服務已經有流量、有依賴的情況下改網段與防火牆，風險和協調成本都高得多。

這也呼應「模組零：infra 是什麼」的 day-1 鐵律：邊界與隔離屬於一開始就該存在的地基，不是長出問題後才補的修補。網路規劃好之後，照「從零建置」路線下一步先進「模組四：環境分離與模組化」確定環境怎麼切，再讓核心服務落進這些 subnet。

## 章節文章

| 文章                                                                                                         | 主題                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| [網路地基 — VPC、subnet 分層與 security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/) | VPC CIDR 規劃、public / private subnet 切分、route table 與 NAT 的可用性成本取捨、security group 最小開放設計與 NACL 定位 |
| [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)                      | 0.0.0.0/0 偵測、未使用 SG 識別、依賴檢查、清理工作流、自動化治理                                                          |
| [流量入口層 — 請求怎麼從使用者到達應用](/infra/03-network-foundation/traffic-entry-layer/)                   | DNS、負載平衡（L4/L7）、reverse proxy、應用的責任鏈，TLS 終結位置、動靜分離、單機 nginx 與雲端 ALB 的選擇條件             |

## 跨分類引用

- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：誰有權改動 security group 與路由表
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：核心服務怎麼落進規劃好的 subnet
- → [運維 模組一：負載平衡](/operations/01-load-balancing/)：入口流量怎麼分到 private subnet 的後端
- → [運維 模組八：成本管理](/operations/08-cost-management/)：NAT 與出站流量的成本取捨
