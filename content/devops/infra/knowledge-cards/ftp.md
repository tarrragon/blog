---
title: "FTP"
date: 2026-06-26
description: "File Transfer Protocol — 檔案傳輸協定，無 SSH 環境的主要檔案管理方式。SFTP 和 FTPS 是其加密變體"
weight: 31
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/ftp/"]
---

FTP（File Transfer Protocol）是把檔案在本地電腦與遠端伺服器之間上傳/下載的協定。操作者透過 FTP client（如 [FileZilla](/devops/infra/knowledge-cards/filezilla/)）連線到伺服器，看到遠端的目錄結構，用拖放或指令傳輸檔案。

## 跟其他概念的關係

FTP 在無 [SSH](/devops/infra/knowledge-cards/ssh/) 的環境裡是唯一的檔案管理途徑——程式碼部署靠 FTP 上傳、備份靠 FTP 下載、檔案比對靠 FTP client 的目錄比較功能。它是接手維運模組「無 SSH 環境」路線的核心工具。

## FTP 的變體

| 協定 | 加密方式                    | 常見情境            |
| ---- | --------------------------- | ------------------- |
| FTP  | 無加密（明文傳輸）          | 老舊主機、內部網路  |
| FTPS | FTP + TLS 加密              | 支援 SSL 的主機     |
| SFTP | 走 SSH 通道（完全不同協定） | 有 SSH 存取的伺服器 |

多數 FTP client（FileZilla、WinSCP）同時支援三種協定。如果伺服器有 SSH，用 SFTP 比 FTP 安全且功能更多。

## 可觀察訊號

FTP 操作的三個限制在接手維運時要意識到：第一，非原子操作——檔案逐一上傳，上傳過程中伺服器上同時存在新舊版本的混合狀態。第二，不支援指令執行——只能傳檔案、不能跑腳本或重啟服務。第三，沒有版本控制——上傳覆蓋就是覆蓋，沒有 diff、沒有 rollback。

## 判斷條件與後果

FTP 只負責傳輸，不提供版本控制與原子性，部署時這兩項要由傳輸以外的步驟補上。本地沒有先 Git commit 就上傳時，上傳的版本在任何地方都沒有紀錄，覆蓋之後沒有 diff 可看、也沒有版本可退；上傳前沒有用目錄比較確認差異時，覆蓋的範圍要等傳完才知道；`index.php`、`.htaccess` 這類關鍵檔案被蓋成錯的版本、或上傳到一半斷線時，站台直接受影響，而伺服器上原本那一份只有事先下載的備份救得回來。所以上傳前依序做三件事：本地 commit、目錄比較、從伺服器下載關鍵檔案的備份。

## 鄰卡

- [SSH](/devops/infra/knowledge-cards/ssh/) — 有 SSH 時用 SFTP 或 SCP 替代 FTP
- [FileZilla](/devops/infra/knowledge-cards/filezilla/) — 最常用的 FTP client
