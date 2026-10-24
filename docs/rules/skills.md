# Skill 的撰寫與同步

這份分冊管 skill 與文章的分界、skill 的依賴邊界與撰寫規則、版號、skill-sync 在本 repo 加的規則、從 report 卡到 skill 的流程、推送前的檢查與同步時的判斷、只留在本 repo 的 skill、Claude Code 與 Codex 共用的 skill 目錄，以及改 report 卡時查 skill 裡的副本。skill-sync 工具本身的指令與分類以 `.claude/skills/skill-sync/SKILL.md` 為準。

## Skill 的撰寫與同步

### Skill 與文章是兩個 surface

`.claude/skills/` 與 `content/` 在體例、格式與依賴上的規則互斥：寫 skill 時不套教學體例、Hugo frontmatter 與 mdtools lint，寫文章時不套操作手冊的體例與 skill 的可攜性限制。兩邊的讀者見`writing.md`〈三種書面產出的體例〉。句子層的規則兩邊共用：`sentences.md`〈句子與命名〉底下各節、`sentences.md`〈譯名避開介面上已有的同名元素〉、`writing.md`〈推導過重時拆篇，不壓縮成一句話的結論〉。

|        | `.claude/skills/`（skill）                                                                          | `content/`（文章）                       |
| ------ | --------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| 載入者 | agent runtime（Claude Code、Codex）直接載入                                                         | 人類讀者經由 Hugo                        |
| 目標   | 可攜：整個目錄複製到別的專案就能運作                                                                | 服務本 blog 的脈絡與累積                 |
| 可依賴 | 只依賴 skill 自身的內容與穩定的公開來源                                                             | 可引用 report、posts 與其他 section      |
| 格式   | SKILL.md 以 YAML frontmatter（`name`、`description`、`metadata`）開頭，接 H1 與正文；不放 Hugo 欄位 | Hugo frontmatter（`title`、`date` 必填） |

`content/skills/<name>/` 是 skill 的公開鏡像，給網站讀者讀，只有對外公開的方法論需要；內部協議型的 skill 只存在於 `.claude/skills/`。鏡像與源檔的正文相同，差在鏡像帶 Hugo frontmatter，由 `bin/skill-mirror` 產生（見〈從 report 卡到 skill 的標準流程〉）。替一支 skill 建鏡像要使用者在這次的指示裡明說（`AGENTS.md`〈要先問使用者的情形〉）。

### Skill 的依賴邊界

`.claude/skills/<name>/` 是可以複製到其他專案獨立運作的單位。寫 skill 時，預設目標專案沒有本 blog 的 `content/`、`report/`、`posts/`、Hugo route、內部 slug 或 `_index.md` 結構。

| 依賴類型                                               | 在 `.claude/skills/` 的處理                                                                                |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| 同一個 skill 內的 reference                            | 相對連結：`./x.md`、`references/x.md`、`principles/x.md`                                                   |
| blog 的 report 或 posts 原則卡                         | 複製進該 skill 的 `references/principles/`，抽象成 skill 內部的 principle；共用卡可以在多個 skill 各有一份 |
| blog 內部 route 或 content 路徑                        | 改成中性名詞：collection index、MOC、article、reference                                                    |
| `content/skills/<name>/` 公開鏡像                      | 下游 mirror，不當依賴來源                                                                                  |
| 穩定的外部規格或公開來源（公開 GitHub repo、官方文件） | 可以引用，段內保留足夠的脈絡，讓讀者不必開外部頁也讀得懂                                                   |

### Skill 的撰寫規則

