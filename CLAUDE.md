@AGENTS.md

---

# Claude Code 專屬的操作

上方的 `@AGENTS.md` 由 Claude Code 自動內嵌；AGENTS.md 是寫作與工程規則的單一真實來源。本檔只寫 Claude Code 才有的操作：回覆語言、skill 的叫用、Agent tool 的派發（reviewer、理解探針、術語探針、審查規則檔時的限制）、多個 session 共用同一個 repo 時的 git 操作，以及 SSH 的權限與 hook。共用的規則不寫在這裡，要改就改 AGENTS.md。

## 回覆語言

給使用者的每一則回覆都用繁體中文，包括工具呼叫之間的短句與工作結束時的總結。指令、程式識別字、錯誤訊息原文、產品與服務名稱保留原文，其餘敘述用中文。

使用者層級的 `~/.claude/settings.json`（`"language": "繁體中文"`）已經注入同一條指示，而長 session 裡最後的總結仍然會寫成英文，多數發生在一長串英文的指令、log、錯誤訊息與程式碼之後。所以前文越是英文密集，送出總結之前越要確認一次語言。

## Skill 的叫用

Claude Code 依 `.claude/skills/<name>/SKILL.md` frontmatter 的 `description` 比對當前任務，自動觸發 skill；系統提示裡會列出每個 skill 的 description。手動調用是在對話中打 `/<skill-name>`。

寫作類的 skill 主動 invoke，不等自動觸發：寫作任務常常以「幫我改這段」「補一句」「這裡讀起來怪怪的」進來，這些措辭不含 `compositional-writing` 的 description 裡任何一個觸發詞，而小改動累積出來的字句層違規跟整篇一樣多。所以：

- 動到 `content/`、`.claude/skills/`、AGENTS.md 或本檔的任何一段文字之前，invoke `compositional-writing`。
- 改完之後照 AGENTS.md〈文章產出流程〉的字句層掃描跑一次 bank，逐類表寫進 commit message 或 work-log（AGENTS.md〈掃描的紀錄寫進 repo〉）。

## Agent tool 的派發

### Reviewer

多輪審查與教學模組流程的 reviewer 用 `subagent_type: "general-purpose"`、`run_in_background: true`，每位負責一個審查維度、平行跑。reviewer 要讀完整的稿件、案例與規範，自己的 context 會被佔滿；放在背景跑，主 session 只接收它的報告。reviewer 的 prompt 結構與產出契約以 `multi-round-review` 的 `references/reviewer-prompt.md` 為準。

### 理解探針

探針與 reviewer 的派發方式不同：reviewer 各審不同維度，要的是判斷力；探針每一份的指令完全一樣，要的是理解的樣本。

- **模型**：用低階模型，目前對應的是 `model: "haiku"`；低階的判斷標準是推理較弱且成本低，以 `multi-round-review` 的 `references/round-2-probes.md` 為準。另加 `run_in_background: true`。
- **一批的範圍**：一批是「報告會被放在一起比對的那幾份」。同一批之內，`prompt` 與餵給它的內容範圍逐字相同：複製同一個字串貼進每一次呼叫，不逐個微調措辭，否則份與份之間的差異無法歸因到模型的理解。換問法（理解正確性換成閱讀負擔）或換讀的範圍就是另一批，兩批之間不比對。
- **prompt 必須寫送達方式**，兩句缺一不可：

```text
完成後必須呼叫 SendMessage 把報告送到 `main`。
只把報告寫在自己的回覆裡不算交付，主 session 讀不到。
```

少了這兩句的話，背景的探針寫完報告就閒置，主 session 讀不到；寫了，Haiku 也照做。reviewer 閒置而沒有送報告時，用 SendMessage 向它索取，不重派。

- **回報的格式**逐項列出：節名或行號、這一節讀到什麼、這個動作誰做、對什麼做、指涉詞各指誰、讀完之後第一個動作是什麼；明令「文章沒說就寫『文章沒說』，不要推測填補」。另外單獨開一段列出「有兩種以上讀法的位置」，逐條寫原文與各種讀法，這一段的價值最高。
- **讀回報**：每份報告先歸因再處置（AGENTS.md〈理解探針〉）。歸因的方法是在原文 grep 那個讀法對應的字串。

