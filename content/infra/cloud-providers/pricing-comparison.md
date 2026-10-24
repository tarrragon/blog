---
title: "雲端免費額度與小型主機的收費比較：計費單位、區域限制、試用結束後的處置與出站流量"
date: 2026-10-24
description: "Oracle Cloud、Google Cloud 與 AWS 的免費方案分別由哪幾種額度組成，比較時要換算的計費單位，免費主機能放在哪些區域，試用期結束後帳號與資源會怎樣，以及付費主機的價格該去哪裡查"
weight: 1
tags: ["infra", "cloud-providers", "free-tier", "cost"]
---

這篇整理比較各家雲端免費方案與小型主機費用時要對齊的項目。範圍是一台個人或實驗用的小型虛擬機：能不能免費開著、放在哪裡、什麼時候會開始收錢。各家的規則取自官方頁面，查證日期寫在比較表上；價格與額度會改，拿來做決定之前回到表上的連結看一次最新版本。

## 免費方案的兩種額度：有期限的試用金與沒有期限的固定額度

三家的免費方案都由兩種性質不同的額度組成，而比較時常被混在一起。

**試用金**是一筆有期限的金額，可以花在大部分付費服務上。有了它，申請後的頭幾週可以試用較大的機型或付費服務；期限一到、或金額用完，額度就結束。

**固定額度**是每個月重置、沒有期限的用量上限，只適用於指定的機型與服務。一台小主機要長期免費開著，靠的是這一種額度。各家對固定額度的稱呼不同：Oracle Cloud 叫 Always Free，Google Cloud 叫 Free Tier，AWS 叫 Always free services。

要長期跑一台小主機時，看的是固定額度；試用金只影響第一個月。

## 計費單位的換算：OCPU、vCPU 與機型配額

三家描述運算額度的單位不同，直接比數字會比錯。

- **Oracle Cloud 用 OCPU 計**：OCPU 對應實體核心，而換算成 vCPU 的比例依架構不同。官方〈Compute Shapes〉的對照是 x86（AMD、Intel）的 1 OCPU 等於 2 個 vCPU，Ampere A1 的 1 OCPU 等於 1 個 vCPU。Always Free 的 A1 額度以「OCPU 小時」與「GB 小時」計，每月 1,500 OCPU 小時、9,000 GB 小時，可以自由切成一台或兩台；整個月開著的 2 OCPU A1 主機，作業系統看到的是 2 個 vCPU。
- **Google Cloud 以機型與台數計**：Free Tier 是每月一台 `e2-micro`。`e2-micro` 是共享核心機型，作業系統看到 2 個 vCPU，而持續使用量是每個 vCPU 12.5%、合計 25% 的 CPU 時間；每個 vCPU 可以短時間爆發到 100%，全速爆發約 30 秒。持續高負載時，它能用的運算量是 0.25 個 vCPU。
- **AWS 以帳號層級的試用金計**：目前的 Free plan 不再列出每月固定的機型時數，EC2 的用量由試用金支付。

所以「OCI 給 2 OCPU、GCP 給 2 vCPU」這類比較不成立：OCI 的 2 OCPU A1 在持續負載下是 2 個完整的 vCPU，GCP 的 `e2-micro` 是 0.25 個。要比的是在持續負載下能拿到多少運算量，以及免費的部分是以時數、台數還是金額計算。

## 免費主機能放在哪些區域

固定額度通常只適用於部分區域，而區域決定主機的實體位置——從使用者所在地連過去的延遲，以及主機對外連線時出口 IP 屬於哪個國家。

- **Oracle Cloud**：Always Free 的運算與區塊磁碟只能建在 home region，home region 在申請時選定、之後不能改（細節見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)）。
- **Google Cloud**：Free Tier 的 `e2-micro` 只適用於美國的三個區域：`us-west1`（奧勒岡）、`us-central1`（愛荷華）、`us-east1`（南卡羅來納）。在亞洲區域建同一個機型照一般價格計費。
- **AWS**：Free plan 的頁面沒有寫明區域限制。

用途需要特定國家的出口 IP 時（例如要讓連線看起來從日本發出），這一欄是第一個篩選條件。Google Cloud 的固定額度只在美國；Oracle Cloud 的前提是申請時就把 home region 選在那個國家；AWS 的試用金可以花在其他區域，但 Free plan 帳號 6 個月後關閉，長期使用要升級成付費帳戶。

## 試用結束之後帳號與資源怎麼處理

