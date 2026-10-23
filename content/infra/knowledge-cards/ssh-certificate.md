---
title: "SSH Certificate（SSH 憑證）"
date: 2026-10-23
description: "主機多、人員常異動而逐台收回 authorized_keys 跟不上，或要讓 SSH 登入權限自動到期時，查 SSH CA 簽發短期憑證的運作方式與導入時要決定的事"
weight: 56
tags: ["infra", "knowledge-cards", "ssh", "access"]
---

SSH 憑證（SSH certificate）是由一把 SSH CA 私鑰簽過名的 [SSH](/infra/knowledge-cards/ssh/) 使用者公鑰，簽名裡帶著有效期間、允許登入的帳號名稱（principal）與識別字串。主機不再逐一記錄每個人的公鑰，只信任 CA 的公鑰：sshd 設定 `TrustedUserCAKeys` 指向 CA 公鑰之後，任何帶著有效 CA 簽名、而且還在有效期內的憑證都能登入它列出的帳號。OpenSSH 從 5.4 版起內建這個機制，格式是 OpenSSH 自己的，與網站用的 X.509 [憑證](/backend/knowledge-cards/certificate/)不相通。

## 概念位置

SSH 憑證處理的是登入主機用的金鑰怎麼發、怎麼失效——[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)把這一層叫主機登入驗證。它與另外兩種金鑰發放方式的差別在權限怎麼失效：

- 靜態 `authorized_keys`（見 [SSH](/infra/knowledge-cards/ssh/)）：沒有到期時間，收回要逐台刪除
- 由中央服務決定可用的公鑰（見 [OS Login](/infra/knowledge-cards/os-login/)）：帳號或角色移除，下一次登入就失敗
- SSH 憑證：憑證到期自動失效，離職或權限變更最晚在一個有效期之後生效

簽發服務通常接在 [Identity Provider](/backend/knowledge-cards/identity-provider/) 後面：管理員用 IdP 帳號登入簽發服務，換到一張短期憑證。管理通道前面那一層的通道授權（決定誰能打開通往主機的連線，例如身分感知代理檢查 IdP 帳號）若也用同一個 IdP，兩層就共用同一個身分來源，停用一個帳號同時擋下兩層。HashiCorp Vault 的 SSH secrets engine 與 Teleport 都以這種方式運作。三種做法收回的都是下一次登入，已經建立的工作階段要另外在主機上中斷。

## 可觀察訊號

- 主機的 `sshd_config` 有 `TrustedUserCAKeys`，而 `~/.ssh/authorized_keys` 是空的或不存在
- 管理員的 `~/.ssh/` 裡在金鑰對旁邊多了一個同名加 `-cert.pub` 結尾的檔（例如 `id_ed25519-cert.pub`），`ssh` 連線時會自動帶上它；用 `ssh-keygen -L -f <cert-file>` 讀得出它的有效期間與 principal
- 每天第一次 SSH 之前要先跑一個登入或簽發指令

## 設計責任

CA 私鑰取代了每台主機上的公鑰清單，所以導入 SSH 憑證時的決定都圍繞著 CA 與憑證內容：

- **CA 私鑰的保管**：CA 私鑰能簽出登入所有主機的憑證，它外洩的影響等於所有主機的所有金鑰一起外洩，所以放在 [HashiCorp Vault](/infra/knowledge-cards/vault/) 或硬體安全模組這類受控位置，不放在任何人的電腦上
- **有效期長度**：有效期等於能接受的最晚收回延遲——離職或權限移除之後，那張憑證最多還能用一個有效期。延遲上限越短，有效期越短，管理員重新簽發也越頻繁；管理員手動簽發時常設成一個工作日左右，讓每天開工時簽一次；簽發由用戶端在連線時自動完成時（Teleport 的 `tsh`、smallstep 的 `step ssh`），有效期可以縮到幾小時以內，收回延遲跟著縮短
- **principal 的對應**：憑證列出的帳號名稱與主機上的帳號怎麼對應，決定一張憑證能登入哪些主機的哪些帳號。主機上只有一個共用帳號（例如雲端映像預設的 `ubuntu`）時，每張憑證的 principal 都是 `ubuntu`，主機端分不出是誰登入，要靠憑證的識別字串（簽發時的 `-I`）出現在 sshd 的認證紀錄裡來辨識人
- **提前撤銷**：憑證還沒到期就要失效時（例如私鑰外洩），sshd 用 `RevokedKeys` 指向撤銷清單，這份清單要能派送到所有主機
- **主機憑證**：同一個機制也能反過來簽主機的金鑰（`HostCertificate`），讓用戶端驗證主機身分。主機經常重建（autoscaling、重新部署）時，每次重建主機指紋都會變，用戶端會反覆看到指紋變更的警告而養成直接接受的習慣；改用主機憑證後用戶端只信任 CA，前提是用戶端的 `known_hosts` 已加入 `@cert-authority` 與 CA 公鑰

簽發的指令形式是 `ssh-keygen -s <ca-private-key> -I <identity> -n <principals> -V <validity> <user-public-key>`：`-I` 是寫進憑證、會出現在主機認證紀錄裡的識別字串（通常填 IdP 帳號），`-n` 是允許登入的帳號名稱、多個用逗號分隔，`-V` 是有效期間（`+8h` 表示從現在起八小時）。實際運作時由簽發服務代為執行，簽出的憑證寫在使用者公鑰旁邊的 `*-cert.pub`。

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 靜態金鑰認證與 `authorized_keys`
- [OS Login](/infra/knowledge-cards/os-login/) — 另一種讓登入權限隨帳號收回的做法
- [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) — 跳板機與目的主機不共用金鑰時，目的主機這一段可以改用憑證
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/#主機登入驗證登入權限的收回靠人工刪除帳號連動或到期) — 人員流動、主機數量與帳號系統不同時，三種金鑰發放方式的選擇條件
