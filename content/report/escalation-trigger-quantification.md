---
title: "升級 trigger 的量化設計：「不夠就升 Y」需要明確的「不夠」指標"
date: 2026-04-26
weight: 91
description: "「先做 L1、不夠時升 L2、再不夠升 L3」這個分批 ship 順序看似合理、但「不夠」沒量化就會 #72 結構性跳過 — 永遠覺得「再觀察一下」、永遠不升級。本卡定升級 trigger 的量化設計：閾值、觀測窗口、決策週期、自動 vs 人工觸發。預設是寫 L1 ship 時就同步定 L2 升級的 trigger 條件、不是 ship 後才想。"
tags: ["report", "事後檢討", "工程方法論", "原則", "Process", "Telemetry"]
---

## 結論

[#86 三層階梯](../capability-gap-three-layer-escalation/) 的「先 L1、不夠升 L2、再不夠升 L3」協議、最容易失敗的點是「不夠」沒量化：

- 沒指標 → 永遠覺得「再觀察一下」 → [#72 結構性跳過](../external-trigger-for-high-roi-work/)
- 指標模糊 → 哪天該升、哪天不該、無共識
- 指標太鬆 → 永遠不升、L1 一直撐到崩
- 指標太嚴 → 一個小波動就升、過度工程

正確設計：**L1 ship 時就同步定 L2 升級的 trigger 條件** — 閾值、觀測窗口、決策週期、誰負責決策。不是 ship 後再想。

---

## 為什麼「再觀察一下」永遠不會升級

「ship L1 → 看效果 → 不夠就升 L2」這個 plan 在沒量化時、實際發生的是：

1. L1 ship、everyone 開心
2. 偶爾有 user 抱怨、但「不知道是不是夠多」
3. 沒有明確 baseline、無法判斷「不夠」
4. 「再觀察一下」變固定回應
5. 半年過去、L2 沒 ship
6. 同類 capability gap 在第 N 個 feature 又發生
7. 「我們系統設計就這樣」變新 baseline

這是 [#72 高 ROI 無外部觸發](../external-trigger-for-high-roi-work/) 的具體 case — 升級是 L4（外部觸發）需要的工作、靠紀律失敗。

---

## 升級 trigger 的四元素

完整的升級 trigger 含四個元素：

### 1. Metric（量什麼）

具體可量化的數字、不是模糊「使用者體驗」：

| 場景               | Bad metric  | Good metric                              |
| ------------------ | ----------- | ---------------------------------------- |
| Search prefix-only | "user 抱怨" | Empty result 率（query 結果為 0 的比例） |
| Cache miss         | "感覺很慢"  | P95 latency、cache hit ratio             |
| Retry exhaustion   | "偶爾失敗"  | Retry-then-fail 率                       |
| Stale data         | "user 困惑" | Manual refresh 觸發率                    |

Metric 必須：

- 數值化（有單位、有 baseline）
- 自動量測（不靠 manual 收集）
- 跟 capability gap 直接相關（不是 proxy 的 proxy）

### 2. Threshold（什麼程度算「不夠」）

明確閾值、寫進 plan：

```text
Trigger：當 search empty result 率 > 15% 持續 2 週、升級 L2（C1 fallback）
Trigger：當 L2 ship 後 fallback 觸發率 > 30%、升級 L3（B1 build-time tokenize）
```

閾值不是猜的、要 justify：

- 從 baseline 推（現況 X、目標 Y、threshold = 中間某點）
- 從業務 SLA 推（acceptable miss rate）
- 從成本曲線推（升級成本 = 維持成本）

### 3. Window（觀察多久）

避免「一個 spike 就升」、也避免「永遠等」：

| Metric 性質            | 適合 window             |
| ---------------------- | ----------------------- |
| 高頻 query（每天千次） | 1-7 天                  |
| 中頻（每天百次）       | 2-4 週                  |
| 低頻（每天個位數）     | 1-3 月                  |
| 偶發 incident          | 累積計數而非時間 window |

Window 太短 = noise 主導、太長 = 真問題拖太久。

### 4. Decision cadence（誰、何時、how 決策）

「達到 threshold」不該是「自動升級」、是「自動觸發 review」：

| 元素        | 設計                                      |
| ----------- | ----------------------------------------- |
| 觸發點      | Threshold 達到時系統自動 alert / 開 issue |
| 決策者      | 預先指定（feature owner / tech lead）     |
| 決策週期    | 每月 review / 每 incident review          |
| 決策 output | "升級 / 不升級 + 理由"、寫進 log          |

關鍵：**決策動作有人擁有、有頻率**、不靠「想到再看」。

---

## L1 ship 時就定 trigger 的範本

寫 L1 plan 時、同時寫：

```yaml
# L1 (ship now)
strategy: UX hint
goal: close 50%+ capability gap
metric: search empty-result rate
baseline: 18% (measured pre-ship)
target: < 12% within 4 weeks
review: weekly

# L2 trigger (defined now, executes later)
trigger_metric: empty-result rate
trigger_threshold: > 15% for 2 consecutive weeks AFTER L1 ship
trigger_owner: search team
trigger_action: implement client-side substring fallback (C1)
trigger_eta: within 1 sprint of trigger firing

# L3 trigger (defined now, executes later)
trigger_metric: fallback hit rate (after L2 ship)
trigger_threshold: > 30% sustained for 4 weeks
trigger_owner: search team
trigger_action: implement build-time suffix tokens (B1)
trigger_eta: within 2 sprints of trigger firing
```

**ship L1 時、L2 / L3 已經有「上膛」的 trigger** — 不靠紀律、靠機制。

---

## 反模式

| 反模式                                  | 後果                                                        |
| --------------------------------------- | ----------------------------------------------------------- |
| 「ship L1、看狀況再說」沒寫 trigger     | 永遠不升級（[#72](../external-trigger-for-high-roi-work/)） |
| Metric 寫「user happiness」（不可量）   | 無法觸發                                                    |
| Threshold 沒 baseline justify           | 隨意設、無法防 over/under-trigger                           |
| Window 不寫                             | Spike 主導、或永遠等                                        |
| Trigger 沒 owner                        | 達到 threshold 沒人 act                                     |
| 「達到 threshold = 自動升級」           | 缺人工 review、可能 over-react                              |
| 達到 threshold 後決策延遲 1+ 個月       | Trigger 失去 timely value                                   |
| L1 / L2 / L3 升級 trigger 共用同 metric | 升級到 L2 後 L3 trigger 沒 reset                            |

---

## 何時不需要量化 trigger

| 情境                                       | 為什麼                                  |
| ------------------------------------------ | --------------------------------------- |
| L1 已知不夠（事前已有 evidence）           | 直接 ship L2、不用 trigger              |
| L1 是 placeholder、L2 / L3 同 PR 一起 ship | 沒有「升級」、是分批                    |
| 問題範圍小（只影響 < 1% user）             | 量化成本 > 收益                         |
| MVP / 探索期                               | 規則還在演化、強行 trigger 可能卡死探索 |
| Internal tool、used by < 10 人             | 直接問 user、不需 metric                |

五類共通：**量化的成本 > 量化的收益**。其他情境必量。

---

## 跟其他抽象層原則的關係

| 原則                                                                     | 關係                                                        |
| ------------------------------------------------------------------------ | ----------------------------------------------------------- |
| [#86 Capability gap 三層階梯](../capability-gap-three-layer-escalation/) | #86 講升級階梯、本卡講升級 trigger 設計                     |
| [#72 高 ROI 無外部觸發](../external-trigger-for-high-roi-work/)          | 沒 trigger 升級就是高 ROI 無觸發、本卡是補上 trigger 的方法 |
| [#76 分批 ship](../incremental-shipping-criteria/)                       | 分批 ship 的「下輪」需要 trigger、本卡定 trigger            |
| [#68 驗收的時間軸](../verification-timeline-checkpoints/)                | Trigger 是 ship 後 checkpoint 的具體形式                    |
| [#42 2 次門檻](../two-occurrence-threshold/)                             | 升級 trigger 通常是「N 次失敗」累積、跟 #42 同骨            |
| [#62 誠實進度 UI](../pattern-honest-progress-ui/)                        | Trigger metric 公開 = 誠實進度的數據版本                    |

---

## 套用到當前 search planning case

D + C1 ship 時、應同步定：

```yaml
# D + C1 (ship together)
strategy: L1 UX hint + L2 title-only substring fallback
metric: search empty-result rate, fallback hit rate
baseline: TBD (instrument at ship time)

# B1 trigger (defined now)
trigger_metric: fallback hit rate (C1)
trigger_threshold: > 30% sustained for 4 weeks
       OR full-content fallback request from user (manual signal)
trigger_owner: 你（個人 blog 沒 team）
trigger_action: 實作 Hugo template suffix tokens (B1)
trigger_review_cadence: 每月 review search analytics

# 降級 trigger（補強 #86）
degrade_metric: B1 maintenance cost / build pipeline complexity
degrade_signal: 升級 Pagefind / Hugo 時 B1 broken 第 N 次
degrade_action: revisit 是否該換 search engine（換工具 vs 維 transformation）
```

**Pre-ship 把 trigger 寫好** = ship L1 時 L2 / L3 都「上膛」。下次 review 看數據、自動知道該不該升。

---

## 判讀徵兆

| 訊號                             | 該做的事                      |
| -------------------------------- | ----------------------------- |
| Plan 寫「ship 後再看」沒 trigger | 補 trigger                    |
| 「再觀察一下」第 3 次出現        | 量化 trigger 不夠、明確閾值   |
| Metric 是「user 抱怨數」         | 補可量化指標、別只靠 anecdote |
| Threshold 沒 baseline 對比       | 量現況、justify threshold     |
| 達到 threshold 但沒人 act        | Trigger 沒 owner、補          |
| Window 太短、被 spike 觸發       | 加 window、要求持續           |
| L1 ship 後沒重看 trigger         | 設 cadence、定期 review       |
| 「達到 trigger 太久才執行」      | ETA 沒寫、補                  |

**核心**：升級 trigger 的設計**跟 ship plan 同步寫、不是 ship 後才想**。沒 trigger = 不會升級 = capability gap 永遠在 L1 撐住。**「再觀察一下」是缺 trigger 的訊號、不是「我謹慎」的訊號**。
