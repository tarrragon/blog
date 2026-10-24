---
title: "登入：SSH 金鑰與預設使用者"
date: 2026-10-24
description: "建立虛擬機時 SSH 金鑰欄位的幾個選項（讓業者產生、上傳、貼上、不放金鑰）各自把什麼放進主機、私鑰由誰保管，映像檔決定的預設使用者名稱，建立之後還能不能加金鑰，以及完全不放金鑰時靠什麼登入"
weight: 4
tags: ["infra", "cloud-providers", "vm", "ssh", "access"]
---

這篇說明建立頁上決定「主機建好之後誰能用什麼登入」的欄位。範圍是第一次登入用的金鑰與帳號；長期給一個團隊用的登入設計（身分代理、短效憑證、離職撤銷）見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## SSH 金鑰欄位做了什麼

Linux 主機用 [SSH](/infra/knowledge-cards/ssh/) 公鑰驗證登入：主機的使用者家目錄裡有一份允許清單（`~/.ssh/authorized_keys`），持有清單上某一把公鑰對應私鑰的人才能登入。建立頁的 SSH 金鑰欄位把一把公鑰交給業者，業者把它存進主機的中繼資料（metadata），主機第一次開機時由 cloud-init 讀出來、寫進預設使用者的 `authorized_keys`。

Oracle Cloud 的建立頁提供四個選項：

- **讓業者產生一對金鑰（Generate a key pair for me）**：業者產生一對 RSA 金鑰，公鑰放進主機，私鑰讓使用者在這一頁下載。私鑰只能在這一刻下載，離開頁面之後就拿不到；官方提醒持有私鑰的人都能登入這台主機，要存在安全的位置。
- **上傳公鑰檔（Upload public key files）**：上傳自己電腦上已經有的公鑰（`.pub` 檔）。私鑰從頭到尾只在自己的電腦上。
- **貼上公鑰（Paste public keys）**：同上，改成貼上公鑰的文字。誤貼私鑰時頁面會報錯。
- **不放金鑰（No SSH keys）**：主機裡沒有任何允許登入的公鑰。

自己已經在用 SSH 的話，上傳或貼上自己的公鑰比較好：私鑰不經過任何網頁，也不必管理另一把專門給這台主機的金鑰。本機還沒有金鑰時，用 `ssh-keygen -t ed25519` 產生一對，公鑰在 `~/.ssh/id_ed25519.pub`。

## 預設使用者由映像檔決定

公鑰寫進的是映像檔預先建立的那個使用者，名稱依作業系統而定。Oracle Cloud 的官方說明是 Ubuntu 平台映像的使用者名稱是 `ubuntu`，Oracle Linux 與相容 RHEL 的平台映像是 `opc`。登入指令因此是 `ssh ubuntu@<主機的 IP>` 或 `ssh opc@<主機的 IP>`，用錯名稱時 SSH 回的是 `Permission denied (publickey)`，看起來跟金鑰錯了一樣。

這個預設使用者有 `sudo` 權限。多人共用同一台主機時，各自建自己的使用者、各自放自己的公鑰，誰做了什麼才分得出來；共用帳號的問題見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## 建立之後還能不能加金鑰

建立頁的金鑰只在第一次開機時寫進主機一次。之後要加金鑰，做法是先用現有的金鑰登入，再在主機裡把新的公鑰加進 `authorized_keys`。Oracle Cloud 對「不放金鑰」這個選項的說明是：選了之後，就不能再提供公鑰或下載業者產生的金鑰。

所以金鑰遺失或一開始沒放時，主機上沒有現成的入口。Oracle Cloud 官方列出的處置有兩種：

- 終止這台主機，帶著新的公鑰重建。
- 經由序列主控台（serial console）進入主機設定 SSH，官方為 Oracle Linux 附了一份重設 `opc` 金鑰的範例。序列主控台不經過網路與 sshd，是金鑰失效時剩下的入口，見 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)。

## 不放金鑰時靠什麼登入

選「不放金鑰」是一種刻意的設計：主機裡沒有長期有效的公鑰，登入改由業者的服務臨時發放。三家各有一種：

- **Oracle Cloud Bastion 的 managed SSH session**：建立一次 session 時指定一把公鑰，主機上的 Bastion plugin 把它臨時加進去，session 到期就失效。前提是主機的代理程式打開了 Bastion plugin（建立時勾選，或建好之後在主機頁面打開、等幾分鐘生效），見 [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/)。
- **Google Cloud 的 OS Login**：登入權限跟著 Google 帳號與 IAM 角色走，見 [OS Login](/infra/knowledge-cards/os-login/)。
- **AWS 的 EC2 Instance Connect 與 Systems Manager Session Manager**：EC2 Instance Connect 臨時推送一把公鑰，Session Manager 經由主機上的代理程式開工作階段、不經過 SSH port。

這條路要求那個服務需要的條件全部備齊：代理程式與它的 plugin、使用者的 IAM 權限、服務連到主機的網路路徑。少了一項時主機照樣建得起來，而登入會失敗；在補齊之前，主機上沒有其他入口可以進去查原因。第一次建主機、還不熟這些服務時，先放自己的公鑰，等臨時發放的登入走通了再拿掉，比較保險。

## 各家的欄位名稱

| 概念              | Oracle Cloud                | Google Cloud                       | AWS                  |
| ----------------- | --------------------------- | ---------------------------------- | -------------------- |
| 建立時放公鑰      | Add SSH keys                | SSH keys（metadata `ssh-keys`）    | Key pair             |
| Ubuntu 預設使用者 | `ubuntu`                    | 依 metadata 裡公鑰附帶的使用者名稱 | `ubuntu`             |
| 臨時發放的登入    | Bastion managed SSH session | OS Login                           | EC2 Instance Connect |

## 延伸閱讀：網路路徑與長期的登入設計

- [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)：金鑰對了之後，連線還要通過的網路與防火牆
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：網路可達性、通道授權與主機登入驗證三層怎麼一起設計
