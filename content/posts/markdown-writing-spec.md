---
title: "Blog Markdown 寫作規範與 mdtools 檢查"
slug: "markdown-writing-spec"
date: 2026-04-24
description: "本 blog 的 Markdown 排版規範權威契約。涵蓋 H1 禁用、MD024 siblings_only、反釣魚 TLD 校驗、卡片雙向完整性、front matter schema；改規則時要與 scripts/mdtools 實作同步。"
tags: ["Markdown", "AI協作心得", "blog心得", "lint", "goldmark"]
---

## 這篇要解決什麼

隨著 blog 文章與知識卡片成長，純靠寫作紀律維持排版一致性越來越不可靠。反覆踩到的問題橫跨兩個層級：

**結構與安全層級**（這是工具鏈存在的主要理由）：

- **裸 URL 在段落與表格中爆版**（MD034），降低閱讀體驗。
- **表格管線風格混用**（MD060），同一張表格有的有空白、有的沒有。
- **平行模板章節重複標題**（MD024），例如多案例文章的 `### 弱點環節` 出現 13 次。
- **顯示文字與實際 href 不一致**（反釣魚）— 不在標準 markdownlint 規則內，但紅隊教材脈絡下必要。
- **卡片雙向完整性**（orphan 卡片、斷連結、斷 anchor、K4 合規、目錄登記）— 跨文件檢查，現成工具做不到。
- **Front matter schema** — Hugo 依賴 YAML front matter 提供 title / date / weight 等欄位，缺失會破壞列表渲染、排序、SEO。

**基礎格式層級**（容易被忽略但影響 parser 穩定性或語義結構）：

- 正文禁止使用 H1（嚴於 MD025）— Hugo front matter `title` 已產生 H1。
- 標題前後需保留空行（MD022），parser 才能正確識別標題邊界。
- 標題結尾禁止標點（MD026）— 例如 `## 常見問題：` 應改為 `## 常見問題`。
- 禁止用 `**bold**` 段落當標題（MD036）— 破壞語義階層與 TOC 產生。
- 程式碼區塊需註明語言（MD040），影響 syntax highlighting 與 accessibility。
- 列表前後需空行（MD032）、fenced code block 前後需空行（MD031）— 否則部分 parser 會把列表吃進段落。
- 有序列表編號風格一致（MD029）— 全部 `1.` 或全部 `1./2./3.`。
- 檔案結尾需有換行（MD047），POSIX 規範。
- 行長度上限（MD013）— **預設關閉**，中英混用技術寫作不適用 80-char 慣例。

前兩類混合在同一份寫作規範裡，因為都由同一個工具鏈檢查、都要落地到相同的 pre-commit hook。純靠紀律記住這十幾條在大型 repo 上不可行，純 regex 又無法穩定處理「平行結構下的標題重複」「卡片段落歸屬」這類語意判斷。因此 blog 專案採用 Go + goldmark AST 做自訂 linter：`scripts/mdtools`。本文是 linter 與寫作規範的對齊文件；AGENTS.md 引用本文作為排版規範來源。

---

## 1. 工具總覽

| 子命令                         | 職責                                                           | 改檔         | 觸發時機                                          |
| ------------------------------ | -------------------------------------------------------------- | ------------ | ------------------------------------------------- |
| `mdtools fmt [--fix\|--check]` | 格式正規化（URL、表格、空行、列表間距、trailing newline）      | `--fix` 會改 | pre-commit（`--fix`）、pre-push / CI（`--check`） |
| `mdtools lint`                 | 結構檢查（標題、反釣魚、code block 語言、front matter schema） | 否           | pre-commit、pre-push、CI                          |
| `mdtools cards`                | 跨文件完整性（連結、fragment、orphan、K4、目錄登記）           | 否           | pre-commit、pre-push、CI                          |

工具原始碼在 `scripts/mdtools/`，binary build 到 `bin/mdtools`（已 gitignore）。

作用範圍是 `content/**/*.md`。`public/`、`themes/`、`node_modules/` 等輸出或第三方資源不檢查。

---

## 2. 標題規則

### 2.1 標題結構與格式規則

- **正文禁止使用 H1**。Hugo 的 front matter `title` 會自動產生 H1，若正文再寫 `# ...` 會出現兩個 H1 並列，破壞語義階層與 SEO 訊號。正文一律從 H2 開始，最深到 H6。
- **同一父標題（直接上層）底下，子標題文字必須唯一**（MD024 siblings_only 模式）。
- 不同父標題底下，子標題允許重名。
- 標題前後需保留空行（MD022），`mdtools fmt --fix` 自動補。
- **標題結尾禁止標點**（MD026）— 禁用字元：`.`、`,`、`:`、`;`、`。`、`，`、`：`、`；`。允許 `?`、`！`、`？`、`!` 作為語氣結尾。`mdtools fmt --fix` 自動去除結尾禁用標點。
- **禁止用粗體當標題**（MD036）— 若段落整段只由 `**文字**` 或 `*文字*` 組成，視為視覺性標題濫用。`mdtools lint` 只報警、不自動修；作者需手動判斷正確的標題層級（通常是 H3 / H4）並改寫。

