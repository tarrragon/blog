---
title: "JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序"
date: 2026-10-28
description: "用 JMeter 實作效能 regression gate 時的判斷：門檻判定放在 JMeter 之外的哪一段、逐筆 assertion 與分佈門檻的分工、負載模型與施壓端設定怎麼影響前後兩版的比較、要保存的執行條件，以及 gate 失敗時怎麼把誤判和真正的退化分開"
weight: 1
tags: ["backend", "reliability", "vendor", "jmeter", "load-test", "release-gate"]
slug: "jmeter-performance-regression-gate"
---

用 JMeter 做效能 regression gate 的人，要判斷的是這一版能不能過 release gate：這一版比基準版本慢了沒有、慢的幅度是否超出雜訊、要不要擋下。這篇整理這個判斷在 JMeter 上的做法。門檻判定的位置：JMeter 在 CLI mode 結束時的 exit code 為什麼不反映失敗的 sample 與 assertion，判定因此要放在 JMeter 之外；判定放在自寫的後處理（讀 JTL 或 dashboard 的 `statistics.json`）、jmeter-maven-plugin、Jenkins 的 Performance plugin 或 Taurus 時，各自做得到 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/) 的絕對門檻、相對退化與統計顯著性裡的哪幾種；Duration Assertion 這類逐筆判定的 assertion 跟分佈上的統計門檻各管哪一類退化，混用時錯誤率與 gate 的結果怎麼被扭曲。兩次執行的可比性：ramp-up 期間的樣本怎麼排除；內建的 Thread Group、Open Model Thread Group、throughput timer 與 jmeter-plugins 的幾種 thread group 各自固定了同時在線數還是到達率（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)），退化因此出現在哪一個指標上；listener、plugin 版本、JMeter 與 Java 的版本、heap 設定怎麼讓兩次結果失去可比性。gate 在 CI 裡的運作：PR 與 nightly 各跑一份設定時各自抓得到、抓不到哪一類退化；JTL、dashboard 與執行條件要保存哪些、存在哪裡；gate 失敗時依序排除哪幾種誤判，才把差距歸給這一版的變更。baseline 的來源、門檻的設法與 variance 控制是 6.13 的內容，本篇只寫它們在 JMeter 上的做法。JMeter 的安裝、test plan 的元件寫法、`.jmx` 的維護與 plugin 的安裝在 [Apache JMeter 使用手冊](https://jmeter.apache.org/usermanual/index.html) 與 [jmeter-plugins.org](https://jmeter-plugins.org/)；同一個工具用來找受測服務飽和點、估算要加多少機器的寫法在 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/)。

## JMeter 在 regression gate 裡負責的環節與 exit code 涵蓋的範圍

效能 regression gate 比較這一版與基準版本（baseline）在同一組負載下的延遲、錯誤率與吞吐量，退化超過門檻時擋下 release（[Release Gate](/backend/knowledge-cards/release-gate/)）。JMeter 用 test plan 描述一次執行的內容，存成 `.jmx` 檔：thread group 決定放進多少個執行緒、怎麼放進去，每個執行緒代表一個虛擬使用者，執行緒依序跑完 thread group 底下的全部元件稱為一輪 iteration；sampler 是一個請求（HTTP、JDBC 這類）；assertion 掛在 sampler 上，檢查每一筆回應；listener 收集結果。JMeter 每送出一個請求、收到回應，就產生一筆 sample，CLI mode 用 `-l` 把每一筆 sample 寫進 JTL 檔（CSV 或 XML）。官方文件〈Listeners〉列出 CSV 格式的欄位，包括 `timeStamp`（毫秒；發行版附的 `jmeter.properties` 設了 `sampleresult.timestamp.start=true`，記的是 sample 的開始時間，這個屬性在程式裡的預設是 `false`，有人把那一行拿掉或改成預設值時記的是結束時間，官方〈Properties Reference〉）、`elapsed`（毫秒）、`label`（sampler 的名稱）、`responseCode`（回應的狀態碼）、`success`（`true` 或 `false`）、`failureMessage`（失敗時的訊息，assertion 判成失敗時寫的是那個 assertion 的訊息）與 `allThreads`（當下所有 thread group 的活躍執行緒數）。`-e -o <資料夾>` 在執行結束後從 JTL 產生 HTML dashboard，`-g <JTL 檔>` 不重跑測試、只從既有的 JTL 產生 dashboard（官方文件〈Generating Report Dashboard〉）。

JMeter 在 gate 裡做的是產生負載與記錄每一筆 sample，它不做 pass 或 fail 的判定。官方文件〈Getting Started〉寫明 CLI mode 在測試正常結束時不呼叫 `System.exit()`，文件列出的例外是某些致命錯誤，以及設了 `jmeterengine.stopfail.system.exit=true` 而 JMeter 停不下所有執行緒時以 `System.exit(1)` 結束；文件沒有任何一處把失敗的 sample 或 assertion 連到 exit code。由這兩點推論（沒有實跑），一次執行裡三成的 sample 失敗，JMeter 正常結束時的 exit code 是 0，跟全部成功的那一次相同，CI 只看 JMeter 的 exit code 時，跑 JMeter 的那個 CI 步驟的結果一律是成功。Gatling 的 assertion 在 simulation 結束時評估、失敗時讓這次執行失敗（[Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/)），k6 的 threshold 直接決定 exit code（[k6：Threshold CI Gate 與 Scenario 設計](/backend/06-reliability/vendors/k6/threshold-ci-gate-and-scenario-design/)）；JMeter 這一段要由 CI 的另一個步驟讀結果、自己決定 exit code。

## 門檻判定的落點：自寫的後處理與外層工具

JMeter 之外承接門檻判定的位置有自寫的後處理、jmeter-maven-plugin、Jenkins 的 Performance plugin 與 Taurus，判定放在哪一個，決定 gate 做得到 6.13 的哪一種判讀。各自讀的結果與比得了的對象如下：

| 落點                                  | 讀的結果                 | 比得了的對象                                                                                          | 對應 6.13 的判讀                          |
| ------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 自寫的後處理                          | `statistics.json` 或 JTL | 任何統計值，可以跟保存下來的基準結果比                                                                | 絕對門檻、相對退化；讀 JTL 時加統計顯著性 |
| jmeter-maven-plugin 的 `results` goal | 結果檔裡的失敗筆數       | 錯誤率對一個固定的百分比                                                                              | 只有錯誤率的絕對門檻                      |
| Jenkins 的 Performance plugin         | JTL 或 CSV               | 錯誤率與每個結果檔的平均回應時間對固定值；或跟前一次、指定編號的 build 比平均、中位數或第 90 百分位數 | 絕對門檻、相對退化                        |
| Taurus 的 passfail 模組               | Taurus 執行時彙整的統計  | 平均、百分位數、失敗的筆數或比例對固定值，可限定 label 與時間窗                                       | 絕對門檻                                  |

**自寫的後處理**讀 JMeter 自己的輸出。HTML dashboard 的產生器預設同時輸出 `statistics.json`（JMeter 5.1 起，`reportgenerator.properties` 裡的 `JsonExporter`），內容是 dashboard 統計表的機器可讀版本：每個 label 一個鍵，彙總整次執行的那一列在英文語系下鍵名是 `Total`；每一列的欄位有 `sampleCount`、`errorCount`、`errorPct`（單位是百分比）、`meanResTime`、`medianResTime`、`pct1ResTime`、`pct2ResTime`、`pct3ResTime` 與 `throughput`（欄位名取自 JMeter 原始碼的 `JsonExporter`）。下面這一組指令先跑測試、產生 dashboard，再拿這一次與基準那一次的 `statistics.json` 比：

```bash
# 跑測試、寫 JTL、結束後產生 dashboard 與 statistics.json；-f 先刪掉上一次留下的結果檔與報告資料夾
jmeter -n -t checkout-gate.jmx -l result.jtl -e -o report/ -f
# 這一次對基準那一次；有門檻不成立時以 exit code 1、判定不完整時以 4 結束，CI 據此擋下合併
python3 gate.py report/statistics.json baseline/statistics.json
```

```python
# gate.py：逐個要把關的 label，比這一次與基準那一次的 p95 與錯誤率
import json, sys

EXIT_REGRESSION = 1     # 有門檻不成立
EXIT_MISSING_DATA = 4   # 團隊自訂：讀不到 statistics.json 或缺某個 label，判定不完整
GATED = ["checkout", "search"]            # 要各自設門檻的 sampler 或 Transaction Controller 名稱

try:
    current = json.load(open(sys.argv[1]))    # 這一次的 statistics.json
    baseline = json.load(open(sys.argv[2]))   # 基準那一次保存下來的 statistics.json
except (OSError, ValueError) as e:            # 報告沒有產生、JTL 是空的、檔案寫壞
    print(f"讀不到 statistics.json，無法判定：{e}")
    sys.exit(EXIT_MISSING_DATA)

regressed = missing = False
for label in GATED:
    if label not in current or label not in baseline:
        print(f"{label}: statistics.json 裡沒有這個 label，無法判定")
        missing = True
        continue
    cur, base = current[label], baseline[label]
    if cur["pct2ResTime"] > base["pct2ResTime"] * 1.10:   # pct2 預設是第 95 百分位數
        print(f"{label}: p95 {cur['pct2ResTime']:.0f} ms，基準 {base['pct2ResTime']:.0f} ms")
        regressed = True
    if cur["errorPct"] > 1.0:                              # errorPct 的單位是百分比
        print(f"{label}: 錯誤率 {cur['errorPct']:.2f}%")
        regressed = True
sys.exit(EXIT_REGRESSION if regressed else EXIT_MISSING_DATA if missing else 0)
```

`jmeter` 那一行照官方文件〈Getting Started〉與〈Generating Report Dashboard〉的選項組成，沒有實跑；`gate.py` 只拿依原始碼欄位名手寫的 `statistics.json` 跑過五種情形（兩邊相同時 0、退化時 1、缺 label、檔案不存在與空檔時都是 4），沒有接過 JMeter 實際產出的檔案。exit code 4 是團隊自己訂的約定：報告沒有產生（JTL 是空的、`-e` 那一步失敗）時，`statistics.json` 不存在，程式不攔下的話只會留下一段 Python 的 traceback，看 CI 結果的人分不出這是退化還是少了資料；CI 把 4 對應成「補上基準或修好 test plan 再跑」，跟 1 的處置分開。有門檻不成立排在缺資料之前判，因為有資料的流程已經量到退化，這個證據不因為別的流程缺資料而失效。`checkout-gate.jmx` 是讀者自己的 test plan；`baseline/statistics.json` 是基準版本那一次執行保存下來的檔案，保存的位置見〈JTL、dashboard 與執行條件的保存〉；`GATED` 裡的 `checkout`、`search` 換成 test plan 裡要各自設門檻的 sampler 或 Transaction Controller 的名稱（Transaction Controller 是把一段流程裡的幾個 sampler 包起來的邏輯控制器，另外產生一筆 sample 記下整段流程花的時間，官方文件〈Component Reference〉）；`1.10`（容許 10% 的相對退化）與 `1.0`（錯誤率 1%）是佔位值，從同一個版本重跑時量到的波動範圍取：例如同一個版本重跑五次，`pct2ResTime` 最高與最低差了基準值的 6%，相對門檻至少要跟這個範圍一樣寬，6.13 的〈Baseline 設定〉與〈相對退化〉寫了 baseline 自身的波動怎麼限制門檻能設多窄（雜訊範圍在 gate 失敗時怎麼用，見〈gate 失敗時的排查順序〉的雜訊範圍那一項）。範例刻意只做到逐個 label 比 p95 與錯誤率，有兩件事沒做：`jmeter` 那一行沒有排除 ramp-up 的樣本，`gate.py` 沒有吞吐量的下限。用 closed model 或 throughput timer 的 gate 兩件都要補，做法分別在〈ramp-up 期間的樣本與統計區間〉與〈thread group 與 timer 的負載模型對前後兩版比較的影響〉。這支程式的寫法背後有四個考量：

- **`pct2ResTime` 指的是哪一個百分位數由設定決定**：`pct1` 到 `pct3` 依序對應 `aggregate_rpt_pct1` 到 `aggregate_rpt_pct3` 三個屬性，預設是第 90、95、99 百分位數。有人在 `user.properties` 改了這三個屬性，同一行程式量的就換成另一個百分位數，而程式與 test plan 都沒有改，code review 看不出 gate 量的百分位數換了；所以這幾個屬性的值要跟結果一起保存，基準那一次與這一次不同時，兩邊的 `pct2ResTime` 不能比。dashboard 估算百分位數的公式也跟 GUI 的 Aggregate Report 不同（`backend_metrics_percentile_estimator` 決定），兩個畫面的數字對不上時，要比的是兩次都用同一種公式算出來的值。
- **失敗的 sample 也算進百分位數**：原始碼裡的統計表把每一筆 sample 的 `elapsed` 都加進百分位數，不分成功或失敗。這一版的變更讓某個 endpoint 立刻回 503 時，那些很快結束的失敗讓 p95 下降，延遲的門檻因此通過；錯誤率的門檻跟延遲的門檻放在同一個 label 上，才擋得下這一類退化。dashboard 的 Response times Percentiles Over Time 圖只統計成功的回應（官方文件〈Generating Report Dashboard〉），所以有失敗的 sample 時，圖上讀到的百分位數跟 `statistics.json` 的可能不同；gate 讀的是 `statistics.json`，reviewer 拿圖對照 gate 的數字時要知道兩者的範圍不同。
- **label 找不到時判成缺資料**：鍵是 sampler 或 Transaction Controller 的名稱，有人在 GUI 裡把 `checkout` 改名成 `Checkout`，`statistics.json` 就沒有這個鍵。程式找不到鍵時直接略過的話，這個流程從此不再受 gate 管，而 CI 一直是綠的。
- **關鍵流程各自設門檻**：`Total` 那一列由請求量最大的 sampler 主導，一個每秒幾千次、回應很快的健康檢查會把結帳流程的退化平均掉；逐個 label 比較時，gate 失敗的訊息也直接指出是哪一個流程退化。

JTL 是有公開欄位說明的逐筆格式，所以自寫的後處理也可以不經過 dashboard、直接讀 JTL：依 `label` 分組、依 `timeStamp` 排除 ramp-up、自己算百分位數，或把兩次執行的逐筆 `elapsed` 交給統計檢定，做出 6.13 的統計顯著性。Gatling 的 OSS 版沒有官方支援的機器可讀輸出，跨次比較要從受測服務那一端取量測；JMeter 這一段可以只靠施壓端自己的輸出完成。付出的是程式要有人維護、要保存基準那一次的結果，以及每次接受新基準時更新那份檔案。

**jmeter-maven-plugin** 的 `results` goal 讀 JMeter 寫出的結果檔，預設只要有任何一筆失敗就讓 Maven 的建置失敗；設了 `errorRateThresholdInPercent`（2.8.1 起）之後，錯誤率超過那個百分比才失敗（官方 wiki〈Test Results File Format〉）。它只看失敗的筆數，延遲多慢都不會讓它失敗，所以它管的是 6.13 的絕對門檻裡錯誤率那一項；延遲的門檻要另外接自寫的後處理。

**Jenkins 的 Performance plugin** 讀 JTL 或 CSV，依門檻把 build 標成 unstable 或 failed，也畫出歷次 build 的趨勢（官方文件〈Performance Trend Reports〉）。plugin 的設定畫面把門檻分成兩種模式，一次只能選一種：Error Threshold 模式依單一 build 判，`errorUnstableThreshold` 與 `errorFailedThreshold` 是錯誤率的門檻，進階設定裡的 `errorUnstableResponseTimeThreshold` 依結果檔設平均回應時間的絕對門檻，每行寫成 `結果檔名:毫秒數`，超過時 build 標成 unstable；Relative Threshold 模式拿這一次跟前一次 build（`compareBuildPrevious`）或指定編號的 build（`nthBuildNumber`）比，比較的統計值由 `configType` 選平均、中位數或第 90 百分位數的回應時間，退化的百分比超過 `relativeUnstableThreshold*` 或 `relativeFailedThreshold*` 時標成 unstable 或 failed。進階設定另有 `baselineBuild`（畫面上標為 Baseline build number），它跟相對門檻比的那一次 build 是什麼關係，說明頁與文件都沒有寫，要用之前先在測試的 job 上確認。相對門檻只有第 90 百分位數可選，6.13 用 p95 或 p99 當門檻時，這個 plugin 量的統計值跟 6.13 設定的不同。它換到的是不必自己保存基準結果：歷次 build 的報告就是基準，付出的是基準跟著 Jenkins 的 build 紀錄走，build 紀錄被輪替刪除或換了 job，基準就跟著消失。兩種模式與各參數的名稱取自 plugin 原始碼裡設定畫面的 `config.jelly`。

**Taurus** 是包在 JMeter 外面的執行框架，`passfail` 模組的條件寫成 `p95 of checkout>500ms` 這類形式：主詞有 `avg-rt`、`p90` 這類百分位數、`fail`（失敗的筆數，錯誤率寫成 `fail>1%`）等，可以限定 label 與時間窗；條件不帶時間窗時，判定用的是整次測試的累計值（官方文件〈Pass/Fail Criteria〉）。passfail 的任一條件判成失敗時，不論是測試中途依時間窗停下，或測試結束時以整次累計值評估，Taurus 都以 exit code 3 結束，CI 可以直接用這個 exit code。它的門檻是寫死的值，對應 6.13 的絕對門檻；相對退化要把門檻參數化，跟上面的程式一樣要保存基準值。exit code 的依據是官方文件〈Command-Line Tool〉的 Exit codes，它把 3 列為自動停止，例子是 Pass/Fail criteria；結束時評估的那一種，passfail 模組的原始碼在 `post_process` 裡同樣以自動停止的例外結束。

落點的取捨看 gate 主要靠哪一種判讀：只要錯誤率的絕對門檻時，maven plugin 的 `results` goal 就夠用；要延遲的絕對門檻時，Taurus 的 passfail 不必寫程式；要相對退化時，Jenkins 的 Performance plugin 或讀 `statistics.json` 的程式都做得到，差在基準存在 Jenkins 的 build 紀錄還是團隊自己的儲存位置；要統計顯著性時，只有直接讀 JTL 的程式做得到。

## 逐筆 assertion 與統計門檻的分工

JMeter 的 assertion 在每一筆 sample 之後執行，作用範圍內的每一個 sampler 都會被檢查（官方文件〈Component Reference〉的 Assertions 一節）。Duration Assertion 把回應時間超過設定毫秒數的那一筆標成失敗；Response Assertion 拿回應的狀態碼、header 或內容比對設定的字串，比對不上的那一筆標成失敗。被 assertion 標成失敗的 sample 在 JTL 裡的 `success` 是 `false`，算進 `statistics.json` 的 `errorCount` 與 `errorPct`。所以 assertion 的判定單位是一筆 sample，regression gate 的判定單位是一次執行的分佈（百分位數、錯誤率、吞吐量），兩者管的退化不同。

Duration Assertion 拿來當延遲的 gate 時，延遲被轉成了錯誤：這一版的 p95 從 200 毫秒變成 260 毫秒、而 Duration Assertion 設在 1000 毫秒時，沒有任何一筆超過，gate 看不到這次退化；設在 250 毫秒時，原本就落在尾端的那幾筆也被標成失敗，錯誤率裡混進了「比 250 毫秒慢」與「受測服務回了錯誤」兩種事件，gate 失敗時讀錯誤率的人分不出是哪一種。施壓端偶爾一次 GC 暫停也會讓幾筆超過門檻；搭配 maven plugin 預設的「任何一筆失敗就讓建置失敗」時，這幾筆就足以擋下一次合併，這是 assertion 誤報（assertion noise）最常見的樣子：大量 assertion 失敗而受測服務的延遲分佈沒有變。

分工因此是：逐筆的 assertion 只檢查回應的正確性，延遲的退化在分佈上判。Response Assertion 檢查狀態碼與回應內容裡該有的欄位，受測服務回了狀態碼 200 的錯誤頁時，只有檢查內容的 assertion 會把那一筆標成失敗，錯誤率才算得到它；延遲的門檻寫在〈門檻判定的落點：自寫的後處理與外層工具〉那一段的後處理或外層工具裡，跟基準版本的百分位數比。assertion 本身也在施壓端花 CPU，官方文件〈Best Practices〉把「assertion 盡量少用」列在降低施壓端資源用量的建議裡，所以 gate 用的 test plan 只留判定正確性需要的那幾個。

## ramp-up 期間的樣本與統計區間

`statistics.json` 預設統計 JTL 裡的全部 sample，ramp-up 期間的也算進去。ramp-up 期間受測服務在預熱：JIT 還沒編譯熱路徑、cache 還沒填滿（[Cache Warmup](/backend/knowledge-cards/cache-warmup/)）、連線池還在建立連線，延遲比穩態（[Steady State](/backend/knowledge-cards/steady-state/)）高；JMeter 自己的 JVM 也在預熱。這些樣本算進統計時，p95 與 p99 會隨 ramp-up 佔整次執行的比例而變，兩次執行只要這個比例不同，受測服務沒有改變也會量到不同的值，這是 6.13〈Variance 控制〉表裡 cold start 那一列在 JMeter 上的樣子。

JMeter 有兩個位置可以把統計限定在穩態的區間：dashboard 的 `jmeter.reportgenerator.start_date` 與 `jmeter.reportgenerator.end_date` 只用這段時間內的資料產生報告與 `statistics.json`；自寫的程式直接讀 JTL 時，依 `timeStamp` 丟掉 ramp-up 結束之前的樣本。dashboard 那一種用的是時鐘時間，CI 要從這次執行的開始時間加上 ramp-up 的長度算出 `start_date`，開始時間取 JTL 第一筆 sample 的 `timeStamp`，或 CI 啟動 JMeter 的時刻，再用 `-g` 加上 `-Jjmeter.reportgenerator.start_date=…` 從同一份 JTL 產生一份只含穩態的報告，指令的寫法見 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/) 的〈從 dashboard 判讀 knee point〉；兩個屬性依 `jmeter.reportgenerator.date_format` 解讀（預設 `yyyyMMddHHmmss`，不帶時區），官方文件〈Generating Report Dashboard〉寫明結果檔的時間戳記在另一個時區時，格式要加上時區（`zzz`）。CI runner 多半跑在 UTC，算出 `start_date` 的那一步與產生報告的 JMeter 用不同時區時，區間會整段錯開幾個小時，報告可能只剩下一部分樣本或完全沒有樣本（依時區的機制推論，沒有實跑），所以時區要跟 JTL 的時間戳記一致，或在 `date_format` 加上 `zzz`。兩種做法都依賴 JTL 保存著逐筆的時間，所以還可以事後用 `-g` 從同一份 JTL 換一個區間重新產生報告，不必重跑測試。Taurus 的 passfail 時間窗（`for`、`within`、`over`）是測試進行中逐段評估的滑動視窗，沒有指定起點的參數（官方文件〈Pass/Fail Criteria〉的 Timeframe Logic），排除不了 ramp-up；用 Taurus 判定時，要排除 ramp-up 一樣在後處理或 dashboard 的 `start_date` 做。兩種都不採用時，兩版的比較要靠每次執行的 ramp-up 完全相同、讓預熱成為兩版共有的偏移，前提與限制跟 [Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/) 的〈ramp-up 期間的請求與量測區間〉相同：兩版每次執行前都從同一種冷啟動的狀態開始，而且這一版的變更沒有改到預熱的行為。

