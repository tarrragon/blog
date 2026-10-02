---
title: "10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS"
slug: "namespace-and-domain-disposition"
date: 2026-10-02
description: "服務結束時網域與名稱的去向，以及它們決定外部引用是失效還是易手：網域的續約與出售、交給中立方的技術控制、套件與雲端資源名稱釋出後被重新申請與佔位、雲端資源刪除後的懸空 DNS 與子網域接管，以及綁在可過期網域上的帳號身分"
weight: 6
tags: ["backend", "evolution", "sunset", "service-termination", "dns", "supply-chain"]
---

本篇的範圍是服務結束時網域與名稱的處置。外部引用（服務發出去、存在別人手上的網址、端點、名稱與身分）在服務結束後有兩種結局：失效是引用不再得到回應，易手是引用指向的網域或名稱換了主人、回應由新主人決定（定義見 [10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/)）；決定走向哪一種的，是引用所在的網域或名稱之後歸誰。上線時怎麼選命名空間見 [10.5 退場能力的設計前置：端點間接層、本地運作模式與引用的命名空間](/backend/10-system-evolution/exit-ready-design/)，這篇處理結束時已經發出去、存在別人手上的那些網域與名稱。

## 網域在服務結束後的去向：續約並回應、續約不回應、到期、出售

服務停止營運之後，它的網域有下列幾種去向，差別在引用會繼續運作、失效還是易手：

- **繼續續約、維持轉址或靜態內容**：引用繼續運作。成本只剩網域續約與一個能回應請求的最小服務，做法見 [10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期](/backend/10-system-evolution/staged-shutdown/)。
- **繼續續約、但不回應任何內容**：引用失效，但不會易手。在不讓網域落到別人手上的做法裡，這是成本最低的一種。
- **讓網域到期**：網域釋出之後任何人都能註冊，引用可能易手。
- **出售或轉讓**：引用確定易手。沒有任何公告的出售，新主人可以照常提供服務，也可以不；公開移交（事先公告接手者、在條款裡寫明延續範圍，條件見 [10.8 移交：資料匯出、開源與交給社群或封存機構](/backend/10-system-evolution/handover-and-archival/) 的〈交給接手的社群或公司〉）讓持有者事先知道新主人是誰，但條款本身沒有被執行的機制。

讓網域到期與沒有公告的出售，對持有者的後果相同：持有者手上的引用照常運作，回應的內容卻由持有者不知道的新主人決定。所以網域的去向要在退場計畫裡明寫，而不是留給公司解散時的資產處分程序決定。短網址服務的需求定義也把網域的去向列進保存承諾：服務結束營運時，「網域在停止營運後由誰續約」是保存承諾的一部分（[0.23 短網址服務的需求定義：自建或購買、保存期限、目的地修改與濫用處理的規格](/backend/00-service-selection/url-shortener-requirements/) 的〈連結的保存期限與保存承諾〉）。

「續約但不回應」要在網域的每一層都做到不回應。網域沒有設定內容時，有些註冊商會預設掛上停放頁並放廣告，回應的內容就變成註冊商決定的，所以要到註冊商的網域設定裡確認停放功能是關的。網域上原本收信的 MX 紀錄也要決定去向：移除它讓寄往舊信箱的信退回，或保留一個有人看管的信箱，讓重設密碼信與客戶的支援信都有人處理。指向雲端 IP 的 A／AAAA 紀錄與萬用字元紀錄也要刪除，雲端業者把那個 IP 分給別人之後，紀錄就會懸空。網域不再寄信時，可以發布表明這個網域不寄信的 SPF 與 DMARC 紀錄，讓別人冒用網域寄出的信被收件端拒收。

續約要持續多久，要分兩種網域判斷。曾經被當成帳號信箱使用的網域，放手的條件是綁在這個網域上的帳號全部改綁到別的信箱，這要另外盤點，和流量無關：本篇〈綁在可過期網域上的帳號身分〉一節的 `ctx` 事件，被重新註冊的就是一個閒置的網域。其他網域看還有沒有引用在被使用：網域釋出之後，註冊它的人能接收所有仍在發出的請求，所以放手的風險隨著請求量與被嵌入的程度上升。判斷請求量需要一份紀錄。掃描器與爬蟲的請求要從請求本身（User-Agent、請求的路徑）排除，這只有 HTTP 存取紀錄做得到，所以判斷要在還保有存取紀錄的靜態封存階段做（見 [10.7 分階段退場：停止新建、唯讀、靜態封存、關閉與公告期](/backend/10-system-evolution/staged-shutdown/)）；關閉之後只剩自己名稱伺服器的查詢紀錄，它看到的是解析器而不是發出請求的人，分不出掃描器，解析器的快取又讓數字偏低，只能當趨勢參考，不能用來判定歸零。沒有這份紀錄、或請求一直沒有歸零時，續約是一筆沒有終點的固定成本，要在退場計畫裡當成長期支出編列；多數註冊商允許一次續約多年，可以在公司還有資金時先付清，並寫明之後由誰接著付。

