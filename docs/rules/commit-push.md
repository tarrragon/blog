# 提交、推送與要先問使用者的情形

這份分冊是 `AGENTS.md`〈提交與推送〉的完整規則：提交前要留的紀錄、工具各種輸出的處置、blog、共用 skill 庫與 dotfiles 的推送方式，以及每一種要停下來問使用者的情形要給哪些材料。

## 提交

下列各項照這個順序做：補欄位與修 lint 都會改變 diff，級別要在它們之後才判。

- **`description` 與 `tags`**：新增的 `content/` 檔案一律補齊；修改既有 `content/` 檔案時，同檔缺這兩個欄位就在同一次變更補上。lint 把它們報在警告層，但它們不是可以新增的技術債。補這兩個欄位是新增行，那一次的改動因此不是排版級（一般文章是措辭級），照那一級做紀錄與掃描。
- **lint**：這次動到 `content/` 的檔案時，提交前跑 `bin/lint-delta <這次的 content/ 檔案...>`。它只印這次新增的問題，既有的只計數；exit 1 代表這次新增了 error，修掉再提交，新增的 warn 寫進回報。全量 lint（`./bin/mdtools lint content/`）只用來觀察歷史基線，不用來判斷這次的品質。
- **commit message 帶著這次的紀錄**：這次的 diff 動到書面產出（`AGENTS.md`〈改動的級別〉）時，commit message（或同一個 commit 裡給讀者看的 work-log 文章）要有同一節定義的級別判定；不是排版級的改動另外要有 `docs/rules/writing-process.md`〈掃描與探針的紀錄寫進 repo〉要求的紀錄。沒有就先補，再 commit。排版級的改動沒有新增詞句，那一節的掃描與探針紀錄都不適用，紀錄就是級別的判定。
- **提交（blog repo）**：用 `bin/commit-files -F <訊息檔> <這次的檔案...>`，不直接 `git commit`。共用的 git index 裡可能有另一個 session（或另一個 agent）staged 的檔案，直接 commit 會把它們一起提交；這支工具經由私有 index 只提交列出的檔案，提交後讓共用 index 對齊。路徑以執行時的目錄起算，刪除的檔案與改名的新舊兩個路徑都列。
  - 提交的內容要確認 `git diff HEAD -- <這次的檔案...>` 的每一段都是這次自己做的編輯：私有 index 隔離的是 staging，不隔離工作樹，另一個 session 改了同一個檔案時，它在工作樹裡的修改會一起提交。自己派出的 subagent 做的編輯也算自己的：提交的人替它們寫紀錄，改這些檔案的 subagent 還在跑時，等它完成再提交。Claude Code 裡 `bin/commit-files` 自己做這個確認（`claude-code.md`〈提交前對照編輯紀錄〉）；其他 agent 在跑 `bin/commit-files` 之前，把 diff 跟 context 裡的編輯紀錄逐段對照，編輯紀錄不在 context 裡的段落算對不上（生成的詞典改用生成器重算，見 `markdown.md`〈自動連結的詞典〉）。`bin/commit-files` 印出 `[ASK-USER]`、或有對不上的段落時，照〈要先問使用者的情形〉處理。自認都是自己寫的不改變本款：對照的是 diff 與編輯紀錄，不是印象。
  - 工具沒有提交時，原因印在 stderr：原因落在這次的檔案上時照它修正；hook 擋下的是這次沒有改過的檔案時，照下面「pre-commit 報錯」那一條處理，不修那個檔案。提交之後印出 `[FOLLOW-UP]` 時，照那幾行做；工作結束時還做不了的，照 `AGENTS.md`〈延到工作結束之後的動作〉寫進給使用者的最後一則總結。各個 exit code 的意思寫在工具的檔頭。
- **pre-commit 報錯**：讀訊息修正，不用 `--no-verify` 繞過。報錯位於這次沒有改過的檔案時（hook 的 `mdtools cards` 掃整個 `content/` 工作樹，另一個 session 寫到一半的檔案會擋下這次的 commit），不改也不繞過那個檔案，這次不提交，把要提交的檔案與擋下它的報錯，照 `AGENTS.md`〈延到工作結束之後的動作〉寫進給使用者的最後一則總結；不在 session 裡反覆重試等它消失。

## 推送

推送的授權與例外寫在 `AGENTS.md`〈推送〉；使用者這次的指示只提到提交、沒有提到推送時，照常推送。要停下來問的情形見〈要先問使用者的情形〉。

