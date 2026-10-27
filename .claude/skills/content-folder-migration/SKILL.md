---
name: content-folder-migration
description: 把 content/ 的資料夾收進大分類、把單篇文章搬進 hands-on/ 或改檔名時用：dry-run、搬移前的檢查、殘留引用、驗證與提交。觸發詞：content 搬移、資料夾遷移、首頁分類收斂、大分類、改網址、Hugo aliases、空 section、空列表。
metadata:
  version: 1.0.0
---

# content 資料夾與文章的搬移

這份 skill 是在本 repo 搬移 `content/` 底下資料夾或文章的程序。「大分類」與「模組」（教學模組的根資料夾）照規則分冊 `docs/rules/content-folders.md`〈文章放在哪一個資料夾〉與〈概念文章與實作文章：`hands-on/` 子資料夾〉的定義；什麼時候搬、搬到哪裡、建大分類換到什麼與付出什麼，是那裡的規則。這裡寫照著做的步驟、每一步的輸出怎麼讀、做錯會怎樣。`<暫存目錄>` 指 repo 以外的暫存目錄（Claude Code 用 session 的 scratchpad）。

## 搬移用到的工具

| 工具                                                                   | 做什麼                                                                                                                                                                       | 讀法                                                                       |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `bin/empty-sections [<資料夾>...]`                                     | 列出底下沒有任何會列出的文章或子 section 的 section（讀者點進去是空列表）                                                                                                     | exit 1 有空的 section；`body=` 是 `_index.md` 正文的非空行數                |
| `bin/content-move [--apply] [--list] [--manifest <檔案>] <src> <dest>` | 網址改變的頁面加 `aliases`、改寫指向它們的連結、被搬頁面的相對連結改成絕對路徑；列出殘留引用（還寫著舊網址或舊路徑、而工具沒有改寫的位置）。不帶 `--apply` 只印計畫（dry-run） | `<dest>` 是搬過去之後的完整路徑；`--manifest` 只在 `--apply` 時把碰到的檔案附加進清單；細節與 exit code 在檔頭 |
| `bin/alias-check`                                                      | 列出 alias 衝突：alias 等於另一頁的網址，或兩頁宣告同一個 alias。pre-commit 與 CI 也跑它                                                                                      | exit 0 沒有衝突                                                            |

站內連結是否指到不存在的檔案，由既有的 `./bin/mdtools cards content/`（L1-broken-link）檢查。

## 涵蓋的搬移

- **資料夾收進大分類**：走下面每一步。
- **單篇文章搬進 `hands-on/`，或改單篇的檔名**：走「搬移前的檢查：要搬的位置」「dry-run、基準值與搬移前的檢查：要改寫的檔案」「`--apply`」「殘留引用」「格式化」「驗證」「提交」這幾步，`<dest>` 寫到 `.md`。改檔名時，frontmatter 有 `slug` 的話把 `slug` 改成新檔名再搬：網址取 slug 而不是檔名，只改檔名的話網址不變，`slug` 也跟檔名不一致。搬進 `hands-on/` 另外三件事照 `content-folders.md`〈概念文章與實作文章〉：`hands-on/_index.md` 不存在時先建、原資料夾 `_index.md` 章節表刪掉那一列、`hands-on/_index.md` 的章節表登記；被搬那一篇的 `weight` 照 `markdown.md`〈列表排序與 weight〉放進新 section 的編號帶。這兩個 `_index.md` 是手改的檔案，記進 `hand.txt`。
- **其他搬移**（移出或撤掉大分類、在模組之間搬子資料夾、改資料夾名）：這份 skill 沒有實際走過，照 AGENTS.md〈沒有使用者明說就不做的動作〉由使用者決定。使用者決定要做時，步驟照資料夾那條路，另外把大分類 `_index.md` 的模組表、`content/_index.md` 的入口與 weight 改成搬移之後的狀態。

## 流程

