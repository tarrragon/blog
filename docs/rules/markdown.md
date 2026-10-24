# Markdown 排版與 mdtools

這份分冊管 `content/` 的 Markdown 排版規範在哪裡、哪些類別由 mdtools 擋下、路徑大小寫、列表排序與 weight，以及修改 mdtools 時讀哪裡。提交前的 lint 在 `AGENTS.md`〈提交〉。

## Markdown 與 mdtools

`content/**` 所有 markdown 的排版與結構規範，以 `content/posts/markdown-writing-spec.md` 為單一真實來源；完整規則、識別碼白名單、TLD 清單、執行時機與擴充流程讀那一篇。工具鏈是 `scripts/mdtools`（Go 加 goldmark AST），在 pre-commit、pre-push 與 CI 執行。規則與 `scripts/mdtools/internal/rules/` 的實作保持同步，任一方修改時同步更新另一方與規範文章。

### 工具會擋的類別與要自己跑的類別

字句層 keyword bank 的唯一住址是 `compositional-writing` skill。下表只記哪些類別已經進了 mdtools、哪些要自己照 bank 跑；判讀與詞表不複製到這裡。

| 類別                                                                                                                          | 誰擋                                                  |
| ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 標題：正文禁止 H1、同層重複、標題尾標點（MD026）、粗體當標題（MD036）                                                         | mdtools lint                                          |
| URL：裸 URL；顯示文字含 TLD 字樣時 domain 要與 href 一致                                                                      | mdtools lint                                          |
| 表格對齊、列表與 code block 的空行、有序列表編號、code block 語言標示                                                         | mdtools fmt / lint                                    |
| Front matter：`title`、`date` 必填；新文章 `description`、`tags` 必填（lint 報在警告層）；卡片層 `description`、`weight` 必填 | mdtools lint / cards                                  |
| 卡片：相對連結有效、orphan、首段與概念位置段含鄰卡連結（`.codex/briefs/knowledge-cards.md` K4）                               | mdtools cards                                         |
| 位置引用與數量命名（REF1「見第 N 章」「§N」、REF2「六大原則」），警告層                                                       | mdtools lint                                          |
| 否定起手（POS-negation-lead「不是 X、而是 Y」「與其 X、不如 Y」），警告層                                                     | mdtools lint                                          |
| 縮寫術語「判準」（TERM-abbreviation），error 層；討論這個詞本身時加「」或行內程式碼                                           | mdtools lint（`.claude/skills/` 不跑 lint，要手動掃） |
| 裝飾符號（emoji、✓ ✗）：表格 status 改用純文字，優缺點改用 `**優點**：` / `**缺點**：`（spec §5.9）                           | 未進 lint，手動跑表格下方的指令                       |
| bank 的其餘類別（喊話、誇飾、必然性、敘事姿態、位置與集合指涉、用詞搭配、泛用詞、物理化錯配等）                               | 未進 lint，照 bank 跑                                 |

裝飾符號的掃描指令（寫在表格外，因為表格儲存格裡的 `|` 要轉義成 `\|`，照抄進 shell 後 rg 會把它當成字面的豎線，永遠零命中）：

```bash
rg "✅|❌|⚠️|🚨|🟡|🟢|⭐|📌|✓|✗" content/
```

### 路徑大小寫

`content/` 的資料夾、檔名與站內連結 route 一律小寫（`content/ci` 對應 `/ci/`）。macOS 預設檔案系統不區分大小寫而 Linux CI 區分：目錄是 `content/CI`、連結寫 `/ci/` 時，`mdtools cards` 在 CI 判成 broken link。懷疑大小寫漂移時跑 `git ls-tree -r --name-only HEAD | rg '^content/[A-Z]'`。

### 列表排序與 weight

Hugo 的列表依 weight 遞增排序，未設 weight 的頁面排在全部有 weight 的頁面之後，同 weight 才依日期遞減。由此推出：

- **同一個 section 的 weight 全有或全無**：混用會讓缺 weight 的頁面沉到列表底部，`mdtools cards` 的 `L5-section-weight-consistency` 會警告。刻意用低 weight 置頂單篇的 section（如 `content/linux/tools/cli`）在 `scripts/mdtools/internal/rules/config.go` 的 `WeightExemptSections` 登記。`weight: 0` 在 Hugo 就是未設，`L9-weight-zero-is-unset` 以 error 擋下，章節從 0 起算時最容易寫出這個值。
- **後補文章的 weight 放在屬於它的位置**：值落在該 section 既有的編號帶之內、順序對得上這篇在模組裡的位置。只確認沒跟別人重號不夠，重號與排序是兩件事。補號前先看該 section 既有的編號帶。L5 只查全有全無，對「有 weight 但值錯」不報。
- **新增一個要求 `title`、`date`、`description`、`weight` 四個欄位都必填的目錄**（目前登記的是知識卡目錄與 `content/report/`）時，在同一個 `config.go` 的 `FrontMatter.CardPaths` 登記，否則卡片層的 frontmatter 檢查不涵蓋它；未納管目錄的零 error 跟合規目錄的零 error 看起來一樣。依據：[檢查規則的作用域要顯式列舉：零 error 可能是沒被檢查](/report/lint-scope-must-be-explicit-fact/)。
- **frontmatter 的 date 是台北時間**：`hugo.toml` 設了 `timeZone = 'Asia/Taipei'`。拿掉這一行的話，在 UTC 的 CI 上、台北 00:00 到 08:00 之間 build，當日日期的文章會被判成未來文章而排除。

### 修改 mdtools

修改 `scripts/mdtools` 之前，讀 `scripts/mdtools/README.md` 的〈Development〉：那一節寫了測試要在哪個目錄跑、跨檔規則放哪個套件、fmt 規則的冪等要求與測試 fixture 的寫法。改完 mdtools 的規則時，同步更新 `content/posts/markdown-writing-spec.md` 與本分冊〈工具會擋的類別與要自己跑的類別〉的表。
