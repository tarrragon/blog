---
title: "GCP 上的雲端費用失控防護：預算警示、強制執行支出上限與自動停用帳單的作用範圍、反應時間、建置與驗收"
date: 2026-10-24
description: "GCP 上為費用失控設防的機制：預算警示寄出通知的時機、範圍、抵免與通知對象、強制執行支出上限涵蓋的服務與暫停期間，以預算通知觸發函式停止用量的兩種處置（解除帳單連結、只停止花錢的資源）、建置步驟、權限與重試設定，帳單資料延遲對這些機制反應時間的影響，以及這個函式上線前後的驗收與停用後的恢復"
weight: 3
aliases: ["/operations/08-cost-management/spend-protection-gcp-budget-killswitch/"]
tags: ["devops", "cost-management", "gcp", "budget", "kill-switch", "security"]
---

這篇整理在 GCP 上為費用失控設防的做法，範圍從專案已經連結到一個帳單帳戶開始。[開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)的〈Per-team 成本上限〉說明了為什麼要給團隊與環境設一個費用的上限；這一篇處理那個上限在 GCP 上由哪些機制執行、每一個機制在費用超過門檻時實際做了什麼，以及從費用發生到它動作之間隔了多久。三個機制分別是預算警示（花費達門檻時寄通知）、強制執行支出上限（暫停指定服務的新用量），以及由預算通知觸發的處置（由程式把專案從帳單帳戶解除連結，或只停止花錢的資源）。

文中的觀察來自 2026 年 10 月在一個 GCP 測試專案上的實跑，分兩次：第一次建出停損開關並觸發一次，第二次驗預算的範圍與抵免、通知管道、只停止花錢的資源、管理專案、分段驗證、心跳監看與恢復。標「未實跑」的做法沒有在這兩次實跑中執行；引用 Cloud Billing 文件或 `gcloud` 說明的行為，出處寫在句子裡。主控台的選項與服務清單會變動，以操作當下看到的為準。

## 費用失控的來源與反應時間

費用失控指的是費用增加的速度快過人發現它、處理它的速度。來源分成兩類，兩類的處置方式不同：

- **服務自己出錯**：程式對失敗的請求無限重試、一個事件觸發的函式又產生同一種事件而形成遞迴、自動擴縮允許的最大執行個體數設得太高。費用花在自己的服務上，修好程式之後費用就停止增加。
- **資源被別人濫用**：外洩的 API 金鑰（API key）被拿去呼叫付費 API、被入侵的 VM 被拿去挖礦。費用花在攻擊者的用途上，處理的人要先切斷攻擊者能用的資源，再處理入侵。

兩類的共同難處在時間：費用從發生到任何機制動作，中間隔著一段延遲。一個防護機制從費用發生到動作，要經過三段：雲端把用量算成費用、寫進帳單資料；帳單資料觸發通知；通知觸發處置（人或程式）。把用量算成費用那一段的延遲由雲端決定，GCP 的帳單主控台寫著費用資料要數小時後才會顯示、有時超過 24 小時。實測時一個專案已經跑了幾個小時的 VM 與 GKE 叢集，那段期間送到的預算通知裡 `costAmount`（本期累計花費）仍是 `0.0`；那個預算用預設的抵免設定，所以這次分不出 `0.0` 來自延遲還是抵免。

預算警示與由預算通知觸發的處置讀的是帳單資料，反應時間至少是這段延遲。強制執行支出上限依的是 GCP 估算的費用，Cloud Billing 文件說這份估算比帳單報表上的費用快得多，但仍不是即時，延遲期間超出上限的部分照常計費。這三個機制的費用最後停在哪裡也不同：

- **強制執行支出上限與解除帳單連結**：費用停止增加，總額是觸發的金額再加上延遲期間已經發生的費用。
- **只停止花錢的資源**：被停掉的資源不再計費，磁碟與儲存照常計費。
- **預算警示**：不停止任何用量，費用停在哪裡取決於收到通知的人多快處理。

要在費用發生的當下限制它，得靠不經過帳單資料的限制，它們也決定了延遲期間最多能多花多少：

- **能用多少**：API 的配額、[速率限制（rate limit）](/backend/knowledge-cards/rate-limit/)、服務允許的最大執行個體數（例如 Cloud Run 的 `--max-instances`、MIG 的最大台數），以及 Compute Engine 的區域 CPU 與 GPU 配額。配額調到實際用量附近，被入侵的帳號能開的 VM 台數就有上限。
- **能建什麼**：組織政策（Organization Policy，GCP 繁體中文介面寫作「機構政策」）可以限制專案能啟用的 API，搭配 Compute Engine 的自訂限制條件可以限制能用的機型，前提是專案屬於一個組織（未實跑：測試帳號底下沒有組織）。
- **金鑰能做什麼**：API 金鑰的使用範圍限定可呼叫的 API 與來源；實測 `gcloud services api-keys create` 不給 `--api-target` 時被拒，新建的金鑰一定帶 API 範圍。金鑰被盜用時，先撤銷或限制那一把金鑰，影響範圍比停用整個專案的帳單小。

