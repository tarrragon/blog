---
title: "Pagefind：靜態站搜尋的 build-time 索引方案"
date: 2026-04-24
description: "靜態站搜尋的核心設計問題、Pagefind 如何用 index 切片與 post-build HTML 爬取回應這些問題、整合到 Hugo + GitHub Pages 的步驟、以及方案的內在屬性評估。"
tags: ["Hugo", "搜尋", "Pagefind", "靜態網站", "工具設計"]
---

## 靜態站搜尋的問題空間

靜態站沒有後端可以接查詢，所有搜尋工作必須在兩個時點之一完成：**build 時**產生索引、**client runtime** 執行匹配。這個前提決定了所有靜態站搜尋方案共同面對的兩個設計軸：

| 設計軸 | 意義 |
|-------|------|
| 索引產生時機 | build 時靜態產生，或 client 載入後動態建立 |
| 索引交付方式 | 一次全量下載，或按查詢 lazy-load |

方案差異來自這兩軸的組合。Pagefind 選的是「build 時產生、按需載入」，它的所有設計決策都是這個選擇的延伸。

---

## 核心設計：索引切片與按需載入

**商業邏輯**：搜尋索引的 scaling 關鍵不是壓縮率、不是演算法效率，而是**單次查詢需要下載多少資料**。若索引是一整包、每次查詢都要先整包載入，訪客體驗與站的大小線性綁定 — 站大 10 倍，首次搜尋延遲 10 倍。

要脫離這條綁定，索引必須能以「與查詢相關」的粒度切片、按需傳輸。這把「索引多大」的問題從訪客手上移回 build pipeline。

**CASE**：Pagefind 的索引是三層結構：

| 層次 | 內容 | 大小 |
|------|------|------|
| `pagefind-entry.json` | 索引目錄，記載有哪些 chunk 與 fragment | <10KB |
| `index/*.pf_index` | 倒排索引切片，依 term 前綴分片 | 10-50KB / chunk |
| `fragment/*.pf_fragment` | 每篇文章的 metadata、URL、摘要 | 2-5KB / fragment |

查「WAF」時，client 下載路徑是：entry（10KB）→ 涵蓋 "W" 的 index chunk（~30KB）→ 命中文章的 fragment（每筆 3KB）。總傳輸量與全站大小幾乎脫鉤 — 站擴大 10 倍，單次搜尋仍然只下載「W」那個 chunk 與少數 fragment。

---

## 架構選擇：爬 rendered HTML

**商業邏輯**：索引內容的來源有兩種可能：**source 層**（markdown、frontmatter、結構化資料）或 **output 層**（render 後的 HTML）。選哪一層決定工具與 framework 的耦合程度 — source 層要求工具懂特定 framework 的內容模型；output 層只要求結果是 HTML。

Pagefind 選 output 層。含義是：它跟 Hugo、Jekyll、Zola、Next.js static export 完全解耦，只要該 framework 產出的是 HTML，Pagefind 都能索引。

**CASE**：此選擇在 blog 端的具體要求：希望被搜到的內容必須出現在 rendered HTML 上。frontmatter 的 `description` 欄位若只存在於 markdown source、沒被 theme 輸出成 `<meta>` 或可見文字，就不會進索引。

這個 blog 天然滿足 — theme 把 description 寫進 `<meta name="description">`，render hook 也用它做 tooltip。移植到任何其他 static site generator，只要目標的 output HTML 有這些欄位，搜尋整合不用重寫。

---

## 整合步驟

### 1. Build pipeline

**核心動作**：Hugo build 後加一步 Pagefind。

```bash
hugo --minify
npx -y pagefind --site public
```

兩步，沒有中間檔。Pagefind 自行讀取 `public/` 的 HTML，將索引寫回 `public/pagefind/`。

### 2. 搜尋頁路由

**核心動作**：建立 Hugo 單頁，指向專屬 layout。

```yaml
---
title: "搜尋"
layout: search
sitemap:
  disable: true
---
```

`sitemap.disable` 避免搜尋頁自己被 Hugo sitemap 收錄。

### 3. UI 掛載

**核心動作**：在 layout 中載入 Pagefind UI 資源，指定 mount point。

