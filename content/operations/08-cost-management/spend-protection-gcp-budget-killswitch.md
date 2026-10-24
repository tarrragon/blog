---
title: "GCP 上的雲端費用失控防護：預算警示、強制執行支出上限與自動停用帳單的作用範圍、反應時間與驗收"
date: 2026-10-24
description: "GCP 上為費用失控設防的機制：預算警示寄出通知的時機與幣別、強制執行支出上限涵蓋的服務，以預算通知觸發函式把專案從帳單帳戶解除連結的建置步驟、權限與重試設定，計費資料延遲對這些機制反應時間的影響，以及停損開關上線前用測試訊息觸發一次的驗收"
weight: 6
tags: ["devops", "cost-management", "gcp", "budget", "kill-switch", "security"]
---

這篇整理在 GCP 上為費用失控設防的做法，範圍從專案已經連結到一個帳單帳戶開始。[開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)的〈Per-team 成本上限〉說明了為什麼要給團隊與環境設一個費用的上限；這一篇處理那個上限在 GCP 上由哪些機制執行、每一個機制在費用超過門檻時實際做了什麼，以及從費用發生到它動作之間隔了多久。文中的指令與觀察來自 2026 年 10 月在一個 GCP 測試專案上的實跑；主控台的選項與服務清單會變動，以操作當下看到的為準。

## 費用失控的來源與反應時間

費用失控指的是費用增加的速度快過人發現它、處理它的速度。來源分成兩類，處置方式不同，所以先分開：

- **服務自己出錯**：程式對失敗的請求無限重試、一個事件觸發的函式又產生同一種事件而形成遞迴、自動擴縮的上限設得太高。費用花在自己的服務上，修好程式就停。
- **資源被別人濫用**：外洩的 API key 被拿去呼叫付費 API、被入侵的 VM 被拿去挖礦。費用花在別人的用途上，要先切斷對方能用的資源，再處理入侵。

兩類共同的問題是時間。一個防護機制從費用發生到動作，要經過三段：雲端把用量算成費用、寫進帳單資料；帳單資料觸發通知；通知觸發處置（人或程式）。把用量算成費用那一段的延遲由雲端決定，GCP 的帳單主控台寫著費用資料要數小時後才會顯示、有時超過 24 小時。實測時一個專案已經跑過幾個小時的 VM、Windows VM 與一個 GKE 叢集，同一時間送到的預算通知裡，`costAmount`（本期累計花費）仍然是 `0.0`。

預算警示、強制執行支出上限與自動停用帳單都讀帳單資料，反應時間都至少是這段延遲。它們限制的是損失的上限，不是即時止血；要更快的控制，得靠不經過帳單資料的限制，例如 API 的配額、[rate limit](/backend/knowledge-cards/rate-limit/) 與 API key 的使用範圍。

## 預算警示：寄出通知，不停止扣款

預算（budget）是掛在帳單帳戶上的一組門檻：本期花費達到預算的某個比例時，GCP 寄通知給帳單帳戶的管理員。門檻有兩種依據，**實際花費**（已經寫進帳單資料的費用）與**預測花費**（GCP 依目前的速度推估到期末的費用）；預測的門檻比實際的早響，代價是一次短暫的尖峰也可能觸發它。預算只寄通知，扣款照常進行。

建立預算的指令如下，門檻設在實際花費的 50%、90%、100%，另加一個預測花費達 100% 的門檻：

```bash
# 查帳單帳戶的 ID 與幣別：預算金額用的是這個幣別
gcloud billing accounts list
gcloud billing accounts describe <billing-account-id> --format="value(currencyCode)"

# 建立預算：金額寫成「數字加幣別代碼」，幣別要與帳單帳戶相同
gcloud billing budgets create --billing-account=<billing-account-id> \
  --display-name=<budget-name> --budget-amount=<amount><currency-code> \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
  --threshold-rule=percent=1.0,basis=forecasted-spend \
  --billing-project=<project-id>
```

- `<billing-account-id>`：`gcloud billing accounts list` 的第一欄，形如 `010F25-91BD35-0036E1`。
- `<amount><currency-code>`：例如帳單帳戶的幣別是新台幣時寫成 `320TWD`。主控台建立預算的表單只顯示一個 `$`，不顯示幣別；幣別是新台幣的帳戶在那裡填 `10`，門檻是新台幣 10 元而不是 10 美元。
- `--billing-project`：預算 API 是透過這個專案呼叫的，那個專案要先啟用 Billing Budgets API（`gcloud services enable billingbudgets.googleapis.com --project=<project-id>`）。它不決定預算的範圍；不另外指定時，預算涵蓋整個帳單帳戶的所有專案。

