---
title: "前端感測器設計"
date: 2026-06-20
description: "什麼行為值得埋感測器、每類感測器的實作方式、取樣策略和效能影響 — 和 auto-intercept 的被動攔截互補"
weight: 6
tags: ["monitoring", "sdk-design", "sensor", "frontend", "instrumentation", "sampling"]
---

感測器是 SDK 主動偵測使用者行為的元件。和 [自動攔截機制](/monitoring/03-sdk-design/auto-intercept/) 的被動攔截不同 — auto-intercept 攔截的是系統級事件（uncaught exception、unhandled rejection），感測器偵測的是業務級行為（使用者點了什麼、看了哪個畫面、操作花了多久）。兩者互補：auto-intercept 提供 error 和 lifecycle 的基礎層，感測器提供 event 和 metric 的業務層。

## 點擊/觸碰感測器

點擊感測器偵測使用者和 UI 元素的互動 — 按鈕點擊、連結觸碰、選單選擇。每次互動產生一個 event 類型的事件。

### 哪些元素值得追蹤

追蹤粒度的判斷依據是「這個互動是否對應一個有意義的使用者意圖」。

有意義的互動（值得追蹤）：提交表單、點擊導航按鈕、觸發功能操作（連線、配對、匯出）。這些互動對應使用者的明確意圖，是 [funnel 分析](/monitoring/08-business-analytics/funnel-analysis/) 的步驟候選。

低價值的互動（通常不追蹤）：滾動、hover、重複的相同操作（每秒多次的按鈕連按）。這些互動要麼太頻繁（滾動每秒觸發數十次），要麼不代表新的使用者意圖。

### 實作方式

**Web（JS/TS）**：在 document 層級用 event delegation 攔截 click 事件，過濾出帶 `data-track` attribute 的元素。開發者在需要追蹤的元素上加 `data-track="connect-button"`，感測器自動收集。不追蹤所有 click — 只追蹤被標記的。

**Flutter**：用 NavigatorObserver 或 custom GestureDetector wrapper。GestureDetector 包裝在需要追蹤的 widget 外層，onTap 觸發時送出事件。

### 效能影響

Event delegation 在 document 層級只有一個 listener，效能影響接近零。瓶頸在事件產生頻率 — 如果追蹤了高頻操作（每秒多次的滑動），事件進入 buffer 的速度可能超過 flush 的速度。用取樣控制（見本章末段）。

## 導航/路由感測器

導航感測器偵測使用者在不同畫面之間的切換 — page view、screen view、route change。每次切換產生一個 lifecycle 類型的事件。

### 平台差異

**Web SPA**：SPA 的 route 變換不觸發頁面載入，需要主動偵測 URL 變化。兩種偵測方式：

- History API 攔截：覆寫 `pushState` / `replaceState`，攔截 `popstate` 事件
- 框架層級 Hook：React Router 的 `useLocation`、Vue Router 的 `afterEach` guard

History API 攔截是 SDK 層的通用做法（不依賴框架）；框架 Hook 更精確但需要使用者整合（見 [JS/TS 平台](/monitoring/05-platform-adaptation/js-ts-platform/) 的 SPA 路由段）。

**Flutter**：用 `NavigatorObserver` 的 `didPush` / `didPop` / `didReplace` 回呼。每次路由變化自動觸發，不需要使用者在每個頁面手動埋點。

**Python CLI/Hook**：沒有「畫面切換」的概念。對應的 lifecycle 事件是 `hook.start` / `hook.complete` — 每個 Hook 執行視為一個「畫面」。

### 事件 schema

```json
{
  "type": "lifecycle",
  "name": "screen.view",
  "data": {
    "screen_name": "TerminalScreen",
    "previous_screen": "HomeScreen",
    "navigation_method": "push"
  }
}
```

`navigation_method`（push / pop / replace / go）記錄導航方式，和 [go vs push 的 UX 語意](/ux-design/05-navigation-patterns/go-push-semantics/) 對應。

## 錯誤邊界感測器

錯誤邊界感測器攔截元件級的 error — 和 auto-intercept 的全域 error 攔截互補。

### 和 auto-intercept 的職責分工

| 層級 | 機制                                                                 | 攔截什麼                                       |
| ---- | -------------------------------------------------------------------- | ---------------------------------------------- |
| 全域 | auto-intercept（`window.onerror` / `FlutterError.onError`）          | uncaught exception、未處理的 Promise rejection |
| 元件 | 錯誤邊界感測器（React ErrorBoundary / Flutter Widget error handler） | 元件渲染失敗、子樹 error                       |

全域攔截捕獲「逃逸到頂層的 error」，錯誤邊界捕獲「在元件層級就被攔住的 error」。如果一個 error 被元件的 ErrorBoundary 捕獲，它不會觸發 `window.onerror` — auto-intercept 看不到它。錯誤邊界感測器填補這個缺口。

### 實作方式

**React**：ErrorBoundary 元件的 `componentDidCatch` 回呼中呼叫 `monitor.error()`。

**Flutter**：在 Widget 層用 `ErrorWidget.builder` 或自訂的 error handling widget。

### 額外 context

