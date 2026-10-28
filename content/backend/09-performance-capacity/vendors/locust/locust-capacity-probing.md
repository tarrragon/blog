---
title: "Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序"
date: 2026-10-28
description: "Locust 只有 closed model 時找飽和點的判斷：逐級增加使用者、從每秒 task 數與延遲換算受測服務的狀態、到達率型服務的延遲低估與 pacing 的上限、worker 與 client 的排除條件，以及容量結論的寫法"
weight: 1
tags: ["backend", "performance", "capacity", "vendor", "locust", "load-test"]
slug: "locust-capacity-probing"
---

用 Locust 做容量探測的人，要判斷的是目前的配置在延遲目標內處理得了多少負載、先用完的是哪一項資源、要加什麼。這篇整理這個判斷在 Locust 上的做法：Locust 在 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 ramp-up 測試裡負責哪一段；Locust 只提供 closed model（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)），所以逐級加壓寫成逐級增加同時在線的使用者數，用 `LoadTestShape` 的 `tick()` 排出倍數加壓與小增量的兩段；從 `--csv` 產生的歷史紀錄裡的使用者數、每秒請求數與延遲百分位數，照 [Little's Law](/backend/knowledge-cards/little-law/) 換算出受測服務處在線性區、knee 還是吞吐量停住的狀態；受測服務的流量屬於到達率型時，closed model 量到的延遲為什麼偏低（coordinated omission），`constant_throughput` 的速率上限在什麼條件下才等於送出的負載；task 的權重怎麼對應 production 的操作分布，以及 closed model 下一個變慢的 endpoint 怎麼拉低其他 endpoint 的負載；執行 Locust 的機器（施壓端，load generator）上 worker 程序要先確認的 CPU、會卡住 gevent 的 client 函式庫、連線池與網卡，worker 的數量怎麼量出來，master 與 `--expect-workers` 的角色；自訂 client 的連線池、逾時與重試怎麼對齊 production；量完要記下哪些條件才寫得成容量結論；延遲上升或吞吐量停住時依序查哪幾件事。飽和的定義、ramp-up 的方法與 CPU、記憶體、磁碟、網路、連線池、外部 API 配額這幾個資源的判讀是 9.4 的內容，本篇只寫它們在 Locust 上的做法。Locust 的安裝、locustfile 的完整語法與 Locust Cloud 在 [Locust 官方文件](https://docs.locust.io/en/stable/)；同一個工具接進 CI、擋下效能退化的寫法在 [Locust 在效能 regression gate 的用法：exit code 與門檻判定、預熱與 on_start 的請求、closed model 下的比較、custom client 回報的請求範圍、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/)；用 open model 注入的工具做同一件事，寫在 [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)。

本篇的程式碼區塊都照官方文件與官方 examples repo 的語法組成，沒有實跑；寫到原始碼行為的地方，以 2026 年 10 月 GitHub 上 locustio/locust 的 master 分支為準（PyPI 上當時的版本是 2.47.0），同樣沒有實跑。

## Locust 在容量探測裡負責的環節

容量探測要量出受測服務在延遲與錯誤率目標之內處理得了的最大負載（[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈概念定位〉；設計容量另以 knee point 為上限，9.4〈Saturation 的精確定義〉），以及到達那個值時哪一項資源先用完（9.4〈Resource saturation 的六個維度〉）。Locust 用這幾個名字區分它執行的內容：User class 是一種虛擬使用者的行為，裡面的 task 是一次要執行的動作（送出一個或幾個請求），`wait_time` 決定一個 task 跑完之後等多久再挑下一個，`LoadTestShape` 決定每一刻同時在線的使用者數。Locust 在這裡做兩件事：照 shape 逐級增加使用者，大約每秒記錄一次當時的使用者數、每秒請求數、每秒失敗數與延遲分佈。

找 knee point（延遲開始隨負載不成比例上升的那一級負載，[Saturation Point](/backend/knowledge-cards/saturation-point/)）要用到兩邊的資料：Locust 的紀錄寫出每一級使用者數下吞吐量與延遲怎麼變，受測服務的資源指標寫出是哪一項資源在排隊。只看 Locust 的紀錄找得到 knee 在哪一級，說不出它為什麼在那裡。`--exit-code-on-error` 在請求有任何失敗時讓 Locust 以非零的 exit code 結束（官方文件〈Configuration〉，預設值是 1）；容量探測本來就要把負載加到 knee 以上，失敗是預期內的結果，所以這個 exit code 在這裡不代表探測失敗。

## closed model 下的逐級加壓：LoadTestShape 的 tick

Locust 的使用者跑完一個 task、等完 `wait_time` 才挑下一個 task，回應沒回來時那個使用者的下一個請求不會送出，所以 Locust 產生的是 closed model 的負載。官方文件〈Writing a locustfile〉在 `wait_time` 那一節寫明：wait time 只能限制吞吐量，不會為了達到目標啟動新的使用者。逐級加壓因此寫成逐級增加同時在線的使用者數 N。下文的 W 是每一輪 task 從送出第一個請求到收齊回應花的時間：task 只送一個請求時就是那個請求的延遲，其中包含網路往返與 client 這一端的時間。量的是 N 加到多少時 W 開始上升、吞吐量的增幅開始小於 N 的增幅（knee），以及 N 再加時吞吐量不再增加（已經越過上限）。

`LoadTestShape` 是 locustfile 裡的一個 class，Locust 找到它就自動使用；Locust 大約每秒呼叫一次它的 `tick()`，`tick()` 回傳「使用者總數、每秒啟動或停止幾個使用者」的 tuple，回傳 `None` 時結束這次執行（官方文件〈Configuration〉的〈Custom load shapes〉）。[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 ramp-up 從平常時段的負載起按倍數加壓、每一級維持 5 到 10 分鐘，寫成 shape 是一張「使用者數、維持秒數」的表：

```python
from locust import HttpUser, LoadTestShape, between, task


class ApiUser(HttpUser):
    wait_time = between(1, 3)  # 每個 task 跑完之後隨機等 1 到 3 秒

    @task(8)
    def read_item(self):
        self.client.get("/items/42", name="/items/[id]")

    @task(2)
    def create_order(self):
        self.client.post("/orders", json={"item_id": 42, "qty": 1})


class DoublingSteps(LoadTestShape):
    # 每一列是（同時在線的使用者數, 這一級維持的秒數）
    stages = [(100, 300), (200, 300), (400, 300), (800, 300)]
    spawn_rate = 20  # 每秒啟動或停止的使用者數

    def tick(self):
        run_time = self.get_run_time()
        elapsed = 0
        for users, duration in self.stages:
            elapsed += duration
            if run_time < elapsed:
                return (users, self.spawn_rate)
        return None  # 走完最後一級就結束
```

讀者要改的位置：`/items/42`、`/orders` 與 request body 換成自己服務的 endpoint 與資料，`name=` 把帶 id 的網址歸成同一列統計；`between(1, 3)` 的停頓與 `@task(8)`、`@task(2)` 的權重從 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 抽出的 workload model 取（權重的意思在〈task 權重與 production 的操作分布〉）；`stages` 的數字都是佔位值。起點那一級的使用者數取 production 平常時段同時進行中的使用者 session 數；只有到達率時，照 Little's Law 用 session 的到達率（每秒開始的 session 數，不是每秒請求數）乘以一個 session 從開始到結束的時間換算。

倍數那一段的四級涵蓋八倍的範圍，用來找出 knee 落在哪兩級之間；找到之後改 `stages`，從那兩級中較低的一級起用固定的增量切細，例如 knee 落在 200 與 400 之間時，從 200 起每級加 40，到 400 為止。官方 examples repo 的 `examples/custom_shape/step_load.py` 是固定增量的寫法：`tick()` 用執行時間除以每級的秒數取得現在是第幾級，回傳級數乘以每級的增量。照它的寫法，從 200 起每級加 40 的那一段是：

```python
import math


class FineSteps(LoadTestShape):
    start_users = 200  # 倍數加壓找到的較低那一級
    step_users = 40    # 每級加的使用者數
    step_time = 300    # 每級維持的秒數
    steps = 6          # 200、240、……、400 共 6 級
    spawn_rate = 20

    def tick(self):
        current = math.floor(self.get_run_time() / self.step_time)
        if current >= self.steps:
            return None
        return (self.start_users + current * self.step_users, self.spawn_rate)
```

這個 class 放進同一份 locustfile、取代 `DoublingSteps`（一份 locustfile 留一個 shape）。`start_users`、`step_users` 與 `steps` 照倍數加壓找到的那兩級填：增量是兩級的差除以想切的段數，級數比段數多起點那一級。兩次執行之間，受測服務要先回到加壓前的資源基線，倍數加壓多半越過飽和點，留下積壓的佇列與耗盡的連線池，接著跑的小增量量到的會是那些殘留。

`spawn_rate` 決定每一級開頭那一段：從 200 加到 400 個使用者、每秒啟動 20 個，要 10 秒才到齊，這 10 秒的使用者數低於這一級的設定，讀穩態時要略過每一級的開頭。新啟動的使用者先執行一次 `on_start`（User class 有寫的話），再依權重挑 task（官方文件〈Writing a locustfile〉）。登入、取 token 寫在 `on_start` 時，每一級開頭都有認證請求的尖峰，請求數是這一級新增的使用者數，送出的速度是 `spawn_rate`；受測服務的認證元件在每一級開頭出現尖峰、穩態時回落，是這個原因，不是那一級的飽和。登入寫在 `@task` 裡時，認證請求混在每一輪 task 裡，量到的容量裡混著認證元件的處理能力。

closed model 下要模擬瞬間湧入（搶票開賣這類），`tick()` 回傳的使用者數在一兩秒內跳高、`spawn_rate` 設大：這模擬的是同時在線的使用者突增，每個使用者仍然等到回應才送下一個請求，受測服務一變慢，送出的請求就跟著變少，跟到達率突增的 production 流量不同。[9.C16 SeatGeek：DynamoDB + Lambda 打造的虛擬等候室](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 Queueing 模式讓受保護區只容納預設的並發人數、其餘依 FIFO 排隊；這種准入控制後面的服務，同時在線的使用者數由准入的上限決定，closed model 的 N 對得上那個上限，是 Locust 量得準的形狀。這一點是依案例描述的機制推論的，案例本身沒有量到。

## 從每秒請求數與延遲判讀受測服務的狀態

`--csv <前綴>` 讓 Locust 寫出 `<前綴>_stats.csv`、`<前綴>_failures.csv`、`<前綴>_exceptions.csv` 與 `<前綴>_stats_history.csv` 四個檔（官方文件〈Configuration〉的〈Save test statistics in CSV format〉；同一頁的選項表只列了其中三個）。逐級判讀用的是 `_stats_history.csv`：它在整次執行中定期追加列，每列有時間戳、`User Count`（當時的使用者數）、`Requests/s`、`Failures/s` 與各百分位數。附加的間隔在原始碼 `locust/stats.py` 的 `CSV_STATS_INTERVAL_SEC` 是 1 秒，官方文件寫的是預設兩秒。`Requests/s` 是最近十秒左右的平均，包含失敗的請求，所以成功的每秒請求數是 `Requests/s` 減 `Failures/s`。

百分位數那幾欄的算法，官方文件與原始碼的寫法不同：官方文件把歷史紀錄寫成十秒的滑動視窗；原始碼只在加了 `--csv-full-history` 時用約十秒的視窗，這時每個請求名稱各寫一列、`Name` 是 Aggregated 的整體那一列也用視窗；不加時只寫 Aggregated 那一列，它的百分位數從執行開始累積到當時，前幾級的低延遲一直混在後面的讀數裡，knee 被沖淡。逐級判讀要的是每一級自己的延遲，所以執行時加 `--csv-full-history`，讀各請求名稱那幾列與 Aggregated 列的百分位數；沒加的那次執行，Aggregated 列的百分位數不能直接當成每一級的延遲。這段讀法來自原始碼，沒有實跑核對。

closed model 下，Little's Law 寫成每秒 task 數 X 等於 N 除以（W 加平均停頓 Z），W 是前面定義的每一輪 task 的時間：`between(1, 3)` 的 Z 平均是 2 秒，一個 task 只送一個請求時，X 就是每秒請求數；一個 task 送 k 個請求時，每秒請求數是 X 乘以 k。

這兩個值從 `_stats_history.csv` 算。X 數的是跑完的 task，不論其中的請求成功或失敗：一輪裡有一個請求失敗時，那一輪仍然跑完，失敗另外看失敗比例。task 每一輪送的請求數固定時，X 是那一級穩態的 `Requests/s` 除以 k。W 是一輪 task 裡各請求延遲的和，要用每一級各請求名稱自己的平均延遲：歷史紀錄裡的平均欄是 `Total Average Response Time`，跟 `Total Request Count` 一樣從執行開始（或 reset）累積（原始碼 `locust/stats.py` 的 `_stats_history_data_rows`），不是每一級的平均。所以取那一級穩態頭尾兩列，用差分算：（尾列的 `Total Average Response Time` × 尾列的 `Total Request Count` − 頭列的 `Total Average Response Time` × 頭列的 `Total Request Count`）÷（尾列的 `Total Request Count` − 頭列的 `Total Request Count`）；各請求名稱的列要加 `--csv-full-history` 才有。task 依序送 `/login`、`/cart` 兩個請求時，W 是兩個名稱這樣算出的平均延遲相加，再加上 task 裡請求之間的程式執行時間（通常很小，可以忽略）。task 有分支、每一輪送出的請求數不固定時，要先有每一級的 task 數：Locust 的 CSV 沒有記錄 task 次數，在 task 開頭自己累加一個計數器（每跑一輪加一，不看請求成敗），依時間寫進 log，跟 CSV 的時間戳對齊（這是推出來的做法，沒有實跑；用 request 事件送一筆假的請求當計數也行，但它會算進 Aggregated 那一列的請求數與延遲）。有了 task 數之後，X 是那一級每秒的 task 數，W 是各請求名稱的平均延遲乘以那個名稱的請求數，加總之後除以 task 數。

k 在負載下可能改變：task 裡依回應決定要不要繼續的分支，在受測服務開始回錯誤時讓後面的請求沒送出，k 變小，每秒請求數比 X 先停住，看起來像 knee。所以下面各狀態用每一級的 X 判讀，每秒請求數只拿來核對 X 乘以 k。逐級增加 N 時，每一級的穩態對應受測服務的幾種狀態：

- **線性區**：每秒跑完的 task 數 X 跟著 N 等比增加，延遲百分位數在各級之間幾乎不變。N 從 200 加到 400、W 維持 50 毫秒時，X 從大約每秒 98 個增加到 195 個。
- **knee**：X 仍在增加、增幅小於 N 的增幅，p99 開始上升、p50 還穩。這就是 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈Ramp-up 測試方法〉列的「throughput 從線性成長轉成 sub-linear」；closed model 下吞吐量由 N 與 W 共同決定，W 一上升 X 就跟不上 N。停頓 Z 比 W 大很多時，X 的下降被 Z 稀釋：`between(1, 3)` 的 Z 平均 2 秒，W 從 50 毫秒升到 250 毫秒，每個使用者每秒的 task 數只從 1÷2.05 降到 1÷2.25，降幅約 9%，可能落在 `Requests/s` 本身的起伏裡；W 已經變成五倍，p99 的上升比 X 的變化明顯得多。所以 Z 大時 knee 的主要訊號是 p99，X 的增幅只當輔助。
- **吞吐量停住**：N 再增加，X 不再上升，停在受測服務這組操作分布下的上限 X_max（成功的每秒請求數是 `X_max × k`）；這時已經越過上限，飽和點在前面 knee 那一段，容量結論的 knee 那一項取 knee 之前最後一個 p99 持平的級。多出來的使用者只是在排隊：照 Little's Law，`W ≈ N / X_max − Z`，隨 N 線性上升。受測服務在爭用下效率下降時（鎖競爭、GC、連線池反覆建立與回收連線），成功的每秒請求數會在越過上限之後往下走，這也是越過上限的樣子。

吞吐量停住這種狀態在 closed model 下的樣子跟 open model 不同。open model 的到達率超過上限時，沒處理完的請求持續累積，延遲在同一級之內一直往上走，接著出現逾時，也就是 9.4 所說的 cliff：延遲變得不可預測、吞吐量開始下降、逾時與錯誤大量出現（[9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)）。closed model 的 N 是固定的，同時在系統裡的請求最多就是 N 個，所以延遲在同一級之內會穩定下來，只隨級數線性增加。Locust 的報告因此很少出現 cliff，「延遲隨使用者數線性上升、吞吐量持平」就是越過上限的樣子。換算也能拿來核對：某一級量到的平均每輪 task 時間跟 N÷X−Z（X 是那一級量到的每秒 task 數）差很多時，代表 N 或 Z 跟設定的不同（使用者還沒到齊、`wait_time` 寫錯、task 裡有沒算進 Z 的 `sleep`），那一級的讀數先不用。

服務在過載時直接拒絕（429、斷路器開路、立即回 503）時，失敗的回應很快回來，W 變短，closed model 的使用者反而更快送出下一個請求，`Requests/s` 繼續上升而成功的部分停住或下降。很快失敗的 task 也算跑完，X 跟著被灌高，所以這種情形下 X 不能拿來判讀，判讀改看成功的每秒請求數與失敗的比例。

knee 落在哪一級之後，同一段時間對照受測服務的資源指標，照 9.4〈Resource saturation 的六個維度〉找出先飽和的資源，定位的流程在 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)；那一項資源才是容量結論裡「要加什麼」的依據。

## 到達率型的服務：coordinated omission 與 constant_throughput 的上限

面向公眾的網站與 API 的使用者彼此獨立，一個人等得久不會讓另一個人晚一點打開 App，這種流量屬於 open model。用 Locust 的 closed model 量這種服務時，受測服務一變慢，每個虛擬使用者送出下一個請求的時間就往後延，送出的請求變少；production 裡那些請求照樣抵達、在服務外排隊，壓測沒有送出它們，它們的等待也沒有被量到，業界稱為 coordinated omission（機制在 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉）。`wait_time` 設成 `poisson(rate)` 也一樣：它讓每個使用者兩個 task 之間的停頓照指數分佈隨機取，平均停頓是 1÷rate 秒（原始碼 `locust/user/wait_time.py` 的說明寫平均每秒 rate 個 task）。停頓加在 task 跑完之後，所以每個使用者實際的速率是 1÷（W 加 1÷rate），只在 W 遠小於 1÷rate 時才接近 rate；使用者還是等到回應才送下一個，所以仍是 closed model。

容量結論從 Locust 的量測裡取兩項：吞吐量的上限 X_max（每秒 task 數，換成請求數是 `X_max × k`），以及延遲目標內的負載（延遲還在目標內的最後一級）。延遲目標內的最後一級可能落在 knee 之前，也可能在 knee 之後（延遲目標訂得寬時，knee 之後幾級的 p99 仍在目標內）；錯誤率目標內的最後一級也要一起比：百分位數只算成功的請求，受測服務從某一級起 503 增加時，延遲可能還在目標內而錯誤率已經超標。9.4 把 knee point 當成設計容量的上限，容量結論因此取 knee 之前最後一個 p99 持平的級、延遲目標內最後一級、錯誤率目標內最後一級三者中最低的那一級，9.6 的 headroom 從那一級算。coordinated omission 讓這兩項受到的影響不同。延遲目標內的負載換算成 production 的到達率時被估高：報告上延遲還在目標內的那一級，同樣的到達率在 production 下延遲已經超過目標。X_max 不受這個偏差影響，前提是 N 已經加到每秒跑完的 task 數 X 不再隨 N 增加：那時它是受測服務每秒處理得完的請求數，可以當成到達率的上界用；N 還沒加到那裡時，量到的停滯可能只是 N 給得不夠。

`wait_time` 設成 `constant_throughput(r)` 時，Locust 依上一輪花掉的時間調整停頓，讓每個使用者的 task 每秒至多執行 r 次；`constant_pacing(t)` 是每 t 秒至多一次（官方文件〈Writing a locustfile〉）。這是 closed model 的 pacing：吞吐量的上限是 N 乘以 r，而一輪 task 的時間超過 1÷r 時，工具沒有剩下的停頓可以縮短，那個使用者的速率就低於 r。官方文件舉的例子是：task 一輪超過 10 秒，吞吐量就低於設定值。所以 r 是上限，報告上的負載只有在量到的每秒 task 數等於 N 乘以 r 時才是設定的那個值。

pacing 讓 Locust 在一個範圍內接近 open model：選一個每人速率 r，讓 1÷r 遠大於延遲目標，再逐級增加 N，讓 N 乘以 r 等於這一級要的每秒 task 數（pacing 限制的是 task 的次數，一個 task 送 k 個請求時，每秒請求數是 N 乘以 r 再乘以 k）。受測服務還快的時候，每個使用者都在排定的時間送出請求，送出的負載等於設定值，量到的延遲沒有少算；某一級起量到的每秒 task 數低於 N 乘以 r，代表有使用者的一輪超過了 1÷r，從這一級起延遲開始少算，量到的延遲是 production 在同樣到達率下延遲的下界。1÷r 越長，越晚碰到這個點，代價是同樣的到達率要更多使用者，每個 worker 要排程的使用者跟著變多（〈worker 程序的檢查與 worker 數的量法〉）。延遲的尾端先撞到 1÷r：平均每秒 task 數還等於 N 乘以 r 時，p99 超過 1÷r 的那一小部分請求已經被延後。這段做法是從官方對 `constant_throughput` 的描述與 coordinated omission 的機制推出來的，沒有實跑比對過 open model 工具的結果。

pacing 涵蓋不了的範圍（受測服務的延遲目標接近 1÷r、到達率很高而 worker 數受限），改用 open model 的工具量延遲目標內的負載：[k6](/backend/09-performance-capacity/vendors/k6/) 的 `ramping-arrival-rate` executor，或 Gatling 的 `injectOpen`（做法在 [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)〈用 open model 的注入步驟寫出逐級加壓〉）。同一個服務用兩種工具量時，Locust 量到的 X_max 與 open model 工具量到的 knee 到達率可以互相對照。

## task 權重與 production 的操作分布

`@task(8)` 與 `@task(2)` 是相對權重：Locust 每次替使用者挑 task 時隨機抽，權重 8 的被挑中的機率是權重 2 的四倍（官方文件〈Writing a locustfile〉）。權重決定的是 task 被執行的次數比例，每個 task 送出的請求數不同時，endpoint 之間的請求數比例是權重乘以各 task 的請求數。所以從 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)〈Traffic shape 的五個維度〉的操作分布（read 與 write 的比例、各 endpoint 的 mix）換算權重時，先除掉每個 task 的請求數，再對到 `@task` 的數字。

closed model 讓權重之外還有一層效應：使用者在一個變慢的 task 上停留得比較久，同樣的 N 裡在等那個 endpoint 的使用者變多，挑其他 task 的使用者變少，所以一個 endpoint 變慢會拉低所有 endpoint 的每秒請求數。production 的使用者彼此獨立抵達，寫入變慢不會讓讀取的抵達變少。探測時每一級都要分開看各 endpoint 的每秒請求數：某一級起所有 endpoint 的吞吐量一起停住，而只有其中一個的延遲上升，飽和的是那個 endpoint 依賴的資源，其他 endpoint 的停滯是 closed model 造成的。這個效應是從 closed model 的機制推論的，沒有實跑量過它的大小。

業務裡兩種流量的高峰在不同時間出現，或延遲目標不同時，一組固定的權重量到的是兩種流量混在一起的平均。[9.C28 FanDuel：體育直播 + 投注的雙重峰值](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的直播與投注在同一場比賽同時到達峰值，而直播容忍的延遲遠比投注長，兩者要各自對照自己的延遲目標。Locust 的做法是兩種流量各寫一個 User class，`tick()` 回傳的 tuple 加上第三個元素 `user_classes`，可以指定這一刻要啟動哪幾個 User class（官方文件〈Configuration〉的〈Restricting which user types to spawn in each tick〉）。高峰錯開時，兩次執行各讓一種 class 逐級加壓、另一種固定在平常的使用者數，量出兩種高峰各自的 knee；高峰同時出現時，兩種 class 依峰值時的比例一起逐級加壓，各自的請求名稱分開讀延遲，看哪一種先超過自己的目標。

## worker 程序的檢查與 worker 數的量法

判讀之前，先確認施壓端在整段測試中沒有飽和：施壓端飽和時，報告上的吞吐量停住與延遲上升跟受測服務的上限長得一樣，每一個數字都混著施壓端自己的時間（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)）。closed model 讓這件事更難從報告分辨：Locust 沒有一個設定的到達率可以拿來比對送出的負載，worker 的延遲讓每個使用者送下一個請求的時間往後延，跟受測服務變慢的效果疊在一起。Locust 的 worker 有幾件特有的事要查：

- **一個 worker 程序只用一顆 CPU 核心**：Locust 的使用者跑在 gevent 的 greenlet 上（協程怎麼切換、monkey patch 換掉了哪些函式，見 [Gevent Monkey Patching](/backend/knowledge-cards/gevent-monkey-patching/)），一個 Python 程序裡的 greenlet 輪流執行，所以一個程序最多用滿一顆核心，官方建議每顆核心跑一個 worker 程序（官方文件〈Distributed load generation〉、〈Increase performance with a more efficient HTTP client〉）。施壓機有 4 顆核心而只跑一個 worker 時，整台的 CPU 顯示 25% 左右就是那個程序的上限；看的單位是每個 worker 程序的 CPU，不是整台機器的。Locust 的程序 CPU 超過 90% 時會在 log 印出 `CPU usage above 90%!`，訊息寫明這會限制吞吐量、讓延遲的量測不一致（原始碼 `locust/runners.py`）。`--processes` 讓一台機器 fork 出好幾個 worker 程序（官方文件〈Configuration〉標成實驗性、不支援 Windows）。
- **task 裡的 CPU 密集工作**：greenlet 只在等 I/O 時讓出執行權，一個使用者在 task 裡做 JSON 序列化、簽章、壓縮這類計算時，同一個程序裡其他使用者的回應已經到了也沒有人處理，等待的時間算進它們的延遲。官方的 CPU 警告處置列了改用 `FastHttpUser`（它用的 CPU 比 `HttpUser` 少得多）與檢查程式裡有沒有非預期的忙碌迴圈（官方原文寫 strange/infinite loops，官方文件〈Increasing the request rate〉）。
- **gevent 管不到的 client 函式庫**：`import locust` 時 Locust 自己呼叫 gevent 的 `monkey.patch_all()`（原始碼 `locust/__init__.py`，設了環境變數 `LOCUST_SKIP_MONKEY_PATCH` 才跳過），標準函式庫的 socket、ssl、time 因此都已經換成會讓出執行權的版本，locustfile 不必自己在第一行呼叫。gevent 補不到的是用 C 寫的 I/O：官方文件〈Testing other systems/protocols〉寫明，函式庫在編譯過的 C 程式碼裡做 I/O 時 gevent 無法替換它，整個 Python 程序會被卡住，結果是每個 worker 程序只跑得了一個使用者；gRPC 那個範例因此先呼叫 `grpc_gevent.init_gevent()`。這一類的樣子是從加壓一開始吞吐量就不隨使用者數增加，而 worker 的 CPU 很低，跟 CPU 密集工作的「CPU 滿了」分得開。
- **連線池與檔案描述元**：`HttpUser` 預設每個使用者有自己的連線池、跨 task 重用連線（官方文件〈Writing a locustfile〉），N 個使用者就對受測服務開 N 條以上的連線；worker 的檔案描述元上限或來源埠先用完時，失敗的請求帶著 `Too many open files` 或 `Cannot assign requested address`。
- **網卡**：回應很大或請求率很高時，施壓端的網路頻寬比 CPU 先到頂，官方文件〈Increasing the request rate〉建議同時看網路使用量與其他作業系統層的指標。

worker 數要量出來，數字依施壓機的規格、client 的種類、task 裡的計算量與回應大小而變，別人機器上的數字不能直接用。量法是用一個 worker 程序、同一個 client 種類與 task 結構，只把 endpoint 換成近乎零成本的那一個，打這個幾乎不做事的 endpoint（健康檢查、回固定內容的靜態頁面），逐級增加使用者數：這個 endpoint 在受測服務上的處理時間接近零，延遲開始上升、吞吐量停住或出現 CPU 警告的那一級，就是一個 worker 程序在這份 locustfile 下送得出的上限。task 裡的計算量與回應大小跟受測的 endpoint 不同時，再用受測的 endpoint 在受測服務還在線性區的負載下，比對 Locust 量到的延遲與受測服務入口量到的延遲：兩者的差距隨每個 worker 的使用者數變大時，那個使用者數就是這份 locustfile 的實際上限。需要的 worker 程序數是探測要到的最大使用者數除以這個上限，再留一段餘裕，讓最後一級也沒有任何一個 worker 接近上限；餘裕留多少依上限量測時的變異決定。

master 不執行任何使用者，只負責 web UI 與告訴 worker 什麼時候啟動或停止使用者（官方文件〈Distributed load generation〉）。`--expect-workers N` 搭配 `--headless` 時，master 等到 N 個 worker 連上才開始這次執行；它的預設值是 1（原始碼 `locust/argument_parser.py`），沒有設時第一個 worker 連上就開始加壓，使用者分到已連上的 worker，每個 worker 的使用者數比規劃的多，先碰到上限。執行中途才連上的 worker，master 會把使用者重新分配過去：原始碼（`locust/runners.py`）處理 worker 連上的那一段，在測試執行中會再呼叫一次 `start()`，不看 `--enable-rebalancing`；那個選項（標成實驗性）管的是 worker 失聯時要不要把它的使用者分給其他 worker。所以晚連上的 worker 之前那一段，負載集中在先連上的 worker，那一段量到的延遲可能混著施壓端的上限。一台機器上一個 master 加兩個 worker 的啟動指令、master 的 log，以及一次 worker 被判失聯（heartbeat 大約 4 秒沒送到）時那一次結果為什麼不能用，見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈master 與兩個 worker〉。

```bash
# 在 master 那台：等 4 個 worker 連上才開始，結果寫到 results/ 底下
locust -f locustfile.py --master --headless --expect-workers 4 \
  --host https://staging.example.com --csv results/doubling --csv-full-history

# 在每一台施壓機：每顆核心一個 worker 程序
locust -f locustfile.py --worker --master-host 10.0.0.5 --processes 4
```

讀者要改的位置：`--expect-workers 4` 填所有施壓機的 worker 程序總數；`--host` 填受測環境的入口，要跟延遲目標的量測點一致（打 CDN 還是 origin，在〈容量結論要記下的條件〉）；`results/doubling` 是輸出檔名的前綴；`10.0.0.5` 換成 master 的位址（佔位值）；`--processes 4` 填那台施壓機的核心數，`-1` 讓 Locust 自己偵測。

worker 把每個請求的延遲以大約兩位有效數字分桶計數（147 毫秒記成 150、3432 記成 3400），每隔約 3 秒把計數送給 master，master 把各 worker 的計數合在一起再算百分位數（原始碼 `locust/stats.py`、`locust/runners.py`）。所以分散施壓時的百分位數來自合併後的整體分佈，不是各 worker 的 p99 取平均（[Percentile](/backend/knowledge-cards/percentile/)）；代價是解析度只到兩位有效數字，相鄰兩級的 p99 差距小於這個解析度時分不出來。worker 送計數的間隔與歷史紀錄的十秒視窗，讓每一級開頭有十幾秒的讀數還混著上一級，跟 `spawn_rate` 的那一段一起略過。worker 跟受測服務在不同區域時，量到的延遲包含 worker 到受測服務的網路往返，探測的施壓機要放在跟延遲目標的量測點同一段網路上。

## 自訂 client 的連線池、逾時與重試

容量結論算的是受測服務在 production 的呼叫方式下處理得了多少，所以 client 的行為要接近 production 的呼叫端，差別會直接算進數字裡：

- **連線池**：production 的呼叫端是一個 BFF 或內部服務、用大小固定的共用連線池時，受測服務看到的連線數是那個池的大小；`HttpUser` 預設每個使用者一個池，N 個使用者開 N 條連線，受測服務的連線上限、每條連線的記憶體與 TLS 交握量都跟 production 不同。`HttpUser` 設 `pool_manager` 可以讓使用者共用一個 `urllib3.PoolManager`；`FastHttpUser` 設 `client_pool = HTTPClientPool(concurrency=K)` 讓全部使用者共用一個池，K 是整個池同時進行的請求上限（官方文件〈Writing a locustfile〉、〈Increase performance with a more efficient HTTP client〉）。兩種寫法照官方文件的範例組成如下（沒有實跑）：

  ```python
  from geventhttpclient.client import HTTPClientPool
  from locust import FastHttpUser, HttpUser
  from urllib3 import PoolManager


  class SharedPoolUser(HttpUser):
      abstract = True  # 只當基底 class，task 寫在繼承它的 User class 裡
      pool_manager = PoolManager(maxsize=50, block=True)  # 對每個 host 共用最多 50 條連線


  class SharedFastUser(FastHttpUser):
      abstract = True
      client_pool = HTTPClientPool(concurrency=50)  # 全部使用者共用，最多同時 50 個請求
  ```

  兩個 class 是要被繼承的片段：沒有 task 的 User class 沒設 `abstract = True` 時，Locust 啟動它會報 `No tasks defined`（原始碼 `locust/user/task.py`）。`50` 是佔位值，填 production 呼叫端連線池的大小；`PoolManager` 的 `maxsize` 是每個 host 那一個池的上限，打到幾個 host 就有幾個池。`FastHttpUser` 的類別屬性 `concurrency`（預設 10）是單一使用者 session 的上限：沒有給 `client_pool`、一般的 task 一次只送一個請求時，使用者只有一個 greenlet，用不到它；它只在 task 裡自己開 gevent pool 並行送請求時才有作用，給了 `client_pool` 時不生效（原始碼 `locust/contrib/fasthttp.py` 的說明）。共用的池小於使用者數時，請求先在 worker 這一端等連線，等待的時間算進 Locust 量到的延遲，受測服務那一端看不到；這時對照受測服務入口的延遲才分得出來。`urllib3.PoolManager` 的池只有設 `block=True` 時，池滿才讓請求在 worker 端等；預設的 `block=False` 在池滿時另開臨時連線，請求不排隊，連線數也限制不住（這是 urllib3 的行為，本篇沒有實跑）。
- **逾時**：`FastHttpUser` 的 `connection_timeout` 與 `network_timeout` 預設都是 60 秒（官方文件〈Increase performance with a more efficient HTTP client〉）；`HttpUser` 沿用 requests 的預設，沒有逾時，每個請求要自己傳 `timeout=`（原始碼 `locust/clients.py` 沒有替 `timeout` 設預設值）。production 的呼叫端在幾秒內就逾時的話，壓測裡一個慢請求讓使用者等到 60 秒或一直等下去，量到的是一個很高的延遲，production 上同一個請求已經失敗、讓呼叫端去做別的事；closed model 下這個使用者在這段時間不送請求，負載跟著下降。逾時設成跟 production 的呼叫端相同，量到的失敗比例與負載才對得上。
- **重試**：`FastHttpUser` 的 `max_retries` 預設是 0。production 的呼叫端有重試時，服務變慢、逾時增加時重試讓實際的負載上升，壓測沒有重試就量不到這個放大（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈設計責任〉）；在 task 裡照 production 的重試次數與退避寫出重試，或在結論裡註明沒有涵蓋。
- **自訂 protocol 的 client**：gRPC、WebSocket、message broker 這類不走 `HttpUser` 的 client，每次呼叫完要自己觸發 `request` 事件、帶上 `response_time`，Locust 的統計才算得到它（官方文件〈Testing other systems/protocols〉）。漏了觸發的那一類呼叫在統計裡不存在，每秒請求數與延遲都少算那一類呼叫，容量數字對應的負載比實際送出的小。

## 容量結論要記下的條件

容量探測的結論寫成條件句：「在這個配置下、同時在線多少個使用者、平均停頓多少秒、p99 低於多少毫秒的條件下，每秒成功處理多少個請求，先飽和的是哪一項資源，距離飽和點還剩多少餘裕（[Headroom Budget](/backend/knowledge-cards/headroom-budget/)）」（[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)〈概念定位〉、〈Saturation 文件化：容量地圖〉）。條件句裡「每秒成功處理多少個請求」填的是 knee 之前最後一個 p99 持平的級、延遲目標內最後一級與錯誤率目標內最後一級三者中最低的那一級，條件句裡同時寫出錯誤率目標。Locust 的單位是同時在線的使用者數，換算成到達率時，吞吐量的上限可以直接用，延遲目標內的負載照〈到達率型的服務：coordinated omission 與 constant_throughput 的上限〉註明是 closed model 量的、或用 pacing 量到哪一級為止。這個結論是 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的輸入，那一章拿 knee 與 headroom 換算成預期的峰值要幾個副本。

條件句的每一項都要能回溯到這次執行：

- **負載的寫法**：locustfile 的版本、User class 與 task 權重、`wait_time` 的種類與參數、`LoadTestShape` 的各級使用者數與秒數、`spawn_rate`、測試資料的來源與產生日期。
- **client**：種類（`HttpUser`、`FastHttpUser` 或自訂）與它的連線池、逾時、重試設定。
- **施壓端**：Locust 的版本、施壓機的台數、規格與每台的 worker 程序數。
- **受測環境**：配置與版本、測試期間的副本數與 autoscaler 設定、負載打在 CDN 還是 origin、下游哪些服務是 mock。探測期間固定副本數的理由，寫在 [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)〈探測之前要固定的條件：副本數與負載打在哪一端〉，那一段跟注入模型無關，Locust 一樣適用。

讀容量結論的人從結論回到這些條件，判斷得了一次結果是受測服務的容量訊號，還是測試設計造成的偏差（worker 飽和、client 的連線池或逾時跟 production 不同、測試資料讓快取命中率偏高、副本數中途改變）。欄位的組織方式照 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 的〈Evidence 欄位〉。

## 延遲上升或吞吐量停住時的排查順序

Locust 的容量探測量到延遲上升或吞吐量停在某個值時，有幾種成因會讓讀數不能直接當成受測服務的容量：worker 飽和或被卡住、client 在 worker 這一端排隊、送出的負載跟換算對不上。順序依一件事排：前一項沒有排除時，後一項的讀數還能不能用。排查之前先確認副本數固定、負載打在哪一端已經決定，否則每一項的讀數都對不上同一個配置。

1. **worker 程序的資源**：log 裡有沒有 `CPU usage above 90%!`（自動化的執行可以在 `quitting` 事件裡讀 `environment.runner.cpu_warning_emitted` 與 master 上的 `worker_cpu_warning_emitted`，原始碼 `locust/runners.py`），每個 worker 程序（不是整台機器）的 CPU，施壓機的網卡吞吐量與 `Too many open files` 這類錯誤，以及 Locust 量到的延遲與受測服務入口量到的延遲的差距。closed model 下沒有設定的到達率可以比，這一項沒排除時，量到的「吞吐量停住」可能是 worker 的上限；worker 飽和時後面每一項的讀數都混著 worker 的時間。
2. **gevent 被卡住**：吞吐量從加壓一開始就不隨使用者數增加、worker 的 CPU 又很低時，查 client 函式庫是不是在 C 程式碼裡做 I/O。這一項排在 client 設定之前，因為被卡住的程序裡每個使用者的延遲都是排隊等那個程序，連線池與逾時的讀數都不是它們自己的。
3. **client 在 worker 這一端的排隊與逾時**：共用連線池的大小（`HTTPClientPool` 的 `concurrency`、`block=True` 的 `PoolManager` 的 `maxsize`）小於使用者數時，Locust 量到的延遲高於受測服務入口量到的；逾時比 production 長時，慢請求變成很高的延遲而不是失敗。這一項排在送出負載的核對之前，因為在 worker 這一端排隊的請求讓 W 變長，Little's Law 的換算會把 worker 的排隊算成受測服務的。
4. **送出的負載與換算值**：每一級的每秒 task 數對照 N÷(W+Z)、用 pacing 時對照 N 乘以 r，各 endpoint 的請求數比例對照權重乘以每個 task 的請求數，每一級開頭的認證尖峰對照 `on_start`。對不上時，先找出原因（使用者還沒到齊、task 裡依回應決定要不要繼續的分支讓後面的請求沒送出、一個變慢的 endpoint 拉低其他 endpoint），knee 的判讀用每一級實際跑完的每秒 task 數 X，跟〈從每秒請求數與延遲判讀受測服務的狀態〉的讀法一致。
5. **knee 所在的一級與先飽和的資源**：前幾項都排除之後，照〈從每秒請求數與延遲判讀受測服務的狀態〉找出 knee 所在的那一級，再對照受測服務的資源指標找出先飽和的資源。這一項的結果就是容量結論。
6. **量到的容量與 production 經驗的差距**：受測服務的流量是到達率型時，先確認延遲目標內的負載是 closed model 量的、還是 pacing 量到哪一級為止，closed model 量的延遲會讓容量估高。其餘的高估來源要查兩件事：測試資料的 key 分佈與測試期間的快取命中率（key 的種類比 production 少時，同一批 key 反覆命中快取，請求很少走到資料庫），以及下游 mock 的回應時間跟真實依賴的延遲差多少。新服務或新區域沒有 production 的值可比時，拿這兩項對照 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 推出的 key 分佈與真實依賴的延遲，都做不到時，容量結論註明「未經 production 校準」。這一項在 knee 之後查，因為要先有 knee 與先飽和資源的結論，才知道高估了多少。

同樣看到 p99 變慢，用 Locust 做 regression gate 時，排查先分辨這是兩次執行條件不同造成的誤判、還是這一版的程式造成退化，要判斷的是擋不擋 release，順序與這裡不同，寫在 [Locust 在效能 regression gate 的用法：exit code 與門檻判定、預熱與 on_start 的請求、closed model 下的比較、custom client 回報的請求範圍、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/)。

## 相關章節與工具頁：飽和點的方法、workload model 與壓測工具選型

- [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：飽和的定義、ramp-up 的方法與各項資源的判讀，本篇的逐級加壓與狀態判讀都建立在它上面。
- [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)：起點的使用者數、`wait_time` 與 task 權重從這裡取。
- [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)：找到 knee 之後，定位是哪一項資源、哪一段程式先飽和。
- [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：把容量結論與 headroom 換算成預期峰值要的副本數。
- [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)：Locust 與 k6、JMeter、Gatling 在腳本的表達能力、支援的協定、施壓的規模與 CI 整合上的取捨。
- [Gatling 在容量探測的用法：open model 的逐級加壓、knee point 的判讀、施壓端的檢查、feeder 資料的分佈與排查順序](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)：用到達率注入找 knee、OSS 版分散施壓時延遲要從受測服務那一端讀的做法。
