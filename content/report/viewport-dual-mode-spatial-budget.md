---
title: "跨 viewport 雙模式 UI 的物理空間預算"
date: 2026-04-25
weight: 2
description: "Responsive 設計的 breakpoint 不該憑感覺取、該由元件的固有尺寸加總推算。本文展開「先列尺寸預算、再決定 breakpoint」的方法。"
tags: ["report", "事後檢討", "CSS", "Responsive Design", "工程方法論"]
---

## 核心原則

**雙模式 UI 的 breakpoint 是「物理空間預算的結果」、不是「設計選擇」。** 把每個元件的固有尺寸與 gap 加總、得到「兩種模式各自能存活的最小 viewport」 — breakpoint 從這個數字往上取一個安全餘裕。憑感覺取（768、1024）會在中間過渡區看到元件擠壓、消失或溢出。

> 本篇焦點：**breakpoint 數字怎麼推算**。
> - **stateful UI 怎麼跨兩個 slot 共用同一份節點**由 [#54 跨 slot 同節點搬遷 pattern](pattern-cross-slot-node-relocation/) 處理（兩議題機制不同：本篇是數字計算、#54 是 state 一致性）

---

## 為什麼 breakpoint 不能憑感覺

### 商業邏輯

Responsive UI 的本質是「同一份內容、在不同寬度有不同的呈現方式」。每種模式（mobile / tablet / desktop）對應一個 layout、每個 layout 有自己的最小可生存寬度 — 這是元件尺寸與 gap 的加總、不是任意選擇。

當 breakpoint 取得比實際所需大、模式切換點與「真正放得下」的點不一致、使用者在過渡區看到擠壓、溢出、或元件神秘消失。

### 預算推算的步驟

| 步驟 | 動作 |
|----|------|
| 1 | 列出該模式下所有可見元件的固有寬度 |
| 2 | 列出元件之間的 gap 與 container 的 padding |
| 3 | 加總得到「該模式所需的最小 viewport」 |
| 4 | breakpoint = 最小 viewport + 安全餘裕（避免邊界情況閃爍） |

---

## 這次任務的實際預算

### 觀察

搜尋頁的 desktop layout 包含：

- main 內容欄寬度 = 70ch ≈ 720px（theme 預設）
- filter sidebar 寬度 = 400px（自訂）
- main 與 filter 之間 gap = 32px
- body 左右 padding 各 64px = 128px

### 判讀

把 filter 放在 main 左外側、main 維持置中時、所需最小 viewport：

```text
最小 viewport ≈ main + 2 × (filter + gap) + body padding
             = 720 + 2 × (400 + 32) + 128
             = 1712px
```

但這是「左右對稱都放下」的條件。若允許 filter 溢出 body padding（仍在 viewport 內可見）、條件放寬為：

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

下方寬度時 filter 顯示在 pagefind 原生位置（drawer 內、結果上方）、由 pagefind 自己處理。

---

## 設計取捨：餘裕的取法

預算算出最小 viewport 後、breakpoint 加多少餘裕？四種做法：

### A：加 ~10% 餘裕（這個專案的預設）

- **機制**：1280 + 120 ≈ 1400
- **選 A 的理由**：避免邊界情況閃爍（使用者視窗剛好在 1280 像素時、輕微 resize 會反覆觸發切換）
- **適合**：一般情境
- **代價**：1280-1400 區間其實能放下、但 CSS 仍走 mobile 模式

### B：取整到常見裝置寬度

- **機制**：1280 → 1366（MacBook Pro 寬度）或 1440（外接螢幕常見）
- **跟 A 的取捨**：B 對齊裝置生態、A 對齊計算結果；B 對「設計給特定裝置的網站」較合理
- **B 比 A 好的情境**：使用者群明確（公司內部工具、特定裝置網站）

### C：完全等於最小值（無餘裕）

- **機制**：breakpoint = 1280
- **跟 A 的取捨**：C 把所有可放下的視窗都納入 desktop 模式、A 留空間給邊界閃爍
- **C 才合理的情境**：實作上有 debounce 處理閃爍、且裝置寬度集中在某個值附近

### D：用 container query 取代 viewport breakpoint

- **機制**：CSS Container Queries — 元件根據父容器寬度切換、跟 viewport 解耦
- **跟 A 的取捨**：D 更精準（容器寬度才是元件真正可用的空間）、A 簡單（viewport 是全局觀念）
- **D 比 A 好的情境**：元件可能放在不同寬度的容器內（CMS 系統、可嵌入元件）

---

## 不該套用「物理空間預算」的情境

預算法有適用邊界：

| 情境 | 為什麼不套用 |
|------|----------|
| 內容靜態、不依設計尺寸（純文字段落） | 內容自然 reflow、不需要 breakpoint |
| 流體 layout（純 % / fr 單位） | 元件自動撐滿可用空間、無「最小寬度」概念 |
| 完全 mobile-first 設計 | 沒有「desktop 模式」這個分支 |
| 元件尺寸 runtime 才知道 | 用 ResizeObserver 動態調整、不是 breakpoint |

**核心判準**：兩種模式之間有「明確的視覺結構切換」嗎？是 → 用預算法；否 → 用流體 layout 或動態量測。

---

## 跟其他原則的關係

| 抽象層原則 | 關係 |
|---------|------|
| [#44 SSoT](single-source-of-truth/) | breakpoint 數字是 fact、CSS 變數住址唯一才能集中管理 |
| [#7 量測值缺一不可](measurement-completeness/) | 預算的每個分量都要有明確來源（寫死 / 量測）、不能估算 |

---

## 判讀徵兆

| 訊號 | 可能的根因 | 第一個該檢查的事 |
|------|---------|---------|
| 中間寬度時 UI 元件擠壓或重疊 | breakpoint 比實際所需小 | 算物理空間預算、確認 breakpoint 對應的最小 viewport |
| 元件在某些寬度下消失但 CSS `display` 是 `block` | 元件被 absolute 定位推出 viewport | 檢查 absolute 元件相對 viewport 的座標、是否為負 |
| Breakpoint 取常見值（768 / 1024）就壞 | 那些值跟你的元件尺寸無關 | 重算預算、不要用「常見」值 |
| Resize 過 breakpoint 時 layout 跳動 | 沒加餘裕、邊界震盪 | 加 10% 餘裕避開閃爍區 |

**順序**：看到擠壓或消失先量空間、不要立刻調 breakpoint 數字。數字背後有計算才不會反覆試錯。
