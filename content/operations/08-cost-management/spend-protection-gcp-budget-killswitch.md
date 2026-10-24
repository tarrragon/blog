---
title: "GCP 上的雲端費用失控防護：預算警示、強制執行支出上限與自動停用帳單的作用範圍、反應時間、建置與驗收"
date: 2026-10-24
description: "GCP 上為費用失控設防的機制：預算警示寄出通知的時機、範圍與幣別、強制執行支出上限涵蓋的服務與暫停期間，以預算通知觸發函式把專案從帳單帳戶解除連結的建置步驟、權限與重試設定，帳單資料延遲對這些機制反應時間的影響，以及這個函式上線前用測試訊息觸發的驗收"
weight: 6
tags: ["devops", "cost-management", "gcp", "budget", "kill-switch", "security"]
---

這篇整理在 GCP 上為費用失控設防的做法，範圍從專案已經連結到一個帳單帳戶開始。[開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)的〈Per-team 成本上限〉說明了為什麼要給團隊與環境設一個費用的上限；這一篇處理那個上限在 GCP 上由哪些機制執行、每一個機制在費用超過門檻時實際做了什麼，以及從費用發生到它動作之間隔了多久。三個機制分別是預算警示（花費達門檻時寄通知）、強制執行支出上限（暫停指定服務的新用量）與自動停用帳單（由程式把專案從帳單帳戶解除連結）。文中的指令與觀察來自 2026 年 10 月在一個 GCP 測試專案上的實跑；主控台的選項與服務清單會變動，以操作當下看到的為準。

## 費用失控的來源與反應時間

費用失控指的是費用增加的速度快過人發現它、處理它的速度。來源分成兩類，兩類的處置方式不同：

- **服務自己出錯**：程式對失敗的請求無限重試、一個事件觸發的函式又產生同一種事件而形成遞迴、自動擴縮的上限設得太高。費用花在自己的服務上，修好程式就停。
- **資源被別人濫用**：外洩的 API 金鑰（API key）被拿去呼叫付費 API、被入侵的 VM 被拿去挖礦。費用花在別人的用途上，處理的人要先切斷對方能用的資源，再處理入侵。

兩類的共同難處在時間：費用從發生到任何機制動作，中間隔著一段延遲。一個防護機制從費用發生到動作，要經過三段：雲端把用量算成費用、寫進帳單資料；帳單資料觸發通知；通知觸發處置（人或程式）。把用量算成費用那一段的延遲由雲端決定，GCP 的帳單主控台寫著費用資料要數小時後才會顯示、有時超過 24 小時。實測時一個專案已經跑過幾個小時的 VM、Windows VM 與一個 GKE 叢集，同一時間送到的預算通知裡，`costAmount`（本期累計花費）仍然是 `0.0`。這個數字偏低還可能有第二個原因：那個預算用的是預設的抵免設定，花費是扣掉帳戶上全部抵免之後的金額，所以這次觀察分不出 `0.0` 來自延遲還是抵免。

預算警示與自動停用帳單讀的是帳單資料，反應時間至少是這段延遲。強制執行支出上限依的是 GCP 估算的費用，Cloud Billing 文件說它比帳單報表上的費用快得多，但仍不是即時，延遲期間超出的部分照常計費。所以強制執行支出上限與自動停用帳單能讓費用停止增加，而停下來時的總額是門檻加上延遲期間已經發生的費用；預算警示本身不停止任何用量，費用停在哪裡取決於收到通知的人多快處理。

要在費用發生的當下限制它，得靠不經過帳單資料的限制：API 的配額、[速率限制（rate limit）](/backend/knowledge-cards/rate-limit/)、API 金鑰的使用範圍（限定可呼叫的 API 與來源），以及服務的擴縮上限（例如 Cloud Run 的 `--max-instances`、MIG 的最大台數）。金鑰被盜用時，先撤銷或限制那一把金鑰，影響範圍比停用整個專案的帳單小。

## 預算警示：門檻依據、範圍、建立指令與通知對象

