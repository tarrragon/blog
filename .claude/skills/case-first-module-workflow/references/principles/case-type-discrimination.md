# Case 類型識別原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md)、[stage-1-case-audit](../stage-1-case-audit.md) 引用。
>
> **何時讀**：Stage 1 抽 findings 時、判讀 case 該如何承接。

## 核心原則

引用案例前要先判斷 case 類型、不同類型適合不同承接深度。誤判類型 → 編造 case 沒寫的細節 → reviewer 抓出 → 修正成本高。

## 兩類 case

### Rich case

- **典型**：跨模組 case 庫（如 09 / 07）中含具體數字、設計細節、遷移路徑的長篇 case
- **內容深度**：50-200 行、含具體數字、業務情境、引用源
- **承接方式**：可直接引用為事實、case 揭露的具體數字（RPS、延遲、TPS、stale window）可放進章節
- **注意**：rich case 內常含「觀察層 + 判讀層」、引用時要分層、見 [fact-vs-derive-layering](./fact-vs-derive-layering.md)
- **例**：「90M RPS + 5M writes/sec + 99.999%」可直接寫進章節

### Skeleton case

- **典型**：模組內部 N.Cx 案例庫中只有 frame、無具體數字的短篇 case
- **內容深度**：10-30 行、只給方向、無具體數字 / taxonomy
- **承接方式**：作為「視角 / 方向」、可引用為「case 揭露 X 議題」、不引用為「case 揭露 X 具體場景數量」
- **承接句型**：「對應 [case] — 揭露 X 方向、以下展開基於通用工程知識補充」
- **例**：Meta Cache Consistency case 只給「promotion、shard move、故障恢復」三個方向、不引用為具體 inconsistency window 數字

## 判讀條件

| 訊號                              | 判讀           |
| --------------------------------- | -------------- |
| 行數 < 30 + 表格為主              | Skeleton       |
| 行數 > 50 + 含具體數字 / 設計細節 | Rich           |
| 行數 30-50                        | 看內容密度決定 |
| 含具體 RPS / 延遲 / TPS 數字      | Rich 傾向      |
| 只有「揭露 X、Y、Z 三個方向」結構 | Skeleton 傾向  |

## 兩類 case 的失分對照

| Case 類型     | 主要失分模式                                       | 修法                                                                                          |
| ------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Skeleton case | 擴寫成 case 沒提的細節、編造數字 / taxonomy        | finding 用「揭露 X 方向、以下基於通用工程知識補充」承接                                       |
| Rich case     | 把作者判讀層當 case fact 引用、混淆 fact vs derive | 引用時分層「觀察 X + 作者判讀 Y」、見 [fact-vs-derive-layering](./fact-vs-derive-layering.md) |

## 實證

backend/01-05 五個模組驗證：

- backend/01：用 09 rich cases 為主、case fidelity 88%（skeleton 比例低）
- backend/02：cache 模組 case 偏向 skeleton、case fidelity 78%（skeleton 過度推論增加）
- backend/03：messaging case 高比例 skeleton、case fidelity 70%（最低、含 3 個 critical 編造）
- backend/04：observability 全 skeleton、case fidelity 92.9%（紀律成熟、嚴守「揭露方向、通用補充」）
- backend/05：5.X skeleton + 引用 09 rich case、case fidelity 80%（rich case 的「判讀層 vs fact」新失分浮現）

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
