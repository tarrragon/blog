---
title: "GitHub"
date: 2026-05-01
description: "GitHub 重大事故時間線與架構脈絡"
weight: 3
---

GitHub 是高 traffic、跨區資料庫 + 強一致性需求的代表、MySQL split-brain / Actions 大規模 outage 是跨區資料一致性與 control-plane 失效的教學標竿。

## 規劃重點

- MySQL 跨區拓撲：master / replica / Orchestrator 自動切換的失敗模式
- Split-brain 復原：為何資料一致性復原比可用性復原更耗時
- Actions / Codespaces 等控制面：使用者面 outage 與 control plane 的關係
- 通訊節奏：GitHub status page / blog 的事故揭露文化

## 預計收錄事故

| 年份    | 事故                      | 教學重點                                      |
| ------- | ------------------------- | --------------------------------------------- |
| 2018-10 | MySQL split-brain 24 小時 | Orchestrator 自動 failover 失誤、人工干預延遲 |
| 待補    | Actions outages           | CI/CD 平台失效的客戶影響量化                  |
| 待補    | 跨區網路事故              | 跨區一致性 vs 可用性的取捨                    |

## 引用源

待補（GitHub Engineering blog、post-incident report URL）。
