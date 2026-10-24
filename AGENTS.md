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

**住址**：每一條規則只寫在一個位置，其他位置用連結指過去。同一條規則寫在兩個位置時，沒有任何工具會偵測兩份分歧：修改的人只改其中一份，照著舊的那一份工作的 agent 會做錯。分工如下：

| 內容                                                                   | 住址                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------ |
| Claude Code 與 Codex 共用的寫作規則與工程規則                          | 本檔（每個 session 都用到的）與 `docs/rules/` 的分冊   |
| Claude Code 專屬的操作（範圍列在 CLAUDE.md 開頭）                      | CLAUDE.md                                              |
| 可以照著執行的偵測細節（字句層 pattern、探針的派發與判讀、審查 frame） | 對應的 skill；規則檔寫規則與判斷標準，並連到 skill     |
| 規則的推導、實測紀錄、事件經過與量測數字                               | `content/report/` 的卡；規則檔寫規則與理由，連到那張卡 |
| 工具自己的行為（腳本的參數、內部邏輯、維護方式）                       | 工具的檔頭註解、README 或它的 skill                    |

例外是刻意建立、而且有工具比對的副本：skill 的 principle 卡是 report 卡的副本（`scripts/principle-mirror-check.py` 比對），`content/skills/` 是 skill 的鏡像（`bin/skill-mirror` 產生）。

**新增或修改規則時**，在本檔或分冊寫出四件事：規則本身、執行者用來判斷的標準、判斷之後的處置、讓執行者判得出適用邊界的理由；推導過程與「先前怎麼寫、後來為什麼改」寫進 report 卡或 commit message。加一節之前問兩件事：這一節的修改理由在不在這份檔案既有的主題裡（不在就放進對應的分冊或新開一份）；寫進 CLAUDE.md 之前，Codex 需不需要它（需要就寫進本檔或分冊）。觸發條件寫成查得到的事實（指令輸出、檔案、diff、frontmatter 欄位），不寫成執行者的主觀狀態（「拿不準時」「懷疑時」）；非用主觀狀態不可時，加一句「執行者自認不成立，不改變本款結果」，因為會誤判的人正是不認為自己在誤判的人。

## 寫作類 skill 的叫用

寫作任務常常以「幫我改這段」「補一句」「這裡讀起來怪怪的」進來，這些措辭比對不到 `compositional-writing` 的 `description` 裡任何一個觸發詞，而每一處小改動都可能帶進字句層 bank（`compositional-writing` 的 SKILL.md「字句層 keyword bank（完整清單）」那一節列的反模式類別與 rg 指令）的任何一類違規。所以動到 `content/`、`.claude/skills/`、本檔、`docs/rules/` 或 CLAUDE.md 的任何一段文字之前，叫用 `compositional-writing`，不等 description 比對自動觸發。改完照 `docs/rules/writing-process.md`〈文章產出流程〉的字句層掃描跑一次 bank，掃描的對象是這次的新增與改動（`git diff -U0` 的新增行），逐類表照 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉留下。

## 回覆語言

給使用者的每一則回覆都用繁體中文，包括工具呼叫之間的短句與工作結束時的總結。指令、程式識別字、錯誤訊息原文、產品與服務名稱保留原文，其餘敘述用中文。前文是一長串英文的指令、log、錯誤訊息與程式碼時，最後的總結最容易漂成英文，所以每一則總結送出之前確認一次語言。

## 提交與推送

### 提交與驗證

- **commit message 帶著這次的紀錄**：這次的 diff 動到 `content/`、`.claude/skills/`、本檔、`docs/rules/` 或 CLAUDE.md 時，訊息檔要有 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉要求的紀錄；沒有就先補，再 commit。
- pre-commit 或 pre-push 報錯時讀訊息修正，不用 `--no-verify` 繞過。報錯落在這次沒有 staged 的檔案時（`./bin/mdtools cards content/` 掃的是整個工作樹，另一個 session 寫到一半的檔案會擋下這次的 commit），不改也不繞過那個檔案，回報使用者，等對方完成再提交。
- `description` 與 `tags` 是警告層，但不是可以新增的技術債：新增內容一律補齊；修改既有 `content/**` 檔案時，同檔缺這兩個欄位就在同一次變更補上。
- 提交前以本次變更的檔案跑 lint（`./bin/mdtools lint <變更的檔案...>`）判斷本次品質，回報時把既有 warning 與本次新增的分開。分法：`git show HEAD:<檔案>` 存到暫存目錄，兩份各跑一次 lint，規則 ID 加行內容的差集就是本次新增的。
- 提交前跑一次 `./bin/mdtools cards content/`。有 error 時 exit 1，stderr 印 `mdtools cards: N error(s), M warning(s)`；零輸出加 exit 0 是通過。指令後面接了 pipe（`| tail`）時，看到的 exit 是 pipe 最後一個指令的，要看 cards 自己的結果就不接 pipe。
- `.githooks/pre-commit` 的 lint 只跑 `content/` 底下的檔案；根目錄的 AGENTS.md、CLAUDE.md、README.md 與 `docs/rules/` 不跑 lint（它們沒有 Hugo frontmatter，跑了會報 front-matter-missing），fmt 照樣會重排它們的表格。

