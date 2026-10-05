---
title: "mod_php：PHP 直譯器嵌進 Apache 程序的執行模型"
date: 2026-10-05
description: "說明 mod_php 怎麼把 PHP 直譯器載入 Apache 的每個子程序：為什麼它要搭配 prefork MPM、每個子程序都帶著 PHP 對記憶體與並發的影響、所有站台共用 Apache 的執行帳號、php.ini 與 .htaccess 的設定方式，以及從 mod_php 搬到 PHP-FPM 時 .htaccess 的 php_value 與 .user.ini 的差異"
weight: 3
tags: ["php", "apache", "mod_php", "deployment"]
---

這篇說明 mod_php 這種執行模型：PHP 以 Apache 模組的形式載入，直譯器住在 Apache 的子程序裡。用 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/) 的那組問題來看，它的答案是：直譯器住在 web 伺服器的程序裡，程序活過很多請求，應用程式狀態仍然只活一個請求。文中的行為取自官方的 `php:8.5-apache` 映像檔。

## PHP 以 Apache 模組的形式載入

mod_php 是編譯成 Apache 模組的 PHP（Debian 系的套件裡檔名是 `libphp.so` 一類），Apache 啟動時用 `LoadModule` 把它載入，它的 SAPI 名稱是 `apache2handler`（見 [mod_php](/php/knowledge-cards/mod-php/)）。載入之後，Apache 的每個子程序裡都有一份完整的 PHP 直譯器，收到 `.php` 的請求時在自己的程序裡直接執行，不經過任何程序之間的溝通。

這個做法省掉了 [CGI](/php/01-server-runtime/cgi/) 每個請求都要啟動一個新程序的成本：子程序處理完一個請求之後留下來，接著處理下一個。在 `php:8.5-apache` 上對同一支計數腳本送 10 個請求，請求平均落在 5 個子程序上，每個處理兩次：

```text
   2 pid=16 static=1 global=1 sapi=apache2handler
   2 pid=17 static=1 global=1 sapi=apache2handler
   2 pid=18 static=1 global=1 sapi=apache2handler
   2 pid=19 static=1 global=1 sapi=apache2handler
   2 pid=20 static=1 global=1 sapi=apache2handler
```

子程序被重複使用，`static` 與全域變數仍然每次從 1 開始：程序活下來了，PHP 依舊在每個請求結束時清空應用程式的狀態。

## mod_php 要搭配 prefork MPM

Apache 處理並發的方式由 MPM（Multi-Processing Module）決定，常見的有三種（見 [Apache MPM](/infra/knowledge-cards/apache-mpm/)）：

| MPM     | 並發的單位                                                                                       |
| ------- | ------------------------------------------------------------------------------------------------ |
| prefork | 每個連線佔用一個子程序，子程序裡沒有多執行緒                                                     |
| worker  | 每個子程序有多個執行緒，每個連線佔用一個執行緒                                                   |
| event   | 跟 worker 一樣用執行緒，另外把閒置的 keep-alive 連線交給專門的執行緒看管，不佔住處理請求的執行緒 |

PHP 官方的安裝文件寫明：除非 PHP 以執行緒安全（`--enable-zts`）編譯，mod_php 只能搭配 prefork MPM，而這「significantly limits concurrency」。原因在 PHP 的實作：沒有開啟 ZTS（Zend Thread Safety）的 PHP 把每個請求的狀態放在全域變數裡，兩個執行緒同時執行 PHP 會互相覆寫；而 PHP 的擴充與它們依賴的 C 函式庫也不保證能在多執行緒下使用（見 [ZTS](/php/knowledge-cards/zts/)）。多數發行版的 mod_php 套件沒有開 ZTS，`php:8.5-apache` 也一樣：

```text
$ apache2ctl -M | grep -E "mpm|php"
 mpm_prefork_module (shared)
 php_module (shared)
$ php -i | grep "Thread Safety"
Thread Safety => disabled
```

Apache 2.4 自己的預設 MPM 是 event（官方 `httpd:2.4` 映像檔回報 `Server MPM: event`）。裝上 mod_php，Apache 就要退回 prefork。

## 每個子程序都帶著 PHP

prefork 加 mod_php 的組合，讓 PHP 直譯器出現在每一個子程序裡，不論這個子程序正在處理什麼請求。在容器裡列出 Apache 的程序與它們映射的 `libphp`：

```text
pid=1  user=root     rss_kb=29112 libphp_mapped=6
pid=16 user=www-data rss_kb=9928  libphp_mapped=6
pid=17 user=www-data rss_kb=10640 libphp_mapped=6
pid=18 user=www-data rss_kb=9928  libphp_mapped=6
```

（讀其他程序的 `/proc/<pid>/maps` 需要 `SYS_PTRACE` 權限，在 Docker 裡要用 `--cap-add SYS_PTRACE` 啟動容器才讀得到。）