## 預算警示：門檻依據、範圍、抵免、建立指令與通知對象

預算（budget）是掛在帳單帳戶上的一組門檻：本期花費達到預算的某個比例時，GCP 寄通知給帳單帳戶的管理員。門檻有兩種依據，**實際花費**（已經寫進帳單資料的費用）與**預測花費**（GCP 依目前的速度推估到期末的費用）；預測花費的門檻通常比實際花費的門檻早觸發，代價是一次短暫的尖峰也可能觸發預測花費的門檻。預算只寄通知，扣款照常進行。

建立預算的人要通過兩道權限檢查。實測沒有任何角色的帳號先被 `--billing-project` 那個專案擋下（缺 `serviceusage.services.use`，訊息寫 `USER_PROJECT_DENIED`）；補上 `roles/serviceusage.serviceUsageConsumer` 約一分鐘後，才換成帳單帳戶的權限不足。所以建立預算的人要有那個專案的 `serviceusage.services.use`，以及帳單帳戶上能管理預算的角色（帳單帳戶管理員或帳單帳戶費用管理員）。下面的指令把範圍限定在一個專案，門檻設在實際花費的 50%、90%、100%，另加一個預測花費達 100% 的門檻：

```bash
# 查帳單帳戶的 ID 與幣別：預算金額用的是這個幣別
gcloud billing accounts list
gcloud billing accounts describe <billing-account-id> --format="value(currencyCode)"

# gcloud 透過 --billing-project 指定的專案呼叫預算 API，那個專案要先啟用這個 API
gcloud services enable billingbudgets.googleapis.com --project=<project-id>

# 建立預算：金額寫成「數字加幣別代碼」，幣別要與帳單帳戶相同
gcloud billing budgets create --billing-account=<billing-account-id> \
  --display-name=<budget-display-name> --budget-amount=<amount><currency-code> \
  --filter-projects=projects/<project-id> \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
  --threshold-rule=percent=1.0,basis=forecasted-spend \
  --billing-project=<project-id>
```

- `<billing-account-id>`：`gcloud billing accounts list` 的第一欄，是三段各六個英數字、以 `-` 分隔的字串，例如 `000000-AAAAAA-111111`（這是佔位值）。
- `<budget-display-name>`：自己取的名稱，只用來在主控台與通知裡辨識這個預算。
- `<amount><currency-code>`：例如帳單帳戶的幣別是新台幣時寫成 `320TWD`。主控台建立預算的表單只顯示一個 `$`，不顯示幣別；幣別是新台幣的帳戶在那裡填 `10`，門檻是新台幣 10 元而不是 10 美元。
- `--filter-projects`：預算只計算這些專案的花費。`gcloud` 說明寫著不給這個旗標時涵蓋所有專案，通知裡的 `costAmount` 就是帳單帳戶下所有專案的合計：別的專案的花費也會讓它越過門檻，而這個專案自己的超支被合計稀釋。`gcloud billing budgets describe` 的 `budgetFilter.projects` 存的是專案編號，不是專案 ID。
- 門檻比例：50% 與 90% 留給收到通知的人處理的時間，100% 對齊花費達到預算的那一刻，預測花費的門檻提早反映速度異常；比例依處理一次所需的時間自己調整。
- `--billing-project`：gcloud 呼叫預算 API 所用的專案，不影響預算的範圍。

**抵免**：`gcloud` 說明寫著預設把帳戶上的抵免扣掉之後才算花費。帳戶上有大額抵免（新創方案、試用額度）時，`costAmount` 在抵免用完之前都接近 0，門檻在抵免被燒光的整段期間都不會觸發。抵免本身也是要保護的錢時，建立預算時加 `--credit-types-treatment=exclude-all-credits`，花費以抵免前的金額計算；實測同一段期間，扣掉抵免的帳戶層級預算報 `costAmount` 0.05，`exclude-all-credits` 的預算報 0.37。只想讓部分抵免照常扣掉（例如免費方案的用量）時，改用 `--credit-types-treatment=include-specified-credits` 搭配 `--filter-credit-types=<要扣掉的抵免類型>`，例如 `FREE_TIER`；`--help` 不列出可用的類型，寫錯時回 `INVALID_ARGUMENT: ... is not a valid credit type string`，類型名稱以 Cloud Billing 文件為準。`FREE_TIER` 是預算接受的抵免類型，由此推得 `exclude-all-credits` 也會把免費方案的用量以原價算進花費，只用免費方案的專案加了這個旗標，門檻可能被免費的用量觸發。