通知會寄給帳單帳戶的管理員與帳單使用者，所以要確認這些帳號的信箱有人在看。預算另外可以把通知送到一個 Pub/Sub topic，這是〈自動停用帳單〉那一節的入口。

## 強制執行支出上限：只涵蓋部分服務

帳單主控台的「Budgets & caps」頁面在建立預算時，有一個「強制執行支出上限（適用於某些服務）」的選項：花費達到上限時，暫停指定服務的用量，直到上限被解除為止。這是帳單功能裡不需要自己寫程式的硬上限，而它的範圍有兩個限制：一次只能套用到單一專案，而且只涵蓋清單上的服務。2026 年 10 月建立表單時列出的是 Cloud Run、Cloud Run Functions、Gemini API 與 Vertex AI 四項，Compute Engine 與 GKE 不在清單上。

所以工作負載跑在這幾種服務上時，這個選項可以直接用；跑在 VM 或 Kubernetes 上時，要的是自動停用帳單。表單的服務下拉選單就是涵蓋清單，建立之前打開看一次。

## 自動停用帳單：把專案從帳單帳戶解除連結

自動停用帳單的做法是讓預算通知觸發一段程式，由程式呼叫 Cloud Billing API 把專案從帳單帳戶解除連結。專案沒有連結帳單帳戶時，GCP 停止專案裡所有需要帳單的資源的運作，費用也就停止增加。這段程式在下文稱為**停損開關**。

```text
預算（帳單帳戶）── 通知 ──> Pub/Sub topic ── 推送 ──> Eventarc 觸發器 ── 呼叫 ──> Cloud Run functions 函式 ── updateBillingInfo ──> 專案的帳單連結被移除
```

建之前先決定要不要建，因為停損開關的效果是一次自己造成的全面停機：VM、資料庫、函式、Kubernetes 叢集一起停擺，停損開關本身跑在同一個專案時也跟著停（實測解除連結之後，查詢函式狀態的 API 直接回 403，訊息要求確認帳單帳戶）。判斷方式是比較兩種代價：「被濫用或程式出錯而多付一筆費用」與「這個專案的服務全部停止」，哪一個比較高。

- **測試專案、個人專案、只跑實驗的專案**：服務停了沒有人受影響，多付的費用卻沒有上限，建停損開關。
- **正式服務**：全面停機的代價通常高於一段時間的超支，改用預算警示加值班處理；要建的話，只建在風險集中的專案上（例如對外公開 API key 的專案），並把正式服務放在另一個專案。

重新連結帳單帳戶之後，資源恢復運作。實測停用大約三分鐘再重新連結，Cloud Router、Cloud NAT、函式與它的觸發器都還在、設定沒變；停用期間 `gcloud compute routers list` 回傳的是零筆。所以停用期間清單是空的，不代表資源已經刪除，重新連結後它們會繼續計費。專案長時間停用之後 GCP 如何處理其中的資源，以 Cloud Billing 文件中停用帳單的說明為準。

## 停損開關的建置：topic、服務帳號的角色、函式與觸發器的呼叫權限

建置有四個元件：接收通知的 [Pub/Sub](/backend/knowledge-cards/pub-sub/) topic、執行函式的[服務帳號](/infra/knowledge-cards/service-account/)、函式本身，以及觸發器呼叫函式的權限。服務帳號的角色、函式的重試設定與觸發器的呼叫權限，任何一項設錯，部署指令都回報成功、函式狀態都顯示 `ACTIVE`，停損開關卻不會切斷帳單，所以每一項都寫清楚它管的是哪一段。

### 接收通知的 topic

```bash
gcloud services enable pubsub.googleapis.com cloudfunctions.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com eventarc.googleapis.com \
  cloudbilling.googleapis.com --project=<project-id>

# 建立 topic，並讓預算把通知送過來
gcloud pubsub topics create budget-alerts --project=<project-id>
gcloud billing budgets update <budget-name> \
  --notifications-rule-pubsub-topic=projects/<project-id>/topics/budget-alerts \
  --billing-project=<project-id>
```

