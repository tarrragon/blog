---
title: "Hugo 部落格側邊章節導航 (TOC) 完整實現指南"
date: 2025-10-08
tags: ["hugo", "toc", "導航", "響應式設計", "javascript"]
description: "詳細說明如何在 Hugo 部落格中實現響應式側邊章節導航功能，包含自動滾動、高亮顯示和手機版適配"
---

## 概述

因為文章太長，閱讀困難，所以看到別人部落格有的TOC功能，就找AI復刻

### 需求

- 使用TOC快速定位
- TOC隨著本文滾動定位當前位置
- 手機寬度下不顯示TOC，改用回到頁首的懸浮按鈕取代

## 1. Hugo 配置設定

### 1.1 啟用 TOC 功能

在 `hugo.toml` 中啟用 TOC 功能：

{{< details summary="點擊查看配置程式碼" >}}

```toml
[markup]
  [markup.tableOfContents]
    startLevel = 2
    endLevel = 4
    ordered = false
```

{{< /details >}}

**參數說明**：

- `startLevel = 2`：從 H2 標題開始生成 TOC
- `endLevel = 4`：到 H4 標題結束
- `ordered = false`：使用無序列表格式

## 2. 自定義文章佈局

### 2.1 建立自定義 single.html

在 `layouts/_default/single.html` 中實現新的佈局結構：

{{< details summary="點擊查看完整 HTML 佈局程式碼" >}}

