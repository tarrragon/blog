---
title: "驗收的時間軸：四個 checkpoint"
date: 2026-04-26
weight: 68
description: "驗收不是單一動作、是分散在四個時點（寫之前 / 開發中 / ship 前 / ship 後）的累積判斷。每個 checkpoint 能 catch 不同類型的失敗、成本不同。早期 checkpoint 抓越多、晚期 checkpoint 越輕鬆。實務上常常 collapse 成「寫的時候 + ship 後出問題才修」、跳過寫之前 / ship 前。"
tags: ["report", "事後檢討", "工程方法論", "驗收", "原則"]
---

## 核心原則

**驗收不是單一動作、是分散在四個時點的累積判斷。**

| Checkpoint | 時點                          | 能驗收的失敗類型                   | 成本           |
| ---------- | ----------------------------- | ---------------------------------- | -------------- |
| 寫之前     | 開工前列「使用者意圖完整集」  | 漏掉的 case、誤解的需求            | 低 — 列清單    |
| 開發中     | 寫一塊測一塊                  | 邏輯錯誤、視覺錯誤、單元失敗       | 中 — 小範圍    |
| Ship 前    | E2E 跑邊界 / 規模 / 失敗 case | 跨 case 整合錯、規模相依失敗、競態 | 高 — 設計 case |
| Ship 後    | 真實使用者紀錄、log monitor   | silent 缺口、長尾 case、罕見組合   | 最高 — 反應慢  |

每個 checkpoint 抓的失敗類型不同、跳過任一個 = 那類失敗會在更晚的 checkpoint 出現（或不出現、變成 silent bug）。

---

## 為什麼分散驗收、而不是集中

### 集中驗收的問題

「寫完一次驗收完整」這個想法看似省事、實際撞兩個牆：

1. **失敗類型不在同一時點**：開發中發現的是邏輯 bug、ship 前發現的是整合 bug、ship 後發現的是 silent 缺口 — 用同一種驗收方法不能 catch 全部
2. **成本指數爆炸**：到 ship 前才發現「需求理解錯」要重做整個 feature；到 ship 後才發現邏輯 bug 要熱修。早期 checkpoint 修一個 case 用 5 分鐘、ship 後修同個 case 用 5 小時

分散驗收 = 在每個 checkpoint catch 「該時點獨有的失敗類型」、累積成完整覆蓋。

### 早期 checkpoint 的槓桿

「寫之前」的成本最低（列清單 5 分鐘）但能 catch 最貴的失敗類型（需求理解錯 = 整個 feature 重做）。**ROI 最高**。

「Ship 後」的成本最高（使用者反映、需要熱修）但只能 catch 最罕見的失敗類型。ROI 最低。

實務上常常 collapse 成「寫的時候 + ship 後出問題才修」、跳過寫之前 / ship 前。這是把 ROI 倒過來。

---

## 四個 Checkpoint 各自驗收什麼

### Checkpoint 1：寫之前

**動作**：列「使用者意圖完整集合」 — happy path、邊界 case、失敗 case、規模 case 各列幾條。

**能 catch**：

- 需求理解跟使用者意圖不同
- 邊界 case 從一開始就忘了想
- 規模 case 沒考慮（10 筆 vs 10 萬筆行為不同）
- 隱含假設沒攤開（「應該都會有 title」「永遠不會空」）

**範例**：寫 filter 之前列：「title 含 X、content 含 X、兩者都含、都不含、source 全空、source 全是、稀疏 case、密集 case」 — 8 個 case 寫之前看見、實作時主動處理。

### Checkpoint 2：開發中

**動作**：寫一塊測一塊 — 單元跑通、視覺看一眼、邊改邊試。

**能 catch**：

- 邏輯錯誤（branch 寫錯、迴圈邊界錯）
- 視覺錯誤（layout 跑掉、樣式套錯）
- API 用錯（呼叫順序錯、參數錯）

**不能 catch**：

- 跨多個 case 的整合錯
- 規模相依失敗
- 競態 / async race
- 跨環境差異

### Checkpoint 3：Ship 前

**動作**：E2E 跑邊界 / 規模 / 失敗 case。

**能 catch**：

- 跨 case 整合錯（filter 切換 + load more 互動）
- 規模相依（500 筆時 jank）
- 競態（快速切換 query 時）
- 真實環境 case（slow network、large data）

