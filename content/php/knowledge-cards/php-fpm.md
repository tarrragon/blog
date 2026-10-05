---
title: "PHP-FPM（FastCGI Process Manager）"
date: 2026-10-05
description: "在 Nginx 或容器環境看到 php-fpm、9000 埠、pool 設定或 502 Bad Gateway，要知道 PHP-FPM 負責什麼、哪些設定決定並發與記憶體時"
weight: 5
tags: ["php", "php-fpm", "knowledge-cards"]
---

PHP-FPM 是 PHP 內建的 FastCGI 程序管理器：一個 master 程序加一群常駐的 worker，master 負責讀設定、開 worker、補死掉的 worker 與處理訊號，worker 實際執行 PHP，透過 FastCGI 協定接收 web 伺服器轉來的請求。它的 [SAPI](/php/knowledge-cards/sapi/) 名稱是 `fpm-fcgi`。可先對照 [mod_php](/php/knowledge-cards/mod-php/) 與 [OPcache](/php/knowledge-cards/opcache/)。

## 概念位置

PHP-FPM 把直譯器放在 web 伺服器外面的常駐程序裡：程序活過很多請求，應用程式狀態仍然只活一個請求（[shared-nothing](/php/knowledge-cards/shared-nothing-request/)）。它只講 FastCGI，所以前面一定要有一個講 HTTP 的 web 伺服器（[nginx](/infra/knowledge-cards/nginx/) 或 Apache 的 `mod_proxy_fcgi`）。PHP 5.3.3 起隨 PHP 本體發行。

## 可觀察訊號與例子

- **`pm.max_children` 決定並發上限**：一個 worker 一次處理一個請求，超過上限的請求排隊，status 頁的 `max listen queue` 會大於 0。
- **502 加上「Connection reset by peer」**：worker 被 `request_terminate_timeout` 終止、或 reload／停機時沒有等進行中的請求（`process_control_timeout` 預設 0）。
- **預設監聽 `9000`**：FastCGI 沒有驗證，PHP 官方文件要求 php-fpm 不能讓不受信任的網路連到。
- **pool**：每個 pool 可以指定執行帳號，讓不同站台的 PHP 互相讀不到檔案。

## 設計責任

部署 PHP-FPM 要決定 `max_children`（以最重請求的記憶體峰值估）、`max_requests`、`request_terminate_timeout` 與 `process_control_timeout`，並把 FastCGI 埠限制在信任的網路內。各設定的實測見 [PHP-FPM](/php/01-server-runtime/php-fpm/)。
