@AGENTS.md

---

# Claude Code 專屬的操作

上方的 `@AGENTS.md` 由 Claude Code 自動內嵌；AGENTS.md 是寫作與工程規則的單一真實來源。本檔只寫 Claude Code 才有的操作：回覆語言設定的注入、skill 的叫用機制、Agent tool 的派發（所有背景 agent 共用的送達規則、reviewer、理解探針、術語探針、審查規則檔時的限制）、Bash 工具跑私有 index 提交時的限制，以及 SSH 的權限與 hook。共用的規則不寫在這裡，要改就改 AGENTS.md。

## 回覆語言的設定

回覆語言的規則在 AGENTS.md〈回覆語言〉。使用者層級的 `~/.claude/settings.json`（`"language": "繁體中文"`）已經把同一條指示注入系統提示，而長 session 裡最後的總結仍然會寫成英文，多數發生在一長串英文的指令、log、錯誤訊息與程式碼之後。注入不能取代送出前的確認：每一則總結送出之前確認一次語言。

## Skill 的叫用

Claude Code 依 `.claude/skills/<name>/SKILL.md` frontmatter 的 `description` 比對當前任務，自動觸發 skill；系統提示裡會列出每個 skill 的 description。使用者在對話中打 `/<skill-name>` 手動叫用；agent 自己要叫用時用 Skill tool，不在回覆裡打斜線指令。

寫作類 skill 不等自動觸發、由 agent 主動叫用的規則（什麼時候叫用、改完要留什麼紀錄），寫在 AGENTS.md〈規則的優先序與住址〉。

## Agent tool 的派發

這一節的三個子節分別管 reviewer、理解探針與術語探針的派發參數，最後一個子節管審查對象是本檔或 AGENTS.md 時的額外限制。下面兩條適用於所有放在背景跑的 agent（reviewer 與探針都是）。

**prompt 必須寫送達方式**，兩句缺一不可：

```text
完成後必須呼叫 SendMessage 把報告送到 `main`。
只把報告寫在自己的回覆裡不算交付，主 session 讀不到。
```

少了這兩句的話，背景 agent 寫完報告就閒置，主 session 讀不到它的報告。`multi-round-review` 的 `references/reviewer-prompt.md` 在送達欄留了佔位，派發時填這兩句。

**背景 agent 閒置而沒有送報告時**，用 SendMessage 向它索取報告，不重派：重派的那一份要從頭讀完全部材料，而閒置的那一份手上已經有寫好的報告。

### Reviewer

派發多輪審查與教學模組流程的 reviewer 時，用 `subagent_type: "general-purpose"`、`run_in_background: true`，每位負責一個審查維度、平行跑。維度從流程的 skill 取：多輪審查用 `multi-round-review` 各輪的 frame，教學模組流程用 `case-first-module-workflow` 的專責 reviewer。reviewer 要讀完整的稿件、案例與規範，自己的 context 會被佔滿；放在背景跑，主 session 只接收它的報告。reviewer 的 prompt 結構與產出契約以 `multi-round-review` 的 `references/reviewer-prompt.md` 為準。

### 理解探針

探針與 reviewer 的派發方式不同：reviewer 各審不同維度，要的是判斷力；探針每一份的指令完全一樣，要的是理解的樣本。

- **模型**：用低階模型，目前對應的是 `model: "haiku"`。「低階」的判斷標準是推理較弱、單位成本低到可以一次派好幾份，以 `multi-round-review` 的 `references/round-2-probes.md`〈探針的派發契約〉為準。
- **背景**：`run_in_background: true`。
- **prompt 的其餘內容**（一批的範圍與逐字相同的條件、回報格式、要求標記不確定）照〈探針的派發契約〉寫；派發之前要成立的條件與讀回報時的歸因方法，在 AGENTS.md〈理解探針〉。

### 術語探針與系統提示

在本 repo 底下派出的 subagent，系統提示裡已經有這幾份文字：本檔與 AGENTS.md、使用者層級的 `~/.claude/CLAUDE.md`、memory 目錄的 `MEMORY.md` 索引，以及全部 skill 的 description 清單。測試詞寫在其中任何一份時，探針回報「有把握」可能只是複述了系統提示裡的定義，而不是這個詞在目標領域的用法。

**派發之前**，列出每個測試詞在這幾份文字裡出現的行數：

```bash
grep -c "<詞>" AGENTS.md CLAUDE.md ~/.claude/CLAUDE.md \
  ~/.claude/projects/-Users-mac-eric-project-blog/memory/MEMORY.md
grep -c "<詞>" .claude/skills/*/SKILL.md | grep -v ':0$'   # 數整份 SKILL.md，比 description 寬；多算的只會讓結果偏向「本批無結論」
```

`grep -c` 數的是含這個詞的行數，不是出現次數；判斷「是不是零」時兩者沒有差別。

**讀回報時**，每個測試詞依它的行數與探針的回報對下表記錄結果。「本批」指同一組放在一起比對的探針報告，結果記在 AGENTS.md〈掃描與探針的紀錄寫進 repo〉指定的位置。

