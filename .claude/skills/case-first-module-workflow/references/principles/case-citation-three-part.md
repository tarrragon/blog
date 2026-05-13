# Case 引用三段式原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md)、[stage-1-case-audit](../stage-1-case-audit.md)、[self-scan-regex](../self-scan-regex.md) 引用。
>
> **何時讀**：Stage 2 寫作引用 case 時、Stage 5 polish pass 修「段首 case 引用框架」時。

## 核心原則

每處引用 case、要遵守三段式結構：

1. **概念定義句**：先寫「該概念是什麼、承擔什麼責任」、放段首
2. **Case 引用**：「對應 [case]：揭露 N 個機制 — ...」、放第二位置
3. **通用展開**：「以下基於通用工程知識補充」+ 具體操作

違反這個結構的最常見形式是「概念定義句缺位、case 引用直接當段首」— 讀者尚未理解概念就被丟入案例細節。

## 為什麼這層紀律重要

06 模組 reviewer 抓出 11/12 新段都犯「case 引用取代概念定義」的問題、屬最大宗 systemic 違規。原因：

- LLM 從 case 反推內容時、容易把 case 揭露當概念出發點
- Case 引用句構單一（「對應 [X]：揭露 N 個機制」）、跨章讀感同質
- 概念定義被推到第二段、商業邏輯先於 case 的原則被推翻

三段式紀律的價值是把「概念」「案例」「展開」三層分離、讓讀者依層級理解。

## 三段式範例

### 正確結構（從 06 修正後抓的）

```markdown
## 失效局部化：cell 邊界跟 shuffle sharding

失效局部化是把單一依賴退化限制在最小可影響範圍的能力。把「依賴 budget」
從統一全域帳本拆成 per-cell 可用度結構、是這層治理的核心責任。失效局部
化要解四個子問題：擴散邊界、熱點重疊、控制面解耦、失敗模式工作量恆定。

對應 [A1 Amazon Shuffle Sharding 與 Cell 邊界](.../shuffle-sharding-and-cell-boundary/)：
揭露四個機制對應上述四個子問題 — cell 邊界（擴散邊界）、shuffle sharding
（熱點重疊）、static stability（控制面解耦）、constant work（失敗模式工作
量恆定）。這四個機制把恢復策略從「全域搶救」轉為「分批收斂」。

[以下基於通用工程知識補充的具體操作]
```

### 錯誤結構（從 06 stage 2 commit 抓的、之後修正了）

```markdown
## 失效局部化：cell 邊界跟 shuffle sharding

依賴 budget 的另一個面向是把失效影響限制在局部、不擴散到全域。多租戶
服務跟共享資源服務若沒有明確邊界，單一依賴退化會觸發整體退化。

對應 [A1 Amazon Shuffle Sharding 與 Cell 邊界](.../shuffle-sharding-and-cell-boundary/)：
揭露四個機制 — cell 邊界、shuffle sharding、static stability、constant work。
```

差異：

- **正確**：段首「失效局部化是...的能力」直接給概念定義、case 揭露的四機制對應到「四個子問題」、讀者懂概念才看到案例
- **錯誤**：段首用「另一個面向」鋪墊、case 直接列四機制、讀者尚未理解就被丟入案例細節

## 跟其他原則的關係

本原則跟 [case-type-discrimination](./case-type-discrimination.md) 跟 [fact-vs-derive-layering](./fact-vs-derive-layering.md) 互補：

- **case-type-discrimination**：決定該不該引用具體細節（看 case 類型 skeleton / medium / rich）
- **fact-vs-derive-layering**：決定引用時要不要分層標明（看 case 內部 fact / derive）
- **case-citation-three-part**（本卡）：決定引用結構（概念 / case / 展開三段）

三層紀律組合起來：

- skeleton case：三段式中段（case 引用）保持「揭露方向」抽象、不擴寫成 fact
- medium case：三段式中段引用 mechanism 名稱、不引用具體數字
- rich case：三段式中段分層引用、fact 跟 derive 分開標明

## Case 引用句構變化

06 模組 12 個新段中 11 個用「對應 [case]：揭露 N 個機制」相同句構、跨章節讀起來同質。三段式紀律的另一面是 case 引用句構應變化：

