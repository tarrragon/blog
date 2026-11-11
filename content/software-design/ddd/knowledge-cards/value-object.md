---
title: "Value Object"
tags: ["值物件", "Value Object"]
date: 2026-07-10
description: "判斷一個概念該用內容比對還是身份追蹤時使用。value object 的同一性由內容定義——內容相等就是同一個、替換實例對系統沒有影響。"
weight: 3
aliases: ["/ddd/knowledge-cards/value-object/"]
---

Value object 的同一性由內容定義：內容相等就是同一個、替換一個內容相同的實例對系統沒有任何影響。要「改」就是造一個新值換上去——不可變。跟 [entity](/software-design/ddd/knowledge-cards/entity/) 相反：entity 的同一性由身份定義。相等性定義本身可以承載業務規則：「什麼算同一個」是業務決策寫進相等性定義的例子。

## 跟其他概念的關係

Value object 有兩個獨立的價值。第一個跟 entity 的判斷標準有關——操作以內容為對象（累加、合併、比對、替換）就用 value object。第二個是語意封閉：把一個領域概念的合法運算限縮成封閉集合——差集裡的每個運算都是等著被誤用的 API。語意封閉的價值獨立於同一性判定、也獨立於容器型別的類別——[資料袋](/software-design/ddd/knowledge-cards/data-bag/)裡照樣可以放語意封閉的 value object。

## 可觀察訊號

一個領域概念以裸的通用型別跨模組流通（金額是 double、識別碼是 string）、而它的合法運算遠少於底層型別——語意封閉的價值已成立。封裝後要給原始值一個語意明確的官方出口（見 [建構路徑設計](/software-design/ddd/construction-path-design/)）。

## 判斷條件與後果

Value object 的相等性定義、不可變策略與封裝出口，各自決定一類錯誤是否可能發生。相等性定義列出哪些欄位參與比對，參與本身就是業務規則：欄位選錯時，業務上算同一個的兩個值被判成不同（或反過來），以內容為對象的累加、合併與比對跟著出錯。不可變策略決定「改」的方式：值能就地修改時，持有同一個實例的其他物件會一起看到這次改動，原因是它們共用的是同一個實例；不可變讓「改」只能是造一個新值換上去，影響限於換上去的那一處。封裝出口決定原始值怎麼取出：封裝之後沒有語意明確的官方出口時，呼叫端為了序列化或顯示只能各自另開取值的方法，被封閉的運算又從這些方法流出去（出口的設計見 [建構路徑設計](/software-design/ddd/construction-path-design/)）。枚舉也是 value object 的一種，它的粒度依消費者需要分辨到多細而定，分類系統本身分到多細不決定它。判斷標準的完整展開見 [entity 與 value object 的判斷標準](/software-design/ddd/entity-vs-value-object/)。