預算（budget）是掛在帳單帳戶上的一組門檻：本期花費達到預算的某個比例時，GCP 寄通知給帳單帳戶的管理員。門檻有兩種依據，**實際花費**（已經寫進帳單資料的費用）與**預測花費**（GCP 依目前的速度推估到期末的費用）；預測花費的門檻通常比實際花費的門檻早觸發，代價是一次短暫的尖峰也可能觸發預測花費的門檻。預算只寄通知，扣款照常進行。

建立預算的人在帳單帳戶上要有能管理預算的角色（帳單帳戶管理員或帳單帳戶費用管理員）；只有專案擁有者、而帳單帳戶屬於別人時，這一步回 403，要請帳單帳戶的管理員建立或授予角色。下面的指令把範圍限定在一個專案，門檻設在實際花費的 50%、90%、100%，另加一個預測花費達 100% 的門檻：

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
- `--filter-projects`：預算只計算這些專案的花費。不給這個旗標時，預算涵蓋整個帳單帳戶的所有專案，通知裡的 `costAmount` 是所有專案的合計；一個帳單帳戶下有好幾個專案時，別的專案的花費也會讓它越過門檻，而這個專案自己的超支被合計稀釋。
- 門檻比例：50% 與 90% 留給收到通知的人處理的時間，100% 對齊花費達到預算的那一刻，預測花費的門檻提早反映速度異常；比例依處理一次所需的時間自己調整。
- `--billing-project`：gcloud 呼叫預算 API 所用的專案，不影響預算的範圍。

通知會寄給帳單帳戶的管理員與帳單使用者，所以要確認這些帳號的信箱有人在看。預算另外可以把通知送到一個 Pub/Sub 主題（topic），自動停用帳單就是從這個主題接收通知。

## 強制執行支出上限：涵蓋的服務、範圍與暫停期間

在帳單主控台的「Budgets & caps」頁面建立預算時，表單裡有一個「強制執行支出上限（適用於某些服務）」的選項：花費達到上限時，GCP 暫停表單裡選定的那個專案、那一項服務的新用量，直到這個預算期間結束（以月為期的預算是到月底，下一期自動重設）或有人手動解除為止。它是帳單功能裡不必自己寫程式就能暫停用量的機制，範圍有三個限制：

- **一個上限只涵蓋一個專案裡的一項服務**：要保護多項服務，就每項各建一個。
- **只涵蓋清單上的服務**：2026 年 10 月建立表單時列出的是 Cloud Run、Cloud Run functions、Gemini API 與 Vertex AI 四項，Compute Engine 與 GKE 不在清單上。表單的服務下拉選單就是涵蓋清單，建立之前打開看一次。
- **持續性資源的固定費用不暫停**：Cloud Billing 文件說明，與持續性資源綁在一起的固定用量不會被暫停，執行也有延遲，超出的部分照常計費。

工作負載跑在清單上的服務時，這個選項不必寫程式；它暫停的是這項服務的新用量，所以對正式服務同樣是一次停機，只是範圍限於這一項服務，要不要建用〈自動停用帳單〉那一節的兩種代價判斷。跑在 VM 或 Kubernetes 上時，帳單功能裡能停止用量的只剩自動停用帳單。

## 自動停用帳單：解除帳單連結的機制、適用的專案與停用期間的資源

自動停用帳單的做法是讓預算通知觸發一段程式，由程式呼叫 Cloud Billing API 把專案從帳單帳戶解除連結。專案沒有連結帳單帳戶時，GCP 停止專案裡所有的服務（包括免費方案的服務），費用也就停止增加。這段程式在下文稱為**停損開關**（kill switch）。

```text
預算（帳單帳戶）── 通知 ──> Pub/Sub 主題 ── 推送 ──> Eventarc 觸發器 ── 呼叫 ──> Cloud Run functions 函式 ── updateBillingInfo ──> 專案的帳單連結被移除
```

建置之前先決定要不要建，因為停損開關的效果是一次自己造成的全面停機：VM、資料庫、函式、Kubernetes 叢集一起停擺，停損開關本身跑在同一個專案時也跟著停（實測解除連結之後，查詢函式狀態的 API 直接回 403，訊息要求確認帳單帳戶）。Cloud Billing 文件另外警告，停用帳單時資源可能被永久刪除，也不保證服務能恢復，所以這是一次可能遺失資料的停機。判斷方式是比較兩種代價：「被濫用或程式出錯而多付一筆費用」與「這個專案的服務全部停止、資料可能遺失」，哪一個比較高。

