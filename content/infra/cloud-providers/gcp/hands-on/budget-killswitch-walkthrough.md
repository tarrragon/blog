---
title: "GCP 預算警示與停損開關的實測紀錄：建預算、Pub/Sub 主題、服務帳號、函式與觸發器、兩段驗收、心跳監看與停用後的恢復"
date: 2026-10-25
description: "要在 GCP 專案上建預算警示，或建一個花費超過預算就解除帳單連結的停損開關，想照一次實跑過的順序做、看每一步漏掉或換一種做法的結果時讀；也用在函式部署成功、狀態 ACTIVE 卻從沒解除過帳單連結，或專案因超支被停用之後要恢復的時候"
weight: 3
tags: ["devops", "cost-management", "gcp", "budget", "kill-switch", "hands-on"]
---

實測日期是 2026-10-24，在 GCP 測試專案 `blog-verify-20261024` 上分兩次實跑：第一次建出停損開關並觸發一次；第二次另開一個可拋棄的目標專案，驗預算的範圍與抵免、電子郵件通知管道、停損開關放在另一個專案、拆開驗證、心跳監看與恢復。帳單帳戶的幣別是新台幣，帳戶上有抵免；測試帳號底下沒有組織。

這篇記錄在 GCP 上建預算警示與停損開關（由預算通知觸發、把專案從帳單帳戶解除連結的函式）的實際操作。內容依操作的順序是：建立限定一個專案的預算；建接收通知的 Pub/Sub 主題並把預算接上；建服務帳號並授予解除帳單連結與讀取帳單狀態的角色；函式的程式；部署函式並指定兩個服務帳號、執行個體上限與重試；授予觸發器呼叫函式的權限；停損開關放在另一個專案時要改的指令；用第一則真實通知與兩則測試訊息做兩段驗收；設心跳監看；超支停用之後的恢復。每一步寫出這次的取值與實測結果，以及漏掉或換一種做法時的結果；替代做法與沒做時的結果沒有另外標註的是這次實測看到的，照官方文件推出的寫出文件，推論的寫明沒有實跑。費用失控的來源與帳單資料的延遲、預算警示與強制執行支出上限的作用範圍、兩種處置（解除帳單連結、只停止花錢的資源）該選哪一種、停損開關為什麼要放在另一個專案、驗收為什麼分兩段，寫在 [GCP 上的雲端費用失控防護](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)（下文稱概念篇），這裡不重寫。

停損開關的效果是一次自己造成的全面停機。建之前先照 [GCP 上的雲端費用失控防護](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/) 的〈由預算通知觸發的處置：解除帳單連結與只停止花錢的資源〉判斷這個專案該不該建、建哪一種。下文以停損開關為例；只停止花錢的資源那一種的取捨與實測結果（跨全部 zone 停 VM、約兩分鐘 `TERMINATED`）寫在那一節，它的函式本體這篇沒有收。

停損開關部署了卻沒有動作時，成因依呼叫鏈的段落分在這幾節：通知裡的 `costAmount` 沒有越過預算（抵免、帳單資料延遲、`--filter-projects` 的範圍）見〈建立限定一個專案的預算〉；通知沒有送到主題或主題接錯預算，見〈建接收通知的主題並把預算接上〉；函式收到了卻沒有解除連結，見〈建服務帳號並授予兩個角色〉〈部署函式：兩個服務帳號、執行個體上限與重試〉〈授予觸發器呼叫函式的權限〉；要確認是哪一段，照〈兩段驗收：第一則真實通知，再發兩則測試訊息〉。

下面的指令用到三個本文取的名稱：主題 `budget-alerts`、服務帳號 `budget-killswitch-sa`、函式 `budget-killswitch`。換成別的名稱時，同一個名稱出現的每一條指令都要一起換。`<project-id>` 指的是放停損開關、同時也是要被停用帳單的那個專案；兩者分開的情形見〈停損開關放在另一個專案時要改的指令〉。

## 建立限定一個專案的預算

