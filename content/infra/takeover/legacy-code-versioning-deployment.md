---
title: "程式碼版控與 FTP 部署紀律"
date: 2026-06-26
description: "共享主機 PHP 專案的程式碼怎麼從 FTP 拉回來建 Git repo、設定檔怎麼分離、FTP 部署怎麼建立可追蹤的流程、以及怎麼用 CI 取代手動上傳"
weight: 11
tags: ["infra", "takeover", "git", "ftp", "deployment", "php"]
---

共享主機上的 PHP 專案通常沒有版本歷史——程式碼直接透過 FTP 覆蓋伺服器上的檔案，每次上傳就是一次不可回溯的覆寫。接手這類專案時，第一步是在本地建立 Git repo 作為程式碼的唯一事實來源，第二步是把 FTP 上傳從「隨手改隨手傳」轉成有紀錄、可回退的部署流程。本篇聚焦在程式碼端的版控與部署；資料庫的備份與變更紀律見[資料庫備份與變更管理](/infra/takeover/legacy-database-backup-migration/)；帳號與存取的安全管理見[共享主機的安全管理](/infra/takeover/legacy-php-security-audit/)。

## 從 FTP 拉下來建立 Git repo

用 FTP client 把整個站台完整下載到本地目錄，這份下載就是 production 的快照。下載完成後在該目錄初始化 Git：

```bash
cd /path/to/downloaded-site
git init
```

在第一次 commit 之前先處理 `.gitignore`。PHP 專案需要排除的檔案分三類：套件依賴（由 Composer 或 npm 管理、可重建）、執行期產物（快取、session、上傳檔案）、以及含有機密值的設定檔。

```text
# 套件依賴
vendor/
node_modules/

# 執行期產物
cache/
tmp/
sessions/
*.log

# 使用者上傳內容（通常很大、且屬於資料不屬於程式碼）
uploads/
media/
wp-content/uploads/

# 機密設定（下一節處理）
.env
config.local.php
wp-config.php
```

使用者上傳的內容（`uploads/`、`media/`）不進 Git 的理由是它屬於資料層：檔案數量可能成千上萬、總容量可能數 GB，Git 不適合管理這類大量二進位檔案。這些檔案的備份策略跟程式碼不同——用 FTP mirror 或 rclone 定期同步到本地即可。

設好 `.gitignore` 後做第一次 commit：

```bash
git add -A
git commit -m "production snapshot $(date +%Y-%m-%d)"
```

這個 commit 就是「接手時 production 長什麼樣」的基準線。後續所有改動都從這裡開始有版本歷史。

## Config 分離：讓 Git repo 不含機密值

共享主機的 PHP 專案常把資料庫密碼、API key、SMTP 憑證直接寫在 `config.php` 或 `wp-config.php` 裡。這些檔案如果進了 Git，機密值就跟著 repo 走——推到 GitHub 就等於公開。

分離的模式是把設定拆成兩份：一份進 Git（結構與預設值）、一份不進 Git（實際機密值）。

### 模式一：.env 檔案

使用 `vlucas/phpdotenv` 套件或手動解析，讓程式碼從 `.env` 檔案讀取環境變數：

```php
// config.php — 進 Git
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();

$db_host = $_ENV['DB_HOST'];
$db_name = $_ENV['DB_NAME'];
$db_user = $_ENV['DB_USER'];
$db_pass = $_ENV['DB_PASS'];
```

```text
# .env — 不進 Git（.gitignore 已排除）
DB_HOST=localhost
DB_NAME=mysite_prod
DB_USER=mysite_user
DB_PASS=actual-password-here
```

同時在 repo 裡放一份 `.env.example`（進 Git），列出所有需要的環境變數但不填實際值：

```text
# .env.example — 進 Git，作為範本
DB_HOST=
DB_NAME=
DB_USER=
DB_PASS=
SMTP_HOST=
SMTP_USER=
SMTP_PASS=
```

### 模式二：config.local.php

如果專案不使用 Composer、引入 phpdotenv 成本太高，用 PHP include 分離：

```php
// config.php — 進 Git
if (file_exists(__DIR__ . '/config.local.php')) {
    require __DIR__ . '/config.local.php';
} else {
    die('config.local.php not found. Copy config.local.example.php and fill in values.');
}
```

```php
// config.local.php — 不進 Git
$db_host = 'localhost';
$db_name = 'mysite_prod';
$db_user = 'mysite_user';
$db_pass = 'actual-password-here';
```

### WordPress 的處理

WordPress 的 `wp-config.php` 同時包含機密值和非機密設定。把整份排除再 include 一份 local 版是最簡單的做法，但也可以只把機密值抽到 `.env`、`wp-config.php` 本身保留在 Git 裡：

```php
// wp-config.php — 進 Git（機密值從 .env 讀）
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();

define('DB_NAME', $_ENV['DB_NAME']);
define('DB_USER', $_ENV['DB_USER']);
define('DB_PASSWORD', $_ENV['DB_PASSWORD']);
define('DB_HOST', $_ENV['DB_HOST'] ?? 'localhost');
```

分離完成後，用 `grep` 確認 repo 裡沒有殘留的明文密碼：

```bash
git grep -in "password\|passwd\|secret\|api_key\|smtp" -- '*.php' ':!*.example*'
```

任何命中都要評估：是真的機密值（要移到 .env）還是變數名稱（可以保留）。

## FTP 部署的風險控制

FTP 上傳是逐檔覆寫，沒有交易性——上傳到一半斷線、或上傳了有語法錯誤的 PHP 檔案，站台會立刻出問題。風險控制的核心是「每次上傳前知道在改什麼、上傳後知道改了什麼」。

