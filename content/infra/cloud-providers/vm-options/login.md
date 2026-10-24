---
title: "登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務"
date: 2026-10-24
description: "建立虛擬機時 SSH 金鑰欄位的幾個選項（讓業者產生、上傳、貼上、不放金鑰）各自把什麼放進主機、私鑰由誰保管，映像檔決定的預設使用者名稱，建立之後還能不能加金鑰、金鑰遺失時剩下哪些入口，以及完全不放金鑰時靠業者的哪些服務登入"
weight: 4
tags: ["infra", "cloud-providers", "vm", "ssh", "access"]
---

建立頁的 SSH 金鑰欄位決定主機第一次開機之後，誰能用哪一把金鑰、以哪一個帳號登入。範圍是第一次登入用的金鑰與帳號；長期給一個團隊用的登入設計（身分感知代理 identity-aware proxy、短效憑證、離職撤銷）見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。

## SSH 金鑰欄位把公鑰放進主機的方式

Linux 主機用 [SSH](/infra/knowledge-cards/ssh/) 公鑰驗證登入：主機的使用者家目錄裡有一份允許清單（`~/.ssh/authorized_keys`），持有清單上某一把公鑰對應私鑰的人才能登入。建立頁的 SSH 金鑰欄位把一把公鑰交給業者，業者把它存進主機的中繼資料（metadata）。Oracle Cloud 與 AWS 的 Linux 映像由 cloud-init（多數 Linux 雲端映像預先裝好、開機時讀中繼資料做初始設定的程式）在主機第一次開機時讀出公鑰、寫進預設使用者的 `authorized_keys`；Google Cloud 的映像由業者的 guest agent 持續依中繼資料同步金鑰，不限第一次開機。

Oracle Cloud 的建立頁提供四個選項：

- **讓業者產生一對金鑰（Generate a key pair for me）**：業者產生一對 RSA 金鑰，公鑰放進主機，私鑰讓使用者在這一頁下載。私鑰只能在這一刻下載，離開頁面之後就拿不到；官方提醒持有私鑰的人都能登入這台主機，要存在安全的位置。
- **上傳公鑰檔（Upload public key files）**：上傳自己電腦上已經有的公鑰（`.pub` 檔）。私鑰從頭到尾只在自己的電腦上。
- **貼上公鑰（Paste public keys）**：同上，改成貼上公鑰的文字。誤貼私鑰時頁面會報錯。
- **不放金鑰（No SSH keys）**：主機裡沒有任何允許登入的公鑰，而且官方說明選了之後就不能再提供公鑰。登入只能靠〈不放金鑰時的登入服務〉那幾種服務，或〈建立之後加金鑰與金鑰遺失時的入口〉列的救援入口。

自己已經在用 SSH 的話，上傳或貼上自己的公鑰比較好：私鑰不經過任何網頁，也不必管理另一把專門給這台主機的金鑰。本機還沒有金鑰時，用 `ssh-keygen -t ed25519` 產生一對（ed25519 是新版 OpenSSH 的 `ssh-keygen` 預設產生的型別），公鑰在 `~/.ssh/id_ed25519.pub`；那個路徑已經有一把金鑰時，`ssh-keygen` 會問要不要覆寫，回答 n，或用 `-f <新的檔名>` 另存一把。

## 預設使用者名稱與映像檔的對應

公鑰寫進的是映像檔預先建立的那個使用者，名稱依作業系統而定。Oracle Cloud 的官方說明是 Ubuntu 平台映像的使用者名稱是 `ubuntu`，Oracle Linux 與相容 RHEL 的平台映像是 `opc`。登入指令因此是 `ssh ubuntu@<主機的 IP>` 或 `ssh opc@<主機的 IP>`，用錯名稱時 SSH 回的是 `Permission denied (publickey)`，看起來跟金鑰錯了一樣。

這個預設使用者有 `sudo` 權限。多人共用同一台主機時，各自建自己的使用者、各自放自己的公鑰，誰做了什麼才分得出來；共用一個帳號時，登入紀錄只顯示那個帳號，對不到是哪一個人，有人離職也無法只撤銷他一個人的存取，見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/) 的〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉。

## 建立之後加金鑰與金鑰遺失時的入口

建立之後能不能再加金鑰，看業者用什麼把金鑰寫進主機。Oracle Cloud 的金鑰由 cloud-init 在第一次開機時寫進主機一次，之後要加金鑰，做法是先用現有的金鑰登入，再在主機裡把新的公鑰加進 `authorized_keys`。Google Cloud 的 guest agent 持續同步中繼資料，主機建好之後把公鑰加進主機或專案的中繼資料，guest agent 就會把它寫進主機。AWS 的 EC2 Instance Connect 與 Systems Manager Session Manager 不依賴主機上原有的金鑰，條件備齊時可以當成另一個入口。

所以在 Oracle Cloud 上，金鑰遺失或一開始沒放、又沒有開 Bastion plugin 時，主機上沒有可以用 SSH 進去的入口。剩下的入口各有前提：

