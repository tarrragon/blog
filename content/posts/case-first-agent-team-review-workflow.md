---
title: "Case-First + Agent Team Review：教學內容的三階段生產流程"
date: 2026-05-13
description: "LLM 寫教學文章常見盲點是內容停在「教科書級」結構、漏掉真實事故才會浮現的失敗模式跟設計取捨。本文整理一套三階段流程：完整閱讀案例庫抽 findings → 基於 findings 建立內容 → Agent team 平行多輪審查、用 01 資料庫模組 12 章 / 47 review issue 的實作驗證效益。"
tags: ["methodology", "writing-workflow", "agent-team", "case-driven", "claude-code"]
---

## 這篇要說什麼

寫教學文章時、純靠 LLM 自生內容會踩到兩個系統性盲點：

1. **Scope 盲點**：內容停在「教科書級」結構、漏掉真實事故才會浮現的失敗模式跟設計取捨。
2. **準確性盲點**：把通用 best practice 包裝成「[case] 揭露」、把案例沒講的細節寫成案例事實。

本文整理在 backend/01 資料庫模組撰寫過程中浮現的三階段流程：

1. **完整閱讀案例庫、抽 findings** — 用案例驅動「該寫什麼」、不只是 LLM 自生
2. **基於 findings 建立內容** — findings 分布到章節、避免硬塞模板
3. **Agent team 平行多輪審查** — 用 3 個專責 reviewer 補 LLM 自盲點

實作數據：12 個章節、4055 行、16 個案例 audit、42 個 findings、47 個 review issue 修正後品質升至無 broken link / 無矛盾 / 案例引用無編造。

## 問題：LLM 自生內容的兩個盲點

純靠 LLM 寫教學章節、容易產出兩種品質風險：

**Scope 盲點**：LLM 從訓練資料抽出的內容偏 *普遍性*、是「教科書 + 部落格 + 文件」的綜合。但真實工程議題的判讀條件常常來自 *特定事故揭露*、不是普遍知識。例：

- 「DynamoDB GSI 在 backfill 完成前查不到完整資料」這種具體陷阱
- 「Super Bowl +50% no sweat 的工程意義是 headroom 提前預留、不是 vendor 神奇」這種反直覺判讀
- 「99.99% → 99.999% 不是 10x 成本而是指數成本」這種規模對照

純技術知識推導不出來、要看真實案例才會浮現。

**準確性盲點**：LLM 寫到「對應 [case]」時、容易把通用 best practice 包裝成案例事實、或把案例沒提到的細節擴寫成「案例揭露」。例（從本文討論的實作中抓出的真實 issue）：

- Snowflake 案例描述「異常查詢偵測維度（query 體積 / IP / 跨 schema scan）」、LLM 自生內容寫成「query 體積從 1MB / 天跳到 10GB / 天、來源 IP 從 office network 變 unknown VPS」— 具體數字是 LLM 加上去的、案例沒寫
- Tixcraft 案例策略段建議「composite key」、LLM 自生內容寫成「Tixcraft 用 user_id 分散、不是 event_id」— 案例沒揭露 Tixcraft 實際 partition key 設計

這兩類盲點都不容易在 self-review 時抓到、因為 LLM 看不出自己內容是否真的對應案例。

## 階段 1：完整閱讀案例庫、抽 findings

### 為什麼要完整閱讀、不能只看 title + description

只看 title + description 能做 *承接*（建立 link）、但無法做 *scope 擴展*（揭露 LLM 不會自生的議題）。case 的 findings 通常埋在 body 的「判讀」段、不在 description 裡。

實作中的對照：第一輪 audit 6 個 case、每 case 平均揭露 2.3 個 finding；其中約 7 成是 description 跟 title 看不到、要讀完整 body 才能抽出。例如 DraftKings 案例的「讀寫雙峰錯位」（比賽中讀爆量、payout 時寫爆量）— description 只說「financial ledger」、要讀「核心負載形狀」段才看到雙峰結構。

