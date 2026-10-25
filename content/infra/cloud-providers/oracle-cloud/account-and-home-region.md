---
title: "Oracle Cloud 的帳號結構與 home region：tenancy、Always Free 的範圍與主控台登入欄位"
date: 2026-10-24
description: "OCI 的 tenancy、home region、compartment 與 availability domain 各自管什麼，home region 為什麼在申請當下就要決定，Always Free 額度的計算與回收規則，以及主控台登入時租用戶與使用者名稱兩個欄位的分工"
weight: 2
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "free-tier"]
---

Oracle Cloud Infrastructure（OCI）帳號裡的 home region 在申請表送出的那一刻就固定，之後不能改，而 Always Free 的運算與區塊磁碟額度只能用在 home region，所以〈選 home region 時要先確認的事〉那一節要在送出申請表之前讀。這篇整理 tenancy、home region、compartment 與 availability domain 各自的範圍、它們怎麼限制 Always Free 額度能用在哪裡，以及在主控台登入時兩個欄位的填法；從本機用 CLI 操作見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)。文中的規則取自 OCI 官方文件，查證日期 2026-10-24；登入欄位的行為在一個 Free Tier 帳號上實際操作過。

## Tenancy、home region、compartment 與 availability domain

OCI 的帳號叫 **tenancy**（主控台中文介面寫作「租用戶」）。一個 tenancy 對應一個客戶，裡面所有的使用者、群組、政策與資源都屬於它；申請時填的 Cloud Account Name 就是 tenancy 的名稱。Tenancy 與它底下的每一個資源各有一個以 `ocid1.` 開頭的唯一識別碼，叫 OCID（Oracle Cloud ID），CLI 與 API 用它指定要操作的對象；tenancy 的 OCID 在 Tenancy Details 頁，其他資源的在各自的詳細頁上。

**Home region** 是 tenancy 建立時所在的那一個區域。官方文件〈[Managing Regions](https://docs.oracle.com/en-us/iaas/Content/Identity/regions/managingregions.htm)〉說明它存放帳號資訊與身分資源（使用者、群組、政策），而且建立之後不能變更，FAQ 的原文是「No. Oracle assigns your home region and you can't change it.」使用者、群組、政策與 compartment 的定義住在 home region、只能在那裡修改：用 API 改 IAM 資源時要打 home region 的端點，用主控台改時主控台會替使用者把請求送到 home region，改完之後由 IAM 自動傳播到 tenancy 訂閱的其他區域，官方提醒傳播可能要幾分鐘。

Tenancy 可以另外訂閱其他區域（region subscription），訂閱之後能在那一區建資源，而帳號與身分資源仍然住在 home region。訂閱改變的是資源能放在哪裡，不改變 home region。訂閱的數量有上限：官方〈Regions and Availability Domains〉寫明試用、Free Tier 與 Pay As You Go 的 tenancy 都只能有一個訂閱區域，也就是 home region 本身；升級成付費帳戶（Pay As You Go）之後可以申請提高這個上限；試用與 Free Tier 的 tenancy 不能申請，訂閱區域就只有 home region 一個。

**Compartment** 是 tenancy 底下用來分組資源與套用政策的容器。Tenancy 本身就是最上層的 root compartment，新帳號一開始只有它。實驗用的資源另開一個 compartment 放，清理時刪那一個 compartment 底下的資源就好，不會碰到 root 裡的其他設定。

**Availability domain**（AD）是一個區域裡彼此隔離的資料中心，跨業者的概念見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/)。區域之間的 AD 數量不同：有些區域有三個，有些只有一個。申請之前，各區域的 AD 數列在官方〈Regions and Availability Domains〉頁的區域表；申請之後，`oci iam availability-domain list`（登入方式見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)）回傳的清單長度就是自己 home region 的 AD 數。AD 數會影響免費機型建不起來時的退路，見〈A1 容量不足時的退路〉。

## Always Free 的額度與它綁在 home region 上的範圍

OCI 的免費方案有兩個部分。試用金是 300 美元、30 天內有效，可以用在大部分付費服務上；Always Free 是沒有期限的固定額度，試用結束之後仍然繼續。官方 Free Tier 頁的原文是「After your trial ends, your account remains active. There is no interruption to the availability of the Always Free Resources you have provisioned.」沒有升級成付費帳戶的帳號，試用結束後不會開始扣款；試用期間用試用金建的付費資源，在試用結束時被回收，A1 主機另有一條依合計規格停用的規則，見下方〈試用結束時超出額度〉那一項。試用中、試用結束而沒有升級、付費帳戶這三種狀態下超出額度各自的結果，整理在〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉。

運算的 Always Free 額度有兩種機型：

