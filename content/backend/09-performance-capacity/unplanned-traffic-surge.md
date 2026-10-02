---
title: "9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路"
slug: "unplanned-traffic-surge"
date: 2026-10-02
description: "沒有準備窗口的瞬時大流量（突發流量、流量暴增）怎麼承接：依流量形狀分辨真人需求、應用層的濫用流量、體積型攻擊（DDoS），自動擴展的反應時間換算成緩衝，入口標記請求優先等級與負載卸除的順序，等候室與事前註冊這類准入控制，把體積型攻擊交給更大的邊緣網路，以及擴展跟不上時的退路"
weight: 15
tags: ["backend", "performance", "capacity", "surge", "load-shedding"]
---

這篇整理沒有準備窗口的瞬時大流量：流量已經進來、或實際需求遠超過預測時，系統還能用什麼機制承接。排得出日期的開賣與發布，需求遠超過預測時，承接的也是這些機制。能排出準備時程、而且需求在預測範圍之內的峰值見 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)。依呼叫者分配配額的限流實作見 [Rate Limit 實作](/backend/09-performance-capacity/rate-limit-implementation/)。流量已經進來時，當下還能做哪些決定見本篇〈事前建好的機制與當下能做的決定〉，事故的止血見 [8.3 止血、降級與回復策略](/backend/08-incident-response/containment-recovery-strategy/)；流量不回落、基準線永久上移時，要重做的是容量規劃，見 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。


## 流量來源的辨識：真人需求、應用層的濫用流量、體積型攻擊

瞬時大流量的處置方式由流量的來源決定，所以第一個判斷是這些請求從哪裡來。來源可以分成三種，各自要用不同的機制處理。

