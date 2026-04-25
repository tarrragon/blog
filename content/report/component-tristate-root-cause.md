---
title: "同一個元件在三種互動狀態下顯示位置不同的 root cause"
date: 2026-04-25
weight: 9
description: "當元件「跟著狀態飄」、不同互動狀態下出現在不同位置 — 不是元件本身的問題，是它依賴的『定位錨點』本身在動。本文以 scope UI 三狀態飄移為例，展開錨點分析法。"
tags: ["report", "事後檢討", "Layout", "Debugging", "工程方法論"]
---

## 核心原則

**元件位置 = 定位基準（anchor）+ 相對基準的偏移。元件「跟著狀態飄」不是元件本身的問題、是它的 anchor 隨狀態在動。** Debug 時把元件位置拆成「找錨點 → 算偏移」兩層、確認哪一層在隨狀態變化。

---

## 為什麼狀態化錯位的根因不在元件本身

### 商業邏輯

CSS 計算元件位置時，元件總是「相對某個 reference」 — block flow 是「上一個 sibling 的下緣」、absolute 是 offset parent、grid item 是 grid container。**這個 reference 才是元件位置的決定因素**。

當 reference 在不同狀態下尺寸或位置變動，元件被動跟著動 — 看起來是元件「自己飄」，根因卻在 reference。

### 三層拆解 debug 法

| 層                        | 問題                               | 修法                                      |
| ------------------------- | ---------------------------------- | ----------------------------------------- |
| 1. 元件本身               | 元件 CSS 規則錯了？                | 看元件的 computed style                   |
| 2. 元件的 reference       | reference 在動嗎？尺寸隨狀態變動？ | 量 reference 在每個狀態下的 bounding rect |
| 3. Reference 的 reference | 上一層也在動嗎？                   | 一層一層往上追                            |

多數狀態化錯位的根因在第 2 或第 3 層、不在第 1 層。

---

## 這次任務的實際情境

### 觀察

新加 scope UI（搜尋範圍 radio group）後出現三個狀態的位置不一致：

| 狀態                            | scope UI 位置                        |
| ------------------------------- | ------------------------------------ |
| 初始載入（pagefind 還沒 mount） | 緊接 H1 下方                         |
| 點擊 input（focus、空查詢）     | 在 input 與 results 區之間（如預期） |
| 輸入查詢（results 載入後）      | 跑到所有結果的最下方                 |

### 判讀

第一輪猜測：scope UI 自己的 CSS 在不同狀態下不同 — 用 playwright 看 computed style，發現三狀態下 scope 的 grid-row 都是 3、CSS 屬性沒變。

第二輪：用 playwright `getBoundingClientRect()` 量 scope 的位置，發現 y 座標確實在三狀態下不同。

第三輪：往上一層看「scope 的 grid container 是誰、container 的 grid template 在不同狀態下變了嗎」。發現 search-shell 的 grid template-rows 是 `auto`、自動依子元素內容撐開。

關鍵發現：**`.pagefind-ui__drawer` 不是 `.pagefind-ui` 的直接子節點 — 它在 `<form>` 內**。

```text
.pagefind-ui (display: contents)
└── form.pagefind-ui__form (grid-row: 2)
    └── div.pagefind-ui__drawer (grid-row: 4 設了沒生效)
```

於是：

- 初始：form 只含 input、row 2 矮、scope 在 row 3 緊接 row 2 下。
- 輸入後：form 含 input + drawer（187 個結果）、row 2 撐到全頁高。grid-row 4 比 row 2 後 — 但 drawer 被 form 包住、整個 form 在 row 2 — scope（row 3）在 form 之後 = 結果之後。

scope 的 anchor（grid container 的 row 排列）在 form 撐開時改變 — anchor 在動、scope 跟著動。

### 執行

確認 anchor 問題後改用 absolute 定位：scope 浮在 form 之上、drawer 用 margin-top 讓位。scope 的 anchor 改為 `.search-shell` 的 `position: relative`、不再依賴 form 的尺寸。三狀態下位置一致。

---

## 拆解 anchor 的四個工具

### 1. 找元件的 reference

| 元件的 position | Reference                            |
| --------------- | ------------------------------------ |
| static（預設）  | 上一個 sibling 的下緣 / 父 container |
| relative        | 元件原本在 flow 中的位置             |
| absolute        | 最近的 positioned ancestor           |
| fixed           | viewport                             |
| sticky          | 滾動容器                             |
| Grid item       | Grid container 的 cell               |
| Flex item       | Flex container 的軸線                |

