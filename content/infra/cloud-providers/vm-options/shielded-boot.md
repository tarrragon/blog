---
title: "安全開機：Secure Boot、Measured Boot 與 TPM"
date: 2026-10-24
description: "建立虛擬機時安全區塊的開機保護選項：Secure Boot 檢查什麼、Measured Boot 與 TPM 記錄什麼、三者在 Oracle Cloud 上建立後不能修改的限制、與機密運算互斥，以及實驗主機要不要開"
weight: 7
tags: ["infra", "cloud-providers", "vm", "security", "secure-boot"]
---

這篇說明建立頁上保護開機過程的選項。Oracle Cloud 把它們歸在 Security 區塊下的 Shielded instance，官方說明是用 Secure Boot、Measured Boot 與 TPM 三者的組合強化韌體層的安全，防的是在開機階段植入的惡意程式（bootkit、rootkit）。這一類程式在作業系統啟動之前就載入，作業系統裡的防毒與稽核工具看不到它。

## 三個選項各自做什麼

- **Secure Boot**：開機時韌體逐一驗證開機載入程式與核心的數位簽章，簽章不屬於受信任的發行者就拒絕載入。效果是只有作業系統廠商簽過的開機程式跑得起來。
- **Measured Boot**：開機過程的每一個元件在載入前先計算雜湊值，記錄到 TPM 裡。它不阻擋任何元件載入，只留下紀錄；之後拿這份紀錄跟第一次開機時的基準比對，不一致就代表開機鏈被改過。
- **TPM（Trusted Platform Module）**：存放開機量測值與金鑰的安全晶片，雲端主機上是虛擬的。Measured Boot 的紀錄寫在這裡，作業系統也可以用它保存磁碟加密金鑰這類秘密。

Secure Boot 是事前攔截，Measured Boot 是事後偵測，TPM 是兩者與其他安全功能共用的保管處。Oracle Cloud 的部分機型要求某幾項一起開，勾選其中一項時主控台會自動勾上必須一起開的其他項。

## 建立之後不能改

Oracle Cloud 的官方說明是 shielded instance 建好之後，只有主機名稱可以修改。所以這三項要在建立頁上決定，事後要開或關，做法是重建主機。

另一個限制是它跟機密運算（confidential computing，CPU 在運算時也把記憶體裡的資料加密）互斥，一台主機只能選其中一種。

## 實驗主機要不要開

開啟的代價在相容性：Secure Boot 會拒絕沒有簽章的核心模組與自己編譯的核心，要裝第三方驅動程式（部分 GPU、虛擬化或網路驅動）或自訂核心時會開不了機或載入失敗。業者的平台映像本身是簽過的，只跑一般套件時開著不會有感。

- **跑一般服務、使用平台映像**：開或不開都可以；有合規要求（要求開機鏈可驗證）時開。
- **要裝自訂核心或沒有簽章的驅動程式**：不開，或先確認那個驅動程式支援 Secure Boot 的簽章流程。
- **實驗與學習用的主機**：維持建立頁的預設（Oracle Cloud 預設三項都關閉）即可，要測試這個功能時另外建一台開啟的。

## 各家的欄位名稱

| 概念           | Oracle Cloud            | Google Cloud         | AWS                             |
| -------------- | ----------------------- | -------------------- | ------------------------------- |
| 開機保護的總稱 | Shielded instance       | Shielded VM          | 無總稱，個別設定                |
| Secure Boot    | Secure Boot             | Secure Boot          | UEFI Secure Boot（AMI 的屬性）  |
| 開機量測       | Measured Boot           | Integrity monitoring | NitroTPM 搭配作業系統的量測工具 |
| TPM            | Trusted Platform Module | vTPM                 | NitroTPM                        |

## 延伸閱讀：其他建立選項

- [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)：Secure Boot 要求的簽章來自映像檔；換成自訂映像時要確認它是否簽過
- [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/)：同樣在建立頁上、影響主機與業者服務互動的其他設定
