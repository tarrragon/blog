---
title: "雲端免費額度與小型主機的收費比較：試用金與固定額度、計費單位、區域限制、試用結束後的處置、出站流量與查價項目"
date: 2026-10-24
description: "Oracle Cloud、Google Cloud 與 AWS 的免費方案分別由哪幾種額度組成，比較時要換算的計費單位，免費主機能放在哪些區域，試用期結束後帳號與資源會怎樣，以及付費主機的價格該去哪裡查"
weight: 1
tags: ["infra", "cloud-providers", "free-tier", "cost", "oracle-cloud", "gcp", "aws"]
---

這篇整理比較 Oracle Cloud、Google Cloud 與 AWS 的免費方案與小型主機費用時要對齊的項目。範圍是一台個人或實驗用的小型虛擬機：能不能免費開著、放在哪裡、什麼時候會開始收錢；服務要不要跑在自己管的虛擬機上、還是交給 PaaS 或 serverless，是比這一篇更早的決定，見 [主機形態光譜](/going-live/hosting-spectrum/)。AWS 的部分指的是 2025-07-15 起開立、開帳號時選 Free account plan 的帳號。2025-07-15 之前開的帳號適用舊的 Free Tier：EC2 使用指南〈[Track your Free Tier usage for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)〉的〈Free Tier benefits before and after July 15, 2025〉對照表寫明，舊帳號的 Free Tier 從開戶日起算 12 個月，免費機型是 `t2.micro` 與 `t3.micro`，超出額度的用量照 pay-as-you-go 價格計費；這篇其餘寫到 AWS 試用金與 Free plan 的地方不適用於這種帳號。各家的規則取自官方頁面，查證日期寫在比較表上；價格與額度會改，拿來做決定之前回到表上的連結看一次最新版本。

## 免費方案的兩種額度：有期限的試用金與沒有期限的固定額度

三家的免費方案都由兩種性質不同的額度組成：試用金與固定額度。

**試用金**（free trial credits）是一筆有期限的金額，可以花在大部分付費服務上。有了它，試用期限內可以試用較大的機型或付費服務；期限一到、或金額用完，額度就結束。

**固定額度**是每個月重置、沒有期限的用量上限，只適用於指定的機型與服務。一台小主機要長期免費開著，靠的是這一種額度。各家對固定額度的稱呼不同：Oracle Cloud 叫 Always Free，Google Cloud 叫 Free Tier，AWS 叫 Always free services。

要長期跑一台小主機時，看的是固定額度；試用金只影響開頭那一段期限（Oracle Cloud 30 天、Google Cloud 90 天、AWS 6 個月，見比較表）。AWS 目前的 Free plan 沒有 EC2 的固定額度，長期跑主機要升級成付費帳戶，見下一節。

## 計費單位的換算：OCPU、vCPU 與機型配額

三家描述運算額度的單位不同。比較的基準是 vCPU：作業系統看到的一個虛擬處理器。多數 x86 機型的一顆實體核心跑兩個硬體執行緒（超執行緒），雲端業者把每個硬體執行緒算成一個 vCPU，這時一個 vCPU 是半顆核心。例外是每核只跑一個執行緒的 x86 機型：AWS 的 [CPU 選項對照表](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/cpu-options-supported-instances-values.html) 上，AMD 處理器的 M7a、C7a、R7a 與 M8a、C8a、R8a 等系列每核執行緒數只有 1，它們的一個 vCPU 就是一顆實體核心。ARM 處理器裡，Oracle Cloud 的 Ampere A1 與 AWS Graviton 每核一個執行緒，一顆核心就是一個 vCPU；Oracle Cloud 較新的 Arm 機型 A2 與 A4 的 OCPU 換算跟 A1 不同，見下方 Oracle Cloud 那一項。

- **Oracle Cloud 用 OCPU 計**：官方〈[Compute Shapes](https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm)〉的〈OCPUs and vCPUs〉一節把 OCPU 定義為實體核心，換算成 vCPU 的比例依處理器不同：x86（AMD、Intel）的 1 OCPU 等於 2 個 vCPU，Ampere A1 的 1 OCPU 等於 1 個 vCPU；同一節另列較新的 Arm 機型 A2 與 A4，它們的 1 OCPU 等於 2 顆核心、也就是 2 個 vCPU，不在 Always Free 額度內。Always Free 的 A1 額度以「OCPU 小時」與「GB 小時」計，每月 1,500 OCPU 小時、9,000 GB 小時，可以自由切成一台或兩台；整個月開著的 2 OCPU A1 主機，作業系統看到的是 2 個 vCPU。
- **Google Cloud 以機型與台數計**：Free Tier 是每月一台 `e2-micro`。`e2-micro` 是共享核心機型，作業系統看到 2 個 vCPU，而持續使用量是每個 vCPU 12.5%、合計 25% 的 CPU 時間；每個 vCPU 可以短時間爆發到 100%，全速爆發約 30 秒。持續高負載時，它能用的運算量是 0.25 個 vCPU。
- **AWS 以帳號層級的試用金計**：目前的 Free plan 不再列出每月固定的機型時數，EC2 的用量由試用金支付。

