---
title: "Playwright 瀏覽器驗證流程"
date: 2026-06-19
description: "用 Playwright 驗證 web 版本的 UI 行為 — test 結構、selector 策略、和 widget test 的互補關係"
weight: 3
tags: ["testing", "playwright", "browser", "e2e", "web"]
---

Playwright 是瀏覽器自動化工具，在真實瀏覽器中執行 UI 操作並驗證結果。和 Flutter 的 widget test 不同，Playwright 操作的是瀏覽器中的 DOM 元素，驗證的是使用者在瀏覽器中實際看到的畫面。

## Playwright 和 widget test 的互補

Widget test 在 Flutter test framework 中執行，不需要瀏覽器，驗證的是 widget tree 的結構和狀態。Playwright 在真實瀏覽器中執行，驗證的是渲染後的 DOM 和視覺呈現。

| 維度     | Widget test            | Playwright                |
| -------- | ---------------------- | ------------------------- |
| 執行環境 | Flutter test framework | 真實瀏覽器（Chromium 等） |
| 驗證對象 | Widget tree 結構       | DOM 元素和視覺呈現        |
| 速度     | 毫秒級                 | 秒級                      |
| 穩定性   | 高（無瀏覽器差異）     | 中（瀏覽器行為差異）      |
| 適用場景 | 邏輯驗證、狀態覆蓋     | 視覺驗證、跨瀏覽器相容    |
| CSS 驗證 | 無法驗證 CSS 渲染      | 可以驗證 CSS 效果         |

兩者的分工：widget test 驗證「邏輯上正確」（該有的元素存在、該觸發的事件發生），Playwright 驗證「視覺上正確」（元素在正確的位置、顏色和大小符合設計）。

## Playwright test 的基本結構

```typescript
import { test, expect } from '@playwright/test';

test('terminal screen shows connection status', async ({ page }) => {
  await page.goto('http://localhost:8080');
  
  // 點擊連線按鈕
  await page.click('text=Connect Terminal');
  
  // 等待畫面轉換
  await page.waitForSelector('[data-testid="terminal-screen"]');
  
  // 驗證連線狀態顯示
  const status = page.locator('[data-testid="connection-status"]');
  await expect(status).toBeVisible();
});
```

### 三個位置的斷言

Playwright test 中的斷言放在三個位置，各自驗證不同的東西：

**假設斷言（test 開頭）**：驗證 test 的前置條件。頁面載入成功、初始狀態正確。如果假設斷言失敗，test 的後續結果不可信。

**行為斷言（操作之後）**：驗證 UI 操作的即時效果。點擊按鈕後 dialog 出現、表單提交後顯示成功訊息。

**互動斷言（流程結束）**：驗證完整操作流程的最終狀態。多步驟操作完成後畫面回到預期狀態。

## Selector 策略

Playwright 用 selector 定位 DOM 元素。Selector 的穩定性決定了 test 的維護成本。

### 推薦：data-testid

在 HTML 元素上加 `data-testid` 屬性，Playwright 用 `[data-testid="xxx"]` 定位。`data-testid` 不受 CSS class 改名、文字內容變更、DOM 結構調整影響。

```html
<button data-testid="connect-button">Connect Terminal</button>
```

### 可接受：文字內容

用 `text=Connect Terminal` 定位。在按鈕文字穩定的場景下可用，但多語系支援或文案調整時會斷。

### 避免：CSS selector

用 `.btn-primary` 或 `#main-content > div:nth-child(2)` 定位。CSS class 和 DOM 結構的改動頻率高，test 頻繁因無關變更而失敗。

## 和開發伺服器的整合

Playwright test 需要一個正在運行的 web 應用。整合方式：

**手動啟動**：開發者先啟動 dev server，再跑 Playwright test。適合本地開發。

**自動啟動**：Playwright 設定檔中指定 `webServer` 配置，Playwright 自動啟動 dev server，test 結束後自動停止。適合 CI。

```typescript
// playwright.config.ts
export default defineConfig({
  webServer: {
    command: 'npm run dev',
    port: 8080,
    reuseExistingServer: !process.env.CI,
  },
});
```

## 下一步路由

- 視覺比對 → [螢幕截圖比對](/testing/04-ui-automation/visual-regression/)
- 狀態覆蓋策略 → [Widget test 的狀態覆蓋策略](/testing/04-ui-automation/state-coverage-strategy/)
- 導航路徑 test → [導航路徑 test](/testing/04-ui-automation/navigation-path-test/)
