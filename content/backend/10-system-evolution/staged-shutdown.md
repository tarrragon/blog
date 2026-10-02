---
title: "10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期"
slug: "staged-shutdown"
date: 2026-10-02
description: "服務結束時把一次全部關閉拆成幾個階段：停止新建、唯讀、靜態封存與關閉各保留什麼、對哪一類持有者有效、維運成本降到哪裡；依使用紀錄決定保留範圍；推動客戶遷移的手段；以及公告期長度、通知管道與補償的安排"
weight: 7
tags: ["backend", "evolution", "sunset", "service-termination"]
---

服務結束（英文常稱 sunset 或 decommissioning）時，從「完整運作」到「完全關閉」之間可以安排幾個階段；本篇整理這些階段，以及依使用紀錄決定保留範圍、推動遷移的手段、公告期與補償。持有者的三類（直接客戶、間接使用者、第三方持有者）見 [10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/)；服務仍在、只淘汰一個 API 版本時的階段安排見 [11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)。

## 退場階段：停止新建、唯讀、靜態封存與關閉

Google 在 2015 年 3 月宣布關閉程式碼託管服務 Google Code 時，公告列出三個日期（[Google Open Source Blog, 2015](https://opensource.googleblog.com/2015/03/farewell-to-google-code.html)）：當天停止建立新專案；2015 年 8 月 24 日起網站變成唯讀，「You can still checkout/view project source, issues, and wikis」；2016 年 1 月 25 日關閉託管服務，改提供原始碼、issue 與 wiki 的封存檔下載，承諾提供到 2016 年底。Microsoft 在 2017 年 3 月宣布關閉 CodePlex 時走了同樣的順序：當天停止建立新專案，10 月唯讀，12 月 15 日改成唯讀的輕量封存（[Microsoft, 2017](https://devblogs.microsoft.com/bharry/shutting-down-codeplex/)）。

這兩個案例共用的順序可以一般化成下列階段，每一個階段比前一個保留的少、成本也低，也讓還能自己行動的持有者在下一階段開始前先離開：

| 階段              | 保留什麼                                           | 停掉什麼                   | 對持有者的效果                                 | 維運成本                                                             |
| ----------------- | -------------------------------------------------- | -------------------------- | ---------------------------------------------- | -------------------------------------------------------------------- |
| 停止新建          | 既有的一切照常運作                                 | 新帳號、新資源、新引用     | 讓外部引用的數量不再增加                       | 和正常營運相近                                                       |
| 唯讀（read-only） | 既有內容可讀取、可匯出，外部引用繼續回應           | 所有寫入                   | 直接客戶有時間匯出；第三方持有者的引用照常運作 | 降低：不必處理寫入；支援範圍縮到匯出相關，既有內容的濫用回報仍要處理 |
| 靜態封存          | 既有內容轉成靜態檔，外部引用由靜態檔或轉址規則回應 | 應用程式、資料庫、帳號系統 | 第三方持有者的引用改由靜態檔或轉址回應         | 網域與 TLS 憑證的續期、靜態檔的儲存與流量，加上下架單一引用的管道    |
| 關閉              | 只剩網域本身，續約但不回應                         | 全部                       | 引用失效，但不會易手                           | 只剩網域續約                                                         |

靜態封存保得住的是只需讀取、不需認證、回應不隨請求內容變化的引用：網址的轉址、被嵌入的固定版本腳本、套件的檔案都屬於這一類；需要寫入或認證的端點，以及依請求動態產生回應的服務，到這一階段就失效，要延續它們得靠 [10.8 移交：資料匯出、開源與交給社群或封存機構](/backend/10-system-evolution/handover-and-archival/) 的接手。

關閉之後若不再續約或出售網域，引用會從失效變成易手（網域換了主人，引用回應的是新主人的內容），各種去向的比較見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈網域在服務結束後的去向：續約並回應、續約不回應、到期、出售〉。

停止新建這一階段本身省不下成本，但它是後面每一階段的前提：外部引用還在增加時，任何保留範圍的估算都會過時。API 版本淘汰也是先停止新的使用、再處理既有使用者，見 [11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/) 的〈Deprecation 的執行工具箱〉。

**靜態封存**是讓第三方持有者的引用繼續運作的最低成本做法。短網址服務把對照表匯出成靜態的轉址規則，放在物件儲存或 CDN 上（做法見 [0.24 短網址服務的實作：短碼生成、對照表儲存、轉址快取與點擊紀錄](/backend/00-service-selection/url-shortener-implementation/) 的〈服務結束時的轉址延續〉）；程式碼託管服務把每個專案頁面輸出成靜態 HTML。CodePlex 的公告另外寫了兩件為持有舊網址的人做的事：「Where possible, we'll put in place redirects so that existing URLs work, or at least redirect you to the project's new homepage on the archive」，以及封存會沿用專案擁有者設定的「I've moved」指向，把訪客帶到專案的新家（[Microsoft, 2017](https://devblogs.microsoft.com/bharry/shutting-down-codeplex/)）。轉址與沿用「I've moved」指向，是 CodePlex 為第三方持有者做的安排：他們手上只有舊網址，轉址讓那些網址繼續有用。靜態封存期間仍要保留下架單一引用的管道：已經轉址到惡意目的地的連結，以及目的地網域到期後被別人註冊的連結，在封存之後照樣把人送過去，要能單筆改寫成說明頁或回 404。

退到靜態檔之後，應用程式的紀錄跟著消失，還量得到的是 CDN 或物件儲存的存取紀錄；關閉之後只剩自己名稱伺服器的查詢紀錄。封存後還要判斷保留範圍的話，這些紀錄要在封存前先開啟。單筆下架能不能到達已經點過連結的瀏覽器，取決於轉址回應帶的快取標頭，見 [12.8 快取設定的應用：轉址、需登入的 API 回應與個人化頁面](/backend/12-http-caching/applying-cache-headers/)。

靜態封存的成本低，但不是零：網域要續約、有人要決定它保留多久。到 2026 年 10 月，Google Code 的封存頁面仍可存取，遠超過承諾的 2016 年底；CodePlex 的公告寫過「There isn't currently any plan to have an end date for the archive」，封存網址現在卻已經轉到 Microsoft 的首頁，Microsoft 何時撤掉封存網站，沒有公告。到了靜態封存與關閉階段，團隊多半已經解散，而網域、TLS 憑證、雲端帳單與註冊商帳號都還有到期日；每一項都要在解散前寫明保管人與付款來源，否則它們會像 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 裡那些過期的信箱網域一樣，在沒人注意時到期。

## 依使用紀錄決定保留範圍

不是每一條外部引用都要保留到同一個階段（例如全部保留到靜態封存）。有使用紀錄的服務，可以依「最近還有沒有人用」把引用分開處理。

goo.gl 的三次公告是這個做法的完整過程。2018 年 3 月 Google 宣布分階段停止建立新的短網址：2018 年 4 月起新使用者不能建立，2019 年 3 月起全面停止，並承諾既有連結繼續轉址（[Google, 2018](https://web.archive.org/web/2018040100000/https://developers.googleblog.com/2018/03/transitioning-google-url-shortener.html)）；2024 年 7 月宣布 2025 年 8 月 25 日起所有連結回 404，理由是超過 99% 的連結在宣布前一個月沒有活動，並從 2024 年 8 月起對部分連結先顯示**中間頁**（點擊短網址時先出現、告知連結即將停止運作的一頁；Google 也寫明它會打斷後續的轉址與社群平台的連結預覽，並提供一個參數讓人跳過；由程式送出的請求收到的是這一頁的 HTML 而不是轉址，告知因此到不了任何人）（[Google, 2024](https://developers.googleblog.com/en/google-url-shortener-links-will-no-longer-be-available/)）；2025 年 8 月 Google 修改了 2024 年的計畫，改為只停用「2024 年底沒有活動」的連結，其餘保留，這一批沒有活動的連結在九個月前已經改導到告知即將停用的訊息頁；修改的理由是「these links are embedded in countless documents, videos, posts and more」（[Google, 2025](https://blog.google/technology/developers/googl-link-shortening-update/)）。

這個過程裡有兩個做法可以直接沿用。一是用中間頁把通知送到第三方持有者面前：他們不在任何聯絡名單上，但只要還在用這條引用，就一定會經過它被使用的那一刻。二是依使用紀錄切出要保留的部分，讓保留的成本隨著還在用的引用數量走，而不是隨著曾經發出去的總數走。

## 推動直接客戶遷移的手段

直接客戶有能力自己遷移，而遷移的時程由他們自己排。提供者推動時程的手段有下列幾種，代價分別落在客戶的使用者、提供者自己與晚到的客戶身上：

- **分段截止日加上降級**：Parse 的遷移指南把遷移拆成三個建議日期（先搬資料、再架自己的伺服器、最後發布指向新伺服器的 app 版本），並說明資料還沒在 2016 年 4 月 28 日前搬走的 app，「a small number of database requests may fail with a 428 error code」；Parse 會優先處理已經搬完的 app 的請求（[Parse 遷移指南，Wayback 2016-12](https://web.archive.org/web/20161231233921/https://parse.com/migration)）。用真實的錯誤讓還沒動的客戶在自己的監控上看到問題，而不只是收到一封可能沒人讀的信（API 淘汰常用的 brownout 是同一種做法，見 [11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/) 的〈Deprecation 的執行工具箱〉），代價是這些客戶的使用者先承受錯誤。
- **縮減而不刪除**：Heroku 在 2022 年終止免費方案時，免費的 app 被縮到零個執行個體，也就是不再有執行中的程序，app 的程式、設定與名稱保留（[Heroku FAQ，Wayback 2022-08-25](http://web.archive.org/web/20220825195919id_/https://help.heroku.com/RSBRUH58/removal-of-heroku-free-product-plans-faq)）；現行的常見問答寫明，訂閱付費方案之後可以再擴回來（[Heroku FAQ](https://help.heroku.com/RSBRUH58/removal-of-heroku-free-product-plans-faq)）。客戶的設定與名稱都還在，回來的成本低。
- **直接刪除**：Heroku 同一次處置刪除了免費方案的資料庫；Parse 在 2017 年 1 月 30 日逐一停用 app 之後，「you will not be able to access the data browser or export any data」（[Parse, 2017](http://web.archive.org/web/2017id_/http://blog.parse.com/announcements/a-parse-shutdown-reminder/)）。兩者都沒有唯讀期，沒趕上截止日的客戶連匯出都做不到。

刪除之前留一段唯讀期，是成本最低的保險：寫入已經停了，只多付儲存與一個讀取介面的成本，換來晚到的客戶還能取回資料。

## 公告期的長度與通知管道

公告期是從宣布到關閉的時間，它要長到讓持有者完成他們要做的工作。下列案例的公告期從零到一年都有：Parse 約一年、Google Code 約十個月、CodePlex 約八個半月、Spotify Car Thing 約六個半月、Heroku 約三個月、Revolv 約十一週，Insteon 則是 2022 年 4 月伺服器停止之後才在官網貼出說明。

決定長度的是持有者要做的工作裡最慢的那一項，而不是提供者想多快結束：

- 直接客戶要搬資料、架設替代服務，時間以月計：Parse 的遷移指南從宣布起算，給搬資料約三個月、架好自己的伺服器約六個月。
- 間接使用者要等客戶發新版 app、自己更新，時間以月計。Parse 的遷移指南把「發布指向新伺服器的 app 版本」排在最後一步，建議日期是 2016 年 9 月 28 日，離 2017 年 1 月 30 日 Parse 停用 app 還有四個月，留給使用者更新。提供者看得到請求裡的 SDK 或 app 版本，舊版客戶端的流量比例降到多少，是決定公告期與降級時點的直接依據；請求要帶哪些識別才量得到，見 [11.12 API 消費者用量觀測：契約決策要的觀測維度、消費者身分的識別、欄位級用量與全量或抽樣的成本邊界](/backend/11-api-design/consumer-usage-observability/)。
- 第三方持有者收不到公告信與公告文章；送得到他們面前的是引用被使用那一刻的訊息，依引用種類不同：網址用中間頁，套件用登錄服務的棄用警告（npm 的 deprecate 會在每次下載時顯示作者寫的訊息，見 [npm unpublish 政策](https://docs.npmjs.com/policies/unpublish)），API 用回應標頭。這些訊息顯示多久，就是他們實際得到的公告期；這段期間沒有使用引用的人，得到的公告期是零。除此之外，保護他們的是靜態封存、依使用紀錄保留，以及 CDN 業者這類中介者的介入（[10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈網域的出售：polyfill.io 的經過〉）。

這條判斷標準假設提供者撐得到那一天。資金用完、公司解散或合約終止時，提供者能給的時間可能短於最慢的那一項工作，Insteon 的公告期就是零；有些工作根本沒有完成的一天，例如沒有更新管道的裝置、印在紙上的網址。這段差距只能由不靠提供者存續的做法承接：靜態封存、預先付清的網域續約、交給中立方的技術控制，以及 [10.8 移交：資料匯出、開源與交給社群或封存機構](/backend/10-system-evolution/handover-and-archival/) 的移交。這些安排的費用與負責人，要在資金還夠的時候先定下來。

通知管道要依持有者的類別分開設計：直接客戶用信件與管理介面；間接使用者要靠直接客戶轉達，提供者能做的是給直接客戶可以轉達的材料；第三方持有者只能在引用被使用的那一刻通知，也就是中間頁或回應裡的訊息。API 的使用者還可以從回應標頭機器可讀地得知退場時點，做法見 [11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/) 的 Sunset header；各類通知工具怎麼組合覆蓋不同類型的消費者，見 [Deprecation Lifecycle](/backend/knowledge-cards/deprecation-lifecycle/) 卡；那張卡依「消費者會看到哪一種通知」分類，和這裡依「提供者聯絡得到誰」分的持有者類別是兩種切法。

## 賣出去的裝置的補償

服務結束讓已經賣出去的硬體失效時，公告期之外還有補償的問題。兩個案例的時序相似：Revolv 的關閉公告最早出現在 2016 年 2 月下旬的網頁快照裡，客服說明只寫「Please contact Revolv customer support」，全額退款的文字到 4 月上旬的快照才出現（[Revolv 官網，Wayback 2016-04-05](http://web.archive.org/web/20160405215954id_/http://revolv.com/)；[Wayback 2016-04-11](http://web.archive.org/web/20160411184606id_/http://revolv.com/)）。Spotify 在 2024 年 5 月 23 日公布 Car Thing 停止支援時，支援頁沒有退款條目，「憑購買證明聯絡客服討論退款」的文字出現在 5 月 28 日到 30 日之間的快照，5 月 30 日 TechCrunch 報導了一件針對 Car Thing 的集體訴訟（[Spotify 支援頁，Wayback 2024-05-28](http://web.archive.org/web/20240528202400id_/https://support.spotify.com/us/article/car-thing-discontinued/)；[Wayback 2024-05-30](http://web.archive.org/web/20240530223649id_/https://support.spotify.com/us/article/car-thing-discontinued/)；[TechCrunch, 2024](https://techcrunch.com/2024/05/30/spotify-begins-offering-car-thing-refunds-as-it-faces-lawsuit-over-bricking-the-streaming-device/)）。兩案的退款都是公告之後才加上的；快照只能界定退款文字出現在哪兩個日期之間，退款與抗議或訴訟之間的因果，一手來源沒有寫明。

FTC 對 Revolv 的調查結論說明了補償在監理上的份量。FTC 決定不採取執法行動，考量的因素包括「the limited number of units sold; Nest's practice of providing full refunds after the Revolv system shutdown was announced」，以及透過網站、app 內通知與信件公告退款（[FTC 結案信, 2016](https://www.ftc.gov/system/files/documents/closing_letters/nid/160707nestrevolvletter.pdf)）。Revolv 的關閉日期在各份文件裡不一致，所以上面的公告期只能寫成約十一週：結案信第一頁寫 2016 年 6 月 19 日，第二頁引用官網當時寫的 5 月 15 日，官網之後又改成 5 月 22 日。

所以補償要和公告一起規劃，而不是等反應出現才加：退款的條件、截止日與申請管道寫在第一份公告裡。至於能不能讓裝置在沒有雲端時繼續運作，要在上線時決定，見 [10.5 退場能力的設計前置：端點間接層、本地運作模式與引用的命名空間](/backend/10-system-evolution/exit-ready-design/) 的〈雲端關閉後的裝置功能：本地運作模式〉。