## thread group 與 timer 的負載模型對前後兩版比較的影響

regression gate 比較前後兩版時，兩次執行要用同一種負載模型與同樣的參數，因為模型決定了這一版變慢時，退化出現在延遲上還是吞吐量上（機制見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉）。JMeter 的負載模型由 thread group 與 timer 的組合決定，下表依官方文件與 jmeter-plugins.org 的說明整理：

| 元件                               | 來源                       | 固定的變數                                                                                | 受測服務變慢時                                                                                         |
| ---------------------------------- | -------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Thread Group                       | 內建                       | 執行緒數（同時在線的使用者數）                                                            | 每個執行緒等回應才送下一個，吞吐量下降                                                                 |
| Concurrency Thread Group           | jmeter-plugins             | 同時在線數（執行中的執行緒不足時補上）                                                    | 同 Thread Group，吞吐量下降                                                                            |
| Constant／Precise Throughput Timer | 內建                       | 一段期間內 sample 數的上限（Constant 以每分鐘計，Precise 以自訂的期間計），靠延長停頓達成 | 停頓縮到零之後再也加不上去，吞吐量下降（pacing）                                                       |
| Throughput Shaping Timer           | jmeter-plugins             | 每秒請求數的排程上限，同樣只能延長停頓                                                    | 執行緒給夠時維持排程；執行緒不夠時吞吐量下降，跟 pacing 一樣減壓                                       |
| Arrivals Thread Group              | jmeter-plugins             | 每秒開始的迭代數（到達率），執行緒都忙時建立新的                                          | 到達率維持，延遲上升；執行緒數碰到 Concurrency Limit（防止記憶體用完的執行緒上限）後送不出設定的到達率 |
| Open Model Thread Group            | 內建（5.5 起，標為實驗性） | 依排程的到達率，每次抵達建立一個新的執行緒、跑完一輪就結束                                | 到達率維持，延遲上升                                                                                   |

