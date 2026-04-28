---
title: "URL slug 必須顯式定義為 fact：跨工具 identifier 用單一定義源"
slug: "url-slug-must-be-explicit-fact"
date: 2026-04-28
weight: 93
description: "URL slug 在 Hugo 預設下從 title 自動推導、在 mdtools lint 下從檔名讀、在跨檔連結時又要寫第三個值 — 一個 identifier 散落在三個推導鏈、典型 SSoT 違反。當多個工具共用一個 identifier、推導不一致 = silent broken link。修法：把 slug 從 derivation（runtime 推導）升級成 fact（frontmatter 顯式定義）、檔名 / 連結都基於這個 fact。本卡是 #44 在 toolchain integration 情境的具體實例、是 #82 字面 vs 行為在 identifier 維度的展現。"
tags: ["report", "事後檢討", "工程方法論", "原則", "Identifier", "SSoT"]
---

## 結論

跨工具共用的 identifier（URL slug、API endpoint、route name、檔案 ID）必須**顯式定義在一處 fact**、不能依賴各工具各自推導。多工具各自推導 = 推導鏈分歧 = silent 失敗（compile / lint 時看不出、跨工具接縫時才爆）。

具體到 Hugo blog 的 URL slug：

| 推導鏈             | 來源                | 觸發時機      |
| ------------------ | ------------------- | ------------- |
| Hugo 自動推導      | `title` 經 `urlize` | runtime build |
| mdtools 字面比對   | 檔名（不含 `.md`）  | pre-commit    |
| 跨檔連結時的引用值 | 寫作者手動算 / 複製 | 寫作時        |

三個推導鏈 — 寫作者寫 `[link](/posts/X/)` 時、X 應該是哪個？沒有 single source 給答案。

**修法**：把 slug 從 derivation 升級成 fact — 在 frontmatter 顯式定義 `slug: <name>`、跟檔名對齊、所有工具基於此 fact 運作、跨檔連結用此 slug。

---

## 為什麼會散落

### 各工具的預設行為都「合理但不一致」

每個工具在自己的領域內都做了「合理的決定」、合起來才產生不一致：

| 工具    | 推導決定          | 為什麼合理                     |
| ------- | ----------------- | ------------------------------ |
| Hugo    | title → slug 推導 | 不寫 slug 也能 build、降低門檻 |
| mdtools | 檔名 = slug       | 字面 lint、不執行 hugo runtime |
| 寫作者  | 看心情寫          | 沒規範就靠記憶 / 複製貼上      |

每個決定本身沒錯、合起來形成「**沒有單一真相**」的狀態。

### Hugo 的 `urlize` 不是純函式

Hugo 的 title → slug 推導用 `urlize`、規則隨版本演進、對中文 / 全形字元 / 連字符的處理會變。寫的當下推導出來的 slug、未來 hugo 升級後可能變不同 — 這是「**runtime 推導 = 隱性依賴 hugo 版本**」。

而 frontmatter 的 `slug: <value>` 是字面值、不依賴任何工具的推導邏輯、跨版本穩定。

### 「能 build 就不寫」是便利驅動偏移（[#67](../ease-of-writing-vs-intent-alignment/)）

Hugo 不寫 slug 也能 build — 寫作的當下、加 slug 是「多餘工作」、看起來沒收益。便利驅動讓寫作者跳過。但這個便利是**借用未來的成本** — 跨檔連結時、slug 推導不一致才暴露、那時要付的修復成本遠大於當初寫 slug 的成本。

---

## Fact vs Derivation：slug 該是哪一種

