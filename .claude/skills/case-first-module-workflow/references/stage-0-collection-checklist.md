# Stage 0 採集 Checklist：執行細節

> **角色**：本卡是 `case-first-module-workflow` 的執行型 reference、被 [stage-0-case-collection](./stage-0-case-collection.md) 引用。
>
> **何時讀**：Stage 0 採集 agent 跑完、寫薄殼 case 檔時。

## Checklist 概覽

採集回傳後寫薄殼 case 檔、每個 case 寫完 commit 前檢查：

1. [ ] Frontmatter 含 title / date / description / weight / tags
2. [ ] 編號連續（接續既有最大編號、不跳號）
3. [ ] Slug 含 vendor / 主題前綴（避免編號衝突）
4. [ ] Link display 跟 href domain 一致（反釣魚）
5. [ ] 觀察 / 判讀分段（不混 fact 跟 derive）
6. [ ] 對應大綱章節明示（跟 vendor 頁的進階主題對齊）
7. [ ] 引用源是「customer / user 視角」、不是 vendor 自家 marketing
8. [ ] 反例 / 退場類案例在 description 標明「反例」標籤

## Link display 跟 href 一致（反釣魚硬規則）

Markdown lint 有反釣魚規則：link display text 若含 TLD 字樣（`.com` / `.org` / `.io` / `.dev` / `.tw` 等）、href domain 必須一致。

### 踩過的例子

```markdown
<!-- ❌ 觸發 anti-phishing：display 含 "NATS.io"、href 是 synadia.com -->
- [How Form3 Built ... with NATS.io JetStream](https://www.synadia.com/blog/...)

<!-- ✅ 修法 1：display 不含 domain hint -->
- [How Form3 Built a Multi-Cloud Low-Latency Payments Service with NATS JetStream (Synadia blog)](https://www.synadia.com/blog/...)

<!-- ✅ 修法 2：用 neutral wording 明示來源平台 -->
- [Form3 NATS Case Study (Synadia)](https://www.synadia.com/blog/...)
```

採集時若發現案例由第三方平台（vendor partner / customer studies 頁）發布、link display 要明示來源平台、避免讀者誤以為連到 vendor 官方頁。

## 命名規則

### 既有 case 庫的編號

既有案例用 `C1`-`C10` 連續編號、檔名是 `cases/<descriptive-slug>.md`（如 `meta-foqs-global-migration.md`）、`_index.md` table 用編號當 ID。

### 新採集案例的命名

當採集量大（30+ 案例）、加 vendor / 主題前綴：

```text
cases/{vendor-or-topic-prefix}-{company}-{focus}.md
```

例：

- `cases/kafka-pinterest-tiered-storage.md`
- `cases/rabbitmq-bloomberg-multi-tenant-vhost.md`
- `cases/redis-streams-bitso-reliable-streams.md`
- `cases/sqs-airbnb-dynein-delayed-jobs.md`
- `cases/pubsub-spotify-event-delivery-platform.md`

數字編號繼續連續（如 C11, C12...）、跟 slug 並存：

- Frontmatter title：`"3.C11 Pinterest：Kafka tiered storage broker-decoupled"`
- Slug：`kafka-pinterest-tiered-storage`

## `_index.md` 重組的章節結構

採集完成後、`_index.md` 重組為：

```markdown
## 通用案例（跨 vendor / 反例 / 規模對照）

[列既有 C1-C10 表格、跨 vendor 通用案例]

## {Vendor A} 案例

[列 vendor A 的專屬案例表格]

## {Vendor B} 案例

[同上]

...

## 案例覆蓋缺口（待補）

下列大綱章節在本案例庫中**公開 customer-side case 偏弱或缺**、撰寫正文時要明示「以下分析依官方文件 / standard / 通用模式推導、非 case-driven」：

- {vendor} {章節}：{原因說明}
- ...
```

「案例覆蓋缺口」段是 stage 0 誠實標明的關鍵段、不省略。詳見 [coverage-gap principle](./principles/case-collection-coverage-gap.md)。

## Vendor 頁的「案例回寫」section

採集完成後、各 vendor 頁的「案例回寫」section 改成：

```markdown
## 案例回寫

### {Vendor} 專屬案例（C{N1}-C{N2}）

| 案例                                | 主討論議題                |
| ----------------------------------- | ------------------------- |
| [3.CN1 {Company} {Topic}](...)      | {對應大綱章節}            |
| ...                                 | ...                       |

### 跨 vendor 對照

| 案例                                | 對該 vendor 的對應          |
| ----------------------------------- | --------------------------- |
| [3.CN {跨 vendor case}](...)        | {對照角度}                  |
| ...                                 | ...                         |

**{特定章節} 缺直接 customer case**：{說明 + 替代方案、依官方文件或 standard 撰寫}
```

兩段（vendor-specific + 跨 vendor 對照）分開、避免讀者把跨 vendor case 當該 vendor 專屬。

## Single-company 多案例的採集處理

某些公司（如 Mercari、Spotify、Pinterest、Wix、LinkedIn）寫 case 是文化、單一公司有 4+ 篇深度 case 文。採集時：

1. **Agent prompt 明示「找到一公司可繼續找該公司其他案例」**：避免不同 agent 重複 fetch
2. **同公司多 case 用不同 slug 區分主題**：`pubsub-mercari-actionable-history.md` / `pubsub-mercari-item-feed-dlt.md` / `pubsub-mercari-line-flow-control.md` / `pubsub-mercari-b2c-grpc-pusher.md`
3. **`_index.md` 列表上不合併同公司案例**：保持每個 case 一行、方便 cross-reference

Mercari 4 篇 Pub/Sub case 是 anchor cluster — 撰寫正文時可作為單一 vendor 多角度的深度引用、其他案例輔助。

## 採集回報後的整理流程

1. Agent 回傳「已驗證案例 + 捨棄候選」清單
2. 主 context 寫薄殼 case 檔（一案一檔）
3. 重組 `_index.md`、按 vendor / 主題分組
4. 更新各 vendor 頁的「案例回寫」section
5. 跑 `mdtools fmt --fix` + `mdtools lint` + `mdtools cards`、確認格式跟連結
6. 若 lint 抓到 anti-phishing 規則錯誤（link display vs href）、修正後再跑一次

## 反覆陷阱（採集階段）

1. **編造案例**：LLM 把訓練資料 + 真實公司名混合成不存在的案例。WebFetch 驗證是唯一硬閘門
2. **vendor marketing 當客戶案例**：vendor 自家寫的 customer story 偏 marketing、技術細節淺。優先找客戶自家 engineering blog
3. **過度追求 10 個案例**：當該 vendor 公開資料偏少（如 NATS 比 Kafka 少）、強求 10 個會導致採集品質下降。誠實標明「該 vendor 公開案例稀薄、本庫採集 N 個」
4. **跨網域引用觸發 anti-phishing**：第三方平台寫的 vendor case（Synadia 寫 NATS、CloudAMQP 寫 RabbitMQ）、link display 要明示來源平台
5. **同公司案例重複 fetch**：4+ 篇深度 case 文的公司、agent 之間不協調會重複 fetch、浪費 token

## 跟 stage 1 audit 的銜接

Stage 0 採集完成、薄殼 case 進入 stage 1 audit 時：

- Stage 1 不用重新採集、只讀薄殼判斷類型（skeleton / medium / rich）
- 若薄殼案例的 source URL 內容深度高、可在 stage 1 後升級為 rich case（擴寫策略 / 下一步路由段）
- 若薄殼案例只給方向、保留 skeleton 形態、不擴寫
