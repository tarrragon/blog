@AGENTS.md

---

# Claude Code 專屬補充

上方 `@AGENTS.md` 由 Claude Code 自動內嵌、AGENTS.md 是寫作 / 工程規範的 SSoT。本檔只放 **Claude Code 專屬行為**、不重複 AGENTS.md 內容。

## Skill 自動觸發

Claude Code 會根據對話內容自動觸發 `.claude/skills/` 內的 skill — 看 `SKILL.md` 開頭的 `description` / `trigger` 字串匹配當前任務。常用觸發詞：

| Skill                      | 觸發情境                                                   |
| -------------------------- | ---------------------------------------------------------- |
| `compositional-writing`    | 寫文章 / 卡片 / 註解 / 文件 / prompt 時                    |
| `requirement-protocol`     | 模糊指令、反覆失敗、覆寫成本、確認嗎 / OK 嗎 / yes-no 二選 |
| `frontend-with-playwright` | 前端 CSS / DOM / framework 共處 / Playwright 驗證 / a11y   |
| `wrap-decision`            | 分析 / 決策 / 比較 / 提案、被困住、根因分析、個人化建議    |
| `blogsearch-lifecycle`     | blogsearch rebuild、語意搜尋、content 變動後 index 過時    |
| `knowledge-cards`          | 建卡 / 缺卡判定 / 卡片 audit / 回填連結 / 卡片目錄重構     |

手動調用：對話中打 `/<skill-name>` 強制啟動。

skill 內容看 `.claude/skills/<name>/SKILL.md`。

### 寫作類 skill 主動 invoke，不等自動觸發

自動觸發靠 `description` 去匹配當前對話的措辭，而寫作任務多數不是用「寫文章」這種話進來的——「幫我改這段」「補一句」「這裡讀起來怪怪的」「順一下」都是寫作任務，而它們一個字都匹配不到。任務越小越不會觸發，但小改動累積出來的字句層違規跟整篇一樣多。

所以動到 `content/` 或 `.claude/skills/` 的任何一段文字之前，主動 invoke `compositional-writing`；改完之後照 AGENTS.md §5 步驟 4 跑一次它的字句層 bank，並把逐類表寫進回覆。

逐類表的欄位、零命中要不要列、以及為什麼這張表是必要的，都在 AGENTS.md §5 的關鍵硬性規則段，這裡不重複。

## Skill ↔ Content 互斥

寫作時要清楚目前在哪個 surface：

| Surface           | 規則檔                                                                       | 自包含？          |
| ----------------- | ---------------------------------------------------------------------------- | ----------------- |
| `.claude/skills/` | `compositional-writing/references/reference-authoring-standards.md`          | 是、不引用 blog   |
| `content/`        | `content/posts/markdown-writing-spec.md`（Hugo 規範）+ AGENTS.md（內容規範） | 否、可 cross-link |

跨 surface 的引用會違反規範 — 寫 skill 時複製 principle 卡進 `references/principles/`、不寫外部連結（AGENTS.md §9.2-3）。

## Hugo `_index.md` vs 文章檔案

`content/` 下的 `_index.md` 是 Hugo 的 **section list page**（模組目錄頁），不是放文章內容的地方。文章內容必須是同目錄下的獨立 `.md` 檔案。

| 檔案類型    | 用途                                                                                       | 內容量    |
| ----------- | ------------------------------------------------------------------------------------------ | --------- |
| `_index.md` | 模組目錄頁：frontmatter + 簡介（1-3 段）+ 章節文章表格 + 跨分類引用                        | 20-90 行  |
| `<slug>.md` | 獨立文章：完整教學內容，有自己的 frontmatter（title / date / description / weight / tags） | 50-300 行 |

新建教學模組時，先建 `_index.md` 寫模組簡介和文章表格，再建各篇獨立文章。**不要把文章內容寫進 `_index.md`**——Hugo 會把它渲染成 list page，文章內容不會以正確的單篇頁面呈現。