| 行數 | 探針的回報                       | 這個詞的結果怎麼記                                                                   |
| ---- | -------------------------------- | ------------------------------------------------------------------------------------ |
| 非零 | 有把握，給的是系統提示裡那份定義 | 本批無結論：這個回報可以完全由系統提示解釋                                           |
| 非零 | 有把握，給的是別的定義或通用定義 | 可以採信，照 round-2-probes〈2-B⁶ 術語探針〉的四類讀法判（多半是同域佔用或一名多義） |
| 非零 | 沒把握、沒見過                   | 可以採信：讀得到定義仍然沒把握，代表這個詞讀不出來                                   |
| 零   | 任何回報                         | 照四類讀法判；行數是零代表這幾份文字沒寫到這個詞，這一步排除不了其他污染來源         |

`Agent` tool 沒有換工作目錄的參數，所以不嘗試「換到沒有規範檔的目錄」或「換一個乾淨的配置」重測。控制詞、安慰劑詞的條件與四類回報的讀法，以 round-2-probes〈2-B⁶ 術語探針〉為準。

### 審查本檔與 AGENTS.md 時

審查對象就是本檔或 AGENTS.md 時，每一位 reviewer 與探針的系統提示裡都已經有受審文本的全文，而且可能是 session 開始時的舊版：

- **prompt 裡寫死受審版本的 commit hash**，要求以 `git show <hash>:<檔名>` 讀到的版本為準。不用 `HEAD`：審查期間別的 session 提交時 HEAD 會移動，各份讀到的版本就不同。受審內容還沒提交時，先提交或把檔案複製到 scratchpad 再給路徑。
- **探針回報讀錯的位置可以採信；回報讀懂的位置不能當成通過**，因為它可能是用系統提示補完的。reviewer 判定「讀得懂」時同樣適用。
- **翻譯探針不跑**：它的設計條件是譯者只拿得到文字，這裡結構上做不到。

## 私有 index 提交在 Bash 工具裡的限制

多個 session 共用 repo 時的提交程序在 AGENTS.md〈多個 session 共用 repo 時的提交〉。Bash 工具每次呼叫的 shell 狀態不保留，環境變數不會帶到下一次呼叫：`export GIT_INDEX_FILE=…` 與 `git add`、`git commit` 分在兩次呼叫時，`git add` 與 `git commit` 用的是共用的 index，而且不報錯。所以那段程序從 `export` 到 `unset` 在同一次 Bash 呼叫裡跑完；私有 index 的路徑寫 scratchpad 的絕對路徑，因為每次呼叫的工作目錄可能不同。

## SSH 的權限與 ssh_guard hook

本專案是教學與實驗用途，`.claude/settings.local.json` 刻意放寬到 `Bash(ssh *)`，讓 agent 對受管的遠端機器做唯讀診斷時不必逐次核准；前提是遠端環境壞了可以重建。

`ssh` 的 `-o ProxyCommand=…` 與 `-o LocalCommand=…`（配 `PermitLocalCommand=yes`）會在本機這台開發機執行任意命令，這條路徑不受「遠端可以重建」保護（規則本身在 AGENTS.md〈遠端機器的操作〉），所以用 PreToolUse hook 攔下：

- **機制**：`.claude/hooks/ssh_guard.py` 註冊為 `Bash` 的 PreToolUse hook。它用兩個 regex 比對指令字串：`SSH_INVOCATION` 認出 `ssh` 以獨立的詞出現（前面是行首、空白或 `; & | ( )` 之一，後面是空白或行尾），`LOCAL_EXEC_OPTS` 認出 ProxyCommand、LocalCommand 或 PermitLocalCommand（不分大小寫）。兩者同時命中時 hook 回 `permissionDecision: deny`；純遠端的唯讀診斷（`ssh <host> <readonly-cmd>`）照常放行。
- **涵蓋範圍**：hook 只比對這一條指令的字串。看不到的形態有：寫在 `~/.ssh/config` 裡的選項、藏進變數或 wrapper script 的選項，以及由別的指令間接呼叫 ssh 的形態（`scp -o …`、`rsync -e …`、`GIT_SSH_COMMAND=…`）；後一類分屬 `scp`、`rsync`、`git` 的權限規則，不在 `Bash(ssh *)` 底下。在「agent 不是敵人，只是要避免它意外動到本機」這個威脅模型下，hook 擋得住誤用，擋不住刻意的繞過。
- **已知副作用**：一條 Bash 指令的文字裡只要有不加引號、以獨立的詞出現的 `ssh`，又在任何位置出現那三個選項名，就會被擋，即使它只是要寫進檔案的文字（例如 heredoc 或 `python3 - <<'EOF'` 的內容裡同時寫到 `ssh` 指令與 ProxyCommand）。`ssh` 緊接在引號後面的（`echo 'ssh -o …'`）不會被擋。要在檔案裡寫這些字串時，用 Write 或 Edit，不放進 Bash。
- **維護**：選項清單與 ssh 呼叫的辨識邏輯在 hook 檔的那兩個 regex。改完把 payload 寫進檔案再餵 stdin 驗證：payload 是 `{"tool_name":"Bash","tool_input":{"command":"<要測的指令>"}}`；deny 的案例 stdout 印出含 `"permissionDecision": "deny"` 的 JSON，放行的案例沒有輸出。deny 的案例不直接寫進測試指令，否則 hook 會擋住測試指令本身。
