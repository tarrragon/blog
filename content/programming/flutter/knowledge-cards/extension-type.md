---
title: "Extension Type"
tags: ["Extension Type", "擴展型別"]
date: 2026-07-10
description: "Dart 3 的零成本包裝型別——runtime 不存在額外物件、只在編譯期提供型別安全。用在 value object 的語意封閉需要零 overhead 時。"
weight: 3
aliases: ["/flutter/knowledge-cards/extension-type/"]
---

Extension type 是 Dart 3 引入的語言特性：在編譯期把一個型別包裝成另一個名字、限縮可用的 API、而 runtime 不存在額外物件（零成本抽象）。它跟 class 的差異在「沒有 runtime 開銷、但也沒有 runtime 的型別檢查——`is` 跟 `as` 看到的是底層型別」。同樣是「限縮型別可用介面」的目標，[freezed](/programming/flutter/knowledge-cards/freezed/) 生成的 class 走 runtime 路徑、extension type 走編譯期路徑，兩者是互斥的實作選擇。

## 跟其他概念的關係

Extension type 是實作 [value object](/software-design/ddd/knowledge-cards/value-object/) 語意封閉的一種載體。金額用 extension type 包 Decimal：開放的運算限於領域有意義的集合（加減、乘數量、乘倍率），差集裡的誤用（金額乘金額）在編譯期就走不通。跟用 class 包裝的差異：class 有 runtime 身份（`is Money` 為 true）但有 overhead；extension type 零 overhead 但 runtime 是透明的。這條分野也決定了誰適合搭 [copyWith](/programming/flutter/knowledge-cards/copywith/)——extension type 沒有 runtime 物件可覆寫欄位，逐欄位覆寫語意只在 class 路徑上成立。

## 判斷條件與後果

Extension type 宣告時就決定它跟底層型別的關係，兩種選擇的代價不同。宣告成底層型別的 subtype 時，值可以隱式 upcast 回底層型別，銜接既有的 API 很方便，代價是封裝邊界弱：任何接受底層型別的函式都收得下它，限縮過的 API 在那裡被繞過。宣告成獨立型別時，只有顯式拆封才拿得到底層值，封裝邊界完整，代價是每個需要底層型別的銜接點都多一次拆封。這個決定在設計時做，原因是之後改的話，所有銜接點的寫法都要跟著改，Migration 案例見 [Money 三段遷移](/work-log/dart_money_extension_type_migration/)。獨立型別的顯式拆封是離開領域型別的唯一出口，取 `toDecimal()` 這類寫出目標型別的名字時，讀程式的人看得出值在這裡離開了領域型別，見 [建構路徑設計](/software-design/ddd/construction-path-design/)。
