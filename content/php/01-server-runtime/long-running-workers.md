---
title: "常駐 worker 模型：FrankenPHP worker 模式、Laravel Octane 與跨請求殘留的狀態"
date: 2026-10-05
description: "說明讓 PHP 應用程式只啟動一次、在記憶體裡連續處理請求的常駐 worker 模型：它省下的是每個請求重新啟動框架的成本，失去的是 shared-nothing 的隔離；以 FrankenPHP 的 worker 模式與 Laravel Octane 實測靜態屬性跨請求累積、記憶體隨請求數線性增長與 max-requests 重啟，以及寫給這個模型的程式要避開的寫法"
weight: 8
tags: ["php", "frankenphp", "octane", "swoole", "roadrunner", "deployment"]
---

這篇說明常駐 worker 模型：應用程式在 worker 啟動時載入一次，之後同一份記憶體裡的應用程式連續處理很多個請求。用 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/) 那組問題來看，它換掉的是第三個答案：應用程式的狀態不再只活一個請求。文中的行為取自 FrankenPHP 1.13（PHP 8.5.11）與 Laravel Octane 2.20（Laravel 13）。

## 常駐 worker 省下的是哪一段成本

[PHP-FPM](/php/01-server-runtime/php-fpm/) 的 worker 常駐，[OPcache](/php/01-server-runtime/opcache/) 讓每個檔案只編譯一次，可是框架的啟動流程每個請求仍然要跑一次：建立服務容器、執行每個服務提供者的註冊、讀設定、建立路由表。這段流程的成本由框架的規模決定，跟請求要做什麼無關，是 [shared-nothing](/php/knowledge-cards/shared-nothing-request/) 的直接代價——每個請求都從空白開始，就得每個請求都重新建立一次應用程式。

常駐 worker 模型把這段流程移到 worker 啟動時：應用程式啟動一次之後留在記憶體裡，每個請求進來只執行「處理這個請求」那一段。Laravel Octane 的文件把這件事寫成一句話：Octane boots your application once, keeps it in memory, and then feeds it requests。

這個模型要求執行 PHP 的程序或執行緒有能力在請求之間不清空狀態，所以它需要特定的伺服器，PHP-FPM 做不到（它在每個請求結束時一定清空）。Octane 支援的伺服器有 FrankenPHP、Swoole、Open Swoole 與 RoadRunner：

| 伺服器     | 寫成什麼         | 怎麼讓 PHP 常駐                                                              |
| ---------- | ---------------- | ---------------------------------------------------------------------------- |
| FrankenPHP | Go（嵌入 Caddy） | PHP 嵌在 Go 程式裡，worker 是執行緒                                          |
| RoadRunner | Go               | Go 程式管理一群常駐的 PHP 程序，預設用標準管道（goridge 協定）交換請求與回應 |
| Swoole     | PHP 的 C 擴充    | PHP 程序自己開伺服器、處理事件迴圈與協程                                     |

## FrankenPHP 的兩種模式

FrankenPHP 是一個講 HTTP 的 web 伺服器，PHP 嵌在它的程序裡（SAPI 名稱是 `frankenphp`），所以它不需要前面再接一個 Nginx。它有兩種模式，差別正好就是狀態壽命。

**傳統模式**：每個請求執行一次 PHP 腳本，執行完清空狀態，跟 PHP-FPM 一樣是 shared-nothing。同一支計數腳本（腳本內容見 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/#一個請求在-php-裡經過的階段)）請求三次：

```text
pid=1 static=1 global=1 sapi=frankenphp
pid=1 static=1 global=1 sapi=frankenphp
pid=1 static=1 global=1 sapi=frankenphp
```

PID 一直是 1，因為 FrankenPHP 只有一個程序，PHP 在它的執行緒裡跑（這個 PHP 是以執行緒安全編譯的，`Thread Safety => enabled`，見 [ZTS](/php/knowledge-cards/zts/)）。計數器每次都是 1。

**worker 模式**：一支 worker 腳本啟動一次，在一個迴圈裡反覆呼叫 `frankenphp_handle_request()`，每呼叫一次處理一個請求：