### 邊際遞減的判斷

不是所有 case 都要讀。實作中觀察到的遞減曲線：

| 輪次   | 讀案例數 | 揭露 findings | 平均 / case | 純新議題 |
| ------ | -------- | ------------- | ----------- | -------- |
| 第一輪 | 6        | 14            | 2.3         | ~95%     |
| 第二輪 | 5        | 15            | 3.0         | ~85%     |
| 第三輪 | 5        | 13            | 2.6         | ~60%     |

第三輪開始 *純新議題* 比例下降、重複 frame 出現（vendor dogfood 在 3 個 case 都揭露、benchmark 對照基準在 3 個 case 都揭露）。這是停止 audit 的訊號。

判讀條件：

- **繼續 audit**：每 case 至少 1.5 個純新議題、且重複 frame 不超過 30%
- **停止 audit**：純新議題 < 1 個 / case、重複 frame > 50%、累積 finding 數已涵蓋目標章節主要議題

實作中 11/94 cases（~12%）時邊際遞減訊號明顯、16/94 cases（~17%）時停止 audit、抽出 ~42 個 unique findings、足以支撐 6 個章節的 scope 擴展。

### Findings 抽取方法

讀 case 時、把每個段落看成可能的 finding 來源、問三個問題：

1. **這段揭露什麼判讀條件**？（是不是純技術推導不易浮現的議題）
2. **這段揭露什麼數字 / 設計細節**？（規模、percentile、partition key 數量、replication lag 量級）
3. **這段揭露什麼失敗模式**？（事故當下會踩什麼坑、有什麼反直覺結論）

寫進 findings 列表時、要附上 *case 來源* 跟 *該對應到哪個章節*。例：

> Finding: 線性擴展是 OLTP 設計最高目標、coordinator 是傳統 OLTP 的擴展瓶頸
> 來源: 9.C10 Spanner 案例「2 nodes → 45K reads/sec, 4 nodes → 90K reads/sec」段
> 章節: 1.11 全球分散式 OLTP

不寫來源跟章節定位、findings 會變成抽象列表、寫稿時用不上。

### Case 類型的承接策略

不同 case 類型適合不同承接深度、誤判類型會引發 *over-extrapolation* 問題。實作中觀察到的兩類 case：

**Rich case**（典型：09/07 案例庫中含具體數字、設計細節、遷移路徑的長篇 case）：

- 內容深度：50-200 行、含具體數字、業務情境、引用源
- 承接方式：可直接引用為事實、case 揭露的具體數字（RPS、延遲、TPS、stale window）可放進章節
- 例：9.C5 Amazon Ads「90M RPS + 5M writes/sec + 99.999%」可直接寫進 1.10 KV 章節
- 例：9.C6 Tinder「4700 萬 MAU 配對引擎、cache 是主要服務面」可直接做為 2.1 high-concurrency 的判讀依據

**Skeleton case**（典型：模組內部 N.Cx 案例庫中只有 frame、無具體數字的短篇 case）：

- 內容深度：10-30 行、只給方向、無具體數字 / taxonomy
- 承接方式：作為「視角 / 方向」、可引用為「case 揭露 X 議題」、但不引用為「case 揭露 X 具體場景數量」
- 例：2.C1 Meta Cache Consistency 只有「promotion、shard move、故障恢復」三個方向、不引用為「具體 inconsistency window 數字」
- 例：3.C9 反例只給「依賴特定 offset / 重試節奏 / idempotency」三個方向、不引用為「4 個具體誤配場景」

**判讀條件**：

- 看 case 行數 + 內容密度判斷類型
- skeleton case 的 finding 要寫成「對應 [case] — 揭露 X 方向、以下展開基於通用工程知識補充」
- rich case 的 finding 可寫「對應 [case] — XXX 具體數字 / 設計」

