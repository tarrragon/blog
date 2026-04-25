---
title: "CSS / JS 拆出獨立檔案"
date: 2026-04-25
weight: 25
description: "Hugo template 內 inline CSS / JS 超過 30 行就值得拆檔、走 resources pipeline。本文展開拆檔的理由、步驟、與得益。"
tags: ["report", "事後檢討", "Hugo", "Refactor", "工程方法論"]
---

## 核心原則

**Inline CSS / JS 超過 ~30 行就值得拆出獨立檔案、走 Hugo `resources.Get | minify | fingerprint` 引入。** Template 變單純、editor 對 .css/.js 有 syntax highlight、minify 自動化、cache-busting fingerprint 自動處理。

---

## 為什麼 inline 有上限

### 商業邏輯

Inline CSS / JS 在 Hugo template 內看似省事（一個檔案搞定），但隨著規模上升出現多個成本：

| 規模     | Inline 的代價                                                    |
| -------- | ---------------------------------------------------------------- |
| < 10 行  | 幾乎無 — 一目了然                                                |
| 10-30 行 | 中 — Editor 不太能 highlight、template 開始混雜                  |
| 30+ 行   | 高 — 找東西要在 template 模式間切換、minify 沒做、cache 控制困難 |

拆檔的成本是「多 1-2 個檔案」、收益是「multiple」 — 過了 30 行門檻、ROI 已正向。

### 拆檔的實際得益

| 維度                    | Inline                               | 拆檔 + Resources Pipeline |
| ----------------------- | ------------------------------------ | ------------------------- |
| Editor syntax highlight | 部分 — 看 editor 是否支援 mixed mode | 完整 — 純 .css / .js 檔   |
| Minify                  | 手動或 hugo template minify          | Hugo `minify` pipe 自動   |
| Cache-busting           | 手動加版本號                         | `fingerprint` 自動        |
| 程式碼重用              | 難 — 跟 template 綁                  | 容易 — 多 template 共用   |
| Version control diff    | 跟 template 改動混                   | 純檔案改動、清楚          |
| 測試                    | 難                                   | 可單獨測                  |

---

## 這次任務的拆檔目標

### 觀察

`layouts/_default/search.html` 現況：

| 段落                  | 行數     |
| --------------------- | -------- |
| Hugo template 與 HTML | ~30      |
| Inline `<script>`     | ~110     |
| Inline `<style>`      | ~80      |
| **總計**              | **~220** |

220 行的 single-file template、CSS / JS 各超過拆檔門檻 3-4 倍。

### 判讀

把 CSS 拆到 `assets/search.css`、JS 拆到 `assets/search.js`、template 只剩 HTML 結構與 Hugo 引入。

### 執行：拆檔步驟

#### Step 1：建立 assets 檔

```text
assets/
├── search.css      # 原本 inline <style> 內容
└── search.js       # 原本 inline <script> 內容
```

#### Step 2：template 引入

```html
{{ define "main" }}
{{- $css := resources.Get "search.css" | minify | fingerprint -}}
<link href="{{ $css.RelPermalink }}" rel="stylesheet" integrity="{{ $css.Data.Integrity }}">

<div data-pagefind-ignore class="search-shell">
  ...
</div>

{{- $js := resources.Get "search.js" | minify | fingerprint -}}
<script src="{{ $js.RelPermalink }}" integrity="{{ $js.Data.Integrity }}" defer></script>
{{ end }}
```

#### Step 3：JS 從全域 `window.PagefindUI` 改為 module 模式

如果原本 inline JS 用 `new PagefindUI(...)` 直接執行、拆檔後仍然可以這樣寫。但若想進一步，把 init 包成 function：

