---
title: "FileZilla"
date: 2026-06-26
description: "跨平台的 FTP/SFTP client，提供目錄同步瀏覽和檔案比較功能"
weight: 23
tags: ["infra", "knowledge-cards"]
---

FileZilla 是一套開源的 [FTP](/infra/knowledge-cards/ftp/) / SFTP / FTPS client，支援 Windows、macOS 和 Linux。它的介面分成本地和遠端兩側的檔案瀏覽器，讓使用者透過拖放或右鍵選單在本機與伺服器之間傳輸檔案。在無 SSH 的主機環境裡，FileZilla 是上傳程式碼和下載備份的主要工具。

## 概念位置

[FTP](/infra/knowledge-cards/ftp/) 是無 SSH 環境裡傳輸檔案的主要協定。FileZilla 把 FTP 操作從 CLI（如 `ftp` 或 `lftp` 指令）包裝成圖形介面，降低操作門檻。接手維運時，FileZilla 的角色是「把整個站台拉回本地」和「把改好的檔案推上 prod」。

## 可觀察訊號

以下情境會用到 FileZilla：接手的專案只有 FTP 帳密沒有 SSH key；部署方式是「FTP 上傳改過的檔案」；或者需要對比本地版本和伺服器版本的差異。

## 設計責任

使用 FileZilla 時有三個關鍵功能和注意事項。

**站台管理員**：儲存多組 FTP 連線設定（主機、帳號、密碼、port），避免每次手動輸入。接手時第一步是在站台管理員建好 prod 的連線，並確認協定選擇正確（FTP 明文、FTPS 加密、SFTP 走 SSH）。

**目錄比較**：「檢視 → 目錄比較 → 啟用」功能會標示本地與遠端的檔案差異——哪些本地較新、哪些遠端較新、哪些只存在於一邊。上傳前先跑目錄比較可以看到即將改動的範圍。

**隱藏檔**：預設不顯示以 `.` 開頭的檔案（如 `.htaccess`、`.env`、`.user.ini`）。要在「伺服器 → 強制顯示隱藏檔案」啟用，否則接手時會漏拉這些關鍵設定檔。

FTP 傳輸是逐檔覆寫、沒有原子性——上傳到一半斷線會讓伺服器上同時存在新舊版本的混合狀態。對關鍵檔案（`index.php`、`.htaccess`）的上傳需要額外小心。

## 鄰卡

無。FileZilla 是獨立工具。替代工具包括 WinSCP（Windows）、Cyberduck（macOS）、Transmit（macOS）。
