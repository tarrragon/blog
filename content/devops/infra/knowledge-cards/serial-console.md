---
title: "Serial Console（序列主控台）"
date: 2026-10-23
description: "SSH 因為防火牆、sshd 設定或磁碟滿而連不進主機，或要規劃管理通道斷掉時的備用路徑時，查序列主控台與頻外管理介面的用法與它本身的暴露面"
weight: 58
tags: ["infra", "knowledge-cards", "access", "recovery"]
aliases: ["/infra/knowledge-cards/serial-console/"]
---

序列主控台（serial console）承擔的是救援：當網路設定或 sshd 出錯而 [SSH](/devops/infra/knowledge-cards/ssh/) 連不進去時，它提供一條不經過主機作業系統的網路設定與 sshd 的登入路徑。實體伺服器上它是一條接到序列埠的線；雲端 VM 把它做成虛擬序列埠，由廠商的網頁管理介面或 CLI 轉送，例如 GCP 的 Serial Console（`gcloud compute connect-to-serial-port`）、AWS 的 EC2 Serial Console，以及 Oracle Cloud 的 serial console connection（先替主機建一個序列主控台連線（instance console connection），再從自己的電腦用 SSH 連上，官方說明本機連線要用 RSA 金鑰）。連上之後看到的是作業系統的文字主控台；只看開機輸出不必登入，要在登入提示登進去時，用主機上設了密碼的本機帳號（Oracle Cloud 官方說明平台映像的 `opc` 沒有預設密碼）。

## 跟其他概念的關係

序列主控台與平時的管理通道設計方向相反：管理通道要隨時可用，救援入口平時關閉、只在需要時打開，因為它繞過了 [Identity-Aware Proxy（身分感知代理）](/devops/infra/knowledge-cards/identity-aware-proxy/) 或 [Bastion Host（跳板機）](/devops/infra/knowledge-cards/bastion-host/) 這些平時的控制點。管理通道的網路可達性、通道授權或主機登入驗證任何一層設定錯了（這三層的分法見[伺服器管理通道的設計](/devops/infra/03-network-foundation/management-access-channel/)），序列主控台都還連得上，因為它不經過那三層的設定。它有自己的授權：雲端上是雲端帳號的 IAM 權限與開啟它的開關，登入時用主機上的本機帳號密碼，所以雲端 IAM 或開關設錯時，它一樣進不去。

不同環境的救援入口形態不同。地端實體伺服器用的是頻外管理控制器（BMC，out-of-band management，其他中文資料常寫作「帶外管理」）：IPMI、Dell iDRAC、HPE iLO 這類嵌在主機板上的管理控制器，有自己的網路埠，在作業系統沒開機時也能看主控台、重開機、掛載安裝媒體。VPS 服務商多半在網頁後台提供一個在瀏覽器裡顯示主機畫面的主控台（常叫 VNC console），用法與雲端的序列主控台相同：不經過主機的網路設定，用本機帳號密碼登入。

## 可觀察訊號

- SSH 連線逾時或被拒，而雲端的網頁管理介面或監控顯示主機仍在執行——網路設定、防火牆或 sshd 出錯時的典型樣貌
- 開機過程卡住（檔案系統檢查、`/etc/fstab` 寫錯）時，序列主控台看得到開機訊息，SSH 在那個階段還沒有啟動
- 雲端帳號或專案的設定裡，序列主控台存取是關閉的（GCP 預設關閉互動登入，用 metadata `serial-port-enable=TRUE` 對單一 VM 開啟；AWS 要在帳號層級先允許）

## 判斷條件與後果

救援入口在出事當下才用得到，而帳號、權限與演練在主機正常時準備最快。出事當下這條入口用不用得上，看下面幾個條件：

- **救援帳號**：序列主控台用本機帳號密碼登入，而用金鑰登入的主機通常沒有設密碼的帳號，這種主機出事時序列主控台登入不了，所以救援帳號在主機正常時就建好。密碼逐台隨機產生、存放在受控的密碼庫時，一台的密碼外洩只影響那一台；sshd 維持只收金鑰時，這組密碼只在序列主控台上有用。這組密碼不隨 IdP 收回，持有它的人離開之後每一台的密碼都還有效，所以要逐台輪替。沒有事先建帳號時，雲端 VM 還有要重開機或停機、因此比較慢的路（GCP 的 startup-script 每次開機以 root 執行；AWS 的 user-data 預設只在第一次開機執行，要改成每次開機執行的 cloud-init 格式；GCP、AWS 與 Oracle Cloud 都能把開機磁碟掛到另一台 VM 修改；官方另為 Oracle Linux 附了經由序列主控台開進維護模式、重設 `opc` 金鑰的範例），地端主機只能重開機進單人模式。不必重開機的路是業者在主機裡執行指令的服務：AWS 的 SSM Run Command 與 Oracle Cloud 的 Run Command，兩者都要主機上的代理程式在運作，代理程式停了或連不到業者的服務端點時用不上；Oracle Cloud 這幾個入口各自的前提見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/devops/infra/cloud-providers/vm-options/login/) 的〈建立之後加金鑰與金鑰遺失時的入口〉
- **演練**：救援帳號建好之後沒有實際用序列主控台登入過時，密碼不對或沒有 sudo 權限要到出事當下才發現，那時主機已經沒有別的入口可以修；建好之後登入一次、確認 sudo 可用再關回去，這兩種錯誤在主機正常時就看得到。平時不存在、事故時才開的權限叫 [Break-Glass Access](/backend/knowledge-cards/break-glass-access/)，事後回顧的做法在那張卡
- **開啟範圍與時機**：序列主控台平時開著時，它是一條不經過 sshd 的常駐入口；只在救援時對單一主機開啟、用完關回去時，這條入口只在救援的那一段時間存在。存取權限在 GCP 上靠角色收不窄：開啟 metadata 與連線都需要 `roles/compute.instanceAdmin.v1`，而這也是一般 VM 管理會用到的角色。GCP 用 Organization Policy 的 `compute.disableSerialPortAccess` 在組織層級預設關閉時，只有能對專案解除這條政策的人開得了序列主控台，救援名單裡沒有這些人時，出事當下沒有人開得了
- **頻外管理介面的網路**：IPMI 這類控制器歷史上有多個認證弱點，它的網路埠接在一般網段或網際網路時，這些弱點從外面就碰得到；接在獨立的管理網段時，碰得到它的只有管理網段上的主機
- **操作紀錄**：序列主控台的連線繞過了平時的稽核點與錄製位置，雲端廠商的 audit log 查得到誰在什麼時候開了主控台，查不到在裡面執行了什麼；有逐指令稽核要求時，這段救援在稽核紀錄裡是空白，所以救援時做了什麼要另外記錄

## 鄰卡

- [SSH](/devops/infra/knowledge-cards/ssh/) — 平時的管理通道，序列主控台在它斷掉時接手
- [Identity-Aware Proxy（身分感知代理）](/devops/infra/knowledge-cards/identity-aware-proxy/) — 平時的通道控制點，救援入口繞過它
- [Bastion Host（跳板機）](/devops/infra/knowledge-cards/bastion-host/) — 另一種平時的通道控制點
- [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/devops/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/#準備救援入口serial-console-與本機救援帳號) — 在 GCP 上建救援帳號、開啟與關閉 Serial Console 的指令
- [Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/devops/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)〈序列主控台：RSA 金鑰、建立連線、ProxyJump 設定與看到的開機輸出〉 — 在 Oracle Cloud 上建序列主控台連線、把官方的連線字串改寫成 ProxyJump 設定，以及連上之後看到的開機輸出