**通知對象**：通知預設寄給帳單帳戶的管理員與帳單使用者，建立預算時先確認這兩個角色的成員信箱有人在看。值班的人通常不在這兩個角色裡，要讓他們收到，建立預算時加 `--notifications-rule-monitoring-notification-channels=<channel-resource-name>`，把通知另外寄到 Cloud Monitoring 的電子郵件通知管道（Cloud Billing 文件寫明預算只支援電子郵件類型的管道）；`<channel-resource-name>` 是通知管道的完整名稱，形如 `projects/<project-id>/notificationChannels/<channel-id>`，在主控台的 Monitoring 通知管道頁面，或 `gcloud beta monitoring channels list`（要安裝 beta 元件，未實跑）列得出來。實測把 webhook 類型的管道接上預算時，只回 `INVALID_ARGUMENT: Request contains an invalid argument`，訊息不會說出原因是管道類型。要送到簡訊、聊天工具或 webhook，改由 Pub/Sub 主題接一段轉送程式。

預算另外可以把通知送到一個 Pub/Sub 主題（topic），由預算通知觸發的處置就是從這個主題接收通知。

預算警示的寄送沒有辦法立即合成觸發，第一封真實的門檻通知寄到之前，「通知送得到收的人」這一段沒有驗證過；寄到時確認收到的是誰、多久後有人看到。

## 強制執行支出上限：涵蓋的服務、範圍與暫停期間

在帳單主控台的「Budgets & caps」頁面（2026 年 10 月主控台顯示的名稱）建立預算時，表單裡有一個「強制執行支出上限（適用於某些服務）」的選項：花費達到上限時，GCP 暫停表單裡選定的那個專案、那一項服務的新用量，直到這個預算期間結束（以月為期的預算是到月底，下一期自動重設）或有人手動解除為止。它是帳單功能裡不必自己寫程式就能暫停用量的機制，範圍有四個限制：

- **一個上限只涵蓋一個專案裡的一項服務**：要保護多項服務，就每項各建一個。
- **只涵蓋清單上的服務**：2026 年 10 月建立表單時列出的是 Cloud Run、Cloud Run functions、Gemini API 與 Vertex AI 四項，Compute Engine 與 GKE 不在清單上。表單的服務下拉選單就是涵蓋清單，建立之前打開看一次。
- **持續性資源的固定費用不暫停**：Cloud Billing 文件說明，與持續性資源綁在一起的固定用量不會被暫停，執行也有延遲，超出的部分照常計費。
- **以抵免前的金額計算**：Cloud Billing 文件寫明上限的花費不扣抵免與折扣，與預算的預設抵免設定相反。帳戶有抵免、而上限與預算的金額相近時，上限會先達到。

工作負載跑在清單上的服務時，這個選項不必寫程式；它暫停的是這項服務的新用量，所以對正式服務同樣是一次停機，只是範圍限於這一項服務。是否建立，依〈由預算通知觸發的處置〉那一節比較兩種損失來判斷。一個專案同時有清單上的服務與不在清單上的服務時，兩種做法可以並用：清單上的服務各建一個支出上限，在估算費用達到上限時先暫停那一項服務；不在清單上的資源由只停止花錢的資源那一種處置接手。改用解除帳單連結的話，停掉的是整個專案，清單上的服務也一起停。

## 由預算通知觸發的處置：解除帳單連結與只停止花錢的資源

這一節的做法是讓預算通知觸發一段程式，由程式在花費達到預算時停止用量。停止用量有兩種做法，差別在停掉的範圍：

- **解除帳單連結**：程式呼叫 Cloud Billing API 把專案從帳單帳戶解除連結。專案沒有連結帳單帳戶時，GCP 停止專案裡所有的服務（包括免費方案的服務），費用也就停止增加。這段程式在下文稱為**停損開關**（kill switch）。
- **只停止花錢的資源**：程式改成停止專案裡執行中的 VM、把 MIG 的目標台數設成 0、把 GKE node pool 縮到 0 個節點。Cloud Billing 文件的〈Control resource usage with notifications〉就是這種做法，範例是逐台停止一個 zone 裡執行中的 VM。實測改用 `instances().aggregatedList` 跨全部 zone 列出 `RUNNING` 的 VM 再逐台 `stop`，服務帳號只給 `roles/compute.instanceAdmin.v1`：訊息發出後函式立刻送出停止，VM 約兩分鐘後變成 `TERMINATED`，帳單仍是啟用、開機磁碟仍在。資料留在磁碟與儲存裡、那部分照常計費，所以費用不會歸零；代價是程式只停它列得出來的資源，漏掉一種資源型別，或攻擊者另外開的新資源，那部分照常計費。

```text
預算（帳單帳戶）── 通知 ──> Pub/Sub 主題 ── 推送 ──> Eventarc 觸發器 ── 呼叫 ──> Cloud Run functions 函式 ──> 解除帳單連結，或停止花錢的資源
```

兩種做法的預算、主題、觸發器與重試設定相同，差別在函式本體、服務帳號的角色與驗收的終點。下文以停損開關為例；改成只停止花錢的資源時，函式改成呼叫 Compute Engine 與 GKE 的 API，服務帳號改給能修改那些資源的角色（VM 與 MIG 例如 `roles/compute.instanceAdmin.v1`，GKE node pool 的縮放要 container 的權限，以 `gcloud iam roles describe` 確認），驗收的終點改成超出預算的訊息之後 `gcloud compute instances list` 的狀態變成 `TERMINATED`、MIG 的目標台數與 node pool 的節點數變成 0，每一個 zone 與資源型別各確認一次（MIG 與 node pool 的部分未實跑）。〈上線前後的驗收〉的帳單狀態查詢與權限檢查，以及〈解除連結之後恢復服務〉，只適用停損開關。

