---
title: "cPanel"
date: 2026-06-26
description: "Web 主機管理面板，提供 PHP 版本切換、cron、email、SSL、備份等功能的圖形介面"
weight: 24
tags: ["infra", "knowledge-cards"]
---

cPanel 是最常見的 Web 主機管理面板，讓租用主機的使用者透過瀏覽器管理伺服器的常用功能——PHP 版本切換、[cron](/infra/knowledge-cards/cron/) job 排程、email 帳號管理、SSL 憑證安裝、檔案管理、資料庫管理、以及完整備份。Plesk 是同類產品，功能範圍相似但介面和設定路徑不同。

## 概念位置

cPanel 是無 SSH 環境裡的「控制中心」。它整合了多種工具的圖形入口：[phpMyAdmin](/infra/knowledge-cards/phpmyadmin/)（資料庫）、檔案管理員（web 版 FTP）、PHP 設定、cron 編輯器、SSL/TLS 管理。接手維運時，第一步是確認有沒有 cPanel 存取權——有的話很多操作（備份、PHP 版本、cron）可以在面板裡完成，不需要 SSH。

## 可觀察訊號

以下情境代表環境有 cPanel：主機商提供了 cPanel 登入 URL（通常是 `domain:2083`）；接手時收到的帳密包含「cPanel 帳號」；或者主機商的服務說明提到 cPanel / WHM。

## 設計責任

接手維運時，cPanel 有幾個關鍵功能要確認：

**完整備份**：「備份精靈」可以一次打包整個帳號（檔案 + 資料庫 + email + cron + DNS 設定）。這是最快的「拍下現況」方式——比 FTP 逐檔拉 + phpMyAdmin 匯出快得多。但完整備份通常只能下載、不能自動排程到外部儲存（部分主機商限制）。

**PHP 版本選擇器**：可以切換整個帳號或單一域名的 PHP 版本。升級 PHP 時，可以先在 staging 子域名切到新版本測試、確認沒問題再切主域名。這是無 SSH 環境裡最安全的 PHP 升級方式。

**cron job 管理**：圖形介面設定排程任務，語法是 cron 標準格式。接手時要截圖或匯出所有 cron——它們可能是系統運作的隱性依賴（定期清快取、寄報表、同步資料）。

**SSL/TLS**：管理 HTTPS 憑證。部分主機商整合了 Let's Encrypt 自動簽發，部分需要手動上傳憑證。

## 鄰卡

- [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/)：通常內嵌在 cPanel 的「資料庫」區塊裡
