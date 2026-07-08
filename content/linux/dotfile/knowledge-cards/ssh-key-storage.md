---
title: "SSH 金鑰儲放與 authorized_keys"
date: 2026-07-08
description: "配置 SSH 免密碼登入、要知道私鑰放哪、公鑰怎麼授權、多裝置各自的鑰匙怎麼管、或高權限操作該不該給完整金鑰時回來讀"
weight: 50
tags: ["linux", "remote", "ssh", "security", "knowledge-cards"]
---

SSH 金鑰登入的模型是非對稱的一對鑰匙分兩處放：**私鑰留在客戶端、公鑰授權在伺服器**。私鑰是你的身分證明、絕不離開你的裝置；公鑰可以到處給、把它加進伺服器的授權清單就等於允許持有對應私鑰的人登入。搞清楚哪個放哪、authorized_keys 的角色、以及認證失敗為什麼會退回問密碼，是配置與除錯免密碼登入的基礎。

## 私鑰在客戶端、公鑰在伺服器

客戶端產一對鑰匙（`ssh-keygen`），預設放在 `~/.ssh/`：私鑰（如 `id_ed25519`、權限 `600`）留在本機、絕不外流；公鑰（`id_ed25519.pub`）是可以公開的那半。登入時客戶端用私鑰證明「我持有它」、伺服器用先前存好的公鑰驗證，全程私鑰不離開客戶端。私鑰外洩等於身分被冒用，所以它的權限與儲放是安全邊界——這也是為什麼私鑰不該進版控、見 [機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/) 的同類原則。

## authorized_keys 是授權清單

伺服器端的 `~/.ssh/authorized_keys`（權限 `600`、`~/.ssh` 為 `700`）是一份「允許誰登入這個帳號」的清單，一行一把公鑰。把一把公鑰加進去，就授權了持有對應私鑰的裝置。這個「一行一把」的結構天然支援 per-device 金鑰：Mac 一把、手機的 client 一把、CI 一把，各自產鑰、公鑰各佔一行，要撤銷某台裝置就刪掉它那行、不影響其他裝置。比所有裝置共用一把私鑰安全得多（共用時撤銷一台等於全部要換）。

## 認證失敗會退回問密碼

`sshd` 通常按順序試多種認證方法：公鑰不被接受時，會退回下一種（`keyboard-interactive` / 密碼）。所以「本來想用金鑰、卻被要求輸入密碼」的典型原因是公鑰沒被伺服器接受——公鑰沒加進 authorized_keys、或 `~/.ssh` / `authorized_keys` 權限太寬被 sshd 拒用（sshd 對權限很挑、太開放的權限會讓它忽略該檔）。判讀方向是看伺服器的 `journalctl -u sshd`：`Accepted publickey` 是金鑰成功、`Failed password` 代表退回了密碼且失敗。

## 信任邊界：不是每個場景都給完整金鑰

一把完整的 SSH 私鑰是高權限物——能登入、能做這個帳號能做的一切。所以「要不要把私鑰交出去」是信任邊界的判斷：讓自動化 / 第三方 / 容器裡的 agent 存取版本控制時，掛一把完整的 SSH key 等於把邊界打穿，範圍受限的 **deploy key**（只綁單一 repo、可設唯讀）是更小的授權面；或乾脆把高權限動作（如推送）留在你信任的 host 側、不進入低信任環境。授權面愈小、外洩的爆炸半徑愈小。

## 判讀訊號 / 邊界

- 免密碼登入失敗先查三處：公鑰在不在伺服器的 authorized_keys、`~/.ssh`（700）與 authorized_keys（600）權限對不對、客戶端有沒有指到對的私鑰。
- 金鑰登入的完整 bootstrap 流程（產鑰、佈署公鑰、驗證）見 [SSH 免密碼登入 bootstrap](/linux/install/ssh-keyless-bootstrap/)。
- 連得到 sshd 但認證失敗，跟「根本連不到」是不同層的問題——先用 [連線逾時 vs 連線被拒](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/) 分清楚是可達性還是認證。
