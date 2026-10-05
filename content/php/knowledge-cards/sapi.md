---
title: "SAPI（Server API）"
date: 2026-10-05
description: "在 PHP_SAPI 或 phpinfo 看到 cli、fpm-fcgi、apache2handler、frankenphp 這類值，要知道它代表 PHP 以哪種方式被啟動、請求怎麼交進來時"
weight: 1
tags: ["php", "knowledge-cards"]
---

SAPI（Server API）是 PHP 核心與外部環境之間的介面層：它把外部環境帶來的請求翻譯成 PHP 認得的形式（填好 `$_SERVER`、`$_GET`，把請求內容交給 `php://input`），再把 PHP 的輸出與回應標頭交回外部環境。同一份 PHP 核心配上不同的 SAPI，就是不同的執行方式。可先對照 [Shared-nothing 請求模型](/php/knowledge-cards/shared-nothing-request/) 與 [PHP-FPM](/php/knowledge-cards/php-fpm/)。

## 概念位置

SAPI 位在 PHP 核心（Zend 引擎與擴充）與 web 伺服器、命令列之間。它決定 PHP 直譯器住在哪個程序、那個程序活多久，這兩件事又決定 [OPcache](/php/knowledge-cards/opcache/) 有沒有編譯結果可以重用。[mod_php](/php/knowledge-cards/mod-php/) 是 SAPI 的一種（`apache2handler`），PHP-FPM 是另一種（`fpm-fcgi`）。

## 可觀察訊號與例子

- **讀目前的 SAPI**：程式裡的 `PHP_SAPI` 常數或 `php_sapi_name()`。命令列執行是 `cli`，PHP-FPM 是 `fpm-fcgi`，mod_php 是 `apache2handler`，`php-cgi` 是 `cgi-fcgi`，FrankenPHP 是 `frankenphp`。
- **同一支程式、兩種行為**：`php-cgi` 被 web 伺服器以 CGI 啟動時處理一個請求就結束，以 FastCGI 模式啟動時常駐，SAPI 名稱都是 `cgi-fcgi`。
- **設定檔依 SAPI 分開**：很多發行版把 `php.ini` 分成 `cli/` 與 `fpm/` 兩份，命令列改的設定不影響網頁請求。

## 設計責任

部署時要先知道服務跑的是哪個 SAPI，因為程序壽命、執行帳號、設定檔位置與 `.htaccess` 能不能改 PHP 設定都跟著它變。完整的比較見 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/)。
