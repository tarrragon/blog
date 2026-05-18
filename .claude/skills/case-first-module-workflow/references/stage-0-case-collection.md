# Stage 0：案例採集（從零或補強建 case 庫）

> **角色**：本卡是 `case-first-module-workflow` 的執行型 reference、被 [SKILL.md](../SKILL.md) 引用。
>
> **何時讀**：開始寫新模組前發現 case 庫從零、或既有 case 庫覆蓋不足某些章節 / vendor / 主題時。

## 為什麼需要 stage 0

既有 stage 1-5 假設「case 庫已存在」、stage 1 從讀 case 開始。但實作上常碰到：

- 新主題沒有 case 庫
- 既有 case 庫只覆蓋部分章節 / vendor、其他章節 / vendor 缺案例
- 案例量不夠驅動寫作（< 5 個 case per vendor 容易讓寫作落入「為了舉例」而非「為了貼合真實需求」）

Stage 0 是 case 庫的「採集生產階段」、跟 stage 1 audit（讀已有 case 抽 finding）是兩個獨立階段。

## 採集目標的量級

每個 vendor / 主題建議採集 **5-10 個案例**、含三類：

| 類別                                  | 比例   | 角色                                                 |
| ------------------------------------- | ------ | ---------------------------------------------------- |
| **Anchor case**（覆蓋多議題、深度高） | 1-3 個 | 寫作主軸、可在多章節引用                             |
| **邊緣 case**（單一議題深度）         | 3-6 個 | 補強特定議題、避免單一 anchor 過載                   |
| **反例 / 退場 case**                  | 1-2 個 | 教學價值高、揭露「不該做什麼」、「何時轉走其他方案」 |

低於 5 個案例的 case 庫不足以驅動 case-first 寫作、應補採集到 5-10 個再進 stage 1。

## 採集執行範式：Agent team 平行調研

跟 stage 3 reviewer 用法不同、stage 0 用 agent 做「研究採集」、不是「審查現有內容」。

### 為什麼平行 agent

- 多 vendor / 多主題的採集任務、各自獨立、適合平行化
- 每個 agent 需要做 WebSearch + WebFetch 多步驟、串行做總時間爆炸
- agent 自身 context 跑滿 search/fetch、不污染主 context

### Spawn 範式

每個 agent 用 `subagent_type: general-purpose`、`run_in_background: true`、prompt 含五個必要要素：

1. **採集目標**：N 個案例（5-10）
2. **硬閘門**：必須 WebFetch 驗證 URL 可訪 + 內容真的提到目標 vendor / 主題、不能編造
3. **排除清單**：已有 case 別重複（列出 vendor / 公司 / 主題）+ vendor 自家 marketing 頁排除
4. **對齊大綱**：列該 vendor 大綱的進階主題、每個案例對應其中一個主題
5. **回傳格式**：清單形式（title / source URL / observation / finding / 對應大綱章節）、附「找到但 URL 失效 / 內容不對應的捨棄候選」列表

主 context 只收 finding summary、不收 agent 完整 transcript。

## WebFetch 驗證的硬閘門

LLM 容易編造或誤引用案例。三類常見編造模式：

1. **公司名是真實的、URL 是猜的**（404）
2. **URL 是真實的、內容不提目標 vendor**（marketing 提及但無工程細節）
3. **公司用該 vendor 但不是案例描述的場景**（例：公司用 Redis 但講的是 cache、不是 Streams）

WebFetch 是反編造的硬閘門。Agent 採集時必須：

- 每個案例的 source URL 都用 WebFetch 取回確認
- 確認頁面真的提到該 vendor / 主題（不只是 logo wall）
- 確認頁面內容對應 finding 描述的議題（不只是順帶一句）

採集回報要明示「已驗證可訪」vs「找到但 URL 失效 / 內容不對應」兩列、避免主 context 重新驗證。

## 採集後的薄殼 case 檔形態

