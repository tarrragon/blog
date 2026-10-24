# Blog 專案的寫作與工程規則

這份檔案是 blog 專案寫作與工程規則的入口，讀者是在這個 repo 工作的 agent。規則分成本檔與 `docs/rules/` 底下的分冊：本檔放每個 session 都會用到的規則（優先序與住址、回覆語言、提交與推送、決策分析、跨 agent 的設定）與下面這張分冊路由表，分冊放各類工作才會用到的規則。

拆成分冊的原因是讀取上限：Codex 讀專案指令檔時有位元組上限（`project_doc_max_bytes`，預設 32 KiB），超過的部分不會進它的 context，而全部規則合起來約 110 KB。所以本檔要維持在這個上限以內，新增的規則寫進對應的分冊。Claude Code 經由 CLAUDE.md 的 `@` 匯入，每個 session 都讀到本檔與全部分冊；Codex 只自動讀到本檔，做下表的工作之前，先把對應的分冊整份讀完再動手。

| 要做的工作                                                        | 先讀的分冊                      |
| ----------------------------------------------------------------- | ------------------------------- |
| 決定文章放哪個資料夾、寫或改 `_index.md`、記 Backlog              | `docs/rules/content-folders.md` |
| 寫或改 `content/` 的文章（定位、讀者、結構、`description`）       | `docs/rules/writing.md`         |
| 寫或改任何一段文字（`content/`、skill、規則檔）的句子、命名與術語 | `docs/rules/sentences.md`       |
| 寫文章的流程、留紀錄、完稿檢查                                    | `docs/rules/writing-process.md` |
| 多輪審查、理解探針                                                | `docs/rules/review.md`          |
| Markdown 排版、mdtools                                            | `docs/rules/markdown.md`        |
| 寫或改 skill、版號、同步到共用 skill 庫                           | `docs/rules/skills.md`          |
| 在遠端機器上驗證或部署                                            | `docs/rules/remote.md`          |

規則之間用〈段名〉互相引用；段名在另一份檔案時，前面寫出檔名（`writing.md`〈開場列出這篇討論的內容〉）。Claude Code 專屬的操作列在 CLAUDE.md 開頭。

## 規則的優先序與住址

**優先序**：本檔與 `docs/rules/` 分冊的規則優先；寫作時另外遵循 `compositional-writing` skill；做分析、決策、比較與提案時遵循 `wrap-decision` skill（見〈決策分析：WRAP〉）。

**住址**：每一條規則只寫在一個位置，其他位置用連結指過去。同一條規則寫在兩個位置時，修改的人只會改其中一份，兩份會漸漸分歧，而照著舊的那一份工作的 agent 會做錯。分工如下：

| 內容                                                                   | 住址                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------ |
| Claude Code 與 Codex 共用的寫作規則與工程規則                          | 本檔（每個 session 都用到的）與 `docs/rules/` 的分冊   |
| Claude Code 專屬的操作（範圍列在 CLAUDE.md 開頭）                      | CLAUDE.md                                              |
| 可以照著執行的偵測細節（字句層 pattern、探針的派發與判讀、審查 frame） | 對應的 skill；規則檔寫規則與判斷標準，並連到 skill     |
| 規則的推導、實測紀錄、事件經過與量測數字                               | `content/report/` 的卡；規則檔寫規則與理由，連到那張卡 |
| 工具自己的行為（腳本的參數、內部邏輯、維護方式）                       | 工具的檔頭註解或它的 skill                             |

在本檔或分冊新增或修改一條規則時，寫規則本身、執行者用來判斷的標準、判斷之後的處置，以及讓執行者理解規則存在原因的理由；推導過程與「先前怎麼寫、後來為什麼改」寫進 report 卡或 commit message。