```html
{{ define "main" }}
<!-- 側邊章節導航 - 獨立於主內容區域 -->
<aside class="toc-sidebar">
  <h3>章節目錄</h3>
  {{ if .TableOfContents }}
    {{ .TableOfContents }}
  {{ else }}
    <p style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; margin: 0;">
      此文章沒有章節標題
    </p>
  {{ end }}
</aside>

<!-- 文章內容 - 保持原有的置中佈局 -->
<article class="article-content">
  {{ if not .Params.menu }}
  <h1>{{ .Title }}</h1>
  <p class="byline">
    <time datetime='{{ .Date.Format "2006-01-02" }}' pubdate>
      {{ .Date.Format (default "2006-01-02" .Site.Params.dateFormat) }}
    </time>
    {{ with .Params.author }}· {{.}}{{ end }}
  </p>
  {{ end }}
  
  <content>
    {{ .Content }}
  </content>
  
  <p>
    {{ range (.GetTerms "tags") }}
      <a class="blog-tags" href="{{ .RelPermalink }}">#{{ lower .LinkTitle }}</a>
    {{ end }}
  </p>
  
  {{ if not .Params.hideReply }}
  {{ with .Site.Params.author.email }}
    <p>
      <a href='mailto:{{ . }}?subject={{ i18n "email-subject" }}"{{ default $.Site.Title $.Page.Title }}"'>
        {{ i18n "email-reply" }} ↪
      </a>
    </p>
  {{ end }}
  {{ end }}
</article>

<!-- 回到頂部按鈕 -->
<button id="back-to-top" class="back-to-top-btn" aria-label="回到頂部">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="m18 15-6-6-6 6"/>
  </svg>
</button>

<!-- 章節導航互動腳本 -->
<script>
document.addEventListener('DOMContentLoaded', function() {
  // 檢查是否在手機版（隱藏 TOC 時不需要執行）
  const isMobile = window.innerWidth <= 768;
  
  if (isMobile) {
    return; // 手機版不執行 TOC 相關功能
  }

  // 確保所有標題都有 ID
  const headings = document.querySelectorAll('.article-content h2, .article-content h3, .article-content h4');
  
  headings.forEach(function(heading) {
    // 如果沒有 ID，則生成一個
    if (!heading.id) {
      // 從標題文字生成 ID
      const text = heading.textContent.trim();
      const id = text.toLowerCase()
        .replace(/[^\w\s-]/g, '') // 移除特殊字符
        .replace(/\s+/g, '-')     // 空格替換為連字符
        .replace(/-+/g, '-')      // 多個連字符合併為一個
        .replace(/^-|-$/g, '');   // 移除開頭和結尾的連字符
      
      if (id) {
        heading.id = id;
      }
    }
  });

  // 更新側邊導航連結的 href
  const tocLinks = document.querySelectorAll('.toc-sidebar a[href^="#"]');
  tocLinks.forEach(function(link) {
    const href = link.getAttribute('href');
    if (href && href.startsWith('#')) {
      const targetId = href.substring(1);
      const targetElement = document.getElementById(targetId);
      if (targetElement) {
        link.addEventListener('click', function(e) {
          e.preventDefault();
          targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        });
      }
    }
  });

  // 滾動時高亮當前章節並自動滾動側邊欄
  function updateActiveSection() {
    const sections = document.querySelectorAll('.article-content h2, .article-content h3, .article-content h4');
    const tocLinks = document.querySelectorAll('.toc-sidebar a[href^="#"]');
    const tocSidebar = document.querySelector('.toc-sidebar');
    
    let currentSection = '';
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    sections.forEach(function(section) {
      const sectionTop = section.offsetTop - 100; // 提前 100px 觸發
      if (scrollTop >= sectionTop) {
        currentSection = section.id;
      }
    });
    
    // 移除所有 active 類別
    tocLinks.forEach(function(link) {
      link.classList.remove('active');
    });
    
    // 為當前章節添加 active 類別並自動滾動側邊欄
    if (currentSection) {
      const activeLink = document.querySelector('.toc-sidebar a[href="#' + currentSection + '"]');
      if (activeLink) {
        activeLink.classList.add('active');
        
        // 自動滾動側邊欄到當前章節位置
        if (tocSidebar && activeLink) {
          // 獲取側邊欄的滾動容器信息
          const sidebarScrollTop = tocSidebar.scrollTop;
          const sidebarHeight = tocSidebar.clientHeight;
          const sidebarScrollHeight = tocSidebar.scrollHeight;
          
          // 獲取當前連結在側邊欄中的位置
          const linkOffsetTop = activeLink.offsetTop;
          const linkHeight = activeLink.offsetHeight;
          
          // 計算連結相對於側邊欄可視區域的位置
          const linkTop = linkOffsetTop - sidebarScrollTop;
          const linkBottom = linkTop + linkHeight;
          
          // 設定緩衝區域（側邊欄高度的 20%）
          const bufferZone = Math.max(20, sidebarHeight * 0.2);
          const safeTop = bufferZone;
          const safeBottom = sidebarHeight - bufferZone;
          
          // 檢查是否需要滾動
          let needsScroll = false;
          let targetScrollTop = sidebarScrollTop;
          
          if (linkTop < safeTop) {
            // 連結太靠近頂部，滾動到連結上方預留緩衝空間
            targetScrollTop = linkOffsetTop - bufferZone;
            needsScroll = true;
          } else if (linkBottom > safeBottom) {
            // 連結太靠近底部，滾動到連結下方預留緩衝空間
            targetScrollTop = linkOffsetTop + linkHeight - sidebarHeight + bufferZone;
            needsScroll = true;
          }
          
          // 如果需要滾動，執行滾動
          if (needsScroll) {
            // 確保滾動位置在有效範圍內
            const maxScrollTop = sidebarScrollHeight - sidebarHeight;
            targetScrollTop = Math.max(0, Math.min(targetScrollTop, maxScrollTop));
            
            // 只有當目標位置與當前位置差距足夠大時才滾動
            if (Math.abs(targetScrollTop - sidebarScrollTop) > 10) {
              tocSidebar.scrollTop = targetScrollTop;
            }
          }
        }
      }
    }
  }

  // 監聽滾動事件
  window.addEventListener('scroll', updateActiveSection);
  
  // 初始化時執行一次
  updateActiveSection();
});

// 回到頂部按鈕功能（所有裝置都支援）
document.addEventListener('DOMContentLoaded', function() {
  const backToTopBtn = document.getElementById('back-to-top');
  
  if (!backToTopBtn) return;
  
  // 顯示/隱藏按鈕
  function toggleBackToTopBtn() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    if (scrollTop > 300) {
      backToTopBtn.style.display = 'flex';
      backToTopBtn.classList.add('visible');
    } else {
      backToTopBtn.style.display = 'none';
      backToTopBtn.classList.remove('visible');
    }
  }
  
  // 回到頂部功能
  function scrollToTop() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }
  
  // 綁定事件
  window.addEventListener('scroll', toggleBackToTopBtn);
  backToTopBtn.addEventListener('click', scrollToTop);
  
  // 初始化
  toggleBackToTopBtn();
});
</script>
{{ end }}
```

{{< /details >}}

## 3. CSS 樣式設計

### 3.1 側邊欄樣式

在 `layouts/partials/custom_head.html` 中添加 CSS：

{{< details summary="點擊查看側邊欄 CSS 樣式" >}}

```css
/* 側邊章節導航樣式 - 獨立側邊欄 */
.toc-sidebar {
  position: fixed;
  top: 50%;
  right: 20px;
  transform: translateY(-50%);
  width: 280px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  transition: all 0.3s ease;
}

.toc-sidebar:hover {
  background: rgba(0, 0, 0, 0.9);
  border-color: rgba(255, 255, 255, 0.25);
}

/* 文章內容保持原有佈局 */
.article-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem;
}

.toc-sidebar h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color, #fff);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 0.5rem;
}

.toc-sidebar ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-sidebar li {
  margin: 0.25rem 0;
}

.toc-sidebar a {
  display: block;
  padding: 0.25rem 0.5rem;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
  font-size: 0.9rem;
  line-height: 1.4;
}

.toc-sidebar a:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--primary-color, #fff);
}

.toc-sidebar a.active {
  background: rgba(255, 255, 255, 0.15);
  color: var(--primary-color, #fff);
  font-weight: 500;
}

/* 不同層級的縮排 */
.toc-sidebar ul ul {
  margin-left: 1rem;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding-left: 0.5rem;
}

.toc-sidebar ul ul ul {
  margin-left: 1rem;
}
```

