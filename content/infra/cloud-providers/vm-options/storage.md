---
title: "磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留"
date: 2026-10-24
description: "雲端主機的磁碟選項：開機磁碟的大小與只能加大的限制、效能等級與費用的關係、靜態加密與傳輸中加密、另外掛載的區塊磁碟，以及刪除主機時開機磁碟是否預設一起刪除"
weight: 5
tags: ["infra", "cloud-providers", "vm", "storage", "block-volume"]
---

建立頁的儲存區塊決定主機的資料放在哪裡、能放多少、讀寫多快，以及刪除主機時資料是否跟著刪除。範圍是掛在單一台主機上的磁碟；備份、快照與跨區域複製的設計另見各家的區塊儲存文件。文中的大小上限、效能等級與預設值取自各家官方文件，查證日期 2026-10-24。

## 開機磁碟與區塊磁碟

雲端主機的磁碟跟主機本身是兩個獨立的資源。**開機磁碟**（Oracle Cloud 叫 boot volume）在建立主機時從映像檔複製出來，裝著作業系統；**區塊磁碟**（block volume）是另外建立、掛上去的資料磁碟，作業系統看到的是一顆新的空磁碟，要自己分割與格式化。兩種都是經由網路掛到主機上的虛擬磁碟，主機停止時資料保留，主機終止之後磁碟可以單獨存在，見 [EBS](/infra/knowledge-cards/ebs/) 卡裡同一個概念在 AWS 上的說明。

實驗用的小主機只用開機磁碟就夠。資料要跟作業系統分開管理時（重裝系統而保留資料、把資料搬到另一台主機），資料放在區塊磁碟上。Oracle Cloud 的建立頁最多可以同時建立並掛載 10 顆區塊磁碟，也可以之後再掛。

## 開機磁碟的大小

開機磁碟的預設大小由映像檔決定，Oracle Cloud 的 Linux 平台映像預設是 50 GB。建立頁可以勾選自訂大小，範圍是 50 GB 到 32 TB，且不能小於映像檔的預設值。免費額度按磁碟容量計算時，加大開機磁碟會直接吃掉額度：Oracle Cloud 的 Always Free（不會到期的免費額度）給的是開機磁碟與區塊磁碟合計 200 GB，一台主機的開機磁碟加大到 200 GB，第二台主機的開機磁碟就超出額度。超出之後的結果依帳號狀態而定，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉；手上已經用掉多少，到區塊儲存服務的開機磁碟與區塊磁碟清單把每顆的大小加起來。

磁碟的大小**只能加大、不能縮小**。Oracle Cloud 支援在主機開著的時候線上加大，加大之後要在作業系統裡把分割區與檔案系統延伸到新的大小，作業系統才用得到新增的空間：一般 Linux 用 `growpart` 延伸分割區，再依檔案系統用 `resize2fs`（ext4）或 `xfs_growfs`（XFS）延伸檔案系統，Oracle Linux 的平台映像另附一支 `oci-growfs` 一次做完。所以建立時先用預設大小，空間不夠再加；一開始開得太大，之後想縮回去只能建新磁碟、把資料搬過去。

## 效能等級

磁碟的讀寫速度有兩種決定方式：獨立於容量另外設定，或依容量換算。Oracle Cloud 與 AWS 的 gp3 讓效能獨立於容量另外設定；Google Cloud 的 Persistent Disk 依容量換算，磁碟類型決定每 GB 的效能，容量越大效能越高。Oracle Cloud 用 VPU（volume performance unit，每 GB 配幾個效能單位）分級：

| 等級                   | 每 GB 的 VPU | 用途                                             |
| ---------------------- | ------------ | ------------------------------------------------ |
| Lower Cost             | 0            | 大量循序讀寫（串流、日誌處理），只能用在區塊磁碟 |
| Balanced               | 10           | 開機磁碟與一般用途的預設值                       |
| Higher Performance     | 20           | 資料庫這類讀寫頻繁的負載                         |
| Ultra High Performance | 30 到 120    | 需要高 IOPS（每秒讀寫次數）與低延遲的負載        |

VPU 另外計費：Lower Cost 只收儲存費，其餘等級在儲存費之外加收效能費。開機磁碟不能選 Lower Cost，預設是 Balanced。官方的 Always Free 頁只寫了 200 GB 的容量，沒有寫這 200 GB 涵蓋哪個效能等級；建立頁在 Always Free 主機上預設給的是 Balanced，實驗機維持預設，建好之後到帳單的成本分析頁看區塊儲存有沒有出現費用，就能確認自己的帳號怎麼算。Oracle Cloud 的效能等級在磁碟建立之後可以修改，不必重建磁碟；主機上的磁碟延遲或 iowait 長時間偏高、資料庫查詢因為讀寫變慢時，就是該往上調的訊號。