這一項決定沒有特別注意時會發生什麼事：試用期過了，主機是繼續免費、被停掉，還是開始收費。

- **Oracle Cloud**：試用結束後帳號照常存在，Always Free 資源不中斷。用試用金建的付費資源會被回收，除非升級成付費帳戶；A1 總量超過 2 OCPU、12 GB 時，全部 A1 主機會被停用、30 天後刪除。
- **Google Cloud**：試用結束時如果沒有升級成付費帳戶，帳單會被停用、資源會被停止、帳號失去 Google Cloud 產品的存取權，有 30 天的寬限期可以升級回復。Free Tier 的固定額度要在付費帳戶上才能繼續用；升級之後超出額度的用量開始計費。
- **AWS**：Free plan 帳號在開立 6 個月後或試用金用完時（先到者為準）自動關閉，除非升級到 Paid plan；升級之後超出額度的用量開始計費。

三家的預設方向不同：Oracle Cloud 不升級也能留著免費資源，Google Cloud 與 AWS 不升級的話資源會停掉或帳號會關閉，而升級之後這兩家超出額度的部分會直接計費。升級成付費帳戶之前，先照 [GCP 帳單防護](/operations/08-cost-management/spend-protection-gcp-budget-killswitch/) 那篇的思路設好預算警示，讓超出額度的費用在發生時有人收到通知。

## 出站流量與閒置回收

主機本身免費，費用仍可能來自出站流量——主機送到網際網路的資料量。跑 VPN、下載站這類用途，流量才是主要成本。

- **Oracle Cloud**：每月 10 TB 出站流量免費。
- **Google Cloud**：Free Tier 每月 1 GB 從北美送往各地的出站流量（不含中國與澳洲）；超過的部分計費。
- **AWS**：Free plan 頁面沒有單獨列出流量額度。

另一項只有 Oracle Cloud 明文寫出的規則是閒置回收：Always Free 主機連續 7 天的 CPU、網路、記憶體使用率都低於 20% 時，Oracle 可能回收它。一台大部分時間沒有流量的 VPN 或實驗機會落在這個條件裡。

## 比較表（查證日期 2026-10-24）

| 項目               | Oracle Cloud                                                                                                                                                                                         | Google Cloud                                                                       | AWS                                           |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------- |
| 試用金             | 300 美元、30 天                                                                                                                                                                                      | 300 美元、90 天                                                                    | 100 美元起、最多 200 美元、6 個月             |
| 固定額度的運算     | A1 每月 1,500 OCPU 小時與 9,000 GB 小時；E2.1.Micro 兩台                                                                                                                                             | 每月一台 `e2-micro`                                                                | 頁面未列出 EC2 的固定時數                     |
| 固定額度的區域     | 只限 home region                                                                                                                                                                                     | `us-west1`、`us-central1`、`us-east1`                                              | 頁面未寫明                                    |
| 試用結束、不升級時 | 帳號保留、Always Free 資源繼續                                                                                                                                                                       | 資源停止、帳號失去存取權                                                           | 帳號關閉                                      |
| 出站流量           | 每月 10 TB                                                                                                                                                                                           | 每月 1 GB（北美出發）                                                              | 頁面未單獨列出                                |
| 官方頁面           | [Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)、[Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) | [Free cloud features](https://docs.cloud.google.com/free/docs/free-cloud-features) | [AWS Free Tier](https://aws.amazon.com/free/) |

## 付費主機的價格去哪裡查

固定額度不夠用、或要把主機放在固定額度以外的區域時，價格要回到各家的價格頁與計算器查。這篇不列單價，理由是單價隨區域、機型世代與時間改變，寫在這裡的數字很快就會跟讀者看到的帳單對不上。查價時把這幾項一起輸入計算器，算出來的才是一台主機一個月的實際費用：

- 運算：機型、核心數（注意 OCPU 與 vCPU 的換算）、記憶體、每月開機時數
- 開機磁碟的容量與類型
- 公開 IPv4 位址：部分業者對公開 IPv4 位址另外計費
- 出站流量的預估量

## 延伸閱讀：各家的實測紀錄與成本防護

- [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)：Always Free 為什麼綁在 home region、選錯時有哪些路
- [GCP 帳單防護](/operations/08-cost-management/spend-protection-gcp-budget-killswitch/)：升級成付費帳戶之後，用預算警示與停損開關限制超出額度的費用
- [主機形態光譜](/going-live/hosting-spectrum/)：在比較 IaaS 主機之前，先決定服務要自己管到哪一層