`<budget-name>` 是 `gcloud billing budgets list --billing-account=<billing-account-id> --billing-project=<project-id> --format="value(name)"` 印出的完整名稱，形如 `billingAccounts/<id>/budgets/<uuid>`。設定通知目標時，GCP 會自動讓預算服務的系統帳號 `billing-budget-alert@system.gserviceaccount.com` 擁有這個 topic 的發布權限，`gcloud pubsub topics get-iam-policy budget-alerts` 看得到這條綁定。

預算接上 topic 之後，GCP 會定期送通知過來，不論花費有沒有越過門檻；實測接上後約八分鐘收到第一則。通知的內容如下，`alertThresholdExceeded` 這類欄位要等越過門檻才會出現：

```json
{"budgetDisplayName": "<budget-name>", "costAmount": 0.0, "costIntervalStart": "2026-10-01T07:00:00Z",
 "budgetAmount": 320.0, "budgetAmountType": "SPECIFIED_AMOUNT", "currencyCode": "TWD"}
```

### 服務帳號的角色

```bash
gcloud iam service-accounts create budget-killswitch --project=<project-id>

# 解除專案的帳單連結
gcloud projects add-iam-policy-binding <project-id> \
  --member=serviceAccount:budget-killswitch@<project-id>.iam.gserviceaccount.com \
  --role=roles/billing.projectManager

# 讀取專案的帳單狀態（getBillingInfo 需要 resourcemanager.projects.get）
gcloud projects add-iam-policy-binding <project-id> \
  --member=serviceAccount:budget-killswitch@<project-id>.iam.gserviceaccount.com \
  --role=roles/browser
```

`roles/billing.projectManager` 只包含兩個權限，建立與刪除專案的帳單連結（`gcloud iam roles describe roles/billing.projectManager` 列得出來），讀取帳單狀態不在裡面。〈函式〉那一節的程式在切斷之前先讀一次帳單狀態，只給這個角色時，那一步回 403「The caller does not have permission」。`roles/browser` 包含 `resourcemanager.projects.get`，整個角色是讀取專案、資料夾與組織的中繼資料以及專案 IAM policy 的六個權限，不包含讀取專案內資源（VM、儲存、資料庫）的權限。這兩個角色都綁在專案層級；停損開關要管多個專案時，每個專案各綁一次，或改綁在資料夾上。

### 函式

函式收到通知、判斷是否切斷、切斷之前確認帳單還在啟用。判斷規則只看實際花費：

```python
import base64
import json
import os

import functions_framework
from googleapiclient import discovery

PROJECT_ID = os.environ["TARGET_PROJECT_ID"]
PROJECT_NAME = f"projects/{PROJECT_ID}"

def should_disable(notification: dict) -> bool:
    # 只看實際花費：預測花費會因為一次短暫的尖峰就切斷正常的服務
    # 讀不懂的通知不構成停機的理由
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
    notification = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))
    print(json.dumps({"received": notification}))

    if not should_disable(notification):
        print(json.dumps({"action": "none"}))
        return

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

同一個目錄放一份 `requirements.txt`，列出 `functions-framework` 與 `google-api-python-client`。判斷規則是一個要自己決定的取捨：改看 `forecastThresholdExceeded` 會切得更早，對被濫用的情形損失更少，而一次正常的流量尖峰也可能讓整個專案停擺；改成「讀不懂就切斷」，格式變動時就會誤切。`should_disable` 現在的寫法是最保守的版本，適合先上線再調整。

部署時加 `--retry`：

```bash
gcloud functions deploy budget-killswitch --gen2 --region=<region> --runtime=python312 \
  --source=<source-dir> --entry-point=stop_billing --trigger-topic=budget-alerts \
  --service-account=budget-killswitch@<project-id>.iam.gserviceaccount.com \
  --set-env-vars=TARGET_PROJECT_ID=<project-id> --max-instances=1 --retry \
  --project=<project-id>