建立預算的人要通過兩道權限檢查：實測沒有任何角色的帳號先被 `--billing-project` 那個專案擋下（缺 `serviceusage.services.use`，訊息寫 `USER_PROJECT_DENIED`）；補上 `roles/serviceusage.serviceUsageConsumer` 約一分鐘後，才換成帳單帳戶的權限不足。所以建立預算的人要有那個專案的 `serviceusage.services.use`，以及帳單帳戶上能管理預算的角色（帳單帳戶管理員或帳單帳戶費用管理員）。

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
- `--filter-projects`：預算只計算這些專案的花費。`gcloud billing budgets describe` 的 `budgetFilter.projects` 存的是專案編號，不是專案 ID。
- 門檻比例：50% 與 90% 留給收到通知的人處理的時間，100% 對齊花費達到預算的那一刻，預測花費的門檻提早反映速度異常；比例依處理一次所需的時間自己調整。
- `--billing-project`：gcloud 呼叫預算 API 所用的專案，不影響預算的範圍。

接停損開關的預算要另外建，不接到既有的帳戶層級警示預算上；它的金額設成這個專案本期能承受的最高花費，減掉帳單資料延遲期間多出的費用，估法見概念篇〈由預算通知觸發的處置：解除帳單連結與只停止花錢的資源〉。

- **沒做時**（不給 `--filter-projects`）：`gcloud billing budgets create --help` 寫著預算涵蓋所有專案，通知裡的 `costAmount` 是帳單帳戶下所有專案的合計；接上停損開關時，別的專案超支會停掉這一個（從程式的判斷規則推論，這次沒有實跑）。
- **替代做法**：
  - 加 `--credit-types-treatment=exclude-all-credits`，換到的是以抵免前的金額計算、大額抵免期間門檻照樣觸發，實測同一段期間扣掉抵免的帳戶層級預算報 `costAmount` 0.05、`exclude-all-credits` 的預算報 0.37；付出的是免費方案的用量也以原價算進花費（推論：`FREE_TIER` 是預算接受的抵免類型，這次沒有量）。
  - 改用 `--credit-types-treatment=include-specified-credits` 搭配 `--filter-credit-types=FREE_TIER`，換到的是只讓免費方案的用量照常扣掉；類型寫錯時回 `INVALID_ARGUMENT: ... is not a valid credit type string`，`--help` 不列出可用的類型，以 Cloud Billing 文件為準。
  - 加 `--notifications-rule-monitoring-notification-channels=<channel-resource-name>`，把通知另外寄到 Cloud Monitoring 的電子郵件通知管道，換到的是值班的人收得到，付出的是只支援電子郵件類型：接上 webhook 類型的管道時只回 `INVALID_ARGUMENT: Request contains an invalid argument`，訊息不說原因。`<channel-resource-name>` 形如 `projects/<project-id>/notificationChannels/<channel-id>`，在主控台的 Monitoring 通知管道頁面查得到。

## 建接收通知的主題並把預算接上

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

`<budget-resource-name>` 是 `gcloud billing budgets list --billing-account=<billing-account-id> --billing-project=<project-id> --format="value(name)"` 印出的完整名稱，形如 `billingAccounts/<id>/budgets/<uuid>`，與建立時給的顯示名稱是兩個值。設定通知目標時，GCP 會自動讓預算服務的系統帳號 `billing-budget-alert@system.gserviceaccount.com` 擁有這個主題的發布權限，`gcloud pubsub topics get-iam-policy budget-alerts --project=<project-id>` 看得到這條綁定。

預算接上主題之後，GCP 一天會送好幾次通知過來，不論花費有沒有越過門檻。第一則送到的時間兩次實跑不同：第一次實跑約 8 分鐘，第二次新建的預算約 35 分鐘；Cloud Billing 文件說第一則可能要數小時。通知的內容如下，`alertThresholdExceeded` 這類欄位要等越過門檻才會出現：

```json
{"budgetDisplayName": "<budget-display-name>", "costAmount": 0.0, "costIntervalStart": "2026-10-01T07:00:00Z",
 "budgetAmount": 320.0, "budgetAmountType": "SPECIFIED_AMOUNT", "currencyCode": "TWD"}
```

