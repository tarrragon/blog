---
title: "Locust 在效能 regression gate 的用法：exit code 與門檻判定、預熱與 on_start 的請求、closed model 下的比較、custom client 回報的請求範圍、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序"
date: 2026-10-28
description: "用 Locust 實作效能 regression gate 時的判斷：內建 exit code 之外的門檻怎麼在 quitting 事件裡判定、登入與預熱的請求怎麼混進統計、closed model 讓退化落在延遲還是吞吐量，以及 gate 失敗時怎麼把誤判和真正的退化分開"
weight: 1
tags: ["backend", "reliability", "vendor", "locust", "load-test", "release-gate"]
slug: "locust-performance-regression-gate"
---

用 Locust 做效能 regression gate 的人，要判斷的是這一版能不能過 release gate：這一版比基準版本慢了沒有、慢的幅度是否超出雜訊、要不要擋下。這篇整理這個判斷在 Locust 上的做法：Locust 內建的 exit code 只反映「這次執行有沒有任何失敗的請求或沒有處理的例外」，[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/) 的絕對門檻、相對退化與統計顯著性要由團隊在 `quitting` 事件裡或 Locust 之外自己判定；判定程式讀的統計怎麼取（整體與單一 endpoint、百分位數的分桶精度、回應內容的驗證）；ramp-up 期間與 `on_start` 裡的登入請求怎麼混進統計、怎麼排除；Locust 只有 closed model（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)），前後兩版比較時退化分別出現在延遲與吞吐量的哪一邊；用 custom client 測非 HTTP 的協定時，client 沒有回報請求的那一類呼叫在 gate 裡完全沒有訊號；PR 與 nightly 各跑一份測試時各自抓得到、抓不到哪一類退化；Locust 的 CSV 與 HTML report 之外還要記下哪些執行條件；gate 失敗時依序排除哪幾種誤判，才把差距歸給這一版的變更。baseline 的來源、門檻的設法與 variance 控制是 6.13 的內容，本篇只寫它們在 Locust 上的做法。Locust 的安裝、locustfile 的完整 API 與 hosted 版本在 [Locust 官方文件](https://docs.locust.io/en/stable/)；同一個工具用來找受測服務飽和點、估算要加多少機器的寫法在 [Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/)。

## Locust 在 regression gate 裡負責的環節：產生負載與內建的 exit code

效能 regression gate 比較這一版與基準版本（baseline）在同一組負載下的延遲、錯誤率與吞吐量，退化超過門檻時擋下 release（[Release Gate](/backend/knowledge-cards/release-gate/)）。Locust 用 Python 寫的 locustfile 描述負載：一個 User class 是一種虛擬使用者，class 裡用 `@task` 標記的方法是它會做的事，task 的權重決定每種事被挑中的比例，`wait_time` 決定做完一個 task 之後停多久；執行時 `-u` 指定同時在線的使用者數上限，`-r` 指定每秒啟動幾個使用者，`-t` 指定執行多久（官方文件〈Configuration〉）。Locust 在 gate 裡做兩件事：照 locustfile 產生負載、記錄每一個請求的延遲與成敗；執行結束時決定 process 的 exit code，CI 依這個 exit code 判斷這一步成功或失敗。

內建的 exit code 只看失敗與例外有沒有發生。官方文件〈Running without the web UI〉寫明，執行中有任何一個失敗的請求時，Locust 以 `--exit-code-on-error` 的值結束（預設 1）；HTTP 回應碼 400 以上算失敗（官方文件〈Writing a locustfile〉的〈Validating responses〉）。Locust 原始碼 `locust/main.py` 的 `shutdown()` 依序判定三件事：有失敗的請求、或 task 裡有未處理的例外（unhandled exception）時，用 `--exit-code-on-error` 的值；兩者都沒有、而 event listener 這類 greenlet（gevent 的輕量協程，Locust 的每個虛擬使用者與事件處理都跑在 greenlet 裡，見 [Gevent Monkey Patching](/backend/knowledge-cards/gevent-monkey-patching/)）裡有未處理的例外時，用 2；三者都沒有時用 0。這個判定沒有門檻：一萬個請求裡失敗一個，exit code 就是 1；全部成功而 p95 延遲變成兩倍，exit code 是 0（有失敗時 1、受測服務變慢而沒有失敗時 0、`--exit-code-on-error` 換值的實測，見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈內建的 exit code：有失敗、沒有失敗但變慢〉）。執行時加了 `--reset-stats`（下文〈預熱與量測區間：--reset-stats 與 on_start 裡的請求〉）時，清空統計的那一刻也清掉已經記下的失敗（`stats.errors`），ramp-up 期間的失敗因此不再影響 exit code；task 例外的紀錄（`runner.exceptions`）不在清空的範圍內。所以 Locust 的 exit code 本身只是一道「零失敗」的檢查，6.13 的三種判讀都要另外寫。

官方文件給的做法是在 `quitting` 事件（Locust process 結束之前觸發）的 listener 裡讀這次的統計、自己設定 `environment.process_exit_code`；設了這個值之後，Locust 用它取代內建的判定（Locust 原始碼 `locust/main.py` 的 `shutdown()` 先看 `process_exit_code`，沒有設定才回到「有沒有失敗」）。三種判讀在這個機制上的做法不同。絕對門檻是 listener 拿統計值跟寫死的數字比。相對退化要拿到基準版本的值：listener 是一般的 Python 程式，執行時可以讀一份基準值的檔案，把門檻寫成「基準 p95 乘以 1.10」，換到的是不必另寫比較程式，付出的是基準值要有地方保存、每次接受新的基準時要更新。統計顯著性要多次執行的樣本，單次執行的 listener 做不到，要由團隊另寫一支程式讀這一次與基準版本那幾次的量測、算出分佈的差異，下文稱它跨次比較的程式。

跨次比較的程式在 Locust 上有官方文件化的輸入可讀：`--csv <前綴>` 在執行期間寫出四個 CSV 檔，其中 `<前綴>_stats.csv` 是整次執行每一個 endpoint 一列再加一列 Aggregated 的統計，`<前綴>_stats_history.csv` 是執行期間持續附加的時間序列（官方文件〈Configuration〉的〈Save test statistics in CSV format〉；附加的間隔在原始碼 `locust/stats.py` 的 `CSV_STATS_INTERVAL_SEC` 是 1 秒；官方文件同一頁有一處寫 2 秒、選項表寫 1 秒）；一次 `--csv` 的實際輸出、`_stats.csv` 是結束前最後一次寫入的快照而比終端機的統計表少一截，以及不加 `--csv-full-history` 時 `_stats_history.csv` 各欄的累積方式，實測見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈headless 執行、終端機的統計表與 CSV〉；`--json` 在結束時把最終統計以 JSON 印到 stdout。這兩種輸出裡的百分位數都經過〈quitting listener 的寫法：統計的範圍、百分位數的分桶與回應的驗證〉的分桶那一項講的分桶，精度有限；要精確的延遲分佈時，跨次比較的程式改讀受測服務那一端的 histogram 型延遲指標（[Percentile](/backend/knowledge-cards/percentile/) 的〈設計責任〉）。

## quitting listener 的寫法：統計的範圍、百分位數的分桶與回應的驗證

listener 讀的統計是 `environment.stats`：`stats.total` 是全部請求合起來的統計，`stats.get(<name>, <method>)` 是單一 endpoint 的統計，兩者都提供 `fail_ratio`、`avg_response_time`、`get_response_time_percentile(<0 到 1 的比例>)`、`num_requests` 與 `total_rps`。官方文件的範例只判 `stats.total`，下面這段改成依關鍵流程各自判定，並讀一份基準值：

```python
import json
import logging
import os

from locust import events
from locust.runners import WorkerRunner

# 這次 gate 要比對的關鍵流程：(HTTP method, 請求名稱)
# 命令列只指定部分 User class 時，這裡列的流程要在那些 class 的 task 裡，
# 否則該流程的 num_requests 是 0，gate 以缺少資料結束
GATED = [("POST", "/checkout"), ("GET", "/item")]

EXIT_REGRESSION = 5    # 團隊自訂：有門檻不成立（避開內建判定用的 1 與 2）
EXIT_INCONCLUSIVE = 3  # 團隊自訂：施壓端的 CPU 超過警告門檻，結果不代表受測服務
EXIT_MISSING_DATA = 4  # 團隊自訂：缺基準值或缺某個流程的請求，判定不完整

def load_baseline():
    path = os.environ.get("GATE_BASELINE")
    if not path:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None

@events.quitting.add_listener
def _(environment, **kw):
    runner = environment.runner
    if isinstance(runner, WorkerRunner):
        return  # worker 每隔幾秒就把統計送給 master 並清空，判定交給 master
    # 施壓端的 CPU 超過門檻時，量到的延遲與吞吐量都混著施壓端的時間，門檻的判定不採用
    if runner.cpu_warning_emitted or runner.worker_cpu_warning_emitted:
        logging.error("gate inconclusive: load generator CPU usage exceeded the warning threshold")
        environment.process_exit_code = EXIT_INCONCLUSIVE
        return
    regressions, missing = [], []
    baseline = load_baseline()
    if baseline is None:
        missing.append("baseline file missing or unreadable")
        baseline = {}
    for method, name in GATED:
        key = f"{method} {name}"  # 基準值檔的鍵，例如 "POST /checkout"
        # 用 entries.get 查：stats.get 對不存在的名稱會建一個空項目，空項目會寫進 _stats.csv
        entry = environment.stats.entries.get((name, method))
        if entry is None or entry.num_requests == 0:
            # 沒有任何請求記錄在這個名稱下：gate 對這個流程沒有訊號
            missing.append(f"{key}: no requests recorded")
            continue
        if key not in baseline:
            missing.append(f"{key}: no baseline value")
            continue
        if entry.get_response_time_percentile(0.95) > baseline[key]["p95_ms"] * 1.10:
            regressions.append(f"{key}: p95 regressed")
        if entry.fail_ratio > 0.01:
            regressions.append(f"{key}: failure ratio above 1%")
    floor = baseline.get("total_rps_floor")
    if floor is None:
        missing.append("no baseline throughput floor")
    elif environment.stats.total.total_rps < floor:
        regressions.append("throughput below floor")
    for r in regressions:
        logging.error("gate failed: %s", r)
    for m in missing:
        logging.error("gate missing data: %s", m)
    if regressions:
        environment.process_exit_code = EXIT_REGRESSION
    elif missing:
        environment.process_exit_code = EXIT_MISSING_DATA
    # 全部通過時不設定，exit code 交回 Locust 內建的判定：有任何失敗的請求（含登入）就是 --exit-code-on-error 的值
```

這段照官方文件〈Running without the web UI〉的〈Controlling the exit code of the Locust process〉範例、`locust.stats` 的 API 與原始碼 `locust/runners.py` 的 `cpu_warning_emitted`、`worker_cpu_warning_emitted` 兩個屬性組成，這一段沒有實跑；只判 `stats.total` 的最小版 listener 實際跑過，`process_exit_code` 設成 0 時蓋掉內建判定、worker 上的統計在結束時是空的（印出 `p95 0 ms`），這兩件事的實測見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈quitting 事件裡的門檻判定〉與〈master 與兩個 worker〉；這兩個屬性定義在所有 runner 共用的基底類別 `Runner` 的 `__init__` 裡，單機執行的 `LocalRunner` 上也有，`worker_cpu_warning_emitted` 在單機執行時一直是假。`GATED` 的兩列是佔位值，填的是 locustfile 裡實際送出的 method 與請求名稱；`GATE_BASELINE` 是 CI 傳進來的環境變數，值是基準值檔的路徑。

基準值檔是一個 JSON 物件，每個流程一個鍵，鍵寫成 method、一個空白、請求名稱（`"POST /checkout"`），值是 `{"p95_ms": <毫秒>}`，另有一個 `total_rps_floor` 鍵放吞吐量下限。CI 從基準版本那一次的 `_stats.csv` 產生這份檔：`Type` 欄是 method、`Name` 欄是請求名稱，兩欄串起來是鍵，`95%` 欄的值是 `p95_ms`；`Request Count` 是 0 的列跳過，那是某段程式用 `stats.get` 查了不存在的名稱而建出的空項目，百分位數欄寫的是 `N/A`（原始碼 `locust/stats.py` 的 `EntriesDict` 與 `_percentile_fields`），上面的 listener 因此改用 `stats.entries.get` 查；`total_rps_floor` 是 Aggregated 那一列的 `Requests/s` 減去雜訊範圍（欄名出自原始碼 `locust/stats.py` 的 `requests_csv_columns`）。`1.10`（相對退化 10%）與 `0.01`（失敗比例 1%）是佔位的門檻，門檻的取法見 6.13 的〈Regression 判讀方法〉；吞吐量下限的取法寫在〈closed model 下前後兩版的比較：延遲與吞吐量〉。

listener 的 exit code 有四種結果，判定的優先序跟〈gate 失敗時的排查順序〉一致：施壓端的 CPU 超過警告門檻時最先判，以 `EXIT_INCONCLUSIVE`（3）結束、不看門檻，因為施壓端飽和時延遲與吞吐量的讀數都混著施壓端的時間，門檻不成立也不能當成退化的證據；其次是有門檻不成立，以 `EXIT_REGRESSION`（5）結束；再其次是缺基準值或某個流程沒有請求，以 `EXIT_MISSING_DATA`（4）結束；都沒有時不設定，交回內建的判定。門檻不成立排在缺資料之前，是因為有資料的流程已經量到退化，這個證據不因為別的流程缺資料而失效。3、4、5 都是團隊自己訂的約定，Locust 沒有「無結論」「缺資料」或「門檻不成立」的 exit code。退化不用 1，是因為 1 是 `--exit-code-on-error` 的預設值，內建判定在「有失敗的請求或 task 例外」時也回 1；兩者共用 1 時，CI 分不出這次是門檻不成立還是零星的失敗。號碼分開之後，CI 依 exit code 走不同的處置：1 是有失敗的請求或未處理的例外（包括 `on_start` 裡的例外：`User.run()` 對它觸發 `user_error`，記進 `runner.exceptions`，原始碼 `locust/user/users.py`）、2 是 listener 這類 greenlet 裡的例外、3 是重跑而不當成退化的證據（處置寫在〈gate 失敗時的排查順序〉的施壓端那一項）、4 是補上基準或修好 locustfile 再跑、5 是照退化處理。執行時也不把 `--exit-code-on-error` 設成 3 到 5，否則內建判定的結果會跟 listener 的約定撞號。

基準值檔不存在、讀不出 JSON、或少了某個流程的鍵時，上面的寫法以缺資料結束並在 log 寫出原因。不這樣處理的話，listener 在讀檔或取鍵的那一行拋出例外，Locust 把例外記進 log、listener 後面的判定都沒有執行；這時 exit code 由內建的判定決定，有失敗的請求時是 `--exit-code-on-error` 的值，沒有時是 2（`event.py` 的 `fire()` 把 listener 的例外記成 greenlet 裡未處理的例外）。兩種結果都不是 0，gate 仍然擋下，但 log 裡只有一段 traceback，看 CI 結果的人分不出這是退化還是少了基準。寫法背後的其他考量如下：

- **全部通過時的 exit code 設定**：官方範例的最後一個分支把 `process_exit_code` 設成 0，這樣做的結果是失敗比例低於 1% 的執行一律通過，內建的「零失敗」檢查被設 0 的那一行關掉了。上面的寫法在通過時不設定，exit code 交回內建的判定，而內建的判定看的是全部請求，包括 `on_start` 裡的登入請求與不在 `GATED` 裡的請求。所以不設 0 時，gate 生效的失敗門檻是「全部請求零失敗」，`fail_ratio > 0.01` 那一行只在某個關鍵流程失敗超過 1% 時多印一條指出流程的訊息；加了 `--reset-stats` 時，ramp-up 期間的失敗在清空統計時一起清掉，不算進這個判定。兩種都成立，差在 gate 容不容許零星的失敗：受測環境穩定到零失敗是常態時，不設定，零星失敗本身就是要看的訊號；受測環境偶爾有網路抖動、或登入走的外部服務偶爾失敗而團隊不想讓它擋下 release 時，改成自己判定：依名稱把要容許的請求（登入）排除，對其餘請求逐一檢查失敗數或失敗比例，全部成立、而且 `environment.runner.exceptions` 是空的時候，才把 `process_exit_code` 設成 0。設 0 會蓋掉內建判定裡 task 例外的那一半：task 在送出請求之前就拋出例外時，那一輪沒有任何請求進統計，失敗比例照樣是零，只有 `runner.exceptions` 記得這件事（原始碼 `locust/main.py` 的 `shutdown()`）。這個選擇要寫在 locustfile 裡讓 code review 看得到，因為兩種寫法在 gate 的報告上看起來一樣。
- **依流程各自判定，不只判 `stats.total`**：`stats.total` 由請求量最大的 endpoint 主導，一個每秒幾千次、回應很快的商品頁會把結帳流程的退化平均掉。依流程判定之後，失敗的那一條訊息也直接指出是哪一個流程退化。`stats.get` 的鍵是請求名稱，URL 帶著商品編號這類變動參數時，每個不同的 URL 各自成為一個統計項目，`stats.get("/item", "GET")` 找不到任何請求；locustfile 要用 `name=` 參數把同一類 URL 歸到同一個名稱底下（官方文件〈Writing a locustfile〉的〈Grouping requests〉）。
- **百分位數的分桶精度**：Locust 把每個請求的延遲先四捨五入成約兩位有效數字再存進分佈，147 毫秒存成 150、3432 毫秒存成 3400（官方文件〈Configuration〉的〈Customizing response time bucketing〉），百分位數從這個分佈算出來。相鄰兩個桶在每個數量級的開頭（100、1000 毫秒附近）相差約 10%，接近下一個數量級時相差約 1%（從上面的分桶規則推算）。p95 落在 100 到 200 毫秒之間時，10% 的相對門檻跟分桶的間距同一個量級，5% 的退化可能被歸進同一個桶而量不出來，也可能剛好跨過桶的邊界而被放大成 10%。官方文件允許替換分桶函式換到更細的精度；替換之後基準版本與這一次要用同一個函式，否則兩邊的百分位數不能比。
- **回應碼 400 以下都算成功**：受測服務回 200 而內容是錯誤頁面、或回了空的結果時，Locust 把它記成成功，而且這類回應通常比正常的回應快，退化的版本因此量到更低的延遲。業務關鍵的請求用 `catch_response=True` 檢查回應內容，不符合時呼叫 `response.failure()` 記成失敗（官方文件〈Validating responses〉），gate 的失敗比例才反映受測服務實際的成敗。
- **分散式執行時由 master 判定**：分散式執行時，worker 把統計送回 master，master 的 `environment.stats` 是全部 worker 合起來的統計（官方文件〈Distributed load generation〉）。worker 大約每 3 秒送一次（原始碼 `locust/runners.py` 的 `WORKER_REPORT_INTERVAL`），送出的同時清空自己的統計（`locust/stats.py` 的 `get_stripped_report()`），所以 worker 結束時觸發 `quitting`，它手上只剩最後一次回報之後、不到約 3 秒內完成的請求。關鍵流程在這幾秒裡有沒有請求，看那個流程的請求率：每個 worker 每秒只送幾個結帳請求、或測試在使用者停止之後才結束時，常常一筆都沒有。listener 不在 worker 上返回的話，這些 worker 會以缺資料結束，其餘的 worker 拿幾秒的樣本判門檻，結果各不相同；listener 因此在 worker 上直接返回，CI 讀的是 master 那個 process 的 exit code。

## 預熱與量測區間：--reset-stats 與 on_start 裡的請求

Locust 的統計從執行開始就累積，ramp-up 期間的請求也算在裡面；`-t` 的計時同樣從執行開始算，不是從所有使用者啟動完成之後算（官方文件〈Running without the web UI〉）。ramp-up 期間受測服務在預熱：JIT 還沒編譯熱路徑、cache 還沒填滿（[Cache Warmup](/backend/knowledge-cards/cache-warmup/)）、連線池還在建立連線，延遲比穩態（[Steady State](/backend/knowledge-cards/steady-state/)）高。這些請求算進 listener 讀的統計時，量到的 p95 會隨 ramp-up 佔整次執行的比例而變，兩次執行只要 `-u`、`-r`、`-t` 任一個不同，比例就不同。這是 6.13〈Variance 控制〉表裡 cold start 那一列在 Locust 上的樣子。

Locust 內建的排除方式是 `--reset-stats`：所有使用者啟動完成時清空統計，之後的請求才算進最終的統計（官方文件〈Configuration〉；分散式執行時 master 與每個 worker 都要加這個參數）。啟動完成的時間是 `-u` 除以 `-r` 秒左右，量測區間因此是 `-t` 減去這段時間，`-t` 要設得夠長，讓量測區間在扣掉 ramp-up 之後仍然有足夠的樣本。`--reset-stats` 排除的是施壓端啟動使用者的那一段，受測服務的預熱時間可能比它長：JIT 編譯與 cache 填滿要的時間由受測服務決定，ramp-up 只花十秒時，預熱的後半段仍然落在量測區間裡。這種情形下有兩種做法：讓 ramp-up 本身拉長到涵蓋受測服務的預熱，或讓跨次比較的程式讀受測服務那一端 histogram 型的延遲指標、只取預熱結束之後的那一段時間。

`_stats_history.csv` 切不出預熱結束之後的那一段：不加 `--csv-full-history` 時它只有 Aggregated 一列，那一列的百分位數從執行開始累積；加了之後每個請求名稱各有一列，百分位數是最近約十秒的視窗（官方文件〈Save test statistics in CSV format〉，原始碼 `locust/stats.py` 的 `_stats_history_data_rows`）。兩種都是算好的百分位數，幾列之間不能相加或平均成一段時間的百分位數（[Percentile](/backend/knowledge-cards/percentile/) 的〈設計責任〉）。Locust 量到的延遲怎麼跟受測服務入口量到的延遲對照、兩者的差距代表什麼，寫在 [Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/) 的〈worker 程序的檢查與 worker 數的量法〉。

`on_start` 是 User class 的方法，每個虛擬使用者啟動時呼叫一次（官方文件〈Writing a locustfile〉的〈on_start and on_stop methods〉），常用來登入、取得 token。`on_start` 裡用 `self.client` 送出的請求跟 task 裡的請求一樣記進統計，所以沒有排除時，登入流程的延遲與失敗混在 `stats.total` 裡。登入流量混進 gate 有兩個後果。一個是歸因錯誤：登入多半經過另一個服務（身分驗證服務或外部的身分提供者（IdP）），那個服務這幾天變慢了，`stats.total` 的 p95 上升，gate 把它讀成這一版的退化；反過來，這一版改壞了某個 API，而登入請求的比例拉低了整體的 p95，退化被稀釋。另一個是比例隨參數變動：每個使用者只登入一次，登入請求佔總請求的比例由 `-u` 與執行時間決定，PR 與 nightly 用不同的參數時，兩邊的 `stats.total` 裡登入的比重不同。處置有兩層，主要的一層是名稱：登入請求用 `name=` 給它一個獨立的名稱，讓 listener 依流程判定時不讀它。輔助的一層是 `--reset-stats`：大部分使用者的 `on_start` 在 ramp-up 期間完成，那些登入請求在清空統計時一起清掉。這一層清不乾淨：`spawning_complete` 在所有使用者的 greenlet 啟動之後就觸發，不等 `on_start` 完成，那一刻 `on_start` 還沒做完的使用者（最後幾批居多，登入慢時更早的幾批也算）在清空之後才完成登入（實測：`-u 20 -r 5` 加 `--reset-stats` 時，清空之後還留著 5 筆登入，見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈--reset-stats 與 on_start 的請求〉；原始碼 `locust/runners.py` 的 `spawn_users` 與 `_start`），它們的登入請求仍然留在 `stats.total` 裡。

登入失敗的影響比登入變慢大，因為它連帶改變 gate 的其他讀數。`on_start` 拋出例外時，那個使用者的 greenlet 就結束了（原始碼 `locust/user/users.py` 的 `run()`），例外記進 `runner.exceptions`，`--reset-stats` 不清這一份紀錄。死掉的使用者補不補回看時機：ramp-up 期間（以及每次 `LoadTestShape` 改變目標時）死掉的，下一步分派依存活的 greenlet 計算還差幾個，會補上新的使用者；啟動完成之後死掉的不再補回（原始碼 `locust/runners.py` 的 `LocalRunner._start` 與 `user_classes_count`）。所以後果分兩種：登入偶爾失敗時，人數多半在 ramp-up 期間補回，`runner.exceptions` 照樣累積；登入一直失敗時，補上的使用者也登入失敗，實際在跑的使用者少於 `-u`，`total_rps` 跟著下降，listener 把它判成吞吐量的退化；`on_start` 沒有拋例外、但沒有拿到 token 時，使用者照樣跑 task，關鍵流程的請求回 401，失敗比例上升，listener 把它判成關鍵流程的退化。兩種情形的成因都在身分驗證服務，不在這一版的變更，排查時的比對方式寫在〈gate 失敗時的排查順序〉的執行條件那一項。用 `LoadTestShape`（locustfile 裡定義的類別，它的 `tick()` 依執行時間回傳這一刻的使用者數與啟動速率）在執行中改變使用者數時，`--reset-stats` 的效果又不同：每一次調整完使用者數都觸發一次 `spawning_complete` 事件（Locust 在使用者數到達目標時觸發的事件），`--reset-stats` 在每一次觸發時都清空統計（原始碼 `locust/runners.py` 的 `on_spawning_complete`），最終的統計只剩最後一級；新加進來的使用者的 `on_start` 也落在各級的量測區間裡。所以用 `LoadTestShape` 跑 gate 時不加 `--reset-stats`，登入請求只靠名稱排除，預熱改用上面受測服務那一端的做法。

## closed model 下前後兩版的比較：延遲與吞吐量

Locust 只有 closed model：同時在線的使用者數由 `-u` 決定，每個使用者做完一個 task、等完 `wait_time` 才挑下一個；官方文件寫明 wait time 只能限制吞吐量，不會為了達到目標啟動新的使用者（官方文件〈Writing a locustfile〉的〈wait_time attribute〉）。受測服務變慢時，每個使用者一輪的時間變長、送出的請求變少，施壓端送出的請求率跟著受測服務的速度下降（機制見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉）。所以 regression gate 比較前後兩版時，這一版變慢的時間分成兩處表現：延遲上升，以及每秒請求數下降；只設延遲門檻的 gate 只看得到延遲上升的那一處，延遲還在門檻內、而每秒請求數已經下降的退化會通過；listener 要加上吞吐量的下限，就是上面範例裡 `total_rps_floor` 那一條。

退化落在延遲與吞吐量的哪一邊，由 `wait_time` 的設法決定：

- **`between`、`constant`、`poisson` 這類停頓**：`poisson` 的停頓從指數分布抽樣，task 的開始時間只在一輪的執行時間遠小於 1 ÷ rate 時才近似 Poisson 抵達，而停頓仍然加在 task 做完之後，所以它跟另外兩種一樣是 closed model（官方文件〈wait_time attribute〉）。一輪的時間是 task 的執行時間加上停頓，受測服務一變慢，一輪就變長，吞吐量立刻下降，延遲上升的幅度因為請求變少而比 open model 下小。退化同時出現在兩個指標上，延遲與吞吐量兩條門檻都需要。
- **`constant_throughput`、`constant_pacing` 這類 pacing**：Locust 依上一輪花掉的時間調整停頓，讓每個使用者每秒至多做設定次數的 task（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的 pacing 那一段）。pacing 限制的是 task 的次數，官方文件寫明 wait time 作用在 task 上、不是請求上，一個 task 送出兩個請求時，每秒請求數是 task 速率的兩倍（〈wait_time attribute〉）。受測服務變慢、而一輪的時間還短於設定的間隔時，Locust 縮短停頓補回來，每秒 task 數維持在設定值，退化主要出現在延遲上；一輪的時間超過設定的間隔時，那一輪的停頓是零，下一輪因此延後開始。這個計算逐輪進行、不補回錯過的時段（原始碼 `locust/user/wait_time.py`），所以平均延遲還短於間隔、而尾端少數幾輪已經超過時，那幾輪的延後就讓吞吐量小幅下降，退化越大下降越多。pacing 下的吞吐量門檻因此對小幅退化的訊號很弱，主要靠延遲門檻抓；gate 報告上每秒 task 數一直等於使用者數乘以設定的速率（每秒請求數等於這個值乘以每個 task 的請求數），才代表這次執行送出的負載是設定的那個值。

吞吐量的下限不能直接設成基準版本量到的值：每秒請求數本身也有雜訊，門檻等於基準值時，大約一半的執行會因為隨機的波動低於它而失敗，所以下限是基準值減去同一個版本重跑時每秒請求數的波動範圍（取法見〈gate 失敗時的排查順序〉的雜訊範圍那一項）。前後兩版的 `-u`、`-r`、`wait_time` 與 task 權重都要相同，否則每秒請求數與延遲的組合不同，差距不能歸給這一版的變更。

closed model 量到的延遲比 open 型流量的使用者會遇到的延遲低：使用者在等回應時不送下一個請求，production 裡那些照樣會抵達的請求在服務外排隊的時間沒有被量到（coordinated omission，見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉）。面向公眾的 API 用 Locust 做 gate 時，同一個退化在 gate 上量到的延遲上升小於 production 上的上升，被壓小的幅度可能落到相對門檻或雜訊範圍以下，gate 的偵測靈敏度因此比門檻的數字看起來低。處置有兩種：門檻依 production 上要擋的退化幅度，換算成 gate 上同一個退化會量到的幅度再設。換算的比例用一次刻意的注入量出來：在 gate 環境的受測服務裡加進一段會佔用服務資源的額外工作（每個請求多做 X 毫秒的 CPU 計算），X 取「讓基準版本的 p95 增加 production 上要擋的那個百分比所需的每請求 CPU 毫秒數」。先用 Locust 照 gate 的參數量一次 p95 的上升量，再用支援 open model 的負載工具量一次，固定到達率取注入之前、基準版本那一次 Locust 量到的平均每秒請求數（注入之後 Locust 的請求率已經被壓低，拿它當到達率，兩邊比的就不是同一個負載）。open model 工具的注入率單位多半是每秒抵達的使用者或 session，換算成每秒抵達數時，用「每秒請求數 ÷ 每個 session 的請求數」，而且兩邊跑的請求組合要相同。Locust 的上升量除以 open model 的上升量就是比例，production 上要擋的退化幅度乘以這個比例，是 gate 上的門檻；這一步假設 production 的資源利用率跟 gate 環境相同，利用率不同時 open model 下的排隊放大也不同，比例要在跟 production 利用率相近的負載下量。比例會隨注入量改變：受測服務越接近飽和，open model 下的排隊放大越多，所以 X 要取要擋的那個幅度，換一個幅度要重量。低負載、`wait_time` 有停頓時量到的比例接近 1 是正確的結果：受測服務離飽和還遠，open model 下也幾乎沒有排隊，兩種模型的延遲上升本來就相近。注入的工作要佔用服務資源：受測服務還沒碰到資源上限時，單純的 sleep 在兩種模型下都讓 p95 上升同樣的 X，量不出 closed model 壓小的那一段（這個量法從兩種模型的機制推出，本篇沒有實跑；比例另外隨使用者數、`wait_time` 與受測服務離飽和多遠而變，換了參數要重量）；或讓 gate 的延遲判讀改用固定到達率的量法，Locust 這邊用 pacing 讓每秒 task 數固定（只在一輪的時間短於設定的間隔時成立，超過之後 pacing 跟一般的 closed model 一樣減壓），或改用支援 open model 的負載工具量延遲。

## custom client 與 gate 讀得到的請求

Locust 內建的 `HttpUser` 與 `FastHttpUser` 只支援 HTTP；要測 gRPC、資料庫、訊息佇列這類協定時，團隊把協定的 client library 包成一個 custom client，在每次呼叫完成之後觸發 Locust 的 `request` 事件，傳入請求類型、名稱、延遲、回應長度與例外，Locust 才把這次呼叫記進統計（官方文件〈Testing other systems/protocols〉）。這個事件是 custom client 與 gate 之間唯一的接點：client 漏了觸發，那一類呼叫在 `environment.stats` 裡完全不存在，listener 讀不到它的延遲也讀不到它的失敗。常見的漏法有三種：只在成功的路徑觸發、例外的路徑直接往外拋，失敗沒有記進統計，失敗比例看起來是零；client 有多個方法而只有部分方法包了觸發，沒包的方法退化時 gate 沒有訊號；延遲的計時範圍不對，把重試、連線建立或序列化算進或排除，前後兩版若有一版改了 client 的這一段，差距會被讀成受測服務的退化。

漏掉的那一類在 gate 上的樣子是「通過」：`stats.get` 對一個沒有任何請求的名稱建出並回傳一個空的統計項目，它的 p95 是 0、失敗比例是 0，跟所有門檻比都成立。所以上面的 listener 在判定任何門檻之前先檢查 `num_requests`，關鍵流程的請求數是零時以缺資料（`EXIT_MISSING_DATA`）結束；這一條檢查擋住的是 client 漏觸發、`name=` 寫錯與 task 被 `--tags` 篩掉這幾種情形，它們的共同點是 gate 對那個流程沒有任何資料。

custom client 另一個要確認的是 client library 能不能被 gevent 的 monkey patch 改寫成非阻塞。gevent 是 Locust 用來在一個 process 裡同時跑大量虛擬使用者的協程函式庫：每個虛擬使用者是一個 greenlet，遇到網路 I/O 時讓出執行權給其他使用者；monkey patch 指 gevent 在執行期間把標準函式庫裡阻塞式的 I/O（`socket` 這類）換成會讓出執行權的版本。Locust 在 `import locust` 時自己做 monkey patch（原始碼 `locust/__init__.py`），純 Python、經由標準函式庫 `socket` 做 I/O 的 library 不需要另外處理，而在 C 擴充模組裡直接做 I/O 的 library patch 不到，一個呼叫會卡住整個 Locust process，結果是每個 worker 只剩一個使用者在送請求（官方文件〈Testing other systems/protocols〉的 note）。這種情形下吞吐量遠低於設定、延遲不代表受測服務，屬於下面排查順序裡施壓端那一項；patch 管得到與管不到的範圍、CPU 運算為什麼同樣卡住其他使用者，見 [Gevent Monkey Patching](/backend/knowledge-cards/gevent-monkey-patching/)。

## PR 與 nightly 兩種執行的分工

[6.1 CI pipeline](/backend/06-reliability/ci-pipeline/) 把 CI 分成每次 push 跑的 fast path、merge request 跑的 slow path 與排程跑的 scheduled path，6.13 沿用這三個名字，把 micro benchmark 放在 fast path、end-to-end 的效能測試放在 slow path 與 scheduled path。Locust 對著部署好的受測環境送請求，屬於 end-to-end 的效能測試，不放在 fast path：fast path 的時間預算與「不碰外部依賴」的條件，容不下一次要部署環境、還要維持幾分鐘負載的執行。PR 跑的那一份對應 slow path，nightly 或 release branch 跑的那一份對應 scheduled path。

CI 在 headless 模式（不開 web UI）下執行 Locust，PR 那一份的指令形狀如下：

```bash
# PR 的 gate：只跑關鍵流程的 User class，ramp-up 之後清空統計，輸出 CSV 與 HTML report
GATE_BASELINE=baseline/checkout.json \
locust -f locustfile.py --headless -u 50 -r 5 -t 10m --reset-stats \
  --host <受測環境的位址> \
  --csv gate-results/run --html gate-results/report.html \
  CheckoutUser
```

這條指令照官方文件〈Configuration〉的參數組成，沒有實跑。`baseline/checkout.json` 是 CI 從保存證據的位置取回的基準值檔；`-u 50 -r 5 -t 10m`（同時在線 50 個使用者、每秒啟動 5 個、執行 10 分鐘）是佔位值，兩版要用同一組；`<受測環境的位址>` 填這次部署的 staging 位址；`gate-results/run` 是 CSV 檔名的前綴，產出 `run_stats.csv` 這一組檔；最後的 `CheckoutUser` 是 locustfile 裡要執行的 User class，不寫時 Locust 執行檔案裡全部的 User class（`--help` 裡 User classes 那一組參數），nightly 那一份不寫或列出完整的組合。

PR 那一份負載低於飽和點（[Saturation Point](/backend/knowledge-cards/saturation-point/)）、只涵蓋關鍵流程，抓的是一次變更造成的明顯延遲退化，用〈quitting listener 的寫法：統計的範圍、百分位數的分桶與回應的驗證〉那段讀基準值檔的 listener 做相對退化的判讀，這是 6.13 定給 slow path 的主要判讀。它抓不到的有兩類。一類是要長時間維持負載才出現的退化：記憶體洩漏、連線池慢慢耗盡、GC 暫停隨堆積的物件變長。另一類是每個請求的資源成本變高：一個請求多用了三成 CPU，請求的延遲主要花在等 I/O 時，低負載下延遲幾乎不變，要到接近飽和時才看得出來；後一類有兩種做法：在 gate 裡另外記錄受測服務每個請求的 CPU 用量、拿它跟基準版本比，或交給 nightly 在接近飽和的負載下量。nightly 那一份時間長、task 組合完整，加上長時間維持負載的 soak 階段，抓的是與時間有關的退化；它也把每一次的 `_stats.csv` 與 `_stats_history.csv` 存下來，替跨次比較的程式累積統計顯著性要的歷次樣本。

兩份共用同一份 locustfile：task 與 User class 只寫一份，流程改動時兩份量的仍然是同一個流程，PR 那一份用命令列指定 User class 或用 `--tags` 篩選 task（官方文件〈Writing a locustfile〉的〈@tag decorator〉）。兩份也共用同一組測試資料（帳號、商品編號），gate 只量得到測試資料走到的路徑：資料只有少數幾個熱門商品時，讀資料庫的長尾路徑兩版都沒有被請求到，這一版的變更若改到那條路徑，gate 對它沒有訊號。CI 跑 Locust 的環境要跟其他工作隔開：staging 上同時有別的 QA 流量或排程工作時，它們的負載混進受測服務的延遲與吞吐量，前後兩版的差距落在這些雜訊裡。這是 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)〈Variance 控制〉表裡共用受測環境那一列的噪音：被共用的是受測環境，不是執行測試的 runner，控制方式是測試期間保留專用的受測環境，做不到時記下同一時段的其他流量、比較時排除重疊的那幾段。