## 加密

- **靜態加密（encryption at rest）**：Oracle Cloud 與 Google Cloud 的磁碟預設就是加密的，金鑰由業者管理，不必另外設定；AWS 的 EBS 要在每個區域打開 EBS encryption by default，新磁碟才會預設加密。要自己掌握金鑰時（合規要求、要能撤銷金鑰讓資料失效），可以改用自己在金鑰管理服務（Oracle Cloud 的 Vault）建立的金鑰。Oracle Cloud 的區塊儲存只支援 AES 金鑰，不支援 RSA 金鑰。
- **傳輸中加密（in-transit encryption）**：主機與磁碟之間經由網路傳送的資料也加密。Oracle Cloud 的虛擬機可以選擇開或不開，建立頁的預設是開啟（[實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/)的 Storage 段，2026-10-24 建立 A1 Ubuntu 主機時）；支援的裸機主機則固定開啟。用自己的 Vault 金鑰時，同一把金鑰也用在傳輸中加密。

在 Oracle Cloud 上兩項都維持預設不會降低安全性，也不影響費用；在 AWS 上要先確認那個區域的預設加密有打開。

## 刪除（終止）主機時開機磁碟的預設去留

這一項三家的預設不同，而 Oracle Cloud 的預設是保留，刪了主機之後磁碟還在：

- **Oracle Cloud**：終止主機時，開機磁碟**預設保留**。主控台的終止對話框裡有一個「Permanently delete the attached boot volume」的勾選框，不勾就保留。跟主機一起建立的區塊磁碟同樣預設保留，另有一個勾選框控制。保留下來的開機磁碟可以拿來重建主機，或當成資料磁碟掛到另一台主機上。
- **Google Cloud**：開機磁碟預設跟著主機一起刪除，建立頁開機磁碟的 Deletion rule 預設是 Delete disk。
- **AWS**：建立主機時一起掛上的根磁碟預設跟著主機一起刪除（`DeleteOnTermination` 預設為 true，這個值來自 AMI 的設定）；之後另外掛上的資料磁碟預設保留。

在 Oracle Cloud 上刪除實驗機時，要嘛勾選刪除開機磁碟，要嘛在之後到區塊儲存服務的開機磁碟清單確認有沒有留下不要的磁碟。保留的磁碟是一個仍然存在的資源。官方的終止說明沒有寫它是否計費，而 Always Free 頁寫明 200 GB 算的是開機磁碟與區塊磁碟的合計，額度用完時要刪掉主機與它的開機磁碟才能空出空間；所以留下來的開機磁碟繼續佔著額度，額度用完之後再建的磁碟就超出額度。

這類主機刪了、自己卻還存在而沒有人記得的資源，叫孤兒資源（orphaned resource），各家的帳單上都會出現，見 [計費模型](/operations/08-cost-management/billing-models/) 的隱藏成本。Oracle Cloud 的這個預設最容易在反覆建刪實驗機時累積起來。用過 Google Cloud、AWS 的人，習慣刪了主機就等於刪了開機磁碟；在 Oracle Cloud 上每刪一台都留下一顆 50 GB 的開機磁碟，而主機清單上已經看不到它，它列在另一個選單（區塊儲存服務的開機磁碟清單），額度還沒用完時帳單上也不會出現任何費用。建刪四輪之後 200 GB 就被這些磁碟佔滿，第五台主機的開機磁碟就超出額度，這時才要回頭逐顆辨認哪些磁碟可以刪。

## 各家的欄位名稱：開機磁碟、資料磁碟、效能等級與終止時的預設

| 概念       | Oracle Cloud                    | Google Cloud                | AWS                        |
| ---------- | ------------------------------- | --------------------------- | -------------------------- |
| 開機磁碟   | Boot volume                     | Boot disk                   | Root volume（EBS）         |
| 資料磁碟   | Block volume                    | Persistent Disk / Hyperdisk | EBS volume                 |
| 效能等級   | VPU（Volume performance units） | Disk type（pd-standard 等） | Volume type（gp3、io2 等） |
| 終止時刪除 | 預設保留                        | 預設刪除                    | 預設刪除                   |

## 延伸閱讀：磁碟之外的建立選項

- [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)：開機磁碟的內容來自哪一個映像檔、停止主機時哪些資源還在計費
- [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/) 的 Management 段：Oracle Cloud 代理程式的 Block Volume Management plugin 與其他 plugin 的用途
