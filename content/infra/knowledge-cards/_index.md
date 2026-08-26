---
title: "Infra 知識卡"
date: 2026-06-26
description: "基礎設施領域的核心術語與概念定義"
weight: 100
tags: ["infra", "knowledge-cards"]
---

Infra 知識卡收錄基礎設施領域的核心術語。每張卡自包含、可獨立閱讀，讀者可以從任何一張卡進入、透過鄰卡連結導航到相關概念。

知識卡的職責是建立術語的語意錨點。教學模組負責情境推導與操作判斷標準，知識卡負責「這個詞是什麼、什麼時候會碰到、使用時要決定什麼」。兩者互相引用但各自完整。

## 卡片清單

| 卡片                                                                                 | 說明                                                                                      |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| [ALB](/infra/knowledge-cards/alb/)                                                   | Application Load Balancer — 流量進入系統的第一站，負責 listener 路由、健康檢查與 TLS 終結 |
| [CIDR](/infra/knowledge-cards/cidr/)                                                 | 用前綴長度表示 IP 地址範圍的表示法，決定 VPC 與 subnet 的地址空間大小                     |
| [CloudTrail](/infra/knowledge-cards/cloudtrail/)                                     | AWS 的 API 層稽核日誌服務，記錄誰在什麼時候對什麼資源做了什麼操作                         |
| [Drift](/infra/knowledge-cards/drift/)                                               | IaC 的 state 與雲端實際狀態之間的不一致，通常因為繞過 IaC 直接在 Console 改設定           |
| [ECS](/infra/knowledge-cards/ecs/)                                                   | AWS 受管容器編排服務，用 task definition 描述容器配置、由平台負責排程與健康管理           |
| [IAM](/infra/knowledge-cards/iam/)                                                   | 雲端平台的授權系統，回答「某個身分能不能對某個資源做某件事」                              |
| [IaC](/infra/knowledge-cards/iac/)                                                   | 用程式碼描述基礎設施的最終狀態，由工具負責收斂現實與描述的差異                            |
| [NAT Gateway](/infra/knowledge-cards/nat/)                                           | 讓 private subnet 的資源主動對外連線、同時不被外部入站觸及                                |
| [OIDC Federation（OIDC 聯合）](/infra/knowledge-cards/oidc/)                         | 讓 CI/CD 平台用短期 token 取代長期 access key 存取雲端資源                                |
| [Security Group](/infra/knowledge-cards/security-group/)                             | 掛在資源網卡層級的有狀態防火牆，逐埠決定哪些來源能連進這個資源                            |
| [State](/infra/knowledge-cards/state/)                                               | IaC 工具用來記錄每個納管資源在雲端真實樣貌的快照                                          |
| [Subnet](/infra/knowledge-cards/subnet/)                                             | VPC 內按可用區與暴露程度切出的子網段，決定資源有沒有通往網際網路的路徑                    |
| [VPC](/infra/knowledge-cards/vpc/)                                                   | 雲端帳號內的一塊邏輯隔離私有網段，是所有網路切分的起點與容器                              |
| [checkov](/infra/knowledge-cards/checkov/)                                           | IaC 靜態安全掃描工具，比對 HCL 裡的已知壞寫法與安全反模式                                 |
| [Deletion Protection](/infra/knowledge-cards/deletion-protection/)                   | 防止誤刪 stateful 資源的平台級保護機制，開啟後刪除需先顯式關閉保護                        |
| [Fargate](/infra/knowledge-cards/fargate/)                                           | AWS ECS 的無伺服器容器執行模式，不需管理 EC2 instance                                     |
| [Remote State Backend](/infra/knowledge-cards/remote-state-backend/)                 | 團隊共享、有鎖、有加密的 state 存放機制                                                   |
| [Route Table](/infra/knowledge-cards/route-table/)                                   | subnet 的流量轉送規則，決定封包離開 subnet 後往哪走                                       |
| [SCP](/infra/knowledge-cards/scp/)                                                   | Organizations 層級的權限天花板，連管理員都越不過                                          |
| [Trust Policy](/infra/knowledge-cards/trust-policy/)                                 | IAM role 的信任關係設定，控制誰能 assume 這個 role                                        |
| [Environment Separation（環境分離）](/infra/knowledge-cards/environment-separation/) | 把同一套基礎設施定義複製成多份隔離的執行實例，各有獨立 state 與故障半徑                   |
| [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/)                                     | Web 介面的 MySQL / MariaDB 管理工具，無 SSH 環境的主要 DB 管理入口                        |
| [FileZilla](/infra/knowledge-cards/filezilla/)                                       | 跨平台 FTP/SFTP client，提供目錄同步瀏覽和檔案比較功能                                    |
| [cPanel](/infra/knowledge-cards/cpanel/)                                             | Web 主機管理面板，整合 PHP 版本切換、cron、email、SSL、備份的圖形介面                     |
| [.htaccess](/infra/knowledge-cards/htaccess/)                                        | Apache 的目錄層級設定檔，控制 URL rewrite、存取權限、PHP 設定覆寫                         |
| [.env](/infra/knowledge-cards/dotenv/)                                               | 存放環境變數的純文字檔案，把機密值從程式碼分離出來                                        |
| [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)                               | PHP 的執行期設定檔，控制記憶體上限、上傳大小、錯誤報告等 runtime 行為                     |
| [Composer](/infra/knowledge-cards/composer/)                                         | PHP 的套件管理工具，管理第三方依賴、版本鎖定與安全掃描                                    |
| [mysqldump](/infra/knowledge-cards/mysqldump/)                                       | MySQL/MariaDB 的 CLI 備份工具，把資料庫匯出成 SQL 純文字檔                                |
| [Reverse Proxy](/infra/knowledge-cards/reverse-proxy/)                               | 代替後端服務接收外部請求的中介層，承擔 TLS 終結、負載平衡與路由分流                       |
| [動靜分離](/infra/knowledge-cards/static-dynamic-separation/)                        | 靜態資源直接回、動態請求才轉後端的入口層分流做法                                          |
| [Database Migration](/infra/knowledge-cards/database-migration/)                     | 用版本化的 SQL 腳本管理資料庫 schema 的變更歷程                                           |
| [Prometheus](/infra/knowledge-cards/prometheus/)                                     | 開源的 metrics 收集與告警系統，用 pull 模式從 target 拉取指標                             |
| [Grafana](/infra/knowledge-cards/grafana/)                                           | 開源的監控視覺化平台，從 Prometheus / Loki 等資料源建立 dashboard                         |
| [HashiCorp Vault](/infra/knowledge-cards/vault/)                                     | 機密管理系統，集中存放密碼與 API key，提供存取控制與稽核                                  |
| [Harbor](/infra/knowledge-cards/harbor/)                                             | 開源的 container image registry，支援映像掃描、RBAC、複製                                 |
| [Helm](/infra/knowledge-cards/helm/)                                                 | Kubernetes 的套件管理工具，用 chart 打包一組 K8s 資源部署定義                             |
| [EC2](/infra/knowledge-cards/ec2/)                                                   | AWS 的虛擬機器服務，由 AMI、instance type、EBS、security group 與 IAM role 組成           |
| [AMI](/infra/knowledge-cards/ami/)                                                   | EC2 instance 的作業系統映像快照，從同一份 AMI 開出的 instance 起始狀態相同                |
| [EBS](/infra/knowledge-cards/ebs/)                                                   | 掛在 instance 上的持久化區塊儲存，生命週期與 instance 獨立、支援 snapshot                 |
| [S3](/infra/knowledge-cards/s3/)                                                     | 物件儲存服務，用 bucket + key 組織檔案，提供 versioning、加密與 lifecycle                 |
| [RDS](/infra/knowledge-cards/rds/)                                                   | 受管關聯式資料庫服務，代管備份、更新與 failover                                           |
| [MySQL](/infra/knowledge-cards/mysql/)                                               | 最廣泛使用的開源關聯式資料庫，大版本升級帶認證方式與查詢行為的破壞性變更                  |
| [nginx](/infra/knowledge-cards/nginx/)                                               | 高效能 Web Server 與 Reverse Proxy，用集中設定檔取代分散在目錄裡的設定                    |
| [DNS](/infra/knowledge-cards/dns/)                                                   | 把域名轉成 IP 的系統，以及 A record、CNAME、NS 與 TTL 各自的角色                          |
| [SSL / TLS](/infra/knowledge-cards/ssl-tls/)                                         | 加密 client 與 server 通訊的協定，決定 HTTPS 能否成立                                     |
| [SSH](/infra/knowledge-cards/ssh/)                                                   | 加密的遠端 shell 連線，它的有無決定整條 CLI 工具鏈能不能用                                |
| [FTP](/infra/knowledge-cards/ftp/)                                                   | 檔案傳輸協定，無 SSH 環境的主要檔案管理方式，SFTP 與 FTPS 是加密變體                      |
| [cron](/infra/knowledge-cards/cron/)                                                 | 按時間表自動執行指令的排程系統，接手維運時要先盤點既有 job                                |
| [HCL](/infra/knowledge-cards/hcl/)                                                   | Terraform 的宣告式設定語言，用 resource block 描述目標狀態                                |
| [terraform plan / apply](/infra/knowledge-cards/terraform-plan-apply/)               | IaC 的兩個核心操作：plan 只產出差異報告、apply 才執行差異                                 |