建置之前先決定要不要建、建哪一種，因為停損開關的效果是一次自己造成的全面停機：VM、資料庫、函式、Kubernetes 叢集一起停擺，停損開關本身跑在同一個專案時也會停（實測解除連結之後，查詢函式狀態的 API 直接回 403，訊息要求確認帳單帳戶；函式本身在停用後約一分鐘內仍處理了下一則通知，之後的行為這次沒有觀察）。Cloud Billing 文件另外警告，停用帳單時資源可能被永久刪除，也不保證服務能恢復，所以這是一次可能遺失資料的停機。判斷方式是比較兩種損失：「被濫用或程式出錯而多付一筆費用」與「這個專案的服務停止、資料可能遺失」，哪一種比較大。

判斷的單位是專案，因為停損開關停的是整個專案。混合了正式服務與沙箱的專案照正式服務判斷；想對沙箱建停損開關，就先把沙箱搬到自己的專案。逐個專案套下面三條：

- **停機時沒有人受影響、而且專案裡的資料都能從別處重建**（只跑實驗的專案、個人的沙箱多半是這樣）：多付的費用沒有上限，建停損開關。
- **停機可以接受、而資料不能遺失**（團隊共用的 staging、有持久資料的實驗專案）：建只停止花錢的資源的那一種。
- **停機會影響使用者或同事**（正式服務）：全面停機的代價通常高於一段時間的超支，改用預算警示，寄到值班的人手上（見〈預算警示〉的通知對象），並把〈費用失控的來源與反應時間〉列的即時限制設上，讓帳單資料延遲期間的花費有上限。沒有人能值班時，處理時間就是自己下一次看到通知的時間，配額要依這段時間能承受的花費來設。風險集中的功能可以拆出去，例如 API 金鑰寫在網頁或 App 裡、任何人都拿得到那把金鑰的功能：拆到自己的專案再對那個專案建停損開關。停損開關停掉那個專案時，正式服務裡用這把金鑰的功能也會一起停，正式服務的其餘部分與正式服務的資料要放在另一個專案。

專案裡跑的工作負載可能被入侵時，攻擊者拿到的身分若有專案的編輯權限，也能刪掉同一個專案裡的函式與主題。這時停損開關要放在另一個專案，見〈停損開關放在另一個專案〉。

實測停用約兩分半鐘再重新連結，Cloud Router、Cloud NAT、函式與它的觸發器都還在、設定沒變；這次沒有觀察 VM 與資料庫。停用期間 `gcloud compute routers list` 回傳零筆，而重新連結之後 Cloud Router 仍在，所以停用期間的空清單不代表資源已經刪除；重新連結之後仍存在的資源會繼續計費，清理時以重新連結之後列出的清單為準。

## 停損開關的建置：主題、服務帳號的角色、函式與觸發器的呼叫權限

停損開關的建置有四個元件：接收通知的 [Pub/Sub](/backend/knowledge-cards/pub-sub/) 主題、執行函式的[服務帳號](/infra/knowledge-cards/service-account/)、函式本身，以及觸發器呼叫函式的權限。服務帳號的角色、函式的重試設定與觸發器的呼叫權限，任何一項設錯，部署指令都回報成功、函式狀態也都顯示 `ACTIVE`，停損開關卻不會解除帳單連結。

下面的指令用到三個本文取的名稱：主題 `budget-alerts`、服務帳號 `budget-killswitch-sa`、函式 `budget-killswitch`。換成別的名稱時，同一個名稱出現的每一條指令都要一起換。`<project-id>` 指的是放停損開關、同時也是要被停用帳單的那個專案；兩者分開的情形見〈停損開關放在另一個專案〉。

接停損開關的預算要另外建，不接到既有的帳戶層級警示預算上：

- **範圍**：用 `--filter-projects` 限定在要停用的那一個專案。
- **金額**：函式在本期累計花費達到預算金額時解除連結，而停下來時的總額還要加上帳單資料延遲期間多出的費用。所以預算金額設成這個專案本期能承受的最高花費減掉那筆延遲費用。延遲費用的上限約是「每小時最多能花的費用 × 延遲的時數」，每小時最多能花多少由〈費用失控的來源與反應時間〉列的配額決定，所以先把配額壓到實際需要的量，才估得出這個上限。
- **一個主題只接一個預算**：本文的函式不分辨通知來自哪一個預算，好幾個預算送到同一個主題時，任何一個超支都會讓它停掉 `TARGET_PROJECT_ID`。要依預期花費收通知，另建一個不接主題的預算。

### 接收通知的主題

主題是預算通知與函式之間的接點：預算把通知發布到主題，Eventarc 觸發器從主題取出通知、呼叫函式。

