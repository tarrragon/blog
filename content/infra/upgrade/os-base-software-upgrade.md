---
title: "OS 與基礎軟體更換"
date: 2026-06-26
description: "EOL 作業系統的遷移評估、目標 OS 選型、原地升級 vs 平行建置的取捨、應用層遷移清單，以及 Apache → nginx 等基礎軟體切換的操作要點"
weight: 5
tags: ["infra", "upgrade", "os", "migration"]
---

作業系統到達 end-of-life（EOL）後不再收到安全修補——每一個新發現的漏洞都會永久敞開。EOL OS 上跑的服務不是「可能有風險」，而是「風險只會隨時間單調增加」。遷移的問題是何時做和怎麼做，不是要不要做。

## EOL 風險評估

EOL 在操作層面的意義是三件事同時停止：安全修補（CVE 不再被回填到該版本的 patch release）、核心更新（kernel 的錯誤修正與硬體支援停止）、套件庫維護（官方 repository 凍結或下架，新裝套件或更新依賴都做不到）。

### 風險時間軸

EOL 是一段逐漸惡化的過程，而非單一時間點：

| 階段       | 事件                                 | 影響                                   |
| ---------- | ------------------------------------ | -------------------------------------- |
| 宣告       | 官方公布 EOL 日期（通常提前 1-2 年） | 開始規劃遷移的訊號                     |
| 正式 EOL   | 最後一個安全修補發布                 | 新 CVE 不再有 patch                    |
| 套件庫凍結 | 官方 mirror 停止同步或下架           | `yum update` / `apt update` 失敗       |
| 合規失效   | 稽核認定執行環境不符標準             | PCI DSS / SOC 2 / ISO 27001 判定不合規 |

### 常見的 EOL 情境

CentOS 7 在 2024 年 6 月結束支援，但仍有大量 production 環境在使用。CentOS 8 在 2021 年 12 月被轉向 CentOS Stream，打破了原本預期到 2029 年的支援承諾，迫使使用者重新選型。Ubuntu 18.04 的標準支援在 2023 年 4 月結束，Canonical 提供 ESM（Extended Security Maintenance）付費延長到 2028 年，但 ESM 只涵蓋 main 套件庫。

ESM 或類似的付費延長支援（RHEL 的 ELS、CentOS 的第三方 TuxCare）是「買時間做遷移」的合理策略——付月費取得額外 2-5 年的安全修補，讓團隊有餘裕規劃平行建置而非被迫緊急遷移。Ubuntu Pro 免費涵蓋 5 台 instance 的 ESM，超過才需要付費。ESM 是給遷移專案爭取時間的保險，而非長期方案——延長支援的套件覆蓋範圍通常比標準期窄。

合規的影響很直接：PCI DSS 要求所有面對持卡人資料的系統都執行在有安全修補支援的軟體上；SOC 2 和 ISO 27001 的定期稽核會檢查作業系統的支援狀態。在 EOL OS 上跑的 production 環境會讓稽核結果出現 finding，需要額外的補償控制（compensating control）才能通過——而補償控制的維護成本通常高於遷移本身。

## 目標 OS 選型

選型看四個維度：LTS 發布週期（支援年限多長）、社群與商業支援（問題能不能查到答案、能不能買付費支援）、套件可用性（應用層需要的 runtime 和 library 在官方 repo 裡有沒有）、團隊熟悉度（操作指令和設定路徑的學習成本）。

### 常見選擇

| OS                          | 支援週期            | 適用情境                         |
| --------------------------- | ------------------- | -------------------------------- |
| Ubuntu 22.04 / 24.04 LTS    | 5 年標準 + 5 年 ESM | 社群最大、套件最新、學習資源最多 |
| Debian 12 (Bookworm)        | ~5 年               | 穩定性優先、更新保守             |
| Amazon Linux 2023           | 5 年                | AWS 生態深度整合、EC2 預設選項   |
| Rocky Linux 9 / AlmaLinux 9 | ~10 年              | CentOS 替代、RHEL 相容           |

### 同家族 vs 跨家族

CentOS → Rocky Linux / AlmaLinux 是同家族遷移：套件名稱、設定路徑、init 系統（systemd）幾乎不變，應用層的改動最少。CentOS → Ubuntu 是跨家族遷移：套件管理從 yum/dnf 換成 apt、設定路徑從 `/etc/httpd/` 變成 `/etc/apache2/`、某些服務名稱不同。

