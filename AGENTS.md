# Blog 專案的寫作與工程規則

這份檔案是 blog 專案寫作與工程規則的入口，讀者是在這個 repo 工作的 agent。本檔放每個 session 都會用到的規則：怎麼讀分冊、規則的優先序與住址、改動的級別、寫作類 skill 的叫用、回覆語言、提交與推送（含要先問使用者的情形與沒有使用者明說就不做的動作）、掃描工具的零輸出、破壞性指令的目標寫在指令文字裡（以及檢查與刪除分成兩次執行）、決策分析的 WRAP 流程，以及各 agent 讀到的檔案。各類工作才會用到的規則放在 `docs/rules/` 的分冊。

拆成入口與分冊的原因是讀取上限：Codex 自動讀專案指令檔時有位元組上限（`project_doc_max_bytes`，預設 32 KiB），它載入的全部 AGENTS.md 合起來算進同一個上限，超過的部分不會進它的 context。所以本檔要維持在這個上限以內（`wc -c AGENTS.md` 小於 32768），新增的規則寫進對應的分冊；任何 session 都可能碰到、觸發條件是一個動作而不是這次要改的路徑、所以〈怎麼讀分冊〉的路由表對不到的規則（例如執行破壞性的 shell 指令時），寫進本檔。

## 怎麼讀分冊

動手改任何檔案之前，依這次要改的路徑讀下表對應的分冊，每一份整份讀完；某一份分冊的全文已經在 context 裡的，那一份不必重讀。Claude Code 經由 CLAUDE.md 開頭的 `@` 匯入，session 一開始就有全部分冊的全文；Codex 與其他只自動讀 AGENTS.md 的 agent 沒有。這次的改動對到好幾列時，每一列的分冊都讀；新建的檔案照它的路徑對表。

| 這次要改的路徑                                          | 要讀的分冊                                                                                           |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `content/` 底下的任何檔案                               | `content-folders.md`、`writing.md`、`sentences.md`、`writing-process.md`、`review.md`、`markdown.md` |
| `.claude/skills/` 底下的任何檔案                        | `skills.md`、`sentences.md`、`writing-process.md`、`review.md`                                       |
| 本檔、`docs/rules/` 的分冊、CLAUDE.md                   | `sentences.md`、`writing-process.md`、`review.md`                                                    |
| `scripts/mdtools/`、`.githooks/`、`hugo.toml`           | `markdown.md`                                                                                        |
| `bin/skill-mirror`、`scripts/principle-mirror-check.py` | `skills.md`                                                                                          |
| dotfiles repo，或經由 SSH 操作遠端機器                  | `remote.md`                                                                                          |

只讀檔案、回答問題而不改任何檔案時，不必讀分冊。

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

- **程序寫成工具**：要執行者照順序跑兩條以上指令、或依輸出走不同分支的程序，寫成 `bin/` 的工具並在 `bin/tests/` 附測試，規則檔只寫什麼時候跑、輸出怎麼讀、非零的 exit 怎麼處置。規則檔裡的指令沒有測試，寫的人自己也常常沒跑過，而照做的 agent 會逐字照抄。測試的輸出要是 `OK` 而且沒有 skipped：跳過的測試照樣印 `OK`，等於沒有在測。單一條、沒有分支的指令（一條 `rg`、一條 `git log`）可以留在規則檔，寫之前照〈掃描工具的零輸出〉跑一次正對照。
- **共用的概念先定義再引用**：兩條以上的規則要用到同一個概念（改動的大小、要停下來問使用者的時機）時，在一個位置定義並命名，其他規則寫名字、連過去，不各寫一份例外。定義時寫出這個概念在工作流程的哪一步之後才查得到：用它當觸發條件的規則，動作不能排在那一步之前。「只有 N 種」這類封閉的列舉只寫在那個唯一的住址，因為別處的規則一新增情形，它就默默失效。
- **觸發條件寫成查得到的事實**（指令的輸出與 exit、檔案、diff、frontmatter 欄位、這次要改的路徑），不寫成執行者的身分或主觀狀態（「拿不準時」「懷疑時」）。非用主觀狀態不可時，加一句「執行者自認不成立，不改變本款結果」，因為會誤判的人正是不認為自己在誤判的人。
- **放對檔案**：加一節之前問兩件事：這一節的修改理由在不在這份檔案既有的主題裡（不在就放進對應的分冊或新開一份）；Codex 需不需要它（需要就寫進本檔或分冊，只有 Claude Code 才有的操作才寫進 CLAUDE.md）。