Constant Throughput Timer 的目標是每分鐘的 sample 數，計算方式有幾種：this thread only 讓每個執行緒各自維持這個速率，整體的吞吐量跟活躍的執行緒數成正比；all active threads in current thread group 與 all active threads 把目標分給同一個 thread group 或所有 thread group 裡活躍的執行緒，另有依任一執行緒上一次執行的時間排程的 shared 版本。說明寫明受測服務處理不了時吞吐量會低於設定值（官方文件〈Component Reference〉）。設成 this thread only 時，每個執行緒各自依自己上一輪的時間計算停頓，所以受測服務只有尾端少數幾筆變慢、讓少數幾輪超過間隔時，吞吐量就會小幅下降，不必等到全部執行緒都變慢；Precise Throughput Timer 則以整個 thread group 為單位計算。

Precise Throughput Timer 的目標是自訂期間（throughput period）內、整個 thread group 裡受它影響的 sampler 合計的 sample 數；說明寫明它不產生執行緒，受測服務處理不了、或執行緒不夠時，吞吐量同樣會低於設定值，並建議多數情形改用 Open Model Thread Group（官方文件〈Component Reference〉）。上限算的是 timer 作用範圍內的 sample：官方文件建議把它放在一輪流程的第一個元素底下，這時它限制的是一輪 iteration 開始的速率，一輪送出幾個請求，每秒請求數就是那個速率乘以一輪的 sampler 數。這兩個 timer 只能延長停頓，讀起來在指定到達率，模型仍是 closed：吞吐量有了上限，受測服務變慢時跟一般的 closed model 一樣減壓，這種設定稱為 pacing，見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的〈概念位置〉。