呼應 [#44](../single-source-of-truth/) 的區分：

| 類型           | 定義                       | slug 的歸類     |
| -------------- | -------------------------- | --------------- |
| **Fact**       | 設計決定、不能從別處算出   | slug 應屬此類   |
| **Derivation** | 從 fact 計算得出、無自主性 | slug 不該屬此類 |

**slug 必須是 fact**、不是 derivation。理由：

- slug 的「值」是設計選擇 — 用什麼字串作為 URL 一部分、是 SEO / 可讀性 / 穩定性的決定、不該被自動推導左右
- 一旦固定後就**不能改**（改 slug = URL 改 = 外部連結全部死）
- 「不能改」+「設計決定」= 應該是 fact

**hugo 的 title→slug 推導**：把一個 fact 偽裝成 derivation。表面上看「我只寫 title、slug 自動算出來」、實際上推導出來的 slug 變成了一個**新的 fact**（一旦發布就不能改）、但這個 fact 的住址不在程式碼裡、在 hugo runtime 裡。

---

## 反模式：分散的 derivation 鏈

### 多工具各自推導 = silent 不一致

當多個工具各自從不同 source derive 同一個 identifier、寫的當下都通過、跨工具接縫時才爆：

| 工具 X 看到 | 工具 Y 看到 | 看到時機 | 後果                     |
| ----------- | ----------- | -------- | ------------------------ |
| 一致        | 一致        | 寫作時   | 表面 OK、累積債          |
| 一致        | 不一致      | 跨工具時 | broken link / build fail |
| 不一致      | 不一致      | 多版本時 | 升級後新舊推導規則不一致 |

**寫的當下看不出**、是這個反模式的核心難處。

### 「規則膨脹」誘惑：教 mdtools 認 hugo 規則

碰到 mdtools 不認 hugo title 推導時、直覺反應是「教 mdtools 也跑 urlize」。這是**用字面工具模擬行為層**（[#82](../literal-interception-vs-behavioral-refinement/) 的反模式）：

- mdtools 是字面 lint、學會 urlize → 增加實作成本、要追 hugo 版本變動
- 解決了表面症狀、但根因（slug 是 derivation）沒動
- 下一個工具（如 search index）加進來、又要再學一次 urlize

正解是**消滅 derivation 鏈、把 slug 升成 fact**。每個工具直接讀 fact、不需要學別人的推導規則。

### 「之後再補 slug」的 trigger 缺失

「先這樣、之後系統性 backfill」是 [#72](../external-trigger-for-high-roi-work/) 的典型訊號。沒有 trigger 時、debt 永遠累積：

- 175 篇文章沒 slug、每多寫一篇 debt 多一份
- backfill 沒被排上 → 永遠不做
- 直到某天有人引用中文 title 的文章、broken link 才浮現

修法：lint 規則加 `missing-slug` check、把 trigger 結構性建立（[#91](../escalation-trigger-quantification/) 量化 trigger 設計）。

---

## 修法：兩層補強

### 規範層（解根因）

每篇 content 文章 frontmatter 必須有 `slug`、值跟檔名對齊（不含副檔名）：

```yaml
---
title: "Hugo 部落格支援 Mermaid 流程圖完整實現指南"
slug: "mermaid-gitgraph"   # 跟檔名 mermaid-gitgraph.md 對齊
date: 2025-10-08
---
```

寫好後：

- Hugo 用 `slug:` 不再 derive title
- mdtools 用檔名比對 frontmatter slug、字面對齊就過
- 跨檔連結 `[...](/posts/mermaid-gitgraph/)` 直接基於 slug、不需推算
- SSoT 集中在 frontmatter、檔名是 mirror（自動驗證一致性）

### 工具層（防呆）

mdtools 加 lint 規則：

| 規則 ID                   | 檢查                             | error / warn  |
| ------------------------- | -------------------------------- | ------------- |
| L1-missing-slug           | content 文章 frontmatter 缺 slug | error（強制） |
| L1-slug-filename-mismatch | slug != 檔名 stem                | error         |
| L2-broken-internal-link   | `/posts/<slug>/` slug 不存在     | error（既有） |

把問題從「跨檔 link 時 broken」提前到「寫作時就 catch」。

### 歷史 backfill

175 篇沒 slug 的文章需要 backfill。可寫 script：

```bash
for f in content/posts/*.md content/work-log/*.md content/record/*.md content/report/*.md; do
  slug=$(basename "$f" .md)
  if ! grep -q "^slug:" "$f"; then
    # 在 date: 後插入 slug: <檔名>
    sed -i.bak "/^date:/a\\
slug: \"$slug\"" "$f"
  fi
done
```

人工 review 確認 slug 沒衝突、commit。

---

## 跟其他抽象層原則的關係

| 原則                                                                          | 關係                                                                                                                     |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| [#44 Single Source of Truth](../single-source-of-truth/)                      | **本卡是 #44 在 identifier 維度的具體實例** — slug 散落三處、fact 升級為主修法                                           |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) | mdtools 是字面 lint、hugo urlize 是 runtime 行為 — 兩層之間的 gap 用「教字面學行為」解 = 規則膨脹、正解是消除 derivation |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)     | 「能 build 就不寫 slug」是便利寫法、「顯式寫 slug」是對齊意圖（不依賴推導）                                              |
| [#72 高 ROI 無外部觸發](../external-trigger-for-high-roi-work/)               | 「之後系統性補 slug」沒 trigger = 永遠不會做、175 篇累積債就是這條訊號                                                   |
| [#91 升級 trigger 的量化設計](../escalation-trigger-quantification/)          | 補 lint 規則是 trigger、把「應該補 slug」從紀律升級成結構性檢查                                                          |
| [#92 視覺手段對齊錯誤層次](../visual-tool-error-layer-alignment/)             | 同骨：工具的 ceiling（mdtools 字面 vs hugo runtime）超出就 false confidence                                              |

本卡跟 #82 / #92 共同形成「**工具 ceiling pattern 系列**」 — 每個工具都有能擋的層 / 擋不到的層、跨層之間需要「升級 fact」或「換工具」、不是「教工具學別人的規則」。

---

## 套用到本系統的 case

### Case 1：175 篇 0 slug 的累積債

實證資料（2026-04-28 撤查）：

| 資料夾    | 文章數 | 有 frontmatter slug |
| --------- | ------ | ------------------- |
| posts/    | 17     | 0                   |
| work-log/ | 12     | 0                   |
| record/   | 53     | 0                   |
| report/   | 93     | 0                   |
| **合計**  | 175    | **0**               |

每一篇都是潛在的 broken link 觸發點、debt 未爆出來只因為「英文檔名跟 hugo 推導剛好一樣」。

### Case 2：mermaid 流程圖文章的引用 broken

寫 [#92](../visual-tool-error-layer-alignment/) 的 case 2 提到 `mermaid_gitgraph_type_color_config` 文章、想連到既有的 `mermaid流程圖.md`。實際軌跡：

1. 第一直覺：寫 `[...](/posts/hugo-部落格支援-mermaid-流程圖完整實現指南/)`（hugo 推導出來的 URL）
2. mdtools L1-broken-link 失敗、它認檔名 `mermaid流程圖.md`
3. 改寫 `[...](/posts/mermaid流程圖/)`、hugo build 後變 404（因為 hugo 認 title 推導的 slug）
4. 退而求其次：去掉超連結、改純文字提及

問題的根本是「mermaid流程圖.md 沒寫 slug」 — fact 缺失、就只能在「mdtools 認的字面」跟「hugo 認的推導」中二選一、兩者都不對。

正解：給 mermaid流程圖.md 補 `slug: mermaid-gitgraph` 或類似、檔名 rename 對齊、所有工具基於同一 fact。

### Case 3：跨工具 identifier 的通用 pattern

不只是 hugo blog — 任何「多工具共用 identifier」的情境都同樣 pattern：

| 領域           | identifier      | 散落的推導鏈                                |
| -------------- | --------------- | ------------------------------------------- |
| Hugo blog      | URL slug        | 檔名 / hugo title / frontmatter             |
| API server     | endpoint route  | controller path / OpenAPI spec / client SDK |
| DB migration   | migration ID    | 檔名 / hash / sequence                      |
| Frontend route | path identifier | 檔案位置 / route config / navigation        |
| LLM tool name  | tool 名稱       | function name / schema / prompt 引用        |

每一類的修法都一樣：**把 identifier 升成 fact、所有工具基於此 fact**、不要讓各工具各自推導。

---

## 判讀徵兆

| 訊號                                  | 該做的事                                                             |
| ------------------------------------- | -------------------------------------------------------------------- |
| 「這個 link 為什麼 broken」debug 半天 | 推導鏈不一致、檢查 identifier 有沒有顯式 fact                        |
| 「教這個工具認另一個工具的規則」      | 規則膨脹的開始、正解是消除 derivation                                |
| 「能跑就不寫 X 欄位」                 | 便利驅動、未來會在跨工具接縫爆                                       |
| 「之後系統性補 backfill」             | [#72](../external-trigger-for-high-roi-work/) 缺 trigger、會永遠跳過 |
| 兩個工具對同個 ID 算出不同值          | 多源 derivation、改成單一 fact                                       |
| 升級工具版本後 link / route 全壞      | 依賴 runtime 推導、推導規則隨版本變                                  |
| 「我手動算一下這個 slug 應該是什麼」  | identifier 不該需要心算、補 fact                                     |
| Lint 不報錯但 production broken       | 字面 lint 跟 runtime 行為的 gap、補 lint 規則或補 fact               |

**核心**：跨工具共用的 identifier 必須是 fact、不是 derivation。**Derivation 鏈把單一值散落在多工具的推導邏輯裡、寫的當下看不出問題、跨工具接縫才爆 — 而那時候 debt 已經累積到難以集中修**。Fact 升級的成本（每篇加一行 frontmatter）遠小於 derivation 鏈失敗的修復成本（broken link / SEO 損失 / debugging 時間）。
