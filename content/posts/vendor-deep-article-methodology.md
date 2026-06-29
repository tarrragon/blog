---
title: "Vendor 深度技術文章方法論的演化紀錄：同 vendor 系列的開場輪替驗證"
date: 2026-05-18
description: "vendor overview 飽和後要寫單一功能深度文章、需要選題與結構依據時回來。這套方法論的驗證來源與 cadence variant 在高風險場景（同 vendor sub-tool 系列）的實證。"
tags: ["writing-methodology", "vendor-article", "technical-writing", "case-first", "retrospective"]
---

Vendor overview 寫完後、往下寫單一功能深度文章時，選題與結構需要不同的方法論。操作步驟維護在 `.claude/skills/vendor-deep-article/`，本文記錄這套方法論從兩輪 batch 中演化出來的過程，重點是 cadence collapse（批量寫作時開場句型同質化重複）怎麼被寫前的 variant 規劃（每篇預先指定不同開場 framing）解決。

## 背景

本 blog 的 backend 教學模組已完成多個 vendor overview。overview 層飽和後、自然的下一步是 overview 頁尾「預計實作話題」backlog 的深度文章。

寫了 deep article + migration playbook 後、確認 deep article 跟 overview 是不同產品、需要自己的方法論。差異見 [migration playbook 方法論演化紀錄](/posts/migration-playbook-methodology/)。

## 第一輪 batch（5 篇）：跨 vendor、5 種 entry framing

| 篇                                                                                                           | Variant  | 章節 1 entry framing                              | 行數 |
| ------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------- | ---- |
| [pgBouncer 配置](/backend/01-database/vendors/postgresql/pgbouncer-config/)                                  | A 標準   | 標準「問題情境」                                  | 263  |
| [Vault dynamic credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/) | A 標準   | 標準「問題情境」                                  | 222  |
| [K8s graceful shutdown](/backend/05-deployment-platform/vendors/kubernetes/graceful-shutdown/)               | B 痛點   | 痛點宣告「沒做對、每次 deploy 都吃 502」          | 213  |
| [Splunk RBA](/backend/07-security-data-protection/vendors/splunk/risk-based-alerting/)                       | C 反向   | 概念反向定義「alert fatigue 是 detection 天花板」 | 193  |
| [Cloudflare Page Shield](/backend/07-security-data-protection/vendors/cloudflare-waf/page-shield-csp-sri/)   | D 對照表 | 對照表驅動「Attack pattern x Defense mechanism」  | 214  |

第一輪確認了結構 framework 成立、且章節名可隨主題調整。

### 6 段 framework 成立但章節名可變

6 段內容指引（問題情境 → 概念 → 配置 → 演練 → 容量 → 整合）在 5 篇都成立。但章節 1 的 framing 因主題本質不同自然分化 — 5 種 entry framing 都成立、章節 1 不必死守「問題情境」標題。

據此小修方法論：6 段 framework 是內容指引、不是章節標題模板。

### Cadence collapse 0% — 主動 variant 有效

後 4 篇寫作前主動規劃 4 種 framing variant。跟 backend/07 的 51 vendor batch 對照：

| 維度                      | backend/07 51 vendor | deep article 後 4 篇 |
| ------------------------- | -------------------- | -------------------- |
| Cadence「任一缺失」族重複 | 51/51 (100%)         | 0/4 (0%)             |
| 章節 1 entry framing 種類 | 1 種                 | 4 種                 |

### Reviewer 單人足夠

deep article 焦點窄（單一 feature）、跨章 frame 重複風險低、case 引用密度低（1-2 個對照）。5 篇都採單一 reviewer 流程、未出現需要 multi-axis review 的盲點。

## 第二輪 batch（5 篇）：同 vendor sub-tool 系列、最高 collapse 風險

第二輪刻意選 cadence collapse 最高風險場景：5 篇 PostgreSQL sub-tool deep article、同 vendor / 同 article type / 同 audience / 同 6-section framework。

| 篇                                                                                                      | Variant              | 章節 1 entry framing                                                                | 行數 |
| ------------------------------------------------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------- | ---- |
| [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)                                       | E lifecycle-driven   | 「Failover lifecycle 5 段不是一條曲線」                                             | 243  |
| [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)                         | B pain-driven        | 「你的 autovacuum 永遠追不上 bloat — 為什麼」                                       | 202  |
| [declarative partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)           | C concept-reversed   | 「Partition 不是『把大表切小』、是『讓 planner pruning + 縮小 maintenance scope』」 | 244  |
| [logical replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) | D table-driven       | 「Replication slot x Failure x Recovery 對照」                                      | 227  |
| [PITR + WAL archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)                     | A standard 6-section | 「問題情境」                                                                        | 273  |

第二輪在最高風險場景（同 vendor sub-tool）仍維持 collapse 0%，且新增第五種 variant（lifecycle-driven）。

### 跨兩輪對照

| 維度                      | 第一輪 N=4（跨 vendor） | 第二輪 N=5（同 vendor sub-tool） |
| ------------------------- | ----------------------- | -------------------------------- |
| Variant 種類              | 4（A / B / C / D）      | 5（A / B / C / D / E）           |
| Cadence collapse          | 0/4 (0%)                | 0/5 (0%)                         |
| 章節 1 entry framing 種類 | 4                       | 5                                |
| 共同 context              | 6-section framework     | 6-section + 同 vendor + 同讀者   |

關鍵驗證：

1. **N=5 仍 0% collapse**：5 種 variant 在最高風險場景（同 vendor sub-tool）仍完全錯開
2. **5 variant 不耗盡**：5 種變體（lifecycle / pain / reverse / table / standard）對應主題自然進入方式、不是強制配對
3. **cadence audit 最佳位置是進度 60-80%**：進度 10-20% 只有 1 樣本訊號弱、60-80% 有 4 樣本對照訊號強

## 方法論演化小結

| 版本 | 修改                                   | 驅動來源                   |
| ---- | -------------------------------------- | -------------------------- |
| v0   | 直覺套 overview 11 章節                | 第一篇 deep article 不合用 |
| v1   | 6 段結構 + 200-400 行 sweet spot       | 第一輪 5 篇 dogfood        |
| v1.1 | 6 段是內容指引、不是章節標題模板       | 章節 1 framing 自然分化    |
| v1.2 | 寫作時間預估 2-4hr → 1-2hr             | overview 已建立 context    |
| v1.3 | cadence audit 抽樣位置 10-20% → 60-80% | 第二輪 N=5 驗證            |

## 相關連結

- Vendor Deep Article skill（`.claude/skills/vendor-deep-article/`）— 操作步驟
- [Migration Playbook 方法論演化紀錄](/posts/migration-playbook-methodology/) — sibling、處理 cross-vendor process
- [Case-First Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/) — 教學模組級批次寫作流程
- [#199 一篇文章只承擔一種功能](/report/single-function-per-article-sop-vs-retrospective/) — 本文精簡的依據
