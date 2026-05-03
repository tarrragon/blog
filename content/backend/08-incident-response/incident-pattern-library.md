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
  - [blast radius](/backend/knowledge-cards/blast-radius/) 失控（單點影響全租戶 / 全區域）
- 每個型態的卡片結構：機制、徵兆、放大因子、控制面、典型 case
- 跟 [cases/](/backend/08-incident-response/cases/) 的關係：cases 是證據來源、型態是抽象索引
- 跟 [knowledge-cards](/backend/knowledge-cards/) 的差異：型態卡是事故脈絡、知識卡是控制面 mechanism

## 概念定位

事故型態庫是把跨服務的共通事故結構抽成型態卡，責任是讓新事故能先對照既有 pattern，而不是從零開始命名。

這一頁處理的是跨案例抽象。case 提供證據，型態庫提供搜尋入口，兩者一起讓 [post-incident review](/backend/knowledge-cards/post-incident-review/) 不只停在個案。

## 核心判讀

判讀型態卡時，先看它是否有足夠的機制描述，再看能否對應到多個真實 case。

重點訊號包括：

- 型態是否有明確機制、徵兆與放大因子
- 型態是否能跨團隊遷移，而不是只對單一事故有用
- 新事故是否能快速被歸入某個型態
- 型態庫是否會隨新 case 持續擴充

## 案例對照

- [AWS S3](/backend/08-incident-response/cases/aws-s3/_index.md)：control-plane / dependency 類型常能對應多個事故。
- [Cloudflare](/backend/08-incident-response/cases/cloudflare/_index.md)：edge / [blast radius](/backend/knowledge-cards/blast-radius/) 類型容易成為共通 pattern。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：大規模平台常同時出現 control-plane 與 coordination 型事故。

## 下一步路由

- 08.5 復盤：[post-incident review](/backend/knowledge-cards/post-incident-review/) 揭露新型態時補卡
- 08.13 repeated / toil：repeated pattern 抽象成型態卡
- 08.8 事故報告轉 workflow：型態卡回寫到日常流程

## 判讀訊號

- 新事故發生時、團隊無共通詞彙描述「這像之前哪一類」
- 每篇 [post-incident review](/backend/knowledge-cards/post-incident-review/) 從零開始寫、無 type 標籤
- 跨團隊事故 retrospective 缺共享參考型態
- chaos / pre-mortem 場景靠人臨時想、無型態 checklist
- 同類型事故反覆發生、但學習未跨團隊傳遞

## 交接路由

- 04.13 service topology：cascading failure 型態的拓撲依據
- 06.4 chaos：型態作為 chaos 場景輸入
- 06.5 failure mode pre-mortem：型態作為 pre-mortem checklist
- 08.5 復盤：[post-incident review](/backend/knowledge-cards/post-incident-review/) 揭露新型態時補卡
- 08.13 repeated / toil：repeated pattern 抽象成型態卡
