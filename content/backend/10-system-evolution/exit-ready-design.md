---
title: "10.5 退場能力的設計前置：端點間接層、本地運作模式與引用的命名空間"
slug: "exit-ready-design"
date: 2026-10-02
description: "服務上線時就決定、越接近關閉越難補上的設計：客戶端讀取服務位置的間接層、沒有雲端時裝置還能做什麼、外部引用落在提供者還是客戶的命名空間、使用紀錄與可交出的資料格式，以及依賴第三方契約與授權而無法移交的功能"
weight: 5
tags: ["backend", "evolution", "sunset", "service-termination", "design"]
---

服務上線時做的幾個設計決定，在服務結束時決定了能不能讓外部引用繼續運作、能不能把服務交給別人。外部引用指服務發出去、存在別人的文件、程式與裝置裡的網址、端點、名稱與身分，持有者是手上有這些引用的人，完整定義見 [10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/)。這篇整理這些決定。它們在上線時的成本多半很低，越接近結束越難補上：引用早就寫進別人的程式、韌體與文件裡，要改只能靠客戶端更新，而更新要在服務還在運作時送到裝置上。

## 客戶端讀取服務位置的端點間接層

**端點間接層**（英文常見的說法是 bootstrap config）指客戶端（行動 app、裝置韌體、SDK）不直接寫死它要連線的伺服器位置，而是先讀一份設定，再依設定連線；完整的間接層還要讓這份設定本身的來源可以由提供者以外的人（使用者或接手者）改寫，下面 Pebble 的案例說明為什麼兩件都要做。有沒有這一層，決定服務結束時能不能讓已經發出去的客戶端改連到別的伺服器。