Throughput Shaping Timer 的頁面寫明 timer 只能延遲執行緒、限制每秒請求數，要另外提供足夠的執行緒，也可以跟 Concurrency Thread Group 的 `__tstFeedback` 回饋函式搭配、依需要調整執行緒數（jmeter-plugins.org〈Throughput Shaping Timer〉）。所以它屬於哪一種模型看執行緒夠不夠：執行緒給夠、受測服務變慢時還有空閒的執行緒可以送出排程的請求，行為接近 open model；執行緒不夠時送不出排程，跟 pacing 一樣減壓。

Concurrency Thread Group 在 jmeter-plugins.org〈Concurrency Thread Group〉的說明是維持同時在線的執行緒數、不足時補上，所以它跟內建的 Thread Group 一樣屬於 closed model，固定的不是到達率。

這張表對 gate 的影響在兩處。closed model 與 pacing 的 gate，這一版變慢的時間有一部分表現成每秒請求數下降、而不是延遲上升，只設延遲門檻的 gate 看不到表現在每秒請求數上的那一份退化，所以門檻要加上吞吐量的下限：`statistics.json` 的 `throughput` 跟基準那一次比，下限是基準值減去同一個版本重跑時吞吐量的波動範圍。test plan 只有一個 thread group、每個 sampler 每輪都執行時，這個下限讀 `Total` 那一列：closed model 下每一輪 iteration 依序跑過各個 sampler，任何一個流程的延遲上升都讓一輪變長，即使那個流程的延遲還在自己的門檻內，整次執行的吞吐量也跟著下降；逐 label 的 `throughput` 在同一輪裡跟著一起變，各自設下限只是重複同一個訊號。有多個 thread group，或 If Controller、Once Only Controller、Throughput Controller 讓某些 label 不是每輪都跑時，`Total` 混著不同 thread group 與不同頻率的 label，改成每個 thread group 挑一個每輪都會執行的 label 當代表，各自設下限。pacing 的 gate 多一個條件：一輪 iteration 花的時間還短於 timer 排定的間隔時，timer 把剩下的時間當停頓，變慢的時間被停頓吸收，吞吐量不變，退化全落在延遲上；一輪的時間超過間隔之後，吞吐量才開始下降。所以 pacing 的 gate 在退化還小時只看得到延遲，退化變大之後延遲與吞吐量都要看。open model（Open Model Thread Group、Arrivals Thread Group）的 gate，到達率由排程決定，退化表現在延遲與錯誤率上，吞吐量的門檻改成檢查實際送出的請求率有沒有達到排程。排程的到達率算的是一輪 iteration 的開始，不是請求：Open Model Thread Group 每個執行緒只跑一輪（原始碼 `OpenModelThreadGroupController` 的註解寫明 every thread performs just one iteration），Arrivals Thread Group 把一次抵達定義為一輪 iteration 的開始，所以要比的是排程的到達率乘以一輪 iteration 的 sampler 數。實際的每秒請求數低於這個值、而受測服務的錯誤沒有讓一輪提早結束時（兩種情形的分法見〈gate 失敗時的排查順序〉的施壓端那一項），送不出負載的是施壓端，這次執行不代表受測服務（〈gate 失敗時的排查順序〉的施壓端那一項）；這個換算怎麼在自己的 test plan 上確認，寫在 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/) 的〈用 Open Model Thread Group 的排程寫出逐級加壓〉。Open Model Thread Group 的排程寫成一串指令：