```bash
gcloud services enable pubsub.googleapis.com cloudfunctions.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com eventarc.googleapis.com \
  cloudbilling.googleapis.com --project=<project-id>

# 建立主題，並讓接停損開關的預算把通知送過來
gcloud pubsub topics create budget-alerts --project=<project-id>
gcloud billing budgets update <budget-resource-name> \
  --notifications-rule-pubsub-topic=projects/<project-id>/topics/budget-alerts \
  --billing-project=<project-id>
```

`<budget-resource-name>` 是 `gcloud billing budgets list --billing-account=<billing-account-id> --billing-project=<project-id> --format="value(name)"` 印出的完整名稱，形如 `billingAccounts/<id>/budgets/<uuid>`，與建立時給的顯示名稱是兩個值。主題原本接在別的預算上時，要從那個預算拿掉：`gcloud billing budgets update` 沒有清除 Pub/Sub 通知的旗標，實測改用預算 API 以 `updateMask=notificationsRule.pubsubTopic` PATCH 成空字串。設定通知目標時，GCP 會自動讓預算服務的系統帳號 `billing-budget-alert@system.gserviceaccount.com` 擁有這個主題的發布權限，`gcloud pubsub topics get-iam-policy budget-alerts --project=<project-id>` 看得到這條綁定。

預算接上主題之後，GCP 一天會送好幾次通知過來，不論花費有沒有越過門檻。實測接上後約十三分鐘收到第一則；Cloud Billing 文件說第一則可能要數小時。通知的內容如下，`alertThresholdExceeded` 這類欄位要等越過門檻才會出現：

```json
{"budgetDisplayName": "<budget-display-name>", "costAmount": 0.0, "costIntervalStart": "2026-10-01T07:00:00Z",
 "budgetAmount": 320.0, "budgetAmountType": "SPECIFIED_AMOUNT", "currencyCode": "TWD"}
```

### 服務帳號的角色

函式以這個服務帳號的身分讀取與修改專案的帳單連結，所以它需要的角色決定了函式在解除連結的那一刻會不會被拒絕。

```bash
gcloud iam service-accounts create budget-killswitch-sa --project=<project-id>

# 解除專案的帳單連結
gcloud projects add-iam-policy-binding <project-id> \
  --member=serviceAccount:budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --role=roles/billing.projectManager

# 讀取專案的帳單狀態（getBillingInfo 需要 resourcemanager.projects.get）
gcloud projects add-iam-policy-binding <project-id> \
  --member=serviceAccount:budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --role=roles/browser
```

`roles/billing.projectManager` 只包含兩個權限，建立與刪除專案的帳單連結（`gcloud iam roles describe roles/billing.projectManager` 列得出來），讀取帳單狀態不在裡面。〈判斷並解除帳單連結的函式〉的程式在解除連結之前先讀一次帳單狀態，只給這個角色時，那一步回 403「The caller does not have permission」。`roles/browser` 包含 `resourcemanager.projects.get`，整個角色是讀取專案、資料夾與組織的中繼資料以及專案 IAM policy 的六個權限，不包含讀取專案內資源（VM、儲存、資料庫）的權限。

這兩個角色都綁在專案層級。函式只停用 `TARGET_PROJECT_ID` 這一個專案，所以要管多個專案時，每個專案各建一個限定在該專案的預算、一個主題與一個函式部署，角色在每個專案各綁一次。

上面兩個角色決定這個服務帳號能做什麼。另一邊是誰能以它的身分行事：執行部署指令的人要有這個服務帳號的 `roles/iam.serviceAccountUser`，才能把它指定給函式與觸發器；專案擁有者本來就有，其他角色的部署者要另外授予。

### 判斷並解除帳單連結的函式

函式收到通知、判斷是否解除連結、解除之前確認帳單還在啟用。下面的程式存成 `<source-dir>/main.py`，判斷規則只看實際花費：

```python
import base64
import json
import os

import functions_framework
from googleapiclient import discovery

PROJECT_ID = os.environ["TARGET_PROJECT_ID"]
PROJECT_NAME = f"projects/{PROJECT_ID}"

def should_disable(notification: dict) -> bool:
    # 只看實際花費：改看預測花費時，一次短暫的尖峰就可能讓函式停掉正常的服務
    try:
        cost = float(notification["costAmount"])
        budget = float(notification["budgetAmount"])
    except (KeyError, TypeError, ValueError):
        print(json.dumps({"warning": "unreadable notification, ignored"}))
        return False
    return budget > 0 and cost >= budget

def billing_enabled(billing) -> bool:
    info = billing.projects().getBillingInfo(name=PROJECT_NAME).execute()
    return info.get("billingEnabled", False)

@functions_framework.cloud_event
def stop_billing(cloud_event):
    # 讀不懂的通知不構成停機的理由；直接結束，不拋出例外，免得 --retry 讓它一直重送
    try:
        notification = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))
    except (KeyError, TypeError, ValueError):
        print(json.dumps({"warning": "undecodable message, ignored"}))
        return
    print(json.dumps({"received": notification}))

    if not should_disable(notification):
        print(json.dumps({"action": "none"}))
        return

    # 呼叫 Cloud Billing API 的錯誤不攔，讓 --retry 重送這則通知
    billing = discovery.build("cloudbilling", "v1", cache_discovery=False)
    if not billing_enabled(billing):
        print(json.dumps({"action": "none", "reason": "billing already disabled"}))
        return

    # billingAccountName 給空字串，就是把專案從帳單帳戶解除連結
    billing.projects().updateBillingInfo(
        name=PROJECT_NAME, body={"billingAccountName": ""}
    ).execute()
    print(json.dumps({"action": "billing disabled", "project": PROJECT_ID}))
```

