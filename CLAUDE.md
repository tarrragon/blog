@AGENTS.md
@docs/rules/content-folders.md
@docs/rules/writing.md
@docs/rules/sentences.md
@docs/rules/writing-process.md
@docs/rules/review.md
@docs/rules/markdown.md
@docs/rules/skills.md
@docs/rules/remote.md

---

# Claude Code 專屬的操作

上方的 `@` 匯入由 Claude Code 自動內嵌：AGENTS.md 是規則的入口，`docs/rules/` 的分冊是各類工作的規則（分工見 AGENTS.md 開頭的路由表）。本檔只寫 Claude Code 才有的操作：回覆語言設定的注入、skill 的叫用機制、Agent tool 的派發（所有背景 agent 共用的送達規則、reviewer、理解探針、術語探針會讀到的系統提示）、Bash 工具跑私有 index 提交時的限制，以及 SSH 的權限與 hook。共用的規則不寫在這裡，要改就改 AGENTS.md 或對應的分冊。

## 回覆語言的設定

回覆語言的規則在 `AGENTS.md`〈回覆語言〉。使用者層級的 `~/.claude/settings.json`（`"language": "繁體中文"`）已經把同一條指示注入系統提示；注入之後總結仍然會漂成英文，所以那一條的「送出前確認」照樣要做。

## Skill 的叫用

Claude Code 依 `.claude/skills/<name>/SKILL.md` frontmatter 的 `description` 比對當前任務，自動觸發 skill；系統提示裡會列出每個 skill 的 description。使用者在對話中打 `/<skill-name>` 手動叫用；agent 自己要叫用時用 Skill tool，不在回覆裡打斜線指令。

寫作類 skill 不等自動觸發、由 agent 主動叫用的規則，寫在 `AGENTS.md`〈寫作類 skill 的叫用〉。

## Agent tool 的派發

這一節先寫所有放在背景跑的 agent（reviewer 與探針都是）共用的兩條，再依序是〈Reviewer〉〈理解探針〉的派發參數，以及〈術語探針與系統提示〉的派發前檢查。審查對象是規則檔時的額外限制，對任何 agent 都成立，寫在 `docs/rules/review.md`〈審查規則類文件時〉。

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
- **prompt 的其餘內容**（一批的範圍與逐字相同的條件、回報格式、要求標記不確定）照〈探針的派發契約〉寫。讀回報時的歸因方法在 `docs/rules/review.md`〈理解探針〉。

### 術語探針與系統提示

在本 repo 底下派出的 subagent，系統提示裡已經有很多文字，至少包括：AGENTS.md 與全部分冊、本檔、使用者層級的 `~/.claude/CLAUDE.md`、memory 目錄的 `MEMORY.md` 索引、專案與使用者層級全部 skill 的 description（含 plugin 的 skill）、agent 類型與 MCP server 的說明，以及 git 狀態裡最近幾筆 commit 的標題。測試詞寫在其中任何一處時，探針回報「有把握」可能只是複述了系統提示裡的定義，而不是這個詞在目標領域的用法。

**派發之前**，列出每個測試詞在這些文字裡出現的行數。檔案形式的來源用 grep；memory 目錄的路徑由工作目錄換算（把絕對路徑的 `/` 換成 `-`，放在 `~/.claude/projects/` 底下）：

```bash
grep -c "<詞>" AGENTS.md docs/rules/*.md CLAUDE.md ~/.claude/CLAUDE.md \
  ~/.claude/projects/<換算後的專案目錄名>/memory/MEMORY.md
grep -rc "<詞>" --include=SKILL.md .claude/skills ~/.claude/skills 2>/dev/null | grep -v ':0$'
git log -20 --format=%s | grep -c "<詞>"
```

skill 那一條數的是整份 SKILL.md，範圍比 description 寬；用 `grep -r --include` 而不用 `*/SKILL.md` 的 glob，因為 zsh 在 `~/.claude/skills/*` 沒有匹配時會讓整條指令不執行，專案自己的 skill 也一起被算成 0。plugin skill、agent 類型與 MCP 說明沒有固定的檔案位置，grep 數不到，要讀這一次系統提示裡的清單人工確認。`grep -c` 數的是含這個詞的行數，不是出現次數；判斷「是不是零」時兩者沒有差別。