錯誤邊界感測器比全域攔截多一個 context — 知道 error 發生在哪個元件（component name / widget name）。這個資訊在 error 的 data schema 中記錄為 `component` 欄位。

## 效能標記感測器

效能標記感測器量測操作的延遲和系統的渲染表現。產生 metric 類型的事件。

### Web Core Vitals

Web 平台用 `PerformanceObserver` API 自動收集三個核心指標：

- **LCP**（Largest Contentful Paint）：最大內容元素的載入時間
- **FID**（First Input Delay）：首次互動的延遲
- **CLS**（Cumulative Layout Shift）：累計佈局位移分數

```javascript
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    monitor.metric(`web.vitals.${entry.entryType}`, {
      value: entry.startTime || entry.value,
      url: location.pathname
    });
  }
}).observe({ type: 'largest-contentful-paint', buffered: true });
```

### Flutter frame timing

Flutter 用 `SchedulerBinding.addTimingsCallback` 偵測掉幀：

```dart
SchedulerBinding.instance.addTimingsCallback((timings) {
  for (final t in timings) {
    if (t.totalSpan > const Duration(milliseconds: 16)) {
      monitor.metric('render.frame_drop', {
        'build_ms': t.buildDuration.inMilliseconds,
        'raster_ms': t.rasterDuration.inMilliseconds,
      });
    }
  }
});
```

16ms 是 60fps 的單幀預算。超過代表掉幀。

### 自訂 duration 量測

業務操作的延遲用手動標記量測：

```dart
final stopwatch = Stopwatch()..start();
await connectToTerminal();
stopwatch.stop();
monitor.metric('terminal.connect.duration', {
  'duration_ms': stopwatch.elapsedMilliseconds,
});
```

## 輸入敏感度感測器

輸入敏感度感測器偵測使用者正在輸入敏感資料 — 密碼欄位、API key 輸入、信用卡號碼。這個感測器的責任是**觸發 redaction，而非記錄輸入內容**。

### 偵測邏輯

**Web**：偵測 `<input type="password">`、帶有 `autocomplete="cc-number"` 或 `data-sensitive` attribute 的欄位。當使用者 focus 這些欄位時，標記當前 session 進入「敏感輸入模式」— 後續的事件自動加嚴 [redaction](/monitoring/knowledge-cards/redaction/) 規則（例如暫停記錄按鍵事件）。

**Flutter**：偵測 `TextField` 的 `obscureText: true` 或 `enableIMEPersonalizedLearning: false`（見 [安全敏感輸入框的 IME 控制](/ux-design/03-input-mechanism/ime-security-checklist/)）。

### 不記錄的原則

輸入敏感度感測器偵測「使用者正在輸入敏感內容」這個事實，但不記錄輸入的內容本身。送出的事件只包含：

```json
{
  "type": "lifecycle",
  "name": "input.sensitive_mode.entered",
  "data": { "field_type": "password" }
}
```

## 取樣策略設計

感測器產生的事件量可能很大（效能標記每 30 秒一筆 × 活躍使用者數）。取樣控制事件量、避免 SDK 和 collector 的資源壓力。

### 三種取樣模式

**全收**：每筆事件都送出。適合事件量低且每筆都有價值的類型 — error（每筆都可能是新 bug）、lifecycle 狀態轉換（量低）、認證失敗（安全敏感）。

**百分比取樣**：隨機丟棄一定比例的事件。適合高頻的效能和行為事件。取樣率由 SDK config 控制：

```yaml
sensors:
  metric:
    render.frame_drop: { sampling: 0.1 }    # 只收 10%
    resource.memory: { sampling: 0.5 }       # 收 50%
  event:
    feature.*.used: { sampling: 1.0 }        # 全收
    click.*: { sampling: 0.1 }               # 只收 10%
```

百分比取樣的代價是低機率事件可能被漏掉（取樣 10% 時、發生 5 次的事件可能一次都沒收到）。

**條件取樣**：正常情況下取樣、特定條件下全收。適合「平時不需要全量但問題發生時需要完整資料」的場景。例：正常 session 取樣 10%、但 session 內發生 error 後、該 session 剩餘事件全收（error session 的完整 context 比正常 session 更有價值）。

### 取樣率的管理

取樣率可以從三個層級設定：

| 層級              | 設定方式                           | 適用場景                     |
| ----------------- | ---------------------------------- | ---------------------------- |
| SDK 本地 config   | 隨 app 版本部署                    | 固定的基線取樣率             |
| Collector 下發    | SDK 啟動時從 collector 取得 config | 動態調整、不需要重新部署 app |
| Feature flag 服務 | 整合 LaunchDarkly / Unleash        | 實驗期間對特定群組調整取樣   |

三個層級由上到下優先順序遞增 — feature flag 覆蓋 collector config、collector config 覆蓋本地 config。

## 下一步路由

- 動機驅動的事件設計（哪些動機需要哪些感測器） → [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)
- 感測器的啟停控制和生命週期 → [感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/)
- 被動攔截機制（和感測器互補） → [自動攔截機制](/monitoring/03-sdk-design/auto-intercept/)
- 安全敏感輸入的完整 checklist → [安全敏感輸入框的 IME 控制](/ux-design/03-input-mechanism/ime-security-checklist/)
