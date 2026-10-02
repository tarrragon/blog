---
title: "10.8 移交：資料匯出、開源與交給社群或封存機構"
slug: "handover-and-archival"
date: 2026-10-02
description: "服務結束時把讓外部引用繼續運作所需的資料、程式碼與網域交出去：交給直接客戶的資料匯出、開源程式碼能不能獨立運作、社群接手需要提供者事先留下什麼、封存機構的兩種取得方式（業者合作交出與外部爬取），以及交不出去的部分"
weight: 8
tags: ["backend", "evolution", "sunset", "service-termination", "open-source"]
---

服務結束時，提供者能把什麼交給誰，讓外部引用在提供者不再運作之後還能運作，是本篇的範圍；這裡的接手指服務端（伺服器、資料與網域）的接手，開源函式庫的維護權轉移是另一個主題，函式庫下架或棄置名稱的後果見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈名稱的保留與回收：套件名稱、雲端資源名稱與短碼〉。外部引用（服務發出去、存在別人手上的網址、端點、名稱與身分）的定義與持有者的分類見 [10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/)；停止新建、唯讀、靜態封存這些分階段降級的做法見 [10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期](/backend/10-system-evolution/staged-shutdown/)；移交能做到什麼程度，大半在上線時就決定了，見 [10.5 退場能力的設計前置：端點間接層、本地運作模式與引用的命名空間](/backend/10-system-evolution/exit-ready-design/)。

## 移交的對象與各自需要的資料、程式碼與權限

移交的對象有四種，每一種需要的不同：

| 對象               | 要拿到什麼                                                                                                                     | 拿到之後能做什麼                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| 直接客戶           | 自己的資料，以別人讀得懂的格式匯出                                                                                             | 搬到另一個服務或自己架設                 |
| 開源程式碼的使用者 | 服務端程式碼，以及讓它跑起來所需的全部元件                                                                                     | 自己架一份相容的服務                     |
| 接手的社群或公司   | 程式碼、資料、客戶端改連新伺服器的方法與客戶端信任的金鑰或憑證、網域與信件服務等營運資產的交接清單，最好還有網域或它的技術控制 | 以同一套客戶端繼續提供服務               |
| 封存機構           | 讓引用繼續解析所需的對照資料，以及網域的技術控制                                                                               | 讓舊引用繼續運作，或至少保留可查詢的紀錄 |

四種對象對應到持有者的類別（[10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/)）：資料匯出與開源照顧直接客戶；社群接手照顧直接客戶（包括買了提供者硬體的人）與間接使用者；在四種對象裡，不需要拿到網域就以第三方持有者為目的的只有封存機構（拿到網域的接手者也照顧第三方持有者；表外還有 CDN 業者提供的鏡像，例子見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈網域的出售：polyfill.io 的經過〉），因為第三方持有者（和提供者沒有關係、聯絡不到的引用持有者）不會自己採取任何動作。提供者自己能為他們做的靜態封存見 [10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期](/backend/10-system-evolution/staged-shutdown/)。表中「網域的技術控制」指代管網域的 DNS 與回應內容、所有權不移轉，見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈交給中立方的技術控制〉。

## 交給直接客戶的資料匯出

匯出是最基本的移交，前提有兩個：客戶在公告期內有時間執行匯出，以及匯出的格式在另一個服務或自架環境裡讀得進去。

