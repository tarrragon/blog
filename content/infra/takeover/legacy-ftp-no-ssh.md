---
title: "無 SSH 的 FTP / 面板管理環境接管"
date: 2026-06-26
description: "接手一個只有 FTP 和 phpMyAdmin（或 cPanel / Plesk）存取的 PHP 專案：沒有 SSH、沒有 CLI 時，怎麼盤點現況、建立本地開發環境、制定部署與資料庫變更紀律，以及找到升級路徑的切入點"
weight: 1
tags: ["infra", "takeover", "legacy", "ftp", "php"]
---

接手一個只有 [FTP](/infra/knowledge-cards/ftp/) 和網頁面板（[cPanel](/infra/knowledge-cards/cpanel/) / Plesk / phpMyAdmin）存取的 PHP 專案時，面對的約束跟有 [SSH](/infra/knowledge-cards/ssh/) 的環境不同：沒辦法登入下指令、沒有 CLI 工具可以批次操作、部署靠 FTP 上傳檔案、資料庫操作靠 phpMyAdmin 的網頁介面。這類環境常見於共享主機，但也可能出現在只安裝了面板的獨立主機或 VPS 上。前一位維護者的「文件」是他的記憶，而這份記憶已經隨著人一起離開。第一步是穩定維運，不是現代化改造。

這篇文章的操作順序按風險排列：先做不碰 prod 的盤點（零風險），再建本地開發環境（只動本機），然後才是碰 prod 的部署與資料庫紀律。

## 拍下完整現況（不動 prod）

接手後的第一個工作日只做一件事：把 prod 的完整狀態拍一份下來存到本地。這一步不改 prod 的任何東西，目的是讓自己手上有一份可對照的快照。

環境不同，拍照的工具和流程不同。先判斷自己的情境：