1. **定清單（資料夾那條路）。** 哪些資料夾收進哪一個大分類、依什麼順序，由使用者決定。使用者提出之後，agent 提供材料：`bin/empty-sections`、dry-run 的頁數與連結數，以及 `content-folders.md`〈文章放在哪一個資料夾〉列的取捨（首頁的分組只改 `content/_index.md` 也做得到）。訂錯的代價：再搬一次時每一頁的 `aliases` 要再加一筆，而第一次的 commit 已經推上去。
2. **搬移前的檢查：要搬的位置。** 這次自己在 `content/` 的其他改動先提交，搬移從乾淨的狀態開始。`git worktree list` 與 `git branch` 只用來列出要逐一檢查的對象，本身一定有輸出，不是停下來的條件。跑三類指令：`git status --short -- content/<要搬的資料夾>`；對其他每一個 worktree 跑 `git -C <worktree 路徑> status --short -- content/<要搬的資料夾>`；對目前分支以外的每一個本地分支跑 `git log --oneline main..<分支> -- content/<要搬的資料夾>`。任一條有輸出，照 AGENTS.md〈要先問使用者的情形〉停下來。代價：分支上已經存在的檔案改了內容，merge 回來時多半自動合進新路徑；分支上新增在舊路徑的檔案會衝突，或留在舊路徑、沒有 alias 也沒有改寫的連結。
3. **大分類的 `_index.md`（資料夾那條路）。** `ls content/<大分類>/_index.md` 沒有這個檔時先建，只寫 frontmatter：`title`、`date`、`description`、`tags`，以及 `weight`（使用者決定它在首頁排第幾，照 `markdown.md`〈列表排序與 weight〉）；正文在「改寫大分類的 `_index.md`」那一步寫。少了它，列表頁顯示的是資料夾名，沒有 title 與 description。
4. **dry-run、基準值與搬移前的檢查：要改寫的檔案。** 第一個對象搬之前記下三個基準值，驗證那一步要比：`bin/alias-check > <暫存目錄>/base-alias.txt`、`bin/empty-sections > <暫存目錄>/base-empty.txt`（都掃整個 `content/`），以及 `hugo --renderToMemory 2>&1 | rg Aliases > <暫存目錄>/base-hugo.txt`。之後照使用者給的順序，每一個對象做完這一步（dry-run 與檢查）與「`--apply`」那一步再換下一個：後面的對象要讀前一次搬完之後的檔案，dry-run 列出的改寫才準。全部對象搬完之後，「殘留引用」到「提交」各步做一次。dry-run 是 `bin/content-move --list <src> <dest> > <暫存目錄>/dry-<名稱>.txt`，讀第一行的頁數與「網址改變」頁數、連結改寫的檔案、殘留引用與警告。下列任一項成立就在 `--apply` 之前照 AGENTS.md〈要先問使用者的情形〉停下來：
   - 連結改寫與殘留引用列出的檔案，照「要搬的位置」那一步的三類指令查（把資料夾換成那些檔案），有輸出；已經在 manifest 裡的檔案是這次前面的搬移改的，不算。檔案清單從 dry-run 輸出取：`rg -o '^  (\S+): \d+$' -r '$1' <暫存目錄>/dry-<名稱>.txt | rg -v '^<dest>/'`（`<dest>` 底下是搬過去之後的新路徑，還不存在；來源已經在「要搬的位置」那一步查過）。
   - 殘留引用列出 `hugo.toml` 的 `[permalinks]` 裡以被搬資料夾為名的鍵：那一組頁面的網址取 slug，搬走之後網址格式改變。
   - 「網址改變」頁數少於頁數，而且來源不在 `[permalinks]` 有鍵的 section 裡。來源在那些 section 裡時，換資料夾網址本來就不變，兩個頁數不等是預期內的，照常往下。
