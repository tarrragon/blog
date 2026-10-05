---
title: "ZTS（Zend Thread Safety）"
date: 2026-10-05
description: "在 php -i 看到 Thread Safety 是 enabled 或 disabled，或要判斷某個 PHP 能不能跑在多執行緒的伺服器（Apache worker/event MPM、FrankenPHP）裡時"
weight: 4
tags: ["php", "knowledge-cards"]
---

ZTS（Zend Thread Safety）是 PHP 的編譯選項（`--enable-zts`）：開啟之後，PHP 把每個請求的狀態放在各執行緒自己的儲存區，而不是全域變數裡，多個執行緒才能同時執行 PHP 而不互相覆寫。沒有開 ZTS 的版本叫 NTS（Non Thread Safe）。可先對照 [mod_php](/php/knowledge-cards/mod-php/) 與 [SAPI](/php/knowledge-cards/sapi/)。

## 概念位置

ZTS 決定 PHP 能不能住在一個多執行緒的程序裡。PHP 跑在獨立程序裡的執行方式（CGI、[PHP-FPM](/php/knowledge-cards/php-fpm/)）不需要它，每個 worker 一次只處理一個請求；PHP 嵌在多執行緒伺服器裡時需要它：mod_php 要搭配 Apache 的 worker 或 event MPM、FrankenPHP 用執行緒當 worker。

## 可觀察訊號與例子

- **`php -i | grep "Thread Safety"`**：`php:8.5-apache` 與 `php:8.5-fpm-alpine` 是 `disabled`，FrankenPHP 映像檔是 `enabled`。
- **mod_php 只能用 prefork**：PHP 官方安裝文件寫明，除非以 `--enable-zts` 編譯，mod_php 需要 prefork MPM。
- **擴充也要支援**：PHP 能以執行緒安全的方式執行，不代表每個擴充與它依賴的 C 函式庫都能。

## 設計責任

選執行模型時，ZTS 是前提條件之一：要讓 Apache 用執行緒、或採用 FrankenPHP，就要拿到 ZTS 版的 PHP 與相容的擴充。不需要執行緒時，NTS 版本較常見、擴充相容性也較好。
