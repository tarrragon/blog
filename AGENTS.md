# Blog 專案的寫作與工程規則

這份檔案是在這個 repo 工作的 agent 每個 session 都會讀到的入口：做哪一件事之前要讀哪一份分冊、規則的優先序、改動的級別、寫作類 skill 的叫用、回覆語言、提交與推送、要先問使用者與不能自己做的動作、延後的動作、掃描工具的零輸出、破壞性指令，以及決策分析的流程。其餘的規則寫在 `docs/rules/` 的分冊。本檔用一句話帶過、連到分冊的規則，跟分冊寫得不一致時以分冊為準。

## 怎麼讀分冊

分冊不在 session 啟動時載入。做下列的事之前，讀它對應的分冊（檔案是 `docs/rules/<名字>.md`），每一份整份讀完；目前的對話裡看得到那一份的完整內容時不必重讀。

- **改某個路徑的檔案（含新建），或 prompt 要求審查它（prompt 寫明範圍以外的檔案不讀時除外）**：下面路徑表對到的每一列。
- **回答這個 repo 的規則怎麼規定**：`rg -n '<關鍵詞>' AGENTS.md docs/rules` 命中的段落與它連到的段落，這一項不必整份讀。
- **提交或推送**：`commit-push`。
- **寫或改含刪除、移動或覆寫的 shell 指令（腳本、規則檔、skill 裡的都算），或這類動作的目標不是字面絕對路徑**：`destructive-commands`。
- **改 dotfiles repo，或經由 SSH 操作遠端機器**：`remote`。
- **用 Agent tool 派 agent、寫 memory 目錄**：`claude-code`。

路徑表（`bin/rule-route <路徑...>` 用同一張表列出分冊）：

- `content/`：`content-folders`、`writing`、`sentences`、`writing-process`、`review`、`markdown`
- `.claude/skills/`：`skills`、`sentences`、`writing-process`、`review`
- `AGENTS.md`、`CLAUDE.md`、`docs/rules/`、`bin/rule-route`：`rule-authoring`、`sentences`、`writing-process`、`review`
- `scripts/mdtools/`、`.githooks/`、`hugo.toml`：`markdown`
- `data/autolink.toml`、`bin/autolink-dict`：`markdown`
- `bin/skill-mirror`、`scripts/principle-mirror-check.py`：`skills`
- `bin/`：`rule-authoring`
- `.claude/hooks/`、`.claude/settings.json`、`.claude/settings.local.json`：`rule-authoring`、`claude-code`

Claude Code 的 hook 在寫入 repo 內的檔案、`bin/commit-files`、`bin/push-main` 與 `ssh` 之前檢查對應的分冊，有還沒讀的就拒絕，拒絕理由列出那幾份；其餘動作，以及 Codex 與其他 agent，沒有這道檢查，照這一節自己讀。

規則之間用〈段名〉互相引用；段名在另一份檔案時，前面寫出檔名（`writing.md`〈開場列出這篇討論的內容〉）。

## 規則的優先序與住址

**優先序**，由高到低：使用者在這次對話裡的指示；本檔與 `docs/rules/` 的分冊；`compositional-writing`（寫作）與 `wrap-decision`（分析、決策、比較與提案，見〈決策分析：WRAP〉）這些 skill；其他 skill。

**住址**：各種內容寫在哪裡、入口與分冊怎麼分工、新增規則時要寫出什麼，在 `docs/rules/rule-authoring.md`。

## 改動的級別

級別要改完之後跑 `bin/changed-lines --level` 才查得到，所以它只用來決定改完之後要做的事：commit message 的紀錄、字句層掃描、多輪審查、skill 的版號。動手之前的步驟（讀分冊、叫用寫作類 skill）不看級別，改動多小都照做。用到級別的規則各自在自己的位置寫「哪一級以上要做」，級別與它用到的兩個名字只在這裡定義：

- **規則類文件**：本檔、`docs/rules/` 的分冊、CLAUDE.md、`bin/rule-route` 的 `ROUTES` 表、`.claude/skills/`，以及被規則檔指定為單一真實來源的 spec：`content/posts/markdown-writing-spec.md`、`content/posts/backlog-format-spec.md`。新增這樣的 spec 時加進這份清單。
- **書面產出**：`content/`、`.claude/skills/`、本檔、`docs/rules/`、`bin/rule-route` 的 `ROUTES` 表與 CLAUDE.md 底下的文字。

