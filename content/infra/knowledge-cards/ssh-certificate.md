---
title: "SSH Certificate（SSH 憑證）"
date: 2026-10-23
description: "主機多、人員常異動而逐台收回 authorized_keys 跟不上，或要讓 SSH 登入權限自動到期時，查 SSH CA 簽發短期憑證的運作方式與導入時要決定的事"
weight: 56
tags: ["infra", "knowledge-cards", "ssh", "access"]
---

SSH 憑證（SSH certificate）是由一把 SSH CA 私鑰簽過名的 [SSH](/infra/knowledge-cards/ssh/) 使用者公鑰，簽名裡帶著有效期間、允許登入的帳號名稱（principal）與識別字串。主機不再逐一記錄每個人的公鑰，只信任 CA 的公鑰：sshd 設定 `TrustedUserCAKeys` 指向 CA 公鑰之後，任何帶著有效 CA 簽名、而且還在有效期內的憑證都能登入它列出的帳號。OpenSSH 從 5.4 版起內建這個機制，格式是 OpenSSH 自己的，與網站用的 X.509 [憑證](/backend/knowledge-cards/certificate/)不相通。

## 概念位置

SSH 憑證屬於伺服器管理通道模型裡的主機登入驗證這一層，處理的是金鑰的生命週期。它與另外兩種金鑰發放方式的差別在「收回」怎麼發生：

- 靜態 `authorized_keys`（見 [SSH](/infra/knowledge-cards/ssh/)）：沒有到期時間，收回要逐台刪除
- 由中央服務在登入當下提供公鑰（見 [OS Login](/infra/knowledge-cards/os-login/)）：帳號或角色移除，下一次登入就失敗
- SSH 憑證：憑證到期自動失效，有效期設成幾小時時，離職或權限變更最晚在一個有效期之後生效

簽發服務通常接在 [Identity Provider](/backend/knowledge-cards/identity-provider/) 後面：管理員用 IdP 帳號登入簽發服務，換到一張短期憑證，所以通道授權與主機登入驗證可以共用同一個身分來源。HashiCorp [Vault](/infra/knowledge-cards/vault/) 的 SSH secrets engine 與 Teleport 都以這種方式運作。

## 可觀察訊號

- 主機的 `sshd_config` 有 `TrustedUserCAKeys`，而 `~/.ssh/authorized_keys` 是空的或不存在
- 管理員的 `~/.ssh/` 裡除了金鑰對，還有一個 `*-cert.pub` 檔，用 `ssh-keygen -L -f <cert-file>` 讀得出它的有效期間與 principal
- 每天第一次 SSH 之前要先跑一個登入或簽發指令

## 設計責任

導入 SSH 憑證時要決定：

- **CA 私鑰的保管**：CA 私鑰能簽出登入所有主機的憑證，它外洩的影響等於所有主機的所有金鑰一起外洩，所以放在 Vault 或硬體安全模組這類受控位置，不放在任何人的電腦上
- **有效期長度**：越短越接近即時收回，代價是管理員要更常重新簽發；以小時計是常見的取值範圍
- **principal 的對應**：憑證列出的帳號名稱與主機上的帳號怎麼對應，決定一張憑證能登入哪些主機的哪些帳號
- **提前撤銷**：憑證還沒到期就要失效時（例如私鑰外洩），sshd 用 `RevokedKeys` 指向撤銷清單，這份清單要能派送到所有主機
- **主機憑證**：同一個機制也能反過來簽主機的金鑰（`HostCertificate`），讓用戶端驗證主機身分，省掉第一次連線時確認主機指紋的步驟

簽發的指令形式是 `ssh-keygen -s <ca-private-key> -I <identity> -n <principals> -V <validity> <user-public-key>`，實際運作時由簽發服務代為執行。

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 靜態金鑰認證與 `authorized_keys`
- [OS Login](/infra/knowledge-cards/os-login/) — 另一種讓登入權限隨帳號收回的做法
- [HashiCorp Vault](/infra/knowledge-cards/vault/) — 可以保管 CA 私鑰並簽發憑證