同一個目錄放一份 `requirements.txt`，列出 `functions-framework` 與 `google-api-python-client`。實測對主題發一則不是 JSON 的訊息，函式留下一筆 `undecodable message, ignored` 的警告、請求回 200，之後沒有重送。

判斷規則是一個要自己決定的取捨：改看 `forecastThresholdExceeded` 會更早解除連結，對被濫用的情形損失更少，而一次正常的流量尖峰也可能讓整個專案停擺；改成「讀不懂就解除連結」，通知格式變動時就會誤停。`should_disable` 現在的寫法在誤停那一側最保守：只有實際花費確實達到預算才停，代價是被濫用時要等到實際花費寫進帳單資料才動作。它適合先上線再依自己的情形調整。

### 部署函式：兩個服務帳號、執行個體上限與重試

部署指令決定函式以誰的身分執行、觸發器以誰的身分呼叫它，以及一次失敗之後那則通知會不會再送一次：

```bash
gcloud functions deploy budget-killswitch --gen2 --region=<region> --runtime=python312 \
  --source=<source-dir> --entry-point=stop_billing --trigger-topic=budget-alerts \
  --service-account=budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --trigger-service-account=budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --set-env-vars=TARGET_PROJECT_ID=<project-id> --max-instances=1 --retry \
  --project=<project-id>
```

- `<region>`：函式所在的 region（區域），例如 `asia-east1`；它與預算或要停用帳單的專案在哪個區域無關。
- `--runtime`：Python 的版本，可用的值由 `gcloud functions runtimes list --region=<region>` 列出；舊版本停止支援之後部署會被拒絕。
- `<source-dir>`：放 `main.py` 與 `requirements.txt` 的本機目錄。
- `--entry-point`：程式裡加了 `@functions_framework.cloud_event` 的那個函式的名稱，改了函式名稱這裡要跟著改。
- `--service-account`：函式執行時的身分，函式以它呼叫 Cloud Billing API。
- `--trigger-service-account`：Eventarc 觸發器呼叫函式時的身分。不給這個旗標時用哪個帳號，`gcloud functions deploy --help` 寫的是專案的 Compute Engine 預設服務帳號，而這次實測用的是 `--service-account` 那一個，兩者不同，所以明確指定，部署後用 `gcloud functions describe budget-killswitch --region=<region> --project=<project-id>` 輸出的 `eventTrigger.serviceAccountEmail` 確認。
- `TARGET_PROJECT_ID`：要停用帳單的專案。這裡填函式自己所在的專案；填別的專案時，〈服務帳號的角色〉的兩條 `add-iam-policy-binding` 改成綁在那個專案上，預算的 `--filter-projects` 也改成那個專案，其餘指令的 `<project-id>` 不變。
- `--max-instances=1`：Cloud Run 對這個函式同一時間最多只啟動一個執行個體。超支之後預算一天會送來好幾則通知，限制成一個讓它們依序處理，不會同時送出多個解除連結的呼叫；重試不斷發生時，函式本身同時佔用的執行個體也只有一個。
- `--retry`：沒有這個旗標時，觸發器的重試政策是 `RETRY_POLICY_DO_NOT_RETRY`（`gcloud functions describe` 輸出的 `eventTrigger.retryPolicy`）。實測函式在讀取帳單狀態時拋出例外，Cloud Run 的請求紀錄卻是 HTTP 200，Pub/Sub 因此把那則超出預算的通知標為已確認收訊（[ack](/backend/knowledge-cards/ack-nack/)），之後不再送；下一次有機會解除連結，要等數小時後的下一則預算通知，這段期間帳單照常計費。加上之後，Pub/Sub 會依觸發器的[重試政策](/backend/knowledge-cards/retry-policy/)在幾分鐘內重送失敗的通知，一次暫時性的錯誤（例如剛授予的權限還沒生效）不必等到下一則通知。不會自己恢復的錯誤（權限少了一個、專案的帳單連結被鎖定）重試也不會成功，那一類只能靠〈上線前後的驗收〉在上線前找出來。

### 觸發器呼叫函式的權限

第二代的 Cloud Run functions 跑在 Cloud Run 上，Eventarc 觸發器以 `--trigger-service-account` 指定的服務帳號身分呼叫它，而那個服務帳號預設沒有呼叫權限。缺這條綁定時，Cloud Run 以 403 擋下每一次推送，紀錄寫著「The IAM principal lacks {run.routes.invoke} permission」，函式一次都不會執行，而 `gcloud functions describe` 顯示的狀態仍是 `ACTIVE`：