- **SKILL.md 的 frontmatter** 只放 skill 規格的欄位（`name`、`description`、`metadata`，`metadata.version` 是版號的住址之一），不放 Hugo 欄位（`title`、`date`、`weight`、`tags`）。Hugo 欄位只出現在 `content/skills/` 的鏡像。
- **skill 裡連到其他知識的連結指向 skill 內部**：不連 `/report/...`、`/posts/...`、`content/...`，搬到別的專案之後這些都是死鏈。
- **去專案化具體例子**：`pagefind`、`hugo`、本 blog 的搜尋這類名詞改成中性的「該元件」「該模組」；論證保留，具體 selector 與檔案路徑改成通用形式。
- **不用 blog 的編號當識別碼**：`#42`、`#58` 是 blog 內部的排序，跨專案沒有意義；內部引用用 slug。
- **principle 卡的開頭**寫「角色 / 何時讀」：

```markdown
> **角色**：本卡是 `{skill-name}` 的支撐型原則（principle）、被 {誰} 引用。
>
> **何時讀**：{觸發情境}。
```

目錄慣例：

```text
.claude/skills/{skill}/
├── SKILL.md                  # 入口、核心支柱與觸發路由
├── CHANGELOG.md              # 版本紀錄（新到舊）
└── references/
    ├── {scenario}.md         # 情境型 reference（協議、步驟、模板）
    └── principles/
        └── {slug}.md         # 支撐型原則卡
```

完稿檢查：

- SKILL.md 以 YAML frontmatter 開頭，沒有 Hugo 欄位
- 沒有 `/report/`、`/posts/` 等站內連結，沒有 `content/`、blog route、`_index.md` 依賴
- 跨檔連結都是同 skill 內的相對路徑
- 沒有 blog 專屬的名詞與編號識別碼
- principle 卡有「角色 / 何時讀」開頭
- 整個 skill 目錄複製到別的專案後仍能完整運作

可攜性掃描：

```bash
rg -n "\\]\\((/|content/|\\.\\./\\.\\./)|(/report/|/posts/|/skills/|content/report|content/posts|content/skills|_index\\.md)" -g '*.md' .claude/skills/<name>
```

這條 rg 掃的是 `.md` 檔裡本 blog 專屬的路徑；`-g '*.md'` 把腳本排除在外，因為腳本裡的 pattern 與註解本來就要寫出這些路徑（`compositional-writing` 的 `scripts/portability-check.sh` 就是），照下面的處置改會改壞腳本。命中是候選：帶 `portability-allow` 標記的那一行是刻意保留的消費端（使用這支 skill 的專案）引用，豁免；其餘掃到的 blog route、`content/` 路徑、`/report/`、`/posts/`、`/skills/`、`_index.md`，改成 skill 內部的 principle、相對連結或中性名詞。

`skill-sync push` 另有一道可攜性閘門，範圍跟這條 rg 不同：它只掃 `.md` 全文與 `.py` 的 docstring 與 `#` 註解（不掃 `.sh` 這類其他檔案，也不掃 `references/project-integration/`），比對任何 `.claude/` 路徑（包括 skill 自己的 `.claude/skills/<自己的名字>/…`）與專案的 ticket ID，不比對 blog route。閘門只擋 SKILL.md frontmatter 宣告了 `metadata.portable: true` 的 skill，其餘只印一行計數。宣告 portable 的 skill，推送前直接跑閘門本身的檢查，不要自己拼 rg（自己拼的 pattern 會掃到腳本裡的 regex 程式碼，照著改會改壞腳本）：

```bash
(cd .claude/skills/skill-sync && uv run -q python -I -c "import sys;sys.path.insert(0,'.');from pathlib import Path;from skill_sync.cli import check_portability as c;[print(v) for v in c(Path('../<name>'))]")
```

或讀 `echo n | skill-sync push <name> -m x` 預覽裡的 `[Portability]` 清單；預覽只列前 20 筆，其餘印成 `... and N more`，超過時用上面那行指令取完整清單。命中的路徑改成相對路徑或中性名詞；刻意保留的那一行，在行尾加 `<!-- portability-allow: <保留的理由> -->`（閘門比對的是那一行裡有沒有 `portability-allow` 這個字串，理由寫得讓後來的人判得出該不該信）。

