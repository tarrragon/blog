# Case 採集覆蓋缺口的誠實標明

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [stage-0-case-collection](../stage-0-case-collection.md) 引用。
>
> **何時讀**：Stage 0 採集完成、發現某些大綱章節公開 case 稀薄時、決定如何寫入 `_index.md` 跟 vendor 頁。

## 核心原則

採集階段不可能對所有大綱章節都採到豐富公開 case。當某些章節 / 主題公開資料稀薄、要**誠實標明缺口**、不假裝完整覆蓋。

誠實姿態的兩個結果：

1. 讀者知道哪些章節 case-driven、哪些章節該對其他來源（standard / 官方文件 / 通用工程知識）信任
2. 寫作者寫到該章節時、不被迫編造 case（編造會破壞 case-first 的可信度）

## 為什麼會有覆蓋缺口

公開 case 的存在度跟以下因素相關、不一定跟議題的工程重要性對齊：

| 因素              | 影響                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------- |
| Vendor 社群活躍度 | Kafka 社群比 NATS 大、公開 case 更多                                                      |
| Feature 成熟度    | 新 feature（Kafka KRaft、Redis Streams + Functions）公開 case 稀薄                        |
| 議題公開度        | 內部運維議題（IAM 配置、Operator 部署）公司不常公開、不像 incident / migration 那樣高觸發 |
| 議題教學成本      | 概念偏底層 / 邊緣的議題、blog 文章作者較少寫                                              |

這些因素是結構性的、不會因為「再多找一輪」就改變。採集到邊際遞減（純新議題 < 1 個 / case、重複 frame > 50%）就該停、不強求覆蓋每個章節。

## 缺口的明示方式

### 在 `_index.md` 加「覆蓋缺口」段

```markdown
## 案例覆蓋缺口（待補）

下列大綱章節在本案例庫中**公開 customer-side case 偏弱或缺**、撰寫正文時要明示「以下分析依官方文件 / standard / 通用模式推導、非 case-driven」：

- **{Vendor A} {章節 X}**：缺 customer 一手案例、目前依官方 {KIP / 公告} 為準
- **{Vendor B} {章節 Y}**：customer engineering blog 著墨少、建議依官方文件 + 通用安全原則
- ...
```

### 在 vendor 頁的「案例回寫」section 末加

```markdown
**{特定章節} 缺直接 customer case**：可補 {替代來源、如 vendor 官方 blog / standard framework / 通用工程知識}、後續若有 customer 一手案例可加。
```

## 缺口跟 standard-driven 領域的關係

[SKILL.md 的 Standard-driven vs case-driven 段]：當整個領域（如 LLM 安全）的 standard framework 比 case 庫成熟、整個領域走 standard-driven、不建 case 庫。

覆蓋缺口是「**case-driven 領域內、部分章節**」的情況、跟整個領域 standard-driven 是不同層次：

| 情境                                   | 處理方式                                                                     |
| -------------------------------------- | ---------------------------------------------------------------------------- |
| 整個領域 standard-driven               | 整模組不建 case 庫、依 standard framework 撰寫 + Last reviewed cadence       |
| Case-driven 領域內、整體 case 庫成熟   | Stage 1 audit 開始寫作                                                       |
| Case-driven 領域內、特定章節 case 稀薄 | 標明覆蓋缺口、該章節改走 standard / 通用工程知識補強、其他章節仍 case-driven |

第三類是這張 principle 卡的處理範圍。

## 撰寫該章節時的策略

當寫作到「公開 case 稀薄」的章節：

1. **不編造 case**：找不到就找不到、不要拿訓練資料拼湊一個假案例
2. **改引官方文件 / KIP / standard**：明示「依 {來源} 跟通用工程知識撰寫」
3. **保留章節結構**：標準章節格式不變、只是內容來源換成 standard / 通用
4. **加 Last reviewed cadence**：因為 standard / 官方文件會改版、章節要定期重審
5. **保留 case 觀察點**：若有零星案例提到該議題（即使深度淺）、列為「值得追蹤的方向」、不寫「對應 [case] 揭露」斷言

## 採集時的缺口判讀

採集後盤點覆蓋：

```text
{Vendor} 進階主題覆蓋盤點：

✅ Topic A：N 個案例（含 anchor）
✅ Topic B：N 個案例
⚠️ Topic C：1 個邊緣案例（公開資料偏少）
❌ Topic D：0 個案例（公開資料缺）
```

⚠️ 跟 ❌ 都該列入「案例覆蓋缺口」段。⚠️ 標「該章節公開案例稀薄」、❌ 標「該章節缺直接 customer case」。

## 已知的覆蓋缺口典型

跨多個模組驗證、以下類型的章節常出現公開 case 稀薄：

| 類型                                                           | 為什麼稀薄                              |
| -------------------------------------------------------------- | --------------------------------------- |
| 新 feature / mode（KRaft、Redis 7 Functions、Pulsar new tier） | Feature 成熟度低、公開使用案例累積中    |
| 內部運維議題（IAM 配置、Operator 部署、ACL 細節）              | 公司不常公開「我們怎麼設 IAM」          |
| 治理 / 流程議題（multi-tenant 配額、命名規範）                 | 通常進公司內部 wiki、不寫成 blog        |
| 替代 vendor 特定 feature（vendor 自家 plugin 整合）            | Cross-vendor 整合的公開資料偏 marketing |

採集時對這些類型先預期缺口、不強求填滿、改走 standard / 通用工程知識補強。

## 跟其他原則的關係

- 跟 [case-type-discrimination](./case-type-discrimination.md) 互補：discrimination 講「拿到 case 後該怎麼承接」、coverage gap 講「沒拿到 case 時該怎麼標明」
- 跟 [fact-vs-derive-layering](./fact-vs-derive-layering.md) 互補：fact-vs-derive 講「case 內的事實 vs 判讀分層」、coverage gap 講「整章節沒 case 時怎麼處理」
