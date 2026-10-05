---
title: "PHP 的請求生命週期與 SAPI：直譯器的位置、程序壽命與狀態壽命"
date: 2026-10-05
description: "說明一個 HTTP 請求怎麼變成一次 PHP 執行：PHP 在程序啟動與每個請求開始、結束時各做什麼，SAPI 這一層介面怎麼讓同一個直譯器接上 CGI、Apache、FastCGI 與常駐伺服器，以及用直譯器住在哪裡、執行它的程序活多久、應用程式的狀態活多久這組問題比較各種執行模型"
weight: 1
tags: ["php", "sapi", "deployment"]
---

這篇說明 PHP 直譯器與 web 伺服器之間的那一層：一個 HTTP 請求進來之後，PHP 在什麼時候被啟動、哪些狀態在請求結束時被清掉、哪些資源留在程序裡。範圍不含 PHP 語法與框架；文中的行為取自 PHP 8.5，用官方 Docker 映像檔實測。

## 一個請求在 PHP 裡經過的階段

PHP 的執行分成兩層生命週期：**程序層**與**請求層**。程序層的工作每個程序只做一次，請求層的工作每個請求都做一次。

| 層     | 階段     | PHP 在這個階段做的事                                                                      |
| ------ | -------- | ----------------------------------------------------------------------------------------- |
| 程序層 | 模組啟動 | 讀 `php.ini`、載入並初始化擴充（`pdo_pgsql`、`redis` 這類），每個擴充註冊自己的函式與類別 |
| 請求層 | 請求啟動 | 依這個請求建立 `$_SERVER`、`$_GET`、`$_POST`、`$_COOKIE` 等超全域變數                     |
| 請求層 | 執行腳本 | 把 `.php` 檔編譯成 opcode（Zend 引擎執行的指令），再執行它                                |
| 請求層 | 請求結束 | 釋放這個請求建立的所有變數、物件與資源，送出剩下的輸出                                    |
| 程序層 | 模組結束 | 程序要結束時，各擴充釋放自己的資源                                                        |

請求結束那一步的範圍很大：全域變數、函式內的 `static` 變數、類別的靜態屬性、開過的檔案與一般的資料庫連線，全部在這一步釋放。下一個請求就算由同一個程序處理，也看不到上一個請求留下的任何 PHP 變數。這個設計叫 **shared-nothing**：請求之間不共享應用程式的狀態，每個請求從空白開始（見 [Shared-nothing 請求模型](/php/knowledge-cards/shared-nothing-request/)）。

這件事可以直接量。下面這支腳本每次執行都把函式內的 `static` 變數與一個全域變數加一，並印出處理它的程序編號：

```php
<?php
function counter() { static $n = 0; return ++$n; }
$GLOBALS['g'] = ($GLOBALS['g'] ?? 0) + 1;
echo "pid=", getmypid(), " static=", counter(), " global=", $GLOBALS['g'], " sapi=", PHP_SAPI, "\n";
```

在 Nginx 加 PHP-FPM 的環境連續請求四次，輸出是：

```text
pid=7 static=1 global=1 sapi=fpm-fcgi
pid=6 static=1 global=1 sapi=fpm-fcgi
pid=7 static=1 global=1 sapi=fpm-fcgi
pid=6 static=1 global=1 sapi=fpm-fcgi
```

兩個程序（PID 6 與 7）輪流處理請求，同一個程序處理第二次時，兩個計數器仍然是 1。程序活了下來，PHP 變數沒有。

### 請求結束後留在程序裡的資源

請求結束只清掉 PHP 程式碼建立的變數，程序本身持有的資源可以跨請求存在，而且只有程序活得夠久時才有意義：

- **OPcache**：把編譯好的 opcode 存在共享記憶體裡，下一個請求不必重新編譯同一個檔案。它的效果完全取決於程序活多久，在 [OPcache 與程序壽命](/php/01-server-runtime/opcache/) 展開。
- **持久連線**：PDO 開了 `PDO::ATTR_PERSISTENT` 的資料庫連線，請求結束時不關閉，留給同一個程序的下一個請求重用。
- **APCu 這類記憶體快取擴充**：資料放在程序（或程序群共用）的記憶體裡，請求結束不清除。

所以 shared-nothing 的精確範圍是「PHP 程式碼建立的狀態」。程序層的資源由程序壽命決定，而程序壽命由下一節的 SAPI 決定。

## SAPI：PHP 直譯器與外部環境之間的介面

**SAPI**（Server API）是 PHP 核心與外部環境之間的一層。PHP 的直譯器本身不知道請求從哪裡來：它可能被命令列啟動、被 web 伺服器 fork 出來、被嵌在 Apache 裡、或在一個常駐的伺服器裡被呼叫。SAPI 負責兩件事：把外部環境帶來的請求翻譯成 PHP 認得的形式（填好 `$_SERVER`、`$_GET`，把請求內容交給 `php://input`），以及把 PHP 的輸出與回應標頭交回外部環境。同一份 PHP 核心配上不同的 SAPI，就是不同的執行方式（見 [SAPI](/php/knowledge-cards/sapi/)）。

程式裡可以用 `PHP_SAPI` 常數（或 `php_sapi_name()`）讀到目前的 SAPI 名稱。上一節的輸出裡 `sapi=fpm-fcgi` 就是這個值。實測過的幾種：