```bash
# 第一個 budget-killswitch 是函式名稱：第二代函式在 Cloud Run 上的服務與函式同名
gcloud run services add-iam-policy-binding budget-killswitch --region=<region> \
  --member=serviceAccount:budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --role=roles/run.invoker --project=<project-id>
```

所以這個服務帳號有兩段權限要設：觸發器以它的身分呼叫函式，函式以它的身分呼叫 Cloud Billing API。

### 停損開關放在另一個專案

主題、函式與服務帳號可以放在一個專門放帳單工具、不受停用影響的專案（Cloud Billing 文件稱為 FinOps administration project，下文稱管理專案；文件建議把帳單相關的主題集中在這種專案），被保護的專案只綁〈服務帳號的角色〉的兩個角色，`TARGET_PROJECT_ID` 填被保護的專案。這樣放有三個效果：解除連結之後函式仍在運作，能記錄並通知人「哪個專案被停了」；被保護的專案裡被入侵的身分刪不掉它；驗收時函式不會跟著停，所以兩則測試訊息不必照順序發。實測把函式放在測試專案、`TARGET_PROJECT_ID` 指向另一個專案：超出預算的訊息讓被保護的專案在 9 秒後停用，管理專案的帳單維持啟用，緊接著的低於預算訊息照常處理。代價是管理專案成了所有停損開關的共同依賴：它的帳單停了或權限被收掉，所有被保護的專案一起失去停損開關，所以監看停損開關有沒有持續收到通知的心跳監看（見〈上線前後的驗收〉）要放在管理專案以外。

## 上線前後的驗收：真實通知、低於預算與超出預算的兩則測試訊息

停損開關平常不動作，壞掉與「還沒輪到它動作」在任何狀態欄上都長得一樣；〈停損開關的建置〉開頭的三項設定，實測時各自讓它在狀態顯示正常時失效過一次。所以部署成功不算完成，驗收看的是呼叫鏈最後一段的結果：專案的帳單狀態。這是[平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)的一個應用。

驗收分成兩段，因為測試訊息是從主題送進去的：主題之後的每一段（觸發器、呼叫權限、函式、角色、重試）都會被行使到，主題之前的那一段（預算的範圍、金額、抵免設定、發布到主題的權限）不會。

**主題之前的那一段，用第一則真實的預算通知確認。** 接上主題之後等第一則通知，用下面這條查詢找到一筆 `received` 紀錄，確認 `budgetDisplayName` 是接停損開關的那個預算，再拿它的 `costAmount` 對照帳單報表上這個專案本期的費用：通知的值接近 0 而報表不是，就是抵免設定或 `--filter-projects` 設錯了。實測預算接上主題約 35 分鐘後收到第一則。

```bash
# 列出函式收到的通知；--freshness 依等待的時間調整
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="budget-killswitch" AND jsonPayload.received:*' \
  --freshness=1d --format="json(timestamp,jsonPayload.received)" --project=<project-id>
```

**主題之後的那一段，用兩則測試訊息確認。** 兩則訊息走的是函式的兩條分支。低於預算的那一則確認訊息送得到、判斷邏輯會跑。停損開關跑在被保護的同一個專案時，它要排在超出預算那一則之前：超出預算那一則會讓專案連同函式一起停擺，之後就沒有東西能接收低於預算的那一則。

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 15.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 等一兩分鐘再查：紀錄寫入有延遲；預期 action 是 none；--freshness=10m 只看最近十分鐘
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="budget-killswitch" AND jsonPayload.action:*' \
  --freshness=10m --format="value(timestamp,jsonPayload.action)" --project=<project-id>
```

這條查詢回傳零筆時，有三種可能：紀錄還沒寫入、觸發器被 403 擋下、查詢條件寫錯。把條件裡的 `AND jsonPayload.action:*` 換成 `AND logName:"run.googleapis.com%2Frequests"`、`--format` 換成 `"value(timestamp,httpRequest.status)"`，查同一個服務的請求紀錄：有 403 的請求代表缺〈觸發器呼叫函式的權限〉那條綁定，連請求都沒有代表訊息沒有送到觸發器，兩者都不是函式邏輯的問題。

低於預算的訊息在判斷規則那一步就結束，解除連結要用到的兩個權限（讀取帳單狀態、解除帳單連結）一次都沒有行使。超出預算的那一則才會走到它們，結果看帳單狀態：

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 350.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 等一兩分鐘再查；預期 billingEnabled 變成 false、billingAccountName 變成空字串
gcloud billing projects describe <project-id>
```

測試訊息裡的 `budgetAmount` 大於 0、而且小於或等於 `costAmount` 時，函式就會解除帳單連結，與預算實際設定的金額無關。實測從發出超出預算的訊息到 `billingEnabled` 變成 `false` 約十三秒，所以停損開關整體的反應時間幾乎全部來自帳單資料的延遲。驗收完用 `gcloud billing projects link <project-id> --billing-account=<billing-account-id>` 重新連結，連結完成才算驗收結束。