- **序列主控台（serial console）**：不經過網路與 sshd，在主控台上建一個主控台連線就能進到開機畫面；官方為 Oracle Linux 附了一份經由它重設 `opc` 金鑰的範例。見 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)。
- **Compute Instance Run Command**：在主控台送一段腳本到主機裡執行，可以用來把新的公鑰寫進 `authorized_keys`。前提是代理程式的這個 plugin 開著，而且主機上的代理程式連得到 Oracle 的服務端點（主機在私有 subnet 時要經由服務閘道）。
- **把開機磁碟掛到另一台主機**：停止這台主機、把它的開機磁碟卸下，當成資料磁碟掛到另一台主機上，直接修改裡面的 `authorized_keys`，再掛回去開機。
- **重建**：終止這台主機，帶著新的公鑰重建。官方對金鑰遺失列的處置就是重建與序列主控台這兩種。

## 不放金鑰時的登入服務

選「不放金鑰」是一種刻意的設計：主機裡不放固定的公鑰，登入時由業者的服務決定這一次可以用哪一把金鑰——有的臨時把一把公鑰放進主機、到期就失效，有的在登入當下向帳號系統查這個人的公鑰與權限。三家的做法：

- **Oracle Cloud 的 Bastion**：Bastion 是業者託管的服務，不是自己架的 [跳板機（bastion host）](/infra/knowledge-cards/bastion-host/)。它在主機所在的 subnet 裡有一個私有端點，主機與 Bastion 都不需要公開 IP。登入的流程是在主控台 Identity & Security → Bastion 建一個指向主機所在 subnet 的 Bastion，設定允許連入的來源位址範圍，再建一個工作階段（session），主控台會給出一條經由 Bastion 轉接的 `ssh` 指令。工作階段有兩種：managed SSH session 由主機上代理程式的 Bastion plugin 把建立工作階段時指定的公鑰臨時放進主機，到期就失效，所以主機可以不放任何金鑰；port forwarding session 只負責把連線轉到主機的 22 port，不經過代理程式，登入用的是主機自己的 sshd 與 `authorized_keys` 裡原有的金鑰。
- **Google Cloud 的 OS Login**：登入時由 Google 查這個 Google 帳號登記的公鑰與 IAM 角色，決定能不能登入、以哪個帳號登入，見 [OS Login](/infra/knowledge-cards/os-login/)。
- **AWS 的 EC2 Instance Connect 與 Systems Manager Session Manager**：EC2 Instance Connect 臨時把一把公鑰推送到主機的中繼資料，有效時間很短；Session Manager 經由主機上的 SSM Agent 開工作階段，不經過 SSH port。

不放金鑰時，這些服務每一種都要求下面這幾項全部備齊：

- **主機上的代理程式**（agent）與它的 plugin：Oracle Cloud 的 managed SSH session 要 Bastion plugin，AWS 的 Session Manager 要 SSM Agent，在建立頁或主機頁面的代理程式設定裡打開，見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/)。Google Cloud 的 OS Login 由映像預先裝好的 guest environment 處理。
- **登入者的權限**：登入的人在雲端帳號裡要有建立工作階段、連到這台主機的權限，在身分與權限的政策裡授予。
- **服務到主機的網路路徑**：服務要連得到主機的私有 IP，或主機上的代理程式要連得出去到服務端點；主機在私有 subnet 時，這條路徑經由服務閘道或 NAT 閘道。官方〈Bastion〉的說明寫明，建立 managed SSH session 之前，VCN 要有一個閘道與通往它的路由規則。

少了一項時主機照樣建得起來，而登入會失敗，主機上又沒有放公鑰，能進去查原因的只剩〈建立之後加金鑰與金鑰遺失時的入口〉那幾條。第一次建主機、還不熟這些服務時，先放自己的公鑰，比較保險：在 Oracle Cloud 上，代理程式或 plugin 出問題、managed SSH session 建不起來時，port forwarding session 不經過代理程式，用自己的公鑰仍然登得進去；等 managed SSH session 走通了，再從 `authorized_keys` 拿掉那把公鑰。

這幾項條件在 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/) 裡分屬三層：服務到主機的網路路徑是網路可達性，登入者的權限是通道授權，業者服務放進主機的那把金鑰是主機登入驗證；三層怎麼一起設計見那一篇。

## 各家的欄位名稱：金鑰欄位、預設使用者與不放金鑰時的登入服務

| 概念                 | Oracle Cloud | Google Cloud                       | AWS                                                   |
| -------------------- | ------------ | ---------------------------------- | ----------------------------------------------------- |
| 建立時放公鑰         | Add SSH keys | SSH keys（metadata `ssh-keys`）    | Key pair                                              |
| Ubuntu 預設使用者    | `ubuntu`     | 依 metadata 裡公鑰附帶的使用者名稱 | `ubuntu`                                              |
| 不放金鑰時的登入服務 | Bastion      | OS Login                           | EC2 Instance Connect、Systems Manager Session Manager |

金鑰對了之後，連線還要通過的網路與防火牆見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)；選 No SSH keys、改走 Bastion 時建立頁上要一起改的設定，見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/) 的 SSH keys 與 Management 段。
