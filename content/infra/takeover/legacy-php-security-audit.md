---
title: "Legacy PHP 的安全盤點"
date: 2026-06-26
description: "接手 legacy PHP 專案後的系統性安全審查：credential 掃描、PHP 版本風險、常見漏洞模式的 grep 偵測、.htaccess 防線、檔案權限、外部依賴與掃描工具"
weight: 12
tags: ["infra", "takeover", "security", "php", "audit"]
---

接手的 legacy PHP 專案在做完[程式碼與資料庫的現況快照](/infra/takeover/legacy-ftp-shared-hosting/)之後，下一步是安全盤點。安全狀態在盤點之前是未知的——前一位維護者可能所有表單都用 prepared statement，也可能每個查詢都直接拼接使用者輸入。盤點的範圍涵蓋 credential 散落、PHP 版本風險、程式碼層的漏洞模式、伺服器端的 .htaccess 與權限設定、以及外部依賴的已知漏洞。

## Credential 掃描與處理

寫死在程式碼裡的 credential 是接手後最先要掌握的風險面。資料庫密碼、API key、SMTP 帳號這些值如果散落在多個 PHP 檔案裡，每一個都是外洩路徑。

### 掃描方式

用 grep 對整個 codebase 搜尋常見的 credential 關鍵字：

```bash
grep -rn "password\|passwd\|secret\|api_key\|app_key\|mysql_connect\|mysqli_connect\|PDO(" \
  --include="*.php" .
```

常見的集中位置是 `config.php`、`wp-config.php`、`database.php`、`settings.php`，以及專案根目錄的 `.env`。但 legacy 專案的 credential 經常散落在意想不到的地方——寫在某個 helper function 的預設參數裡、硬編碼在 cron job 的 PHP 檔案裡、或藏在某個很久沒改的 email 發送模組裡。grep 的涵蓋範圍應該是整個專案目錄，不只是已知的 config 檔案。

如果專案已經在本地 Git repo（見[主文](/infra/takeover/legacy-ftp-shared-hosting/)的快照步驟），檢查 Git 歷史裡有沒有曾經存在但後來被刪除的 credential：

```bash
git log --all -p -- '*.php' | grep -i "password\|secret\|api_key" | head -30
```

歷史裡的 credential 無法從 Git 裡真正移除（rewrite history 可以但成本高），所以找到的 credential 都要列入輪替清單。

### 處理方式

掃描結果彙整成一張清單，每筆記錄：credential 類型、所在檔案、用途、是否可輪替。處理優先序：

| 類型                         | 處理方式                                       | 優先級   |
| ---------------------------- | ---------------------------------------------- | -------- |
| 資料庫密碼                   | 移到 `.env` 或 `config.local.php`（gitignore） | 立刻     |
| 第三方 API key（金流、簡訊） | 移到 config + 確認可輪替                       | 立刻     |
| SMTP 密碼                    | 移到 config                                    | 第二順位 |
| 內部服務 token               | 移到 config + 確認對方端有沒有輪替機制         | 第二順位 |
| 已停用的 credential          | 確認停用後從 code 移除                         | 第三順位 |

把 credential 從 code 移到 `.env` 後，用 `getenv('DB_PASSWORD')` 或框架的 config 機制讀取。`.env` 加進 `.gitignore`，prod 的 `.env` 透過 FTP 單獨上傳、不進版本控制。

## PHP 版本與已知漏洞

PHP 版本決定了這個專案暴露在什麼層級的平台風險下。已結束安全支援（EOL）的 PHP 版本不代表「馬上會被攻擊」，但代表任何未來被發現的漏洞都不會得到官方修補。

### 版本確認

在站台放一個 `phpinfo.php`，瀏覽後記錄版本號，完成後立刻刪除（`phpinfo()` 輸出含伺服器路徑與配置細節，留在 prod 上是資訊外洩）：

```php
<?php phpinfo(); ?>
```

或在 cPanel / Plesk 的 PHP 設定頁面直接查看。

### 版本風險對照

| 版本      | 安全支援狀態（2026）     | 風險等級   | 行動                   |
| --------- | ------------------------ | ---------- | ---------------------- |
| 5.6 以下  | 已 EOL 超過 8 年         | 高         | 列入升級計畫、優先處理 |
| 7.0 - 7.4 | 已 EOL                   | 中高       | 排進季度 roadmap       |
| 8.0       | 已 EOL（2023-11）        | 中         | 排進半年 roadmap       |
| 8.1       | 安全修補中（至 2025-12） | 已接近 EOL | 規劃升級到 8.2+        |
| 8.2+      | 活躍支援中               | 低         | 維持更新               |

