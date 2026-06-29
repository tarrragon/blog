---
title: "1.9 Reconciliation 與 Data Repair"
date: 2026-05-13
description: "資料不一致的分類、偵測模式、修復策略、audit trail、跟 backup / PITR 整合"
weight: 9
tags: ["backend", "database", "reconciliation", "data-repair"]
---

Reconciliation 與 data repair 的核心責任是把資料錯誤從模糊異常轉成可驗證、可修復、可稽核的流程。進入特定資料庫或 ORM 前、讀者需要先理解資料修復屬於正式狀態責任的一部分。

本章從不一致分類開始、進入偵測模式（連續 vs scheduled）、處理修復策略（auto vs manual）、最後對接 audit trail 跟 backup recovery。讀完後讀者能設計：對帳機制、修復 runbook、evidence handoff、audit chain。

## Reconciliation

Reconciliation 的責任是比較兩個或多個資料來源、確認正式狀態是否與外部事實一致。付款狀態要和金流 provider 對齊、發票狀態要和開票系統對齊、庫存狀態要和出貨或倉儲系統對齊。

對帳需要明確定義資料來源、時間窗、比對鍵、差異分類與 owner。這些欄位能把「資料看起來不一致」轉成可分派、可修復、可驗證的決策材料。

### 對帳系統的設計欄位

設計對帳作業時、要先把這幾件事談清楚、再寫 query。少談任何一項、對帳結果都會在事故當下被質疑可信度。

**來源 A 與來源 B**：明確指出哪個是內部 source of truth、哪個是外部事實。金流對帳的 A 是訂單表、B 是 provider 結算檔；庫存對帳的 A 是訂單庫存表、B 是倉儲 WMS 報表。兩邊都要有明確 owner、否則差異發生時沒人能解釋為何資料長那樣。

**比對鍵（comparison key）**：A 跟 B 要用什麼欄位對齊。最理想是雙方共用的業務 ID（例如金流交易序號）；次優是 timestamp + 業務外鍵組合；最差是用 fuzzy matching（金額 + 時間範圍）、這時對帳結果天然帶有噪音、要在 output schema 標示信心度。

**時間窗（time window）**：對帳要對哪段時間的資料、什麼時候做。每日對帳通常設定 T-1 整天、跳過今天（避免 [in-flight](/backend/knowledge-cards/in-flight/) 資料）；分鐘級對帳要明確處理 in-flight：是排除最近 N 分鐘、還是允許重複跑直到收斂。在跨時區業務裡、時間窗要對齊雙方 timezone、不然每天差異會穩定出現在 0:00 前後。

**差異分類規則**：mismatch 不是只有「不一致」一種。常見要再切：「A 有 B 沒有」（missing in B）、「B 有 A 沒有」（missing in A）、「兩邊都有但欄位不同」（value mismatch）、「同一個 key 在 A 有多筆」（duplicate）。每類差異的處理路徑跟 owner 都不同、不分類會讓修復決策無法分派。

**Output schema**：對帳產出的不是「對 / 不對」、而是一份結構化報告。最少要有：mismatch 樣本（不是全部）、總筆數與金額影響、覆蓋率（總共比對了多少筆）、未覆蓋資料（哪些 A 或 B 沒涵蓋）、結果時間戳。這份報告會被 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 收進釋出證據鏈、結構不穩定會讓上游 release gate 拒絕採信。

### 對帳跟 anomaly detection 的差異

兩件事都是「找資料異常」、但本質不同、不能互相替代。

對帳是 deterministic：給定兩個來源、結果是確定的差異集合、可以被任何工程師重跑驗證。anomaly detection 是 statistical：用模型或閾值判斷一筆資料是否「看起來不對」、結果帶機率、不同模型跑出來不一樣。

在金流、庫存、付款這類正式狀態場景、對帳是必須、anomaly detection 是補充。anomaly detection 適合抓「對帳沒設計到的維度」（突然某 tenant 訂單量爆增）、但不能用它當 source of truth、因為事故時無法回答「為何這筆被判定為異常」。

