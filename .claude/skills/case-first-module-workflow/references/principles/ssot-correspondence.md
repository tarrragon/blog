# SSoT 對應原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md) 引用。
>
> **何時讀**：Stage 2 寫作前 30 分鐘做 SSoT 對應規劃時。

## 核心原則

當同一 finding 或 frame 在 *多個章節* 都有用、要在開始寫之前 *先定 SSoT 對應*、否則 case-driven 擴章必然出現 frame 重複展開。

每個 cross-chapter frame 指定 *一個* 主寫章節（SSoT）、其他章節 *只 link、不展開*。

## 為什麼這層紀律重要

漏掉 SSoT 對應、reviewer 跨章一致性會抓出 5-10 個 frame 重複 issue。修正成本高（要把已展開內容收斂回 SSoT、要重寫多個段落）。Stage 2 前花 30 分鐘做 SSoT 對應、能省下 Stage 4 / Stage 5 數小時的重構工。

## SSoT 對應的判讀順序

1. 列出所有 cross-chapter findings（出現在多章的 frame）
2. 每個 frame 指定 *一個* 主寫章節（SSoT）
3. 其他章節 *只 link、不展開*
4. SSoT 章節要有完整論述、被引用章節保留簡述跟 cross-link

## SSoT 選擇標準

- frame 涉及 *跨模組層級概念* → 寫進模組索引檔（module index、Hugo 結構下為 `_index.md`、其他可能是 `README.md` / `index.md`）
- frame 涉及 *單章核心責任* → SSoT 為該章
- frame 涉及 *跨章交接點* → 選最相關章節為 SSoT、其他章節 link
- frame 涉及 *兩個 lens（不同角度看同議題）* → 兩章各自 SSoT、但要互相 lens 區分宣告

## 實證案例

來自 backend/01-05 模組驗證、SSoT 漏定的反例：

### 02 cache 模組

- 「cache 角色變化」frame 在 2.1 主寫、但實際屬模組層級、應在模組索引檔
- Tubi 案例在 2.1 / 2.2 / 2.8 三章各自展開 mini-finding（沒選 SSoT）
- Snap KeyDB 在 2.1 / 2.7 / 2.8 三章重複（沒選 SSoT）

### 03 message-queue 模組（最嚴重）

- 「三層語意（delivery / processing / recovery）」在 3.4 / 3.6 / 3.8 三章各自定義（無 SSoT）
- 「Slack Kafka+Redis 拓樸」在 3.4 跟 3.8 兩章逐字重複（無 SSoT）
- 「規模對照（小 / 中 / 大型）」在 3.4 / 3.6 / 3.8 三章拆用、結論散落、讀者拼不出總圖

### 04 observability 模組（SSoT 設計成功）

- 觀測遷移執行順序 → 4.11 SSoT、其他章 link
- 雙軌採集對照驗證 → 4.17 SSoT、4.11 link
- audit log 邊界 → 4.12 SSoT、4.20 link
- cardinality 失控 → 4.7 SSoT、4.17 link

結果：04 Reviewer C 抓 14 個 issue 中只有 3 個 frame 重複 issue（H1 sampling、H2 規模差異雙 lens、H3 雙軌對照）、且都有對應 lens 區分宣告。

## 合成章的硬規則（第 6 個模組驗證新增）

模組若含「合成型框架章」（從全案例庫合成推導、無專屬案例、案例支撐標「合成」）、SSoT map 要對它加一條硬規則：**合成章引用任何案例、只允許「一句話結論 + 數字 + link 主寫章」、案例的機制 / 清單 / 時序展開一律留給主寫章**。

依據：合成章的每個論點都需要例證、全庫最強的 anchor 案例正好都能當它的例證、寫作壓力會讓合成章把案例細節完整吸進來 — 下游主寫章要嘛重複展開、要嘛反向 link、map 的主寫方向被靜默反轉。實測一個 10 章模組（含 1 個合成章）：6 個 High 重複展開 issue 有 4 個同此根因。配套技巧：合成章初稿可以最後寫、或主寫章成形後回頭壓縮 — 「該壓到多薄」有明確參照。

寫作中的生效點判讀：寫合成章時發現某段「需要一個好例子」、而想到的例子在 map 上分派給別章 — 這一刻寫一句話 + link、不寫細節。

## 寫後回填輪（第 6 個模組驗證新增）

SSoT map 是「宣告 + 寫作紀律 + 回填工序」三件套。大綱的案例支撐欄與 case 檔的「對應大綱」欄是寫作前的預測、正文完成後必然偏離（偏離是健康的、寫作發現優於規劃）— 正文全部完成後要跑一輪機械性回填：對每章 grep 實際引用的案例編號、更新大綱支撐欄；對每個被引用案例、更新對應大綱欄；未實現的預測交叉刪除或標「候選」。實測缺這一輪時、對齊類 issue 佔一致性 review 近半（22 中 10）、稀釋 reviewer 對結構性問題的注意力。

## Lens 區分宣告（同 frame 兩個角度）

當同 frame 在兩章各有合理 SSoT（不同 lens）、要明示 lens 區分：

例：「規模差異」frame 在 4.11 跟 4.18 都展開：

- 4.11：「本段聚焦遷移期的節奏取捨；常態 ownership 配置由 [4.18 規模差異下的角色配置] 處理、兩者 lens 不同」
- 4.18：「本段聚焦常態 ownership 配置（不同規模下角色矩陣的差異）；遷移期的節奏取捨由 [4.11 規模差異下的遷移節奏] 處理、兩者 lens 不同」

雙向 anchor link + lens 區分宣告 = SSoT 對 lens 拆分的標準做法。

## Stage 2 寫作前的 SSoT 對應清單

寫作前要完成的清單：

```text
Cross-chapter frames:
- <frame_1>:
  - SSoT: <chapter_X>
  - Link from: <chapter_Y>, <chapter_Z>
  - Lens 區分: 無 / <Y 的 lens 是 X 看 ABC>

- <frame_2>:
  - SSoT: 模組索引（跨模組層級）
  - Link from: <chapter_X>, <chapter_Y>

- ...
```

每個 frame 對應完才開始寫 stage 2。

## 自掃描提示

寫作完後、檢查：

1. 每個 cross-chapter frame 是否只在 SSoT 章展開、其他章只 link？
2. 雙 lens frame 是否互相 anchor link + lens 區分宣告？
3. cross-link 目標是否正確（章節 URL 而非 knowledge card URL）？
4. SSoT map 中的 frame 是否在模組索引的章節列表中可見？
5. 合成章是否守住「一句話 + link」規則？（對每個 anchor 案例 grep 它的關鍵數字、命中超過一章即候選）
6. 回填輪是否跑過？（大綱案例支撐欄、case 檔對應大綱欄、跟正文實際引用三方對照）

如果 reviewer C 抓出 frame 重複 issue、回頭檢查是否 stage 2 前漏定 SSoT、補在後續模組的 SSoT 對應清單。