剛處理過一個靜態檔 `hello.txt` 請求的子程序，也映射著 `libphp`。這帶出 mod_php 的三個代價，它們的根源相同：

**送靜態檔的程序也背著 PHP。** 一個頁面載入一支 PHP 與數十個圖片、CSS、JS，每個請求都佔用一個帶著 PHP 的子程序。能同時存在的子程序數量受主機記憶體約束，而每個子程序的記憶體裡都有一份 PHP，所以同樣的記憶體能開的子程序比純送靜態檔的 web 伺服器少。

**並發數等於子程序數。** prefork 一個連線佔一個子程序，同時能處理的連線數上限就是子程序的上限（`MaxRequestWorkers`）。網路慢的客戶端、或是在 keep-alive 時間內沒有送下一個請求的連線，都會佔住一個帶著 PHP 的子程序，而它在這段時間什麼都沒做。

**所有站台以同一個帳號執行。** 子程序的執行帳號是 Apache 的帳號（上面的 `www-data`）。同一台伺服器上的每個站台，PHP 都以這個帳號執行，A 站的 PHP 讀得到 B 站的設定檔；PHP 產生的檔案屬於 `www-data`，站台擁有者用自己的 FTP 帳號刪不掉。共享主機因此長期用 [CGI](/php/01-server-runtime/cgi/#cgi-在共享主機上留下來的理由) 加 suEXEC，而不用 mod_php。例外是第三方的 MPM `mpm-itk`：它讓每個虛擬主機以自己的帳號執行 mod_php，使用的人較少，Apache 官方發行的 prefork、worker、event 都沒有這個能力。

## 設定的位置與生效時機

mod_php 的 PHP 跟 Apache 是同一個程序，所以 PHP 的設定跟 Apache 綁在一起：

- **`php.ini` 改了要重新載入 Apache**：設定在子程序啟動時讀入，改了檔案要 `apachectl graceful` 讓 Apache 換掉子程序才生效。重啟 PHP 就是重啟 Apache。
- **`.htaccess` 可以改 PHP 設定**：mod_php 在 Apache 裡註冊了 `php_value`、`php_flag` 這些指令，站台在自己目錄的 [.htaccess](/infra/knowledge-cards/htaccess/) 裡寫 `php_value upload_max_filesize 64M` 就能覆寫設定，不必有伺服器的管理權限。這是共享主機時代最常用的調整方式。

## 從 mod_php 換到 PHP-FPM 時 .htaccess 的變化

PHP 官方文件現在對 Apache 的建議是：新的部署用 PHP-FPM 搭配 Apache 的 `mod_proxy_fcgi`，這樣 Apache 可以用 event MPM，PHP 也能獨立重啟（見 [PHP-FPM](/php/01-server-runtime/php-fpm/)）。換過去時，`.htaccess` 裡的 PHP 設定是最常撞到的問題。

`php_value` 這個指令是 mod_php 註冊的，Apache 沒載入 mod_php 時不認得它。在官方的 `httpd:2.4` 上放一個只有一行 `php_value upload_max_filesize 64M` 的 `.htaccess`，連同目錄下的靜態檔 `index.html` 都回 500，錯誤 log 是：

```text
[core:alert] ... /usr/local/apache2/htdocs/.htaccess: Invalid command 'php_value', perhaps misspelled or defined by a module not included in the server configuration
```

`.htaccess` 一旦有 Apache 不認得的指令，整份檔案都不能用，所以壞掉的是整個目錄，不只是 PHP 的請求。

PHP-FPM（以及 CGI）下對應的機制是 `.user.ini`：放在站台目錄裡、語法跟 `php.ini` 相同的檔案，PHP 官方文件寫明它只由 CGI/FastCGI SAPI 處理（見 [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)）。所以搬家時要把 `.htaccess` 裡的 `php_value` 與 `php_flag` 移到 `.user.ini`，並刪掉 `.htaccess` 裡的那幾行。`.user.ini` 不是每個請求都重讀：PHP 依 `user_ini.cache_ttl`（預設 300 秒）快取它，改了之後最多要等這段時間才生效。

## mod_php 適合的場合

mod_php 的優點是簡單：一個程序、一份設定，Apache 與 PHP 之間沒有任何協定要設定，也沒有第二個服務要監看。單一站台、流量不大、靜態檔由 CDN 或另一台伺服器處理時，它的代價不明顯。

它的代價集中在兩件事上：每個子程序都帶著 PHP，以及 PHP 的壽命與身分綁在 Apache 上。把 PHP 從 web 伺服器的程序裡搬出去、同時保留常駐程序的好處，需要一個讓 web 伺服器與 PHP 程序溝通的協定，那就是 [FastCGI](/php/01-server-runtime/fastcgi/)。
