# Blog Codex Writing Rules

本文件是 blog 專案的內容生產準則。目標是把教學內容寫成可重用、可擴展、可交接的工程知識，而不是專案維護手冊。

## 0. 規範優先序

1. 本檔（`blog/codex.md`）為當前專案最高優先寫作規範。
2. 文章撰寫需遵循 `compositional-writing` 方法。
3. 提案/分析需遵循 `wrap-decision`（WARP）方法。
4. 版本與文件流需遵循 `doc-flow` 分工邏輯。

---

## 1. 寫作核心原則（強制）

### 原則一：核心原則先行

- 每段首句先說「這個概念是什麼、承擔什麼責任」。
- 例子與補充放在原則之後，提醒/邊界放最後。
- 禁止先丟案例、最後才補定義。

### 原則二：正向陳述優先

- 主要敘述使用正向句建立概念。
- 反例段落可以存在，但目的為對照，不可讓否定句主導段落。
- 完稿後必做關鍵字掃描：`不行`、`不可以`、`不是`、`不要`、`無法`、`不能`。

### 原則三：商業邏輯先於 CASE

- 先寫系統層概念（為何存在、解什麼問題），再寫具體案例。
- 不能只給設定值或語法片段。

### 原則四：表格不是終點

- 表格中的每個「情境/判斷」都要有延伸子段落。
- 要回答：這情境在真實服務長什麼樣、為何成立、常見陷阱是什麼。

### 原則五：避免專案綁定敘事

- 教材不可預設讀者熟悉特定內部專案（例如 ccsession）。
- 不引用專案私有運作細節作為理解前提。
- 用獨立範例、通用情境與虛擬程式碼說明。

### 原則六：讀者定位用內容體現

- 預設讀者工程經驗有限，但文中不使用「新手」「新人」字樣。
- 用現實服務案例補足經驗差距，而不是降低技術深度。

### 原則七：每篇都要有可操作判準

- 段落至少包含：判讀訊號、風險、邊界、下一步路由。
- 不能只做名詞定義。

---

## 2. 語言與主題邊界

### Go 教材定位

- Go 章節核心是語言精神與工程實踐，不是單一專案維運指南。
- 後端擴充章節可寫，但必須從 Go 的設計思想與工程決策出發。

### Backend 教材定位

- Backend 是語言無關層，描述服務能力、風險、成本與決策，不綁 Go/Python。
- 各語言章節可連到 Backend 能力，但 Backend 不反向依賴語言實作。

---

## 3. 知識卡片規範（Atomic Cards）

### 建卡原則

- 一張卡片只說一個語意責任。
- 名詞若跨情境變義，必拆卡，不可混寫。
- 優先使用情境精確命名，避免傘狀詞。

### 拆卡判準

- transport vs process vs workflow
- durable vs ephemeral
- ordered vs unordered
- replayable vs one-way
- single consumer vs fan-out
- human workflow vs machine protocol
- service boundary vs language boundary

### 使用規則

- 文章內出現關鍵術語，優先連到卡片。
- 卡片是概念索引，章節是決策與情境推導。
- 術語過於寬泛時，不硬建卡，改寫成具體情境詞。

---

## 4. WARP（wrap-decision）分析方法（強制觸發）

當需求包含「分析」「決策」「比較」「提案」「查詢」時，使用 WARP：

1. Anchor Check：先對齊核心目標與決策錨點。
2. Step 0 資料充足度：判斷是否可直接下結論。
3. Widen Options：至少列出多個本質不同選項。
4. Reality Test：用來源與反例驗證，不靠直覺。
5. Attain Distance：評估機會成本與長期影響。
6. Prepare to be Wrong：預先設計失敗回退與監控。
7. Tripwire：設定何時重新評估決策。

### WARP 查詢輸出要求

- 清楚標示：觀察、判讀、策略、結論。
- 引用來源要可回溯。
- 必含反向驗證（批評/反例/限制）。

---

## 5. 文章產出流程（每次都要跑）

1. 更新章節大綱（outline 為唯一 backlog）。
2. 依大綱撰寫草稿。
3. 術語掃描：補連結、補缺卡。
4. 寫作規範掃描：核心先行、正向陳述、案例補足。
5. 結構掃描：避免重複、補交叉引用與路由。
6. 最終 review：確認可直接交付。

### 關鍵硬性規則

- 每次生成後，必做一次「規範檢討 pass」；不可直接交稿。
- 若檢討發現違規，先修文，再進下一章。

---

## 6. 完稿檢查清單（提交前）

- [ ] 每段首句是核心原則，不是例子
- [ ] 負向陳述已降到必要最小
- [ ] 每個抽象名詞都有情境化說明
- [ ] 表格項目都有延伸解釋段
- [ ] 未依賴特定專案背景知識
- [ ] 關鍵術語已連到對應卡片
- [ ] 有明確下一步路由（章節/模組連結）

