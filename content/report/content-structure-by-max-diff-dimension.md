---
title: "Process content 結構由最大差異維度決定、不是 universal phased"
date: 2026-05-19
weight: 127
description: "跨 X process content（migration / upgrade / rollout / playbook）的結構由 source / target 之間 *最大差異維度* 決定、不存在 universal phased 模板；5 種 migration type 實證（schema 差 / drop-in / operational / multi-tool / paradigm）跑出 5 種不同結構（6-phase / 6-section + audit / hybrid / parallel streams / partial + 混合）；寫作前必須做 *diff dimension audit* 才能決定結構、跳過會套錯模板"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "Content-design", "Process-writing"]
---

## 結論

跨 X process content（migration / upgrade / rollout / 演練 / playbook）的結構不是 universal、由 source 跟 target 之間的 *差異維度組合* 決定。固定套「6-phase playbook」「6-section deep article」會在 *結構錯位* 的場景失效。

實證：6 種 migration / process type 產出 6 種不同結構：

| Migration / process type | 主導差異維度        | 結構                                        | 結構元素數 | 週期       |
| ------------------------ | ------------------- | ------------------------------------------- | --------- | ---------- |
| 高 schema 差             | Schema / API        | 6-phase rule translation                    | 11-12     | 4-9 個月   |
| Drop-in compatible       | 無顯著差異          | 6-section + audit prefix                    | 7-8       | 1-4 週     |
| Operational redesign     | Operational model   | Hybrid (4-phase 含 audit + drop-in cutover)| 11-12     | 6-12 週    |
| Multi-tool 拆分          | 一站式 → 多 component | Parallel migration streams                  | 10-11     | 2-4 個月   |
| Paradigm shift           | Abstraction model   | Partial + 混合架構                          | 10-11     | 不收斂     |
| Topology re-layout       | Data topology       | 機制 + execution flow（同 cluster 內重劃）   | 7-9       | 1 天-2 週   |

6 種結構是 *常見 type*、不是窮盡分類；source / target 配對可能同時屬多 type（多軸 High）、或不屬任一 type（6 維皆 Medium）— 處理規則見「多重歸類跟 tie-breaking」段。本卡前身是「最大差異維度決定結構」+ 5 維 audit、Redis re-sharding dogfood 揭露 *data topology* 是漏掉的第 6 維、Type F 是對應的第 6 type；本卡擴張為 6 維 audit + 6 type。

---

## 為什麼 universal phased 模板會失效

寫第一篇 migration playbook 時自然會想：「6 phase 是 migration 的標準結構吧」 — 套到 drop-in compatible migration 後發現 80% phase 不需要、文章變成「為了 phase 而 phase」；套到 paradigm shift 後發現 phased 假設 *線性收斂*、實際是 *永遠混合架構*、phased 模板強迫一個 *不存在* 的「cleanup phase」。

Universal phased 失效的三個機制：

1. **Schema 差不顯著時、phased 多數 phase 變空白**：drop-in compatible（如 Redis → DragonflyDB）的「Schema translation phase」內容空、強寫變廢話
2. **Operational 差是主軸時、phased 把 operational redesign 壓進「phase 1」變太薄**：PostgreSQL → Aurora 的 *operational model 重設計* 是核心、不該壓在一個 phase
3. **Paradigm 差時、phased 假設 source 完全消失**：Kafka ↔ NATS 是 *永遠共存*、phased cleanup phase 假設不存在

→ **結構必須跟差異維度對位、不能反向假設**。

---

## Diff dimension audit：寫作前的必要 step

寫 process content 前先做 audit、列出 source 跟 target 在 6 個維度的差異程度：

| 維度                 | 評估問題                                                            | High / Medium / Low |
| -------------------- | ------------------------------------------------------------------- | ------------------- |
| Schema / API         | source 跟 target 的 API、data model、wire protocol 差異多大？        | -                   |
| Operational model    | HA / backup / monitoring / capacity 邏輯差異多大？                   | -                   |
| Abstraction / paradigm | 兩端是否同類產品（同抽象層）？                                       | -                   |
| Number of components | 一站式 vs multi-tool 是否需要拆分？                                  | -                   |
| Application change   | application code 需要改多少？                                        | -                   |
| **Data topology**    | **Sharding / partition / region / replication 拓樸是否變動？**       | -                   |

