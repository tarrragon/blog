---
title: "Oracle Cloud 的帳號結構與 home region：tenancy、Always Free 的範圍與主控台登入欄位"
date: 2026-10-24
description: "OCI 的 tenancy、home region、compartment 與 availability domain 各自管什麼，home region 為什麼在申請當下就要決定，Always Free 額度的計算與回收規則，以及主控台登入時租用戶與使用者名稱兩個欄位的分工"
weight: 2
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "free-tier"]
---

這篇整理 Oracle Cloud Infrastructure（OCI）帳號申請完成後就固定下來的結構，以及它們怎麼限制 Always Free 額度能用在哪裡。範圍從申請表送出那一刻開始，到在主控台登入為止；從本機用 CLI 操作見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)。文中的規則取自 OCI 官方文件，查證日期 2026-10-24；登入欄位的行為在一個 Free Tier 帳號上實際操作過。

## Tenancy、home region、compartment 與 availability domain

OCI 的帳號叫 **tenancy**（主控台中文介面寫作「租用戶」）。一個 tenancy 對應一個客戶，裡面所有的使用者、群組、政策與資源都屬於它；申請時填的 Cloud Account Name 就是 tenancy 的名稱。Tenancy 與它底下的每一個資源各有一個以 `ocid1.` 開頭的唯一識別碼，叫 OCID（Oracle Cloud ID），CLI 與 API 用它指定要操作的對象；tenancy 的 OCID 在 Tenancy Details 頁，其他資源的在各自的詳細頁上。

**Home region** 是 tenancy 建立時所在的那一個區域。官方文件〈Managing Regions〉說明它存放帳號資訊與身分資源（使用者、群組、政策），而且建立之後不能變更，FAQ 的原文是「No. Oracle assigns your home region and you can't change it.」使用者、群組、政策與 compartment 的定義住在 home region、只能在那裡修改：用 API 改 IAM 資源時要打 home region 的端點，用主控台改時主控台會替使用者把請求送到 home region，改完之後由 IAM 自動傳播到 tenancy 訂閱的其他區域，官方提醒傳播可能要幾分鐘。

Tenancy 可以另外訂閱其他區域（region subscription），訂閱之後能在那一區建資源，而帳號與身分資源仍然住在 home region。訂閱改變的是資源能放在哪裡，不改變 home region。訂閱的數量有上限：官方〈Regions and Availability Domains〉寫明試用、Free Tier 與 Pay As You Go 的 tenancy 都只能有一個訂閱區域，也就是 home region 本身；Pay As You Go 可以申請提高這個上限，試用與 Free Tier 不行。

**Compartment** 是 tenancy 底下用來分組資源與套用政策的容器。Tenancy 本身就是最上層的 root compartment，新帳號一開始只有它。實驗用的資源另開一個 compartment 放，清理時刪那一個 compartment 底下的資源就好，不會碰到 root 裡的其他設定。

**Availability domain**（AD）是一個區域裡彼此隔離的資料中心，跨業者的概念見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/)。區域之間的 AD 數量不同：有些區域有三個，有些只有一個。申請之前，各區域的 AD 數列在官方〈Regions and Availability Domains〉頁的區域表；申請之後，`oci iam availability-domain list`（登入方式見 CLI 那篇）回傳的清單長度就是自己 home region 的 AD 數。AD 數會影響免費機型建不起來時的退路，見〈Always Free 的額度與它綁在 home region 上的範圍〉。

## Always Free 的額度與它綁在 home region 上的範圍

OCI 的免費方案有兩個部分。試用金是 300 美元、30 天內有效，可以用在大部分付費服務上；Always Free 是沒有期限的固定額度，試用結束之後仍然繼續。官方 Free Tier 頁的原文是「After your trial ends, your account remains active. There is no interruption to the availability of the Always Free Resources you have provisioned.」

運算的 Always Free 額度有兩種機型：

- **Ampere A1（`VM.Standard.A1.Flex`，ARM）**：每月 1,500 OCPU 小時與 9,000 GB 小時的記憶體，相當於 2 OCPU、12 GB 記憶體整個月開著。可以全部給一台，也可以拆成兩台各 1 OCPU。OCI 的 OCPU 是一顆實體核心，跟其他業者以 vCPU 計價時的單位不同，比較時見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。
- **AMD Micro（`VM.Standard.E2.1.Micro`，x86）**：最多兩台，每台 1/8 OCPU、1 GB 記憶體。

儲存與網路另有額度：開機磁碟與區塊磁碟合計 200 GB（每台主機的開機磁碟預設 50 GB，也算在這 200 GB 裡）、備份最多 5 份、出站流量每月 10 TB；試用結束後沒有升級的 Free Tier tenancy，VCN 最多 2 個。

**運算與區塊磁碟的 Always Free 額度只能用在 home region。** Free Tier 頁寫的是「You can provision Always Free Autonomous AI Databases and compute instances only in the home region」，區塊磁碟也有同樣的限制。訂閱了其他區域、在那裡建主機，那台主機照一般價格計費。所以 home region 同時決定了免費主機的實體位置——對外連線時的出口 IP 在哪個國家、從使用者所在地連過去的延遲多少。

