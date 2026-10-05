---
title: "PHP 知識卡"
date: 2026-10-05
description: "PHP 執行模型的核心術語：SAPI、shared-nothing、mod_php、ZTS、PHP-FPM、OPcache"
weight: 100
tags: ["php", "knowledge-cards"]
---

PHP 知識卡收錄 PHP 執行模型的術語。每張卡自包含、可獨立閱讀；情境推導與實測在 [伺服器上的 PHP 執行模型](/php/01-server-runtime/) 各篇。

## 卡片清單

| 卡片                                                                    | 說明                                                              |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [SAPI](/php/knowledge-cards/sapi/)                                      | PHP 核心與外部環境之間的介面，決定 PHP 怎麼被啟動、請求怎麼交進來 |
| [Shared-nothing 請求模型](/php/knowledge-cards/shared-nothing-request/) | 每個請求結束時清空 PHP 程式碼建立的全部狀態，下一個請求從空白開始 |
| [mod_php](/php/knowledge-cards/mod-php/)                                | 以 Apache 模組形式載入的 PHP，直譯器住在 Apache 的子程序裡        |
| [ZTS](/php/knowledge-cards/zts/)                                        | Zend Thread Safety，讓 PHP 能在多執行緒的伺服器裡執行的編譯選項   |
| [PHP-FPM](/php/knowledge-cards/php-fpm/)                                | 管理一群常駐 PHP worker、用 FastCGI 接請求的程序管理器            |
| [OPcache](/php/knowledge-cards/opcache/)                                | 把 PHP 檔案編譯好的 opcode 存在共享記憶體裡重用的內建擴充         |
