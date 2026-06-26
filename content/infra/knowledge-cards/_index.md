---
title: "Infra 知識卡"
date: 2026-06-26
description: "基礎設施領域的核心術語與概念定義"
weight: 100
tags: ["infra", "knowledge-cards"]
---

Infra 知識卡收錄基礎設施領域的核心術語。每張卡自包含、可獨立閱讀，讀者可以從任何一張卡進入、透過鄰卡連結導航到相關概念。

知識卡的職責是建立術語的語意錨點。教學模組負責情境推導與操作判準，知識卡負責「這個詞是什麼、什麼時候會碰到、使用時要決定什麼」。兩者互相引用但各自完整。

## 卡片清單

| 卡片                                                                 | 說明                                                                                      |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [ALB](/infra/knowledge-cards/alb/)                                   | Application Load Balancer — 流量進入系統的第一站，負責 listener 路由、健康檢查與 TLS 終結 |
| [CIDR](/infra/knowledge-cards/cidr/)                                 | 用前綴長度表示 IP 地址範圍的表示法，決定 VPC 與 subnet 的地址空間大小                     |
| [CloudTrail](/infra/knowledge-cards/cloudtrail/)                     | AWS 的 API 層稽核日誌服務，記錄誰在什麼時候對什麼資源做了什麼操作                         |
| [Drift](/infra/knowledge-cards/drift/)                               | IaC 的 state 與雲端實際狀態之間的不一致，通常因為繞過 IaC 直接在 Console 改設定           |
| [ECS](/infra/knowledge-cards/ecs/)                                   | AWS 受管容器編排服務，用 task definition 描述容器配置、由平台負責排程與健康管理           |
| [IAM](/infra/knowledge-cards/iam/)                                   | 雲端平台的授權系統，回答「某個身分能不能對某個資源做某件事」                              |
| [IaC](/infra/knowledge-cards/iac/)                                   | 用程式碼描述基礎設施的最終狀態，由工具負責收斂現實與描述的差異                            |
| [NAT Gateway](/infra/knowledge-cards/nat/)                           | 讓 private subnet 的資源主動對外連線、同時不被外部入站觸及                                |
| [OIDC 聯合](/infra/knowledge-cards/oidc/)                            | 讓 CI/CD 平台用短期 token 取代長期 access key 存取雲端資源                                |
| [Security Group](/infra/knowledge-cards/security-group/)             | 掛在資源網卡層級的有狀態防火牆，逐埠決定哪些來源能連進這個資源                            |
| [State](/infra/knowledge-cards/state/)                               | IaC 工具用來記錄每個納管資源在雲端真實樣貌的快照                                          |
| [Subnet](/infra/knowledge-cards/subnet/)                             | VPC 內按可用區與暴露程度切出的子網段，決定資源有沒有通往網際網路的路徑                    |
| [VPC](/infra/knowledge-cards/vpc/)                                   | 雲端帳號內的一塊邏輯隔離私有網段，是所有網路切分的起點與容器                              |
| [checkov](/infra/knowledge-cards/checkov/)                           | IaC 靜態安全掃描工具，比對 HCL 裡的已知壞寫法與安全反模式                                 |
| [Deletion Protection](/infra/knowledge-cards/deletion-protection/)   | 防止誤刪 stateful 資源的平台級保護機制，開啟後刪除需先顯式關閉保護                        |
| [Fargate](/infra/knowledge-cards/fargate/)                           | AWS ECS 的無伺服器容器執行模式，不需管理 EC2 instance                                     |
| [Remote State Backend](/infra/knowledge-cards/remote-state-backend/) | 團隊共享、有鎖、有加密的 state 存放機制                                                   |
| [Route Table](/infra/knowledge-cards/route-table/)                   | subnet 的流量轉送規則，決定封包離開 subnet 後往哪走                                       |
| [SCP](/infra/knowledge-cards/scp/)                                   | Organizations 層級的權限天花板，連管理員都越不過                                          |
| [Trust Policy](/infra/knowledge-cards/trust-policy/)                 | IAM role 的信任關係設定，控制誰能 assume 這個 role                                        |
| [環境分離](/infra/knowledge-cards/environment-separation/)           | 把同一套基礎設施定義複製成多份隔離的執行實例，各有獨立 state 與故障半徑                   |
| [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/)                     | Web 介面的 MySQL / MariaDB 管理工具，無 SSH 環境的主要 DB 管理入口                        |
| [FileZilla](/infra/knowledge-cards/filezilla/)                       | 跨平台 FTP/SFTP client，提供目錄同步瀏覽和檔案比較功能                                    |
| [cPanel](/infra/knowledge-cards/cpanel/)                             | Web 主機管理面板，整合 PHP 版本切換、cron、email、SSL、備份的圖形介面                     |
| [.htaccess](/infra/knowledge-cards/htaccess/)                        | Apache 的目錄層級設定檔，控制 URL rewrite、存取權限、PHP 設定覆寫                         |
| [.env](/infra/knowledge-cards/dotenv/)                               | 存放環境變數的純文字檔案，把機密值從程式碼分離出來                                        |
| [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)               | PHP 的執行期設定檔，控制記憶體上限、上傳大小、錯誤報告等 runtime 行為                     |
