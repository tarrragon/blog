# Blog 專案的寫作與工程規則

這份檔案是 blog 專案寫作與工程規則的入口，讀者是在這個 repo 工作的 agent。本檔放每個 session 都會用到的規則：怎麼讀分冊、規則的優先序與住址、改動的級別、寫作類 skill 的叫用、回覆語言、提交與推送（含要先問使用者的情形）、掃描工具的零輸出、決策分析的 WRAP 流程，以及各 agent 讀到的檔案。各類工作才會用到的規則放在 `docs/rules/` 的分冊。

拆成入口與分冊的原因是讀取上限：Codex 自動讀專案指令檔時有位元組上限（`project_doc_max_bytes`，預設 32 KiB），它載入的全部 AGENTS.md 合起來算進同一個上限，超過的部分不會進它的 context。所以本檔要維持在這個上限以內（`wc -c AGENTS.md` 小於 32768），新增的規則寫進對應的分冊。

## 怎麼讀分冊

先看自己的 context 裡有沒有 `docs/rules/` 分冊的全文。Claude Code 經由 CLAUDE.md 開頭的 `@` 匯入，session 一開始就載入了本檔與全部分冊；Codex 與其他只自動讀 AGENTS.md 的 agent 沒有。context 裡已經有分冊全文的，不必再打開分冊，做事時照分冊的規則做。沒有的，動手之前依這次要改的路徑讀下表對應的分冊，整份讀完；這次的改動對到好幾列時，每一列的分冊都讀。

| 這次要改的路徑                         | 要讀的分冊                                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `content/` 底下的任何檔案              | `content-folders.md`、`writing.md`、`sentences.md`、`writing-process.md`、`review.md`、`markdown.md` |
| `.claude/skills/` 底下的任何檔案       | `skills.md`、`sentences.md`、`writing-process.md`、`review.md`                                       |
| 本檔、`docs/rules/` 的分冊、CLAUDE.md  | `sentences.md`、`writing-process.md`、`review.md`                                                    |
| `scripts/mdtools/`                     | `markdown.md`                                                                                        |
| dotfiles repo，或經由 SSH 操作遠端機器 | `remote.md`                                                                                          |

只打算做排版級的改動（〈改動的級別〉）時，`content/` 那一列只讀 `markdown.md`；改完照〈寫作類 skill 的叫用〉確認級別，不是排版級就把那一列的分冊讀完。只讀檔案、回答問題而不改任何檔案時，不必讀分冊。

規則之間用〈段名〉互相引用；段名在另一份檔案時，前面寫出檔名（`writing.md`〈開場列出這篇討論的內容〉）。

## 規則的優先序與住址

**優先序**，由高到低：使用者在這次對話裡的指示；本檔與 `docs/rules/` 的分冊；`compositional-writing`（寫作）與 `wrap-decision`（分析、決策、比較與提案，見〈決策分析：WRAP〉）這些 skill；其他 skill。

**住址**：每一條規則、每一個被兩條以上規則用到的概念，都只寫在一個位置，其他位置用連結指過去。同一件事寫在兩個位置時，沒有任何工具會偵測兩份分歧：修改的人只改其中一份，照著舊的那一份工作的 agent 會做錯。摘要與轉述也是副本：路由表轉述分冊的觸發條件、入口重述分冊的掃描範圍，都會在原文改動之後過期。分工如下：

| 內容                                                                   | 住址                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------ |
| Claude Code 與 Codex 共用的寫作規則與工程規則                          | 本檔（每個 session 都用到的）與 `docs/rules/` 的分冊   |
| Claude Code 專屬的操作（範圍列在 CLAUDE.md 開頭）                      | CLAUDE.md                                              |
| 可以照著執行的偵測細節（字句層 pattern、探針的派發與判讀、審查 frame） | 對應的 skill；規則檔寫規則與判斷標準，並連到 skill     |
| 超過一條指令、或帶分支的操作程序                                       | `bin/` 的工具與 `bin/tests/` 的測試                    |
| 規則的推導、實測紀錄、事件經過與量測數字                               | `content/report/` 的卡；規則檔寫規則與理由，連到那張卡 |
| 工具自己的行為（參數、內部邏輯、維護方式）                             | 工具的檔頭註解、README 或它的 skill                    |

例外是刻意建立、而且有工具比對的副本：skill 的 principle 卡是 report 卡的副本（`scripts/principle-mirror-check.py` 比對），`content/skills/` 是 skill 的鏡像（`bin/skill-mirror` 產生）。

**新增或修改規則時**，在本檔或分冊寫出四件事：規則本身、執行者用來判斷的標準、判斷之後的處置、讓執行者判得出適用邊界的理由；推導過程與「先前怎麼寫、後來為什麼改」寫進 report 卡或 commit message。寫的時候守四條：

