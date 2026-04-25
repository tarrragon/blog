---
title: "Pattern：Document 全文件 query"
date: 2026-04-25
weight: 46
description: "`document.querySelector` 從整個頁面找元素 — 是探索期與一次性 script 的合理工具、不是 production 客製的預設。本文展開這個 pattern 的適用邊界。"
tags: ["report", "pattern", "JavaScript", "DOM"]
---

## 核心做法

```js
document.querySelector('.target');
document.querySelectorAll('.target');
```

從整個頁面找元素、不指定 ancestor scope。

---

## 這個做法存在的價值

簡潔。一行就能取到目標、不需要先建立元件根變數。在「我只想快速確認某個元素在不在 / 取它的某個屬性」這類情境下、寫一個 import shell 變數 + null check 是過度工程。

---

## 適合的情境

| 情境 | 為什麼合理 |
|------|----------|
| Devtools console 一行查詢 | 沒有「未來會壞」的問題、用完就丟 |
| 原型 / spike 階段程式碼 | 預期會被丟棄重寫、不需要長期維護考量 |
| 確定全頁唯一的單例（`document.body`、`<html>`） | 從定義上不會多個、也不會被誤命中 |
| Build-time script、不會在 runtime 跑 | 沒有「同頁多元件」的可能性 |

核心特徵：**這段程式不會在多元件 / 動態 DOM 環境長期存活**。

---

## 不適合的情境

| 情境 | 失敗模式 |
|------|---------|
| Production 客製、預期長期存活 | 未來頁面結構變動、誤命中或漏命中 |
| 同頁可能有多個同類元件 | 只取第一個、其他被忽略且不報錯 |
| 元件可能在 SPA 路由中動態增減 | query 時機跟元件 mount 時機不對齊 |
| 寫入第三方函式庫 | 使用者頁面的其他 class 可能跟你的 selector 撞 |

**安靜失敗是最危險的特徵** — 不報錯、操作了錯元素、bug 表現遠離 root cause。

---

## 跟其他起點做法的關係

[#14 Selector 精準度](dom-selector-precision/) 的「起點」維度有四種做法、document query 是其中之一：

| 做法 | 比較 |
|------|------|
| 本卡片：document query | 簡潔但不防護未來變動 |
| [元件根變數](pattern-component-root/) | 多一行 setup、換到「shell 內隔離」 |
| [起點當參數](pattern-root-as-parameter/) | 多實例支援、適合可能擴展的客製 |
| [closest 反向找根](pattern-closest-lookup/) | 事件委派情境、動態元件 |

選擇順序：production 客製預設用「元件根變數」、原型 / 探索 / 一次性才用 document query。

---

## 邊界：什麼時候 document query 在 production 也合理

幾個常見的 production 例外：

```js
// 例外 1：操作的目標就是「全頁面唯一單例」
document.body.classList.add('page-search');
document.documentElement.setAttribute('data-theme', 'dark');

// 例外 2：跨元件邊界的元素（不在任何元件內）
var slot = document.querySelector('.search-filter-slot');
// (slot 是 main 的子節點、不在 search-shell 內、不能從 shell 找)

// 例外 3：頁面層級的 meta 元素
document.querySelector('meta[name="description"]');
```

例外都共享一個特徵：**目標元素本質上就在「頁面層級」、不是任何元件的內部**。

不是例外的場景、即使「當前頁面只有一個」、也用元件根變數 — 預防未來擴展。

---

## 判讀徵兆

| 訊號 | 該換做法嗎？ |
|------|----------|
| 「現在只有一個、之後再想」 | 是 — 換元件根變數 |
| 同檔案多處 `document.querySelector('.x')` | 是 — 至少改成存變數重用 |
| 寫第三方 library 用 document query | 是 — 改用根參數 pattern |
| 操作 `document.body` / `<html>` | 否 — 這就是合理場景 |
| 程式跑一次後丟棄（migration script） | 否 — 簡潔優先 |

**核心原則**：document query 不是反模式、是有適用範圍的工具。判斷「這段程式預期活多久」 — 短命用 document、長命用元件根。
