---
title: "平台遷移"
date: 2026-06-26
description: "FTP 面板主機到 VPS、VPS 到雲端、地端到雲端的遷移路徑 — 資料同步策略、DNS 切換、驗證與回退"
weight: 3
tags: ["infra", "upgrade", "migration", "platform"]
---

平台遷移改變的是系統跑在哪裡，不是系統跑什麼。應用程式碼不動，改變的是網路拓樸、儲存位置、運算環境與存取方式。遷移成功的判準是應用程式在新平台上以等同或更好的效能運作，且舊平台可以被安全退役。

遷移的核心約束是帶電施工——系統在搬遷過程中要持續服務。這決定了操作模式：在新平台建起平行環境、驗證通過後用 DNS 切換流量、確認沒問題再拆舊環境。每一步都保留回退到舊環境的能力，直到新環境穩定運行一段時間。

## 遷移路徑的常見組合

| 路徑           | 獲得                                 | 失去                              | 主要變動                             |
| -------------- | ------------------------------------ | --------------------------------- | ------------------------------------ |
| 共享主機 → VPS | SSH、cron 彈性、自訂軟體安裝         | 主機商代管的面板、email、自動備份 | 需要自己管 OS、web server、SSL       |
| VPS → 雲端     | Auto-scaling、managed DB、IaC、多 AZ | 固定月費的簡單計費                | 計費模型改按用量、運維複雜度上升     |
| 地端 → 雲端    | 彈性擴縮、不管硬體                   | 對硬體的直接控制                  | 網路重新設計、合規審查、資料主權確認 |

每條路徑的遷移工程量級不同：共享主機 → VPS 是最輕的（應用層搬家）、地端 → 雲端是最重的（整個基礎設施重建）。選擇遷移路徑時先確認商業目標——如果目標是「能裝自訂軟體」，共享主機 → VPS 就夠了，不需要一步跳到雲端。

## 共享主機 → VPS 遷移

### 遷移前的記錄

把共享主機的所有設定記下來，作為 VPS 上重建的 checklist。需要記錄的項目：

| 項目                       | 記錄方式           | 用途                 |
| -------------------------- | ------------------ | -------------------- |
| PHP 版本與模組             | `phpinfo()` 匯出   | VPS 上安裝對應版本   |
| Cron jobs                  | 主機面板截圖或匯出 | VPS 上重建 crontab   |
| Email 帳號與轉發規則       | 面板匯出           | 另外處理（見下方）   |
| DNS 記錄（A / CNAME / MX） | 域名管理介面匯出   | 切換時需要           |
| SSL 憑證                   | 簽發者、到期日     | VPS 上重新簽發或遷移 |
| .htaccess 規則             | 從站台下載         | 轉換成 nginx 設定    |

接手維運模組的[環境設定拍照](/infra/takeover/legacy-ftp-no-ssh/)有更完整的盤點方法。

### VPS 環境建立

VPS 上從零安裝 web stack：

```bash
# Ubuntu 22.04 為例
sudo apt update && sudo apt upgrade -y

# Web server
sudo apt install nginx -y

# PHP（對齊共享主機的版本）
sudo apt install php8.1-fpm php8.1-mysql php8.1-curl php8.1-mbstring php8.1-gd php8.1-xml -y

# MySQL
sudo apt install mysql-server -y

# SSL（Let's Encrypt）
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d example.com -d www.example.com
```

安裝完成後用 `php -m` 比對共享主機的 phpinfo 記錄，確認所有模組都已安裝。缺少的模組用 `apt install php8.1-<module>` 補上。

### 資料搬移

```bash
# 程式碼：從本地 Git repo 部署（不從共享主機直接搬）
git clone git@github.com:org/site.git /var/www/site

# 資料庫：從備份匯入
mysql -u root -p site_db < backup-latest.sql

# 使用者上傳檔案：從共享主機 FTP 下載後 rsync 到 VPS
rsync -avz /local/backup/uploads/ user@vps:/var/www/site/uploads/
```

### .htaccess → nginx 設定轉換

共享主機用 Apache 的 `.htaccess`，VPS 如果改用 nginx 需要手動轉換。常見的規則對照：