**不能 catch**：

- 罕見組合（特定 user pattern）
- 真實使用者意外行為
- 長尾邊界（千分之一機率的狀態）

**這個 checkpoint 最常被跳過** — 因為設計 E2E case 成本高、要刻意製造規模 / 失敗 / 競態場景。但跳過 = ship 後才發現。

### Checkpoint 4：Ship 後

**動作**：log monitor、error tracking、使用者行為紀錄。

**能 catch**：

- silent 缺口（沒人 report、log 看出來）
- 罕見組合
- 真實使用者意外行為
- 跨時間退化（穩定 vs 漸變）

**特性**：成本最高、反應最慢、只能 catch 前三個 checkpoint 都漏的失敗。**價值在於「保底」、不是主力驗收**。

---

## 為什麼 Ship 前 checkpoint 最常被跳過

四個 checkpoint 中、Ship 前是被跳過機率最高的一個。原因是結構性的、不是隨機的：

| Checkpoint  | 觸發機制                | 是否有便利路徑                  |
| ----------- | ----------------------- | ------------------------------- |
| 寫之前      | 外部驅動（需求 / spec） | 有 — 別人推著走                 |
| 開發中      | 內建在寫的動作裡        | 有 — 寫一塊看一眼是反射動作     |
| **Ship 前** | **要主動設計 case**     | **沒有 — 需要刻意停下來想邊界** |
| Ship 後     | 被動（使用者反映）      | 有 — 別人推著走                 |

寫之前跟 Ship 後都是「被外部 / 別人推著」、有現成觸發；開發中是反射動作、不需要刻意。**只有 Ship 前需要寫的人主動停下、設計 E2E case、執行 case** — 沒有現成觸發、沒有便利路徑。

這正是 [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/) 在驗收動作上的應用：跟「便利路徑」對齊的 checkpoint 會被做、要「主動設計」的 checkpoint 會被跳。

修這個結構性偏差的方法：