- **程序寫成工具**：要執行者照順序跑兩條以上指令、或依輸出走不同分支的程序，寫成 `bin/` 的工具並在 `bin/tests/` 附測試，規則檔只寫什麼時候跑、輸出怎麼讀、非零的 exit 怎麼處置。規則檔裡的指令沒有測試，寫的人自己也常常沒跑過，而照做的 agent 會逐字照抄。單一條、沒有分支的指令（一條 `rg`、一條 `git log`）可以留在規則檔，寫之前照〈掃描工具的零輸出〉跑一次正對照。
- **共用的概念先定義再引用**：兩條以上的規則要用到同一個概念（改動的大小、要停下來問使用者的時機）時，在一個位置定義並命名，其他規則寫名字、連過去，不各寫一份例外。「只有 N 種」這類封閉的列舉只寫在那個唯一的住址，因為別處的規則一新增情形，它就默默失效。
- **觸發條件寫成查得到的事實**（指令的輸出與 exit、檔案、diff、frontmatter 欄位、這次要改的路徑），不寫成執行者的身分或主觀狀態（「拿不準時」「懷疑時」）。非用主觀狀態不可時，加一句「執行者自認不成立，不改變本款結果」，因為會誤判的人正是不認為自己在誤判的人。
- **放對檔案**：加一節之前問兩件事：這一節的修改理由在不在這份檔案既有的主題裡（不在就放進對應的分冊或新開一份）；Codex 需不需要它（需要就寫進本檔或分冊，只有 Claude Code 才有的操作才寫進 CLAUDE.md）。

依據：[規則檔的修法逐輪製造新歧義：程序寫成有測試的工具，共用的概念只定義一次](/report/rule-patches-breed-new-ambiguity/)。

## 改動的級別

叫用寫作類 skill、字句層掃描的紀錄、多輪審查、skill 的版號，這四條規則都依一次改動的大小決定要不要做。改動的大小分成三級，四條規則各自在自己的位置寫「哪一級以上要做」，級別本身只在這裡定義：

- **排版級**：`bin/changed-lines --level <這次的檔案...>` 的最後一行是 `level: 排版級`。工具判的是 diff 上的事實：每一處改動的新增行與刪除行一一對應，每一對去掉空白、標點、表格符號與連結網址之後相同，或只有一個字元被替換成另一個字元（錯字），或只改了 frontmatter 的 `weight`、`date` 的值。刪掉一句、插入一個字、新檔都不是排版級；完整的判定條件在工具的檔頭。
- **措辭級**：不是排版級，而且規則類文件（本檔、`docs/rules/` 的分冊、CLAUDE.md、`.claude/skills/`）裡每一條規則的條件、判斷標準與處置都沒有變。`content/` 的文章不訂規則，它的改動不是排版級時就是措辭級。
- **規則級**：規則類文件裡，至少一條規則的條件、判斷標準或處置被新增、刪除或改動。

措辭級與規則級的分界要讀語意，工具判不了，所以每一級都在 commit message 留下判定：排版級貼上 `bin/changed-lines --level` 的輸出（含「錯字候選」那幾行，讓讀 commit 的人看得到每一處被替換的字）；措辭級寫出改動的段落，以及「條件、判斷標準、處置都沒變」；規則級寫出改了哪一條規則的哪一項。

## 寫作類 skill 的叫用

寫作任務常常以「幫我改這段」「補一句」「這裡讀起來怪怪的」進來，這些措辭比對不到 `compositional-writing` 的 `description` 裡任何一個觸發詞，而每一處改寫都可能帶進字句層 bank（`compositional-writing` 的 SKILL.md「字句層 keyword bank（完整清單）」那一節列的反模式類別與 rg 指令）的任何一類違規。所以要改 `content/`、`.claude/skills/`、本檔、`docs/rules/` 或 CLAUDE.md 的文字之前，叫用 `compositional-writing`，不等 description 比對自動觸發。Claude Code 用 Skill tool 叫用；Codex 讀 `.agents/skills/compositional-writing/SKILL.md` 全文。

只打算做排版級的改動（改錯字、標點、連結網址、表格對齊、空白、frontmatter 的 `weight` 與 `date`）時可以不叫用。改完跑 `bin/changed-lines --level <這次的檔案...>`：最後一行不是 `level: 排版級` 時，代表改動超出了排版，叫用 skill、照下一段跑完掃描再提交。

**改完之後的掃描**：措辭級以上的改動，照 `docs/rules/writing-process.md`〈文章產出流程〉的字句層掃描跑一次 bank，掃描對象是這次的新增行：

```bash
bin/changed-lines <這次的檔案...> > <暫存目錄>/added.txt   # 新增行，不帶 diff 的 + 前綴；新檔整份都算
```