```nginx
# .htaccess: RewriteEngine On / RewriteRule ^(.*)$ index.php/$1
# nginx 等價：
location / {
    try_files $uri $uri/ /index.php?$query_string;
}

# .htaccess: Options -Indexes
# nginx 等價：
autoindex off;

# .htaccess: deny from all (某目錄)
# nginx 等價：
location ~ /\.env { deny all; }
```

轉換後在本地或 staging 驗證每條規則的行為是否一致。WordPress、Laravel 等框架有現成的 nginx 設定範例可參考。

### Email 處理

共享主機通常附帶 email 服務（用主機面板建 email 帳號）。VPS 預設不含 email。三個處理方式：

- 自架 email server（Postfix + Dovecot）：維運成本高、不推薦除非有特殊需求
- 改用第三方 email 服務（Google Workspace / Zoho Mail）：設定 MX 記錄指向服務商
- 只轉發（不收信）：應用程式的寄信功能改用 SMTP relay（SendGrid / Mailgun）

DNS 的 MX 記錄要在切換前就改好指向新的 email 服務，否則切換後 email 會中斷。

### SSL 自動續期

共享主機的 SSL 通常由主機商代管續期。VPS 上用 Let's Encrypt 的 certbot 會自動設定 systemd timer 或 cron 做續期，但要驗證它確實在跑：

```bash
# 確認 certbot 的自動續期排程存在
sudo systemctl list-timers | grep certbot

# 模擬續期測試（不實際續期）
sudo certbot renew --dry-run
```

## VPS → 雲端遷移

### 服務盤點與雲端對照

VPS 上的每個 process 都需要對應到雲端的服務：

| VPS 上的角色    | 雲端對應                        | 備註                 |
| --------------- | ------------------------------- | -------------------- |
| nginx + PHP-FPM | ECS Fargate / EC2 + ALB         | 容器化或直接搬       |
| MySQL           | RDS                             | managed DB、自動備份 |
| cron jobs       | EventBridge + Lambda / ECS task | 排程觸發的獨立 task  |
| 背景 worker     | ECS service / SQS + Lambda      | 依工作模式選型       |
| 檔案儲存        | S3 + CloudFront                 | 上傳檔案搬到物件儲存 |

### 自動化遷移工具

AWS Application Migration Service（MGN）可以自動化 VM workload 的搬遷——把現有 server 的 block-level data 持續複製到 AWS、切換時啟動 EC2 instance。適合大量 VM 的 lift-and-shift，但不處理應用層的重構（nginx config、cron 轉 EventBridge 等仍需手動）。單台 VM 的遷移用 MGN 反而比手動 dump/restore 多一層設定成本，適用場景是同時搬 5 台以上。

### IaC 的導入時機

VPS → 雲端是導入 IaC 的最佳時機——新環境從零建起，沒有歷史包袱。用 Terraform 描述 VPC、subnet、RDS、ECS、ALB 等資源，讓新環境可重現（見[模組一：最小可行 IaC](/infra/01-minimal-iac/)）。遷移完成後，這套 IaC 直接成為持續維運的基礎。

### 資料庫遷移

小型資料庫（< 10GB）：mysqldump + 匯入 RDS，遷移期間短暫唯讀即可。

```bash
# 從 VPS dump
mysqldump -u user -p --single-transaction site_db | gzip > site_db.sql.gz

# 匯入 RDS
gunzip -c site_db.sql.gz | mysql -h rds-endpoint.region.rds.amazonaws.com -u admin -p site_db
```

大型資料庫（> 10GB 或需要零停機）：使用 AWS DMS（Database Migration Service）做持續複寫，VPS 上的 MySQL 作為 source、RDS 作為 target，DMS 做初始全量複製後持續同步增量，切換時把應用指向 RDS 端點。

### 網路設計

雲端環境的網路要在遷移前規劃好。VPC、subnet、security group 的設計見[模組三：網路地基](/infra/03-network-foundation/)。VPS 上的 iptables 規則要映射成 security group 規則——iptables 的每條 accept 對應一條 SG ingress rule，但 SG 不支援 deny（用「不開就是 deny」的白名單模式）。

## 資料同步策略

