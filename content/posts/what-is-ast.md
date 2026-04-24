---
title: "什麼是 AST — 從字串到語法樹的視角轉換"
date: 2026-04-24
description: "解釋 AST（抽象語法樹）是什麼、跟 regex 工具的差異在哪、什麼時候該升級到 AST 工具鏈。以 blog 專案自訂的 markdown linter 為例。"
tags: ["AST", "Markdown", "goldmark", "lint", "工具設計"]
---

## 為什麼會碰到這個詞

最初的問題很小：blog 文章數量成長後，每次 commit 都會收到 markdownlint 的同類警告反覆出現。有三個代表性的：

- `MD034/no-bare-urls` — 裸 URL 散落在段落與表格。
- `MD024/no-duplicate-heading` — 平行結構章節（例如 13 個案例各自有 `### 弱點環節`）全部被判重複。
- `MD060/table-column-style` — 表格管線前後空白不一致。

前兩個用現成工具 `--fix` 不一定修得乾淨，因為 `MD024` 的「重複」在我們的語境下是**合法的平行結構**（不同父標題下重名其實是特色），而「裸 URL 轉換」要處理表格儲存格、程式碼區塊等特殊情境，單純 regex 會誤判。

討論到後來關鍵字出現：**要做得精確，可能要用 AST 工具，而不是 regex 工具**。

那麼 AST 到底是什麼？跟我們熟悉的 regex / 字串處理差在哪？

## Regex 工具看世界的方式：字元序列

Regex 工具處理 markdown 的方式是「逐行掃描 + pattern matching」。它看到的是字元流，沒有語法結構的概念。

舉個例子：

```markdown
## 【案例一】Uber 2022

事件中攻擊者取得 `session_token`，參考：
https://www.uber.com/newsroom/security-update/

| 事件 | 來源 |
| --- | --- |
| Uber 2022 | https://uber.com |
```

Regex 工具看到的是：

```text
Line 1: "## 【案例一】Uber 2022"            ← ^#{1,6} match  → heading
Line 3: "事件中攻擊者取得 `session_token`..."  ← 無 pattern 命中
Line 4: "https://www.uber.com/..."            ← ^https?:// match → bare URL!
Line 7: "| Uber 2022 | https://uber.com |"   ← ^\| match     → table row
```

每一行獨立判讀，沒有上下文。Regex 工具不知道 line 4 到底是「段落的一部分」、「引用區塊裡的連結」、還是「程式碼範例」。它只看 pattern。

## AST 工具看世界的方式：語法樹

AST = Abstract Syntax Tree，抽象語法樹。AST 工具先把整段 markdown 用 parser **解析成結構化的樹**，然後工具在樹上走訪（traverse），操作「節點」而不是「行」。

同一段 markdown，goldmark（Hugo 內建的 markdown parser）解析後的樹大致是：

```text
Document
├── Heading (level=2)
│   └── Text: "【案例一】Uber 2022"
├── Paragraph
│   ├── Text: "事件中攻擊者取得 "
│   ├── CodeSpan: "session_token"            ← 知道這是 inline code
│   ├── Text: "，參考："
│   └── AutoLink: "https://www.uber.com/..."  ← 知道這是段落中的裸 URL
└── Table
    ├── TableHeader: [事件, 來源]
    └── TableRow
        ├── TableCell: "Uber 2022"
        └── TableCell: AutoLink "https://uber.com"  ← 知道這是表格儲存格中的 URL
```

對同一個 URL，AST 工具能分辨「它在段落裡」還是「它在表格儲存格裡」還是「它在程式碼區塊裡」— 因為節點的父子關係已經是樹的一部分。

這個差異乍看像技術細節，實際影響的是能寫出什麼樣的規則。

## 典型踩坑情境：regex 會誤判的三個 case

### 程式碼區塊內的 URL

````markdown
## 測試範例

```bash
curl https://example.com/api  # 這是程式碼範例，不該報 MD034
```
````