### 術語探針與系統提示

subagent 的系統提示會繼承本檔與 AGENTS.md，所以測試詞寫在這兩份檔案裡時，探針量到的是它在系統提示裡出現了幾次，不是這個詞在目標領域通不通用。派發術語探針之前：

1. 列出每個測試詞在兩份檔案的詞頻：`grep -c "<詞>" AGENTS.md CLAUDE.md`。
2. 詞頻非零而探針回報「有把握，並給出本站自己的定義」時，這個詞的結果記成「本批無結論」，因為這個結果可以完全由系統提示解釋。
3. 詞頻非零而探針仍回報「沒把握」時，結果可以採信。
4. 詞頻全部是零時，這個檢查一定通過，通過不代表沒有受到系統提示的影響（規範檔沒涵蓋那個領域）。

`Agent` tool 沒有換工作目錄的參數，所以不嘗試「換到沒有規範檔的目錄」或「換一個乾淨的配置」重測。控制詞、安慰劑詞的條件與四類回報的讀法，以 `multi-round-review` 的 `references/round-2-probes.md`〈術語探針〉為準。

### 審查本檔與 AGENTS.md 時

審查對象就是本檔或 AGENTS.md 時，每一位 reviewer 與探針的系統提示裡都已經有受審文本的全文（而且可能是 session 開始時的舊版）：

- prompt 裡要求以 `git show HEAD:<檔名>` 讀到的版本為準。
- 理解探針回報「讀懂了」不算通過，因為它可以用系統提示補完；只有「讀了仍然讀錯」的那一側可以採信。
- 翻譯探針不跑：它的設計條件是譯者只拿得到文字，這裡結構上做不到。

## 多個 session 共用同一個 repo

另一個 session 正在使用 git 時，`git add` 或 `git commit` 會因為 `.git/index.lock` 存在而失敗。這時用私有的 index 提交，不刪除 lock：

```bash
export GIT_INDEX_FILE=<scratchpad>/idx   # 私有 index 的路徑，放在 scratchpad
git read-tree HEAD                        # 以 HEAD 初始化私有 index
git add <這次的檔案...>
git commit -F <訊息檔>
unset GIT_INDEX_FILE
```

提交之後，共用的 index 裡那些檔案仍是舊版本；另一個 session 用它 commit 時，會把這次的改動改回去。lock 釋放之後，跑 `git reset -q -- <這次的檔案...>`，讓共用的 index 對齊 HEAD。

## SSH 的權限與 ssh_guard hook

本專案是教學與實驗用途，`.claude/settings.local.json` 刻意放寬到 `Bash(ssh *)`，讓 agent 對受管的遠端機器做唯讀診斷時不必逐次核准；前提是遠端環境壞了可以重建。

`ssh` 的 `-o ProxyCommand=…` 與 `-o LocalCommand=…`（配 `PermitLocalCommand=yes`）會在本機這台開發機執行任意命令，這條路徑不受「遠端可以重建」保護，所以用 PreToolUse hook 攔下：

- **機制**：`.claude/hooks/ssh_guard.py` 註冊為 `Bash` 的 PreToolUse hook。一條指令同時呼叫 ssh、又帶 ProxyCommand、LocalCommand 或 PermitLocalCommand 時，hook 回 `permissionDecision: deny`；純遠端的唯讀診斷（`ssh <host> <readonly-cmd>`）照常放行。
- **涵蓋範圍**：hook 只比對指令字串本身，寫在 `~/.ssh/config` 裡的 ProxyCommand 看不到。在「agent 不是敵人，只是要避免它意外動到本機」這個威脅模型下，它擋得住誤用，擋不住刻意把選項寫進設定檔的繞過。
- **已知副作用**：任何 Bash 指令的文字裡同時出現 ssh 呼叫與這些選項就會被擋，例如 `echo 'ssh -o ProxyCommand=…'` 這種示範字串。要在指令裡引用這些字串時，用 Write 或 Edit 寫進檔案，不放進 Bash。
- **維護**：危險選項清單與 ssh 呼叫的辨識邏輯在 hook 檔裡。改完用 payload 檔餵 stdin 驗證；deny 的案例不直接寫進測試指令，否則 hook 會擋住測試指令本身。