`.claude/skills/` 底下的 `.md` 在 pre-commit 同時跳過 mdtools 的 lint 與 fmt：重排會讓本地 skill 跟共用庫的版本分歧，而 fmt 會刪掉行內的 HTML 註解（理由寫在 `.githooks/pre-commit`）。

### 版號

修改 skill 內容後更新版號，版號遵循 semver：

- **patch**（0.1.0 → 0.1.1）：排版級與措辭級的改動（級別的定義在 `AGENTS.md`〈改動的級別〉）
- **minor**（0.1.0 → 0.2.0）：新增 reference 或 principle 卡、擴充段落、加觸發詞
- **major**（0.X → 1.0.0）：結構重組、支柱變動
- 規則級的改動（`AGENTS.md`〈改動的級別〉）依範圍判：改一條規則的條件、判斷標準或處置是 minor；改掉支柱或整個流程的結構是 major
- 未標版號的 skill 首次補標用 `1.0.0`。

版號的住址：

- **該 skill 的 `CHANGELOG.md` 最上面一條**，格式為 `**Version**: X.Y.Z — 變更摘要`，新的一條加在最上面。
- **`SKILL.md` frontmatter 的 `metadata.version`**。SKILL.md 正文只留一行指向 CHANGELOG：skill 是 runtime 整份載入的檔案，版本紀錄留在 SKILL.md 等於每次叫用都多讀一段沒有用的內容。
- **帶 `pyproject.toml` 的 skill**（如 `skill-sync`）另有第三個住址 `project.version`。改了版號就跑那支 skill 的測試（`skill-sync` 是 `(cd .claude/skills/skill-sync && uv run pytest -q tests/test_cli.py -k three_version)`），三個住址不一致時這個測試會失敗；`bin/skill-version-check` 不比對 pyproject。

改完跑 `bin/skill-version-check <name> …`（不給參數掃全部），它比對 frontmatter 的 `metadata.version` 與同目錄 `CHANGELOG.md` 最上面那一條，不一致的列出來。它結尾一定會印 `checked N skill(s), M failing`：零輸出代表腳本中途中止，不代表通過；N 要等於給的支數，名字打錯時它印 `skip: <name>（無 SKILL.md）` 而 N 是 0，exit 仍是 0。`bin/skill-mirror` 也會比對這兩個住址並在不一致時中止，但它只在有 `content/skills/` 鏡像的 skill 上執行。

### skill-sync 指令

本專案的 `.claude/skills/` 與共用 skill 庫 `https://github.com/tarrragon/claude-skills.git` 共用同一組 skill，用 `skill-sync` 同步。`~/.local/bin/skill-sync` 是一個 shim：它以當前 git repo 的根目錄解析出 `.claude/skills/skill-sync`，再用 `uv run --directory` 執行，所以跑的是這個 repo 裡那份 source；拉取 skill-sync 這個 skill 等於升級工具本身，下一次呼叫就生效。

指令、`pull` 報告的每一種分類與預設處置、`[WARNING]` 的種類、`--force` 的效果、非互動環境的兩段式（`echo n` 預覽、`echo y` 套用），以 `.claude/skills/skill-sync/SKILL.md` 為準，這裡不重寫。本 repo 在那份之外加的規則寫在〈推送前的檢查〉與〈同步時的判斷〉。

### 從 report 卡到 skill 的標準流程

流程從 report 卡開始：report 卡是原則的單一真實來源（有情境、根因、理想做法），skill 是它的操作化。兩者的責任不同：卡歸納缺陷與解法，skill 給處理方式與判斷方法。只改 skill、不涉及新原則時，從「修改 skill」那一步開始，commit message 寫出 `AGENTS.md`〈改動的級別〉的判定。

