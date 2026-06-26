---
title: "phpMyAdmin"
date: 2026-06-26
description: "Web 介面的 MySQL / MariaDB 管理工具，透過瀏覽器操作資料庫"
weight: 22
tags: ["infra", "knowledge-cards"]
---

phpMyAdmin 是一套透過瀏覽器操作 MySQL 和 MariaDB 的 Web 應用程式。它提供圖形介面執行 SQL 查詢、瀏覽資料表、匯出與匯入資料庫、修改 schema（新增欄位、改索引、刪表）、以及管理使用者權限。多數主機商在安裝 cPanel 或 Plesk 時會一併預裝，讓租用主機的使用者不需要 SSH 就能管理資料庫。

## 概念位置

在無 SSH 的主機環境裡，phpMyAdmin 通常是唯一可用的資料庫管理入口。它取代了 `mysql` CLI client 和 `mysqldump` 指令的角色——查詢用 SQL 編輯器、匯出用匯出頁面、匯入用上傳 SQL 檔。接手維運時，phpMyAdmin 是拍下資料庫現況（SQL dump）的主要工具。

## 可觀察訊號

以下情境會遇到 phpMyAdmin：主機面板（cPanel / Plesk）裡有「phpMyAdmin」按鈕可以進入；接手的專案的資料庫操作文件提到「在 phpMyAdmin 裡執行」；或者專案的部署流程包含「登入 phpMyAdmin 匯入 SQL」。

## 設計責任

使用 phpMyAdmin 時要處理三個限制。第一是匯出 timeout：大資料庫（50MB 以上）的匯出可能因為 PHP 的 `max_execution_time` 限制而中斷，需要分表匯出或調整 phpMyAdmin 設定。第二是沒有 CLI 可腳本化：所有操作都要手動點擊，無法排程自動備份。第三是安全暴露：phpMyAdmin 掛在 web 上、可被外部存取，如果沒有設密碼保護或 IP 白名單，等於把資料庫管理介面開給全世界。

如果主機允許遠端 MySQL 連線（port 3306 開放），可以改用桌面工具（DBeaver、TablePlus、HeidiSQL）直連資料庫，繞過 phpMyAdmin 的 timeout 限制。

## 鄰卡

- [cPanel](/infra/knowledge-cards/cpanel/)：phpMyAdmin 通常內嵌在 cPanel 裡