實作中（01/02/03 三個模組驗證）、skeleton case 寫成 rich case 對應是 case fidelity reviewer 抓出 over-extrapolation 的主要來源（02 / 03 各 3-4 個 critical 編造都來自此陷阱）。誤判類型 → 編造 case 沒寫的細節 → reviewer 抓出 → 修正成本高。stage 1 抽 findings 時就要 *標明 case 類型*、stage 2 寫作時依類型決定承接深度。

## 階段 2：基於 findings 建立內容

### Findings 分布到章節

抽完 findings 後、按章節主題分類、看哪個章節缺口最大、哪個 finding 該寫去哪。實作中的分布：

- 1.1 高併發：7 findings
- 1.5 紅隊：8 findings
- 1.9 reconciliation：4 findings
- 1.10 KV：6 findings
- 1.11 全球分散式：10 findings（最大缺口）
- 1.6+1.12 migration：5 findings

涉及多軸取捨的章節（1.11 一致性 / 可用性 / 成本 / 延遲）暴露最多缺口、純流程章節（1.9）暴露最少。這是 *章節結構性質* 的差異、不是寫得好壞。

### Stage 2 寫作前先定 SSoT 對應

當同一 finding 或 frame 在 *多個章節* 都有用、要在開始寫之前 *先定 SSoT 對應*、否則 case-driven 擴章必然出現 frame 重複展開。

實作中觀察到的反例（02 / 03 模組都踩過）：

- **02 cache**：「cache 角色變化」frame 在 2.1 主寫但實際屬模組層級、應在 `_index`；Tubi 案例在 2.1 / 2.2 / 2.8 三章各自展開 mini-finding；Snap KeyDB 在 2.1 / 2.7 / 2.8 三章重複
- **03 message-queue**（最嚴重）：「三層語意（delivery / processing / recovery）」在 3.4 / 3.6 / 3.8 三章各自定義；「Slack Kafka+Redis 拓樸」在 3.4 跟 3.8 兩章逐字重複；「規模對照（小 / 中 / 大型）」在 3.4 / 3.6 / 3.8 三章拆用、結論散落讀者拼不出總圖

**SSoT 對應的判讀順序**：

1. 列出所有 cross-chapter findings（出現在多章的 frame）
2. 每個 frame 指定 *一個* 主寫章節（SSoT）
3. 其他章節 *只 link*、不展開
4. SSoT 章節要有完整論述、被引用章節保留簡述跟 cross-link

**SSoT 選擇標準**：

- frame 涉及 *跨模組層級概念* → 寫進 `_index.md`
- frame 涉及 *單章核心責任* → SSoT 為該章
- frame 涉及 *跨章交接點* → 選最相關章節為 SSoT、其他章節 link

漏掉這步、reviewer 跨章一致性會抓出 5-10 個 frame 重複 issue、修正成本高（要把已展開內容收斂回 SSoT）。Stage 2 前花 30 分鐘做 SSoT 對應、能省下 Stage 3 數小時的重構工。

### 避免硬塞模板

最大的反模式是把多個 findings 硬塞成同一個 table、每 row 一短語、失去情境敘事。

實作中的反例：1.9 章新增「Dual-track IC 5 個角色表」、本來想用表格整齊呈現、但 reviewer 抓出「5 角色平鋪、責任只一行、未展開每角色在真實事故的決策樣態」。修正後拆成：

- 主表格（5 個角色快速對照）
- Overall IC 跟 Tech IC 的差異獨立段（300 字）
- Data IC 的特殊角色獨立段（300 字、含「為什麼不能讓 Tech IC 兼任」的失誤對照）
- 事先準備 4 項各自延伸（不只列項目、解釋失效樣態）

這樣 *每個項目都是情境* 而非 *硬塞的欄位*、符合 AGENTS.md §1.4「表格不是終點」原則。

### 情境敘事的判讀條件

每段內容寫完後、問三個檢查問題：