A1 免費機型在某個 AD 暫時沒有容量時，建立主機的 API 回 `Out of host capacity`。官方 Always Free 頁建議的退路是換一個 AD、等一段時間再試，或升級成付費帳戶；Compute 的〈Known Issues〉頁另外列了不指定 fault domain、改用較小的機型規格，以及建立前用 `CreateComputeCapacityReport` 這個 API 查某個機型當下有沒有容量。Home region 只有一個 AD 時，換 AD 這一條用不上。實測在一個只有一個 AD 的區域（`ap-batam-1`），建立 A1 主機的請求先以 90 秒的間隔送了九次，前三次收到 `429 TooManyRequests`（請求太頻繁被限流）、後六次是 `Out of host capacity`；間隔 90 秒會觸發限流，之後改成 5 分鐘一次。

改用 E2.1.Micro 也不一定是退路：區域之間提供的機型不同，`ap-batam-1` 的 AD 根本沒有 E2.1.Micro，而帳號的服務配額表照樣列出 `vm-standard-e2-1-micro-count` 為 2。配額表列的是帳號允許開多少，不代表那一區有這種硬體；在沒有這個機型的區域建立 Micro 主機，API 回的是 `404 NotAuthorizedOrNotFound`，這個錯誤碼同時涵蓋權限不足與資源不存在，從訊息本身分不出是哪一種。一個區域實際提供哪些機型，用 `oci compute shape list --compartment-id <compartment 的 OCID> --availability-domain <AD 名稱>` 查，回傳的清單才是那個 AD 能建的機型；AD 名稱要填 `oci iam availability-domain list` 回傳的完整名稱，它帶有 tenancy 專屬的前綴，只寫 `AD-1` 會失敗。這條指令要先有 tenancy 才能跑，所以申請之前沒有辦法確認某一區有沒有 E2.1.Micro；申請之後才發現缺機型時，能做的事見〈選錯 home region 之後的選項〉。

Always Free 的主機另有兩條回收規則：

- **閒置回收**：連續 7 天內 CPU 使用率（第 95 百分位）、網路使用率、記憶體使用率（只算 A1）三項都低於 20%，Oracle 可能回收這台主機。只在需要時才登入的實驗機會符合這個條件。
- **試用結束時超出額度**：試用期間用試用金建了超過 2 OCPU、12 GB 的 A1 主機，試用結束時全部 A1 主機會被停用，30 天後刪除，除非升級成付費帳戶；用試用金建的其他付費資源同樣會被回收。要保留 A1 主機，試用結束前把總量降回 2 OCPU、12 GB 以內。

## 選 home region 時要先確認的事

Home region 在申請表上是一個下拉選單，它同時決定了免費主機的實體位置（出口 IP 的國家、延遲）與容量不足時有沒有別的 AD 可以換。選之前先確認這台免費主機要做什麼：

- **用途需要特定國家的出口 IP**（例如要讓連線看起來從日本發出）：只有那個國家的區域符合，其他區域的延遲再低都達不到目的。
- **用途是給特定地區的使用者連**：選離使用者近的區域，延遲由距離決定。
- **主要拿來實驗**：優先選 AD 多的大型區域（官方區域表上 AD 數為 3 的那幾個），A1 容量不足時有其他 AD 可以換。

## 選錯 home region 之後的選項

Home region 不能改；官方有刪除 tenancy 的流程（〈Deleting a Free Tier Tenancy and Cloud Account〉：管理員在 Tenancy Details 頁按「Request tenancy deletion」），刪除後資源先被暫停、30 天後永久刪除且無法復原，而官方文件沒有寫明刪除之後能不能用同一個 email 與付款方式重新申請。走這條路之前，先開 support ticket 問清楚重新申請的條件。另一條路是升級成 Pay As You Go、在 Limits, quotas and usage 申請提高訂閱區域的上限（Subscribed region count），核准後訂閱想要的區域，在那裡建付費主機，Always Free 額度則繼續留在原本的 home region。

## 主控台登入：租用戶與使用者名稱兩個欄位

OCI 的登入頁把登入拆成兩個欄位，依序出現：

1. **租用戶（Cloud Account Name）**：填 tenancy 的名稱，也就是申請時取的帳戶名稱。OCI 用它找到要登入的是哪一個 tenancy。已經登入的主控台上，右上角人像選單的「租用戶」或「Tenancy:」後面就是這個值。
2. **使用者名稱**：填 tenancy 裡那個使用者的名稱。申請時建立的管理員帳號，使用者名稱是申請用的 email。頁面要求選 identity domain 時選 `Default`。

兩個欄位任一個填錯，登入頁顯示的都是同一句「使用者名稱或密碼無效」，不會指出是哪一欄錯。實際登入時，租用戶欄填對、使用者名稱欄填成 tenancy 名稱，得到的就是這句訊息，密碼本身沒有錯。從本機用 `oci session authenticate` 登入時開出的瀏覽器頁面是同一個登入頁，欄位與錯誤訊息相同。

## 延伸閱讀：CLI 登入、免費額度比較與管理通道

- [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)：同一個 tenancy 從終端機登入，session token 的時效與 API 簽章金鑰的取捨
- [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)：Always Free 的 home region 限制與 GCP、AWS 的區域限制並排
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)：在 OCI 建好主機之後，管理員怎麼登入它的三層模型
