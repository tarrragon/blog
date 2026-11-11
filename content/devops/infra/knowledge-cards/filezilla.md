---
title: "FileZilla"
date: 2026-06-26
description: "跨平台的 FTP/SFTP client，提供目錄同步瀏覽和檔案比較功能"
weight: 23
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/filezilla/"]
---

FileZilla 是一套開源的 [FTP](/devops/infra/knowledge-cards/ftp/) / SFTP / FTPS client，支援 Windows、macOS 和 Linux。它的介面分成本地和遠端兩側的檔案瀏覽器，讓使用者透過拖放或右鍵選單在本機與伺服器之間傳輸檔案。在無 SSH 的主機環境裡，FileZilla 是上傳程式碼和下載備份的主要工具。

## 跟其他概念的關係

[FTP](/devops/infra/knowledge-cards/ftp/) 是無 SSH 環境裡傳輸檔案的主要協定。FileZilla 把 FTP 操作從 CLI（如 `ftp` 或 `lftp` 指令）包裝成圖形介面，降低操作門檻。接手維運時，FileZilla 的角色是「把整個站台拉回本地」和「把改好的檔案推上 prod」。

## 可觀察訊號

以下情境會用到 FileZilla：接手的專案只有 FTP 帳密沒有 SSH key；部署方式是「FTP 上傳改過的檔案」；或者需要對比本地版本和伺服器版本的差異。

## 判斷條件與後果

FileZilla 的三項功能各自對應接手維運時的一種失誤：連線設定選錯協定、上傳蓋掉不該蓋的檔案、下載漏掉設定檔。

**站台管理員**：儲存多組連線設定（主機、帳號、密碼、port）與各自的協定。每次手動輸入時協定也每次重選，選到 FTP 時帳密以明文傳過網路；在站台管理員建好 prod 的連線並選定協定（FTP 明文、FTPS 加密、SFTP 走 SSH）之後，每次連線都用同一組設定。

**目錄比較**：「檢視 → 目錄比較 → 啟用」標出哪些檔案本地較新、哪些遠端較新、哪些只存在於一邊。上傳前沒有比較時，覆蓋的範圍要等傳完才知道，遠端較新的檔案（直接改在伺服器上的那一份）會被本地的舊版蓋掉。

**隱藏檔**：預設不顯示以 `.` 開頭的檔案（如 `.htaccess`、`.env`、`.user.ini`），整站拉回本地時這些檔案不在傳輸清單裡，本地副本缺了 rewrite 規則與機密設定。在「伺服器 → 強制顯示隱藏檔案」啟用之後，它們才會一起傳。

FTP 傳輸逐檔覆寫、沒有原子性，上傳到一半斷線時伺服器上同時存在新舊版本。`index.php`、`.htaccess` 這類每個請求都會讀到的檔案處在半新半舊時，整個站台的回應都受影響，所以這類檔案上傳前先從伺服器下載一份備份。

## 鄰卡

無。FileZilla 是獨立工具。替代工具包括 WinSCP（Windows）、Cyberduck（macOS）、Transmit（macOS）。