```text
rate(0) random_arrivals(${__P(rampSec,60)} sec) rate(${__P(rate,20)}/sec) random_arrivals(${__P(holdSec,600)} sec) pause(10 sec)
```

這一串照官方文件〈Component Reference〉的 Open Model Thread Group 一節的語法組成，沒有實跑；到達率是 0 時文件允許省略時間單位，所以起點寫成 `rate(0)`，寫成 `rate(0/sec)` 也合法。到達率在 `rampSec` 秒內從 0 升到每秒 `rate` 個，再維持 `holdSec` 秒，最後的 `pause(10 sec)` 讓排程結束後還在跑的執行緒有時間收尾（文件寫明排程結束時 thread group 會中斷執行緒）。`${__P(名稱,預設值)}` 讀 JMeter 屬性，CLI 用 `-Jrate=40` 這類寫法傳值；`60`、`20`、`600` 是佔位值，取法見 [6.2 load test](/backend/06-reliability/load-testing/) 的〈Workload model 設計〉。文件也寫明排程只在測試開始時計算一次，用了函式時只取第一次的結果，所以到達率要在啟動時用 `-J` 給定，測試進行中改屬性不會改變到達率；PR 與 nightly 要不同的到達率時，在各自的 job 啟動 JMeter 時傳不同的值。這個元件在 JMeter 5.5 加入時標為實驗性，現行的元件說明仍寫著之後的版本可能改變它的行為，所以 gate 的證據要記下 JMeter 的版本：升級 JMeter 之後第一次執行的差距，可能來自負載模型本身。

模型要依 production 流量選：面向公眾的 API 屬於 open 型，用 Open Model Thread Group 或 Arrivals Thread Group，量到的延遲退化比較接近使用者會遇到的退化；呼叫端數量固定的服務（固定 worker 數的批次程式）用 Thread Group，量到的吞吐量下降對應的就是批次跑完的時間變長。既有的 `.jmx` 用 Thread Group 加 throughput timer 壓 open 型的服務時，gate 照樣比得出前後兩版的差，只是延遲退化的一部分會落在吞吐量上，延遲的門檻與吞吐量的下限都要設。

## listener、plugin 版本與 heap 對基準可比性的影響

JMeter 量到的每一筆 `elapsed`，是施壓端從送出請求到處理完回應的時間，施壓端自己排隊、做 GC 暫停的時間都算在裡面（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)）。所以施壓端的設定在兩次執行之間有任何不同，差距就有一部分屬於施壓端，比較的對象不再只有受測服務。JMeter 上會讓施壓端的工作量在兩次之間改變的設定有四類：

