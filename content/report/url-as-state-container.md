---
title: "URL 是 stateful UI 的儲存層 — 哪些 state 該寫進 URL"
date: 2026-04-26
weight: 70
description: "互動式 UI 的 state 散落在多層（in-memory / URL / localStorage / server / index）、每層有不同特性。可分享 / 可恢復 / 可導航的 state 該寫進 URL — 不寫進 = silent 把這些特性犧牲掉。本文展開「state 的儲存層選擇」協議與 URL 的具體位置。"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "UX", "Architecture"]
---

## 核心原則

**State 的儲存層決定它的特性 — 可分享 / 可恢復 / 可導航 的 state 該寫進 URL、不寫進 = silent 把這些特性犧牲掉。**

| 儲存層         | 可分享 | 可 reload 恢復 | 可 back/forward 導航 | 跨 tab 同步     | 跨 device 同步   |
| -------------- | ------ | -------------- | -------------------- | --------------- | ---------------- |
| In-memory      | ❌     | ❌             | ❌                   | ❌              | ❌               |
| URL            | ✅     | ✅             | ✅                   | 部分（同 URL）  | 部分（複製連結） |
| sessionStorage | ❌     | ✅             | ❌                   | ❌              | ❌               |
| localStorage   | ❌     | ✅             | ❌                   | ✅（同 origin） | ❌               |
| Server         | ✅     | ✅             | ❌                   | ✅              | ✅               |

寫 stateful UI 時、每個 state 的儲存位置是個設計選擇 — 不選 = 預設用 in-memory = 預設犧牲所有上面五個特性。

---

## 為什麼 URL 容易被忽略

### URL 是隱形維度

In-memory state 在 React useState / Vue ref / vanilla 變數裡 — 寫起來最便利、是「預設位置」。URL state 需要 `URLSearchParams` + `history.pushState` + `popstate` listener、寫起來成本高。

