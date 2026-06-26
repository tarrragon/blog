---
title: "Runtime 版本升級"
date: 2026-06-26
description: "PHP / Node.js / Python 大版本升級的相容性評估、本地驗證、分批部署策略與常見陷阱"
weight: 2
tags: ["infra", "upgrade", "php", "runtime", "node", "python"]
---

Runtime 版本升級改變的是既有程式碼的執行環境。程式碼是針對某個版本的行為寫的——函式存不存在、預設值是什麼、型別檢查嚴不嚴格——新版本可能移除函式、改變預設行為、引入更嚴格的型別系統。升級的工作量不在「切換版本」這個動作本身（多數環境只需要改一個設定），而在「讓既有程式碼在新版本下行為正確」的驗證與修正。

本篇以 PHP 為主要範例（legacy 升級最常見的情境），Node.js 和 Python 的對應工具在各段併列。

## 相容性評估

升級前要先知道「現有程式碼跟新版本有多少不相容」。不相容的類型分四種：

| 類型           | 範例（PHP 7→8）                                         | 影響                     |
| -------------- | ------------------------------------------------------- | ------------------------ |
| 移除的函式     | `each()`、`create_function()`、`mysql_*` 系列           | 呼叫直接 fatal error     |
| 改變的預設行為 | `error_reporting` 預設含 `E_DEPRECATED`、字串比較更嚴格 | 行為靜默改變、不一定報錯 |
| 更嚴格的型別   | 內部函式的參數型別檢查從警告升級為 TypeError            | 之前能跑的呼叫現在拋例外 |
| 擴充模組可用性 | `json` 從可選變內建、`mcrypt` 已移除                    | 部分功能無法使用         |

### PHP 相容性掃描

PHPCompatibility 是 PHP_CodeSniffer 的規則集，可以自動掃描程式碼裡哪些寫法在目標版本不相容：

```bash
# 安裝
composer global require phpcompatibility/php-compatibility

# 掃描：目標版本 8.0
phpcs --standard=PHPCompatibility \
  --runtime-set testVersion 8.0 \
  --extensions=php \
  -p \
  src/
```

掃描結果會列出每一處不相容的位置、原因和嚴重度。常見的命中包括：

```text
FILE: src/legacy/Database.php
----------------------------------------------------------------------
FOUND 3 ERRORS:
 42 | ERROR | Function mysql_connect() is removed since PHP 7.0
 89 | ERROR | Function each() is removed since PHP 8.0
156 | ERROR | Curly brace access syntax is deprecated since PHP 7.4
----------------------------------------------------------------------
```

`php -l` 可以做基本的語法檢查，但它只抓語法錯誤、抓不到 deprecated 函式和行為變更。PHPCompatibility 掃描的覆蓋面更廣。

### PHP 升級的高頻修改項

| 項目       | PHP 5.6→7.x                        | PHP 7.x→8.x                     |
| ---------- | ---------------------------------- | ------------------------------- |
| 資料庫連線 | `mysql_*` → `mysqli_*` 或 PDO      | —                               |
| 陣列遍歷   | —                                  | `each()` → `foreach`            |
| 字串存取   | —                                  | `$str{0}` → `$str[0]`           |
| 錯誤處理   | `set_error_handler` 行為變更       | 內部函式 TypeError 取代 warning |
| 建構函式   | 同名建構函式 deprecated            | 同名建構函式 removed            |
| 正則表達式 | `ereg_*` → `preg_*`                | —                               |
| 加密       | `mcrypt_*` → `openssl_*` 或 sodium | —                               |

### Node.js 相容性掃描

```bash
# 用 nvm 切換版本後跑測試
nvm install 20
nvm use 20
npm test

# 檢查 package.json 的 engines 欄位
cat package.json | jq '.engines'
```

Node.js 的 breaking change 集中在 V8 引擎行為（`Buffer` 建構式、`fs` 的 callback 簽章）和原生模組的 ABI 相容性。如果專案用了原生模組（`node-gyp` 編譯的），版本升級後要重新 `npm rebuild`。

### Python 相容性掃描

```bash
# Python 2→3：用 2to3 掃描
2to3 --no-diffs -w src/

# Python 3.x 小版本：用 pyupgrade
pip install pyupgrade
pyupgrade --py310-plus src/**/*.py
```

Python 2→3 的修改量通常很大（print 語法、unicode 處理、dict 方法），是接近重寫等級的升級。Python 3.x 之間的升級相對溫和，主要是 deprecation 移除和 typing 語法的演進。

## 本地驗證

相容性掃描找出的是靜態分析能偵測的不相容。執行期的行為變更（如字串比較規則改變、排序穩定性改變）只有跑起來才看得到。

### 建立目標版本的本地環境

用 Docker 建一個精確匹配目標版本的環境：

```yaml
services:
  app:
    image: php:8.2-apache
    volumes:
      - ./src:/var/www/html
    ports:
      - "8080:80"
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: localdev
      MYSQL_DATABASE: app
```

如果不用 Docker，MAMP Pro 或 Laragon 可以切換 PHP 版本。關鍵是本地環境的 runtime 版本要跟升級目標完全一致——PHP 8.0 跟 8.2 之間也有差異。

### 驗證策略

有測試套件的專案跑測試套件。沒有測試套件的專案（legacy 專案的常態）按照這個優先序手動驗證：

1. **首頁能載入**：最基本的 smoke test，確認 PHP 不 fatal error
2. **登入流程**：session 處理是版本升級最常出問題的區域
3. **資料庫操作**：CRUD 的每一種至少各跑一次
4. **金流 / 第三方 API**：callback URL 和 API 呼叫是否正常
5. **表單提交**：file upload、驗證邏輯

PHP 升級時把 `error_reporting` 開到最大：