- **blog repo**：跑 `bin/push-main --mine <這次 session 提交的 commit...>`（`bin/commit-files` 每次提交都印出它的 hash）。它先 fetch；推送範圍裡有 `--mine` 以外的 commit 時不推送、不動本地的 `main`，印出 `[ASK-USER]`；目前在分支、worktree 或 detached HEAD 上時，它把目前的 commit fast-forward 進 `main` 再推。推送之後印出 `[CLEANUP]` 時，分支或 worktree 用完就照那幾行清理。
- **共用 skill 庫**：改過的 skill 照 `docs/rules/skills.md`〈推送前的檢查〉推（`skill-sync push` 的兩段式：`echo n` 取預覽、讀完再 `echo y`）。`echo y` 是 agent 自己執行的套用步驟，不是問使用者。`docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 不推（`AGENTS.md`〈沒有使用者明說就不做的動作〉）。skill 改動同時要推 blog 與共用 skill 庫時，先提交 blog；`bin/commit-files` 成功而且 `git status --porcelain -- .claude/skills/<name>` 沒有輸出時才跑 `skill-sync push`。有輸出時不跑（它推的是工作樹的內容，可能含另一個 session 的改動或還沒追蹤的新檔），照 `AGENTS.md`〈延到工作結束之後的動作〉寫進最後一則總結。
- **dotfiles**：部署照 `docs/rules/remote.md`〈遠端機器的操作〉跑 `remote-sync.sh`，它本身會 push。

直接推送拿掉的是「問使用者」這一步，不是檢查。工具印出 `[ASK-USER]` 時照〈要先問使用者的情形〉；其餘的非零 exit、預覽裡有 `[WARNING]`、pre-push 報錯、遠端拒絕時，停下來修，修不了就照 `AGENTS.md`〈延到工作結束之後的動作〉寫進給使用者的最後一則總結。還沒推送的 commit 用 `bin/push-main --list-unpushed` 列出：它列出所有分支與 detached HEAD 上還沒推到任何遠端的 commit，fetch 成功或失敗時都適用。

## 要先問使用者的情形

這一節是「停下來等使用者決定」的唯一住址：別處的規則碰到這類情形時連到這裡，新增一種情形時加在這裡。下列情形停下來，把指定的材料給使用者，等使用者決定再往下做：

- **提交前**，`bin/commit-files` 或 `bin/session-edits-check` 印出 `[ASK-USER]`（生成的詞典先照 `markdown.md`〈自動連結的詞典〉處置），或 `git diff HEAD -- <這次的檔案...>` 有段落對不上這次自己做過的編輯：把工具印的 diff 或那幾段 diff 原文貼進回覆（太長時存成檔案，給路徑與 `git diff --stat`），並說明同意之後會照〈推送〉直接推送，由使用者決定是不是一起提交。這次清單裡的檔案都等使用者決定，不先提交其餘的：同一次改動的檔案可能必須在同一個 commit 裡（skill 的源檔與它的鏡像）。
- **推送 blog 時**，`bin/push-main` 印出 `[ASK-USER]`：給它列出的 commit（別的 session 還沒推送的），由使用者決定要不要一起推。
- **收斂遠端分支時**（`docs/rules/remote.md`〈遠端機器的操作〉）：`bin/converge-branch` 印出 `[ASK-USER]`（merge 衝突、分岔），給它印的兩邊 commit 與衝突的段落；dotfiles 的工作樹有 `??` 的檔案或不是這次自己做的未提交改動，給 `git status --short` 與那幾段 diff；本地 main 有不是這次的未推 commit、或分支只在遠端機器上，給那幾個 commit 或分支名。由使用者決定怎麼處理；不替它 commit、不還原、不在遠端寫入。
- **同步 skill 時**，`[DIVERGED]` 或 `[CONFLICT]` 的兩邊在共同基底之後改到同一段文字（合併時有衝突）：給兩邊的 `git log` 與衝突的段落（`docs/rules/skills.md`〈同步時的判斷〉）。
- **多輪審查的大綱稽核或設計稽核到了停點時**（停點的條件定義在 `multi-round-review` 的 `references/planning-and-stopping.md`〈Round N 規劃判讀〉開頭）：不重組也不重寫，給那一節指定的材料，由使用者決定方向；不受「Round 3 跑完之前不問」限制。
- **搬移 `content/` 的資料夾或文章、在 `--apply` 之前**（`content-folder-migration` skill 的「搬移前的檢查：要搬的位置」與「dry-run、基準值與搬移前的檢查：要改寫的檔案」兩步；這次自己的其他改動在搬移之前先提交），下列任一項成立：要搬的資料夾或 dry-run 列出要改寫的檔案，`git status`、其他 worktree 的 `git status` 或其他分支的 `git log main..<分支>` 有輸出（已經在這次搬移的 manifest 裡的檔案不算）；dry-run 的殘留引用列出 `hugo.toml` 的 `[permalinks]` 裡以被搬資料夾為名的鍵（搬走之後那一組頁面的網址格式改變）；dry-run 的「網址改變」頁數少於頁數，而那些頁面不在 `[permalinks]` 有鍵的 section 裡。給 dry-run 的輸出與 skill 那一步檢查指令的輸出，由使用者決定搬不搬、怎麼搬。