### 2. 用 `getBoundingClientRect` 量

```js
const el = document.querySelector('.search-scope');
console.log(el.getBoundingClientRect());
```

在三個狀態下分別量、比對 y 座標。差異對應到「reference 在動」。

### 3. 往上追 ancestor chain

```js
let parents = []; let el = target;
while (el) {
  parents.push(el.tagName + '.' + el.className);
  el = el.parentElement;
}
console.log(parents);
```

找出 reference 是誰、reference 的 reference 是誰、一層一層追到「不會動」的元素。

### 4. Computed style vs DOM tree 一起看

CSS 規則在 computed style 顯示為「我設了什麼」、DOM tree 顯示「實際巢狀關係」。兩者一起看才知道規則為什麼沒生效。

---

## 內在屬性比較：三種定位策略對狀態化錯位的抵抗

| 策略                             | Anchor 穩定性               | 狀態化飄移風險                     |
| -------------------------------- | --------------------------- | ---------------------------------- |
| Static / block flow              | 低 — 任何前置元素變動都影響 | 高 — sibling 撐高就被推下去        |
| Grid / Flex item                 | 中 — 跟 container 設計綁定  | 中 — container row 撐開時跟著動    |
| Absolute（自定義 offset parent） | 高 — anchor 是固定 ancestor | 低 — anchor 不變則元件不動         |
| Fixed                            | 最高 — anchor 是 viewport   | 不會因內容變動飄移、但會因捲動變化 |

當一個元件需要在多種狀態下保持固定位置 — 優先 absolute（搭配明確的 offset parent）。

---

## 設計取捨：對抗狀態化飄移的定位策略

四種做法、各自機會成本不同。這個專案選 A（absolute + 自定義 offset parent）當預設、其他做法在特定情境合理。

### A：Absolute + 穩定 offset parent（這個專案的預設）

- **機制**：元件 `position: absolute`、選定一個尺寸不隨狀態變動的 ancestor 作為 offset parent
- **選 A 的理由**：anchor 不變則元件不動、跨所有互動狀態位置一致
- **適合**：需要在多狀態下保持固定位置的元件
- **代價**：跳出 layout flow、附近元件需要手動讓位（margin spacer）

### B：Grid / Flex item

- **機制**：把元件當 grid / flex container 的子項、用 grid-row / flex-order 排
- **跟 A 的取捨**：B 自然 reflow、A 完全 anchor-driven；B 在 container 內容隨狀態撐開時、grid 排序跟著重算
- **B 比 A 好的情境**：container 尺寸不隨狀態變動的場景（純 layout、內容靜態）

### C：Static / block flow（預設 layout）

- **機制**：不設 position、跟 sibling 自然排
- **跟 A/B 的取捨**：C 最簡單、A/B 主動處理 anchor；C 完全受前置 sibling 影響、狀態化飄移風險最高
- **C 才合理的情境**：頁面內容極穩定、無狀態切換 — 否則第 N 個元素位置受前 N-1 個元素影響

### D：Fixed（相對 viewport）

- **機制**：`position: fixed`、anchor 是 viewport
- **跟 A 的取捨**：D 永遠在 viewport 同位置、A 跟著內容；D 對「導航類元件」合理、對「內容相關元件」不合理
- **D 比 A 好的情境**：永遠可見的功能元件（toolbar、scroll-to-top button）

---

## 判讀徵兆

| 訊號                                      | 可能的根因                      | 第一個該嘗試的動作                          |
| ----------------------------------------- | ------------------------------- | ------------------------------------------- |
| 元件位置在不同互動狀態下不同              | Anchor 隨狀態變動               | 用 playwright 量三個狀態下的 bounding rect  |
| Computed style 三狀態下都一樣、但位置不同 | Reference 元素的尺寸在動        | 量 reference 元素的尺寸、確認哪個狀態下變大 |
| 改元件 CSS 一個狀態好了、另一個壞         | 用了 reference-dependent layout | 改用 absolute、選擇穩定的 offset parent     |
| 元件初始正確、互動後跑掉                  | Reference 因 reactivity 撐開    | 找出該 reference、用 absolute 跳出其影響    |

**核心原則**：元件「會飄」不是元件的個性、是它依賴的東西在飄。先找飄的源頭，不要追著元件改。
