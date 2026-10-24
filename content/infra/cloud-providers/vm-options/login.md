---
title: "登入：SSH 金鑰與預設使用者"
date: 2026-10-24
description: "建立虛擬機時 SSH 金鑰欄位的幾個選項（讓業者產生、上傳、貼上、不放金鑰）各自把什麼放進主機、私鑰由誰保管，映像檔決定的預設使用者名稱，建立之後還能不能加金鑰，以及完全不放金鑰時靠什麼登入"
weight: 4
tags: ["infra", "cloud-providers", "vm", "ssh", "access"]
---

這篇說明建立頁上決定「主機建好之後誰能用什麼登入」的欄位。範圍是第一次登入用的金鑰與帳號；長期給一個團隊用的登入設計（身分感知代理 identity-aware proxy、短效憑證、離職撤銷）見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## SSH 金鑰欄位把公鑰放進主機的方式

Linux 主機用 [SSH](/infra/knowledge-cards/ssh/) 公鑰驗證登入：主機的使用者家目錄裡有一份允許清單（`~/.ssh/authorized_keys`），持有清單上某一把公鑰對應私鑰的人才能登入。建立頁的 SSH 金鑰欄位把一把公鑰交給業者，業者把它存進主機的中繼資料（metadata）。Oracle Cloud 與 AWS 的 Linux 映像由 cloud-init（多數 Linux 雲端映像預先裝好、開機時讀中繼資料做初始設定的程式）在主機第一次開機時讀出公鑰、寫進預設使用者的 `authorized_keys`；Google Cloud 的映像由業者的 guest agent 持續依中繼資料同步金鑰，不限第一次開機。

Oracle Cloud 的建立頁提供四個選項：

- **讓業者產生一對金鑰（Generate a key pair for me）**：業者產生一對 RSA 金鑰，公鑰放進主機，私鑰讓使用者在這一頁下載。私鑰只能在這一刻下載，離開頁面之後就拿不到；官方提醒持有私鑰的人都能登入這台主機，要存在安全的位置。
- **上傳公鑰檔（Upload public key files）**：上傳自己電腦上已經有的公鑰（`.pub` 檔）。私鑰從頭到尾只在自己的電腦上。
- **貼上公鑰（Paste public keys）**：同上，改成貼上公鑰的文字。誤貼私鑰時頁面會報錯。
- **不放金鑰（No SSH keys）**：主機裡沒有任何允許登入的公鑰。

自己已經在用 SSH 的話，上傳或貼上自己的公鑰比較好：私鑰不經過任何網頁，也不必管理另一把專門給這台主機的金鑰。本機還沒有金鑰時，用 `ssh-keygen -t ed25519` 產生一對，公鑰在 `~/.ssh/id_ed25519.pub`。

## 預設使用者名稱與映像檔的對應

公鑰寫進的是映像檔預先建立的那個使用者，名稱依作業系統而定。Oracle Cloud 的官方說明是 Ubuntu 平台映像的使用者名稱是 `ubuntu`，Oracle Linux 與相容 RHEL 的平台映像是 `opc`。登入指令因此是 `ssh ubuntu@<主機的 IP>` 或 `ssh opc@<主機的 IP>`，用錯名稱時 SSH 回的是 `Permission denied (publickey)`，看起來跟金鑰錯了一樣。

這個預設使用者有 `sudo` 權限。多人共用同一台主機時，各自建自己的使用者、各自放自己的公鑰，誰做了什麼才分得出來；共用一個帳號時，登入紀錄只顯示那個帳號，對不到是哪一個人，有人離職也無法只撤銷他一個人的存取，見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/) 的〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉。

## 建立之後加金鑰與金鑰遺失時的入口

三家在這一點的做法不同。Oracle Cloud 建立頁的金鑰只在第一次開機時寫進主機一次，之後要加金鑰，做法是先用現有的金鑰登入，再在主機裡把新的公鑰加進 `authorized_keys`；官方對「不放金鑰」這個選項的說明是，選了之後就不能再提供公鑰或下載業者產生的金鑰。Google Cloud 可以在主機建好之後把公鑰加進主機或專案的中繼資料，guest agent 會把它寫進主機。AWS 的 EC2 Instance Connect 與 Systems Manager Session Manager 不依賴主機上原有的金鑰，條件備齊時可以當成另一個入口。

所以在 Oracle Cloud 上，金鑰遺失或一開始沒放、又沒有開 Bastion plugin 時，主機上沒有可以用 SSH 進去的入口。官方列出的處置有兩種：

- 終止這台主機，帶著新的公鑰重建。
- 經由序列主控台（serial console）進入主機設定 SSH，官方為 Oracle Linux 附了一份重設 `opc` 金鑰的範例。序列主控台不經過網路與 sshd，是金鑰失效時剩下的入口，見 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)。

## 不放金鑰時的臨時登入服務

選「不放金鑰」是一種刻意的設計：主機裡沒有長期有效的公鑰，登入改由業者的服務臨時發放。三家各有一種：

- **Oracle Cloud Bastion 的 managed SSH session**：建立一次工作階段（session）時指定一把公鑰，主機上的 Bastion plugin 把它臨時加進去，工作階段到期就失效。前提是主機的代理程式打開了 Bastion plugin（建立時勾選，或建好之後在主機頁面打開、等幾分鐘生效），見 [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/)。
- **Google Cloud 的 OS Login**：登入權限跟著 Google 帳號與 IAM 角色走，見 [OS Login](/infra/knowledge-cards/os-login/)。
- **AWS 的 EC2 Instance Connect 與 Systems Manager Session Manager**：EC2 Instance Connect 臨時推送一把公鑰，Session Manager 經由主機上的代理程式開工作階段、不經過 SSH port。

這三種服務各自要求幾個條件全部備齊：

- **主機上的代理程式**（agent）與它的 plugin：Oracle Cloud 要開 Bastion plugin，AWS 的 Session Manager 要 SSM Agent，在建立頁或主機頁面的代理程式設定裡打開，見 [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/)。
- **登入者的權限**：登入的人在雲端帳號裡要有建立工作階段、連到這台主機的權限，在身分與權限的政策裡授予。
- **服務到主機的網路路徑**：服務要連得到主機的私有 IP，或主機上的代理程式要連得出去到服務端點；主機在私有 subnet 時，這條路徑經由服務閘道或 NAT 閘道。

少了一項時主機照樣建得起來，而登入會失敗，主機上又沒有放公鑰，能進去查原因的只剩序列主控台：它要另外建一個主控台連線，而且主機裡要有一個能登入的帳號或照官方範例重設金鑰。第一次建主機、還不熟這些服務時，先放自己的公鑰，等臨時發放的登入走通了再拿掉，比較保險。三層條件怎麼一起設計見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## 各家的欄位名稱：金鑰欄位、預設使用者與臨時登入

| 概念              | Oracle Cloud                | Google Cloud                       | AWS                  |
| ----------------- | --------------------------- | ---------------------------------- | -------------------- |
| 建立時放公鑰      | Add SSH keys                | SSH keys（metadata `ssh-keys`）    | Key pair             |
| Ubuntu 預設使用者 | `ubuntu`                    | 依 metadata 裡公鑰附帶的使用者名稱 | `ubuntu`             |
| 臨時發放的登入    | Bastion managed SSH session | OS Login                           | EC2 Instance Connect |

## 延伸閱讀：網路路徑與長期的登入設計

- [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)：金鑰對了之後，連線還要通過的網路與防火牆
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：網路可達性、通道授權與主機登入驗證三層怎麼一起設計
- [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/)：選 No SSH keys、改走 Bastion 時，建立頁上要一起改的設定
