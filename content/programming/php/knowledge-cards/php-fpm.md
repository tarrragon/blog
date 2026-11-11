---
title: "PHP-FPM（FastCGI Process Manager）"
date: 2026-10-05
description: "在 Nginx 或容器環境看到 php-fpm、9000 埠、pool 設定或 502 Bad Gateway，要知道 PHP-FPM 負責什麼、哪些設定決定並發與記憶體時"
weight: 5
tags: ["php", "php-fpm", "knowledge-cards"]
aliases: ["/php/knowledge-cards/php-fpm/"]
---

PHP-FPM 是 PHP 內建的 FastCGI 程序管理器：一個 master 程序加一群常駐的 worker，master 負責讀設定、開 worker、補死掉的 worker 與處理訊號，worker 實際執行 PHP，透過 FastCGI 協定接收 web 伺服器轉來的請求。它的 [SAPI](/programming/php/knowledge-cards/sapi/) 名稱是 `fpm-fcgi`。可先對照 [mod_php](/programming/php/knowledge-cards/mod-php/) 與 [OPcache](/programming/php/knowledge-cards/opcache/)。

## 跟其他概念的關係

PHP-FPM 把直譯器放在 web 伺服器外面的常駐程序裡：程序活過很多請求，應用程式狀態仍然只活一個請求（[shared-nothing](/programming/php/knowledge-cards/shared-nothing-request/)）。它只講 FastCGI，所以前面一定要有一個講 HTTP 的 web 伺服器（[nginx](/devops/infra/knowledge-cards/nginx/) 或 Apache 的 `mod_proxy_fcgi`）。PHP 5.3.3 起隨 PHP 本體發行。

## 可觀察訊號與例子

- **`pm.max_children` 決定並發上限**：一個 worker 一次處理一個請求，超過上限的請求排隊，status 頁的 `max listen queue` 會大於 0。
- **502 加上「Connection reset by peer」**：worker 被 `request_terminate_timeout` 終止、或 reload／停機時沒有等進行中的請求（`process_control_timeout` 預設 0）。
- **預設監聽 `9000`**：FastCGI 沒有驗證，PHP 官方文件要求 php-fpm 不能讓不受信任的網路連到。
- **pool**：每個 pool 可以指定執行帳號，讓不同站台的 PHP 互相讀不到檔案。

## 判斷條件與後果

部署 PHP-FPM 時，四個程序管理設定與 FastCGI 埠的開放範圍各自對應一種失效。`max_children` 是並發上限：設得比記憶體容得下的多，最重的請求同時執行時記憶體耗盡；設得太少，請求在 listen queue 排隊，所以它以最重請求的記憶體峰值估。`max_requests` 讓 worker 處理到一定次數後重啟，沒有設時，擴充或程式碼的記憶體洩漏在常駐的 worker 裡一直累積。`request_terminate_timeout` 終止執行太久的請求，web 伺服器收到 502 加上「Connection reset by peer」；`process_control_timeout` 預設 0，reload 或停機時不等進行中的請求，同樣產生 502。FastCGI 沒有驗證，任何連得到這個埠的客戶端都能送請求讓 PHP 執行，所以這個埠只開給信任的網路。各設定的實測見 [PHP-FPM](/programming/php/01-server-runtime/php-fpm/)。