5. **`--apply`。** `bin/content-move --apply --list --manifest <暫存目錄>/manifest.txt <src> <dest> > <暫存目錄>/apply-<名稱>.txt`，每一次給同一個 manifest；前一次跑完才跑下一個對象的 dry-run，同時跑時後寫入的那一次會蓋掉先寫入那一次改好的連結。exit 2 是用法或前提錯（原因在 stderr），還沒有寫檔，修正之後重跑；其他非零 exit 代表可能寫了一半，用 `git status --short` 列出改動，交給使用者。
6. **殘留引用。** apply 輸出裡「殘留的引用」那一段，照 `references/residual-references.md` 的處置表逐筆處理；那一份也列了殘留掃描看不到、要另外查的兩類位置。
7. **改寫大分類的 `_index.md`（資料夾那條路）。** 讀者在網站上只看得到它的 `title`、`description` 與子 section 列表：`title` 冒號之後寫出它收的模組，`description` 照觸發條件寫並寫出那些模組。正文是工作底稿：列模組的表（weight、收錄的內容、排在這個位置的理由）、範圍、`## Backlog`。大分類 `_index.md` 原有正文裡寫給讀者看的推導讀者看不到，寫成導讀文章或記進這一頁的 Backlog；跟新結構矛盾的段落刪掉。把各模組的 `title` 與 `description` 並排讀一次，讀者分不出哪一個收什麼時記進這一頁的 Backlog。
8. **重排模組的 weight（資料夾那條路）。** 大分類底下第一層各模組 `_index.md` frontmatter 的 `weight`，照使用者給的閱讀順序改成 1 到 N。原本的值是跟首頁其他頂層資料夾比的，搬進來之後不沿用。
9. **更新首頁 `content/_index.md`（資料夾那條路）。** 首頁顯示的就是這一頁的正文（theme 的 `index.html` 輸出 `.Content`），照文章的體例寫，不寫「哪一天搬進來」這類維護資訊。大分類是新建的時，在對應的分類段加它的入口；被搬走的頂層入口收成大分類底下的子項。不改的話，首頁還列著已經不在第一層的入口，網址靠 alias 轉。
10. **格式化。** 連結改寫會讓表格欄寬改變而對齊失效。「這次的檔案清單」是 manifest 加上這次手改的檔案（agent 在搬移之後用編輯工具改的每一個檔案，改的當下逐行記進 `<暫存目錄>/hand.txt`）；取其中還存在的 `.md`：`cat <暫存目錄>/manifest.txt <暫存目錄>/hand.txt | while read f; do [ -f "$f" ] && echo "$f"; done | rg '\.md$' | sort -u > <暫存目錄>/existing.txt`。跑 `xargs ./bin/mdtools fmt --fix --quiet < <暫存目錄>/existing.txt`，再 `xargs ./bin/mdtools fmt -check < <暫存目錄>/existing.txt` 到沒有輸出。不格式化整個 `content/`：共用工作樹裡別的 session 改到一半的檔案會被一起改掉。
11. **驗證**，下表每一列都跑，每一列結尾印的計數行寫進 commit message（沒跑的那一列寫「未跑」與原因）。改過 `config.go` 時先重建 mdtools：`(cd scripts/mdtools && go build -o ../../bin/mdtools . && go test ./...)`，通過是 exit 0、沒有 `FAIL`（`[no test files]` 不是失敗）；`cd` 放在括號裡，否則後面的指令都在 `scripts/mdtools` 底下執行。

    | 指令                                             | 驗什麼                                       | 通過                                                                                                                                                                                       |
    | ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | `./bin/mdtools cards content/`                   | 站內連結有沒有指到不存在的檔案；知識卡的結構 | exit 0；通過時沒有任何輸出，紀錄寫「exit 0」                                                                                                                                              |
    | `bin/alias-check`                                | alias 衝突                                   | 跟 `base-alias.txt` 相比沒有新增的行；新增的是這次造成的（包括頁面既有的 alias 撞上另一頁的新網址），停下來照 AGENTS.md〈要先問使用者的情形〉交給使用者：改 alias 等於改舊網址導向哪一頁 |
    | `hugo --renderToMemory`                          | 整站 build                                   | exit 0；`Aliases` 比基準值多出的數量，等於各次 apply 結尾 `alias(es) added` 的總和，減去被搬頁面裡 `draft: true` 的頁數（`rg -l '^draft: true' <dest> \| wc -l`；Hugo 不 build draft，也不輸出它的 alias） |
    | `bin/empty-sections`                             | 這次有沒有造成新的空 section                 | `diff <(sed -e 's#content/<src>/#content/<dest>/#' <暫存目錄>/base-empty.txt \| sort) <(bin/empty-sections \| sort)` 沒有 `>` 開頭的行（多個對象時串多個 `-e`）；這次新建的大分類不在 `>` 的行裡。有的照 `content-folders.md`〈目錄頁 `_index.md` 與文章檔的分工〉處置 |
    | `xargs bin/lint-delta < <暫存目錄>/existing.txt` | AGENTS.md〈提交〉要求的 lint                 | 沒有新的 error。先 `xargs git add -A -- < <暫存目錄>/manifest.txt`，lint-delta 才會把被搬的檔案配對到舊路徑；沒有 add 時它把被搬的檔案當新檔，搬移前就有的問題也列成新的。這個 add 寫進共用 index，`bin/commit-files` 經由私有 index 只提交列出的檔案，提交後讓共用 index 對齊。git 只把內容相似度 50% 以上的配對成改名：連結改寫多的短檔在 `git status --short` 是一對 `D` 與 `A`，lint-delta 列出它的問題時，拿 `git show HEAD:<舊路徑> > <暫存目錄>/old.md` 再 `./bin/mdtools lint <暫存目錄>/old.md` 對照（lint 只認 `.md` 檔名，給 `/dev/stdin` 時印 `no markdown files` 而 exit 0），搬移前就有的不算這次的                          |

    `alias-check` 管 Hugo 與 `cards` 看不到的那一種衝突：alias 等於另一頁的網址時 Hugo 不發警告（`--printPathWarnings` 也沒有輸出），頁面直接蓋過 alias，舊網址導向的是那一頁；`cards` 依檔案路徑解析連結，不讀 aliases。
