---
title: "Case-First + Agent Team Review：教學內容的五階段生產流程"
date: 2026-05-13
description: "LLM 寫教學文章常見盲點是內容停在「教科書級」結構、漏掉真實事故才會浮現的失敗模式跟設計取捨。本文整理一套完整流程：完整閱讀案例庫抽 findings → 基於 findings 建立內容 → Agent team 平行多輪審查 → 修正循環 → Polish pass 處理系統性殘留。用 backend/01 至 backend/05 五個模組 / 263 review issue 的實作驗證效益。"
tags: ["methodology", "writing-workflow", "agent-team", "case-driven", "claude-code"]
---

## 這篇要說什麼

寫教學文章時、純靠 LLM 自生內容會踩到兩個系統性盲點：

1. **Scope 盲點**：內容停在「教科書級」結構、漏掉真實事故才會浮現的失敗模式跟設計取捨。
2. **準確性盲點**：把通用 best practice 包裝成「[case] 揭露」、把案例沒講的細節寫成案例事實。

本文整理在 backend/01 至 backend/05 五個模組撰寫過程中浮現的五階段流程：

1. **完整閱讀案例庫、抽 findings** — 用案例驅動「該寫什麼」、不只是 LLM 自生
2. **基於 findings 建立內容** — findings 分布到章節、避免硬塞模板
3. **Agent team 平行多輪審查** — 用 3 個專責 reviewer 補 LLM 自盲點
4. **修正循環** — 按檔案批次修 high + 重要 medium、reviewer 抓出問題各章節對應修
5. **Polish pass** — 跨檔系統性 pattern 集中處理（負向骨架掃描、編號漂移、用語不一、cross-link 補漏）

實作數據：5 個模組（backend/01-05）、~30 章 / 263 個 review issue、case fidelity 落在 70-93% 區間、修正後品質升至 0 critical 編造、cross-link 全綠、規範違反 polish pass 後降到單位數低 issue。

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

**Rich case 引用的反向風險（04/05 模組新發現）**：rich case 雖然可以引用具體數字、但 case 內常含「觀察層」（具體 fact）跟「判讀層」（作者推論）兩段、引用時要分開處理。05 模組驗證時 case fidelity reviewer 抓出 4 個 high issue 都來自把「判讀層作者推論」寫成「case 揭露的 fact」：

- 9.C12 Riot Games：5.2 寫「揭露 35ms latency 反推 region 部署」、實際 case 的「35ms」是觀察層、「反推 region 部署」是作者判讀層
- 9.C34 GCP 130K：5.2 寫「揭露 Spanner 替 etcd 才是 K8s 規模極限的關鍵」、實際 case 用更保守的「control plane 極限取決於 storage backend、GCP 用 Spanner 替換 etcd」分兩個點寫
- 9.C12 Riot：5.2 引用「single-tenant per game 的多 cluster 策略」、漏掉 case 揭露的關鍵歷史轉折「從 multi-tenant cluster 模型改成 single-tenant per game」

**修法**：rich case 引用時、用「揭露 X 觀察 + 作者判讀 Y」分層標明、避免把推論寫成 fact。或在引用後補一句「（case 中 X 屬作者判讀層、本章引用此推論）」明示分層。

兩類 case 的引用紀律可總結成一個 *fact vs derive* 分層原則：

- **Skeleton case**：絕大多數內容是 derive（方向 / 議題）、引用時不擴寫成 fact
- **Rich case**：含 fact（具體數字 / 設計）跟 derive（作者判讀）、引用時分層標明、避免把 derive 升級成 fact

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

5 個模組（01 / 02 / 03 / 04 / 05）驗證後、每模組 reviewer 抓到的 issue 數量穩定、可作為流程預期：

| Reviewer 維度          | 01      | 02       | 03       | 04        | 05       | baseline        |
| ---------------------- | ------- | -------- | -------- | --------- | -------- | --------------- |
| Standards reviewer     | 25      | 20       | 20       | 31        | 28       | 20-30 issue     |
| Case fidelity reviewer | 9 (88%) | 20 (78%) | 15 (70%) | 6 (92.9%) | 13 (80%) | 6-20 issue      |
| Consistency reviewer   | 13      | 15       | 15       | 14        | 18       | 13-18 issue     |
| **總計**               | **47**  | **55**   | **50**   | **51**    | **59**   | **47-59 issue** |