主題原本接在別的預算上時，只有一種做法拿得掉：`gcloud billing budgets update` 沒有清除 Pub/Sub 通知的旗標，要對預算 API 送 PATCH，`updateMask` 設成 `notificationsRule.pubsubTopic`、`notificationsRule.pubsubTopic` 設成空字串。這次用這個方式拿掉了；送出的完整指令沒有留下來，請求的形狀以 Cloud Billing Budget API 的 `budgets.patch` 文件為準。

- **沒做時**（一個主題接了好幾個預算）：本文的函式不分辨通知來自哪一個預算，任何一個超支都會讓它停掉 `TARGET_PROJECT_ID`（從程式的判斷規則推論，這次沒有實跑）。要依預期花費收通知，另建一個不接主題的預算。

## 建服務帳號並授予兩個角色

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

`roles/billing.projectManager` 只包含兩個權限，建立與刪除專案的帳單連結（`gcloud iam roles describe roles/billing.projectManager` 列得出來），讀取帳單狀態不在裡面。`roles/browser` 包含 `resourcemanager.projects.get`，整個角色是讀取專案、資料夾與組織的中繼資料以及專案 IAM policy 的六個權限，不包含讀取專案內資源的權限。執行部署指令的人另外要有這個服務帳號的 `roles/iam.serviceAccountUser`，才能把它指定給函式與觸發器；專案擁有者本來就有。要管多個專案時，每個專案各建一個限定在該專案的預算、一個主題與一個函式部署，兩個角色在每個專案各綁一次。

- **沒做時**（只給 `roles/billing.projectManager`）：函式在解除連結之前先讀一次帳單狀態，那一步回 403「The caller does not have permission」；函式部署成功、狀態 `ACTIVE`，停損開關卻不會解除帳單連結。
- **替代做法**：拿掉函式裡讀帳單狀態的那一步、只留解除連結，換到的是少一個角色，付出的是重複的通知會對已經停用的專案再送一次解除連結（推論，這次沒有實跑）。

## 判斷並解除帳單連結的函式

下面的程式存成 `<source-dir>/main.py`，判斷規則只看實際花費：

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

- **沒做時**（讀不懂的訊息拋出例外）：加了 `--retry` 之後，那則訊息會被一直重送（從重試政策的作用推論，這次沒有實跑）。
- **替代做法**（判斷規則）：改看 `forecastThresholdExceeded`，換到的是更早解除連結、被濫用時損失更少，付出的是一次正常的流量尖峰也可能讓整個專案停擺；改成「讀不懂就解除連結」，換到的是格式異常時偏向保護費用，付出的是通知格式變動時就會誤停（兩者都是推論，這次沒有實跑）。現在的寫法在誤停與漏停兩種錯誤裡最不會誤停，代價是被濫用時要等到實際花費寫進帳單資料才動作。

## 部署函式：兩個服務帳號、執行個體上限與重試

```bash
gcloud functions deploy budget-killswitch --gen2 --region=<region> --runtime=python312 \
  --source=<source-dir> --entry-point=stop_billing --trigger-topic=budget-alerts \
  --service-account=budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --trigger-service-account=budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --set-env-vars=TARGET_PROJECT_ID=<project-id> --max-instances=1 --retry \
  --project=<project-id>
```

