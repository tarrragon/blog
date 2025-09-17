---
title: "在文章中加入圖片的語法"
date: 2025-09-17
draft: false
description: "描述如何在部落格中引用圖片"
tags: ["Hugo", "Bear Cub", "AI協作心得"]
---


## 在文章中引用assets的圖片

我現在的做法是assets第一層資料夾是大分類，第二層資料夾一個文章一個資料夾，然後每個文章使用的圖片集中那個資料夾

<!--more-->

## 語法

1.使用 Hugo 的圖片處理功能

```makdown
{{< figure src="/work-log/flutter_toggle_button/ToggleButtons.png" alt="ToggleButtons 樣式" >}}
```

2.使用標準 Markdown 語法

```makdown
![ToggleButtons 樣式](/work-log/flutter_toggle_button/ToggleButtons.png)
```

3.使用 Hugo 的圖片 shortcode

```makdown
{{< figure src="/work-log/flutter_toggle_button/ToggleButtons.png" 
           alt="ToggleButtons 樣式" 
           caption="Flutter ToggleButtons 元件樣式展示"
           width="600" >}}
```

## 重要注意事項

1.圖片路徑：在 Hugo 中，assets 資料夾的內容會被處理並放在網站根目錄下，所以路徑是 /work-log/flutter_toggle_button/ToggleButtons.png

2.圖片優化：Hugo 會自動處理圖片優化，但你可以透過 shortcode 參數來控制大小和品質

3.響應式設計：使用 {{< figure >}} shortcode 可以確保圖片在不同裝置上都能正確顯示
