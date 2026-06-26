---
title: "無 SSH 環境的監控與告警"
date: 2026-06-26
description: "無 SSH 環境沒辦法裝 agent、沒辦法串 log pipeline，用外部 HTTP check、錯誤追蹤服務與效能基線建立最低成本的監控能力"
weight: 13
tags: ["infra", "takeover", "monitoring", "uptime", "php"]
---

無 SSH 的環境通常不允許安裝監控 agent（Datadog agent、New Relic APM daemon 都需要 daemon 常駐或 root 權限），伺服器的內部指標（CPU、記憶體、磁碟）只能從主機商的控制面板看到靜態數值，沒有告警機制。這種環境的監控策略是從外部觀測——用 HTTP check 確認服務存活、用不需要 agent 的錯誤追蹤服務捕捉例外、用定期量測建立效能基線。每一層都不依賴 server 端安裝任何東西。

## 可用性監控（外部 HTTP check）

外部 HTTP check 的運作方式是從第三方伺服器定期對目標 URL 發 HTTP 請求，驗證回應狀態碼、回應時間、以及頁面內容是否包含預期的文字。服務掛了或回應異常時觸發告警。

### 工具選型

| 工具         | 免費方案             | 檢查間隔 | 特色                               |
| ------------ | -------------------- | -------- | ---------------------------------- |
| UptimeRobot  | 50 個 monitor        | 5 分鐘   | 設定簡單、API 可整合               |
| Better Stack | 10 個 monitor        | 3 分鐘   | 含 incident 管理與 status page     |
| Pingdom      | 1 個 monitor（試用） | 1 分鐘   | Synthetic monitoring、付費功能完整 |

UptimeRobot 的免費方案對多數無 SSH 環境的站台足夠——50 個 monitor 可以覆蓋一個站台的主要入口。

### 該監控哪些 URL

選監控目標的判準是「這個 URL 掛了代表哪一層出問題」：

| URL                  | 驗證的層次       | 掛了代表什麼                 |
| -------------------- | ---------------- | ---------------------------- |
| 首頁                 | web server 存活  | Apache/Nginx 或 PHP 本身掛了 |
| 登入頁               | 應用框架正常運作 | PHP session 或框架初始化失敗 |
| 一個資料庫相依的頁面 | DB 連線存活      | MySQL 掛了或連線數滿了       |
| 金流 callback URL    | 第三方服務可達   | 付款回調會失敗、訂單狀態卡住 |

每個 monitor 設兩層閾值：回應時間 >3 秒為警告（效能劣化的早期訊號）、>10 秒或非 200 狀態碼為嚴重（服務已不可用）。

### 告警通道

免費方案通常支援 email 與 webhook（可串 Slack）。付費方案加 SMS 和電話。接手初期用 email + Slack 即可，等確認告警不會誤報後再決定要不要升級到 SMS。頻繁誤報會讓團隊學會忽略通知——閾值要設在「真的有問題才響」的水位。

## 錯誤追蹤（不需要 server agent）

PHP 的錯誤追蹤在無 SSH 環境有兩條路徑：server 端用 PHP 內建的 error_log、client 端用不需要安裝的 SaaS 服務。

### PHP error_log（server 端、不需 SSH）

PHP 可以把錯誤寫進檔案，設定方式是在 `.htaccess` 或 `php.ini`（如果主機允許）加入：

```apache
# .htaccess — 啟用錯誤記錄、關閉畫面顯示
php_flag display_errors off
php_flag log_errors on
php_value error_log /home/user/logs/php_errors.log
```

`error_log` 的路徑要指向 web root 之外的目錄，避免錯誤訊息被外部存取。設定後透過 FTP 定期下載這個檔案、用 grep 篩選嚴重等級：

```bash
# 篩選 Fatal 和 Warning（過濾掉 Notice / Deprecated）
grep -E "Fatal|Warning" php_errors.log | tail -50
```

### Sentry（PHP + JavaScript、不需 server agent）

Sentry 的 PHP SDK 不需要系統層 agent，只需要在應用程式碼裡初始化：

```bash
composer require sentry/sentry
```

```php
// 在應用程式進入點（如 index.php 最前面）加入
\Sentry\init([
    'dsn' => 'https://examplekey@o0.ingest.sentry.io/0',
    'traces_sample_rate' => 0.1,
]);
```

這段程式碼會在 PHP 拋出未捕捉的例外或觸發 error 時，把錯誤資訊（stack trace、request context、使用者資訊）透過 HTTP 送到 Sentry 的 SaaS 平台。免費方案每月 5,000 個事件，對流量不大的流量不大的站台通常足夠。

前端的 JavaScript 錯誤追蹤更簡單——在 HTML 的 `<head>` 加一行 Sentry 的 CDN script，不需要修改 server 設定：

```html
<script
  src="https://browser.sentry-cdn.com/8.x/bundle.tracing.min.js"
  crossorigin="anonymous"
></script>
<script>
  Sentry.init({ dsn: "https://examplekey@o0.ingest.sentry.io/0" });
</script>
```

JavaScript SDK 捕捉的是瀏覽器端的錯誤——DOM 操作失敗、AJAX 請求異常、未處理的 Promise rejection。跟 PHP 端的 SDK 各抓不同層的問題。

### error_log vs Sentry 的分工

error_log 是 server 端的文字紀錄，需要手動下載和篩選；Sentry 有搜尋、聚合、告警和 stack trace 視覺化。兩者互補：error_log 保留完整紀錄作為備份、Sentry 提供可操作的告警和分析介面。error_log 在 PHP 嚴重到 Sentry SDK 自己也掛掉的情況下仍然有紀錄。

## 效能基線

