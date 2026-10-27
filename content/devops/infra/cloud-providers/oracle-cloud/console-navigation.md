---
title: "Oracle Cloud 主控台導覽：頂端列、導覽選單的分類、清單頁的 compartment 篩選器與常用頁面的路徑"
date: 2026-10-24
description: "Oracle Cloud 主控台頂端列各個按鈕（導覽選單、搜尋、區域、Cloud Shell、人像選單）做什麼，導覽選單各分類底下有哪些項目，清單頁的 compartment 篩選器，以及建立主機、網路、Bastion、預算、稽核紀錄、配額這些常用頁面在選單上的實際路徑"
weight: 1
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "console"]
aliases: ["/infra/cloud-providers/oracle-cloud/console-navigation/"]
---

這篇是 Oracle Cloud Infrastructure 主控台的導覽：哪個功能在選單的哪裡。選單內容取自 2026-10-24 一個 Free Tier 帳號的主控台英文介面，介面語言可以從人像選單切換，切成中文時選單名稱會跟著翻譯。每個管理領域在做什麼、各家的對照見 [雲端主控台的管理領域](/devops/infra/cloud-providers/console-areas/)。

## 頂端列

登入後畫面最上面那一列，由左到右是：

- **☰（導覽選單）**：所有服務的入口，內容見〈導覽選單的分類〉。選單上方有一個搜尋框，打服務名稱就列出它所在的分類，例如打 `Bastion` 會列出「Bastion · Identity & Security」。
- **搜尋（放大鏡）**：搜尋資源與服務，也能用資源名稱找到某一台主機或某一個 VCN。
- **區域選擇器**：目前選定的區域，例如「Indonesia North (Batam)」。清單頁只顯示這個區域的資源。
- **Developer tools**：兩個項目，Cloud Shell（瀏覽器裡的終端機，已經裝好 OCI CLI 並以目前登入的身分驗證，不必在本機安裝 CLI 或設定金鑰）與 Code Editor。
- **通知（鈴鐺）**：Oracle 的公告，包括排定的硬體維護。
- **說明（問號）**：文件與支援的入口。
- **人像選單**：從上到下是目前的使用者名稱、identity domain（tenancy 裡存放使用者與群組的分區，新帳號只有 `Default` 一個）、tenancy 名稱（tenancy 是 Oracle Cloud 的帳號，一個客戶一個）、介面語言、User settings（個人的密碼、多因素驗證、API 簽章金鑰與其他憑證）、Console settings、Sign out。點 tenancy 名稱進入 Tenancy Details 頁，那裡看得到 home region 與 tenancy 的 OCID（Oracle Cloud ID：Oracle Cloud 給每個資源的唯一識別碼，以 `ocid1.` 開頭，CLI 與 API 用它指定要操作的對象）。

Free Tier 帳號在試用期間，頂端列上方另有一條「Free Tier account」的橫幅，說明試用結束後只剩 Always Free 資源，並附 Upgrade 連結。

## 導覽選單的分類

選單左欄是分類，點一個分類，右側展開它底下的服務與頁面。實測的分類依序是：Home、Compute、Storage、Networking、Oracle AI Database、Databases、Analytics & AI、Developer Services、Identity & Security、Observability & Management、Hybrid & Multicloud、Migration & Recovery、Billing & Cost Management、Governance & Administration、Marketplace。管理一台主機會用到的是下面這幾類：

**Compute**：Overview、Instances、Instance Maintenance、Dedicated Virtual Machine Hosts、Instance Configurations、Instance Pools、Cluster Networks、Autoscaling Configurations、Capacity Reservations、Custom Images。建立與管理主機都從 Instances 進去。

**Storage**：Block Storage（Block Volumes、Block Volume Backups、Block Volume Replicas、Volume Groups 與它們的備份與複本、Backup Policies）、File Storage（File Systems、Mount Targets）、Object Storage & Archive Storage（Buckets、Private Endpoints）。開機磁碟不列在導覽選單上：進入任一個 Block Storage 頁面（例如 Block Volumes）之後，頁面頂端的「Storage」那一列可以展開，子選單裡有 Boot Volumes、Boot Volume Backups 等項目，刪除主機後留下的開機磁碟從這裡找。進入服務頁面之後，頁面頂端都有這樣一列可以展開的服務子選單，在同一個服務的各頁面之間切換用它比回導覽選單快。

**Networking**：Overview、Virtual cloud networks、Load balancers（Load balancer、Network load balancer）、DNS management（Public zones、Private zones 等）、IP management（Reserved public IPs、BYOIP、Public IP pools 等）、Network Command Center（Network visualizer、Network Path Analyzer 等）。VCN、subnet、security list、NSG、閘道都從 Virtual cloud networks 進入某一個 VCN 之後設定。

**Identity & Security**：Identity（Overview、Domains、Network Sources、Policies、Compartments）、Cloud Guard、Security Zones、Security Advisor、Certificates、Scanning（Vulnerability Reports 等）、Key Management（Vault 等）、Secret Management、Zero Trust Packet Routing，以及 Bastion。使用者與群組在 Domains 裡的 `Default` domain 底下管理。

