---
title: "磁碟：開機磁碟的大小、效能、加密與去留"
date: 2026-10-24
description: "建立虛擬機時儲存區塊的選項：開機磁碟的大小與只能加大的限制、效能等級與費用的關係、靜態加密與傳輸中加密、另外掛載的區塊磁碟，以及終止主機時開機磁碟預設會不會一起刪除"
weight: 5
tags: ["infra", "cloud-providers", "vm", "storage", "block-volume"]
---

這篇說明建立頁上儲存區塊的選項。範圍是掛在單一台主機上的磁碟；備份、快照與跨區域複製的設計另見各家的區塊儲存文件。

## 開機磁碟與區塊磁碟

雲端主機的磁碟跟主機本身是兩個獨立的資源。**開機磁碟**（Oracle Cloud 叫 boot volume）在建立主機時從映像檔複製出來，裝著作業系統；**區塊磁碟**（block volume）是另外建立、掛上去的資料磁碟，作業系統看到的是一顆新的空磁碟，要自己分割與格式化。兩種都是經由網路掛到主機上的虛擬磁碟，主機停止時資料保留，主機終止之後磁碟可以單獨存在，見 [EBS](/infra/knowledge-cards/ebs/) 卡裡同一個概念在 AWS 上的說明。

實驗用的小主機只用開機磁碟就夠。資料要跟作業系統分開管理時（重裝系統而保留資料、把資料搬到另一台主機），資料放在區塊磁碟上。Oracle Cloud 的建立頁最多可以同時建立並掛載 10 顆區塊磁碟，也可以之後再掛。

## 開機磁碟的大小

開機磁碟的預設大小由映像檔決定。Oracle Cloud 的建立頁可以勾選自訂大小，範圍是 50 GB 到 32 TB，且要大於映像檔的預設值。Always Free 的儲存額度是開機磁碟與區塊磁碟合計 200 GB，一台主機的開機磁碟加大到 200 GB 就用完了全部額度，第二台主機的開機磁碟會開始計費。

磁碟的大小**只能加大、不能縮小**。Oracle Cloud 支援在主機開著的時候線上加大，加大之後要在作業系統裡把分割區與檔案系統延伸到新的大小，作業系統才用得到新增的空間。所以建立時先用預設大小，空間不夠再加；一開始開得太大，之後想縮回去只能建新磁碟、把資料搬過去。

## 效能等級

區塊儲存的讀寫速度可以獨立於容量另外設定。Oracle Cloud 用 VPU（volume performance unit，每 GB 配幾個效能單位）分級：

| 等級                   | 每 GB 的 VPU | 用途                       |
| ---------------------- | ------------ | -------------------------- |
| Lower Cost             | 0            | 不常讀寫的資料，只付儲存費 |
| Balanced               | 10           | 開機磁碟與一般用途的預設值 |
| Higher Performance     | 20           | 資料庫這類讀寫頻繁的負載   |
| Ultra High Performance | 30 到 120    | 需要高 IOPS 與低延遲的負載 |

VPU 另外計費：Lower Cost 只收儲存費，其餘等級在儲存費之外加收效能費。開機磁碟的預設是 Balanced，實驗機維持預設即可。效能等級在磁碟建立之後可以修改，不必重建磁碟。

## 加密

- **靜態加密（encryption at rest）**：磁碟上的資料預設就是加密的，金鑰由業者管理，不必另外設定。要自己掌握金鑰時（合規要求、要能撤銷金鑰讓資料失效），可以改用自己在金鑰管理服務（Oracle Cloud 的 Vault）建立的金鑰。Oracle Cloud 的區塊儲存只支援 AES 金鑰，不支援 RSA 金鑰。
- **傳輸中加密（in-transit encryption）**：主機與磁碟之間經由網路傳送的資料也加密。Oracle Cloud 的虛擬機可以選擇開或不開，建立頁的預設是開啟；支援的裸機主機則固定開啟。用自己的 Vault 金鑰時，同一把金鑰也用在傳輸中加密。

兩項都維持預設不會降低安全性，也不影響費用。

## 終止主機時，開機磁碟會不會一起刪除

這一項三家的預設不同，而且是最容易留下意外費用的地方：

- **Oracle Cloud**：終止主機時，開機磁碟**預設保留**。主控台的終止對話框裡有一個「Permanently delete the attached boot volume」的勾選框，不勾就保留。跟主機一起建立的區塊磁碟同樣預設保留，另有一個勾選框控制。保留下來的開機磁碟可以拿來重建主機，或當成資料磁碟掛到另一台主機上。
- **Google Cloud**：開機磁碟預設跟著主機一起刪除（建立時的「刪除執行個體時一併刪除開機磁碟」預設勾選）。
- **AWS**：根磁碟預設跟著主機一起刪除（`DeleteOnTermination` 預設為 true）。

在 Oracle Cloud 上刪除實驗機時，要嘛勾選刪除開機磁碟，要嘛在之後到 Block Storage → Boot Volumes 確認有沒有留下不要的磁碟。保留的磁碟是一個仍然存在的資源；官方的終止說明沒有寫它是否計費，而它佔用的是區塊儲存，Always Free 的 200 GB 額度算的正是開機磁碟與區塊磁碟的合計。

## 各家的欄位名稱

| 概念       | Oracle Cloud                    | Google Cloud                | AWS                        |
| ---------- | ------------------------------- | --------------------------- | -------------------------- |
| 開機磁碟   | Boot volume                     | Boot disk                   | Root volume（EBS）         |
| 資料磁碟   | Block volume                    | Persistent Disk / Hyperdisk | EBS volume                 |
| 效能等級   | VPU（Volume performance units） | Disk type（pd-standard 等） | Volume type（gp3、io2 等） |
| 終止時刪除 | 預設保留                        | 預設刪除                    | 預設刪除                   |

## 延伸閱讀：磁碟之外的建立選項

- [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/)：開機磁碟的內容來自哪一個映像檔、停止主機時哪些資源還在計費
- [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/)：Oracle Cloud 的 Block Volume Management plugin 負責替主機設定區塊磁碟的連線