1. **建 report 卡**：在 `content/report/` 建卡。取號、查核與目錄頁的登記位置照 `content-folders.md`〈寫之前要做的查核〉；關係段與反向指標照 `writing-process.md`〈寫完之後的檢討〉的連結既有原則那一步。
2. **評估要不要進 skill、進多少**：先問這一條進了 skill 之後 agent 的動作會不會不同，不會就留在卡裡，commit message 寫出這個判定。會的話，skill 寫出執行時要用的判斷標準、觸發條件與處置；推導、實例與「為什麼既有審查抓不到」留在 report 卡上，skill 用相對連結指向這張卡的 principle 副本（`references/principles/<slug>.md`，在「修改 skill」那一步建立），不連 `/report/`。驗收：一個沒讀過那張卡的 agent，照 skill 這一段做得出動作嗎。進 skill 的內容越多，skill 越長、agent 越讀不完，而每一段單獨看都有道理，所以決定要進的時候，同時寫出它取代或縮短 skill 裡的哪一段，寫進 commit message。
3. **修改 skill**：在 `.claude/skills/<name>/` 修改。要引用 report 卡的內容時，把那張卡複製成 `references/principles/<slug>.md` 並去專案化（〈Skill 的撰寫規則〉），skill 本文用相對連結連到這份副本。
4. **新增 principle 卡時登記對應**：`bin/skill-mirror` 的 `find_report_slug()` 先在 `content/report/` 找同名的卡，找到就自動對應；副本的 slug 與 report 卡不同名，或本體是 `content/record/` 的文章時，在 `find_report_slug()` 裡的 `case` 加一條 principle slug → report 或 record slug 的對應。改了 `bin/skill-mirror` 之後，照 `scripts/principle-mirror-check.py` 檔頭的四個驗收案例跑過。
5. **更新版號**：照〈版號〉，跑 `bin/skill-version-check <name>`。
6. **同步鏡像**：`content/skills/<name>/` 存在時才做這一步；不存在代表這支 skill 沒有公開鏡像，跳過（`bin/skill-mirror` 對它會印 `content/skills/<name> not found (create it first)`，這個訊息不代表要建目錄，建不建鏡像見〈Skill 與文章是兩個 surface〉）。跑 `bin/skill-mirror <name>`，它處理 Hugo frontmatter、H1 轉 H2、連結轉換與 fmt，產生 `content/skills/<name>/` 底下的 `skill.md` 與各 reference 的鏡像。新增的 reference 第一次不會被鏡像：鏡像保留自己為 blog 讀者寫的 frontmatter，工具只對已存在的鏡像填正文。先手動放一份只有 frontmatter 的 `content/skills/<name>/<ref>.md` 再重跑；工具會把沒有鏡像的檔名印在 stderr。讀 stderr 的兩種訊息（見這一節末尾「principle 連結沒有對應時的訊號」那一段），不只看結尾那一行。
7. **commit 到 blog repo**：這次動過的檔案在同一個 commit 提交。用 `git status --short` 對照前面每一步改過的檔案，至少包括 `.claude/skills/<name>/`、`content/skills/<name>/`（有鏡像時）、新卡與 `content/report/_index.md`、補了反向指標的舊卡、改過的 `bin/skill-mirror`。pre-commit 的 skill mirror 檢查要求 `.claude/skills/<name>/` 與 `content/skills/<name>/` 一起 staged，只 staged 一邊會警告。
8. **推送**：照 `AGENTS.md`〈推送〉直接推送：blog repo 推 `main`，skill 照〈推送前的檢查〉推上共用 skill 庫。

**principle 連結沒有對應時的訊號**：「登記對應」那一步漏了時，`bin/skill-mirror` 依連結寫在哪裡給出兩種結果。連結寫在 SKILL.md 時，鏡像把它降成不能點的純文字，stderr 印 `WARN: no report card for <slug> — hyperlink degraded to inert path`，cards 不會擋，結尾還是印 `All principle links resolved to /report/`；連結寫在 reference 檔時，鏡像原樣保留相對連結，stderr 印 `WARN: <ref> 引用的 <slug> 沒有對應 report 卡 — 原樣保留`，之後 commit 時 pre-commit 的 cards 以 broken link 擋下。兩種都回頭補對應，重跑同步鏡像那一步。

