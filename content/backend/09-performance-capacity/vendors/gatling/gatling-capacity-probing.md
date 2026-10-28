---
title: "Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序"
date: 2026-10-27
description: "用 Gatling 找受測服務飽和點時的判斷：逐級加壓的兩種注入寫法與各自適用的階段、report 的四張圖怎麼換算成受測服務的狀態、施壓端要先排除的資源與 OSS、Enterprise 的分散施壓、feeder 資料怎麼讓容量估高、讀寫高峰錯開時的 scenario 寫法，以及容量結論要附的執行條件"
weight: 1
tags: ["backend", "performance", "capacity", "vendor", "gatling", "load-test"]
slug: "gatling-capacity-probing"
---

用 Gatling 做容量探測的人，要判斷的是目前的配置在延遲目標內處理得了多少負載、先用完的是哪一項資源、要加什麼。這篇整理這個判斷在 Gatling 上的做法：Gatling 在 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 ramp-up 測試裡負責哪一段；用 open model（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)）的注入步驟（injection step）寫出逐級加壓，Gatling 的 stairs 每一級加固定的量、跟 9.4 建議的倍數加壓怎麼搭配；探測之前受測環境要先固定的條件（副本數、負載打在哪一端）；從 HTML report 的 Users start rate、每秒請求數、每秒回應數與同時在線使用者數，判讀受測服務處在延遲平穩的線性區、延遲開始不成比例上升的 knee point（也就是飽和點），還是回應跟不上抵達的 cliff，以及服務直接回錯誤時的讀法；執行 Gatling 的機器（施壓端，load generator）有哪些資源要先確認沒有用完，單台送不出需要的負載時，OSS 與 Enterprise 各自怎麼分散施壓；feeder 的資料分佈怎麼讓快取命中率偏離 production、把容量估高，以及資料要怎麼脫敏；讀取與寫入的高峰錯開出現時怎麼寫成幾個 scenario；量完的結果要記下哪些條件才能寫成容量結論；延遲上升或吞吐量停滯時依序查哪幾件事。飽和的定義、ramp-up 的方法與 CPU、記憶體、磁碟、網路、連線池、外部 API 配額這幾個資源的判讀是 9.4 的內容，本篇只寫它們在 Gatling 上的做法。Gatling 的安裝、simulation 的完整 API 與各版本的升級指南在 [Gatling 官方文件](https://docs.gatling.io/)；同一個工具接進 CI、擋下效能退化的寫法在 [Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/)。

## Gatling 在容量探測裡負責的環節

容量探測要量出受測服務在延遲與錯誤率目標之內處理得了的最大負載（[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈概念定位〉），以及到達那個值時哪一項資源先用完（9.4〈Resource saturation 的六個維度〉）。Gatling 用兩個名字區分它執行的內容：scenario 是一個虛擬使用者依序送出的請求與中間的停頓；simulation 是一次執行的單位，包含 scenario、注入步驟與 assertion。Gatling 在這裡做兩件事：照 simulation 的注入步驟產生逐級升高的負載，記錄每一段時間開始的使用者數、送出的請求數、收到的回應數（分成功與失敗）與延遲分佈。

找 knee point（延遲開始隨負載不成比例上升的那一級負載，[Saturation Point](/backend/knowledge-cards/saturation-point/)）要用到兩邊的資料：Gatling 的 report 記錄每一級負載下延遲怎麼變、成功的回應跟不跟得上抵達，受測服務的資源指標記錄是哪一項資源在排隊。只看 Gatling 的 report 找得到 knee 在哪一級，說不出它為什麼在那裡。Gatling 的 assertion（執行結束時拿統計值比對門檻、決定 simulation 成敗的條件）在這裡不決定這次執行成功或失敗：容量探測本來就要把負載加到 knee 以上，延遲超過目標是預期內的結果。

## 用 open model 的注入步驟寫出逐級加壓

找飽和點時用哪一種注入模型，跟著 production 流量的來源走（判斷的方法在 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈可觀察訊號與例子〉）。面向公眾的服務用 open model；用 closed model 量的話，延遲目標內的到達率會被估高，飽和點找在比實際更高的位置。呼叫端數量固定的服務（固定 worker 數的批次程式、連線池大小固定的內部呼叫方）照同一張卡〈設計責任〉對 closed 型流量的做法：逐級增加同時在線的使用者數（`rampConcurrentUsers`、`incrementConcurrentUsers`），report 的讀法在〈從 report 判讀 knee point〉講 closed model 的那一段。這一節只寫 open model 的寫法，它的注入步驟放在 `injectOpen(...)` 裡，同一條注入鏈只能用 open model 的步驟。

[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈Ramp-up 測試方法〉的 ramp-up 從平常時段的流量起按倍數加壓（1x、2x、4x、8x），每一級維持 5 到 10 分鐘看穩態。Gatling 有兩種寫法對應：

```java
// 倍數加壓：每秒抵達的使用者，每一級是前一級的兩倍，各維持 5 分鐘
scn.injectOpen(
  constantUsersPerSec(50).during(Duration.ofMinutes(5)),
  constantUsersPerSec(100).during(Duration.ofMinutes(5)),
  constantUsersPerSec(200).during(Duration.ofMinutes(5)),
  constantUsersPerSec(400).during(Duration.ofMinutes(5))
)

// stairs：先用 2 分鐘從每秒 0 升到 200 當預熱，再從每秒 200 個使用者起，
// 每一級加 40，共 6 級（200 到 400），每級 5 分鐘，級與級之間用 1 分鐘線性升高
scn.injectOpen(
  rampUsersPerSec(0).to(200).during(Duration.ofMinutes(2)),
  incrementUsersPerSec(40.0)
    .times(6)
    .eachLevelLasting(Duration.ofMinutes(5))
    .separatedByRampsLasting(Duration.ofMinutes(1))
    .startingFrom(200.0)
)
```

兩段照官方文件〈Injection〉的語法組成，沒有實跑。`scn` 是讀者自己在 simulation 裡定義的 scenario。數字都是佔位值：倍數那一段的起點取 production 平常時段每秒開始的使用者流程數（[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 的〈Traffic shape 的五個維度〉），stairs 那一段假設倍數加壓之後 knee 落在 200 與 400 兩級之間。

stairs（`incrementUsersPerSec`）每一級加的是固定的量，不是倍數（官方文件的範例每級加 5：每秒 10、15、20、25、30 個使用者）。兩種寫法因此適合不同的階段：執行壓測的人先用倍數加壓，以少數幾級涵蓋好幾倍的範圍，找出 knee 落在哪兩級之間；再用 stairs 從那兩級中較低的一級起，把那一段切細，找出 knee 比較精確的位置。增量是兩級的差除以想切的段數：範例切成 5 段，（400 − 200）÷ 5 = 40；級數比段數多起點那一級，所以設成 `times(6)`，最後一級剛好是 400。只用 stairs 從平常時段的流量一路加上去，以同樣每級加 40 從 50 走到 400 要十級左右，每級 5 分鐘加 1 分鐘的升高，一次執行約一個小時；倍數加壓走到同一個範圍只要四級、二十分鐘。

兩次執行之間，受測服務要先回到平常的狀態再開始下一次：倍數加壓多半會越過 cliff，留下積壓的佇列、耗盡的連線池，甚至記憶體用完而重啟的實例；資源指標回到加壓前的基線之後再跑 stairs，stairs 量到的才是受測服務本身。stairs 那一段開頭的 2 分鐘升高，是為了不讓第一級（每秒 200）直接從 0 跳上去、把預熱混進第一級的讀數。

stairs 的 `separatedByRampsLasting` 讓級與級之間用一段時間線性升高，不一次跳上去：到達率一次跳升時，受測服務的連線池與施壓端的 JVM 同時要承接突然多出來的使用者，下一級前一兩分鐘的延遲混著這段過渡，穩態要晚一點才出現。倍數加壓那一段沒有寫升高，級與級之間是直接跳升，所以讀每一級的穩態時，要略過每一級開頭的那一段。1 分鐘是佔位值，這裡沒有比較其他長度；它要長到受測服務與施壓端在下一級開始之前跟得上，太短時效果接近直接跳升。

`constantUsersPerSec` 與 `rampUsersPerSec` 另有 `.randomized()` 的寫法，讓抵達的間隔隨機分佈，不是等距（官方文件〈Injection〉）。production 的抵達多半不是等距的，同一秒內有時多、有時少，等距注入量到的排隊比 production 少；受測服務對短暫的湧入敏感時（連線池小、佇列短），用 randomized 量到的 knee 比較接近 production。

## 探測之前要固定的條件：副本數與負載打在哪一端

容量結論寫的是「這個配置下」處理得了多少，所以探測期間受測服務的配置要固定。受測環境開著 autoscaler 時，某一級中途擴容，延遲先升後降、成功的回應暫時跟不上再追上，〈從 report 判讀 knee point〉列的狀態都對不上，量到的也不是任何一個配置的容量。量單一配置的容量時，探測期間把副本數固定、關掉 autoscaler，量到的是固定副本數下的容量，要加多少副本另外換算（[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)）。要量的就是 autoscaler 本身時（擴容要多久、擴容期間延遲多高），記下每一次擴容事件的時間，擴容前後那幾級不讀成某一個配置的容量。

受測環境用的是會累積額度的規格時（雲端的可突發機型的 CPU credit、雲端磁碟的 burst 額度），長時間的探測會把額度用完，用完之後效能降回基準值，knee 隨時間往較低的到達率移，樣子跟後面那幾級飽和相同；探測期間記下額度的餘量，或改用固定效能的規格。

負載打在哪一端也要先決定。受測服務前面有 CDN 時，打 CDN 量到的是 CDN 加上 origin 在這組快取命中率下的容量，打 origin 量到的是 origin 自己的容量；兩者的命中率與錯誤都不同。CDN 或 WAF 可能把壓測流量判成攻擊，回 403 或 429，這些錯誤來自前面那一層的防護，不是 origin 過載；打 CDN 時要事先讓那一層放行施壓端的來源，或把這類錯誤在讀數裡分開看。

## 從 report 判讀 knee point

Gatling 的 HTML report 有四張隨時間變化的圖用來判讀 knee point：Users start rate（每秒開始的虛擬使用者數）、Requests per second over time（每秒送出的請求數）、Responses per second over time（每秒收到的回應數，分成功與失敗）、Number of concurrent users（同時在線的虛擬使用者數）（官方文件〈Reports〉）；延遲的百分位數另有一張隨時間變化的圖，這張圖只統計成功的請求。open model 設定的到達率以使用者計，一個使用者跑完整個 scenario，中間可能送出好幾個請求、也可能停頓，所以四張圖之間要先換算：

- Users start rate 應該等於設定的到達率，這張圖是確認負載有沒有送足的那一張。
- 每秒請求數在穩態下等於到達率乘以每個 scenario 的請求數；scenario 只有一個請求時，兩者才相等。scenario 裡的停頓只拉長使用者在線的時間，不改變每秒送出的請求數。
- 同時在線數是還沒跑完 scenario 的使用者數，照 [Little's Law](/backend/knowledge-cards/little-law/) 等於到達率乘以一個使用者跑完 scenario 的時間，這段時間包含 scenario 裡的停頓。到達率固定時，停頓的長度不變，同時在線數上升代表請求在受測服務裡花的時間變長了。停頓遠比請求的延遲長時（scenario 裡停頓 30 秒、請求延遲從 50 毫秒升到 200 毫秒），同時在線數只多不到百分之一，圖上看不出來，所以同時在線數只當輔助的訊號。

換算之後，判讀看的是成功的回應與延遲的百分位數，錯誤另外看比例。每一級的穩態對應受測服務的幾種狀態：

- **線性區**：成功的回應數跟得上每秒請求數，錯誤率接近 0，延遲的百分位數在各級之間幾乎不變。
- **knee**：成功的回應數仍然跟得上、錯誤率仍然接近 0，但 p99 的增幅開始遠大於到達率的增幅，p50 還穩。Saturation Point 卡給的量化訊號是「負載增加 10%、延遲增加 100%」：到達率每加一級，p99 增加的比例遠大於到達率增加的比例，就是請求在受測服務裡開始排隊了；排隊先發生在撞上短暫湧入的少數請求上，所以先反映在尾端的百分位數。這個比例的判斷標準要在 stairs 的小增量下套用：倍數加壓每一級的到達率加一倍，p99 加五成的那一級既不是持平、也不到十倍的比例，歸不進任一種狀態，所以倍數加壓只用來找出「最後一個 p99 持平的級」與「第一個 p99 明顯上升的級」，knee 落在兩者之間，再用 stairs 的小增量（例如每級加兩成）找出第一個出現這個比例的級，那一級就是 knee point 所在的那一級。
- **cliff**：成功的回應數低於每秒請求數，同時在線數在同一級之內持續上升：抵達的比處理完的多，沒處理完的請求在累積。延遲隨時間一直往上走，接著出現逾時與錯誤；這之後服務呈現的是變慢、請求失敗、無回應還是程序終止，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)。
- **失敗比例上升**：回應數（含失敗）跟得上請求數，但失敗的回應比例隨級數上升，分兩種情形。一種是受測服務在過載時直接拒絕（429、斷路器開路、立即回 503），失敗的回應很快回來，總回應數跟得上，同時在線數甚至下降。另一種是請求等到 Gatling 的逾時才失敗，同時在線數停在一個上限（每個使用者最多卡在逾時值那麼久）。兩種情形的延遲百分位數圖都看不到這些失敗的請求，因為那張圖只統計成功的請求，所以只看總回應數或延遲圖，會把這種狀態讀成線性區或 knee；判讀看的是失敗的比例。它屬於 cliff 之後的過載表現，同樣見 9.16。

線性區與 knee 的判讀單位是每一級的穩態（略過級與級之間的升高）；cliff 在同一級之內就不持平，判讀看的是同一級之內的趨勢。接近 knee 時，排隊收斂到穩態的時間會拉長，同一級的同時在線數可能在 5 分鐘內仍在上升、只是越升越慢，這時比較那一級的後半與前半：增幅在收斂，就延長那一級再判，不急著讀成 cliff；5 分鐘是 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 建議的下限，不是固定值。

9.4〈Ramp-up 測試方法〉把「throughput 從線性成長轉成 sub-linear」列成 knee 的訊號，那是吞吐量隨負載增加的形狀。open model 下，吞吐量在受測服務處理得了的範圍內跟著設定的到達率走，到達率加一倍、成功的回應數也加一倍，所以 sub-linear 在 open model 的 report 上表現成成功的回應數低於每秒請求數，也就是 cliff 那一種，出現在 knee point 之後；在 open model 下，knee point 的訊號是更早出現的 p99 上升。

closed model 的 report 讀法不同：同時在線數是設定值，不會隨服務變慢而上升，要看的是成功的每秒請求數與延遲。逐級增加同時在線數時，成功的每秒請求數跟同時在線數同比例增加、延遲持平是線性區；某一級起成功的每秒請求數的增幅小於同時在線數的增幅、延遲開始上升，那一級是 closed 型服務的 knee：同時在線數固定時，吞吐量等於同時在線數除以一個使用者每輪花的時間（延遲加停頓，[Little's Law](/backend/knowledge-cards/little-law/)），增幅變小代表每個請求在受測服務裡花的時間開始變長。再加同時在線數而成功的每秒請求數不再增加時，已經越過服務的上限，多出來的使用者只是在受測服務裡排隊（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈設計責任〉）。容量結論的單位是「同時在線多少個使用者時，每秒成功處理多少個請求、延遲多少」。服務快速回錯誤時，closed model 下總請求數會繼續上升，所以這裡同樣只看成功的那一部分。

knee 落在哪一級之後，同一段時間對照受測服務的資源指標，照 9.4〈Resource saturation 的六個維度〉找出先飽和的資源，定位的流程在 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)；那一項資源才是容量結論裡「要加什麼」的依據。

## 施壓端的檢查與分散施壓

判讀 report 之前，先確認施壓端在整段測試中沒有飽和：施壓端飽和時，report 上的停滯與延遲上升跟受測服務飽和的樣子相同，每一個數字都混著施壓端自己的時間，knee 落在哪一級無從判讀。施壓端的資源與訊號依症狀分成三類，完整的清單在 [Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/) 的〈可觀察訊號與例子〉：

- **Users start rate 低於設定的到達率**：施壓端排程不出設定的使用者，用完的是 CPU、記憶體或被 GC 暫停卡住。Gatling 跑在 JVM 上，GC 是容量探測裡最常隨負載變化的一項：到達率越高，施壓端每秒處理的回應越多，產生的物件也越多，heap 給得不夠時 GC 暫停變頻繁。
- **失敗的回應帶著施壓端的錯誤訊息**：`Too many open files`（檔案描述元用完）或 `Cannot assign requested address`（來源埠用完）。使用者照樣開始，請求以連線錯誤失敗，Users start rate 不會因此下降。
- **延遲上升而前兩類都乾淨**：比對 Gatling 量到的延遲與受測服務入口量到的延遲，差距變大代表多出來的時間花在施壓端或網路上，要看施壓端網卡的吞吐量有沒有到頂（回應很大時，頻寬比 CPU 先用完），以及 GC 暫停有沒有加長延遲。

單台施壓端送不出需要的到達率時，要把負載分到幾台施壓端。Gatling 官方的 [FAQ](https://docs.gatling.io/tutorials/faq/) 寫明不支援用 OSS 版做分散施壓，維護者在[官方論壇](https://community.gatling.io/t/generate-gatling-report-from-multiple-simulation-log-files-with-version-3-13-5/9737)（2025 年，針對 3.13.5 版）也說明過，分散施壓只有 Gatling Enterprise 支援，OSS 版不能把多台的結果合成一份 report。所以 OSS 的做法是每台施壓端各自執行一份 simulation、各自負責總到達率的一部分、各自產生 report，另外有幾件事要一起處理：

- **feeder 依台切分**：一次性的資料（只能用一次的 token、有唯一約束的欄位、同一個帳號不能同時登入兩個 session）在多台共用時會互相衝突；用依序取用（`queue`）的 feeder 時，各台還會同時走同一批 key，快取命中率比 production 高（機制在〈feeder 資料的分佈、脫敏與快取命中率〉）。每台拿到不重疊的一段資料，這兩種問題都避開。
- **施壓端不共用網路出口**：幾台施壓端走同一個 NAT、或跑在同一台主機上時，來源埠與頻寬仍然共用，台數加了，施壓端的上限沒有跟著加（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/) 的確認方法也以這一點為前提）。
- **各台同時開始、時鐘一致**：各台的 simulation 要同時啟動、系統時鐘要同步，每一級的開始與結束才對得齊；對不齊時，加總之後每一級的穩態被拉平，knee 看不清楚。
- **哪些數字可以跨台加總**：Users start rate、每秒請求數、每秒回應數與同時在線數是計數，各台相加就是總數；百分位數不能相加或平均（[Percentile](/backend/knowledge-cards/percentile/) 的〈設計責任〉）。所以延遲從受測服務那一端讀，前提是受測服務的延遲指標用 histogram 型、可以跨副本加總之後再算百分位數，而且量測點跟延遲目標的量測點一致（目標訂在入口或用戶端時，就從入口或用戶端量）；受測服務的指標是各副本自己算好的百分位數時，各副本的 p99 平均起來同樣不是整體的 p99，這次探測的延遲結論就不可用。

Gatling Enterprise 預設把 simulation 的注入步驟分配到各台施壓端、把結果合在一起；`noShard` 這個設定關掉分配，讓每台施壓端各自跑完整的注入步驟（官方文件〈Injection〉的 `noShard` 一節）。Enterprise 也能從不同的區域施壓。兩者的取捨在容量探測裡看的是需要的負載量與施壓的位置：單台送得出需要的到達率時 OSS 就夠；台數增加之後，OSS 要自己分配到達率、切分 feeder、對齊時鐘、加總計數、從受測服務那一端讀延遲，每多一台施壓端，這幾件事各多一份要核對的資料；要從幾個區域同時施壓時，OSS 還要在每個區域各自部署施壓端。選 Enterprise 時另有兩個條件：受測環境在私有網路裡時，雲端的施壓端進不去，要另外架設自管的施壓端；測試結果存在廠商的服務上，有資料存放規定的團隊要先確認可不可以。另一個選項是換用 OSS 版本就支援分散施壓的工具（Locust 的 master 與 worker、JMeter 的 remote testing），各工具在一台施壓機的上限怎麼量、分散擴容用什麼方式的比較，在 [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/) 的規模能力那一個選型維度。

## feeder 資料的分佈、脫敏與快取命中率

feeder 是 Gatling 餵資料給 scenario 的機制，每個虛擬使用者從 feeder 取一筆資料（帳號、商品編號、搜尋字）帶進請求。feeder 的資料分佈直接影響容量探測的結論：受測服務前面有快取時，feeder 裡 key 的種類數少於 production 在同一段時間裡會請求到的 key，同一小批帳號或商品反覆被請求，快取命中率比 production 高，請求很少走到資料庫，量到的 knee 落在比 production 高的到達率上，容量被估高；production 上那些命中不了快取、要讀資料庫的長尾請求，壓測裡沒有出現。

feeder 的分佈偏差在容量探測裡的影響比在效能 regression gate 裡大。gate 比較前後兩版，兩次用同一份 feeder，偏差造成的偏移兩版都有，比較的是差距（gate 的盲區是這一版改到 feeder 沒走到的路徑，寫在 [Gatling 在效能 regression gate 的用法](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/) 的 PR 與 nightly 那一節）。容量探測的結論是一個絕對的數字（處理得了每秒多少個使用者），偏差直接算進那個數字。所以 feeder 的資料量與 key 的分佈要對得上 production，包括很少被存取的長尾。

feeder 的資料從 production 產生時，帳號、電話、地址這類個人資料要先匿名化或替換，並讓替換後的值的種類數（cardinality）跟 production 一致：種類數變少，同一批值被反覆請求，快取命中率又會偏高。做法見 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)〈從 production log 抽 workload model〉裡脫敏處理的那一步（hash 加 salt、保留種類數）。資料也要定期重新產生：過期的 token、已經下架的商品讓請求回錯誤，錯誤率上升看起來像服務到了 cliff。Gatling 的 feeder 有依序（`queue`，預設）、打亂（`shuffle`）、隨機（`random`）與循環（`circular`）四種取用方式；依序與打亂兩種用完資料時，Gatling 報錯並中止這次執行，隨機與循環不會用完（官方文件〈Feeders〉）。

## 讀取與寫入的高峰錯開的流量：多個 scenario 同時注入

業務裡兩種流量的高峰在不同的時間出現時，寫進同一個 scenario 注入，量到的是兩種流量混在一起的平均，看不到任何一種高峰。[9.C4 DraftKings：Aurora 處理每分鐘 100 萬 ops 的體育博彩金融帳本](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 是這種形狀：一段時間內查詢餘額的讀取是高峰，另一個時點結算的寫入是高峰，兩個高峰錯開。Gatling 在 `setUp(...)` 裡可以放好幾個 scenario，各自有自己的注入步驟，同時執行。量兩種高峰要跑兩次：一次讓讀取的 scenario 逐級加壓、寫入的 scenario 固定在平常的到達率，量出「讀取高峰疊上平常的寫入」的 knee；另一次反過來，量出「寫入高峰疊上平常的讀取」的 knee。兩個 knee 可能落在不同的資源上，例如讀取的高峰先用完 replica 的連線、寫入的高峰先用完主庫的寫入能力；這是依讀寫分流的架構推論的，案例本身沒有量到。

## 量完之後寫成容量結論要記下的條件

容量探測的結論寫成條件句：「在這個配置下、p99 低於多少毫秒的條件下，處理得了每秒多少個使用者，先飽和的是哪一項資源，距離飽和點還剩多少餘裕（[Headroom Budget](/backend/knowledge-cards/headroom-budget/)）」（[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈概念定位〉、〈Saturation 文件化：容量地圖〉）；closed 型服務的單位換成同時在線的使用者數。這個結論是 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的輸入，那一章拿 knee 與 headroom 換算成預期的峰值要幾個副本。條件句的每一項都要能回溯到這次執行：simulation 的版本、注入步驟與到達率、每個 scenario 的請求數、feeder 的來源與產生日期、受測環境的配置與版本、測試期間的副本數與 autoscaler 設定、負載打在 CDN 還是 origin、Gatling 的版本、施壓端的台數與規格、下游哪些服務是 mock。reviewer 從結論回到這些條件，判斷得了一次結果是受測服務的容量訊號，還是測試設計造成的偏差（feeder 偏差、施壓端飽和、副本數中途改變、下游 mock 的回應比實際的下游服務快）。欄位的組織方式照 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 的〈Evidence 欄位〉。

## 延遲上升或吞吐量停滯時的排查順序

Gatling 的容量探測量到延遲上升或吞吐量停在某個值時，有幾種成因會讓讀數不能直接當成受測服務的容量：施壓端飽和、feeder 資料過期、scenario 實際送出的請求跟換算對不上。下面的施壓端、feeder 與每秒請求數三項依序排除這幾種，knee 那一項是排除之後的容量結論，最後跟 production 經驗比對的那一項是結論偏高時的檢查。順序依一件事排：前一項沒有排除時，後一項的讀數還能不能用。排查之前先確認〈探測之前要固定的條件〉那一節的條件成立（副本數固定、負載打在哪一端已經決定），否則每一項的讀數都對不上同一個配置。

1. **施壓端的資源**：open model 下先看 Users start rate 與設定值，不必另外收集指標；接著依〈施壓端的檢查與分散施壓〉的三類訊號看 CPU 與 GC、施壓端的錯誤訊息、工具與受測服務入口的延遲差距。closed model 下沒有設定的到達率可以比，只能靠施壓端的 CPU、GC、錯誤訊息與那個延遲差距；closed model 下施壓端飽和的樣子（成功的每秒請求數停住、延遲上升）跟受測服務的飽和點相同，這一項沒排除時，量到的飽和點可能是施壓端的上限。施壓端飽和時，report 上的每一個數字都混著施壓端的時間，後面每一項的讀數都不能用。
2. **feeder 資料的有效性**：錯誤的明細裡有大量認證失敗或找不到資源（HTTP 401、404）時，先分辨成因：feeder 的資料過期時，這類錯誤從第一級起就以大致固定的比例出現；錯誤比例隨級數上升時，比較可能是負載造成的（認證服務本身飽和、讀取 replica 的延遲讓剛寫入的資料讀不到），那是容量的訊號。級數是依時間排的，所以資料在執行中途失效時（token 的有效期限比整次執行短、`circular` 的 feeder 繞完一圈之後重用只能用一次的資料），錯誤也會隨級數上升；分辨的依據是錯誤開始增加的時點對齊什麼：對齊級與級的交界，是負載造成的；對齊某個時鐘時間（token 到期的時刻）或 feeder 繞完一圈的時點，是資料的問題。拿 feeder 的產生日期與 token 的有效期限對照，或用新產生的資料重跑同一級，就能確認。這一項排在每秒請求數之前，因為過期資料造成的錯誤會經由 scenario 裡依回應決定是否繼續的步驟，讓下一項的每秒請求數跟著變少，也會讓 cliff 看起來提早出現。
3. **每秒請求數與換算值**：每秒請求數低於 Users start rate 乘以 scenario 的請求數時（兩種注入模型都用 Users start rate 換算，它在 report 上都有），使用者實際送出的請求比流程少。Gatling 預設不會因為一個請求失敗就中止 scenario，所以這種落差來自 scenario 裡依回應決定是否繼續的步驟（`exitHereIfFailed`、依前一個回應決定要不要送下一個請求的條件分支）：受測服務開始回錯誤時，後面的請求沒有送出，受測服務收到的負載比換算的少。這時 knee 落在哪一級的判讀，要用實際的每秒請求數計算。
4. **knee 所在的一級與先飽和的資源**：施壓端、feeder 的有效性與實際送出的請求都排除之後，照判讀 knee point 的方法找出 knee 所在的那一級，再對照受測服務的資源指標找出先飽和的資源。這一項的結果就是容量結論。
5. **量到的容量與 production 經驗的差距**：量到的容量高於 production 實際觀察到的值時，查 feeder 的分佈與快取命中率、下游 mock 的回應時間，它們讓容量被估高。新服務或新區域沒有 production 的值可比時，比對的對象改成跟這次量測互相獨立的參照：測試期間的快取命中率對照 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 推出的 key 分佈預期會有的命中率、下游 mock 的回應時間對照真實依賴的延遲、另外加跑一次快取冷啟動或只打長尾 key 的變體；三者都做不到時，容量結論註明「未經 production 校準」。[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)拿這次的量測當輸入，不能反過來當成驗證這次量測的參照。這一項在 knee 之後查，因為要先有 knee 與先飽和資源的結論，才知道高估了多少。

同樣看到 p99 變慢，用 Gatling 做 regression gate 時，排查先比對兩次執行的條件，再排除施壓端飽和與雜訊範圍，要判斷的是這一版有沒有退化、擋不擋 release，順序與這裡不同，寫在 [Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/) 的排查順序那一節。

## 相關章節與工具頁：飽和點的方法、workload model 與壓測工具選型

- [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：飽和的定義、ramp-up 的方法與 CPU、記憶體、磁碟、網路、連線池、外部 API 配額的判讀，本篇的加壓寫法與 knee 判讀都建立在它上面。
- [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)：注入步驟的到達率、feeder 的資料分佈與脫敏從這裡取。
- [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)：找到 knee 之後，定位是哪一項資源、哪一段程式先飽和。
- [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：把容量結論與 headroom 換算成預期峰值要的副本數。
- [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)：Gatling 與 k6、JMeter、Locust 在腳本表達能力、協議支援、規模能力、CI 整合、結果分析與學習曲線上的取捨。