三個級別：

- **排版級**：`bin/changed-lines --level <這次的檔案...>` 的最後一行是 `level: 排版級`，而且執行者逐一確認了它印的每一處「錯字候選：舊→新」都是同一個詞的錯字與正字；工具判定的條件在它的檔頭。刪掉一句、插入一個字、補一個 frontmatter 欄位（例如補 `description`）、新檔都不是排版級。有一處錯字候選換的是另一個詞，這次就不是排版級。
- **措辭級**：規則類文件以外的書面產出（`content/` 的文章），改動不是排版級的。
- **規則級**：規則類文件裡，改動不是排版級的。改的是措辭還是規則的意思不分開判：分開判要執行者判語意，而那條分界本身就是規則檔反覆被讀成兩種意思的位置；一律算規則級，代價是規則檔的措辭改動也照規則級走審查。

每一級都在 commit message 留下判定：排版級貼上 `bin/changed-lines --level` 的輸出（含「錯字候選」那幾行，讓讀 commit 的人看得到每一處被替換的字）；措辭級與規則級寫出級別與改動的段落，規則級另外寫出改到哪幾條規則。

## 寫作類 skill 的叫用

要改書面產出（〈改動的級別〉）的文字之前，叫用 `compositional-writing`，不等 description 比對自動觸發：使用者常寫「幫我改這段」「補一句」，agent 拿這些措辭比對 description 時對不到它的觸發詞。改錯字、標點或連結網址也照做，因為級別要改完才查得到。Claude Code 用 Skill tool 叫用；Codex 讀 `.agents/skills/compositional-writing/SKILL.md` 全文。不是排版級的改動，改完照 `docs/rules/writing-process.md`〈字句層掃描的檔案集〉掃一次。

## 回覆語言

給使用者的每一則回覆都用繁體中文，包括工具呼叫之間的短句與工作結束時的總結。指令、程式識別字、錯誤訊息原文、產品與服務名稱保留原文，其餘敘述用中文。前文是一長串英文的指令、log、錯誤訊息與程式碼時，最後的總結最容易漂成英文，所以每一則總結送出之前確認一次語言。

## 提交與推送

### 提交

在這個 repo 提交時用 `bin/commit-files -F <訊息檔> <這次的檔案...>`，不加 `--no-verify`，也不直接跑 `git commit`。提交之前要留的紀錄與工具輸出的處置在 `docs/rules/commit-push.md`〈提交〉。

### 推送

commit 之後直接推送，不另外問使用者：使用者已經授權推送。指示另有要求時（「先不要推」「只推 blog」），照這次的指示。指令與工具輸出的處置在 `docs/rules/commit-push.md`〈推送〉。

### 要先問使用者的情形

工具印出 `[ASK-USER]`、`git diff HEAD -- <這次的檔案...>` 有段落不是這次自己做的編輯，或別的規則寫「照〈要先問使用者的情形〉」時，停下來，讀 `docs/rules/commit-push.md` 的同名段落，把它指定的材料給使用者，等使用者決定再往下做。

## 沒有使用者明說就不做的動作