參考既有模組的結構：`content/infra/00-infra-mindset/`（`_index.md` + 3 篇獨立文章）。

## 文章寫作避免模板化

Claude Code 寫 `content/` 文章時，不要為了整齊而把案例、反例、規模對照或 tripwire 抽成共通模板。不同情境的業務壓力、資料形狀、流量型態、失敗條件與回退路徑若不同，必須用該情境自己的敘事說明與判讀條件。

表格只能輔助整理，不可取代情境判讀。若欄位化後讓內容變得僵硬、抽象或遺失細節，應改回段落式說明。

## 教學模組寫作流程

寫跨多章節的教學模組時（例：backend/01 資料庫模組 12 章）、走 [Case-First + Agent Team Review 標準流程](/posts/case-first-agent-team-review-workflow/)、不要直接用 LLM 自生內容塞章節。

完整方法論看該文章、Claude Code 執行重點：

1. **完整讀 case 庫抽 findings**：用 Read tool 完整讀目標 case（不只 frontmatter）、邊讀邊抽 findings 跟章節對應、邊際遞減訊號出現就停止 audit
2. **內容生成**：寫稿時案例引用要回 case 原文驗證、避免把通用 best practice 包裝成「[case] 揭露」
3. **Agent team review**：用 Agent tool spawn 3 個 `general-purpose` reviewer、各自指定不同維度（寫作規範 / 案例準確性 / 跨章一致性）、`run_in_background: true` 平行跑、主 context 只看彙整報告

**為什麼 background**：reviewer 要讀完整 commit + 案例 + 章節、自身 context 會被佔滿；用 background 把 reviewer context 跟主 context 分開、主 context 只接收精煉摘要、節省 ~80% context。

**何時用**：跨 5+ 章節模組 + 有 case 庫 + 品質高於速度。詳細適用 / 不適用條件見 AGENTS.md §5「教學模組級流程」段。