1. **首句是不是核心原則**？（不是「某 case 揭露 X」、是「X 是什麼、承擔什麼責任」）
2. **是不是用否定句主導**？（「不是 X」「不只 X」開段要回到正向陳述）
3. **這個 finding 在不同情境下是否會變義**？（一個 finding 套到多個情境、要分情境寫、不是套同模板）

### 案例引用的準確性

寫「對應 [case] — XXX」時、要回 case 原文驗證 XXX 是否真的出現。實作中常見的失分：

- 把 case 沒提到的數字補進去（「30-90 天 baseline」、「1MB→10GB / 天」）
- 把通用 best practice 寫成案例事實（「Snowflake 之後改為預設強制 MFA」— case 只說「資料平台應預設強制 MFA」、不是描述後續行動）
- 公開事實但 case 沒寫（「MOVEit 跨上百家客戶」、「LastPass master password 弱可被離線爆破」）

寫稿當下不容易抓、要靠階段 3 的 case fidelity reviewer 對照。

## 階段 3：Agent team 平行多輪審查

### 為什麼要 agent team、不能交給單一 reviewer

單一 reviewer 有兩個限制：

1. **維度盲點**：一個 reviewer 同時看寫作規範、案例準確性、跨章一致性、容易 *維度互相干擾*、最後每個維度都看不深
2. **Context 污染**：reviewer 讀完整 commit + 所有案例 + 所有章節後、自身 context 就被佔滿、給的建議會 *對應主 context 也跟著沉重*

解法是用 3 個專責 reviewer、平行 background 跑、各自獨立報告、主 context 只看精煉摘要。

### 三個維度 reviewer 分工

實作中使用的三個 reviewer：

#### Reviewer A：寫作規範審查（AGENTS.md 八原則）

- 對照核心原則先行、正向陳述優先、商業邏輯先於 case、表格不是終點、情境優先於模板、可操作判準等八原則
- 找首句用否定句切入、表格 / bullet 平鋪沒延伸、表格項硬塞模板等
- 實作中抓出 25 個 issue

#### Reviewer B：案例引用準確性

- 對照原始 case 內容、驗證「對應 [case] — XXX」斷言是否真的來自案例
- 識別編造數字、過度推論、把通用 best practice 寫成案例事實
- 實作中抓出 9 個 issue、包含 3 個 critical 編造

#### Reviewer C：跨章一致性

- 跨多章找重複 frame、矛盾說法、失效 cross-link、章節邊界錯位
- 識別「該在 A 章卻寫在 B 章」、「frame 重複展開沒整併」
- 實作中抓出 13 個 issue

### 平行 background 跑、不佔主 context

關鍵設計是 3 個 reviewer 並行、各自 background、各自寫 output file、不污染主 context：

- 主 context 只看到「啟動 reviewer」跟「reviewer 完成的彙整報告」
- Raw output 跟 reviewer 的 deep dive 留在 output file、需要時 SendMessage 繼續對話
- 3 個 reviewer 完成時間 ~5-15 分鐘、可以同時跑、不必等

實作中 3 個 reviewer 平均 2-3 分鐘完成、主 context 增量 ~3K tokens（彙整 + 47 issue 清單）、相比把所有案例跟章節塞進主 context 做 review 節省 ~80% context。

### Reviewer issue 數量的 baseline

3 個模組（01 / 02 / 03）驗證後、每模組 reviewer 抓到的 issue 數量穩定、可作為流程預期：

| Reviewer 維度          | 01 modules   | 02 modules    | 03 modules    | baseline        |
| ---------------------- | ------------ | ------------- | ------------- | --------------- |
| Standards reviewer     | 25           | 20            | 20            | 20-25 issue     |
| Case fidelity reviewer | 9 (88% 準確) | 20 (78% 準確) | 15 (70% 準確) | 10-20 issue     |
| Consistency reviewer   | 13           | 15            | 15            | 13-15 issue     |
| **總計**               | **47**       | **55**        | **50**        | **45-55 issue** |

