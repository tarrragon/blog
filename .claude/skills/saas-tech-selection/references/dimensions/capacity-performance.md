# Dimension：Capacity / Performance（容量假設與成本邊界）

本維度處理「系統撐多少、花多少錢、什麼時候會不夠」。觸發展開：可預期高峰活動、成本敏感、或規模假設首年破十萬用戶時進入；其餘場景本維度收斂成幾條底線 + tripwire 總表（見 scale-stage-triggers reference）。初始化階段的容量工作不是壓測 — 是把「容量假設」寫成數字、讓未來有東西可以對照。

---

## 訪談問題

| 問題                                                   | 為什麼問                                                         |
| ------------------------------------------------------ | ---------------------------------------------------------------- |
| 一個典型使用者一天產生多少 request / 多少資料？        | 用戶量級 × 單用戶用量 = 容量假設的第一個數字、之後所有規劃的分母 |
| 有沒有已知的高峰時刻（開賣、結算日、行銷活動）？       | 可預期高峰是唯一「事前準備收益確定」的容量投資                   |
| 月度基礎設施預算的天花板？超了誰會知道？               | 雲端費用是用出來才看到的、預算 alert 是防呆不是優化              |
| 哪個操作最貴（報表、匯出、批次）？跟線上流量搶資源嗎？ | 貴操作隔離（時段 / 資源池 / replica）是早期就能做的便宜決策      |

**反向問**：「帳單比預期多三倍、你會在第幾天發現？」— 多數團隊的答案是「月底」、預算 alert 把這個數字縮短到計費資料的延遲（通常是數小時、有時超過一天）。再追一句：「服務出錯或被濫用、一小時花掉一個月的預算，警示寄到之前已經花了多少？」— 答得出數字才知道需不需要支出停損。

---

## Day one 最小集

| 項目           | 最小實作                                                                                             |
| -------------- | ---------------------------------------------------------------------------------------------------- |
| 容量假設文件化 | 三個數字進決策記錄：預期 QPS（平均 / 高峰）、資料月增量、單 request 成本估算                         |
| 預算 alert     | 雲端帳單 alert 設在預算的 50% / 90% / 100% 三檔，另加一檔預測花費達 100%；確認通知寄到會被看到的信箱 |
| 連線池算術     | 池上限 × 實例數 ≤ DB 連線上限、寫進設定註解；加實例時這條算式是第一個檢查項                          |
| 資源上限       | container / VM 的記憶體上限、request body 上限、分頁上限 — 讓失控有邊界                              |

連線池是容量維度最早撞到的隱形牆：水平擴展加實例、每個實例帶自己的池、DB 連線數以乘法增長 — 在加第二台實例之前想過這件事、跟事故當下才發現、是兩種成本。

---

## 防護底線（non-negotiable）

1. **容量假設有數字**：「應該夠用」不是假設；數字錯了沒關係、有數字才有「偏離多少」可言。
2. **帳單有 alert**：預算超標要在天的尺度被發現、不是月的尺度。警示只通知、不停止扣款；需要硬上限時另建支出停損（見下方〈支出停損〉），而停損上線時要實際觸發過一次。
3. **連線池上限設定過、算式留痕**。
4. **失控有邊界**：單一 client / 單一 query / 單一上傳能消耗的資源有上限（與入口維度的 rate limit 共用實作）。

---

## 支出停損（spend kill switch：費用失控時自動停止計費）

預算 alert 只寄通知，不會停止扣款；雲端帳單的「支出上限」功能通常只涵蓋少數服務（GCP 的強制執行支出上限只涵蓋 Cloud Run、Cloud Run functions、Gemini API、Vertex AI 這類，Compute Engine 與 GKE 不在內），而且一個上限只涵蓋一個專案裡的一項服務、暫停到預算期間結束為止、持續性資源的固定費用不暫停。服務出錯（無限重試、遞迴觸發）或被濫用（盜用的 API key、被拿去挖礦的 VM）時，費用的增長速度可以遠快於人工處理，這時涵蓋所有服務的做法是**預算通知觸發程式、程式把專案從帳單帳戶解除連結**。

