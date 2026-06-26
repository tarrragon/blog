---
title: "SSH"
date: 2026-06-26
description: "Secure Shell — 加密的遠端 shell 連線，有 SSH 等於有 CLI 工具鏈，沒有就只能靠 FTP 和 web 面板"
weight: 30
tags: ["infra", "knowledge-cards"]
---

SSH（Secure Shell）是加密的遠端 shell 連線協定，讓操作者在本地終端機執行遠端伺服器上的指令。連線建立後，操作者看到的是遠端伺服器的命令列——可以跑任何該伺服器上安裝的 CLI 工具。

## 概念位置

SSH 在接手維運的情境裡是一條關鍵分界線：有 SSH 存取就能用 `mysqldump`、`git`、`systemctl` 等 CLI 工具操作伺服器；沒有 SSH 就只能用 FTP 傳檔案、用 phpMyAdmin 管資料庫、用 cPanel 改設定。兩種情境的操作流程和可用工具完全不同。

## 可觀察訊號

判斷有沒有 SSH 存取：嘗試 `ssh user@host`。如果連線成功進入命令列就有；如果 timeout 或被拒，可能是主機不開放 SSH（共享主機常見）、或 port 不是預設的 22、或需要 IP 白名單。cPanel 的「終端機」功能有時提供 web-based SSH，但功能受限。

## 設計責任

SSH 的認證方式有兩種：密碼（簡單但不安全，容易被暴力嘗試）和 SSH key pair（公鑰放在 server 的 `~/.ssh/authorized_keys`，私鑰留在 client）。生產環境應該用 key 認證並關閉密碼登入。

接手維運時要確認：SSH 的登入帳號是什麼、用密碼還是 key、key 在哪裡、有沒有其他人也有存取權限。前任維護者的 SSH key 如果還在 `authorized_keys` 裡，離職後應該移除。

```bash
# 產生 SSH key pair
ssh-keygen -t ed25519 -C "your-email@example.com"

# 把公鑰加到遠端 server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host
```

## 鄰卡

- [FTP](/infra/knowledge-cards/ftp/) — 沒有 SSH 時的檔案傳輸替代方案
