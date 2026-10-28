---
title: "JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序"
date: 2026-10-28
description: "用 JMeter 找飽和點時的判斷：thread group 與 timer 量的是哪一種負載模型、Open Model Thread Group 的逐級加壓、從 dashboard 判讀 knee、施壓端與 TLS 連線的失真、分散施壓，以及容量結論要附的條件"
weight: 1
tags: ["backend", "performance", "capacity", "vendor", "jmeter", "load-test"]
slug: "jmeter-capacity-probing"
---

用 JMeter 做容量探測的人，要判斷的是目前的配置在延遲目標內處理得了多少負載、先用完的是哪一項資源、要加什麼。這篇整理這個判斷在 JMeter 上的做法，分成產生負載、讀結果、排除失真與寫結論幾組。

產生負載的部分：JMeter 在 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 ramp-up 測試裡負責哪一段；JMeter 內建與 plugin 提供的幾種 thread group 與 throughput timer，各自固定了 [Little's Law](/backend/knowledge-cards/little-law/) 裡的哪一個變數（同時在線的使用者數、到達率，或每個使用者的速率上限），選的模型跟 production 流量不同時，飽和點會量在哪個方向；用 Open Model Thread Group 的排程寫出 9.4 的倍數加壓與把 knee 附近切細的小增量加壓，呼叫端數量固定的服務改用 Concurrency Thread Group 逐級加同時在線數。

讀結果的部分：從 HTML dashboard 的幾張隨時間變化的圖，換算出受測服務處在延遲平穩的線性區、延遲開始不成比例上升的 knee point，還是回應跟不上抵達的 cliff，以及 dashboard 的 Statistics 表把所有級混在一起時怎麼取出單一級的數字。

排除失真的部分：執行 JMeter 的機器（施壓端，load generator）要先排除的 GUI mode、listener、JVM heap 與 GC，以及 thread group 的種類怎麼決定連線是否沿用、每次抵達都重做 TLS handshake 時量到的上限為什麼屬於 TLS 終結那一層；單台送不出需要的負載時，remote mode 的 controller 收結果怎麼成為新的瓶頸、Backend Listener 與合併 JTL 兩種取得結果的方式、CSV 資料檔怎麼分發；HTTP 以外的 sampler（JDBC、JMS）讓容量結論涵蓋了哪些依賴、又繞過了應用程式的哪一段。

寫結論的部分：量完的結果要記下哪些條件才能寫成容量結論，以及延遲上升或吞吐量停滯時依序查哪幾件事。飽和的定義、ramp-up 的方法與 CPU、記憶體、磁碟、網路、連線池、外部 API 配額這幾個資源的判讀是 9.4 的內容，本篇只寫它們在 JMeter 上的做法。JMeter 的安裝、test plan 的元件設定、`.jmx` 的維護方式與 plugin 的安裝在 [Apache JMeter 官方文件](https://jmeter.apache.org/usermanual/index.html) 與 [jmeter-plugins.org](https://jmeter-plugins.org/)；同一個工具接進 CI、擋下效能退化的寫法在 [JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/)。

## JMeter 在容量探測裡負責的環節

容量探測要量出受測服務在延遲與錯誤率目標之內處理得了的最大負載（[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈概念定位〉；9.4 另把 knee point 當成設計容量的上限），以及到達那個值時哪一項資源先用完（9.4〈Resource saturation 的六個維度〉）。JMeter 的 test plan（存成 `.jmx` 檔）由幾類元件組成：thread group 決定有多少個 thread（JMeter 用一個 thread 代表一個虛擬使用者）在什麼時間執行它底下的流程；sampler 是流程裡送出的一個請求（HTTP、JDBC、JMS 等）；timer 在 sampler 之前插入停頓；listener 處理每一筆結果（sample result）。thread 跑完一次 thread group 底下的全部流程稱為一輪 iteration。JMeter 在容量探測裡做兩件事：照 thread group 與 timer 的設定產生逐級升高的負載，把每一筆 sample 的開始時間、耗時、連線時間、成功與否寫進結果檔（JTL）。

找 knee point（延遲開始隨負載不成比例上升的那一級負載，[Saturation Point](/backend/knowledge-cards/saturation-point/)）要用到兩邊的資料：JMeter 的結果記錄每一級負載下延遲怎麼變、處理完的請求數與抵達數的差距，受測服務的資源指標記錄是哪一項資源在排隊。只看 JMeter 的結果找得到 knee 在哪一級，判斷不了 knee 為什麼落在那一級。JMeter 的 assertion 在這裡只把個別 sample 標成失敗，不用來決定這次執行成功與否：容量探測本來就要把負載加到 knee 以上，延遲超過目標是預期內的結果。

## thread group 與 throughput timer 各自固定的負載變數

[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 那張卡把負載工具產生請求的方式分成兩種：open model 固定到達率 λ，跟受測服務回應得多快無關；closed model 固定虛擬使用者的總數 N，每個使用者等到回應才送下一個。JMeter 的元件分屬兩種模型，而名字分不出來：Throughput Shaping Timer 名字裡是 throughput、設定的是每秒請求數，它能維持多高的到達率，取決於同一個 thread group 給了多少個 thread。下表的右欄是每個元件固定的變數，來源是 [官方 Component Reference](https://jmeter.apache.org/usermanual/component_reference.html) 與 [jmeter-plugins.org](https://jmeter-plugins.org/) 的各元件頁：

| 元件                                                | 來源                                                  | 固定的變數                                                                         |
| --------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Thread Group                                        | 內建                                                  | thread 數 N（closed）                                                              |
| Concurrency Thread Group                            | plugin                                                | 同時在線的 thread 數 N（closed），依排程逐級加，少了就補                           |
| Open Model Thread Group                             | 內建（5.5 起，官方標實驗性）                          | 到達率 λ（open），每次抵達建立一個新 thread、跑一輪就結束                          |
| Arrivals Thread Group                               | plugin                                                | 到達率 λ（open），arrival 定義成一輪 iteration 的開始；Concurrency Limit 是上限    |
| Throughput Shaping Timer                            | plugin                                                | 每秒請求數的目標，只能延後 thread；thread 給夠時接近 open，不夠時跟著減壓          |
| Constant Throughput Timer、Precise Throughput Timer | 內建（搭配 Thread Group 或 Concurrency Thread Group） | 在固定的 thread 數上設一段期間內 sample 數的上限（pacing），受測服務變慢時跟著減壓 |

Thread Group 與 Concurrency Thread Group 是 closed model。Concurrency Thread Group 的頁面寫它的用途是維持同時在線的數量，執行中的 thread 不夠時再啟動新的；它控制的是同時在線數 N，不是到達率。受測服務變慢時，每個 thread 送出下一個請求的時間往後延，實際的請求率跟著下降，所以用它壓面向公眾、使用者各自獨立抵達的服務時，延遲目標內的到達率會被估高，飽和點找在比實際更高的位置（推導在 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈可觀察訊號與例子〉）。呼叫端數量固定的服務（固定 worker 數的批次程式、連線池大小固定的內部呼叫方）屬於 closed 型流量，用它量才對得上 production。

Open Model Thread Group 與 Arrivals Thread Group 是 open model：抵達的時刻由排程決定，現有的 thread 都在等回應時，下一次抵達照樣照時送出；兩者建立 thread 的方式不同。Open Model Thread Group 每一次抵達建立一個新的 thread，那個 thread 跑完一輪 iteration 就結束；原始碼的說明寫明 thread 依需要建立、跑完就結束，而且 thread 的總數沒有上限（`OpenModelThreadGroup.kt`）。Arrivals Thread Group 在所有現有的 thread 都忙著跑 iteration 時才建立新的 thread，有空閒的 thread 就交給它跑下一次抵達（jmeter-plugins.org 的頁面）。

Arrivals Thread Group 的頁面另外提醒，到達率固定而服務變慢時同時在線數會一直增加，所以它有 Concurrency Limit 當上限，避免施壓端的記憶體用完；碰到這個上限之後，新的抵達要等現有的 thread 空出來，負載又變回 closed，排程上的到達率沒有送出去。這個上限的估法照 Little's Law：預期 knee 附近的到達率乘以一輪 iteration 的時間（含 timer 的停頓），再留餘裕給 knee 之後延遲變長的那幾級。餘裕依這次要量到的最高那一級決定：那一級的到達率乘以一輪 iteration 可能拉長到的時間；一輪最長不會超過各 sampler 的逾時設定加總再加上停頓，用這個值算出的是上限，記憶體容得下時就用它。量完要確認 thread 數沒有碰到 Concurrency Limit。Open Model Thread Group 沒有這個上限，服務變慢時 thread 數會一直增加，要靠施壓端的記憶體與 heap 的監看發現。

Throughput Shaping Timer 用排程設定每秒請求數，頁面自己的說明是 timer 只能延後 thread，thread 不夠時到不了目標的 RPS；頁面給的 thread 數估法是目標 RPS 乘以最長的回應時間（Little's Law 的 L = λW），並建議搭配 Concurrency Thread Group 與 `__tstFeedback` 函式，讓 thread 數依目標自動補足。thread 數給得夠時它的行為接近 open model；受測服務變慢、需要的 thread 數超過給的數量時，它跟 pacing 一樣減壓：每個 thread 仍然等到回應才送下一個。它匯出的 `<元件名>_cntDelayed` 這個 JMeter 屬性是正在等待的 thread 數，頁面寫明低於 1 代表 thread 不夠、到不了目標的 RPS；頁面寫的讀法是 `__P` 函式或 JSR223 元件裡的 `props.get("<元件名>_cntDelayed")`，例如在流程裡加一個 JSR223 元件，用 `log.info` 把這個值寫進 `jmeter.log`（這個寫法沒有實跑）。不加這個元件時，讀者拿得到的訊號是 dashboard 的 Hits per second：它低於排程的 RPS，代表 thread 不夠。

Constant Throughput Timer 與 Precise Throughput Timer 是 pacing：它們只在既有的 thread 上插入長度會變的停頓，讓吞吐量接近設定值，不建立 thread。設定的單位是一段期間內的 sample 數：Constant Throughput Timer 是每分鐘的 sample 數，Precise Throughput Timer 是 Target throughput（sample 數）除以 Throughput period（秒）。Constant Throughput Timer 的 Calculate Throughput based on 決定這個值分給誰：this thread only 是每個 thread 各自的速率，總吞吐量跟著 active thread 數成正比；all active threads in current thread group 與 all active threads 把設定值當成整個 thread group 或全部 thread group 的總量，分給目前在跑的 thread，另有 shared 的變體以任何一個 thread 上一次執行的時間來算停頓（官方 Component Reference）。它限制的是哪一種速率，依 timer 放的位置而定：官方文件寫明 timer 作用於同層的每一個元素與它們底下的元素，放在 thread group 底下時，範圍內每一個 sampler 送出之前都經過它，限制的是 sample 的速率，一輪 iteration 有 k 個 sampler 時，每秒完成幾輪流程是設定值除以 k；放在一輪流程的第一個 sampler 底下時（官方對 Precise Throughput Timer 建議的位置，例如在流程開頭放一個 dummy sampler、把 timer 放在它底下），每一輪只在開頭停頓一次，限制的是 iteration 開始的速率。官方文件替兩者都寫了限制：受測服務處理不了、或 thread 不夠時，吞吐量會低於設定值；Precise Throughput Timer 那一節還寫「in many cases, Open Model Thread Group would be a better choice」。pacing 讓請求率在受測服務還快的時候穩定在設定值，讀起來像 open model，而服務變慢時它跟 closed model 一樣減壓（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉講 pacing 的那一段）。兩者的差別在送出的間隔：官方文件寫 Constant Throughput Timer 收斂到設定的速率而間隔偏向等距，Precise Throughput Timer 依 Poisson 分佈排定抵達的時刻，抵達有時密集、有時稀疏，比較接近 production 的隨機抵達。

從表裡選元件的依據是 production 流量的模型，判斷的方法在 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈可觀察訊號與例子〉：看送出請求的一方是否等到回應才送下一個。這一步選錯時，後面每一級的讀數都還是正確的量測，量到的卻是另一種流量下的飽和點，報告上看不出來。

## 用 Open Model Thread Group 的排程寫出逐級加壓

[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈Ramp-up 測試方法〉從平常時段的流量起按倍數加壓（1x、2x、4x、8x），每一級維持 5 到 10 分鐘看穩態。Open Model Thread Group 的排程是一串指令：`rate(...)` 設定到達率，`random_arrivals(...)` 是一段時間，這段時間前後的 `rate` 不同時線性升降、相同時維持，`pause(...)` 是一段沒有新抵達的時間。倍數加壓寫成：

```text
// 預熱：2 分鐘從每秒 0 升到 50
rate(0) random_arrivals(2 min) rate(50/sec)
// 每一級維持 5 分鐘；級與級之間用 1 分鐘線性升到下一級（前一級的兩倍）
random_arrivals(5 min) rate(50/sec)
random_arrivals(1 min) rate(100/sec)
random_arrivals(5 min) rate(100/sec)
random_arrivals(1 min) rate(200/sec)
random_arrivals(5 min) rate(200/sec)
random_arrivals(1 min) rate(400/sec)
random_arrivals(5 min) rate(400/sec)
// 排程一結束 thread group 就中斷所有 thread，留 2 分鐘讓最後抵達的流程跑完
pause(2 min)
```

這段排程照官方文件〈Open Model Thread Group〉的語法組成，沒有實跑。`rate(0)` 沒有寫單位，是官方文件寫明的省略：rate 是 0 時可以不寫時間單位，寫成 `rate(0/sec)` 也是同一個值。數字都是佔位值：起點 50 取 production 平常時段每秒開始的使用者流程數（[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 的〈Traffic shape 的五個維度〉），其餘各級是它的倍數。結尾的 `pause` 對應官方文件的說明：排程走完時 thread group 立刻中斷 thread，並建議在排程最後加一段 `pause` 讓 thread 安全結束。沒有這一段時，最後一級還在等回應的 sample 被中斷，多半記成失敗，混進最後一級的讀數（推論，沒有實跑）。

`rate` 的單位，官方文件寫成每秒請求數，而一次抵達跑的是一輪 iteration：原始碼裡這個 thread group 的 controller（`OpenModelThreadGroupController.kt`）在第一輪跑完之後就把自己標成完成，註解寫明每個 thread 目前只跑一輪。thread group 底下有好幾個 sampler 時，每秒送出的請求數是 rate 乘以一輪的 sampler 數；確認的方法是跑一級固定的 rate，比對 dashboard 的 Hits per second（每秒開始的請求數）是否等於這個乘積。`jmeter.save.saveservice.subresults` 是預設的 `true` 時，重導與 embedded resources 這類子結果也逐列寫進 JTL，Hits per second 會高於這個乘積，比對時把子結果另計。後面每秒請求數的換算都依賴這個結果。

倍數加壓以少數幾級涵蓋好幾倍的範圍，用來找出 knee 落在哪兩級之間；找到之後，從那兩級中較低的一級起用小增量把那一段切細。官方文件給了用 `__groovy` 函式產生逐級排程的寫法，套到 knee 落在每秒 200 與 400 之間的情形：

```text
rate(0) random_arrivals(2 min) rate(200/sec) random_arrivals(5 min) rate(200/sec)
${__groovy((1..5).collect { "random_arrivals(1 min) rate(" + (200 + it * 40) + "/sec) random_arrivals(5 min) rate(" + (200 + it * 40) + "/sec)" }.join(" "))}
pause(2 min)
```

這段同樣照官方文件的語法組成、沒有實跑。`(1..5)` 是切成的段數，`200` 是起點那一級，`40` 是每一級加的量，等於兩級的差除以段數（（400 − 200）÷ 5）；三個數都是佔位值，依倍數加壓的結果填。官方文件寫明排程只在測試開始時計算一次，所以用函式產生的排程在執行中途不會變。

`random_arrivals` 讓抵達的間隔隨機分佈，不是等距；文件裡等距的 `even_arrivals` 標著還沒實作。production 的抵達多半不是等距的，同一秒內有時多、有時少，受測服務對短暫的湧入敏感時（連線池小、佇列短），隨機抵達量到的 knee 比較接近 production。thread group 另有 Random Seed (change from 0 to random) 這個欄位，0 代表每次的抵達時刻都不同；同一次探測要跑兩次互相比對時，填同一個非零值，兩次的抵達時刻才相同。

級與級之間的 1 分鐘線性升高，讓受測服務的連線池與施壓端的 JVM 不必一次承接突然多出來的抵達；不升高、一次跳上去時，下一級開頭一兩分鐘的延遲混著這段過渡。1 分鐘是佔位值，這裡沒有比較其他長度。

兩次執行之間，受測服務要先回到加壓前的資源基線再跑下一次：倍數加壓多半會越過 cliff，留下積壓的佇列與耗盡的連線池，接著跑的小增量加壓會量到上一次的殘留。

呼叫端數量固定的服務照 closed model 量，用 Concurrency Thread Group：Target Concurrency 是最後一級的同時在線數，Ramp Up Time 與 Ramp-Up Steps Count 把它分成幾級逐級加上去，Hold Target Rate Time 是最後一級的維持時間（欄位名照 jmeter-plugins.org 的頁面）。原始碼（casutg plugin 的 `ConcurrencyThreadStarter`）在開始的那一刻就放進第一級，每一級的長度是 Ramp Up Time 除以 Ramp-Up Steps Count，每一級加 Target Concurrency 除以 Ramp-Up Steps Count 個 thread；Ramp Up Time 的最後一段已經是 Target Concurrency，所以最後一級實際維持「Ramp Up Time 除以 Ramp-Up Steps Count」再加上 Hold Target Rate Time。照 9.4 每一級都維持 5 分鐘時，Ramp Up Time 設成 5 分鐘乘以 Ramp-Up Steps Count，Hold Target Rate Time 設 0；Hold 設成 5 分鐘時，最後一級是 10 分鐘。時間的單位由 Time Unit 欄位決定，設定畫面的預設是 minutes。這個換算讀自原始碼，沒有實跑；跑一次之後在 Active Threads Over Time 上確認每一級的長度與 thread 數。closed model 的讀法在〈從 dashboard 判讀 knee point〉講 closed model 的那一段。

## 從 dashboard 判讀 knee point

`jmeter -n -t <plan>.jmx -l <result>.jtl -e -o <dir>` 在 CLI mode 執行 test plan，把每一筆 sample 寫進 JTL，測完產生 HTML dashboard；`-g <result>.jtl -o <dir>` 只從既有的 JTL 產生 dashboard（官方 [Getting Started](https://jmeter.apache.org/usermanual/get-started.html)）。dashboard 的 Statistics 表每個 sampler 一列，加上一列 Total，每一列都統計整次執行的 sample，倍數加壓的每一級都混在裡面，那一列的 p99 不屬於任何一級。所以判讀 knee 不讀 Statistics 表，讀隨時間變化的圖，或替每一級另外產生一份 dashboard：

```bash
# 只取某一級穩態的那幾分鐘（略過級與級之間的升高），產生這一級自己的 dashboard
jmeter -g probe-run.jtl -o report-level-240/ \
  -Jjmeter.reportgenerator.start_date=20261028143000 \
  -Jjmeter.reportgenerator.end_date=20261028143500
```

這條指令照官方〈Generating Report Dashboard〉的設定名組成，沒有實跑。`probe-run.jtl` 是這次執行寫出的 JTL，`report-level-240/` 是輸出目錄（要是空的或不存在）；兩個日期是那一級穩態的開始與結束，格式是 `jmeter.reportgenerator.date_format` 的預設 `yyyyMMddHHmmss`，時區要跟 JTL 裡的時間戳記一致（產生 dashboard 的機器跟執行測試的機器時區不同時，官方文件要求格式加上 `zzz` 寫明時區），從排程推算，或從 Active Threads Over Time 那張圖讀出每一級開始的時刻。這樣產生的 Statistics 表才是單一級的 p99。這張表的百分位數把失敗的 sample 也算進去，而 Response times Percentiles Over Time 只算成功的回應；受測服務開始很快地回錯誤時，失敗的 sample 把 Statistics 表的 p99 拉低，knee 看起來往後移。所以判讀 knee 的 p99 用 Percentiles Over Time 那張圖、或只取成功的 sample；Statistics 表的 p99 只在那一級的錯誤率接近 0 時跟它相同。隨時間變化的圖預設每一分鐘一個點（`jmeter.reportgenerator.overall_granularity`，預設 60000 毫秒，官方寫明不能低於 1000），每級 5 分鐘只有五個點，看級內的趨勢時要把它調小。

open model 下判讀用到的圖與換算：

- **Active Threads Over Time** 是同時在線的 thread 數。照 Little's Law 等於到達率乘以一個 thread 跑完一輪的時間，這段時間包含 timer 的停頓；到達率固定時，停頓的長度不變，同時在線數上升代表請求在受測服務裡花的時間變長了。停頓遠比請求的延遲長時，同時在線數只多一點點，圖上看不出來，所以它只當輔助訊號。
- **Hits per second** 依每一筆 sample 的開始時間分到每一秒（原始碼 `HitsPerSecondGraphConsumer` 以開始時間取時間桶），所以它是每秒開始的請求數。open model 下它跟著排程走，受測服務變慢時不會下降，只用來確認負載是否照排程送出：穩態下等於到達率乘以一輪的 sampler 數（〈用 Open Model Thread Group 的排程寫出逐級加壓〉確認過的換算）。這個乘積的前提是每一輪都跑完全部 sampler：流程裡有依回應分支的 If Controller，或 sampler 出錯時的動作設成 Start Next Thread Loop 時，受測服務回錯會讓一輪提早結束，Hits per second 跟著下降，而施壓端並沒有少送抵達。子結果同樣讓 Hits per second 高於這個乘積，要另計。確認到達率要比對的是一輪第一個 sampler 的開始次數，這個 sampler 要每一輪都執行、會寫出 sample，而且不是 Flow Control Action 或 Transaction Controller（官方〈Generating Report Dashboard〉寫明 Hits per second 略過 Transaction Controller 的結果）。用 `-Jjmeter.reportgenerator.sample_filter=<第一個 sampler 的 label>` 另外產生一份 dashboard（`sample_filter` 是官方〈Generating Report Dashboard〉的設定，值是一個要跟整個 label 相符的正規表示式，label 裡有 `?`、`.`、`(`、`[` 這類字元時用 `\Q…\E` 包起來；整段相符也順帶排除了那個 sampler 的子結果；這個用法沒有實跑），那一份的 Hits per second 就是每秒開始的 iteration 數，應該等於排程的到達率。
- **Total Transactions Per Second** 與 **Response codes per second** 依 sample 的結束時間分桶（`TotalTPSGraphConsumer`、`CodesPerSecondGraphConsumer`），是每秒完成的請求數；Total Transactions Per Second 分成功與失敗兩條線，Response codes per second 分每一種回應碼。每秒完成的請求數低於每秒開始的請求數，代表抵達的比處理完的多。
- **Response times Percentiles Over Time** 只統計成功的回應，失敗的請求不在這張圖裡。

換算之後，每一級的穩態對應受測服務的幾種狀態：

- **線性區**：每秒完成的請求跟得上換算值，錯誤率接近 0，延遲的百分位數在各級之間幾乎不變。
- **knee**：完成的請求仍然跟得上、錯誤率仍然接近 0，但 p99 的增幅開始遠大於到達率的增幅，p50 還穩。Saturation Point 卡給的量化訊號是「負載增加 10%、延遲增加 100%」；倍數加壓每一級的到達率加一倍，這個比例要在小增量加壓下套用，倍數加壓只用來找出最後一個 p99 持平的級與第一個 p99 明顯上升的級。
- **cliff**：Total Transactions Per Second 上每秒完成的請求低於換算值（也低於 Hits per second 上每秒開始的請求），Active Threads Over Time 上的同時在線數在同一級之內持續上升，Percentiles Over Time 上的延遲隨時間一直往上走，接著出現逾時與錯誤；之後服務呈現的是變慢、請求失敗、無回應還是程序終止，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)。
- **失敗比例上升**：回應數（含失敗）跟得上，但 Response codes per second 上 429、503 這類回應的比例隨級數上升。受測服務在過載時直接拒絕，失敗的回應很快回來，百分位數圖只統計成功的請求，看起來像線性區；判讀看的是失敗的比例。例如結帳 API 從每秒 200 那一級起 503 開始增加，而 Percentiles Over Time 上成功回應的 p99 一直持平，這時 knee 還沒出現，錯誤率卻已經超過目標；容量結論停在錯誤率超標之前的那一級（〈量完之後寫成容量結論要記下的條件〉的取法）。

[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈Ramp-up 測試方法〉列成 knee 訊號的「throughput 從線性成長轉成 sub-linear」，在 open model 下對應的是 cliff。open model 下吞吐量在受測服務處理得了的範圍內跟著設定的到達率走，到達率加一倍、每秒完成的請求也加一倍；sub-linear 在 dashboard 上表現成每秒完成的請求低於換算值，那已經是 cliff 那一種狀態。所以 open model 下 knee 的訊號是更早出現的 p99 上升。

closed model（Thread Group、Concurrency Thread Group）的讀法不同：Active Threads Over Time 是設定值，不會隨服務變慢而上升，要看的是成功的每秒請求數（Total Transactions Per Second 的成功那一條）與延遲。逐級增加同時在線數時，成功的每秒請求數與同時在線數以相同的比例增加、延遲持平是線性區；成功的每秒請求數仍在增加、但增幅小於同時在線數的增幅，p99 開始上升的那一級是 knee，那一級的同時在線數是 closed 型服務的飽和點；成功的每秒請求數不再隨同時在線數增加時，已經越過處理得了的上限，多出來的同時在線數只是在受測服務裡排隊，延遲隨之上升（9.4〈Ramp-up 測試方法〉的 sub-linear 訊號在 closed model 下就是這個增幅的落差）。

dashboard 與 GUI 的 Aggregate Report 算百分位數的公式不同，官方文件寫明分佈很散或 sample 很少時兩者的差距最明顯，要兩邊一致時把 `backend_metrics_percentile_estimator` 設成 `R_3`。容量探測的各級要用同一種算法比較，結論裡記下用的是哪一種。

knee 落在哪一級之後，同一段時間對照受測服務的資源指標，照 9.4〈Resource saturation 的六個維度〉找出先飽和的資源，定位的流程在 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。

## 施壓端的檢查：GUI、listener、heap 與 TLS handshake

判讀 dashboard 之前，先確認施壓端在整段測試中沒有飽和：施壓端飽和時，dashboard 上的停滯與延遲上升跟受測服務飽和的樣子相同，每一個數字都混著施壓端自己的時間，資源的分類與確認方法在 [Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)。官方〈Best Practices〉寫明受測服務回應得越快，JMeter 要做的事越多，所以施壓端的上限跟受測服務的速度有關，同一台施壓端打不同的服務，上限不同。JMeter 上有幾件事會先佔掉施壓端的資源，或讓量到的上限屬於另一個元件：

- **GUI mode**：官方寫明 GUI mode 只用來建立測試腳本，負載測試要用 CLI mode（`-n`）。GUI 的 View Results Tree 這類 listener 把 sample 留在記憶體裡顯示，〈Best Practices〉要求負載測試時不開，只在寫腳本時除錯用。
- **listener 與結果檔**：每一個 listener 都要處理每一筆 sample。CLI mode 用 `-l` 寫 JTL 之後，test plan 裡的其他 listener 可以全部停用；〈Best Practices〉另外建議結果檔用 CSV 而不是 XML、只存需要的欄位。
- **JVM heap 與 GC**：JMeter 預設以 1 GB 的 heap 執行（啟動腳本的 `HEAP`，預設 `-Xms1g -Xmx1g`），預設的 GC 是 G1（`GC_ALGO`；5.6.3 的啟動腳本設 `MaxGCPauseMillis=100`，官方〈Getting Started〉仍寫 250）。open model 的同時在線數隨受測服務變慢而增加，thread 越多、heap 用得越多，GC 暫停也越頻繁，而暫停的時間算進那段時間內每一筆 sample 的延遲。heap 要給多少依 test plan 與 thread 數而定，官方沒有給數字；量法是開 GC log 跑一級，看暫停的頻率與長度在各級之間是否跟著上升。GC log 用 JVM 的 `-Xlog:gc*:file=<路徑>` 開啟（Java 9 以後的寫法），經由啟動腳本的 `JVM_ARGS` 環境變數傳進去，這個寫法沒有實跑。
- **連線的重用與 TLS handshake**：thread group 的種類決定每個請求是否要重做 TLS handshake，量到的上限可能因此屬於終結 TLS 的那一層，機制、各 thread group 的行為與判讀寫在清單之後的幾段。

連線與 TLS handshake 的機制：官方 Component Reference 寫明每個 thread 用自己的 SSL context，所以一個 thread 關掉連線的時機，決定了下一個請求是否要重做 TLS handshake。handshake 主要耗用受測端終結 TLS 那一層的 CPU（負載平衡器、反向代理或應用程式本身）。每個請求都重做 handshake 時，探測量到的 knee 可能落在那一層的 CPU 上，而不在應用程式上。握手的延遲與 CPU 成本怎麼來、重用連線攤平多少，以及 k6、Gatling、Locust 各自什麼時候建新連線，見 [TLS Handshake（TLS 握手）的成本與連線重用](/backend/knowledge-cards/tls-handshake-cost/)。

各 thread group 關掉連線的時機與這篇的確認程度：

| thread group             | 連線在什麼時候關掉                                                                                                                                                                                                              | 確認程度                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Thread Group             | Same user on each iteration（5.2 起，預設勾選）勾選時下一輪 iteration 沿用同一條連線；取消勾選時每一輪之間開新連線，這時才套用 `httpclient.reset_state_on_thread_group_iteration`（預設 `true`，關閉已開的連線、重設 SSL 狀態） | 官方 Component Reference 與 properties reference；原始碼 `HTTPHC4Impl` 在勾選時忽略那個屬性 |
| Concurrency Thread Group | 設定畫面有 Same User On Each Iteration（預設勾選），推論勾選時跟 Thread Group 一樣沿用連線                                                                                                                                      | 欄位與預設值讀自新版 casutg plugin 的原始碼（`AdditionalFieldsPanel`）；連線行為是推論      |
| Open Model Thread Group  | thread 跑完一輪就結束，結束時關閉這個 thread 的所有連線，所以每一次抵達都新建一條連線、做一次 handshake；那個屬性與選項都改不了                                                                                                 | 原始碼（`OpenModelThreadGroup.kt` 的說明、`HTTPHC4Impl` 的 thread 結束處理），沒有實跑      |
| Arrivals Thread Group    | 把下一次抵達交給空閒的 thread；設定畫面同樣有 Same User On Each Iteration（預設勾選），連線是否沿用不確定                                                                                                                       | 欄位與預設值讀自新版 casutg plugin 的原始碼；連線行為沒有實跑確認                           |

判讀用 Connect Time Over Time 這張圖：官方〈Glossary〉寫明 Connect Time 包含 SSL handshake 的時間，它隨級數上升、而受測服務入口量到的應用程式延遲沒有跟著上升時，上升的時間花在建立連線上。設定依 production 用戶端的連線方式選：production 的使用者每次都是新連線時（短暫造訪、每次重新登入的流量），Open Model Thread Group 每次抵達一次 handshake 的形狀接近 production；production 的用戶端會長時間重用連線時（內部服務之間的呼叫、App 長時間開著的連線），Open Model Thread Group 量到的 knee 可能落在 TLS 終結那一層，結論寫的是 TLS 終結的上限。這種流量又要用 open model 量時，Open Model Thread Group 給不出這種負載形狀，可以改用 Arrivals Thread Group（連線行為要先實跑確認）或在結論裡寫明這個限制。

施壓端能送出的上限要量，不沿用別的機器量到的數字：讓同一台施壓端用同樣的排程打一個幾乎不做事的 endpoint（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/) 的〈可觀察訊號與例子〉），或用官方提到的 JavaTest sampler（不需要網路，可以看出 JMeter 在這台機器上的最大吞吐量），把量到的上限跟這次要送的到達率比較。量到的上限要明顯高於要送的到達率：打真實服務時，每個回應要解析的內容比空 endpoint 多，open model 下同時在線的 thread 也隨受測服務變慢而增加，施壓端的負擔比打空 endpoint 時高。差距要多大沒有通用的數字，所以這個比較只用來排除明顯不夠的施壓端；探測期間仍照同一張卡的方法，持續比對 JMeter 量到的延遲與受測服務入口量到的延遲，差距隨級數變大時施壓端已經在加上自己的時間。

## 分散施壓：remote mode 的結果回傳、Backend Listener 與資料檔

單台施壓端送不出需要的到達率時，要把負載分到幾台施壓端。JMeter 的 remote mode 由一台 client（官方文件也稱 controller）控制多台執行 `jmeter-server` 的節點，用 `-r`（使用設定檔裡的節點清單）或 `-R <host1>,<host2>` 指定節點（官方〈Remote Testing〉）。用在容量探測時有幾件事要先處理：

- **每個節點跑完整的 test plan**：官方寫明 JMeter 不在節點之間分配負載，1000 個 thread 配 6 個節點就是 6000 個 thread。Open Model Thread Group 的到達率同樣乘上節點數（照這句推論）：test plan 裡寫的排程是每個節點各自的到達率，要合計每秒 R 個抵達時，每個節點的排程填 R 除以節點數。
- **client 收結果會成為瓶頸**：listener 的結果從各節點送回 client 寫檔。官方寫明節點多時 client 本身與它的網路連線都可能過載，要確認 client 沒有過載。回傳方式由 client 上的 `mode` 屬性決定：預設是 `StrippedBatch`（去掉成功 sample 的回應內容、累積到門檻再送）；`Standard` 是每一筆同步送回，官方寫明 thread 要等結果送回才繼續，會壓低節點的最大吞吐量；`Statistical` 只送彙總，各筆 sample 的其他欄位會遺失，事後無法從 JTL 重算每一級的百分位數。client 的 CPU、網路與 heap 要跟各節點一起收集。
- **不經 client 的兩種做法**：官方〈Best Practices〉提到可以在多台機器上各自用 CLI mode 執行、事後合併各台的結果檔，這樣 client 不在結果的路徑上，代價是各台要自己同時啟動、時鐘要同步，合併之後每一級的開始與結束才對得齊。另一種是 Backend Listener：官方寫明它是非同步的 listener，把彙總指標（各 sampler 的次數、平均、百分位數，以及 active thread 數）送到 Graphite 或 InfluxDB，能跟受測服務的資源指標放進同一個 Grafana、同一條時間軸，Load Generator Saturation 卡要求的「施壓端與受測服務的指標放在同一個時間軸上」可以這樣做到。它的百分位數是每個節點自己用滑動視窗（`backend_metrics_window`，預設最近 100 筆 sample）算好的值，幾個節點的 p99 不能相加或平均（[Percentile](/backend/knowledge-cards/percentile/) 的〈設計責任〉），所以跨節點的延遲從合併後的 JTL 算，或從受測服務那一端讀（前提是受測服務的延遲指標用 histogram 型、量測點跟延遲目標的量測點一致）。
- **資料檔不會自動分發**：官方寫明 client 會把 test plan 送到各節點，CSV 這類資料檔不會，要事先放到每個節點的對應目錄；每個節點要用唯一的 id 時，把資料分成幾份檔案。各節點拿同一份檔案時，一次性的資料（只能用一次的 token、有唯一約束的欄位）互相衝突，各節點同時走同一批 key 又讓快取命中率比 production 高。
- **節點的版本要一致**：官方要求所有節點用完全相同的 JMeter 版本與相同的 Java 版本；plugin（Concurrency Thread Group、Throughput Shaping Timer 這類）沒有隨 test plan 送出，也要每個節點各裝同一版。版本不一致時，各節點產生負載的方式不同，量到的容量無法重現。

施壓端的機器要跟受測服務分開放，官方〈Remote Testing〉也提醒把節點放在受測服務同一個網段，降低網路對結果的影響；幾個節點走同一個 NAT 出口時，來源埠與頻寬仍然共用，節點數加了，施壓端的上限沒有跟著加。

## 多 protocol sampler 讓容量結論涵蓋的依賴範圍

JMeter 的 sampler 涵蓋 HTTP 以外的 JDBC、JMS、TCP 等 protocol，同一份 test plan 可以同時對應用程式與它的依賴施壓。容量結論因此要寫明負載經由哪一條路徑到達每一個依賴：經由應用程式的 HTTP sampler 打到資料庫的負載，帶著應用程式的連線池、查詢模式與快取；JDBC sampler 直接打資料庫的負載，繞過了這些。直接打資料庫的 sampler 量到的是資料庫在這組查詢與連線數下的容量，不能直接寫成應用程式的容量。

JDBC sampler 的連線數由 JDBC Connection Configuration 決定，官方建議的 Max Number of Connections 是 0，代表每個 thread 各有一個只放一條連線的 pool；所以 thread 數就是打到資料庫的連線數，open model 的同時在線數上升時，資料庫的連線數跟著上升。原始碼（`DataSourceElement`）把這種每個 thread 一個的 pool 存在 Java 的 ThreadLocal 裡、測試結束（testEnded）時才關閉；Open Model Thread Group 用一個會重用底層 Java thread 的執行緒池執行每一次抵達，所以連線數會停在同時在線數的峰值附近，同時在線數下降時不跟著釋放（從原始碼推論，沒有實跑）。production 裡應用程式的連線池有固定的上限，資料庫看到的連線數不會隨流量一直增加；兩者對不上時，探測可能先用完資料庫的連線上限或每條連線的記憶體，那是 production 不會出現的瓶頸。JMS sampler 同樣是把訊息直接送進 broker，量到的是 broker 與消費端在這個送入速率下的表現，不包含應用程式產生訊息的那一段。

依賴是共用的時候（同一個資料庫服務好幾個應用程式），直接打依賴的 sampler 適合用來量依賴本身還剩多少餘裕，把結果當成應用程式容量的上界之一；要量應用程式的容量，負載從應用程式的入口送，依賴的指標從依賴那一端讀。資料的分佈同樣影響結果：CSV Data Set Config 預設 Recycle on EOF 是 `true`、所有 thread 共用同一份檔案，檔案裡 key 的種類數少於 production 在同一段時間會請求到的 key 時，同一批 key 被反覆請求，快取命中率比 production 高，容量被估高；資料量與 key 的分佈要從 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)〈從 production log 抽 workload model〉取，包括很少被存取的長尾。

## 量完之後寫成容量結論要記下的條件

容量探測的結論寫成條件句：「在這個配置下、p99 低於多少毫秒的條件下，處理得了每秒多少個使用者流程，先飽和的是哪一項資源，距離飽和點還剩多少餘裕（[Headroom Budget](/backend/knowledge-cards/headroom-budget/)）」（[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈概念定位〉、〈Saturation 文件化：容量地圖〉）；closed 型服務的單位換成同時在線的使用者數。9.4 把 knee point 當成設計容量的上限，所以結論裡的「處理得了」取三者中最低的那一級：knee 之前最後一個 p99 持平的級、p99 還在延遲目標內的最後一級、錯誤率還在錯誤率目標內的最後一級。只看 knee 與延遲時，受測服務在過載時快速回錯誤的情形會被漏掉，因為延遲的百分位數只算成功的回應。這個結論是 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的輸入。條件句的每一項都要能回溯到這次執行：

- **負載模型**：用的是哪一種 thread group 與 timer、排程或逐級的同時在線數、隨機種子、一輪 iteration 的 sampler 數，以及確認到達率有送足的依據（Arrivals Thread Group 沒碰到 Concurrency Limit；Throughput Shaping Timer 的 Hits per second 對得上排程的 RPS，有用 JSR223 元件記下 `cntDelayed` 時，它沒有低於 1）。
- **施壓端**：JMeter、Java 與 plugin 的版本（Open Model Thread Group 標實驗性，版本變了行為可能跟著變）、heap 與 GC 設定、節點數與規格、remote mode 的 `mode` 或改用的取得結果方式、百分位數的算法。
- **連線與 protocol**：thread group 的種類與 Same user on each iteration 的值（取消勾選時另記 `httpclient.reset_state_on_thread_group_iteration` 的值）、哪些依賴經由應用程式、哪些由 JDBC 或 JMS sampler 直接施壓、JDBC 的連線數設定。
- **資料**：CSV 的來源、產生日期、key 的種類數、各節點怎麼分。
- **受測環境**：配置與版本、測試期間的副本數（探測時固定副本數、關掉 autoscaler，量到的才是單一配置的容量）、負載打在 CDN 還是 origin、下游哪些服務是 mock。

讀容量結論的人（做容量規劃或審查報告的工程師）從結論回到這些條件，判斷得了一次結果是受測服務的容量訊號，還是測試設計造成的偏差（closed model 壓 open 型流量、施壓端飽和、每次抵達都重做 handshake、直接打依賴而繞過連線池、資料偏差）。欄位的組織方式照 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 的〈Evidence 欄位〉。

## 延遲上升或吞吐量停滯時的排查順序

JMeter 的容量探測量到延遲上升或吞吐量停在某個值時，有幾種成因會讓讀數不能直接當成受測服務的容量：施壓端飽和、負載模型沒有照設定送出、資料過期、連線建立的成本混進延遲。下面的順序依一件事排：前一項沒有排除時，後一項的讀數是否還可用。

1. **施壓端與 client 的資源**：各節點與 remote mode 的 client 的 CPU、heap 與 GC 暫停，test plan 是否留著 GUI listener，施壓端的錯誤訊息是否出現 `Too many open files` 或 `Cannot assign requested address`；比對 JMeter 量到的延遲與受測服務入口量到的延遲，差距隨級數變大代表多出來的時間花在施壓端或網路上。施壓端飽和時，每一個數字都混著施壓端的時間，後面每一項都不能用；closed model 下施壓端飽和的樣子（成功的每秒請求數停住、延遲上升）跟受測服務的飽和點相同，這一項沒排除時，量到的飽和點可能是施壓端的上限。
2. **負載是否照模型送出**：open model 下比對一輪第一個 sampler（每一輪都執行、會寫出 sample、不是 Flow Control Action 或 Transaction Controller 的那一個）的每秒開始次數與排程的到達率（只保留那個 label 的 dashboard 上的 Hits per second，做法與 label 的寫法在〈從 dashboard 判讀 knee point〉講 Hits per second 的那一項），再看 Active Threads Over Time 是否停在 Concurrency Limit 或 Throughput Shaping Timer 給的 thread 數；停住代表到達率沒有送出去，負載退回 closed model，這段讀數裡的 knee 會被估高。全部 sampler 的 Hits per second 低於換算值、而第一個 sampler 的開始次數對得上排程時，到達率有送出去，少掉的請求來自錯誤讓一輪提早結束，這是受測服務回錯的訊號，交給資料有效性那一項與錯誤率的判讀。closed model 下核對 Active Threads Over Time（或 JTL 的 `allThreads` 欄位）是否達到這一級設定的 thread 數；沒達到時，這一級量到的不是設定的同時在線數。remote mode 下另外確認每個節點的排程填的是總量除以節點數。這一項排在資料與連線之前，因為送出的負載不對時，錯誤比例與連線時間的變化都對不上設定的負載。
3. **資料的有效性**：錯誤裡有大量 401、404 時，從加壓的起點那一級起就以大致固定的比例出現的，多半是 CSV 的資料過期；比例隨級數上升的，比較可能是負載造成的（認證服務飽和、replica 的延遲讓剛寫入的資料讀不到），那是容量的訊號。錯誤開始增加的時點對齊某個時鐘時間（token 到期）或 CSV 繞完一圈的時點，成因在資料；對齊級與級的交界，成因在負載。這一項排在連線成本之前，因為過期資料造成的失敗回應很快回來，受測服務沒有做完整的工作，同一級的延遲與資源用量都被壓低，連線時間佔延遲的比例跟著變大，下一項的判讀會偏向連線成本。
4. **連線建立的成本**：Connect Time Over Time 隨級數上升、而受測服務入口的應用程式延遲持平時，上升的時間花在連線與 TLS handshake；對照 thread group 的種類、Same user on each iteration 的值與 production 用戶端的連線方式（〈施壓端的檢查：GUI、listener、heap 與 TLS handshake〉的連線那一項），判斷這次量到的上限屬於 TLS 終結那一層還是應用程式。
5. **knee 所在的一級與先飽和的資源**：施壓端、負載模型、資料與連線成本都排除之後，用單一級的 dashboard 或隨時間變化的圖找出 knee 所在的那一級，再對照受測服務的資源指標找出先飽和的資源。knee 之前最後一個 p99 持平的級、延遲目標內的最後一級與錯誤率目標內的最後一級，三者中最低的那一級寫進容量結論（〈量完之後寫成容量結論要記下的條件〉）。
6. **量到的容量與 production 經驗的差距**：量到的容量高於 production 實際觀察到的值時，查 CSV 的 key 分佈與快取命中率、直接打依賴的 sampler 是否繞過了應用程式的連線池、下游 mock 的回應時間，它們讓容量被估高；沒有 production 的值可比時，結論註明「未經 production 校準」。這一項在 knee 之後查，因為要先有 knee 與先飽和資源的結論，才知道高估了多少。

同樣看到 p99 變慢，用 JMeter 做 regression gate 時，排查先分辨這次的變慢是測試條件造成的誤判、還是這一版的效能退化了，順序與權重跟這裡不同，寫在 [JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/)。同一個模組裡用 Gatling 做容量探測時，注入步驟、report 的四張圖與 OSS 版不支援分散施壓的處理方式在 [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)。

## 相關章節：飽和點的方法、workload model 與壓測工具選型

- [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：飽和的定義、ramp-up 的方法與 CPU、記憶體、磁碟、網路、連線池、外部 API 配額的判讀，本篇的加壓寫法與 knee 判讀都建立在它上面。
- [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)：排程的到達率、CSV 資料的分佈與脫敏從這裡取。
- [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)：找到 knee 之後，定位是哪一項資源、哪一段程式先飽和。
- [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：把容量結論與 headroom 換算成預期峰值要的副本數。
- [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)：JMeter 與 k6、Gatling、Locust 在腳本表達能力、協議支援、規模能力與 CI 整合上的比較。
- [JMeter → k6：k6 不是 JMeter 的「script 版本」、是 VU model 取代 thread model](/backend/09-performance-capacity/vendors/k6/migrate-from-jmeter/)：把既有的 JMeter test plan 搬到 k6 時，thread group 怎麼對應到 k6 的 executor。
