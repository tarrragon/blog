---
title: "共享主機與 FTP 環境的接管"
date: 2026-06-26
description: "接手一個跑在共享主機上的 PHP 專案：沒有 SSH、沒有 CLI、只有 FTP 和 phpMyAdmin 時，怎麼盤點現況、建立本地開發環境、制定部署與資料庫變更紀律，以及找到升級路徑的切入點"
weight: 1
tags: ["infra", "takeover", "legacy", "ftp", "php"]
---

接手一個跑在共享主機上的 PHP 專案時，面對的約束跟雲端環境不同：沒有 SSH 可以登入下指令、沒有 CLI 工具可以批次操作、部署靠 FTP 上傳檔案、資料庫操作靠 phpMyAdmin 的網頁介面。前一位維護者的「文件」是他的記憶，而這份記憶已經隨著人一起離開。第一步是穩定維運，不是現代化改造。

這篇文章的操作順序按風險排列：先做不碰 prod 的盤點（零風險），再建本地開發環境（只動本機），然後才是碰 prod 的部署與資料庫紀律。

## 拍下完整現況（不動 prod）

接手後的第一個工作日只做一件事：把 prod 的完整狀態拍一份下來存到本地。這一步不改 prod 的任何東西，目的是讓自己手上有一份可對照的快照。

### 程式碼與靜態資源

用 FTP client（FileZilla、WinSCP、Cyberduck）把整個網站目錄下載到本地，然後初始化成 Git repo：

```bash
mkdir project-takeover && cd project-takeover
# FTP 下載完整站台到此目錄後
git init
git add -A
git commit -m "initial snapshot from production FTP"
```

這個 commit 是接手的基準線。之後任何改動都能 diff 回這個起點，知道自己改了什麼。

### 資料庫

用 phpMyAdmin 的「匯出」功能，選「自訂」模式，勾選所有資料表，格式選 SQL，編碼選 UTF-8。把匯出的 `.sql` 檔存進 repo：

```bash
mkdir db-snapshots
# 把 phpMyAdmin 匯出的檔案存到這裡
mv ~/Downloads/production-dump.sql db-snapshots/$(date +%Y%m%d)-initial.sql
git add db-snapshots/
git commit -m "initial database snapshot from phpMyAdmin"
```

如果主機面板有提供 `mysqldump` 的 web 介面（部分 cPanel 有），用那個比 phpMyAdmin 的匯出更可靠——phpMyAdmin 在大資料庫上容易因為 PHP 記憶體限制而中斷。

### 環境資訊記錄

在 repo 根目錄建一份 `ENVIRONMENT.md`，記錄以下資訊：

```markdown
## Production 環境

- **主機商**：[名稱]、方案：[方案名稱]
- **PHP 版本**：查看 phpinfo() 或控制面板
- **MySQL 版本**：phpMyAdmin 首頁顯示
- **Web server**：Apache / LiteSpeed / Nginx（控制面板或 response header）
- **域名 / DNS**：誰管的、nameserver 指向哪裡
- **SSL**：Let's Encrypt 自動續期 / 主機商代管 / 手動上傳
- **Cron jobs**：控制面板 → Cron Jobs 頁面截圖或列表
- **Email**：有沒有用主機的 email 服務、轉寄規則
- **.htaccess**：已包含在 FTP 下載中（注意隱藏檔有沒有漏）
```

### 掃描 hardcoded credential

PHP 專案常見的做法是把資料庫密碼、API key 直接寫在 `config.php` 或 `wp-config.php` 裡。在本地 repo 跑一次掃描：

```bash
grep -rn "password\|passwd\|secret\|api_key\|apikey\|api_secret" \
  --include="*.php" --include="*.ini" --include="*.env" .
```

把找到的每一筆記錄下來：哪個檔案、什麼 credential、用在哪裡。這份清單是後續 credential 輪替的輸入。

### 第三方整合清單

翻 code 找出所有對外部服務的呼叫——金流（綠界、藍新、Stripe）、簡訊（Twilio、三竹）、Email（SendGrid、SMTP）、社群登入（Facebook、Google）、CDN、Analytics。每一個整合都有對應的 API key 或 webhook URL，這些都是接手後需要確認存取權的項目。

## 建立本地開發環境

本地能跑起來，才有安全的測試空間。目標是用 Docker 或 MAMP/XAMPP 在本機重現 prod 的 PHP + MySQL 版本組合。