## CSV、HTML report 與執行條件的保存

Locust 每次 headless 模式的執行可以留下三種輸出：`--csv` 的四個 CSV 檔（整次執行的統計、失敗、例外，以及統計的時間序列）、`--html` 的 HTML report，以及 `--json` 印到 stdout 的最終統計。CI 的 job 把它們存成 build artifact，gate 失敗時 reviewer 打開 HTML report 與 `_failures.csv`，找出是哪一個請求名稱、在哪一段時間退化；跨次比較的程式讀 `_stats.csv` 與 `_stats_history.csv`。這些檔案要存在保留期限不受 CI 控制的位置（物件儲存、測試結果資料庫）：CI 平台的 artifact 有保留天數，基準版本那一次的 CSV 到期刪掉之後，下一次 gate 就沒有基準版本的結果可比。CI 平台刪除過期的 artifact 時不會通知任何人；從那一次的結果寫出的基準值檔若也跟著刪掉，listener 照上面的寫法以缺資料結束（exit code 4）、log 印出 `baseline file missing or unreadable`，看到這個訊息的人要知道失敗的原因是少了基準，處置是重建基準，不是回頭查這一版的變更。

輸出只記錄這一次的結果；要讓另一個人判斷兩次結果比不比得了，CI 的 job 在同一份證據裡另外記下三組欄位。一組是 [6.2 load test](/backend/06-reliability/load-testing/)〈Load test 結果的證據留存〉列的最小欄位：workload model 版本、測試環境、saturation point（飽和點，[Saturation Point](/backend/knowledge-cards/saturation-point/)）、throughput ceiling（受測服務量到的吞吐量上限，[Throughput](/backend/knowledge-cards/throughput/)）、主要瓶頸歸因、headroom ratio（目前負載離飽和點還剩多少容量的比例，[Headroom Budget](/backend/knowledge-cards/headroom-budget/)）、退化模式分類與測試日期。一組是這次執行的條件，其中幾項是 Locust 特有、而且只看 locustfile 的 commit 看不出來的：locustfile 的版本（commit）；這次執行了哪些 User class、`--tags` 篩了哪些 task；task 權重與 `wait_time`（寫在 locustfile 裡時 commit 已經涵蓋，由設定檔或環境變數覆寫時要另外記）；`-u`、`-r`、`-t` 與有沒有加 `--reset-stats`；worker 的數量、每台的規格與 `--processes` 的值；Locust 的版本與 client library 的版本（`FastHttpUser` 底下的 geventhttpclient、custom client 包的協定 library），兩者升級都可能改變計時的範圍或分桶的方式；分桶函式有沒有替換。其餘的條件跟其他負載工具相同：受測服務的副本數、受測資料庫的資料量（或每次重建時用的 seed 版本）、下游哪些服務是 mock、沒有 mock 的下游各是哪一個版本，包括 `on_start` 會呼叫的身分驗證服務。一組是比較的另一邊：這次跟哪一次基準執行比（那一次的執行編號或 commit），以及 listener 讀的基準值檔是哪一個版本。這些欄位跟著 gate 的判定交給下游的方式，照 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) 的〈Handoff 欄位〉。

