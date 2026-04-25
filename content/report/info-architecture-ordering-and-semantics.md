---
title: "資訊架構決策：排序與語意定位"
date: 2026-04-25
weight: 6
description: "Filter 順序、UI 區域語意、客製深度上限 — 這些不是純技術選擇，而是『使用者掃描成本』與『維護成本』的權衡。本文展開三個具體決策。"
tags: ["report", "事後檢討", "UX", "Information Architecture", "工程方法論"]
---

## 核心原則

**UI 順序由使用者掃描成本決定、語意層級不同的元素放在不同區域、客製深度有上限。** 這三條規則對應到搜尋頁的三個具體決策：filter 順序（短清單優先）、scope vs facet 分區、disclosure marker 的接受。

---

## 順序：使用者掃描成本優先於字母排序

### 商業邏輯

當清單有多個選項供使用者挑選，**選項數量影響掃描時間**。短清單先看完、長清單花更多時間 — 把短清單放前面讓使用者先排除一個維度、再面對長清單。

字母排序對「找已知名稱」有效；多選 facet 場景下使用者通常不知道確切選項名、需要 scan，這時候掃描成本主導。

### 這次的應用

Pagefind filter 預設按 filter key 字母排序：`tag` < `type`，所以 Tag 先顯示。

實際內容：

| Filter | 選項數量                                   |
| ------ | ------------------------------------------ |
| Type   | ~5 個（post / card / glossary 等 section） |
| Tag    | ~80 個（站上所有 tags）                    |

Type 短、Tag 長 — Type 先顯示讓使用者先用 section 收斂、再進 Tag 找。

### 執行

```js
function reorderFilters() {
  var blocks = filter.querySelectorAll('.pagefind-ui__filter-block');
  var desiredOrder = ['type', 'tag'];
  var byKey = {};
  blocks.forEach(b => {
    var key = b.querySelector('.pagefind-ui__filter-name').textContent.trim().toLowerCase();
    byKey[key] = b;
  });
  desiredOrder.forEach(k => byKey[k] && filter.appendChild(byKey[k]));
}
```

---

## 語意：mode 與 facet 屬於不同層級

### 商業邏輯

Filter UI 看起來都是「縮小搜尋結果」的控制，但語意層級不同：

| 控制類型            | 作用對象           | UI 慣例位置          |
| ------------------- | ------------------ | -------------------- |
| Mode（模式）        | 改變搜尋演算法本身 | 靠近輸入框           |
| Facet（多面向篩選） | 在搜尋結果上篩選   | 結果區附近 / sidebar |

Mode 決定「如何搜」、facet 決定「篩選什麼結果」。把兩者混在同一 UI 區域會讓使用者誤以為是同一層的選項、可能出現「為什麼勾這個 facet 結果這麼少」這類困惑。

### 這次的應用

| 控制                         | 類型                        | UI 位置               |
| ---------------------------- | --------------------------- | --------------------- |
| 搜尋範圍：全部 / 標題 / 內文 | Mode（影響 regex 比對範圍） | 緊貼搜尋輸入框下方    |
| Filter：Type / Tag           | Facet（在已搜結果上篩選）   | 左側 sidebar / drawer |

兩者視覺上分開、語意對使用者更清楚。

---

## 覆寫深度：知道何時停手

### 商業邏輯

客製外部組件時，「能不能改」與「值不值得改」是兩件事。**覆寫深度的成本來自三個累積層**：

| 層               | 成本                                                     |
| ---------------- | -------------------------------------------------------- |
| UA 預設樣式      | 跨瀏覽器差異 — Chrome / Safari / Firefox 各自 pseudo     |
| 框架 specificity | hash class 提升 specificity、需要 `!important` 或 layers |
| 框架渲染週期     | 改了可能下次 patch 被 revert                             |

三層全部碰到的覆寫值不值得做？標準是：**覆寫深度 vs 改善的使用者價值**。

### 這次的應用

要移除 Pagefind filter 的 `<details><summary>` disclosure 三角圖示。實作需要：

```css
/* 1. UA 預設 marker（Chrome / Firefox） */
summary::marker { content: ""; color: transparent; font-size: 0; }
/* 2. UA 預設 marker（Safari / 老 Chrome） */
summary::-webkit-details-marker { display: none; }
/* 3. 改變 summary 的 display 避免 list-item 行為 */
summary { display: block; list-style: none; }
/* 4. 蓋過 pagefind 的 ::after 自訂 chevron */
.pagefind-ui__filter-name::after { display: none !important; }
/* 5. 處理 Pagefind 重置邊界外的 fallback */
/* ... */
```

跨 3 個瀏覽器、4 條規則、跨組件 specificity — 為了一個視覺小細節。最後決定：**接受原設計**。

### 執行

把這幾條規則全部刪掉、保留 disclosure 三角。改動成本回到 0、視覺上有個小三角不影響使用。

---

## 內在屬性比較：覆寫值不值得做

| 評估維度              | 用法                                       |
| --------------------- | ------------------------------------------ |
| 改善的使用者價值      | 視覺更乾淨？操作更直覺？無障礙更好？       |
| 跨瀏覽器規則數量      | 1-2 條：合理；3+ 條：警訊                  |
| 框架 specificity 對抗 | 有 layers 解決：可接受；沒有解決方案：警訊 |
| 框架渲染週期風險      | 是否會 revert                              |
| 維護負擔              | 升級時要重新驗證的範圍                     |

當「改善的使用者價值低」且「實作累積三層成本」 — 接受原設計。

---

## 正確概念與常見替代方案的對照

### UI 順序由掃描成本決定

**正確概念**：選項清單按「使用者掃描順序」排序 — 短清單先、長清單後；高頻選項先、低頻選項後。

**替代方案的不足**：用字母排序（取資料來源預設） — 對「找已知名稱」有效，對「探索式選擇」掃描成本高。

### Mode 與 facet 視覺分區

**正確概念**：影響搜尋演算法的控制（mode）與篩選結果的控制（facet）放在不同 UI 區域、視覺上明確分開。

**替代方案的不足**：把所有控制都塞進「filter」區 — 使用者誤以為勾「標題」是過濾標題欄位，實際上改變了搜尋演算法。

### 覆寫深度有上限

**正確概念**：當客製需要對抗 UA + 跨瀏覽器 + framework 三層、改善的使用者價值不夠大 — 接受原設計、不打覆寫戰。

**替代方案的不足**：堅持完美客製 — 寫 5 條 CSS 還沒蓋過、加 `!important` 又出新問題、最後用了 30 分鐘做出一個視覺上 99% 的差異。

---

## 判讀徵兆

| 訊號                                   | 對應決策類型      | 第一個該檢查的事                         |
| -------------------------------------- | ----------------- | ---------------------------------------- |
| 使用者抱怨「找不到我要的選項」         | 順序問題          | 看清單長度、把短的排前面                 |
| 使用者搞不清楚「為什麼這個結果出現了」 | mode / facet 混淆 | 確認控制類型、分區擺放                   |
| 為了一個視覺小調整寫了 5+ 條 CSS       | 覆寫深度過深      | 評估改善價值 vs 維護成本、考慮接受原設計 |
| 同一個 UI 元素在三種瀏覽器表現不同     | UA 差異浮現       | 跨瀏覽器測試、決定是否值得統一           |

**核心原則**：UI 決策不只是技術選擇 — 順序、語意、覆寫深度都涉及成本權衡。一行 CSS 決定的事，背後常有設計判斷。