- 把 Ship 前 case 設計列進開工前的「使用者意圖完整集合」（推到 Checkpoint 1、有便利路徑）
- 用 layout test / E2E test 把 case 固化（[#15](../layout-tests-with-playwright/)）— 寫一次、之後 CI 自動跑、不需要主動觸發
- 公司 / 團隊建立「Ship 前 checkpoint review」會議 — 把它變成外部驅動

---

## 瀑布原則：漏一層代價指數放大

漏掉一個 checkpoint 不是線性影響、是指數放大：

| 漏掉哪個 checkpoint | 該失敗會在哪 checkpoint 才被發現 | 修復成本                 |
| ------------------- | -------------------------------- | ------------------------ |
| 寫之前              | Ship 前（甚至 ship 後）          | 重做整個 feature（×100） |
| 開發中              | Ship 前                          | 改一個 module（×10）     |
| Ship 前             | Ship 後                          | 熱修 + 信任損失（×100）  |
| Ship 後             | 永遠不修                         | 累積技術債（不可估）     |

「Ship 後修 bug 多」不是「ship 後驗收做得好」、是「上游 checkpoint 沒做好把 bug 全推下來」 — 看起來在做事、實際在付出指數成本。

### 為什麼指數放大

每個 checkpoint 漏掉的失敗、進入下一個 checkpoint 時：

1. **Context 已經消失**：下一個 checkpoint 才發現時、寫的人可能已經在做其他事、要重建上下文
2. **依賴已經建立**：別的代碼已經依賴這個有 bug 的 feature、改一處要連帶改五處
3. **使用者已經受影響**：ship 後修還要處理使用者信任 / 資料一致性 / 通知

每多漏一層、上述三個因素都疊加、成本翻 N 倍而不是 +N。

### 防線概念：每個 checkpoint 是獨立防線

把驗收看成 **defense in depth** — 每個 checkpoint 是一道防線、漏掉一道下一道接住。但每道防線的修復成本不同、越上游越便宜。

跟 a11y 三道防線（[#37 動態 focus](../focus-management-on-dom-move/) / [#38 aria-live](../aria-live-for-dynamic-content/) / [#39 native HTML](../native-html-over-aria-role/)）共骨：分散獨立防線比集中單一防線更穩、因為單點失效不會打穿全系統。

---

## Checkpoint 之間的累積關係

每個 checkpoint 都該補前面的洞 — 不是等量分配、是優先填上游：

```text
[寫之前 ROI: 高]   抓需求 / 邊界 / 規模意圖
       ↓ 漏掉的進入下一層
[開發中 ROI: 中]   抓邏輯 / 視覺 / 單元
       ↓ 漏掉的進入下一層
[Ship 前 ROI: 中-低] 抓整合 / 規模 / 競態
       ↓ 漏掉的進入下一層
[Ship 後 ROI: 低]   抓罕見 / silent / 長尾
```

「Ship 後修 bug 多」= 上游 checkpoint 沒做好、不是「ship 後驗收做得好」。

---

## 跟其他原則的關係

### 跟 [#42 2 次門檻](../two-occurrence-threshold/)

「畫面對一次」「測試過一次」「使用者沒反映一次」都是低資訊量訊號 — 對應「開發中 checkpoint 過了一次」。第 2 次（跨多個 case / 規模 / 時間）才是真訊號 — 對應「ship 前 checkpoint 也過了」。

[#56 視覺完成 ≠ 功能完成](../visual-completion-vs-functional-completion/) 是這個關係在「視覺驗收」面向的應用。

### 跟 [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)

寫之前 checkpoint 列「意圖完整集」 = 跟便利度脫鉤、強制看見意圖。跳過 = 接受被便利驅動。

### 跟 [#56 視覺完成 ≠ 功能完成](../visual-completion-vs-functional-completion/)

「畫面對」是開發中 checkpoint 的訊號、不是終點訊號。把它當完工 = 跳過 ship 前 / ship 後 checkpoint。

---

## 不該套用本原則的情境

「驗收分散在四個時點」這條原則在 ship 給其他人的開發情境成立、但有合理例外：

| 情境               | 為什麼不該套用                                             |
| ------------------ | ---------------------------------------------------------- |
| 純 research / 實驗 | 不會 ship 給別人、ship 前 / ship 後 checkpoint 都不存在    |
| 一次性 script      | 跑完就丟、沒有「ship」這個階段、四 checkpoint 概念不適用   |
| 純 prototype       | 預期會被丟掉、ship 後 monitor 沒意義、開發中 checkpoint 夠 |
| 個人玩具專案       | 失敗只影響自己、信任損失成本 ≈ 0、可放寬                   |

四類共同特徵：**「ship 後的失敗成本」≈ 0** — 因為沒有真實使用者、沒有信任損失、沒有累積技術債。本原則的瀑布原則建立在「漏一層代價指數放大」上、ship 後成本為 0 時自然不放大。

判讀：寫之前自問「失敗會不會影響別人」 — 否 → 本原則可放寬；是 → 本原則嚴格適用。

---

## 判讀徵兆

| 訊號                                           | 該做的事                                            |
| ---------------------------------------------- | --------------------------------------------------- |
| 寫之前沒列「使用者意圖完整集合」               | 補 — 5 分鐘列、可以避免 5 小時重做                  |
| 開發中只測了 happy path                        | 補邊界 / 失敗 / 規模 case                           |
| Ship 前沒設計 E2E case、預設「能 build 就 OK」 | 加：規模 case + 競態 case + 失敗 case               |
| Ship 後沒 log / monitor                        | 加 — 保底 checkpoint 沒設 = 永遠不知道有 silent bug |
| Bug report 含「ship 後一週才被發現」           | 表示前三個 checkpoint 漏了、要回頭加固              |
| 內心 OS：「之後 QA / 使用者會發現」            | 是「集中驗收」幻覺、跳過早期 checkpoint             |

**核心原則**：驗收的價值在「分散在多個時點」、每個 checkpoint catch 不同類型的失敗。把驗收 collapse 成單一時點 = 接受該時點之外的失敗都 silent 通過。早期 checkpoint ROI 最高、跳過代價最大。

Checkpoint 2「開發中」+ Checkpoint 3「Ship 前」內部的具體協議：[#69 Test-First：先看到 RED 才相信 GREEN](../test-first-red-before-green/) — 寫測試 + 跑兩次（RED-buggy + GREEN-fixed）才能驗證測試本身有用。跳過 RED = 接受測試可能是壞的。