- **有 cPanel / Plesk 完整備份功能** → [用主機面板一次打包](#用主機面板一次打包)
- **只有 FTP 存取** → [用 FTP 逐層拍照](#用-ftp-逐層拍照)
- **有 SSH 存取**（部分 VPS 或獨立主機）→ 改讀[有 SSH 但沒有 IaC 的雲端環境接管](/infra/takeover/cloud-no-iac/)

### 用主機面板一次打包

如果主機有 cPanel，「備份精靈（Backup Wizard）」可以一次打包程式碼 + 資料庫 + email 設定 + cron jobs，是最快的完整快照方式。Plesk 的對應功能在「工具與設定 → 備份管理員」。

面板備份通常包含：網站檔案（含隱藏檔）、所有 MySQL 資料庫、email 帳戶與轉寄規則、cron job 設定、DNS zone 記錄。下載打包檔後解壓到本地、用 Git 初始化（見下方「初始化 Git repo」段）。

面板備份可能不包含的：SSL 憑證的私鑰（Let's Encrypt 自動續期的通常不需要手動備份）、PHP 版本與模組設定（需要另外記錄，見[環境設定的拍照](#環境設定的拍照)）、`.htaccess` 以外的 Apache/LiteSpeed 自訂設定。拿到面板備份後仍然要跑「環境設定的拍照」段，因為面板備份拍的是檔案、不是環境設定。

### 用 FTP 逐層拍照

沒有主機面板（或面板不提供完整備份）時，要用 FTP 和 phpMyAdmin 分別拍程式碼和資料庫。

**程式碼與靜態資源**：用 FTP client 把整個網站目錄鏡像到本地。[FileZilla](/infra/knowledge-cards/filezilla/) 的操作路徑：站台管理員連線後，在遠端面板對根目錄按右鍵 → 「下載」，或用「伺服器 → 同步瀏覽」模式讓本地與遠端目錄結構保持對齊。WinSCP 提供「保持更新（Keep Remote Directory up to Date）」功能，但接手階段只需要一次性的完整下載，不需要持續同步。下載前確認 FTP client 的設定有勾選「顯示隱藏檔案」——`.htaccess`、`.env`、`.user.ini` 這類隱藏檔經常包含關鍵設定。

**資料庫**：用 phpMyAdmin 的「匯出」功能匯出完整資料庫（詳見下方「資料庫」段）。FTP 只拍程式碼，資料庫要另外匯出。

### 初始化 Git repo

不論用面板備份還是 FTP 逐層拍，拿到檔案後都初始化成 Git repo：

```bash
mkdir project-takeover && cd project-takeover
# FTP 下載完整站台到此目錄後
git init
git add -A
git commit -m "initial snapshot from production FTP"
```

這個 commit 是接手的基準線。之後任何改動都能 diff 回這個起點，知道自己改了什麼。

### 資料庫

用 phpMyAdmin 的「匯出」功能：選「自訂」模式 → 勾選所有資料表 → 格式選 SQL → 勾選「加入 DROP TABLE / VIEW / PROCEDURE / FUNCTION / EVENT / TRIGGER 敘述」（讓匯入時能乾淨覆蓋）→ 壓縮選 gzip（大型資料庫避免瀏覽器逾時）→ 編碼選 UTF-8 → 執行。

phpMyAdmin 的匯出在資料庫超過幾百 MB 時容易因 PHP `max_execution_time` 或記憶體限制中斷。替代方案：如果主機有 cPanel，「phpMyAdmin → 匯出」旁邊通常有「MySQL 資料庫備份」或透過 cPanel API 的 `mysqldump` 介面，比 phpMyAdmin 的 PHP 層匯出更可靠。另一個選項是本地安裝 DBeaver（免費、跨平台）或 TablePlus（macOS/Windows），用主機提供的遠端 MySQL 連線（cPanel → 遠端 MySQL → 加入本機 IP 白名單）直接從本機執行 `mysqldump`。HeidiSQL（Windows 免費）也支援同樣的遠端連線匯出。

把匯出的 `.sql` 檔存進 repo：

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
- **PHP 版本**：cPanel/Plesk 的 PHP 設定頁直接顯示；沒有控制面板時，FTP 上傳一個 `phpinfo.php`（內容 `<?php phpinfo();`）到站台根目錄、瀏覽器開啟後記錄版本、確認後立刻刪除（phpinfo 會暴露伺服器完整設定）
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

### 環境設定的拍照

程式碼和資料庫之外，伺服器的執行環境本身也要記錄。非 container 環境沒有 `docker commit` 可以一次打包整台機器，要逐層拍：

**PHP 設定**：在站台根目錄上傳一個 `phpinfo.php`（內容 `<?php phpinfo();`），用瀏覽器打開後把完整輸出另存為 HTML 檔。記錄完立刻刪掉這個檔案——phpinfo 會暴露伺服器的完整設定與路徑。需要記錄的關鍵項：PHP 版本、載入的模組（`mysqli`、`curl`、`mbstring`、`gd`、`imagick`）、`upload_max_filesize`、`post_max_size`、`max_execution_time`、`memory_limit`、`error_reporting`、`session.save_handler`。這些值直接影響程式碼能不能在本地環境重現相同的行為。

**Cron jobs**：cPanel 的 Cron Jobs 頁面或 Plesk 的排程工作清單，截圖或逐條抄到 `ENVIRONMENT.md`。每一條 cron 記錄三項：排程時間、執行的指令（通常是 `/usr/local/bin/php /home/user/public_html/cron.php`）、這條 cron 的業務用途（如果能從指令或檔案名推斷）。

**SSL 憑證**：記錄域名、簽發者（Let's Encrypt / 自購 / 主機商代管）、到期日。瀏覽器的鎖頭圖示可以查看憑證詳情。從本機也可以用 CLI 確認：

```bash
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates -issuer
```

如果是 Let's Encrypt 自動續期，要確認續期機制是 cPanel 內建（AutoSSL）還是某個自訂 cron。手動購買的憑證要記錄到期日並設日曆提醒——過期後站台會直接出現瀏覽器安全警告。

**.htaccess 規則**：`.htaccess` 可能散在多個目錄（根目錄、`uploads/`、`wp-admin/`、`api/`）。FTP 下載時已包含在內（前提是 FTP client 有設定顯示隱藏檔案），確認一下這些檔案都在 repo 裡。

**外部服務連線**：除了前一節的第三方整合清單，用 grep 掃程式碼找出所有對外 URL。這些連線在未來遷移時要同步處理——搬了伺服器但 callback URL 沒改，金流通知就收不到。

```bash
grep -rn "https\?://" --include="*.php" . \
  | grep -v "localhost\|127\.0\.0\.1\|example\.com" \
  | sort -u > _environment/external-urls.txt
```

**檔案權限**：FileZilla 的遠端檔案清單有權限欄。記錄 `uploads/`、`cache/`、`sessions/`、config 檔案的權限。777 的目錄是安全風險（任何使用者都能寫入），在多租戶的主機上尤其危險——同台主機的其他帳戶也能存取。

把以上資料存進 repo 的 `_environment/` 目錄：

```text
_environment/
├── phpinfo-20260626.html      # phpinfo 完整輸出
├── cron-jobs.md               # cron 清單
├── ssl-cert-info.txt          # 憑證資訊
├── external-urls.txt          # 外部連線清單
└── file-permissions.txt       # 目錄權限記錄
```

`_environment/` 可加進 `.gitignore`（phpinfo 含敏感資訊），或只 ignore HTML 檔、其餘進 Git。

## 建立本地開發環境

本地能跑起來，才有安全的測試空間。目標是在本機重現 prod 的 PHP + MySQL 版本組合。

### 選型：Docker vs 本地堆疊

| 工具           | 平台                    | 費用              | 適用情境                                            |
| -------------- | ----------------------- | ----------------- | --------------------------------------------------- |
| Docker Compose | 跨平台                  | 免費              | 最精確對齊 prod 版本，特別是 PHP 5.6/7.0 這類舊版本 |
| MAMP Pro       | macOS                   | 付費（約 $50/年） | 圖形介面切 PHP 版本，不熟 Docker 時最快上手         |
| Laragon        | Windows                 | 免費              | 比 XAMPP 現代、內建 PHP 版本切換與虛擬網域          |
| XAMPP          | Windows / macOS / Linux | 免費              | 最老牌、社群資源多，但 PHP 版本切換較麻煩           |
| Laravel Valet  | macOS                   | 免費              | 輕量 CLI 為主，適合已經熟悉 CLI 的開發者            |
| ServBay        | macOS                   | 免費版可用        | 較新、支援多 PHP 版本共存、內建資料庫管理           |

選型判準：如果 prod 的 PHP 版本是 5.6 或 7.0 這類已停止維護的舊版，Docker 是唯一能精確對齊的選項——MAMP/XAMPP 通常只提供仍在維護的版本。常見版本（7.4、8.0、8.1、8.2）用 MAMP/Laragon 會比 Docker 更快跑起來。

### Docker 方式

Docker Compose V2（`docker compose` 指令）不需要 `version` 欄位。如果使用舊版 `docker-compose` CLI，在檔案開頭加 `version: '3.8'`。

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
  phpmyadmin:
    image: phpmyadmin/phpmyadmin
    environment:
      PMA_HOST: db
    ports:
      - "8081:80"
```

PHP 版本要對齊 prod。如果 prod 是 PHP 7.4，本地用 `php:7.4-apache`。版本差異會導致函式行為不同（`str_contains` 在 8.0 才有、`mysql_*` 系列在 7.0 移除），測試通過但 prod 壞掉。phpmyadmin service 讓本地也有跟 prod 相同的資料庫操作介面，方便驗證 phpMyAdmin 上要執行的操作。

### 匯入資料庫

Docker 啟動後匯入初始快照：

```bash
docker exec -i project-db-1 mysql -uroot -plocaldev project < db-snapshots/20260626-initial.sql
```

MAMP/Laragon/XAMPP 的匯入方式：開啟對應的 phpMyAdmin（通常在 `localhost/phpmyadmin`）→ 選資料庫 → 匯入 → 選 `.sql` 檔案 → 執行。或用 DBeaver/TablePlus 連本地 MySQL 後執行 SQL 檔。

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

無 SSH 的主機環境通常不提供自動快照。備份要自己做：

| 備份項目 | 頻率                      | 方式                               | 保留               |
| -------- | ------------------------- | ---------------------------------- | ------------------ |
| 程式碼   | 每次部署前                | Git tag                            | 永久（在 repo 裡） |
| 資料庫   | 每週 + 每次 schema 變更前 | phpMyAdmin 匯出                    | 至少保留 4 週      |
| 上傳檔案 | 每週                      | FTP 下載 uploads/ 目錄             | 至少保留 4 週      |
| 主機設定 | 每次變更                  | 控制面板截圖 + ENVIRONMENT.md 更新 | 在 repo 裡         |

如果主機面板有自動備份功能（cPanel 的 Backup Wizard），確認它有開並且能還原。但不要把它當唯一備份——主機商的備份可能在主機出問題時一起不見。

### 備份自動化（沒 SSH 也能做）

無 SSH 的環境沒有 cron + CLI 的組合，但可以用本機排程 + FTP client 的 CLI 模式達成自動化備份。

用 lftp（macOS/Linux 可透過 Homebrew 或 apt 安裝）做定期站台鏡像：

```bash
# backup.sh — 加入本機的 cron 或 launchd 每日執行
lftp -e "mirror --verbose /public_html/ /local/backup/site/; quit" \
  -u username,password ftp.example.com
```

rclone 是另一個選項，支援 FTP/SFTP 且有更好的增量同步（只傳有變更的檔案）：

```bash
# 設定 rclone remote（首次）
rclone config  # 選 FTP、填入主機資訊

# 同步（之後每次只傳差異）
rclone sync myhost:/public_html/ /local/backup/site/ --progress
```

macOS 用 launchd plist、Windows 用工作排程器（Task Scheduler）排定每日執行這些腳本，讓備份不再依賴人工記得。

資料庫的自動備份較受限——phpMyAdmin 沒有 CLI 介面。如果主機允許遠端 MySQL 連線，可以在本機 cron 裡加一條 `mysqldump`：

```bash
mysqldump -h mysql.example.com -u dbuser -p'password' dbname | gzip > /local/backup/db/$(date +%Y%m%d).sql.gz
```

不允許遠端連線時，退而求其次：每週手動從 phpMyAdmin 匯出一次、存進 repo。

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

長期目標是把 credential 從 code 裡搬出來。即使在沒有 SSH 的環境也能做：

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

## 外部監控（prod 不用裝東西）

無 SSH 的環境裝不了監控 agent，但可以用外部 HTTP 檢查服務從外面看。這類服務從多個地理位置定期對網站發送 HTTP request，回應異常時通知。

UptimeRobot 的免費方案提供 50 個 monitor、每 5 分鐘檢查一次，夠用於一個站台的首頁 + 幾個關鍵頁面（登入頁、API endpoint、金流回呼 URL）。Better Stack（原 Better Uptime）提供類似功能並附帶 status page。兩者都只需要填入 URL 和通知方式（email / Slack / webhook），不需要在 server 上裝任何東西。

設定後至少加三個 monitor：首頁（網站是否活著）、登入或後台入口（PHP 是否正常執行）、以及任何有外部依賴的頁面（金流 callback、API endpoint）。這不是完整的可觀測性，但至少讓「網站掛了」這件事從「使用者打電話來」變成「手機收到通知」。

## 時程參考

完整走完盤點（FTP mirror + DB dump + 環境記錄）約需半天到一天。本地環境建立與驗證約需半天到一天（取決於 PHP 版本對齊的難度）。紀律建立（changelog + 部署流程）是持續的、但框架搭建約需 2-3 小時。CI 化 FTP 部署約需半天。整體從接手到穩定維運約 2-3 個工作天。

## 升級路徑的切入點

接手穩定後，逐步脫離無 SSH 環境的約束。每一步都獨立且可回退。

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

### 下一步：遷移到有 SSH 的 VPS

當以下任一條件出現時，無 SSH 環境的約束會變成瓶頸：

- 需要 SSH 存取（裝 Git、跑 CLI 工具、設排程）
- 需要自訂 PHP extension 或 PHP 版本
- 需要更多的運算資源或記憶體
- 需要環境分離（dev / staging / prod）

遷移到 VPS（DigitalOcean、Linode、AWS Lightsail）後，SSH 存取讓所有雲端環境的工具鏈成為可用——Git on server、composer、artisan、mysqldump CLI、cron 的完整控制。這一步之後，接手維運的環境開始對齊[模組負一：還沒有 infra 的環境](/infra/before-infra/)的操作紀律，後續可以按[成熟度階梯](/infra/00-infra-mindset/)逐步往 IaC 推進。

## 跨分類引用

- → [有 SSH 但沒有 IaC 的雲端環境接管](/infra/takeover/cloud-no-iac/)：搬到 VPS 或雲端後的接管流程
- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：接手完成、環境穩定後，操作紀律對齊這裡
- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：成熟度階梯作為接手後評估現況的座標
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：credential 盤點與輪替的系統性設計
- → [模組八：治理好習慣](/infra/08-governance-habits/)：tagging、secret 管理、成本可見性
