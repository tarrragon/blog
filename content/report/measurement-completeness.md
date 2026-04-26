---
title: "量測值缺一不可：依賴未測量值會錯位"
date: 2026-04-25
weight: 7
description: "對齊本質是『同一條基準線在多個元素上重現』 — 任何一個元素的高度沒有確定值、整條線都靠不住。本文展開『把對齊問題當線性方程組』的角度。"
tags: ["report", "事後檢討", "Layout", "工程方法論"]
---

## 核心原則

**對齊基準上的每個未知數都要解出來、整組才有解。** 這跟線性方程組一樣 — 任何一個變數靠估算、整條基準線就不準。每個參與對齊的元素都需要「來源明確的數字」（寫死或量測），不能依賴「應該差不多吧」的視覺直覺。

---

## 為什麼缺一個值整個壞

### 商業邏輯

對齊不是「視覺感」、是「相對位置的數學關係」。filter 的 padding-top 要等於右側「H1 + input + gap」的總和；任何一個值不準、padding 就錯、視覺上看起來就是沒對齊。

人眼可以分辨 1px 的差異 — 估算「大概 60px」實際上 56 或 64 都可能、視覺一眼看出。

### 解線性方程組需要所有變數

| 步驟 | 動作                                                   |
| ---- | ------------------------------------------------------ |
| 1    | 列出對齊基準上的所有元素                               |
| 2    | 對每個元素標註「值的來源」：寫死 / 量測 / 未知         |
| 3    | 任何「未知」都要先解決（決定寫死或量測）才能寫對齊規則 |

跳過第 2 步直接寫對齊規則 = 拿一組有未知數的方程組嘗試代入解 — 不會對。

---

## 這次任務的實際情境

### 觀察

要把 filter sidebar 的內容上緣對齊到右側 results 上緣。filter 用 `padding-top` 把內容下推。

第一次嘗試：估 `padding-top: 152px`（H1 64 + input 68 + gap 20）。

實際渲染：filter 上緣比 results 上緣高了 ~10px。

### 判讀

`152px` 的計算用了估算的 H1 height（64px）。實際 H1 受 theme 的 `margin-block-end` 影響、總高度可能 ~70px。差了 ~6px。

進一步檢查：`--pagefind-ui-scale: 0.8` 時 input 高度 = 64 × 0.8 = 51.2px、不是 68px。又差 ~17px。

差距加總超過視覺可接受範圍。

### 執行

把所有變數轉為「來源明確」：

| 元素                           | 解決方式                                                         |
| ------------------------------ | ---------------------------------------------------------------- |
| H1                             | 寫死 height + line-height + margin: 0，強制等於 token            |
| Pagefind input                 | 設 `--pagefind-ui-scale: 1.0`，加 border 共 68px、強制等於 token |
| Scope UI（高度受字型換行影響） | 用 ResizeObserver 量測寫回 CSS 變數                              |
| Gap（drawer margin-top）       | 從 pagefind CSS 取得固定值 20px                                  |

`padding-top` 用 `calc()` 加總所有變數、永遠跟著走。

---

## 內在屬性比較：值的「來源」分類

| 來源                                 | 適用情境                  | 維護負擔            |
| ------------------------------------ | ------------------------- | ------------------- |
| Design token（CSS 變數寫死）         | 設計可決定的固定值        | 低 — 改一處全部跟上 |
| 組件提供的 hook（如 pagefind scale） | 透過組件 API 鎖定渲染參數 | 低 — 跟組件升級走   |
| Runtime 量測（ResizeObserver）       | 內容動態決定的值          | 中 — JS 程式要寫對  |
| 估算 / magic number                  | 不適用 — 永遠錯           | 不該存在            |

**不要把「估算 / magic number」當作來源**。每個 magic number 都是未來 debug 的潛在炸彈。

---

## 把對齊看成方程組的步驟

```text
基準線 P 的位置 = sum(每個前置元素的 height + margin + padding + gap)
```

例：filter 的 `padding-top` = `H1.height + input.height + drawer.margin-top`。

把每個變數列出、確認來源、用 CSS `calc()` + 變數寫成 single source。

```css
.search-filter-slot {
  padding-top: calc(
    var(--search-title-h)        /* 寫死 64px */
    + var(--search-form-h)       /* 鎖 scale=1.0、寫死 68px */
    + var(--search-scope-h)      /* ResizeObserver 量測 */
    + 8px                        /* 固定 padding */
    + var(--search-gap)          /* pagefind drawer margin 20px */
  );
}
```

---

## 設計取捨：對齊基準上每個值的來源

四種做法、各自機會成本不同。預設選擇取決於值的可預測性 — 設計可決定 → A、組件提供 hook → B、內容動態 → C、估算永遠不是答案。

### A：Design token（CSS 變數寫死）

- **機制**：`--search-title-h: 64px` 寫成設計系統 token
- **選 A 的理由**：build time 確定、純 CSS、改 token 全部跟上
- **適合**：設計可決定的固定值（spacing、typography scale、icon size）
- **代價**：值無法跟 runtime 內容變動 — 字型大幅變化時可能不適配

### B：組件提供的 hook（如 pagefind scale）

- **機制**：`.search-shell { --pagefind-ui-scale: 1.0 }`、透過組件 API 鎖定渲染參數
- **跟 A 的取捨**：B 把組件納入自家設計系統、A 自己決定值；B 在「組件渲染參數可調」時最乾淨
- **B 比 A 好的情境**：值由組件決定但組件提供 hook 可控（例如 vendor library 的 size variant）

### C：Runtime 量測（ResizeObserver 寫回 CSS 變數）

- **機制**：JS 量元素實際渲染尺寸、寫回 CSS 變數、其他元素引用
- **跟 A/B 的取捨**：C 自動跟著實際走、A/B 假設條件穩定；C 多 JS 一層
- **C 比 A 好的情境**：值受字型 / 換行 / 內容動態影響、無法 build time 預測

### D：估算 / magic number

- **機制**：執行者依感覺給數字、不寫變數、不量測
- **成本特別高的原因**：未來 debug 的潛在炸彈、估錯時錯誤被視覺接受不被發現、跨情境（字型 / scale / theme）必壞
- **D 是反模式**：任何「沒來源」的值都是 unsolved 變數、會在邊界情境爆掉

---

## 判讀徵兆

| 訊號                      | 可能的根因                   | 第一個該檢查的事                      |
| ------------------------- | ---------------------------- | ------------------------------------- |
| 視覺對齊「看起來差幾 px」 | 某個元素的高度估算不準       | 量測該元素真實 height、跟假設值比對   |
| 換 viewport 對齊壞掉      | 某個值依賴 viewport 但沒處理 | 找出該值、改用響應式變數              |
| 換字型 / 縮放後對齊壞掉   | 某個值受字型影響但寫死了     | 改用 ResizeObserver 量測              |
| 改某個 token 要去多處跟改 | 沒用 CSS 變數                | 把 magic number 提成變數、calc 串起來 |

**核心原則**：對齊問題的根因永遠是「某個變數沒解出來」。先找出那個變數、確定來源、再寫對齊規則。

「估值補方程式」是便利（用感覺寫死）、「找變數真實來源」是對齊（量測或從 token 算）— 同 [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)。對齊問題的 silent 失敗常常是估值的後果。