- **停機時沒有人受影響、而且專案裡的資料都能從別處重建**（只跑實驗的專案、個人的沙箱多半是這樣）：多付的費用沒有上限，建停損開關。
- **停機會影響使用者或同事，或專案裡有重建不了的資料**（正式服務、團隊共用的 staging）：全面停機的代價通常高於一段時間的超支，改用預算警示加值班處理。要建的話，只建在風險集中的專案上，例如 API 金鑰寫在網頁或 App 裡、任何人都拿得到的專案；停損開關停掉這個專案時，正式服務裡用這把金鑰的功能也會一起停，所以正式服務的其餘部分與正式服務的資料放在另一個專案。

實測停用約兩分半鐘再重新連結，Cloud Router、Cloud NAT、函式與它的觸發器都還在、設定沒變；這次沒有觀察 VM 與資料庫。停用期間 `gcloud compute routers list` 回傳零筆，而重新連結之後 Cloud Router 仍在，所以停用期間的空清單不代表資源已經刪除；重新連結之後仍存在的資源會繼續計費，清理時以重新連結之後列出的清單為準。專案停用之後 GCP 如何處理其中的資源，以 Cloud Billing 文件中停用帳單的說明為準。

## 停損開關的建置：主題、服務帳號的角色、函式與觸發器的呼叫權限

停損開關的建置有四個元件：接收通知的 [Pub/Sub](/backend/knowledge-cards/pub-sub/) 主題、執行函式的[服務帳號](/infra/knowledge-cards/service-account/)、函式本身，以及觸發器呼叫函式的權限。服務帳號的角色、函式的重試設定與觸發器的呼叫權限，任何一項設錯，部署指令都回報成功、函式狀態都顯示 `ACTIVE`，停損開關卻不會解除帳單連結。

下面的指令用到三個自己取的名稱：主題 `budget-alerts`、服務帳號 `budget-killswitch-sa`、函式 `budget-killswitch`。換成別的名稱時，同一個名稱出現的每一條指令都要一起換。`<project-id>` 指的是放停損開關、同時也是要被停用帳單的那個專案；兩者分開的情形見〈部署函式〉的 `TARGET_PROJECT_ID`。

這裡用的預算要與〈預算警示〉那一節不同：函式在本期累計花費達到預算金額時解除連結，所以接停損開關的預算，金額要設成這個專案本期能承受的最高花費，範圍用 `--filter-projects` 限定在這一個專案；要依預期花費收通知，另建一個不接主題的預算。

### 接收通知的主題

主題是預算通知與函式之間的接點：預算把通知發布到主題，Eventarc 觸發器從主題取出通知、呼叫函式。

```bash
gcloud services enable pubsub.googleapis.com cloudfunctions.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com eventarc.googleapis.com \
  cloudbilling.googleapis.com --project=<project-id>

# 建立主題，並讓預算把通知送過來
gcloud pubsub topics create budget-alerts --project=<project-id>
gcloud billing budgets update <budget-resource-name> \
  --notifications-rule-pubsub-topic=projects/<project-id>/topics/budget-alerts \
  --billing-project=<project-id>
```

`<budget-resource-name>` 是 `gcloud billing budgets list --billing-account=<billing-account-id> --billing-project=<project-id> --format="value(name)"` 印出的完整名稱，形如 `billingAccounts/<id>/budgets/<uuid>`，與建立時給的顯示名稱是兩個值。設定通知目標時，GCP 會自動讓預算服務的系統帳號 `billing-budget-alert@system.gserviceaccount.com` 擁有這個主題的發布權限，`gcloud pubsub topics get-iam-policy budget-alerts --project=<project-id>` 看得到這條綁定。

預算接上主題之後，GCP 一天會送好幾次通知過來，不論花費有沒有越過門檻。實測接上後約十三分鐘收到第一則；Cloud Billing 文件說第一則可能要數小時。通知的內容如下，`alertThresholdExceeded` 這類欄位要等越過門檻才會出現：

