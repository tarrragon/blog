# 6 維 diff dimension audit framework

> **角色**：本卡是 `migration-playbook-methodology` 的支撐型原則、被 [SKILL.md](../../SKILL.md) Step 1-6 引用。
>
> **何時讀**：寫 migration playbook / cross-vendor process content 前、判讀 type 跟結構時。

## 6 個維度

跨 X process content 的結構由 source / target 在以下 6 維度的差異組合決定：

| 維度                 | 評估問題                                                            | 例（High）                              |
| -------------------- | ------------------------------------------------------------------- | --------------------------------------- |
| Schema / API         | source 跟 target 的 API、data model、wire protocol 差異多大？        | Splunk SPL ↔ Elastic KQL                |
| Operational model    | HA / backup / monitoring / capacity 邏輯差異多大？                   | Self-managed → cloud managed            |
| Abstraction / paradigm | 兩端是否同類產品（同抽象層）？                                       | Kafka log ↔ NATS pub-sub                |
| Number of components | 一站式 vs multi-tool 是否需要拆分？                                  | Datadog → Mimir + Loki + Tempo          |
| Application change   | application code 需要改多少？                                        | SDK 換、retry pattern 重設計             |
| Data topology        | Sharding / partition / replication / region / co-location 拓樸是否變動？ | Redis cluster re-sharding / multi-DC |

每維度評 High / Medium / Low、主導維度決定主結構。

## 主導維度對映常見 type

| 維度組合                             | 對映 type                                                 |
| ------------------------------------ | --------------------------------------------------------- |
| Schema = High（其他 Low）            | Type A phased rule translation                            |
| 全 Low / 全 Medium                   | Type B drop-in                                            |
| Operational = High（其他 Low）       | Type C operational redesign hybrid                        |
| Components = High（一站式 → multi-tool）| Type D parallel streams                                   |
| Paradigm = High                      | Type E partial + 混合架構                                 |
| Topology = High（其他 Low）          | Type F topology re-layout                                 |
| 多軸 High                            | 按多重歸類規則處理                                        |

## 多重歸類 + tie-breaking

實際 source / target 配對 *很少* 完美對映單一 type；常見情境：

| 情境                                  | 例                                                              | 處理規則                                                                                       |
| ------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 三維度都 High                          | PostgreSQL → CockroachDB（Schema + Operational + Paradigm 三 High）| 主結構選讀者最關心的維度、其他維度抽出獨立段補充                                              |
| 全 Medium（無 High）                   | Redis → KeyDB（API 微差 + ops 微差）                            | 走 Type B drop-in、用「相容性 audit」段列 medium 差異點                                       |
| 一維 High 但 application change 連帶 High | MySQL → PostgreSQL                                          | 走 Type A、application change 章節獨立段、不壓進 Phase 4 cutover                              |
| Schema High + Components High         | Splunk → Elastic + Tines + PagerDuty                            | 主結構走 Type A（Schema 為主驅動）、Type D 的 multi-tool 用「target stack 拆分」獨立段        |
| Schema + Operational + Paradigm 全 High | PostgreSQL → CockroachDB                                       | 主結構走 Type E（paradigm 為主）、Schema + Operational 高維度獨立段                          |

**主導維度優先序**（current best heuristic、audience-dependent）：

```text
Schema > Paradigm > Operational > Topology > Components
```

注意：

- 這是「跨 audience 平均」、不是 universal 規則
- DBA 視角下 Topology 可能 > Operational、application developer 視角下 Schema > Paradigm
- 沒有 tie-breaking 規則時用優先序、有業務 context 時優先依 context

## Step 6 漏類處理

6 type 不窮盡、已知漏類至少 3 種、不適用 6 type：

| 漏類                            | 例                                            | 為何現有 type 不覆蓋                                                       |
| ------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------ |
| 同 vendor major version upgrade | PostgreSQL 14 → 17 / Kafka 3 → 4              | Source / target 是同 vendor、現有 type 預設跨 vendor                      |
| 政策 / 合規驅動                 | Atlassian server EOL / PCI 強制資料 region    | Driver 在外部、但資料層仍走 type A-F 之一；audit 重點是 evidence collection |
| Acquisition / merger consolidation | 兩 org 合併 / 兩 K8s cluster federate     | Source / target 同產品、處理 identity / RBAC / 歷史資料合併                |

漏類情境的結構：

- Major version upgrade：deep article 6-section + upgrade audit 段
- 政策驅動：底層仍走 Type A-F、加合規 evidence collection 段
- Acquisition：跨 identity / RBAC 議題、跟既有 6 type 都不對齊、可能需要自訂結構

## Step 7 候選軸評估

第三輪 batch 揭露 3 軸候選（identity / consistency / residency）、各 1 case 驗證可獨立發生 + 帶獨立工作量：

- **Identity axis**：Vault → AWS Secrets Manager、identity model 對位是主軸（不歸 schema / operational / application）
- **Consistency axis**：DynamoDB strong → eventual、per-call-site contract review 是主軸（不歸 paradigm）
- **Residency axis**：GDPR multi-region、合規 evidence collection 是主軸；可能是 cross-cutting constraint 而非獨立軸

**Current status**：候選、不 commit；累積 3-5 case / 軸後再評估升 audit 7-9 維。

詳細 axis 候選評估流程見 [axis-candidate-evaluation](./axis-candidate-evaluation.md)。

## 反模式

| 反模式                                   | 後果                                                       |
| ---------------------------------------- | ---------------------------------------------------------- |
| 跳過 audit 直接套既有模板                 | Phase 變空白 / process 強行線性                            |
| 假設「migration 都 phased」              | drop-in / paradigm shift / topology re-layout 套 phased 失真 |
| 6 維 audit 只看 schema                   | 忽略 operational / paradigm / components / topology 維度    |
| 多軸 High 強塞單一 type 標籤             | 5 種 type 內容差異被壓平、跨篇連讀預期化                    |
| 沒列「結構 differentiator」段             | 讀者不知道為什麼這篇結構跟其他 migration playbook 不同      |
| Audit 維度只看「是否變動」、不看「是否變動有獨立工作量」 | 把 connectivity 等 *衍生變量* 當獨立軸                    |

## 跟其他原則的關係

| 原則                                                                   | 關係                                                                     |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [stage-0-variant-discipline](./stage-0-variant-discipline.md)          | 寫作流程紀律 — audit 完成後寫批量必須做 stage 0 variant 規劃             |
| [self-aware-limitation-pattern](./self-aware-limitation-pattern.md)    | 後處理紀律 — audit 框架擴張時用 meta-acknowledgment 模式                |
| [axis-candidate-evaluation](./axis-candidate-evaluation.md)            | 演化機制 — 6 維不夠用時、評估升 7-9 維的規則                            |