## gate 失敗時的排查順序

Locust 的 gate 失敗時，有四種誤判會讓差距看起來像這一版的退化：兩次執行的條件不同、施壓端飽和、gate 讀到的請求範圍跟基準那一次不同、差距落在雜訊之內。下面的執行條件、施壓端、請求的範圍與雜訊範圍四項依序排除這四種誤判，退化的流程與幅度那一項是全部排除之後、把差距歸給這一版的那一步。順序依兩件事排：排除那種誤判要花多少力氣，以及前一項沒排除時後一項的讀數是否還能解讀。施壓端排在請求範圍與雜訊之前，是因為施壓端飽和時兩者的讀數都失真：closed model 下施壓端變慢讓每個流程送出的請求數一起變少，請求範圍的比對會把它讀成某個流程漏了請求；施壓端排隊的時間又讓延遲的波動變大，拿這次的讀數跟雜訊範圍比，比的是施壓端的波動。

這四種誤判都建立在一個前提上：這一次的執行本身完整跑完了。施壓端在執行中途出狀況時，quitting listener 照樣判定，exit code 看起來是正常，或看起來是這一版的退化。worker 在執行中被殺掉時，master 判它失聯，`failed to send heartbeat` 那一行只寫進 `--logfile`，listener 照樣判 PASS，負載卻只剩一部分 worker 送出；`--expect-workers` 等的 worker 一直沒連上時，master 一直等下去，加了 `--expect-workers-max-wait` 之後回 1，沒有 listener 的判定，跟門檻不成立的 1 是同一個值；受測環境只有一部分故障時，錯誤率落在 0 與 100% 之間，讀起來跟退化相同，要看 Error report 裡錯誤的類別才分得出來（`RemoteDisconnected`、`ConnectionRefusedError` 是連線層的錯誤）。所以讀 gate 的結果之前，先核對四件事：這一次連上的 worker 數跟設定的相同、沒有 worker 失聯、實際的執行時間落在 `-t` 加上啟動時間之內、失敗是連線層還是 HTTP 的錯誤。任一件對不上時，這一次量到的是不完整的負載，拿它跟基準比，比出來的差距歸不到這一版，排查改成找出這一次為什麼沒有跑完。這一步排在比對條件之前，因為它只讀這一次自己的輸出，而且它不成立時，後面每一項比的都是一次不完整的量測。這幾種情形的實跑結果，見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈master 與兩個 worker〉與〈quitting 事件裡的門檻判定〉。