```php
<?php
// 這段只在 worker 啟動時執行一次：模擬框架啟動
$bootedAt = microtime(true);
$requestLog = [];

$handler = static function () use ($bootedAt, &$requestLog) {
    static $count = 0;
    $count++;
    $requestLog[] = $_SERVER['REQUEST_URI'];
    echo "static=", $count, " log_entries=", count($requestLog),
         " booted=", round($bootedAt, 3), "\n";
};

// 每次迴圈處理一個請求；伺服器要這個 worker 結束時回傳 false
while (frankenphp_handle_request($handler)) {
    gc_collect_cycles();
}
```

連續請求四次：

```text
static=1 log_entries=1 booted=1791203186.703
static=2 log_entries=2 booted=1791203186.703
static=3 log_entries=3 booted=1791203186.703
static=4 log_entries=4 booted=1791203186.703
```

`booted` 的時間戳四次都一樣，證明迴圈前的那段只跑了一次；`static` 與 `$requestLog` 一路累加，證明前一個請求留下的變數被下一個請求看到了。FrankenPHP 的文件對此寫得很直接：Static variables, class static properties, global variables, and in-memory caches all persist across requests。

## Laravel Octane：框架層的常駐 worker

自己寫 worker 迴圈要處理的事情很多：每個請求之間重設框架的哪些物件、例外怎麼處理、什麼時候重啟 worker。Laravel Octane 是 Laravel 官方的套件，把這些包好，讓既有的 Laravel 應用程式跑在上面那幾種伺服器上，用 `php artisan octane:frankenphp`（或 `octane:swoole`、`octane:roadrunner`）啟動。

Octane 會在每個請求之間重設 Laravel 自己的請求相關狀態，但應用程式程式碼留下的狀態它管不到。在 Laravel 骨架加一條路由，用一個類別的靜態屬性計數，並在每個請求往一個靜態陣列塞 100 KB 的資料——模擬把查詢結果或 log 暫存在靜態屬性裡這種在 PHP-FPM 下無害的寫法：

```php
Route::get('/state', function () {
    RequestLog::$count++;
    RequestLog::$entries[] = str_repeat('x', 100 * 1024);
    return ['count' => RequestLog::$count,
            'php_mem_mb' => round(memory_get_usage() / 1048576, 1)];
});
```

在 Octane 加 FrankenPHP、一個 worker、`--max-requests=500` 下連續請求：

```text
request #1   -> count=1   php_mem=5.6MB
request #100 -> count=100 php_mem=15.8MB
request #200 -> count=200 php_mem=26.1MB
request #400 -> count=400 php_mem=46.5MB
request #499 -> count=499 php_mem=56.6MB
request #500 -> count=1   php_mem=1.2MB    # 處理滿 500 個請求，worker 重啟
request #600 -> count=101 php_mem=11.5MB
```

同一段程式碼在 PHP-FPM 下，`count` 永遠是 1、記憶體在請求結束時全部釋放。在常駐 worker 下它變成兩個問題：

- **狀態洩漏到下一個請求**：`count` 一路累加。換成「目前登入的使用者」「這個請求的語系」這類資料，就是前一個使用者的資料被下一個使用者看到。
- **記憶體隨請求數線性增長**：每個請求多 0.1 MB，`max-requests` 到了 worker 重啟才歸零。Octane 的文件寫明它預設在 worker 處理滿 500 個請求後 gracefully restart，理由正是 to help prevent stray memory leaks，並舉了同一個例子：adding data to a statically maintained array will result in a memory leak。

