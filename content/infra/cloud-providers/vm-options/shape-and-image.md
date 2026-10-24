---
title: "機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統"
date: 2026-10-24
description: "建立虛擬機時機型決定的 CPU 架構、核心與記憶體，計費模式（隨用隨付、可被收回、預留容量、專屬主機）各自的條件，映像檔與機型之間的架構相容性，以及哪些項目建立後可以調整"
weight: 2
tags: ["infra", "cloud-providers", "vm", "compute", "image"]
---

這篇說明建立頁上決定主機「是什麼樣的電腦」的兩組選項：機型（CPU 架構、核心數、記憶體與計費模式）與映像檔（開機磁碟上預先裝好的作業系統）。兩者放在一起講，因為它們之間有一條硬性的相容條件：映像檔的 CPU 架構必須跟機型一致。

## CPU 架構：x86 與 ARM

機型的第一個屬性是 CPU 架構，目前雲端上有兩種：x86（Intel、AMD）與 ARM（Oracle Cloud 的 Ampere A1、AWS 的 Graviton、Google Cloud 的 Axion 與 Tau T2A）。架構決定主機能執行哪些程式：

- 作業系統與套件庫提供兩種架構的版本，`apt install` 這類安裝會自動拿到對應架構的套件。
- 只發佈 x86 版本的程式（部分商用軟體、舊版工具、只建了 `amd64` 映像的容器）在 ARM 主機上跑不起來，或要靠模擬執行而變慢。

ARM 機型的同等規格通常比較便宜，Oracle Cloud 的 Always Free 額度大部分也在 ARM（A1）上。要跑的軟體確認有 ARM 版本時，ARM 是比較划算的選擇；不確定時，先查那個軟體的下載頁或容器映像的平台清單有沒有 `arm64`。

架構在建立之後不能換，因為開機磁碟上的作業系統是為那個架構編譯的。要換架構，做法是用另一個架構的映像檔建一台新主機。

## 核心數與記憶體

固定規格的機型名稱本身就決定了核心數與記憶體（AWS 的 `t3.micro`、Google Cloud 的 `e2-micro`）。彈性機型（Oracle Cloud 名稱以 `.Flex` 結尾的 shape、Google Cloud 的自訂機型）讓使用者在範圍內自己填核心數與記憶體，而記憶體能填的範圍隨核心數變動。

各家計算核心的單位不同。Oracle Cloud 用 OCPU，x86 機型的 1 OCPU 等於 2 個 vCPU、Ampere A1 的 1 OCPU 等於 1 個 vCPU；其他兩家用 vCPU。共享核心機型（Google Cloud 的 `e2-micro`）作業系統看得到 2 個 vCPU，持續使用量卻只有 0.25 個。比較規格時的換算見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

核心數與記憶體建立之後可以調整，代價是重開機。Oracle Cloud 的官方說明是主機在執行中時，改機型的過程會把它重開，私有 IP、公開 IP 與掛載的磁碟維持不變；改之前在作業系統裡先把應用程式正常關掉，避免寫到一半的資料損壞。不是每種機型都能改：Oracle Cloud 的 `VM.Standard.E2.1.Micro` 不能調整，A1 Flex 可以在 Always Free 額度內調整核心數與記憶體。所以實驗機先開小一點，不夠再加，比一開始就開滿划算——改大要重開機，但不必重建。

## 計費模式：隨用隨付、可被收回、預留容量與專屬主機

同一個機型可以用不同的方式取得容量，差別在價格與「業者能不能把這台主機收回去」。Oracle Cloud 建立頁的 Capacity type 欄位列出這幾種：