這次驗收會實際讓專案停擺，排在停機可以接受的時段做；之後每一次修改函式、角色或觸發器，都再做一次。專案有停用之後不能遺失的資料時，改用分段驗證（做法的推導在[平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)）：

- **在可拋棄的專案上完整觸發一次**：另外部署一份複本，函式名稱與主題都換掉（例如 `budget-killswitch-test` 與 `budget-alerts-test`），`--trigger-topic` 與 `gcloud pubsub topics publish` 都用新的主題，`TARGET_PROJECT_ID` 指向一個可拋棄的空專案，〈服務帳號的角色〉的兩個角色綁在那個空專案上，再對它發超出預算的訊息。複本若沿用正式的函式名稱，部署會蓋掉正式的函式；訊息若發到正式的主題，被停用的就是正式專案。
- **在正式專案上只確認權限**：用 IAM 的權限檢查工具 Policy Troubleshooter，確認服務帳號在正式專案上持有 `resourcemanager.projects.deleteBillingAssignment` 與 `resourcemanager.projects.get`。指令是 `gcloud policy-intelligence troubleshoot-policy iam //cloudresourcemanager.googleapis.com/projects/<project-id> --principal-email=<sa-email> --permission=<permission>`，執行的專案要先啟用 `policytroubleshooter.googleapis.com`；輸出的 `overallAccessState` 是 `CAN_ACCESS` 才算有。實測沒有綁角色的服務帳號回 `CANNOT_ACCESS`。

分段驗證仍沒有行使正式專案上那一次 `updateBillingInfo`，驗收紀錄要寫明缺了這一段。

別人調整了角色（例如權限盤點時收掉 `roles/browser`）或鎖定了專案的帳單連結時，部署的人不會知道要重驗，所以另設一個[心跳監看（dead man's switch）](/backend/knowledge-cards/dead-mans-switch/)：預算一天會送好幾則通知，函式的紀錄長時間沒有出現帶 `action` 欄位的紀錄就通知，讓函式停止收到通知這件事本身也成為訊號。實測的做法是用 `gcloud logging metrics create` 把那類紀錄做成日誌指標，再在 Cloud Monitoring 建一條缺席條件（condition absent）的告警；缺席條件的時間窗上限是 23 小時 30 分，設成 24 小時會被拒，所以時間窗設 23 小時。這個心跳監看本身也是平常不動作的機制，設好之後暫時把時間窗縮到幾分鐘，確認通知送到收的人手上，再改回 23 小時：實測時間窗設 3 分鐘，最後一筆紀錄之後 4 到 9 分鐘告警送達。停損開關正常觸發之後，被保護的專案整個停擺，所以心跳監看不能放在被保護的專案裡，要放在第三個專案。

## 解除連結之後恢復服務

實際因為超支而停用之後，`costAmount` 是本期累計值，整個預算期間都不會降回預算以下；只重新連結的話，下一則預算通知（一天會來好幾則）會讓函式再解除一次。恢復的順序依停用的原因而不同。

**服務自己出錯**：修好程式之後，先調高預算金額（`gcloud billing budgets update <budget-resource-name> --budget-amount=<amount><currency-code> --billing-project=<project-id>`）或刪掉函式，再重新連結。

**資源被別人濫用**：重新連結之前，把預算金額調成目前的 `costAmount` 加上清理期間能承受的金額，讓停損開關在攻擊者再開資源時仍會動作，又不會在清理途中被已經累計的花費再觸發一次；並先撤銷外洩的 API 金鑰與服務帳號金鑰：實測帳單停用期間 `gcloud services api-keys list` 與 `delete` 都照常可用。重新連結之後列出並刪除不屬於自己的 VM、instance template 與 MIG，清單要在重新連結之後列，因為停用期間的清單是空的；確認乾淨之後再把預算調回原本的金額。

實測重新連結之後 4 分鐘內沒有再被停用：停用期間對主題發布的訊息照樣被接受，而函式在停用後的那一分鐘內就把它處理掉了（回報帳單已停用），沒有留到重新連結之後。

## 延伸閱讀：上限的理由、費用的歸因、防護機制的驗收與服務帳號的兩邊權限

- → [開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)：〈Per-team 成本上限〉說明給每個團隊與環境設上限的理由，本篇是那個上限在 GCP 上的執行方式
- → [成本監控與告警](/operations/08-cost-management/cost-monitoring/)：收到預算警示之後，靠資源標記定位是哪個團隊的哪類資源在漲；停損開關解除連結之前，要依歸因的結果選定是哪一個專案
- → [平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)：停損開關、稽核紀錄與告警共用的驗收方法，以及「部署成功、狀態正常」為什麼不算驗收
- → [Service Account（服務帳號）](/infra/knowledge-cards/service-account/)：服務帳號的權限分成「它能做什麼」與「誰能以它的身分行事」兩邊，停損開關的角色與部署者的 `serviceAccountUser` 各屬一邊
