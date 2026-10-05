---
title: "CGI：每個請求啟動一個 PHP 程序的執行模型"
date: 2026-10-05
description: "說明 CGI 怎麼把一個 HTTP 請求交給外部程式：web 伺服器為每個請求啟動一個程序，用環境變數與標準輸入輸出傳遞請求和回應；PHP 以 php-cgi 執行時每個請求付出的啟動成本、OPcache 為什麼沒有作用、以每個站台的使用者身分執行帶來的隔離，以及請求資料與程式呼叫參數之間的邊界問題"
weight: 2
tags: ["php", "cgi", "deployment"]
---

這篇說明 CGI（Common Gateway Interface）這種執行模型，以及 PHP 用它執行時的行為與成本。它是 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/) 那組問題的一組答案：PHP 直譯器住在每個請求新啟動的程序裡，程序與應用程式狀態都只活一個請求。

## CGI 怎麼把請求交給外部程式

CGI 是 web 伺服器呼叫外部程式來產生回應的介面，規格寫成 RFC 3875（CGI/1.1），RFC 自己記載這個介面從 1993 年起就在 web 上使用。它跟語言無關：被呼叫的可以是 Perl、C、shell script 或 PHP，早期網站的 `cgi-bin/` 目錄放的就是這類程式（見 [CGI](/infra/knowledge-cards/cgi/)）。

一個請求經過 CGI 的過程：

| 動作者     | 做的事                                                                                                                                    |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| web 伺服器 | 收到請求，判斷這個路徑要交給哪一支程式                                                                                                    |
| web 伺服器 | 啟動那支程式的一個新程序（fork 加 exec）                                                                                                  |
| web 伺服器 | 把請求的資訊放進這個程序的環境變數：`REQUEST_METHOD`、`QUERY_STRING`、`CONTENT_TYPE`、`CONTENT_LENGTH`、`REMOTE_ADDR`，以及各個 HTTP 標頭 |
| web 伺服器 | 把請求的內容（POST 的資料）寫進程序的標準輸入                                                                                             |
| 外部程式   | 從環境變數與標準輸入讀到請求，把回應標頭、一個空行與回應內容寫到標準輸出                                                                  |
| 外部程式   | 結束程序                                                                                                                                  |
| web 伺服器 | 把標準輸出的內容整理成 HTTP 回應送回客戶端                                                                                                |

RFC 3875 把這些環境變數叫做 meta-variables。PHP 的 `$_SERVER` 陣列裡那些大寫的鍵（`REQUEST_METHOD`、`QUERY_STRING`、`SCRIPT_FILENAME`）就是從這裡來的，後來的 FastCGI 與 PHP-FPM 沿用了同一套名稱。

## PHP 以 CGI 執行時的行為

PHP 提供一支叫 `php-cgi` 的程式給 CGI 使用，官方的 PHP Docker 映像檔（`php:8.5-cli`）裡就有。下面用 lighttpd 當 web 伺服器，設定所有 `.php` 結尾的請求都交給 `php-cgi` 執行：

```text
# lighttpd.conf
server.document-root = "/var/www/html"
server.modules = ( "mod_cgi" )
# 副檔名對應到要執行的程式：每個 .php 請求都啟動一個 php-cgi 程序
cgi.assign = ( ".php" => "/usr/local/bin/php-cgi" )
```

`server.document-root` 是網站檔案所在的目錄，`cgi.assign` 的右邊是 `php-cgi` 在這個環境裡的實際路徑，換到別的系統要用 `which php-cgi` 查。對一支印出程序編號與計數器的腳本（腳本內容見 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/#一個請求在-php-裡經過的階段)）連續請求四次：

```text
pid=15 static=1 global=1 sapi=cgi-fcgi
pid=16 static=1 global=1 sapi=cgi-fcgi
pid=17 static=1 global=1 sapi=cgi-fcgi
pid=18 static=1 global=1 sapi=cgi-fcgi
```

每個請求都是一個新的程序。PHP 的兩層生命週期在這裡疊成一層：模組啟動（讀 `php.ini`、初始化所有擴充）與請求啟動每個請求都各做一次，請求結束時程序也跟著結束。

### 每個請求付出的啟動成本

在同一台電腦、同一支極小的腳本上，循序送 300 個請求，CGI 每個請求的平均時間大約是 PHP-FPM 的七倍（一次量測：8.7 ms 對 1.3 ms）。腳本本身幾乎不花時間，差距來自 CGI 每個請求都要做的事：作業系統建立一個新程序、載入 PHP 的執行檔與共用函式庫、讀設定、初始化每一個擴充。PHP-FPM 的 worker 是常駐的，這些工作在 worker 啟動時做過一次就不再重複。