同家族遷移的優勢是應用層風險低——多數設定檔可以直接搬過去。跨家族遷移的優勢是可以借機切到更活躍的生態（Ubuntu 的社群回答量和第三方套件支援在多數指標上領先），代價是設定檔要全面調整。

選型判準：如果團隊已經有 Ubuntu 經驗、或其他系統已經跑 Ubuntu，統一到 Ubuntu 的長期維護成本較低。如果團隊對 RHEL 系操作更熟、或有 RHEL 付費支援合約，Rocky/Alma 是阻力最小的路。

## 遷移策略：原地升級 vs 平行建置

### 原地升級

在現有伺服器上直接換 OS 版本。做法是用 OS 提供的升級工具（如 `do-release-upgrade`、`leapp`）在跑著的系統上切換。

風險集中在升級過程中系統處於不確定狀態——kernel 換了但 userland 還沒、init 系統切了但服務設定還指向舊路徑。如果中途失敗、伺服器可能開不了機，而 rollback 意味著從備份還原整台機器。原地升級只在同 OS 家族的小版本升級（如 Ubuntu 20.04 → 22.04）且有完整 VM 快照保底時才值得考慮。

### 平行建置

在旁邊建一台新 OS 的伺服器、安裝應用層、遷移資料、用 DNS 或 load balancer 切換流量。舊伺服器保留作為 rollback 目標，確認新環境穩定後再退役。

平行建置的成本是短期多付一台伺服器的費用（通常是幾天到幾週）。收益是：升級失敗時舊伺服器完好無損、切回去只需要改 DNS 或 LB 的 target；新伺服器可以在切換前充分測試、不影響線上服務；整個過程可以在非尖峰時段進行。

對多數環境來說平行建置是預設策略。原地升級只在無法多開一台伺服器（預算極度受限、或裸機硬體無備品）時才退而求其次。

## 應用層的遷移清單

新 OS 上要重建整個應用執行環境。以下是逐項需要確認的面向：

### Web 伺服器

如果新舊 OS 都用 Apache，設定檔的路徑可能不同（RHEL 系 `/etc/httpd/conf.d/`、Debian 系 `/etc/apache2/sites-available/`），模組載入方式也不同（`LoadModule` 指令 vs `a2enmod` 工具）。逐一比對現有的 VirtualHost 設定、rewrite 規則、SSL 設定。

如果同時換成 nginx，見下一節。

### Runtime 版本對齊

新 OS 的官方 repo 裡的 PHP / Node / Python 版本可能跟舊 OS 不同。Ubuntu 22.04 預設 PHP 8.1、如果應用需要 PHP 7.4 要加第三方 PPA（如 ondrej/php）。確認所有 PHP extension（mysqli、curl、gd、mbstring、redis）在新 OS 上都有對應的套件名稱且已安裝。

```bash
# 舊伺服器：列出所有已載入的 PHP module
php -m > old-php-modules.txt

# 新伺服器：比對缺了什麼
php -m > new-php-modules.txt
diff old-php-modules.txt new-php-modules.txt
```

### 資料庫客戶端程式庫

應用連接 MySQL / PostgreSQL 用的 client library（`libmysqlclient`、`libpq`）版本要跟資料庫伺服器相容。跨大版本（MySQL 5.7 client → MySQL 8.0 server）通常向前相容，但反過來可能有驗證方式不匹配的問題（如 MySQL 8.0 的 `caching_sha2_password` 預設驗證方式）。

### Cron jobs

從舊伺服器匯出 crontab（`crontab -l`），在新伺服器重建。如果舊 OS 使用 `/etc/cron.d/` 的檔案式 [cron](/infra/knowledge-cards/cron/)，確認新 OS 的 cron daemon 支援同樣的格式。Cron 的環境變數（PATH、MAILTO）在不同 OS 可能有不同預設。

### 日誌路徑

Apache 的預設 log 路徑在 RHEL 系是 `/var/log/httpd/`、Debian 系是 `/var/log/apache2/`。應用程式如果 hardcode 了日誌路徑，要在新 OS 上對齊。同時確認 logrotate 的設定在新 OS 上存在且正確。

### 檔案權限與使用者

不同 OS 的 web server 執行使用者不同（RHEL 的 `apache`、Debian 的 `www-data`）。如果應用依賴特定使用者名稱的檔案權限（如 upload 目錄的 owner），遷移後要調整 `chown`。

### 服務管理

