---
title: "Hugo Shortcode 實現可折疊區塊"
date: 2025-10-09
tags: ["hugo", "shortcode", "markdown"]
description: "說明如何使用 Hugo Shortcode 實現可折疊內容區塊"
---

## 問題背景

在撰寫技術文章時，我們會在文章中加入程式碼範例。但是 blog 的目標是分享我處理問題的思路，而不是提供解決方案，所以我希望預設把程式碼隱藏。

### 最初的解決方案

使用 HTML5 的 `<details>` 和 `<summary>` 標籤：

```html
<details>
<summary>📝 點擊查看程式碼</summary>

\```javascript
console.log('Hello World');
\```

</details>
```

這個方案雖然功能正常，但會觸發 **MD033 Markdown Linter 警告**：

```text
MD033/no-inline-html: Inline HTML [Element: details]
```

## 為什麼會有這個警告？

### Markdown 設計哲學

Markdown 的設計理念是：

- 保持純文字的可讀性
- 避免直接使用 HTML 標籤
- 使用語義化的標記語法

### MD033 規則的目的

MD033 規則旨在：

1. **維持 Markdown 的純淨性**：避免 HTML 與 Markdown 混用
2. **提升可維護性**：純 Markdown 更容易閱讀和維護
3. **確保相容性**：不同的 Markdown 渲染器對 HTML 的支援程度不同

## Hugo Shortcode 解決方案

### 什麼是 Shortcode？

Hugo Shortcode 是 Hugo 靜態網站生成器提供的一個強大功能，允許你：

- 在 Markdown 中使用自定義的簡短標記
- 封裝複雜的 HTML 結構
- 保持 Markdown 文件的整潔

### 優勢分析

| 特性            | HTML 標籤     | Hugo Shortcode |
| --------------- | ------------- | -------------- |
| Markdown Linter | ❌ 觸發警告   | ✅ 無警告      |
| 可維護性        | ❌ 分散在各處 | ✅ 集中管理    |
| 可讀性          | ⚠️ 較差        | ✅ 優秀        |
| 彈性            | ⚠️ 固定結構    | ✅ 可自定義    |
| Hugo 最佳實踐   | ❌ 不推薦     | ✅ 官方推薦    |

## 實現步驟

### 步驟 1：創建 Shortcode 檔案

在專案根目錄創建 `layouts/shortcodes/details.html`：

{{% details summary="📝 點擊查看 Shortcode 程式碼" %}}

```html
{{/* 
  Details shortcode - 用於創建可折疊的內容區塊
  
  使用方式:
  {{< details summary="點擊展開" >}}
  內容...
  {{% /details %}}
  
  參數:
  - summary: 摘要文字（可選，預設為 "點擊展開"）
*/}}
<details>
  <summary>{{ .Get "summary" | default "點擊展開" }}</summary>
  {{ .Inner | markdownify }}
</details>
```

{{% /details %}}

**程式碼說明**：

1. **註解區塊**：`{{/* ... */}}` 用於說明 shortcode 的用途和使用方式
2. **參數獲取**：`.Get "summary"` 獲取 summary 參數
3. **預設值**：`default "點擊展開"` 提供預設文字
4. **內容處理**：`.Inner` 獲取標籤內的內容
5. **Markdown 渲染**：`markdownify` 將內容中的 Markdown 語法轉換為 HTML

### 步驟 2：在 Markdown 中使用

**舊方式（會觸發 MD033）：**

```markdown
<details>
<summary>📝 點擊查看程式碼</summary>

\```toml
[markup]
  [markup.tableOfContents]
    startLevel = 2
\```

</details>
```

**新方式（符合 Markdown 規範）：**

```markdown
{{< details summary="📝 點擊查看程式碼" >}}

\```toml
[markup]
  [markup.tableOfContents]
    startLevel = 2
\```

{{% /details %}}
```

### 步驟 3：添加 CSS 樣式

在 `layouts/partials/custom_head.html` 中添加樣式：

{{% details summary="📝 點擊查看 CSS 樣式程式碼" %}}

```css
/* 可折疊程式碼區塊樣式 */
details {
  margin: 1.5rem 0;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

details:hover {
  background: rgba(0, 0, 0, 0.08);
  border-color: rgba(0, 0, 0, 0.15);
}

details[open] {
  background: rgba(0, 0, 0, 0.03);
  border-color: rgba(0, 0, 0, 0.2);
}

summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
  padding: 0.5rem;
  margin: -1rem -1rem 0 -1rem;
  border-radius: 8px 8px 0 0;
  background: rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
  user-select: none;
  list-style: none;
}

summary::-webkit-details-marker {
  display: none;
}

summary::before {
  content: '▶';
  display: inline-block;
  margin-right: 0.5rem;
  transition: transform 0.3s ease;
  font-size: 0.8rem;
}

details[open] summary::before {
  transform: rotate(90deg);
}

summary:hover {
  background: rgba(0, 0, 0, 0.1);
}

details[open] summary {
  margin-bottom: 1rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px 8px 0 0;
}

/* 確保 details 內的程式碼區塊樣式正常 */
details pre {
  margin: 1rem 0 0 0;
}

details > *:not(summary) {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 響應式設計 */
@media (max-width: 768px) {
  details {
    margin: 1rem 0;
    padding: 0.8rem;
  }

  summary {
    font-size: 0.9rem;
    padding: 0.4rem;
    margin: -0.8rem -0.8rem 0 -0.8rem;
  }
}
```