Regex 看到 `https://` 開頭就標記裸 URL。AST 知道這一行在 `FencedCodeBlock` 子樹內，跳過。

### Front matter 裡的 `#` 被當 heading

```markdown
---
title: "Python 的 # 註解語法"
---

真正的文章內容...
```

Regex 看到 `^#` 就當 heading 記一筆（title 裡面有 `#` 字元）。AST 知道 `---...---` 區塊是 YAML front matter，title 的值是字串。

### 平行結構標題被誤判為重複

在多案例教材裡：

```markdown
## 【案例一】Uber 2022
### 弱點環節        ← 第 1 次出現
### 攻擊路徑

## 【案例二】Okta 2023
### 弱點環節        ← 第 2 次出現，regex 會直接報重複
```

要用 regex 實作「不同父標題下允許重複」這種 `siblings_only` 規則，需要自己維護狀態機追蹤「目前 H2 是誰」「遇到 H3 時算哪個 H2 底下」。遇到 H4/H5 階層更複雜。

用 AST，父子關係已經內建在樹結構裡：

```go
// 偽代碼，實際用 goldmark walker 取代
for _, h2 := range allHeadingsAtLevel(doc, 2) {
    children := childrenOfType(h2, Heading)
    checkDuplicates(children)  // 自動只比對同一 H2 下的子標題
}
```

不用追蹤狀態，邏輯上直接表達。

## 為什麼對我們特別重要：goldmark = Hugo 的 parser

Hugo（blog 的 static site generator）內建的 markdown parser 就是 goldmark。用 goldmark 寫 lint 有個平凡但關鍵的保證：**lint 的判讀跟 Hugo render 的判讀完全一致**。

如果用不同的 parser 寫 lint（例如 Python 的 `mistune`、JavaScript 的 `markdown-it`），很可能遇到這種尷尬：

- Lint 通過，但 Hugo 解析不出來，render 失敗或跑版。
- Lint 報錯，但 Hugo 看得懂、實際沒有問題。

兩套 parser 解讀差異是長尾 bug 的溫床。用同一個 parser 可以從源頭杜絕這類不一致。

## 什麼時候 AST 不是必要的

不要為了「比較先進」就上 AST。Regex 在下列情境完全夠用：

- 檢查每行開頭字元（`^#`、`^|`、`^- `）。
- 簡單字串替換（例如 URL 前後加 `<>` 包裹）。
- 不需要知道上下文的格式正規化（行尾空白、tab 轉空白）。

需要 AST 才能穩定做到的是：

- 判斷「這段文字在 code block 內嗎？」
- 判斷「這個 heading 的父 heading 是誰？」
- 追蹤跨文件的連結關係（卡片 backlink 完整性）。
- 檢查「這個 Strong 節點是不是整個段落的唯一子節點？」（MD036 粗體當標題濫用）

一個實務判準：**如果 rule 需要「知道這段文字處在什麼結構中」，regex 會卡住；AST 天生就有這個資訊。**

## 我們的判斷：什麼時機該升級到 AST

blog 專案一開始也考慮過用 Python + regex 先頂著，等規則變複雜再升級 Go + goldmark。後來有兩件事讓我們直接選 AST：

1. **MD024 siblings_only** 已經是「需要上下文」的規則，regex 做得到但會寫得脆弱。
2. **知識卡片雙向完整性**是當前在做的工作（每張卡片要被正文連到、每張卡片首段要有鄰卡連結），這類**跨文件 + 段落歸屬**的檢查，regex 做不出來。

當需求已經在手上，延遲決策反而更貴。對我們來說，AST 不是超前部署，是**現在的 blocker**。

## 延伸閱讀

- [Blog Markdown 寫作規範與 mdtools 檢查](/posts/markdown-writing-spec/) — 所有規則的正式契約
- [mdtools：Go + goldmark 的 markdown 工具鏈設計](/posts/mdtools-design/) — 如何把 AST 能力組裝成 pre-commit hook
- [goldmark 官方 repo](https://github.com/yuin/goldmark) — Hugo 所用的 markdown parser
