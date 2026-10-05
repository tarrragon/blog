---
title: "Shared-nothing 請求模型"
date: 2026-10-05
description: "要判斷 PHP 的全域變數、static 變數或類別靜態屬性會不會留到下一個請求，或評估換成常駐 worker（Octane、FrankenPHP worker）時哪些程式碼會出問題時"
weight: 2
tags: ["php", "knowledge-cards"]
---

Shared-nothing 請求模型的核心概念是「每個請求結束時，PHP 清空這個請求裡由 PHP 程式碼建立的全部狀態」：全域變數、函式內的 `static` 變數、類別的靜態屬性、物件與一般的資源都在請求結束時釋放，下一個請求從空白開始，即使由同一個程序處理。可先對照 [SAPI](/php/knowledge-cards/sapi/) 與 [OPcache](/php/knowledge-cards/opcache/)。

## 概念位置

Shared-nothing 是 PHP 傳統執行方式（CGI、[mod_php](/php/knowledge-cards/mod-php/)、[PHP-FPM](/php/knowledge-cards/php-fpm/)）共有的狀態壽命：程序可能活過很多請求，狀態只活一個請求。它清的是 PHP 程式碼建立的狀態，程序層的資源（OPcache、持久連線、APCu）不在範圍內。常駐 worker 模型（FrankenPHP 的 worker 模式、Laravel Octane）放棄了它。

## 可觀察訊號與例子

- **同一個 PID、計數器仍是 1**：在 PHP-FPM 下對一支每次把 `static` 變數加一的腳本連續請求，同一個 worker 處理第二次時計數器仍然是 1。
- **常駐 worker 下計數器累加**：同一段程式碼放進 Octane 或 FrankenPHP worker，計數器變成 1、2、3……，往靜態陣列塞資料的程式會讓記憶體隨請求數線性增長。
- **框架每個請求重新啟動**：Laravel 這類框架每個請求都要重建服務容器、讀設定、建路由表，這段成本是 shared-nothing 的代價。

## 設計責任

在 shared-nothing 下，程式可以放心把請求資料放在靜態屬性裡；要換成常駐 worker 之前，這類寫法都要改掉。實測與要避開的寫法見 [常駐 worker 模型](/php/01-server-runtime/long-running-workers/)。