**模式觀察**：

- **每模組 ~50 issue 是穩定值**、不會因主題不同大幅波動、但 04/05 略往上推到 ~55、Standards reviewer 抓的「不是 X、而是 Y」段首結構成為新大宗
- **Case fidelity 準確率分布更廣**：04 的 92.9% 來自 skeleton case 嚴守「揭露方向、通用補充」紀律；05 的 80% 因引用 09 rich case 加入「fact vs derive 分層」新失分模式（見前面 *Rich case 引用的反向風險*）
- **Consistency reviewer 抓到的 frame 重複跟章節數成正比**：02 / 03 / 04 都有 ~13-18 個一致性 issue、05 跨模組（引 09 rich case）讓 issue 推到 18

**Stage 3 修正成本估算**：

- Critical（編造、矛盾）：~每個 5-10 分鐘修正、佔 0-5 個（04/05 都 0 critical、紀律已成熟）
- High（重複 frame、章節邊界、判讀層 vs fact）：~每個 10-20 分鐘修正、佔 5-14 個
- Medium / Low（規範細節、cross-link 補）：~每個 2-5 分鐘修正、佔 35-45 個
- **總計 ~1.5-2.5 小時 / 模組**

**Stage 4 修正後仍會有 ~30-40% issue 殘留**（low / medium 的 cross-link、編號漂移、用語不一）、屬於系統性 pattern、適合在 Stage 5 polish pass 集中處理（見後段）。

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

## 階段 5：Polish pass（04/05 模組後新增）

Stage 4 修完 high + 重要 medium 後、仍有 ~30-40% 的 low / medium 殘留、屬於系統性 pattern（負向骨架、編號漂移、cross-link 缺漏、模板化）。這些 issue 不適合按章節批次修、適合用「跨檔系統性掃描」處理 — 這是 polish pass 的核心責任。

### Polish pass 的觸發條件

Stage 4 後出現以下任一訊號、就該排 polish pass：

- Standards reviewer 抓出的「不是 X、而是 Y」段首結構超過 5 處（屬寫作習慣、單章修改無效率）
- Consistency reviewer 抓出「編號漂移」「失效 link」「用語不一」多處（屬跨檔規範問題）
- 自掃描漏掉的 pattern 出現在 reviewer report（例：04 自掃描說 pass、reviewer A 抓出 31 個 issue、暴露自掃描 regex 不夠寬）

### Polish pass 不該做的事

- **不重寫章節結構**：polish pass 是把現有內容修得更貼合規範、不是重新組織。重寫的觸發條件應該回到 stage 2、不是 polish pass。
- **不擴大 scope**：原本 4.20 / 5.4 等不在擴充範圍的章節、polish pass 也不動。Polish pass 邊界 = stage 4 修改過的章節集合。
- **不追求 0 issue**：reviewer 抓的 ~15 個 low 通常可保留為下次擴章節時自然處理。Polish pass 處理「系統性 pattern」、不處理「孤立 issue」。

### Polish pass 的標準工序

按系統性 pattern 分批處理、每批跑一次自掃描確認：

1. **負向骨架掃描修正**：用更寬泛的 regex `不是 |而不是|沒有.*[，、]會` 掃描、把「不是 X、而是 Y」「而不是 X」改成正向陳述 + 後置邊界提醒。技術約束敘述（「多人共用 IP 無法區分」）保留。
2. **編號漂移統一**：把 `04.X` 風格 plain text 改成 `[4.X title](url)` markdown link、跟 _index 對齊。
3. **表格延伸段補強（關鍵段）**：選 2-3 個最高 impact 表格（判讀訊號表的爭議列、Buffer / Sampling 等選型表）補延伸子段、不全部補（避免擴展超出 scope）。
4. **模板化拆敘事（代表性段）**：選 1-2 個最明顯的「四步驟模板套不同情境」段、拆成情境化敘事、其他保留為下次。
5. **Cross-link 補漏 + ownership 邊界補強**：reviewer C 報告的所有 cross-link 缺漏一次補完、用同一個批次跑 mdtools 驗證。
6. **用語不一統一 + 失效 link 修正**：簡轉繁、`/knowledge-cards/` vs `/section/` URL 統一、失效 link 改規劃中或正確路徑。
7. **最終驗證 + commit**：跑 `mdtools fmt --fix && mdtools cards && mdtools lint`、確認全綠、commit。

