# Skill 的撰寫與同步

## Skill 的撰寫與同步

### Skill 與文章是兩個 surface

`.claude/skills/` 與 `content/` 在體例、格式與依賴上的規則互斥：寫 skill 時不套教學體例、Hugo frontmatter 與 mdtools lint，寫文章時不套操作手冊的體例與 skill 的可攜性限制。兩邊的讀者見`writing.md`〈三種書面產出的體例〉。句子層的規則兩邊共用：`sentences.md`〈句子與命名〉底下各節、`sentences.md`〈譯名避開介面上已有的同名元素〉、`writing.md`〈不用一句話交代或總結；推導過重時拆篇〉。

|        | `.claude/skills/`（skill）                                                                          | `content/`（文章）                       |
| ------ | --------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| 載入者 | agent runtime（Claude Code、Codex）直接載入                                                         | 人類讀者經由 Hugo                        |
| 目標   | 可攜：整個目錄複製到別的專案就能運作                                                                | 服務本 blog 的脈絡與累積                 |
| 可依賴 | 只依賴 skill 自身的內容與穩定的公開來源                                                             | 可引用 report、posts 與其他 section      |
| 格式   | SKILL.md 以 YAML frontmatter（`name`、`description`、`metadata`）開頭，接 H1 與正文；不放 Hugo 欄位 | Hugo frontmatter（`title`、`date` 必填） |

`content/skills/<name>/` 是 skill 的公開鏡像，給網站讀者讀，只有對外公開的方法論需要；內部協議型的 skill 只存在於 `.claude/skills/`。鏡像與源檔的正文相同，差在鏡像帶 Hugo frontmatter，由 `bin/skill-mirror` 產生（見〈從 report 卡到 skill 的標準流程〉）。要不要替一支 skill 建鏡像由使用者決定。

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
rg -n "\\]\\((/|content/|\\.\\./\\.\\./)|(/report/|/posts/|/skills/|content/report|content/posts|content/skills|_index\\.md)" .claude/skills/<name>
```

命中是候選：帶 `portability-allow` 標記的那一行是刻意保留的消費端引用，豁免；skill 自己的路徑（`.claude/skills/<自己的名字>/…`）不算依賴。其餘掃到的 blog route、`content/` 路徑、`/report/`、`/posts/`、`/skills/`、`_index.md`，改成 skill 內部的 principle、相對連結或中性名詞。`skill-sync push` 另有一道可攜性閘門（見〈推送前的檢查〉），這條 rg 在推送之前就先找出命中。

`.claude/skills/` 底下的 `.md` 在 pre-commit 同時跳過 mdtools 的 lint 與 fmt：重排會讓本地 skill 跟共用庫的版本分歧，而 fmt 會刪掉行內的 HTML 註解（理由寫在 `.githooks/pre-commit`）。

### 版號

修改 skill 內容後更新版號，版號遵循 semver：

- **patch**（0.1.0 → 0.1.1）：修錯字、補連結、格式調整
- **minor**（0.1.0 → 0.2.0）：新增 reference 或 principle 卡、擴充段落、加觸發詞
- **major**（0.X → 1.0.0）：結構重組、支柱變動、改變既有行為
- 未標版號的 skill 首次補標用 `1.0.0`。

版號的住址：

- **該 skill 的 `CHANGELOG.md` 最上面一條**，格式為 `**Version**: X.Y.Z — 變更摘要`，新的一條加在最上面。
- **`SKILL.md` frontmatter 的 `metadata.version`**。SKILL.md 正文只留一行指向 CHANGELOG：skill 是 runtime 整份載入的檔案，版本紀錄留在 SKILL.md 等於每次叫用都多讀一段沒有用的內容。
- **帶 `pyproject.toml` 的 skill**（如 `skill-sync`）另有第三個住址 `project.version`。三者一致由那支 skill 自己的測試守著（`skill-sync` 是 `tests/test_cli.py` 的 `test_three_version_addresses_agree`），`bin/skill-version-check` 不比對 pyproject。

改完跑 `bin/skill-version-check <name> …`（不給參數掃全部），它比對 frontmatter 的 `metadata.version` 與同目錄 `CHANGELOG.md` 最上面那一條，不一致的列出來。它結尾一定會印 `checked N skill(s), M failing`：零輸出代表腳本中途中止，不代表通過；N 要等於給的支數，名字打錯時它印 `skip: <name>（無 SKILL.md）` 而 N 是 0，exit 仍是 0。`bin/skill-mirror` 也會比對這兩個住址並在不一致時中止，但它只在有 `content/skills/` 鏡像的 skill 上執行。

### skill-sync 指令

本專案的 `.claude/skills/` 與共用 skill 庫 `https://github.com/tarrragon/claude-skills.git` 共用同一組 skill，用 `skill-sync` 同步。`~/.local/bin/skill-sync` 是一個 shim：它以當前 git repo 的根目錄解析出 `.claude/skills/skill-sync`，再用 `uv run --directory` 執行，所以跑的是這個 repo 裡那份 source；拉取 skill-sync 這個 skill 等於升級工具本身，下一次呼叫就生效。

