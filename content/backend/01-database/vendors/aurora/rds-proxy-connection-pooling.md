---
title: "Aurora RDS Proxy 與連線管理：connection multiplexing、pinning 陷阱與 failover 加速"
date: 2026-06-02
description: "RDS Proxy 不是「連上去就自動省連線」；本文展開 connection multiplexing 機制、哪些 session 操作會觸發 pinning 讓 multiplexing 失效、failover 期間 proxy 如何保持 client 連線縮短中斷，以及 RDS Proxy 與自管 pgbouncer 的責任切分"
weight: 33
tags: ["backend", "database", "aurora", "rds-proxy", "connection-pool", "serverless", "deep-article"]
---

Lambda 函式在流量尖峰被同時拉起幾百個實例、每個各自開一條到 Aurora 的連線、Aurora 的 connection 上限瞬間被打爆、新請求拿不到連線、整批失敗。這不是 Aurora 容量不夠，而是 *連線管理* 缺位——serverless 與高並發短連線 workload 製造的連線數遠超過資料庫該同時維持的後端連線。RDS Proxy 在 application 與 Aurora 之間做 connection multiplexing，把大量 client 連線收斂成少量後端連線。但它不是「連上去就自動省」——某些 session 操作會讓連線被 pin 住、multiplexing 失效。

本文不是 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 而是 RDS Proxy 連線管理機制與陷阱的實作層教學。

## 核心機制：connection multiplexing

RDS Proxy 維護一個到 Aurora 的後端連線池，多個 client 連線共享這些後端連線。當 client 連線閒置（交易之間沒有活動），proxy 可以把對應的後端連線釋放回池子給其他 client 用：

| 沒有 proxy                        | 有 RDS Proxy                                   |
| --------------------------------- | ---------------------------------------------- |
| 每個 client 連線 = 一條後端連線   | 多個 client 連線共享少量後端連線               |
| Lambda 並發 N → 後端 N 條連線     | Lambda 並發 N → 後端遠少於 N 條                |
| failover 時 client 連線斷、要重連 | proxy 保持 client 連線、後端切換對 client 透明 |
| 連線建立開銷由 application 承擔   | proxy 維持暖連線池、省去反覆建立               |

multiplexing 生效的前提是 client 連線「閒置時可以被借走」。這只在連線處於 *交易之間* 的乾淨狀態時成立——一旦連線帶了交易內狀態，proxy 不能把它借給別人，這就是 pinning。

> **Scope warning**：「RDS Proxy 支援的 engine / 連線數上限 / IAM 認證細節」屬 AWS vendor 規格、實作時 cross-verify 官方 doc 當前值。本文不含 production case 揭露的 proxy 配置數字。

對應 knowledge card：[connection pool](/backend/knowledge-cards/connection-pool/)。

## Pinning：multiplexing 失效的主因

Pinning 是 RDS Proxy 最常被忽略、卻直接決定省連線效果的機制。當 client 在連線上做了「跨交易持續的 session 狀態」操作，proxy 無法安全地把這條後端連線借給其他 client，於是把它 *pin*（綁定）到該 client 直到連線關閉——這條後端連線在 pin 期間不參與 multiplexing。

常見觸發 pinning 的操作：

- session 層級的變數設定（`SET` 某些 session variable）
- 建立 temp table
- prepared statement（某些情況）
- advisory lock、保持開啟的交易
- 部分 session 層級的設定語句

pinning 的後果是「明明裝了 RDS Proxy、後端連線數卻沒降下來」。若大量 client 都觸發 pinning，等於退化回「一個 client 一條後端連線」、proxy 白裝。

**判讀與修法方向**：

- 監控 `DatabaseConnectionsCurrentlySessionPinned`，看 pinning 比例
- application 端避免不必要的 session 狀態（少用 session variable、temp table；改用交易內可清理的方式）
- 真的需要 session 狀態的 workload，接受該連線會 pin、或評估這類 workload 是否適合走 proxy

> **Scope warning**：「哪些具體語句觸發 pinning」隨 RDS Proxy 版本與 engine 演進、實作時以 AWS doc 當前清單為準；本段列舉是常見類型、非完整或固定清單。

## Failover 加速

RDS Proxy 的第二個價值是縮短 failover 對 application 的中斷。沒有 proxy 時，writer failover 會讓所有 client 連線斷掉、application 要偵測、重連、重建連線池；有 proxy 時，proxy 保持與 client 的連線、在後端把流量切到新 writer，client 端感知到的中斷時間縮短。

這對連線建立成本高、或 failover 期間不能大量重連的 workload 特別有價值。但 proxy 不消除 failover 本身——in-flight 的交易仍會失敗、application 仍要有 retry；proxy 縮短的是「重建連線」這段，不是「交易不中斷」。

## 操作流程

從連線壓力判讀到上線的 6 步流程。

#### Step 1：確認是不是連線問題

先區分「Aurora 容量不夠」vs「連線管理問題」。看 `DatabaseConnections` 是否逼近上限、且 CPU/IOPS 還有餘量——後者是典型的連線數問題、proxy 能解；若是 CPU/IOPS 飽和，proxy 不解。

#### Step 2：判斷 workload 是否適合 proxy

- serverless / Lambda / 高並發短連線 → 適合（連線爆炸是主問題）
- 少量長連線、穩定的 application server → proxy 效益有限（連線數本就可控）
- 大量 session 狀態 workload → pinning 會吃掉 multiplexing 效益、要先評估

#### Step 3：建立 proxy