### 上傳前的比對

FileZilla 的目錄比較功能（「檢視 → 目錄比較 → 啟用」）可以在上傳前看到本地與遠端的差異：哪些檔案是本地較新、哪些是遠端較新、哪些只存在於一邊。上傳前先跑比較、確認差異清單符合預期——如果出現預期外的「遠端較新」檔案，代表有人在伺服器上直接改了東西，要先下載回來合併再上傳。

### 只上傳改過的檔案

一次上傳整個站台目錄既慢又危險。只上傳 Git diff 顯示的改動檔案：

```bash
# 列出相對於上次部署 tag 改了哪些檔案
git diff --name-only deploy-2026-06-25 HEAD
```

把這份清單對照 FileZilla 的比較結果，逐一上傳。量大時用 lftp 的 mirror 指令加 `--only-newer` flag 只傳新檔。

### 關鍵檔案的額外保護

`index.php`、`.htaccess`、設定檔這類檔案壞掉會讓整個站台無法存取。上傳這些檔案之前，先從伺服器下載一份當前版本存到本地的 `_backup/` 目錄（gitignored）。如果上傳後站台出問題，可以立刻把備份版本傳回去。

## 部署前後的驗證

### 部署前檢查

| 項目                   | 確認方式                            |
| ---------------------- | ----------------------------------- |
| 本地測試通過           | 在本地環境跑過改動的頁面 / 功能     |
| Git 已 commit          | `git status` 顯示 clean             |
| 要上傳的檔案清單已確認 | `git diff --name-only` 輸出符合預期 |
| 關鍵檔案已備份         | `_backup/` 有當前版本               |

### 部署後驗證

上傳完成後立刻驗證：

1. 首頁能正常載入（HTTP 200、頁面內容正確）
2. 本次改動涉及的功能可正常操作
3. 如果是電商站：結帳流程、金流 callback 測試
4. 檢查 PHP error log（cPanel → 錯誤日誌、或 FTP 下載 `error_log` 檔案）

如果驗證失敗，回退方式是從 Git 歷史取出上一個版本的受影響檔案重新上傳：

```bash
# 取出上一個部署 tag 的特定檔案
git show deploy-2026-06-25:path/to/file.php > _rollback/file.php
# 用 FTP 上傳 _rollback/file.php 覆蓋 prod
```

## CI 化 FTP 部署

手動 FTP 部署的問題是它依賴特定人的 FTP client 和操作紀律。用 GitHub Actions 把 FTP 上傳自動化，可以讓部署變成「push 到 main → CI 跑測試 → CI 上傳到伺服器」的流程，不依賴任何人的本地環境。

```yaml
name: Deploy via FTP
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - name: Deploy to FTP
        uses: SamKirkland/FTP-Deploy-Action@v4
        with:
          server: ${{ secrets.FTP_HOST }}
          username: ${{ secrets.FTP_USER }}
          password: ${{ secrets.FTP_PASS }}
          server-dir: /public_html/
          exclude: |
            **/.git*
            **/.git*/**
            **/node_modules/**
            **/.env
            **/config.local.php
```

FTP 憑證存在 GitHub repo 的 Secrets 裡（Settings → Secrets and variables → Actions），不寫在 workflow 檔案裡。

### CI 化後的改變

| 面向       | 手動 FTP                        | CI 化 FTP                                 |
| ---------- | ------------------------------- | ----------------------------------------- |
| 部署紀錄   | FTP client 的 log（通常不保留） | GitHub Actions 的 run history（永久保留） |
| 部署觸發   | 某人手動操作                    | push 到 main 自動觸發                     |
| 上傳前測試 | 依賴個人紀律                    | CI 可加 lint / test step                  |
| 多人協作   | 需要共用 FTP 帳密               | 帳密在 GitHub Secrets、workflow 共用      |

### 限制

FTP 部署沒有原子性（atomic deployment）——檔案逐一上傳的過程中，伺服器上同時存在新舊版本的檔案混合狀態。如果上傳的檔案之間有依賴關係（新的 A.php 引用新的 B.php，但 B.php 還沒上傳完），短暫的錯誤窗口無法避免。流量高的站台如果需要零停機部署，需要升級到 SSH + symlink 切換的部署方式，那屬於 VPS 遷移之後的能力。

## Git tagging 部署紀錄

每次部署前在 Git 打一個 tag，讓「這次部署的是哪個版本」有明確的錨點：

```bash
git tag deploy-$(date +%Y-%m-%d-%H%M)
git push origin --tags
```

tag 的命名用日期時間戳而非版號，因為這類專案通常沒有語意化版號的概念。tag 的作用是：

- 回退時知道要退到哪個版本（`git diff deploy-previous deploy-current` 看這次改了什麼）
- 多次部署之間的差異可追蹤
- CI 化後可以用 tag 觸發部署而非每次 push 都部署

資料庫變更的回退跟程式碼獨立處理——程式碼可以靠 Git 回退，資料庫要靠 SQL dump 回退，兩者的回退點要對齊但機制不同。資料庫的備份策略見[資料庫備份與變更管理](/infra/takeover/legacy-database-backup-migration/)。

## 跨分類引用

- → [共享主機與 FTP 環境的接管](/infra/takeover/legacy-ftp-shared-hosting/)：本篇的母文章，涵蓋接手的完整流程
- → [資料庫備份與變更管理](/infra/takeover/legacy-database-backup-migration/)：資料庫端的備份、migration 紀律與回退策略
- → [共享主機的安全管理](/infra/takeover/legacy-php-security-audit/)：credential 分離之後的存取控制與安全掃描
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：從 FTP CI 化進一步演進到完整的 PR review 流程
