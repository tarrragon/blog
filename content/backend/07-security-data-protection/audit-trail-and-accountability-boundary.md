---
title: "7.7 稽核追蹤與責任邊界"
date: 2026-04-24
description: "大綱稿：以問題驅動方式整理高風險操作追蹤、可回查與責任切分"
weight: 77
---

本章的責任是定義稽核追蹤與責任邊界問題節點，讓高風險操作在事故時可以快速回查與決策。

## 本章寫作邊界

本章聚焦證據模型、責任鏈與跨部門節奏。案例在問題節點被觸發時作為判讀佐證。

## 大綱（待填充）

1. 稽核事件資料模型
2. 高風險操作責任鏈
3. 代理操作與批准時序
4. 技術時序與業務時序並行
5. 平台級事件責任切分
6. 交接路由到 06/08

## 問題節點（案例觸發式）

| 問題節點 | 判讀訊號 | 風險後果 | 前置控制面 | 交接路由 |
| --- | --- | --- | --- | --- |
| 稽核欄位結構缺漏 | 主體、目的、資產欄位不完整 | 事故回查效率下降 | [audit-log](../knowledge-cards/audit-log/)、[incident-timeline](../knowledge-cards/incident-timeline/) | `08` |
| 代理與批准節奏脫鉤 | 變更事件與批准事件時序偏移 | 責任邊界判讀成本上升 | [authorization](../knowledge-cards/authorization/)、[incident-command-system](../knowledge-cards/incident-command-system/) | `08` |
| 跨部門通報節奏失衡 | 技術更新與對外訊息不同步 | 決策一致性下降 | [incident-communication-channel](../knowledge-cards/incident-communication-channel/)、[post-incident-review](../knowledge-cards/post-incident-review/) | `08` |
| 平台級事件責任混層 | 平台與產品責任切分不清 | 收斂順序與優先級混亂 | [management-plane](../knowledge-cards/management-plane/)、[containment](../knowledge-cards/containment/) | `06 + 08` |

## 下一步路由

- 演練與驗證：`06-reliability`
- 分級、指揮、通報、復盤：`08-incident-response`