兩者輸出格式也不同：對帳輸出 mismatch list、anomaly detection 輸出 confidence score。把兩者混在同一份報告會讓 incident reviewer 無法判斷哪些是必修、哪些是可疑。

## 不一致的三種分類

不是所有「資料不一致」都一樣。按 *成因* 分三類、各有不同處理策略。

### Temporal Inconsistency（時間性不一致）

- 來源：replication lag、async event delivery、[eventual consistency](/backend/knowledge-cards/eventual-consistency/)
- 特徵：兩邊都是「對的」、只是 *時間點* 不同
- 例：cache 跟 DB 看到不同 value（cache 還沒 invalidate）、replica 跟 primary 不同步
- 處理：等待收斂或主動觸發 sync、不必修資料
- 持續時間：通常 < 1 秒到分鐘級

### Structural Inconsistency（結構性不一致）

- 來源：schema migration 期間、dual-write 失敗、partial write
- 特徵：兩邊應該一致但實際不一致、其中一邊是 *錯的*
- 例：訂單寫進主表但 line items 沒寫、外鍵 reference 一個不存在的 row
- 處理：必須修復、不能等
- 持續時間：永久（直到修復）

### Semantic Inconsistency（語意不一致）

- 來源：業務邏輯 bug、應用層 race condition、人工誤操作
- 特徵：資料結構 OK、但 *業務語意* 錯
- 例：訂單付款狀態是 `paid` 但金流端是 `refunded`、帳戶餘額跟交易紀錄 sum 不符
- 處理：複雜、需要業務判斷哪邊是 source of truth
- 持續時間：永久（且容易擴大）

**處理優先序**：Semantic > Structural > Temporal。Semantic 影響業務最深、Temporal 通常自動收斂。

## 偵測模式

不同類型的不一致需要不同偵測模式。

### Continuous Detection（持續偵測）

- 每筆寫入跑 sanity check（trigger、constraint）
- 應用層 invariant check
- 適合：structural inconsistency（讓 DB 自己擋）
- 成本：每筆寫入有 overhead

### Scheduled Detection（定期對帳）

- 每 N 分鐘 / 每天跑對帳 query
- 跟外部 provider 比對
- 適合：semantic inconsistency（業務級對齊）
- 成本：對帳 query 本身耗資源

### Sampling Detection（抽樣偵測）

- 不跑全表、抽樣 10% / 1% 跑 checksum
- 適合：大表（全表對帳成本高）
- 成本：可能漏掉低頻 inconsistency

### Reactive Detection（反應式偵測）

- 用戶 / 客服回報後才查
- 適合：尾長 inconsistency（找不到通用 pattern）
- 成本：用戶體驗已受影響

