---
title: "8.9 事故型態庫入口"
date: 2026-05-01
description: "把跨服務的共通事故型態抽成型態卡，作為新事故的判讀錨點"
weight: 9
---

## 大綱

- 為何要有事故型態庫：個案易忘、型態可遷移
- 型態跟 case 的差異：case 是時間線、型態是跨案例的共通結構
- 核心型態（暫定）：
  - cascading failure（依賴鏈崩塌）
  - split-brain（一致性 vs 可用性裂解）
  - control-plane failure（管理面失效、data plane 連帶）
  - thundering herd（重啟 / 快取冷啟動 / retry storm）
  - configuration push 風險（全域配置同步發布）
  - capacity surprise（流量模式變化超出規劃）
  - long-tail recovery（短時間故障、長時間 recover）
  - blast radius 失控（單點影響全租戶 / 全區域）
- 每個型態的卡片結構：機制、徵兆、放大因子、控制面、典型 case
- 跟 [cases/](/backend/08-incident-response/cases/) 的關係：cases 是證據來源、型態是抽象索引
- 跟 [knowledge-cards](/backend/knowledge-cards/) 的差異：型態卡是事故脈絡、知識卡是控制面 mechanism

## 判讀訊號

- 新事故發生時、團隊無共通詞彙描述「這像之前哪一類」
- 每篇 postmortem 從零開始寫、無 type 標籤
- 跨團隊事故 retrospective 缺共享參考型態
- chaos / pre-mortem 場景靠人臨時想、無型態 checklist
- 同類型事故反覆發生、但學習未跨團隊傳遞

## 交接路由

- 04.13 service topology：cascading failure 型態的拓撲依據
- 06.4 chaos：型態作為 chaos 場景輸入
- 06.5 failure mode pre-mortem：型態作為 pre-mortem checklist
- 08.5 復盤：postmortem 揭露新型態時補卡
- 08.13 repeated / toil：repeated pattern 抽象成型態卡
