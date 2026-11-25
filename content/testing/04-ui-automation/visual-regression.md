---
title: "螢幕截圖比對"
date: 2026-06-19
description: "Visual regression testing — 用螢幕截圖比對偵測非預期的視覺變化、baseline 管理和 diff 閾值設定，以及它跟計算後樣式快照比對的分工"
weight: 4
tags: ["testing", "visual-regression", "screenshot", "playwright", "ui-test"]
---

螢幕截圖比對（visual regression testing）用基準截圖（baseline）和當前截圖的像素差異來偵測非預期的視覺變化。這一層驗證的是「畫面看起來是否和上次一樣」，捕捉 CSS 變更、layout 偏移、字體替換等邏輯 test 無法發現的視覺問題。這篇整理截圖比對的運作方式（建立、比對、更新 baseline）、Playwright 的 `toHaveScreenshot()`、diff 閾值的取捨、baseline 的版本控制、跨平台差異與動態內容、截圖比對跟逐元素比對計算後樣式（computed style）的快照各抓得到哪些差異、刻意改 CSS 值的批次該用哪一種讀差異，以及截圖比對跟 widget test、導航 test 的分工。

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

## 截圖比對與計算後樣式快照的分工：各抓得到哪些差異、刻意改 CSS 值的批次怎麼讀差異

截圖比對量的是像素：任何原因造成、超過閾值的外觀改變它都抓得到，但一張 diff 圖只標出哪一塊變了，不帶是哪個元素的哪個 CSS 屬性變了。另一種比對量的是計算後的樣式（概念見 [Computed Style（計算後的樣式）](/ux-design/knowledge-cards/computed-style/) 卡）：測試腳本從要比對的區塊的根元素往下走訪每個元素，用 `getComputedStyle` 記錄一組事先列好的屬性（下文稱屬性清單：字級、行高、顏色、內外距、寬高……）的值，寫成一份 JSON，下文稱計算後樣式快照。比對腳本逐元素、逐屬性比對前後兩版的快照，把差異依「屬性、舊值、新值、元素的 class」分組，同一個元件的同一種改變因此歸在同一組。兩種比對各有量不到的情形：

| 情形                                                               | 截圖比對                                                                                                                            | 計算後樣式快照                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 某個按鈕的行高從 24px 變成 26px                                    | 差異超過〈Diff 閾值設定〉的閾值時抓得到位移；diff 圖不帶元素與屬性                                                                  | 抓得到，每一筆差異帶著元素與屬性                                                                                                                                                                                                                      |
| 沒放進屬性清單的屬性變了                                           | 抓得到                                                                                                                              | 抓不到                                                                                                                                                                                                                                                |
| 兩個版本共有的錯誤（整頁水平溢出）                                 | 比對抓不到：baseline 裡已經有同一個錯誤。讀整頁截圖的人看得到截圖比視窗寬，或另外量 `document.documentElement.scrollWidth` 才看得到 | 抓不到：比對只驗兩版是否相同，兩版有同一個錯誤時判成相同                                                                                                                                                                                              |
| 不在畫面上的元素（未開的 `<dialog>`、未展開的 `<details>` 的內容） | 看不到                                                                                                                              | 讀得到計算值。寬高這類排版屬性：`display: none` 的元素（未開的 `<dialog>`）沒有排版，讀到的是 `auto` 或樣式表寫的值；未展開的 `<details>` 的內容，瀏覽器可能照樣替它排版（Chromium 讀得到像素值），也可能不排版。在展開的狀態下量，才確定是展開後的值 |
| 一批刻意改字級的改動裡，哪些差異是預期的                           | 讀不出：diff 圖把每一處差異標在一起                                                                                                 | 依屬性、舊值、新值與 class 分組讀得出                                                                                                                                                                                                                 |