### 多個 session 共用 repo 時的提交

共用的 git index 裡可能有另一個 session（或另一個 agent）staged 的檔案，直接 `git commit` 會把它們一起提交；對方正在跑 git 時，`git add` 與 `git commit` 會因為 index lock 存在而失敗。執行者看不到別的 session 在不在，所以每次 commit 前先做兩個查得到的檢查：

```bash
git diff --cached --name-only                 # 列出共用 index 裡已經 staged 的檔案
test -e "$(git rev-parse --git-path index.lock)" && echo locked   # worktree 裡 .git 是檔案，lock 的路徑用 rev-parse 取
```

第一條列出這次以外的檔案，或第二條印出 `locked`，就改用私有的 index 提交，不刪除 lock。整段在同一個 shell 裡跑完，`staged` 那一行的比對失敗時 shell 直接結束，不會走到 commit：

```bash
export GIT_INDEX_FILE=<暫存目錄的絕對路徑>/idx   # Claude Code 用 session 的 scratchpad；沒有的話用 mktemp -d 建一個
git read-tree HEAD                             # 以 HEAD 初始化私有 index
git add <這次的檔案...>
staged="$(git diff --cached --name-only | sort)"
[ "$staged" = "$(printf '%s\n' <這次的檔案...> | sort)" ] || { echo "staged 的不只這次的檔案"; unset GIT_INDEX_FILE; exit 1; }
git commit -F <訊息檔>
unset GIT_INDEX_FILE
```

- 私有 index 隔離的是 staging，不隔離工作樹：兩個 session 改了同一個檔案時，`git add` 會把對方在工作樹裡的修改一起提交。這次的檔案在 `git diff HEAD -- <檔案>` 裡出現不是自己寫的段落時，先跟使用者確認。
- 提交之後，共用的 index 裡那些檔案仍是 commit 前的版本；另一個 session 用它 commit 時，會把這次的改動改回去。lock 釋放之後，跑 `git diff --cached --name-only <這次的 commit>~1 -- <這次的檔案...>`：輸出是空的，代表共用 index 裡這幾個檔案只剩 commit 前的版本、沒有對方的 staging，再跑 `git reset -q -- <這次的檔案...>` 讓共用的 index 對齊 HEAD；有輸出代表對方也 staged 了同一個檔案，reset 會清掉它，先跟對方協調。直接跑 `git diff --cached --name-only` 判不出對方有沒有 staged：共用 index 裡存的是 commit 前的版本，這次的檔案一定會列出來。
- 工作結束時 lock 還沒釋放、reset 還沒跑，把要跑的 reset 指令寫進給使用者的最後一則總結。

### 推送

commit 之後直接推送，不另外問使用者（使用者 2026-10-25 的裁定）：blog repo 推 `main`；改過的 skill 照 `docs/rules/skills.md`〈推送前的檢查〉的兩段式預覽推上共用 skill 庫；dotfiles 的部署照 `docs/rules/remote.md`〈遠端機器的操作〉跑 `remote-sync.sh`，它本身會 push。直接推送拿掉的是「問使用者」這一步，不是預覽與檢查：預覽裡有 `[WARNING]`、pre-push 報錯、遠端拒絕時，停下來修，修不了就回報。

推送不了的情形（沒有網路、遠端拒絕、使用者這次的指示明說先不要推），把還沒推送的 commit 寫進給使用者的最後一則總結：`git log @{u}..HEAD --oneline`（`@{u}` 是目前分支追蹤的遠端分支，先 `git fetch -q` 才準）。

### 延到工作結束之後的動作

規則要求的動作做不到當下、要延到之後（lock 釋放後的 reset、還沒推送的 commit、遠端的暫時檔、登記待驗的判定），寫進給使用者的最後一則總結，附要跑的指令。延後的動作沒有其他觀察者，只寫在對話中段或腦中的那一份不會有人回來做。

## 掃描工具的零輸出

