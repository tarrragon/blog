---
title: "Registrable Domain"
date: 2026-07-31
description: "判斷兩個主機名算不算同一方、或某個跨站防護的信任邊界實際涵蓋誰時，用來定位「站」的切點在哪一層"
weight: 429
tags: ["backend", "knowledge-card", "security", "web"]
---

Registrable domain 是「一個人能向註冊機構買下來的最小單位」，也就是公共後綴再加左邊一層：`example.com` 是可註冊網域，而 `a.example.com` 與 `b.example.com` 都落在它底下。判斷哪一段是公共後綴要查一份維護中的清單（Public Suffix List），因為它不是靠數幾個點就能算出來——`example.co.uk` 與 `example.com` 的公共後綴長度不同，而 `github.io` 這類讓任何人開子網域的服務也被登記成公共後綴。它與 [same-origin policy](/backend/knowledge-cards/same-origin-policy/) 的「來源」是兩個不同的切點，落差見下一段。

## 概念位置

它的作用是界定「同一方」這個概念的範圍，而瀏覽器的各種機制對「同一方」用的切點並不一致。[Same-origin policy](/backend/knowledge-cards/same-origin-policy/) 的來源看的是協定、主機名與埠三者全等，於是 `a.example.com` 與 `b.example.com` 是兩個來源、互相讀不到回應。SameSite 屬性判定「站」時看的卻是可註冊網域，於是同樣這兩個主機在 cookie 的規則下屬於同一方、彼此的請求不算跨站。

這條落差是多數跨站防護缺口的共同成因：防護以為自己守著一個主機，實際守著整個可註冊網域底下的所有主機。判讀見 [7.36 憑證在請求中怎麼帶](/backend/07-security-data-protection/credential-transport-in-request/) 與 [cross-site request forgery](/backend/knowledge-cards/cross-site-request-forgery/)。

## 可觀察訊號與例子

要拿這個概念做判讀的訊號是組織底下存在由不同團隊或外部廠商維護的主機——活動頁、文件站、狀態頁、外包的行銷網站。它們與主站共用可註冊網域時，就共用 SameSite 判定下的信任邊界，而維護它們的人多半不知道自己在那個邊界之內。

另一個訊號是把服務開在共享的第三方網域上（各種靜態網站託管、應用平台的預設網域）。那一類網域若沒有被登記進公共後綴清單，同一個平台上的其他使用者就與自己共用可註冊網域；登記進去之後才彼此隔開。判斷自己落在哪一種，查那份清單而不是憑直覺。

## 設計責任

信任邊界要按實際的切點畫，而不是按「這是我們公司的主機」畫。把子網域交給外部維護時，主站的防護要包含一層不依賴可註冊網域判定的檢查——來源檢查或請求標頭層的判定，見 [7.36](/backend/07-security-data-protection/credential-transport-in-request/) 的三層防護。

Cookie 的作用域設定要把這個範圍當成上限來看。把 cookie 設在可註冊網域這一層時，它會被送往底下所有主機；設在具體主機上則不會。這個決定與 [session](/backend/knowledge-cards/session-invalidation/) 的撤銷範圍互相牽動，在多子網域的架構上要一起定。

需要判斷某個主機名的可註冊網域時用現成的函式庫，不要自己數點。清單持續變動，自寫的規則會在遇到多層公共後綴或新登記的平台網域時判錯，而判錯的方向是把不同方當成同一方。