整理 CSS 的改動分成兩種批次。只換寫法的批次（改成引用 design token、刪重複規則），計算後的值應該不變；拿改動前的快照當預期值，就是以現狀當預期值的特徵測試（Characterization Test）。比對出現的每一筆差異都要查來源：有的來自量測（腳本讀值時 `<details>` 的展開狀態兩版不同），有的是規範上等價的兩種寫法，剩下的才是畫面改了、要退回的退步。等價的判斷標準是依規範兩個值畫出來的結果相同：完全透明的顏色不論寫成 `transparent` 還是 `rgba(255,255,255,0)`，單獨畫時都看不見，`getComputedStyle` 卻讀到 `rgba(0, 0, 0, 0)` 與 `rgba(255, 255, 255, 0)` 兩個字串；判成等價時寫出依據的規範段落。截圖比對在這一種批次上的角色是佐證：快照有差異而截圖 0 差異時，那一筆可能是等價寫法或量測造成的，再回頭找規範段落或量測的證據確認。design token 是取了名字、讓元件規則引用的設計值，見 [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/) 卡。刻意改值的批次（把十幾種字級併成由小到大固定幾級的尺寸階），畫面本來就要變，讀差異的人要判斷每一處差異是不是計畫內的那一個舊值變成那一個新值。截圖比對的 diff 圖在這一種批次上把字級變了的每一塊都標紅；元素截圖（`locator.screenshot()`）定位得到是哪一個元件變了，仍然讀不出是哪個屬性從哪個值變成哪個值，逐張核准等於逐張憑眼睛判斷是不是計畫內的那一個新值，更新 baseline 等於整批放行。比對快照的人可以拿分組後的差異去對開始前寫下的對應表（每一個舊值要變成哪一個新值），對不上的那幾處才是要查的。字級一變，元素的寬高跟著變，這些跟著改變的差異對不上表；它們出現在自己或子孫的字級、行高也有差異的元素上時，算隨字級改變的預期內差異，其餘的寬高差異照樣要查，不整類放行。所以刻意改值的批次用計算後樣式快照讀差異。兩種批次為什麼要分開，見 [Two Hats（兩頂帽子）](/testing/knowledge-cards/two-hats/) 卡。

兩種一起用時各有分工：跑測試的人把截圖比對留著當最外層的網，抓屬性清單以外的變化；比對兩份快照列出哪個元素的哪個屬性變了，讓讀差異的人對照預期；兩版共有的錯誤兩種比對都抓不到，水平溢出這一類靠另外量 `scrollWidth`。快照比對本身也可能沒在讀：只印差異清單的比對，讀到 0 個元素時印出的是一份空清單，跟兩版完全沒變時印出的一樣，讀結果的人分不出是哪一種。所以比對腳本要印出比對了幾個元素與屬性、兩版配對不上的元素有幾個，並跑一次正對照（[Positive Control（正對照）](/testing/knowledge-cards/positive-control/)）：在新版故意改一個值，確認比對報得出這一筆差異。一次實際的做法（量了哪些畫面與寬度、差異怎麼歸類）在 [CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](/work-log/css-token-refactor-verified-by-computed-style-diff/)；整理成可以照著做的流程（只換寫法與刻意改值兩種批次、比對的範圍、差異歸成 0 差異／差異都在預期屬性上／預期以外的差異，以及什麼時候退回）在 [Refactor Without Visual Change — 重構 CSS 而不改外觀的比對與差異歸類](/skills/frontend-with-playwright/refactor-without-visual-change/)。

## 和其他 test 層的關係

截圖比對是 UI test 的最外層 — 驗證視覺呈現而非邏輯行為。它和 widget test（驗證 widget 結構）、導航 test（驗證路由行為）互補：

widget test 通過但截圖比對失敗 = 邏輯正確但視覺不對（CSS bug）。截圖比對通過但 widget test 失敗 = 視覺沒變但邏輯壞了（功能 bug 還沒影響到視覺）。

## 下一步路由

- 狀態覆蓋策略 → [Widget test 的狀態覆蓋策略](/testing/04-ui-automation/state-coverage-strategy/)
- Playwright 驗證流程 → [Playwright 瀏覽器驗證流程](/testing/04-ui-automation/playwright-verification/)
- 畫面狀態矩陣 → [ux-design 模組一 畫面狀態矩陣](/ux-design/01-screen-state-machine/state-matrix-definition/)