```js
// assets/search.js
(function () {
  function init() {
    new PagefindUI({ ... });
    // ... rest of setup
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

#### Step 4：清理 template

Template 從 220 行降到 ~30 行 — 只剩 HTML 結構。

---

## 內在屬性比較：四種引入方式

| 方式                                      | 維護成本           | Cache 控制                | 可重用性                |
| ----------------------------------------- | ------------------ | ------------------------- | ----------------------- |
| Inline `<style>` / `<script>`             | 中 — template 混雜 | 自動跟著 template         | 低 — 跟特定 template 綁 |
| 拆 .css / .js + 直接 link / script tag    | 低 — 純檔案        | 手動加版本號              | 高                      |
| Hugo resources.Get + minify               | 低                 | 內容變動觸發新 path       | 高                      |
| Hugo resources.Get + minify + fingerprint | 低                 | 內容 hash 自動 cache-bust | 高 + 安全               |

優先選 fingerprint — Hugo 自動處理快取、瀏覽器看到內容變動的 fingerprint 一定 reload。

---

## Hugo Resources Pipeline 的細節

### `resources.Get`

```go
{{ $css := resources.Get "search.css" }}
```

讀 `assets/search.css`。如果路徑下沒有、回傳 nil（要做 nil 檢查）。

### `| minify`

去除空白、註解、合併 selector — 減少傳輸大小。

### `| fingerprint`

對檔案內容做 hash、加到 URL（`search.abc123.css`）。內容變動時 fingerprint 變、瀏覽器把它當新檔案。

### `.RelPermalink` / `.Permalink`

`RelPermalink` — site root 相對路徑（`/search.abc123.css`）  
`Permalink` — 完整 URL（`https://site.com/search.abc123.css`）

通常用 `RelPermalink` 即可。

### `.Data.Integrity`

Subresource Integrity hash — 給 `integrity` attribute 用、瀏覽器驗證下載內容沒被篡改。

---

## 拆檔的判斷門檻

| Template 內含            | 建議                      |
| ------------------------ | ------------------------- |
| 0-10 行 inline CSS / JS  | 不拆 — 維護成本最低       |
| 10-30 行                 | 視情況 — 有重用性需求就拆 |
| 30+ 行                   | 拆 — 各方面收益都正向     |
| 50+ 行                   | 強烈建議拆                |
| 多個 template 共用同一段 | 立刻拆 — 重用性主導       |

當前 search.html 的 ~190 行 inline 程式碼遠超門檻、屬於「強烈建議拆」。

---

## 設計取捨：CSS / JS 引入策略

四種做法、各自機會成本不同。這個專案在 inline > 30 行時選 A（拆檔 + Hugo pipeline）當預設、其他做法在特定情境合理。

### A：拆檔 + Hugo `resources.Get | minify | fingerprint`（這個專案的預設）

- **機制**：CSS / JS 拆到 `assets/`、template 用 `resources.Get | minify | fingerprint` 引入
- **選 A 的理由**：minify 自動、cache-bust 自動、editor syntax highlight、跨 template 重用
- **適合**：規模超過 30 行、預期長期維護的客製
- **代價**：多 1-2 個檔案、template 跟 assets 分屬兩處（grep 多一步）

### B：拆檔 + 直接 `<link>` / `<script>` tag

- **機制**：拆檔到 `static/` 或 `assets/`、template 直接 link
- **跟 A 的取捨**：B 簡單、A 自動處理 minify / fingerprint；B 改檔案後 cache 可能用舊版（要手動加版本號）
- **B 比 A 好的情境**：簡單 prototype、確定不需要 cache-bust（純內部工具）

### C：保持 inline

- **機制**：CSS / JS 寫在 template 的 `<style>` / `<script>` 內
- **跟 A 的取捨**：C 一個檔案搞定、A 拆兩個；但 C 在 30+ 行時 syntax highlight 失效、難維護
- **C 比 A 好的情境**：< 10 行的小段、跟 template 邏輯緊密相關

### D：CDN 引入第三方資源

- **機制**：`<script src="https://cdn.../lib.js">`
- **成本特別高的原因**：依賴第三方可用性、跨域 CORS / SRI 處理、隱私問題（追蹤）
- **D 才合理的情境**：第三方明確支援 SRI 且 CDN 是官方建議方式（少數 vendor library）

---

## 判讀徵兆

| 訊號                                              | 拆檔動作                           |
| ------------------------------------------------- | ---------------------------------- |
| Template 內 `<style>` / `<script>` 超過 30 行     | 拆到 `assets/` 下對應 .css / .js   |
| Editor 對 inline CSS / JS 沒 highlight            | 拆檔讓 editor 套對應 mode          |
| 改 inline JS 後 cache 沒更新                      | 拆檔 + fingerprint 自動 cache-bust |
| 同樣的 CSS / JS 在多個 template 重複              | 拆出共用檔案                       |
| Inline 程式碼跟 Hugo template 邏輯混在一起難 grep | 拆檔讓 grep 範圍清楚               |

**核心原則**：Template 是 markup 的家、CSS / JS 是各自獨立檔案的家。三者混在一個檔案是過渡狀態、不是長期方案。