### 2.2 補充範例：MD026 與 MD036 的典型誤用

MD026（標題尾標點）常見誤用：

```markdown
#### 字型選擇說明：        ← 違規（結尾 `：`）
#### 字型選擇說明          ← 合法
```

中文寫作習慣用冒號引入後續內容，這個模式在「段首句」合理、在「標題」就不合理 — 標題本身的存在就暗示了後續有內容，冒號變成冗餘訊號。

MD036（粗體當標題）常見誤用：

```markdown
**字型選擇說明**           ← 違規：整段只有粗體，視覺像標題但不是真標題

這段內容...

### 字型選擇說明           ← 合法：用正式的 H3 取代
```

差異看起來微小，實際影響包含：Hugo TOC 不會抓到、卡片反向連結失效、screen reader 無法跳轉。這是「語義 vs 視覺」錯位的典型案例，AST linter 容易檢出（Paragraph 節點唯一子節點為 Strong/Emph）。

### 2.3 為什麼採 siblings_only 而非全域唯一

平行結構（多案例、多模板章節）的複用語義來自上層標題賦予的脈絡。例如：

```markdown
## 【案例一】Uber 2022
### 弱點環節        ← 合法
### 攻擊路徑

## 【案例二】Okta 2023
### 弱點環節        ← 合法，因為在不同的父層下
### 攻擊路徑
```

重名只有在同層並列時才代表結構錯誤。強制全域唯一會逼作者寫 `### 【案例二】弱點環節`，破壞平行結構的視覺一致性，收益並不大。

---

## 3. URL 與連結規則

### 3.1 裸 URL 轉換（`mdtools fmt --fix` 自動處理）

段落或表格儲存格內的裸 URL 會自動包成 markdown 連結。顯示文字依路徑可識別性分級：

| 情境                     | 顯示文字            | 範例（before → after）                                                                                                                                                    |
| ------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 路徑含識別碼（例如 CVE） | `domain.com/識別碼` | `https://nvd.nist.gov/vuln/detail/CVE-2023-34362` → `[nvd.nist.gov/CVE-2023-34362](https://nvd.nist.gov/vuln/detail/CVE-2023-34362)`                                      |
| 路徑冗長但無識別性       | `domain.com`        | `https://www.cisa.gov/news-events/alerts/2024/06/03/snowflake-recommends-...` → `[cisa.gov](https://www.cisa.gov/news-events/alerts/2024/06/03/snowflake-recommends-...)` |
| 已是 markdown 連結       | 不動                | —                                                                                                                                                                         |

識別碼偵測用 regex 白名單，初始清單專注在高頻識別碼格式（例如 `CVE-YYYY-N`），其他格式以「遇到再加」原則擴充。清單維護在 `scripts/mdtools/internal/rules/identifiers.go`。

### 3.2 反釣魚校驗（`mdtools lint` 強制檢查）

Markdown 語法允許顯示文字與實際 href 完全不符，這是釣魚攻擊的結構基礎。本規則在 AST 層阻擋此模式。

- **R-URL-1（URL 樣顯示文字一致性）**：若顯示文字含 `.com` / `.org` / `.gov` / `.net` / `.io` / `.dev` / `.tw` 等 TLD 字樣，則顯示文字的 domain 必須等於 href 的 domain（含子網域比對）。
- **R-URL-2（描述型顯示文字自由）**：顯示文字不含 TLD 字樣時，視為人類可讀描述，不做 domain 比對。