確切的倍數隨機器、載入的擴充數量與腳本大小變動，值得帶走的是成本的位置：CGI 的固定成本落在每一個請求上，常駐程序把它攤到很多個請求上。

### OPcache 在 CGI 下沒有作用

OPcache 把 PHP 檔案編譯好的 opcode 存在共享記憶體裡，讓之後的請求跳過編譯。它的共享記憶體屬於啟動它的那個程序，程序結束，快取就跟著消失。在 CGI 下印出 OPcache 的統計：

```text
pid=19 opcache_enabled=true cached_scripts=1 hits=0
pid=20 opcache_enabled=true cached_scripts=1 hits=0
pid=21 opcache_enabled=true cached_scripts=1 hits=0
```

OPcache 是開著的，每個程序也把腳本編譯進了快取（`cached_scripts=1`），可是命中次數永遠是 0：下一個請求是新程序，拿到的是一份全新、空白的快取。框架每個請求要載入數百個檔案，這些檔案在 CGI 下每次都要重新編譯。OPcache 與程序壽命的關係在 [OPcache 與程序壽命](/php/01-server-runtime/opcache/) 展開。

## CGI 在共享主機上留下來的理由

CGI 的成本這麼高，它在共享主機上用了很久，理由是隔離。每個請求都是一個獨立的程序，所以 web 伺服器可以用不同的使用者身分啟動它。Apache 的 suEXEC 讓 CGI 程式以站台擁有者的帳號執行，而不是 Apache 自己的帳號：

- **站台之間互相看不到檔案**：A 站的 PHP 以 A 的帳號執行，讀不到 B 站的設定檔與資料庫密碼。
- **檔案權限對得上**：PHP 上傳或產生的檔案屬於站台擁有者，透過 FTP 登入的同一個帳號能修改與刪除它們。
- **一個請求出錯只影響那一個程序**：記憶體洩漏或當掉都隨程序結束而消失。

這組需求是 [mod_php](/php/01-server-runtime/mod-php/) 在 Apache 官方的 MPM 下做不到的：mod_php 的 PHP 住在 Apache 的程序裡，所有站台都以同一個帳號執行。後來 [PHP-FPM](/php/01-server-runtime/php-fpm/) 用 pool（每個站台一組 worker、各自指定執行帳號）在常駐程序上做到同樣的隔離，共享主機才有理由離開 CGI。

## 請求資料與程式呼叫參數之間的邊界

CGI 用啟動一支程式的方式處理請求，所以請求的內容有機會被當成「啟動程式的方式」解讀。PHP 在這個邊界上出過一個嚴重的漏洞：CVE-2012-1823。依 NVD 的公告，PHP 5.3.12 與 5.4.2 之前，`php-cgi` 以 CGI 方式執行時沒有正確處理不含 `=` 的查詢字串，使查詢字串的內容可能被當成 `php-cgi` 的命令列選項，進而導致遠端執行程式碼。修正方式是升級到修補過的版本，而這個類型的問題只出現在 PHP 以 CGI 程式被呼叫的部署上。

這類問題在 FastCGI 下不存在同樣的形式：FastCGI 的 PHP 程序早就啟動好了，請求資料走的是協定裡的參數，不會變成程序的啟動參數。PHP 端還有兩個跟 CGI 有關的設定一直保留到今天，`cgi.force_redirect` 與 `cgi.fix_pathinfo`，其中 `cgi.fix_pathinfo` 在 FastCGI 環境仍然影響安全，在 [FastCGI](/php/01-server-runtime/fastcgi/#web-伺服器決定-php-執行哪個檔案) 說明。

## CGI 在今天的位置

新部署很少用 CGI 執行 PHP，原因是前面量到的兩件事：每個請求的啟動成本，以及 OPcache 沒有作用。它仍然出現在兩種地方：一些舊的共享主機，以及只需要偶爾執行一支腳本、不值得常駐一個程序的場合。

CGI 的設計有兩項比它本身活得久：環境變數形式的請求資訊（`$_SERVER` 的鍵名）、「web 伺服器負責 HTTP、外部程式負責產生內容」的分工，都被 FastCGI 原樣繼承。FastCGI 改掉的只有一件事：程序不再每個請求結束，見 [FastCGI](/php/01-server-runtime/fastcgi/)。
