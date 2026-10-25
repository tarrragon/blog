---
title: "機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統"
date: 2026-10-24
description: "雲端主機的機型決定的 CPU 架構、核心與記憶體，計費模式（隨用隨付、可被收回、預留容量、專屬主機）各自的條件，映像檔與機型之間的架構相容性，以及哪些項目建立後可以調整"
weight: 2
tags: ["infra", "cloud-providers", "vm", "compute", "image", "spot-instance", "reserved-instance"]
---

映像檔的 CPU 架構必須跟機型一致，所以建立頁上決定主機「是什麼樣的電腦」的兩組選項要一起決定：機型（CPU 架構、核心數與記憶體），以及開機磁碟上預先裝好的作業系統，也就是映像檔。同一個機型取得容量的方式（計費模式）也在這裡選。文中各家機型的規格、限制與計費規則取自官方文件，查證日期 2026-10-24。

## CPU 架構：x86 與 ARM

機型的第一個屬性是 CPU 架構，目前雲端上有兩種：x86（Intel、AMD）與 ARM（Oracle Cloud 的 Ampere A1、AWS 的 Graviton、Google Cloud 的 Axion 與 Tau T2A）。架構決定主機能執行哪些程式：

- 作業系統與套件庫提供兩種架構的版本，套件管理員（`apt`、`dnf`）依主機的架構下載對應的套件。
- 只發佈 x86 版本的程式（部分商用軟體、舊版工具、只建了 `amd64` 映像的容器）在 ARM 主機上跑不起來，或要靠模擬執行而變慢。容器最常在這裡出事：在 x86 的筆電或 CI 上 build 出來的映像預設只有 `amd64`，本機測試全部通過，拿到 A1 主機上啟動才出現 `exec format error`。在 x86 機器上一次 build 出 `amd64` 與 `arm64` 兩種映像的做法見 [BuildKit 與跨平台 build](/backend/05-deployment-platform/vendors/docker/buildkit-cross-platform/) 的〈跨平台 build：一次出多架構〉。

ARM 機型的同等規格通常比較便宜，Oracle Cloud 的 Always Free 額度大部分也在 ARM（A1）上。要跑的軟體確認有 ARM 版本時，ARM 是比較划算的選擇；不確定時，先查那個軟體的下載頁或容器映像的平台清單有沒有 `arm64`。

架構在建立之後不能換，因為開機磁碟上的作業系統是為那個架構編譯的，換架構只能用另一個架構的映像檔重建。用 IaC 管理主機時，改映像檔這一類屬性在 Terraform 的 plan 上顯示成先刪後建（forces replacement），主機與它的開機磁碟會被重建，見 [terraform plan / apply](/infra/knowledge-cards/terraform-plan-apply/)。

## 核心數與記憶體

固定規格的機型名稱本身就決定了核心數與記憶體（AWS 的 `t3.micro`、Google Cloud 的 `e2-micro`）。彈性機型（Oracle Cloud 名稱以 `.Flex` 結尾的 shape、Google Cloud 的自訂機型）讓使用者在範圍內自己填核心數與記憶體，而記憶體能填的範圍隨核心數變動。

各家計算核心的單位不同。vCPU 是作業系統看到的一個虛擬處理器；Oracle Cloud 用 OCPU，官方把一個 OCPU 定義為一顆實體核心；Oracle Cloud 的 x86 機型（AMD、Intel）1 OCPU 等於 2 個 vCPU，因為多數 x86 處理器的一顆核心跑兩個硬體執行緒，Ampere A1 的 1 OCPU 等於 1 個 vCPU；其他兩家直接用 vCPU。x86 裡每核只跑一個執行緒的例外機型與 Oracle Cloud 較新的 Arm 機型怎麼換算，見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/) 的〈計費單位的換算：OCPU、vCPU 與機型配額〉。共享核心機型（Google Cloud 的 `e2-micro`）作業系統看得到 2 個 vCPU，持續使用量卻只有 0.25 個，三家規格放在一起比較時的換算也在同一節。