**模式觀察**：

- **每模組 ~50 issue 是穩定值**、不會因主題不同大幅波動
- **Case fidelity 準確率隨 skeleton case 比例下降**：01 用 09 rich cases 為主（88%）、03 用 skeleton case 比例高（70%）。下次規劃時要評估 case 庫的 rich vs skeleton 比例、預期準確率
- **Consistency reviewer 抓到的 frame 重複跟章節數成正比**：02 / 03 都有 ~13-15 個一致性 issue、跟章節 8-11 個對應、平均每章 ~1.5 個跨章邊界 issue

**Stage 3 修正成本估算**：

- Critical（編造、矛盾）：~每個 5-10 分鐘修正、佔 3-5 個
- High（重複 frame、章節邊界）：~每個 10-20 分鐘修正、佔 5-8 個
- Medium / Low（規範細節、cross-link 補）：~每個 2-5 分鐘修正、佔 35-45 個
- **總計 ~1.5-2.5 小時 / 模組**

### 為何要多輪 review、不是一次到位

第一輪 review 的目的是 *找問題*、不是 *修問題*。問題清單列出後、要做兩件事：

1. **分類優先序**：critical / high / medium / low、按嚴重度跟修改成本排序
2. **修正循環**：批次修正、避免一個一個改散開、修完再跑驗證

修正後可選擇性做第二輪 review、檢查：

- 修正本身有沒有引入新問題
- 之前 reviewer 漏掉的維度（例：教學性、讀者路徑、實作可行性）
- 跨 commit 一致性

實作中第一輪足夠處理 47 個 issue、第二輪沒進行、留到未來模組（02 cache、03 message queue）累積經驗後再評估是否必要。

## 修正循環的執行原則

47 個 issue 分布到 6 個章節、修正時 *按檔案批次*、不是按 issue 編號順序。每個檔案一次修完所有相關 issue、減少切換成本：

- 1.5 紅隊章（12 issue）：含 2 個 critical 編造、優先處理
- 1.10 KV（7 issue）：含 1 個 critical 編造
- 1.11 全球分散式（5 issue）
- 1.12 大規模遷移（10 issue）：表格密度最高、最多延伸
- 1.1 高併發（4 issue）
- 1.9 reconciliation（5 issue）

每個檔案修完後跑一次 `mdtools fmt --fix` + `mdtools cards` + `mdtools lint`、確認該檔內部一致、再進下一檔。最後跑一次跨檔驗證、確認 cross-link 全部對齊。

## 適用情境跟限制

### 適用情境

- **長期累積的教學模組**：6+ 章、跨章引用密集、規範遵循重要
- **有現成 case 庫**：07/09 累積的 100+ 案例是這套流程的前提、沒案例庫做不到 case-first
- **品質高於速度**：完整三階段約 3-4 小時 / 模組（stage 2 寫作 ~1.5-2hr + reviewer ~15 分鐘 + stage 3 修正 ~1.5-2hr）、適合長期累積的內容、不適合 one-off 文章
- **主 context 容量敏感**：reviewer 平行 background 是節省 context 的關鍵設計

### 不適用情境

- **新主題沒案例庫**：要先建案例庫、不能直接套這流程
- **單篇短文**：流程的固定成本（讀案例 + 跑 reviewer）對短文 ROI 低
- **快速迭代原型**：流程偏向 *寫一次寫好*、不是 *快速修改*

### 限制

- **Reviewer 維度有限**：當前 3 個 reviewer 沒覆蓋「教學性」「讀者路徑」「實作可行性」、若主題需要這些維度、要加 reviewer
- **修正可能引入新 issue**：第一輪 review 後修正、修正本身可能違反規範、若大量修正最好做第二輪
- **Case 庫品質決定 findings 品質**：case 寫得淺、findings 也淺；case fidelity reviewer 也只能驗證「跟 case 一致」、不能驗證「case 本身對不對」
- **依賴 LLM agent 平台能力**：流程預設可平行跑 background agent、不是所有 LLM 平台都支援

