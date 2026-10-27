---
title: "安全開機：Secure Boot、Measured Boot 與 TPM"
date: 2026-10-24
description: "雲端主機的開機保護選項：Secure Boot 檢查什麼、Measured Boot 與 TPM 記錄什麼、三者在 Oracle Cloud 上建立後不能修改的限制、與機密運算互斥、維護時不能遷移，以及實驗主機要不要開"
weight: 7
tags: ["infra", "cloud-providers", "vm", "security", "secure-boot"]
aliases: ["/infra/cloud-providers/vm-options/shielded-boot/"]
---

在開機階段植入的惡意程式（bootkit、rootkit）在作業系統啟動之前就載入，作業系統裡的防毒與稽核工具看不到它。建立頁上保護開機過程的選項就是針對這一類程式：Oracle Cloud 把它們歸在 Security 區塊下的 Shielded instance，官方說明是用 Secure Boot、Measured Boot 與 TPM 三者的組合強化韌體層的安全。

## Secure Boot、Measured Boot 與 TPM 各自的作用

- **Secure Boot**：開機時韌體逐一驗證開機載入程式與核心的數位簽章，簽章不屬於受信任的發行者就拒絕載入。效果是只有作業系統廠商簽過的開機程式跑得起來。
- **Measured Boot**：開機過程中，每一個階段的程式（韌體、開機載入程式）在載入下一個元件之前先量測那個元件，量測值寫進 TPM 的平台設定暫存器（PCR）。它不阻擋任何元件載入，只留下紀錄。Oracle Cloud 把第一次開機的量測值存成基準（golden measurements），之後每次開機時，新的量測值跟基準比對（官方〈Shielded Instances〉沒有寫比對在主機裡還是在業者那一端執行），結果顯示在主控台主機詳細資料頁的盾牌圖示上：開機順序跟基準不符時是紅色，多出新的 PCR 值時是黃色，兩種情形主機都照樣開機。官方提醒更新作業系統之後可能要重設基準，重設的步驟在同一頁。Google Cloud 對應的比對功能叫 integrity monitoring。
- **TPM（Trusted Platform Module）**：存放開機量測值與金鑰的安全晶片，雲端主機上是虛擬的。Measured Boot 的紀錄寫在這裡，作業系統也可以用它保存磁碟加密金鑰這類秘密。

Secure Boot 是事前攔截，Measured Boot 是事後偵測。TPM 是 Measured Boot 存放量測值的地方；官方說明裡 Secure Boot 的簽章驗證由 UEFI 韌體完成，沒有寫它用到 TPM。Oracle Cloud 上哪幾項要一起開依作業系統而定：Windows 虛擬機三項必須一起開，勾選其中一項時主控台會自動勾上另外兩項；Linux 虛擬機可以只開 Secure Boot、只開 TPM 加 Measured Boot，或三項全開。

## Oracle Cloud 上 shielded instance 的限制

Oracle Cloud 的官方〈Shielded Instances〉寫明，shielded instance 建好之後編輯主機時只能改名稱：機型不能改、遷移的設定也不能改，三項安全開機的設定同樣不能事後開關。所以開了安全開機的主機，核心數與記憶體要在建立時就定好，要改就重建。同一頁另外列了下面這些限制：

- 不支援自訂映像，只能用業者的平台映像建立。
- 不支援即時遷移與重開機遷移：業者維護底層硬體時，不會替這台主機做自動遷移，官方寫的是要遷移就由使用者手動遷移，搬到新硬體之後 Secure Boot 的金鑰與開機量測值會在新主機上重新取得。官方〈Infrastructure Maintenance〉的手動遷移做法是終止主機、再用保留下來的開機磁碟建一台新的，開了 TPM 的主機另有額外步驟；維護事件發生時 shielded 虛擬機要停機多久、業者是否事先通知，兩頁都沒有單獨寫。其他主機的維護行為見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/devops/infra/cloud-providers/vm-options/management/) 的〈硬體維護時的行為〉。
- 跟機密運算（confidential computing，CPU 在運算時也把記憶體裡的資料加密）互斥，一台主機只能選其中一種。

這幾條是 Oracle Cloud 的規則。Google Cloud 的 Confidential VM 本身就是 Shielded VM，兩者不互斥。

## 實驗主機開啟安全開機的取捨

官方〈Shielded Instances〉沒有提到開啟這三項會另外收費；要確認自己的帳號，建好之後到帳單的成本分析頁看有沒有出現新的計費項目。開啟的代價在相容性：Secure Boot 會拒絕沒有簽章的核心模組與自己編譯的核心，要裝第三方驅動程式（部分 GPU、虛擬化或網路驅動）或自訂核心時會開不了機或載入失敗。業者的平台映像本身是簽過的，只跑一般套件時開著不會有感。在 Oracle Cloud 上另有一個代價在彈性：開了之後機型不能改，實驗機「先開小、不夠再加」的做法就走不通。

- **跑一般服務、使用平台映像**：開或不開都可以；有合規要求（要求開機鏈可驗證）時開。
- **要裝自訂核心或沒有簽章的驅動程式**：不開，或先確認那個驅動程式支援 Secure Boot 的簽章流程。在 Linux 上，這個流程是用自己的金鑰簽驅動程式、再把那把金鑰登錄進開機鏈信任的清單（Machine Owner Key，MOK）；合規要求開機鏈可驗證、又要裝這類驅動程式時，就要走這條路，做法以那個驅動程式與發行版的文件為準。這一組條件最容易在主機建好幾個月之後才遇到：用 DKMS（套件更新時自動重新編譯核心模組的機制）安裝的驅動程式，編譯與套件安裝都會成功，到 `modprobe` 載入模組時才被拒絕，錯誤訊息是 `Key was rejected by service`；而 Oracle Cloud 上安全開機的設定建立後不能關，只能登錄 MOK 或重建主機。官方另外寫明，主機終止時登錄過的 MOK 會一起刪除，重建的主機要先用標準簽章的核心開機、再重新登錄 MOK。
- **實驗與學習用的主機**：維持建立頁的預設即可，要測試這個功能時另外建一台開啟的。Oracle Cloud 建立 A1 Ubuntu 主機時建立頁上三項預設都關閉（[實測紀錄](/devops/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)的 Security 段）；Google Cloud 的 Shielded VM 預設開啟 vTPM 與 integrity monitoring。

## 各家的欄位名稱：開機保護的總稱、Secure Boot、開機量測與 TPM

| 概念           | Oracle Cloud            | Google Cloud         | AWS                             |
| -------------- | ----------------------- | -------------------- | ------------------------------- |
| 開機保護的總稱 | Shielded instance       | Shielded VM          | 無總稱，個別設定                |
| Secure Boot    | Secure Boot             | Secure Boot          | UEFI Secure Boot（AMI 的屬性）  |
| 開機量測       | Measured Boot           | Integrity monitoring | NitroTPM 搭配作業系統的量測工具 |
| TPM            | Trusted Platform Module | vTPM                 | NitroTPM                        |

映像檔的三種來源與架構相容的規則見 [機型與映像檔](/devops/infra/cloud-providers/vm-options/shape-and-image/)；Oracle Cloud 的 shielded instance 只能用其中的平台映像。
