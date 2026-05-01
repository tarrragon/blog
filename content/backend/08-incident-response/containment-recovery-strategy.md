---
title: "8.3 止血、降級與回復策略"
date: 2026-04-23
description: "把短期止血與正式回復拆成可執行步驟"
weight: 3
---

## 大綱

- containment priority
- [degradation](/backend/knowledge-cards/degradation/) path
- rollback checkpoints
- recovery validation

## 判讀訊號

- 止血優先級跟回復優先級衝突、現場臨時做選擇
- rollback checkpoint 沒測、按下去才知道掛了
- degradation 路徑沒設計、事故時臨時砍功能
- recovery 完成判讀無客觀標準、靠 IC 主觀宣告
- containment 後驗證關閉缺步驟、同事故反覆再起

## 交接路由

- 06.7 DR / rollback：演練結果作為事中決策素材
- 08.15 vendor 事故：依賴方掛掉時的止血手段
- 06.17 feature flag：ops flag 作為事中止血手段
- 08.17 security vs operational：止血策略差異