依據：[規則檔的修法逐輪製造新歧義：程序寫成有測試的工具，共用的概念只定義一次](/report/rule-patches-breed-new-ambiguity/)、[規則的修法逐句驗證會通過、套到案例上才互撞：改完才查得到的事實管不了動手之前的步驟，修完要拿任務重走](/report/rule-fixes-pass-per-sentence-and-collide-per-case/)。

## 改動的級別

級別要改完之後跑 `bin/changed-lines --level` 才查得到，所以它只用來決定改完之後要做的事：commit message 的紀錄、字句層掃描、多輪審查、skill 的版號。動手之前的步驟（讀分冊、叫用寫作類 skill）不看級別，改動多小都照做。用到級別的規則各自在自己的位置寫「哪一級以上要做」，級別與它用到的兩個名字只在這裡定義：

- **規則類文件**：本檔、`docs/rules/` 的分冊、CLAUDE.md、`.claude/skills/`，以及被規則檔指定為單一真實來源的 spec：`content/posts/markdown-writing-spec.md`、`content/posts/backlog-format-spec.md`。新增這樣的 spec 時加進這份清單。
- **書面產出**：`content/`、`.claude/skills/`、本檔、`docs/rules/` 與 CLAUDE.md 底下的文字。

三個級別：

- **排版級**：`bin/changed-lines --level <這次的檔案...>` 的最後一行是 `level: 排版級`，而且執行者逐一確認了它印的每一處「錯字候選：舊→新」都是同一個詞的錯字與正字。工具判的是 diff 上的事實：每一處改動的新增行與刪除行一一對應，每一對去掉空白、標點、表格符號與連結網址之後相同、只有一個字元被替換（數字、拉丁字母、否定與情態字的替換不算），或只改了 frontmatter 裡 `weight`、`date` 的值；完整的條件在工具的檔頭。刪掉一句、插入一個字、補一個 frontmatter 欄位（例如補 `description`）、新檔都不是排版級。有一處錯字候選換的是另一個詞，這次就不是排版級。
- **措辭級**：規則類文件以外的書面產出（`content/` 的文章），改動不是排版級的。
- **規則級**：規則類文件裡，改動不是排版級的。改的是措辭還是規則的意思不分開判：分開判要執行者判語意，而那條分界本身就是規則檔反覆被讀成兩種意思的位置；一律算規則級，代價是規則檔的措辭改動也照規則級走審查。

每一級都在 commit message 留下判定：排版級貼上 `bin/changed-lines --level` 的輸出（含「錯字候選」那幾行，讓讀 commit 的人看得到每一處被替換的字）；措辭級與規則級寫出級別與改動的段落，規則級另外寫出改到哪幾條規則。

## 寫作類 skill 的叫用

寫作任務常常以「幫我改這段」「補一句」「這裡讀起來怪怪的」進來，這些措辭比對不到 `compositional-writing` 的 `description` 裡任何一個觸發詞，而每一處改寫都可能帶進字句層 bank（`compositional-writing` 的 SKILL.md「字句層 keyword bank（完整清單）」那一節列的反模式類別與 rg 指令）的任何一類違規。所以要改書面產出（〈改動的級別〉）的文字之前，叫用 `compositional-writing`，不等 description 比對自動觸發。Claude Code 用 Skill tool 叫用；Codex 讀 `.agents/skills/compositional-writing/SKILL.md` 全文。

改錯字、標點或連結網址也照這一條叫用：動手之前不知道改動會停在哪一級，改一個字也可能改到規則。

**改完之後的掃描**：不是排版級的改動（措辭級與規則級），照 `docs/rules/writing-process.md`〈文章產出流程〉的字句層掃描跑一次 bank，掃描對象是這次的新增行：

```bash
bin/changed-lines <這次的檔案...> > <暫存目錄>/added.txt   # 新增行，不帶 diff 的 + 前綴；新檔整份都算
```

它涵蓋已經 staged、還沒 staged 的改動與還沒 add 的新檔，不寫 git index；路徑以執行時的目錄起算。stderr 的 `changed-lines: N added line(s) from M file(s)` 裡，N 是 0 而這次的改動有新增文字時，代表給的檔案不對，修正之後重跑；這次只刪除文字時 N 是 0，沒有新增行可掃，逐類表寫「只刪除，沒有新增行」。N 不是 0 時照 bank 對 `added.txt` 跑。逐類表照 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉留下。

