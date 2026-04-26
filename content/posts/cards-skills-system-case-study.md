---
title: "Cards-Skills 系統的活案例：從一個 search bug 到 14 張新卡的閉環"
date: 2026-04-26
description: "把 content/report/ 的 atomic cards + .claude/skills/ 的 protocol skills 當成「活的 knowledge infrastructure」、而不是靜態文件。本文以一次 search filter bug 修復為主軸、紀錄 28 個 commits 的閉環過程：從 bug 提出 → 拆卡片 → 抽抽象原則 → 灌進 skill → 指導實作 → retrospective 找漏網 case → 再迭代。八輪迭代讓系統從 54 卡長到 71 卡 + 兩個 skill v0.2、過程中卡片自我修正、修了實作也修了 dogfooding 失敗。"
tags: ["case-study", "知識基礎建設", "compositional-writing", "Cards-Skills", "TDD", "Retrospective"]
---

## 這篇要說什麼

`content/report/` 累積了 70+ 張原子化事後檢討卡片、`.claude/skills/` 收錄三個 protocol skill。這些不是靜態文件 — 是用來指導下一輪實作、又會被下一輪實作的學習回流修正的活基礎建設。

本文把這套系統實際跑一輪的歷程紀錄下來、當未來「想用這套系統的人」的 onboarding case study。主軸是修一個 search filter bug — 看似一週工作、實際走完八輪迭代、產出 14 張新卡片 + 兩個 skill 的 v0.2 + 4 個 CI test、過程中還抓到自己的 dogfooding 失敗、回頭修一次。

---

## 起點：使用者問題

"我們搜尋頁的 標題/內文篩選功能現在雖然做出來了、但是還是有一個很嚴重的 BUG"

具體：Pagefind 分批 load、view 層 post-filter；切到 title-only 後、第二批 load more 的 8 筆全部 title 不含 query → 全 hidden、畫面閃但內容沒變、使用者看到「load more 沒效果」silent 失敗。

User 還明確補了一句：「**所以除了用 JS 取巧解決畫面、但是實際功能面上怎麼配合跟實作 我們並沒有解決**」— 這已經點到核心：問題不在畫面、在抽象層。

---

## 第一輪：拆卡片之前先想清楚

直接修 bug 是可選但不是 user 要的。User 強調：「**先思考我的需求、然後思考各種狀況的邊界**」。

依當時的兩個 skill — `requirement-protocol`（對話協議）跟 `frontend-with-playwright`（前端執行協議）— 把問題分解：

1. **Bug 的結構性根因**：filter 寫在視覺層、source 在資料層分批、兩層的「一筆」定義不一致 → silent 缺口
2. **解法策略空間**：5 個合理選項（推進 query / 自動續抓 / 多 index / 誠實 UX / 明示縮小）— 每個機會成本不同
3. **跨領域通用性**：這結構不只前端有 — 後端 middleware filter、map-reduce、SQL view 都同模式

User 的關鍵回應：「**這部份可以補充 SKILL 中演算法不足的原因 ... 卡片是經過多次迭代、擴充、然後分拆、再擴充、最後做連結**」。

明確了協作方式：先建卡片、再灌進 skill、最後才修。卡片本身要走原子化拆解 → 補充 → 反向擴充 → 連結的多輪迭代。

---

## 14 張卡片的拆解（第一冷啟）

依 user 對 atomic 的標準（一卡一議題、一個議題多面向 OK、議題太多就拆），列出 10 張卡片提案：

| 分組     | 卡片                                                                       |
| -------- | -------------------------------------------------------------------------- |
| 問題分析 | #55 層錯位 / #56 視覺完成 ≠ 功能完成 / #57 三狀態區分                      |
| 指令澄清 | #58 篩選類指令的澄清時機                                                   |
| 解法策略 | #59 五策略對照 + #60-62 三張 pattern 卡（自動續抓 / 推進 query / 誠實 UX） |
| 抽象原則 | #63 資料源形狀 / #64 同層合成                                              |