## 網域的出售：polyfill.io 的經過

polyfill.io 是一個公共 CDN 腳本，網站以 `<script>` 嵌入它，讓舊瀏覽器補上新的 JavaScript 功能。它的經過有完整的公開時間線：

- 2024 年 2 月，網域與 GitHub 帳號轉給新的經營者（[Sansec, 2024](https://sansec.io/research/polyfill-supply-chain-attack)），Cloudflare 的文章寫明新經營者是 Funnull。Cloudflare 隨即在 cdnjs 推出鏡像，理由是「any website embedding a link to the original polyfill.io domain, will now be relying on Funnull to maintain and secure the underlying project」（[Cloudflare, 2024-02](https://blog.cloudflare.com/polyfill-io-now-available-on-cdnjs-reduce-your-supply-chain-risk/)）；Fastly 也提供了替代網址（[Fastly 社群, 2024](https://community.fastly.com/t/new-options-for-polyfill-io-users/2540)）。
- 2024 年 6 月 25 日，Sansec 公布這個網域自易手之後就對行動裝置注入惡意程式碼、把訪客導向博弈網站，受影響的網站超過十萬個（[Sansec, 2024](https://sansec.io/research/polyfill-supply-chain-attack)）。
- 隔天 Cloudflare 對免費方案的網站預設把 polyfill.io 的連結改寫到自己的鏡像，並說明刻意不直接封鎖這個網域，因為「it could cause widespread web outages given how broadly polyfill.io is used with some estimates indicating usage on nearly 4% of all websites」（[Cloudflare, 2024-06](https://blog.cloudflare.com/automatically-replacing-polyfill-io-links-with-cloudflares-mirror-for-a-safer-internet/)）。
- 2025 年 5 月，美國財政部制裁 Funnull，新聞稿寫它在 2024 年購入一個開發者使用的程式碼庫並惡意修改（未點名 polyfill）（[美國財政部, 2025](https://home.treasury.gov/news/press-releases/sb0149)）。

整個過程裡，沒有任何機制直接通知嵌入這個腳本的網站：警告只出現在原作者與 Cloudflare、Fastly 的公開文章裡，看到文章的網站才會換掉；保護其餘網站的是 CDN 業者與資安研究者的介入，網域的處置本身沒有任何安排。被大量嵌入的引用，網域的處置等於在決定所有嵌入者的安全；出售這個網域，就是把所有嵌入者交給買方；這是軟體供應鏈攻擊的一條路徑，建置與發布端的供應鏈信任見 [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)。嵌入者這一側的防護（內容安全政策與第三方腳本的監控）見 [Cloudflare Page Shield：用 CSP + SRI + script monitoring 防 client-side supply chain](/backend/07-security-data-protection/vendors/cloudflare-waf/page-shield-csp-sri/)。

## 交給中立方的技術控制

讓網域繼續運作、又不由自己維運的做法，是把網域的**技術控制**交給一個中立的一方：由對方設定 DNS 與回應內容，所有權仍留在原處。2009 年由短網址業者組成、Internet Archive 管理的封存計畫 301Works，參與條款就是這樣設計的：參與的短網址業者關站時，「technical control of the shortening service domain will be transferred to 301Works.org in order to continue redirecting existing shortened URLs」，並註明「This does not mean that the company will transfer ownership of the domain in such a case」（[Internet Archive, 2009](https://web.archive.org/web/20091114063044/http://www.301works.org/post/240736199/url-shorteners-working-with-internet-archive-for)；[301Works 參與條款](https://web.archive.org/web/20091116124902/http://www.301works.org/post/220152694/terms-of-participation)）。

技術控制的移交要在服務還活著時簽好，結束時才去找，通常已經來不及。tr.im 在 2009 年宣布關站、隨即撤回並改說要開源交給社群時，承諾把網域捐給一個代為持有的第三方：「donate the tr.im domain name to a 3rd party that will hold it in trust」（[tr.im, 2009](https://web.archive.org/web/20090922172221/http://blog.tr.im/post/189122283/open-source-release)），但可查到的網頁快照顯示，2012 年網域只剩空白的目錄列表，2013 年起由新的經營者重新上線，沒有找到網域交給代持第三方的公告。承諾本身沒有被執行的機制。條款裡要寫明的還有續約費由誰付，以及網域所有權轉手時（例如公司解散、資產出售）技術控制是否延續。

## 名稱的保留與回收：套件名稱、雲端資源名稱與短碼

共用登錄服務裡的名稱（套件名稱、雲端資源名稱、使用者名稱）被刪除之後能不能被別人重新申請，決定了引用這個名稱的人會不會在不知情的情況下拿到別人發布的內容。

npm 的 left-pad 事件展示了名稱被回收時發生的事。2016 年 3 月 22 日，一位作者下架了自己的 273 個套件，其中 left-pad 被大量專案間接依賴，建置隨即失敗。有人在十分鐘內以同一個名稱重新發布了功能相同的套件，npm 說明當時的規則：「we allow anyone to use an abandoned package name as long as they don't use the same version numbers」；被下架的其他名稱則由社群搶先發布佔位套件，「to prevent malicious publishing of modules under their names」（[npm, 2016](https://blog.npmjs.org/post/141577284765/kik-left-pad-and-npm)）。一週後 npm 修改政策：全部版本被移除的套件，以安全佔位套件取代，讓名稱不會被惡意搶註（[npm, 2016](https://blog.npmjs.org/post/141905368000/changes-to-npms-unpublish-policy)）；現行政策延續了同一個名稱的同一個版本號不能再使用的規定，並把下架限縮在發布 72 小時內且沒有其他套件相依，或沒有其他套件相依、上週下載少於 300 次、只有單一維護者的套件，其餘只能標記為棄用；全部版本下架之後，文件只寫 24 小時內不能再發布新版本，沒有寫名稱會不會被佔位（[npm unpublish 政策](https://docs.npmjs.com/policies/unpublish)）。版本號不重用保護的是 lockfile：lockfile 記下確切版本與內容雜湊，在重新產生 lockfile 之前，安裝拿到的不會是別人發布的內容；重新解析版本範圍時，才可能拿到新主人發布的新版本。

雲端服務對資源名稱有類似的保留：Azure 的經典雲端服務（classic cloud service，`*.cloudapp.net`）刪除後，對應的 DNS 名稱在保留期內只允許原本租用戶的訂閱重新使用，保留期過後任何訂閱都能申請（[Microsoft Learn](https://learn.microsoft.com/en-us/azure/security/fundamentals/subdomain-takeover)）；App Service 刪除後同樣只讓原本的租用戶重新使用這個名稱，保留多久文件沒有寫明（[Microsoft Learn](https://learn.microsoft.com/en-us/azure/app-service/reference-dangling-subdomain-prevention)）。短網址服務的短碼也是發出去之後會被引用、刪除後可能被重新申請的名稱，[0.23 短網址服務的需求定義：自建或購買、保存期限、目的地修改與濫用處理的規格](/backend/00-service-selection/url-shortener-requirements/) 寫過回收的短碼不能再發給新的連結，要留一筆紀錄佔住；這筆紀錄不設清除期限，否則名稱到期後又回到可申請的池子。

npm 2016 年的規則與短碼的佔位紀錄，共同做法是**佔位**：名稱不再使用時，留一筆沒有期限的紀錄讓它不能被重新申請，而不是把它放回可申請的池子。npm 的佔位名稱仍可由其他人向 npm 申請、經人工審核後轉給對方。Azure 的保留期是對照：它讓原租用戶有時間清理，期限一到名稱就回到可申請的池子。佔位的成本是一筆紀錄，放回池子的代價，是所有還持有這個名稱的引用都可能易手。佔位紀錄只需要名稱、狀態與刪除時間，不需要保留原擁有者的個人資料，所以它和刪除個人資料的要求可以並存。

## 懸空 DNS 與子網域接管

**懸空 DNS**（dangling DNS）指一筆 DNS 紀錄還指向一個已經刪除的雲端資源。客戶在自己的網域設定一筆 CNAME，指向雲端服務給的主機名稱；資源刪除之後，這筆紀錄如果沒有一起刪除，而那個主機名稱又被別人重新申請，客戶的子網域就由別人提供內容，稱為**子網域接管**（subdomain takeover）。Microsoft 的文件寫明接管者能做的事不只放一個假網頁：「a threat actor can use the hijacked subdomain to apply for and receive a valid SSL certificate」（[Microsoft Learn](https://learn.microsoft.com/en-us/azure/security/fundamentals/subdomain-takeover)）。

客戶這一側的防護是刪除雲端資源之前先刪掉指向它的 DNS 紀錄，並定期拿自家網域裡指向雲端主機名的 CNAME 對照仍存在的資源；本節展開的是提供者這一側。防止子網域接管的工作橫跨客戶與提供者兩方：DNS 紀錄在客戶的網域裡，提供者無法替客戶刪除；主機名稱在提供者的命名空間裡，能不能被別人重新申請由提供者決定。提供者這一側能做的有下列幾件：

- **刪除後保留名稱一段時間**，只給原本的租用戶重新使用（〈名稱的保留與回收：套件名稱、雲端資源名稱與短碼〉一節的 Azure 規則）。
- **要求驗證網域的所有權**：GitHub Pages 讓帳號驗證自己的網域，驗證之後只有這個帳號能把網站發布到這個網域，並列出接管發生的情形：「when you delete your repository, when your billing plan is downgraded, or after any other change which unlinks the custom domain or disables GitHub Pages while the domain remains configured for GitHub Pages and is not verified」（[GitHub Docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)）。
- **讓預設主機名稱無法被預測**：見 [10.5 退場能力的設計前置：端點間接層、本地運作模式與引用的命名空間](/backend/10-system-evolution/exit-ready-design/) 的〈外部引用所屬的命名空間：提供者網域、客戶網域與共用登錄服務〉裡 Azure 的雜湊主機名稱。

服務本身結束時，保留名稱、驗證網域與不可預測的主機名稱這幾項做法要延續下去：提供者自己的網域裡，所有曾經發給客戶的子網域（例如 `<app>.herokuapp.com` 這一類）都不能放回可申請的池子。Heroku 在 2022 年終止免費方案時，把免費的 app 縮到零個執行個體，而不是刪除 app：程式、設定與名稱都保留，只是不再有執行中的程序（[Heroku FAQ，Wayback 2022-08-25](http://web.archive.org/web/20220825195919id_/https://help.heroku.com/RSBRUH58/removal-of-heroku-free-product-plans-faq)）。同一次處置從 2022 年 10 月起刪除閒置一年以上的帳號（[Heroku, 2022](https://www.heroku.com/blog/next-chapter/)）；刪除帳號這一條路，正是曾經發給客戶的子網域名稱可能回到可申請池子的地方。

## 綁在可過期網域上的帳號身分

[10.4 服務終止的範圍：外部引用的種類與持有者](/backend/10-system-evolution/service-termination-scope/) 列的外部引用裡，綁在網域上的身分是最不顯眼的一種：套件登錄服務用維護者的信箱寄送重設密碼的信，而信箱屬於維護者自己的網域。網域過期、被別人註冊之後，新主人能收到重設密碼的信，接管維護者的帳號與帳號下的所有套件。

2022 年 5 月 14 日，PyPI 套件 `ctx` 擁有者帳號的信箱網域被重新註冊，事件報告記錄網域註冊後十二分鐘，密碼重設與惡意版本的上傳就開始了（[PyPI 事件報告](https://python-security.readthedocs.io/pypi-vuln/index-2022-05-24-ctx-domain-takeover.html)）。同一時期的研究在 npm 找到 2,818 個維護者信箱屬於已過期的網域，可以藉此接管 8,494 個套件（[Zahan 等, 2022](https://arxiv.org/abs/2112.10165)）。PyPI 自 2025 年起定期檢查信箱網域的狀態，網域進入過期階段時取消該信箱的驗證（PyPI 稱這類事件為 domain resurrection），到 2025 年 8 月已取消 1,800 個以上（[PyPI, 2025](https://blog.pypi.org/posts/2025-08-18-preventing-domain-resurrections/)）。

綁在網域上的帳號身分對服務終止有兩層意義。第一層在提供者自己：提供者的網域到期、被別人註冊之後，新主人收得到寄往這個網域的所有信，包括提供者自己在其他服務上的帳號的重設密碼信，因而能接管那些帳號，也收得到客戶寄來的支援信。第二層在登錄服務：它在這一種引用裡是持有者，同時經營自己的帳號系統，要把「維護者信箱的網域是否仍有效」當成帳號安全的一部分持續檢查，而不是只在註冊時驗證一次。