版本升級是獨立的工程專案——可能會觸發函式棄用警告、行為變更、甚至語法不相容。盤點階段的任務是記錄版本和風險等級，升級規劃放在穩定維運之後。

## 常見的 PHP 安全漏洞模式

Legacy PHP 專案最常見的四類漏洞都可以用 grep 做初步掃描。掃描結果是候選清單、不是確認的漏洞——每個命中都需要讀上下文確認是否有防護。

### SQL injection

任何把使用者輸入直接拼接到 SQL 查詢裡的寫法都是 SQL injection 的候選：

```bash
# 找使用 mysql_query / mysqli_query 但沒有 prepare/bind 的查詢
grep -rn "mysql_query\|mysqli_query" --include="*.php" . | grep -v "prepare\|bind_param"

# 找字串拼接的 SQL 查詢
grep -rn "query.*\\\$_GET\|query.*\\\$_POST\|query.*\\\$_REQUEST" --include="*.php" .
```

修法是改用 prepared statement（PDO 或 mysqli 的 `prepare` + `bind_param`）。如果 codebase 大量使用 `mysql_*` 函式（PHP 7.0 已移除），這本身就是版本升級的阻礙——需要同時處理。

### XSS（跨站腳本）

把使用者輸入直接輸出到 HTML 而沒有跳脫：

```bash
# 找直接 echo/print 使用者輸入的地方
grep -rn "echo.*\\\$_GET\|echo.*\\\$_POST\|echo.*\\\$_REQUEST\|echo.*\\\$_COOKIE" --include="*.php" .

# 找 PHP 短標籤輸出
grep -rn "<?=.*\\\$_" --include="*.php" .
```

修法是所有輸出都經過 `htmlspecialchars($var, ENT_QUOTES, 'UTF-8')`。模板引擎（如 Twig、Blade）預設會做跳脫，使用模板引擎的專案 XSS 風險較低。

### 檔案包含（File Inclusion）

把使用者輸入當作 `include` 或 `require` 的路徑：

```bash
grep -rn "include.*\\\$_\|require.*\\\$_\|include_once.*\\\$_\|require_once.*\\\$_" --include="*.php" .
```

這類寫法讓攻擊者可以指定載入任意檔案（本地或遠端）。修法是用白名單限制可載入的檔案路徑。

### 檔案上傳

檢查上傳處理的三個面向：副檔名驗證（只允許白名單）、上傳目錄是否可執行 PHP（不應該）、檔案大小限制。

```bash
# 找上傳處理程式碼
grep -rn "move_uploaded_file\|\\\$_FILES" --include="*.php" .
```

每個命中的上傳處理都要確認：有沒有驗證副檔名（黑名單不夠、要白名單）、上傳目錄有沒有 `.htaccess` 禁止 PHP 執行（見下節）、有沒有重新命名上傳的檔案（避免覆寫攻擊）。

### Session 管理

```bash
# 找 session 相關設定
grep -rn "session_start\|session_regenerate_id\|session\.cookie_httponly\|session\.cookie_secure" --include="*.php" .
```

確認：登入成功後有沒有呼叫 `session_regenerate_id(true)` 防止 session fixation、`session.cookie_httponly` 是否為 on（防止 JavaScript 讀取 session cookie）、`session.cookie_secure` 在 HTTPS 站台是否為 on。

## .htaccess 安全設定

共享主機上 `.htaccess` 是可用的伺服器端安全防線。盤點時確認這些設定是否存在，缺少的補上。

### 基礎安全設定

```apache
# 禁止目錄列表 — 防止瀏覽上傳目錄的檔案清單
Options -Indexes

# 阻擋敏感檔案的 HTTP 存取
<FilesMatch "\.(env|local|bak|sql|log|ini|conf|yml|json|lock|md)$">
    Require all denied
</FilesMatch>

# 阻擋隱藏檔案與目錄（.git、.env 等）
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule (^\.|/\.) - [F]
</IfModule>

# 強制 HTTPS
<IfModule mod_rewrite.c>
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>
```

### 上傳目錄的 PHP 執行禁令

在上傳目錄（如 `uploads/`、`wp-content/uploads/`）放一個獨立的 `.htaccess`：

```apache
# 禁止此目錄下的 PHP 執行
php_flag engine off

# 只允許靜態檔案類型
<FilesMatch "\.(?!jpg|jpeg|png|gif|pdf|webp|svg|css|js)">
    Require all denied
</FilesMatch>
```

這條設定讓即使攻擊者成功上傳了 `.php` 檔案，也無法透過 HTTP 請求觸發執行。

### 安全 header