Parse 在 2016 年宣布關閉時提供的資料庫遷移工具，把匯出做成不停機的線上搬遷：先建立快照，再持續同步寫入，讓開發者驗證之後才確認切換，「this can happen without downtime」（[Parse, 2016](http://web.archive.org/web/2017id_/http://blog.parse.com/announcements/moving-on/)；搬遷步驟見 [Parse 遷移指南，Wayback 2016-12](https://web.archive.org/web/20161231233921/https://parse.com/migration)）。它也把搬遷拆成兩件可以分開做的事：資料先搬到開發者自己的 MongoDB，客戶端照舊連線 `api.parse.com`，由 Parse 託管的 API 伺服器改去讀寫開發者自己的資料庫；客戶端改連自己的伺服器是下一步。拆開之後，資料留在 Parse 手上這件最急的事可以先解決，等使用者更新 app 這件最慢的事可以晚一點。

匯出的範圍要涵蓋讓外部引用繼續運作的全部資料，而不只是客戶在介面上看得到的部分。Parse 的託管檔案放在 Parse 自己的 S3 儲存，「our S3 bucket will also be turned down, which means those files will need to be migrated before that date」（[Parse, 2016](http://web.archive.org/web/2017id_/http://blog.parse.com/announcements/hosting-files-on-parse-server/)），所以檔案要另外用一個工具搬。goo.gl 在 2018 年讓帳號持有人從管理介面匯出自己的連結資料（[Google, 2018](https://web.archive.org/web/2018040100000/https://developers.googleblog.com/2018/03/transitioning-google-url-shortener.html)），匯出的是對照表，但網域留在 Google 手上：客戶拿到對照表之後，能做的是在自己的網域上重建連結，原本 `goo.gl` 開頭的引用仍然依賴 Google。匯出期結束之後，讓引用繼續運作所需的資料（例如靜態封存保留的短網址對照表）依服務條款保留，其餘客戶資料依合約與適用的個人資料規定刪除，備份也在範圍內；刪除的時點寫進公告，客戶才知道匯出的最後期限；刪除的證據怎麼留，見 [7.11 資料駐留、刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)。匯出範圍也包括帳號憑證：密碼雜湊連同演算法、參數與 pepper（如果有）一起交出，客戶的使用者才不必全部重設密碼。

## 開源程式碼獨立運作所需的元件與授權

開源服務端程式碼讓客戶與社群能自己架一份相容的服務。它的價值取決於釋出的程式碼是不是完整到能跑起來，而這一點常常受限於上線時採用的第三方元件。

Parse 開源的 Parse Server 是可以跑的例子：它以 Node.js 實作了大部分的 Parse API，宣布同一天就釋出，之後 Parse Dashboard 也開源，至今由社群在 `parse-community` 組織下維護（[Parse, 2016](http://web.archive.org/web/2017id_/http://blog.parse.com/announcements/introducing-parse-server-and-the-database-migration-tool/)；[GitHub parse-community/parse-server](https://github.com/parse-community/parse-server)）。它也有沒涵蓋的部分：同一篇公告列出分析與遠端設定（Parse Config）這兩項功能不在 Parse Server 的支援範圍裡。

Google 在 2025 年釋出 PebbleOS 原始碼則是另一種結果：移除了部分專有程式碼，主要是晶片支援與藍牙堆疊，所以釋出的版本「will not compile or link as released」（[Google Open Source Blog, 2025](https://opensource.googleblog.com/2025/01/see-code-that-powered-pebble-smartwatches.html)）。釋出仍然有用，社群拿到了建置系統與大部分程式；但要讓它跑起來，缺的那幾塊得有人重寫。

開源能不能當作移交手段，取決於讓這份程式碼跑起來的全部元件裡，有多少的授權允許一起釋出。授權不允許的元件只有兩種去處：在釋出前換成可以釋出的替代品，或在公告裡寫明缺了什麼，讓接手的人知道要補哪裡。

## 交給接手的社群或公司

社群或另一家公司接手，是讓直接客戶（包括買了提供者硬體的人）與間接使用者（客戶的 app 或裝置的使用者）繼續使用服務的做法，前提是接手者能讓既有的客戶端改連到新伺服器。

Pebble 的雲端服務由社群專案 Rebble 接手，接手需要的條件在這個案例裡大多是提供者事先留下的。Pebble 在 2016 年 12 月宣布團隊轉入 Fitbit 時就寫明，之後要「phase out cloud services, providing the ability for the community to take over, where possible」（[Pebble 開發者部落格, 2016](http://web.archive.org/web/2017id_/https://developer.pebble.com/blog/2016/12/06/developer-community-update/)）；2017 年的手機 app 更新讓使用者能用一個連結改寫服務設定的來源（[10.5 退場能力的設計前置：端點間接層、本地運作模式與引用的命名空間](/backend/10-system-evolution/exit-ready-design/) 的〈客戶端讀取服務位置的端點間接層〉）；2018 年 1 月把停止日延後半年到 2018 年 6 月 30 日（[Fitbit, 2018](https://dev.fitbit.com/blog/2018-01-24-pebble-support/)）。Rebble 公布接手計畫時感謝 Fitbit 在轉換規劃上的協作，並說明使用者只要在手機上點一個連結就會切換到 Rebble 的服務（[Rebble, 2018](https://rebble.io/2018/02/15/rebble-web-services.html)；[Rebble, 2018-06](https://rebble.io/2018/06/13/get-ready-to-rebble.html)）。Pebble 原創辦人 Eric Migicovsky 在 2025 年回顧時寫道，Rebble 在 2017 年、伺服器關閉之前就封存並開始託管一份應用程式商店的副本（[Eric Migicovsky, 2025](https://ericmigi.com/blog/re-introducing-the-pebble-appstore)）。

Insteon 是沒有任何移交安排的對照案例。2022 年 4 月經營公司停止營運、伺服器關閉，官網隨後貼出的說明只談公司的財務狀況與資產處分。兩個月後，一群 Insteon 使用者買下這個品牌與服務，新公司寫道「Our first priority was getting the hubs online immediately before we had access to this site, the email service provider, social accounts, etc.」（[Insteon, 2022](https://www.insteon.com/blogs/news/a-new-day-for-insteon)）：接手者要先自己摸清楚怎麼讓集線器（連接家中開關與感測器、再連上雲端的裝置）重新上線，官網、信件服務與社群帳號都是之後才拿到的。服務恢復之後改成了付費訂閱（[Insteon, 2022-06](https://www.insteon.com/blogs/news/customer-support-google-assistant-and-product-updates)，現行頁面）。

兩案的差別說明接手者需要提供者事先留下的條件：客戶端改連新伺服器的方法與它信任的金鑰或憑證、服務端的程式碼與資料，以及網域、信件服務、帳號這些營運資產的交接清單。這些都準備好時，交接可以在停止日之前完成；什麼都沒準備時，接手者得在服務已經中斷的情況下從頭重建。

接手者拿到網域時，持有者手上的引用就換了主人，對持有者來說同樣是易手。**公開移交**指三件都做到的移交：提供者事先公告接手者的名稱；在移交條款裡寫明延續服務的範圍與期限；寫明網域或它的技術控制再次轉手時，條款是否跟著延續。公開移交讓持有者事先知道新主人是誰，但條款本身沒有被執行的機制（tr.im 的例子見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈交給中立方的技術控制〉），所以它降低的是新主人看不見的風險，不保證接手者做到。Pebble 交給 Rebble 是事先安排的接手，那一案沒有移交網域，使用者是點一個連結把手機 app 改指到 Rebble 的伺服器。

## 交給封存機構

封存機構照顧的是第三方持有者：讓服務結束前發出去的外部引用繼續解析，或至少讓人查得到它原本指向哪裡。取得對照資料有兩種方式，差別在業者有沒有參與，這決定了能保住的範圍。

**業者合作交出**：2009 年由短網址業者組成、Internet Archive 管理的 301Works，參與的業者「will provide regular backups of their URL mappings」，關站時把網域的技術控制交給 301Works 繼續轉址（[Internet Archive, 2009](https://web.archive.org/web/20091114063044/http://www.301works.org/post/240736199/url-shorteners-working-with-internet-archive-for)）。條款同時考慮了隱私：查詢時要拿著短網址，一次只回一筆（[301Works 參與條款](https://web.archive.org/web/20091116124902/http://www.301works.org/post/220152694/terms-of-participation)）。這個方式的效果取決於業者是否真的上傳；Internet Archive 上的 301Works 收藏至今標示為不公開取用（[Internet Archive 中繼資料](https://archive.org/metadata/301works)），公開資料裡也沒有找到任何參與業者關站時交出網域技術控制的例子。

**外部爬取**：ArchiveTeam 的 URLTeam 不等業者合作，用分散式爬蟲對短碼空間逐一送出請求、記下轉址的目的地，結果公開發布。它的說明頁寫道「Even 301Works founding member bit.ly does not actually share their databases and most other big shorteners don't share theirs either」（[ArchiveTeam URLTeam](https://wiki.archiveteam.org/index.php/URLTeam)）。爬取不需要業者同意，但只能拿到爬得到的部分：短碼是不是循序產生、業者有沒有限制請求速率，決定了能保住多少對照資料。短碼的可猜測性和 [0.24 短網址服務的實作：短碼生成、對照表儲存、轉址快取與點擊紀錄](/backend/00-service-selection/url-shortener-implementation/) 的〈短碼生成：可猜測性與協調成本的取捨〉是同一件事的兩面：短碼越難猜，承載私密連結越安全，關站時外部也越難把對照表保住。

所以想讓封存機構接手的服務，要在上線期間就定期交出對照資料，並在條款裡寫好關站時網域技術控制的去向；等到關站時才聯絡，封存機構拿到的只會是爬得到的那一部分。

## 交不出去的功能與引用：第三方契約、授權限制與提供者網域

有些功能與引用無論提供者多配合都交不出去，退場公告要明寫它們會消失：

- **依賴提供者與第三方契約的功能**：Pebble 在 iOS 上回覆簡訊的功能依賴與電信商的協議，時間軸的即時推送只有 Fitbit 能提供，Rebble 都接不走（[Rebble, 2018](https://rebble.io/2018/02/15/rebble-web-services.html)）。
- **授權不允許釋出的程式碼**：PebbleOS 的晶片與藍牙程式碼。
- **提供者網域下的引用**：除非網域本身或它的技術控制也交出去（以本篇〈交給接手的社群或公司〉的公開移交交出；各種去向的比較見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈網域在服務結束後的去向：續約並回應、續約不回應、到期、出售〉），否則接手者只能在新網域上重建服務，舊的引用仍指向原本的網域。提供者網域的處置見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/)。

短網址服務在這幾項裡只碰到提供者網域下的引用，但它正好是短網址的全部價值所在：對照表可以交出去，引用卻寫在提供者的網域上。短網址服務的退場實作見 [0.24 短網址服務的實作：短碼生成、對照表儲存、轉址快取與點擊紀錄](/backend/00-service-selection/url-shortener-implementation/) 的〈服務結束時的轉址延續〉。
