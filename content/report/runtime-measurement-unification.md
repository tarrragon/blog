---
title: "runtime 量測模式統一"
date: 2026-04-25
weight: 27
description: "對齊基準上的所有元素、要嘛全部寫死、要嘛全部用 ResizeObserver 量測 — 不要混搭。混搭時某些字型 / theme 變化會打破對齊、且難以重現。"
tags: ["report", "事後檢討", "JavaScript", "Refactor", "工程方法論"]
---

## 核心原則

**對齊基準上的尺寸值、要嘛統一寫死、要嘛統一 runtime 量測 — 不要混搭。** 混搭時某些變化（字型替換、scale 改變、theme 切換）會打破對齊、且問題只在特定情境出現、難以重現。選一邊走到底。

---

## 為什麼混搭會不穩

### 商業邏輯

對齊問題本質是「方程組」 — 每個變數的值都要正確、結果才對。

寫死值的特徵：

- 來源是 build time 設計決定
- 變動需要手動改 CSS
- 假設某個渲染條件成立（特定字型、特定 scale）

量測值的特徵：

- 來源是 runtime DOM 量測
- 自動跟著實際渲染走
- 不依賴特定渲染條件

混搭時的失敗模式：寫死值依賴的渲染條件變了、但量測值跟著變、寫死值沒跟 — 兩者錯位、對齊壞掉。

### 統一往一邊靠的選擇

| 統一策略                 | 適合                                        |
| ------------------------ | ------------------------------------------- |
| 全部寫死（鎖渲染條件）   | 設計 token 穩定、組件提供 scale hook 可鎖定 |
| 全部量測（runtime 同步） | 內容動態、字型 / 排版可能變動               |

選擇看「願意接受多少不確定性」 — 全寫死要鎖很多條件、全量測要寫多個 ResizeObserver。

---

## 這次任務的混搭問題

### 觀察

對齊基準上四個值的處理：

| 值                           | 來源                                          |
| ---------------------------- | --------------------------------------------- |
| `--search-title-h` (H1)      | 寫死 64px                                     |
| `--search-form-h` (input)    | 寫死 68px、靠 `--pagefind-ui-scale: 1.0` 鎖定 |
| `--search-gap` (drawer 上方) | 寫死 20px                                     |
| `--search-scope-h`           | ResizeObserver 量測寫回                       |

混搭：前三個寫死、第四個量測。

### 判讀

當前情境穩定 — pagefind scale 鎖在 1.0、theme h1 高度可預測。但若：

- Theme 升級改 h1 line-height → 寫死 64px 不準
- 使用者裝置字型不同 → form 內容寬度變動可能間接影響高度
- pagefind 升級 input 高度算法 → 寫死 68px 不準

寫死值「假設某些條件成立」、條件變了寫死值就錯。

### 執行：兩種統一方向

#### 方向 1：全部寫死、鎖更多渲染條件

```css
body.page-search {
  --search-title-h: 64px;
  --search-form-h: 68px;
  --search-gap: 20px;
  --search-scope-h: 56px;            /* 不再 JS 量測 */
  --pagefind-ui-scale: 1.0;
}

.search-title {
  height: var(--search-title-h);
  line-height: var(--search-title-h);
  margin: 0;                         /* 鎖 H1 margin */
}

.search-scope {
  height: var(--search-scope-h);     /* 鎖 scope 高度、超過裁掉 */
  overflow: hidden;
}
```

代價：scope 內容超過時被裁、UI 可能不適合動態內容。

#### 方向 2：全部量測、ResizeObserver 同步所有

```js
function measureAll() {
  setVar('--search-title-h', titleEl.offsetHeight);
  setVar('--search-form-h', formEl.offsetHeight);
  setVar('--search-scope-h', scopeEl.offsetHeight);
  // gap 是 pagefind drawer 內建、無法從外部量測
}
function setVar(name, val) {
  document.body.style.setProperty(name, val + 'px');
}

[titleEl, formEl, scopeEl].forEach(el => {
  new ResizeObserver(measureAll).observe(el);
});
```

代價：JS 多了一層、初始載入時 fallback 值不對齊（直到 JS 跑完）。

### 推薦

**這個專案選方向 1（全寫死）**：

- Pagefind scale 已能鎖定
- Theme 由本人控制、h1 變動可預期
- Scope UI 設計成單行、不需要動態高度

把當前 scope-h 從量測改寫死、移除 ResizeObserver。混搭問題消失。