## 回覆語言

給使用者的每一則回覆都用繁體中文，包括工具呼叫之間的短句與工作結束時的總結。指令、程式識別字、錯誤訊息原文、產品與服務名稱保留原文，其餘敘述用中文。前文是一長串英文的指令、log、錯誤訊息與程式碼時，最後的總結最容易漂成英文，所以每一則總結送出之前確認一次語言。

## 提交與推送

### 提交

- **commit message 帶著這次的紀錄**：這次的 diff 動到書面產出（〈改動的級別〉）時，commit message（或同一個 commit 裡給讀者看的 work-log 文章）要有〈改動的級別〉的判定；不是排版級的改動另外要有 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉要求的紀錄。沒有就先補，再 commit。排版級的改動沒有新增詞句，那一節的掃描與探針紀錄都不適用，紀錄就是級別的判定。
- **`description` 與 `tags`**：新增的 `content/` 檔案一律補齊；修改既有 `content/` 檔案時，同檔缺這兩個欄位就在同一次變更補上。lint 把它們報在警告層，但它們不是可以新增的技術債。補這兩個欄位是新增行，那一次的改動因此不是排版級（一般文章是措辭級），照那一級做紀錄與掃描。
- **lint**：這次動到 `content/` 的檔案時，提交前跑 `bin/lint-delta <這次的 content/ 檔案...>`。它只印這次新增的問題，既有的只計數；exit 1 代表這次新增了 error，修掉再提交，新增的 warn 寫進回報。全量 lint（`./bin/mdtools lint content/`）只用來觀察歷史基線，不用來判斷這次的品質。
- **提交**：用 `bin/commit-files -F <訊息檔> <這次的檔案...>`，不直接 `git commit`。共用的 git index 裡可能有另一個 session（或另一個 agent）staged 的檔案，直接 commit 會把它們一起提交；這支工具經由私有 index 只提交列出的檔案，提交後讓共用 index 對齊。路徑以執行時的目錄起算，刪除的檔案與改名的新舊兩個路徑都列。
  - 提交的內容要確認 `git diff HEAD -- <這次的檔案...>` 的每一段都是這次自己做的編輯：私有 index 隔離的是 staging，不隔離工作樹，另一個 session 改了同一個檔案時，它在工作樹裡的修改會一起提交。自己派出的 subagent 做的編輯也算自己的：提交的人替它們寫紀錄，改這些檔案的 subagent 還在跑時，等它完成再提交。Claude Code 裡 `bin/commit-files` 自己做這個確認（CLAUDE.md〈提交前對照編輯紀錄〉）；其他 agent 在跑 `bin/commit-files` 之前，把 diff 跟 context 裡的編輯紀錄逐段對照，編輯紀錄不在 context 裡的段落算對不上。`bin/commit-files` 印出 `[ASK-USER]`、或有對不上的段落時，照〈要先問使用者的情形〉處理。自認都是自己寫的不改變本款：對照的是 diff 與編輯紀錄，不是印象。
  - 工具沒有提交時，原因印在 stderr：原因落在這次的檔案上時照它修正；hook 擋下的是這次沒有改過的檔案時，照下面「pre-commit 報錯」那一條處理，不修那個檔案。提交之後印出 `[FOLLOW-UP]` 時，照那幾行做；工作結束時還做不了，寫進〈延到工作結束之後的動作〉。各個 exit code 的意思寫在工具的檔頭。
- **pre-commit 報錯**：讀訊息修正，不用 `--no-verify` 繞過。報錯落在這次沒有改過的檔案時（hook 的 `mdtools cards` 掃整個 `content/` 工作樹，另一個 session 寫到一半的檔案會擋下這次的 commit），不改也不繞過那個檔案，這次不提交，把要提交的檔案與擋下它的報錯寫進〈延到工作結束之後的動作〉；不在 session 裡反覆重試等它消失。

### 推送

commit 之後直接推送，不另外問使用者：使用者已經授權推送。使用者這次的指示只提到提交、沒有提到推送時，照常推送；指示另有要求時（「先不要推」「只推 blog」），照這次的指示。要停下來問的情形見〈要先問使用者的情形〉。

