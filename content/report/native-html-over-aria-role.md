---
title: "Native HTML element 優先於 ARIA role 的取捨"
date: 2026-04-25
weight: 39
description: "用 `<fieldset><legend>` 比 `<div role=\"radiogroup\">` 安全、用 `<button>` 比 `<div role=\"button\">` 直接 — native element 自帶完整無障礙語意與行為。本文盤點 ARIA role 是 fallback、不是 default。"
tags: ["report", "事後檢討", "Accessibility", "ARIA", "工程方法論"]
---

## 核心原則

**有 native HTML element 提供的語意與行為時、永遠優先用 native — ARIA role 是「沒有 native 對應時的 fallback」、不是設計起點。** Native element 自帶 keyboard、focus、screen reader 行為；ARIA 是給作者宣告 semantic 的工具、需要作者自己補完所有行為。

---

## 為什麼 native 永遠優先

### 商業邏輯

ARIA 規範自己有一條 first rule：

> **First Rule of ARIA**: If you can use a native HTML element with the semantics and behavior you require already built in, instead of re-purposing an element and adding an ARIA role, do so.

理由是 native element 提供「semantic + behavior」雙包裝：

| 包裝層                               | Native element                    | ARIA role                   |
| ------------------------------------ | --------------------------------- | --------------------------- |
| Semantic（screen reader 知道是什麼） | 是                                | 是                          |
| 鍵盤行為                             | 是（瀏覽器內建）                  | 否（要作者自己寫）          |
| Focus 行為                           | 是（tab order、:focus）           | 否（要作者管 tabindex）     |
| Form 整合                            | 是（form submission、validation） | 否                          |
| 跨瀏覽器一致                         | 高（標準行為）                    | 中（看 screen reader 解讀） |

ARIA role 只貼 semantic 標籤、不送行為 — 用 ARIA 等於承擔「補完所有行為」的責任。

### 何時 ARIA 是必要

| 情境                                     | ARIA 必要              |
| ---------------------------------------- | ---------------------- |
| Native element 有對應功能                | 否 — 用 native         |
| 需要 semantic 但沒 native 對應           | 是 — 用 ARIA role      |
| 加強 native element 的描述（aria-label） | 是 — ARIA 補強、不取代 |
| 動態狀態（aria-expanded、aria-checked）  | 是 — native 表達不了   |

ARIA 的設計用途是「補強 native」、不是「取代 native」。

---

## 搜尋頁的具體風險點

### 風險 1：Scope UI 用 `div role="radiogroup"` 而非 `fieldset`

**位置**：

```html
<div class="search-scope" role="radiogroup" aria-label="搜尋範圍">
  <label><input type="radio" name="search-scope" value="all" checked><span>全部</span></label>
  <!-- ... -->
</div>
```

**判讀**：`<div role="radiogroup">` 給 screen reader 看到「這是 radio group」、但作者要自己保證：

- 鍵盤方向鍵在選項間切換
- Tab 行為符合 radiogroup 慣例（tab 進到 group、方向鍵在內切換、tab 出 group）
- aria-required / aria-invalid 等狀態同步

`<fieldset><legend>` 是 native element：

- 自帶 group semantic
- legend 自動關聯為 group label
- 內部 `<input type="radio" name="X">` 已是完整 radiogroup（HTML 內建）

**症狀**：screen reader 可能不認得自訂 radiogroup、無法用方向鍵切換。

**第一個該查的**：用 NVDA / VoiceOver 進入 radiogroup、按方向鍵看是否能切換。失敗則改用 fieldset。

```html
<fieldset class="search-scope">
  <legend>搜尋範圍</legend>
  <label><input type="radio" name="search-scope" value="all" checked> 全部</label>
  <label><input type="radio" name="search-scope" value="title"> 標題</label>
  <label><input type="radio" name="search-scope" value="content"> 內文</label>
</fieldset>
```

`name="search-scope"` 同名讓三個 radio 自動成為 group、HTML 自帶方向鍵切換。

### 風險 2：用 `<div onclick>` 取代 `<button>`

**位置**：自訂按鈕 UI（搜尋頁未必有、但常見 anti-pattern）。

**判讀**：

- `<button>` 自帶 enter / space 觸發、tab focus、disabled 狀態
- `<div onclick>` 只有 click 事件、鍵盤無法觸發、tab 不會 focus

**症狀**：鍵盤使用者無法操作該 UI。

**第一個該查的**：找 `<div onclick>` / `<span onclick>` 的 pattern、改為 `<button>`。