1. **兩次執行的條件**：比對證據裡兩邊記下的條件，locustfile、User class、`-u`、`-r`、`-t`、worker 配置、Locust 與 client library 的版本、受測環境、沒有 mock 的下游版本有任一項不同，差距就不能歸給這一版的變更。容易漏的三種：身分驗證服務或身分提供者（IdP）變慢或失敗（變慢時，登入請求沒有用名稱排除、也沒有被 `--reset-stats` 清掉的部分，延遲直接進了 `stats.total`；失敗時，`on_start` 拋例外的使用者在啟動完成之後不再補回，一直失敗時實際使用者數少於 `-u`、吞吐量跟著下降，沒拿到 token 的使用者讓關鍵流程回 401；比對證據裡這次實際在跑的使用者數與 `-u`、`runner.exceptions` 與 `_exceptions.csv` 裡有沒有 `on_start` 的例外、`_failures.csv` 裡有沒有 401，就分得出成因在身分驗證服務）；受測資料庫的資料量漂移（gate 每次執行都寫入訂單、帳號，資料表一路變大，查詢慢慢變慢，樣子跟漸進退化相同，每次執行前重建資料庫才排除得了）；Locust 或 client library 升級（計時範圍或分桶方式改了，兩邊的數字量的已經不是同一件事）。基準版本那一次本身是離群值時，之後每一版都像退化，基準的選法見 6.13 的〈Baseline 設定〉。這一項只要比對紀錄，花的力氣最少。
2. **施壓端的資源**：Python 的一個 process 只用得到一個 CPU 核心（官方文件〈Distributed load generation〉），process 的 CPU 用量超過 90% 時 Locust 在 log 印出 `CPU usage above 90%! This may constrain your throughput and may even give inconsistent response time measurements!`（官方文件〈Increasing the request rate〉，同一行字串也在原始碼 `locust/runners.py`）。執行結束時，CPU 曾超過門檻的 process 另印 `CPU usage was too high at some point during the test!`；分散式執行時，有 worker 超過門檻的話 master 再印 `CPU usage threshold was exceeded on workers during the test!`，master 自己也超過時兩行都會印（這兩行出自原始碼 `locust/runners.py`）。印出警告的同時，runner 把 `cpu_warning_emitted`（master 另有 `worker_cpu_warning_emitted`，代表有 worker 超過門檻）設成真，〈quitting listener 的寫法：統計的範圍、百分位數的分桶與回應的驗證〉的 listener 在 `quitting` 裡讀這兩個屬性，為真時以 `EXIT_INCONCLUSIVE` 結束，CI 不必掃 log。CPU 超過門檻時，量到的延遲包含施壓端自己排隊的時間（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)），而 closed model 下施壓端變慢跟受測服務變慢一樣讓吞吐量下降，兩者在報告上分不開。網路頻寬、來源埠，以及 custom client 被 C 擴充模組卡住的情形都不觸發 CPU 警告，兩個屬性都是假時施壓端仍可能飽和，要靠 Locust 量到的延遲與受測服務入口量到的延遲的差距才看得到。CPU 警告的屬性與這個延遲差距都拿不到時（例如 CI 沒有收集受測服務入口的延遲，而施壓端飽和的成因不是 CPU），這一項無法排除，這次 gate 的結果是無結論：失敗不足以當成退化的證據，通過也不足以當成沒有退化的證據，處置是補上施壓端的指標收集後重跑。
3. **gate 讀到的請求範圍**：比對這次與基準那一次每個關鍵流程的請求數，以及 `stats.total` 裡各請求名稱的組成。某個流程這次的請求數是零或明顯變少（client 漏觸發 `request` 事件、`name=` 改了、`--tags` 篩掉了 task），gate 對那個流程的判定沒有依據；請求名稱的組成不同（新增了 endpoint、登入請求的比重變了），`stats.total` 的兩次統計量的是不同的請求組合。這一項放在雜訊之前，因為請求的組合不同時，雜訊範圍是用另一個組合量出來的，拿來比沒有意義。
4. **差距與雜訊的範圍**：CI 在建立 baseline 時把同一個版本重跑幾次（次數與樣本量的取法見 6.13 的〈Regression 判讀方法〉），listener 用到的每一個統計值（各流程的 p95、失敗比例、`total_rps`）的波動範圍就是它的雜訊範圍：同一個版本幾次執行裡那個統計值最高與最低的差，占基準值的百分比；這個範圍怎麼限制門檻能設多窄，寫在 6.13 的〈Baseline 設定〉與〈相對退化〉；p95 在 100 到 200 毫秒之間時，〈quitting listener 的寫法：統計的範圍、百分位數的分桶與回應的驗證〉講的分桶間距也算進這個範圍。退化的幅度小於這個範圍時，這次的差距還不能當成退化的證據；門檻設得比這個範圍窄時，gate 會反覆誤報，團隊開始略過它。雜訊範圍超過想抓的退化幅度時，單次執行的比較抓不到這個幅度，要照 6.13〈Variance 控制〉縮小雜訊，或在 scheduled path 讓跨次比較的程式用歷次的 CSV 做統計顯著性（同一個版本多跑幾次、基準版本與候選版本在同一個環境交錯執行）。
5. **退化的流程與幅度**：執行條件、施壓端、請求範圍與雜訊範圍都排除之後，差距屬於這一版的變更。listener 印的失敗原因與 `_stats.csv` 的各列指出是哪一個流程；退化從哪一段時間開始，要看加了 `--csv-full-history` 的 `_stats_history.csv` 裡那個請求名稱的各列（每列是最近約十秒的視窗），或受測服務那一端的延遲指標（從開頭就慢是穩態的退化，隨時間變慢是 soak 才看得到的那一類）。退化落在有自己門檻的關鍵流程時，那一條判定失敗本身就是擋下 release 的依據，原因的定位方法在 6.13〈退化定位與行動〉的 profiling diff 與 commit bisect。失敗的是 `stats.total` 的吞吐量下限、而各關鍵流程的延遲門檻都通過時，先比對各流程 p95 相對基準的變化量。closed model 下每個使用者依序做各種 task，一個流程變慢，使用者每一輪的時間變長，全部流程的每秒請求數一起下降，所以吞吐量下降不一定來自關鍵流程以外的請求：某個關鍵流程的 p95 上升了、只是還在門檻以內，也會讓總吞吐量低於下限（[Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/) 的〈task 權重與 production 的操作分布〉寫了這個效應，標明是從機制推論、沒有實跑量過大小）。變化量集中在某個關鍵流程時，退化屬於那個流程，照它的門檻與 6.13 的定位方法處理；各關鍵流程的變化量都在雜訊範圍內時，才判斷關鍵流程以外的請求在服務的效能預算（[Performance Budget](/backend/knowledge-cards/performance-budget/)）裡有沒有額度：預算有涵蓋它們，這次退化照樣擋下；預算沒有涵蓋，回到 6.13 的〈Regression 判讀方法〉決定門檻的範圍與值。在那之前若決定放行，放行的人、理由與這次的差距要跟著 gate 的判定寫進證據（6.23〈Handoff 欄位〉），代價是關鍵流程以外那些請求的退化會累積到下一次調整門檻。

同樣看到 p95 變慢，用 Locust 做容量探測時，排查從施壓端查起：worker 的 CPU 與數量是否足夠、實際送出的請求率是否跟著使用者數上升，要判斷的是受測服務哪一項資源先飽和，順序與這裡不同，寫在 [Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/) 的排查順序那一節。

## 相關章節與工具頁：gate 的方法、load test 的 baseline，以及 Gatling 與 k6 的 gate 寫法

- [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)：baseline 的 production percentile、CI benchmark history 與 load test 結果三種來源，絕對門檻、相對退化與統計顯著性三種判讀方法，以及 variance 控制；本篇的 listener 與排查順序都建立在它上面。
- [6.2 load test](/backend/06-reliability/load-testing/)：訂定 gate 拿來比對的 baseline 與 saturation point，以及 load test 結果要留存的欄位。
- [Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/)：同一類 gate 換成 Gatling 時，門檻寫在 simulation 的 assertion 裡、由 assertion 決定成敗，而且 open 與 closed 兩種注入模型都選得到。
- [k6：Threshold CI Gate 與 Scenario 設計](/backend/06-reliability/vendors/k6/threshold-ci-gate-and-scenario-design/)：同一類 gate 換成 k6 時，threshold 與 executor 的寫法。