---

## 7. 文件分工（doc-flow 對齊）

- `doc`：需求、提案、spec（上游）
- `doc-flow`：版本文件與一致性（中台）
- `ticket`：任務執行與追蹤（下游）

寫作工作需反映在對應大綱與版本文件，避免散落 todo。

---

## 8. Markdown 排版規範（引用）

`content/**` 所有 markdown 的排版與結構規範，以 `content/posts/markdown-writing-spec.md` 為單一真實來源。本章只保留給 agent 的最小提要：

- 工具鏈：`scripts/mdtools`（Go + goldmark AST）在 pre-commit 與 CI 強制執行。
- 核心規則摘要：
  - **標題**：正文禁止 H1（front matter `title` 已產生 H1）；siblings_only 重複偵測；標題尾禁標點（MD026）；禁用粗體當標題（MD036）。
  - **URL**：裸 URL 禁止；顯示文字若含 TLD 字樣（`.com` / `.org` / `.gov` / `.net` / `.io` / `.dev` / `.tw`），domain 必須與 href 一致（反釣魚）。
  - **表格**：aligned 風格，每欄補空白對齊（CJK 雙寬）；分隔線 `| --- |` 長度隨欄寬自動增減。`mdtools fmt --fix` 負責重新對齊。
  - **列表與代碼**：列表 / code block 前後空行；有序列表 `1./2./3.` 一致；code block 需語言標示。
  - **Front matter**：通用層 `title` + `date` 必填；卡片層加 `description` + `weight` 必填。
  - **卡片**：相對連結有效、卡片 orphan 偵測、卡片首段與概念位置段需含鄰卡連結（對應 `.codex/briefs/knowledge-cards.md` K4）。
- 完整規則、識別碼白名單、TLD 清單、執行時機、擴充流程：**讀 `content/posts/markdown-writing-spec.md`**。
- 規則與 `scripts/mdtools/internal/rules/` 實作必須保持同步。任一方修改時同步更新另一方與規範文章。
- 寫作時遇到 pre-commit 報錯：讀訊息修正，**不可用 `--no-verify` 繞過**。

---

## 9. Skill 撰寫規範（區別於文章）

`.claude/skills/` 跟 `content/` 是**兩個不同的 surface**、規則互斥。寫 skill 時不要套用文章規範、寫文章時不要套用 skill 規範。

### 定位差異

|            | `.claude/skills/`（skill）                    | `content/`（文章）                           |
| ---------- | --------------------------------------------- | -------------------------------------------- |
| **讀者**   | Claude runtime 直接呼叫                       | 人類讀者透過 Hugo                            |
| **目標**   | 跨專案 portable（複製整個目錄就能移到別專案） | 服務本 blog 的脈絡與累積                     |
| **可依賴** | 只依賴 skill 自身內容                         | 可引用 report / posts / 其他 section         |
| **格式**   | H1 + body、**無 Hugo frontmatter**            | 有 Hugo frontmatter（`title` / `date` 必填） |

### Skill 撰寫硬規則

1. **檔案結構**：H1 標題開頭、不寫 Hugo frontmatter（`title` / `date` / `weight` / `tags` 都不寫）。Anthropic Skill 格式由 H1 + body 構成、加 frontmatter 反而會讓 Claude runtime 解析錯。

2. **連結只能指向 skill 內部**：禁止連結到 `/report/...` `/posts/...` `content/...` — 跨專案後這些都是死鏈。引用同 skill 內其他檔案用相對路徑（`./xxx.md` 或 `references/xxx.md`）。

3. **引用 blog 抽象原則**：若 skill 要引用 `content/report/` 的原則卡、**把卡複製進該 skill 的 `references/principles/` 目錄**、不是寫外部連結。每個 skill 帶自己的 principles/、共用卡可重複存在於多個 skill。

4. **去專案化具體例子**：移除 `pagefind` / `hugo` / `this blog's search` 等 blog-specific 名詞、改成中性「該元件」「該模組」「某搜尋元件」。論證邏輯保留、具體 selector / 檔案路徑改通用形式。

5. **不用 blog 編號當 identifier**：原 report 的 `#42` `#58` `#85` 等編號是 blog-internal 排序、跨專案沒意義。內部引用用 slug。

### Skill 結構慣例

```text
.claude/skills/{skill}/
├── SKILL.md                  # 入口、三大支柱 + 觸發路由
└── references/
    ├── {scenario}.md         # 情境型 reference（協議 / 步驟 / 模板）
    └── principles/           # 支撐型原則卡（從 content/report/ 抽象出來）
        └── {slug}.md         # 每張卡開頭：H1 + 「角色 / 何時讀」起手段
```

