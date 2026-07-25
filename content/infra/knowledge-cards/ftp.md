---
title: "FTP"
date: 2026-06-26
description: "File Transfer Protocol — 檔案傳輸協定，無 SSH 環境的主要檔案管理方式。SFTP 和 FTPS 是其加密變體"
weight: 31
tags: ["infra", "knowledge-cards"]
---

FTP（File Transfer Protocol）是把檔案在本地電腦與遠端伺服器之間上傳/下載的協定。操作者透過 FTP client（如 [FileZilla](/infra/knowledge-cards/filezilla/)）連線到伺服器，看到遠端的目錄結構，用拖放或指令傳輸檔案。

## 概念位置

FTP 在無 [SSH](/infra/knowledge-cards/ssh/) 的環境裡是唯一的檔案管理途徑——程式碼部署靠 FTP 上傳、備份靠 FTP 下載、檔案比對靠 FTP client 的目錄比較功能。它是接手維運模組「無 SSH 環境」路線的核心工具。

## FTP 的變體

| 協定 | 加密方式                    | 常見情境            |
| ---- | --------------------------- | ------------------- |
| FTP  | 無加密（明文傳輸）          | 老舊主機、內部網路  |
| FTPS | FTP + TLS 加密              | 支援 SSL 的主機     |
| SFTP | 走 SSH 通道（完全不同協定） | 有 SSH 存取的伺服器 |

多數 FTP client（FileZilla、WinSCP）同時支援三種協定。如果伺服器有 SSH，用 SFTP 比 FTP 安全且功能更多。

## 可觀察訊號

FTP 操作的三個限制在接手維運時要意識到：第一，非原子操作——檔案逐一上傳，上傳過程中伺服器上同時存在新舊版本的混合狀態。第二，不支援指令執行——只能傳檔案、不能跑腳本或重啟服務。第三，沒有版本控制——上傳覆蓋就是覆蓋，沒有 diff、沒有 rollback。

## 設計責任

用 FTP 部署時要建立的紀律：本地先 Git commit 再上傳（Git 提供版本控制、FTP 只負責傳輸）；上傳前用目錄比較確認差異；關鍵檔案（`index.php`、`.htaccess`）上傳前先從 server 下載一份備份。

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 有 SSH 時用 SFTP 或 SCP 替代 FTP
- [FileZilla](/infra/knowledge-cards/filezilla/) — 最常用的 FTP client
