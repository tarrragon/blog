# 殘留引用的處置

> **何時讀**：`content-folder-migration` 流程的「殘留引用」那一步，讀 `bin/content-move --apply --list` 輸出裡「殘留的引用」那一段時。這張表是殘留引用處置的唯一住址。

殘留引用是還寫著舊網址或舊路徑、而 `bin/content-move` 沒有改寫的位置。工具掃 `git ls-files -co --exclude-standard` 列出的全部檔案，比對舊網址（含帶 baseURL 路徑的 `/blog/<舊前綴>/` 與完整網址）與 `content/<舊資料夾>`；它改寫的只有 `content/`（鏡像 `content/skills/` 除外）、`docs/`、AGENTS.md、CLAUDE.md 裡的 markdown 連結。

## 處置表

| 殘留的位置                                                                                     | 處置                                                                                                                                                        | 不處理的後果                                                                                                                       |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/mdtools/internal/rules/config.go` 的 `CardPaths`、`CardsRoots`、`WeightExemptSections` | 改成新路徑，`ls -d` 確認每一行都指到存在的資料夾                                                                                                           | `CardPaths`、`CardsRoots` 指錯時 lint 不再檢查那批知識卡；`WeightExemptSections` 指錯時那個 section 的 weight 豁免失效，L5 開始警告 |
| `hugo.toml` 的選單 `url`；`layouts/`、`static/` 裡寫死的路徑                                    | 改成新網址或新路徑，驗證包括 `hugo --renderToMemory`                                                                                                        | 選單靠 alias 轉一次；模板指向不存在的 section                                                                                      |
| README.md、`tests/`、`scripts/` 裡指向被搬頁面的網址（e2e 測試、擷取腳本的預設網址）或 repo 路徑 | 網址改成新網址；README 裡指向 repo 路徑的連結（`./content/<舊資料夾>/`）改成新的 repo 路徑，不換成網址：它在 GitHub 上連到資料夾                             | 測試與腳本打到 alias 頁面，量到的是轉址頁不是實際頁面；README 的連結在 GitHub 上 404                                               |
| `.claude/skills/` 裡的連結或路徑                                                               | `docs/rules/skills.md`〈只留在本 repo 的 skill〉清單裡的 skill 改成新網址；其餘是共用 skill，照〈Skill 的撰寫規則〉改成中性名詞。兩者都是規則級改動         | agent 照 skill 去找不存在的路徑；共用庫裡出現 blog 路徑                                                                            |
| `content/skills/` 底下的鏡像                                                                    | 不直接改：改 `.claude/skills/` 的源檔，再跑 `bin/skill-mirror <名稱>`                                                                                       | 下一次產生鏡像時，直接改的內容被蓋回去                                                                                             |
| `.codex/`、註解、`_index.md` 與正文裡寫成文字的路徑、讀者會照抄的指令範例裡的路徑               | 改成新路徑                                                                                                                                                  | 讀者照抄得到不存在的路徑                                                                                                           |
| 記錄過去狀態的敘述：事件說明與實測環境（「實測頁開在 `/blog/monitoring/…`」）、CHANGELOG、commit 引用、擷取結果的 JSON | 不改：那是當時的事實；讀者照著重做時要用的位置，寫在指令與步驟裡（上一列改的就是那些）                                                                     | 改了就是竄改紀錄                                                                                                                   |
| `docs/rules/` 與規則類 spec 的路徑範例                                                         | 改成新路徑；規則級改動，照 AGENTS.md〈改動的級別〉走多輪審查                                                                                                | 照規則做的 agent 去找不存在的資料夾                                                                                                |
| 單元測試在自己的 fixture 裡建立的路徑（`scripts/` 底下的 `*_test.go`、`bin/tests/`）             | 不改：測試在拋棄式目錄裡自己建檔，不讀 `content/`，跟真實資料夾同名也不受搬移影響。對著建好的網站跑的測試（`tests/` 的 e2e）打的是真實網址，歸「README.md、`tests/`、`scripts/`」那一列 | 無                                                                                                                                 |

## 殘留掃描看不到、要另外查的位置

- **依目錄深度寫死的 glob**：`rg -n 'content/(\*|[a-z-]+/\*)/' docs content/posts AGENTS.md CLAUDE.md .claude bin .githooks`。層數對不上搬移後的深度時，改成不依深度的寫法（`rg -l '<pattern>' content -g '_index.md'`）。
- **只寫 slug、不帶路徑的提及**（單篇搬移時）：殘留掃描比對的是路徑與網址，寫成「`oracle-cloud/` 的 cli-session-login」這種文字比對不到。另外跑 `rg -n '<slug>' content docs .claude <memory 目錄>`，逐筆照上面的處置表判。
- **Claude Code 的 memory**：`rg -n 'content/<舊資料夾>|/<舊網址前綴>/' <memory 目錄>`（memory 目錄的路徑寫在系統提示的 Memory 段；單篇搬移時改用上一項的 slug 比對），逐筆改；寫著「因為搬移而延後」的待辦，在搬移的 commit 推上去之後改成可以接著做。
