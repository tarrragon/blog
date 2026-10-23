---
title: "SSH Host Key 與 known_hosts（主機金鑰）"
date: 2026-10-23
description: "ssh 第一次連線問要不要信任指紋、出現 REMOTE HOST IDENTIFICATION HAS CHANGED 警告，或主機重建之後連不上時，查 host key 怎麼證明主機身分、known_hosts 記了什麼，以及首次信任的風險"
weight: 61
tags: ["infra", "knowledge-cards", "ssh", "security"]
---

SSH host key 是主機用來向用戶端證明自己身分的金鑰對，存在主機的 `/etc/ssh/ssh_host_*_key`（私鑰）與同名 `.pub`（公鑰）。用戶端第一次連線時看到的「指紋」就是這把公鑰的雜湊；用戶端確認之後把它記進 `~/.ssh/known_hosts`（全機共用的是 `/etc/ssh/ssh_known_hosts`），之後每次連線都比對主機出示的 host key 與記下的是否相同。可先對照 [SSH](/infra/knowledge-cards/ssh/)。

## 概念位置

host key 擋的是中間人攻擊：有人攔截連線、冒充目標主機時，他出示的 host key 與 `known_hosts` 記的不同，`ssh` 會拒絕連線。這個保護的弱點在第一次連線：用戶端還沒有任何記錄，只能由使用者判斷指紋對不對，這種做法叫 TOFU（trust on first use，首次使用時信任），而多數人不會去核對指紋。主機重建時 host key 重新產生，`ssh` 看到的就是一把不同的金鑰。[SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/) 的主機憑證把逐台信任換成信任一把主機 CA，用戶端在 `known_hosts` 用 `@cert-authority` 一行信任它。

## 可觀察訊號

- 第一次連線：`The authenticity of host '...' can't be established. ED25519 key fingerprint is SHA256:...`
- host key 與記錄不同：`WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`，連線被拒，訊息會指出 `known_hosts` 裡衝突的那一行
- `ssh-keyscan <host>` 取得主機出示的公鑰；`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` 在主機上印出指紋，可以與用戶端看到的對照

## 設計責任

主機經常重建的環境裡，指紋變更警告會天天出現，管理員會被訓練成直接刪掉舊記錄、接受新的，而真正的中間人攻擊看起來一模一樣。這種環境改用主機憑證，或讓建立主機的流程把新的 host key 公鑰派送到用戶端的 `/etc/ssh/ssh_known_hosts`；不把 `StrictHostKeyChecking no` 當成長期做法。看到指紋變更而不確定主機是否重建過時，先從另一條路徑（雲端主控台、序列主控台）在主機上印出指紋核對，再更新記錄。

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — host key 是 SSH 連線建立時的主機驗證
- [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/) — 主機憑證取代逐台確認指紋
- 實作見 [OpenSSH 內建 CA 的 SSH 憑證導入](/infra/03-network-foundation/openssh-ca-setup/)