```bash
# 列出遠端所有 skill
skill-sync list

# 盤點已安裝的 skill 與遠端的落差，只出報告、不動任何檔案（分類見〈同步時的判斷〉）
skill-sync pull

# 套用：新安裝或更新一支 skill
skill-sync pull <skill-name>

# 本地推到遠端（自動更新 versions.json）
skill-sync push <skill-name> -m "commit message"
```

`pull <name>` 與 `push` 在套用之前會停下來問 `[y/N]`。agent 的 Bash 沒有互動輸入，`input()` 讀到 EOF 時當成 N、印 `Aborted.`，所以分兩次跑：第一次 `echo n | skill-sync push <name> -m "…"` 取得預覽，讀完預覽（見〈推送前的檢查〉），確定要套用再跑 `echo y | skill-sync push <name> -m "…"`。`pull <name>` 同樣用 `echo n`／`echo y`。推送到共用庫之前先問使用者（`AGENTS.md`〈規則的優先序與住址〉的推送那一條）。

### 從 report 卡到 skill 的標準流程

流程從 report 卡開始：report 卡是原則的單一真實來源（有情境、根因、理想做法），skill 是它的操作化。兩者的責任不同：卡歸納缺陷與解法，skill 給處理方式與判斷方法。只改 skill、不涉及新原則時（修錯字、改步驟、對齊工具行為），從步驟 3 開始。

1. **建 report 卡**：在 `content/report/` 建卡，更新 `content/report/_index.md` 的篇目索引。
2. **評估要不要進 skill、進多少**：先問這一條進了 skill 之後 agent 的動作會不會不同，不會就留在卡裡。會的話，skill 寫出執行時要用的判斷標準、觸發條件與處置；推導、實例與「為什麼既有審查抓不到」留在 report 卡上，skill 用相對連結指向步驟 3 建的 principle 副本，不連 `/report/`。驗收：一個沒讀過那張卡的 agent，照 skill 這一段做得出動作嗎。進 skill 的內容越多，skill 越長、agent 越讀不完，而每一段單獨看都有道理，所以決定要進的時候，同時寫出它取代或縮短 skill 裡的哪一段。
3. **修改 skill**：在 `.claude/skills/<name>/` 修改。要引用 report 卡的內容時，把那張卡複製成 `references/principles/<slug>.md` 並去專案化（〈Skill 的撰寫規則〉），skill 本文用相對連結連到這份副本。
4. **新增 principle 卡時**：副本的 slug 與 report 卡不同名時，在 `bin/skill-mirror` 的 `find_report_slug()` 裡的 `case` 加一條 principle slug → report slug 的對應；同名的會自動精確比對，不用加。
5. **更新版號**：CHANGELOG.md 最上面加一條、SKILL.md frontmatter 的 `metadata.version` 改成同一個值；帶 `pyproject.toml` 的同時改 `project.version` 並跑那支 skill 的測試。跑 `bin/skill-version-check <name>`。
6. **同步鏡像**：`content/skills/<name>/` 存在時才做這一步；不存在代表這支 skill 沒有公開鏡像，跳過（`bin/skill-mirror` 對它會印 `content/skills/<name> not found (create it first)`，這個訊息不代表要建目錄，建不建鏡像見〈Skill 與文章是兩個 surface〉）。跑 `bin/skill-mirror <name>`，它處理 Hugo frontmatter、H1 轉 H2、連結轉換與 fmt，產生 `content/skills/<name>/` 底下的 `skill.md` 與各 reference 的鏡像。新增的 reference 第一次不會被鏡像：鏡像保留自己為 blog 讀者寫的 frontmatter，工具只對已存在的鏡像填正文。先手動放一份只有 frontmatter 的 `content/skills/<name>/<ref>.md` 再重跑；工具會把沒有鏡像的檔名印在 stderr。
7. **commit 到 blog repo**：skill、鏡像與 report 卡在同一個 commit 提交：`git add .claude/skills/<name>/ content/skills/<name>/ content/report/<slug>.md content/report/_index.md`（沒有的路徑不加）。pre-commit 的 skill mirror 檢查要求 `.claude/skills/<name>/` 與 `content/skills/<name>/` 一起 staged，只 staged 一邊會警告。
8. **推送到 skill 庫**：先問使用者，再照〈skill-sync 指令〉的兩段式跑 `skill-sync push <name> -m "描述"`，不帶 `--force`（見〈推送前的檢查〉）。
9. **推送 blog repo**：照`AGENTS.md`〈規則的優先序與住址〉的推送那一條，由使用者決定。

