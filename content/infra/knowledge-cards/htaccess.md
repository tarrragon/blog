---
title: ".htaccess"
date: 2026-06-26
description: "Apache Web Server 的目錄層級設定檔，控制 URL rewrite、存取權限、PHP 設定覆寫與安全標頭"
weight: 25
tags: ["infra", "knowledge-cards"]
---

`.htaccess`（Hypertext Access）是 Apache Web Server 的目錄層級設定檔。它讓使用者在沒有伺服器管理員權限的情況下，覆寫 Apache 的部分全域設定——包括 URL 重寫規則、目錄存取控制、PHP 設定覆寫、HTTPS 強制跳轉、以及 HTTP 安全標頭。每個目錄可以有自己的 `.htaccess`，Apache 處理請求時會從根目錄到目標目錄逐層讀取並套用。常搭配 [php.ini / .user.ini](/infra/knowledge-cards/php-ini/) 一起管理 PHP 應用的行為。

## 概念位置

在 Apache 為主的主機環境（多數共享主機和部分 VPS），`.htaccess` 是不需要重啟伺服器就能調整行為的設定機制。WordPress、Laravel、Drupal 等 PHP 框架都依賴 `.htaccess` 的 URL rewrite 規則來實現 pretty URL（把 `/blog/post-title` 轉成 `index.php?page=post-title`）。相對地 [nginx](/infra/knowledge-cards/nginx/) 沒有對等機制、設定要集中寫在主設定檔。

## 可觀察訊號

站台根目錄有 `.htaccess` 檔案（注意它是隱藏檔，FTP client 要啟用「顯示隱藏檔案」才看得到）。上傳目錄（`uploads/`）、後台目錄（`admin/`、`wp-admin/`）可能各有一份獨立的 `.htaccess` 做額外的存取控制。

## 設計責任

接手維運時，`.htaccess` 要注意四件事：

**URL rewrite 規則**：這些規則決定了站台的 URL 結構。亂改或刪除會讓所有內頁都回 404。修改前先備份原始版本。

**安全設定**：`Options -Indexes` 禁止目錄列表、`php_flag engine off` 禁止上傳目錄執行 PHP、`Require all denied` 禁止存取 `.env` 等機密檔案。這些設定分散在多個目錄的 `.htaccess` 裡，接手時要全部找出來。

**PHP 設定覆寫**：部分 PHP 設定（如 `upload_max_filesize`、`max_execution_time`）可以在 `.htaccess` 裡用 `php_value` 或 `php_flag` 指令覆寫。這些覆寫可能不在 `php.ini` 裡，只存在於 `.htaccess`。

**遷移到 nginx 的影響**：nginx 沒有 `.htaccess` 的對等機制——所有設定都在集中的 nginx 設定檔裡。從 Apache 遷移到 nginx 時，`.htaccess` 裡的每一條規則都要手動轉換成 nginx 語法。

## 鄰卡

- [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)：`.htaccess` 管 Apache 行為，`.user.ini` 管 PHP 行為，兩者互補
