---
title: "Extension Type"
tags: ["Extension Type", "擴展型別"]
date: 2026-07-10
description: "Dart 3 的零成本包裝型別——runtime 不存在額外物件、只在編譯期提供型別安全。用在 value object 的語意封閉需要零 overhead 時。"
weight: 3
---

Extension type 是 Dart 3 引入的語言特性：在編譯期把一個型別包裝成另一個名字、限縮可用的 API、而 runtime 不存在額外物件（零成本抽象）。它跟 class 的差異在「沒有 runtime 開銷、但也沒有 runtime 的型別檢查——`is` 跟 `as` 看到的是底層型別」。

## 概念位置

Extension type 是實作 [value object](/ddd/knowledge-cards/value-object/) 語意封閉的一種載體。金額用 extension type 包 Decimal：開放的運算限於領域有意義的集合（加減、乘數量、乘倍率），差集裡的誤用（金額乘金額）在編譯期就走不通。跟用 class 包裝的差異：class 有 runtime 身份（`is Money` 為 true）但有 overhead；extension type 零 overhead 但 runtime 是透明的。

## 設計責任

Extension type 的 subtype 決策要在設計時做好——它是底層型別的 subtype（寬鬆：可以隱式 upcast 回底層型別）還是獨立型別（嚴格：只能顯式拆封）。前者方便、但封裝邊界弱；後者安全、但每個需要底層型別的銜接點都要顯式拆封。顯式拆封的出口要有語意明確的名字（如 `toDecimal()`），見 [建構路徑設計](/ddd/construction-path-design/)。Migration 案例見 [Money 三段遷移](/work-log/dart_money_extension_type_migration/)。