- **listener 與執行模式**：官方文件〈Getting Started〉要求負載測試用 CLI mode、不用 GUI mode；〈Best Practices〉建議 listener 盡量少用，用 `-l` 寫 JTL 時其他 listener 都可以刪掉或停用，View Results Tree 與 View Results in Table 只在寫腳本時用來除錯。基準那一次只用 `-l` 寫 JTL，這一次有人除錯時打開了 View Results Tree 而忘了停用，這一次的施壓端多了一個處理每一筆 sample 的 listener，施壓端的 CPU 與記憶體用量跟基準那一次不同，量到的延遲變長時，原因可能不在受測服務。Backend Listener 是非同步的 listener（官方文件〈Component Reference〉），把結果推到外部的時序資料庫；它同樣在施壓端花資源，兩次執行要都開或都不開。listener 的設定存在 `.jmx` 裡，所以 `.jmx` 的 diff 看得到它。
- **heap 與 GC 的設定**：JMeter 預設的 heap 是 1 GB（官方文件〈Getting Started〉），執行腳本讀 `HEAP` 與 `JVM_ARGS` 這類環境變數調整。heap 太小時 GC 頻繁，每次暫停的時間加進那段時間內每一筆 sample 的延遲；CI 的 runner image 換了一組 JVM 參數，兩次執行量到的尾端延遲就不同。這組參數不在 `.jmx` 裡，要在證據裡另外記下。
- **JMeter 與 Java 的版本**：remote testing 的文件要求所有節點跑完全相同版本的 JMeter，Java 版本不同可能可以運作但不建議；同一台施壓端在兩次執行之間升級版本，也會改變 HTTP client、thread group（尤其是標為實驗性的 Open Model Thread Group）與 dashboard 的行為。
- **plugin 的版本**：Concurrency Thread Group、Arrivals Thread Group、Throughput Shaping Timer 這些負載模型的元件來自 jmeter-plugins，版本不同時排程的行為可能不同。Plugins Manager 的命令列版本（jmeter-plugins.org〈Plugins Manager from Command-Line〉）用 `status` 列出已安裝的 plugin 與版本，用 `install <plugin ID>=<版本>` 安裝指定的版本：Concurrency Thread Group 與 Arrivals Thread Group 都在 ID 為 `jpgc-casutg` 的 Custom Thread Groups 套件裡，Throughput Shaping Timer 的 ID 是 `jpgc-tst`（jmeter-plugins.org 的[套件清單](https://jmeter-plugins.org/repo/)），寫成 `PluginsManagerCMD install jpgc-casutg=<版本>,jpgc-tst=<版本>`，`<版本>` 填基準那一次的證據裡 `status` 列出的版本。`install-for-jmx <檔案>` 依 test plan 用到的元件安裝 plugin，文件沒有寫它裝的是哪一個版本，CI 的 image 要固定版本時，用帶版本號的 `install`。

另外有一組設定不改變施壓端的工作量、而改變統計的定義：`user.properties` 與 `-J` 傳進來的屬性（`aggregate_rpt_pct1` 這類百分位數設定、`jmeter.save.saveservice.*` 決定 JTL 存哪些欄位）。它們不在 `.jmx` 裡，兩次執行的值不同時，`statistics.json` 同一個欄位名代表的統計值也不同。所以 gate 判讀兩次結果之前，先比對這四類設定與這組屬性；任一項不同，這次的差距要先當成條件不同，見〈gate 失敗時的排查順序〉。

## PR 與 nightly 兩種執行的分工

[6.1 CI pipeline](/backend/06-reliability/ci-pipeline/) 把 CI 分成每次 push 跑的 fast path、merge request 跑的 slow path 與排程跑的 scheduled path，6.13 沿用這三個名字，把 micro benchmark 放在 fast path、end-to-end 的效能測試放在 slow path 與 scheduled path。JMeter 對著部署好的受測環境送請求，屬於 end-to-end 的效能測試，所以不放在 fast path。PR 跑的那一次對應 slow path，nightly 或 release branch 跑的那一次對應 scheduled path，兩者抓的退化不同。

PR 跑的那一次負載低於飽和點（[Saturation Point](/backend/knowledge-cards/saturation-point/)）、只涵蓋關鍵流程，時間落在 slow path 的預算內，判讀用相對退化；它抓的是一次變更造成的明顯延遲退化與錯誤。它抓不到兩類：要長時間維持負載才出現的退化（記憶體洩漏、連線池慢慢耗盡、GC 暫停隨堆積的物件變長），以及每個請求的資源成本變高、而延遲主要花在等 I/O 時，在低負載下 CPU 還不是瓶頸、延遲幾乎不變的退化。後一類有兩個出口。一個是 gate 另外記錄受測服務每個請求的 CPU 用量（從受測服務的監控取，JMeter 量不到），拿它跟基準版本比。另一個是交給 nightly，在接近飽和的負載下量。nightly 跑的那一次時間長、流程完整，加上長時間維持負載的 soak 階段，抓的是與時間有關的退化；同一個版本多跑幾次、保存每一次的 JTL，就有了統計顯著性需要的樣本。

兩種執行共用同一份 `.jmx`，負載的差別用屬性傳進去：thread group 的執行緒數、到達率與持續時間寫成 `${__P(...)}`，PR 的 job 與 nightly 的 job 各自用 `-J` 給值。流程只寫一份，`.jmx` 改了流程，兩種執行量的仍然是同一個流程；兩邊的門檻各自寫在後處理的設定裡。兩種執行也共用同一份 CSV Data Set（餵帳號、商品編號這類測試資料給執行緒的設定元件），gate 只量得到 CSV 裡的資料走到的路徑：資料只有少數幾個熱門商品時，讀資料庫的長尾路徑兩版都沒有被請求到，這一版的變更若改到那條路徑，gate 對它沒有訊號；CSV 的資料怎麼從 production 取得接近的分佈，寫在 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 的〈從 production log 抽 workload model〉：從 access log 與 APM trace 抽樣、依 endpoint 分組算出百分位數與 payload 的分佈、保留抵達的間隔，以及脫敏。CI 跑 JMeter 的環境要跟其他工作隔開：staging 上同時有別的 QA 流量或排程工作在跑時，它們的負載混進受測服務的延遲與吞吐量，前後兩版的差距落在這些雜訊裡。這跟 6.13〈Variance 控制〉表裡 shared runner 鄰居效應那一列的性質類似，差在被共用的是受測環境，不是執行 CI 的 runner。

## JTL、dashboard 與執行條件的保存

JMeter 每次執行留下三種結果：JTL 是逐筆的原始紀錄，HTML dashboard 是給人讀的報告，`statistics.json` 是後處理讀的統計。三種裡 JTL 最值得保存：dashboard 與 `statistics.json` 都可以用 `-g` 從 JTL 重新產生，基準那一次的百分位數設定或統計區間跟這一次不同時，拿保存的 JTL 用這一次的設定重新產生一份，兩邊就比得了；只保存 `statistics.json` 時，設定不同的那一次就再也比不了。CI 的 job 把 JTL 與 dashboard 存成 build artifact 之外，要另外存在保留期限不受 CI 控制的位置（物件儲存、測試結果資料庫）：CI 平台的 artifact 有保留天數，基準那一次的檔案到期刪掉之後，下一次 gate 就沒有基準可比，而後處理只會回報讀不到檔案，或在程式沒寫好時直接通過。

結果只記錄這一次量到什麼；要讓另一個人判斷兩次結果比不比得了，CI 的 job 在同一份證據裡另外記下這幾組欄位：

- **6.2 的最小欄位**：[6.2 load test](/backend/06-reliability/load-testing/)〈Load test 結果的證據留存〉列的 workload model 版本、測試環境、saturation point、throughput ceiling、主要瓶頸歸因、headroom ratio、退化模式分類與測試日期。其中 saturation point、throughput ceiling 與 headroom ratio 填最近一次 6.2 load test 量到的值，gate 這一次的執行負載低於飽和點，量不出這三項。
- **test plan 與屬性**：`.jmx` 的版本（commit）、這次用 `-J` 傳進去的屬性與 `user.properties` 的內容、決定 JTL 內容的屬性（`sampleresult.timestamp.start`、`jmeter.save.saveservice.*`）、thread group 的種類與參數、CSV Data Set 的來源與產生日期。
- **施壓端**：JMeter 的版本（`jmeter --version` 的輸出）、Java 的版本、`HEAP` 與 `JVM_ARGS`、Plugins Manager `status` 列出的 plugin 與版本、施壓端的台數與規格（用了 remote testing 時，各節點的配置）。
- **受測環境**：受測服務的副本數、受測資料庫的資料量（或每次重建時用的 seed 版本）、下游哪些服務是 mock、沒有 mock 的下游各是哪一個版本。
- **比較的對象**：這次跟哪一次基準執行比（那一次的執行編號或 commit），以及後處理用的門檻設定是哪一個版本。

這些欄位跟著 gate 的判定交給下游的方式，照 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) 的〈Handoff 欄位〉。

