---
title: "baseof.html override 範圍最小化"
date: 2026-04-25
weight: 32
description: "Override theme 檔案時、只動非改不可的部分、註解標明跟 theme 版本的差異 — 升級時容易 sync 變更、不會吃掉本地客製。"
tags: ["report", "事後檢討", "Hugo", "Theme", "工程方法論"]
---

## 核心原則

**Override theme 檔案的範圍越小、theme 升級時越容易 sync。** 整檔 copy + 改 1-2 行的 override 在 theme 改了 baseof 時、本地必須手動 merge；只 override 必要的部分（用 partial 或最小檔案）讓變更面積小、merge 容易。

---

## 為什麼 override 要小

### 商業邏輯

Hugo theme 的 lookup order：本地 `layouts/` 優先於 `themes/<name>/layouts/`。本地有同名檔案、本地的整個內容生效、theme 的版本完全被忽略。

當本地 override 整個 baseof.html、只改 1-2 行：

| Theme 升級時的代價                                               |
| ---------------------------------------------------------------- |
| 本地 override 不會自動更新 — 永遠是當初 copy 的版本              |
| Theme 的新功能（新 partial、改進的 SEO meta）不會生效            |
| 要手動 diff `themes/<name>/layouts/baseof.html` 與本地、合併變更 |
| 容易忘記、theme 的修正在本地永遠沒套到                           |

Override 範圍小 = merge 面積小 = 升級時手動 sync 的工作量小。

---

## 這次任務的 override

### 觀察

`layouts/_default/baseof.html` 是整個 theme 的 baseof 複製、只改了：

```diff
- <body>
+ <body{{ if eq .Layout "search" }} class="page-search"{{ end }}>
+   {{- partial "pagefind_meta.html" . -}}
```

兩個改動：

1. `<body>` 加條件 class（搜尋頁需要的 hook）
2. `<main>` 內加 `pagefind_meta.html` partial 引用

整個 baseof（44 行）完全 copy、只為了這兩處 5 行改動。

### 判讀

兩個改動都有更小的 override 方式：

#### 改動 1：body class

Hugo 的 `block` 機制讓 child template override `block` 內容。如果 theme baseof 預先定義了 `body-class` block：

```html
<!-- theme baseof.html -->
<body class="{{ block "body-class" . }}{{ end }}">
```

那本地搜尋頁 layout 可以：

```html
<!-- layouts/_default/search.html -->
{{ define "body-class" }}page-search{{ end }}
```

不需要 override 整個 baseof。

但這次的 theme 沒有 `body-class` block — 所以這條路不通、必須 override。

替代：用 `custom_body.html` 之類已有的 partial hook。Theme 可能在 body 結束前 inject `custom_body.html`、但那發生在 body 開始之後、無法影響 body 的 attribute。

結論：第一個改動需要 override baseof、無更小的方式。

#### 改動 2：pagefind_meta.html partial

這個 partial 注入在 `<main>` 開頭、加 hidden filter spans。可以放到 `custom_head.html`（theme 已有的 hook） — 但 head 內的元素不會被 pagefind 索引、所以那條路不通。

也可以從每個 layout 內手動引入：

```html
<!-- layouts/_default/single.html -->
{{ define "main" }}
{{- partial "pagefind_meta.html" . -}}
<h1>{{ .Title }}</h1>
...
{{ end }}
```

但這樣每個 layout（single、list、search、taxonomy）都要重複引用 — 維護成本不一定更低。

結論：第二個改動放在 baseof 比放在每個 layout 更乾淨。

### 執行：當前 override 已是最小

兩個改動都是 baseof override 較合理。但可以做的精簡是 **註解標明跟 theme 版本的差異**：

```html
{{- /*
  本地 override theme baseof.html。

  跟 themes/hugo-bearcub/layouts/_default/baseof.html 的差異：
    1. <body> 加條件 class="page-search"（給搜尋頁的 CSS / JS hook 用）
    2. <main> 內加 partial "pagefind_meta.html"（注入 pagefind filter metadata）

  Theme 升級時、把上面兩個改動套到新版 baseof 即可。
*/ -}}
<!DOCTYPE html>
<html lang="...">
...
```

註解告訴未來的維護者「這檔案 override 了什麼、為什麼、升級時要看哪些 diff」。

---

## 內在屬性比較：四種 override 策略