**Observability & Management**：Application Performance Monitoring、Logging（Logs、Audit 等）、Monitoring（Metrics Explorer、Alarm Definitions 等）、Log Analytics、Events Service、Management Agent 等。主機的 CPU 與記憶體圖表在主機頁面上就看得到；跨主機的指標與告警從 Monitoring 進去。

**Billing & Cost Management**：Billing（Subscriptions、Invoices、Usage Statements、Payment History、Upgrade and Manage Payment）、Cost Management（Overview、Cost Analysis、Cost and Usage Reports、Budgets、Scheduled Reports、Cost Anomaly Detection 等）。

**Governance & Administration**：Account Management（Tenancy Details、Announcements、Region Management）、Cloud Advisor、Resource Scheduler、Tenancy Management（Resource Explorer、Tenancy Explorer、Quota policies、Limits, quotas and usage、Tag Namespaces）、Organization Management。

右側每個項目滑過時會出現「Press P to pin link」，釘選的項目出現在 Home 分類與首頁的 Pinned 區，常用的頁面釘起來就不必每次翻選單。

## 清單頁的 compartment 篩選器

Compartment 是 tenancy 底下用來分組資源與套用權限政策的容器，tenancy 本身是最上層的 root compartment，每個資源都建在某一個 compartment 裡。Instances、Virtual cloud networks、Block Volumes 這類清單頁的表格上方有一行「Applied filters」，其中的 Compartment 那一項篩選條件就是 compartment 篩選器，清單只列出選定 compartment 裡的資源。實測新帳號的預設是 root compartment，這一項篩選條件顯示為「<tenancy 名稱> (root)」。資源建在另一個 compartment 時，清單看起來是空的，要把篩選器切過去。建立頁上的下拉選單也一樣：VCN、subnet 的選單只列出「所在 compartment」那一欄選定的 compartment 裡的資源。

## 常用頁面的路徑

| 要做的事                                                       | 選單路徑                                                                                                                     |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 建立、停止、刪除主機                                           | Compute → Instances                                                                                                          |
| 建立 VCN、subnet，改防火牆規則                                 | Networking → Virtual cloud networks → 點進某個 VCN                                                                           |
| 保留一個固定的公開 IP                                          | Networking → IP management → Reserved public IPs                                                                             |
| 找刪除主機後留下的開機磁碟                                     | Storage → Block Storage → Block Volumes，再從頁面頂端的 Storage 子選單切到 Boot Volumes                                      |
| 建立 Bastion、在它底下建立登入主機用的 SSH 工作階段（session） | Identity & Security → Bastion                                                                                                |
| 建立實驗用的 compartment                                       | Identity & Security → Identity → Compartments                                                                                |
| 加使用者、群組                                                 | Identity & Security → Identity → Domains → `Default`                                                                         |
| 寫權限政策                                                     | Identity & Security → Identity → Policies                                                                                    |
| 開多因素驗證、建 API 簽章金鑰                                  | 人像選單 → User settings；API 簽章金鑰在 Token and keys 分頁，或頁面左下角 Resources 區段的 API Keys（官方文件兩種寫法都有） |
| 設預算與警示                                                   | Billing & Cost Management → Cost Management → Budgets                                                                        |
| 看這個月花了多少                                               | Billing & Cost Management → Cost Management → Cost Analysis                                                                  |
| 查誰做了什麼操作                                               | Observability & Management → Logging → Audit                                                                                 |
| 看主機指標、設告警                                             | Observability & Management → Monitoring                                                                                      |
| 查某種資源的上限與用量                                         | Governance & Administration → Tenancy Management → Limits, quotas and usage                                                  |
| 看 home region 與 tenancy OCID                                 | Governance & Administration → Account Management → Tenancy Details                                                           |
| 訂閱其他區域（付費帳戶限定）                                   | Governance & Administration → Account Management → Region Management                                                         |

試用與 Free Tier 帳號只能有一個訂閱區域（就是 home region），升級成 Pay As You Go 之後還要先在 Limits, quotas and usage 申請提高 Subscribed region count，才能在 Region Management 訂閱第二個區域。

選單路徑對不上時（改版、介面語言不同），在導覽選單的搜尋框打表格裡的頁面名稱。

## 延伸閱讀：各頁面背後的概念

這些分類各自管什麼、Google Cloud 與 AWS 的對應名稱，見 [雲端主控台的管理領域](/devops/infra/cloud-providers/console-areas/)；從 Compute → Instances 進去之後建立頁每個分頁的取值，見 [Oracle Cloud 建立主機的實測紀錄](/devops/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)；Tenancy Details 頁上 home region 的意義與它對 Always Free 額度的限制，見 [Oracle Cloud 的帳號結構與 home region](/devops/infra/cloud-providers/oracle-cloud/account-and-home-region/)。