對應 [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — migration 期間 [shadow read](/backend/knowledge-cards/shadow-read/) 持續對帳、抓 mapping 規則漂移。

## Data Repair

Data repair 的責任是把已確認的資料差異修回正式狀態、並保留修復原因、範圍、證據與回退條件。修復可以是 SQL update、補事件、補發 webhook、重建 projection 或人工客服流程、但每種修復都要有範圍控制。

資料修復要先分成三種：

| 類型         | 說明                          | 常見風險                       |
| ------------ | ----------------------------- | ------------------------------ |
| 欄位修復     | 修正單筆或小批正式欄位        | mapping 規則錯誤會造成二次污染 |
| 派生狀態重建 | 重建 index、cache、read model | 可能掩蓋正式狀態尚未修復       |
| 補償動作     | 補退款、補發票、補通知        | 可能產生重複副作用             |

修復前要先確認問題落在哪一層。正式欄位錯誤要修 source of truth；派生狀態錯誤要重建副本；外部副作用漏做要走補償流程。

欄位修復的判讀重點是 mapping 規則是否正確、因為錯誤規則會把單點差異擴成批次污染。派生狀態重建的判讀重點是 source of truth 是否已經正確、否則重建會複製錯誤。補償動作的判讀重點是副作用是否可逆、因為退款、通知或外部 webhook 可能已經被使用者或第三方看見。

## Repair 原則

不管哪種修復、都遵守三個原則：

### 1. Idempotency（冪等）

- 同樣的修復跑兩次、結果跟跑一次一樣
- 用 `WHERE current_value != target_value` 而不是無條件 update
- 補通知 / webhook 帶 idempotency key、第三方可去重
- 對應 [Idempotency 卡片](/backend/knowledge-cards/idempotency/)

### 2. Auditable（可稽核）

- 每次修復都有 record：誰、什麼時候、改了什麼、為什麼
- 修復前 + 修復後的 snapshot 都要存
- 對應 [Audit Log 卡片](/backend/knowledge-cards/audit-log/)、[1.5 Red Team](/backend/01-database/red-team-data-layer/) 的 audit 段

### 3. Reversible（可逆）

- 萬一修復是錯的、能回退到 before state
- 不可逆操作（DELETE）必須有 dry-run、必須備份
- 對應 [Rollback Window 卡片](/backend/knowledge-cards/rollback-window/)

## 修復前的 dry-run 與 impact assessment

修復前要先回答「這次修復會碰多少筆、影響多少業務、最壞情況是什麼」、才能進入執行。直接跑 update 是 production-grade 流程的反例、即使在 incident 壓力下也不能跳過這步。

**Dry-run 的責任**：把 update 改成 select、用同樣的 WHERE 條件、產出將被修改的資料樣本。Dry-run 結果要包含：影響筆數總計、影響金額或業務值（如果有）、affected tenant / user list 的抽樣、未涵蓋的邊界 case。Dry-run 跟正式修復必須共用 mapping 規則、否則 dry-run 結果無法當審核依據。

**規模分級的執行策略**：影響筆數會決定執行方式。

- **單筆到十筆**：客服等級的修復、一名工程師執行 + 一名同儕審核 + audit log 即可。
- **百筆到千筆**：要在低流量時段執行、分批跑、每批跑完比對 invariant、發現意外停下。
- **萬筆以上**：當成 production deploy 處理、要有 deploy review、staged rollout（先 1% tenant、再 10%、再全量）、跟 oncall 同步。
- **跨表 / 跨 service**：必須先做跨團隊 review、確認下游依賴（cache、search index、外部 webhook）的處理計畫、不能單一團隊獨自決定。

**Impact assessment 的必看欄位**：除了筆數、還要看 *連帶影響*。修復 orders 表會不會觸發 audit trigger 把每筆寫進 audit log 表？會不會觸發 outbox event 把每筆當成新事件對外發布？會不會讓某 tenant 的 metric 一次性異常、誤觸 alert？這些 second-order effect 在 dry-run 階段就要識別、否則修復本身會變成新事故。

**Sandbox / staging 驗證**：不可逆或大規模修復、先在 staging 跑一次、確認 query plan、執行時間、lock 行為。Production 規模沒辦法在 staging 重現的話、至少要在 production 的某個低風險 tenant / region 先試跑、再擴大。

**Approval gate（4-eyes process）**：超出單筆規模或修復金錢、權限、個資的場合、必須 *兩位以上人員* 各自看過 dry-run 結果再簽核。常見實作是：執行者提 PR / ticket 帶 dry-run output、reviewer 簽核後才能執行、執行後產出 audit log 帶兩人簽核紀錄。Reviewer 的責任不是橡皮圖章、是獨立驗證 dry-run 結果跟 incident 描述一致。

## Repair Patterns

實務上常見的 repair pattern：

### Pattern 1：條件式 UPDATE

最簡單也最安全的修復。

```sql
UPDATE orders
SET status = 'paid'
WHERE id = 12345
  AND status = 'pending'
  AND payment_id = 'abc';
```

`AND` 條件確保只在 *當前狀態符合預期* 時才改、避免 race condition。

### Pattern 2：批次修復 + 節流

大量資料修復、必須節流避免影響 production。

```sql
-- 每批 100 筆、間隔 1 秒
UPDATE orders SET status = 'fixed'
WHERE status = 'broken'
  AND id IN (SELECT id FROM orders WHERE status = 'broken' LIMIT 100);
```

對應 [Backfill 卡片](/backend/knowledge-cards/backfill/) — backfill 跟 batch repair 是同類技術。

### Pattern 3：補事件 / 補 webhook

外部副作用漏做時、補發事件。

- 必須帶 idempotency key（third-party 才能去重）
- 紀錄補發原因（incident report 連結）
- 注意：補發前確認 third-party 是否真的沒收到

### Pattern 4：重建 derived state

cache 跟 search index 是 derived state、出錯通常 *砍掉重建*。

- 不是直接修 cache value、是 invalidate 讓下次 read 重算
- 大規模重建用 batch job 跑、避免 thundering herd
- 對應 [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) feature store 重建模式

### Pattern 5：Point-in-time Recovery

當資料 *損毀且無法重建* 時、靠 backup recovery。

- PostgreSQL：WAL + base backup → PITR
- MySQL：binlog + snapshot → PITR
- Aurora：cluster snapshot + continuous backup
- 注意：recovery 期間可能要 *整個 DB restore*、影響範圍大

## Repair Runbook

Repair runbook 的責任是讓資料修復可重複執行、並降低對當下工程師記憶的依賴。最小 runbook 需要包含：

1. 差異查詢與 query link
2. 影響範圍與 tenant / region / time range
3. 修復方式與 dry-run 結果
4. 審核 owner 與執行 owner
5. rollback condition 與後續 validation query

runbook 要和 [validation query](/backend/knowledge-cards/validation-query/) 共用語意。若查詢與修復程式用不同 mapping 規則、修復結果就難以被同一份 evidence 驗證。

## Audit 與權限邊界

Data repair 常常需要高權限、因此必須接到 audit 與資料保護邊界。修復個資、付款、權限或方案資料時、要保留操作者、審核者、查詢範圍、寫入範圍與修復前後樣本。

**Audit log 必要欄位**：

- timestamp（操作時間）
- actor（誰執行）
- reviewer（誰審核、如果是 4-eyes process）
- query（執行了什麼 SQL / API call）
- before / after snapshot（值的變化）
- reason（為什麼做這次修復、incident ID）
- rollback path（如何回退）

這裡要接到 [7.7 Audit Trail 與 Accountability Boundary](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)。資料修復同時是可靠性、資安與合規問題。

### 權限分離與憑證時效

修復權限不該是常駐權限。日常開發 / SRE 帳號只該有 read-only、修復需要時才透過 break-glass 流程申請臨時 write 權限。

常見實作：

- **角色分離**：reviewer 跟 executor 是不同帳號、reviewer 不能執行、executor 不能 self-approve。系統強制檢查兩個帳號不同、避免一人偽造另一身分。
- **時效性憑證**：申請 write 權限時帶 expiry（30 分鐘 / 2 小時）、過期自動回收。不是「給了就一直有」、避免遺留高權限帳號變成攻擊面。
- **範圍限定**：申請時要指定哪張表、哪個 tenant / region。粒度不細的話、一次申請就拿到全 production write、超出實際需求。
- **同步 alert**：高權限被啟用要同步發 alert 到 security channel、給 security team reviewer 看見。事後若 audit log 跟 alert 對不上、表示權限被繞過。

對應 [Identity Access Boundary](/backend/07-security-data-protection/identity-access-boundary/) 跟 [Secrets and Machine Credential Governance](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)。修復權限管理跟 incident-time 緊急存取是同一套機制、不該各做各的。

## 跨服務 / 跨組織的對帳責任

當對帳跨團隊、跨子系統、跨外部 provider 時、責任不清是首要失敗模式。對帳結果在組織邊界 *穿越* 時、要明確標記每段的 owner、否則 mismatch 出現後、所有相關方都會說「不是我們的問題」。

**跨服務對帳的責任切分**：

- **資料 owner**：誰擁有那張表 / 那組欄位、誰負責解釋為何資料長那樣。資料 owner 通常是寫入該表的服務團隊。
- **對帳作業 owner**：誰負責定義 reconciliation query、跑、看結果。可能跟資料 owner 是不同人（例如平台團隊跑對帳、業務團隊擁有資料）。
- **差異處理 owner**：mismatch 出現後、誰負責決定修復策略。通常跟資料 owner 一致、但跨團隊 mismatch 要先約定誰主導。
- **修復執行 owner**：實際下 SQL / call API 的人。可能跟差異處理 owner 不同（後者決策、前者執行）。

四個 owner 在簡單場景可以是同一人、在複雜跨團隊場景必須清楚分派。AGENTS.md §0 的 「明確 owner」原則在這裡指的是 *對每一段流程* 都有人能簽收、不是只指對帳這件事整體有 owner。

**跨組織對帳的特殊問題**：跟外部 provider（金流、物流、SaaS supplier）對帳時、對方不見得會接受你的對帳結果、也不見得會給差異列表。常見處理：

- 自己跑兩份對帳：A vs provider report（每天）、A vs provider API（即時抽樣）、兩份結果不同代表 provider report 本身有問題。
- 約定差異仲裁流程：簽 SLA 時就寫清楚、mismatch 出現後雙方各保留多久的資料、誰先給對方檢視。
- 不能依賴 provider 修：金流 provider 通常只負責對帳、不負責修你的 DB。修復永遠是你方責任。

## 跟 Backup / PITR 整合

備份的 *權限獨立性* 跟 *attack surface* 屬於 [1.5 Red Team 備份段](/backend/01-database/red-team-data-layer/) — 本段聚焦 *recovery* 角度的資料修復責任。兩者互補：1.5 解決「備份本身怎麼防被攻擊」、本段解決「事故後怎麼用備份回復」。

當修復必須跨越「point in time」時、需要 backup 配合。

### Snapshot-based recovery

- 整個 cluster 從 N 小時前的 snapshot 還原
- 影響：所有 *其他* 資料也回到那個時間點
- 適合：catastrophic data corruption

### PITR（Point-in-Time Recovery）

- snapshot + WAL / binlog replay 到指定時間
- 影響：只在指定時間點 stop replay
- 適合：「3 小時前 admin 誤刪一張表」這類精準回放

### Logical backup（mysqldump / pg_dump）

- 整個 schema + data 的 SQL script
- 適合：跨環境遷移、特定表回復、小規模修復

### Continuous archive

- WAL / binlog 持續備份到 S3 / GCS
- 一直可以回放到 *任何時間點*
- 對應 [9.C24 Genesys 99.999%](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 高可用需要快速 PITR

### Recovery 時的對抗壓力

PITR / snapshot recovery 不是純技術問題、會在事故當下面對「為了快、要不要跳檢查」的取捨。對應 [VMware ESXiArgs 2023 ransomware recovery pressure](/backend/07-security-data-protection/red-team/cases/data-exfiltration/vmware-esxiargs-2023-ransomware-recovery-pressure/) — 虛擬化平台勒索後、團隊在 *營運壓力* 跟 *資料可信度* 之間擺盪：snapshot 是否乾淨、回復後資料是否被污染、跳過 integrity check 換 RTO 是否可接受。判讀重點：recovery 流程要事前 *演練* 過、否則事故當下不知道要 verify 什麼、容易在壓力下接受被污染的 backup。對應 [8.5 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)、事故當下的取捨要寫進 decision log。

### RTO/RPO 跟業務可接受中斷的對照表

業務可接受中斷時間是 RTO/RPO 的判讀對照基準。RTO（Recovery Time Objective、多久能恢復）跟 RPO（Recovery Point Objective、最多丟多少資料）是技術指標、要對照業務側的可接受上限才能判斷夠不夠。常見錯誤是把 RTO/RPO 訂在「技術上能做到的最佳值」、忽略業務實際的容忍範圍。

對應 [Change Healthcare 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/) — 「定義核心流程的 RTO / RPO、讓資料修復時間跟業務可接受中斷時間明示對照、不藏在直覺」。事故當下發現「DB 能 2 小時恢復、但業務只能容忍 30 分鐘中斷」、來不及補救。

**對照表設計**：

| 業務流程   | RTO（技術） | 業務可接受中斷 | 落差處理                   |
| ---------- | ----------- | -------------- | -------------------------- |
| 用戶登入   | 30 分鐘     | 5 分鐘         | 加 standby region failover |
| 訂單寫入   | 1 小時      | 30 分鐘        | 加 outbox + replay         |
| 報表查詢   | 4 小時      | 1 天           | RTO 充裕、不需投資         |
| 對帳 batch | 8 小時      | 3 天           | RTO 充裕                   |
| 付款       | 1 小時      | 0（不能停）    | 必須 active-active         |

**關鍵情境延伸**：

- **付款（必須 active-active）**：業務可接受中斷為 0、單一 region failover 都不能用（failover 期間用戶看到失敗）、必須多 region 同時寫入、靠 Aurora DSQL / Spanner / Cosmos DB multi-region write 撐。設計權衡是 *跨 region 寫入延遲* 跟 *對帳一致性的特殊處理*（同一筆款項可能在兩個 region 各被處理一次、要靠 idempotency key 去重）。詳見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)。
- **訂單寫入（outbox + replay）**：30 分鐘容忍區間夠用 outbox pattern — 訂單寫進 DB 同步寫進 outbox table、async worker 把 outbox event 推下游。即使下游中斷、訂單本身已落地、event 可在恢復後 replay。設計權衡是 outbox table 的儲存成本跟 replay 邏輯的冪等性、跟 [03 訊息佇列模組](/backend/03-message-queue/) 的 outbox pattern 整合。
- **用戶登入（standby region failover）**：5 分鐘容忍意味 *自動 failover* 必須在這時間內完成、人類介入做不到、要靠 DNS health check + Route 53 / Cloudflare 自動切流。權衡是 standby region 平時付閒置成本、跟 active-active 比、便宜但 failover 時有 1-3 分鐘延遲跟 cache miss。

落差是 *投資訊號*、不是「忽略它」。RTO > 業務容忍時、要嘛降 RTO（加 HA / DR 投資）、要嘛跟業務協商提高容忍（通常不接受）。

判讀重點：對照表要每年 review。業務模式變了（例如從 B2C 變 B2B 客服 SaaS）、容忍時間會大幅縮短、RTO 必須跟著降。

## 事故角色預定義

DB 事故當下、*資安處置* 跟 *業務連續性處置* 要 *分軌並行*、不是線性執行。這要求事先有 dual-track IC（Incident Command）角色、不是事故當下臨時拉人。

對應 [Change Healthcare 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/) — 「技術處置與業務處置分軌並行的前提是事先有 dual-track IC 角色」。沒事先定義、事故當下會出現「資安 team 在隔離系統、business team 在喊客戶等不及」、兩條軌道互相干擾。

**Dual-track IC 角色定義**（以下為通用 IC 模型、非案例直接揭露；具體角色細分視組織規模調整）：

| 軌道       | 角色                | 責任                                                  |
| ---------- | ------------------- | ----------------------------------------------------- |
| 技術軌道   | Tech IC             | 漏洞修補、系統恢復、技術決策（rollback / restart 等） |
| 業務軌道   | Business IC         | 客戶溝通、降級流程啟動、合規通報、業務 fallback       |
| 協調軌道   | Overall IC          | 兩條軌道協調、跨軌道決策、對外發言                    |
| 資料軌道   | Data IC             | 資料完整性驗證、修復決策、audit chain                 |
| Comms 軌道 | Communications Lead | 內部通報、外部公告、media 應對                        |

**Overall IC 跟一般技術 IC 的差異**：一般 IC 主要在技術軌道內決策（要不要 rollback、要不要重啟）；Overall IC 額外承擔 *跨軌道仲裁* 責任 — 當 Tech IC 想停服務止血、Business IC 想保服務維持收入、兩者衝突時、由 Overall IC 拍板。這個角色需要對技術跟業務都有足夠理解、不能只懂一邊；通常由高階工程主管或 CTO/VP Eng 兼任、不是輪值的 oncall。

**Data IC 的特殊角色**：跟其他軌道相比、Data IC 的決策時間軸最長 — 技術修復可能 1 小時完成、但 *資料是否被污染、要不要 PITR、PITR 到哪個時間點* 可能要 24-72 小時驗證。Data IC 不能被 Tech IC 跟 Business IC 的「快快上線」壓力推動、必須有獨立判斷權。實務上常見的失誤是讓 Tech IC 兼任 Data IC、結果為了 RTO 跳過 integrity check、事後發現資料污染擴大。

**事先準備**：

- **Primary + backup 雙人配置**：每個角色都要有 primary + backup、避免單人不可用（休假、生病、被另一事故占住）讓事故當下卡住。實務上要有 *指定流程* 而非「臨時找誰」、避免事故當下浪費 30 分鐘喬人。
- **責任寫進 runbook**：runbook 要列出每個角色該做什麼決策、不該做什麼決策（避免越權）。事故當下查職位、會在最壓力大的時候做組織決策、出錯機會高。
- **定期 tabletop 演練**：演練的重點不是「技術修復對不對」、是「角色交接是否流暢」。Overall IC 跟 Tech IC 之間的權限邊界、Data IC 何時介入、Comms Lead 何時對外發言、都要在演練中試出來。
- **跨時區 follow-the-sun 輪值**：B2B SaaS 跟全球業務、事故不分時區、要有 24/7 覆蓋。單一時區團隊在事故發生在凌晨時、人力不足或反應慢、會放大事故代價。

判讀重點：DB 事故不只是技術事件、會成為 *跨多軌道* 的事件。角色預定義是組織能力、不是技術能力、但缺它會放大技術事故的代價。

對應 [8.5 Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 跟 [7.13 Security Routing](/backend/07-security-data-protection/security-routing-from-case-to-service/) — 角色預定義是這些跨模組工作的前置。

## Evidence Handoff

資料修復的 evidence handoff 要能支援 release gate 與 incident review。

| 欄位         | 內容                                             |
| ------------ | ------------------------------------------------ |
| Source       | reconciliation query、provider report、audit log |
| Time range   | 差異發生窗口與修復窗口                           |
| Query link   | mismatch sample、修復前後驗證                    |
| Owner        | data owner、service owner、reviewer              |
| Data quality | 抽樣覆蓋率、延遲、未覆蓋資料                     |
| Known gap    | 尚未確認的 provider callback、低流量 tenant      |

這份 handoff 要進入 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## 判讀訊號

| 訊號                               | 判讀重點                             | 對應動作                                        |
| ---------------------------------- | ------------------------------------ | ----------------------------------------------- |
| 對帳差異率持續上升                 | 上游邏輯有 bug、或時間窗對齊問題     | 修上游 + 確認對帳時間窗                         |
| 同筆資料對帳 run-to-run 結果不同   | 對帳 query 沒處理 in-flight 資料邊界 | 排除最近 N 分鐘、或允許收斂多跑幾次             |
| 修復後不一致再次出現               | 沒修根因、只修了 symptom             | 找根因、增加 invariant check                    |
| 修復影響超出預期範圍               | mapping 規則錯誤、二次污染           | 立即停止修復、回退                              |
| 修復沒 dry-run 直接執行            | 流程違規、事後無法佐證影響範圍       | 事後 audit、把 dry-run 列入 gate                |
| Recovery 後 derived state 仍錯     | 重建 derived 時 source 還沒修        | 先修 source、再重建 derived                     |
| Audit log 缺欄位                   | 事故時無法追究、難 rollback          | 補 audit schema、加 reviewer 欄位               |
| 高權限帳號在非 incident 時段啟用   | 可能誤用或攻擊面、break-glass 沒回收 | 立刻檢查 audit log、回收憑證                    |
| 跨服務 mismatch、各方都推卸        | 對帳 owner 沒分派、責任空白          | 補資料 owner / 對帳 owner / 執行 owner          |
| anomaly alert 跟對帳 mismatch 混報 | 兩種訊號性質不同、reviewer 無法判讀  | 拆 dashboard、deterministic 跟 statistical 分開 |

## 常見誤區

把對帳當成「定期 batch job」、不關心 *當下不一致*。實時對帳跟 batch 對帳是 *不同工具*、不能互相替代。

把資料修復當成「一個工程師動手改」、沒 audit、沒 review、沒 rollback。資料修復本質是 production 操作、跟 deploy 同等嚴格。

把 PITR 當成 *常規修復工具*。PITR 影響大、適合 catastrophic event、不適合單筆資料修復。

把 derived state 不一致跟 canonical state 不一致 *混在一起* 處理。derived 是 *再生* 的、canonical 是 *永久* 的、處理流程完全不同。

把對帳結果跟 anomaly detection 結果放同一份報告。前者是 deterministic、後者是 statistical、混報會讓 incident reviewer 無法判斷必修跟可疑。對帳 mismatch 要有獨立追蹤面板、anomaly 走另一條路徑。

跳過 dry-run、直接 update。即使單筆修復、也要先 select 看到當前 row、確認 WHERE 條件命中預期。incident 壓力下尤其容易跳、結果反而把單點問題擴成批次污染。

把修復權限當常駐權限發放。長期 write 權限放在工程師帳號上、會在事故無關時段被誤用、且事後無法區分「正常工作」跟「非法修復」。修復權限要時效化、申請即用即收。

## 案例對照

| 案例                                                                                                  | reconciliation 重點                   |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------- |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)             | migration 期間用 shadow read 持續對帳 |
| [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)         | 體育博彩 ledger、結算後對帳           |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 跨市場銀行、每市場獨立對帳            |

## 實體服務討論承接點

實體資料庫文章要承接本篇的 reconciliation 與 data repair 責任。PostgreSQL、MySQL、MSSQL 或其他資料庫的差異、應放在它們如何產生 validation query、保留 audit trail、支援 point-in-time recovery、處理 replica lag 與控制修復權限。

若服務需要高頻對帳、後續文章要比較查詢成本、索引策略與 replica 讀取延遲。若服務需要高風險資料修復、後續文章要比較 transaction log、backup/restore、row-level audit 與權限分離。若服務需要跨系統補償、後續文章要把資料庫能力接到 queue replay 與 incident decision log。

## 跨模組路由

1. 與 1.3 的交接：transaction boundary 決定哪些不一致可避免 — [Transaction Boundary](/backend/01-database/transaction-boundary/)
2. 與 1.5 的交接：audit 跟 access control — [Red Team Data Layer](/backend/01-database/red-team-data-layer/)
3. 與 1.7 的交接：migration 後驗證 — [Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)
4. 與 1.8 的交接：canonical vs derived 是修復的前置 — [State Ownership](/backend/01-database/state-ownership-query-boundary/)
5. 與 3.8 的交接：消息重放與補事件 — [Queue Consumer Retry / Replay](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)
6. 與 4.20 的交接：evidence handoff — [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
7. 與 7.7 的交接：audit trail — [Audit Trail and Accountability Boundary](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
8. 與 8.22 的交接：incident evidence write-back — [Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)

## 下一步路由

要處理 migration 造成的資料差異、接著讀 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)。要處理事件漏發造成的副作用修復、接著讀 [3.8 Queue Consumer Retry 與 Replay Handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。要設計跨服務 reconciliation 跟 saga compensation、接著讀 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 的 Saga 段。