```php
// 開發環境設定（不要在 prod 開）
error_reporting(E_ALL);
ini_set('display_errors', '1');
```

所有 notice、warning、deprecation 都要修——它們在下一個版本可能升級為 error。

### 第三方依賴相容性

```bash
# Composer：檢查哪些套件需要更新
composer outdated

# 檢查各套件是否支援目標 PHP 版本
composer why-not php 8.2
```

`composer why-not` 會列出哪些套件的 `require.php` 限制不允許目標版本。這些套件要先升級到支援新版本的版號，才能升 PHP。

如果某個套件已經不再維護且不支援新 PHP 版本，要評估替代方案或 fork 修改。這個評估的工作量可能佔整個升級的大部分時間。

## 分批部署策略

### 有獨立環境控制的情境（VPS / 雲端）

最安全的策略是建一套平行環境跑新版本：

1. 用新 PHP 版本建一台新的 VM 或容器
2. 部署相同的程式碼
3. 匯入 prod 資料庫的副本
4. 在新環境跑完整驗證
5. DNS 或 load balancer 切換流量到新環境
6. 舊環境保留一段時間作為 rollback 目標

rollback 是把流量切回舊環境。舊環境在確認新環境穩定之前不要關——保留期至少一週。

### 共享主機的情境

共享主機的 PHP 版本切換通常是 per-domain 的設定：

- **cPanel**：MultiPHP Manager，選域名 → 選 PHP 版本 → Apply
- **Plesk**：PHP Settings → PHP version 下拉選單

切換是即時生效的，rollback 也是即時的（選回舊版本）。但沒有「平行環境驗證」的能力——除非主機商提供 staging subdomain 可以先測。

共享主機的升級策略：

1. 如果有 staging subdomain：先在 staging 切換版本、驗證、再切 prod
2. 如果沒有：選流量最低的時段切換（如凌晨），切換後立刻驗證關鍵流程，出問題立刻切回
3. 切換前備份（FTP mirror + DB dump），確認 rollback 路徑存在

### WordPress / 框架的版本矩陣

WordPress 和主流框架有明確的 PHP 版本支援矩陣。升級 PHP 前要先確認框架版本是否支援目標 PHP 版本：

| 框架      | 查詢方式                                                 |
| --------- | -------------------------------------------------------- |
| WordPress | [官方需求頁](https://wordpress.org/about/requirements/)  |
| Laravel   | 各版本 `composer.json` 的 `require.php`                  |
| Symfony   | [Release and support](https://symfony.com/releases) 頁面 |

如果框架不支援目標 PHP 版本，要先升級框架。框架升級和 PHP 升級不要同時做——先升框架、驗證穩定、再升 PHP，每一步都有獨立的 rollback 點。

## 常見的升級陷阱

### Session 序列化格式

PHP 的 session 序列化格式在某些版本之間有變更。版本切換後舊 session 檔案可能無法反序列化，使用者會被強制登出。處理方式：

- 在維護窗口切換版本（使用者預期重新登入）
- 或在切換前清除所有 session 檔案

### opcache 快取

PHP 的 opcache 會快取編譯後的 bytecode。版本切換後如果 opcache 沒清，可能用舊版本編譯的 bytecode 跑在新版本上。切換後的第一件事：

```bash
# CLI 方式清除（如果有 SSH）
php -r "opcache_reset();"

# 或重啟 PHP-FPM / Apache
systemctl restart php8.2-fpm
```

### Composer 的 PHP 版本鎖定

`composer.lock` 裡的套件版本是根據當時的 PHP 版本解析的。PHP 版本變了之後，要重新 `composer update` 讓 Composer 用新版本重新解析依賴。但 `composer update` 可能升級其他套件——較安全的做法是 `composer update --lock` 只更新 lock file 的 metadata、不升級套件版本。

### 隱性的行為變更

PHP 8.0 起，字串跟數字的比較規則改了（`0 == "foo"` 從 `true` 變 `false`）。這類變更不會報錯、不會拋例外，程式碼照跑但行為不同。靜態分析抓不到，只有業務邏輯測試能覆蓋。

如果沒有測試套件，至少在切換後的一週內密切監控錯誤日誌和業務指標（訂單數、登入數、API 錯誤率），用業務指標的異常作為行為變更的偵測手段。

## 時程與管理層溝通

| 升級類型                | 典型時程 | 主要成本來源              |
| ----------------------- | -------- | ------------------------- |
| PHP 小版本（8.0→8.2）   | 2-5 天   | 依賴更新 + 測試           |
| PHP 跨大版本（7.4→8.x） | 1-2 週   | 函式替換 + 行為驗證       |
| PHP 跳代（5.6→8.x）     | 4-8 週   | 大量程式碼修改 + 框架升級 |
| Node.js 大版本          | 3-5 天   | 原生模組重編 + API 變更   |
| Python 2→3              | 8-16 週  | 接近重寫等級              |

向管理層溝通時要說明：「升級 runtime 版本不只是在伺服器改一個設定。程式碼裡用到的函式和行為在新版本有不同的定義，需要逐一修改和驗證。時程取決於程式碼用了多少舊版本的專屬功能。」

成本參考：PHP 版本升級本身的工具和環境不花錢（PHPCompatibility 開源、Docker 免費、cPanel 版本切換內建）。成本全在工程師時間。

## 跨分類引用

- → [升級的共通操作框架](/infra/upgrade/upgrade-framework/)：四階段模型（評估 → 平行環境 → 切換 → 退役）
- → [Legacy PHP 的安全盤點](/infra/takeover/legacy-php-security-audit/)：PHP 版本風險評估與漏洞掃描
- → [程式碼版控與 FTP 部署紀律](/infra/takeover/legacy-code-versioning-deployment/)：升級前的 Git 基準線與 rollback 策略
