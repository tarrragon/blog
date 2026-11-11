---
title: ".htaccess"
date: 2026-06-26
description: "Apache Web Server 的目錄層級設定檔，控制 URL rewrite、存取權限、PHP 設定覆寫與安全標頭"
weight: 25
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/htaccess/"]
---

`.htaccess`（Hypertext Access）是 Apache Web Server 的目錄層級設定檔。它讓使用者在沒有伺服器管理員權限的情況下，覆寫 Apache 的部分全域設定——包括 URL 重寫規則、目錄存取控制、PHP 設定覆寫、HTTPS 強制跳轉、以及 HTTP 安全標頭。每個目錄可以有自己的 `.htaccess`，Apache 處理請求時會從根目錄到目標目錄逐層讀取並套用。常搭配 [php.ini / .user.ini](/devops/infra/knowledge-cards/php-ini/) 一起管理 PHP 應用的行為。

## 跟其他概念的關係

在 Apache 為主的主機環境（多數共享主機和部分 VPS），`.htaccess` 是不需要重啟伺服器就能調整行為的設定機制。WordPress、Laravel、Drupal 等 PHP 框架都依賴 `.htaccess` 的 URL rewrite 規則來實現 pretty URL（把 `/blog/post-title` 轉成 `index.php?page=post-title`）。相對地 [nginx](/devops/infra/knowledge-cards/nginx/) 沒有對等機制、設定要集中寫在主設定檔。

## 可觀察訊號

站台根目錄有 `.htaccess` 檔案（注意它是隱藏檔，FTP client 要啟用「顯示隱藏檔案」才看得到）。上傳目錄（`uploads/`）、後台目錄（`admin/`、`wp-admin/`）可能各有一份獨立的 `.htaccess` 做額外的存取控制。

## 判斷條件與後果

`.htaccess` 的規則分散在各目錄的隱藏檔裡、每次請求即時生效，站台的 URL 結構、存取限制與 PHP 設定可能只記錄在這些檔案裡。接手維運時漏看其中一類，各有不同的後果：

**URL rewrite 規則**：這些規則決定站台的 URL 結構，改錯或刪除時所有內頁都回 404。規則存檔就生效、檔案本身沒有版本紀錄，所以修改前先備份原始版本。

**安全設定**：`Options -Indexes` 禁止目錄列表、`php_flag engine off` 禁止上傳目錄執行 PHP、`Require all denied` 禁止存取 `.env` 等機密檔案。這些設定分散在多個目錄的 `.htaccess` 裡，搬站或重建時漏掉其中一份，那個目錄就失去對應的保護：上傳目錄裡的 PHP 檔可以被執行，或 `.env` 可以被直接下載。

**PHP 設定覆寫**：`upload_max_filesize`、`max_execution_time` 這類設定可以在 `.htaccess` 裡用 `php_value` 或 `php_flag` 覆寫。覆寫只存在於 `.htaccess` 時，只讀 `php.ini` 得到的不是目前生效的值，搬到新主機而漏了這份 `.htaccess` 時，這些設定變回 `php.ini` 的值。

**遷移到 nginx**：nginx 沒有 `.htaccess` 的對等機制，設定集中在 nginx 設定檔裡，`.htaccess` 裡的每一條規則都要手動轉換成 nginx 語法。沒轉到的規則在 nginx 上不存在：rewrite 規則沒轉，內頁回 404；安全設定沒轉，那個目錄失去保護。

## 鄰卡

- [php.ini / .user.ini](/devops/infra/knowledge-cards/php-ini/)：`.htaccess` 管 Apache 行為，`.user.ini` 管 PHP 行為，兩者互補