- **Ampere A1（`VM.Standard.A1.Flex`，ARM）**：每月 1,500 OCPU 小時與 9,000 GB 小時的記憶體，相當於 2 OCPU、12 GB 記憶體整個月開著。可以全部給一台，也可以拆成兩台各 1 OCPU。OCI 的 OCPU 是一顆實體核心，跟其他業者以 vCPU 計價時的單位不同，比較時見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。
- **AMD Micro（`VM.Standard.E2.1.Micro`，x86）**：最多兩台，每台 1/8 OCPU、1 GB 記憶體。

儲存與網路另有額度：開機磁碟與區塊磁碟合計 200 GB（每台主機的開機磁碟預設 50 GB，這 50 GB 從同一份 200 GB 額度裡扣）、備份最多 5 份、出站流量每月 10 TB；試用結束後沒有升級的 Free Tier tenancy，VCN 最多 2 個。

**運算與區塊磁碟的 Always Free 額度只能用在 home region。** Free Tier 頁寫的是「You can provision Always Free Autonomous AI Databases and compute instances only in the home region」；Always Free Resources 頁對區塊磁碟的原文是「the volume must be created in the home region of the tenancy」。升級成付費帳戶並訂閱其他區域之後，建在 home region 以外那些訂閱區域的主機照一般價格計費。

免費主機只能建在 home region，主機的實體位置因此就是 home region。這個位置決定兩件事。一是出口 IP 的國家：業者配給一台主機的公開 IP 位址，屬於那個區域所在國家的位址段，主機對外連線時，對方看到的來源 IP 就登記在那個國家。二是延遲：從使用者所在地連到主機的延遲，由兩地的距離決定。

Always Free 的主機另有兩條回收規則：

- **閒置回收**：連續 7 天內 CPU 使用率（第 95 百分位）、網路使用率、記憶體使用率（只算 A1）三項指標各自都低於 20%，Oracle 可能回收這台主機。官方頁用的詞是 reclaim，沒有寫回收之後主機是停止還是刪除。只在需要時才登入的實驗機會符合這個條件。
- **試用結束時超出額度**：Free Tier 頁判斷 A1 是否超額，看的是 tenancy 裡全部 A1 主機的合計（OCPU 加總、記憶體加總），不看單台主機的規格。合計超過 2 OCPU、12 GB 時，試用結束那一刻 tenancy 裡的 A1 主機全部被停用，30 天後刪除，除非升級成付費帳戶。被停用的是每一台 A1 主機，包括單台規格在額度內的那幾台。官方沒有寫已經被停用的主機在升級之後會不會恢復。試用期間超出的部分由試用金支付，帳單上看不到費用，所以 A1 合計超額的後果要到試用結束那一刻才浮現。這個合計要自己加總：到 Compute → Instances 清單逐台記下 A1 主機的 OCPU 與記憶體；清單一次只列一個 compartment，每個放過主機的 compartment 都要切過去看。要保留 A1 主機，試用結束前把合計壓回 2 OCPU、12 GB 以內：把其中幾台的 OCPU 或記憶體改小，或刪掉其中一台。

官方對閒置回收只寫了三項指標都要低於 20%，沒有寫網路使用率的 20% 是對什麼的比例，也沒有寫升級成付費帳戶之後這條規則還適不適用；被回收之後主機的狀態與能不能恢復同樣沒寫。

## A1 容量不足時的退路

A1 免費機型在某個 AD 暫時沒有容量時，建立主機的 API 回 `Out of host capacity`。可以做的事有下面這些，出處分別是官方 Always Free 頁與 Compute 的〈Known Issues〉頁；標明「會計費」的幾項不在 Always Free 額度內，結果依帳號狀態而定，見〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉：