冷啟版本一次寫完不求完美 — 約 1700 行、各卡 self-contained。

---

## 七輪迭代

### 迭代 1：抽 Pattern + 瘦身

寫完 #59 五策略後、發現 A/B/C/D/E 中 C（多 index）、E（明示縮小）沒對應 pattern 卡。抽出 #65 / #66 補完 pattern 卡組。同時瘦身 #59 → 純路由（細節留 pattern 卡）、#55 + #57 移除跟 #63 重複的「四類資料源」段。

### 迭代 2：補概念深度

回頭讀 #56 / #63 / #64、補抽象層的「為什麼」：

- #56 加「驗收的時間軸：四個 checkpoint」概念
- #63 加「形狀識別 protocol」+「形狀混合」+「形狀的可改造性」
- #64 加「跨領域通用的本質 = 資訊可見範圍」+「上推代價」

### 迭代 3：跨卡連結

新卡跟 #1-#54 既有卡互相補連結。例如 #55 ↔ #11 playwright、#57 ↔ #38 aria-live、#58 ↔ #21 decide-vs-confirm、#64 ↔ #43 minimum-scope + #44 SSOT。整個 collection 從兩個獨立輪次變一張互連網。

### 迭代 4：抽更高層原則

重讀新卡發現兩個議題夠 abstract、值得抽獨立卡：

- **#67 寫作便利度跟意圖對齊反相關** — 從「為什麼層錯位 bug 容易寫出來」抽出。發現它是 #43 / #44 / #45 / #64 的共同上位原則：**便利位置 vs 對齊位置永遠反相關**
- **#68 驗收的時間軸：四個 checkpoint** — 從 #56 抽出獨立成卡

### 迭代 5：跨輪共骨

系統性掃 #1-#54 找跟新系列共骨的、加連結。例：#6 filter-order ↔ #58 / #59、#10 placeholder ↔ #68、#15 layout-test ↔ #68、#14 selector / #20 failure / #28 class-toggle ↔ #67。

### 迭代 6：#67/#68 加深

再讀兩張抽象卡、補「為什麼人會違反這條規則」的結構性解釋：

- #67 加「便利度的時間維度：當下便利 vs 未來便利反向」+「我等下會 refactor 是個謊言」
- #68 加「為什麼 Ship 前 checkpoint 最常被跳過」（沒便利路徑）+「瀑布原則：漏一層代價指數放大」

從「規則陳述」進到「結構性解釋」 — 不只說「該怎麼做」、也說「為什麼人會違反」。

### 迭代 7：compositional-writing 規範稽核

User 提醒「再做一次 compositional-writing 的檢查」。發現兩類違規：

1. **Rule 7 違規**：26 處「X 才合理的情境：實務上幾乎不存在」假反模式 — 改成「X 是反模式：理由」格式
2. **結構違規**：#67/#68 是抽象層原則卡、不該寫設計取捨 ABCD（情境檢討卡的格式）— 改成「不該套用本原則的情境」（適用邊界）

修完 31 張卡片（含既有 #1-#54）。整個 collection 對齊 v0.6 規範。

---

## 灌進 Skills

把 #55-#68 系列接進兩個 skill：

- **requirement-protocol v0.2**：clarifying-ambiguous-instructions 加第 5 類「篩選類」+ 三問模板（呼應 #58）；SKILL.md 加「相關抽象層原則」段路由 #42-45 + #67-68
- **frontend-with-playwright v0.2**：新增第 7 份 reference `data-flow-and-filter-composition`（涵蓋 #55-#66 跨領域範例）；強調「不只前端、適用後端 / 演算法 / DB」

Skill 的角色 = 路由器、Reports = 深度內容 — 兩層分工不重述。

---

## 實作：策略 C + Phase 1-4

依 #59 + Pagefind 1.5.2 capabilities：

- **A 推進 query** ❌（Pagefind 無 native title filter API）
- **C 多 index** ✅（最對齊意圖）
- B / D / E 是 fallback

Phase 1-4：