效能基線的責任是回答「正常狀態下回應時間是多少」，讓異常浮現時有比對的參考。沒有基線時，回應時間從 200ms 劣化到 2 秒、但因為「好像一直都這麼慢」而沒人察覺。

### 量測方式

最簡單的量測是從本機或 CI 環境定期 curl：

```bash
# 量測回應時間（秒），只看 time_total
curl -o /dev/null -s -w "%{time_total}\n" https://example.com
```

把這段做成 GitHub Actions 的 scheduled workflow，每小時跑一次、把結果追加到 repo 的 CSV 檔案，就有了一條回應時間的趨勢線：

```yaml
on:
  schedule:
    - cron: '0 * * * *'
jobs:
  perf-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          TIME=$(curl -o /dev/null -s -w "%{time_total}" https://example.com)
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),$TIME" >> perf-log.csv
      - run: git add perf-log.csv && git commit -m "perf check" && git push
```

這條趨勢線本身就是監控：回應時間連續幾個小時上升，代表某個東西在劣化（DB 查詢變慢、磁碟快滿、PHP process 卡住）。

### 頁面效能

Google PageSpeed Insights（免費、不需安裝）分析前端載入效能，包含 LCP、CLS、FID 等 Core Web Vitals。對 legacy PHP 站台有用的是它會指出渲染阻塞的 CSS/JS、未壓縮的圖片、缺少快取 header 這類不需要動後端就能改善的問題。

### 資料庫效能（需改 code）

如果能修改 PHP 程式碼，在資料庫查詢前後加計時、超過閾值就寫 error_log：

```php
$start = microtime(true);
$result = $pdo->query($sql);
$elapsed = microtime(true) - $start;
if ($elapsed > 1.0) {
    error_log(sprintf("Slow query (%.2fs): %s", $elapsed, substr($sql, 0, 200)));
}
```

累積一段時間後，從 error_log 裡 grep `Slow query` 就能看出哪些查詢是效能瓶頸。這不是完整的 APM，但在沒有 agent 的環境裡是最接近 slow query log 的替代方案。

## 帳單與流量異常偵測

這類主機通常按流量或磁碟空間計費，異常流量（bot 掃描、DDoS、爬蟲）會讓帳單飆高或觸發主機商的流量限制。

### 流量監控

主機控制面板（cPanel 的 AWStats 或 Webalizer）提供基本的流量分析——top referrer、top page、bot 流量佔比。每月檢查一次，重點看：

- bot 流量佔比是否異常高（>50% 通常代表有爬蟲）
- 單一 IP 的請求量是否異常集中
- 帶寬使用量的趨勢（月增超過 20% 且沒有對應的業務成長要查原因）

### 客戶端分析（不需 server 安裝）

Google Analytics 或 Plausible（隱私友善替代品）只需要在頁面加一段 JavaScript。它們追蹤的是真實使用者的瀏覽行為（page view、session、referrer），跟 server 端的 access log 互補：server log 看所有請求（含 bot），GA/Plausible 只看真實瀏覽器。

### Cloudflare 免費方案

如果 DNS 可以切換，把 domain 接上 Cloudflare（免費方案）提供三個能力而不需要動 server：

- **流量分析**：比 AWStats 更即時、有地理分佈和 bot 過濾
- **DDoS 保護**：基本的 Layer 3/4 防護免費
- **CDN 快取**：靜態資源（CSS/JS/圖片）由 Cloudflare 快取、減輕 origin 負擔

設定只需要把 domain 的 nameserver 改成 Cloudflare 提供的 NS、原始 DNS record 在 Cloudflare 重建。對無 SSH 環境的站台來說這是投資報酬率最高的單一改善動作——不動 server、不改 code、但同時拿到流量可見性和基本防護。

## 整合成最低成本監控方案

按投入程度分三層，每一層都包含上一層：

| 層級               | 組成                                                | 月費   | 覆蓋                            |
| ------------------ | --------------------------------------------------- | ------ | ------------------------------- |
| Tier 1（零成本）   | UptimeRobot free + Sentry free + Google Analytics   | $0     | 可用性 + 錯誤追蹤 + 流量        |
| Tier 2（最低付費） | +Better Stack ($19/mo) + Cloudflare free            | ~$19   | +incident 管理 + 流量分析 + CDN |
| Tier 3（升級路徑） | 遷移到 VPS → 安裝 APM agent → 對齊模組六的 IaC 監控 | 依 VPS | 完整 server 端可觀測性          |

Tier 1 在接手當天就能建好（30 分鐘設定 UptimeRobot + Sentry + GA），零成本提供基本的「服務掛了會知道、程式碼出錯會收到、流量異常看得到」的覆蓋。Tier 2 適合站台有營收或合約 SLA 要求時。Tier 3 是離開無 SSH 環境後的正規化路徑，監控從外部觀測升級為 server 端全面可觀測性，見[模組六：可觀測性與 log](/infra/06-observability-logging/)。

## 跨分類引用

- → [無 SSH 的 FTP / 面板管理環境接管](/infra/takeover/legacy-ftp-no-ssh/)：本篇的母篇，監控建立在盤點與本地環境之後
- → [程式碼版控與 FTP 部署紀律](/infra/takeover/legacy-code-versioning-deployment/)：部署後的驗證用監控確認服務正常
- → [Legacy PHP 的安全盤點](/infra/takeover/legacy-php-security-audit/)：錯誤追蹤可能暴露安全問題（未捕捉的 SQL error、路徑洩漏）
- → [模組六：可觀測性與 log](/infra/06-observability-logging/)：Tier 3 升級路徑的目標——有 server 存取後的 IaC 監控
- → [Monitoring 監控體系](/monitoring/)：客戶端行為訊號（SDK / Collector）的完整討論