- **隨用隨付（on-demand）**：預設值。在共享的實體主機上開一台虛擬機，開著的時間計費，業者不會因為別人要用而收回它。Always Free 的額度也是在這種模式下計算。
- **可被收回（preemptible，Google Cloud 與 AWS 叫 Spot）**：同樣的機型，Oracle Cloud 的價格是隨用隨付的一半，而業者需要容量時會直接終止它，沒有保證的最短執行時間，終止前兩分鐘發出一個事件通知。建立後不能停止、啟動或重開，也不能轉成隨用隨付。適合跑得斷、可以重來的批次工作；要一直開著的服務與手動設定過的實驗機不適合，被收回時設定會跟著消失。
- **預留容量（capacity reservation）**：先向業者保留一定數量的某種機型容量，之後建主機時從保留的額度裡扣。它處理的是「要用的時候沒有容量」：保留期間不論有沒有主機在用都計費。
- **專屬主機（dedicated host）**：整台實體主機只給這個帳號的虛擬機用，不跟其他客戶共用硬體，用在合規要求或授權按實體主機計算的軟體。Oracle Cloud 只允許在建立時把主機放上專屬主機。

這幾種模式互斥，一台主機只能選一種。實驗用的小主機選隨用隨付。

## 停止主機時的計費

停止（stop）跟終止（terminate）是兩件事：停止是關機，主機與磁碟都保留，之後可以再開；終止是刪除主機。Oracle Cloud 的標準機型在停止期間暫停計算資源的計費，但仍然佔用服務配額；Dense I/O、HPC 與多數 GPU 機型停止時照樣計費，要終止才會停。官方另外提醒，在作業系統裡下 `shutdown` 不會停止計費，要從主控台或 API 停止主機。磁碟的計費跟主機是否開著無關，見 [磁碟：開機磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)。

## 映像檔：開機磁碟上的作業系統

映像檔是建立主機時複製到開機磁碟上的作業系統內容。主控台的映像檔清單通常分成三種來源：

- **業者提供的平台映像（platform image）**：Ubuntu、Oracle Linux、Debian、Windows 等，由業者維護並預先裝好它自己的代理程式。實驗與一般用途選這一種。
- **市集映像（marketplace）**：第三方預先裝好特定軟體的映像，部分要另外付授權費。
- **自訂映像（custom image）**：從自己的主機或開機磁碟做出來的映像，用來複製已經設定好的環境。

同一個作業系統常有完整版與 minimal 版。Minimal 版只裝開機與連網需要的套件，開機磁碟用量小、要修補的套件少，代價是常用工具（文字編輯器、部分診斷工具）要自己裝。

映像檔要跟機型的架構一致：清單上 Ubuntu 的 ARM 版名稱帶 `aarch64`，x86 版不帶。Oracle Cloud 的主控台會把跟已選映像檔不相容、或這個可用區沒有提供的機型標成不可選；用 CLI 或 API 建立時沒有這層畫面上的提示，映像檔的 OCID 要自己挑對架構，查詢映像檔時加上機型條件（`oci compute image list --shape <機型>`）回傳的就只有相容的那些。映像檔也決定了預設的登入使用者名稱，見 [登入：SSH 金鑰與預設使用者](/infra/cloud-providers/vm-options/login/)。

映像檔只在建立的那一刻複製一次。之後作業系統的更新由主機自己的套件管理員處理，跟映像檔清單上出現的新版本無關；要換成另一個作業系統，做法是用新的映像檔建一台新主機。

## 各家的欄位名稱

| 概念     | Oracle Cloud         | Google Cloud        | AWS                         |
| -------- | -------------------- | ------------------- | --------------------------- |
| 機型     | Shape                | Machine type        | Instance type               |
| 彈性規格 | Flex shape           | Custom machine type | 無（選固定規格）            |
| 可被收回 | Preemptible capacity | Spot VM             | Spot Instance               |
| 預留容量 | Capacity reservation | Reservation         | Capacity Reservation        |
| 映像檔   | Image                | Image               | AMI（Amazon Machine Image） |

## 延伸閱讀：機型之後要決定的事

- [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)：某個機型在一個區域建不起來時，換可用區與換機型的取捨
- [磁碟：開機磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)：映像檔複製到的那顆開機磁碟能設定什麼