[#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/) 直接解釋為什麼：URL state 是「對齊使用者期望」的位置（使用者預期 URL 包含 state、能分享）、in-memory 是「便利位置」。預設便利、要刻意才走對齊。

### 沒寫 URL state 的失敗訊號是 silent

使用者打開搜尋頁、輸入「pagefind」、選擇 title-only filter、看到結果。這時：

- **複製 URL 分享給朋友** → 朋友打開看到空白搜尋框（query 不在 URL）
- **重整頁面** → 自己也看到空白搜尋框
- **點 back** → browser back 跳離搜尋頁、不是回到「沒 filter 的同個搜尋」

這三個動作沒有 error、沒有崩潰、就是「state 不見了」。使用者通常以為「網站就這樣」、不會 report bug。Silent 失敗 = 維護者永遠不知道有問題。

對照 [#55 Filter × Source 層錯位](../view-layer-filter-vs-source-layer/) — 都是 silent 失敗、都是「該存在的東西不在」。

---

## State 該寫進 URL 的判準

### 三問

1. **使用者會分享這個 state 嗎**？— 是 → URL（複製連結即帶 state）
2. **使用者 reload 後預期 state 還在嗎**？— 是 → URL 或 sessionStorage
3. **使用者期望 browser back/forward 在 state 之間導航嗎**？— 是 → URL

任一個「是」 → URL。

### 反向判準：什麼不該寫進 URL

| State 類型                                  | 為什麼不該寫進 URL                                |
| ------------------------------------------- | ------------------------------------------------- |
| Scroll position                             | 頻繁變動破壞 history、且每個瀏覽器自己管          |
| Focus / hover state                         | Ephemeral、跟使用者操作直接綁定、寫進 URL 沒意義  |
| Form 編輯中的暫存值                         | 使用者沒提交、不該被分享                          |
| 敏感資訊（token / 密碼）                    | URL 進 history / referer header / log、安全性問題 |
| 高頻 polling 結果                           | 每秒變、history 爆炸                              |
| 內部 component state（折疊 / 展開動畫進度） | 跟 UI 細節綁、不是使用者意圖                      |

---

## 多面向：常見 UI 元素的 URL state 對照

### 面向 1：Search filter（這次任務的 case）

```text
Query string、scope filter、type filter、tag filter
→ 都該進 URL：使用者會分享「我搜什麼 + 怎麼篩」
```

範例 URL：`/search/?q=pagefind&scope=title&type=post&tag=js`

### 面向 2：Tab / step navigation

```text
Active tab、wizard step
→ 該進 URL：分享 = 直接打開該 tab/step
```

範例：`/settings/?tab=notifications`、`/checkout/?step=payment`

### 面向 3：Sort / pagination

```text
排序欄位、頁碼
→ 該進 URL：分享 = 朋友看到同樣排序的同一頁
```

範例：`/posts/?sort=date_desc&page=3`

### 面向 4：Modal / drawer 開合

```text
看情境：
- 重要 modal（圖片預覽、編輯對話框）→ URL（可分享 / back 關閉）
- 純 UX 提示 modal（welcome tour）→ in-memory（不該分享）
```

### 面向 5：Theme / UI preference

```text
Dark mode、字型大小
→ localStorage（跨 session 但不分享、跟 device 綁）
不進 URL（不會「分享你的 dark mode 設定」）
```

---

## URL state 的實作模式

### 讀：載入時從 URL 同步到 component state

```js
function getInitialState() {
  const params = new URLSearchParams(location.search);
  return {
    query: params.get('q') || '',
    scope: params.get('scope') || 'all',
    type: params.get('type') || null,
  };
}

const initialState = getInitialState();
// component 用 initialState 初始化
```

### 寫：state 變動時同步到 URL

```js
function syncUrl(state) {
  const params = new URLSearchParams();
  if (state.query) params.set('q', state.query);
  if (state.scope && state.scope !== 'all') params.set('scope', state.scope);
  if (state.type) params.set('type', state.type);
  const url = `${location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
  history.replaceState(null, '', url);
}

// 每次 state 變動觸發
onStateChange((newState) => syncUrl(newState));
```

選擇 `replaceState` vs `pushState`：

- `replaceState`：每次 state 變動覆蓋當前 history entry — back/forward 跳過中間狀態
- `pushState`：每次 state 變動加新 history entry — back 回到上一個 state

通常 search filter / sort / pagination 用 `replaceState`（typing 太快、不該每個字符一個 history entry）；tab / step 用 `pushState`（每個 step 該 back 回上一個）。

### 雙向：聽 popstate 處理 back/forward

```js
window.addEventListener('popstate', () => {
  const state = getInitialState();
  applyStateToUI(state);  // back/forward 後、把 state 套回 UI
});
```

沒 listen popstate = back/forward 不會觸發 UI 更新、URL 跟 UI 不同步。

---

## 不該套用本原則的情境

「URL 是 state 儲存層」原則在「公開可分享的 UI」成立、但有合理例外：

| 情境                        | 為什麼不該套用                                    |
| --------------------------- | ------------------------------------------------- |
| 內部 admin 工具             | 不分享、不公開、URL persistence ROI 低            |
| Single-page wizard 強制流程 | 不該允許 deep link 跳關卡（業務規則需要照順序走） |
| 一次性確認對話框            | 不該被 back 回來、不該分享                        |
| 開發中的 prototype          | 還沒穩定的 UI、不該固化 URL contract              |

---

## 跟其他抽象層原則的關係

| 原則                                                                      | 跟本卡的關係                                                       |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [#44 SSOT](../single-source-of-truth/)                                    | URL 是 state 的 SSOT 候選 — 選對位置 = 一處可改、不選 = 多源 drift |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/) | In-memory state 是便利位置、URL state 是對齊（使用者預期）位置     |
| [#55 Filter × Source 層錯位](../view-layer-filter-vs-source-layer/)       | 都是 silent 失敗結構 — state 該在的位置不在、使用者沒訊號          |
| [#56 視覺完成 ≠ 功能完成](../visual-completion-vs-functional-completion/) | URL state 沒做 = 「畫面對了但 reload 後不見」是同類功能缺口        |
| [#66 明示語意縮小](../pattern-explicit-semantic-narrowing/)               | 「URL 不持久化」如果是設計選擇、要明示（「重整會清除狀態」hint）   |

---

## 對應的實作篇

- 搜尋頁的 scope filter URL persistence — Phase 1+2 修完後 retrospective Checkpoint 1 才發現遺漏（#68 dogfooding）
- 任何 search / list / dashboard UI — 都該檢視 URL state coverage

---

## 判讀徵兆

| 訊號                                                          | 該做的事                                                                             |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 寫互動 UI 但沒寫 URL 同步                                     | 跑三問、確認該不該寫進 URL                                                           |
| 使用者 report「我分享連結給朋友、他看不到我看到的」           | URL state 缺漏的 silent 訊號顯現                                                     |
| `replaceState` 跟 `pushState` 沒區分、所有 state 變動用同一個 | 評估：哪些是 history entry 該被記、哪些不該                                          |
| 沒 listen `popstate`                                          | back/forward 會 silent 失效、補 listener                                             |
| URL 變超長、含 ephemeral state                                | 過度寫進 URL、用反向判準砍掉不該寫的                                                 |
| 內心 OS：「state 用 useState 就好、URL 之後再說」             | 「之後再說」= [#67 reformer 謊言](../ease-of-writing-vs-intent-alignment/)、補不回來 |

**核心原則**：URL 是 stateful UI 的隱形儲存層。沒寫 URL state = silent 犧牲分享 / 恢復 / 導航三個 UX 特性。寫之前跑三問（分享？reload？back/forward？）、任一個是 → URL。