現代 OS 都使用 systemd。但如果舊 OS 還有 sysvinit 腳本（`/etc/init.d/`），遷移時要轉換成 systemd unit file。轉換的核心是把 init 腳本的 start/stop/restart 邏輯對應到 systemd 的 `ExecStart`、`ExecStop`、`Restart` 欄位。

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
After=network.target mysql.service

[Service]
Type=simple
User=www-data
ExecStart=/usr/bin/php /var/www/myapp/worker.php
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 基礎軟體切換（Apache → nginx）

如果已經在為 OS 遷移建新伺服器，同時切換 web server 是成本最低的時機——反正設定檔要重寫、不如一次到位。分開做的話要拆兩次遷移、測兩次、承受兩次風險。

### .htaccess → nginx 設定轉換

Apache 的 .htaccess 是分散式設定——每個目錄可以有自己的 `.htaccess`，Apache 在每次請求時逐層讀取。nginx 沒有這個機制，所有設定集中在 `/etc/nginx/` 的設定檔裡。

轉換的第一步是找出所有 .htaccess 檔案：

```bash
find /var/www/ -name ".htaccess" -exec echo "=== {} ===" \; -exec cat {} \;
```

常見的轉換對應：

| Apache .htaccess                           | nginx 對應                                        |
| ------------------------------------------ | ------------------------------------------------- |
| `RewriteRule ^old$ /new [R=301]`           | `rewrite ^/old$ /new permanent;`                  |
| `RewriteCond %{HTTPS} off` + `RewriteRule` | `if ($scheme = http) { return 301 https://...; }` |
| `Options -Indexes`                         | `autoindex off;`（通常是預設）                    |
| `php_flag engine off`                      | `location /uploads/ { deny all; }` 或不傳給 PHP   |
| `<Files .env>` + `Deny from all`           | `location ~ /\.env { deny all; }`                 |
| `AuthType Basic` + `.htpasswd`             | `auth_basic` + `auth_basic_user_file`             |

### 平行測試

在新伺服器上同時安裝 nginx（port 80）和 Apache（port 8080）。用 curl 比對兩者的回應：

```bash
# 比對首頁
diff <(curl -s http://new-server/) <(curl -s http://new-server:8080/)

# 比對一個有 rewrite 規則的 URL
diff <(curl -sI http://new-server/old-path) <(curl -sI http://new-server:8080/old-path)
```

回應一致後再把 Apache 移除。重點比對項：HTTP status code（rewrite 的 301/302）、response body（PHP 輸出）、response header（cache control、security header）。

### 常見陷阱

.htaccess 的分散式設定在 WordPress 或其他 CMS 中常被用來動態控制 URL rewrite。WordPress 的 permalink 功能依賴根目錄的 `.htaccess`，切到 nginx 需要在設定檔裡加 `try_files $uri $uri/ /index.php?$args;` 才能讓 permalink 運作。其他 CMS（Drupal、Laravel）也有各自的 nginx 設定範例，通常在官方文件裡可以找到。

## 時程與管理層溝通

OS 遷移（平行建置）的時程取決於應用層的複雜度：

| 環境複雜度 | 時程估算 | 典型特徵                           |
| ---------- | -------- | ---------------------------------- |
| 簡單       | 1-2 週   | 單一 web app、標準 LAMP/LEMP stack |
| 中等       | 2-3 週   | 多個服務、自訂套件、cron 密集      |
| 複雜       | 3-4 週   | 多台伺服器、叢集、自建 daemon      |

跟管理層溝通時用三個框架：

**為什麼現在做**：「目前的 OS 已經停止安全修補，每個月不遷移等於多一個月的曝險窗口。如果有合規要求（PCI DSS / SOC 2），下次稽核會被標記。」

**做什麼**：「在旁邊建一台新 OS 的伺服器，把應用搬過去、驗證通過後切換。舊伺服器保留一到兩週作為 rollback。」

**花多久和多少錢**：「工程師時間 1-3 週（依複雜度）。多一台伺服器的費用只有切換期間的短期成本。不做的隱藏成本是安全事故的潛在損失和合規罰款。」

## 跨分類引用

- → [升級的共通操作框架](/infra/upgrade/upgrade-framework/)：四階段模型（評估差異 → 平行環境 → 分批切換 → 退役）
- → [平台遷移](/infra/upgrade/platform-migration/)：如果 OS 遷移同時伴隨平台搬遷（地端 → 雲端）
- → [Runtime 版本升級](/infra/upgrade/runtime-version-upgrade/)：PHP / Node 版本升級常伴隨 OS 遷移
- → [接手維運](/infra/takeover/)：接手一個 EOL OS 的環境後的下一步