- **換一個 AD**（Always Free 頁）：home region 只有一個 AD 時，這一項不存在。
- **等一段時間再試**（Always Free 頁）：有人釋出資源時才會短暫空出位置。重送的間隔看回應碼調整：`429 TooManyRequests` 是請求太頻繁被限流（[Rate Limit](/backend/knowledge-cards/rate-limit/) 卡），收到就拉長間隔，做法見 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/) 卡；`Out of host capacity` 才是那個 AD 當下沒有硬體。限流的門檻依帳號與 API 而定。
- **不指定 fault domain**（Known Issues 頁）：建立頁的 Fault domain 欄選「Let Oracle choose the best fault domain」，不把主機限定在單一個 fault domain 的硬體上。
- **改小規格**（Known Issues 頁）：同一個機型把 OCPU 或記憶體改小，需要的硬體少，容量比較容易拿到，仍然在免費額度內。
- **建立前查容量**（Known Issues 頁）：用 `CreateComputeCapacityReport` 這個 API 查某個機型當下在某個 AD 有沒有容量，查完再送建立請求。
- **換成 x86 機型**（會計費）：x86 的 Flex 機型不在免費額度內；試用期間用試用金建，當天就有主機可用，代價是這台用試用金建的 x86 主機在試用結束時會被回收。換架構要重新確認軟體有沒有那個架構的版本，見 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/) 的〈CPU 架構：x86 與 ARM〉。免費的 x86 機型 E2.1.Micro 在一個區域裡只建得在一個 AD 上，2026-10-24 實測的 `ap-batam-1` 沒有這種機型，出處與實測見〈E2.1.Micro 在各區域的供應：服務配額表與 404 錯誤〉。
- **改用可被收回的容量（preemptible）**（官方沒有寫它算不算免費額度，這裡按會計費看待）：官方 Always Free 頁與 Free Tier 頁都沒有提到 preemptible。業者需要容量時會直接終止這種主機，價格與限制見 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/) 的〈計費模式：隨用隨付、可被收回、預留容量與專屬主機〉。
- **預留容量（capacity reservation）**（會計費）：先向業者保留某種機型的容量，保留期間的計費方式見 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/) 的〈計費模式：隨用隨付、可被收回、預留容量與專屬主機〉。
- **升級成付費帳戶**（Always Free 頁）：官方寫升級之後能用的運算資源種類變多（原文「gives you access to more types of Compute resources」）。對容量不足來說，升級的作用是讓上面那幾項會計費的選項（x86 的 Flex 機型、可被收回的容量、預留容量）在試用金用完或試用結束之後仍然建得起來。Always Free 的部分仍然不收費，額度以外建的資源照一般價格計費。

Home region 只有一個 AD、而且只用免費額度時，能用的退路是等待重試、不指定 fault domain、改小規格與建立前查容量這四項；換 AD 在這種區域不存在；x86 的 Flex 機型、可被收回的容量與預留容量不在免費額度內，要用試用金或升級成付費帳戶才建得起來。在只有一個 AD 的 `ap-batam-1` 實際重送的紀錄、OCI CLI 在一條指令裡自己重送造成的限流，以及依回應碼調整間隔的重送腳本，見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 的〈重送建立請求：CLI 自己的重送、限流門檻與重送腳本〉。

## E2.1.Micro 在各區域的供應：服務配額表與 404 錯誤

E2.1.Micro 是 Always Free 的另一種機型。官方 Always Free 頁對它的供應寫的是 AD 層級：「Instances using the VM.Standard.E2.1.Micro shape can only be created in one availability domain.」也就是一個區域裡只有一個 AD 建得了 Micro，而官方沒有列出是哪一個 AD、哪些區域完全沒有。2026-10-24 在 `ap-batam-1` 實測，這一區唯一的 AD 沒有 E2.1.Micro，所以在這一區，A1 建不起來時改用 Micro 也建不起來。

主控台的服務配額表（Limits, quotas and usage 頁）上的數字是這個帳號允許開的台數上限，它不反映那一區是否提供那種硬體。這次的帳號在配額表上的 `vm-standard-e2-1-micro-count` 是 2，而 `ap-batam-1` 一台 Micro 也建不起來。

在沒有這個機型的區域用 CLI 建立 Micro 主機，API 回的是 `404 NotAuthorizedOrNotFound`。這個錯誤碼同時涵蓋權限不足與資源不存在，從訊息本身分不出是哪一種。一個區域實際提供哪些機型，用 `oci compute shape list --compartment-id <compartment 的 OCID> --availability-domain <AD 名稱>` 查，回傳的清單才是那個 AD 能建的機型；AD 名稱要填 `oci iam availability-domain list` 回傳的完整名稱，它帶有 tenancy 專屬的前綴，只寫 `AD-1` 會失敗。這條指令要先有 tenancy 才能跑，所以申請之前沒有辦法確認某一區有沒有 E2.1.Micro；申請之後才發現缺機型時，能做的事見〈選錯 home region 之後的選項〉。

## 超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果

多建一台 A1、加大一顆磁碟、改用不在免費額度內的 x86 機型，這類讓用量超出 Always Free 額度的操作，結果由帳號當下的狀態決定：

- **試用中**：超出的部分由試用金支付，帳單上看不到費用。試用結束時，用試用金建的付費資源會被回收，A1 合計超額時全部 A1 主機會被停用。
- **試用結束而沒有升級**：官方 Always Free 頁寫明，用不在 Always Free 範圍內的映像建主機，帳號必須是付費帳戶、或是還有試用金餘額的 Free Trial 帳號（原文「you must have a paid account or a Free Trial account with available credits」）；試用結束而沒有升級的帳號兩者都不是，所以超出額度的運算資源建不了，運算以外的資源這一頁沒有逐字寫；Free Tier 頁另外寫明，不升級的話申請時填的信用卡不會被扣款。
- **升級成付費帳戶（Pay As You Go）**：Always Free 的部分仍然不收費，超出的部分照一般價格計費。

