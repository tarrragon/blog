---
title: "寫作便利度跟意圖對齊反相關"
date: 2026-04-26
weight: 67
description: "寫程式時最容易寫出的版本、通常是離意圖最遠的版本。便利度建立在「現有上下文 / 已 materialize 資料 / 已存在 API」上、而意圖對齊需要找到正確的層、處理上游、跨抽象層 — 兩者方向相反。識別這個反相關 = 識別自己掉進「容易寫的陷阱」。"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層"]
---

## 核心原則

**寫程式時最容易寫出的版本、通常是離意圖最遠的版本。**

| 變數        | 寫作便利度高的特徵     | 意圖對齊高的特徵        |
| ----------- | ---------------------- | ----------------------- |
| 起點        | 用現成的 context / API | 找到正確的層            |
| 範圍        | 寬（捕魚式撈一遍）     | 窄（精準命中）          |
| 操作位置    | 下游（已 materialize） | 上游（stream / source） |
| 認知負擔    | 低（就地能解）         | 中-高（要回到上層分析） |
| Silent 風險 | 高（看起來能用）       | 低（強制處理邊界）      |

兩個方向反相關 — **越容易寫、越容易錯位**。識別這個反相關 = 識別自己正在掉進「容易寫的陷阱」、不是寫出對的東西。

---

## 為什麼便利度跟正確性反向

### 便利度的來源

寫程式當下、能「快速寫出」的條件是：

- 手邊已經有需要的資料（已 fetch、已 render、已 materialize）
- 現成的 API 能直接呼叫（`document.querySelectorAll`、`Array.from`、`results.filter`）
- 不需要跨抽象層（不用回到 source / framework 邊界 / build pipeline）

這些條件都建立在「**已是 subset / 已展開 / 已下游**」的位置 — 因為下游才有「現成上下文」。

### 意圖對齊的代價

「跟使用者意圖對齊」的條件相反：

- 操作 stream 全集（不是 subset）
- 在 source 層處理（不是 view 層）
- 處理 build-time 抽象（不是 runtime 取巧）

這些條件要求**回到上游 / 跨抽象層 / 處理沒被 materialize 的東西** — 而上游沒有「現成上下文」、需要刻意建立。

### 反相關的本質

便利度 = 用已有資訊；意圖對齊 = 處理還沒有的資訊。**資訊狀態相反 → 兩個目標反相關**。

「容易寫」這件事本身就是「在錯位的層」的徵兆。不是「容易寫的有時候錯」、是「容易寫的多半錯」。

---

## 多面向：跨領域的同個結構

### 面向 1：Filter 在 view 層（#55 的 case）

容易寫：`document.querySelectorAll('.result').forEach(el => el.hidden = !matches(el))` — 5 行、用現成 DOM。