Principles 卡的「角色 / 何時讀」起手段：

```markdown
> **角色**：本卡是 `{skill-name}` 的支撐型原則（principle）、被 {誰} 引用。
>
> **何時讀**：{觸發情境}。
```

### 同步到 `content/skills/`（可選）

若該 skill 要在 blog 上給人類讀者瀏覽（如 `compositional-writing`）、把 SKILL.md / references 複製一份到 `content/skills/{skill}/`、加 Hugo frontmatter（`title` / `date` / `description` / `tags`）。**兩份內容主體相同、只差 frontmatter**。

不是所有 skill 都需要 content/ 鏡像 — 只有對外公開的方法論才需要。內部協議型 skill（如 `requirement-protocol`、`frontend-with-playwright`）可以只存在於 `.claude/`。

### Skill 完稿檢查

- [ ] H1 開頭、沒有 Hugo frontmatter
- [ ] 沒有 `/report/` `/posts/` 等外部連結
- [ ] 跨檔連結都是同 skill 內相對路徑
- [ ] 沒有 blog-specific 名詞（pagefind / hugo / 具體檔名）
- [ ] 沒有 blog 編號（`#42`）當主要 identifier
- [ ] principles/ 卡有「角色 / 何時讀」起手段
- [ ] 整個 skill 目錄複製到別專案後仍能完整運作

### Pre-commit lint 豁免

`.claude/skills/` 路徑下的 .md 檔在 pre-commit 跳過 mdtools lint（lint 規則針對 Hugo content）— 這是設計、不是 bug。fmt 仍正常執行。

---

## 10. Content 資料夾分類流程

`content/` 下有四個內容資料夾、定位不同、不可混用。寫每一篇文章 / 卡片前先判斷該放哪。

### 10.1 四資料夾的定位

| 資料夾      | 定位                                          | 典型內容                                         | 結構模板                                               |
| ----------- | --------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| `posts/`    | blog 本身的規範 / 設計 / Hugo & Markdown 經驗 | mdtools 設計、Markdown 規範、Hugo / Mermaid 配置 | 教學或踩坑紀錄、自由結構                               |
| `work-log/` | 工作中遇到的工具 / 技術問題（不是 blog 本身） | git / Flutter / Gradle / Dart 等的具體 case      | 問題情境 → 範例 → 解法                                 |
| `record/`   | 方法論記錄（中性 frame、不一定有具體 case）   | 5W1H 自察、敏捷、acceptance criteria 等          | 不固定、視內容定                                       |
| `report/`   | 工程方法論的事後檢討（從 case 抽象出原則）    | 編號連續的卡片系統（#1-93+）                     | 結論 / 為什麼 / 反模式 / 修法 / 關係 / case / 判讀徵兆 |

**判斷流程**：

1. 議題是「blog 內部設定 / Hugo / Markdown / mdtools」？→ `posts/`
2. 議題是「我用某工具 / 技術遇到的事件性問題」？→ `work-log/`
3. 議題是「我整理的某個方法論 / 工作模式」？→ `record/`
4. 議題是「從某個 case 抽出可重用的工程原則」？→ `report/`

**容易誤判的邊界（實際踩過的坑）**：

| 誤判                            | 正確分類                                               |
| ------------------------------- | ------------------------------------------------------ |
| blog mermaid 配置放 `work-log/` | mermaid 是 blog 內部設定、屬 `posts/`                  |
| 寫作檢討放 `record/`            | 寫作 retrospective 是 case-driven 抽原則、屬 `report/` |
| git 操作技巧放 `record/`        | 是工作中遇到的具體 case、屬 `work-log/`                |

### 10.2 寫作前 due-diligence（強制）

寫新文章 / 卡片前、依資料夾跑對應檢查：

**寫 `report/` 卡片前**：

1. 讀 `content/report/_index.md` 場景路徑、確認議題沒被既有卡片涵蓋
2. 若議題跟既有卡片有重疊但角度不同、定位為「sibling」或「補某卡缺的維度」、不是新主題
3. 卡片用既有編號往後遞增（不可跳號）

**寫 `posts/` 文章前**：

1. 確認沒有既有 posts 在講同一主題
2. 若是補既有指南的特定議題、開頭引用既有指南建立 context

**寫 `work-log/` 文章前**：

1. 純技術事件、不需要 due-diligence（事件本身就是 unique）

**任何資料夾都檢查**：

frontmatter 的 `slug` 跟檔名對齊（見 `markdown-writing-spec.md` §6.5）。

### 10.3 寫作後的 retrospective 流程

寫一篇文章後若發生「來回修改 / 多次 review / 踩到非預期的坑」、進 retrospective：

