---
title: "Fuse.js / MiniSearch：客戶端載入索引的搜尋方案"
date: 2026-04-24
description: "客戶端搜尋的核心設計問題、Fuse.js 與 MiniSearch 如何用 build-time JSON + runtime in-memory 回應、Hugo 整合步驟、方案的內在屬性評估與兩家 library 的定位差異。"
tags: ["Hugo", "搜尋", "Fuse.js", "MiniSearch", "靜態網站"]
---

## 客戶端搜尋的問題空間

靜態站搜尋必須在 build 時或 client runtime 完成。選擇**整包序列化 + client 載入**這條路時，核心設計軸是：

| 設計軸       | 意義                                                   |
| ------------ | ------------------------------------------------------ |
| 索引內容     | 由作者在 build time 明確決定要搜哪些欄位、哪些 section |
| 索引結構     | 扁平 JSON 陣列，每筆一個頁面，欄位直寫                 |
| runtime 處理 | 在瀏覽器內建索引、記憶體內匹配                         |

Fuse.js 與 MiniSearch 是這條路上的兩個主要實作。差異在匹配策略（fuzzy vs 全文），共享的是「一包索引載入瀏覽器、之後所有查詢不再出站」這個骨幹。

---

## 核心設計：build 時序列化 + runtime in-memory

**商業邏輯**：把搜尋放在 client runtime 的關鍵是**搜尋不再跨網路來回**。第一次載入索引之後，每次打字的匹配都在使用者的 RAM 內完成，不受網路延遲影響、不受後端服務狀態影響、甚至不需要網路連線。

此設計把「索引存放」從伺服端或 CDN 移到了訪客自己的瀏覽器，換得 runtime 的完全獨立。

**CASE**：整個流程兩個時點：

**Build time（Hugo 階段）**：Hugo 用 custom output format 產出一份 JSON，每筆一個頁面。

```json
{ "title": "WAF", "url": "/backend/knowledge-cards/waf/",
  "description": "說明 WAF 如何在入口層過濾攻擊",
  "content": "完整內文…" }
```

**Runtime（瀏覽器階段）**：使用者打開搜尋頁，browser `fetch` JSON → library 在 memory 中建索引 → 使用者打字 → library 匹配 → 結果渲染。

第一次 fetch + build index 通常 100-500ms；之後的每次查詢在 memory 內匹配，一般 <10ms。

---

## 架構選擇：作者定義索引內容

**商業邏輯**：索引的範圍與欄位由誰決定，這件事決定了搜尋結果的邊界。Fuse.js / MiniSearch 採「作者顯式宣告」的路線 — Hugo template 明確列出哪些 section 進索引、每筆要哪些欄位。

這個選擇讓搜尋結果成為**作者設計決策的產物**：想排除 work-log 類別就不列入 range；想讓 tag 也可搜就加一個 `tags` 欄位到 JSON；想降低索引大小就只存 `title + description` 而不存 `content`。

**CASE**：`layouts/index.json` 決定 JSON 內容：

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

配套在 `hugo.toml`：

```toml
[outputs]
  home = ["HTML", "RSS", "JSON"]

[outputFormats.JSON]
  mediaType = "application/json"
  baseName = "index"
  isPlainText = true
```

Build 後 `public/index.json` 就是整站可搜內容的權威來源。

---

## 整合步驟（以 Fuse.js 為例）

### 1. Hugo 產生 index.json

**核心動作**：設定 custom output format，寫 template 輸出 JSON。

見上方「架構選擇」段落的 `hugo.toml` 與 `layouts/index.json`。

### 2. 搜尋頁載入 library + index

**核心動作**：前端一個 `<input>`、一段 script，完成 fetch + 建索引 + 匹配 + 渲染。

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

30 行內可以跑起來。

### 3. MiniSearch 的 API 差異

**核心動作**：選 MiniSearch 時，API 形狀相近、配置項不同。

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

- `boost` 決定各欄位命中的權重：title 命中比 content 命中重 3 倍
- `prefix: true` 讓 "WA" 命中 "WAF"
- `fuzzy: 0.2` 開啟 approximate match，容錯程度可調

---

## 方案的內在屬性

