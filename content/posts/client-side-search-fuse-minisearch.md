---
title: "Fuse.js / MiniSearch：客戶端載入索引的搜尋方案"
date: 2026-04-24
description: "Fuse.js 與 MiniSearch 的運作方式、用 Hugo custom output format 產生索引 JSON 的方法、前端整合步驟、可控的 UI 客製能力，以及它們適合的場景。"
tags: ["Hugo", "搜尋", "Fuse.js", "MiniSearch", "靜態網站"]
---

## 它們是什麼

Fuse.js 與 MiniSearch 是**純 JavaScript 的搜尋 library** — 跑在瀏覽器裡、不需要任何後端。使用方式很直接：build 時把要搜的資料序列化成 JSON，瀏覽器載入這個 JSON、交給 library 建 in-memory 索引、使用者打字時在 client 即時匹配。

兩者定位相近、各有側重：

- **Fuse.js** — 以 fuzzy / approximate match 著稱，對拼錯與近似詞有容錯，~10KB gzipped
- **MiniSearch** — 偏向傳統全文檢索，支援 prefix、boolean、field boosting，~6KB gzipped

也可以把 Lunr.js 算同一類，但它較老、API 較沉。

## 運作機制

整個流程在兩個時點發生：

### Build time（Hugo 階段）

Hugo 用 custom output format 吐出一份 `index.json`，內含所有要搜的頁面。每筆通常是：

```json
{ "title": "WAF", "url": "/backend/knowledge-cards/waf/",
  "description": "說明 WAF 如何在入口層過濾攻擊", "content": "完整內文…" }
```

### Runtime（瀏覽器階段）

使用者打開搜尋頁，browser `fetch` 這份 JSON → library 讀進去建索引 → 使用者打字時 library 在 memory 內匹配 → 結果渲染回 DOM。

整個過程沒有網路來回（除了最初那次 JSON 下載）、沒有後端參與。匹配速度非常快，因為資料都在記憶體裡。

## 整合步驟（以 Fuse.js 為例）

### 1. Hugo 產生 index.json

`config.toml` 新增一個 output format：

```toml
[outputs]
  home = ["HTML", "RSS", "JSON"]

[outputFormats.JSON]
  mediaType = "application/json"
  baseName = "index"
  isPlainText = true
```

`layouts/index.json` 決定 JSON 內容：

```go-html-template
{{- $pages := where .Site.RegularPages "Section" "in" (slice "posts" "backend" "go" "python") -}}
[
{{- range $i, $p := $pages -}}
  {{- if $i }},{{ end }}
  { "title": {{ .Title | jsonify }},
    "url": {{ .RelPermalink | jsonify }},
    "description": {{ .Description | jsonify }},
    "content": {{ .Plain | jsonify }} }
{{- end -}}
]
```

Build 完 `public/index.json` 就是整站的可搜內容。

### 2. 搜尋頁載入 library + index

`layouts/_default/search.html`：

```html
{{ define "main" }}
<input id="q" placeholder="搜尋…">
<ul id="results"></ul>

<script src="https://cdn.jsdelivr.net/npm/fuse.js@7/dist/fuse.min.js"></script>
<script>
  fetch('{{ "index.json" | relURL }}')
    .then(r => r.json())
    .then(data => {
      const fuse = new Fuse(data, {
        keys: ['title', 'description', 'content'],
        threshold: 0.3,
        includeMatches: true
      });
      document.getElementById('q').addEventListener('input', e => {
        const results = fuse.search(e.target.value).slice(0, 20);
        document.getElementById('results').innerHTML = results
          .map(r => `<li><a href="${r.item.url}">${r.item.title}</a>
                     <p>${r.item.description}</p></li>`)
          .join('');
      });
    });
</script>
{{ end }}
```

核心就這樣 — 30 行內可以跑起來。

### 3. MiniSearch 的差別

MiniSearch 的 API 類似，但額外支援 field boosting 與 prefix search：

```js
const mini = new MiniSearch({
  fields: ['title', 'description', 'content'],
  storeFields: ['title', 'url', 'description'],
  searchOptions: {
    boost: { title: 3, description: 2 },
    prefix: true,
    fuzzy: 0.2
  }
});
mini.addAll(data);
const results = mini.search(query);
```

Boost 讓 title 命中比 content 命中更重要；prefix 讓 "WA" 也能命中 "WAF"。

## 優點

**整合單純、路徑短。** 一個 JSON output、一個 HTML 頁面、一段 script — 不需要額外工具、不需要 post-build step、不用 Makefile 或 CI 改動。

**UI 完全自己寫，樣式與互動 100% 可控。** 搜尋框的位置、結果卡片的排版、有沒有 modal、要不要鍵盤操作 — 全都由你決定。可以跟 theme 風格完全融合。

**library 體積小、容易理解。** Fuse.js ~10KB、MiniSearch ~6KB（gzipped）。整個 library 原始碼規模可讀、API 面積小、debug 容易。

**離線可用。** 使用者載入一次後，即便斷網或 refresh 也能搜（PWA 加 Cache API 就完全離線）。

**Fuzzy match 開箱強。** Fuse.js 的 approximate match 對錯字、相似詞容錯極好 — 搜 "kubernates" 能命中 "kubernetes"。這是 Lucene 家族的傳統全文檢索不擅長的地方。

**Field boosting 細緻。** MiniSearch 的 boost 機制讓你精確控制排序權重，例如 title 比 content 重要 3 倍、description 重要 2 倍。

**完全自託管、無第三方。** 索引資料不離開你的網域。敏感內容或私有文件的搜尋特別適合。

## 需要知道的事

**Index 是一次性下載。** 使用者第一次打開搜尋頁會載入整份 `index.json`。這決定了它最適合的規模 — 幾百到一兩千頁、索引大小幾百 KB 到 1-2MB 的站點，體驗非常好。

**首次載入有延遲，之後很快。** 第一次 fetch JSON + build index 可能 100-500ms；之後的每次打字都在 memory 內匹配，通常 <10ms。常見做法是在搜尋頁的 `DOMContentLoaded` 就 preload JSON，讓使用者看到搜尋框時索引已建好。

**要自己決定索引什麼。** Pagefind 直接爬 rendered HTML；Fuse.js / MiniSearch 需要你在 Hugo template 裡明確列出要索引的 section、要哪些 field。這個「明確」是代價也是優點 — 代價是多寫幾行，優點是 100% 控制範圍。

**Tokenization 看 library。** Fuse.js 是 character-level 匹配，對中文天然能搜（不需要斷詞）；MiniSearch 預設用空白斷詞，對中文要傳自訂 `tokenize` function（例如每個字一個 token，或接 intl segmenter）。

**排版客製 = 要自己寫。** 沒有 drop-in UI，排版、無障礙、鍵盤操作、focus management、ARIA 都要自己處理。對想要完全客製的人是優點；對想要「開箱就好」的人是工作量。

## 適合的場景

- 站不大（幾百到一兩千頁）且規模成長可預期
- UI 需要深度客製，與 theme 風格緊密整合
- 想要最少的構建步驟、最單純的 pipeline
- 內容敏感、不想接第三方服務、索引不離開網域
- 開發者本身熟悉前端，享受親手打造搜尋體驗的過程
- 需要 fuzzy match（Fuse.js）或精細的 field boost / prefix 搜尋（MiniSearch）