步驟 7 被 pre-commit 的 `cards` 擋下時，最可能的成因是步驟 4 漏了：`find_report_slug()` 沒有對應的 principle slug，鏡像因此留著 `references/principles/` 的相對連結，在 `content/` 底下解析不到。`bin/skill-mirror` 對這種情形只印 `WARN: N unresolved`、不中止，症狀出現在離成因很遠的 commit 階段。回頭補對應，重跑步驟 6。

批量推送多個 skill 時逐一執行 `skill-sync push`，不手動 clone 遠端 repo 操作。

### 推送前的檢查

推送之前要確認三件事：不帶 `--force`、預覽裡沒有 `[WARNING]`、判斷共用庫的狀態時讀的是 clone。

推送一律不帶 `--force`。`--force` 做兩件事：拿掉每一道 `[WARNING]` 之後的 `[y/N]` 停點（警告照樣印在 stderr，但不再等人讀完），以及放行宣告了 `metadata.portable: true` 的 skill 的可攜性閘門（沒帶 `--force` 時，這種 skill 帶著消費端專屬的路徑會印 `[Portability]` 清單並中止）。確實要用 `--force` 時，把被放行的那幾條寫進 commit message。

`echo n` 取得的預覽裡，出現任何一行 `[WARNING]` 都不跑 `echo y`。各種警告的意思與處置：

| 警告的開頭                                                   | 意思                                                     | 處置                                                             |
| ------------------------------------------------------------ | -------------------------------------------------------- | ---------------------------------------------------------------- |
| `Sync base shows both sides changed independently`           | 上次同步之後，本地與遠端各自改過，推送會蓋掉遠端的改動   | 用 `skill-sync pull <name>` 的預覽看遠端改了什麼，逐段合併後再推 |
| `Sync base suggests this skill has only moved the other way` | 上次同步之後只有遠端前進，本地沒改                       | 改用 `skill-sync pull <name>`                                    |
| `Content changed since last sync … but version is still X`   | 內容改了而版號沒動                                       | 照〈版號〉bump 之後再推                                          |
| `Local content matches an older historical version`          | 本地內容跟共用庫歷史上的某一版相同，推送會用舊版蓋掉新版 | 先 `skill-sync pull <name>` 取得遠端現況，再決定                 |
| `--force ignored N direction warning(s)`                     | 這次帶了 `--force`，上面的警告被略過                     | 回頭讀那幾道警告，確認推送沒有蓋掉別人的改動                     |

`[Version] local X vs remote Y` 是給人對照 changelog 用的顯示行，不是判定依據：skill-sync 已經把版本字串移出同步決策，內容是否相同改用 hash 比對，X 高於 Y 不代表可以推送。要確定一支 skill 的版本，讀它 SKILL.md frontmatter 的 `metadata.version`，不讀任何報告裡的字串。

