---
title: "OPcache"
date: 2026-10-05
description: "部署新版程式碼之後頁面還在跑舊版、評估 OPcache 的大小設定，或比較不同執行模型下 PHP 的效能差距時"
weight: 6
tags: ["php", "opcache", "knowledge-cards"]
---

OPcache 是 PHP 內建的擴充，把 PHP 檔案編譯好的 opcode（Zend 引擎執行的指令）存進共享記憶體，之後執行同一個檔案時跳過讀檔與編譯。它快取的是程式碼的編譯結果，不是資料。可先對照 [PHP-FPM](/php/knowledge-cards/php-fpm/) 與 [Shared-nothing 請求模型](/php/knowledge-cards/shared-nothing-request/)。

## 概念位置

OPcache 是程序層的資源，效果取決於執行 PHP 的程序活多久：CGI 每個請求一個新程序，快取永遠命中不了；[PHP-FPM](/php/knowledge-cards/php-fpm/) 與 [mod_php](/php/knowledge-cards/mod-php/) 的父程序建立共享記憶體，所有 worker 共用同一份快取。PHP 8.5 起 OPcache 靜態編進 PHP 本體。它省掉的是編譯，框架每個請求的啟動流程它省不掉，那一段要靠常駐 worker 模型。

## 可觀察訊號與例子

- **`opcache_get_status()` 的 `hits`**：CGI 下永遠是 0；PHP-FPM 下跨 worker 累加。
- **改了檔案頁面不變**：`opcache.validate_timestamps=0` 時 OPcache 不檢查檔案，要 reload PHP-FPM 才生效；預設的 `validate_timestamps=1`、`revalidate_freq=2` 下，改檔後最多約 2 秒生效。
- **開與關的差距**：Laravel 13 骨架的健康檢查請求，開 OPcache 約 3.8 ms、關掉約 49.3 ms。
- **快取滿了不報錯**：放不進去的檔案每次重新編譯，從外面看只是變慢；要讀 `free_memory` 與 `num_cached_scripts`。

## 設計責任

部署要配合 `validate_timestamps` 的設定：程式碼在映像檔裡的容器部署可以關掉檢查，覆寫檔案的部署要留著或在換完程式碼後 reload。`memory_consumption` 與 `max_accelerated_files` 依實際專案跑過主要請求後的統計調整。詳見 [OPcache 與程序壽命](/php/01-server-runtime/opcache/)。
