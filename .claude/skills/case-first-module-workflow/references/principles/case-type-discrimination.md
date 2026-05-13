# Case 類型識別原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md)、[stage-1-case-audit](../stage-1-case-audit.md) 引用。
>
> **何時讀**：Stage 1 抽 findings 時、判讀 case 該如何承接。

## 核心原則

引用案例前要先判斷 case 類型、不同類型適合不同承接深度。誤判類型 → 編造 case 沒寫的細節 → reviewer 抓出 → 修正成本高。

## 三類 case

### Rich case

- **典型**：跨模組 case 庫（如 09 / 07）中含具體數字、設計細節、遷移路徑的長篇 case
- **內容深度**：50-200 行、含具體數字、業務情境、引用源
- **承接方式**：可直接引用為事實、case 揭露的具體數字（RPS、延遲、TPS、stale window）可放進章節
- **注意**：rich case 內常含「觀察層 + 判讀層」、引用時要分層、見 [fact-vs-derive-layering](./fact-vs-derive-layering.md)
- **例**：「90M RPS + 5M writes/sec + 99.999%」可直接寫進章節

### Medium case（06 模組新發現的類別）

- **典型**：模組內部 case 庫中、含結構化「決策機制」+「可觀測訊號」表、但無具體數字的中篇 case
- **內容深度**：30-50 行、結構化 5 段（問題場景 / 決策機制 / 可觀測訊號 / 常見陷阱 / 下一步路由）、含 mechanism + 訊號名稱、但不給具體 RPS / 延遲數字
- **承接方式**：用 case 直接列出的 **mechanism 名稱** 精準引用（如「揭露 cell 邊界 / shuffle sharding / static stability / constant work 四個機制」）— 比 skeleton 精準、但比 rich 保守
- **承接句型**：「對應 [case]：揭露 N 個機制 — A（核心問題 1）、B（核心問題 2）、...。這 N 機制把 X 從 Y 轉為 Z。」
- **注意**：medium case 的「決策機制」段通常是 fact 層、「常見陷阱」段可能含作者判讀層、引用時也要分層
- **例**：06 模組 G1 Google Error Budget Policy 揭露 SLI / SLO / Budget gate 三對齊、可直接引用三對齊名稱跟對應「使用者價值 / 可接受承諾 / 交付節奏」、但不引用具體 burn rate 閾值數字

### Medium case 的「可引用範圍」表（07 模組新發現的強化紀律）

07 紅隊事件 case（51 行 medium case）在「來源」段用表格 *明確標明每個來源的可引用範圍*、是 fact-vs-derive 分層的最強紀律：

```markdown
## 來源

| 來源                                                  | 類型      | 可引用範圍                                                |
| ----------------------------------------------------- | --------- | --------------------------------------------------------- |
| [blog.cloudflare.com](...)                            | 官方      | 客戶側偵測、即時回應、Zero Trust 與 hardware key 防守效果 |
| [sec.okta.com](...)                                   | 政府/監管 | 上游事件 root cause、影響範圍、session token hijack 機制  |
| [cloud.google.com](...)                               | 技術分析  | UNC3944 對 SaaS 攻擊 TTP、跨組織 chain 模式               |
```

引用紀律：

- 章節引用要 *嚴守* 來源表標明的「可引用範圍」、不超出
- 例：來源表標「客戶側偵測」、章節寫「揭露客戶側偵測 mechanism」屬範圍內；寫「揭露完整攻擊鏈時序」屬超出範圍（攻擊鏈時序的可引用來源是 root cause 那條來源）
- Stage 3 reviewer B prompt 要明示「來源表可引用範圍」是 high 級 issue 抓取項

這層紀律比 09 rich case 的「觀察 vs 判讀」段落分割更精細 — case 文本作者已預先做了「來源 × 範圍」對應、章節引用要尊重這層 metadata。

### Skeleton case