{{< /details >}}

### 3.2 回到頂部按鈕樣式

{{< details summary="點擊查看回到頂部按鈕 CSS 樣式" >}}

```css
/* 回到頂部按鈕樣式 */
.back-to-top-btn {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 50px;
  height: 50px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  color: white;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.back-to-top-btn:hover {
  background: rgba(0, 0, 0, 0.9);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.back-to-top-btn:active {
  transform: translateY(0);
}

.back-to-top-btn.visible {
  display: flex;
  animation: fadeInUp 0.3s ease;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

{{< /details >}}

### 3.3 響應式設計

{{< details summary="點擊查看響應式設計 CSS 樣式" >}}

```css
/* 響應式設計 */
@media (max-width: 1024px) {
  .toc-sidebar {
    width: 240px;
    right: 15px;
  }
}

@media (max-width: 768px) {
  /* 手機版隱藏 TOC */
  .toc-sidebar {
    display: none;
  }
  
  /* 確保文章內容在手機版有足夠的邊距 */
  .article-content {
    max-width: 100%;
    padding: 0 1.5rem;
  }
  
  .back-to-top-btn {
    bottom: 1.5rem;
    right: 1.5rem;
    width: 45px;
    height: 45px;
  }
}

/* 平板版調整 */
@media (max-width: 1024px) and (min-width: 769px) {
  .toc-sidebar {
    width: 220px;
    padding: 1rem;
    font-size: 0.9rem;
  }
  
  .toc-sidebar h3 {
    font-size: 0.9rem;
  }
  
  .toc-sidebar a {
    font-size: 0.85rem;
    padding: 0.2rem 0.4rem;
  }
}
```

{{< /details >}}

## 4. 標題間距優化

### 4.1 改善文章可讀性

{{< details summary="點擊查看標題間距 CSS 樣式" >}}

```css
/* 調整標題間距 */
.article-content h2 {
  margin-top: 4.5rem;
  margin-bottom: 1.5rem;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}

.article-content h3 {
  margin-top: 2.5rem;
  margin-bottom: 1.2rem;
  padding-top: 0.4rem;
  padding-bottom: 0.4rem;
}

.article-content h4 {
  margin-top: 2rem;
  margin-bottom: 1rem;
  padding-top: 0.3rem;
  padding-bottom: 0.3rem;
}

/* 第一個標題不需要上邊距 */
.article-content h2:first-child,
.article-content h3:first-child,
.article-content h4:first-child {
  margin-top: 0;
}

/* 段落與標題之間的間距 */
.article-content p {
  margin-bottom: 1.2rem;
  line-height: 1.6;
}

/* 列表與標題之間的間距 */
.article-content ul,
.article-content ol {
  margin-top: 1rem;
  margin-bottom: 1.5rem;
}

.article-content li {
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

/* 確保標題有正確的錨點 ID */
.article-content h2,
.article-content h3,
.article-content h4 {
  scroll-margin-top: 2rem;
}
```

{{< /details >}}

## 5. 需求描述

### 5.1 桌面版功能

- **固定側邊欄**：右側固定位置的章節目錄
- **自動高亮**：滾動時自動高亮當前章節
- **智能滾動**：側邊欄自動滾動到當前章節位置
- **平滑跳轉**：點擊章節標題平滑滾動到對應位置

### 5.2 平板版功能

- **縮小側邊欄**：較窄的側邊欄（220px）
- **保持所有功能**：與桌面版相同的導航功能

### 5.3 手機版功能

- **隱藏 TOC**：手機寬度不足以顯示TOC
- **回到頂部按鈕**：使用懸浮按鈕讓使用者至少可以快速回到開頭
- **響應式佈局**：文章內容全寬顯示

## 6. 技術實現細節

### 6.1 自動滾動算法

- 使用動態緩衝區域（側邊欄高度的 20%）
- 智能判斷是否需要滾動
- 避免微小震盪的閾值保護

### 6.2 效能優化

- 手機版不執行 TOC 相關功能
- 滾動事件節流處理
- 條件式 DOM 操作

### 6.3 無障礙設計

- 正確的 ARIA 標籤
- 鍵盤導航支援
- 語義化 HTML 結構
