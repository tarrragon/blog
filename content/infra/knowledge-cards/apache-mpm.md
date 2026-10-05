---
title: "Apache MPM（Multi-Processing Module）"
date: 2026-10-05
description: "在 Apache 設定或 httpd -V 看到 prefork、worker、event，或要判斷 mod_php 為什麼讓 Apache 只能用 prefork、換成 PHP-FPM 之後能改用哪一種時"
weight: 53
tags: ["infra", "apache", "knowledge-cards"]
---

Apache MPM 決定 Apache 用程序還是執行緒處理並發的連線：prefork 每個連線佔一個子程序、子程序裡沒有多執行緒；worker 每個子程序有多個執行緒，每個連線佔一個執行緒；event 跟 worker 一樣用執行緒，另外把閒置的 keep-alive 連線交給專門的執行緒看管。Apache 2.4 的官方映像檔預設是 event。可先對照 [nginx](/infra/knowledge-cards/nginx/) 與 [CGI](/infra/knowledge-cards/cgi/)。

## 概念位置

MPM 是 Apache 的並發模型，跟 [nginx](/infra/knowledge-cards/nginx/) 的事件驅動模型是同一個問題的不同答案；它也跟 PHP 的執行方式互相限制：[mod_php](/php/knowledge-cards/mod-php/) 把 PHP 放進 Apache 的程序裡，沒有以 [ZTS](/php/knowledge-cards/zts/) 編譯時只能搭配 prefork；PHP 改由 [PHP-FPM](/php/knowledge-cards/php-fpm/) 在外面執行（Apache 用 `mod_proxy_fcgi` 轉送）時，Apache 就能用 event。

## 可觀察訊號與例子

- **`httpd -V` 的 `Server MPM`**：官方 `httpd:2.4` 是 `event`，`php:8.5-apache` 是 `prefork`（裝了 mod_php）。
- **`apache2ctl -M` 列出 `mpm_prefork_module`**：同時列出 `php_module` 時，就是 mod_php 加 prefork 的組合。
- **並發上限等於子程序上限**：prefork 下 `MaxRequestWorkers` 就是能同時處理的連線數，慢客戶端與閒置的 keep-alive 連線都佔著一個子程序。

## 設計責任

從 mod_php 換到 PHP-FPM 時，可以順便把 MPM 換成 event，讓 Apache 用較少的資源處理大量連線。詳見 [mod_php](/php/01-server-runtime/mod-php/)。
