---
title: "8.15 Vendor / 第三方依賴事故處理"
date: 2026-05-01
description: "依賴方掛掉、自己無 control 時的決策模型"
weight: 15
---

## 大綱

- 依賴事故的特殊性：control plane 在外、自家 IR 流程多數工具失效
- 決策模型：等 / 切換 / 降級 / 主動止血 的判讀
- vendor [status page](/backend/knowledge-cards/status-page/) 的可信度：滯後、語焉不詳、單點訊號
- 等待 vs 切換 的成本對照：vendor ETA 不可信時的決策
- 多區 / 多 vendor 的 failover 路徑（跟 6.7 DR 整合）
- 跟客戶溝通：vendor 事故的對外承擔邊界
- 跟 [6.14 dependency budget](/backend/06-reliability/dependency-reliability-budget/) 的整合：事故是 budget 耗盡的事件
- 跟 [8.10 stakeholder](/backend/08-incident-response/stakeholder-communication/) 的整合：對外溝通不能單純甩鍋給 vendor
- 反模式：依賴掛了只能等、無 fallback；對客戶說「是 vendor 的問題」就不更新；vendor SLA credit 從未請領

## 概念定位

Vendor / 第三方依賴事故處理是面對自己無法直接修正的故障時，選擇等待、切換、降級或止血的決策流程，責任是把控制權不足轉成可執行的判斷。

這一頁處理的是外部控制面的失效。當 vendor 的狀態與自家觀測不一致時，最重要的是先決定自己還能做什麼。

## 核心判讀

判讀 vendor 事故時，先看可替代路徑，再看等待的成本是否可接受。

重點訊號包括：

- vendor [status page](/backend/knowledge-cards/status-page/) 是否可信
- 自家服務是否有 fallback 或 multi-vendor 策略
- 等待 vendor ETA 的成本是否高於切換成本
- 對外說明是否能清楚承擔自己服務的影響

## 案例對照

- [Datadog](/backend/08-incident-response/cases/datadog/_index.md)：監控平台本身是許多團隊的 vendor 依賴。
- [Heroku](/backend/08-incident-response/cases/heroku/_index.md)：PaaS 型依賴掛掉時，使用者常沒有太多控制面。
- [Microsoft 365](/backend/08-incident-response/cases/microsoft-365/_index.md)：身份與協作依賴故障會跨產品擴散。

## 下一步路由

- 06.7 DR：多 vendor / 多區 failover
- 06.14 dependency budget：事故事件的 budget 影響
- 08.3 containment：對 vendor 故障的止血手段
- 08.10 stakeholder：對外通訊的承擔邊界

## 判讀訊號

- 依賴掛了、自家 IR 流程進入「等」狀態無 alternative
- vendor [status page](/backend/knowledge-cards/status-page/) 跟自家 observed 訊號不一致
- 客戶投訴「為什麼你們的服務也掛」、無對外說明 playbook
- 同 vendor 反覆出事、無多 vendor 策略
- vendor 事故事後無 SLA credit 請領記錄

## 交接路由

- 06.7 DR：多 vendor / 多區 failover
- 06.14 dependency budget：事故事件的 budget 影響
- 08.3 containment：對 vendor 故障的止血手段
- 08.10 stakeholder：對外通訊的承擔邊界