批量推送多個 skill 時逐一執行 `skill-sync push`，不手動 clone 遠端 repo 操作：手動 clone 推上去的內容繞過了 skill-sync 的預覽閘門，也不會更新遠端的 `versions.json` 與本地的同步基底，之後的 `pull` 報告會在 `[SHOULD PUSH]` 與 `[SHOULD PULL]` 之間來回，看不出實際的方向。

### 推送前的檢查

推送 skill 到共用庫之前確認三件事，細節以 `.claude/skills/skill-sync/SKILL.md` 為準：

- **用兩段式**：`echo n | skill-sync push <name> -m "…"` 取預覽，讀完再 `echo y | …`。agent 的 shell 沒有互動輸入，直接跑會被當成 N 而中止。
- **預覽裡出現任何一行 `[WARNING]` 就不跑 `echo y`**：每一種警告的意思與處置照 skill-sync SKILL.md〈Report categories and non-interactive use〉的警告表，處理完重跑預覽。宣告 portable 的 skill 印出 `[Portability]` 清單並中止時，照〈Skill 的撰寫規則〉的可攜性掃描修掉再推。
- **不帶 `--force`**：`--force` 拿掉警告之後的停點，並放行 portable skill 的可攜性閘門。沒有使用者在這次的指示裡明說就不帶（`AGENTS.md`〈要先問使用者的情形〉），被放行的那幾條寫進這次 `skill-sync push -m` 的訊息。

`[Version] local X vs remote Y` 是給人對照 changelog 用的顯示行，不是判定依據：skill-sync 用內容雜湊判斷兩邊相不相同，X 高於 Y 不代表可以推送。要確定一支 skill 的版本，讀它 SKILL.md frontmatter 的 `metadata.version`。

查共用庫的實際狀態用 `git clone`，不用 `raw.githubusercontent.com`：那個端點有 CDN 快取，回讀到的是數分鐘前的內容，而且沒有任何訊號顯示它過期。skill-sync 印的 `[Version]` 比對的是 clone，可以信。

### 同步時的判斷

`skill-sync pull`（不帶參數）的分類與預設處置以 skill-sync SKILL.md〈Report categories and non-interactive use〉為準。本 repo 加的規則：

- **`[SKIP]` 遠端沒有這個條目**：在〈只留在本 repo 的 skill〉清單裡的不推；不在清單裡的照 `AGENTS.md`〈推送〉推上去。
- **`[DIVERGED]` 與 `[CONFLICT]`**：比對兩邊的歷史（共用庫 clone 裡那個 skill 路徑的 `git log`，對本 repo 的 `git log -- .claude/skills/<name>`），把兩邊各自改了什麼寫進 commit message，合併之後推。兩邊在共同基底之後改到同一段文字（合併時有衝突）時，照 `AGENTS.md`〈要先問使用者的情形〉把兩邊的 log 與衝突的段落給使用者。
- **`[SUSPECT REVERT]`**：不拉。查是誰把舊版推上共用庫，把較新的那一份推回去。
- 遠端有新增的檔案（原則卡、hooks）時，用 `skill-sync pull <name>` 取到本地，再推合併版回遠端。
- 遠端的版本加了 emoji 或把相對連結改成絕對路徑時，修正後推回：本專案禁止 emoji，skill 內的連結要是相對路徑。
- 同步完本地 `.claude/skills/` 後，有 `content/skills/` 鏡像的 skill 跑一次 `bin/skill-mirror <name>`（pre-commit hook 會提醒）。
- 不帶參數的 `pull` 不是唯讀：它會替已經同步的 skill 重寫 `.skill-sync-base`（被 gitignore，不會出現在 diff 裡）。

### 只留在本 repo 的 skill

下列 skill 是 blog 專屬的，刻意不推上共用 skill 庫（`skill-sync pull` 對它們印 `[SKIP]` … no remote entry），改了它們只提交 blog repo：