1. **辨識議題層次**：是視覺 / 語意 / 邏輯哪一層的問題？（見 compositional-writing 的 multi-pass layer 維度）
2. **抽抽象原則**：問「下一個類似情境會怎麼踩同樣的坑」、有的話寫成 `report/` 卡片
3. **連結既有原則**：新卡片必須在「跟其他抽象層原則的關係」段、列至少 3 個現有 `report/` 卡片的關係
4. **更新規範**：若議題揭露既有規範缺失（例如本次 slug 議題揭露 `markdown-writing-spec.md` 漏 §6.5）、補規範
5. **更新 _index.md 場景路徑**：給未來遇到同類情境的讀者一條讀法路線

### 10.4 跨 surface 的內容處理

**Skill ↔ Content** 規則互斥（見 §9）— 但這次寫作 retrospective 揭露議題時、可能同時要動兩個 surface：

- Report 卡片是 content/、可以 cross-link 其他 report
- Skill reference 必須自包含、不能引用 content/
- 若議題該同時記在兩處、各寫一份、語境化在各 surface 內、**不互相引用**

例：本次「multi-pass review 的 layer 軸」：

- `content/report/visual-tool-error-layer-alignment.md` — case-driven、引用其他 report 卡
- `.claude/skills/compositional-writing/references/writing-articles.md` 的「層次意識」段 — 自包含、不提 report 卡編號

兩者主旨對應、但各自獨立、不交叉引用。

---

## 11. 跨 AI agent 設定（CLAUDE.md vs AGENTS.md）

本 repo 設計上同時支援 Claude Code 跟 Codex（以及其他遵循 AGENTS.md 標準的 agent）、但有預設工具：**目前以 Claude Code 為主**。

### 11.1 規則檔結構

| 檔案        | 角色                                  | 誰讀                                       |
| ----------- | ------------------------------------- | ------------------------------------------ |
| `AGENTS.md` | 寫作 / 工程規範的 SSoT                | Codex、Claude Code（透過引用）、其他 agent |
| `CLAUDE.md` | Claude Code 專屬行為 + 內嵌 AGENTS.md | Claude Code                                |

CLAUDE.md 第一行是 `@AGENTS.md` — Claude Code 會自動把 AGENTS.md 內容內嵌進來、所以 Claude Code 看到 = AGENTS.md 全部 + CLAUDE.md 補充。

`@<file>` 是 Claude Code 專屬語法、Codex 不會解析、但 Codex 直接讀 AGENTS.md、不需要 CLAUDE.md。

### 11.2 修改規則時的 SSoT 原則

- **共用規則**（資料夾分類、寫作流程、commit 規則）：寫在 AGENTS.md、不重複到 CLAUDE.md
- **Claude Code 專屬**（skill 自動觸發機制、`/skill-name` 調用）：寫在 CLAUDE.md
- **Codex 專屬**（如需）：寫在 AGENTS.md 標明 `[Codex only]`

避免 SSoT 違反：同一條規則只在一個檔案出現、另一檔透過 `@` 引用或不重複。

### 11.3 Skill 在兩工具的差異

| 項目       | Claude Code                                         | Codex                                                                      |
| ---------- | --------------------------------------------------- | -------------------------------------------------------------------------- |
| Skill 路徑 | `.claude/skills/<name>/`                            | `.agents/skills/<name>/`                                                   |
| 觸發機制   | description / trigger 自動匹配 + `/skill-name` 手動 | description 自動匹配（implicit invocation）+ `/skills` 手動                |
| Metadata   | SKILL.md frontmatter                                | SKILL.md frontmatter（接近 Anthropic 格式）+ optional `agents/openai.yaml` |

**目前狀態**：本 repo 只維護 `.claude/skills/`、未同步到 `.agents/skills/`。

**Codex 用戶若要使用本 repo 的 skill**、選一：

- **Symlink**（推薦）：`ln -s .claude/skills .agents/skills`、兩處共用
- **手動複製**：`cp -r .claude/skills .agents/skills`、兩處獨立維護

差異主要在 SKILL.md 的 frontmatter — Anthropic 格式 / Codex 格式接近但不完全相同、symlink 後可能要小調 frontmatter。

### 11.4 之後的方向

當需要正式支援 Codex 時、需評估：

1. 是否建立 `.agents/skills/` symlink、補對應 frontmatter
2. AGENTS.md 是否要加 Codex 特定段落（如 `agents/openai.yaml` 配置）
3. 文件流（doc-flow）對齊兩個 agent 的執行差異

目前不做、留作 follow-up（屬 [#72](/report/external-trigger-for-high-roi-work/) 結構性跳過議題、需要 trigger 才執行）。