### Docker 方式

```yaml
# docker-compose.yml
services:
  web:
    image: php:8.1-apache
    volumes:
      - ./:/var/www/html
    ports:
      - "8080:80"
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: localdev
      MYSQL_DATABASE: project
    volumes:
      - ./db-snapshots/initial.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
```

PHP 版本要對齊 prod。如果 prod 是 PHP 7.4，本地用 `php:7.4-apache`。版本差異會導致函式行為不同（`str_contains` 在 8.0 才有、`mysql_*` 系列在 7.0 移除），測試通過但 prod 壞掉。

### 匯入資料庫

Docker 啟動後匯入初始快照：

```bash
docker exec -i project-db-1 mysql -uroot -plocaldev project < db-snapshots/20260626-initial.sql
```

### 常見的「本地跑不起來」原因

| 症狀                     | 原因                                                  | 修法                                   |
| ------------------------ | ----------------------------------------------------- | -------------------------------------- |
| 白頁或 500               | config 裡寫了 prod 的絕對路徑                         | 改成相對路徑或用環境變數               |
| 連不上資料庫             | DB host 寫了 `localhost` 但 Docker 裡 DB 是另一個容器 | 改成 Docker service 名稱（`db`）       |
| 某些功能壞掉             | prod 有裝特定 PHP extension（gd、mbstring、curl）     | Dockerfile 加 `docker-php-ext-install` |
| .htaccess rewrite 不生效 | Apache mod_rewrite 沒啟用                             | Dockerfile 加 `a2enmod rewrite`        |
| 圖片上傳失敗             | 上傳目錄權限不對                                      | `chmod 777 uploads/`（僅限本地）       |

本地能完整跑起來之後，這個環境就是所有變更的測試場。任何改動都先在這裡驗證。

## 資料庫變更紀律

phpMyAdmin 讓修改 prod DB 只需要幾次點擊，這正是它危險的原因——沒有 preview、沒有 undo、沒有 review。紀律要靠流程補上。

### 變更流程

1. 在本地 DB 寫好 SQL 並執行，確認結果正確
2. 把 SQL 存進 repo 的 `migrations/` 目錄，檔名帶日期：

```bash
# migrations/2026-06-26-add-status-column.sql
ALTER TABLE orders ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
```

3. 在 phpMyAdmin 上對要改的資料表做匯出（只匯出該表的結構 + 資料），存進 `db-snapshots/` 作為回退依據
4. 在 phpMyAdmin 的 SQL 頁籤貼上已驗證的 SQL 執行
5. 在 repo 的 `CHANGELOG.md` 記錄：時間、操作者、改了什麼、為什麼

### 高風險操作的額外防護

修改欄位型別、刪除欄位、刪除資料表、批次更新資料——這些操作在 phpMyAdmin 上執行就生效，沒有乾淨的 undo。額外防護是在執行前先確認：

- 有沒有剛做的該資料表備份（不是上週的，是剛剛做的）
- 這張表有沒有 foreign key 或觸發器會連帶影響其他表
- 如果改錯了，回退的具體步驟是什麼（從備份 SQL 重建整張表？還是用 UPDATE 改回來？）

## 部署紀律

FTP 部署沒有 CI pipeline 的自動化保護，但不代表不能有流程。流程的目標是讓每次部署都可追溯、可回退。

### 部署步驟

```text
1. git diff HEAD~1 --name-only          # 確認這次改了哪些檔案
2. 本地測試通過
3. FTP client 開兩個窗格：左邊本地、右邊 prod
4. 用 FileZilla 的目錄比較功能確認差異
5. 只上傳有變更的檔案（不要整站覆蓋）
6. 上傳完在瀏覽器驗證功能
7. git tag deploy-20260626 && git push   # 標記這次部署的版本
```

### 備份策略

共享主機通常不提供自動快照。備份要自己做：

| 備份項目 | 頻率                      | 方式                               | 保留               |
| -------- | ------------------------- | ---------------------------------- | ------------------ |
| 程式碼   | 每次部署前                | Git tag                            | 永久（在 repo 裡） |
| 資料庫   | 每週 + 每次 schema 變更前 | phpMyAdmin 匯出                    | 至少保留 4 週      |
| 上傳檔案 | 每週                      | FTP 下載 uploads/ 目錄             | 至少保留 4 週      |
| 主機設定 | 每次變更                  | 控制面板截圖 + ENVIRONMENT.md 更新 | 在 repo 裡         |