Parse 與 Pebble 兩個案例的差別，在改寫連線位置要不要經過發布新版 app。Parse 在 2016 年 1 月宣布關閉時，同一天釋出開源的 Parse Server，並寫道「Our client SDKs now support changing the API server location to direct them to your own」（[Parse, 2016](http://web.archive.org/web/2017id_/http://blog.parse.com/announcements/introducing-parse-server-and-the-database-migration-tool/)）。要讓已經安裝在使用者手機上的 app 改連自架的伺服器，開發者得發布帶新設定的 app 版本，使用者得更新；遷移指南直接說發布新版、讓客戶端改連自架伺服器這一階段「is non-trivial, and will require dedicated development time」（[Parse 遷移指南，Wayback 2016-12](https://web.archive.org/web/20161231233921/https://parse.com/migration)）。

Pebble 的手機 app 讀取的是一份服務設定（boot config），裡面列出各項雲端服務的位置。2017 年 4 月的更新開放使用者用一個連結改寫這份設定的來源：「The link pebble://custom-boot-config-url/CUSTOM_URL forces the Pebble mobile app to load its service configuration from the specified CUSTOM_URL」（[Pebble 開發者部落格, 2017](http://web.archive.org/web/2017id_/https://developer.pebble.com/blog/2017/04/04/transitioning-update/)）。2018 年 Fitbit 停止 Pebble 的雲端服務時，社群專案 Rebble 接手，切換方式是讓使用者在手機上點一個連結（Rebble 的公告沒有寫出背後用的是哪個機制，推測就是這個改寫設定來源的連結），「you have nothing to download or install」（[Rebble, 2018](https://rebble.io/2018/06/13/get-ready-to-rebble.html)）。Pebble 2017 年的公告只寫了使用者可以改寫設定的來源；手機 app 讀取服務設定這一層是不是從 Pebble 手錶上市時就存在，公告沒有交代。這個案例也說明，改寫設定來源的能力可以晚於上線補上，條件是補上它的那一版客戶端，要在提供者的發布管道與更新伺服器還在運作時送到足夠多的裝置上；Pebble 的這次更新比雲端關閉早了一年多。沒有更新管道、或更新管道已經停止的客戶端（不支援線上更新的韌體、停止發版的 app）沒有這條路；支援線上更新（OTA）的韌體和 app 適用同一個條件。寫死在客戶端的主機名稱本身也是一層間接：網域移交出去，接手者就能把它指到新的伺服器。客戶端信任公開的憑證機構時，接手者用網域就能重新申請憑證；只有客戶端釘選了憑證或自帶信任錨點時，才需要提供者交出金鑰或換錨點的路徑。

所以設計上要預留的是兩件事（寫死的主機名稱落在可以移交的網域上，是兩件都沒有時的後備）：客戶端連線的位置來自一份可以更新的設定，而不是編譯進程式的常數；以及這份設定的來源，在提供者不再運作時有辦法被指到接手者的伺服器。只做到「設定可以更新」這一件，存放設定的伺服器本身仍是提供者的服務，它關閉時客戶端就停在最後一份設定上。另外還有客戶端信任的對象要預留：客戶端若只接受提供者憑證的連線、或只安裝提供者金鑰簽章的韌體與設定，接手者即使改寫了設定來源，也要拿到這些金鑰，或有一條換掉信任錨點的路徑，才連得上、推得出更新。

## 雲端關閉後的裝置功能：本地運作模式

**本地運作模式**（英文多稱 local control 或 offline mode）指裝置在連不上提供者的雲端服務時，仍能完成它被買來做的那件事，例如開關燈、感測器觸發其他裝置。對賣出去的硬體來說，有沒有這個模式決定雲端關閉時裝置是少了一些功能，還是整台失效（英文報導多稱為 bricking）。它和雲端架構裡的 [Static Stability](/backend/knowledge-cards/static-stability/) 是同一個想法：控制面失效時，資料面照最後的狀態繼續運作。

Insteon 與 Revolv 分別是有本地模式與沒有本地模式的結局。Insteon 的開關、插座與感測器之間用本地的專有無線協定連動。2022 年 4 月經營公司停止營運、伺服器關閉時，「All of those stayed operational, but users couldn't remotely access their hub through the app or program the hub」（[Stacey on IoT, 2022](https://staceyoniot.com/users-report-insteons-servers-are-back-online/)）：失去的是 app 遠端控制與雲端整合，家裡的燈照樣開關。Revolv 的集線器沒有本地模式，Nest 在 2016 年關閉它的雲端服務時，集線器整台無法運作，Nest 能給的補救只剩退款，而退款是公告一個多月後才加上的（見 [10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期](/backend/10-system-evolution/staged-shutdown/) 的〈賣出去的裝置的補償〉）。美國聯邦貿易委員會（FTC）調查 Revolv 的關閉後寫道，擔心的是「reasonable consumers would not expect the Revolv hubs to become unusable」（[FTC 結案信, 2016](https://www.ftc.gov/system/files/documents/closing_letters/nid/160707nestrevolvletter.pdf)）。

本地模式也能在結束前補上，但要提前很久做。Fitbit 在 2016 年 12 月接手 Pebble 之後，第一步是更新手機 app，「loosening their dependency on a patchwork of cloud services」（[Pebble 開發者部落格, 2016](http://web.archive.org/web/2017id_/https://developer.pebble.com/blog/2016/12/14/first-steps-forward-with-fitbit/)）：2017 年 4 月的版本在連不上認證與更新伺服器時仍可使用，並加入離線模式（[Pebble 開發者部落格, 2017](http://web.archive.org/web/2017id_/https://developer.pebble.com/blog/2017/04/04/transitioning-update/)）。這次 app 更新比 2018 年 6 月雲端關閉早了一年多。Spotify 的車用控制器 Car Thing 則沒有本地模式，2024 年停止支援時，支援頁建議使用者回復原廠設定，並依電子廢棄物規定處理裝置（[Spotify 支援頁，Wayback 2024-05-23](http://web.archive.org/web/20240523162707id_/https://support.spotify.com/us/article/car-thing-discontinued/)）。

設計時要分清楚哪些功能本質上需要雲端（跨裝置同步、遠端存取、第三方整合），哪些只是實作時方便放在雲端（排程、裝置之間的連動、本機設定）。後一類功能在上線時就放在本地執行，雲端關閉時裝置保留它被買來做的那些事。

## 外部引用所屬的命名空間：提供者網域、客戶網域與共用登錄服務

**命名空間**在這裡指分配名稱、並決定名稱指向哪裡的那一層。外部引用的網址、主機名稱或名稱都屬於某個命名空間：提供者的網域、客戶自己的網域、或某個共用的登錄服務。服務結束時，引用能不能被保住，取決於誰還控制那個命名空間。

落在提供者網域下的引用，提供者停止續約或出售網域，引用就跟著失效或易手。Firebase Dynamic Links 在 2025 年關閉時，常見問答回答使用者能不能保留或轉移 `page.link` 網域：「No, once the Firebase Dynamic Links service is shut down any .page.link domains will no longer be available」（[Firebase 常見問答](https://firebase.google.com/support/dynamic-links-faq)）。Firebase Dynamic Links 也讓客戶改用自己的網域；用自己網域的客戶，服務關閉後還能把網域指到別的轉址服務。短網址服務提供自訂網域的理由之一就在這裡，見 [0.23 短網址服務的需求定義：自建或購買、保存期限、目的地修改與濫用處理的規格](/backend/00-service-selection/url-shortener-requirements/) 的〈自訂網域與網域名聲的隔離〉；客戶網域讓連結能搬到別的服務，這件事的商業分析，見 [短網址的商業模型：訂閱、自架、平台內建與廣告插頁各由誰出資維持轉址](/business/case-analyses/url-shortener-business-models/) 的〈網域：品牌短網址的定價與切換成本〉。

落在共用命名空間的名稱，要看名稱釋出之後能不能被別人申請。Azure App Service 舊的預設主機名 `<應用程式名稱>.azurewebsites.net`，Microsoft 自己的文件形容為「globally predictable」；新的主機名加上一段隨機雜湊，外人無法重建同名的主機，而同一份文件寫明這種雜湊主機名「You can't apply them to existing resources retroactively」（[Microsoft Learn](https://learn.microsoft.com/en-us/azure/app-service/reference-dangling-subdomain-prevention)）。名稱可預測的風險在於：客戶網域裡指向這個主機名的 CNAME，若在資源刪除後沒有一起刪掉，別人重新申請同名的主機，就會接收客戶那個子網域的流量，稱為懸空 DNS 與子網域接管。雜湊主機名這項補救只涵蓋之後新建的資源；名稱已經以可預測的方式發出去的既有資源，要靠網域驗證或偵測懸空 DNS 紀錄這類另外的手段。名稱的保留與回收、子網域接管的細節見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/)。

被嵌入的程式碼另有一層提供者做得到的設計：發布帶版本號、內容固定的網址，嵌入者就能加上子資源完整性（Subresource Integrity，SRI）雜湊。跨來源載入的腳本要比對雜湊，提供者的回應還要帶 CORS 標頭（`Access-Control-Allow-Origin`），嵌入者在 `<script>` 加上 `crossorigin` 屬性。網域易手、內容被換掉之後，瀏覽器比對雜湊不符會拒絕載入，引用的結局從易手變成失效。

## 使用紀錄與可交出的資料格式

服務結束時有兩個問題要靠上線時就存在的資料回答：哪些外部引用還有人在用，以及讓引用繼續運作需要哪些資料、能用什麼格式交出去。

**使用紀錄**回答哪些外部引用還有人在用。記錄的單位與做法（最後使用時間表、消費者身分與客戶端版本的識別）見 [11.12 API 消費者用量觀測：契約決策要的觀測維度、消費者身分的識別、欄位級用量與全量或抽樣的成本邊界](/backend/11-api-design/consumer-usage-observability/)；客戶端版本與憑證是事後推估持有者類別、決定公告期的依據，所以和最後使用時間一起記。goo.gl 在 2024 年宣布所有連結將回 404，理由之一是「more than 99% of them had no activity in the last month」；2025 年修正為只停用 2024 年底沒有活動的連結（[Google, 2024](https://developers.googleblog.com/en/google-url-shortener-links-will-no-longer-be-available/)；[Google, 2025](https://blog.google/technology/developers/googl-link-shortening-update/)）。兩個決定都建立在點擊紀錄上；沒有點擊紀錄，提供者只能在「全部保留」與「全部停用」之間選。紀錄要保存到什麼粒度，同時受隱私要求限制：只需要知道「這條引用最近有沒有被使用」時，保存彙總後的最後使用時間就夠了。

**可交出的資料格式**回答讓引用繼續運作所需的資料能不能交出去。讓外部引用繼續運作所需的資料（短網址的對照表、套件的檔案與中繼資料、專案的原始碼與 issue）要能匯出成別人讀得懂的格式。2009 年由短網址業者組成、Internet Archive 管理的封存計畫 301Works，參與條款寫明對照表的格式是以 tab 分隔的長網址、短網址與選填的點擊數（[301Works 參與條款，Wayback 2009](https://web.archive.org/web/20091116124902/http://www.301works.org/post/220152694/terms-of-participation)）；Microsoft 在 2017 年關閉 CodePlex 時，提供 Markdown 與 JSON 格式的專案封存檔（[Microsoft, 2017](https://devblogs.microsoft.com/bharry/shutting-down-codeplex/)）。客戶自己使用者的聯絡資料也在要能匯出的範圍裡：提供者聯絡不到間接使用者，只能靠客戶轉達，客戶手上有沒有這份名單，決定轉達做不做得到（見 [10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期](/backend/10-system-evolution/staged-shutdown/) 的〈公告期的長度與通知管道〉）。格式在上線時就定下來，結束時只要執行匯出；結束時才設計格式，就要在最缺人力的時候設計並實作一套新的匯出格式。交給誰、交出去之後怎麼用，見 [10.8 移交：資料匯出、開源與交給社群或封存機構](/backend/10-system-evolution/handover-and-archival/)。

## 依賴第三方契約與授權而無法移交的部分

有些功能在服務結束時無法交給別人，原因在它們依賴提供者和第三方之間的契約或授權，缺的並不是資料或程式碼。這些功能能不能移交，在提供者選用那個第三方服務、簽下契約的時候就決定了。

Rebble 接手 Pebble 的雲端服務時，有兩項功能接不走。一是時間軸的即時推送：「for technical reasons it is impossible for any entity other than Fitbit to provide that service」。二是 iOS 上回覆簡訊的功能：「Pebble had agreements in place with several carriers and service providers in order to provide the ability to reply to text messages on iOS」（[Rebble, 2018](https://rebble.io/2018/02/15/rebble-web-services.html)）。程式碼也有同樣的限制：Google 在 2025 年釋出 PebbleOS 原始碼時，移除了部分專有程式碼，主要是晶片支援與藍牙堆疊，所以釋出的版本「will not compile or link as released」（[Google Open Source Blog, 2025](https://opensource.googleblog.com/2025/01/see-code-that-powered-pebble-smartwatches.html)）。

條款不允許移交的功能，屬於 [10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/) 盤點清單裡「結束時一定會失去的部分」那一項，它們在結束時的處置見 [10.8 移交：資料匯出、開源與交給社群或封存機構](/backend/10-system-evolution/handover-and-archival/) 的〈交不出去的功能與引用：第三方契約、授權限制與提供者網域〉。

## 租戶的可遷出保險清單與提供者的退場設計

[0.21 交付形態選型：從全託管到自建的光譜與邊界](/backend/00-service-selection/delivery-mode-selection/) 列了一份「可遷出保險清單」，給租戶（在別人的平台上經營服務的一方）用。清單裡的自有網域、資料定期匯出、客戶聯絡管道自有三項，是租戶在採用別人的平台時替自己買的保險。這篇的設計是同一份保險從提供者這一側看：讓客戶能用自己的網域、讓資料能匯出、讓客戶能匯出自己使用者的聯絡資料，分別對應清單的三項；讓客戶端的連線位置能被改寫，則是租戶清單沒有、只有提供者做得到的一項。提供者在上線時做了這些，等於替所有持有外部引用的人買了同一份保險，包括那些不在合約裡、也不會替自己買保險的第三方持有者。清單另外三項的提供者側各不相同：金流可攜靠的是讓扣款授權綁在客戶自己名下的金流帳戶，或配合金流商之間的卡號資料轉移，授權本身不在提供者的匯出檔裡；密碼不可攜的預案是讓密碼雜湊連同演算法、參數與 pepper（如果有）一起匯出；業務邏輯文件化對應的是讓設定與規則能匯出。租戶側的處理見 [10.3 託管形態遷出：資產線盤點與並行期執行](/backend/10-system-evolution/managed-platform-exit/) 的〈身分線〉與〈整合線〉；這些都是 [Vendor Lock-in](/backend/knowledge-cards/vendor-lock-in/) 在提供者這一側的解法。
