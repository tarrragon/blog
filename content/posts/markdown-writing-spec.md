---
title: "Blog Markdown 寫作規範與 mdtools 檢查"
date: 2026-04-24
description: "本 blog 的 Markdown 排版規範、反釣魚校驗與卡片雙向完整性的工具化契約，由 scripts/mdtools（Go + goldmark AST）強制執行"
tags: ["Markdown", "AI協作心得", "blog心得", "lint", "goldmark"]
---

## 這篇要解決什麼

隨著 blog 文章與知識卡片成長，純靠寫作紀律維持排版一致性越來越不可靠。反覆踩到的問題橫跨兩個層級：

**結構與安全層級**（這是工具鏈存在的主要理由）：

- **裸 URL 在段落與表格中爆版**（MD034），降低閱讀體驗。
- **表格管線風格混用**（MD060），同一張表格有的有空白、有的沒有。
- **平行模板章節重複標題**（MD024），例如多案例文章的 `### 弱點環節` 出現 13 次。
- **顯示文字與實際 href 不一致**（反釣魚）— 不在標準 markdownlint 規則內，但紅隊教材脈絡下必要。
- **卡片雙向完整性**（orphan 卡片、斷連結、K4 合規）— 跨文件檢查，現成工具做不到。
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

| 子命令 | 職責 | 改檔 | 觸發時機 |
| --- | --- | --- | --- |
| `mdtools fmt [--fix\|--check]` | 格式正規化（URL、表格、空行、列表間距、trailing newline） | `--fix` 會改 | pre-commit（`--fix`）、CI（`--check`） |
| `mdtools lint` | 結構檢查（標題、反釣魚、code block 語言、front matter schema） | 否 | pre-commit、CI |
| `mdtools cards` | 跨文件完整性（連結、orphan、K4） | 否 | pre-commit、CI |

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

| 情境 | 顯示文字 | 範例（before → after） |
| --- | --- | --- |
| 路徑含識別碼（例如 CVE） | `domain.com/識別碼` | `https://nvd.nist.gov/vuln/detail/CVE-2023-34362` → `[nvd.nist.gov/CVE-2023-34362](https://nvd.nist.gov/vuln/detail/CVE-2023-34362)` |
| 路徑冗長但無識別性 | `domain.com` | `https://www.cisa.gov/news-events/alerts/2024/06/03/snowflake-recommends-...` → `[cisa.gov](https://www.cisa.gov/news-events/alerts/2024/06/03/snowflake-recommends-...)` |
| 已是 markdown 連結 | 不動 | — |

識別碼偵測用 regex 白名單，初始清單專注在高頻識別碼格式（例如 `CVE-YYYY-N`），其他格式以「遇到再加」原則擴充。清單維護在 `scripts/mdtools/internal/rules/identifiers.go`。

### 3.2 反釣魚校驗（`mdtools lint` 強制檢查）

Markdown 語法允許顯示文字與實際 href 完全不符，這是釣魚攻擊的結構基礎。本規則在 AST 層阻擋此模式。

- **R-URL-1（URL 樣顯示文字一致性）**：若顯示文字含 `.com` / `.org` / `.gov` / `.net` / `.io` / `.dev` / `.tw` 等 TLD 字樣，則顯示文字的 domain 必須等於 href 的 domain（含子網域比對）。
- **R-URL-2（描述型顯示文字自由）**：顯示文字不含 TLD 字樣時，視為人類可讀描述，不做 domain 比對。

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

- 統一使用 compact 風格：`| cell |` 前後各一格空白，欄位分隔線 `| --- |`（不含對齊冒號 `:`）。
- 欄位寬度由內容決定。**不做手工對齊、不做補空白對齊**。
- `mdtools fmt --fix` 自動正規化表格格式，作者不需手工維護對齊。

手工對齊在長表格反覆編輯時會失效（新增一行就全表要重對齊），工具化正規化比紀律維持便宜。

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

### 5.7 行長度上限（MD013）— 預設關閉

本規則**預設關閉**。中英混用的技術寫作不適用 80-char 慣例：

- 中文每字元算 1 個寬度時，80-char ≈ 40 個中文字，寫到一半就要斷行，嚴重影響可讀性。
- 中文每字元算 2 個寬度時，80-char 相當於 20-30 個中文字，更離譜。
- Markdown 編輯器普遍支援軟斷行與 IDE word wrap，實體行長度對閱讀體驗影響小。

若未來需要打開（例如發現真的有人寫出 2000-char 單行段落），建議上限 **400 字元**（軟上限，warn 不阻擋）。設定在 `scripts/mdtools/internal/rules/config.go` 的 `LineLengthLimit` 欄位。

---

## 6. Front matter schema（`mdtools lint`）