- **blog repo**：跑 `bin/push-main --mine <這次 session 提交的 commit...>`（`bin/commit-files` 每次提交都印出它的 hash）。它先 fetch；推送範圍裡有 `--mine` 以外的 commit 時不推送、不動本地的 `main`，印出 `[ASK-USER]`；目前在分支、worktree 或 detached HEAD 上時，它把目前的 commit fast-forward 進 `main` 再推。推送之後印出 `[CLEANUP]` 時，分支或 worktree 用完就照那幾行清理。
- **共用 skill 庫**：改過的 skill 照 `docs/rules/skills.md`〈推送前的檢查〉推（`skill-sync push` 的兩段式：`echo n` 取預覽、讀完再 `echo y`）。`echo y` 是 agent 自己執行的套用步驟，不是問使用者。`docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 不推（〈沒有使用者明說就不做的動作〉）。skill 改動同時要推 blog 與共用 skill 庫時，兩者互不依賴，沒有先後。
- **dotfiles**：部署照 `docs/rules/remote.md`〈遠端機器的操作〉跑 `remote-sync.sh`，它本身會 push。

直接推送拿掉的是「問使用者」這一步，不是檢查。工具印出 `[ASK-USER]` 時照〈要先問使用者的情形〉；其餘的非零 exit、預覽裡有 `[WARNING]`、pre-push 報錯、遠端拒絕時，停下來修，修不了就寫進〈延到工作結束之後的動作〉。還沒推送的 commit 用 `bin/push-main --list-unpushed` 列出：它列出所有分支與 detached HEAD 上還沒推到任何遠端的 commit，fetch 成功或失敗時都適用。

### 要先問使用者的情形

這一節是「停下來等使用者決定」的唯一住址：別處的規則碰到這類情形時連到這裡，新增一種情形時加在這裡。下列情形停下來，把指定的材料給使用者，等使用者決定再往下做：

- **提交前**，`bin/commit-files` 或 `bin/session-edits-check` 印出 `[ASK-USER]`，或 `git diff HEAD -- <這次的檔案...>` 有段落對不上這次自己做過的編輯：把工具印的 diff 或那幾段 diff 原文貼進回覆（太長時存成檔案，給路徑與 `git diff --stat`），並說明同意之後會照〈推送〉直接推送，由使用者決定是不是一起提交。這次清單裡的檔案都等使用者決定，不先提交其餘的：同一次改動的檔案可能必須在同一個 commit 裡（skill 的源檔與它的鏡像）。
- **推送 blog 時**，`bin/push-main` 印出 `[ASK-USER]`：給它列出的 commit（別的 session 還沒推送的），由使用者決定要不要一起推。
- **收斂遠端分支時**（`docs/rules/remote.md`〈遠端機器的操作〉）：`bin/converge-branch` 印出 `[ASK-USER]`（merge 衝突、分岔），給它印的兩邊 commit 與衝突的段落；dotfiles 的工作樹有 `??` 的檔案或不是這次自己做的未提交改動，給 `git status --short` 與那幾段 diff；本地 main 有不是這次的未推 commit、或分支只在遠端機器上，給那幾個 commit 或分支名。由使用者決定怎麼處理；不替它 commit、不還原、不在遠端寫入。
- **同步 skill 時**，`[DIVERGED]` 或 `[CONFLICT]` 的兩邊在共同基底之後改到同一段文字（合併時有衝突）：給兩邊的 `git log` 與衝突的段落（`docs/rules/skills.md`〈同步時的判斷〉）。
- **搬移 `content/` 的資料夾或文章、在 `--apply` 之前**（`content-folder-migration` skill 的「搬移前的檢查：要搬的位置」與「dry-run、基準值與搬移前的檢查：要改寫的檔案」兩步；這次自己的其他改動在搬移之前先提交），下列任一項成立：要搬的資料夾或 dry-run 列出要改寫的檔案，`git status`、其他 worktree 的 `git status` 或其他分支的 `git log main..<分支>` 有輸出（已經在這次搬移的 manifest 裡的檔案不算）；dry-run 的殘留引用列出 `hugo.toml` 的 `[permalinks]` 裡以被搬資料夾為名的鍵（搬走之後那一組頁面的網址格式改變）；dry-run 的「網址改變」頁數少於頁數，而那些頁面不在 `[permalinks]` 有鍵的 section 裡。給 dry-run 的輸出與 skill 那一步檢查指令的輸出，由使用者決定搬不搬、怎麼搬。

### 沒有使用者明說就不做的動作

這一節是這類動作的唯一住址。下列動作沒有使用者在這次的指示裡明說就不做，也不主動提議、不停下來問：`skill-sync push --force`；替一支 skill 建 `content/skills/` 的公開鏡像；把 `docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 推上共用庫（那些 skill 依賴本 blog 的結構，推上去之後別的專案用不了）；把工作樹裡不是這次自己做的改動還原或蓋掉（`git checkout --`、`git checkout .`、`git restore`、`git stash`、`git reset --hard`、`git clean`、用 Write 整份重寫），那些改動可能是另一個 session 還沒提交的工作，蓋掉之後沒有任何紀錄；搬移或改名 `content/` 底下含 `_index.md` 的資料夾（收進或移出大分類、建立或撤掉大分類、在模組之間搬子資料夾；`docs/rules/content-folders.md`〈文章放在哪一個資料夾〉），首頁的分類結構、網址與讀者的閱讀路線由使用者決定，搬錯了再搬一次時每一頁要多一筆 `aliases`；使用者提出要搬之後，跑 dry-run 與 `bin/empty-sections` 提供材料不算主動提議。