- **典型**：模組內部 N.Cx 案例庫中只有 frame、無具體數字的短篇 case
- **內容深度**：10-30 行、只給方向、無具體數字 / taxonomy
- **承接方式**：作為「視角 / 方向」、可引用為「case 揭露 X 議題」、不引用為「case 揭露 X 具體場景數量」
- **承接句型**：「對應 [case] — 揭露 X 方向、以下展開基於通用工程知識補充」
- **例**：Meta Cache Consistency case 只給「promotion、shard move、故障恢復」三個方向、不引用為具體 inconsistency window 數字

## 判讀條件

| 訊號                                                                     | 判讀          |
| ------------------------------------------------------------------------ | ------------- |
| 行數 < 30 + 表格為主、無 mechanism 段                                    | Skeleton      |
| 行數 30-50 + 結構化「決策機制 + 可觀測訊號」表、無具體數字               | Medium        |
| 行數 > 50 + 含具體數字 / 設計細節                                        | Rich          |
| 含具體 RPS / 延遲 / TPS 數字                                             | Rich 傾向     |
| 含 mechanism 列表（cell boundary / shuffle sharding 等具名機制）但無數字 | Medium 傾向   |
| 只有「揭露 X、Y、Z 三個方向」結構                                        | Skeleton 傾向 |

## 三類 case 的失分對照

| Case 類型     | 主要失分模式                                                                                 | 修法                                                                                          |
| ------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Skeleton case | 擴寫成 case 沒提的細節、編造數字 / taxonomy                                                  | finding 用「揭露 X 方向、以下基於通用工程知識補充」承接                                       |
| Medium case   | 把 case 沒提的具體實作層擴寫進來、或混淆「決策機制」段（fact）跟「常見陷阱」段（含作者判讀） | 用 mechanism 名稱精準引用、不擴寫到 case 沒提的具體實作層、判讀段引用時標明「作者判讀」       |
| Rich case     | 把作者判讀層當 case fact 引用、混淆 fact vs derive                                           | 引用時分層「觀察 X + 作者判讀 Y」、見 [fact-vs-derive-layering](./fact-vs-derive-layering.md) |

## 實證

backend/01-07 七個模組驗證：

- backend/01：用 09 rich cases 為主、case fidelity 88%（skeleton 比例低）
- backend/02：cache 模組 case 偏向 skeleton、case fidelity 78%（skeleton 過度推論增加）
- backend/03：messaging case 高比例 skeleton、case fidelity 70%（最低、含 3 個 critical 編造）
- backend/04：observability 全 skeleton、case fidelity 92.9%（紀律成熟、嚴守「揭露方向、通用補充」）
- backend/05：5.X skeleton + 引用 09 rich case、case fidelity 80%（rich case 的「判讀層 vs fact」新失分浮現）
- backend/06：reliability 全 medium case、case fidelity 88%（首次套用 medium case 紀律、揭露「實作層擴寫過頭」失分跟「常見陷阱」段 fact-derive 分層不清）
- backend/07 batch 1：紅隊 medium case（51 行、含「來源表可引用範圍」表）+ skeleton 主 case、case fidelity 81%（揭露「跨 case 合成 frame」失分新類型、reviewer B 2 high 都屬此類）

## Stage 1 抽 findings 的判讀步驟

讀每個 case 時：

1. 看行數 + 內容密度、初判類型
2. 看是否有具體數字 / 設計細節、確認 Rich case
3. 看是否只給方向 / 議題、確認 Skeleton case
4. 介於中間時、傾向保守判讀為 Skeleton（避免過度承接）
5. 把類型寫進 findings 列表、stage 2 寫作時依類型決定承接深度

## 跨類型混合引用

模組可能同時引用 skeleton case（模組內）跟 rich case（跨模組）。兩類引用要分開處理：

- 同一段內若引兩類 case、先寫 rich case fact 作為支撐、再用 skeleton case 補方向
- 不要把 skeleton case 的方向跟 rich case 的數字混合成單一斷言
- 跨類型引用時 disclaimer 要明示哪段屬通用、哪段屬 case fact

## 自掃描提示

寫作完後、檢查每處 case 引用是否：

1. 標明 case 類型（findings 列表有記）
2. Skeleton case 引用是否擴寫成具體數字 / taxonomy（編造風險）
3. Rich case 引用是否分層（fact vs derive）
