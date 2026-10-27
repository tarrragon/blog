---
title: "Open and Closed Workload Model（開放與封閉負載模型）"
date: 2026-10-27
description: "設計壓測的注入方式、要在固定到達率與固定同時在線人數之間選一種，或壓測量到的延遲低於 production、懷疑負載工具少送了請求時讀"
weight: 497
tags: ["backend", "performance", "load-test", "knowledge-card"]
---

Open workload model 與 closed workload model 是負載測試產生請求的兩種方式，差別在新的請求什麼時候送出。open model 依到達率送出：每秒抵達多少個新的虛擬使用者是事先設定的，跟受測服務回應得多快無關；closed model 依同時在線的虛擬使用者數送出：固定數量的虛擬使用者各自送出請求、等到回應、再送下一個，回應沒回來，那個使用者的下一個請求就不會送出。兩種模型各自固定了 [Little's Law](/backend/knowledge-cards/little-law/)（L = λW：L 是同時在系統內的請求數，λ 是到達率，W 是一個請求在系統內停留的時間）裡的一個變數：open model 固定到達率 λ，closed model 固定虛擬使用者的總數 N。虛擬使用者在兩個請求之間沒有停頓（think time）時，N 就是 L；有停頓時，停頓中的使用者不在系統內，L 小於 N。

## 概念位置

兩種模型的差別在受測服務變慢、也就是 W 變長的時候才看得到。open model 下 λ 固定，W 變長時 L 跟著上升：沒完成的請求在服務裡累積，排隊的時間算進量到的延遲，延遲在負載接近 [Saturation Point](/backend/knowledge-cards/saturation-point/) 時急遽上升。closed model 下 N 固定，每個虛擬使用者每送出一個請求要花 W 加上停頓的時間，所以吞吐量等於 N 除以（W 加停頓），W 變長時 λ 只能下降：每個虛擬使用者送出下一個請求的時間往後延，實際的請求率跟著下降，負載工具配合受測服務的速度少送了請求。在 production 裡，那些少送的請求會照樣抵達、在服務外排隊，壓測沒有送出它們，它們的等待時間也就沒有被量到；這種少算業界稱為 coordinated omission。

coordinated omission 不只發生在 closed model：open model 下施壓端自己飽和、送不出設定的到達率時，請求比排定的時間晚送出，延遲從實際送出的那一刻起算，那段延後同樣沒有被量到（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)）。

所以模型的選擇是 [Workload Model](/backend/knowledge-cards/workload-model/) 的一部分：production 的流量屬於哪一種模型，壓測就用哪一種，量到的延遲與吞吐量才對得上 production。實際的流量常常介於兩者之間：使用者以 open 的方式抵達，進來之後在同一個 session 裡依序送出好幾個請求，每個請求等前一個的回應，session 之內是 closed 的；這種形狀稱為 partly-open model，負載工具裡一個使用者跑完多個請求的 open 注入就是這一種，抵達率由注入步驟決定，session 的長度由受測服務的速度決定。

closed model 另有一種常見的設定，依每一輪花掉的時間縮短或拉長停頓、讓每段時間開始的輪數固定在上限以內，英文稱為 pacing，下文沿用這個詞：工具依上一輪花掉的時間調整停頓，讓虛擬使用者在一段固定的時間內，至多開始設定次數的一輪工作（Locust 的一輪是一個 task，JMeter 的 timer 掛在單一 sampler 底下時，一輪是那個 sampler 的一次執行，官方建議掛在一輪流程的第一個 sampler 底下，它每輪執行一次，所以一輪就等於一次 iteration；放在 thread group 層、讓範圍內每個 sampler 都經過它時，一輪是每一個 sample；一輪可能送出好幾個請求）。速率上限有兩種算法：依每個使用者計算時（Locust 的 `constant_throughput`），一輪的次數上限是 N 乘以每人的速率；依整組使用者計算時（JMeter 的 Precise Throughput Timer，以及 Constant Throughput Timer 的多數計算模式），上限就是設定的總量。兩種算法得到的都是每秒的輪數上限，換算成每秒請求數時，再乘以一輪送出的請求數。pacing 仍然是 closed model，因為使用者還是等到回應才開始下一輪：受測服務變慢、一輪花掉的時間超過設定的間隔時，工具沒有剩下的停頓可以縮短，速率就低於設定值，整體吞吐量跟著下降，同樣有 coordinated omission。所以 pacing 讓請求率在受測服務還快的時候穩定在設定值，讀起來像 open model，而服務變慢時它跟一般的 closed model 一樣減壓；只有在量到的每秒輪數一直等於設定的上限時，報告上的負載才是設定的那個值。