R-URL-1 的觸發條件是一份 TLD 清單，而這份清單有 [#251](/report/stale-list-costs-precision-not-coverage/) 描述的形狀：**未列入的 TLD（`.ai`、`.app`、`.xyz` 等）不會觸發比對，而漏掉不產生任何訊號**——檢查回報 clean 與「這個連結沒被檢查」在輸出上完全相同。清單過時的代價因此落在覆蓋而非精度，與該卡建議的方向相反。要修的話有兩個方向：把觸發條件從列舉改成通用形態（顯示文字看起來像網域就比對），或至少讓未列入清單的 TLD 命中一個警告層。在那之前，這是一個已知且被記錄下來的缺口。

違規範例（會被 lint 阻擋）：

```markdown
[nvd.nist.gov](https://malicious.example.com/fake)     ← 顯示文字暗示 NVD，href 卻不是
[cisa.gov/advisory](https://cisa-gov.evil.example)     ← 顯示文字抄 CISA 格式，domain 不符
```

合法範例：

```markdown
[Uber 事件公告](https://www.uber.com/newsroom/security-update/)
[nvd.nist.gov/CVE-2023-34362](https://nvd.nist.gov/vuln/detail/CVE-2023-34362)
```

這條規則在紅隊 / 安全相關教材中特別重要：讀者本來就該對來源警戒，排版規則不該削弱這個警戒訊號。縮短顯示文字提升可讀性，反釣魚校驗守住安全底線，兩者互補。

### 3.3 例外情境

- **程式碼區塊**（fenced code block，```` ``` ```` 包圍）內的 URL **不做任何處理**（不縮短、不校驗）。代碼範例經常需要展示完整 URL 給讀者複製執行。
- **引用區塊**（`>` 開頭）內的 URL **比照段落處理**，會縮短也會做反釣魚校驗。

---

## 4. 表格規則

- 統一使用 **aligned 風格**：每欄內容用空白補齊到該欄的最大寬度，使 `|` 在 monospace 渲染下垂直對齊。
- 欄位分隔線使用 `| --- |` 形式，不含對齊冒號 `:`（分隔線內的 `-` 數量跟隨該欄寬度自動填足）。
- 寬度計算使用顯示寬度（display width）— CJK 字元佔 2 欄寬、ASCII 佔 1 欄寬，分隔列與資料列按同一套寬度對齊。
- `mdtools fmt --fix` 自動正規化：插入新行或改動欄寬時會全表重算，作者不需手工維持對齊。

選 aligned 而非 compact 的理由是**原始檔可讀性**：技術教材的表格常需在 code review 裡對照，aligned 風格讓 reviewer 直接看出哪些欄位對應哪些內容，不用在腦中解析鋸齒狀的 pipes。手工對齊在長表格反覆編輯時確實會失效（新增一行就全表要重對齊），但這正是 `mdtools fmt --fix` 接手的地方。

---

## 5. 基礎格式細節

這節整理容易被忽略、但會影響 parser 正確性或渲染品質的小規則。

### 5.1 程式碼區塊必須註明語言（MD040）

由 `mdtools lint` 檢查。未註明語言的 fenced code block 會被報警：

````markdown
```                   ← 違規：缺語言標示
func main() {
    fmt.Println("hi")
}
```

```go                 ← 合法
func main() {
    fmt.Println("hi")
}
```
````

純文字輸出（例如 terminal output、log 片段）使用 `text` 或 `plain`：

````markdown
```text
Error: permission denied
```
````

Shell 範例統一用 `bash`（即使是 zsh 語法，讓 syntax highlighter 有合理預設）；純設定檔依實際格式（`toml`、`yaml`、`json`、`ini`）。

### 5.2 fenced code block 前後需空行（MD031）

由 `mdtools fmt --fix` 自動處理。缺空行會讓前後段落被 parser 併入 code block 或反之。

### 5.3 列表前後需空行（MD032）

由 `mdtools fmt --fix` 自動處理。

```markdown
上一段結束。
- 列表項一           ← 違規：列表前無空行，會被部分 parser 當段落延續
- 列表項二

上一段結束。

- 列表項一           ← 合法
- 列表項二

下一段開始。
```

### 5.4 有序列表編號一致性（MD029）

由 `mdtools fmt --fix` 正規化。本專案採 `ordered` 風格（全部遞增編號）：

```markdown
1. 第一步
2. 第二步           ← 合法
3. 第三步

1. 第一步
1. 第二步           ← 違規：混用風格（fmt --fix 會改成 1./2./3.）
2. 第三步
```

選擇 `ordered` 的理由：原始檔可讀性高，作者直接看到步驟數；插入新項目的對齊代價比全部重新渲染低。

### 5.5 段落間空行

段落之間、標題前後、列表與段落之間都需空行。`mdtools fmt --fix` 會自動規範化多餘 / 缺失的空行，作者不需手工維護。

### 5.6 檔案結尾需有換行（MD047）

POSIX 文字檔規範；缺失時 git diff 會出現 `\ No newline at end of file`。`mdtools fmt --fix` 自動補。

### 5.7 Tab 字元（MD010）— 僅限 fenced code block

由 `mdtools lint` 檢查（warn 等級）。Prose / 列表 / 表格 / 引用等非 code-block 行內若出現 tab 字元，會被標記並建議改成空白；fenced code block 內的 tab 保留（Go 原始碼依 gofmt 慣例用 tab，文章要讓讀者能直接複製貼用）。

Repo 根目錄的 `.markdownlint.json` 用 `"MD010": { "code_blocks": false }` 告知 IDE 的 markdownlint extension 採用同一套 policy，讓編輯器跟 CI 的警告保持一致。

### 5.8 行長度上限（MD013）— 預設關閉

本規則**預設關閉**。中英混用的技術寫作不適用 80-char 慣例：

- 中文每字元算 1 個寬度時，80-char ≈ 40 個中文字，寫到一半就要斷行，嚴重影響可讀性。
- 中文每字元算 2 個寬度時，80-char 相當於 20-30 個中文字，更離譜。
- Markdown 編輯器普遍支援軟斷行與 IDE word wrap，實體行長度對閱讀體驗影響小。

若未來需要打開（例如發現真的有人寫出 2000-char 單行段落），建議上限 **400 字元**（軟上限，warn 不阻擋）。設定在 `scripts/mdtools/internal/rules/config.go` 的 `LineLengthLimit` 欄位。

### 5.9 裝飾符號禁用（emoji / 視覺記號）

> **本節本身豁免**：規範要描述「哪些符號禁用」必然要列舉這些符號（use-mention distinction）。本節舉例的 emoji 屬 mention（指稱）、非 use（裝飾使用）、不違反規則。掃描指令會 hit 到本節、判讀時跳過。

`content/**` 正文不可使用 emoji（如 ✅ ❌ ⚠️ 🚨 🟡 🟢 ⭐ 📌 💡 ⚡ 🎯）與裝飾性 unicode 符號（✓ ✗ ✘）。**表格、列表、行內標記都不行**。

**替換策略**（emoji 承載的語意要回到文字結構、不是純粹刪除符號）：

| 原寫法                                              | 改成                                                        |
| --------------------------------------------------- | ----------------------------------------------------------- |
| 表格 status `\| ✅ 解了 \|`                         | 純文字描述：「解了」/「是」/「適用」                        |
| 表格 status `\| ❌ 漏 \|`                           | 純文字描述：「漏」/「否」/「不適用」                        |
| 列表優缺點 `- ✅ 簡單` / `- ❌ 慢`                  | 拆成 `**優點**：簡單` / `**缺點**：慢` 段落或標題段         |
| 列表錯誤示範 `- ❌ 把 key 寄 email` / `- ✅ 用 CSR` | 拆成 `**錯誤做法**：` / `**正確做法**：` 標題段             |
| 行內視覺強調 `🚨 critical`                          | markdown 粗體 `**critical**` 或引用塊 `> **critical**：...` |

**理由**：

- **Grep-ability**：emoji 無法用 plain text grep 命中；視覺結構容易掩蓋語意結構、reviewer 看不出「優 / 缺」是用 emoji 區分還是用標題段區分
- **CLI parser 相容性**：部分 multi-byte emoji 在 Rust-based CLI 工具（如某些 mdtools / pagefind / lint pipeline）觸發 char-boundary panic
- **跨語境穩定**：emoji 在不同字型 / 平台 / 終端機渲染差異大、容易斷行或顯示為框

**掃描指令**（提交前自己跑一次、有 hit 就替換）：

```bash
rg "✅|❌|⚠️|🚨|🟡|🟢|🔴|🟠|🔵|⭐|📌|💡|⚡|🎯|✨|📝|🔍|🛠|⛔|✓|✗|✘" content/
```

> 本規則目前**未進 `mdtools lint` 自動掃描**、靠人工 grep。未來會加進 lint pipeline。

---

### 5.10 位置引用與數量命名候選掃描（REF1 / REF2、警告層）

`mdtools lint` 對 `content/**` 跑兩個警告層掃描、來源是引用紀律卡（[#155 引用章節用語意標題](/report/reference-by-semantic-title-not-number/)、[#156 集合命名用角色](/report/name-collections-by-role-not-count/)）：

- **REF1-positional-anchor**：正文中的位置式引用候選 —「見第 3 點」「詳見第五章」「§4」。位置編號是當下排列的衍生值、目標是活文件時、結構重排會讓引用 silent 指向錯的內容。
- **REF2-count-in-name**：標題與 front matter `title` 中內嵌成員數的集合命名 —「六大原則」「遷移五階段流程」。成員增減時名稱先失真、且名稱是被複製最多次的字串。

兩個規則都停在警告層、**命中是候選、不是判決** — 回報前要做語意判定：

| 命中情境                                 | 判定                      |
| ---------------------------------------- | ------------------------- |
| 引用法條條號等發布方凍結的編號           | 合規、編號是 fact         |
| 數字緊鄰它描述的清單（「確認三件事：」） | 合規、漂移在編輯當下可見  |
| 外部凍結品牌名（SOLID 五原則）           | 合規、數量由發布方凍結    |
| 目標是內部活文件 / 內部活集合            | 改語意標題引用 / 角色命名 |

掃描器內建三個自動豁免：落在 `「」` 區間內的命中視為反例引用（判定用區間包含、不是緊鄰開引號 — 引用內常帶粗體與內層 `『』`）；「第」開頭的序數（第三階段）不屬 REF2 的集合命名；同一行引用 RFC / ISO / IEEE 文件時的 `§N` 是該規格發布方凍結的編號、不隨我方結構重排漂移（`見第 N 章` 這種散文引用形式不吃這個豁免、仍照常掃）。法條條號目前沒有自動豁免、靠上表的人工判定。

### 5.11 否定起手候選掃描（POS-negation-lead、警告層）

`mdtools lint` 對 `content/**` 跑否定起手掃描、來源是 [#166 重點優先陳述是跨語言的資訊結構原則](/report/lead-with-the-point-cross-language/)（搭配 [#165 register 違規要文體異源](/report/register-violation-needs-cross-style-eyes/)）：

- **POS-negation-lead**：正文中「不是 X、而是 Y」「不是 X — 是 Y」「與其 X、不如 Y」的重點後置候選。核心概念（Y）被擠到「而是 / 不如」之後、讀者要先處理一個被否定的 X 才拿到重點。這是資訊結構效率問題、跨語言成立（英文「not X but Y」、日文「X ではなく Y」）、不是中文特有句型 — 偵測可機械化、判定不可。pattern 涵蓋的連接詞（而是 / 「— 是」/ 不如）枚舉不完、判斷標準是「核心概念在不在句首」而非哪個連接詞 — 漏掉的變體只是讓候選 silent 到有人讀到（規則第一版就漏了「不是 X — 是 Y」、靠人發現才補）。

判定用「重點位置」、**命中是候選、不是判決**：

| 命中情境                                                                              | 判定                       |
| ------------------------------------------------------------------------------------- | -------------------------- |
| 核心概念第一次正面出現在句首（「有深度、不是非黑即白的二元」）                        | 合規、重點先行             |
| 明示反例 / 對照段落內的否定（見 [#94](/report/positive-rewrite-preserves-contrast/)） | 合規、否定是對照本體       |
| 核心概念被擠到「而是」之後（「不是二元、而是有深度」）                                | 改正向、把核心概念移到句首 |

掃描器豁免兩類命中：落在 `「」` 區間內的引用（反例引用 / 句型佔位符）、以及 backtick 行內程式碼內的 pattern（grep regex / 技術識別碼）。講這個句型的 meta 卡與本規範段落大量自我觸發 — 把被討論的句型用 `「」` 包起來就同時滿足引用慣例與豁免條件，這是 meta 卡的標準寫法。全 `content/` 的存量警告已在 2026-07-10 清零（真違規改寫、引用型加 `「」`），新命中因此都是本次變更引入的、要當場判讀。

## 6. Front matter schema（`mdtools lint`）

Hugo 依賴 YAML front matter 提供 title / date / weight 等欄位給 render pipeline。缺欄位會讓列表頁、排序、SEO 壞掉，但 Hugo 本身不會失敗（靜默接受不完整資料），所以必須由 linter 守住。

### 6.1 通用層（`content/**/*.md`）

所有內容文章必須有：

- `title`：字串，不可空。
- `date`：`YYYY-MM-DD` 格式（ISO 8601 date）。

**Hugo `_index.md` section 頁面例外**：這類檔案是 Hugo 的 section 列表 landing page，不是內容文章，沒有語意上的「日期」。只要求 `title`，不強制 `date`。

### 6.2 推薦層（警告，不阻擋）

推薦填寫（`mdtools lint` warn level）：

- `description`：字串，建議 30–150 字，影響 SEO 與列表頁預覽。
- `tags`：陣列，至少 1 個標籤。

推薦層是歷史內容的緩衝區，不是新增內容的放行條件。新增文章必須同時填寫 `description` 與 `tags`；修改既有文章時，若同一檔案缺少推薦欄位，應在同次變更補齊，避免每次驗證都被舊 warning 淹沒。

驗證時先跑 changed-set scoped lint 判斷本次變更品質，再視需要跑 full lint 觀察整體基線。回報 full lint 結果時，要把歷史 warning、已知 warning 與本次新增問題分開描述。

### 6.3 卡片嚴格層（`content/backend/knowledge-cards/**`）

知識卡片額外要求（對應 `.codex/briefs/knowledge-cards.md` K2）：

- `title`、`date`、`description` 必填。
- `weight`：整數，決定在 `_index.md` 主題表格中的排序位置。

### 6.4 禁止欄位

以下欄位存在時 `mdtools lint` 警告（避免語義混淆）：

- `author`：本專案為單作者 blog，統一於 Hugo 設定。
- `permalink`：使用 Hugo 預設路徑規則，避免手動覆蓋。

若未來需要鬆綁，在 `scripts/mdtools/internal/rules/frontmatter.go` 的 `DisallowedFields` 清單調整。

### 6.5 slug 必填、跟檔名對齊

所有 content 文章 frontmatter 必須有 `slug` 欄位，值跟檔名（不含 `.md`）對齊。

```yaml
---
title: "視覺手段對齊錯誤層次"
slug: "visual-tool-error-layer-alignment"   # 跟檔名對齊
date: 2026-04-28
---
```

**為什麼必填**：

slug 是 URL 的核心識別、跨多個工具共用（Hugo build、mdtools lint、跨檔 markdown link、search index）。若不顯式定義，slug 散落在三處推導鏈：

| 來源                            | 推導值                         |
| ------------------------------- | ------------------------------ |
| Hugo 預設（從 title 用 urlize） | runtime 推導、隨 hugo 版本變化 |
| mdtools 字面比對                | 檔名 stem                      |
| 跨檔連結時的引用                | 寫作者手動算 / 複製            |

三個推導鏈不一致時 = silent broken link（mdtools pass 但 hugo build 後 404、或反過來）。把 slug 升成 frontmatter 顯式 fact、所有工具基於同一 source、消除 derivation 鏈。

詳細論述見 [report #93 URL slug 必須顯式定義為 fact](/report/url-slug-must-be-explicit-fact/)。

**檔名對齊規則**：

- 檔名命名建議：英文小寫、kebab-case 或 snake_case、不含中文（避免 hugo `urlize` 規則跨版本變動）
- slug 值 == 檔名 stem（不含 `.md`）
- 修檔名時必須同步修 slug；修 slug 時必須同步 rename 檔案

**Hugo `_index.md` 例外**：section 列表頁已有 `slug:` 欄位指定資料夾路徑、不適用本規則。

---

## 7. 卡片雙向完整性（`mdtools cards`）

作用範圍：`content/**/*.md`，重點關注 `content/backend/knowledge-cards/`。

| 層級                    | 規則                                                                                              | 實作                                           |
| ----------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **L1 連結有效性**       | 所有相對連結 `[...](/posts/markdown-writing-spec/path)` / `[...](/posts/path)` 的目標檔案必須存在 | AST 抽 Link node → 解析相對路徑 → stat 檔案    |
| **L2 卡片 orphan 偵測** | 每張卡片至少被 `content/**` 中一篇非卡片正文引用                                                  | 建反向索引 → 找無 incoming edge 的卡片         |
| **L4 卡片 K4 結構合規** | 卡片首段與「概念位置」段各至少 1 個相鄰卡片連結                                                   | AST 定位段落節點 → 統計子樹 Link 數            |
| **L6 卡片目錄登記**     | 每張卡片被自己所屬 cards root 內的某個 `_index.md` 列出                                           | 取 source 為該 root 內 section index 的 edge   |
| **L7 Fragment 有效性**  | 連結的 `#fragment` 必須命名目標頁上存在的標題                                                     | 建每頁 heading ID 索引 → 比對 edge 的 fragment |
| **L8 slug 與檔名對齊**  | 頁面若有 `slug`，值必須等於檔名 stem（`_index.md` 豁免）                                          | 取 front matter 的 `slug` → 比對 filename stem |

L3（正文首次出現術語必須連結到卡片）暫不納入，待術語字典（`.codex/briefs/knowledge-web-expansion.md`）啟動後再開。

### L2 與 L6 問的是兩個不同問題

L2 問「有沒有教學正文連這張卡」，而它刻意不計來源本身是卡片的連結——目錄頁 `_index.md` 就在 cards root 之下，所以它的連結不算 inbound edge。於是一張卡可以完全滿足 L2（好幾章都引用它），同時從來沒出現在讀者瀏覽的清單上。**連得到與列得到是兩個性質**，L6 之前只有前者有規則。

缺口會累積是因為登記動作沒有觸發器：寫章節時建卡的動機明確（那篇要連它），而回目錄補一列不改變那篇的完成度。L6 上線時全站有 101 張未登記卡片（backend 78、infra 14、monitoring 8、llm 1），建立時間橫跨數個月、分布在每個主題段，證實它是逐批累積而非某一次遺漏。

判定是機械的（檔案存在、索引沒連），因此警告層即可，不需要語意豁免。卡片經過取代而該刪除時，正確動作是刪檔而非留著不登記——訊息把這條寫在修法建議裡。

### L7 驗 fragment、L1 只驗檔案

L1 的責任停在目標檔案存在，`resolveTarget` 解析時把 `#` 之後截掉。這個分工留下的缺口是：標題一改，指向它的跨檔 anchor 全部靜默失效——連結仍然點得開、頁面仍然存在，讀者落在頁首而不知道自己該看哪一段。這是 [#155](/report/reference-by-semantic-title-not-number/) 說的「misdirected 比 dangling 難偵測」在 fragment 層的形態：dangling 有 404 當訊號，misdirected 兩端看起來都正常。

L7 補上這一層，判定是「fragment 命名的 ID 在目標頁的 heading ID 集合裡」。上線時全站 302 條帶 fragment 的連結全部命中，因此**採 error 層而非警告層**——存量為零時，之後報出來的每一條都是新斷的，放它進 main 正是這條規則要擋的事。

### L8 驗的是 Hugo 實際服務的那個 URL

L1 與 L7 都在檔案系統這一側工作：目標檔存在、目標頁有那個標題。它們共同的前提是「連結寫的路徑就是讀者最後拿到的路徑」，而 `slug` 正是打破這個前提的欄位——Hugo 有 slug 就用它當 URL 最後一段，而 repo 裡的每一條連結都是照著檔案樹寫出來的。兩者拼字不同時，檔案存在（L1 通過）、標題存在（L7 通過）、而讀者拿到 404。

促成這條規則的事故（2026-08-04 量測）：`content/macos/` 有七篇用底線檔名配連字號 slug，Hugo 發布在 `/macos/macos-apfs-volume-structure/`，而指向它們的 45 條連結全部寫成底線形式。`mdtools cards` 一路回報零錯誤——它按檔名解析，而「按檔名解析得到的答案」與「Hugo 服務的答案」在有 slug 時本來就是兩個問題。這是 [#221](/report/lint-scope-must-be-explicit-fact/) 描述的形態：零 error 與「沒有任何檢查在問這一軸」給出相同訊號。

判定是機械的（兩個字串相等），**採 error 層**：上線時全站 148 個帶 slug 的檔案全部對齊。`_index.md` 豁免，因為它的 slug 命名的是它所領的 section、不是 section 底下的頁面；代價是 `_index.md` 的 slug 寫錯會靜默改掉整個 section 的 route 而這條規則看不到。頁面若真的需要與檔名不同的 URL，正解是改檔名——同時維護兩種拼字並記住連結該用哪一種，正是這條規則要消除的狀態。

#### L8 的沉默區（規則本身也適用 #221）

L8 只在「有 slug」時判定，因此它的零 error 涵蓋兩種狀態。2026-08-04 量測，全站 3079 個非 `_index` 頁面裡有 2758 個沒有 slug、落在第二種，而這兩種的風險完全不同：

- **無 `[permalinks]` 模板的 section**（`macos/`、`report/`、`backend/` 等）：slug 缺席時 Hugo 退回檔名，與連結寫法一致，無害。目前的 2758 個無 slug 頁面全部落在這裡。
- **有 `[permalinks]` 模板的 section**：`hugo.toml` 為 `posts` / `work-log` / `record` / `other` 設了 `/<section>/:slug/`。`:slug` 缺席時 Hugo 退回的是 **title 的 urlize**，中文標題會變成 percent-encoded 字串，沒有任何連結會這樣寫。這四個 section 目前全部有 slug（183/183 route 與檔名對齊），因此這一類的存量是零。

這條規則落地時，第二類有 173 篇無 slug、指向它們的 663 條檔名式連結分布在 257 個檔案裡、全部 404。那批已於同日補齊（slug 值取檔名 stem），過程中另外處理兩個邊界：`hook&agent_how_to_define.md` 因 Hugo 會把 slug 裡的 `&` 去掉而改名，`other/application/kando.md` 因模板攤平子目錄、手寫連結兩邊都對不上而改由自動列表承接。

**「slug 必填」這一半仍然沒有任何規則承載**——L8 管拼字一致、規範管有沒有，而 lint 與 cards 都沒有在執行後者。有模板的四個 section 現在存量為零，但沒有東西會擋住下一篇忘記加 slug 的文章。要不要把必填做成規則，登記在 [文章列表](/posts/) 的 Backlog。

驗收基準要能被重跑，否則它在字面上存在、在操作上不存在。產生上面那些數字的指令記在這裡：

```bash
# 有 [permalinks] 模板的 section 裡、無 slug 的頁面數
for s in posts work-log record other; do
  n=$(rg -L --files "content/$s" -g '*.md' -g '!_index.md' 2>/dev/null | while read -r f; do
        awk '/^---$/{c++; next} c==1 && /^slug:/{found=1} c==2{exit} END{exit found}' "$f" && echo "$f"
      done | wc -l)
  echo "$s: $n"
done
```

四個 section 現在都是 0。這條指令的用途從驗收轉為回歸檢查——新文章忘記加 slug 時它會變回非零，而在「必填」做成規則之前，這是唯一會發出訊號的地方。

heading ID 用 Hugo 的 github 型 auto-ID 演算法計算，規則（hugo 建最小站實測確認）是保留 unicode 字母、數字與 `_` 並轉小寫，空白與既有連字號轉 `-`，其餘一律丟棄且**不留連字號**——全形括號、冒號、頓號、引號都適用，這也是手算 anchor 最常算錯的地方。ID 從渲染後的文字產生，所以標題內的 markdown 連結只取顯示文字、行內 code 只取內容。同頁重複標題依文件順序加 `-1` / `-2` 後綴。標題寫 `{#custom-id}` 時該 ID 一併登記。

程式碼圍籬裡的示範連結自動豁免，因為它們不是 Link node——走 AST 而非 regex 換到的性質。已知邊界是**不屬於任何標題的 anchor**（腳註反向連結、theme 注入的 ID）：repo 目前沒有這類用法，出現時的修法是讓這條規則認識那個產生器，不是放寬規則。

減少暴露的寫作面做法仍然有效：**標題不內嵌數量**（[#156](/report/name-collections-by-role-not-count/)）。實際斷掉的案例裡有一條的肇因就是標題從「33 個 vendor」改成「51 個 vendor」；現在 L7 會攔下它，而標題本來就不該把數量寫死。注意 `mdtools lint` 的 REF2 只認「數字 + 支柱 / 原則 / 步驟 / 階段 / 面向 / 心法」這組量詞，「三份來源」「三同步」「51 個 vendor」都在它的視野之外。

### 為什麼要做跨文件檢查

知識卡片是 blog 的核心知識資產。隨著卡片數量增加：

- **Orphan 卡片**（沒有正文連結進來）會變成知識死角，讀者無法發現。
- **斷掉的相對連結**（檔案被改名或移動）肉眼難以發現，只有讀者點擊失敗才暴露。
- **K4 合規**（首段 + 概念位置段要有鄰卡連結）保證卡片間的知識網不會鬆散。

這些檢查用 regex 做都卡在「段落歸屬怎麼判斷」。AST 天生知道節點的父子結構，做起來自然。

---

## 8. 執行時機

### Pre-commit hook（`.githooks/pre-commit`）

1. `mdtools fmt --fix` — 自動修格式；改動會 `git add` 回 staged，避免改完又沒進 commit。
2. `mdtools lint` — 結構檢查；失敗阻擋 commit。
3. `mdtools cards` — 完整性檢查；失敗阻擋 commit。

### Pre-push hook（`.githooks/pre-push`）

`pre-push` 的責任是把 CI 同款全量檢查提前到本機。`pre-commit` 為了速度只處理 staged markdown；`pre-push` 會跑 `make check`，也就是 `mdtools fmt --check content/`、`mdtools lint content/`、`mdtools cards content/`，讓整個 `content/` 的格式與連結 drift 在推送前被攔下。

啟用 hook：

```bash
git config core.hooksPath .githooks
# 或：make install-hooks
```

### CI（`.github/workflows/md-check.yml`）

三個子命令都跑 `--check` / 嚴格模式，任何違規 fail CI。

---

## 9. 寫作者使用指引

- 寫作時優先遵循本規範。pre-commit / pre-push 報錯時讀訊息修正；**不可用 `git commit --no-verify` 或跳過 hook 的方式繞過檢查**。
- 新增案例平行章節（例如多個「工具評測」「事件時序」）時不需登記到任何白名單 — siblings_only 自動判讀。
- 新增 URL 時優先採用裸 URL 轉換段的分級形式；若顯示文字含 TLD 字樣，確認 domain 與 href 完全一致。
- 新增卡片時確認首段與「概念位置」段各有至少一個相鄰卡片連結（L4 要求）；確認 front matter 含 `title` / `date` / `description` / `weight`（卡片嚴格層）；在該 cards root 的 `_index.md` 補一列（L6 要求）——這一步的動機不來自正在寫的那篇，最容易漏。
- 程式碼區塊養成習慣先寫語言標示再填內容；純文字輸出用 `text`。
- 改標題文字時，先查有沒有連結指向它的舊 anchor（`rg '#<舊 anchor>' content/`）。L7 會在 commit 前擋下漏改的那些，而先查一次比被擋下來再回頭找便宜。

---

## 10. 規則擴充流程

新規則進入本文的路徑：

1. 先在 `scripts/mdtools/internal/rules/` 實作為可開關的 rule（預設關）。
2. 在代表性檔案上測試誤判率。
3. **在規則的實作檔頂端宣告作用域**：這條規則掃哪些檔案、以及它結構性看不到哪些檔案。作用域是獨立於規則內容的 fact（見 [#221](/report/lint-scope-must-be-explicit-fact/)），住址固定在實作檔的 doc comment，本文只寫規則說什麼。沒有宣告時，作用域是繼承來的預設值，而繼承的預設與被決定過的選擇在程式碼裡長得一樣。
4. **上線前量一次存量並記下數字**：規則對全 content 樹報幾條、以及它的沉默區有多大。數字寫進本文對應的規則段，附上重跑那個量測的指令——沒有指令的驗收基準在字面上存在、在操作上不存在。存量非零時在對應模組的 `## Backlog` 登記清理工作，不留在規則說明裡。
5. 誤判率 < 1% 且有明確教材品質收益時，預設開啟並更新本文。
6. 預設開啟後同步修正既有違規；若違規數量大，可分批 PR。

---

## 11. 為什麼自訂而不是用現成 markdownlint

`markdownlint-cli2` 的 MD022 / MD024 / MD026 / MD029 / MD031 / MD032 / MD034 / MD036 / MD040 / MD047 / MD060 這些基礎規則都有（MD013 預設關閉、MD025 本規範嚴於原版），為什麼還要自寫？

關鍵差在**卡片雙向完整性**、**反釣魚校驗**、**Front matter schema** 這三類檢查，屬於跨文件 / AST 層 / 業務邏輯層的自訂邏輯，現成 linter 無法表達。這些檢查是 blog 品質的核心訊號，必須跟基礎格式檢查放在同一個工具鏈、同一次 AST parse 內處理，避免多個工具重複解析、重複維護。

另外 goldmark 是 Hugo 內建的 markdown parser。用同一個 parser 做 lint 保證「lint 通過 → Hugo render 一致」，杜絕兩套 parser 解讀不同的長尾 bug。

---

本文為 blog 專案 Markdown 寫作規範的單一真實來源。repo 根目錄的 `AGENTS.md` 引用本文作為排版規範權威，規則與 `scripts/mdtools` 實作保持同步。