**決策點**：停損切下去，專案裡所有服務一起停擺，等於一次自己造成的全面停機；雲端文件另外警告停用帳單時資源可能被永久刪除。判斷的單位是專案，逐個專案問停機影響誰、資料能不能重建：停機沒有人受影響、資料都能重建（沙箱、只跑實驗的專案）→ 建停損；停機可以接受而資料不能遺失（共用 staging）→ 改成只停止花錢的資源（函式停 VM、MIG 縮到 0，同一條鏈只換函式與角色）；停機會影響使用者（正式服務，不論規模）→ 警示加即時限制（配額、最大執行個體數），或把高風險的工作負載拆到另一個專案再對那個專案建停損。

**GCP 的做法**（停損鏈已實測；`--filter-projects`、`--credit-types-treatment` 與恢復指令依 gcloud 說明，未實跑）：接停損的預算與一般預算警示分開建。範圍用 `--filter-projects=projects/<project>` 限定在要停用的那一個專案（不限定時 `costAmount` 是整個帳單帳戶的合計，別的專案的花費也會觸發停損），金額設成這個專案本期能承受的最高花費，而不是預期花費。帳戶有大額抵免時加 `--credit-types-treatment=exclude-all-credits`，否則抵免用完前花費接近 0、停損不會觸發。

```bash
# 預算通知送到 Pub/Sub topic；設定時會自動授權 billing-budget-alert@system.gserviceaccount.com 發布
gcloud pubsub topics create budget-alerts
# 接停損的預算另外建，不接到既有的帳戶層級警示預算上；一個 topic 只接一個預算，
# 好幾個預算共用一個 topic 時，任何一個超支都會讓接在 topic 上的每一個停損開關動作
gcloud billing budgets create --billing-account=<billing-account-id> --display-name=<name> \
  --budget-amount=<能承受的最高花費減掉延遲期間的花費><currency> --filter-projects=projects/<project> \
  --notifications-rule-pubsub-topic=projects/<project>/topics/budget-alerts --billing-project=<project>

# 停損程式的服務帳號：解除帳單連結用 billing.projectManager，讀取帳單狀態另外要 browser；
# --condition=None 讓專案裡已有條件式綁定時，非互動模式不會停下來要求選擇條件
gcloud projects add-iam-policy-binding <project> --member=serviceAccount:<sa> --role=roles/billing.projectManager --condition=None
gcloud projects add-iam-policy-binding <project> --member=serviceAccount:<sa> --role=roles/browser --condition=None

# 部署由 topic 觸發的 function；兩個服務帳號旗標都明確指定（--trigger-service-account 不給時，
# gcloud 的說明寫用 Compute Engine 預設服務帳號，實測卻沿用 --service-account，依版本而異）；
# --retry 讓失敗的那則通知會重送；--max-instances=1 讓多則通知依序處理、不並行送出解除連結的呼叫；
# --runtime、--entry-point、--source、--region 依程式填，TARGET_PROJECT_ID 是要停用的專案
gcloud functions deploy <name> --gen2 --trigger-topic=budget-alerts --service-account=<sa> \
  --trigger-service-account=<sa> --retry --max-instances=1 --set-env-vars=TARGET_PROJECT_ID=<project> \
  --runtime=<runtime> --entry-point=<function> --source=<dir> --region=<region>

# 觸發器以 --trigger-service-account 的身分呼叫 function，要給它呼叫權限，否則每次推送都 403
gcloud run services add-iam-policy-binding <name> --region=<region> --member=serviceAccount:<sa> --role=roles/run.invoker
```

程式的判斷規則：只看實際花費（通知裡的 `costAmount >= budgetAmount`），讀不懂的訊息不切斷；呼叫 Cloud Billing API 的 `projects.updateBillingInfo`、`billingAccountName` 給空字串就是解除連結。

**反應時間與限制**：停損限制的是損失的上限，帳單資料延遲期間已經發生的費用攔不下來（實測從超支訊息發出到停用約十幾秒，延遲幾乎都在訊息發出之前）。帳單停用期間資源清單回傳空的，空清單不代表資源已刪除，重新連結後留下的資源繼續計費，清理以重新連結後的清單為準。實際因為超支而停用之後，先調高預算金額或刪掉函式再重新連結，否則下一則通知會再停用一次。停損程式跑在被停用的專案上時，它自己也跟著停擺。

