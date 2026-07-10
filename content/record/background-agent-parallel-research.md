---
title: "Background Agent 平行研究：main context 節省的量化效應"
date: 2026-05-18
description: "用 background agent 平行做同類研究任務、主 context 只收 finding summary、節省 ~80% context 用量的工作方法"
tags: ["agent", "context-management", "methodology"]
---

跨多個獨立子任務的研究（如多個 vendor 案例採集、多個主題 web research、多個檔案的 fact-check）、用 background agent 平行做、比串行單一 agent 或主 context 直接做都更省 token。

這份紀錄整理 backend/03-message-queue 模組 6 vendor case 庫採集的實作經驗、量化 main context 節省效應、給未來類似任務作為設定參考。

## 採集任務的特徵

backend/03 模組需要為 6 個 vendor（Kafka / RabbitMQ / NATS / Redis Streams / SQS / Pub/Sub）採集 5-10 個公開 case。任務特徵：

- 各 vendor 獨立、無相互依賴
- 每個 vendor 需要 WebSearch 找候選 + WebFetch 驗證 URL + 抽 finding、多步驟
- 每個 agent 任務時長 4-7 分鐘（含 WebFetch 多次往返）
- 採集回報是清單形式、易於主 context 整合

## Background agent 平行的執行方式

每個 agent 用 `subagent_type: general-purpose`、`run_in_background: true`、`prompt` 含：

1. 採集目標（5-10 案例）
2. 硬閘門（WebFetch 驗證）
3. 排除清單（已有案例 / vendor 自家 marketing）
4. 對齊大綱（該 vendor 的進階主題列表）
5. 回傳格式（清單、含 source / observation / finding / 對應章節）

主 context 一個 message spawn 6 個 agent、然後等通知。

## 量化結果

| 維度                | 串行單 agent                     | Background 平行 6 agent   | 主 context 直接做          |
| ------------------- | -------------------------------- | ------------------------- | -------------------------- |
| 總時間              | ~40 分鐘（6 vendor × 7 分鐘）    | ~7 分鐘（最慢 agent）     | ~60 分鐘（含探索盲區）     |
| 主 context token    | 高（每次 WebFetch 都進 context） | 低（只收 summary）        | 最高（整個流程在 context） |
| Agent context token | 跟串行同                         | 每 agent 獨立、不影響主   | N/A                        |
| 失敗風險            | 任一 agent 失敗影響全部          | 失敗 agent 獨立、其他繼續 | 主 context 失敗整體中斷    |

主 context 節省效應 ~80%：每個 agent 報告約 2KB summary、6 個總 12KB；若主 context 直接做、每次 WebFetch 取回的 markdown 約 10-30KB、累積後容易 > 100KB。

## 適用場景判斷

Background agent 平行適用：

- 多個**獨立子任務**（不互相依賴 input / output）
- 每個子任務需要**多步驟 tool use**（WebFetch / WebSearch / Bash / Glob）
- 子任務回報是**結構化清單 / summary**、不是 raw transcript
- 主 context 需要**節省 token** 做後續工作（如寫檔、整理 index）

不適用：

- 線性依賴（任務 B 需要任務 A 結果）
- 短任務（單一 WebFetch、串行直接做更快、平行 overhead 不划算）
- 需要主 context 即時介入決策的任務

## 跟其他 agent 用法的對比

backend 模組過去用過的其他 agent 用法：

| 用法                | 階段   | 目的                  |
| ------------------- | ------ | --------------------- |
| Stage 0 平行採集    | 寫作前 | 研究、補案例庫        |
| Stage 3 平行 review | 寫作後 | 審查、抓 issue        |
| 即時 Explore agent  | 寫作中 | 找 file / symbol 位置 |

三種都用 background、都節省主 context、但目的跟回報格式不同。Stage 0 採集回報是「**清單 + 捨棄候選**」、Stage 3 review 回報是「**issue list + severity**」、Explore 回報是「**file path + match**」。

## 設定參考

spawn 平行 agent 的 anti-pattern：

- **不寫硬閘門**：「找 5-10 case」沒明示 WebFetch 驗證 → agent 編造 URL
- **不列排除清單**：「找 Kafka 案例」沒列既有案例 → agent 重複採集
- **要求 raw transcript 回報**：「把找到的內容貼給我」→ 主 context 爆炸
- **單一巨大 agent**：「找所有 6 個 vendor」串行做 → 失去平行優勢
- **平行過頭**：spawn 20+ agent 但實際只有 6 個獨立任務 → 不必要的協調成本

## 跟 case-first 流程的關係

這個方法已寫入 `.claude/skills/case-first-module-workflow/references/stage-0-case-collection.md`、成為 case-first 流程的 stage 0 採集標準執行範式。但實際適用範圍超出 case 採集、適用所有「多獨立子任務 + 多步驟 tool use」場景。

## 下一步該追蹤的議題

1. **平行 agent 數量上限**：6 個跑 OK、20+ 是否會撞到 rate limit 或協調成本？實作上限是多少？
2. **Agent context 跑滿後的恢復策略**：若某個 agent context 跑滿、其他 agent 繼續但該 agent 失敗、要不要 retry？怎麼接續？
3. **跨 agent 共享 cache**：6 個 agent 都 WebSearch 同一個 vendor 主頁、有沒有 cache 共享機制可省 token？目前每 agent 獨立、可能重複 fetch