### 風險 3：Pagefind 自身的 ARIA 實作

**位置**：Pagefind 的 `<details><summary>` filter blocks。

**判讀**：

- `<details>` / `<summary>` 是 native element、自帶 expand / collapse、enter 切換
- Pagefind 包了 `.pagefind-ui__filter-name` class 但底層仍是 native — 行為跟著
- 這是好的設計、不需要動

**症狀**：rare、native element 多半 OK。

**第一個該查的**：確認 Pagefind 沒用 div+role 重新實作這些 — 從 source 看大致符合 native first principle。

### 風險 4：Search input 用 `<input type="search">` 還是 `<input type="text">`

**位置**：Pagefind 自身的 input。

**判讀**：

- `<input type="search">` 在 mobile 顯示「搜尋」鍵盤、自帶清除按鈕
- `<input type="text">` 純文字輸入

**症狀**：mobile 鍵盤不適配搜尋場景、額外清除 UI 自己做。

**第一個該查的**：確認 Pagefind 用 `type="search"`。從 pagefind-ui 渲染結果可看到 `type="text"`、有自訂的清除按鈕 — 可考慮是否值得改。

---

## 內在屬性比較：四種實作 radio group 的方式

| 實作                                                   | 鍵盤切換              | screen reader 認                       | 維護成本 |
| ------------------------------------------------------ | --------------------- | -------------------------------------- | -------- |
| `<fieldset><legend>` + `<input type="radio">` × N      | 是 — HTML 內建        | 是 — fieldset semantic                 | 低       |
| `<div role="radiogroup">` + `<input type="radio">` × N | 是 — input radio 自帶 | 部分 — div role 跟 input semantic 重複 | 中       |
| `<div role="radiogroup">` + `<div role="radio">` × N   | 否 — 要自己寫         | 是 — 但需作者完整實作 ARIA pattern     | 高       |
| 純自訂無 ARIA                                          | 否                    | 否                                     | 不適用   |

優先順序：**fieldset > div role + native input > div role + div role**。

---

## ARIA 使用的判斷流程

每個 UI 元素開始實作前、走這個流程：

```text
1. 有沒有 native element 對應？
   是 → 用 native（fieldset、button、input、details / summary）
   否 → 進 2

2. 有沒有 ARIA pattern 對應？
   是 → 用 div + role + 完整 ARIA 屬性 + 自己寫鍵盤行為
   否 → 進 3

3. 用 div + 自己想 semantic
   注意：可能 screen reader 不認得、需要充分測試
```

多數情境停在 1 — native HTML 涵蓋常見 UI 模式。需要走到 2、3 的場景比想像中少。

---

## 正確概念與常見替代方案的對照

### Native 自帶 semantic + behavior 雙包裝

**正確概念**：選 native element 等於同時拿到 semantic 標籤與鍵盤 / focus / form 行為。

**替代方案的不足**：用 div + role 取代 — 拿到 semantic 但要自己補完所有行為、容易漏。

### ARIA 是補強、不是取代

**正確概念**：ARIA 用在「native 已存在但需要額外資訊」（aria-label、aria-describedby）、「動態狀態」（aria-expanded、aria-checked）、「沒對應 native」的場景。

**替代方案的不足**：把 ARIA 當「無障礙的萬能解」、所有自訂 UI 都加 role — 多數情境用 native 更乾淨、ARIA 反而增加維護成本。

### 跨瀏覽器一致性靠 native

**正確概念**：Native element 行為由 HTML 標準定義、跨瀏覽器一致。

**替代方案的不足**：自訂 UI 跨瀏覽器測試 — Chrome / Safari / Firefox + 各 screen reader（NVDA / JAWS / VoiceOver）的組合測試不完。

---

## 判讀徵兆

| 訊號                                         | Refactor 動作                                  |
| -------------------------------------------- | ---------------------------------------------- |
| 用 `<div role="X">` 取代有 native 的 element | 評估改用 native、減少 ARIA 維護                |
| 自訂 UI 鍵盤無法操作                         | 改用 native button / input、自帶鍵盤行為       |
| 自訂 form 元素跟 form submission 不整合      | 改用 native input、自動加入 form data          |
| Screen reader 不一致地解讀 ARIA              | 改用 native、多數 screen reader 對 native 一致 |

**核心原則**：ARIA 的 first rule 是「能用 native 就不用 ARIA」。Native element 是 50 年累積的瀏覽器 + 輔助技術知識結晶、不要繞道。