這一節是這類動作的唯一住址。下列動作沒有使用者在這次的指示裡明說就不做，也不主動提議、不停下來問：`skill-sync push --force`；替一支 skill 建 `content/skills/` 的公開鏡像；把 `docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 推上共用庫（那些 skill 依賴本 blog 的結構，推上去之後別的專案用不了）；把工作樹裡不是這次自己做的改動還原或蓋掉（`git checkout --`、`git checkout .`、`git restore`、`git stash`、`git reset --hard`、`git clean`、用 Write 整份重寫），那些改動可能是另一個 session 還沒提交的工作，蓋掉之後沒有任何紀錄；搬移或改名 `content/` 底下含 `_index.md` 的資料夾（任何一種都算，例如收進或移出大分類、建立或撤掉大分類、把幾個模組合成一個模組底下的系列子資料夾、在模組之間或系列子資料夾之間搬子資料夾；`docs/rules/content-folders.md`〈文章放在哪一個資料夾〉），首頁的分類結構、網址與讀者的閱讀路線由使用者決定，搬錯了再搬一次時每一頁要多一筆 `aliases`；使用者提出要搬之後，跑 dry-run 與 `bin/empty-sections` 提供材料不算主動提議。

## 延到工作結束之後的動作

規則要求的動作做不到當下、要延到之後時（`bin/commit-files` 的 `[FOLLOW-UP]`、還沒推送的 commit、因為別人的檔案擋下而沒提交的改動、印了 `[ASK-USER]` 而等使用者決定的提交、`bin/converge-branch` 還沒處理的 `[ASK-USER]` 與還沒跑的 `[NEXT]`、遠端的暫時檔、登記待驗的判定、沒有模組 Backlog 可記的未完成工作），寫進給使用者的最後一則總結，附要跑的指令。延後的動作沒有其他觀察者，只寫在對話中段的那一份不會有人回來做。

## 掃描工具的零輸出

grep、lint、檢查腳本回報零命中有兩種成因：目標確實不存在，或是指令沒有在掃（pattern 打錯、shell 的 `|` 被轉義、變數沒有切詞、zsh 的 glob 沒有匹配而整條指令沒執行、腳本裡找不到工具、掃描範圍不含目標、餵進去的檔案集是空的）。所以把零輸出當成「通過」之前，先做兩件事：確認餵進去的檔案集不是空的（行數或檔案數不是 0），再餵一個已知會命中的輸入（正對照，positive control），確認它在這個寫法下會命中。正對照沒有命中時，修指令，不採用那次的零輸出。

檔頭寫了計數格式的 `bin/` 工具，計數的讀法在 `docs/rules/writing-process.md`〈掃描工具的計數〉；計數沒有印出來，代表工具中途中止，不代表通過。

## 破壞性指令的目標寫在指令文字裡，檢查與刪除分成兩次執行

agent 下 shell 指令刪除、移動或覆寫已經存在的檔案時守下面的規則。寫進 `/dev/null` 與暫存目錄裡這次工作自己建的檔不算。**暫存目錄**指 repo 以外、這次工作專屬的目錄：Claude Code 是系統提示列出的 scratchpad，其他 agent 用 `mktemp -d` 新建，腳本自己用 `mktemp` 建的也算。執行 repo 內的工具（`bin/skill-mirror`、`mdtools fmt`、`bin/content-move --apply`）時，目標由工具決定，不套「目標寫成字面的絕對路徑」；有預覽或 dry-run 的先跑那一步，跟會改檔的那一次分成兩次執行。

- **目標寫成字面的絕對路徑**：目標由變數、glob、`find` 的條件、管線或直譯器決定時，核准這次呼叫的人讀不到要刪什麼，展開失敗時刪除範圍還會改變。目標要靠條件選出時，先在一次工具呼叫裡只列出目標，下一次呼叫用清單上的字面路徑刪。
- **檢查與刪除分成兩次執行**：掃描、正對照、驗證這類唯讀的指令，不在同一次工具呼叫裡串進刪除或覆蓋，否則核准一次檢查就等於核准了那次刪除。
- **不跑 `git clean`**：它會刪到另一個 session 還沒提交的新檔。
- **手動建的正對照假資料留著不刪**：放在暫存目錄底下的新子目錄（`mktemp -d <暫存目錄>/pc.XXXXXX`）。
- **shell 腳本用變數組出目標時**，每一個變數都寫成 `${X:?}`，變數為空時腳本會中止。

適用範圍的細節、哪些目標不算字面路徑，以及長清單、腳本與假資料的處置，在 `docs/rules/destructive-commands.md`。

## 決策分析：WRAP

需求要在幾個選項或幾種解釋之間取捨才下得了結論時（分析、決策、比較、提案），用 `wrap-decision` skill 的 WRAP 流程；步驟名與各步驟要做的事照 skill。查一個事實、讀一份文件、交叉核對同一個事實的幾個來源（答案只有一個，核對的是來源是否正確）不用。寫一篇排查紀錄時，文章交代的是已經做完的原因分析，不用 WRAP；寫作中要替讀者或使用者在幾個方案之間做新的選擇時才用。

分析的輸出清楚標示觀察、判讀、策略、結論；引用的來源要可回溯；包含反向驗證（批評、反例、限制）。
