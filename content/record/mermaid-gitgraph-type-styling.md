---
title: "Mermaid gitGraph 自訂 type 顏色配置"
date: 2026-04-28
draft: false
description: "解決 Mermaid gitGraph 中 type: HIGHLIGHT/REVERSE 無法渲染顏色的配置缺陷"
tags: ["Mermaid", "gitGraph", "視覺化", "配置", "除錯"]
---

## 問題描述

在 Hugo 部落格中使用 Mermaid gitGraph，定義自訂 commit type 時發現顏色無法正確渲染：

```mermaid
gitGraph
   commit id: "A" type: HIGHLIGHT
   commit id: "C" type: REVERSE
```

期望：HIGHLIGHT 顯示綠色、REVERSE 顯示紅色  
實際：所有 commit 都是預設灰色，type 標記無效

<!--more-->

## 根本原因

Mermaid 初始化配置中缺少 **gitGraph 特定的顏色變數定義**。

在 `layouts/partials/custom_head.html` 的 `mermaid.initialize()` 中：

```javascript
themeVariables: {
  primaryColor: '#2d3748',      // 通用顏色
  secondaryColor: '#e2e8f0',    // 通用顏色
  // ❌ 缺少 gitGraph 專用顏色定義
}
```

Mermaid 無法找到對應的顏色變數，所以自訂 type 無法正確着色。

## 解決方案

在兩個層面加入配置：

### 1. JavaScript 初始化層（themeVariables）

```javascript
mermaid.initialize({
  // ... 其他配置 ...
  themeVariables: {
    // ... 既有配置 ...
    
    // gitGraph 顏色配置
    git0: '#90ee90',    // HIGHLIGHT - 綠色
    git1: '#ffb6c6',    // REVERSE - 紅色
    git2: '#4a5568'     // 其他 - 灰色
  }
});
```

### 2. CSS 樣式層（直接選擇器）

由於 JavaScript 變數支援可能不完整，補充 CSS 選擇器規則：

```css
/* gitGraph commit type 顏色 */
.mermaid svg [id$="_HIGHLIGHT"] circle {
  fill: #90ee90;
  stroke: #2d7a2d;
}

.mermaid svg [id$="_REVERSE"] circle {
  fill: #ffb6c6;
  stroke: #d32f2f;
}
```

Mermaid 生成的 SVG 會為每個 commit 創建一個帶 `id` 的元素，格式為 `commit_<TYPENAME>`。CSS 選擇器透過 `[id$="_TYPENAME"]` 精確匹配並着色。

## 驗證方法

修改後在本地預覽 gitGraph 圖表，確認：

- ✅ HIGHLIGHT type 的 commit 顯示綠色
- ✅ REVERSE type 的 commit 顯示紅色
- ✅ 無 type 的 commit 保持預設顏色

## 應用場景

適用於任何需要視覺區分 commit 類型的流程圖：

- 功能分支 vs 修補分支
- 待合併 vs 已合併
- 重要里程碑 vs 日常提交

---

**相關記錄**：本缺陷在檢視部落格文章時發現，當時用於區分 git rebase 操作中的「目標 commit」和「變更來源」。