## 3 個模組驗證後的反覆陷阱

01 / 02 / 03 三個模組執行下來、以下三個陷阱在 *每個模組都重複出現*、屬於 LLM case-driven 寫作的系統性失分點。本流程下次套用前要 *主動防範*、不能依賴 stage 3 reviewer 補救（雖然 reviewer 都會抓到、但修正成本高）。

### 陷阱 1：Skeleton case 擴寫成 case 事實

當 case 內容簡短（10-30 行、只有 frame 沒有具體數字 / taxonomy）、LLM 寫作時容易把通用知識（具體數字、攻擊向量列表、設計細節）寫成「對應 [case] —」斷言。實際 case 沒寫的。

**實證**：

- 01 紅隊：Snowflake「30-90 天 baseline」編造、Tixcraft「partition key 用 user_id」編造
- 02 cache：Tubi 三層 cache 具體 latency（L1 < 1ms、L2 < 10ms、L3 10-100ms）編造、Redis「100K-200K ops/sec」無來源、KeyDB「5-10x throughput」其實是 case 判讀段非引用源
- 03 messaging：PayPay「broker 寫入 3K msg/sec」實際 case 寫的是「DynamoDB 寫入 3K msg/sec」（PayPay 用 DynamoDB 不是傳統 broker）、3.C9 case 三個方向被擴寫成「4 個誤配場景」、3.C10 case 「大型服務 DLQ 是診斷入口」完全編造

**防範**：

- Stage 1 抽 findings 時 *標明 case 類型*（rich vs skeleton）
- Stage 2 寫 skeleton case finding 時、用「對應 [case] — 揭露 X 方向、以下展開基於通用工程知識補充」這種 *fact vs derive* 標記
- 不要為了「整齊的 4 個攻擊面」「3 個攻擊向量」「5 個誤配場景」這種數字感、把 case 沒寫的 taxonomy 寫成 case 揭露

### 陷阱 2：Frame 重複展開（SSoT 不清）

同一概念在多章 case-driven 擴章時各自展開、形成 frame 重複。讀者跨章讀會踩到重述、結論散落拼不出總圖。

**實證**：

- 01：容量三口徑 frame 在 1.1 跟 1.12 重複展開、storage / compute 分離 frame 在 1.1 跟 1.11 重複
- 02：cache 角色變化 frame 在 2.1 主寫但屬模組層級、應在 _index；Tubi 案例在 2.1 / 2.2 / 2.8 三章 mini-展開
- 03（最嚴重）：三層語意（delivery / processing / recovery）在 3.4 / 3.6 / 3.8 三章各自定義；Slack Kafka+Redis 拓樸在 3.4 跟 3.8 兩章逐字重複；規模對照在 3.4 / 3.6 / 3.8 三章拆用

**防範**：

- Stage 2 寫作前花 30 分鐘做 SSoT 對應（見前面「Stage 2 寫作前先定 SSoT 對應」段）
- 列出 cross-chapter frames、指定唯一主寫章節、其他章節只 link
- 寫每章前問「這個 frame 主寫在哪？我現在寫的是主寫還是 link？」

### 陷阱 3：負向陳述 + 模板化（規範系統性失分）

「不是 X、是 Y」推進論證、L1/L2/L3 三層平鋪、三選一表格、四步驟流程。這兩個原則違反在每模組都重複出現、是 LLM 寫作的反覆模式、stage 3 standards reviewer 每模組會抓 10-20 處。

**實證**：

- 01 規範 violation：表格不延伸（7 處）、負向陳述（5 處）、首句結構（4 處）
- 02 規範 violation：原則 8 模板化（6 處）、原則 2 負向陳述（6 處）、原則 4 表格不延伸（4 處）
- 03 規範 violation：原則 2 負向陳述（12 處最嚴重）、原則 1 首句結構（5 處）、原則 6 用語節制（2 處）