**真人需求**是真實使用者同時湧入，例如產品爆紅、廣告播出、新功能上線。這些請求都想被服務，處置的方向是承接、排隊或降級。Coinbase 在 2022 年美式足球超級盃播出 QR code 廣告後，一分鐘內 landing page 收到超過 2,000 萬次請求，互動量是過去基準的 6 倍。工程團隊事前做過「handle millions of simultaneous hits」的壓測，實際流量仍超出預測，結果是「temporarily throttling our systems」（[Coinbase，Wayback 2022-02-14](https://web.archive.org/web/20220214201410id_/https://blog.coinbase.com/everyone-wins-at-super-bowl-lvi-wagmi-c0039452975f)）。Coinbase 的這篇文章沒有交代節流做在哪一層，它能說明的是一件事：做過壓測，預測仍可能失準。

**應用層的濫用流量**是程式送出、不該被服務的完整請求，可能夾在真人需求裡，例如搶票與搶購的機器人，也可能單獨出現，例如大量註冊帳號、大量建立資源、掃描網址、在應用層大量送出請求的 HTTP flood（業界稱為 L7 DDoS）。合法的程式客戶不在這一類：帶 API 金鑰的客戶程式、搜尋引擎爬蟲、合作夥伴的批次作業是要承接的需求，依〈負載卸除與限流的分工、請求的優先等級〉一節的等級處置。它沒有塞滿頻寬，請求在協定、格式與目標路徑上和正常請求一樣，處置的方向是辨識出來再拒絕；夾在真人需求裡時，真人的部分仍要承接。Ticketmaster 在 2022 年 11 月 Taylor Swift 巡演開賣時，系統請求總數達到 35 億，是過去峰值的 4 倍，業者把成因歸給「bot attacks as well as fans who didn't have codes」（[Ticketmaster, 2022](https://business.ticketmaster.com/business-solutions/taylor-swift-the-eras-tour-onsale-explained/)）。機器人佔多少比例、怎麼偵測，原文沒有寫，這個歸因是業者自己的說法。這類流量由哪個機制處理，看它怎麼分布：集中在少數來源的，依呼叫者的限流就擋得住；分散在大量來源、或像 HTTP flood 一樣打在任意端點的，瀏覽器流量要靠邊緣的機器人管理（bot management，用 JavaScript 挑戰、瀏覽器特徵等判斷請求是不是真的瀏覽器）與 WAF 速率規則辨識；呼叫者是程式而且要認證的 API，挑戰機制用不上，做法是在邊緣先擋掉沒帶有效憑證的請求，再依金鑰限流，過載時先卸除未認證的流量。WAF 的速率規則多半依單一來源位址計數，對每個來源都低速率的分散攻擊，失效方式和依呼叫者的限流相同。站內還沒有專講 DDoS 與機器人防護的文章，攻擊面見 [7.R4 資源濫用與可用性破壞](/backend/07-security-data-protection/red-team/resource-abuse/)；搶購與開賣裡夾雜的機器人，由事前註冊篩掉進入佇列的資格，它們送出的請求仍要靠邊緣吸收，見〈准入控制〉一節。

**體積型攻擊**（volumetric DDoS）是非人為流量直接塞滿入口頻寬，請求本身不需要被服務。SYN flood 這類協定層攻擊耗盡的是伺服器的連線狀態而不是頻寬；規模在 SYN cookies 與負載平衡器能吸收的範圍內時可以在本地處理，超過時同樣要交給邊緣網路。GitHub 在 2018 年 2 月 28 日遭受 memcached 反射放大攻擊，峰值 1.35 Tbps、每秒 1.269 億個封包，來源分散在上千個自治系統（ASN，網際網路上各自管理路由的獨立網路）的數萬個端點（[GitHub, 2018](https://github.blog/news-insights/company-news/ddos-incident-report/)）。攻擊者偽造來源位址，向開放的 memcached 伺服器送出小請求，伺服器把大得多的回應送往目標，「overwhelming its resources - most typically the network itself」（[Cloudflare, 2018](https://blog.cloudflare.com/memcrashed-major-amplification-attacks-from-port-11211/)）。

三種來源光看總量分不出來，要看流量的形狀。GitHub 偵測到攻擊，靠的是監控系統發現「an anomaly in the ratio of ingress to egress traffic」：正常的網站回應比請求大，所以平常出站流量多於入站；這時入站流量反而遠超過出站，表示湧進來的不是正常請求。依這三種來源的產生方式推論，它們的形狀通常不同：真人需求分布在平常就會被造訪的路徑上，來源跟著使用者的地理分布；應用層的濫用流量常集中在少數高價值端點，請求的間隔與參數比真人規律，不針對特定端點的 HTTP flood 則要看來源分布與請求間隔的規律性，而合法的 API 客戶流量同樣集中而規律，所以這個訊號要和「有沒有帶有效憑證」一起看；體積型攻擊集中在少數協定與埠號，或是像 GitHub 這次一樣，是根本沒有對應請求的回應封包。偵測訊號要在事前就照形狀設計（基準線與異常偵測見 [4.14 Anomaly Detection](/backend/04-observability/anomaly-detection/)，告警的設計見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)），因為流量進來的當下，只有既有的儀表板可以看。

## 自動擴展（autoscaling）的反應時間與緩衝

**擴展的反應時間**是從擴展決策做出、到新容量開始服務請求的時間。這段時間裡流量還在上升，所以真正要回答的問題是：反應時間內流量會再上升多少，現有容量撐不撐得住這段增量。撐得住這段增量所需的額外容量，就是**擴展緩衝**，它是 [Headroom Budget](/backend/knowledge-cards/headroom-budget/) 裡因應擴展反應時間的那一部分。這個算法只適用於擴展得上去的層：沒有自動擴展、只能人工加機器時，反應時間就是人工擴容的時間，緩衝等於平常就留著的固定容量；自建的資料庫與快取這類有狀態、不能即時水平擴展的層，要按預估峰值加上 headroom 預留（見 [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/) 與 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的〈不可水平擴容服務的容量規劃〉），託管的隨需模式資料庫也有自己的擴展速率上限，要查業者文件；超出的部分交給後面卸除、准入與退路三節。

Hotstar 的工程文用一組估算說明這個關係。Hotstar 的直播觀眾在比賽關鍵時刻像海嘯一樣湧入，事前把容量擴到預期同時在線人數「was resulting in a heavy infrastructure costs」，所以 2019 年開始在自己的 Kubernetes 平台上試用自建的 autoscaler。文中假設加節點約 90 秒，容器建立與應用啟動約 75 秒，再加上收集指標與做決策，總延遲約 4 分鐘，「we would have missed about two million people on the platform within these 4 minutes」。直播期間的緩衝因此加大：依同時在線人數分階擴展的服務多加 200 萬人，依請求數擴展的服務多加 30%（[Hotstar, 2019，Wayback](https://web.archive.org/web/20210221203256id_/https://blog.hotstar.com/scaling-for-tsunami-traffic-2ec290c37504)）。依這個關係，緩衝的大小是反應時間內流量的上升量，上升速度固定時就是兩者相乘；像 Coinbase 那樣一分鐘內湧入的階梯式上升，緩衝要涵蓋的是整段階梯。兩個值都要對自己的系統量出來，Hotstar 文中的數字只是估算的示範；上升速度取自過去事件的紀錄，反應時間取自實際擴展一次的計時。兩個值都容易被低估：無預警事件的上升速度正好是超出過去紀錄的那一種，反應時間在過載與網路劣化時也比平靜時長（下面 Slack 的例子），所以反應時間要在負載下量；緩衝涵蓋不到的那一段上升，交給〈負載卸除與限流的分工、請求的優先等級〉與〈准入控制〉兩節的機制。緩衝也是平常一直在付的閒置容量，Hotstar 改用 autoscaler 的理由正是事前全額擴容太貴。

擴展的觸發訊號要選負載上升時數值也跟著上升的指標。Hotstar 多數服務用處理中的請求數觸發，而不是 CPU。Slack 在 2021 年 1 月 4 日的事故說明了 CPU 會指錯方向：網路在太平洋時間早上 7 點前就開始劣化，執行緒花更多時間等待，CPU 使用率因此下降，自動擴展先觸發了縮容，隨後執行緒使用率上升，才轉為大量擴容，7:01 到 7:15 之間試圖加入 1,200 台伺服器（[Slack, 2021](https://slack.engineering/slacks-outage-on-january-4th-2021/)）。Amazon 的 Builders' Library 提醒另一個方向的錯：負載卸除的門檻若和擴展門檻設在相近的 CPU 值，卸除會把 CPU 壓在門檻以下，「reactive scaling will never receive or get a delayed signal to launch new instances」（[Amazon Builders' Library](https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/)）。

擴展本身也是一條有上限的依賴鏈。Slack 在同一次事故裡，加機器的動作本身也失敗了：負責設定與測試新機器的 provision-service 在劣化的網路下同時建立大量機器，撞到 Linux 的 open files 上限與 AWS 的 quota；大量沒建好的機器佔滿了 auto scaling group 預先設定的數量上限，真正能服務的機器反而不夠。根源是託管的 AWS Transit Gateway（連接多個 VPC 的託管路由元件，新機器的流量都經過它）沒有及時擴展，最後由 AWS 工程師手動擴大容量。這條鏈上的雲端 quota、群組大小上限與檔案描述符上限，都是事前設定的值，流量上升時，擴展動作會同時消耗這些上限；託管的網路元件的擴展由業者控制，Slack 事後的對策是在下一個假期結束前「request a preemptive upscaling」，這個對策需要一個已知的日期；無預警的流量沒有日期可預約，能做的是在架構上不讓所有流量都經過單一個託管元件，或向業者購買常駐的容量預留。上限調高也不夠：Slack 的群組上限原本就是「multiples of the number of instances that we normally require to serve our peak traffic」，被佔滿的原因是建失敗的機器也佔名額。所以上限要容納的是峰值所需的機器數，加上擴展過程中還沒建好或建失敗、但已經佔了名額的機器；擴展路徑本身（provision-service 這一類）也要在擴展規模下壓測，這正是 Slack 事後的另一項對策。盤點擴展路徑上的上限，是 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/) 在 T-30 天申請 quota 那一步的同一件事，差別在無預警的流量沒有 T-30 天，這些上限要平常就調好。上限同時也是成本的上限：應用層的濫用流量一樣會觸發自動擴展，攻擊會直接變成帳單，所以上限是兩個方向的取捨：它要放得下擴展所需的機器數，同時是願意付的成本上限，調高的同時要設預算告警（見 [成本模型](/operations/05-capacity-planning/cost-model/) 的〈Autoscaler 的 max 是財務斷路器〉與 [成本監控與告警](/operations/08-cost-management/cost-monitoring/) 的〈異常告警：抓突增，然後定位〉）。自動擴展的其他設計責任見 [Autoscaling](/backend/knowledge-cards/autoscaling/) 與 [Cold Start](/backend/knowledge-cards/cold-start/)。

## 負載卸除與限流的分工、請求的優先等級

**負載卸除**（load shedding）是系統接近過載時，主動拒絕一部分請求，讓系統決定繼續處理的那些請求能在客戶端逾時之前完成（見 [Load Shedding](/backend/knowledge-cards/load-shedding/)）。Stripe 把它和限流（[Rate Limit](/backend/knowledge-cards/rate-limit/)）分開定義：限流依「誰在送請求」決定要不要拒絕，負載卸除「makes its decisions based on the whole state of the system rather than the user who is making the request」（[Stripe, 2017](https://stripe.com/blog/rate-limiters)）。兩者要分開，是因為瞬時大流量常常來自大量各自都沒超過配額的使用者，依呼叫者分配的配額全部合規，系統整體仍然過載。

負載卸除要能決定先拒絕誰，前提是每個請求在進入系統時就帶著優先等級。Stripe 的做法分成機群與單台機器兩層。機群這一層保留一部分容量給關鍵請求：「If our reservation number is 20%, then any non-critical request over their 80% allocation would be rejected with status code 503」。單台機器這一層把請求分成四類：關鍵方法、寫入（POST）、讀取（GET）與測試模式的流量。機器忙到處理不了時先卸除測試模式的流量，仍然過載才擴大卸除的範圍；依這四類的列舉順序推論，接著是讀取、寫入，最後才是關鍵方法。Google SRE 的做法是給每個請求四級重要性（criticality）（CRITICAL_PLUS、CRITICAL、SHEDDABLE_PLUS、SHEDDABLE），在最靠近瀏覽器與行動客戶端的 HTTP 前端設定，隨後續的每一次內部呼叫傳遞下去，服務要「provision enough capacity for all expected CRITICAL and CRITICAL_PLUS traffic」（[Google SRE Book, Handling Overload](https://sre.google/sre-book/handling-overload/)）。

優先等級在入口標好，是因為過載時每個服務各自判斷會用上互相衝突的規則：前端保住了一個請求，它呼叫的下游卻把那個請求的子呼叫丟掉，前端花的工作全部白費。Amazon 指出，各服務若用互相衝突的優先規則，「systemwide availability could be affected and work could be wasted」；Google SRE 的做法正是在最靠近客戶端的入口設定、往下傳遞。要在入口標記等級，入口要有自家能改的 gateway 或 middleware；全部交給託管負載平衡器的服務，這一步要先補。Amazon 也列出兩個容易漏掉的等級：負載平衡器送來的健康檢查最重要，回應不及時，負載平衡器會把那台機器移出，機群因此變小；搜尋引擎爬蟲的請求比真人的請求優先度低，最好移到離峰時段（[Amazon Builders' Library](https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/)）。健康檢查的設計見 [Health Check](/backend/knowledge-cards/health-check/)。

卸除與恢復的速度也要事先決定。Stripe 寫明「It's very important that shedding and bringing load happen slowly, or you can end up flapping」：削得太快，負載一降就把流量全部放回來，系統又過載，在兩個狀態之間擺盪。限流器與卸除器本身也會壞，Stripe 列出的部署注意事項中有三件：任何層級的例外都 fail open，讓限流器的錯誤不會讓 API 停擺；準備一個 kill switch 能整個關掉（見 [6.17 Feature Flag Governance](/backend/06-reliability/feature-flag-governance/) 的〈Kill switch 設計〉）；新的限流器先 dark launch（[Dark Launch](/backend/knowledge-cards/dark-launch/)），只記錄它會擋掉哪些請求而不真的擋。

被拒絕的請求會重試，重試又會加重過載。Amazon 描述了這個回饋迴圈：延遲超過客戶端的逾時，客戶端放棄並重送，伺服器同時處理已經沒人等的舊請求與新的重試，過載因此變成穩定狀態。Google SRE 的對策是重試預算：每個請求最多嘗試 3 次（含第一次），每個客戶端的重試比例不超過 10%。重試預算與重試風暴見 [Retry Budget](/backend/knowledge-cards/retry-budget/) 與 [Retry Storm](/backend/knowledge-cards/retry-storm/)。

降級（只回應部分功能或較舊的資料）是負載卸除之外的另一個選項，它保住的是「有回應」。Google SRE 提醒它的邊界：「under extreme overload, the service might not even be able to compute and serve degraded responses」。降級要有用，降級的那條路徑必須比正常路徑便宜，例如直接讀本地快取，而不是換一種算法重算。降級的設計責任見 [Degradation](/backend/knowledge-cards/degradation/)。

## 准入控制：虛擬等候室（virtual waiting room）、waitlist 與事前註冊

**准入控制**（[Admission Control](/backend/knowledge-cards/admission-control/)）決定誰能進入系統、什麼時候進入，負載卸除決定的是已經到達的請求要不要處理。准入控制把湧入的人留在受保護的路徑外面排隊，所以被擋下的使用者看到的是等候畫面，而不是錯誤。

SeatGeek 的虛擬等候室是准入控制的典型形狀（[AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/build-a-virtual-waiting-room-with-amazon-dynamodb-and-aws-lambda-at-seatgeek/)）。守門判斷的第一版跑在 Fastly 的 CDN 邊緣，在請求到達後端之前就決定它進受保護區，還是導去等候室。等候室有兩種模式，也可以先後組合：一種在開賣前把請求導到另一頁，到時間依預設的吞吐量放行；另一種讓受保護區只容納預設的並發人數，其餘依先到先服務（FIFO）排隊。開賣前產生的 access token 數量等於可售票數，所以受保護區的上限同時防止超賣。原文另外寫明兩件事：等候室可以在「a load spike, while more resources (EC2 instances) are being launched」時使用，替擴展爭取時間；等候室本身會遭受 DDoS，前面要放 DDoS 防護與 [WAF](/backend/knowledge-cards/waf/)。案例細節見 [SeatGeek：DynamoDB + Lambda 打造的虛擬等候室](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)。

事前註冊把准入判斷提早到開賣之前，前提是註冊本身有成本或驗證（付款卡、手機號碼），否則機器人一樣能大量註冊。Ticketmaster 的 Verified Fan 要求歌迷事先註冊，目的是「identifying real humans and weeding out bots」：超過 350 萬人註冊，約 150 萬人收到預售碼，其餘列入候補，只有通過驗證的人能進入佇列。Taylor Swift 巡演那一次，准入規則守住了，總流量卻沒有：「No one who wasn't verified was allowed to enter the queue, but the huge traffic hitting the site overall meant we had to slow down queues to keep them stable」，業者放慢部分場次、延後其他場次，約 15% 的互動出錯，包括預售碼驗證錯誤讓歌迷失去已放進購物車的票（[Ticketmaster, 2022](https://business.ticketmaster.com/business-solutions/taylor-swift-the-eras-tour-onsale-explained/)）。限量發售還有另一種准入方式是抽籤：把先到先得改成隨機抽選，搶快就沒有優勢，湧入分散到報名期；大量報名能提高中籤機率，所以抽籤同樣需要報名有成本或驗證這個前提。

Ticketmaster 這次開賣說明准入控制只決定誰能進佇列：沒通過驗證的人與機器人，請求照樣打在同一個網站上，佇列本身也要靠網站運作。所以准入控制之外還要能吸收總流量，兩者要分開設計：准入控制決定誰、什麼時候進到受保護的路徑（事前註冊在這一步篩掉機器人），總流量的吸收靠邊緣的快取、WAF 與〈負載卸除與限流的分工、請求的優先等級〉一節的負載卸除。

准入控制也可以直接寫進產品的發布方式。OpenAI 在 2023 年 3 月發布 GPT-4 時，公告裡先寫明「we expect to be severely capacity constrained」，ChatGPT 介面的 GPT-4 只給付費使用者並設使用上限，上限「depending on demand and system performance」隨時調整；API 走 waitlist 逐批邀請，「scale up gradually to balance capacity with demand」，預設的速率限制是每分鐘 4 萬個 token、200 個請求（[OpenAI, 2023，Wayback](https://web.archive.org/web/20230316235659id_/https://openai.com/research/gpt-4)）。同年 2 月推出的 ChatGPT Plus 把「General access to ChatGPT, even during peak times」列為付費的好處（[OpenAI, 2023，Wayback](https://web.archive.org/web/20230203001642id_/https://openai.com/blog/chatgpt-plus/)），等於把請求優先等級做成商業方案：尖峰時段免費使用者的優先度較低。這種做法適用於需求可以預期會超過容量、而產品允許使用者等待的情形。

## 體積型攻擊（DDoS）的處置：流量清洗與邊緣網路

體積型攻擊在網路層就塞滿了入口頻寬，負載卸除、優先等級與部署在自家機房或來源端的 WAF 都位在被塞滿的入口之後，攻擊流量在到達它們之前就已經佔滿頻寬。能處理的方式是把流量交給頻寬比攻擊量更大的網路，由對方在邊緣濾掉攻擊流量（流量清洗，scrubbing），再把乾淨的流量送回來。

GitHub 那次事件的處置順序是：17:21 偵測到入站與出站流量的比例異常；判斷其中一個機房的入站頻寬已超過 100 Gbps，決定把流量交給 Akamai；17:26 用 ChatOps 工具（在聊天室裡下指令觸發的自動化）撤回經由 transit 業者（把網路接上整個網際網路、按頻寬計價的上游網路業者）的 BGP 宣告，只經由 Akamai 宣告自己的網段，也就是改變網際網路對「GitHub 的位址該從哪條線路進來」的路由，路由在幾分鐘內收斂，Akamai 在邊界用存取控制清單濾掉攻擊；17:30 恢復。17:21 到 17:26 全站不可用，17:26 到 17:30 間歇不可用（[GitHub, 2018](https://github.blog/news-insights/company-news/ddos-incident-report/)）。

17:21 到 17:30 這九分鐘裡，人只做了一個決定：切換（17:34 GitHub 又撤回經由網際網路交換中心的路由，移走另外 40 Gbps，屬於恢復之後的後續處置）。其餘的條件都是事前就存在的：過去一年 GitHub 把 transit 頻寬擴大了一倍以上，Akamai 這個合作夥伴事前就已經在（原文稱 partners，沒有寫合約形式），撤回與宣告路由的指令已經寫進 ChatOps，偵測用的流量比例監控已經在跑。報告也寫明這些準備的邊界：「attacks like this sometimes require the help of partners with larger transit networks to provide blocking and filtering」，後續的改進方向是讓監控系統自動啟用清洗服務，縮短人做決定的時間。用 CDN 或雲端業者的邊緣網路承接所有入口流量，是讓這種切換平常就處於啟用狀態的做法（不走 HTTP 的協定，例如遊戲的 UDP 或 SSH，放不到 HTTP CDN 後面，要用 L4 代理（業者把 TCP 或 UDP 流量轉送回 origin），或 GitHub 這種 BGP 方式的網路層清洗；後者需要自有、能對外宣告的 IP 網段）。它的前提是攻擊者繞不過邊緣，也就是 origin 不被繞過：origin 的防火牆只放行邊緣業者的位址範圍、或改由 origin 主動往外連到邊緣的通道對外服務（[Outbound Tunnel](/backend/knowledge-cards/outbound-tunnel/)）、或用憑證驗證每一個回源請求，而且 origin 的位址不從歷史 DNS 紀錄、寄信標頭或沒經過邊緣的子網域外洩；否則攻擊會直接打 origin。站內還沒有專講 origin 被繞過的文章；[5.9 邊緣分發與靜態資源（CDN / Origin Protection）](/backend/05-deployment-platform/edge-cdn-static-distribution/) 的〈Origin Protection 的設計責任〉處理的是快取命中、回源控制與 origin 故障時的回退，不涵蓋 origin 被繞過。WAF 在其中負責的是應用層的規則，見 [WAF](/backend/knowledge-cards/waf/)。

## 擴展跟不上時的退路：panic mode、fast-fail 與分批上線

擴展與卸除都可能來不及，退路是事前建好、在這時接手的一組機制，目標是讓系統從「完全沒有回應」退到「慢但有回應」。

Slack 2021 年 1 月那次事故從掛掉退到降級，靠的是三個事前就存在的機制。負載平衡器有一個「panic mode」，大部分主機的健康檢查都失敗時，它不再只送給健康的主機，而是平均分配到所有主機；加上重試與 circuit breaker（下游服務持續失敗時暫停呼叫那個下游，避免把失敗擴散開來），到太平洋時間早上 9:15 左右，「Slack was slower than normal and error rates were higher, but by around 9:15am PST Slack was degraded, not down」。人工做的是停掉自動縮容、保住現有的服務容量，同時修復 provision-service、清掉沒建好的機器，讓可服務的主機數回到足夠的數量；panic mode 生效的前提，正是 web tier 還有足夠數量的正常主機。panic mode 保住的是有回應，不是每個請求都成功：在多數主機不健康時仍然送流量給它們，換來的是一部分請求失敗而不是全部請求被拒絕。Circuit breaker 的設計見 [Circuit Breaker](/backend/knowledge-cards/circuit-breaker/)。

佇列是另一個要事先決定的退路，決定的是過量的請求要排隊還是立刻失敗。Amazon 建議負載平衡器用 spillover 的設定，「which fast-fails instead of queueing excess requests」，超過容量的請求直接回失敗、不排隊（[Fail Fast](/backend/knowledge-cards/fail-fast/)），並限制請求在任何佇列裡停留的時間，過舊的請求直接丟掉（[Deadline](/backend/knowledge-cards/deadline/)）：客戶端早就逾時了，處理它只是浪費容量。和上游的回饋機制見 [Backpressure](/backend/knowledge-cards/backpressure/)。

准入控制一節的等候室也是退路：SeatGeek 原文把它列為新機器還在啟動時替系統爭取時間的工具。分批上線（先在部分地區上線，再擴到其他地區）則可以把退路提早到流量進來之前；這是本篇的讀法，Google 的原文沒有說 Niantic 分區上線是為了容量。Pokémon GO 在 2016 年先在澳洲與紐西蘭上線，15 分鐘內流量就「surged well past Niantic's expectations」，實際流量最後是原始目標的 50 倍、最壞估計的 10 倍；Niantic 在美國上線前一天找了 Google 的支援團隊，並在日本上線前升級叢集版本、換掉負載平衡器，美國上線時仍有穩定性問題（「Not everything was smooth sailing at launch!」），日本上線時新註冊數是美國的 3 倍而沒有事故（[Google Cloud, 2016](https://cloud.google.com/blog/products/gcp/bringing-pokemon-go-to-life-on-google-cloud)；案例見 [Niantic Pokémon GO：在 GCP 上承載 50 倍突發流量](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)）。先在小市場上線，等於用真實流量量出預測錯了多少，下一個市場上線前還有時間改。

## 事前建好的機制與當下能做的決定

把這幾個案例的處置並排，當下做的事分成兩種。一種是啟用或調整已經存在的機制：GitHub 決定切換到清洗業者，Slack 停掉自動縮容，Ticketmaster 放慢佇列、延後場次，OpenAI 在公告裡預告會依需求調整使用上限。另一種是修復：Slack 修好 provision-service、清掉沒建好的機器，AWS 工程師手動擴大 Transit Gateway 的容量；Slack 的修復花了兩個多小時，這段期間服務不可用，之後才退到降級。那些機制本身，包括交給更大邊緣網路的路徑、照形狀設計的偵測訊號、入口的請求優先等級、為關鍵請求預留的容量、等候室與事前註冊、量過的擴展反應時間與緩衝、panic mode 與 circuit breaker，都是在流量進來之前就建好、部署好的。

判斷一個機制屬於事前建好的機制，還是當下能做的決定，問的是：在過載正在進行時，要讓它生效，需不需要部署新的程式或新的設定、或簽一份新的合約。需要的，最好在流量來之前完成，因為過載的系統上，部署本身也可能失敗，Slack 那次連擴展都失敗了；業界把相關的性質叫 [Static Stability](/backend/knowledge-cards/static-stability/)：控制面（擴展用的 provision-service、雲端 API 這類負責變更系統的元件）失效時，資料面不需要做任何變更就能維持服務，Slack 擴展失敗正是控制面失效的例子。本篇的判斷標準比它寬，允許執行事前演練過的既有指令與改既有設定的值。只需要改一個既有設定的值、或只需要人做一個決定的，才能留到當下；分界在設定的欄位、作用路徑與權限是不是事前就存在並演練過：GitHub 撤回 BGP 宣告的 ChatOps 指令是事前寫好的，當下只是執行它，所以算當下的決定；當下才要新增一條規則或一條路徑，就屬於事前要建的機制。修復也發生在當下，而修復花的時間裡，服務只剩事前建好的退路撐得住的程度：Slack 在 panic mode 生效之前不可用，之後是降級。沒有事前機制時，當下仍然做得到幾件事，各有代價：在既有的擴展上限欄位調高數值，風險是那個值沒演練過；臨時把網域接到 CDN 或清洗業者後面，DNS 切換要時間生效，origin 的位址如果已經外洩，攻擊照樣直接打 origin；找業者手動擴容，取決於業者的支援安排：Slack 那次是 AWS 從自家監控發現封包遺失後手動擴大 Transit Gateway，Pokémon GO 則是 Niantic 主動找 Google 的支援團隊。改架構可以在兩波流量之間做，Pokémon GO 就是在美國與日本上線之間換掉負載平衡器。所以無預警的流量雖然無法預測時間，準備的方式和 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/) 相同，差別在 9.11 的準備時程對著一個日期，這篇列的機制要平常就處於可用狀態，並在演練（[Game Day](/backend/knowledge-cards/game-day/)）時實際啟用一次，確認切換的指令、權限與儀表板都還能用。

## 延伸閱讀：限流實作、可預期峰值、案例與事故處理

- 依呼叫者分配配額的限流演算法與實作：[Rate Limit 實作](/backend/09-performance-capacity/rate-limit-implementation/)，限流的對外契約見 [Rate Limit Contract](/backend/knowledge-cards/rate-limit-contract/)。
- 有日期可排的峰值、T-90 到 T-0 的準備時程與演練：[9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)。
- 擴展要依哪一個軸、無狀態的前提：[9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/)。
- 售票搶購的案例：[拓元 Tixcraft：售票搶購的瞬間爆量架構](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)。
- 這些機制落在短網址服務上的形狀（爆紅連結、建立路徑的機器人濫用、轉址網域的攻擊）：[0.25 短網址服務的瞬時大流量：爆紅連結、建立路徑的機器人濫用與轉址路徑的攻擊](/backend/00-service-selection/url-shortener-traffic-surge/)。
- 流量已經造成事故時的止血與降級：[8.3 止血、降級與回復策略](/backend/08-incident-response/containment-recovery-strategy/)；分級、溝通與事後檢討見 [08 事故處理模組](/backend/08-incident-response/)。