### Polish pass 的實作成本

實作中（04 / 05 polish pass 合併 commit `1072087`）：

- 處理範圍：11 個檔案、+44 / -29 行
- 修正項目：~35 個 issue（10 個負向骨架、2 個模板化、3 個編號漂移、3 個表格延伸段、3 個 cross-link、1 個 case 引用結構）
- 時間：~30-45 分鐘（不重寫、只 pattern match）
- 剩餘 ~15 個 low 保留下次

Polish pass 的 ROI 來自「系統性 pattern 一次處理 vs 散在各章一個個改」的效率差異。每個 pattern 在多章重複出現時、用 grep / rg 跨檔修一輪比每章單獨修快 3-5 倍。

### 自掃描盲點更新

04 流程暴露了一個 self-scan 盲點：原 regex `不行|不可以|不要|無法|不能` 漏掉「核心責任不是 X、而是 Y」這個變體段首。修正建議：

- 加 `^[^|].*責任(不是|並非)` 抓「核心責任不是 X」變體
- 加 `^[^|].*[，,]而是` 抓「X、而是 Y」結構（已是正常陳述、但段首位置仍是負向骨架）
- 加 `^[^|].*[，,]不是` 抓「X、不是 Y」結構

把自掃描 regex 視為持續演進的工具、每個 reviewer 抓出新 pattern 就更新一次、避免在下個模組重蹈覆轍。

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

## 5 個模組驗證後的反覆陷阱

01 / 02 / 03 / 04 / 05 五個模組執行下來、以下陷阱在 *多數模組都重複出現*、屬於 LLM case-driven 寫作的系統性失分點。本流程下次套用前要 *主動防範*、不能依賴 stage 3 reviewer 補救（雖然 reviewer 都會抓到、但修正成本高）。

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
- 04 規範 violation：原則 2 負向陳述（12 處最嚴重、含「核心責任不是 X、而是 Y」變體段首）、原則 1 首句結構（9 處）、原則 4 表格不延伸（9 處）
- 05 規範 violation：原則 2「不是 X、而是 Y」+「沒有 X、會 Y」（10 處）、原則 8 四步驟 / 四層並列模板（7 處）、原則 3 case 引用框架取代商業邏輯先行（6 處）

**防範**：

- Stage 2 寫完後 *寫稿端就跑掃描*、不等 reviewer：
  - `rg -n "不行|不可以|不要|無法|不能" <module-path>` 找負向骨架（技術約束敘述例外）
  - `rg -n "^[^|].*責任(不是|並非)" <module-path>` 找「核心責任不是 X」變體段首（04 模組新發現的 pattern）
  - `rg -n "^[^|].*[，,]而是|^[^|].*[，,]不是" <module-path>` 找對比骨架開段
  - 自查表格：每個 bullet 是否有後文延伸？
  - 自查首句：是否「核心原則先行」而非「對應 [case] 揭露」
- 模板化（L1/L2/L3、三選一）出現時、先問「這三項是真的對等？還是業務情境不同？」— 不同情境的話拆敘事段、不用表格

### 陷阱 4：Rich case 判讀層被當 case fact 引用（04/05 模組新發現）

引用 09 / 07 等 rich case 時、case 內常含「觀察層」（具體 fact）跟「判讀層」（作者推論）兩段。LLM 寫作時容易把兩層壓縮成「揭露 X」、把作者判讀升級為 case fact。

跟陷阱 1（skeleton case 擴寫成 case 事實）的差別：

- **陷阱 1**：case 沒提的細節（具體數字、taxonomy）被寫成 case 揭露
- **陷阱 4**：case 有提、但屬作者判讀層的內容被寫成 case fact

**實證**：

- 05 / 9.C12 Riot：5.2 寫「揭露 35ms latency 反推 region 部署」、實際 case 的「35ms」是觀察層、「反推 region 部署」是作者判讀層
- 05 / 9.C34 GCP：5.2 寫「揭露 Spanner 替 etcd 才是 K8s 規模極限的關鍵」、實際 case 用更保守的「control plane 極限取決於 storage backend、GCP 用 Spanner 替換 etcd」分兩個點寫、章節壓縮 + 強化成硬性結論
- 05 / 9.C12 Riot：漏掉 case 揭露的關鍵歷史轉折「從 multi-tenant cluster 模型改成 single-tenant per game」