- `<region>`：函式所在的 region，例如 `asia-east1`；它與預算或要停用帳單的專案在哪個區域無關。
- `--runtime`：Python 的版本，可用的值由 `gcloud functions runtimes list --region=<region>` 列出；舊版本停止支援之後部署會被拒絕。
- `<source-dir>`：放 `main.py` 與 `requirements.txt` 的本機目錄。
- `--entry-point`：程式裡加了 `@functions_framework.cloud_event` 的那個函式的名稱。
- `--service-account`：函式執行時的身分，函式以它呼叫 Cloud Billing API。
- `--trigger-service-account`：Eventarc 觸發器呼叫函式時的身分。不給這個旗標時用哪個帳號，`gcloud functions deploy --help` 寫的是專案的 Compute Engine 預設服務帳號，而這次實測用的是 `--service-account` 那一個，兩者不同，所以明確指定，部署後用 `gcloud functions describe budget-killswitch --region=<region> --project=<project-id>` 輸出的 `eventTrigger.serviceAccountEmail` 確認。
- `TARGET_PROJECT_ID`：要停用帳單的專案。
- `--max-instances=1`：同一時間最多只啟動一個執行個體，超支之後一天好幾則通知依序處理，不會同時送出多個解除連結的呼叫。
- `--retry`：讓 Pub/Sub 依觸發器的[重試政策](/backend/knowledge-cards/retry-policy/)在幾分鐘內重送失敗的通知，一次暫時性的錯誤（剛授予的權限還沒生效）不必等到下一則通知。不會自己恢復的錯誤（權限少了一個、專案的帳單連結被鎖定）重試也不會成功，那一類只能靠〈兩段驗收：第一則真實通知，再發兩則測試訊息〉在上線前找出來。

- **沒做時**（不加 `--retry`）：觸發器的重試政策是 `RETRY_POLICY_DO_NOT_RETRY`（`gcloud functions describe` 輸出的 `eventTrigger.retryPolicy`）。函式在讀取帳單狀態時拋出例外，Cloud Run 的請求紀錄卻是 HTTP 200，Pub/Sub 因此把那則超出預算的通知標為已確認收訊（[ack](/backend/knowledge-cards/ack-nack/)），之後不再送；下一次有機會解除連結，要等數小時後的下一則預算通知，這段期間帳單照常計費。
- **沒做時**（不加 `--max-instances=1`）：超支之後同時到的幾則通知可能各自啟動一個執行個體、各送一次解除連結（推論，這次沒有實跑）。

## 授予觸發器呼叫函式的權限

第二代的 Cloud Run functions 跑在 Cloud Run 上，Eventarc 觸發器以 `--trigger-service-account` 指定的服務帳號身分呼叫它，而那個服務帳號預設沒有呼叫權限：

```bash
# 第一個 budget-killswitch 是函式名稱：第二代函式在 Cloud Run 上的服務與函式同名
gcloud run services add-iam-policy-binding budget-killswitch --region=<region> \
  --member=serviceAccount:budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --role=roles/run.invoker --project=<project-id>
```

- **沒做時**：Cloud Run 以 403 擋下每一次推送，紀錄寫著「The IAM principal lacks {run.routes.invoke} permission」，函式一次都不會執行，而 `gcloud functions describe` 顯示的狀態仍是 `ACTIVE`。
- **替代做法**：觸發器改用另一個只有 `roles/run.invoker` 的服務帳號，換到的是呼叫權限與解除帳單連結的權限分在兩個身分上，付出的是多管一個服務帳號（推論，這次沒有實跑）。

## 停損開關放在另一個專案時要改的指令

主題、函式與服務帳號放在一個專門放帳單工具的管理專案、要停用帳單的是另一個專案時，上面的指令照下面改，其餘不變：

- 主題、服務帳號、函式、觸發器的呼叫權限：`--project=<project-id>` 與服務帳號位址裡的 `<project-id>` 都填管理專案。
- 服務帳號的兩個角色：`gcloud projects add-iam-policy-binding` 的第一個引數改成被保護的專案，`--member` 仍是管理專案裡的服務帳號。
- 部署：`--set-env-vars=TARGET_PROJECT_ID=` 填被保護的專案。
- 預算：`--filter-projects=projects/` 填被保護的專案。

第二次實跑把函式放在 `blog-verify-20261024`、`TARGET_PROJECT_ID` 指向另一個可拋棄的專案：超出預算的訊息讓被保護的專案在 9 秒後停用，管理專案的帳單維持啟用，緊接著的低於預算訊息照常處理。這樣放的效果與代價見概念篇〈停損開關放在另一個專案〉。