查共用庫的實際狀態用 `git clone`，不用 `raw.githubusercontent.com`：那個端點有 CDN 快取，回讀到的是數分鐘前的內容，而且沒有任何訊號顯示它過期。skill-sync 印的 `[Version]` 比對的是 clone，可以信。

### 同步時的判斷

不帶參數的 `skill-sync pull` 把每支 skill 分到下列其中一類，各類的處置：

- **`[SKIP]`，遠端沒有這個條目**：先確認它是不是刻意只留在本 repo 的 blog 專屬 skill（例如 `blogsearch-lifecycle`、`vendor-deep-article`），是就不推；不是的話，問使用者要不要推上共用庫。
- **`[SKIP]`，遠端有條目但沒有 hash**：遠端的 `versions.json` 還沒有這支的 hash，下一次推送任何 skill 時會補上；不用處理。
- **`[SHOULD PULL]`**：本地自上次同步後沒有改動、遠端前進了，沒有會被覆蓋的本地修改。看過預覽裡進來的內容後用 `skill-sync pull <name>` 拉取。
- **`[SHOULD PUSH]`**：遠端自上次同步後沒有改動、本地前進了。照〈從 report 卡到 skill 的標準流程〉的推送步驟處理。
- **`[SHOULD PUSH --PRUNE]`**：遠端只多了本地刻意刪掉的檔案；拉取會把它們放回來。推送時帶 `--prune`。
- **`[CONFLICT]`**：兩邊在上次同步後各自改過。逐段比對兩邊，合併之後再推。
- **`[DIVERGED]`**：內容不同，而沒有同步基底可以判斷方向。逐段比對，判斷哪一邊較新再決定拉或推。
- **up to date**：不用處理。

其他情形：

- 遠端有新增的檔案（原則卡、hooks）時，用 `skill-sync pull <name>` 取到本地，再推合併版回遠端。
- 遠端的版本加了 emoji 或把相對連結改成絕對路徑時，修正後推回：本專案禁止 emoji，skill 內的連結要是相對路徑。
- 同步完本地 `.claude/skills/` 後，有 `content/skills/` 鏡像的 skill 跑一次 `bin/skill-mirror <name>`（pre-commit hook 會提醒）。

### 改既有 report 卡時查它在 skill 裡的副本

report 卡的內容可能已經被複製成 skill 的 principle 卡。只改 report 卡而沒改 principle 卡，共用庫裡就留著一份被推翻的規則，下游專案拉到的是舊版。副本與本體（被複製的那張 report 卡）的對應有四種形態（檔名相同、H1 相同、`bin/skill-mirror` 的 `find_report_slug()` 對應、只在正文引用），每一種只有一個鍵找得到，所以用腳本找，不自己用 `rg` 或 `find` 拼：

```bash
scripts/principle-mirror-check.py <report-或-record-卡的-slug>   # 查一張，落後的會標出來
scripts/principle-mirror-check.py --all                          # 全庫掃，列出本體較新的那些
```

`--all` 列出的數量隨每一次 commit 變動，不抄進任何文件，要知道就跑一次。逐張判斷該不該同步：本體的變更改動了規則、判斷標準或處置時同步；只改了措辭或案例時，先確認那段措辭不是 skill 用來判讀的依據（principle 卡裡的措辭本身可能就是 bank 某一類的判讀標準），拿不準時同步。`--all` 看的是 commit 時間、不看內容，副本晚於本體 commit 而內容已經分岔的，它抓不到；要確認內容一致，打開兩份比對。同步時兩份的段標用同一組字串，之後靠 anchor 比對的檢查才不會錯位。副本落在 `content/skills/` 底下時，那是 `bin/skill-mirror` 產生的鏡像，改 `.claude/skills/` 的副本再重跑鏡像，不手改。

修改 `scripts/principle-mirror-check.py` 或 `bin/skill-mirror` 之前，讀 `scripts/principle-mirror-check.py` 檔頭的驗收案例，改完逐個跑過再提交。