**多輪審查硬底線**：寫完章節後跑 `multi-round-review` skill 時，至少跑三輪、不問「要不要繼續」。Round 3 的 steelman / outbound frame 每次實測都找出 10+ 項 Round 1-2 結構性盲區（漏選項、反向引用、搜尋落點、知識卡缺口）。「還要不要再跑一輪」這個問題，等 Round 3 跑完才輪到主 session 判斷；在那之前它不是判讀題、是執行紀律。詳見 [#202](/report/multi-round-review-minimum-three-rounds/)。

### 低階 model 讀者探針的派發方式

規範層（何時跑、五個設計條件、歸因與處置、不可信的三個維度）在 AGENTS.md §5 的「理解取樣：低階 model 讀者探針」段，這裡只記 Claude Code 的操作面。

探針與上一段的 agent team reviewer 是兩種不同的派發，別套用同一組參數：reviewer 是 `general-purpose`、各自審不同維度、要的是判斷力；探針是 Haiku、每一份的指令完全一樣、要的是理解的樣本。

用 `Agent` tool 派發、`model: "haiku"`、`run_in_background: true`。

**一批的定義是「報告會被放在一起比對的那幾份」**：同一批之內，`prompt` 與餵給它的內容範圍都要逐字相同——複製同一個字串貼進每次呼叫，不要逐個微調措辭，否則回報的差異無法歸因到模型的理解，第一個設計條件當場失效。換問法（理解正確性換成閱讀負擔）或換讀的範圍就是另一批，兩批之間不比對。

**prompt 必須含送達方式**，兩句缺一不可：

```text
完成後必須呼叫 SendMessage 把報告送到 `main`。
只把報告寫在自己的回覆裡不算交付，主 session 讀不到。
```

實測漏掉這兩句是 0/9 自行交件、寫了是 9/9，Haiku 也照做——這是指令有沒有寫的問題、不是模型能力問題。細節見 memory 的 `reviewer-agents-need-sendmessage-pull`。

**術語探針的派發，第一步是查測試詞在不在探針自己的系統提示裡。** subagent 會繼承本檔與 AGENTS.md，而值得量的詞多半就寫在那兩份裡面——量到的會是詞頻不是語域，且兩者同向（本檔詞頻 3 的詞五份全數有把握並給出本站自己的定義，詞頻 0 的五份全數沒把握）。列一次詞頻，命中的換到沒有專案規範檔的目錄下派、或**同向的那幾個直接記成「本批無結論」**——`Agent` 沒有換工作目錄的參數，subagent 一律繼承本檔與 AGENTS.md，所以「換一個乾淨的配置重測」目前沒有跑通過的做法，別把它當成可執行的補救，否則唯一可執行的分支會變成豁免。詞頻全部是零的時候這個檢查是恆真的（規範檔沒涵蓋那個領域），通過不代表乾淨。逆向的命中（提示裡有而探針仍回報沒把握）可以直接採信。

同批另放一個**安慰劑詞**，四個條件缺一就給假訊號：**與測試詞同域**（跨域的詞回報「沒見過」是因為領域不符，假陰性）、只在規範檔出現、語意不可由組成推出（可拆解的詞探針靠拆解就答得出來，假陽性）、詞頻與測試詞同量級。實測合格的安慰劑詞三份全數有把握並複述規範檔原文，所以這一項確實有效；但本檔涵蓋的是寫作方法論，替 `content/business/` 這類分類撈不到同域的安慰劑詞，那時報告上記「本批無污染對照」。通用性控制詞對這一種無感，因為通用詞讀不讀得到提示都收斂。見 [#309](/report/probe-reads-the-prompt-that-defines-the-term/)。

**第二步是控制詞。** 受測單位是一個詞而不是一段文字時（懷疑某個高頻用詞在目標語域沒有穩定所指、或某個譬喻太口語），prompt 要同時列出測試詞與**至少兩個已知通用的術語**，混在同一份清單裡、不標示哪個是控制，問法是「這幾個詞在<領域>裡各指什麼；沒把握或沒見過就直接寫沒見過，不要推測」。控制詞收斂才代表這批的分歧可歸因到詞本身，控制詞也分歧就整批作廢——少了這一步，「全部答不出來」與「這批模型不行」在報告上長得一樣。prompt 另外要求「有把握的那些，寫出它指的東西」——少了這一句，回報會退化成一張把握度清單，而同域佔用的證據全在定義的內容裡。回報分四類讀，收斂度只分得出前三類（收斂＝通用、各給不同定義而都有把握＝一名多義、全部沒見過＝非通用）；第四類是少數份有把握而它們一致指向另一個所指，代表這個詞在同一個領域已經有主人，它在收斂度上與非通用詞同區而處置嚴格得多——非通用可以就地定義後留用，同域佔用只能換掉，且要換成描述不是同義詞（見 [#307](/report/term-already-owned-inside-the-domain/)）。而**非通用不等於自創**：先查這個詞在別的領域有沒有穩定用法，有就是語域錯配。判定之後的替換要先列詞形分佈再按義項走，程序見 [#289](/report/term-probe-measures-register-not-invention/)。

prompt 的其餘要求：回報格式逐項列出（節名或行號 / 這一節讀到什麼 / 這個動作誰做 / 指涉詞各指誰 / 讀完之後第一個動作是什麼），並明令「文章沒說就寫『文章沒說』，不要推測填補」。另外要它單獨開一段列出「有兩種以上讀法的位置」，逐條寫原文與各種讀法——那一段是這個 frame 產出價值最高的部分。

主 context 只接收彙整。每份報告讀進來之後先做歸因——在原文 grep 那個讀法對應的字串——再進處置，順序顛倒會把作者自己寫的矛盾誤判成讀者誤讀。

## Content 路徑大小寫

`content/` 的資料夾與對外 route 一律使用小寫（例如 `content/ci` ↔ `/ci/`）。在 macOS 本機大小寫錯誤可能不會浮現，但 Linux CI 會把 `content/CI` 與 `/ci/` 視為不同路徑，造成 `mdtools cards` 大量 broken link。

提交前最少做一次：

```bash
./bin/mdtools cards content/
```

若要快速掃描 repo 是否殘留大寫內容路徑：

```bash
git ls-tree -r --name-only HEAD | rg '^content/[A-Z]'
```

### Portable pass

Claude Code 修改 `.claude/skills/` 時要把 skill 當成「可搬到空白專案的獨立目錄」。允許依賴同 skill 內的相對檔案；需要 report / posts 的抽象原則時，先抽成 `references/principles/<slug>.md`，再用相對連結引用。

提交前掃描 portable 風險：

```bash
rg -n "\\]\\((/|content/|\\.\\./\\.\\./)|(/report/|/posts/|/skills/|content/report|content/posts|content/skills|_index\\.md)" .claude/skills/<name>
```

掃到 blog route、`content/` path、`/report/`、`/posts/`、`/skills/`、Hugo-only `_index.md` 時，改成 skill 內部 principle、相對連結或中性名詞（collection index / MOC / article / reference）。

## Content 排序與 mdtools 作用域

Hugo 的列表排序是 weight 遞增、**未設 weight 的頁面排在全部有 weight 的頁面之後**、同 weight 才用日期遞減。這條語意衍生出幾個操作規則（背景見 [#221](/report/lint-scope-must-be-explicit-fact/)）：

- **weight 全有或全無**：同一 section 混用會讓缺 weight 的頁面靜默沉到列表底部。`mdtools cards` 的 `L5-section-weight-consistency` 會對混合 section 警告。刻意用低 weight 置頂單篇的 section（如 `content/linux/tools/cli`）在 `scripts/mdtools/internal/rules/config.go` 的 `WeightExemptSections` 登記 — 豁免要有記錄、不能是沒人決定過的遺漏。
- **後補文章的 weight 要放「屬於它的位置」**：值要落在該 section 既有編號帶之內、順序對得上這篇在模組裡的位置。只確認沒跟別人重號就填上去是不夠的，重號與否跟排序對不對是兩件事。實例：`07-security` 的 7.27 曾被給 27（其餘章節 72-95）而排到整個模組第一篇、`postgresql` 的 pgbouncer-config 曾被給 100 而沉到最後。L5 只查全有全無、對「有 weight 但值錯」沉默 — 補號前先看該 section 的既有編號帶（postgresql 有預留空號、mysql 是連續序）。
- **新增卡片型目錄**（必填 `title` / `date` / `description` / `weight` 的）時在 `scripts/mdtools/internal/rules/config.go` 的 `FrontMatter.CardPaths` 登記（跟上面那條的 `WeightExemptSections` 同一個檔），否則卡片層 frontmatter 檢查永遠不涵蓋它、缺欄位不會被攔。規則存在不等於規則涵蓋、未納管目錄的零 error 跟合規目錄的零 error 訊號相同。
- **frontmatter 的 date 是台北時間**：`hugo.toml` 已設 `timeZone = 'Asia/Taipei'`。拿掉這行的話、UTC 的 CI 在台北 00:00-08:00 之間 build 會把當日日期的文章判成未來文章而排除。

### 改 mdtools 的守則

- `go test ./...` 必跑、CI 的 md-check 也會跑（Test step 在 lint / cards 之前）。新增檢查邏輯要附測試、並用突變驗證測試不是恆真（改壞實作、確認對應 case 失敗）。
- **跨檔規則放 `mdcards`、不放 `mdlint`**：pre-commit 只餵 staged 檔給 lint、跨檔規則在那裡會把「其他檔沒被 staged」誤判成違規。`cards` 是 whole-content scan。
- **fmt 規則必須冪等**（`fmt(fmt(x)) == fmt(x)`）：CI 的 `fmt --fix` 會 auto-commit、非冪等規則會讓 bot 每次 push 都產生新 diff。`internal/mdfmt/fixer_test.go` 的 `TestApplyAllIdempotent` 守著這條、新 fmt 規則要加 fixture 進去。
- 測試 fixture 不要用 map 迭代建圖（Go map 順序隨機、會做出碰巧通過的測試）、依賴走訪順序的行為要有正序 / 逆序各餵一次的測試。

## Skill 庫同步

本專案的 `.claude/skills/` 與遠端 skill 庫 `https://github.com/tarrragon/claude-skills.git` 共用同一組 skill。使用 `skill-sync` CLI 工具同步（透過 `uv tool` 安裝在 `~/.local/bin/skill-sync`）。

### skill-sync 指令

```bash
# 列出遠端所有 skill
skill-sync list

# 批次更新已安裝的 skill（比對 versions.json，只更新有差異者）
skill-sync pull

# 拉取指定 skill（新安裝或強制更新）
skill-sync pull <skill-name>

# 本地 → 遠端（修改 skill 後推送，自動更新 versions.json）
skill-sync push <skill-name> -m "commit message"
```

### 版號規則（強制）

修改 skill 內容後必須更新 SKILL.md 末尾的版本號，格式為 `**Version**: X.Y.Z — 變更摘要`。版號遵循 semver：

- **patch**（0.1.0 → 0.1.1）：修錯字、補連結、格式調整
- **minor**（0.1.0 → 0.2.0）：新增 reference / principle 卡、擴充段落、加觸發詞
- **major**（0.X → 1.0.0）：結構重組、支柱變動、破壞既有行為

未標版號的 skill 首次補標用 `1.0.0`。變更摘要簡述改了什麼，參考 compositional-writing 的版本紀錄格式。

**版號有兩個住址，兩個都要改**：文末的 `**Version**:` 版本紀錄，以及 SKILL.md frontmatter 的 `metadata.version`。只改文末是高頻漏失——`bin/skill-mirror` 會擋下不一致，但它只跑在有 `content/skills/` 鏡像的 skill 上，沒有鏡像的 skill 漂多久都不會有人發現。一次全庫掃描的結果：三個 skill 的 frontmatter 分別落後一到四個版本，三個都沒有鏡像。

改完用這條掃全庫，兩個住址對不上的會列出來：

```bash
for f in .claude/skills/*/SKILL.md; do
  n=$(basename $(dirname $f))
  fm=$(sed -n '/^  version:/{s/^  version: *//;s/"//g;p;q;}' "$f")
  cl=$(grep -oE '[0-9]+\.[0-9]+\.[0-9]+' "$f" | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)
  if [ -n "$fm" ] && [ "$fm" != "$cl" ]; then echo "DRIFT $n frontmatter=$fm changelog=$cl"; fi
done
```

推導值取的是「檔案裡最大的版本號」，所以引用了別的 skill 裸版號的 changelog 會給假陽性。命中之後先看該檔的 `**Version**:` 清單確認那個號碼真的是版本紀錄，再改 frontmatter。

### 標準操作流程

流程從 report 卡開始，不從 skill 修改開始。report 是原則的 SSoT（有情境、根因、理想做法），skill 是 report 的操作化引用。先有 report 才有 skill 引用的依據。

1. **建 report 卡**：在 `content/report/` 建卡，更新 `_index.md` 篇目索引
2. **評估是否進 skill、以及進多少**：先問這一條進了 skill 之後 agent 的動作會不會不同——不會就留在卡裡。會的話只搬可執行的那一半（判斷標準、觸發條件、處置），推導、實例與「為什麼既有審查抓不到」留在卡上，skill 用一句話帶過並連回去。**report 不是 skill 的草稿，兩者的責任不同**：卡歸納問題與解法，skill 給處理方式與判斷方法。驗收問一句——一個沒讀過那張卡的 agent，照 skill 這一段做得出動作嗎；做得出就夠了，多的是說明。
   搬多了的代價是 skill 膨脹到沒有人讀得完，而膨脹不可逆，因為每一段單獨看都有道理。決定要進的時候順便決定它擠掉誰的注意力
3. **修改 skill**：在 `.claude/skills/<name>/` 修改 SKILL.md，引用 report 卡的路徑（`.claude/` 用 `references/principles/` 相對連結、`content/` 鏡像會自動轉成 `/report/` 路徑）
4. **如果新增 principle 卡**：在 `references/principles/` 建卡，並在 `bin/skill-mirror` 的 mapping table 加上 principle slug → report slug 的對應
5. **更新版本號**：SKILL.md 末尾加版本號（見上方版號規則）
6. **commit 到 blog repo**
7. **推送到 skill repo**：`skill-sync push <name> -m "描述" --force`
8. **同步鏡像**：`bin/skill-mirror <name>`（自動處理 Hugo frontmatter、H1→H2、連結轉換、fmt）
9. **commit 鏡像**：`git add content/skills/<name>/skill.md && git commit`
10. **push**

步驟 9 若被 pre-commit 的 `cards` 擋下，最可能的成因是步驟 4 漏了——mapping table 沒有對應的 principle slug，鏡像因此留著 `references/principles/` 相對連結而在 `content/` 下解析不到。`bin/skill-mirror` 對這種情形只印 `WARN: N unresolved` 而不中止，所以真正攔下它的是 `cards`。回頭補 mapping、重跑步驟 8。

簡化版（步驟 6-10）：

```bash
git add .claude/skills/<name>/ content/report/ && git commit
skill-sync push <name> -m "vX.Y.Z: 描述" --force
bin/skill-mirror <name>
git add content/skills/<name>/skill.md && git commit
git push
```

批量推送多個 skill 時逐一執行 `skill-sync push`，不要嘗試手動 clone 遠端 repo 操作。

### 改既有 report 卡時要查鏡像

上面的流程管的是新卡建立，改**既有**卡時另有一個缺口：卡的內容可能已經被抄成 skill 的 principle 卡，改了 report 側而沒改 skill 側，共用庫裡就留著一份已被推翻的規則，而下游專案 pull 到的是舊版。

發現方式不能靠記憶，也不能用任何單一個名字去掃。副本與本體的對應在本庫有四種形態，每一種只有一個鍵抓得到：檔名相同、去專案化時改過標題（H1 相同）、兩者都改過（靠 `bin/skill-mirror` 的 mapping table）、只在正文引用（內容掃描）。四個鍵合起來才是完整的射程，所以這件事交給腳本：

```bash
scripts/principle-mirror-check.py <report-或-record-卡的-slug>   # 查一張，落後的會標出來
scripts/principle-mirror-check.py --all                          # 全庫掃，列出本體較新的那些
```

**這支腳本取代了先前那段手寫的 `rg` + `find` 程序，而取代的理由要記住。** 那段程序先只用卡自己的 slug，後來補了 mapping table 反查，兩個版本都會對真正分岔的副本回報零命中——實測 `multi-round-review-minimum-three-rounds` 在兩個版本下都是零行，而 `.claude/skills/multi-round-review/references/principles/minimum-three-rounds.md` 就在那裡、H1 與 report 卡的 title 逐字相同、本體新兩個月。成因是 mapping table 的涵蓋率由「這個 skill 有沒有 `content/skills/` 鏡像」決定（`skill-mirror` 只在有鏡像的 skill 上跑），而查副本的需求由「這張卡有沒有任何副本」決定，兩個作用域不同：150 張 principle 卡裡有 36 張既非同名也不在 mapping 表裡。

驗收案例固定四個，改動腳本之後逐個跑過再提交——**其中兩個的正確輸出都是零行以外的東西，所以「跑起來沒報錯」不算通過**：

| slug                                      | 該有的結果                                          |
| ----------------------------------------- | --------------------------------------------------- |
| `multi-round-review-minimum-three-rounds` | 靠 H1 抓到 `minimum-three-rounds.md`，並標為落後    |
| `teaching-article-context-method`         | 靠 mapping table 抓到 `teaching-article-context.md` |
| `basics-anchor-the-advanced`              | 靠同名抓到                                          |
| `description-frames-the-article`          | 副本 0 份（真陰性）                                 |

`--all` 目前回報 74 張卡的 skill 側副本落後於本體。這個數字是存量不是本批造成的，處置是逐張判斷該不該同步，不是一次全改。

量測指令：

```bash
for f in $(find .claude/skills -path '*/principles/*.md'); do
  slug=$(basename "$f" .md); grep -q "$slug" "$f" && echo "$slug"
done | wc -l
```

同步時連段標一起對齊：同一個結構單位在兩份鏡像裡要用同一組 canonical 字串，否則之後靠 anchor 比對的自動化與人工檢查都會錯位。

### 同步判斷原則

- 版本號相同但檔案有差異 → 本地是客製版，以本地為準推回遠端。
- 遠端版本較新 → diff 審查後決定是否合併（`skill-sync pull` + 本地比對）。
- 本地版本較高 → 不覆蓋，本地為準。
- 遠端有新增檔案（原則卡、hooks）→ `skill-sync pull` 取用到本地，再推合併版回遠端。

### 注意事項

- 本專案 AGENTS.md 禁 emoji（§8），遠端若加了 emoji 是倒退、要修正推回。
- Skill 內連結必須是相對路徑（portable 原則），遠端若改成絕對路徑要修正推回。
- 同步完本地 `.claude/skills/` 後，有 `content/skills/` 鏡像的 skill 要同步更新鏡像（pre-commit hook 會提醒）。

## 遠端機器操作標準（dotfiles-driven，不 ad-hoc SSH）

在 VM 或任何「我們管理的」遠端機器上做實機驗證 / 部署時，狀態改動一律走 dotfiles repo + git 同步，**不透過 SSH 手動放置持久性檔案或設定**。這條規則跟本 blog 教的 dotfile / bootstrap / infra-as-code 哲學一致：機器的狀態必須永遠能從 repo 重現，手放的東西下次重裝就消失、也沒人記得。

### 硬規則

- **SSH 只用來做唯讀診斷與觸發**：`hyprctl` / `systemctl status` / 讀 log / `pgrep` / 跑 repo 內的部署腳本這類，可以。
- **任何該持久存在的東西**（腳本、systemd unit、設定檔、cron、drop-in）→ 先寫進 [dotfiles repo](https://github.com/tarrragon/dotfiles)、commit/push，再由遠端 `git pull` + 冪等 deploy 部署。**不 scp、不 heredoc 寫進 /tmp、不手動 `tee` 到 /etc。**
- **一次性驗證用的暫時檔**（測試 service、探測腳本）可以臨時放，但測完必須清掉、且正式版要回收進 repo。

### SSH 權限與本機逃逸攔截（ssh_guard hook）

本專案是教學 / 實驗用途、`.claude/settings.local.json` 刻意放寬到 `Bash(ssh *)`、讓 agent 對受管遠端機器做唯讀診斷不必逐次核准。這個決定的前提是「遠端環境掛了重建就好」。

但 `ssh *` 的語意涵蓋一個跟遠端無關的暴露面：ssh 的 `-o ProxyCommand=…` 與 `-o LocalCommand=…`（配 `PermitLocalCommand=yes`）會在**本機這台開發機**執行任意命令、等於繞過 sandbox。這條路徑不受「遠端可重建」保護、因此用一個 PreToolUse hook 攔下。

- **機制**：`.claude/hooks/ssh_guard.py` 註冊為 `Bash` 的 PreToolUse hook。一條指令同時「呼叫 ssh」且「帶 ProxyCommand / LocalCommand / PermitLocalCommand」時回 `permissionDecision: deny`；純遠端唯讀診斷（`ssh <host> <readonly-cmd>`）照常放行。
- **邊界**：只比對指令字串本身。ProxyCommand 若寫在 `~/.ssh/config` 而非命令列則看不到；防的是誤用 / 意外、不是防主動繞過的對手。以「agent 非敵人、只是別讓它不小心動到本機」的威脅模型足夠。
- **已知副作用**：任何 Bash 指令的文字裡只要同時出現 ssh 呼叫 + 這些選項就會被擋（例如 `echo 'ssh -o ProxyCommand=…'` 這種示範字串）。要在指令裡引用這些字串時改用 Write / Edit 寫檔、不要塞進 Bash。
- **維護**：改動危險選項清單改 `LOCAL_EXEC_OPTS` regex；改 ssh 呼叫辨識改 `SSH_INVOCATION`。改完用 payload 檔餵 stdin 驗證（deny 案例別直接寫進測試指令、否則 hook 會擋住測試指令本身）。

### 可複用工具（在 dotfiles repo）

| 工具                                         | 作用                                                                                                                                  |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/remote-sync.sh <host> [deploy-cmd]` | 管遠端機器的標準入口：本地 commit/push → 遠端 `git pull --ff-only` → 遠端跑冪等 deploy。本地有未提交變更就擋下（逼你走 repo，不繞過） |
| `scripts/install.sh`                         | bootstrap：套件 → stow 部署 → zsh → Claude Code（家目錄層，冪等）                                                                     |
| `<pkg>/deploy.sh`                            | 系統層（`/etc`、`/usr/local`）的部署橋，stow 管不到的用這個（如 `monitoring/deploy.sh`）                                              |

標準流程：

```bash
# 本地改 → commit/push → 一鍵同步部署到遠端
scripts/remote-sync.sh arch-vm                          # 跑完整 install.sh
scripts/remote-sync.sh arch-vm 'sudo ./monitoring/deploy.sh'   # 只部署某個系統層套件
```

遠端在 feature 分支、無法 ff 時，正解是**在 repo 端把分支收斂**：本地 checkout 該分支、`git merge main`、解衝突、push，VM 再 `git pull --ff-only`。衝突在 repo 裡用正常編輯解、不在 VM 上 SSH 解。**不要用 `git checkout <ref> -- <paths>` 把檔塞進工作區**——它會把那些路徑 staged 進 index，下次 ff-pull 就被「index 有未提交變更」擋住（本次實測踩過、清理花了額外功夫）。stow 過的設定檔改內容不需重新 stow，symlink 會自動反映。

### 家目錄 vs 系統層

- **家目錄檔**（`~/.config/...`、`~/.local/bin/...`）→ 做成 stow 套件、`install.sh` 部署。
- **系統檔**（`/etc/systemd/system/...`、`/usr/local/bin/...`，root-owned、stow 管不到）→ 套件內附 `deploy.sh`，在目標機 `sudo` 跑，冪等安裝。
- **私密值**（ntfy topic、healthcheck UUID、token）→ **不進 git**，repo 只放 `.example` 佔位，deploy 只在目標不存在時建佔位、真值手填或走 gitignore 的本地檔。
- **app 自己管理（atomic-write）的 config**（如 caelestia `shell.json`：程式會把 stow symlink 換成實檔、`stow --adopt` 還會把它改寫過的內容 clobber 回 repo）→ **不 stow，改 copy 部署**：套件內附 `deploy.sh` 以一般使用者 `cp` repo 版蓋過 live 檔、從 stow_pkgs 移除該套件。**repo 為唯一真實來源**——持久設定改 repo + 部署，**不要用該 app 的 GUI 改**（會寫進 live 檔、下次部署被覆蓋）。判斷訊號：部署後該檔從 symlink 變實檔、或內容被程式重排。

## 跟 Codex / 其他 agent 的差異

本 repo 同時支援 Claude Code 跟 Codex。差異點：

- **規範**：CLAUDE.md 跟 AGENTS.md 共用內容（透過 `@AGENTS.md`）、Codex 直接讀 AGENTS.md
- **Skill**：路徑不同（Claude Code 用 `.claude/skills/`、Codex 用 `.agents/skills/`）— 本 repo 用 directory symlink 共用（`.agents/skills` → `../.claude/skills`）、改 `.claude/skills/<name>/` 兩工具同步生效
- 詳見 AGENTS.md §11
