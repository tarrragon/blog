---
title: "Log 時間真空是 silent hang 訊號、happy log 是 anti-signal"
date: 2026-06-29
weight: 200
description: "非互動 process（CI / cron / container init）的最後一行 log 是成功訊息、到被 cancel 之間有大段時間無輸出時回來。判讀靠訊息時序的真空、不是最後一行的成功訊息。"
tags: ["report", "事後檢討", "工程方法論", "原則", "debugging", "ci"]
---

## 論述基礎與限制

本卡抽自 blog CI 的 Playwright install step 反覆 timeout 事件。Playwright 1.59 在 Node.js 24.16.0 上 extract-zip silent hang，表面看是「下載太慢 / timeout 太緊」，實際是 upstream regression。limitation：evidence 來自單一 CI 事件，但 silent hang 模式在 Docker build、cron job、database migration 等場景都出現過。

完整 case study 見 [CI step silent hang](/work-log/ci-silent-hang-diagnosis/)。

## 核心原則

非互動 process 的 log 輸出中，最後一行成功訊息（happy log）到被外部 cancel 之間的大段時間無輸出（時間真空），是 silent hang 的判讀訊號。

技術人員習慣在 log 裡搜尋 error keyword 找失敗原因。但 silent hang 沒有 error keyword — process 沒 crash，只是不再做任何事。辨識 silent hang 需要轉換訊號類型：從「訊息內容」轉到「訊息時序」。

## 情境

CI step 跑了 15 分鐘被 timeout cancel。最後一行 log 是「chromium 下載 100% 完成」— 這是 happy log，直覺判斷是「下載慢、timeout 太緊」。加了 cache + bump timeout 到 25 分鐘，仍然頂到上限被 cancel。

回頭看 detailed log 的 timestamp：

```text
2026-05-27T09:59:44.110Z  | 100% of 170.4 MiB
2026-05-27T10:24:15.201Z  ##[error]The operation was canceled.
```

24 分 31 秒的時間真空。下載 2 秒完成，之後 process 完全沒有任何 log 輸出直到被 cancel。

## 理想做法

CI step timeout 時，先抓四個 timestamp 判斷是否 silent hang，再決定修法：

1. Step 開始的 timestamp
2. Step 結束（cancel / fail）的 timestamp
3. 最後一行有意義輸出的 timestamp
4. 計算 #3 到 #2 之間的時間真空

真空相對該 step 正常輸出節奏明顯異常（CI extract 類場景通常秒級輸出、真空超過數分鐘即可疑）且最後一行是 happy log → silent hang 嫌疑高 → 用症狀詞查 upstream issue tracker，不是加 timeout。

三類 timeout 模式的修法不同：

| 訊號                                | 根因         | 修法                      |
| ----------------------------------- | ------------ | ------------------------- |
| 進度持續、最後階段到 timeout        | 時間真的不夠 | bump timeout              |
| 有失敗訊息之後 timeout              | code 邏輯錯  | 看訊息修                  |
| 最後一行 happy log 之後大段時間真空 | silent hang  | 查 upstream issue tracker |

## 沒這樣做的麻煩

- **反覆加 timeout**：每次都「差一點」（頂到上限），每次都以為「timeout 不夠」，實際上 process 永遠不會自己結束
- **Cache 是假瓶頸**：直覺判斷「下載慢 → 加 cache」，但瓶頸在 extract hang（下載只花 2 秒）
- **False positive 越雕越精緻**：cache key 調整、timeout 微調、retry 策略 — 每一步單看合理，合起來是把錯誤假設越做越細

## 判讀徵兆

兩個訊號同時出現時，應該先排除 silent hang 再提其他解法：

1. 非互動 process 跑的時間接近或等於 timeout 上限（「頂到上限」模式）
2. 最後一行 log 是成功訊息（下載完成 / build succeeded / tests passed）

另一個後設訊號：同方向修法（加 timeout / 加 cache / 加 retry）2 次都仍頂到上限 — 這時候問題幾乎確定不是「時間不夠」。對應 [#20 同方向反覆失敗的轉折點](/report/failure-direction-pivot-point/)。

## 跟其他抽象層原則的關係

- → [#20 同方向反覆失敗的轉折點](/report/failure-direction-pivot-point/)：本案例是 #20 在 CI timeout 場景的 evidence — 第二次 bump timeout 仍 fail 時就該停下來換思路
- → [#199 一篇文章只承擔一種功能](/report/single-function-per-article-sop-vs-retrospective/)：本卡的來源文章原本放在 `posts/`，實際是 debugging case study，搬到 `work-log/` 後從中抽出本卡，是 #199 拆分動作的實例