12. **提交。** 清單取自 manifest 與 `hand.txt`（刪除的舊路徑也在 manifest 裡），不從整份 `git status` 取，別的 session 的改動才不會混進來；`git status` 只用來比對有沒有漏列。清單分成兩個 commit：
    - **搬移的 commit**：manifest 裡的檔案、`config.go`、`hugo.toml`，以及 `hand.txt` 裡不是規則類文件的檔案。工具改寫的連結落在規則類文件（`docs/`、AGENTS.md、CLAUDE.md）而那個檔案沒有手改時，`bin/changed-lines --level <那個檔案>` 判得出排版級（每一對只差連結網址），也放這裡。`config.go` 與搬移不能分開：分開的話，中間那個 commit 的 lint 設定指向不存在的資料夾。
    - **規則的 commit**：手改過的規則類文件（殘留處置表標規則級的列；同一個檔案也有工具改寫時整個檔案放這裡），走多輪審查。審查完跟搬移的 commit 一起推送，遠端不停在規則指向舊路徑的狀態。搬檔是刪除加新增，工具與 `fmt` 不經過 Edit 寫檔，`bin/commit-files` 一定印 `[ASK-USER]`；照 AGENTS.md〈要先問使用者的情形〉，完整 diff 存成檔案給路徑，`git diff --stat HEAD` 與手改那幾段 diff 貼進回覆。

## 搬移之後

- **語意搜尋的 index**：blogsearch 的向量 index 記的是舊路徑，照 `blogsearch-lifecycle` skill 重建。
- **舊分支 merge 回來**：分支上新增在舊路徑的檔案，對它們再跑一次 `bin/content-move`，再跑 `bin/alias-check` 與 `./bin/mdtools cards content/`。舊網址的前綴空出來之後，有人在那裡新建一頁就會蓋掉 alias；pre-commit 的 `alias-check` 會擋下這種提交。

## 範例：going-live、infra、ci、operations、monitoring 收進 devops

`content/devops/` 原本只有 `_index.md`，`bin/empty-sections` 把它列為空的 section。使用者決定依 going-live、infra、ci、operations、monitoring 的順序收進來；infra 的 dry-run 是 186 頁、186 頁網址改變、1859 處連結、277 個檔案。apply 之後要改的殘留是 `config.go` 的知識卡路徑（六行）、`hugo.toml` 的一行註解、三份 `_index.md` 裡寫成文字的路徑、`content-folders.md` 與 `markdown.md` 的路徑範例；那時殘留掃描還看不到帶 `/blog/` 的網址與 README.md，事後另外補了一份文章裡讀者照抄的指令、README.md、e2e 測試與擷取腳本的網址。格式化修了 76 個表格；`Aliases` 從 54 變成 452，多出的 398 是 399 個 `alias(es) added` 減去 1 頁 draft。

## `bin/content-move` 不處理、要手動補的情形

- 它只認得 `[permalinks]` 裡的 `:slug`；設定用到其他變數時它 exit 2。
- TOML frontmatter（`+++`）的頁面不加 `aliases`，列在警告裡，要手動加。
- `relref` shortcode 依檔名解析，搬移不改檔名，所以不改寫。
- weight 不調整（「重排模組的 weight」那一步）。

版本紀錄在同目錄的 `CHANGELOG.md`。