```html
{{ define "main" }}
<div data-pagefind-ignore>
  <link href="{{ "pagefind/pagefind-ui.css" | relURL }}" rel="stylesheet">
  <div id="search"></div>
  <script src="{{ "pagefind/pagefind-ui.js" | relURL }}"></script>
  <script>
    window.addEventListener('DOMContentLoaded', function () {
      new PagefindUI({
        element: "#search",
        showSubResults: true,
        translations: { placeholder: "搜尋卡片或文章…" }
      });
    });
  </script>
</div>
{{ end }}
```

兩個細節：

- `data-pagefind-ignore` 告訴 Pagefind 這頁本身不要進索引（避免搜「搜尋」出現搜尋頁）。
- `relURL` 處理 baseURL 的 subpath（例如 `/blog/`），讓 UI 自動推斷 chunk 相對位置。

### 4. CI workflow

**核心動作**：GitHub Actions 在 Hugo build 步驟後插入 Pagefind。

```yaml
- name: Build Pagefind search index
  run: npx -y pagefind --site public
```

ubuntu-latest runner 內建 node，`npx -y` 首次執行會下載並 cache binary，後續執行直接從 cache 取用。

---

## 方案的內在屬性

評估 Pagefind 不看「比較快」「比較省事」這類時間維度，用下列內在屬性：

| 維度 | Pagefind 的特徵 |
|------|----------------|
| 覆蓋完整性 | 索引全站 HTML；不需要逐 section 註冊 |
| 可逆性 | 產物是檔案，移除就是刪除 `public/pagefind/` 與搜尋頁，無殘留依賴 |
| 維護成本 | build pipeline 多一步；無 runtime 服務、無 key 管理、無版本相依性 |
| 可理解性 | UI drop-in、filter 用 HTML 屬性宣告、三層索引結構直觀 |
| 依賴前提 | 要求目標 framework 能產出 HTML（絕大多數 static generator 滿足） |
| 擴展性 | 單次查詢下載量與全站大小脫鉤 — scaling 由 build time 吸收，不轉嫁到訪客 |

**內建的一等公民特性**：

- **Filter by facet**：`data-pagefind-filter="type:card"` 標在 HTML 元素上，UI 自動出現對應 filter checkbox
- **Snippet highlighting**：命中的關鍵字在結果摘要中高亮
- **無障礙**：Component UI（1.5.0+）內建 keyboard navigation、ARIA label、screen reader 公告

這些特徵都源自「build 時產生 + 按需載入」這個核心選擇的延伸，不是外掛功能。

---

## 運作特徵

### zh-tw 走 character n-gram

**核心定義**：Pagefind 對非空白分詞語言採 n-gram — 以字元序列作為匹配單位，而非詞。

**行為**：搜「負載平衡」能命中「負載平衡器」、「負載平衡器測試」等任何包含該字元序列的頁面。啟動時會印一行 stemming note，那是針對屈折變化語言（英文、德文）的 stemming 提示，對中文無意義也無限制。

**邊界**：少數情境下跨詞邊界的字元組合會誤命中（例如搜「負載過」可能命中「負載過高」與「負載過往」）。在名詞為主的技術站影響極小。

### 索引來自 rendered HTML

**核心定義**：索引內容 = Pagefind 在 `public/*.html` 看到的可見文字與 meta tag。

**含義**：想加入索引的欄位必須出現在 output HTML 上。想排除的區塊用 `data-pagefind-ignore` 標記。想作為 filter 的屬性用 `data-pagefind-filter="name:value"`。

### Default UI 的樣式是 Pagefind 自家風格

**核心定義**：`PagefindUI` component 有固定的視覺設計，透過 CSS variable 可微調顏色、圓角、spacing。

**含義**：想要與 theme 完全融合有兩條路 — 覆寫 CSS variable（官方 docs 列出可覆寫清單），或改用 Pagefind JS API 自己組 UI（更完整客製）。

### Build pipeline 多一步

**核心定義**：Pagefind 是 Hugo build 外的獨立步驟。

**含義**：CI 與本地都要記得跑 `npx pagefind`。這個 blog 以 Makefile 的 `make site` 封裝 `hugo + pagefind` 兩步，把「記得」轉成 infrastructure 強制項。

---

## 適合的場景

- 靜態站、內容持續成長
- 部署在 GH Pages / Netlify / Cloudflare Pages 等純靜態平台
- 希望零外部依賴、完全自託管
- 內容以文字為主（blog、docs、knowledge base）
- 未來可能換 framework — 希望搜尋整合不隨之重寫