| 句構                                               | 適用場景                                           | 範例                              |
| -------------------------------------------------- | -------------------------------------------------- | --------------------------------- |
| 「對應 [case]：揭露 N 個機制 — ...」               | case 直接列出 N 個 mechanism、且本章對應 SSoT 概念 | A1 四機制對應失效局部化           |
| 「[case] 的四元素揭露了 X 子問題的完整 contract」  | case 提供結構化框架、本章解該框架                  | N1 四元素對應 chaos 完整 contract |
| 「N1 三機制中、reliability contract 對本節最直接」 | 引用 case 部分 mechanism、其他用 link 帶過         | SP1 部分 mechanism 對本節重要     |
| 「[case] 的 P0/P1 分級告訴我們...」                | case 揭露的是政策框架、不是 mechanism list         | G2 分級政策                       |
| 「[case] 揭露兩個層次的對照：X 跟 Y」              | case 揭露對比結構                                  | H1 BFCM peak vs daily ops 對照    |

寫多章時刻意變化句構、避免讀者連讀數章感「每段開頭都長一樣」。

## Stage 2 自查清單

寫完每章 case 引用後、檢查：

1. **段首是否是概念定義句**？（不是 case 引用、不是反例鋪墊、不是「另一個面向」鋪墊）
2. **Case 引用是否在第二位置**？（不是段首）
3. **通用展開是否有「以下基於通用工程知識補充」承接**？
4. **句構是否跟前面章節相同**？（同模組超過 3 章用同句構就該變化）

掃描指令：

```bash
# 找段首是 case 引用的段（最嚴格）
rg -n "^對應 \[" <module-paths>

# 找 ## 標題後緊接 case 引用的段（要手動 review）
rg -B0 -A3 -n "^## " <file> | rg "對應 \["
```

## Polish pass 修法

如果 stage 3 reviewer 抓出大量「case 引用段首」issue、polish pass 的修法是：

1. 每個有 issue 的段、在 case 引用前補一句「概念定義 + 核心責任」
2. 不重寫整段、只加 lead sentence（保留 case 引用本身）
3. 變化 case 引用句構：把 11/12 段同一句構打散成 3-4 種變化
4. 修完跑自掃描確認段首不再是 case 引用

修法成本：每段補 1-2 句概念定義、單章約 5-10 分鐘、整模組 1-2 小時。

## 案例引用句構同質化（07 模組新發現）

07 batch 1 模組驗證後浮現新 pattern：即使遵守三段式紀律、跨章 case 引用句構仍會同質化。13 處 case 引用 11 處用同一句構：

```text
對應 [case]：揭露 N 層失效控制面 — A、B、C。案例「可落地檢查點」標明 mechanism 為「X」、前提是「Y」。
```

讀者跨章連讀時、會把 case 引用當儀式而非論證。Stage 5 polish pass 要主動分流。

### 分流原則：句構跟著 case 類型走

不同 case 類型適合不同句構、用 case 自身結構決定引用方式、避免硬塞同模板：

| Case 結構                      | 適用句構                                                | 範例觸發場景                         |
| ------------------------------ | ------------------------------------------------------- | ------------------------------------ |
| Case 直接列 N 個 mechanism     | 「揭露 N 層失效控制面 — A、B、C」                       | A1 Amazon Shuffle Sharding 四機制    |
| Case 主寫單一壓力場景          | 「補的失效訊號是 X、mechanism 是 Y」                    | Snowflake 資料外送單一場景           |
| Case 揭露歷史轉折              | 「從 X 改成 Y 的關鍵架構決策」                          | Riot multi-tenant → single-tenant    |
| Case 揭露對比結構              | 「揭露兩個層次的對照：A vs B」                          | BFCM peak vs daily ops 對照          |
| 多 case 並列補不同層           | 「A case 補 X、B case 補 Y」                            | Citrix + PAN-OS 共同三同步 mechanism |
| Case 揭露 mechanism 可引用範圍 | 「案例『可落地檢查點』直接列出 mechanism 屬可引用範圍」 | 07 紅隊 case 來源表標明              |

### Stage 5 polish 工序

1. 跑 `rg -c "揭露[^。]*失效控制面" <module-paths>` 看模組內同句構次數
2. 超過 5 處用同一句構：選 2-3 處改別的句構（按 case 結構決定）
3. 不追求 0 重複：保留部分同句構用於 case 結構相似的場景、避免過度變化

修法成本：每處 2-3 分鐘、整模組約 30 分鐘。

### 對 Stage 2 寫作的回饋

Stage 2 寫每個 case 引用時、問「這個 case 的結構是什麼類型？」再選對應句構。寫完每章後跑句構同質化掃描、避免跨章累積。
