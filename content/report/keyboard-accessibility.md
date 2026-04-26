---
title: "鍵盤可達性：focus indicator、tab 順序、escape 路徑"
date: 2026-04-25
weight: 52
description: "鍵盤使用者用 tab / shift+tab 導航、enter / space 激活、esc 退出。三件事決定可不可用：focus 是否可見、tab 順序是否合理、modal / overlay 有沒有 escape 路徑。本文盤點搜尋頁的鍵盤 a11y 風險點。"
tags: ["report", "事後檢討", "Accessibility", "Keyboard", "工程方法論"]
---

## 核心原則

**鍵盤使用者導航三要素：focus 可見、tab 順序合理、有 escape 路徑。** 三者任一缺失、鍵盤使用者就卡住。視覺使用者看不到 focus 也能用滑鼠繼續、鍵盤使用者沒有 fallback。

> 本篇焦點：**鍵盤可達性**。
> - **視覺呈現面的 a11y**（對比 / 放大）由 [#40 視覺輔助](../visual-aids-contrast-zoom-responsive/) 處理
> - **行動 / motor 使用者的 a11y**（hit target）由 [#53 Motor 可達性](../motor-accessibility-hit-target/) 處理
> - **DOM 移動時的 focus 處理**由 [#37 focus management on DOM move](../focus-management-on-dom-move/) 處理（本篇處理「靜態 focus 設計」、#37 處理「動態 focus 移動」）

---

## 為什麼鍵盤可達性需要獨立盤點

### 使用者類型

| 使用者                       | 為什麼用鍵盤                   |
| ---------------------------- | ------------------------------ |
| 全盲（screen reader 使用者） | 完全靠鍵盤、滑鼠看不到游標位置 |
| 低視力                       | 鍵盤比滑鼠精準（不需要瞄準）   |
| Motor 障礙                   | 鍵盤比滑鼠手部負擔小           |
| Power user                   | 鍵盤比滑鼠快                   |

最後一類占人口比例不小 — 鍵盤可達性對全體使用者都有價值、不只 a11y 使用者。

### 三要素的失敗模式

| 要素        | 失敗模式                               | 後果                              |
| ----------- | -------------------------------------- | --------------------------------- |
| Focus 可見  | `outline: 0` 移除預設 focus 但沒補替代 | 鍵盤使用者不知道 focus 在哪、迷失 |
| Tab 順序    | 順序跟視覺布局不一致                   | 跳來跳去、迷失                    |
| Escape 路徑 | Modal 沒有 ESC 關閉                    | 卡在 modal 出不來                 |

三者都是「視覺使用者通常不會碰到、鍵盤使用者必碰」— 開發者用滑鼠測 100% OK、鍵盤使用者一進去就壞。

---

## 風險點 1：Focus indicator 的可見度

**位置**：tab focus 到 search input、scope radio、filter checkbox 等元素。

**判讀**：

- 瀏覽器預設 focus outline（藍色 2px）
- 某些 theme 用 `outline: 0` 移除 — 鍵盤使用者迷失
- 自訂 outline 要對比足夠（WCAG 2.4.7、AA 3:1 對比 + 至少 2px 寬）

**症狀**：鍵盤使用者 tab 過去看不到 focus 在哪、不知道下一個 enter 會激活誰。

**第一個該查的**：用 keyboard tab 過所有互動元素、確認每個都有可見 focus。

**修正方向**：

```css
/* 預設 — 信任瀏覽器 outline */
/* 不寫 outline: 0 */

/* 客製 — 用 :focus-visible（只在鍵盤觸發時顯示、滑鼠點擊不顯示） */
:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/* 移除 outline 必須補 box-shadow / border 等替代 */
button:focus { outline: 0; box-shadow: 0 0 0 3px var(--focus-color); }
```

`:focus-visible` 是現代做法 — 滑鼠使用者不看到 outline（不會覺得「煩」）、鍵盤使用者看到 outline（必要的回饋）。

### Focus indicator 的對比度

WCAG 2.4.11 要求 focus indicator 跟相鄰背景對比 ≥ 3:1：

```css
/* 較差 — 灰底 + 灰 outline、對比不足 */
.button { background: #f0f0f0; }
.button:focus-visible { outline: 2px solid #cccccc; }

/* 好 — 跟背景對比足夠 */
.button:focus-visible { outline: 2px solid #0066cc; }
```

---

## 風險點 2：Tab 順序與視覺布局的對齊

**位置**：搜尋頁元素：H1 → search input → scope radio → results → filter sidebar。

**判讀**：

預設 tab 順序 = DOM 順序。如果視覺布局跟 DOM 順序不一致（例如 sidebar 在右、但 DOM 在前）、鍵盤使用者體驗：

- Tab 1：H1（OK）
- Tab 2：跑到 sidebar（視覺在右下、鍵盤跳過去）
- Tab 3：search input（視覺在左上、鍵盤跳回來）

**症狀**：鍵盤使用者 tab 順序看似隨機、失去空間感。

**第一個該查的**：用 keyboard tab 過所有互動元素、看 focus 移動順序是否符合視覺閱讀順序（左到右、上到下）。

**修正方向**：

| 策略                        | 機制                                                                |
| --------------------------- | ------------------------------------------------------------------- |
| DOM 順序對齊視覺順序        | 改 HTML 結構讓 DOM 順序就是 tab 順序                                |
| 用 `tabindex` 調整順序      | 顯式控制 tab 順序（風險：違反 DOM 順序、對 screen reader 仍依 DOM） |
| Skip link 跳過長 navigation | 讓鍵盤使用者快速跳到主內容                                          |

預設選「DOM 順序對齊視覺順序」 — 不需要 `tabindex`、對所有 a11y 工具都正確。

### Skip link 設計

```html
<body>
  <a href="#main" class="skip-link">跳到主內容</a>
  <nav>...</nav>
  <main id="main">...</main>
</body>
```

```css
.skip-link {
  position: absolute;
  top: -40px;       /* 預設藏起來 */
  left: 0;
  background: var(--bg);
  padding: 8px;
}
.skip-link:focus {
  top: 0;            /* tab 到時顯示 */
}
```

第一個 tab 焦點 = skip link、鍵盤使用者可以選擇跳過 nav 直達主內容。

---

## 風險點 3：Modal / overlay 的 escape 路徑

**位置**：Pagefind drawer 在 mobile 模式展開、filter sidebar 在某些 layout 是 modal-like。

**判讀**：

鍵盤使用者進入 modal 後需要：

1. 按 ESC 可以關閉
2. Tab 順序限制在 modal 內（focus trap、不會 tab 到背景元素）
3. 關閉 modal 後 focus 回到觸發元素

任一缺失 = 卡住。

**症狀**：鍵盤使用者打開 filter drawer 後 tab 跑到背景元素、不知道怎麼關 drawer。

**第一個該查的**：開啟 modal / drawer / overlay、按 ESC 看會不會關、tab 看會不會跑到背景。

**修正方向**：

```js
function openModal(modal, trigger) {
  modal.showModal?.() || (modal.style.display = 'block');

  // ESC 關閉
  modal.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal(modal, trigger);
  });

  // Focus trap（簡化版）
  var focusables = modal.querySelectorAll('button, input, select, [tabindex]');
  focusables[0]?.focus();

  modal.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab') return;
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  });
}

function closeModal(modal, trigger) {
  modal.close?.() || (modal.style.display = 'none');
  trigger?.focus();  // 焦點回觸發元素
}
```

**用 `<dialog>` 元素自動 trap**：

```html
<dialog id="filter-modal">...</dialog>
```

```js
modal.showModal();  // 自動 focus trap + ESC 處理
```

`<dialog>` 是現代做法 — 鍵盤行為由瀏覽器處理、不需要手寫 trap 邏輯。

---

## 設計取捨：focus 處理策略

當需要客製 focus 視覺時、四種做法：

### A：信任瀏覽器預設 outline（這個專案的預設）

- **機制**：完全不寫 `outline` 規則、瀏覽器藍色 outline 自動套用
- **選 A 的理由**：成本最低、跨瀏覽器一致、不會意外破壞
- **適合**：對 focus 視覺沒有強烈品牌需求
- **代價**：focus 看起來「不夠精緻」（瀏覽器預設不一定符合品牌風格）

### B：用 `:focus-visible` 客製 outline

- **機制**：`:focus-visible { outline: 2px solid var(--brand); }`、滑鼠點擊不顯示
- **跟 A 的取捨**：B 達到品牌一致性、滑鼠使用者不被「煩」；A 簡單但視覺一般
- **B 比 A 好的情境**：品牌設計嚴格要求 focus 視覺

### C：用 `box-shadow` 取代 outline

- **機制**：`:focus-visible { box-shadow: 0 0 0 3px var(--focus); outline: 0; }`
- **跟 B 的取捨**：C 跟 outline 視覺差異是「跟著元素圓角」、適合圓角 UI；outline 永遠是矩形
- **C 比 B 好的情境**：圓角元素需要 focus 跟隨圓角

### D：完全移除 focus indicator

- **機制**：`*:focus { outline: 0; }`、不補替代
- **成本特別高的原因**：違反 WCAG 2.4.7、鍵盤使用者完全無法導航
- **D 是反模式**：違反 WCAG 2.4.7（合規層） — 即使品牌追求極簡、也該保留 focus indicator

「邏輯 tab 順序」要素的詳細展開（DOM vs tabindex 的取捨、跟 mental model 對齊）見 [#71 Tab Order = DOM Order = Mental Model 三者對齊](../tab-order-mental-model-alignment/)。

---

## 跟其他原則的關係

| 篇                                                                      | 關係                                                                                 |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [#37 Focus management on DOM move](../focus-management-on-dom-move/)    | 互補 — 本篇處理「靜態 focus 設計」、#37 處理「DOM 移動時 focus 該怎麼跟」            |
| [#39 Native HTML 優先於 ARIA role](../native-html-over-aria-role/)      | 用 `<button>` / `<dialog>` / `<input>` 等 native element、自動獲得正確 keyboard 行為 |
| [#45 跟外部組件合作的層次](../external-component-collaboration-layers/) | 客製 focus 樣式時、注意不要打破 framework 內部的 focus 邏輯                          |

---

## 開發階段檢查清單

| 檢查         | 動作                                                           |
| ------------ | -------------------------------------------------------------- |
| Focus 可見   | 拔掉滑鼠、只用鍵盤、tab 過所有互動元素、確認每個都有可見 focus |
| Focus 對比   | DevTools Contrast Ratio 量 focus indicator 跟背景對比 ≥ 3:1    |
| Tab 順序     | tab 過去確認順序符合視覺閱讀順序                               |
| ESC 關閉     | 開啟 modal / drawer、按 ESC 看會不會關                         |
| Focus trap   | 開啟 modal、tab 看是否限制在 modal 內                          |
| Focus return | 關閉 modal、看 focus 是否回觸發元素                            |

每個 ~30 秒、開發完成前跑一輪。

---

## 判讀徵兆

| 訊號                                | 該檢查的位置                                        |
| ----------------------------------- | --------------------------------------------------- |
| 鍵盤使用者反映「不知道 focus 在哪」 | 確認沒有 `outline: 0` 沒補替代、用 `:focus-visible` |
| Tab 順序看起來隨機                  | DOM 順序對齊視覺順序、必要時用 skip link            |
| Modal 開啟後鍵盤使用者卡住          | 加 ESC 關閉 + focus trap、或改用 `<dialog>`         |
| Modal 關閉後 focus 跑到頁面開頭     | 關閉時手動 `trigger.focus()`                        |
| Focus 在 dark mode 看不清           | 加對比度檢查（≥ 3:1）                               |

**核心原則**：鍵盤可達性的三要素都是「視覺使用者通常不會碰、鍵盤使用者必碰」 — 開發階段必須拔滑鼠測一輪、不能依賴使用者通報。
