# Stage 0 variant 規劃紀律

> **角色**：本卡是 `migration-playbook-methodology` 的支撐型原則、被 [SKILL.md](../../SKILL.md) Stage 0 variant 規劃段引用。
>
> **何時讀**：批量寫 migration playbook（≥ 5 同類檔）寫前；發現「為什麼遷：X/Y/Z driver」collapse pattern 時。

## 核心原則

寫批量 migration playbook 前必須做 Stage 0 variant 規劃 — 主動列 N 種 entry framing variant、對映 N 篇主題分配；不是事後 polish、不是依賴 stage-internal checkpoint 抓 collapse。

## 為什麼必須

30 篇 migration / process content 跨 6 dogfood batch cadence audit 結果（截至 2026-05-19）：

| 批次                              | Sample | Variant 規劃                  | Entry framing collapse |
| --------------------------------- | ------ | ----------------------------- | ---------------------- |
| backend/07 vendor batch（無規劃）  | N=51   | 無                            | 51/51 (100%)           |
| Deep article 第一批（跨 vendor）   | N=4    | 主動                          | 0/4 (0%)               |
| Deep article 第二批（同 vendor）   | N=5    | 主動                          | 0/5 (0%)               |
| Migration playbook 第一輪          | N=5    | 3 被動 + 2 主動               | 3/5 (60%)              |
| Migration playbook 第二輪          | N=5    | 全主動                        | 0/5 (0%)               |
| Migration playbook 第三輪          | N=5    | 全主動                        | 0/5 (0%)               |
| Migration playbook 第四輪          | N=5    | 全主動 entry layer            | 0/5 (0%) entry / **5/5 (100%) section 2** |
| Migration playbook 第五輪（驗證）  | N=5    | 全主動 entry layer            | 0/5 (0%) entry / **5/5 (100%) section 2** |

**注意**：上表 batch 4-5 揭露 *entry framing variant 解決不了 section 2+ collapse*；entry 0% 不代表整篇 cadence 健康。詳見 [multi-element-variant-planning](./multi-element-variant-planning.md) 處理 driver framing + 其他 element axis 的 collapse 風險。

關鍵 finding：

- **Sample size 不能解 collapse**：N=5 仍可 100% collapse（被動寫作）跟 0% collapse（主動規劃）— 唯一變數是 Stage 0
- **主題相似性高（migration 都圍繞「為什麼遷」）會自然 collapse**：被動寫作下「為什麼遷：cost / multi-vendor / cloud-native driver」是 natural attractor
- **Stage-internal checkpoint 不夠**：第一輪有抽樣 checkpoint、仍 3/5 collapse、因為 stage 0 沒準備 variant、checkpoint 只能 detect 不能 design

## Variant 列表（從 20 篇 dogfood 收集）

| Variant | Frame                                                      | 範例篇                                                  |
| ------- | ---------------------------------------------------------- | ------------------------------------------------------- |
| A       | 標準「問題情境」開頭                                       | New Relic → Datadog（migration playbook 第五輪）         |
| B       | 痛點宣告 case-led「為什麼 X 越跑越慢」                       | K8s graceful shutdown / PG partition redesign            |
| C       | 概念反向定義「X 不是 Y、是 Z」                              | Partition 不是切表 / Atlas 不是 Mongo + managed         |
| D       | 對照表 / 矩陣 / 決策表開頭                                 | Cloudflare Page Shield / DynamoDB consistency           |
| E       | Lifecycle-driven 結構標題                                  | Patroni HA failover lifecycle 5 段                       |
| F       | Meta-reflection「為什麼這篇不套 N 種 type」                | PG major version upgrade / PG multi-region GDPR        |
| G       | Paradox「字面 X 不成立」                                    | Kafka ↔ NATS / Redis re-sharding source = target        |
| H       | Cost / bill 拆解開頭                                       | Datadog → Grafana Stack                                 |
| I       | Reviewer / question 回應                                   | MongoDB shard + multi-DC（reviewer D 質疑回應）         |
| J       | Code-led example sample                                    | MySQL → PostgreSQL SQL dialect diff sample              |

## Stage 0 流程

```text
Step 1: 列預計寫的批量 N 篇主題

Step 2: 為每篇分配 Variant（A-J 中選）
  - 同 batch 內 N 種 variant 不重複
  - 主題本質適合什麼 variant：drop-in 適合 C / paradox 主題適合 G
  - 不確定時用「natural fit」、不強制配對

Step 3: 寫第 1 篇前驗證
  - 第 1 篇 entry framing 是否符合分配的 variant
  - 章節 1 H2 標題是否反映 variant frame

Step 4: 寫第 N+1 篇前回顧
  - 抽前 N 篇章節 1 entry 並列
  - 確認分配的 variant 仍在輪替
  - 發現 drift 立即修方向

Step 5: 整批完成後跨檔 cadence audit
  - rg「為什麼遷：」collapse marker
  - rg「✅ ❌」emoji
  - 跨檔 grep 過渡詞密度
```

## 反模式

| 反模式                                       | 後果                                          |
| -------------------------------------------- | --------------------------------------------- |
| Variant 規劃延後到「寫到 1-2 篇後再說」      | Natural attractor 已 lock-in、後續難脫鉤      |
| 主題相似就「自然會錯開」                     | 主題相似 = 主題語意 attractor 強、被動下 collapse |
| 寫完後 reviewer audit 才發現 cadence collapse | 修正成本 N 倍                                  |
| 同 variant 寫 2 篇                            | 局部 collapse、應 1 篇 1 variant               |
| Stage-internal checkpoint 取代 Stage 0       | Checkpoint 是監測工具、不是設計工具            |

## 跟其他原則的關係

| 原則                                                                  | 關係                                                          |
| --------------------------------------------------------------------- | ------------------------------------------------------------- |
| [six-dimension-audit-framework](./six-dimension-audit-framework.md)   | 互補 — audit 決定主結構、variant 決定 entry framing            |
| [self-aware-limitation-pattern](./self-aware-limitation-pattern.md)   | Reviewer audit 後處理 — Stage 0 確保 cadence、不擋 review 揭露 structural issue |

## 自查清單

寫批量 migration playbook 前：

1. **批量 N ≥ 3 嗎**？SKILL.md 表面寫 ≥ 3 必做、實務上 N=3-4 小批量也建議 Stage 0
2. **N 篇主題列了嗎**？
3. **每篇對映了 variant 嗎**？
4. **N 個 variant 不重複嗎**？
5. **寫前 30 分鐘有規劃時間嗎**？沒有就先停寫、不要邊寫邊規劃
