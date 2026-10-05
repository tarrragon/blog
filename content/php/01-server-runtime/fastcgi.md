---
title: "FastCGI：讓 web 伺服器與常駐的 PHP 程序溝通的協定"
date: 2026-10-05
description: "說明 FastCGI 協定怎麼在 CGI 的基礎上去掉每個請求重啟程序這一點：常駐的應用程式程序、web 伺服器與它之間的連線、一個請求在協定裡的樣子，以及 SCRIPT_FILENAME 由 web 伺服器決定會帶來的安全邊界（cgi.fix_pathinfo 與 try_files）"
weight: 4
tags: ["php", "fastcgi", "nginx", "deployment"]
---

這篇說明 FastCGI 這個協定：它怎麼讓 web 伺服器與一個常駐的 PHP 程序溝通，以及這個分工帶來的一個安全邊界。它是 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/) 三個問題的一組答案：PHP 直譯器住在 web 伺服器外面的常駐程序裡。FastCGI 是協定，管理那群 PHP 程序的實作是 [PHP-FPM](/php/01-server-runtime/php-fpm/)，本篇只講協定本身與它的安全面。

## FastCGI 要解決 CGI 的哪一件事

[CGI](/php/01-server-runtime/cgi/) 的成本集中在一句話：每個請求啟動一個新程序，請求結束程序就消失。載入 PHP 執行檔、讀設定、初始化擴充這些工作，每個請求都要重做一次，OPcache 也因為程序不續命而永遠命中不了。

FastCGI 的原始規格由 Open Market 在 1996 年發布，開宗明義寫它「designed to support long-lived application processes」——支援長時間存活的應用程式程序。它保留 CGI 已經可行的部分（請求資訊用一組具名的參數傳遞，回應用資料流送回），只改掉程序的壽命：應用程式程序啟動一次後常駐，透過一條連線接收一個又一個請求。

| 面向                       | CGI                       | FastCGI                                     |
| -------------------------- | ------------------------- | ------------------------------------------- |
| 程序壽命                   | 每個請求一個新程序        | 應用程式程序常駐，處理很多請求              |
| 傳遞請求的方式             | 環境變數加標準輸入        | 連線上的 `FCGI_PARAMS` 與 `FCGI_STDIN` 記錄 |
| 傳遞回應的方式             | 標準輸出                  | 連線上的 `FCGI_STDOUT` 記錄                 |
| web 伺服器與應用程式的連線 | fork 出來的程序，父子關係 | TCP（如 `127.0.0.1:9000`）或 Unix socket    |

## 一個請求在 FastCGI 協定裡的樣子

FastCGI 把一條連線上的資料切成一筆一筆的記錄（record），每筆記錄有型別。一個請求用到的主要型別：

- **`FCGI_PARAMS`**：web 伺服器把請求的參數（名稱與值的配對）送給應用程式，裝的就是 CGI 那套 meta-variables——`REQUEST_METHOD`、`QUERY_STRING`、`SCRIPT_FILENAME` 等。PHP 的 `$_SERVER` 就是從這裡填出來的。
- **`FCGI_STDIN`**：請求的內容（POST 的資料）。
- **`FCGI_STDOUT`**：應用程式送回的回應，包含標頭與內容。
- **`FCGI_END_REQUEST`**：應用程式宣告這個請求處理完了。

FastCGI 的角色裡最常用的是 Responder，規格說它對應 CGI 原本做的事：接收一個 HTTP 請求的全部資訊，產生一個 HTTP 回應。PHP-FPM 實作的就是這個角色。

這帶出一個分工上的事實：**web 伺服器收到 HTTP 請求之後，自己把它拆解成 `FCGI_PARAMS` 裡的參數，再送給 PHP**。PHP 收到的是 web 伺服器整理好的參數，原始的 HTTP 請求留在 web 伺服器那一側。其中一個參數決定了 PHP 要執行哪個檔案，而它由 web 伺服器填寫——這是下一節的安全邊界。

## web 伺服器決定 PHP 執行哪個檔案

`SCRIPT_FILENAME` 這個參數告訴 PHP 要執行磁碟上的哪一個檔案。在 Nginx 加 PHP-FPM 的設定裡，它由 Nginx 組出來：

```nginx
location ~ \.php$ {
    fastcgi_pass fpm:9000;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
}
```