```json
{"budgetDisplayName": "<budget-display-name>", "costAmount": 0.0, "costIntervalStart": "2026-10-01T07:00:00Z",
 "budgetAmount": 320.0, "budgetAmountType": "SPECIFIED_AMOUNT", "currencyCode": "TWD"}
```

帳戶上有大額抵免額度時，預設設定下 `costAmount` 在抵免用完之前都接近 0，停損開關不會觸發。要讓抵免消耗也算進門檻，建立預算時加 `--credit-types-treatment=exclude-all-credits`，花費就以抵免前的金額計算。

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

這兩個角色都綁在專案層級。函式只停用 `TARGET_PROJECT_ID` 這一個專案，所以要管多個專案時，每個專案各建一個限定在該專案的預算與一個函式部署，角色在每個專案各綁一次，或綁在它們共同的資料夾上。

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

同一個目錄放一份 `requirements.txt`，列出 `functions-framework` 與 `google-api-python-client`。判斷規則是一個要自己決定的取捨：改看 `forecastThresholdExceeded` 會更早解除連結，對被濫用的情形損失更少，而一次正常的流量尖峰也可能讓整個專案停擺；改成「讀不懂就解除連結」，通知格式變動時就會誤停。`should_disable` 現在的寫法在誤停那一側最保守：只有實際花費確實達到預算才停，代價是被濫用時要等到實際花費寫進帳單資料才動作。它適合先上線再依自己的情形調整。

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
- `--trigger-service-account`：Eventarc 觸發器呼叫函式時的身分。`gcloud functions deploy --help` 寫著不給這個旗標時用專案的 Compute Engine 預設服務帳號，而這次實測不給時，觸發器用的是 `--service-account` 那一個；預設值會隨版本變動，所以明確指定，部署後用 `gcloud functions describe budget-killswitch --region=<region> --project=<project-id>` 輸出的 `eventTrigger.serviceAccountEmail` 確認。
- `TARGET_PROJECT_ID`：要停用帳單的專案。這裡填函式自己所在的專案；填別的專案時，〈服務帳號的角色〉的兩條 `add-iam-policy-binding` 改成綁在那個專案上，預算的 `--filter-projects` 也改成那個專案，其餘指令的 `<project-id>` 不變。
- `--max-instances=1`：Cloud Run 對這個函式同一時間最多只啟動一個執行個體。超支之後預算一天會送來好幾則通知，限制成一個讓它們依序處理，不會同時送出多個解除連結的呼叫；重試不斷發生時，函式本身同時佔用的執行個體也只有一個。
- `--retry`：沒有這個旗標時，觸發器的重試政策是 `RETRY_POLICY_DO_NOT_RETRY`（`gcloud functions describe` 輸出的 `eventTrigger.retryPolicy`）。實測函式在讀取帳單狀態時拋出例外，Cloud Run 的請求紀錄卻是 HTTP 200，Pub/Sub 因此把那則超出預算的通知標為已確認收訊（[ack](/backend/knowledge-cards/ack-nack/)），之後不再送，帳單照常計費。加上之後，Pub/Sub 會依觸發器的[重試政策](/backend/knowledge-cards/retry-policy/)重送失敗的通知，一次暫時性的錯誤（例如剛授予的權限還沒生效）不會讓那則通知消失。重試會持續到成功或訊息超過保留期限為止，權限少了一個這類不會自己恢復的錯誤也會一直重試而不會解決，所以重試設定要配合〈上線前的驗收〉。

### 觸發器呼叫函式的權限

第二代的 Cloud Run functions 跑在 Cloud Run 上，Eventarc 觸發器以 `--trigger-service-account` 指定的服務帳號身分呼叫它，而那個服務帳號預設沒有呼叫權限。缺這條綁定時，Cloud Run 以 403 擋下每一次推送，紀錄寫著「The IAM principal lacks {run.routes.invoke} permission」，函式一次都不會執行，而 `gcloud functions describe` 顯示的狀態仍是 `ACTIVE`：

```bash
# 第一個 budget-killswitch 是函式名稱：第二代函式在 Cloud Run 上的服務與函式同名
gcloud run services add-iam-policy-binding budget-killswitch --region=<region> \
  --member=serviceAccount:budget-killswitch-sa@<project-id>.iam.gserviceaccount.com \
  --role=roles/run.invoker --project=<project-id>
```