## gate 失敗時的排查順序

JMeter 的 gate 失敗時，有三種誤判會讓差距看起來像這一版的退化：兩次執行的條件不同、施壓端飽和、差距落在雜訊之內。下面的執行條件、施壓端與雜訊範圍三項依序排除這三種誤判，退化的流程與幅度那一項是三種都排除之後、把差距歸給這一版的那一步。排除誤判的三項依兩件事排序：排除那種誤判要花多少力氣，以及前一項沒排除時後一項的讀數是否還能解讀。施壓端排在雜訊範圍之前就是後一個理由：雜訊範圍是受測服務在同一個版本重跑時的波動，施壓端飽和的那一次量到的值混進了施壓端自己的時間，拿它跟受測服務的雜訊範圍比，比出來的差距歸不到任何一方；施壓端的訊號又多半在 JTL 裡就查得到，不必重跑。

1. **兩次執行的條件**：比對證據裡兩邊記下的條件，`.jmx`、屬性、thread group 的參數、JMeter 與 Java 的版本、plugin 版本、heap、受測環境、副本數、施壓端配置、沒有 mock 的下游版本有任一項不同，差距就不能歸給這一版的變更。JMeter 上容易漏的有四種：`.jmx` 的 diff 裡有人打開了 View Results Tree 或加了 assertion（施壓端的工作量變了）；sampler 改了名稱（後處理找不到那個 label，或拿新名字跟基準裡的另一個 sampler 比）；`aggregate_rpt_pct*` 的值不同（同一個欄位名代表不同的百分位數，拿保存的 JTL 用同一組設定重新產生 `statistics.json` 就排除得了）；CSV Data Set 的資料過期（基準版本與這一次相隔幾天時，token 或商品過期，請求回錯誤，錯誤率的門檻失敗）。受測資料庫的資料量隨每次執行寫入而變大、staging 上的鄰居流量，跟其他工具一樣算條件不同或雜訊；基準那一次本身是離群值時，基準的選法見 6.13 的〈Baseline 設定〉。這一項只要比對紀錄，花的力氣最少。
2. **施壓端的資源**：施壓端的 CPU、記憶體、GC 暫停、網路頻寬、檔案描述元或來源埠用完時，量到的延遲包含施壓端自己的時間，gate 的結果不代表受測服務。JTL 裡有兩個不必另外收集指標的訊號，兩者都只看得到「負載沒有送足」：closed model 下 `allThreads` 沒有到達設定的執行緒數，代表施壓端沒有把執行緒全部放進去；open model 下實際開始的 iteration 數低於排程，代表施壓端送不出設定的到達率。iteration 的開始次數用「每輪都會執行、而且會寫出 sample 的第一個 sampler」的列數算，依 `timeStamp` 每秒數一次，它就是實際的到達率。這個 sampler 不能是 Flow Control Action（官方〈Component Reference〉寫明它不產生 sample result），不能包在 Once Only、If 或 Loop Controller 裡，也不是 Transaction Controller 產生的那一筆。依 `timeStamp` 分到每一秒的做法依賴 `sampleresult.timestamp.start=true`；不是 `true` 時記的是結束時間，每一筆往後位移一個延遲，每秒的計數跟著位移，總數不變。直接數 JTL 的全部列數，有兩種情形會讀錯。一種是錯誤讓一輪提早結束：thread group 的 Action to be taken after a Sampler error 設成 Start Next Thread Loop，或 If Controller 依回應決定要不要送後面的 sampler 時，受測服務回錯會讓那一輪少送幾個請求，每秒請求數下降，而施壓端沒有飽和。另一種是 JTL 裡不只 sampler 的列：Transaction Controller 產生的那一筆、以及 `jmeter.save.saveservice.subresults`（預設 `true`）存下的子結果（例如 HTTP 重導的各段）也各占一列，全部列數會高估請求數。要用全部列數換算時，只數 sampler 的列，乘數改成一輪實際寫進 JTL 的列數，並先排除錯誤造成的提早結束。

   這兩個訊號正常時也排除不了三類情形。施壓端的 CPU 飽和時，closed model 的執行緒數照樣到達設定值，只是每一輪變慢。GC 暫停與頻寬用完只加長延遲、不減少送出的請求。檔案描述元或來源埠用完時，請求以失敗記下，`responseCode` 寫成 `Non HTTP response code: <例外的類別名稱>`，`responseMessage` 寫成 `Non HTTP response message: <例外的訊息>`（原始碼 `HTTPSamplerBase` 的 `errorResult`），在錯誤率上看起來像受測服務的錯誤，讀 `responseCode` 才分得出來。這三類要靠施壓端的 GC log 與資源指標，或比對 JMeter 量到的延遲與受測服務入口量到的延遲：兩者的差距變大，多出來的時間花在施壓端或網路上。判斷 GC 是否比基準那一次頻繁，比對兩次執行在量測區間內 GC 暫停的總時間；沒有 GC log 時，看那個延遲差距有沒有變大。

   用了 remote testing 時，每個節點跑完整的 test plan：官方文件〈Remote Testing〉寫明 JMeter 不在節點之間分配負載，設 1000 個執行緒、6 個節點，就送出 6000 個執行緒的負載。結果預設以 StrippedBatch 模式成批送回發起測試的那一台（同一份文件的 `mode` 屬性）。所以比較的對象是單一節點的排程乘以節點數，或在寫 JTL 的那一台（發起測試的 client）設 `jmeter.save.saveservice.hostname=true`（預設 `false`）讓 JTL 多一欄 Hostname，分節點計算；`allThreads` 是不是每個節點的 JVM 各自計數，文件沒有寫，依它記的是當下活躍的執行緒數推論是各自計數（沒有實跑）。發起測試的那一台也要一起檢查，分散施壓的檢查方法在 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/) 的〈分散施壓：remote mode 的結果回傳、Backend Listener 與資料檔〉。

   這兩種方法都拿不到時（CI 沒有收集施壓端的指標、受測服務入口也量不到延遲），這一項無法排除，這次 gate 的結果是無結論：失敗不足以當成退化的證據，通過也不足以當成沒有退化的證據，處置是補上施壓端的指標收集後重跑。
