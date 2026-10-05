---
title: "mod_php"
date: 2026-10-05
description: "接手 Apache 加 mod_php 的舊站、評估要不要換成 PHP-FPM，或遇到 .htaccess 的 php_value 在新環境回 500 時"
weight: 3
tags: ["php", "apache", "knowledge-cards"]
---

mod_php 是編譯成 Apache 模組的 PHP，Apache 啟動時用 `LoadModule` 載入，之後 Apache 的每個子程序裡都有一份 PHP 直譯器，收到 `.php` 請求就在自己的程序裡執行。它的 [SAPI](/php/knowledge-cards/sapi/) 名稱是 `apache2handler`。可先對照 [PHP-FPM](/php/knowledge-cards/php-fpm/) 與 [Apache MPM](/infra/knowledge-cards/apache-mpm/)。

## 概念位置

mod_php 把直譯器放進 web 伺服器的程序裡：省掉 CGI 每請求啟動程序的成本，代價是 PHP 的壽命、執行帳號與設定都綁在 Apache 上。沒有以 [ZTS](/php/knowledge-cards/zts/) 編譯的 mod_php 只能搭配 prefork MPM。PHP 官方文件對新部署的建議是改用 PHP-FPM 搭配 Apache 的 `mod_proxy_fcgi`。

## 可觀察訊號與例子

- **`apache2ctl -M` 列出 `php_module` 與 `mpm_prefork_module`**：多數發行版的 mod_php 沒有開 ZTS，`php -i` 顯示 `Thread Safety => disabled`。
- **送靜態檔的子程序也映射著 `libphp`**：每個子程序都帶著 PHP，不論它在處理什麼請求。
- **所有站台以 Apache 的帳號（如 `www-data`）執行**：PHP 產生的檔案屬於這個帳號。
- **`.htaccess` 的 `php_value`**：mod_php 註冊了這個指令；沒載入 mod_php 的 Apache 讀到它會回 500（`Invalid command 'php_value'`），而且整個目錄都壞掉。

## 設計責任

從 mod_php 搬到 PHP-FPM 時，`.htaccess` 裡的 `php_value` / `php_flag` 要移到 `.user.ini`（見 [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)）。完整的行為與實測見 [mod_php](/php/01-server-runtime/mod-php/)。