讀回報時照 round-2-probes〈2-B⁶ 術語探針〉的詞頻判讀與四類讀法，判成「本批無結論」的詞，照 `docs/rules/review.md`〈理解探針〉末段登記「待驗」、寫進最後一則總結。`Agent` tool 沒有換工作目錄的參數，所以不嘗試「換到沒有規範檔的目錄」或「換一個乾淨的配置」重測。

## 私有 index 提交在 Bash 工具裡的限制

多個 session 共用 repo 時的提交程序在 `AGENTS.md`〈多個 session 共用 repo 時的提交〉。Bash 工具每次呼叫的 shell 狀態不保留，環境變數不會帶到下一次呼叫：`export GIT_INDEX_FILE=…` 與 `git add`、`git commit` 分在兩次呼叫時，`git add` 與 `git commit` 用的是共用的 index，而且不報錯。所以那段程序從 `export` 到 `unset` 在同一次 Bash 呼叫裡跑完；私有 index 的路徑寫 session scratchpad 的絕對路徑，因為每次呼叫的工作目錄可能不同。

## SSH 的權限與 ssh_guard hook

本專案是教學與實驗用途，`.claude/settings.local.json` 刻意放寬到 `Bash(ssh *)`，讓 agent 對受管的遠端機器做唯讀診斷時不必逐次核准；前提是遠端環境壞了可以重建。

`ssh` 的 `-o ProxyCommand=…` 與 `-o LocalCommand=…`（配 `PermitLocalCommand=yes`）會在本機這台開發機執行任意命令，這條路徑不受「遠端可以重建」保護（規則本身在 `docs/rules/remote.md`〈遠端機器的操作〉），所以用 PreToolUse hook 攔下：

- **機制**：`.claude/hooks/ssh_guard.py` 註冊為 `Bash` 的 PreToolUse hook。它用兩個 regex 比對整條指令的文字：`SSH_INVOCATION` 認出 `ssh` 以獨立的詞出現（`ssh` 的前一個字元是行首、空白或 `; & | ( )` 之一，後一個字元是空白或行尾），`LOCAL_EXEC_OPTS` 認出 ProxyCommand、LocalCommand 或 PermitLocalCommand（不分大小寫）。兩者在同一條指令的任何位置同時命中時，hook 回 `permissionDecision: deny`：那條指令不執行，工具回傳 hook 寫的拒絕理由。純遠端的唯讀診斷（`ssh <host> <readonly-cmd>`）照常執行。
- **涵蓋範圍**：hook 只比對這一條指令的文字。看不到的形態有：寫在 `~/.ssh/config` 裡的選項、藏進變數或 wrapper script 的選項、用完整路徑呼叫的 `/usr/bin/ssh`（`ssh` 的前一個字元是 `/`）、反引號的命令替換（`` `ssh …` ``，前一個字元是反引號），以及由別的指令間接呼叫 ssh 的形態（`scp -o …`、`rsync -e …`、`GIT_SSH_COMMAND=…`）；間接呼叫的那一類分屬 `scp`、`rsync`、`git` 的權限規則，不在 `Bash(ssh *)` 底下。在「agent 不是敵人，只是要避免它意外動到本機」這個威脅模型下，hook 擋得住誤用，擋不住刻意的繞過。
- **已知副作用**：判定只看 `ssh` 的前一個字元與選項名有沒有出現，不看引號，所以兩種無害的指令也會被拒絕：要寫進檔案的文字（heredoc、`python3 - <<'EOF'` 的內容、`echo "note: ssh -o …"` 這種引號裡 `ssh` 前面是空白的字串）同時寫到 `ssh` 與選項名，以及遠端的唯讀指令本身提到選項名（`ssh <host> 'grep -i <選項名> ~/.ssh/config'`）。`ssh` 緊接在引號後面的（`echo 'ssh -o …'`）前一個字元是引號，不會被拒絕。要在檔案裡寫這些字串時，用 Write 或 Edit，不放進 Bash。
- **維護**：選項清單與 ssh 呼叫的辨識邏輯在 hook 檔的那兩個 regex。改完把 payload 寫進檔案再餵 stdin 驗證：payload 是 `{"tool_name":"Bash","tool_input":{"command":"<要測的指令>"}}`；deny 的案例 stdout 印出含 `"permissionDecision": "deny"` 的 JSON，放行的案例沒有輸出。deny 的案例不直接寫進測試指令的文字，否則 hook 會拒絕測試指令本身。