**防範**：

- 引用 rich case 前、先把 case 內的「觀察段」跟「判讀段」分開讀、抽 finding 時各自標明來源層
- 引用時用「揭露 X 觀察 + 作者判讀 Y」分層寫、或在引用後補一句「（case 中 X 屬作者判讀層、本章引用此推論）」
- 避免使用「才是 / 必須 / 一定」這類強化詞、保留 case 原文的條件性表述
- Stage 3 case fidelity reviewer 的 prompt 要特別點出「判讀層 vs 觀察層」的分界、把這當作 high 級 issue 抓取

### 陷阱 5：自掃描盲點累積（04/05 模組顯現）

自掃描的 regex 跟 reviewer 抓的 pattern 會逐漸脫節。04 模組驗證時、self-scan 說 pass、但 reviewer A 抓出 31 issue、其中「核心責任不是 X、而是 Y」變體段首佔 12 處 — 屬於 self-scan 漏掉的新 pattern。

**實證**：

- 04 自掃描用 `不行|不可以|不要|無法|不能` 跟「不是 X、是 Y」掃描通過、但 reviewer A 抓出「核心責任不是 X、而是 Y」變體段首（佔 12 處）
- 05 自掃描通過、但 reviewer A 仍抓出「沒有 X、會 Y」鏈式負向句構 + 「四步驟模板」+ 「case 引用框架取代商業邏輯先行」三類新 pattern

**防範**：

- 每個模組 reviewer 抓出新 pattern 後、回頭更新 self-scan regex
- 把 self-scan 視為持續演進的工具、不是固定 checklist
- Stage 5 polish pass 是處理自掃描盲點累積的標準入口（見前段）

### 衍生 insight：reviewer 維度沒覆蓋的部分

3 個模組跑下來、發現現有 3 reviewer 維度（規範 / 案例準確性 / 跨章一致性）有未覆蓋的問題：

- **教學性 / 讀者路徑**：章節之間的閱讀順序是否合理？讀者讀完 A 章能不能銜接 B 章？目前沒 reviewer 檢查
- **判讀條件可操作性**：寫了判讀訊號、但實際工程師能不能用這些訊號做決策？沒 reviewer 驗證
- **實作可行性**：建議的設計是否真的能落地？跨團隊協調是否現實？需要懂業務的 reviewer

未來 6 / 7 / 8 模組執行時、可以考慮加第 4 個 reviewer 維度（教學性 + 實作可行性）。

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

本流程在 backend/01 至 backend/05 五個模組驗證後（共 ~30 章 / 263 review issue / case fidelity 70-93% 區間）、後續套用到：

- backend/06 reliability：用 09 reliability cases + 07 chaos cases
- backend/07 security / data protection：紅隊 cases 已有完整體系、本流程處理跨章一致性
- backend/08 incident response：跟 04 / 06 / 07 cross-link 密度最高、SSoT 對應規劃壓力最大
- 其他模組依此類推

流程本身會在每個模組後 retrospective、看 reviewer 維度是否該調整、findings 抽取方法是否該強化、polish pass 處理 pattern 是否該擴充。目前已知改進方向：

- 加 reviewer：教學性審查（讀者路徑是否清楚、判讀順序是否合理）
- 強化 findings 抽取：標註 finding 的 *泛化程度*、避免把 case-specific 細節推為通用結論
- Rich case 引用紀律：把「fact vs derive」分層寫進 stage 1 抽 findings 模板、stage 3 case fidelity reviewer prompt 也明示此分界
- 自掃描 regex 持續演進：每個模組 reviewer 抓出新 pattern 後、回頭加進 self-scan 工具、避免在下個模組重蹈覆轍
- 加修正後自動 lint：修完不只跑 mdtools、加跑「找首句否定句」「找表格沒延伸」「找模板化並列點」的自動掃描

跟其他寫作協議的整合：本流程跟 `compositional-writing` skill 互補（後者管 *單篇* 寫作的原子化跟意圖、本流程管 *跨章模組* 的 scope 跟一致性）、跟 `requirement-protocol` skill 互補（後者管 *對話協議*、本流程管 *內容生產*）。