| 維度       | Fuse.js / MiniSearch 的特徵                                                   |
| ---------- | ----------------------------------------------------------------------------- |
| 覆蓋完整性 | 由作者顯式宣告索引範圍 — 要搜什麼完全可控                                     |
| 可逆性     | 移除只需刪除 `index.json` output、搜尋頁、script reference                    |
| 維護成本   | 無額外 build step；索引 schema 改動要同步改 template 與 client code           |
| 可理解性   | library 原始碼規模可讀（Fuse.js ~10KB、MiniSearch ~6KB gzipped），API 面積小  |
| 依賴前提   | 要求 Hugo 支援 custom output format（所有版本皆支援）；要求 client 能跑 JS    |
| 擴展性     | 單次查詢發生在 memory 內 — 查詢效能不受網路或站規模影響；索引載入是首次一次性 |

**與 runtime 獨立相關的延伸特徵**：

- **離線可用**：索引載入後所有查詢不需要網路；PWA 加 Cache API 讓索引也能離線快取
- **自託管**：索引資料不離開你的網域；敏感內容或私有文件特別適合
- **隱私**：訪客查詢字串不會送到任何第三方服務

**與 UI 獨立相關的延伸特徵**：

- **樣式與互動 100% 可控**：搜尋框位置、結果卡排版、modal 與否、鍵盤操作 — 每一項都由作者決定
- **與 theme 緊密整合**：UI 可以直接套用站上其他元件的 CSS variable 與設計 token

---

## 兩家 library 的定位差異

Fuse.js 與 MiniSearch 共享核心架構，**設計重心不同**：

| 面向         | Fuse.js                                                  | MiniSearch                              |
| ------------ | -------------------------------------------------------- | --------------------------------------- |
| 匹配策略     | 以 fuzzy / approximate match 為主軸                      | 傳統全文檢索（詞項匹配 + 評分）         |
| 擅長情境     | 錯字容錯、近似詞匹配 — 搜 "kubernates" 命中 "kubernetes" | 精確詞匹配、field boosting、prefix 搜尋 |
| Gzipped 大小 | ~10KB                                                    | ~6KB                                    |

兩者的 API 形狀相近，切換成本低。決定用哪一個，主要看**希望怎麼對待 query**：可能有錯字的模糊輸入偏向 Fuse.js，結構化的技術關鍵字偏向 MiniSearch。

---

## 運作特徵

### Index 在首次載入

**核心定義**：索引是一份 JSON，使用者打開搜尋頁時由瀏覽器一次性 fetch。

**含義**：首次延遲 = 下載 JSON + library 建索引。常見做法是在 `DOMContentLoaded` 就 preload JSON，讓使用者看到搜尋框時索引已建好、第一次打字即可查詢。

**規模適合度**：幾百到一兩千頁、索引 JSON 幾百 KB 到 1-2MB 的站，體驗最穩定。索引大小由作者在 Hugo template 內決定 — 只索引 title + description 可以把 size 壓到很小。

### 索引範圍由作者決定

**核心定義**：Hugo template 明確列出要進索引的 section 與欄位。

**含義**：搜尋結果的邊界是作者設計決策。增減 section、增減 field、調整儲存策略，都在 template 這一層直接生效。

### Tokenization 依 library 而異

**核心定義**：Fuse.js 採 character-level 匹配；MiniSearch 預設用空白分詞。

**含義**：

- Fuse.js 對中文天然能搜，不需要斷詞設定
- MiniSearch 對中文需要傳自訂 `tokenize` function，可以一個字一 token，或接 Intl.Segmenter 做詞界切分

### UI 由作者自己寫

**核心定義**：library 只提供搜尋 API，不提供視覺組件。

**含義**：排版、鍵盤操作、focus management、ARIA 這些 UI 層責任由作者顯式實作。收穫是與 theme 完全融合的客製體驗。

---

## 適合的場景

- 站的規模穩定在幾百到一兩千頁
- UI 需要深度客製、與 theme 風格緊密整合
- 想要最單純的 build pipeline（無 post-build step、無額外工具）
- 內容敏感、希望索引不離開自家網域
- 希望搜尋在離線狀態仍可用
- 需要 fuzzy match（Fuse.js）或精細 field boost + prefix（MiniSearch）