所以「OCI 給 2 OCPU、GCP 給 2 vCPU」這類比較不成立：OCI 的 2 OCPU A1 在持續負載下是 2 個完整的 vCPU，GCP 的 `e2-micro` 是 0.25 個。要比的是在持續負載下能拿到多少運算量，以及免費的部分是以時數、台數還是金額計算。

## 固定額度的區域限制

固定額度通常只適用於部分區域，而區域決定主機的實體位置——從使用者所在地連過去的延遲，以及主機對外連線時出口 IP 屬於哪個國家。

- **Oracle Cloud**：Always Free 的運算與區塊磁碟只能建在 home region，home region 在申請時選定、之後不能改（細節見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)）。
- **Google Cloud**：Free Tier 的 `e2-micro` 只適用於美國的三個區域：`us-west1`（奧勒岡）、`us-central1`（愛荷華）、`us-east1`（南卡羅來納）。在亞洲區域建同一個機型照一般價格計費。
- **AWS**：〈[Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/)〉寫明試用金與方案選擇在中國的 ZHY、BJS 兩區不提供（原文「The AWS Free Tier credits and account plan selections are not available in the China (ZHY) and China (BJS) regions.」），GovCloud（US）區域不適用 Free Tier（Lambda 等少數服務例外）；其他區域 FAQ 沒有列出限制。

用途需要特定國家的出口 IP 時（例如要讓連線看起來從日本發出），固定額度的區域限制是第一個篩選條件。Google Cloud 的固定額度只在美國；Oracle Cloud 的前提是申請時就把 home region 選在那個國家，而那個國家的區域多半只有一個可用區，A1 免費機型容量不足時沒有別的可用區可以換（容量不足時還有哪些退路，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈A1 容量不足時的退路〉）；AWS 的 Free Tier FAQ 排除的只有中國與 GovCloud 的區域，日本的區域不在排除之列，而 Free plan 帳號最晚 6 個月後關閉，長期使用要升級成付費帳戶。

## 試用結束後帳號與資源的處置

試用期結束、而沒有升級成付費帳戶時，主機繼續免費、被停掉還是開始收費，各家不同。

- **Oracle Cloud**：試用結束後帳號照常存在，Always Free 資源不中斷。除非升級成付費帳戶，用試用金建的付費資源會被回收；tenancy 裡全部 A1 主機的合計超過 2 OCPU、12 GB 時，全部 A1 主機會被停用、30 天後刪除。A1 合計的判斷方式與試用結束前怎麼避免，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈Always Free 的額度與它綁在 home region 上的範圍〉。
- **Google Cloud**：試用結束時如果沒有升級成付費帳戶，帳單帳戶會被停用、資源會被停止、帳號失去 Google Cloud 產品的存取權，有 30 天的寬限期可以升級回復。Free Tier 的固定額度要在付費帳戶上才能繼續用；升級之後超出額度的用量開始計費。
- **AWS**：Free plan 在開立 6 個月後或試用金用完時（先到者為準）結束，帳號隨即自動關閉、失去資源與資料的存取權；AWS 保留帳號內容 90 天，90 天內升級到 Paid plan 可以保住帳號的存取權，剩下的試用金會用在之後的帳單上。升級之後超出試用金的用量開始計費。

三家在不升級時的處置不同：Oracle Cloud 不升級也能留著免費資源，Google Cloud 與 AWS 不升級的話資源會停掉或帳號會關閉，而升級之後這兩家超出額度的部分會直接計費。升級成付費帳戶之前先設好預算警示，讓超出額度的費用在發生時有人收到通知。預算警示的門檻怎麼訂、從預算通知觸發停損的建置，目前只寫在 Google Cloud 的實作篇 [GCP 上的雲端費用失控防護](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)；成本監控與異常告警的設計見 [運行期維運的成本管理](/operations/08-cost-management/)。Oracle Cloud 不同帳號狀態下超出額度的結果，見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉。

## 出站流量與閒置回收

