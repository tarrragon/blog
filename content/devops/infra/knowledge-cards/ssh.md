---
title: "SSH"
date: 2026-06-26
description: "Secure Shell — 加密的遠端 shell 連線，有 SSH 等於有 CLI 工具鏈，沒有就只能靠 FTP 和 web 面板"
weight: 30
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/ssh/"]
---

SSH（Secure Shell）是加密的遠端 shell 連線協定，讓操作者在本地終端機執行遠端伺服器上的指令。連線建立後，操作者看到的是遠端伺服器的命令列——可以跑任何該伺服器上安裝的 CLI 工具。SSH 建立安全連線所依賴的公私鑰機制，跟 [SSL/TLS](/devops/infra/knowledge-cards/ssl-tls/) 以數位憑證驗證伺服器身分同屬非對稱加密的應用。

## 跟其他概念的關係

SSH 在接手維運的情境裡是一條關鍵分界線：有 SSH 存取就能用 `mysqldump`、`git`、`systemctl` 等 CLI 工具操作伺服器；沒有 SSH 就只能用 [FTP](/devops/infra/knowledge-cards/ftp/) 傳檔案、用 phpMyAdmin 管資料庫、用 cPanel 改設定。兩種情境的操作流程和可用工具完全不同。

## 可觀察訊號

判斷有沒有 SSH 存取：嘗試 `ssh user@host`。如果連線成功進入命令列就有；如果 timeout 或被拒，可能是主機不開放 SSH（共享主機常見）、或 port 不是預設的 22、或需要 IP 白名單。cPanel 的「終端機」功能有時提供 web-based SSH，但功能受限。

## 判斷條件與後果

SSH 的認證方式有兩種：密碼與 SSH key pair（公鑰放在 server 的 `~/.ssh/authorized_keys`，私鑰留在 client）。伺服器開著密碼登入、而且 SSH 埠對外開放時，任何人都能對它反覆猜密碼，帳號的安全只剩密碼的強度；只收 key 時，沒有對應私鑰的連線在認證這一步就被拒絕，所以生產環境關閉密碼登入、只收 key。

接手一台主機時，誰能登入它寫在 `authorized_keys` 與帳號密碼裡，而不在任何一份交接文件裡。前任維護者的公鑰還留在 `authorized_keys` 時，他離職之後仍然登入得了；所以接手時逐一列出登入帳號、認證方式、key 的位置與還有誰持有存取權，不認得的公鑰移除。主機一多，逐台刪除就難以盤點，這時改用隨帳號收回的 [OS Login](/devops/infra/knowledge-cards/os-login/) 或會自動到期的 [SSH Certificate（SSH 憑證）](/devops/infra/knowledge-cards/ssh-certificate/)，選擇條件見[伺服器管理通道的設計](/devops/infra/03-network-foundation/management-access-channel/)的〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉。

```bash
# 產生 SSH key pair
ssh-keygen -t ed25519 -C "your-email@example.com"

# 把公鑰加到遠端 server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host
```

## 鄰卡

- [FTP](/devops/infra/knowledge-cards/ftp/) — 沒有 SSH 時的檔案傳輸替代方案
- [SSH Certificate（SSH 憑證）](/devops/infra/knowledge-cards/ssh-certificate/) — 由 CA 簽發、會自動到期的 SSH 金鑰
- [OS Login](/devops/infra/knowledge-cards/os-login/) — GCP 上讓登入權限跟著帳號收回的做法
- [Bastion Host（跳板機）](/devops/infra/knowledge-cards/bastion-host/) — 只有一台主機對外開 SSH、其餘經由它轉接