Hugo 依賴 YAML front matter 提供 title / date / weight 等欄位給 render pipeline。缺欄位會讓列表頁、排序、SEO 壞掉，但 Hugo 本身不會失敗（靜默接受不完整資料），所以必須由 linter 守住。

### 6.1 通用層（`content/**/*.md`）

所有 markdown 檔必須有：

- `title`：字串，不可空。
- `date`：`YYYY-MM-DD` 格式（ISO 8601 date）。

### 6.2 推薦層（警告，不阻擋）

推薦填寫（`mdtools lint` warn level）：

- `description`：字串，建議 30–150 字，影響 SEO 與列表頁預覽。
- `tags`：陣列，至少 1 個標籤。

### 6.3 卡片嚴格層（`content/backend/knowledge-cards/**`）

知識卡片額外要求（對應 `.codex/briefs/knowledge-cards.md` K2）：

- `title`、`date`、`description` 必填。
- `weight`：整數，決定在 `_index.md` 主題表格中的排序位置。

### 6.4 禁止欄位

以下欄位存在時 `mdtools lint` 警告（避免語義混淆）：

- `author`：本專案為單作者 blog，統一於 Hugo 設定。
- `permalink`：使用 Hugo 預設路徑規則，避免手動覆蓋。

若未來需要鬆綁，在 `scripts/mdtools/internal/rules/frontmatter.go` 的 `DisallowedFields` 清單調整。

---

## 7. 卡片雙向完整性（`mdtools cards`）

作用範圍：`content/**/*.md`，重點關注 `content/backend/knowledge-cards/`。

| 層級 | 規則 | 實作 |
| --- | --- | --- |
| **L1 連結有效性** | 所有相對連結 `[...](./path)` / `[...](../path)` 的目標檔案必須存在 | AST 抽 Link node → 解析相對路徑 → stat 檔案 |
| **L2 卡片 orphan 偵測** | 每張卡片至少被 `content/**` 中一篇非卡片正文引用 | 建反向索引 → 找無 incoming edge 的卡片 |
| **L4 卡片 K4 結構合規** | 卡片首段與「概念位置」段各至少 1 個相鄰卡片連結 | AST 定位段落節點 → 統計子樹 Link 數 |

L3（正文首次出現術語必須連結到卡片）暫不納入，待術語字典（`.codex/briefs/knowledge-web-expansion.md`）啟動後再開。

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

啟用 hook：

```bash
git config core.hooksPath .githooks
# 或：make install-hooks
```

### CI（`.github/workflows/md-check.yml`）

三個子命令都跑 `--check` / 嚴格模式，任何違規 fail CI。

---

## 9. 寫作者使用指引

- 寫作時優先遵循本規範。pre-commit 報錯時讀訊息修正；**不可用 `git commit --no-verify` 繞過 hook**。
- 新增案例平行章節（例如多個「工具評測」「事件時序」）時不需登記到任何白名單 — siblings_only 自動判讀。
- 新增 URL 時優先採用 §3.1 分級形式；若顯示文字含 TLD 字樣，確認 domain 與 href 完全一致。
- 新增卡片時確認首段與「概念位置」段各有至少一個相鄰卡片連結（L4 要求）；確認 front matter 含 `title` / `date` / `description` / `weight`（§6.3）。
- 程式碼區塊養成習慣先寫語言標示再填內容；純文字輸出用 `text`。

---

## 10. 規則擴充流程

新規則進入本文的路徑：

1. 先在 `scripts/mdtools/internal/rules/` 實作為可開關的 rule（預設關）。
2. 在代表性檔案上測試誤判率。
3. 誤判率 < 1% 且有明確教材品質收益時，預設開啟並更新本文。
4. 預設開啟後同步修正既有違規；若違規數量大，可分批 PR。

---

## 11. 為什麼自訂而不是用現成 markdownlint

`markdownlint-cli2` 的 MD022 / MD024 / MD026 / MD029 / MD031 / MD032 / MD034 / MD036 / MD040 / MD047 / MD060 這些基礎規則都有（MD013 預設關閉、MD025 本規範嚴於原版），為什麼還要自寫？

關鍵差在**卡片雙向完整性**、**反釣魚校驗**、**Front matter schema** 這三類檢查，屬於跨文件 / AST 層 / 業務邏輯層的自訂邏輯，現成 linter 無法表達。這些檢查是 blog 品質的核心訊號，必須跟基礎格式檢查放在同一個工具鏈、同一次 AST parse 內處理，避免多個工具重複解析、重複維護。

另外 goldmark 是 Hugo 內建的 markdown parser。用同一個 parser 做 lint 保證「lint 通過 → Hugo render 一致」，杜絕兩套 parser 解讀不同的長尾 bug。

---

本文為 blog 專案 Markdown 寫作規範的單一真實來源。repo 根目錄的 `AGENTS.md` 引用本文作為排版規範權威，規則與 `scripts/mdtools` 實作保持同步。