| 策略                                 | 改動面積   | 升級成本                    | 適用情境                 |
| ------------------------------------ | ---------- | --------------------------- | ------------------------ |
| 整檔 copy + 修改                     | 大         | 高 — 手動 merge 整檔        | Theme 沒提供 hook、必要  |
| Override 加註解標明 diff             | 大         | 中 — 註解告訴升級者改了什麼 | 整檔 override 的最佳實踐 |
| 用 theme 提供的 partial / block hook | 小         | 低 — theme 升級不影響       | Theme 設計時預留了 hook  |
| Fork theme 並維護                    | 整個 theme | 最高 — 整個 theme 都要 sync | 客製極深、theme 沒 hook  |

優先選「用 theme 提供的 hook」、次選「override 加註解」、最後才考慮 fork。

---

## Override 的具體最佳實踐

### 1. 註解標明 diff

```html
{{- /*
  Override theme/.../baseof.html。
  改了：
    - <body> 加 class hook
    - <main> 內加 partial
*/ -}}
```

註解讓未來維護者一眼知道改了什麼。

### 2. Override 檔案內容對齊 theme 版本

當 theme 升級時：

```bash
diff themes/hugo-bearcub/layouts/_default/baseof.html \
     layouts/_default/baseof.html
```

差異應該只有註解內標明的那幾處。如果差異更多 — 表示 theme 有變更我們沒套到。

### 3. 標明 theme 版本

```html
{{- /*
  Override based on themes/hugo-bearcub@v1.2.3.
  跟該版本的 baseof.html 差異：...
*/ -}}
```

知道是基於哪個版本 override、升級到 v1.3.0 時知道要 diff 哪兩個版本。

### 4. 主動建議 theme 加 hook

如果常需要 override theme 同樣的位置、考慮給 theme 提 PR 加 `block` 或 `partial` hook — 這樣升級後 hook 自動有、不需要繼續 override。

---

## 設計取捨：Theme 客製的策略

四種做法、各自機會成本不同。優先選 A（用 theme hook）— 不夠用才退到 B / C / D。

### A：用 theme 提供的 partial / block / template hook（最佳）

- **機制**：theme 預留 `block`、`custom_head.html`、`custom_body.html` 等 hook、本地只填 hook
- **選 A 的理由**：theme 升級不影響本地客製、hook 是公開介面
- **適合**：theme 設計時預留了對應 hook 的客製需求
- **代價**：需要 theme 預先支援、若不支援考慮給 theme 提 PR 加 hook

### B：Override 加 diff 註解（這個專案的預設）

- **機制**：複製 theme 檔案到本地、改必要的部分、註解標明跟 theme 版本的差異
- **跟 A 的取捨**：B 不需要 theme 預留 hook、A 需要；B 升級時要手動 sync
- **適合**：theme 沒對應 hook、必須 override
- **代價**：升級時要 diff theme 新版手動 merge、註解可降低 merge 成本

### C：Override 不加註解

- **機制**：複製 theme 檔案、改必要部分、不註解
- **跟 B 的取捨**：C 寫法簡單、B 額外註解；但 C 未來維護者不知為什麼這檔案在本地、漏 sync 風險高
- **C 才合理的情境**：純探索性 override、之後會還原 — production 不該如此

### D：Fork theme 維護自己版本

- **機制**：fork theme 整個 repo、所有客製改在 fork 內
- **成本特別高的原因**：每次原 theme 升級都要 merge upstream、長期維護負擔重
- **D 才合理的情境**：客製極深（多檔案 override + 改 internal logic）、且願意承擔 fork 維護成本

---

## 判讀徵兆

| 訊號                                  | Refactor 動作                             |
| ------------------------------------- | ----------------------------------------- |
| 整檔 override theme 檔案、只改 1-2 行 | 加註解標明 diff、未來容易升級             |
| Override 不知道是基於哪個 theme 版本  | 加版本註解                                |
| Theme 升級後本地客製失效 / 出怪事     | Diff theme 新版與本地 override、手動 sync |
| 多個 override 檔案、不知道為什麼存在  | 每個 override 加用途註解                  |
| 同樣的客製需求要 override 多個檔案    | 評估給 theme 提 PR 加 hook                |

**核心原則**：Override 是雙面刃 — 短期解決客製、長期增加升級成本。把 override 範圍與 diff 範圍維持最小、註解說明來由 — 是長期可維護的妥協。