意圖對齊：把 filter 推到 source 層（[#61](../pattern-query-side-pushdown/)）— 改 SDK 呼叫、可能改 build。

「為什麼層錯位的 bug 容易寫出來」見 [#55 Filter 與 Source 的層錯位](../view-layer-filter-vs-source-layer/)。

### 面向 2：Selector 用過寬範圍

容易寫：`document.querySelectorAll('.title')` — 一行命中所有 `.title`。

意圖對齊：`document.querySelector('.pagefind-ui').querySelectorAll(':scope > .results > .result > .title')` — 起點 + 範圍 + 過濾顯式設計（[#14](../dom-selector-precision/) / [#43](../minimum-necessary-scope-is-sanity-defense/)）。

過寬 selector 的代價是「命中無關元素 → 副作用未知」 — 但寫的時候不會看到。

### 面向 3：Inline style + !important

容易寫：`el.style.setProperty('display', 'none', 'important')` — 立刻生效。

意圖對齊：`el.classList.toggle('is-hidden')` + CSS class（[#28](../class-toggle-over-important/)）— 樣式留 CSS、JS 只 toggle state。

Important 是「立刻生效」的便利、代價是「DevTools 看不出為什麼」、改視覺要 grep 多處。

### 面向 4：Middleware filter（後端 case）

容易寫：在 API response 後加 filter middleware — 對 response array 做 `.filter()`。

意圖對齊：把 filter 推進 ORM query / SQL `WHERE` — 改 query、可能加 index。

Middleware 在 pagination 之後、漏掉沒在這頁的符合項（[#64](../compose-feature-at-source-layer/)）。

### 面向 5：Cached subset 上算統計

容易寫：`stats.average = cache.values().reduce(...) / cache.size` — 直接用 cache。

意圖對齊：先 revalidate、再算；或標明「statistic on cached subset」（[#66](../pattern-explicit-semantic-narrowing/)）。

Cache subset 算出的統計跟 fresh dataset 算出的不同、但寫的時候看不到差異。

**五個面向共用結構**：用「已存在的東西」5 行解決、產出對「沒處理到的東西」silent 失敗的版本。

---

## 識別訊號：什麼時候你正掉進這個陷阱

### 訊號 1：「這樣寫最快」

內心 OS「直接 forEach + filter 就好」「就用現成的 API 啊」 — 「最快 / 現成」這兩個詞通常標記下游 / subset 位置。

### 訊號 2：跨層的成本看起來高、但本層解看起來夠

「為了一個 filter 改 build pipeline 太誇張了吧」「直接前端 filter 不就好了」 — 這個內心 OS 在錯估、因為下游解的 silent 風險不在當下顯露。

### 訊號 3：寫完手動測一次就過

第 1 次 happy path 過了、覺得對。但 happy path 過 = 子集裡有命中、不證明 stream 全集對齊。同 [#42 2 次門檻](../two-occurrence-threshold/)：第 1 次成功是低資訊量訊號。

### 訊號 4：「先這樣、晚點補資料層」

這個想法本身就是「我知道這寫法不對齊意圖、但便利度太高」 — 補不回來、會 ship 進 production silent 失敗。同 [#56 視覺完成 ≠ 功能完成](../visual-completion-vs-functional-completion/)。

---

## 設計取捨：要選便利還是對齊

### A：寫之前先評估「容易 vs 對」

- **機制**：開工前自問「現在這個寫法是因為它對、還是因為它容易」、便利訊號 ≥ 2 個就停下重新評估
- **選 A 的理由**：把反相關變成主動識別、避免事後修
- **代價**：寫之前花 1-2 分鐘評估

### B：先寫便利版、用測試 / 邊界 case 補強

- **機制**：寫便利版能用、再補單元測試 / e2e / 規模 case 試出層錯位
- **跟 A 的取捨**：B 短期速度快、長期測試成本高（因為架構選錯）
- **B 才合理的情境**：原型期、預期方向會大改

### C：先寫便利版、加 explicit 語意縮小

- **機制**：用 [#66 明示語意縮小](../pattern-explicit-semantic-narrowing/) 把「便利版的限制」攤給使用者、不假裝是對齊版
- **跟 A 的取捨**：C 接受不對齊、但避免 silent 失敗；A 真的對齊
- **C 才合理的情境**：對齊成本太高、且使用者能接受縮小

### D：寫便利版、不告知

- **D 成本特別高的原因**：silent 失敗 + 使用者基於錯訊號決策、信任損失（同 #55 silent post-filter）
- **D 才合理的情境**：實務上幾乎不存在

選擇順序：**A → B → C → D**。

---

## 跟其他抽象層原則的關係

| 原則                                                                | 跟本卡的關係                                         |
| ------------------------------------------------------------------- | ---------------------------------------------------- |
| [#42 2 次門檻](../two-occurrence-threshold/)                        | 「容易寫」是低資訊量訊號、跟「第 1 次成功」同類      |
| [#43 最小必要範圍](../minimum-necessary-scope-is-sanity-defense/)   | 寬範圍是便利、窄範圍是對齊 — 同個反相關              |
| [#44 SSOT](../single-source-of-truth/)                              | 多源是便利（就地寫個值）、單源是對齊（找 fact 位置） |
| [#45 外部組件合作四層](../external-component-collaboration-layers/) | 內部結構層便利、公共介面層對齊                       |
| [#64 同層合成](../compose-feature-at-source-layer/)                 | 下游合成便利、上游合成對齊                           |

本卡是這幾條的共同上位原則 — 它們都是「**便利 vs 正確性的取捨**」在不同情境的具體展現。

---

## 判讀徵兆

| 訊號                                       | 該做的行動                                   |
| ------------------------------------------ | -------------------------------------------- |
| 內心 OS：「這樣寫最快」「直接用現成 API」  | 停 — 評估「快」是不是「在錯層」的徵兆        |
| 5 行解決一個原本應該跨層的問題             | 是 — 跨層通常 50+ 行、5 行是訊號             |
| 跨層解的工程量看起來「不值得」             | 注意 — 你可能在錯估 silent 風險的代價        |
| 「先做、晚點補上游」                       | 補不回來、要嘛當下做、要嘛接受 explicit 縮小 |
| 寫完 happy path 一次就過                   | 補規模 / 稀疏 / 跨情境驗證                   |
| 程式跑得通、但你說不出為什麼這個位置是對的 | 這是「便利驅動」而不是「意圖驅動」的訊號     |

**核心原則**：寫程式當下的便利度跟正確性反相關、是因為兩者用的資訊狀態相反。識別「我現在在容易的位置」 = 識別「我可能在錯的層」。**便利度本身是個診斷訊號**、不是好東西。