站內各篇寫到「超出免費額度」的地方，指的都是這三種結果。升級之前先設好預算警示，見 [雲端主控台的管理領域](/infra/cloud-providers/console-areas/) 的〈帳單與成本：花了多少、會花多少〉。

## 選 home region 時要先確認的事

Home region 在申請表上是一個下拉選單，選定的區域同時決定了免費主機的實體位置（出口 IP 的國家、延遲）與容量不足時有沒有別的 AD 可以換。選之前先確認這台免費主機要做什麼：

- **用途需要特定國家的出口 IP**（例如要讓連線看起來從日本發出）：只有那個國家的區域符合，其他區域的延遲再低都達不到目的。以日本為例，這個條件與下方「主要拿來實驗」那一條的「選 AD 多的區域」同時滿足不了：日本的兩個區域（東京 `ap-tokyo-1`、大阪 `ap-osaka-1`）都只有一個 AD，選了日本，A1 容量不足時就沒有別的 AD 可以換，而 E2.1.Micro 有沒有提供要申請之後才查得到。兩者只能取一個：日本的出口 IP 是硬條件時，選日本的區域，接受 A1 容量不足時無處可換；出口 IP 只是加分項時，選 AD 多的區域，放棄日本的出口 IP。東京與大阪之間，官方沒有公開各區的容量資訊，選哪一個只能看延遲。預算為零而容量一直不足時，能用的退路見〈A1 容量不足時的退路〉最後一段。
- **用途是給特定地區的使用者連**：選離使用者近的區域，延遲由距離決定。
- **主要拿來實驗**：優先選 AD 多的區域（官方區域表上 AD 數為 3 的那幾個，名單見 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/) 卡），A1 容量不足時有其他 AD 可以換。AD 多代表的是多了可以換的地方，不代表那一區的 A1 空閒容量比較多。
- **資料要留在特定國家**（法規或合約要求）：只有那個國家的區域符合，跟出口 IP 那一條同樣是硬條件。

## 選錯 home region 之後的選項

Home region 不能改；官方有刪除 tenancy 的流程（〈[Deleting a Free Tier Tenancy and Cloud Account](https://docs.oracle.com/en-us/iaas/Content/General/Tasks/deleting_tenancy_freetier.htm)〉：管理員在 Tenancy Details 頁按「Request tenancy deletion」），刪除後資源先被暫停、30 天後永久刪除且無法復原，而官方文件沒有寫明刪除之後能不能用同一個 email 與付款方式重新申請。走這條路之前，先開 support ticket 問清楚重新申請的條件。不刪 tenancy 的做法是保留原帳號、在想要的區域另建付費主機：管理員先把帳號升級成 Pay As You Go，再到 Limits, quotas and usage 頁申請提高訂閱區域的上限（Subscribed region count）；核准之後訂閱想要的區域，在那一區建的主機照一般價格計費。Always Free 額度仍然只能用在原本的 home region。

## 主控台登入：租用戶與使用者名稱兩個欄位，與「使用者名稱或密碼無效」

OCI 的登入頁把登入拆成兩個欄位，依序出現：

1. **租用戶（Cloud Account Name）**：填 tenancy 的名稱，也就是申請時取的帳戶名稱。OCI 用它找到要登入的是哪一個 tenancy。已經登入的主控台上，右上角人像選單的「租用戶」或「Tenancy:」後面就是這個值。
2. **使用者名稱**：填 tenancy 裡那個使用者的名稱。申請時建立的管理員帳號，使用者名稱是申請用的 email。頁面要求選 identity domain（tenancy 裡存放使用者與群組的分區）時選 `Default`，新帳號只有這一個。

兩個欄位任一個填錯，登入頁顯示的都是同一句「使用者名稱或密碼無效」，不會指出是哪一欄錯。實際登入時，租用戶欄填對、使用者名稱欄填成 tenancy 名稱，得到的就是這句訊息，密碼本身沒有錯。從本機用 `oci session authenticate` 登入時開出的瀏覽器頁面是同一個登入頁，欄位與錯誤訊息相同。

## 延伸閱讀：CLI 登入、免費額度比較、位置與管理通道

同一個 tenancy 從終端機登入的做法，以及 session token 與 API 簽章金鑰各自的時效，見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)；Always Free 的 home region 限制跟 Google Cloud、AWS 的區域限制並排，見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)；home region 這一層之下，可用區與故障域在建立主機時各決定什麼，見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)；compartment 這種資源分組在三家主控台上的對應，見 [雲端主控台的管理領域](/infra/cloud-providers/console-areas/)；主機建好之後，管理員登入它要經過的網路可達性、通道授權與主機登入驗證三層，見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。