**寫作類 skill 由 agent 主動叫用**：寫作任務常常以「幫我改這段」「補一句」「這裡讀起來怪怪的」進來，這些措辭比對不到 `compositional-writing` 的 `description` 裡任何一個觸發詞，而每一處小改動都可能帶進字句層 bank 的任何一類違規。所以動到 `content/`、`.claude/skills/`、本檔或 CLAUDE.md 的任何一段文字之前，叫用 `compositional-writing`，不等 description 比對自動觸發；改完照`docs/rules/writing-process.md`〈文章產出流程〉的字句層掃描跑一次 bank，逐類表照`docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉留下。

**提交之後的推送**：commit 完成後，推不推送到遠端由使用者決定。使用者沒有在這次的指示裡要求推送時，回報有哪些 commit 還沒推送（`git log origin/main..main --oneline`），等使用者指示；推送 skill 到共用庫（`docs/rules/skills.md`〈skill-sync 指令〉）同樣先問。

## 回覆語言

給使用者的每一則回覆都用繁體中文，包括工具呼叫之間的短句與工作結束時的總結。指令、程式識別字、錯誤訊息原文、產品與服務名稱保留原文，其餘敘述用中文。前文是一長串英文的指令、log、錯誤訊息與程式碼時，最後的總結最容易漂成英文，所以每一則總結送出之前確認一次語言。

## 提交與推送

### 提交與驗證

- pre-commit 或 pre-push 報錯時讀訊息修正，不用 `--no-verify` 繞過。
- `description` 與 `tags` 是警告層，但不是可以新增的技術債：新增內容一律補齊；修改既有 `content/**` 檔案時，同檔缺這兩個欄位就在同一次變更補上。
- 提交前以本次變更的檔案跑 lint（`./bin/mdtools lint <變更的檔案...>`）判斷本次品質；全量 lint 用來觀察歷史基線。回報時把既有 warning 與本次新增的問題分開。
- 提交前跑一次 `./bin/mdtools cards content/`。有 error 時 exit 1，stderr 印 `mdtools cards: N error(s), M warning(s)`；零輸出加 exit 0 是通過。指令後面接了 pipe（`| tail`）時，看到的 exit 是 pipe 最後一個指令的，要看 cards 自己的結果就不接 pipe。

### 多個 session 共用 repo 時的提交

同一個 repo 有其他 session（或其他 agent）也在工作時，共用的 git index 裡可能有對方 staged 的檔案，直接 `git commit` 會把它們一起提交；對方正在跑 git 時，`git add` 與 `git commit` 會因為 `.git/index.lock` 存在而失敗。這兩種情形都用私有的 index 提交，不刪除 lock：

```bash
export GIT_INDEX_FILE=<scratchpad 的絕對路徑>/idx   # 私有 index 的位置
git read-tree HEAD                                 # 以 HEAD 初始化私有 index
git add <這次的檔案...>
git diff --cached --name-only                      # 確認 staged 的只有這次的檔案
git commit -F <訊息檔>
unset GIT_INDEX_FILE
```

- `git diff --cached --name-only` 列出對方的路徑時，代表私有 index 沒有生效（多半是環境變數沒有帶到那一行），中止，不 commit。
- 提交之後，共用的 index 裡那些檔案仍是舊版本；另一個 session 用它 commit 時，會把這次的改動改回去。所以 lock 釋放之後（`test -e .git/index.lock` 回傳非零），先用 `git diff --cached --name-only` 確認那些檔案沒有對方的 staging，再跑 `git reset -q -- <這次的檔案...>`，讓共用的 index 對齊 HEAD；對方也 staged 了同一個檔案時，reset 會清掉它的 staging，先跟對方協調。

## 決策分析：WRAP

需求包含分析、決策、比較、提案或查詢時，用 `wrap-decision` skill 的 WRAP 流程。流程的步驟名照 skill：

- **錨點確認**：對齊核心目標與決策錨點；skill 的閘門判斷這一題要不要往下走。
- **Step 0（資料充足度閘門）**：判斷手上的資料足不足以直接下結論。
- **W（擴增選項，Widen Options）**：列出多個本質不同的選項。
- **R（現實檢驗，Reality-test）**：用來源與反例驗證，不靠直覺。
- **A（拉開距離，Attain Distance）**：評估機會成本與長期影響。
- **P（準備好犯錯，Prepare to be Wrong）**：預先設計失敗回退與監控。
- **絆腳索（tripwire）**：設定到達什麼條件時重新評估決策。

分析與查詢的輸出清楚標示觀察、判讀、策略、結論；引用的來源要可回溯；包含反向驗證（批評、反例、限制）。

## 跨 agent 的設定

本 repo 同時支援 Claude Code 與 Codex（以及其他遵循 AGENTS.md 標準的 agent），目前以 Claude Code 為主。

| 檔案              | 角色                                                  | 誰讀                                                                   |
| ----------------- | ----------------------------------------------------- | ---------------------------------------------------------------------- |
| `AGENTS.md`       | 寫作與工程規則的單一真實來源                          | Codex、Claude Code（經由 `@AGENTS.md`）、其他 agent                    |
| `docs/rules/*.md` | 各類工作的規則分冊，路由表在本檔開頭                  | Claude Code（經由 CLAUDE.md 的 `@` 匯入）、Codex（做那類工作前自己讀） |
| `CLAUDE.md`       | Claude Code 專屬的操作，開頭用 `@` 匯入本檔與全部分冊 | Claude Code                                                            |

`@<file>` 是 Claude Code 專屬語法，Codex 不解析：Codex 自動讀到的只有本檔，分冊要照開頭的路由表自己讀。新增規則時依〈規則的優先序與住址〉決定寫在哪一份；Codex 專屬的規則（如果有）寫在本檔，標明 `[Codex only]`。

**skill 的路徑**：Claude Code 用 `.claude/skills/`，Codex 用 `.agents/skills/`。本 repo 用 directory symlink 共用兩處（`.agents/skills` → `../.claude/skills`）：改 skill 時直接編輯 `.claude/skills/<name>/`，Codex 經由 symlink 看到；不直接修改 `.agents/skills/`。Anthropic SKILL.md 的 frontmatter（`name`、`description`）是 Codex SKILL.md frontmatter 的子集，Codex 直接讀 Anthropic 格式。

symlink 失效、需要拆成兩份獨立目錄的訊號：

| 訊號                                         | 拆開之後的差異                                     |
| -------------------------------------------- | -------------------------------------------------- |
| Codex 加了 Anthropic 不認的 frontmatter 欄位 | `.agents/skills/<name>/` 獨立寫，加 Codex 專屬欄位 |
| Anthropic 加了 Codex 不認的 frontmatter 欄位 | `.claude/skills/<name>/` 獨立寫，`.agents/` 拆出去 |
| 需要 Codex 專屬的 `agents/openai.yaml`       | 放在 `.agents/skills/<name>/agents/openai.yaml`    |
| skill 在兩個工具裡的行為要不同               | 拆成兩份，各自客製                                 |

拆開的步驟：刪除 symlink、`cp -r .claude/skills .agents/skills`、各自維護。兩邊的 frontmatter 規格改版時，重新確認相容性。
