---
title: "Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序"
date: 2026-10-27
description: "用 Gatling 實作效能 regression gate 時的判斷：assertion 對應哪一種判讀方法、OSS 怎麼做出相對門檻與跨次比較、預熱的請求怎麼處理、注入模型怎麼影響前後兩版的比較、Gatling 在 CI 的哪幾條路徑跑、要保存哪些執行條件，以及 gate 失敗時怎麼把誤判和真正的退化分開"
weight: 1
tags: ["backend", "reliability", "vendor", "gatling", "load-test", "release-gate"]
slug: "gatling-performance-regression-gate"
---

用 Gatling 做效能 regression gate 的人，要判斷的是這一版能不能過 release gate：這一版比基準版本慢了沒有、慢的幅度是否超出雜訊、要不要擋下。這篇整理這個判斷在 Gatling 上的做法：Gatling 的 assertion 對應 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/) 的絕對門檻、相對退化與統計顯著性裡的哪一種，OSS 怎麼做出另外兩種，以及 Enterprise 在這一點上換到什麼；assertion 的統計範圍、百分位數與錯誤率怎麼寫；OSS 版的 assertion 把 ramp-up 的請求也算進去的影響與排除方式；open 與 closed 兩種注入模型（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)）讓退化出現在不同的指標上；PR 與 nightly 各跑一份 simulation 時各自抓得到、抓不到哪一類退化；HTML report 之外還要記下哪些執行條件、存在哪裡，另一個人才判斷得了兩次結果比不比得了；gate 失敗時依序排除哪幾種誤判，才把差距歸給這一版的變更。baseline 的來源、門檻的設法與 variance 控制是 6.13 的內容，本篇只寫它們在 Gatling 上的做法。Gatling 的安裝、simulation 的完整 API 與各版本的升級指南在 [Gatling 官方文件](https://docs.gatling.io/)；同一個工具用來找受測服務飽和點、估算要加多少機器的寫法在 [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)。

## Gatling 在 regression gate 裡負責的環節

效能 regression gate 比較這一版與基準版本（baseline）在同一組負載下的延遲、錯誤率與吞吐量，退化超過門檻時擋下 release（[Release Gate](/backend/knowledge-cards/release-gate/)）。Gatling 用兩個名字區分它執行的內容：scenario 是一個虛擬使用者依序送出的請求與中間的停頓，也就是使用者流程；simulation 是一次執行的單位，包含 scenario、注入步驟（injection step，每秒或同時放進多少個虛擬使用者）與 assertion（執行結束時拿統計值比對門檻、決定 simulation 成敗的條件）。Gatling 在 gate 裡做兩件事：照 simulation 產生負載、記錄每一個請求的結果；執行結束時拿這一次的統計值比對 assertion，任一條不成立，這次 simulation 判為失敗（官方文件〈Assertions〉）。團隊在 Maven 或 Gradle 的建置裡執行 simulation 時，多半用各自的 Gatling plugin，plugin 把 simulation 的失敗轉成 build 失敗，CI 因此擋下這次合併。

assertion 拿這一次的統計值跟一個數字比，這個數字寫死時，它就是 6.13 的絕對門檻。相對退化（跟基準版本比慢了多少百分比）要拿到基準版本的值，OSS 有兩種做法：一種是參數化門檻，simulation 是一般的 Java、Kotlin 或 Scala 程式，載入時可以讀一份基準值的檔案或 CI 傳進來的參數，把 assertion 寫成 `lt((int) (baselineP95 * 1.10))` 這類形式（照語法推出、沒有實跑；延遲的門檻是整數毫秒，所以要轉型），換到的是不必另寫比較程式，付出的是基準值要有地方保存、而且每次接受新的基準時要更新；另一種是團隊另寫一支程式，讀這一次與基準版本那一次的量測、算出差距，下文稱它跨次比較的程式。跨次比較的程式要讀的量測，OSS 的 Gatling 沒有官方支援的機器可讀輸出：官方 FAQ 明寫不支援自行解析 `simulation.log`，它的格式沒有公開、隨時會變，3.13 起也不是純文字；HTML report 裡的統計檔同樣不是公開的介面。所以 OSS 的跨次比較改從受測服務那一端取量測：受測服務用 histogram 型的延遲指標（[Percentile](/backend/knowledge-cards/percentile/) 的〈設計責任〉），比較程式依這次與基準那一次的執行時間區間查詢，算出兩邊的百分位數與分佈。統計顯著性（兩組量測的分佈有沒有顯著差異）要的是多次執行的樣本或每個請求的延遲分佈，參數化門檻做不到，只能靠跨次比較的程式。Gatling Enterprise 的 Run trends 與 Run comparison 提供跨次比較的介面；在 Enterprise 的測試上設了 SLO 之後，simulation 裡的 assertion 不再評估，gate 的門檻改由 SLO 決定（官方文件〈Assertions〉）。三種做法的取捨看 gate 主要靠哪一種判讀：只拿絕對門檻當安全網時，寫死的 assertion 就夠用；要靠相對退化抓每次只慢一點點的漸進退化時，參數化門檻用最少的工作做得到；要做統計顯著性、或要讓 reviewer 在介面上翻歷次的趨勢時，OSS 的團隊要自己維護比較程式、受測服務的 histogram 指標與歷次結果的保存，這一段維護工作就是 Enterprise 替 regression gate 省下的部分。

## assertion 的寫法：統計範圍、百分位數與錯誤率

Gatling 的 assertion 由統計範圍、統計值與比較方式組成。範圍有三種：`global()` 統計整次 simulation 的全部請求，`forAll()` 對每一個請求各自統計，`details(...)` 只統計指定的 group 或 request。統計值有 `responseTime`（後面再接 `percentile(...)`、`max()`、`mean()` 這類）、`failedRequests`、`successfulRequests`、`requestsPerSec`。比較方式有 `lt`、`lte`、`gt`、`gte`、`between` 等。

```java
setUp(scn.injectOpen(rampUsersPerSec(1).to(50).during(60)))
  .protocols(httpProtocol)
  .assertions(
    // 整次執行的 p95 延遲低於 500 毫秒
    global().responseTime().percentile(95.0).lt(500),
    // scenario 裡命名為 checkout 的 group，失敗率低於 1%
    details("checkout").failedRequests().percent().lt(1.0)
  );
```

這段照官方文件〈Assertions〉列的語法組成，沒有實跑。`scn` 與 `httpProtocol` 是讀者自己在 simulation 裡定義的 scenario 與 HTTP 協定設定（受測服務的位址、共用的 header）。注入步驟的 `1`、`50`、`60`（每秒抵達的使用者從 1 升到 50、歷時 60 秒）與門檻的 `500`、`1.0` 都是佔位值；門檻從基準版本在同一個環境、同一份 simulation 量到的結果取，取法見 6.13 的〈Baseline 設定〉；`checkout` 是 scenario 裡用 `group("checkout")` 包起來的那一段流程的名字。兩條 assertion 各自擋一類退化，寫法背後的考量如下：

- **百分位數寫成 `percentile(95.0)`**：Gatling 另有 `percentile1` 到 `percentile4` 的寫法，它們指的是 `gatling.conf` 裡設定的四個百分位數，預設是第 50、75、95、99。有人改了設定檔，同一行 assertion 量的就換成另一個百分位數，而 assertion 的文字沒有改，code review 看不出 gate 量的百分位數換了。
- **門檻涵蓋尾端延遲與錯誤率，不只平均值**：少數請求變慢很多時，平均延遲幾乎不動，而使用者感受到的是那些慢的請求（[Percentile](/backend/knowledge-cards/percentile/)）。只寫 `mean()` 的 gate 會讓這類退化通過。
- **業務關鍵的流程各自設門檻**：`global()` 的統計由請求量最大的 endpoint 主導，一個每秒幾千次、回應很快的健康檢查 endpoint，會把結帳流程的退化平均掉。把關鍵流程用 `group` 包起來、用 `details(...)` 各自設門檻之後，gate 失敗時，失敗的那一條 assertion 也直接指出是哪一個流程退化。關鍵流程以外的請求只受 `global()` 那幾條門檻管。

## ramp-up 期間的請求與量測區間

OSS 版的 assertion 統計整次 simulation 的請求，沒有指定時間區間的參數；排除 ramp-up 與 ramp-down 時間的設定只有 Gatling Enterprise 有（官方文件〈Assertions〉）。ramp-up 期間受測服務在預熱：JIT 還沒編譯熱路徑、cache 還沒填滿、連線池還在建立連線，延遲比穩態高；執行 Gatling 的機器，也就是施壓端（load generator），自己的 JVM 也在預熱。這些請求算進 assertion 時，量到的 p95 與 p99 會隨 ramp-up 佔整次執行的比例而變，兩次執行只要這個比例不同，受測服務沒有改變也會量到不同的值。這是 6.13〈Variance 控制〉表裡 cold start 那一列在 Gatling 上的樣子。

OSS 版排除預熱有三種做法，代價不同：

- **預熱與量測用不同的請求名稱或 group**：預熱階段的請求用另一個名字，assertion 只用 `details(...)` 指向量測的那一組。採用這個做法時，每一條 assertion 都要從 `global()` 改成 `details(<量測的那一組>)`，上面範例裡 `global().responseTime().percentile(95.0)` 那一條也一樣：用 `global()` 統計時，Gatling 會把預熱的請求一起算進去。代價是 scenario 要依階段區分請求的名字，而且少了整次執行的總覽門檻。
- **先跑一次只用來預熱的 simulation**：CI 先跑預熱用的 simulation、不看它的結果，再跑量測用的 simulation。代價是 CI 的時間變長，而且只有在兩次執行之間受測服務的狀態（cache、已建立的連線）保留下來時才有效。
- **從受測服務那一端依時間區間計算**：團隊已經有跨次比較的程式、而受測服務用 histogram 型的延遲指標時，比較程式只查 ramp-up 結束之後那一段時間的指標計算統計值，assertion 只留粗的安全網。代價是受測服務要有 histogram 指標，而且比較程式要知道每一次執行的 ramp-up 在什麼時候結束（注入步驟的時間加上執行的開始時間）。Gatling 自己的 `simulation.log` 官方不支援自行解析，不能拿來做這件事。

三種都不採用時，寫 simulation 的人讓每一次執行的注入步驟完全相同，ramp-up 的比例就固定，預熱的影響變成兩版共有的偏移，前後兩版的比較仍然成立。這個前提有兩件事要成立：兩版每次執行前都重新部署、從同一種冷啟動的狀態開始（基準版本跑在剛部署的環境、這一次跑在已經熱好的環境時，偏移不是共有的）；兩版的預熱行為相同（這一版的變更改到 cache 的結構、啟動時載入的資料或熱路徑時，預熱的變化會被讀成穩態的退化，或穩態的退化被預熱的改善抵掉，這時要改用前面三種排除方式之一重量）。代價是門檻不能直接拿 production 的延遲目標當值，要從同一份 simulation 的基準版本結果取。

## 注入模型對前後兩版比較的影響

regression gate 比較前後兩版時，兩次執行要用同一種注入模型與同樣的參數，兩種模型的差別在於退化出現在哪一個指標上（機制見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉）。open model（`rampUsersPerSec`、`constantUsersPerSec`）下，每秒抵達的使用者數由注入步驟決定，新版本變慢時延遲的 assertion 會失敗，每秒請求數跟著注入步驟走、不隨受測服務變慢而下降，所以〈assertion 的寫法〉那段 `rampUsersPerSec` 的範例不設吞吐量門檻。closed model（`constantConcurrentUsers`、`rampConcurrentUsers`）下，變慢的時間有一部分表現成每秒請求數下降、而不是延遲上升，只設延遲門檻的 gate 會讓這一部分通過，所以 closed model 的 gate 要加上吞吐量的門檻：

```java
setUp(scn.injectClosed(constantConcurrentUsers(50).during(600)))
  .protocols(httpProtocol)
  .assertions(
    global().responseTime().percentile(95.0).lt(500),
    // 吞吐量的下限：基準版本量到的每秒請求數，減去重跑時量到的波動範圍
    global().requestsPerSec().gte(110.0)
  );
```

這段同樣照官方文件〈Assertions〉與〈Injection〉的語法組成，沒有實跑；`50`（同時在線的虛擬使用者數）、`600`（秒）、`110.0` 是佔位值。吞吐量的門檻不能直接設成基準版本量到的值：每秒請求數本身也有雜訊，門檻等於基準值時，大約一半的執行會因為隨機的波動低於它而失敗，所以下限是基準值減去同一個版本重跑時每秒請求數的波動範圍（取法見〈gate 失敗時的排查順序〉的雜訊範圍那一項）。production 流量屬於 open 型的服務（多數面向公眾的 API）用 open model，量到的延遲退化比較接近使用者會遇到的退化；呼叫端數量固定的服務（固定 worker 數的批次程式）用 closed model，量到的吞吐量下降對應的就是批次跑完的時間變長。

## PR 與 nightly 兩種 simulation 的分工

[6.1 CI pipeline](/backend/06-reliability/ci-pipeline/) 把 CI 分成每次 push 跑的 fast path、merge request 跑的 slow path 與排程跑的 scheduled path，6.13 沿用這三個名字，把 micro benchmark 放在 fast path、end-to-end 的效能測試放在 slow path 與 scheduled path。Gatling 對著部署好的受測環境送請求，屬於 end-to-end 的效能測試，所以不放在 fast path：fast path 的時間預算與「不碰外部依賴」的條件，容不下一次要部署環境、還要維持幾分鐘負載的執行。PR 跑的 simulation 對應 slow path，nightly 或 release branch 跑的 simulation 對應 scheduled path，兩份 simulation 抓的退化不同。

PR 跑的 simulation 負載低於飽和點（[Saturation Point](/backend/knowledge-cards/saturation-point/)）、只涵蓋關鍵流程，執行時間落在 slow path 的預算內；它抓的是一次變更造成的明顯延遲退化。它抓不到的有兩類。一類是要長時間維持負載才出現的退化：記憶體洩漏、連線池慢慢耗盡、GC 暫停隨堆積的物件變長。另一類是每個請求的資源成本變高：一個請求多用了三成 CPU、多配置了記憶體，請求的延遲主要花在等 I/O（資料庫、下游呼叫）時，在低負載下 CPU 還不是瓶頸，延遲幾乎不變，要到接近飽和時才看得出來；請求的處理本身就是 CPU 密集時，多出來的 CPU 時間直接加長延遲，PR 的 simulation 看得到。後一類要嘛在 gate 裡另外記錄受測服務每個請求的 CPU 與記憶體配置量、拿它跟基準版本比，要嘛交給 nightly 在接近飽和的負載下量。6.13 把相對退化定為 slow path 的主要判讀，PR 的 simulation 用〈Gatling 在 regression gate 裡負責的環節〉寫的參數化門檻就做得到；統計顯著性要多次執行的樣本，放在 nightly。nightly 跑的 simulation 時間長、流程完整，加上長時間維持負載的 soak 階段，抓的是與時間有關的退化，也替統計顯著性累積歷次的結果。

兩份 simulation 共用同一份 scenario 程式碼，各自定義注入步驟與 assertion：scenario 只寫一份，流程改動時兩份 simulation 量的仍然是同一個流程。兩份也共用同一組 feeder（餵測試資料給虛擬使用者的資料來源，帳號、商品編號這類），gate 只量得到 feeder 的資料走到的路徑：feeder 只有少數幾個熱門商品時，讀資料庫的長尾路徑兩版都沒有被請求到，這一版的變更若改到那條路徑，gate 對它沒有訊號。feeder 的分佈怎麼對上 production，寫在 [Gatling 在容量探測的用法](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/) 的 feeder 那一節。CI 跑 Gatling 的環境要跟其他工作隔開：staging 上同時有別的 QA 流量或排程工作在跑時，它們的負載混進受測服務的延遲與吞吐量，前後兩版的差距落在這些雜訊裡（6.13〈Variance 控制〉的 shared runner 鄰居效應那一列）。

## HTML report 與執行條件的保存

Gatling 每次執行結束後產生一份 HTML report，內容有延遲的百分位數分佈、每個 request 與 group 的統計，以及隨時間變化的 Users start rate（每秒開始的虛擬使用者數）、同時在線使用者數、每秒請求數與每秒回應數，還有錯誤的明細（官方文件〈Reports〉）。CI 的 job 把這份 report 存成 build artifact，gate 失敗時 reviewer 打開它，找出是哪一個 group、在哪一段時間退化。report 是給人讀的，裡面的統計只有 `gatling.conf` 設定的那幾個百分位數，也不是公開的機器介面；跨次比較的程式讀的是受測服務那一端的 histogram 指標。report 與證據都要存在保留期限不受 CI 控制的位置（物件儲存、測試結果資料庫），受測服務的指標也要保留到下一次比較用得到的時候：CI 平台的 artifact 有保留天數，監控系統的指標也有保留期限，基準版本那一次的資料到期刪掉之後，下一次 gate 就沒有基準版本的結果可比，而這件事不會報錯。

report 只記錄這一次的結果；要讓另一個人判斷兩次結果比不比得了，CI 的 job 在同一份證據裡另外記下三組欄位。一組是 [6.2 load test](/backend/06-reliability/load-testing/)〈Load test 結果的證據留存〉列的最小欄位：workload model 版本、測試環境、saturation point、throughput ceiling、主要瓶頸歸因、headroom ratio、退化模式分類與測試日期。一組是這次執行的條件：simulation 的版本（commit）、注入步驟、feeder 的來源與產生日期、Gatling 的版本、施壓端的台數與規格、受測服務的副本數、受測資料庫的資料量（或每次重建時用的 seed 版本）、下游哪些服務是 mock、沒有 mock 的下游各是哪一個版本。一組是比較的另一邊：這次跟哪一次基準執行比（那一次的執行編號或 commit），以及跨次比較的程式或參數化門檻用的基準值檔是哪一個版本。這些欄位跟著 gate 的判定交給下游的方式，照 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) 的〈Handoff 欄位〉。

