---
title: "Sentry Error Grouping 與 Fingerprinting 策略"
date: 2026-06-22
description: "說明 Sentry 預設 grouping 演算法、自訂 fingerprint rules、merge/unmerge 操作、grouping 不準的判讀與大量 unique errors 的治理"
weight: 10
tags: ["backend", "observability", "sentry", "error-tracking", "grouping"]
---

> 本文是 [Sentry](/backend/04-observability/vendors/sentry/) 的 vendor deep article，深化 overview「Issue grouping / fingerprint」段。初次接觸 Sentry 的讀者建議先讀 [Sentry 服務頁](/backend/04-observability/vendors/sentry/)。

## 問題情境

Error grouping 決定 Sentry 的使用體驗。Grouping 太粗（不同 bug 被合併成同一個 issue），團隊會漏掉新問題；grouping 太細（同一個 bug 被拆成數百個 issue），issue list 變成 noise。理解 Sentry 的 grouping 演算法跟自訂 fingerprint 機制，才能讓 issue list 反映真實的 bug 數量而非 error event 數量。

## 預設 Grouping 演算法

### Stack trace 為主

Sentry 的預設 grouping 策略以 exception type + stack trace 為核心。兩個 error event 會被歸到同一個 issue，如果它們的 exception type 相同、且 stack trace 的「相關 frame」相同。

「相關 frame」是 Sentry 的判定結果 — 它會過濾掉標準函式庫、框架內部 frame 跟已知 noise frame，只留下 application code frame。這個過濾邏輯叫 stack trace rules，由 Sentry 的 grouping 引擎自動決定。

### Grouping 版本

Sentry 的 grouping 演算法有多個版本（稱為 grouping config）。新建的 project 自動用最新版（截至 2024 年是 `newstyle:2023-01-11`），舊 project 可能還在用舊版。升級 grouping config 會改變 issue 的歸屬 — 之前合併的 event 可能被拆開，之前分開的可能合併。

確認目前的 grouping config：Project Settings → General Settings → Event Grouping。升級前先用 Sentry 的 grouping preview 功能測試影響範圍。

### 非 exception 事件

沒有 stack trace 的事件（`capture_message`、breadcrumb-only event、CSP violation）用 message 內容做 grouping。相同 message template 的事件歸到同一個 issue。

message 中如果包含動態值（user ID、request ID、timestamp），Sentry 會嘗試辨識並忽略動態部分。但辨識不完美 — 如果 message 格式不一致，同一種錯誤可能被拆成多個 issue。

## 自訂 Fingerprint

### 何時需要自訂

預設 grouping 不夠用的常見場景：

| 場景                      | 問題                                        | Fingerprint 解法                               |
| ------------------------- | ------------------------------------------- | ---------------------------------------------- |
| 外部 API timeout          | 不同 caller 的 stack trace 不同，但根因相同 | 用 `{{ default }}` + error type 做 fingerprint |
| Database connection error | 每個 query 的 stack trace 不同              | 用 error message pattern 做 fingerprint        |
| 前端 minified code        | source map 缺失導致 frame 不穩定            | 先修 source map 上傳，而非硬 fingerprint       |
| Rate limit / 429 error    | 大量 429 拆成數百個 issue                   | 用 HTTP status code 做 fingerprint             |

### Server-side fingerprint rules

在 Project Settings → Issue Grouping → Fingerprint Rules 設定。語法：

```text
# 所有 ConnectionError 歸成一個 issue
error.type:ConnectionError -> connection-error

# 特定 message pattern 歸成一個 issue
message:"Rate limit exceeded*" -> rate-limit

# 特定 module 的所有 error 歸成一組
module:payment.gateway.* -> payment-gateway-error

# 組合條件
error.type:TimeoutError module:external.api.* -> external-api-timeout
```

Server-side rules 的優先順序：越後面的 rule 優先順序越高。如果一個 event 匹配多條 rule，用最後一條。

### SDK-side fingerprint

在 SDK 的 `before_send` callback 中設定 `event.fingerprint`：

```python
def before_send(event, hint):
    if "ConnectionError" in str(hint.get("exc_info", "")):
        event["fingerprint"] = ["connection-error"]
    return event

sentry_sdk.init(dsn="...", before_send=before_send)
```

SDK-side 跟 server-side 的差異：

| 面向     | Server-side rules       | SDK-side fingerprint |
| -------- | ----------------------- | -------------------- |
| 設定位置 | Sentry Web UI           | 程式碼               |
| 部署速度 | 即時生效                | 需要 deploy          |
| 可見性   | 團隊都能看到跟修改      | 散在程式碼裡         |
| 複雜邏輯 | 只支援 pattern matching | 可用任意程式邏輯     |