| `PHP_SAPI` 的值  | 啟動方式                                                            | 誰對外講 HTTP                      |
| ---------------- | ------------------------------------------------------------------- | ---------------------------------- |
| `cli`            | 在命令列執行 `php script.php`                                       | 沒有 HTTP                          |
| `cgi-fcgi`       | `php-cgi` 這支程式，被 web 伺服器以 CGI 啟動，或以 FastCGI 模式常駐 | web 伺服器                         |
| `apache2handler` | mod_php：PHP 以 Apache 模組的形式載入 Apache 的程序裡               | Apache                             |
| `fpm-fcgi`       | PHP-FPM：一個常駐的主程序管理一群 worker，用 FastCGI 接請求         | 前面的 web 伺服器（Nginx、Apache） |
| `frankenphp`     | FrankenPHP：PHP 嵌在一個用 Go 寫的 web 伺服器裡                     | FrankenPHP 自己                    |

`cgi-fcgi` 這個名字反映了一件事：`php-cgi` 同一支程式能以兩種協定運作。CGI 與 FastCGI 是兩個不同的協定，FastCGI 沿用 CGI 傳遞請求資訊的那套參數名稱，改掉的是程序壽命。被 web 伺服器以 CGI 執行時，`php-cgi` 處理完一個請求就結束；以 FastCGI 模式啟動時，它常駐下來接收多個請求。兩者的差別在 [CGI](/php/01-server-runtime/cgi/) 與 [FastCGI](/php/01-server-runtime/fastcgi/) 兩篇分別說明。

## 比較執行模型的三個問題

SAPI 的種類很多，而它們之間的差異可以歸到三個問題上。每一種執行模型對這三個問題各有一組答案，後面的行為差異幾乎都從這組答案推得出來。

**直譯器住在哪裡。** PHP 直譯器可能住在 web 伺服器自己的程序裡（mod_php），也可能住在另一個獨立的程序裡（CGI、PHP-FPM），或住在某個程序的執行緒裡（FrankenPHP）。住在 web 伺服器外面時，web 伺服器與 PHP 之間需要一種溝通方式，CGI 與 FastCGI 就是這種方式。這也決定了誰對外講 HTTP：直譯器住在 web 伺服器外面時，PHP 這一側只收得到 web 伺服器翻譯過的請求。

**執行它的程序活多久。** 程序可能只活一個請求（CGI），也可能活過成千上萬個請求（mod_php、PHP-FPM、FrankenPHP）。程序活得越久，程序層的工作（讀設定、載入擴充）攤在越多請求上，OPcache 這類程序層的快取也才有編譯結果可以重用。

**應用程式的狀態活多久。** 在 shared-nothing 的模型裡，狀態只活一個請求，框架每個請求都要重新啟動一次：載入設定、註冊服務、建立路由表。常駐 worker 模式（FrankenPHP 的 worker 模式、Laravel Octane）讓應用程式啟動一次後留在記憶體裡，狀態活過很多個請求，省下每次重新啟動框架的成本，代價是上一個請求留下的變數與物件會被下一個請求看到：放在靜態屬性裡的「目前登入的使用者」會被下一個使用者的請求讀到，每個請求往靜態陣列加資料的程式會讓記憶體隨請求數一路增長。

| 執行模型                                 | 直譯器住在             | 程序壽命 | 應用程式狀態壽命 |
| ---------------------------------------- | ---------------------- | -------- | ---------------- |
| CGI                                      | 每個請求新啟動的程序   | 一個請求 | 一個請求         |
| mod_php                                  | Apache 的子程序        | 很多請求 | 一個請求         |
| FastCGI（PHP-FPM）                       | 獨立的常駐 worker 程序 | 很多請求 | 一個請求         |
| FrankenPHP 傳統模式                      | 常駐程序裡的執行緒     | 很多請求 | 一個請求         |
| 常駐 worker（FrankenPHP worker、Octane） | 常駐的 worker          | 很多請求 | 很多請求         |

這張表裡最容易混在一起的是程序壽命與應用程式狀態壽命這兩欄，而它們是兩件獨立的事：FrankenPHP 的傳統模式只有一個程序、而且一直不結束，同一支計數腳本在它上面跑三次，三次的 PID 都是 1、計數器三次都是 1；換成 worker 模式，PID 仍然是 1，計數器變成 1、2、3、4。程序一樣常駐，差在 PHP 有沒有在請求之間清空狀態。

## 三個問題各自展開的位置

這個模型的三個問題，每換掉一個答案就走到另一種執行模型：

- **把直譯器放在每個請求新啟動的程序裡**，就是 [CGI](/php/01-server-runtime/cgi/)：最簡單的隔離，每個請求付一次啟動 PHP 的成本。
- **把直譯器放進 web 伺服器的程序裡**，就是 [mod_php](/php/01-server-runtime/mod-php/)：省掉啟動成本，代價是 web 伺服器的每個程序都帶著整個 PHP，包括只負責送圖片的那些。
- **把直譯器放在 web 伺服器外面、讓程序常駐**，需要一個讓兩邊溝通的協定，就是 [FastCGI](/php/01-server-runtime/fastcgi/)；管理那群常駐程序的實作是 [PHP-FPM](/php/01-server-runtime/php-fpm/)。
- **讓程序活得更久**對效能的意義集中在 [OPcache](/php/01-server-runtime/opcache/)：程序壽命從一個請求變成很多個請求時，被重用的是什麼。
- **讓應用程式的狀態也活過很多請求**，就是 [常駐 worker 模型](/php/01-server-runtime/long-running-workers/)：框架只啟動一次，同時失去 shared-nothing 的隔離。