**驗收**：部署成功、狀態 `ACTIVE` 不算完成。`run.invoker`、`browser` 與 `--retry` 三項缺任何一個，停損都會在看似正常的狀態下失效。驗收分兩段，見 [protection-proves-itself-by-firing](../principles/protection-proves-itself-by-firing.md)：

1. **topic 之前**：等第一則真實的預算通知，查函式紀錄裡的 `received`，確認 `budgetDisplayName` 是接停損的預算、`costAmount` 與帳單報表上這個專案本期的費用相符（接近 0 而報表不是，就是抵免或範圍設錯）。
2. **topic 之後**：超出預算那一則會實際停用帳單、可能刪除資料，所以排在停機可以接受的時段做。專案有停用後不能遺失的資料時改用分段驗證：另部署一份換了函式名稱與 topic 的複本（例如 `budget-killswitch-test`、`budget-alerts-test`），`TARGET_PROJECT_ID` 指向可拋棄的空專案、兩個角色綁在那個空專案上，對複本的 topic 發訊息——沿用正式名稱會蓋掉正式函式，發到正式 topic 會停掉正式專案；正式專案只用 Policy Troubleshooter 確認函式的服務帳號持有 `resourcemanager.projects.deleteBillingAssignment` 與 `resourcemanager.projects.get`。先發低於預算的那一則（`gcloud pubsub topics publish budget-alerts --message='{"costAmount": <值>, "budgetAmount": <預算>}'`，`<值>` 低於 `<預算>`），確認函式紀錄有 `action=none`；再發 `<值>` 不低於 `<預算>` 的那一則，看到 `billingEnabled` 變成 `false`。最後用 `gcloud billing projects link <project> --billing-account=<billing-account-id>` 重新連結，連結完成才算驗收結束。

---

## 高峰活動 readiness（觸發時才展開）

可預期高峰（開賣、活動、結算）出現時、事前清單：

1. **流量模型**：高峰是平日的幾倍、持續多久、打在哪些路徑（通常集中在少數 endpoint）。
2. **逐層對照**：高峰路徑經過的每一層（LB、app、DB、第三方）各自的上限、最低的那層就是系統上限。
3. **降級預案**：超出上限時丟掉什麼保住什麼（排隊頁、關閉非核心功能、靜態化首頁）— 事前決定、不是事故當下即興。「先停哪些請求」的順序判斷標準（依到達類別 × 級別）與降級不可靜默的要求見事件流負載仲裁方法論（判斷標準）與 `event-flow-arbitration-design` skill（六步流程與範本，判斷標準的落地執行）、本清單只管預案的盤點。
4. **壓測**：上面三步做完才有壓測的意義 — 壓測驗證對照表、不是代替思考。

---

## 延後與 tripwire

| 可延後項                       | 建議重評條件                                                                                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 正式 load test                 | 首次可預期高峰前、或容量決策需要數字依據                                                                                                                                       |
| 自動擴縮                       | 流量波動大到人工調整跟不上、且 stateless 前提成立                                                                                                                              |
| 成本工程（右算規格）           | 月帳單成長率連續超過用戶成長率                                                                                                                                                 |
| 支出停損                       | 出現第一次費用異常、對外公開可計費的 API key 或端點、或專案開始跑沒有人值守的批次與自動擴縮                                                                                    |
| 連線池／worker pool 分池或擴容 | 仲裁器回報不可棄請求無法服務（等待型無法服務、或推送型延後至接收視窗填滿），判斷標準見事件流負載仲裁方法論〈讓步與卸載順序〉、套用流程見 `event-flow-arbitration-design` skill |

---

## 決策記錄要記什麼

容量假設三數字、預算與 alert 檔位、支出停損建或不建與理由（建的話記下合成觸發的日期與結果）、連線池算式、資源上限清單、防護底線段各條的狀態、高峰 readiness 的觸發承諾、連線池／worker pool 分池或擴容的觸發狀態（是否已收到仲裁器容量失敗訊號）。