這裡的記憶體增長跟 [PHP-FPM 那篇〈max_requests〉一節](/php/01-server-runtime/php-fpm/#max_requests定期換掉-worker-以控制記憶體) 量到的不同。PHP-FPM 下 PHP 程式碼建立的記憶體每個請求都會釋放，worker 的記憶體反映最近一次請求的峰值；常駐 worker 下，靜態屬性裡的資料不會被釋放，記憶體跟著累計的請求數往上長。`max-requests` 在兩個模型下都存在，防的記憶體成長不一樣。在常駐 worker 下，它的值是兩個成本的取捨：設得低，洩漏累積到的上限低，代價是 worker 重啟頻繁、每次重啟都要重新啟動一次框架；設得高，重啟少，代價是洩漏能長到的量大。先用上面那種逐請求記錄記憶體的方式量出每個請求漲多少，再依可接受的記憶體上限回推。

worker 是程序還是執行緒，也決定一個 worker 崩潰時影響多大。RoadRunner 的 worker 是各自獨立的 PHP 程序，一個因為擴充的錯誤而 segfault 時只有它自己結束；FrankenPHP 與 Swoole 的 worker 跑在同一個程序裡，程序層級的崩潰會連同其他 worker 一起帶走。

FrankenPHP 的 worker 是執行緒，所以重啟時 PID 不變（這次實測一直是同一個 PID），換掉的是執行緒裡的 PHP 狀態。看 PID 判斷 worker 有沒有重啟，在這個伺服器上不成立。

## 寫給常駐 worker 的程式要避開的寫法

Octane 的文件列出的幾類問題，根源都是「物件比請求活得久」：

- **靜態屬性與全域變數存放請求的資料**：上面那個例子。請求的資料放在請求範圍的物件裡，或在請求結束時清掉。
- **把服務容器或請求物件注入到長壽物件的建構子**：Octane 文件的原文是 that object may have a stale version of the container or request on subsequent requests——一個 singleton 在第一個請求時拿到了那個請求的 `Request`，之後的請求它手上一直是第一個請求的版本。
- **在 singleton 裡快取會變的值**：設定、目前的使用者、語系，在 PHP-FPM 下每個請求都重新算，在常駐 worker 下只算一次。

既有的 Laravel 應用程式搬上 Octane 之前，要把程式碼與用到的套件逐一檢查過這幾類寫法；套件作者沒有考慮常駐 worker 的話，問題會出在套件裡，而它們在 PHP-FPM 下從來不會顯現。

## 速度差多少要在自己的應用程式上量

常駐 worker 省下的是框架的啟動流程，所以省下多少由框架啟動流程佔每個請求多少時間決定。在 Laravel 13 骨架的 `/healthz` 上，同一時段各循序送 300 個請求：

| 執行方式                                       | 中位數  | p95     |
| ---------------------------------------------- | ------- | ------- |
| PHP-FPM（容器內 Nginx 加 php-fpm，開 OPcache） | 3.20 ms | 7.57 ms |
| Octane 加 FrankenPHP worker                    | 2.43 ms | 4.07 ms |

兩者的中位數只差不到一毫秒，而這個差距還包含 PHP-FPM 那一側多經過的容器內 Nginx 一跳，所以兩邊不完全對等。量測對象是一個幾乎沒有服務提供者的空骨架，框架啟動流程本來就短，開了 OPcache 之後能省的不多。正式專案的服務提供者、套件與設定檔越多，啟動流程越長，常駐 worker 省下的越多。所以這組數字只說明量測的方式，不說明手上的專案會差多少：在自己的應用程式、自己的主要請求上量一次，才知道省下的時間值不值得上一節那些改寫與檢查的成本。

## 常駐 worker 在執行模型裡的位置

這一系列的執行模型可以排成一條線，每一步讓程序或應用程式狀態活得更久：[CGI](/php/01-server-runtime/cgi/) 的程序與狀態都只活一個請求；[mod_php](/php/01-server-runtime/mod-php/) 與 [PHP-FPM](/php/01-server-runtime/php-fpm/) 讓程序活過很多請求，[OPcache](/php/01-server-runtime/opcache/) 因此有編譯結果可以重用；常駐 worker 讓應用程式的狀態也活過很多請求。

每往前一步，省下一段每個請求都要重付的成本，也失去一層隔離：CGI 的程序隔離讓一個請求的錯誤隨程序消失；shared-nothing 讓一個請求的資料不會被下一個請求看到。常駐 worker 走到最後一步，代價是這兩層隔離的責任從執行環境移到了程式碼身上——PHP-FPM 替程式清空的那些狀態，現在要程式自己不留下來。