**防範**：

- Stage 2 寫完後 *寫稿端就跑掃描*、不等 reviewer：
  - `rg -n "不行|不可以|不要|無法|不能" <module-path>` 找負向骨架（技術約束敘述例外）
  - `grep` 找「不是 X、是 Y」開段結構
  - 自查表格：每個 bullet 是否有後文延伸？
  - 自查首句：是否「核心原則先行」而非「對應 [case] 揭露」
- 模板化（L1/L2/L3、三選一）出現時、先問「這三項是真的對等？還是業務情境不同？」— 不同情境的話拆敘事段、不用表格

### 衍生 insight：reviewer 維度沒覆蓋的部分

3 個模組跑下來、發現現有 3 reviewer 維度（規範 / 案例準確性 / 跨章一致性）有未覆蓋的問題：

- **教學性 / 讀者路徑**：章節之間的閱讀順序是否合理？讀者讀完 A 章能不能銜接 B 章？目前沒 reviewer 檢查
- **判讀條件可操作性**：寫了判讀訊號、但實際工程師能不能用這些訊號做決策？沒 reviewer 驗證
- **實作可行性**：建議的設計是否真的能落地？跨團隊協調是否現實？需要懂業務的 reviewer

未來 4 / 5 / 6 / 7 / 8 模組執行時、可以考慮加第 4 個 reviewer 維度（教學性 + 實作可行性）。

## 跟其他寫作流程的差異

跟「LLM 自生 + 人工 review」比、本流程的差異：

| 維度         | LLM 自生 + 人工 review     | Case-first + Agent team                          |
| ------------ | -------------------------- | ------------------------------------------------ |
| Scope 來源   | 訓練資料 + 提示詞          | 真實案例 findings                                |
| 準確性檢查   | 人工讀完對比               | Case fidelity reviewer 自動對照                  |
| 規範遵循     | 人工 checklist             | Standards reviewer 自動掃描                      |
| 跨章一致性   | 人工跨檔 grep              | Consistency reviewer 自動檢查                    |
| Context 成本 | 低（人工不佔 LLM context） | 中（reviewer 各自佔自己 context、主 context 輕） |
| 時間成本     | 高（人工逐段讀）           | 中（reviewer 平行）                              |
| 真實事故揭露 | 受限於 reviewer 經驗       | 受限於案例庫覆蓋                                 |

跟「LLM 自生 + 自我 review」比：

- 自我 review 抓不到自生內容的盲點（self-blindness）
- Agent team 是 *不同 instance*、不共享 context、能扮演獨立 reviewer

## 下一步

本流程在 backend/01 模組（12 章 / 4055 行）驗證有效後、預計套用到：

- backend/02 cache：用 09 cache cases（Tinder Valkey、Tubi feature store、Snap KeyDB 等）+ 07 cache-relevant 紅隊
- backend/03 message queue：用 09 messaging cases（PayPay 3 億 msg/day、Spotify Kafka→PubSub）
- 其他模組依此類推

流程本身也會在每個模組後 retrospective、看 reviewer 維度是否該調整、findings 抽取方法是否該強化。目前已知改進方向：

- 加 reviewer：教學性審查（讀者路徑是否清楚、判讀順序是否合理）
- 強化 findings 抽取：標註 finding 的 *泛化程度*、避免把 case-specific 細節推為通用結論
- 加修正後自動 lint：修完不只跑 mdtools、加跑「找首句否定句」「找表格沒延伸」的自動掃描

跟其他寫作協議的整合：本流程跟 `compositional-writing` skill 互補（後者管 *單篇* 寫作的原子化跟意圖、本流程管 *跨章模組* 的 scope 跟一致性）、跟 `requirement-protocol` skill 互補（後者管 *對話協議*、本流程管 *內容生產*）。