核心數與記憶體建立之後可以調整，代價是一段停機。Oracle Cloud 的官方說明是主機在執行中時，改機型的過程會把它重開，私有 IP、公開 IP 與掛載的磁碟維持不變；改之前在作業系統裡先把應用程式正常關掉，避免寫到一半的資料損壞。官方的主控台步驟另外註明，主機掛了兩顆以上的區塊磁碟時（原文是 more than one block volume attached），要先把區塊磁碟卸下才能改機型。Google Cloud 與 AWS 要先把主機停止才能換機型，換完再啟動；AWS 停止再啟動時，自動指派的公開 IP 會換成新的。能調整的機型也有限：Oracle Cloud 的 `VM.Standard.E2.1.Micro` 不能調整，開了安全開機（shielded instance）的主機也不能改機型，A1 Flex 可以在 Always Free 額度內調整核心數與記憶體。

既然改大只要一段停機、不必重建，實驗機先開小一點、不夠再加；前提是改大的時候那一區還有容量，A1 這種容量經常不足的機型，在建得起來的那一刻就要把規格想好；要在改機型之前確認新機型當下有沒有容量，Oracle Cloud 的改機型說明寫明用 `CreateComputeCapacityReport` 這個 API 查。付費機型開小直接省錢，Always Free 的 A1（每月額度相當於 2 OCPU、12 GB 整個月開著，見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)）則是把剩下的額度留給第二台主機。「不夠」的訊號在主機的指標上：CPU 使用率長時間接近滿載、或記憶體用完開始用 swap、程式被 OOM 終止。

某個機型在一個區域建不起來（容量不足）時，本篇處理的是改小規格、換架構與改用可被收回的容量，代價看選哪一種；其餘的退路（換可用區、等待重試、不指定故障域、建立前查容量、預留容量、升級付費帳戶）與這幾種排在一起的完整清單，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈A1 容量不足時的退路〉。在同一種機型裡改小規格，容量比較容易拿到，免費額度也不變；換到另一個架構（例如 A1 建不起來改用 x86 的 Flex 機型），要重新確認軟體有沒有那個架構的版本，而且 Oracle Cloud 上 x86 的 Flex 機型不在 Always Free 額度內，試用期間由試用金支付、當天就建得起來，試用結束之後的結果依帳號狀態而定，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉；改用可被收回的容量，價格低，但主機隨時可能被收回，而官方 Always Free 頁沒有寫這種容量是否算在免費額度內。換可用區的部分見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)。

## 計費模式：隨用隨付、可被收回、預留容量與專屬主機

同一個機型可以用不同的方式取得容量，差別在價格與「業者能不能把這台主機收回去」。Oracle Cloud 建立頁的 Capacity type 欄位列出這幾種：

- **隨用隨付（on-demand）**：預設值。在共享的實體主機上開一台虛擬機，開著的時間計費，業者不會因為別人要用而收回它。Oracle Cloud 的官方 Always Free 頁沒有提到其他計費模式，在 Always Free 額度內建主機時維持這個預設。
- **可被收回（preemptible）**：同樣的機型，價格較低，而業者需要容量時會直接終止它。Oracle Cloud 的 preemptible 是隨用隨付價格的一半，沒有保證的最短執行時間，終止前兩分鐘發出一個事件通知，建立後不能停止、啟動或重開，也不能轉成隨用隨付。Google Cloud 與 AWS 的同類機型叫 Spot，規則各自不同，例如 Google Cloud 的 Spot VM 被收回之後可以再啟動。適合跑得斷、可以重來的批次工作；要一直開著的服務與手動設定過的實驗機不適合，被收回時設定會跟著消失。
- **預留容量（capacity reservation）**：先向業者保留一定數量的某種機型容量，之後建主機時從保留的額度裡扣。它處理的是「要用的時候沒有容量」，用在必須在某個時間點拿到主機的情境：大促前要擴容、災難時要在另一區重建、熱門機型經常容量不足。保留期間不論有沒有主機在用都計費。
- **專屬主機（dedicated host）**：整台實體主機只給這個帳號的虛擬機用，不跟其他客戶共用硬體，用在合規要求或授權按實體主機計算的軟體。Oracle Cloud 只允許在建立時把主機放上專屬主機。

Oracle Cloud 的 Capacity type 欄位一次只能選其中一種；AWS 的 capacity reservation 則是讓隨用隨付的主機去使用保留下來的容量，兩者同時成立。預留容量跟用一到三年的承諾換取折扣的 reserved instance 是兩件事：預留容量保證拿得到容量、不打折；AWS 的 reserved instance 打折，而保不保證容量看範圍，以區域為範圍的 regional reserved instance 不保留容量，指定可用區的 zonal reserved instance 另外保留那一區的容量。Reserved instance 與 savings plan 的承諾差異、什麼時候值得買，見 [計費模式理解](/operations/08-cost-management/billing-models/) 的〈承諾模式：用彈性換折扣〉。實驗用的小主機選隨用隨付。