1. Makefile 跑 3 輪 pagefind（all / title / content）
2. single.html `<content>` → `<div class="article-body" data-pagefind-body>`
3. search.html 移除 view 層 post-filter、改 destroy + new PagefindUI(bundlePath)
4. 4 個 Playwright tests 固化

跑出來：`make site` 三 index 成功、`make test` 4/4 PASS、live 驗證 sparse case 顯示 explicit empty。**看起來完工**。

---

## User 抓到 dogfooding 失敗 — 第 8 輪

User 問：「**剛剛的過程我不確定、你開始修改之前有先寫測試確保符合預測狀態、然後才調整嗎？**」

沒有。流程是：先修 → 才補測試 → 4/4 GREEN。**沒走 RED**。

這是 #67「便利驅動」+ #68「Checkpoint 2/3 內部協議」的 dogfooding 失敗。我寫了 #67/#68 教這些原則、自己卻違反。

依 user 規範：先建卡片再修。抽 **#69 Test-First：先看到 RED 才相信 GREEN**：

- 測試本身是程式、會有 bug（5 種失敗模式）
- 沒看過 RED = 不知道測試有沒有 catch 能力
- RED → GREEN 兩個訊號都看到 = 測試 + 修復都被驗證

retrospective 補驗證流程：checkout pre-fix commit → cherry-pick test → build → run（看 RED）→ restore → run（看 GREEN）。

跑下去 — 結果震撼：**4 個測試只有 1 個真的 catch 到 bug、其他 3 個對 buggy code 也 PASS**（placebo）。如果不做 retrospective、會帶著 3/4 placebo 測試 ship。

強化測試（network-level + structural assertion 替換弱 invariant）：buggy code 1 PASS / 3 FAIL ✓、fixed code 4 PASS ✓。RED-GREEN 真的 catch 到 bug + 真的解掉。

---

## User 抓到第二個 dogfooding 失敗 — Checkpoint 1

我問 user 還有什麼該迭代。User 列了 7 項、選 1+2：

1. 補 Checkpoint 1（列使用者意圖完整集）
2. 跟 user 確認 known limitations

跑 Checkpoint 1 retrospective — 用 Playwright MCP 系統性測 5 維度（data / interaction / URL / a11y / performance）。發現 3 個 silent 缺口：

| 維度      | 漏掉的 case                           | 結論            |
| --------- | ------------------------------------- | --------------- |
| URL state | `?q=X&scope=Y` 持久化                 | 完全沒實作      |
| A11y      | Tab order: scope 在 search input 之前 | 反 mental model |
| Filter UX | type/tag filter 在 sub-mode 完全消失  | Silent 限制     |

依 user 規範：**先建卡片再修**。抽：

- **#70 URL 是 stateful UI 的儲存層** — 5 個儲存層特性對照 + 三問判準
- **#71 Tab Order = DOM Order = Mental Model 三者對齊** — DOM 順序 = tab 順序、不對齊時優先重排 DOM
- 更新 #68 加「為什麼 Checkpoint 1 也常被跳過」段、用本次任務當 self-case

然後實作 — 依 #69 RED-GREEN 順序：

1. 寫 4 個 RED tests
2. 跑 → 4 個 fail（confirms RED）
3. 修 search.html（URL persist + DOM reorder + UI hint）
4. 跑 → 8/8 GREEN

---

## CI + 自動化

最後補 CI 防護：

- **`.github/workflows/playwright.yml`** — push / PR 自動跑 8 個 tests
- **`deploy.yml` 修 critical bug** — production 一直只 build 單 index、現在 build 三份對齊本地
- **`make test` + `make verify-red-green PRE_FIX=<sha>`** — codify retrospective 流程、不需手動 stash / checkout / restore

---

## 數字總結