Stage 0 採集只寫**薄殼**（不寫策略 / 下一步路由）、目的是先覆蓋大量案例、避免每個案例都當 rich case 寫到位拖慢採集進度。

薄殼形態約 15-20 行、含：

```markdown
---
frontmatter (title / date / description / weight / tags)
---

這個案例的核心責任是 {one-sentence purpose}。

## 觀察

{2-3 sentences observation：規模、場景、做了什麼}

## 判讀

{2-3 sentences finding：核心工程議題、揭露什麼判讀條件}

## 對應大綱

{vendor / 主題} 進階主題：{對應的章節}

## 下一步路由

回 [{vendor} vendor 頁](...)。

## 引用源

- [{Title}]({URL})
```

不寫「策略」段、不寫詳細「下一步路由」清單 — 這兩段在 stage 1 audit 後、確認該 case 升級為 anchor 時才擴寫（升為 rich case）。

## 命名規則（vendor / 主題前綴）

當案例量大（30+ 案例、跨多 vendor）、單純編號（C1, C2...）會難辨識來源。建議命名：

```text
cases/{vendor-or-topic-prefix}-{company}-{focus}.md
```

例：

- `cases/kafka-pinterest-tiered-storage.md`
- `cases/rabbitmq-bloomberg-multi-tenant-vhost.md`
- `cases/nats-form3-multi-cloud-payments.md`

數字編號（C1, C2...）保留當 reference ID、跟 slug 並存。`_index.md` 列表用編號、檔案系統用 slug。

## 採集完成後的整理

採集完成後、`_index.md` 重組成「by vendor / by 主題」分組、加「跨 vendor 對照案例」獨立段、加「覆蓋缺口」明示段。

詳見 [stage-0-collection-checklist](./stage-0-collection-checklist.md)。

## Stage 0 完成的退出條件

- 每個目標 vendor / 主題達 5-10 個 verified 案例
- 案例庫含 anchor + 邊緣 + 反例三類
- `_index.md` 重組完成、含覆蓋缺口明示
- 每個 vendor 頁的「案例回寫」section 改為實際案例列表（取代「待補」）

進入 Stage 1 audit 前、把「該章節公開 case 稀薄」的覆蓋缺口寫入 vendor 頁 / 章節大綱、提醒後續寫作該段時改走 standard-driven 或通用工程知識補強。

## 跟其他 stage 的關係

- **Stage 0 → Stage 1**：採集到的薄殼案例進入 audit、抽 findings
- **Stage 0 跟 Stage 3 都用 agent team、但用法不同**：
  - Stage 0：研究採集、agent 跑 WebSearch / WebFetch、回傳 finding 清單
  - Stage 3：審查既有內容、agent 讀 commit + case + 章節、回傳 review issue
  - 兩種都用 `subagent_type: general-purpose`、`run_in_background: true`、節省主 context

## 採集陷阱（已踩過）

1. **跨網域引用觸發 anti-phishing**：synadia.com 引用 NATS 案例、若 link display 寫 "NATS.io" 會觸發 markdown lint 反釣魚規則。採集薄殼時注意 link display 要跟 href domain 一致、或用 neutral wording（如「Synadia blog」明示來源平台）。詳見 [stage-0-collection-checklist](./stage-0-collection-checklist.md)。
2. **同公司多案例不要平行 fetch**：某些公司（如 Mercari）寫 case 是文化、單一公司有 4+ 篇深度 case 文。Agent 採集時建議「找到一個案例就把同公司其他案例列入候選」、避免不同 agent 重複 fetch 同公司、浪費 token。
3. **公開案例的 vendor 偏向**：Kafka 案例庫遠比 NATS / Redis Streams 豐富、不只是「案例庫不完整」、是 vendor 社群活躍度差異。採集量級該對齊 vendor 的公開資料密度、不強求每個 vendor 都 10 個案例。詳見 [coverage-gap principle](./principles/case-collection-coverage-gap.md)。