## gate 失敗時的排查順序

Gatling 的 gate 失敗時，有三種誤判會讓差距看起來像這一版的退化：兩次執行的條件不同、施壓端飽和、差距落在雜訊之內。下面的執行條件、施壓端與雜訊範圍三項依序排除這三種誤判，退化的流程與幅度那一項是三種都排除之後、把差距歸給這一版的那一步。排除誤判的三項，順序依兩件事排：排除那種誤判要花多少力氣，以及前一項沒排除時後一項的讀數是否還能解讀。

1. **兩次執行的條件**：比對證據裡兩邊記下的條件，simulation、注入步驟、受測環境、副本數、施壓端配置、沒有 mock 的下游版本有任一項不同，差距就不能歸給這一版的變更。容易漏的三種：feeder 過期（基準版本與這一次相隔幾天時，token 或商品過期，請求回錯誤，`failedRequests` 的 assertion 失敗）；受測資料庫的資料量漂移（gate 每次執行都寫入訂單、帳號，資料表一路變大，查詢慢慢變慢，樣子跟漸進退化相同，每次執行前重建資料庫才排除得了）；staging 上的鄰居流量（證據裡記得到時算條件不同，記不到時只能算進下一項的雜訊）。基準版本那一次本身是離群值（剛好偏快的一次）時，之後每一版都像退化，基準的選法見 6.13 的〈Baseline 設定〉。這一項只要比對紀錄，花的力氣最少。
2. **施壓端的資源**：施壓端的 CPU、記憶體、GC 暫停、網路頻寬、檔案描述元或來源埠用完時，量到的延遲包含施壓端自己的時間（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)），gate 的結果不代表受測服務。open model 下有兩個不必另外收集指標的訊號：Users start rate 低於設定值，代表施壓端送不出設定的負載；Gatling 量到的延遲跟受測服務入口量到的延遲差距變大，代表多出來的時間花在施壓端或網路上。GC 暫停與頻寬用完只加長延遲、不減少送出的使用者數，Users start rate 正常也排除不了它們，要靠施壓端的資源指標或上面那個延遲差距才看得到。這兩種都拿不到時（CI 沒有收集施壓端的資源指標、受測服務入口也量不到延遲），這一項無法排除，這次 gate 的結果是無結論：雜訊範圍與退化幅度的讀數無法歸給受測服務，這次失敗不足以當成退化的證據，通過也不足以當成沒有退化的證據，處置是補上施壓端的指標收集後重跑。
3. **差距與雜訊的範圍**：CI 在建立 baseline 時把同一個版本重跑幾次（次數與樣本量的取法見 6.13 的〈Regression 判讀方法〉），這次 gate 用到的每一個統計值（p95、p99、錯誤率，closed model 的 gate 還有每秒請求數）的波動範圍就是它的雜訊範圍。退化的幅度小於這個範圍時，這次的差距還不能當成退化的證據；門檻不能設得比這個波動範圍更窄，所以 6.13〈Variance 控制〉縮小雜訊之後門檻要重算，雜訊沒縮小之前門檻設得比它窄，gate 會反覆誤報，團隊開始略過它。雜訊範圍大到超過想抓的退化幅度時（例如每次波動 15%，而想抓 5% 的退化），單次執行的比較抓不到這個幅度，絕對門檻也只擋得下大於雜訊的退化；要抓 5% 的退化有兩條路：照 6.13〈Variance 控制〉縮小雜訊，或在 scheduled path 用統計顯著性（同一個版本多跑幾次、基準版本與候選版本在同一個環境交錯執行），樣本數夠時抓得到比單次雜訊小的退化。
4. **退化的流程與幅度**：執行條件、施壓端與雜訊範圍都排除之後，差距屬於這一版的變更。HTML report 與 `details(...)` 的 assertion 指出是哪一個流程。退化落在有自己 `details(...)` 門檻的關鍵流程時，那一條 assertion 失敗本身就是擋下 release 的依據，原因的定位方法在 6.13〈退化定位與行動〉的 profiling diff 與 commit bisect。失敗的是 `global()` 的門檻、而退化落在關鍵流程以外的請求時，判斷看這些請求在服務的效能預算（[Performance Budget](/backend/knowledge-cards/performance-budget/)）裡有沒有額度：預算有涵蓋它們，這次退化照樣擋下；預算沒有涵蓋，可能是這些請求本來就不需要擋，也可能是新的 endpoint 還沒補進預算，兩種都要回到 6.13 的〈Regression 判讀方法〉決定門檻的範圍與值。在那之前若決定放行，放行的人、理由與這次的差距要跟著 gate 的判定寫進證據（6.23〈Handoff 欄位〉），代價是這一部分的退化會累積到下一次調整門檻；受稽核的服務沒有這筆紀錄時，release 的效能證據就少了一段。

同樣看到 p99 變慢，用 Gatling 做容量探測時，排查從施壓端與實際抵達的使用者數查起，要判斷的是受測服務哪一項資源先飽和，順序與這裡不同，寫在 [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/) 的排查順序那一節。

## 相關章節與工具頁：gate 的方法、load test 的 baseline 與 k6 的 threshold gate

- [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)：baseline 的 production percentile、CI benchmark history 與 load test 結果三種來源，絕對門檻、相對退化與統計顯著性三種判讀方法，以及 variance 控制；本篇的 assertion 與排查順序都建立在它上面。
- [6.2 load test](/backend/06-reliability/load-testing/)：訂定 gate 拿來比對的 baseline 與 saturation point，以及 load test 結果要留存的欄位。
- [k6：Threshold CI Gate 與 Scenario 設計](/backend/06-reliability/vendors/k6/threshold-ci-gate-and-scenario-design/)：同一類 gate 換成 k6 時，threshold 與 executor 的寫法。