### 延到工作結束之後的動作

規則要求的動作做不到當下、要延到之後時（`bin/commit-files` 的 `[FOLLOW-UP]`、還沒推送的 commit、因為別人的檔案擋下而沒提交的改動、印了 `[ASK-USER]` 而等使用者決定的提交、`bin/converge-branch` 還沒處理的 `[ASK-USER]` 與還沒跑的 `[NEXT]`、遠端的暫時檔、登記待驗的判定、沒有模組 Backlog 可記的未完成工作），寫進給使用者的最後一則總結，附要跑的指令。延後的動作沒有其他觀察者，只寫在對話中段的那一份不會有人回來做。

## 掃描工具的零輸出

grep、lint、檢查腳本回報零命中有兩種成因：目標確實不存在，或是指令沒有在掃（pattern 打錯、shell 的 `|` 被轉義、變數沒有切詞、zsh 的 glob 沒有匹配而整條指令沒執行、腳本裡找不到工具、掃描範圍不含目標、餵進去的檔案集是空的）。所以把零輸出當成「通過」之前，先做兩件事：確認餵進去的檔案集不是空的（行數或檔案數不是 0），再餵一個已知會命中的輸入（正對照，positive control），確認它在這個寫法下會命中。正對照沒有命中時，修指令，不採用那次的零輸出。

`bin/changed-lines`、`bin/lint-delta`、`bin/session-edits-check`、`bin/skill-version-check`、`bin/term-prompt-count`、`bin/report-weight`、`bin/content-move`、`bin/empty-sections`、`bin/alias-check` 在結尾印計數，格式寫在各工具的檔頭。交給它檔案清單的工具，計數要對得上交給它的數量；自己找檔案的工具（`bin/term-prompt-count`、`bin/report-weight`、`bin/content-move`、`bin/empty-sections`、`bin/alias-check`），代表掃描範圍的那一個計數是 0、或 stderr 列出讀不到的來源時，檔案集不對；那一個計數是 `content-move` 的 `page(s) moved`、`empty-sections` 的 `section(s) scanned`、`alias-check` 的 `page(s)`，同一行的其他計數（`collision(s)`、`empty`）是 0 代表通過。計數沒有印出來，代表工具中途中止，不代表通過。

## 破壞性指令的目標寫在指令文字裡，檢查與刪除分成兩次執行

這一節管 agent 執行的 shell 指令，以及規則檔、skill、`bin/` 與 `.githooks/` 的 shell 腳本裡的指令；既有的指令只在這次改到那一行時才照改。`bin/` 與 skill 裡的 Python 由程式算出路徑、由各自的測試驗證，不在此列；容器、雲端資源這類檔案以外的刪除也不在此列；agent 執行 repo 內的工具（`bin/skill-mirror`、`mdtools fmt`、`bin/content-move --apply`）時，被改寫的檔案由工具自己決定、由它的檔頭與測試管（有預覽或 dry-run 的先跑那一步），也不套本節的觸發；`content/` 文章裡給讀者照做的示範指令不套本節。「一次執行」指一次工具呼叫（Claude Code 的一次 Bash 呼叫、Codex 的一次指令執行），裡面用 `;`、`&&`、`|` 串起來的都算同一次。「暫存目錄」指 repo 以外、這次工作專屬的目錄：Claude Code 是系統提示列出的 scratchpad，其他 agent 用 `mktemp -d` 新建；腳本自己用 `mktemp` 建的檔與目錄也算。

