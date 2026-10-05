---
title: "CGI（Common Gateway Interface）"
date: 2026-10-05
description: "接手 cgi-bin 目錄或以 php-cgi 執行的舊站，或在 $_SERVER 看到 REQUEST_METHOD、QUERY_STRING 這類大寫鍵名，要知道它們從哪裡來時"
weight: 52
tags: ["infra", "knowledge-cards"]
---

CGI 是 web 伺服器呼叫外部程式來產生回應的介面，規格是 RFC 3875（CGI/1.1）：web 伺服器為每個請求啟動一個新程序，把請求資訊放進環境變數（RFC 稱為 meta-variables）、把請求內容寫進標準輸入，程式把回應寫到標準輸出後結束。它跟語言無關。可先對照 [nginx](/infra/knowledge-cards/nginx/) 與 [Apache MPM](/infra/knowledge-cards/apache-mpm/)。

## 概念位置

CGI 是「web 伺服器負責 HTTP、外部程式負責產生內容」這個分工的起點。後來的 FastCGI 保留了同一套參數名稱，只改掉程序壽命（程序常駐、處理很多請求），PHP 的實作是 [PHP-FPM](/php/knowledge-cards/php-fpm/)。[.htaccess](/infra/knowledge-cards/htaccess/) 時代的共享主機常用 CGI 加 suEXEC 讓每個站台以自己的帳號執行。

## 可觀察訊號與例子

- **`$_SERVER` 的大寫鍵名**：`REQUEST_METHOD`、`QUERY_STRING`、`SCRIPT_FILENAME` 來自 CGI 的 meta-variables，FastCGI 沿用了它們。
- **每個請求一個新 PID**：PHP 以 `php-cgi` 被 CGI 呼叫時，每個請求的 `getmypid()` 都不同，OPcache 永遠命中不了。
- **CVE-2012-1823**：PHP 5.3.12 / 5.4.2 之前，以 CGI 方式執行的 `php-cgi` 可能把查詢字串當成命令列選項，只影響這種部署。

## 設計責任

接手 CGI 部署時，要知道它的每請求啟動成本與隔離方式；換成 PHP-FPM 時，用 pool 的執行帳號保留原本 suEXEC 提供的隔離。詳見 [CGI](/php/01-server-runtime/cgi/)。