- **沒做時**（停損開關跑在被保護的同一個專案）：解除連結之後，查詢函式狀態的 API 直接回 403，訊息要求確認帳單帳戶；函式本身在停用後約一分鐘內仍處理了下一則通知，之後的行為這次沒有觀察。兩段驗收的兩則測試訊息要照順序發。

## 兩段驗收：第一則真實通知，再發兩則測試訊息

驗收分成預算到 Pub/Sub 主題、主題之後兩段，各用不同的訊息確認，理由見概念篇〈驗收：真實通知確認預算到 Pub/Sub 主題的一段，測試訊息確認主題之後的一段〉。

**Pub/Sub 主題之前的那一段，用第一則真實的預算通知確認。** 接上主題之後等第一則通知，用下面這條查詢找到一筆 `received` 紀錄，確認 `budgetDisplayName` 是接停損開關的那個預算，再拿它的 `costAmount` 對照帳單報表上這個專案本期的費用：通知的值接近 0 而報表不是，就是抵免設定或 `--filter-projects` 設錯了。

```bash
# 列出函式收到的通知；--freshness 依等待的時間調整
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="budget-killswitch" AND jsonPayload.received:*' \
  --freshness=1d --format="json(timestamp,jsonPayload.received)" --project=<project-id>
```

**Pub/Sub 主題之後的那一段，用兩則測試訊息確認。** 低於預算的那一則確認訊息送得到、判斷邏輯會跑；停損開關跑在被保護的同一個專案時，它要排在超出預算那一則之前。

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 15.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 等一兩分鐘再查：紀錄寫入有延遲；預期 action 是 none；--freshness=10m 只看最近十分鐘
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="budget-killswitch" AND jsonPayload.action:*' \
  --freshness=10m --format="value(timestamp,jsonPayload.action)" --project=<project-id>
```

這條查詢回傳零筆時，有三種可能：紀錄還沒寫入、觸發器被 403 擋下、查詢條件寫錯。把條件裡的 `AND jsonPayload.action:*` 換成 `AND logName:"run.googleapis.com%2Frequests"`、`--format` 換成 `"value(timestamp,httpRequest.status)"`，查同一個服務的請求紀錄：有 403 的請求代表缺〈授予觸發器呼叫函式的權限〉那條綁定，查不到任何請求代表訊息沒有送到觸發器。

低於預算的訊息在判斷規則那一步就結束，讀取帳單狀態與解除帳單連結的權限一次都沒有行使。超出預算的那一則才會走到它們，結果看帳單狀態：

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 350.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 等一兩分鐘再查；預期 billingEnabled 變成 false、billingAccountName 變成空字串
gcloud billing projects describe <project-id>
```

測試訊息裡的 `budgetAmount` 大於 0、而且小於或等於 `costAmount` 時，函式就會解除帳單連結，與預算實際設定的金額無關。實測從發出超出預算的訊息到 `billingEnabled` 變成 `false` 約十三秒。驗收完用 `gcloud billing projects link <project-id> --billing-account=<billing-account-id>` 重新連結，連結完成才算驗收結束。這次驗收會實際讓專案停擺，排在停機可以接受的時段做；之後每一次修改函式、角色或觸發器，都再做一次。