- `blogsearch-lifecycle`
- `vendor-deep-article`

新增一支只給本 repo 用的 skill 時，加進這份清單；清單裡的 skill 沒有使用者在這次的指示裡明說就不推上共用庫（`AGENTS.md`〈要先問使用者的情形〉）。

### Claude Code 與 Codex 共用的 skill 目錄

Claude Code 讀 `.claude/skills/`，Codex 讀 `.agents/skills/`。本 repo 用 directory symlink 讓兩者讀到同一份檔案：`.agents/skills` 與 `.codex/skills` 都指向 `../.claude/skills`。改 skill 時編輯 `.claude/skills/<name>/`；經由 symlink 的路徑改，改到的也是同一份，但 diff 與 `git log` 只記在 `.claude/skills/` 底下，所以引用與交給 `bin/commit-files` 的路徑都寫 `.claude/skills/` 的路徑。Anthropic SKILL.md 的 frontmatter（`name`、`description`）是 Codex SKILL.md frontmatter 的子集，Codex 直接讀 Anthropic 格式。

symlink 不再適用、要拆成兩份獨立目錄的訊號：

| 訊號                                         | 拆開之後的差異                                     |
| -------------------------------------------- | -------------------------------------------------- |
| Codex 加了 Anthropic 不認的 frontmatter 欄位 | `.agents/skills/<name>/` 獨立寫，加 Codex 專屬欄位 |
| Anthropic 加了 Codex 不認的 frontmatter 欄位 | `.claude/skills/<name>/` 獨立寫，`.agents/` 拆出去 |
| 需要 Codex 專屬的 `agents/openai.yaml`       | 放在 `.agents/skills/<name>/agents/openai.yaml`    |
| skill 在兩個工具裡的行為要不同               | 拆成兩份，各自客製                                 |

拆開的方式是刪除 symlink、`cp -r .claude/skills .agents/skills`，之後兩份各自維護。兩邊的 frontmatter 規格改版時，重新確認兩者還相容。

### 改既有 report 卡時查它在 skill 裡的副本

report 卡的內容可能已經被複製成 skill 的 principle 卡。只改 report 卡而沒改 principle 卡，共用庫裡就留著一份被推翻的規則，下游專案拉到的是舊版。副本與本體（被複製的那張 report 卡）的對應有四種形態（檔名相同、H1 相同、`bin/skill-mirror` 的 `find_report_slug()` 對應、只在正文引用），每一種只有一個鍵找得到，所以用腳本找，不自己用 `rg` 或 `find` 拼：

```bash
scripts/principle-mirror-check.py <report-或-record-卡的-slug>   # 查一張，落後的會標出來
scripts/principle-mirror-check.py --all                          # 全庫掃，列出本體較新的那些
```

`--all` 列出的數量隨每一次 commit 變動，不抄進任何文件，要知道就跑一次。逐張判斷該不該同步，判定只有兩條：一、本體的變更改動了規則、判斷標準或處置，同步。二、本體只改了措辭或案例，就把改前的句子用 `grep -F '<改前的句子>' <副本路徑>` 在副本裡找一次：找得到，代表副本逐字抄了那一句（措辭本身可能就是 skill 用來判讀的依據），同步；找不到，代表副本已經改寫成 skill 自己的寫法，不同步。commit message 寫出副本清單與每一份的判定。`--all` 看的是 commit 時間、不看內容，副本晚於本體 commit 而內容已經分岔的，它抓不到；要確認內容一致，打開兩份比對。同步時兩份的段標用同一組字串，之後逐段比對兩份（打開兩份、照段標對齊段落）時才對得上。副本落在 `content/skills/` 底下時，那是 `bin/skill-mirror` 產生的鏡像，改 `.claude/skills/` 的副本再重跑鏡像，不手改。

修改 `scripts/principle-mirror-check.py` 或 `bin/skill-mirror` 之前，讀 `scripts/principle-mirror-check.py` 檔頭的驗收案例，改完逐個跑過再提交。