所以這個服務帳號有兩段權限要設：觸發器以它的身分呼叫函式，函式以它的身分呼叫 Cloud Billing API。

## 上線前的驗收：低於預算與超出預算的兩則測試訊息

停損開關平常不動作，壞掉與「還沒輪到它動作」在任何狀態欄上都長得一樣；呼叫權限、讀取帳單狀態的角色與重試這三項設定，實測時各自讓它在狀態顯示正常時失效過一次。所以部署成功不算完成，驗收是對真實的主題發測試訊息，看呼叫鏈最後一段的結果：專案的帳單狀態。這是[平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)的一個應用。

兩則訊息走的是函式的兩條分支。低於預算的那一則確認訊息送得到、判斷邏輯會跑；它要排在超出預算那一則之前，因為超出預算那一則會讓專案連同函式一起停擺，之後就沒有東西能接收低於預算的那一則：

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 15.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 等一兩分鐘再查：紀錄寫入有延遲；預期 action 是 none；--freshness=10m 只看最近十分鐘
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="budget-killswitch" AND jsonPayload.action:*' \
  --freshness=10m --format="value(timestamp,jsonPayload.action)" --project=<project-id>
```

低於預算的訊息在判斷規則那一步就結束，解除連結要用到的兩個權限（讀取帳單狀態、解除帳單連結）一次都沒有行使。超出預算的那一則才會走到它們，結果看帳單狀態：

```bash
gcloud pubsub topics publish budget-alerts --project=<project-id> \
  --message='{"costAmount": 350.0, "budgetAmount": 320.0, "currencyCode": "TWD"}'

# 等一兩分鐘再查；預期 billingEnabled 變成 false、billingAccountName 變成空字串
gcloud billing projects describe <project-id>
```

測試訊息裡的 `budgetAmount` 大於 0、而且不大於 `costAmount` 時，函式就會解除帳單連結，與預算實際設定的金額無關。實測從發出超出預算的訊息到 `billingEnabled` 變成 `false` 約十三秒，所以停損開關整體的反應時間幾乎全部來自帳單資料的延遲。驗收完用 `gcloud billing projects link <project-id> --billing-account=<billing-account-id>` 重新連結。

實際因為超支而停用之後，`costAmount` 是本期累計值，整個預算期間都不會降回預算以下；只重新連結的話，下一則預算通知會讓函式再解除一次。所以恢復服務的順序是先調高預算金額（`gcloud billing budgets update <budget-resource-name> --budget-amount=<amount><currency-code> --billing-project=<project-id>`）或刪掉函式，再重新連結。

這次驗收會實際讓專案停擺，所以排在專案還沒有正式服務的時候、或能承受中斷的時段；之後每一次修改函式、角色或觸發器，都再做一次。實測補上呼叫權限之後，低於預算的訊息已經能讓函式執行並回報 `none`，而讀取帳單狀態的權限與重試設定這兩項缺漏，都是發出超出預算的訊息之後才出現的。別人調整了角色（例如權限盤點時收掉 `roles/browser`）的時候，部署的人不會知道要重驗，所以可以在函式的紀錄上另設一個告警：預算一天會送好幾則通知，超過一天沒有出現帶 `action` 欄位的紀錄就通知，讓函式停止收到通知這件事本身也成為訊號。

## 延伸閱讀：上限的理由、費用的歸因、防護機制的驗收與服務帳號的兩邊權限

- → [開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)：〈Per-team 成本上限〉說明給每個團隊與環境設上限的理由，本篇是那個上限在 GCP 上的執行方式
- → [成本監控與告警](/operations/08-cost-management/cost-monitoring/)：收到預算警示之後，靠資源標記定位是哪個團隊的哪類資源在漲；停損開關解除連結之前，要依歸因的結果選定是哪一個專案
- → [平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)：停損開關、稽核紀錄與告警共用的驗收方法，以及「部署成功、狀態正常」為什麼不算驗收
- → [Service Account（服務帳號）](/infra/knowledge-cards/service-account/)：服務帳號的權限分成「它能做什麼」與「誰能以它的身分行事」兩邊，停損開關的角色與部署者的 `serviceAccountUser` 各屬一邊