---

## 內在屬性比較：四種對齊值來源策略

| 策略                       | 穩定性                | 維護成本       | 對動態內容適應          |
| -------------------------- | --------------------- | -------------- | ----------------------- |
| 全寫死 + 鎖渲染條件        | 高 — 條件鎖死後值穩定 | 低 — 純 CSS    | 低 — 動態內容超過值會裁 |
| 全量測 ResizeObserver      | 高 — 值跟著實際走     | 中 — JS 多一層 | 高                      |
| 混搭（部分寫死、部分量測） | 中 — 邊界 case 壞     | 中             | 中                      |
| Magic number 估算          | 低                    | 不適用         | 低                      |

選擇順序：**內容靜態 → 全寫死；內容動態 → 全量測；不要混搭**。

---

## 鎖定渲染條件的具體技巧

### 1. 使用組件提供的 scale hook

```css
.search-shell { --pagefind-ui-scale: 1.0; }
```

讓組件按我們指定的 scale 渲染、寫死值才有意義。

### 2. 寫死 H1 height + line-height + margin

```css
.search-title {
  height: 64px;
  line-height: 64px;
  margin: 0;
  /* 確保 box height 永遠是 64、不受 font / padding 影響 */
}
```

不留任何「看 box-sizing 與 inheritance 決定」的空間。

### 3. 用 box-sizing: border-box 確保 padding 不影響 box height

```css
.search-scope {
  box-sizing: border-box;
  height: var(--search-scope-h);
  padding: 8px 16px;
  /* total height 還是 var(--search-scope-h)、padding 算在內 */
}
```

---

## 設計取捨：對齊基準上來源機制的選擇

四種做法、各自機會成本不同。預設依內容性質選 — 內容靜態 → A、內容動態 → B、混搭 / 估算永遠不是答案。

> 本篇是 [#44 SSoT](../single-source-of-truth/) 抽象原則在「來源機制統一」這個面向的應用。

### A：全寫死 + 鎖渲染條件（內容靜態的預設）

- **機制**：所有對齊基準值用 CSS 變數寫死、同時鎖定相關渲染條件（pagefind scale、H1 line-height、box-sizing）
- **選 A 的理由**：純 CSS 不依 JS、值 build time 確定、改 token 自動跟上
- **適合**：對齊內容靜態、可預測（設計穩定的搜尋頁、文章頁）
- **代價**：需要鎖很多渲染條件（scale / line-height / box-sizing 等）、scope 內容超過寫死值會被裁

### B：全量測 ResizeObserver 寫回變數（內容動態的預設）

- **機制**：所有對齊基準值用 ResizeObserver 量、寫回 CSS 變數、其他元素引用
- **跟 A 的取捨**：B 自動跟著實際渲染、A 假設條件穩定；B 多 JS 一層、初始 fallback 值不對齊（直到 JS 跑完）
- **B 比 A 好的情境**：內容動態（字型可能變、theme 切換、跨環境部署）

### C：混搭（部分寫死、部分量測）

- **機制**：「主要值寫死、邊界值量測」混合策略
- **成本特別高的原因**：邊界情境（字型變、scale 變、theme 切換）下兩者錯位、對齊在某些 case 壞、難以重現
- **C 才合理的情境**：實務上幾乎不存在 — 「主要 vs 邊界」的判斷本身就不可靠（邊界常常變主要）

### D：Magic number 估算

- **機制**：執行者依感覺給數字、不寫變數、不量測
- **成本特別高的原因**：跨情境（字型 / scale / theme）必壞、估錯時錯誤被視覺接受
- **D 才合理的情境**：實務上幾乎不存在 — 任何「沒來源」的值都會在邊界情境爆掉

---

## 判讀徵兆

| 訊號                               | Refactor 動作                      |
| ---------------------------------- | ---------------------------------- |
| 對齊在某些字型 / 主題 / 縮放下壞掉 | 找出依賴的渲染條件、鎖定或改量測   |
| 改了某個 token 要去多處驗證對齊    | 統一來源（全寫死 or 全量測）       |
| ResizeObserver 量了 A、B 卻寫死    | 評估 B 是否也需要量、避免混搭      |
| 寫死值跟實際渲染差距 > 2px         | 該值依賴的條件沒鎖、改量測或鎖條件 |

**核心原則**：對齊問題的根因常常是「混搭」 — 用統一策略消除這個根因、debug 範圍從「某個情境」縮到「整套策略對嗎」。