```

- `<region>`：函式所在的 region，例如 `asia-east1`；它與預算或要切斷的專案在哪個 region 無關。
- `<source-dir>`：放 `main.py` 與 `requirements.txt` 的本機目錄。
- `TARGET_PROJECT_ID`：要切斷帳單的專案。這裡填函式自己所在的專案；填別的專案時，服務帳號的兩個角色要綁在那個專案上。
- `--retry`：沒有這個旗標時，觸發器的重試政策是 `RETRY_POLICY_DO_NOT_RETRY`（`gcloud functions describe` 輸出的 `eventTrigger.retryPolicy`）。實測函式在讀取帳單狀態時拋出例外，Cloud Run 的請求紀錄卻是 HTTP 200，那則超出預算的通知被確認收訊（[ack](/backend/knowledge-cards/ack-nack/)）之後就不會再送，帳單照常計費。加上之後，失敗的通知會依觸發器的[重試政策](/backend/knowledge-cards/retry-policy/)重送，一次暫時性的錯誤（例如剛授予的權限還沒生效）不會讓那則通知消失。

### 觸發器呼叫函式的權限

```bash
gcloud run services add-iam-policy-binding budget-killswitch --region=<region> \
  --member=serviceAccount:budget-killswitch@<project-id>.iam.gserviceaccount.com \
  --role=roles/run.invoker --project=<project-id>
```

第二代的 Cloud Run functions 跑在 Cloud Run 上，Eventarc 觸發器以部署時指定的服務帳號身分呼叫它，而那個服務帳號預設沒有呼叫權限。缺這條綁定時，每一次推送都被 403 擋下，Cloud Run 的紀錄寫著「The IAM principal lacks {run.routes.invoke} permission」，函式一次都不會執行，而 `gcloud functions describe` 顯示的狀態仍是 `ACTIVE`。服務帳號因此有兩段權限要設：觸發器以它的身分呼叫函式，函式以它的身分呼叫 Cloud Billing API。

## 上線前的驗收：用測試訊息觸發一次

停損開關平常不動作，壞掉與「還沒輪到它動作」在任何狀態欄上都長得一樣；上面三項設定（呼叫權限、讀取帳單狀態的角色、重試）實測時各自讓它在狀態顯示正常時失效過一次。所以部署成功不算完成，驗收是對真實的 topic 發測試訊息，看終點的帳單狀態。

先發一則低於預算的訊息，確認函式收得到、判斷為不切斷：

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 15.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 函式的判斷結果記在 Cloud Run 的紀錄裡，預期是 none
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="budget-killswitch" AND jsonPayload.action:*' \
  --freshness=10m --format="value(timestamp,jsonPayload.action)" --project=<project-id>
```

這一則只驗證了訊息送得到、判斷邏輯會跑；切斷要用到的兩個權限（讀取帳單狀態、解除帳單連結）一次都沒有行使。所以接著發一則超出預算的訊息，看帳單狀態變成停用：

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 350.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 預期 billingEnabled 變成 false、billingAccountName 變成空字串
gcloud billing projects describe <project-id>
```

測試訊息裡的 `budgetAmount` 只要小於 `costAmount` 就會觸發，與預算實際設定的金額無關。實測從發出超出預算的訊息到 `billingEnabled` 變成 `false` 約十三秒，所以停損開關整體的反應時間幾乎全部來自計費資料的延遲。驗收完用 `gcloud billing projects link <project-id> --billing-account=<billing-account-id>` 重新連結。

這次驗收會實際讓專案停擺，所以排在專案還沒有正式服務的時候、或能承受中斷的時段；之後每一次修改函式、角色或觸發器，都再做一次。只發低於預算的那一則不夠：實測補上呼叫權限之後，低於預算的訊息已經能讓函式執行並回報 `none`，而讀取帳單狀態的權限與重試設定這兩個問題，都是發出超出預算的訊息之後才出現的。

## 延伸閱讀：上限的理由、費用的歸因與防護機制的驗收

- → [開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)：〈Per-team 成本上限〉說明給每個團隊與環境設上限的理由，本篇是那個上限在 GCP 上的執行方式
- → [成本監控與告警](/operations/08-cost-management/cost-monitoring/)：警示響了之後靠資源標記定位是哪個團隊的哪類資源在漲；停損開關切斷之前，歸因決定要切哪一個專案
- → [平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)：停損開關、稽核紀錄與告警共用的驗收方法，以及「部署成功、狀態正常」為什麼不算驗收
- → [Service Account（服務帳號）](/infra/knowledge-cards/service-account/)：服務帳號的權限分成「它能做什麼」與「誰能以它的身分行事」兩邊，停損開關兩邊都要設