```bash
aws rds create-db-proxy \
  --db-proxy-name my-aurora-proxy \
  --engine-family POSTGRESQL \
  --auth ... \
  --role-arn ... \
  --vpc-subnet-ids ...
```

application 連到 proxy endpoint 而非直連 cluster endpoint。

#### Step 4：減少 pinning

review application 的 session 狀態使用、移除不必要的 `SET` / temp table；連線池設定避免長時間持有閒置連線。

#### Step 5：驗證 multiplexing 生效

```text
# 對照後端連線數：裝 proxy 後 Aurora 的 DatabaseConnections 應顯著低於 client 並發數
# 看 DatabaseConnectionsCurrentlySessionPinned：pinning 比例高代表 multiplexing 沒發揮
```

#### Step 6：驗證 failover 行為

主動觸發一次 failover、測量 application 感知到的中斷時間、確認 retry 邏輯能吸收 in-flight 交易失敗。

**Rollback boundary**：application 可在 proxy endpoint 與直連 cluster endpoint 間切換、proxy 出問題時改回直連（但直連會回到連線爆炸風險，要先確認後端撐得住）。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：裝了 proxy 但 pinning 比例高、連線沒降

application 大量用 session variable / temp table、多數連線被 pin、後端連線數沒降、proxy 白裝。修法：監控 pinning 比例、減少 session 狀態；理解 proxy 的省連線前提是連線可被借走。

#### Case 2：把 proxy 當「Aurora 容量擴充」

連線數沒問題、是 CPU/IOPS 飽和、卻裝 proxy 期待變快。修法：proxy 解連線管理、不解運算容量；容量問題要擴 instance / 加 replica。

#### Case 3：以為 proxy 讓 failover 零中斷

裝了 proxy 就拿掉 application 的 retry、failover 時 in-flight 交易失敗沒處理。修法：proxy 縮短重連時間、不保證交易不中斷；application 仍要 retry in-flight 交易。

#### Case 4：少量長連線 workload 強裝 proxy

穩定的 application server 連線數本就可控、裝 proxy 多一跳延遲、效益有限。修法：proxy 的價值在連線爆炸場景（serverless / 高並發短連線）；連線可控的 workload 不必加。

#### Case 5：proxy 與自管 pooler 疊加未理清責任

application 已有自管連線池（如語言層 pool）、又加 RDS Proxy、兩層 pool 互相打架、連線數行為難預測。修法：理清兩層職責——application 層 pool 管「app 到 proxy」、proxy 管「proxy 到 Aurora」；兩層設定要協調、不是各設各的。

**Anti-recommendation**：連線數本就可控的少量長連線 workload、或 workload 大量依賴 session 狀態（pinning 會吃掉效益）→ 不必上 RDS Proxy；它的價值集中在 serverless / Lambda / 高並發短連線的連線爆炸場景。

## 容量與觀測

CloudWatch metric：

- `DatabaseConnections`（Aurora 端）：裝 proxy 後應顯著低於 client 並發數
- `DatabaseConnectionsCurrentlySessionPinned`：pinning 數、判斷 multiplexing 效益
- `ClientConnections`（proxy 端）：client 側連線數、對照後端收斂比例
- `QueryDatabaseResponseLatency`：proxy 多一跳的延遲影響

**判讀**：

- 後端連線數沒因 proxy 下降 → pinning 比例高或 workload 不適合
- pinning 數持續高 → application session 狀態過多、需 review
- proxy 延遲明顯 → 評估這一跳對延遲敏感路徑是否值得

> **Scope warning**：本文未引用 production case 的 proxy metric 數字；上述指標與判讀屬 vendor 規格 + 通用連線管理工程。

接回 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)、[1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)。

## 邊界與整合

### RDS Proxy vs 自管 pgbouncer

兩者都是 connection pooler，責任切分在「managed vs 自管」：

- **RDS Proxy**：AWS managed、跟 Aurora / IAM / Secrets Manager 整合、零運維、含 failover 加速；綁 AWS
- **自管 pgbouncer / pgcat**：自己部署運維、pooling 模式（session / transaction / statement）可細調、跨雲可攜；運維責任自負

PostgreSQL 的通用連線池機制與 pgbouncer 細節主寫於 [pgbouncer-config](/backend/01-database/vendors/postgresql/pgbouncer-config/) 與 [connection-pooler-comparison](/backend/01-database/vendors/postgresql/connection-pooler-comparison/)；本篇聚焦 RDS Proxy 這個 AWS managed 方案的機制與 pinning 陷阱。要細調 pooling 模式、或需要跨雲可攜 → 評估自管 pooler；要零運維 + Aurora 原生整合 + failover 加速 → RDS Proxy。

### Sibling 與 cross-link

- [serverless-v2-scaling](/backend/01-database/vendors/aurora/serverless-v2-scaling/) — serverless + Lambda 場景的連線管理常與 RDS Proxy 一起出現
- [cross-az-failover-rto](/backend/01-database/vendors/aurora/cross-az-failover-rto/) — proxy 縮短 failover 重連時間、與 RTO 目標結合
- [pgbouncer-config](/backend/01-database/vendors/postgresql/pgbouncer-config/) / [connection-pooler-comparison](/backend/01-database/vendors/postgresql/connection-pooler-comparison/) — 通用連線池 SSoT、自管方案對照
- [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/) — 連線池與 transaction 範圍控制
- 替代路由：需要細調 pooling 模式 / 跨雲 → 自管 pgbouncer
