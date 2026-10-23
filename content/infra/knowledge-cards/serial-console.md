---
title: "Serial Console（序列主控台）"
date: 2026-10-23
description: "SSH 因為防火牆、sshd 設定或磁碟滿而連不進主機，或要規劃管理通道斷掉時的備用路徑時，查序列主控台與頻外管理介面的用法與它本身的暴露面"
weight: 58
tags: ["infra", "knowledge-cards", "access", "recovery"]
---

序列主控台（serial console）承擔的是救援：當網路設定或 sshd 出錯而 [SSH](/infra/knowledge-cards/ssh/) 連不進去時，它提供一條不經過主機網路與 sshd 的登入路徑。實體伺服器上它是一條接到序列埠的線；雲端 VM 把它做成虛擬序列埠，由廠商的主控台或 CLI 轉送，例如 GCP 的 Serial Console（`gcloud compute connect-to-serial-port`）與 AWS 的 EC2 Serial Console。登入時看到的是作業系統的文字主控台，用主機上的本機帳號密碼登入。

## 概念位置

在伺服器管理通道的模型裡，序列主控台是救援入口：管理通道的網路可達性、通道授權或主機登入驗證任何一層出錯時的備用路徑。它與管理通道的設計方向相反——管理通道要隨時可用，救援入口平時關閉、只在需要時打開，因為它繞過了 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) 或 [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) 這些平時的控制點。

地端實體伺服器的對應是頻外管理介面（out-of-band management）：IPMI、Dell iDRAC、HPE iLO 這類嵌在主機板上的管理控制器，有自己的網路埠，在作業系統沒開機時也能看主控台、重開機、掛載安裝媒體。

## 可觀察訊號

- SSH 連線逾時或被拒，而主控台或監控顯示主機仍在執行——網路設定、防火牆或 sshd 出錯時的典型樣貌
- 開機過程卡住（檔案系統檢查、`/etc/fstab` 寫錯）時，序列主控台看得到開機訊息，SSH 在那個階段還沒有啟動
- 雲端帳號或專案的設定裡，序列主控台存取是關閉的（GCP 預設關閉互動登入，用 metadata `serial-port-enable=TRUE` 對單一 VM 開啟；AWS 要在帳號層級先允許）

## 設計責任

規劃序列主控台時要決定：

- **救援帳號**：序列主控台用本機帳號密碼登入，而用金鑰登入的主機通常沒有設密碼的帳號，所以救援帳號要在主機正常時就建好、密碼存放在受控的密碼庫
- **開啟範圍與時機**：平時保持關閉，救援時只對單一主機開啟，用完關回去；存取權限只授予持有救援責任的少數帳號
- **頻外管理介面的網路**：IPMI 這類控制器歷史上有多個認證弱點，它的網路埠接在獨立的管理網段，不接到一般網段或網際網路
- **操作紀錄**：序列主控台的連線繞過了平時的稽核點，雲端廠商的 audit log 要開啟，才查得到誰在什麼時候開了主控台

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 平時的管理通道，序列主控台在它斷掉時接手
- [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) — 平時的通道控制點，救援入口繞過它
- [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) — 另一種平時的通道控制點