## 停止主機時的計費

停止（stop）跟終止（terminate）是兩件事：停止是關機，主機與磁碟都保留，之後可以再開；終止是刪除主機。Oracle Cloud 的標準機型在停止期間暫停計算資源的計費，但仍然佔用服務配額；Dense I/O、HPC 與多數 GPU 機型停止時照樣計費，要終止才會停。官方另外提醒，在作業系統裡下 `shutdown` 不會停止計費，要從主控台或 API 停止主機。Google Cloud 與 AWS 的規則方向相同：停止期間不收 vCPU 與記憶體的費用，磁碟與保留的公開 IP 照樣計費。磁碟的計費跟主機是否開著無關，見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)。

## 映像檔：開機磁碟上的作業系統

映像檔是建立主機時複製到開機磁碟上的作業系統內容。主控台的映像檔清單通常分成三種來源：

- **業者提供的平台映像（platform image）**：Ubuntu、Oracle Linux、Debian、Windows 等，由業者維護並預先裝好它自己的代理程式（agent，見 [代理程式、中繼資料服務、初始化腳本、維護行為與標籤](/infra/cloud-providers/vm-options/management/)）。實驗與一般用途選這一種。
- **市集映像（marketplace）**：第三方預先裝好特定軟體的映像，部分要另外付授權費。
- **自訂映像（custom image）**：從自己的主機或開機磁碟做出來的映像，用來複製已經設定好的環境。

同一個作業系統常有完整版與 minimal 版。Minimal 版只裝開機與連網需要的套件，開機磁碟用量小、要修補的套件少，代價是常用工具（文字編輯器、部分診斷工具）要自己裝。要登入主機手動操作、排錯的實驗機選完整版；只跑容器或由初始化腳本、[IaC](/infra/knowledge-cards/iac/) 裝好全部軟體、平常不登入的主機選 minimal 版。

映像檔要跟機型的架構一致：Oracle Cloud 的映像清單上，Ubuntu 的 ARM 版名稱帶 `aarch64`、x86 版不帶；AWS 與 Google Cloud 的映像多半以 `arm64` 標示 ARM 版，名稱看不出時看映像詳細資料裡的架構欄位。Oracle Cloud 的主控台只列出這一區有的機型，並把跟已選映像檔不相容的標成不可選；用 CLI 或 API 建立時沒有這層畫面上的提示，映像檔要自己挑對架構。查詢映像檔的指令是 `oci compute image list --compartment-id <tenancy 的 OCID> --shape <機型名稱>`：Oracle Cloud 給每個資源一個唯一識別碼叫 OCID，平台映像列在 tenancy（帳號本身，也是最上層的 compartment）底下，所以 `--compartment-id` 填 tenancy 的 OCID；`--shape` 填機型名稱（例如 `VM.Standard.A1.Flex`），CLI 只回傳跟那個機型相容的映像檔。tenancy 的 OCID 在哪裡查見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。映像檔也決定了預設的登入使用者名稱，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/)。

映像檔只在建立的那一刻複製一次。之後作業系統的更新由主機自己的套件管理員處理，跟映像檔清單上出現的新版本無關；換作業系統同樣要用新的映像檔重建。

## 各家的欄位名稱：機型、可被收回、預留容量與映像檔

| 概念     | Oracle Cloud         | Google Cloud        | AWS                                                        |
| -------- | -------------------- | ------------------- | ---------------------------------------------------------- |
| 機型     | Shape                | Machine type        | Instance type                                              |
| 彈性規格 | Flex shape           | Custom machine type | 無（選固定規格）                                           |
| 可被收回 | Preemptible capacity | Spot VM             | Spot Instance                                              |
| 預留容量 | Capacity reservation | Reservation         | Capacity Reservation                                       |
| 映像檔   | Image                | Image               | [AMI](/infra/knowledge-cards/ami/)（Amazon Machine Image） |

映像檔複製到的那顆開機磁碟能設定的大小、效能與加密，見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)；一台 Always Free 的 A1 Ubuntu 主機實際選的規格與映像檔，見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 的 Basic information 段。