優先用 server-side rules — 集中管理、即時生效。SDK-side 用在 server-side rules 表達不了的複雜邏輯。

### `{{ default }}` 組合

Fingerprint 中的 `{{ default }}` 代表 Sentry 預設的 grouping 結果。跟自訂值組合使用：

```text
# 用預設 grouping + environment 維度拆分
fingerprint: ["{{ default }}", "{{ environment }}"]
```

這樣同一個 bug 在 staging 跟 production 會分成兩個 issue，方便分別追蹤。

## Merge 與 Unmerge

### 事後修正

當 grouping 不準時，Sentry 提供事後修正：

**Merge**：選擇多個 issue，合併成一個。合併後的 issue 保留所有 event，但只保留一個 issue ID。適合預設 grouping 太細（同一 bug 被拆成多個 issue）的情況。

**Unmerge**（拆分）：從一個 issue 中選擇部分 event，拆出成新 issue。適合預設 grouping 太粗（不同 bug 被合在同一個 issue）的情況。

### Merge/Unmerge 的限制

Merge 跟 Unmerge 都是「貼 OK 繃」— 只影響現有 event，新進的 event 仍然用原來的 grouping 邏輯。如果根因是 grouping 太粗或太細，應該修 fingerprint rule，而非持續 merge/unmerge。

判讀順序：

1. 發現 grouping 不準
2. 先用 merge/unmerge 處理現有 issue（止血）
3. 分析 root cause — 是 stack trace 不穩定、message 有動態值、還是缺 fingerprint rule
4. 加 fingerprint rule 永久修正
5. 驗證新進 event 的 grouping 是否正確

## Grouping 不準的判讀

### 太細的訊號

- Issue list 中出現大量「相似標題但不同 ID」的 issue
- 單一事件只有 1-2 個 occurrence 的 issue 大量出現
- 同一個使用者操作觸發的 error 被分散到多個 issue

常見原因：message 中包含動態值（user ID、timestamp、request path）、source map 缺失（前端）、stack trace 包含 generated code frame。

### 太粗的訊號

- 一個 issue 的 event 數量持續增長，但 event detail 看起來是不同問題
- Issue 的 status 被 resolve 後馬上 regress，但新 event 跟原因不同
- 團隊 ignore 了一個「雜 issue」但裡面混著真正需要處理的 bug

常見原因：exception type 太通用（`RuntimeError`、`Exception`）、fingerprint rule 太粗（把整個 module 的 error 合成一個 issue）。

## 大量 Unique Errors 的治理

### 問題：Issue 爆量

project 的 issue 數量超過數千時，issue list 失去可操作性。on-call 打開 Sentry 看到 2000 個 unresolved issue，等於沒有 triage。

### 治理策略

**Inbound filter**：在 Project Settings → Inbound Filters 設定，丟棄已知的 noise event（browser extension error、crawler error、legacy browser error）。丟棄在 ingestion 層，不消耗 quota。

**Rate limit**：project 或 key 級別的 rate limit。超過限額的 event 被丟棄。適合防止單一 bug 的暴增 event 耗盡 quota，但不解決 issue 數量問題。

**Alert rule 搭配 ownership**：用 Sentry alert rule 把特定 tag（service、team、module）的新 issue 通知對應 team。不是所有 issue 都要同一個人看。

**定期 triage cadence**：每週或每兩週的 triage session，把 issue 分成 fix / ignore / merge 三類。Sentry 的 `For Review` tab 自動列出需要初次 triage 的 issue。

**Auto-resolve**：設定 auto-resolve policy — 超過 N 天沒有新 event 的 issue 自動 resolve。避免舊 issue 永遠佔據 unresolved list。

### 治理後的穩態

合理的穩態是：unresolved issue 數量穩定在數十到數百，每週新增 issue 跟 resolve issue 數量大致平衡。如果 unresolved 持續增長，先檢查是否有 noise event 沒被 filter，或 fingerprint 太細。

## 整合與下一步

- Error tracking 跟 observability 的邊界：Sentry 處理 error lifecycle、metrics/logs/traces 處理系統行為，見 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- OTel context 整合：Sentry SDK 接受 OTel trace_id / span_id，讓 error 跟 trace 關聯，見 [OpenTelemetry Collector 部署模式](/backend/04-observability/vendors/opentelemetry/collector-deployment-patterns/)
- Release tracking 跟 session replay：見 [Release Tracking 與 Session Replay](../release-tracking-session-replay/)
- 事故響應整合：嚴重 issue → alert → on-call，見 [08 Incident Response 模組](/backend/08-incident-response/)