如果主機面板有自動備份功能（cPanel 的 Backup Wizard），確認它有開並且能還原。但不要把它當唯一備份——主機商的備份可能在主機出問題時一起不見。

### 回退方式

FTP 部署沒有 rollback 按鈕。回退的方式是：

```bash
git checkout deploy-20260625 -- path/to/changed/file.php
# 把特定檔案回到上一次部署的版本，再 FTP 上傳
```

整站回退則是 checkout 到上一個 deploy tag，再整批 FTP 上傳。這就是為什麼 deploy tag 重要——沒有 tag 就不知道要回退到哪個版本。

## credential 盤點與保護

接手後要回答的問題是：有哪些 credential、誰有存取權、哪些需要輪替。

### 盤點清單

| 類型         | 常見位置                              | 輪替難度                     |
| ------------ | ------------------------------------- | ---------------------------- |
| 資料庫密碼   | `config.php`、`wp-config.php`、`.env` | 低（phpMyAdmin + 改 config） |
| 主機面板登入 | 主機商帳號                            | 中（可能綁前人的 email）     |
| 金流 API key | `payment.php` 或 config 檔            | 中（需要登入金流後台）       |
| SMTP 密碼    | `mail.php` 或 config 檔               | 低                           |
| 域名管理     | DNS 服務商帳號                        | 高（可能綁前人的帳號）       |
| SSL 憑證     | 主機面板或 Let's Encrypt              | 低（自動續期則不用管）       |

最高優先輪替的是前人可能仍持有存取權的 credential：主機面板密碼、資料庫密碼。如果前人的離開不是善意的（被解僱、爭端），這些應該在接手的第一天就改。

### 從 hardcode 到 config 分離

長期目標是把 credential 從 code 裡搬出來。即使在共享主機上也能做：

```php
// 改前：password 直接寫在 code 裡
$db_password = 'p@ssw0rd123';

// 改後：從 .env 讀取（用 vlucas/phpdotenv 或手寫 parse）
$db_password = getenv('DB_PASSWORD') ?: parse_ini_file(__DIR__ . '/.env')['DB_PASSWORD'];
```

`.env` 放在 webroot 之外（如果主機允許）或在 `.htaccess` 裡禁止存取：

```apache
<Files ".env">
    Require all denied
</Files>
```

## 升級路徑的切入點

接手穩定後，逐步脫離共享主機的約束。每一步都獨立且可回退。

### 最低成本的第一步：CI 化 FTP 部署

在 GitHub repo 設定 GitHub Actions，推到 main 時自動跑測試（如果有的話）+ 自動 FTP 部署。FTP credential 存在 GitHub Secrets 裡，不在 code 裡。

```yaml
# .github/workflows/deploy.yml
name: Deploy via FTP
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SamKirkland/FTP-Deploy-Action@v4
        with:
          server: ${{ secrets.FTP_HOST }}
          username: ${{ secrets.FTP_USER }}
          password: ${{ secrets.FTP_PASS }}
          server-dir: /public_html/
```

這一步的價值是部署從「開 FileZilla 手動上傳」變成「push to main 自動部署」，人為失誤的空間顯著縮小。Prod 伺服器不需要任何改動。

### 下一步：共享主機 → VPS

當以下任一條件出現時，共享主機的約束會變成瓶頸：

- 需要 SSH 存取（裝 Git、跑 CLI 工具、設排程）
- 需要自訂 PHP extension 或 PHP 版本
- 需要更多的運算資源或記憶體
- 需要環境分離（dev / staging / prod）

遷移到 VPS（DigitalOcean、Linode、AWS Lightsail）後，SSH 存取讓所有雲端環境的工具鏈成為可用——Git on server、composer、artisan、mysqldump CLI、cron 的完整控制。這一步之後，接手維運的環境開始對齊[模組負一：還沒有 infra 的環境](/infra/before-infra/)的操作紀律，後續可以按[成熟度階梯](/infra/00-infra-mindset/)逐步往 IaC 推進。

## 跨分類引用

- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：接手完成、環境穩定後，操作紀律對齊這裡
- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：成熟度階梯作為接手後評估現況的座標
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：credential 盤點與輪替的系統性設計
- → [模組八：治理好習慣](/infra/08-governance-habits/)：tagging、secret 管理、成本可見性
