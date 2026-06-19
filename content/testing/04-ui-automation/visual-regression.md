---
title: "螢幕截圖比對"
date: 2026-06-19
description: "Visual regression testing — 用螢幕截圖比對偵測非預期的視覺變化、baseline 管理和 diff 閾值設定"
weight: 4
tags: ["testing", "visual-regression", "screenshot", "playwright", "ui-test"]
---

螢幕截圖比對（visual regression testing）用基準截圖（baseline）和當前截圖的像素差異來偵測非預期的視覺變化。這一層驗證的是「畫面看起來是否和上次一樣」，捕捉 CSS 變更、layout 偏移、字體替換等邏輯 test 無法發現的視覺問題。

## 運作方式

### 建立 baseline

第一次執行時擷取每個測試畫面的螢幕截圖，儲存為 baseline。Baseline 代表「目前正確的視覺狀態」。

### 比對差異

後續執行時擷取當前截圖，和 baseline 逐像素比對。差異超過閾值時 test 失敗，產出 diff 圖片標示差異區域。

### 更新 baseline

視覺變更是刻意的（新設計、改佈局）時，用新截圖覆蓋 baseline。更新 baseline 是明確的決策 — 代表「新的視覺狀態是正確的」。

## Playwright 的截圖比對

Playwright 內建 `toHaveScreenshot()` 方法：

```typescript
test('terminal screen matches baseline', async ({ page }) => {
  await page.goto('http://localhost:8080/terminal');
  await page.waitForSelector('[data-testid="terminal-screen"]');
  
  await expect(page).toHaveScreenshot('terminal-connected.png', {
    maxDiffPixelRatio: 0.01,  // 允許 1% 像素差異
  });
});
```

首次執行時自動建立 baseline 截圖，後續執行時自動比對。Diff 圖片儲存在 test results 目錄。

## Diff 閾值設定

像素比對的閾值影響 test 的敏感度：

**過低（0.001）**：anti-aliasing 差異、字體渲染微調、次像素定位變化都會觸發失敗。Test 頻繁因無關變化而失敗（flaky）。

**過高（0.1）**：小型 layout 偏移、顏色微調、邊框消失可能不被偵測。Test 的保護力下降。

**建議起點（0.01）**：允許 1% 的像素差異。能容忍 anti-aliasing 差異，同時捕捉有意義的視覺變化。根據實際 flaky 頻率調整。

## Baseline 管理

### 版本控制

Baseline 截圖加入 git。每次視覺變更的 PR 包含 baseline 更新，reviewer 從 diff 中看到「視覺變化了什麼」。

Baseline 檔案較大（PNG，數十 KB 到數百 KB）。Git LFS 適合管理這類二進位檔案。

### 跨平台差異

不同作業系統的字體渲染、anti-aliasing 演算法不同。同一段 HTML 在 macOS 和 Linux 上的截圖會有微小差異。

處理策略：

- **一個平台一套 baseline**：macOS 和 Linux 各自維護 baseline。CI 環境固定在一個平台。
- **只在 CI 比對**：本地開發不跑截圖比對（平台差異導致 flaky），CI 環境固定平台後比對。

### 動態內容

畫面中有動態內容（時間戳、隨機 ID、動畫）時，截圖每次都不同。

處理策略：

- **遮蔽動態區域**：截圖前用 CSS 隱藏動態元素，或在截圖比對時指定忽略區域。
- **固定動態值**：test 中 mock 時間和隨機數，讓畫面內容確定。
- **只截靜態區域**：用 element screenshot（`locator.screenshot()`）而非 full page screenshot，只截不含動態內容的區域。

## 和其他 test 層的關係

截圖比對是 UI test 的最外層 — 驗證視覺呈現而非邏輯行為。它和 widget test（驗證 widget 結構）、導航 test（驗證路由行為）互補：

widget test 通過但截圖比對失敗 = 邏輯正確但視覺不對（CSS bug）。截圖比對通過但 widget test 失敗 = 視覺沒變但邏輯壞了（功能 bug 還沒影響到視覺）。

## 下一步路由

- 狀態覆蓋策略 → [Widget test 的狀態覆蓋策略](/testing/04-ui-automation/state-coverage-strategy/)
- Playwright 驗證流程 → [Playwright 瀏覽器驗證流程](/testing/04-ui-automation/playwright-verification/)
- 畫面狀態矩陣 → [ux-design 模組一 畫面狀態矩陣](/ux-design/01-screen-state-machine/state-matrix-definition/)