{{% /details %}}

## 進階功能

### 自定義參數

你可以擴展 shortcode 支援更多參數：

{{% details summary="📝 點擊查看進階 Shortcode 程式碼" %}}

```html
{{/*
  進階 Details shortcode
  
  參數:
  - summary: 摘要文字
  - open: 是否預設展開（true/false）
  - class: 自定義 CSS 類別
*/}}
<details {{ if .Get "open" }}open{{ end }} {{ with .Get "class" }}class="{{ . }}"{{ end }}>
  <summary>{{ .Get "summary" | default "點擊展開" }}</summary>
  {{ .Inner | markdownify }}
</details>
```

{{% /details %}}

**使用範例**：

```markdown
{{< details summary="重要提示" open="true" class="warning" >}}
這個區塊預設是展開的
{{% /details %}}
```

### 巢狀使用

Shortcode 支援巢狀使用：

```markdown
{{< details summary="外層標題" >}}

這是外層內容

{{< details summary="內層標題" >}}
這是內層內容
{{% /details %}}

{{% /details %}}
```

## 遷移指南

### 批量替換

如果你已經有很多使用 HTML 標籤的文章，可以使用以下步驟批量替換：

#### 步驟 1：備份檔案

```bash
git commit -am "備份：準備遷移到 shortcode"
```

#### 步驟 2：使用 sed 批量替換（macOS）

{{% details summary="📝 點擊查看批量替換腳本" %}}

```bash
# 替換開始標籤
find content -name "*.md" -type f -exec sed -i '' \
  's/<details>$/{{&lt; details summary="📝 點擊查看程式碼" &gt;}}/g' {} +

# 替換帶 summary 的開始標籤
find content -name "*.md" -type f -exec sed -i '' \
  's/<details>.*<summary>\(.*\)<\/summary>/{{&lt; details summary="\1" &gt;}}/g' {} +

# 替換結束標籤
find content -name "*.md" -type f -exec sed -i '' \
  's/<\/details>/{{&lt; \/details &gt;}}/g' {} +
```

{{% /details %}}

#### 步驟 3：驗證結果

```bash
# 檢查是否還有 HTML 標籤
grep -r "<details>" content/
grep -r "</details>" content/
```

#### 步驟 4：測試並提交

```bash
hugo server -D
# 確認無誤後提交
git add .
git commit -m "遷移到 shortcode：移除 HTML 標籤"
```

## 常見問題

### Q1: Shortcode 不生效？

**可能原因**：

1. 檔案路徑錯誤：確認檔案在 `layouts/shortcodes/` 目錄
2. 檔案名稱錯誤：檔案名稱應該是 `details.html`
3. Hugo 版本過舊：確認 Hugo 版本 >= 0.55

**解決方案**：

```bash
# 檢查 Hugo 版本
hugo version

# 重新啟動 Hugo server
hugo server -D --disableFastRender
```

### Q2: Markdown 內容沒有被渲染？

**問題**：shortcode 內的 Markdown 語法沒有被轉換為 HTML

**解決方案**：

確認使用了 `markdownify` 函數：

```html
{{ .Inner | markdownify }}
```

### Q3: 如何處理全域 gitignore 規則？

如果你的專案需要追蹤 `.claude/settings.local.json`，但被全域 gitignore 排除：

#### 方案 1：強制添加

```bash
git add -f .claude/settings.local.json
```

#### 方案 2：在專案 `.gitignore` 中覆蓋

```gitignore
# 允許追蹤 .claude/settings.local.json
!.claude/settings.local.json
```

### Q4: CSS 樣式沒有生效？

**檢查清單**：

1. ✅ CSS 是否正確載入到 `custom_head.html`
2. ✅ 瀏覽器快取是否清除（Ctrl+Shift+R 強制重新整理）
3. ✅ CSS 選擇器是否正確
4. ✅ 是否有其他 CSS 覆蓋了樣式

## 效能考量

### Shortcode vs HTML 標籤

| 項目       | HTML 標籤 | Shortcode      |
| ---------- | --------- | -------------- |
| 建置時間   | 快        | 稍慢（需處理） |
| 執行時效能 | 相同      | 相同           |
| 快取效果   | 相同      | 相同           |
| 維護成本   | 高        | 低             |