主導差異維度對映常見 type：

- **Schema = High（其他 Low）** → Type A phased rule translation
- **Operational = High（其他 Low）** → Type C operational redesign hybrid
- **Paradigm = High** → Type E partial + 混合架構
- **Components = High（一站式 → multi-tool）** → Type D parallel streams
- **Topology = High（其他 Low）** → Type F topology re-layout（見 [#128](../data-topology-as-audit-dimension/)）
- **全 Low** → Type B drop-in、6-section + audit prefix

第 6 維 *Data topology* 是後續從 Redis cluster re-sharding dogfood 浮現補位、見 [#128 Data topology 是 process content 的第 6 audit 維度](../data-topology-as-audit-dimension/)；本卡原為 5 維 audit、被第二輪 batch evidence 揭露盲點後擴張為 6 維。

## 多重歸類跟 tie-breaking

實際 source / target 配對 *很少* 完美對映單一 type；常見情境跟處理規則：

| 情境                                  | 例                                                              | 處理規則                                                                                       |
| ------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 兩維度都 High                          | PostgreSQL → CockroachDB（Schema + Operational + Paradigm 三 High）| 主結構選 *讀者最關心* 的維度（多數情境 Schema > Paradigm > Operational > Components）、其他維度抽出獨立段補充 |
| 三維度都 High                          | 同上                                                            | 結構走 Type E（paradigm 為主、partial + 混合）、用「為什麼這不是 drop-in」段交代另外兩維度        |
| 全 Medium（無 High）                   | Redis → KeyDB（API 微差 + ops 微差）                            | 走 Type B drop-in、用「相容性 audit」段列 medium 差異點                                       |
| 一維 High 但 *application change* 連帶 High | MySQL → PostgreSQL（Schema High + SQL dialect 連帶 application 改）| 走 Type A、application change 章節獨立段、不壓進 Phase 4 cutover                              |
| Schema High + Components High         | Splunk → Elastic + Tines + PagerDuty                            | 主結構走 Type A（Schema 為主驅動 phased translation）、Type D 的 multi-tool 用「target stack 拆分」獨立段 |

關鍵原則：**主導維度決定主結構、其他高維度獨立加段**、不強迫單一 type 標籤。Backlog 的「Type A/D 混合」「Type B/D 混合」標示是 *維度組合* 的簡記、不是承認 5 type 互斥失效；下表多重歸類處理規則才是正式判讀。

## 5 type 是 axis-aligned simplification、非窮盡

本卡 5 type 來自 5 篇 migration playbook 的 dogfood 觀察、是 *已浮現的 type*、不是 *涵蓋所有 migration 的完備分類*。已知漏類至少 4 種：

| 漏類                            | 例                                            | 為何 5 type 不覆蓋                                                       |
| ------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------ |
| 同 vendor major version upgrade | PostgreSQL 14 → 17 / Kafka 3 → 4              | Source / target 是同 vendor、5 type 預設跨 vendor、deep article methodology 也不完全 cover |
| 政策 / 合規驅動                 | Atlassian server EOL / PCI 強制資料 region    | Driver 在外部、但資料層仍走 type A-E 之一；audit 重點是 evidence collection、不是結構 |
| 容量重新規劃 / re-sharding      | 單實例 → sharded / 單 region → multi-region   | Source / target 同 vendor、無 schema / paradigm 差、但 data topology 重劃；5 維度沒「topology」軸 |
| Acquisition / merger consolidation | 兩 Datadog org 合併 / 兩 K8s cluster federate | Source / target 同產品、要處理 identity / RBAC / 歷史資料合併；5 type 不覆蓋 |

未來累積更多 migration playbook 後、可能浮現第 6-9 type、或對 5 type 重構。本卡的 type 集合是 *open*、不是 *closed*。

---

## 5 種結構的 anatomy

**「結構 differentiator」**是本系列引入的概念：每篇 process content 在開頭加一段、*明示這篇用什麼結構、跟其他同 category content 的結構差異在哪*。功能類似 type signature — 讓讀者一開始就知道接下來的章節組織方式、避免套錯預期。例：drop-in migration 的「結構 differentiator」段會說「跟 phased migration 對照、本篇是 6-section + audit、不是 6-phase」。

### Type A：Phased translation（schema 差為主）

```text
Phase 0 audit → Phase 1 schema 對位 → Phase 2 translation
→ Phase 3 parallel run → Phase 4 cutover → Phase 5 cleanup
```

特徵：

- *線性* 流程、phase 之間有 dependency
- 每 phase 有獨立 *回退邊界*
- Schema translation 是工作量主軸（4-12 週）

適用：Splunk → Elastic / Datadog APM → New Relic / MySQL → Postgres

### Type B：6-section + audit prefix（drop-in compatible）

```text
為什麼遷 → 結構 differentiator → 相容性 audit
→ Step-by-step cutover → 故障演練 → Capacity → 整合
```

特徵：

- 接近 deep article 6-section
- 多一段 *相容性 audit*（在 cutover 前列出風險點）
- 不需要 phased、單次 cutover

適用：Redis → DragonflyDB / OpenJDK → Adoptium / MariaDB → MySQL（部分版本）

### Type C：Operational redesign hybrid

```text
為什麼遷 → 結構 differentiator → Operational redesign 對位
→ 4-phase operational migration（Phase 0 audit + 3 active phase）→ Drop-in cutover → 故障演練 → Capacity → 整合
```

特徵：

- application code 不變、operational model 全換
- *operational 表格對位* 是內容主軸
- Cutover 本身簡單（protocol 相容）、operational 準備複雜

適用：PostgreSQL → Aurora / Self-managed Redis → ElastiCache / Self-managed Kafka → MSK

### Type D：Parallel streams（multi-tool 拆分）

```text
為什麼遷 → 五個責任、五個 component → 5 parallel migration stream
→ Stream-level audit / deploy / dual-ship / cutover → 故障演練 → Capacity → 整合
```

特徵：

- source 一站式、target N 個專責 component
- 每個 stream 獨立 audit / deploy / cutover、stream 間少 dependency
- 整體不是線性、是 *staggered parallel*

適用：Datadog → Grafana Stack / Splunk → Elastic + Tines + PagerDuty / Atlassian Suite → 各 specialized tool

### Type E：Partial + 混合架構（paradigm shift）

```text
「不是 migration、是 paradigm 重設計」→ Paradigm 對位
→ 什麼情境真的能換 → Application 重設計 → 部分 stream cutover → 長期混合架構
```

特徵：

- 不存在「complete migration」、是 *按 use case 拆分 + 共存*
- application 模式重設計（不是 SDK 換）
- *混合架構是 long-term default*

適用：Kafka ↔ NATS / REST → gRPC / SQL → NoSQL / VM → Serverless

### Type F：Topology re-layout（data topology = High）

```text
為什麼 re-layout → 結構 differentiator（re-layout 不是 migration）
→ Pre-layout analysis（topology audit）→ Re-layout 機制
→ Execution flow（per-step + rollback boundary）
→ 故障演練 → Capacity / cost → 整合
```

特徵：

- Source / target 多數是 *同 cluster 不同 state*、不是跨 vendor
- 主軸是 *topology audit + 重劃機制*、不是 schema translation / paradigm shift
- Pre-layout analysis（識別 hot key / 當前 distribution）是 Type F 的核心 audit 段
- Execution flow per-step、含 *rollback boundary*

適用：Redis cluster re-sharding / PostgreSQL partition redesign / Kafka topic re-partitioning / Cassandra keyspace re-balance / 加 region / multi-master rollout

詳細 audit dimension 跟 sub-dimension 見 [#128 Data topology 是 process content 的第 6 audit 維度](../data-topology-as-audit-dimension/)。

---

## 跟 deep article methodology 的關係

[Deep article methodology](/posts/vendor-deep-article-methodology/) 的 6-section structure（問題情境 → 概念 → 配置 → 演練 → 容量 → 整合）是 *single feature implementation* 的模板、不是 *cross-vendor process* 的模板。Migration playbook 是 *新 content category*、需要自己的 methodology。

兩者關係：

- **Single feature deep article**：6-section、200-400 行、focused on *how to implement / debug feature X*
- **Migration playbook**：5 種 structure（依 diff dimension）、200-400 行 / 篇、focused on *how to move from A to B*
- 共同：問題情境 / 故障演練 / 容量 / 整合段；差異：中間「process / structure」段

寫前的 *content category 判讀* 是新方法論議題、不是 deep article methodology 涵蓋。

---

## 反模式

| 反模式                                                  | 後果                                                                |
| ------------------------------------------------------- | ------------------------------------------------------------------- |
| 寫 migration playbook 前不做 diff dimension audit       | 套錯結構模板、phase 變空白或 process 強行線性                       |
| 假設「migration 都 phased」                             | drop-in / paradigm shift 套 phased 結構失真                          |
| 假設「跟 deep article methodology 一樣」                | 6-section 套 cross-vendor process 缺 differentiation                |
| 跨 type 強行套同一個結構                                | 5 種 type 內容差異被壓平、跨篇連讀預期化                            |
| 沒列「結構 differentiator」段                           | 讀者不知道為什麼這篇結構跟其他 migration playbook 不同              |
| Diff dimension audit 只看 schema                        | 忽略 operational / paradigm / components 維度、套錯結構             |
| 把混合架構 paradigm shift 寫成 phased                   | 假設 source 會消失、cleanup phase 變 fiction                         |
| 把 drop-in 寫成 phased                                  | 多 phase 變空白、文章拉長但無內容                                   |

---

## 跟其他抽象層原則的關係

| 原則                                                                                            | 關係                                                                                                                              |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [#122 Cadence 同質化是模板的隱形維度](../cadence-homogenization-in-batch-writing/)              | 補位 — #122 處理 *同 type 內的 framing collapse*、本卡處理 *跨 type 套錯結構*；兩者都跟「主題語意 attractor」相關                |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                       | 同骨 — 套既有結構模板最便利（不用判 diff dimension）、但意圖（跟主題本質對位）失準                                              |
| [#125 Collapse 是隱形預設](../collapse-is-implicit-default/)                                   | 子實例 — 結構模板 collapse 到單一 type 是 #125 在「content structure」surface 的具體形態                                          |
| [#118 Standard-driven vs case-driven domain judgment](../standard-driven-vs-case-driven-domain-judgment/) | Sibling — 兩卡都是 *寫作前的 domain audit*、#118 判 case-driven vs standard-driven、本卡判 process structure type           |
| [#119 章節已有 routing skeleton 走補強段](../routing-layer-chapter-recognition/)                | 同骨 — 都是「結構辨識先於內容生成」、#119 是章節內、本卡是文章層                                                                |
| [#128 Data topology 是 process content 的第 6 audit 維度](../data-topology-as-audit-dimension/) | 子卡 — 本卡 audit 框架從 5 維擴張到 6 維、新增 Type F；#128 是 6 維 audit 的 atomic 定義跟 Type F 詳細 anatomy                  |

---

## 判讀徵兆

| 訊號                                              | 該做的事                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| 寫 migration playbook 前直覺套「6 phase」         | 先跑 diff dimension audit、可能 type A-E 對應不同結構                |
| 寫到一半某 phase 內容空白                         | 結構錯位、可能不需要這個 phase                                       |
| 兩篇同 category content 連讀差異不大              | 結構過於 universal、缺結構 differentiator 段                          |
| 「cleanup phase」寫不出內容                       | 可能是 paradigm shift type、source 不會消失                          |
| 章節數 ≥ 15 還沒寫完                               | 結構過 phased、考慮是不是 type B / E 不需要這麼多                    |
| 章節 4 「故障演練」段比其他段都簡單                | 結構過 abstract、實作層細節缺                                        |
| 寫作前沒列 source / target 的 diff dimension      | 結構 risk、補 audit                                                  |

**核心**：Process content 的結構由 *source / target 差異維度組合* 決定、不是 universal phased / 6-section 模板。寫作前必須跑 *diff dimension audit*（schema / operational / paradigm / components / application change 5 維度）、選對應主結構、其他高維度獨立加段；跳過 audit 會套錯模板、phase 變空白或 process 強行線性。

---

## Self-aware limitation：本卡的 sample-driven over-fit 風險

本卡 5 type 來自 5 篇 migration playbook 的 dogfood 觀察、本身就是 *N=5 sample 推導出 5 type taxonomy* — 跟本卡批判的「universal phased 模板」「[#122](../cadence-homogenization-in-batch-writing/) cadence collapse」「[#125](../collapse-is-implicit-default/) reduce 多維到單格」是 *同骨錯誤*。

| Reviewer 揭露的本卡 over-fit | 對應的本卡建議 |
| --------------------------- | -------------- |
| 5 type 非窮盡（漏 4 種主流情境）| 「5 type 是 axis-aligned simplification、非窮盡」段、未來累積更多 sample 後可能重構 |
| 5 type 互斥失效（多軸 High 配對）| 「多重歸類跟 tie-breaking」段、不強迫單一 type 標籤 |
| 「最大維度」沒處理 tie       | 主導維度判讀規則（Schema > Paradigm > Operational > Components）|
| 「Partial collapse 教育價值高」是 post-hoc | 修正為 [#122 Update 段第 8 點](../cadence-homogenization-in-batch-writing/) — partial collapse 是 attractor 訊號、不增強 principle |

本卡是 *current best understanding*、不是 *已驗證的完備理論*。Tripwire：

- 若下一輪 migration batch 浮現 *無法歸進現有 5 type 的新 structure*、應該擴充 type 集合而不是強行歸類
- 若同一 source/target 配對出現 *結構翻轉*（例 PostgreSQL → CockroachDB 在不同 application context 走不同主結構）、應該檢視 *主導維度* 規則是否需要動態化
- 若 type 數量擴張到 8+、應該評估是否該重構為 *維度 × 維度 grid* 而不是 type list

---

承認 limitation 本身是 dogfood — [#122 cadence 同質化](../cadence-homogenization-in-batch-writing/) 講「natural attractor 不規劃就 collapse」、本卡的 5 type 就是 *5 個 sample 的 natural attractor*；不在卡內承認、就重複了 [#125 隱形預設](../collapse-is-implicit-default/) 的 collapse pattern。本段是 self-correction、不是 disclaimer。

### Update（2026-05-19）：第二輪 migration batch 驗證 limitation

第二輪 migration batch（5 篇）跑完、self-aware limitation 三項預測得到驗證：

| 預測（self-aware limitation 段）              | 第二輪實證                                                                                            |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 漏類確實存在、未來累積更多 sample 後可能重構  | major version upgrade（[postgresql/major-version-upgrade](/backend/01-database/vendors/postgresql/major-version-upgrade/)）跟 re-sharding（[redis/cluster-resharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)）結構跟 5 type 完全不同、各有自己的 anatomy；漏類確認 |
| Multi-axis 處理規則（主導維度 + 高維度獨立段）| [postgresql/migrate-to-cockroachdb](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) 三維皆 High、結構 = Type E 主結構 + Type A schema gap 段 + Type C operational redesign 段、不強迫單一 type 標籤；規則成立 |
| Type A / Type C 標準形態仍適用                | [mysql/migrate-to-postgresql](/backend/01-database/vendors/mysql/migrate-to-postgresql/)（Type A）+ [mongodb/migrate-to-atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)（Type C）走標準模板、跟第一輪同 type 對應；標準形態驗證 |

新發現（不在 self-aware limitation 預測內、需要後續處理）：

- **新 audit 維度浮現**：re-sharding 揭露「data topology」是 5 維沒有的軸；audit 擴張為 6 維（加 topology 軸）已執行、見 [#128 Data topology 是 process content 的第 6 audit 維度](../data-topology-as-audit-dimension/) + 本卡 audit table 新加 row 跟 Type F anatomy
- **「為什麼這篇不套」是漏類文章的好結構模板**：major-version-upgrade 跟 cluster-resharding 都用這個 frame 開頭、明示跟 5 type 的邊界
- **「高維度獨立段」對照表**自然在 multi-axis 文章浮現（cockroachdb 篇）— 應該升級為 multi-axis migration 的標準結構元素