```apache
# 防止 MIME type sniffing
Header set X-Content-Type-Options "nosniff"

# 防止 clickjacking
Header set X-Frame-Options "SAMEORIGIN"

# XSS 防護（現代瀏覽器多已內建、但舊站加上無害）
Header set X-XSS-Protection "1; mode=block"

# Referrer 資訊控制
Header set Referrer-Policy "strict-origin-when-cross-origin"
```

## 檔案權限

共享主機的權限控制能力有限——多數情況下透過 FTP client 檢查和調整。

| 對象                         | 建議權限 | 理由                                                                      |
| ---------------------------- | -------- | ------------------------------------------------------------------------- |
| 目錄                         | 755      | owner 可讀寫執行、group/other 可讀可執行（Apache 需要執行權才能進入目錄） |
| PHP 檔案                     | 644      | owner 可讀寫、group/other 只讀                                            |
| Config 檔案（含 credential） | 640      | group 可讀（Apache 通常跟 owner 同 group）、other 不可讀                  |
| 上傳目錄                     | 755      | 跟一般目錄相同，搭配 .htaccess 禁止 PHP 執行                              |

777 權限（所有人可讀寫執行）在共享主機上等於同一台伺服器的其他租戶也能讀寫這些檔案。如果發現任何目錄或檔案是 777，立刻改回 755/644。FileZilla 在檔案上按右鍵 → 「File permissions」可以查看和修改。

## 外部依賴的安全性

### Composer 管理的依賴

如果專案使用 Composer，在本地跑一次已知漏洞檢查：

```bash
composer audit
```

這條指令比對 `composer.lock` 裡的每個套件版本與 Packagist 的安全公告資料庫，列出有已知 CVE 的套件。

### 手動管理的依賴

沒有 Composer 的 legacy 專案可能直接把第三方程式碼複製進專案目錄。常見的高風險依賴：

| 依賴               | 常見位置                            | 檢查方式                                 |
| ------------------ | ----------------------------------- | ---------------------------------------- |
| PHPMailer          | `class.phpmailer.php`、`PHPMailer/` | 比對版本號與 GitHub releases 的安全公告  |
| jQuery             | `js/jquery.min.js`                  | 打開檔案看版本號、低於 3.5.0 有 XSS 漏洞 |
| CKEditor / TinyMCE | `editor/`、`tinymce/`               | 舊版有 XSS 漏洞、比對 CVE                |
| WordPress plugins  | `wp-content/plugins/`               | 用 WPScan 掃描                           |

### JavaScript CDN 引用

檢查 HTML 裡引用的外部 JavaScript CDN 連結，確認：使用 `integrity` 屬性（Subresource Integrity）防止 CDN 被竄改、引用的 CDN 是否仍在維護。

## 掃描工具

除了手動 grep，可以用工具做自動化掃描。這些工具都從本地或外部執行，不需要在 prod 伺服器上安裝任何東西。

| 工具                                | 類型            | 用途                                    | 費用                       |
| ----------------------------------- | --------------- | --------------------------------------- | -------------------------- |
| PHP_CodeSniffer + Security Standard | 靜態分析        | 掃描 PHP 程式碼的安全反模式             | 免費                       |
| PHPStan / Psalm                     | 靜態分析        | 型別檢查間接發現不安全的資料流          | 免費                       |
| WPScan                              | WordPress 專用  | 掃描 WordPress 核心、plugin、theme 漏洞 | 免費（API key 有額度限制） |
| Nikto                               | Web server 掃描 | 從外部掃描 HTTP server 的已知弱點       | 免費                       |
| Mozilla Observatory                 | 線上掃描        | 檢查 HTTP security header 設定          | 免費                       |
| Snyk                                | 依賴掃描        | 類似 `composer audit` 但涵蓋更廣        | 免費方案可用               |

WordPress 站台的掃描指令：

```bash
# WPScan 掃描（從本地執行、掃描遠端站台）
wpscan --url https://example.com --enumerate vp,vt,u
# vp = vulnerable plugins, vt = vulnerable themes, u = users
```

所有掃描結果存進 repo 的 `security-audit/` 目錄，標上日期。這份報告是後續修補計畫的輸入，也是向管理層說明安全狀態的依據。

## 跨分類引用

- → [共享主機與 FTP 環境的接管](/infra/takeover/legacy-ftp-shared-hosting/)：本文的前置步驟（程式碼與資料庫快照）
- → [資料庫備份與變更管理](/infra/takeover/legacy-database-backup-migration/)：SQL injection 修復前先備份，避免修補過程造成資料遺失
- → [無 SSH 環境的監控與告警](/infra/takeover/legacy-external-monitoring/)：安全事件的持續偵測與錯誤追蹤
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：credential 管理的系統性設計
- → [Backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：應用層安全的完整討論