3. **差距與雜訊的範圍**：CI 在建立 baseline 時把同一個版本重跑幾次（次數與樣本量的取法見 6.13 的〈Regression 判讀方法〉），gate 用到的每一個統計值（`pct2ResTime` 這類百分位數、`errorPct`，closed model 的 gate 還有 `throughput`）的波動範圍就是它的雜訊範圍：同一個版本幾次執行裡那個統計值最高與最低的差，占基準值的百分比；這個範圍怎麼限制門檻能設多窄，寫在 6.13 的〈Baseline 設定〉與〈相對退化〉。退化的幅度小於這個範圍時，這次的差距還不能當成退化的證據；門檻設得比這個範圍窄時，gate 會反覆誤報，團隊開始略過它。雜訊範圍大到超過想抓的退化幅度時（例如每次波動 15%，而想抓 5% 的退化），單次執行的比較抓不到這個幅度，要照 6.13〈Variance 控制〉縮小雜訊，或在 scheduled path 保存多次執行的 JTL、用統計顯著性判讀。錯誤率的門檻失敗時，這一項另外要分出 assertion 誤報：失敗的那幾筆在 JTL 的 `failureMessage` 欄位寫著 Duration Assertion 的訊息（回應時間超過設定的毫秒數）、而受測服務沒有回錯誤時，錯誤率上升來自〈逐筆 assertion 與統計門檻的分工〉那一段寫的混用，延遲的變化要回到百分位數與它的雜訊範圍判讀，test plan 的 assertion 要改成只檢查正確性。
4. **退化的流程與幅度**：執行條件、施壓端與雜訊範圍都排除之後，差距屬於這一版的變更。後處理逐個 label 的輸出與 dashboard 指出是哪一個流程、在哪一段時間退化。退化落在有自己門檻的關鍵流程時，那一條門檻失敗本身就是擋下 release 的依據，原因的定位方法在 6.13〈退化定位與行動〉的 profiling diff 與 commit bisect。吞吐量的下限失敗、而各流程的延遲門檻都通過時，執行條件、施壓端與雜訊範圍都排除之後的第一步，是比對各流程延遲的變化量再歸因：closed model 下幾個流程的延遲各上升一點，即使都在各自的門檻內，加起來讓一輪變長、整次執行的吞吐量下降，這時退化分散在那幾個流程的延遲上，定位要從變化量最大的那幾個流程開始。gate 用了涵蓋整次執行的門檻時（後處理讀的 `Total` 那一列、Jenkins 依結果檔設的門檻、Taurus 沒有限定 label 的條件），失敗的是這一類門檻、而退化落在關鍵流程以外的 sampler 時，判斷看這些請求在服務的效能預算（[Performance Budget](/backend/knowledge-cards/performance-budget/)）裡有沒有額度：預算有涵蓋它們，這次退化照樣擋下；預算沒有涵蓋，要回到 6.13 的〈Regression 判讀方法〉決定門檻的範圍與值。在那之前若決定放行，放行的人、理由與這次的差距要跟著 gate 的判定寫進證據（6.23〈Handoff 欄位〉），代價是這些請求的退化會累積到下一次調整門檻。

同樣看到 p95 變慢，用 JMeter 做容量探測時，排查從施壓端與實際送出的負載查起，要判斷的是受測服務哪一項資源先飽和，順序與這裡不同，寫在 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/) 的〈延遲上升或吞吐量停滯時的排查順序〉。

## 相關章節與工具頁：gate 的方法、load test 的 baseline、其他工具的 gate 與遷移

- [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)：baseline 的 production percentile、CI benchmark history 與 load test 結果三種來源，絕對門檻、相對退化與統計顯著性三種判讀方法，以及 variance 控制；本篇的門檻落點與排查順序都建立在它上面。
- [6.2 load test](/backend/06-reliability/load-testing/)：訂定 gate 拿來比對的 baseline 與 saturation point，以及 load test 結果要留存的欄位。
- [Gatling 在效能 regression gate 的用法：assertion 的門檻、ramp-up 與量測區間、注入模型、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/)：同一類 gate 換成 Gatling 時，assertion 在工具內部決定執行的成敗，而 OSS 版的跨次比較要從受測服務那一端取量測。
- [k6：Threshold CI Gate 與 Scenario 設計](/backend/06-reliability/vendors/k6/threshold-ci-gate-and-scenario-design/)：同一類 gate 換成 k6 時，threshold 與 executor 的寫法。
- [JMeter → k6：k6 不是 JMeter 的「script 版本」、是 VU model 取代 thread model](/backend/09-performance-capacity/vendors/k6/migrate-from-jmeter/)：考慮把 gate 從 JMeter 搬到 k6 時，thread group 換成 executor 的落差，以及讀 JTL 的後處理要重寫的部分。
