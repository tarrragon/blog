---
title: "Rule engine 設計"
date: 2026-06-19
description: "條件 → 動作 → 模板的三段式規則結構 — 讓 collector 從被動儲存變成主動回應"
weight: 4
tags: ["monitoring", "collector", "rule-engine", "alerting", "automation"]
---

Rule engine 是 collector 的主動處理層。事件寫入儲存後，rule engine 檢查事件是否匹配預定義的規則，匹配時執行對應的動作。沒有 rule engine 的 collector 是被動的資料倉庫 — 開發者需要主動查詢才能發現問題。Rule engine 讓 collector 能在問題發生時主動通知。

## 三段式規則結構

每條規則由三部分組成：條件（什麼事件觸發）、動作（觸發後做什麼）、模板（動作的內容格式）。

### 條件

條件定義「哪些事件匹配這條規則」。條件是事件欄位的過濾器 — 事件類型、事件名稱、屬性值的比較。

```json
{
  "condition": {
    "type": "error",
    "name": "terminal.connect.*",
    "severity": "fatal"
  }
}
```

條件支援的匹配方式：

- **精確匹配**：`"type": "error"` — 事件類型必須是 error
- **前綴匹配**：`"name": "terminal.connect.*"` — 事件名稱以 `terminal.connect.` 開頭
- **數值比較**：`"data.duration_ms": { "gt": 5000 }` — 持續時間超過 5 秒
- **組合條件**：多個欄位條件同時滿足（AND 邏輯）

### 動作

動作定義「條件匹配後做什麼」。常見的動作類型：

**通知**：發送訊息到指定管道（email、Slack webhook、Telegram bot、桌面通知）。

**寫 summary**：把匹配的事件摘要寫入 summary 檔案，供定期 review。和逐筆事件不同，summary 是聚合後的結果（例如「過去一小時有 15 個 terminal.connect.failed」）。

**觸發 webhook**：向外部 URL 發送 HTTP POST，讓其他系統可以接收事件並做進一步處理。

**執行腳本**：在 collector server 上執行預定義的 shell script。適合自動化回應（重啟服務、清理暫存檔、輪替 log）。執行腳本的安全風險需要控制 — 只允許白名單內的腳本。

### 模板

模板定義動作的內容格式。通知的訊息內容、webhook 的 request body — 用模板語法（Go template 或 mustache）把事件欄位填入。

```text
{{ .name }} 發生於 {{ .ts }}
嚴重度：{{ .data.severity }}
訊息：{{ .data.message }}
```

模板讓同一個動作類型適用不同的事件 — 不需要為每種事件寫不同的通知函式。

## 規則評估時機

### 即時評估

每個事件寫入後立即評估所有規則。適合需要即時回應的規則（fatal error 通知）。

即時評估的成本和規則數量成正比 — 100 條規則代表每個事件寫入後做 100 次條件匹配。規則數量在數十條以內時，評估時間可以忽略。

### 批次評估

定期（每分鐘、每小時）掃描一段時間內的事件，評估聚合類規則。適合基於統計的規則（「過去 5 分鐘 error 數量超過 10」「過去 1 小時某 endpoint 的 P95 回應時間超過 2 秒」）。

批次評估需要時間窗口的概念 — 規則條件中包含時間範圍和聚合函式（count、avg、max、percentile）。

### 混合策略

即時評估用於單一事件觸發的規則（fatal error → 立即通知），批次評估用於聚合觸發的規則（error rate 異常 → 定期檢查）。兩者可以共存。

## 規則管理

規則以 JSON 或 YAML 檔案儲存在 collector 的設定目錄中。新增、修改、刪除規則是編輯檔案 + 重新載入 collector（signal 或 API call）。

```yaml
rules:
  - name: fatal-error-notify
    condition:
      type: error
      data.severity: fatal
    action:
      type: slack
      webhook: https://hooks.slack.com/...
      template: "FATAL: {{ .name }} at {{ .ts }}"
```

規則檔案版本控制在 git 中，和 collector 的其他設定一起管理。規則變更歷史可追溯。

## Shell 執行的安全邊界

Rule engine 的「執行腳本」動作在 collector 主機上執行 shell command。這個能力和 collector 的認證狀態組合後產生不同的風險等級。

### 攻擊鏈

無認證模式下，攻擊者可以向 collector 的 `/v1/events` endpoint 注入偽造事件。如果偽造事件匹配了一條規則、且規則的動作是執行 free-form shell command，攻擊者等於取得了 collector 主機的命令執行權（RCE — Remote Code Execution）。

攻擊路徑：注入假事件 → 匹配 rule → 執行 shell → RCE。

### 防護措施

**Rule 定義不可透過 API 新增**。Rule 只能由管理員透過配置檔或 CLI 設定，collector 的 HTTP API 不提供 rule CRUD endpoint。攻擊者即使能注入事件也無法新增 rule — 但現有 rule 的條件如果太寬（例如 `type: error` 沒有進一步限定 name），偽造的 error 事件仍可能匹配。

**Shell command 使用 allowlist**。Rule 的 action 指定 command name（如 `restart-ttyd`），command 的實際路徑在配置檔的 allowlist 中定義。Rule 不接受 free-form shell string（如 `sh -c "rm -rf /"`）。

```yaml
# 配置檔
allowed_commands:
  restart-ttyd: /usr/local/bin/restart-ttyd.sh
  notify-slack: /usr/local/bin/notify-slack.sh

rules:
  - name: fatal-error-response
    condition:
      type: error
      data.severity: fatal
    action:
      type: command
      command: restart-ttyd  # 只接受 allowlist 中的 name
```

**無認證模式下的額外限制**。Collector 無認證時（同區網信任），建議禁用 command 類型的動作、只允許通知和 webhook。認證啟用後才解鎖 command 動作 — 認證確保只有授權的 SDK 實例能送事件，降低偽造事件觸發 rule 的風險。

## 下一步路由

- Collector 的完整架構 → [Collector 架構](/monitoring/04-collector/architecture/)
- 規模成長後的演進路徑 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- 事件的分類和命名 → [監控心智模型 四類事件](/monitoring/01-mental-model/four-event-types/)