主機本身免費，費用仍可能來自出站流量（outbound data transfer，也常寫作 egress）——主機送到網際網路的資料量。跑 VPN、下載站這類用途，流量才是主要成本。出站流量在整份帳單裡跟其他隱藏成本（NAT 閘道的流量費、被遺忘的資源）放在一起看，見 [計費模式理解](/operations/08-cost-management/billing-models/) 的〈隱藏成本：帳單上的意外〉。

- **Oracle Cloud**：每月 10 TB 出站流量免費。
- **Google Cloud**：Free Tier 每月 1 GB 從北美送往各地的出站流量（不含中國與澳洲）；超過的部分計費。
- **AWS**：Free plan 頁面沒有列流量額度，額度寫在 EC2 的價格頁：每月 100 GB 送往網際網路的出站流量免費，所有服務與區域合計（不含中國與 GovCloud 區域）。

另一項只有 Oracle Cloud 明文寫出的規則是閒置回收：Always Free 主機在 7 天內的 CPU 使用率（取第 95 百分位）、網路使用率、記憶體使用率（只算 A1 機型）都低於 20% 時，Oracle 可能回收它（官方沒有寫網路使用率的 20% 是對什麼的比例）；官方頁用的詞是 reclaim，沒有寫回收之後主機是停止還是刪除。規則的出處見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。一台大部分時間沒有流量的 VPN 或實驗機會落在這個條件裡。

## 三家免費方案比較表（查證日期 2026-10-24）

| 項目               | Oracle Cloud                                                                                                                                                                                         | Google Cloud                                                                       | AWS                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 試用金             | 300 美元、30 天                                                                                                                                                                                      | 300 美元、90 天                                                                    | 註冊後 100 美元，完成官方列出的入門活動（例如用 EC2 建一台主機、用 AWS Budgets 設預算）最多再加 100 美元；Free plan 最長 6 個月                                                                                                                                                                                                                                                                                      |
| 固定額度的運算     | A1 每月 1,500 OCPU 小時與 9,000 GB 小時；E2.1.Micro 兩台                                                                                                                                             | 每月一台 `e2-micro`                                                                | 頁面未列出 EC2 的固定時數                                                                                                                                                                                                                                                                                                                                                                                            |
| 固定額度的區域     | 只限 home region                                                                                                                                                                                     | `us-west1`、`us-central1`、`us-east1`                                              | 試用金與方案選擇不含中國（ZHY、BJS），GovCloud 不適用（FAQ）                                                                                                                                                                                                                                                                                                                                                         |
| 固定額度的磁碟     | 開機磁碟與區塊磁碟合計 200 GB                                                                                                                                                                        | 30 GB-months 的 standard persistent disk（開機磁碟類型要選 standard 才算）         | 頁面未列出                                                                                                                                                                                                                                                                                                                                                                                                           |
| 試用結束、不升級時 | 帳號保留、Always Free 資源繼續（A1 合計超額時全部 A1 停用）                                                                                                                                          | 資源停止、帳號失去存取權                                                           | 帳號關閉                                                                                                                                                                                                                                                                                                                                                                                                             |
| 出站流量           | 每月 10 TB                                                                                                                                                                                           | 每月 1 GB（北美出發）                                                              | 每月 100 GB（所有服務合計，列在 EC2 價格頁）                                                                                                                                                                                                                                                                                                                                                                         |
| 官方頁面           | [Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)、[Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) | [Free cloud features](https://docs.cloud.google.com/free/docs/free-cloud-features) | [AWS Free Tier](https://aws.amazon.com/free/)、[Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/)、[Track your Free Tier usage for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)、[Choosing a plan](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)、[EC2 On-Demand Pricing](https://aws.amazon.com/ec2/pricing/on-demand/) |

## 查付費主機價格時要輸入的項目

固定額度不夠用、或要把主機放在固定額度以外的區域時，價格要回到各家的價格頁與計算器查。這篇不列單價，理由是單價隨區域、機型世代與時間改變，寫在這裡的數字很快就會跟讀者看到的帳單對不上。查價時把這幾項一起輸入計算器，算出來的才是一台主機一個月的實際費用：

- 運算：機型、核心數（注意 OCPU 與 vCPU 的換算）、記憶體、每月開機時數
- 開機磁碟的容量與類型
- 公開 IPv4 位址：AWS 對每個公開 IPv4 位址按小時另外計費，其他業者去各自價格頁的 IP 位址那一項查
- 出站流量的預估量
- 負載平衡器：服務對外、主機留在私有 subnet 時要用。Oracle Cloud 的 Always Free 含一個 10 Mbps 的負載平衡器，AWS 與 Google Cloud 另外計費
- NAT 閘道：私有 subnet 的主機要下載套件更新時要用，AWS 的 NAT Gateway 與 Google Cloud 的 Cloud NAT 另外計費