它涵蓋已經 staged、還沒 staged 的改動與還沒 add 的新檔，不寫 git index。stderr 的 `changed-lines: N added line(s) from M file(s)` 裡，M 要等於給的檔案數、N 不是 0，才照 bank 對 `added.txt` 跑。逐類表照 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉留下。

## 回覆語言

給使用者的每一則回覆都用繁體中文，包括工具呼叫之間的短句與工作結束時的總結。指令、程式識別字、錯誤訊息原文、產品與服務名稱保留原文，其餘敘述用中文。前文是一長串英文的指令、log、錯誤訊息與程式碼時，最後的總結最容易漂成英文，所以每一則總結送出之前確認一次語言。

## 提交與推送

### 提交

- **commit message 帶著這次的紀錄**：這次的 diff 動到 `content/`、`.claude/skills/`、本檔、`docs/rules/` 或 CLAUDE.md 時，commit message（或同一個 commit 裡給讀者看的 work-log 文章）要有〈改動的級別〉的判定，以及 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉要求的紀錄；沒有就先補，再 commit。排版級的改動只貼級別的判定。
- **`description` 與 `tags`**：新增的 `content/` 檔案一律補齊；修改既有 `content/` 檔案時，同檔缺這兩個欄位就在同一次變更補上。lint 把它們報在警告層，但它們不是可以新增的技術債。
- **lint**：這次動到 `content/` 的檔案時，提交前跑 `bin/lint-delta <這次的 content/ 檔案...>`。它只印這次新增的問題，既有的只計數；exit 1 代表這次新增了 error，修掉再提交，新增的 warn 寫進回報。全量 lint（`./bin/mdtools lint content/`）只用來觀察歷史基線，不用來判斷這次的品質。
- **提交**：用 `bin/commit-files -F <訊息檔> <這次的檔案...>`，不直接 `git commit`。共用的 git index 裡可能有另一個 session（或另一個 agent）staged 的檔案，直接 commit 會把它們一起提交；這支工具經由私有 index 只提交列出的檔案，提交後讓共用 index 對齊。檔案寫從 repo 根目錄起算的路徑，刪除的檔案與改名的新舊兩個路徑都列。
  - 跑之前先跑 `git diff HEAD -- <這次的檔案...>`，把 diff 跟這次自己做過的編輯逐段對照：私有 index 隔離的是 staging，不隔離工作樹，另一個 session 改了同一個檔案時，它在工作樹裡的修改會一起提交。有對不上的段落時，照〈要先問使用者的情形〉處理。自認都是自己寫的不改變本款：對照的是 diff 與編輯紀錄，不是印象。
  - exit 1 是沒有提交，讀 stderr 修正（清單裡有目錄、檔案內容跟 HEAD 相同，或 hook 報錯）。exit 3 是已經提交、共用 index 還沒對齊，照它印的 `[FOLLOW-UP]` 那幾行做；工作結束時還做不了，寫進〈延到工作結束之後的動作〉。
- **pre-commit 報錯**：讀訊息修正，不用 `--no-verify` 繞過。報錯落在這次沒有改過的檔案時（hook 的 `mdtools cards` 掃整個 `content/` 工作樹，另一個 session 寫到一半的檔案會擋下這次的 commit），不改也不繞過那個檔案，這次不提交，把要提交的檔案與擋下它的報錯寫進〈延到工作結束之後的動作〉；不在 session 裡反覆重試等它消失。

### 推送

commit 之後直接推送，不另外問使用者：使用者已經授權推送。這次的指示另有要求時（「先不要推」「只推 blog」），照這次的指示；要停下來問的情形見〈要先問使用者的情形〉。

- **blog repo**：跑 `bin/push-main --mine <這次 session 提交的 commit...>`（`bin/commit-files` 每次提交都印出它的 hash）。它先 fetch；目前的 checkout 在分支或 worktree 上時，它把那個分支 fast-forward 進 `main`；推送範圍裡有 `--mine` 以外的 commit 時不推送、exit 3。分支或 worktree 用完時，先 `git worktree remove <路徑>`，再 `git branch -d <分支>`：worktree 還在時刪不掉它的分支。
- **共用 skill 庫**：改過的 skill 照 `docs/rules/skills.md`〈推送前的檢查〉推（`skill-sync push` 的兩段式：`echo n` 取預覽、讀完再 `echo y`）。`echo y` 是 agent 自己執行的套用步驟，不是問使用者。`docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 不推。
- **dotfiles**：部署照 `docs/rules/remote.md`〈遠端機器的操作〉跑 `remote-sync.sh`，它本身會 push。

直接推送拿掉的是「問使用者」這一步，不是檢查：工具回非零的 exit、預覽裡有 `[WARNING]`、pre-push 報錯、遠端拒絕時，停下來修，修不了就寫進〈延到工作結束之後的動作〉。還沒推送的 commit 用 `git log --branches --not --remotes --oneline` 列出：它列出所有分支上還沒推到任何遠端的 commit，目前在 `main` 或其他分支、fetch 成功或失敗時都適用。

### 要先問使用者的情形

這一節是「停下來等使用者決定」的唯一住址：別處的規則碰到這類情形時連到這裡，新增一種情形時加在這裡。下列情形停下來，把指定的材料給使用者，等使用者決定再往下做：

- **提交前**，`git diff HEAD -- <這次的檔案...>` 有段落對不上這次自己做過的編輯：給那幾段 diff，由使用者決定是不是一起提交。
- **推送 blog 時**，`bin/push-main` exit 3：給它列出的 commit（別的 session 還沒推送的），由使用者決定要不要一起推。
- **同步 skill 時**，`[DIVERGED]` 或 `[CONFLICT]` 比對兩邊的歷史仍判斷不出哪一邊較新：給兩邊的 `git log`（`docs/rules/skills.md`〈同步時的判斷〉）。
- **要把 `docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 推上共用庫時**：那些 skill 依賴本 blog 的結構，推上去之後別的專案用不了。

