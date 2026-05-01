---
title: "8.15 Vendor / 第三方依賴事故處理"
date: 2026-05-01
description: "依賴方掛掉、自己無 control 時的決策模型"
weight: 15
---

## 大綱

- 依賴事故的特殊性：control plane 在外、自家 IR 流程多數工具失效
- 決策模型：等 / 切換 / 降級 / 主動止血 的判讀
- vendor status page 的可信度：滯後、語焉不詳、單點訊號
- 等待 vs 切換 的成本對照：vendor ETA 不可信時的決策
- 多區 / 多 vendor 的 failover 路徑（跟 6.7 DR 整合）
- 跟客戶溝通：vendor 事故的對外承擔邊界
- 跟 [6.14 dependency budget](/backend/06-reliability/dependency-reliability-budget/) 的整合：事故是 budget 耗盡的事件
- 跟 [8.10 stakeholder](/backend/08-incident-response/stakeholder-communication/) 的整合：對外溝通不能單純甩鍋給 vendor
- 反模式：依賴掛了只能等、無 fallback；對客戶說「是 vendor 的問題」就不更新；vendor SLA credit 從未請領

## 判讀訊號

- 依賴掛了、自家 IR 流程進入「等」狀態無 alternative
- vendor status page 跟自家 observed 訊號不一致
- 客戶投訴「為什麼你們的服務也掛」、無對外說明 playbook
- 同 vendor 反覆出事、無多 vendor 策略
- vendor 事故事後無 SLA credit 請領記錄

## 交接路由

- 06.7 DR：多 vendor / 多區 failover
- 06.14 dependency budget：事故事件的 budget 影響
- 08.3 containment：對 vendor 故障的止血手段
- 08.10 stakeholder：對外通訊的承擔邊界