這段設定要讀者改的是 `fastcgi_pass` 後面的位址：`fpm:9000` 是 PHP-FPM 在這個環境裡的主機名與埠，同一台機器上通常是 `127.0.0.1:9000` 或一個 Unix socket 的路徑。`$fastcgi_script_name` 是 Nginx 從請求路徑推出來的腳本路徑。問題出在 `location ~ \.php$`：它只要求路徑以 `.php` 結尾，沒有要求那個檔案存在。

這一點配上 PHP 的 `cgi.fix_pathinfo` 設定會變成一個漏洞。`cgi.fix_pathinfo` 開著時（這是預設值），PHP 拿到一個不存在的檔案路徑，會往前找路徑裡存在的那一段當成要執行的腳本。把這幾件事擺在一起，一個常見的攻擊路徑是：使用者上傳一個內含 PHP 程式碼、副檔名卻是圖片的檔案（`evil.jpg`），再用 `/uploads/evil.jpg/x.php` 這個網址存取它。

在刻意寫成不安全版本（`location ~ \.php$` 沒有檢查檔案存在、`cgi.fix_pathinfo=1`、PHP-FPM 的 `security.limit_extensions` 放寬到容許 `.jpg`）的環境實測：

```text
$ curl localhost/uploads/evil.jpg/x.php
executed as PHP: /var/www/html/uploads/evil.jpg   [200]
```

Nginx 看到路徑以 `.php` 結尾，把它交給 PHP；PHP 找不到 `x.php`，依 `cgi.fix_pathinfo` 往前找到存在的 `evil.jpg`，把這個圖片當成 PHP 執行了。上傳的內容因此變成在伺服器上執行的程式碼。

### 三道各自獨立的防線

這個漏洞要同時打穿幾道設定才成立，所以每一道都能單獨擋下它。實測三種修法各自的效果：

PHP-FPM 的 `security.limit_extensions` 限制哪些副檔名可以被當成 PHP 執行，預設只有 `.php`。保持預設時，`evil.jpg` 根本不會被執行：

```text
$ curl localhost/uploads/evil.jpg/x.php
Access denied.   [403]
# php-fpm log: Access to the script '/var/www/html/uploads/evil.jpg'
#   has been denied (see security.limit_extensions)
```

把 `cgi.fix_pathinfo` 關掉（`php_admin_value[cgi.fix_pathinfo] = 0`），PHP 不再往前找存在的檔案，找不到 `x.php` 就直接回報沒有輸入檔：

```text
$ curl localhost/uploads/evil.jpg/x.php
No input file specified.   [404]
```

在 Nginx 的 `location ~ \.php$` 裡加 `try_files $uri =404`，要求檔案存在才交給 PHP，不存在的 `x.php` 在 Nginx 這一層就被擋下，根本到不了 PHP：

```text
location ~ \.php$ {
    try_files $uri =404;        # 檔案不存在就直接回 404，不轉給 PHP
    fastcgi_pass fpm:9000;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
}
```

```text
$ curl localhost/uploads/evil.jpg/x.php
[404]
```

三道防線的位置不同：`try_files` 在 web 伺服器（請求還沒到 PHP）、`security.limit_extensions` 與 `cgi.fix_pathinfo` 在 PHP 端。預設值已經擋住這個攻擊（`security.limit_extensions` 預設 `.php`、而 `fix_pathinfo` 的風險要配上寬鬆的 `location` 才成立），要出事得有人主動放寬設定。三道一起設是縱深防禦：任何一道被改錯，另外兩道還在。

這個邊界的根源是本篇開頭那件事：**`SCRIPT_FILENAME` 由 web 伺服器決定**，PHP 照著它執行。PHP 信任 web 伺服器交來的檔案路徑，所以 web 伺服器的路由規則寫得鬆，PHP 就會執行到不該執行的檔案。

## FastCGI 與 PHP-FPM 的關係

FastCGI 是協定，規定 web 伺服器與應用程式程序之間怎麼傳遞請求和回應。它本身不規定那群常駐的應用程式程序由誰啟動、開幾個、一個掛了怎麼補、記憶體漲了怎麼辦。

這些是「程序管理」的工作，PHP 的答案是 PHP-FPM（FastCGI Process Manager）。它實作 FastCGI 的 Responder 角色，接 Nginx 或 Apache 用這個協定送來的請求，並管理那一群 PHP worker 程序。程序管理的每一個旋鈕，以及它們怎麼影響服務的行為與壓測數字，在 [PHP-FPM](/php/01-server-runtime/php-fpm/) 展開。
