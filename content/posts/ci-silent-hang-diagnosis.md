---
title: "CI step silent hang：時間真空才是訊號、happy log 反而是 anti-signal"
date: 2026-05-28
description: "CI step timeout 時要區分『時間不夠』跟『silent hang』：訊號不是錯誤訊息、是『最後一行 happy log 到 cancel 之間的時間真空』。本文以本 blog Playwright CI 案例（Playwright 1.59 在 Node 24.16 的 extract-zip regression）拆解 silent hang 的識別訊號、第一輪歸因錯誤的 anatomy、與 upstream issue 搜尋的優先序。"
tags: ["ci", "github-actions", "debugging", "root-cause-analysis", "wrap"]
---

> **核心議題**：CI step 看起來「跑了很久才 timeout」時，要分辨「真的時間不夠」跟「silent hang 占滿時間」 — 兩者修法完全不同。Silent hang 的訊號是「最後一行 happy log 到 cancel 之間有大段時間真空」、不是「最後一行錯誤訊息」。第一次歸因錯誤後、第二次 fail 不該再加 timeout、該停下來重看 detailed log。
> **案例骨幹**：本 blog 的 Playwright CI 一直 timeout、初診「cache 缺失 + timeout 太緊」加了 cache + bump timeout、仍 timeout。重看 detailed log 發現 chromium 下載 2 秒完成、之後 24 分 31 秒**完全沒任何 log** 才被 cancel — Playwright 1.59 在 Node.js 24.16.0 的 extract-zip regression（[microsoft/playwright#41000](https://github.com/microsoft/playwright/issues/41000)、上游 [nodejs/node#63487](https://github.com/nodejs/node/issues/63487)）。升 Playwright 1.60.0 後該 step 從 25 分鐘卡死降到 22 秒。

---

## 1. Silent hang 是 happy log 的 anti-signal

CI step timeout 時、第一個本能是看「step 跑了多久」。15 分鐘 timeout 然後被砍、直覺判斷是「時間不夠、bump timeout」。這個直覺對應的失敗模式是「step 真的需要 16 分鐘才能跑完」。

但有另一種失敗模式長得很像、修法完全不同：**silent hang** — step 在某個點之後就不再輸出任何 log、process 仍在執行（沒有 crash）、直到外部 timeout 才被砍。表面看跟「時間不夠」一樣（step 跑很久才被 cancel）、但根因是 process 本身卡死、給多少時間都跑不完。

辨識 silent hang 的關鍵訊號是「最後一行 happy log 到 cancel 訊息之間有大段時間真空」。**「Happy log」指的是看起來成功的訊息**（例：下載 100% 完成、build succeeded、X tests passed）— 這類訊息特別會誤導判斷、因為它讓人以為任務在進展。Silent hang 開始之前的最後一行通常正是這種 happy log、是正常結束訊號的反面。

### 三類 timeout 模式的對照

| 訊號                                                | 可能根因                           | 修法                                          |
| --------------------------------------------------- | ---------------------------------- | --------------------------------------------- |
| 整個 step 進度持續、最後階段加速到 timeout          | 時間真的不夠                       | bump timeout                                  |
| 有失敗訊息（exception / non-zero exit）之後 timeout | code 邏輯錯                        | 看訊息修                                      |
| **最後一行 log 之後有大段時間真空、然後 cancel**    | **Silent hang**、可能 upstream bug | **查 upstream issue tracker、不是加 timeout** |

第三種最容易誤判、因為「log 之間沒輸出」沒被當成訊號 — 但**訊息真空本身就是訊號**。寫 debug log 的人會記得補 error 訊息、但 silent hang 通常發生在工具內部的某個沒輸出 log 的等待點、所以沒有 error 訊息可看。

---

## 2. 為什麼「cache 缺失 + bump timeout」的初診是 false positive

第一次看 CI fail log 時、有三件容易抓到的事：

1. workflow YAML 裡的 `timeout-minutes: 15`
2. step 跑了 `15m 6s`（幾乎等於 timeout 上限）
3. step 名稱是 `Install Playwright browsers`（要下載 170 MiB）

直覺合成的結論：「cache 缺失 + timeout 太緊」。這結論看起來「應該對」 — 因為這兩個都是「Install Playwright browsers」眾所周知的優化點。修法：加 `actions/cache` + bump timeout 25 min。

修完仍 timeout、但這次跑 `25m 6s`（一樣頂到上限）。

**這時的訊號應該是「同樣的 step 在 1.67 倍的 timeout 下仍頂到上限」** — 如果是時間不夠、bump 之後該往中間靠（譬如完成在 18-20 min）；如果一直頂到上限、意思是 step 不會自己結束、是 hang。

但初診時很容易略過這個訊號、轉而繼續想「是不是 cache step 設定有問題？」。這個歸因方向是錯的、因為前置假設「cache 是瓶頸」本身就沒驗證過。

### 一輪 false positive 的 anatomy

| 步驟              | 容易做的                | 該做的                                         |
| ----------------- | ----------------------- | ---------------------------------------------- |
| 看到 timeout      | 假設「時間不夠」        | 先區分「時間不夠」vs「silent hang」            |
| 看 high-level log | 假設「下載慢」          | 應該看下載前後 timestamp 比對                  |
| 提解法            | 加 cache + bump timeout | 應該先確認瓶頸真的在下載                       |
| 解法仍 fail       | 假設「cache 沒 hit」    | 應該意識到「同個 step 又頂到上限」是 hang 訊號 |

每一步單看都合理、合起來就是把 false positive 越雕越精緻。這個 anatomy 對任何「初診沒驗證就改」的場景都適用、不限 CI。

---

## 3. WRAP 的 R 在第二次 fail 時是 stop 訊號

WRAP 決策框架的 R（Reality Test）原則是「需要什麼事證才能證明這個方法可行？」。它不只是決策前的檢查、更是**連續失敗後的 stop 訊號**。

第二次 fail 時、繼續同方向加 timeout 是自動駕駛模式。WRAP 在這個位置該提醒的事：

- 「兩次同類修法都沒解、是不是前置假設錯了？」
- 「我有沒有資料去判斷真正卡哪？」（資料充足度閘門）
- 「同類問題的 base rate 是什麼？」（基本率思考）

**Stop 訊號的觸發條件是「同方向修法連續 fail 2 次」、不是「fail 3 次」**。第二次就該回到資料層；第三次已經是浪費 cycle 而且強化錯誤假設。

實際上第二次 fail 後做的對的事是停下來、grep detailed log 的 timestamp 序列、發現「下載完成」跟「cancel」之間有 24 分鐘空白 — 這時才確認是 silent hang。如果第二次沒做這個轉折、第三次大概率是「換更大的 timeout」或「換不同的 cache key」、仍 fail。

---

## 4. Detailed log 的關鍵讀法：找「沒輸出的時間段」

CI 平台的 step log 通常很長、人眼掃容易跳過。看 silent hang 嫌疑時、讀法不是順序讀、是抓四個 timestamp：

1. **Step 開始的 timestamp**（log header 通常有）
2. **Step 結束（cancel / fail）的 timestamp**
3. **最後一行有意義輸出的 timestamp**
4. 計算 #3 到 #2 之間的時間真空

真空夠大（> 1 分鐘）+ #3 是 happy log = silent hang 嫌疑高。

GitHub Actions 用 `gh` CLI 的具體做法：

```bash
# 取某個 step 的所有 log（filter step 名稱）
gh run view <run-id> --log --job <job-id> | rg "Install Playwright browsers"

# 抓最後幾行看真空尾巴
gh run view <run-id> --log --job <job-id> | rg "Install Playwright browsers" | tail -3
```

本案例的最後 3 行（簡化過）：

```text
2026-05-27T09:59:44.110Z  | 100% of 170.4 MiB
2026-05-27T10:24:15.201Z  ##[error]The operation was canceled.
```

24 分 31 秒真空、最後一行 happy log 是「下載 100% 完成」 — silent hang 確認。

這個讀法的核心是「**時間真空優先於訊息內容**」。技術人員習慣讀訊息內容找 error keyword、但 silent hang 沒有 error keyword 可找、只有時間真空。轉個訊號類型才看得到。

---

## 5. Upstream issue 搜尋的優先序

Silent hang 確認後、下一步通常**不是繼續 reason 根因**、是去查 upstream issue tracker。Silent hang 多半是工具 / 依賴的 bug、而非自己 config 錯 — 因為 config 錯通常有 error message、不會 silent。

查詢策略：

```bash
gh api 'search/issues?q=repo:<upstream>/<repo>+<symptom keywords>+is:issue&per_page=10&sort=updated'
```

關鍵是 **keyword 選擇用「症狀詞」而不是「猜測詞」**。症狀詞描述讀者實際觀察到的現象（`hangs after download`、`stuck during extract`），猜測詞描述讀者推測的根因（`slow`、`timeout`、`network issue`）。猜測詞會找到大量無關 issue；症狀詞通常直接命中。

本案例查詢 `playwright install hangs chromium` 第二筆結果就是 issue #41000、標題完全匹配「`playwright install chromium` hangs after download completes on Node.js 24.16.0 (extract-zip)」。Issue 詳情指向上游 [nodejs/node#63487](https://github.com/nodejs/node/issues/63487)、給出兩個 workaround（升 Playwright 1.60.0 或 pin Node 24.15.0）。從查詢到確認根因、全程不到 5 分鐘。

### 為什麼 issue tracker 該優先於 self-reasoning

技術人員的 instinct 是「自己想出根因」。但 CI silent hang 這類問題、根因通常在工具版本、runtime 版本、OS、container image 的微妙交互、不在自己的 codebase。**Reasoning 找不到的東西、社群 issue tracker 經常已經有人回報過**。

「先 reason 再查」跟「先查再 reason」的取捨：

| 問題範圍                                      | 哪個優先 | 為什麼                                         |
| --------------------------------------------- | -------- | ---------------------------------------------- |
| 自己 codebase 內的邏輯 bug                    | reason   | 自己最熟、reasoning 通常較快                   |
| Upstream tool / runtime / OS / container 範圍 | 查 issue | 自己沒上游知識、reasoning 容易卡在錯誤前置假設 |
| 兩者交界（自己 config 觸發 upstream bug）     | 並行     | 先查找 known issue、同時 reason 自己 config    |

Silent hang 預設屬於第二類、應該優先查 issue tracker。

---

## 6. 整合：訊號 → 行動 mapping

把本案例的經驗整理成可重用的訊號表：

| 訊號                                | 行動                                              |
| ----------------------------------- | ------------------------------------------------- |
| Step timeout 且最後一行是 happy log | 計算 timestamp 真空、確認是否 silent hang         |
| 同方向修法 2 次都 fail              | 停止、回到資料層、不再加 timeout / retry          |
| Silent hang 確認                    | 用症狀詞查 upstream issue tracker                 |
| Issue 命中且有 workaround           | 套 workaround、不要先 reason                      |
| Issue 沒命中                        | 才回到 self-debug、加 verbose log（`DEBUG=` env） |

這張表的順序很重要：每一步的「該做的事」是下一步的「前置條件」。略過任一步、後面的判斷會建立在錯誤假設上。

---

## 適用範圍

「Silent log 是 happy log 的 anti-signal」這個原則對所有非互動 process（CI、cron job、background worker、container init）都適用：

- **Docker build 卡住**（特別是 RUN apt-get / npm install / pip install）— 同類 silent hang 模式
- **CI cache restore 卡住** — 大量小檔案的 cache 操作可能 silent hang
- **Database migration 卡住** — schema 變更 + 長 transaction 可能 silent hang
- **任何 process 跑時間接近 timeout 上限被 cancel** — 先檢查是否 silent hang 才提解法

「WRAP R 在第二次 fail 時是 stop 訊號」這條原則不限 CI、適用所有「同方向修法重複 fail」的場景：debug、設定調校、效能優化。

---

## 參考資料

- [microsoft/playwright issue #41000](https://github.com/microsoft/playwright/issues/41000) — 本案例的 upstream issue（Playwright 1.57-1.59 在 Node 24.16.0 extract-zip hang）
- [nodejs/node issue #63487](https://github.com/nodejs/node/issues/63487) — Node 24.16 extract-zip / yauzl regression 上游
- 同 blog 文章：[WRAP 決策框架的 R 階段操作](/skills/wrap-decision/) — Reality Test 詳細用法
