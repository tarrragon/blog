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
| 2020-11 | Actions outages           | CI/CD 平台失效的客戶影響量化                  |
| 2021-11 | 跨區網路 / replication    | 跨區一致性 vs 可用性的取捨                    |

## 案例定位

GitHub 這個案例在講的是跨區資料一致性如何把事故拉長。讀者先看懂 replication、Orchestrator 與 status communication 的責任，再把 split-brain 與 Actions outage 視為不同層級的 control-plane 失效。

## 判讀重點

當 replication lag 或 schema 變更讓資料庫進入不穩定狀態時，恢復速度會被一致性約束拉慢。當使用者面產品也同時掛掉時，狀態頁與事故報告就成了對外與對內的共同路由，讓時間線保持一致。

## 可操作判準

- 能否說明哪個節點持有權威寫入
- 能否區分自動 failover 與人工切換的責任邊界
- 能否把事故時間線寫成對外可理解的 status update
- 能否把 Actions 這類控制面事故量化成客戶影響

## 與其他案例的關係

GitHub 和 Atlassian、Microsoft 365 的共通點，是都把「對外說明」與「內部復原」綁在一起。它也能和 Azure AD 對照，因為一旦身份或 replication 的控制面退化，後面所有產品層的恢復都會被拉長。

## 代表樣本

- 2018-10 split-brain 事故說明權威寫入與人工切換的邊界。
- 2020-11 Actions outage 與 2021-11 replication 問題則展示了控制面失效如何影響客戶體感與恢復時間。
- replication lag、schema migration 與 read replica deadlock 都屬於相近失敗面。
- status report 的寫法本身也是事故管理能力的一部分。
- orchestrator 自動切換失敗讓自動化與人工介入的邊界更明顯。
- control-plane outage 會同時影響 CI/CD 與資料服務的信任感。
- code hosting 與 CI/CD 共享控制面，讓一個事故同時影響多種使用情境。
- read replica deadlock 讓 schema 變更也成為事故起點。

## 引用源

- [October 21 post-incident analysis](https://github.blog/2018-10-30-oct21-post-incident-analysis/)：GitHub 2018 年資料庫與 replication 事故的深度分析。
- [GitHub Availability Report: November 2020](https://github.blog/2020-12-02-availability-report-november-2020/)：MySQL replication lag 與 Actions 事故的官方報告。
- [GitHub Availability Report: December 2020](https://github.blog/news-insights/company-news/github-availability-report-december-2020/)：November incident 的後續說明。
- [GitHub Availability Report: November 2021](https://github.blog/news-insights/company-news/github-availability-report-november-2021/)：schema migration / MySQL read replica deadlock 的官方報告。
