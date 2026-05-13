# Stage 1：案例庫 audit + Findings 抽取

> **角色**：本卡是 `case-first-module-workflow` 的執行型 reference、被 [SKILL.md](../SKILL.md) 引用。
>
> **何時讀**：開始寫新模組、進入 stage 1 抽 findings 時。

## 為什麼要完整閱讀、不能只看 title + description

只看 title + description 能做 *承接*（建立 link）、但無法做 *scope 擴展*（揭露 LLM 不會自生的議題）。case 的 findings 通常埋在 body 的「判讀」段、不在 description 裡。

第一輪 audit 6 個 case、每 case 平均揭露 2.3 個 finding；其中約 7 成是 description 跟 title 看不到、要讀完整 body 才能抽出。

## 邊際遞減的判斷

不是所有 case 都要讀。實作觀察到的遞減曲線：

| 輪次   | 讀案例數 | 揭露 findings | 平均 / case | 純新議題 |
| ------ | -------- | ------------- | ----------- | -------- |
| 第一輪 | 6        | 14            | 2.3         | ~95%     |
| 第二輪 | 5        | 15            | 3.0         | ~85%     |
| 第三輪 | 5        | 13            | 2.6         | ~60%     |

第三輪開始 *純新議題* 比例下降、重複 frame 出現。這是停止 audit 的訊號。

判讀條件：

- **繼續 audit**：每 case 至少 1.5 個純新議題、且重複 frame 不超過 30%
- **停止 audit**：純新議題 < 1 個 / case、重複 frame > 50%、累積 finding 數已涵蓋目標章節主要議題

## Findings 抽取方法

讀 case 時、把每個段落看成可能的 finding 來源、問三個問題：

1. **這段揭露什麼判讀條件**？（純技術推導不易浮現的議題）
2. **這段揭露什麼數字 / 設計細節**？（規模、percentile、partition key 數量、replication lag 量級）
3. **這段揭露什麼失敗模式**？（事故當下會踩什麼坑、有什麼反直覺結論）

寫進 findings 列表時、要附上 *case 來源*、*該對應到哪個章節*、*case 類型（rich / skeleton）*。例：

```text
Finding: 線性擴展是 OLTP 設計最高目標、coordinator 是傳統 OLTP 的擴展瓶頸
來源: 9.C10 Spanner 案例「2 nodes → 45K reads/sec, 4 nodes → 90K reads/sec」段
案例類型: Rich case (含具體數字)
案例層級: 觀察層 (case fact、非作者判讀)
章節: 1.11 全球分散式 OLTP
```

不寫來源 / 章節 / 類型 / 層級、findings 會變成抽象列表、寫稿時用不上。

## Case 類型分類

三類 case 適合不同承接深度。誤判類型會引發 over-extrapolation 問題。

### Rich case

- 內容深度：50-200 行、含具體數字、業務情境、引用源
- 承接方式：可直接引用 case 揭露的具體數字（RPS、延遲、TPS、stale window）為 fact
- **重要**：rich case 內常含「觀察層」（具體 fact）+「判讀層」（作者推論）、引用時要分層、見 [principles/fact-vs-derive-layering](./principles/fact-vs-derive-layering.md)
- 例：09 模組 case「90M RPS + 5M writes/sec + 99.999%」可直接寫進章節

### Medium case（06 模組新發現的類別）

- 內容深度：30-50 行、結構化 5 段（問題場景 / 決策機制 / 可觀測訊號 / 常見陷阱 / 下一步路由）、含 mechanism + 訊號名稱但無具體數字
- 承接方式：用 case 直接列出的 **mechanism 名稱** 精準引用、不擴寫到 case 沒提的具體實作層
- Finding 寫法：「對應 [case]：揭露 N 個機制 — A（核心問題 1）、B（核心問題 2）、...。這 N 機制把 X 從 Y 轉為 Z。」
- **重要**：medium case「決策機制」段是 fact 層、「常見陷阱」段可能含作者判讀層、引用時也要分層
- 例：06 模組 A1 Amazon shuffle sharding 揭露 cell boundary / shuffle sharding / static stability / constant work 四機制、直接引用機制名稱、不擴寫到「cell 邊界具體大小」「shuffle sharding 具體 shard 數量」等 case 沒提的細節

### Skeleton case

- 內容深度：10-30 行、只給方向、無具體數字 / taxonomy
- 承接方式：作為「視角 / 方向」、可引用為「case 揭露 X 議題」、不引用為「case 揭露 X 具體場景數量」
- Finding 寫法：「對應 [case] — 揭露 X 方向、以下展開基於通用工程知識補充」
- 例：2.C1 Meta Cache Consistency 只給「promotion、shard move、故障恢復」三個方向、不引用為具體 inconsistency window 數字

### 判讀條件

- 看 case 行數 + 內容密度判斷類型
- 行數 < 30 + 表格為主、無 mechanism 段 → skeleton
- 行數 30-50 + 結構化「決策機制 + 可觀測訊號」表、無數字 → medium
- 行數 > 50 + 含具體數字 / 設計細節 → rich
- 介於中間 → 看內容密度跟結構決定（含 mechanism 列表優先 medium、含具體數字優先 rich、只給方向優先 skeleton）

## 三類 case 的失分對照

| Case 類型     | 主要失分                                                                                   | 修法                                                                                                                |
| ------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| Skeleton case | 擴寫成 case 沒提的細節、編造數字 / taxonomy                                                | finding 用「揭露 X 方向、以下基於通用工程知識補充」承接                                                             |
| Medium case   | 把 case 沒提的具體實作層擴寫進來、混淆「決策機制」段（fact）跟「常見陷阱」段（含作者判讀） | 用 mechanism 名稱精準引用、不擴寫到 case 沒提的具體實作層                                                           |
| Rich case     | 把作者判讀層當 case fact 引用、混淆 fact vs derive                                         | 引用時分層「觀察 X + 作者判讀 Y」、見 [principles/fact-vs-derive-layering](./principles/fact-vs-derive-layering.md) |

## Stage 1 完成的退出條件

- Findings 列表完整（含來源、章節、類型 skeleton / medium / rich、層級 fact / derive）
- 邊際遞減訊號出現（純新議題 < 1 個 / case 或重複 frame > 50%）
- Findings 覆蓋目標章節的主要議題
- Medium / Rich case 引用點都已標明「觀察層 vs 判讀層」分界（見 [principles/fact-vs-derive-layering](./principles/fact-vs-derive-layering.md)）
- 每個 case 的引用句構預先設想跟前面章節變化（避免 11/12 段同句構、見 [principles/case-citation-three-part](./principles/case-citation-three-part.md)）

進入 Stage 2 前、把 findings 跟章節大綱對齊、確認每章預期擴充量、開始 SSoT 對應規劃。