下列動作沒有使用者在這次的指示裡明說就不做，也不主動提議：`skill-sync push --force`（它拿掉警告之後的停點、放行可攜性閘門），以及替一支 skill 建 `content/skills/` 的公開鏡像。

### 延到工作結束之後的動作

規則要求的動作做不到當下、要延到之後時（`bin/commit-files` 的 `[FOLLOW-UP]`、還沒推送的 commit、因為別人的檔案擋下而沒提交的改動、遠端的暫時檔、登記待驗的判定、沒有模組 Backlog 可記的未完成工作），寫進給使用者的最後一則總結，附要跑的指令。延後的動作沒有其他觀察者，只寫在對話中段的那一份不會有人回來做。

## 掃描工具的零輸出

grep、lint、檢查腳本回報零命中有兩種成因：目標確實不存在，或是指令沒有在掃（pattern 打錯、shell 的 `|` 被轉義、變數沒有切詞、zsh 的 glob 沒有匹配而整條指令沒執行、腳本裡找不到工具、掃描範圍不含目標、餵進去的檔案集是空的）。所以把零輸出當成「通過」之前，先做兩件事：確認餵進去的檔案集不是空的（行數或檔案數不是 0），再餵一個已知會命中的輸入（正對照，positive control），確認它在這個寫法下會命中。正對照沒有命中時，修指令，不採用那次的零輸出。

本 repo `bin/` 底下的工具在結尾印計數（`checked N`、`from M file(s)` 這類），N 與 M 要等於交給它掃描的數量；計數沒有印出來，代表工具中途中止，不代表通過。

## 決策分析：WRAP

需求要在幾個選項或幾種解釋之間取捨才下得了結論時（分析、決策、比較、提案），用 `wrap-decision` skill 的 WRAP 流程；步驟名與各步驟要做的事照 skill。查一個事實、讀一份文件、交叉核對同一個事實的幾個來源（答案只有一個，核對的是來源是否正確）不用。寫一篇排查紀錄時，文章交代的是已經做完的原因分析，不用 WRAP；寫作中要替讀者或使用者在幾個方案之間做新的選擇時才用。

分析的輸出清楚標示觀察、判讀、策略、結論；引用的來源要可回溯；包含反向驗證（批評、反例、限制）。

## 各 agent 讀到的檔案

本 repo 同時支援 Claude Code 與 Codex（以及其他遵循 AGENTS.md 標準的 agent），目前以 Claude Code 為主。

| 檔案              | 角色                                                       | 誰讀                                                                   |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| `AGENTS.md`       | 規則的入口：每個 session 都用到的規則與分冊路由表          | Codex（自動讀）、Claude Code（經由 CLAUDE.md 的 `@` 匯入）、其他 agent |
| `docs/rules/*.md` | 各類工作的規則分冊                                         | Claude Code（經由 `@` 匯入）、Codex（照〈怎麼讀分冊〉自己讀）          |
| `CLAUDE.md`       | Claude Code 專屬的操作，開頭用 `@` 匯入本檔與全部分冊      | Claude Code                                                            |
| `.codex/`         | Codex 的工作簡報（`briefs/`）與讀取順序說明（`README.md`） | Codex；規則以本檔與分冊為準，簡報與規則衝突時照規則                    |

`@<file>` 是 Claude Code 專屬語法，Codex 不解析。新增規則時依〈規則的優先序與住址〉決定寫在哪一份；Codex 專屬的規則（如果有）寫在本檔，標明 `[Codex only]`。兩個 agent 共用同一份 skill 目錄的方式與拆開的訊號，在 `docs/rules/skills.md`〈Claude Code 與 Codex 共用的 skill 目錄〉。