| 策略                       | 停機時間         | 複雜度 | 適用場景                    |
| -------------------------- | ---------------- | ------ | --------------------------- |
| 一次性 dump + restore      | 分鐘到小時級     | 低     | 資料 < 10GB、可接受維護窗口 |
| 持續複寫（DMS / 邏輯複寫） | 秒級（切換瞬間） | 高     | 資料大、不允許停機          |
| 檔案 rsync 增量同步        | 取決於差異量     | 低     | 靜態檔案、上傳內容          |

選擇策略時先問兩個問題：資料量多大（決定 dump 時間）、業務能接受多長的唯讀或停機窗口（決定要不要持續複寫）。

對於上傳檔案（圖片、文件），遷移到雲端時通常從本地檔案系統搬到 S3：

```bash
# 從 VPS 同步上傳目錄到 S3
aws s3 sync /var/www/site/uploads/ s3://site-uploads/ --delete
```

應用程式碼裡的檔案路徑要改成 S3 URL 或用 CDN 代理。

## DNS 切換與驗證

### 切換前準備

遷移前 48 小時，降低 DNS TTL 到 300 秒（5 分鐘）。正常的 TTL 通常是 3600 秒（1 小時）或更長——如果切換出問題需要回退，短 TTL 讓 DNS 傳播更快。

```bash
# 確認當前 TTL
dig example.com +short +ttlid
```

### 切換操作

```bash
# 更新 A record 指向新平台的 IP / ALB endpoint
# 如果用 Route 53：
aws route53 change-resource-record-sets --hosted-zone-id Z123 --change-batch '{
  "Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
    "Name": "example.com", "Type": "A",
    "AliasTarget": {"HostedZoneId": "Z456", "DNSName": "alb-xxx.region.elb.amazonaws.com", "EvaluateTargetHealth": true}
  }}]
}'
```

### 切換後監控

切換後的驗證窗口至少等 2 倍 TTL（短 TTL 設 300 秒的話，至少等 10 分鐘）。在這段時間內：

- 新平台：監控 HTTP 狀態碼、回應時間、錯誤率
- 舊平台：觀察流量是否遞減到零（仍有流量代表 DNS 還沒完全傳播）
- 功能驗證：跑一次關鍵流程（登入、查詢、交易）

### 回退

如果新平台出問題，回退方式是把 DNS 切回舊平台的 IP。回退的生效時間等於當前的 TTL——這正是切換前降低 TTL 的理由。舊平台在 DNS 切換後要保留至少 72 小時（全球 DNS 快取最慢的清除時間），確認完全沒有流量後再退役。

### 切換後收尾

穩定運行 1-2 週後：

- 把 DNS TTL 恢復到正常值（3600 秒）
- 退役舊平台（關機 → 保留快照 → 一個月後刪除）
- 更新文件：新環境的存取方式、部署流程、監控端點

## 時程與管理層溝通

| 遷移路徑       | 典型時程 | 主要風險                             |
| -------------- | -------- | ------------------------------------ |
| 共享主機 → VPS | 1-2 週   | .htaccess 轉換、email 處理、SSL 續期 |
| VPS → 雲端     | 2-4 週   | 資料庫遷移、網路設計、IaC 建立       |
| 地端 → 雲端    | 4-8 週   | 網路重建、合規審查、資料主權         |

向管理層溝通時的關鍵訊息：「應用程式碼不變、改的是運行環境。風險集中在資料搬移和 DNS 切換這兩個步驟，兩者都有回退路徑。」

成本變化也要提前說明：共享主機 → VPS 的月費通常持平或略增（$5-30/月）；VPS → 雲端的月費取決於資源用量，初期可能增加 50-200%（換到的是彈性和 managed 服務），但可以透過 reserved instance 和 rightsizing 後續優化。

## 跨分類引用

- → [升級的共通操作框架](/infra/upgrade/upgrade-framework/)：評估差異 → 平行環境 → 切換 → 退役的四階段模型
- → [接手維運：無 SSH 的 FTP 環境](/infra/takeover/legacy-ftp-no-ssh/)：遷移前的環境盤點方法
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：雲端遷移是導入 IaC 的最佳時機
- → [模組三：網路地基](/infra/03-network-foundation/)：雲端環境的 VPC / subnet 設計