grep、lint、檢查腳本回報零命中有兩種成因：真的沒有，或是指令沒有在掃（pattern 打錯、shell 的 `|` 被轉義、變數沒有切詞、腳本裡找不到工具、掃描範圍不含目標）。所以把零輸出當成「通過」之前，先餵它一個已知會命中的輸入（正對照，positive control），確認它在這個寫法下會命中；正對照沒有命中時，修指令，不採用那次的零輸出。工具結尾印「checked N」這類計數的，N 要等於交給它掃描的數量。

## 決策分析：WRAP

需求包含分析、決策、比較、提案，或要比較多個來源才能下結論的查詢時，用 `wrap-decision` skill 的 WRAP 流程；查一個事實、讀一份文件這類單一來源的查詢不用。流程的步驟名照 skill：

- **錨點確認**：對齊核心目標與決策錨點；skill 的閘門判斷這一題要不要往下走。
- **Step 0（資料充足度閘門）**：判斷手上的資料足不足以直接下結論。
- **W（擴增選項，Widen Options）**：列出多個本質不同的選項。
- **R（現實檢驗，Reality-test）**：用來源與反例驗證，不靠直覺。
- **A（拉開距離，Attain Distance）**：評估機會成本與長期影響。
- **P（準備好犯錯，Prepare to be Wrong）**：預先設計失敗回退與監控。
- **絆腳索（tripwire）**：預先設定一個條件，到達時就重新評估決策。

分析與查詢的輸出清楚標示觀察、判讀、策略、結論；引用的來源要可回溯；包含反向驗證（批評、反例、限制）。

## 跨 agent 的設定

本 repo 同時支援 Claude Code 與 Codex（以及其他遵循 AGENTS.md 標準的 agent），目前以 Claude Code 為主。

| 檔案              | 角色                                                       | 誰讀                                                                   |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| `AGENTS.md`       | 規則的入口：每個 session 都用到的規則與分冊路由表          | Codex（自動讀）、Claude Code（經由 CLAUDE.md 的 `@` 匯入）、其他 agent |
| `docs/rules/*.md` | 各類工作的規則分冊                                         | Claude Code（經由 `@` 匯入）、Codex（做那類工作前照路由表自己讀）      |
| `CLAUDE.md`       | Claude Code 專屬的操作，開頭用 `@` 匯入本檔與全部分冊      | Claude Code                                                            |
| `.codex/`         | Codex 的工作簡報（`briefs/`）與讀取順序說明（`README.md`） | Codex；規則以本檔與分冊為準，簡報與規則衝突時照規則                    |

`@<file>` 是 Claude Code 專屬語法，Codex 不解析：Codex 自動讀到的只有本檔，而且讀專案指令檔有位元組上限（見開頭），所以本檔維持在 32 KiB 以內。新增規則時依〈規則的優先序與住址〉決定寫在哪一份；Codex 專屬的規則（如果有）寫在本檔，標明 `[Codex only]`。

**skill 的路徑**：Claude Code 用 `.claude/skills/`，Codex 用 `.agents/skills/`。本 repo 用 directory symlink 共用兩處（`.agents/skills` → `../.claude/skills`）：改 skill 時編輯 `.claude/skills/<name>/`，Codex 經由 symlink 讀到同一份檔案；經由 `.agents/skills/` 的路徑改，改到的也是同一份，但 diff 與 `git log` 都只記在 `.claude/skills/` 底下，所以引用與 `git add` 都寫 `.claude/skills/` 的路徑。Anthropic SKILL.md 的 frontmatter（`name`、`description`）是 Codex SKILL.md frontmatter 的子集，Codex 直接讀 Anthropic 格式。

symlink 失效、需要拆成兩份獨立目錄的訊號：

| 訊號                                         | 拆開之後的差異                                     |
| -------------------------------------------- | -------------------------------------------------- |
| Codex 加了 Anthropic 不認的 frontmatter 欄位 | `.agents/skills/<name>/` 獨立寫，加 Codex 專屬欄位 |
| Anthropic 加了 Codex 不認的 frontmatter 欄位 | `.claude/skills/<name>/` 獨立寫，`.agents/` 拆出去 |
| 需要 Codex 專屬的 `agents/openai.yaml`       | 放在 `.agents/skills/<name>/agents/openai.yaml`    |
| skill 在兩個工具裡的行為要不同               | 拆成兩份，各自客製                                 |

拆開的步驟：刪除 symlink、`cp -r .claude/skills .agents/skills`、各自維護。兩邊的 frontmatter 規格改版時，重新確認相容性。
