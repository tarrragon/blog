---
title: "拓樸理解先行於 CSS 規則"
date: 2026-04-25
weight: 4
description: "寫 CSS 之前看真實 DOM tree、不靠 class name 推測層級。本文以『drawer 在 form 內、不是 form 的 sibling』這個假設錯誤為例，展開『拓樸理解 → CSS 規則』的順序。"
tags: ["report", "事後檢討", "CSS", "DOM", "工程方法論"]
---

## 核心原則

**CSS 是基於 DOM tree 的規則系統 — 不知道 tree 的真實結構，寫的 CSS 規則無法生效。** 看 class name 的命名規則（如 `__form`、`__drawer` 看起來像 sibling）容易推錯層級；寫 CSS 之前用工具直接讀 live DOM tree、確認哪些是 grid item、哪些是 grid item 內部的子元素。

---

## 為什麼 class name 不能用來推層級

### 商業邏輯

CSS class name 是「用途標記」、不是「結構描述」。`.parent__child` 這種 BEM 風格在很多框架裡只是作者方便辨認用途，跟元素之間的 DOM parent-child 關係無對應。

當作者在 wrapper 裡又加一層 wrapper，class name 不一定改 — 同一個 class name 在不同框架版本可能對應不同的 DOM 巢狀。

唯一能確定 DOM 層級的方法是**讀 live DOM**。

### 看 DOM 的工具選擇

| 工具                               | 適用情境                                             | 限制                     |
| ---------------------------------- | ---------------------------------------------------- | ------------------------ |
| 瀏覽器 DevTools Elements 面板      | 手動探索、單次確認                                   | 截圖溝通慢、不能寫成測試 |
| `playwright browser_evaluate`      | 程式化讀 parent chain、computed style、bounding rect | 需要 server 跑著         |
| 框架原始碼（svelte template、JSX） | 確認靜態 DOM 結構                                    | 動態渲染情境看不到       |

優先用 playwright — 同一段 query 可以重複跑、結果可以寫進測試。

---

## 這次任務的拓樸誤判

### 觀察

要把 search scope UI 放在「搜尋輸入框與結果之間」。基於 class name 推測 DOM 結構：

```text
.pagefind-ui
├── .pagefind-ui__form        ← 搜尋輸入框
└── .pagefind-ui__drawer      ← 結果（與 filter）
```

Class name `__form` 與 `__drawer` 都用 `__` 前綴、並列在 `.pagefind-ui` 下、看起來是 sibling。

### 判讀

依此假設寫 CSS Grid：把 `.pagefind-ui` 設為 grid、用 `display: contents` 串接、把 form 放 row 2、scope 放 row 3、drawer 放 row 4。

實際渲染後：scope 跑到頁尾。

用 `playwright browser_evaluate` 讀 live DOM tree：

```js
const drawer = document.querySelector('.pagefind-ui__drawer');
let parents = [], el = drawer;
while (el && el !== document.body) {
  parents.push(el.tagName + '.' + el.className);
  el = el.parentElement;
}
```

結果：

```text
DIV.pagefind-ui__drawer
FORM.pagefind-ui__form        ← drawer 在 form 內！
DIV.pagefind-ui
DIV#search
```

drawer 是 form 的 child、不是 sibling。我們的 grid 規則把 form（含 drawer 全部結果）放在 row 2、scope 放 row 3 — scope 自然跑到所有結果之後。

### 執行

確認 DOM 後改用「scope absolute 浮在 form 上、drawer 用 margin-top 讓位」的策略 — 不再嘗試把 form 與 drawer 拆到不同 grid row。

---

## 內在屬性比較：拓樸推理的可靠性

| 推理來源                          | 可靠性                    | 適用情境                |
| --------------------------------- | ------------------------- | ----------------------- |
| Live DOM（playwright / DevTools） | 最高 — 反映實際渲染       | Debug、整合外部組件     |
| 框架 source / template            | 高 — 靜態結構             | 自家組件、可讀的 source |
| Class name 命名規則               | 低 — 命名是慣例、不是契約 | 僅參考、不依賴          |
| 視覺截圖推測                      | 最低 — 看不到 DOM 包裹層  | 不應作為唯一依據        |

選擇順序：**Live DOM > source > 命名 > 視覺**。Class name 與視覺只能形成假設、必須用前兩者驗證。

---

## display: contents 的拓樸限制

當決定用 `display: contents` 串接讓子元素參與外層 grid，必須注意：**contents 只能讓直接子節點上去、不能跨越多層 box**。

例：要讓 form 內的 drawer 參與 search-shell 的 grid，需要 form 也設 `display: contents`。但 form 設 contents 後：

- form 自己的 box 消失
- 依賴 form 為 offset parent 的子元素（如 absolute 定位的 clear button）失去定位基準
- form 的 `::before` / `::after` 偽元素可能不渲染

**display: contents 適用條件**：中間層 box 沒有自己的視覺責任（背景、邊框、定位、尺寸） — 否則拆開後視覺破壞。

---

## 設計取捨：拓樸理解的方法

四種做法、各自機會成本不同。這個專案選 A（讀 live DOM）當預設、其他做法在特定情境合理。

### A：讀 live DOM（playwright / DevTools）（這個專案的預設）

- **機制**：用 `playwright browser_evaluate` 讀 ancestor chain、computed style、bounding rect；或 DevTools Elements 面板手動探索
- **選 A 的理由**：反映實際渲染結果、跨 framework 都對、可寫成測試
- **適合**：debug、整合外部組件、寫第一版 CSS 之前
- **代價**：需要 server 跑著（可用 hugo dev / static server）

### B：讀框架 source / template

- **機制**：直接看 svelte / react component 的 template
- **跟 A 的取捨**：B 看靜態結構、A 看 runtime 結構；B 對自家組件夠用、對動態渲染（runtime wrapper / portal）會漏
- **B 比 A 好的情境**：自家組件、template 跟 DOM 1:1 對應、不需要 runtime 確認

### C：用 class name 命名規則推測

- **機制**：看 `.parent__child` 推測 DOM 巢狀
- **跟 A 的取捨**：C 完全不需要工具、A 需要 server；但 C 命名是慣例不是契約、容易錯
- **C 才合理的情境**：初步假設、必須用 A/B 驗證後才能寫 CSS — 不應作為唯一依據

### D：視覺截圖推測

- **機制**：看截圖猜 DOM 結構
- **成本特別高的原因**：截圖看不到 wrapper、看不到 display: contents 等不可視結構
- **D 是反模式**：視覺上看起來相同的 DOM 可能完全不同 — 截圖驗收的盲區會在規則寫了不生效時才被發現、debug 成本指數放大

---

## 判讀徵兆

| 訊號                                        | 可能的根因                                | 第一個該嘗試的動作                                 |
| ------------------------------------------- | ----------------------------------------- | -------------------------------------------------- |
| 寫好的 CSS 規則完全沒生效                   | 元素根本不在預期的 DOM 位置               | 用 playwright `browser_evaluate` 讀 ancestor chain |
| Grid / flex 排序與預期不符                  | 子元素不是直接 grid item                  | 確認 grid container 的 direct children             |
| 設了 `display: contents` 後某些定位元素跑掉 | 那層 box 是 absolute 元素的 offset parent | 把該層 box 留下、找其他方式達成 layout             |
| 框架重繪後 layout 完全變了                  | 框架增加了 wrapper 元素                   | 重新讀 live DOM、更新 CSS 假設                     |

**核心原則**：CSS 行為與預期不符 ≥ 1 次，先回去看 DOM tree、不要繼續調 CSS 規則。先看才不會試錯。
