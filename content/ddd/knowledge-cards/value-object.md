---
title: "Value Object"
tags: ["值物件", "Value Object"]
date: 2026-07-10
description: "判斷一個概念該用內容比對還是身份追蹤時使用。value object 的同一性由內容定義——內容相等就是同一個、替換實例對系統沒有影響。"
weight: 3
---

Value object 的同一性由內容定義：內容相等就是同一個、替換一個內容相同的實例對系統沒有任何影響。要「改」就是造一個新值換上去——不可變。跟 [entity](/ddd/knowledge-cards/entity/) 相反：entity 的同一性由身份定義。相等性定義本身可以承載業務規則：「什麼算同一個」是業務決策寫進相等性定義的例子。

## 概念位置

Value object 有兩個獨立的價值。第一個跟 entity 的判準有關——操作以內容為對象（累加、合併、比對、替換）就用 value object。第二個是語意封閉：把一個領域概念的合法運算限縮成封閉集合——差集裡的每個運算都是等著被誤用的 API。語意封閉的價值獨立於同一性判定、也獨立於容器型別的類別——[資料袋](/ddd/knowledge-cards/data-bag/)裡照樣可以放語意封閉的 value object。

## 可觀察訊號

一個領域概念以裸的通用型別跨模組流通（金額是 double、識別碼是 string）、而它的合法運算遠少於底層型別——語意封閉的價值已成立。封裝後要給原始值一個語意明確的官方出口（見 [建構路徑設計](/ddd/construction-path-design/)）。

## 設計責任

Value object 需要決定相等性定義（哪些欄位參與比對、參與本身就是業務規則）、不可變策略、以及封裝出口。枚舉是 value object 的一種——粒度判準看消費者需求、不看分類系統本身。判準的完整展開見 [entity 與 value object 的判準](/ddd/entity-vs-value-object/)。