**破壞性動作的目標寫在指令文字裡。** 破壞性動作依效果判：刪除、移動或覆寫一個已經存在的檔案，例如 `rm`、`mv`、`git rm`、`git clean`、`find … -delete`、`find … -exec rm`、`xargs rm`、`rsync --delete`、`sed -i`、`truncate`，以及 `>`、`tee`、`cp` 寫到已經存在的檔案；寫進暫存目錄裡、這次工作自己建的檔（新建或重跑時覆寫，例如 `bin/changed-lines … > <暫存目錄>/added.txt`）與 `/dev/null` 不算。目標由變數、字串截取、命令替換、glob、`find` 的條件或前一段管線決定時，核准這次工具呼叫的使用者、事後讀 log 與 transcript 的人在指令文字裡讀不到要刪的路徑，而審核的實際動作是讀指令的文字。展開失敗也不報錯，只改變刪除範圍：`S` 為空時，`rm -rf ${S%/content/books}/` 展開成 `rm -rf /`（其餘的展開結果在依據卡）。

- **觸發**：破壞性動作的目標不是寫在指令文字裡的絕對路徑。常見的形態：目標含 `$`（`$HOME` 也算）、反引號或 glob；由 `find` 的條件、管線、檔案內容（`xargs rm < list.txt`）或直譯器（`python3 -c`）算出；相對路徑，而同一次執行的開頭沒有 `cd` 到一個字面的絕對路徑（cwd 不在指令文字裡，前一次呼叫的 `cd` 會延續）。`~` 開頭的路徑算絕對路徑。
- **處置**：改成字面的絕對路徑。目標要靠 glob 或條件選出時（agent 自己下的 `for` 迴圈也是），先在一次執行裡只列出目標（`ls`、不帶 `-delete` 的 `find`），讓核准刪除的人看過那份清單，下一次執行用清單上的字面路徑刪；清單長到寫不進一條指令時，下一次執行用同一個條件加 `-delete`，條件跟列出清單的那一次逐字相同。shell 腳本裡的相對路徑照腳本檔頭寫明的執行目錄起算，不套觸發裡相對路徑那一種。shell 腳本（含腳本裡的迴圈）用變數組出目標時，組成路徑的每一個變數都寫成 `${X:?}`（截取之前的 `${S:?}`、`${SKILL_NAME:?}`），只檢查組好的那個字串擋不到空值：`content/skills/${SKILL_NAME}/skill.md` 在名字為空時仍然不是空字串。截取的結果另存一個變數、印到 stderr，再交給刪除：非互動的腳本裡沒有人在刪除之前核准，印出來的路徑讓事後讀 log 的人看得到實際刪了什麼。`git clean` 不跑：它刪的是工作樹裡的未追蹤檔，其中可能有另一個 session 還沒提交的新檔（〈沒有使用者明說就不做的動作〉）；刪自己建的未追蹤檔，用 `rm` 加字面的絕對路徑。
- **檢查與刪除分成兩次執行**：掃描、正對照、驗證這類唯讀的指令（〈掃描工具的零輸出〉的正對照就是一種）不在同一次執行裡串進刪除或覆蓋。串在一起時，核准的人看的是「這次在檢查什麼」，核准檢查就核准了那次刪除。要清理時另開一次只做清理的執行，讓核准的人知道自己在核准刪除。shell 腳本在一次執行裡先檢查、再清理自己建的暫存檔不受這一項限制，照「處置」那一條的變數寫法處理。
- **手動建的正對照假資料留著不刪**：放在暫存目錄底下的新子目錄（`mktemp -d <暫存目錄>/pc.XXXXXX`），重跑時再建一個。暫存目錄本來就跟專案隔開，刪除換到的整潔抵不過它帶進來的風險。工具與測試在自己的 `finally`、`tearDown` 裡清掉自己建的暫存目錄不在此列。檢查的工具只讀 repo 工作樹、假資料非放進 repo 不可時，檢查跑完另開一次執行、用字面路徑刪掉，提交之前用 `git status --short` 確認它不在工作樹裡：留在 `content/` 的假資料會被 pre-commit 掃到，擋下其他 session 的提交。

依據：[破壞性指令的目標用變數的字串截取組出來時，審核的人看不到要刪什麼；空值、尾斜線與截取對不上會改變刪除範圍，而這類清理夾在檢查指令裡時，核准一次檢查就核准了一次刪除](/report/destructive-target-built-by-string-expansion/)。

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