- **沒做時**（只看部署成功與 `ACTIVE`）：〈建服務帳號並授予兩個角色〉的 `roles/browser`、〈部署函式：兩個服務帳號、執行個體上限與重試〉的 `--retry`、〈授予觸發器呼叫函式的權限〉的 `roles/run.invoker`，實測時各自讓停損開關在狀態顯示正常時失效過一次。
- **替代做法**（專案有停用之後不能遺失的資料時）：拆開驗證，第二次實跑做過。
  - 在可拋棄的專案上完整觸發一次：另外部署一份複本，函式名稱與主題都換掉（例如 `budget-killswitch-test` 與 `budget-alerts-test`），`TARGET_PROJECT_ID` 指向一個可拋棄的空專案，兩個角色綁在那個空專案上，再對它發超出預算的訊息。複本若沿用正式的函式名稱，部署會蓋掉正式的函式；訊息若發到正式的主題，被停用的就是正式專案。
  - 在正式專案上只確認權限：`gcloud policy-intelligence troubleshoot-policy iam //cloudresourcemanager.googleapis.com/projects/<project-id> --principal-email=<sa-email> --permission=<permission>`。`<sa-email>` 是 `budget-killswitch-sa@<project-id>.iam.gserviceaccount.com`，`<permission>` 依序填 `resourcemanager.projects.deleteBillingAssignment` 與 `resourcemanager.projects.get`；執行的專案要先啟用 `policytroubleshooter.googleapis.com`。輸出的 `overallAccessState` 是 `CAN_ACCESS` 才算有，沒有綁角色的服務帳號回 `CANNOT_ACCESS`。

  拆開驗證仍沒有行使正式專案上那一次 `updateBillingInfo`，驗收紀錄要寫明缺了這一段。

## 心跳監看：函式停止收到通知時告警

預算一天會送好幾則通知，函式的紀錄長時間沒有出現帶 `action` 欄位的紀錄就通知，讓函式停止收到通知這件事本身也成為訊號。心跳監看建在第三個專案：停損開關正常觸發之後，被保護的專案整個停擺，告警放在那裡會一起停；也不放在管理專案，管理專案失效時要有人知道。實測的做法是用 `gcloud logging metrics create` 把帶 `action` 欄位的那類紀錄做成日誌指標，再在 Cloud Monitoring 建一條缺席條件（condition absent）的告警；缺席條件的時間窗上限是 23 小時 30 分，設成 24 小時會被拒，所以時間窗設 23 小時。設好之後暫時把時間窗縮到幾分鐘，確認通知送到收的人手上，再改回 23 小時：實測時間窗設 3 分鐘，最後一筆紀錄之後 4 到 9 分鐘告警送達。這次建指標與告警政策的完整指令沒有留下來，日誌指標的 filter 用〈兩段驗收：第一則真實通知，再發兩則測試訊息〉那條 `jsonPayload.action:*` 的查詢條件。

- **沒做時**：別人調整了角色（例如權限盤點時收掉 `roles/browser`）或鎖定了專案的帳單連結時，部署的人不會知道要重驗，停損開關一直顯示 `ACTIVE`（推論，這次沒有實跑）。

## 超支停用之後的恢復

恢復之前先調預算的理由（`costAmount` 是本期累計值，只重新連結的話下一則通知會讓函式再解除一次）與依停用原因分開的順序，見概念篇〈解除連結之後恢復服務的順序〉。

**服務自己出錯**：修好程式之後，先調高預算金額或刪掉函式，再重新連結：

```bash
gcloud billing budgets update <budget-resource-name> --budget-amount=<amount><currency-code> --billing-project=<project-id>
gcloud billing projects link <project-id> --billing-account=<billing-account-id>
```

**資源被別人濫用**：重新連結之前，把預算金額調成目前的 `costAmount` 加上清理期間能承受的金額，並先撤銷外洩的 API 金鑰與服務帳號金鑰：實測帳單停用期間 `gcloud services api-keys list` 與 `delete` 都照常可用。重新連結之後列出並刪除不屬於自己的 VM、instance template 與 MIG，確認乾淨之後再把預算調回原本的金額。

實測停用約兩分半鐘再重新連結，Cloud Router、Cloud NAT、函式與它的觸發器都還在、設定沒變（這次沒有觀察 VM 與資料庫）；停用期間 `gcloud compute routers list` 回傳零筆，重新連結之後 Cloud Router 仍在。重新連結之後 4 分鐘內沒有再被停用：停用期間對主題發布的訊息照樣被接受，而函式在停用後的那一分鐘內就把它處理掉了（回報帳單已停用），沒有留到重新連結之後。

- **替代做法**：刪掉函式再重新連結，換到的是不必估清理期間的金額，付出的是清理期間沒有停損開關；被濫用的情形下，這段時間正是攻擊者可能再開資源的時候（推論，這次沒有實跑）。