| 維度                 | 數字                                                                   |
| -------------------- | ---------------------------------------------------------------------- |
| Commits              | 30+                                                                    |
| 新卡片               | 17（#55-#71）                                                          |
| 既有卡修改           | 31 張（rule 7 稽核）                                                   |
| 新 skill reference   | 1（data-flow-and-filter-composition）                                  |
| Skill 版本           | requirement-protocol v0.1 → v0.2、frontend-with-playwright v0.1 → v0.2 |
| Playwright tests     | 8                                                                      |
| RED-GREEN cycles     | 2（初版測試 + 強化版）                                                 |
| CI workflows 加 / 修 | 2（新增 playwright + 修 deploy multi-index）                           |

---

## 學到什麼

### 1. Cards-skills 系統是雙向的

不是「先寫卡片、再用卡片」。是「卡片指導實作、實作問題回流卡片」。每一輪迭代都把學到的東西反饋。本次 14 張新卡有 8 張是修過程中實際遇到的問題抽出來的、不是預先想的。

### 2. User 提問是「外部觸發」

我自己跑 #67 / #68 / Checkpoint 1 的機率低 — 因為這些都是「沒便利路徑」的工作。User 的兩次提問（「有先寫測試嗎」+「需求確認最重要功能」）剛好對應 #69 + Checkpoint 1 的觸發。**結構性偏差需要外部觸發來修正、不能靠自我提醒**。

### 3. Test 過 ≠ 對齊使用者意圖

第一輪修完、跑 4/4 GREEN、看起來完工。實際漏了：

- 3 個測試是 placebo（沒做 RED 不知道）
- 3 個 silent 缺口（沒做 Checkpoint 1 不知道）

任何「跑得通就 OK」的訊號都低資訊量。Real 訊號 = 對照「使用者意圖完整集合」逐一驗收。

### 4. 一個 bug 修完 = 一個 case study 起點

如果停在「bug 修了、test 過了」、這次任務 5 個 commits 結束。User 的兩次提問把它變成 30+ 個 commits 的 case study、產出 17 張新卡 + 兩個 skill 升級 + CI 補強。**修 bug 是 trigger、不是終點**。

---

## 適合 reuse 這個流程的條件

不是每個 bug 都該走這套。適合的訊號：

- Bug 修法不直觀、會碰到多種策略選項（→ 需要 #59 類取捨架構）
- 修法可能影響其他 feature 或產生新案例（→ 需要 Checkpoint 1）
- 需要長期 regression 防護（→ 需要 #69 RED-GREEN 驗證）
- 修的過程中發現新原則（→ 抽卡片）

不適合：純 typo / config / build 失敗 — 直接修。

---

## 對未來想用這套系統的人

進入點：

1. 讀 `content/skills/_index.md` — 三個 skill 的 routing table
2. 從你的問題情境找對應 skill：
   - 不確定怎麼跟 user 溝通 → `requirement-protocol`
   - 前端 / 資料流實作 → `frontend-with-playwright`
   - 寫文件 / 註解 / log → `compositional-writing`
3. Skill 路由你到 specific reference、reference 路由你到 `content/report/` 深度卡片
4. 修問題過程中發現新原則 → 抽卡片回流

「卡片不是在實作之前一次寫完、是在實作之中持續累積」 — 這套系統的 leverage 在於「下一個類似問題能直接用、不用重新發明」。

---

## 結語

`content/report/` 從 54 張長到 71 張、`.claude/skills/` 從 v0.1 進到 v0.2、CI 從假 pass 變真防護、search bug 從 silent 失敗變到 8/8 regression test 守護。

過程不是線性。是「先做 → 抓到 dogfooding 失敗 → 抽卡片 → 回頭修 → 再被抓失敗 → 再抽卡片 → 再修」。每一輪都讓系統往對齊使用者意圖的方向多走一點。

User 的角色關鍵：兩次提問都不在「指出 bug」、是在「指出我跳過的 checkpoint」。這是純執行者看不到的盲點 — 自己的 dogfooding 失敗。**外部 reviewer 是 cards-skills 系統的必要組件、不是 optional**。

下次有類似情境的人 — 不需要把這條路再走一遍、直接用 #55-#71 + 三個 skill 起步。如果發現新 case、抽新卡回流。系統的價值在每次使用都會變強。