## 可觀察訊號與例子

Production 流量屬於哪一種模型，看送出請求的一方會不會等回應。面向公眾的網站與 API 屬於 open model：使用者彼此獨立，一個人等得久，不會讓另一個人晚一點打開 App；搶票、限時開賣這類瞬間湧入的流量，更是由到達率決定。呼叫端的數量固定、拿到回應之前不送下一個的流量屬於 closed model：固定 worker 數的批次程式、連線池大小固定的內部服務呼叫方、固定座席數的客服系統。

用 closed model 壓 open 型流量時，延遲目標內的到達率與吞吐量的上限，兩者偏差的方向不同。延遲目標內的到達率被估高：服務外排隊的時間沒有量到，報告上的延遲在比 production 更高的到達率下仍然低於目標。吞吐量的上限則取決於 N 設得多大：吞吐量等於 N 除以（W 加停頓），N 設得小時，吞吐量停在服務處理得了的值以下，N 設得大時才會碰到服務的上限。所以壓測報告的延遲曲線平穩、吞吐量停在某個值不再上升，而 production 在相近的流量下出現延遲尖峰，是這種誤用的常見樣子：報告上停住的吞吐量是 N、W 與停頓決定的值，不一定是服務的上限。

負載工具各自用不同的名字區分兩種模型。Gatling 把注入步驟（injection step）分成兩組，同一條注入鏈只能用同一組（官方文件〈Injection〉）：`constantUsersPerSec`、`rampUsersPerSec`、`atOnceUsers`、`rampUsers`、`stressPeakUsers` 與逐級加壓的 `incrementUsersPerSec` 屬於 open model，其中 `atOnceUsers` 在同一刻放進指定數量的使用者、`rampUsers` 在一段時間內平均放進指定的總數，兩者都不等回應，仍是 open model；`constantConcurrentUsers`、`rampConcurrentUsers` 與逐級加壓的 `incrementConcurrentUsers` 屬於 closed model，名字裡都帶 `Concurrent`。

k6 用 executor 區分：`constant-arrival-rate`、`ramping-arrival-rate` 是 open model，`constant-vus`、`ramping-vus` 是 closed model。

Locust 的使用者數由 `-u`（`--users`，同時在線的使用者數）或 `LoadTestShape` 決定，每個使用者跑完一個 task、等完 `wait_time` 才挑下一個，屬於 closed model；官方文件〈Writing a locustfile〉寫明 wait time 只能限制吞吐量、不會為了達到目標啟動新的使用者。`wait_time` 設成 `constant_throughput` 或 `constant_pacing` 是 pacing；設成 `poisson` 時，官方的說明寫 task 依 Poisson 過程抵達，而停頓仍然加在上一個 task 跑完之後，同樣是 closed model。

JMeter 用 thread group 與 timer 區分：內建的 Thread Group 與 plugin 的 Concurrency Thread Group 固定同時在線的 thread 數，是 closed model；5.5 起內建的 Open Model Thread Group（官方標為 experimental）依排程在每次抵達時建立一個新的 thread、跑完一輪就結束，plugin 的 Arrivals Thread Group 在現有的 thread 都忙時建立新的 thread，兩者都是 open model，Arrivals Thread Group 碰到它的 Concurrency Limit 之後退回 closed；Constant Throughput Timer 與 Precise Throughput Timer 是 pacing。plugin 的 Throughput Shaping Timer 以每秒請求數為目標，但它只能延後 thread、不會多開 thread，thread 數不夠時到不了目標值（jmeter-plugins.org 的說明），所以只有在 thread 數給夠時才接近 open model。

## 設計責任

設計壓測時先判斷 production 流量的模型，再選工具的注入方式；工具的預設值不一定是 production 的那一種。找飽和點的方式跟著模型走：open 型流量逐級提高到達率，量的是延遲在哪一個到達率開始不成比例上升，用 closed model 量的話，工具的減壓讓那個到達率被估高；closed 型流量逐級增加虛擬使用者的總數，量的是 N 加到多少時 W 開始上升、吞吐量的增幅開始小於 N 的增幅，那一級是 knee；再加 N 而吞吐量不再增加時，已經越過服務的上限。兩次結果要互相比較時（同一個 release gate 的前後兩版），兩次用同一種模型與同樣的參數。兩種模型都假設抵達不受服務的速度影響（open）或只因等回應而變慢（closed），而 production 的用戶端常常會重試：服務變慢、逾時增加時，重試讓實際的抵達率反而上升，兩種模型都沒有涵蓋這個放大，壓測量到的結果因此比 production 樂觀；用戶端有重試時，壓測要另外模擬重試的行為，或在結論裡註明沒有涵蓋。
