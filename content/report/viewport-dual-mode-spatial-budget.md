---
title: "跨 viewport 雙模式 UI 的物理空間預算"
date: 2026-04-25
weight: 2
description: "Responsive 設計的 breakpoint 不該憑感覺取，而該由元件的固有尺寸加總推算。本文以搜尋頁的 filter 雙 slot 為例，展開『先列尺寸預算、再決定 breakpoint』的方法。"
tags: ["report", "事後檢討", "CSS", "Responsive Design", "工程方法論"]
---

## 核心原則

**雙模式 UI 的 breakpoint 是「物理空間預算的結果」、不是「設計選擇」。** 把每個元件的固有尺寸與 gap 加總，得到「兩種模式各自能存活的最小 viewport」 — breakpoint 從這個數字往上取一個安全餘裕。憑感覺取（768、1024）會在中間過渡區看到元件擠壓、消失或溢出。

---

## 為什麼 breakpoint 不能憑感覺

### 商業邏輯

Responsive UI 的本質是「同一份內容、在不同寬度有不同的呈現方式」。每種模式（mobile / tablet / desktop）對應一個 layout，每個 layout 有自己的最小可生存寬度 — 這是元件尺寸與 gap 的加總、不是任意選擇。

當 breakpoint 取得比實際所需大，模式切換點與「真正放得下」的點不一致，使用者在過渡區看到擠壓、溢出、或元件神秘消失。

### 預算推算的步驟

| 步驟 | 動作                                                      |
| ---- | --------------------------------------------------------- |
| 1    | 列出該模式下所有可見元件的固有寬度                        |
| 2    | 列出元件之間的 gap 與 container 的 padding                |
| 3    | 加總得到「該模式所需的最小 viewport」                     |
| 4    | breakpoint = 最小 viewport + 安全餘裕（避免邊界情況閃爍） |

---

## 這次任務的實際預算

### 觀察

搜尋頁的 desktop layout 包含：

- main 內容欄寬度 = 70ch ≈ 720px（theme 預設）
- filter sidebar 寬度 = 400px（自訂）
- main 與 filter 之間 gap = 32px
- body 左右 padding 各 64px = 128px

### 判讀

把 filter 放在 main 左外側、main 維持置中時，所需最小 viewport：

```text
最小 viewport ≈ main + 2 × (filter + gap) + body padding
             = 720 + 2 × (400 + 32) + 128
             = 1712px
```

但這是「左右對稱都放下」的條件。若允許 filter 溢出 body padding（仍在 viewport 內可見），條件放寬為：

```text
最小 viewport ≈ main + filter + gap + body padding
             = 720 + 400 + 32 + 128
             = 1280px
```

選 1280 為下限、加餘裕後取 1400px。

### 執行

```css
@media (min-width: 1400px) {
  .search-filter-slot { display: block; /* 桌面寬模式 */ }
}
```

下方寬度時 filter 顯示在 pagefind 原生位置（drawer 內、結果上方），由 pagefind 自己處理。

---

## 雙 slot 切換：搬節點而非複製

選定 breakpoint 後，要決定「兩種模式怎麼共用同一個 filter UI」。

**核心定義**：用 `matchMedia + appendChild` 在兩個 slot 之間搬同一個 DOM 節點。

```js
var mql = window.matchMedia('(min-width: 1400px)');
function place() {
  if (mql.matches) {
    desktopSlot.appendChild(filter);
  } else {
    drawer.insertBefore(filter, drawer.firstChild);
  }
}
mql.addEventListener('change', place);
```

**為什麼搬而不複製**：filter 內部有 state（checkbox 勾選、目前篩選條件），複製兩份會造成兩份 state 不同步。搬同一份節點 — state 永遠跟著節點。

---

## 內在屬性比較：四種雙模式實作

| 做法                                           | 依賴前提              | 維護成本 | state 一致性            |
| ---------------------------------------------- | --------------------- | -------- | ----------------------- |
| CSS-only（兩個 slot 都顯示，CSS 隱藏其中一個） | 兩份節點獨立可用      | 低       | 差 — 需要同步兩份 state |
| JS 搬同一節點（matchMedia）                    | 節點可被任意 reparent | 中       | 高 — 一份 state         |
| JS 完全重建 UI（每次 viewport 變動重 mount）   | UI 構建快             | 中-高    | 中 — 重建時 state 重置  |
| 兩種完全獨立的 UI 實作                         | 各自有 source code    | 最高     | 不適用                  |

優先選擇「JS 搬同一節點」 — 對 stateful UI 是 state 一致性與維護成本的最佳折衷。

---

## 正確概念與常見替代方案的對照

### Breakpoint 是預算的下游、不是上游

**正確概念**：先算物理空間預算，breakpoint 從預算推導。

**替代方案的不足**：直接套用 `768 / 1024 / 1440` 等流行 breakpoint — 這些是針對「常見裝置寬度」設計的，跟你的元件尺寸無關。元件比預期大就會在中間區看到擠壓。

### 雙模式不等於兩份程式

**正確概念**：同一個 stateful UI 在兩個 slot 之間搬移，state 跟著節點走。

**替代方案的不足**：在兩個 slot 各放一份節點、用 CSS 隱藏其中一個 — 看起來簡單，但 state 同步要額外寫 sync 邏輯，bug 容易卡在「兩份 state 不一致」這類難重現的地方。

### 中間過渡區要明確處理

**正確概念**：低於最小 viewport 時 fall back 到 mobile 模式，不要讓元件部分可見、部分被截斷。

**替代方案的不足**：只設計「夠寬」與「太窄」兩個極端，中間區任元件溢出 — 使用者看到一半 filter 卡在 viewport 邊緣，比完全隱藏更困惑。

---

## 判讀徵兆

| 訊號                                            | 可能的根因                        | 第一個該檢查的事                                    |
| ----------------------------------------------- | --------------------------------- | --------------------------------------------------- |
| 中間寬度時 UI 元件擠壓或重疊                    | breakpoint 比實際所需小           | 算物理空間預算、確認 breakpoint 對應的最小 viewport |
| 元件在某些寬度下消失但 CSS `display` 是 `block` | 元件被 absolute 定位推出 viewport | 檢查 absolute 元件相對 viewport 的座標、是否為負    |
| 兩份 UI 顯示不同步（一邊勾選、另一邊沒勾）      | 兩份節點各自 state                | 改成 JS 搬一個節點，不複製                          |
| 模式切換時 UI 閃爍 / 重新初始化                 | 每次切換都重 mount                | 用 `appendChild`（搬節點）取代 `innerHTML = ...`    |

**順序**：看到擠壓或消失先量空間、不要立刻調 breakpoint 數字。數字背後有計算才不會反覆試錯。
