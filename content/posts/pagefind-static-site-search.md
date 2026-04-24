---
title: "Pagefind：靜態站搜尋的 build-time 索引方案"
date: 2026-04-24
description: "Pagefind 的運作機制、整合到 Hugo + GitHub Pages 的步驟、UI 掛載方式、zh-tw 的行為、以及它適合的場景。"
tags: ["Hugo", "搜尋", "Pagefind", "靜態網站", "工具設計"]
---

## 它是什麼

Pagefind 是一個為靜態站設計的搜尋方案。它不是一個 library、也不是 service — 是一個 **post-build 工具**：Hugo build 完 `public/` 之後，Pagefind 去爬那個目錄的 HTML，產生一組切片式的搜尋索引、外加一個 drop-in UI，全部寫回 `public/pagefind/` 底下。成品還是純靜態檔，直接丟 GitHub Pages、S3、任何 CDN 都能跑。

由 Cloudcannon 維護，binary 以 npm package 形式發佈，`npx -y pagefind` 會自動下載對應平台的 binary。

## 運作機制

三層資料結構：

1. **`pagefind-entry.json`** — 索引目錄，UI 載入時第一個抓的檔，大小 <10KB。記錄這站有哪些 index chunk、有哪些 fragment。
2. **`index/*.pf_index`** — 倒排索引切片。Pagefind 依 term 前綴把索引分片，一個 chunk 通常 10-50KB。使用者打字時，UI 只抓含該 term 的 chunk。
3. **`fragment/*.pf_fragment`** — 每篇文章的 metadata、URL、摘要片段。搜到才載對應 fragment，一個約 2-5KB。

查「WAF」時 client 的傳輸大約是：entry（10KB）+ 涵蓋 "W" 的 index chunk（~30KB）+ 命中的 fragment（每筆 3KB）。**總傳輸量與站的大小幾乎脫鉤** — 再加 10 倍文章，單次搜尋下載量不會跟著放大 10 倍。

它讀的是 rendered HTML 而不是 markdown source。這意味著 Pagefind 跟 Hugo（或任何 framework）完全解耦 — 換 Jekyll、Zola、Next.js static export 都能直接用。

## 整合步驟

四個接口：

### 1. Build pipeline

```bash
hugo --minify
npx -y pagefind --site public
```

兩步，沒有中間檔。Pagefind 自己決定要索引哪些 HTML（預設全部），把結果寫到 `public/pagefind/`。

### 2. 搜尋頁路由

`content/search.md` 設 `layout: search` + `sitemap.disable: true`。

```yaml
---
title: "搜尋"
layout: search
sitemap:
  disable: true
---
```

### 3. UI 掛載

`layouts/_default/search.html`：

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

外層的 `data-pagefind-ignore` 讓搜尋頁自己不被索引（避免搜尋結果出現「搜尋」這一頁）。

baseURL 帶 subpath（如 `/blog/`）時，用 Hugo 的 `relURL` 讓 Pagefind UI 自動推斷 chunk 位置。

### 4. CI workflow

GitHub Actions 在 Hugo build 後加一步：

```yaml
- name: Build Pagefind search index
  run: npx -y pagefind --site public
```

ubuntu-latest runner 自帶 node，`npx -y` 會 cache binary，首次多花約 5 秒下載。

## 優點

**索引按需載入。** 單次搜尋的 client 傳輸量與站大小脫鉤，站長到幾千頁仍然輕。這是 Pagefind 最有辨識度的特徵。

**純靜態、零外部依賴。** 產物是一組檔案，丟 GitHub Pages 即可。不需要 API key、不需要外部服務同步、不需要後端。

**Framework 無關。** 爬 rendered HTML 的選擇讓它能搭配任何靜態 framework。換 framework 時不用重寫搜尋整合。

**Drop-in UI 上線快。** 官方 `PagefindUI` component 含搜尋框、結果列表、filter、snippet highlighting、無障礙屬性，不寫任何 UI 程式碼就可以用。

**Filter 是內建一等公民。** 在 HTML 上標 `data-pagefind-filter="type:card"`，UI 會自動出現對應的 filter checkbox。

**無障礙支援到位。** Component UI（1.5.0+）內建 keyboard navigation、ARIA label、screen reader 相容的結果公告。

## 需要知道的事

**zh-tw 走 character n-gram。** Pagefind 對非空白分詞的語言採 n-gram：「負載平衡」能命中「負載平衡器」、「負載平衡器測試」。啟動時會印一行 stemming note，那是針對屈折變化語言的提示，對中文不構成限制。少數情境下（跨詞邊界的字元組合）會誤命中，在名詞為主的技術站影響極小。

**索引來自 rendered HTML。** 要被搜到的內容必須 render 到 HTML 上。frontmatter 的 description 要靠 theme 輸出到 `<meta>` 或可見文字才會進索引 — 這個 blog 天然滿足（render hook 用 description 做 tooltip、theme 寫到 meta tag）。

**Default UI 的樣式有固定風格。** 要與 site theme 完全融合，改 CSS variables 覆寫（官方 docs 列出可覆寫的 variable 清單），或改用 Pagefind JS API 自己組 UI（可以完全客製，但要寫更多）。

**Build 多一步。** CI 與本地要記得跑 `npx pagefind`。這個 blog 用 Makefile 的 `make site` 封裝 `hugo + pagefind` 兩步，避免忘記。

## 適合的場景

- 靜態站、內容會持續成長
- 部署在 GH Pages / Netlify / Cloudflare Pages 等純靜態平台
- 希望零外部依賴、完全自託管
- 內容以文字為主（blog、docs、knowledge base）
- 未來可能換 framework — 想要搜尋整合不隨之重寫
