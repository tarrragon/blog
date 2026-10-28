---
title: "JMeter 在本機跑負載測試的實測紀錄：Docker image、test plan 的元件、CSV Data Set、CLI mode 與 JTL、dashboard 與 statistics.json、JMeter 之外的門檻判定、remote testing 的 client 與 server"
date: 2026-10-28
description: "要在本機用 Docker 照一次實測跑 JMeter：建 image、寫 test plan、從 CSV 餵測試資料、用 CLI mode 跑出 JTL 與 dashboard、讀 statistics.json 判定門檻、開 client 與多台 server 做 remote testing 時讀；也用在 sample 失敗了 exit code 還是 0、CSV 裡某些值從來沒被請求到、-J 傳的屬性在 server 上沒有作用、-o 回報資料夾不是空的時候"
weight: 1
tags: ["backend", "reliability", "vendor", "jmeter", "load-test", "hands-on"]
slug: "jmeter-local-lab"
---

實測日期是 2026-10-28，環境是一台 macOS 筆電上的 Docker（server 29.8.2，Docker 可用 8 顆 CPU 與 8 GB 記憶體），JMeter 5.6.3 跑在以 `eclipse-temurin:21-jre`（`java -version` 印出 21.0.12.1）自建的 image 裡，受測服務是同一個 Docker network 裡另一個 container 跑的 Python 標準函式庫程式；這次的操作是從手寫一份 test plan 開始，用 CLI mode 執行、產生報告、在 JMeter 之外判定門檻，最後開一台 client 與兩台 server 做 remote testing。

這篇記錄在本機用 Docker 跑 JMeter 的完整操作：自建 JMeter image 並核對發行檔的雜湊值；test plan 裡各元件負責的事（HTTP Request Defaults、CSV Data Set、Thread Group、只登入一次的 Once Only Controller、依隨機數挑請求的 If Controller、放使用者停頓時間（think time）的 Flow Control Action）；CLI mode 的參數與 JTL 的欄位；這次遇到的 Throughput Controller 與 CSV Data Set 週期對齊、讓某個商品編號從來沒被請求到的情形與改法；有失敗的 sample（JMeter 對一次請求的量測紀錄）時 exit code 仍然是 0；HTML dashboard 與 `statistics.json`，以及用 `-g` 從 JTL 重新產生報告；一支讀 `statistics.json` 判定門檻的程式；remote testing 的 client 與 server 怎麼啟動、`-J` 與 `-G` 的差別、JTL 怎麼分出來自哪一台 server；最後是清理。受測服務與 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 用的是同一支程式，兩篇的負載模型也對齊（每個使用者登入一次、商品頁與會失敗的 endpoint 四比一、每一輪停 1 到 3 秒），讀者可以拿同一個受測服務比較兩個工具的輸出。這些操作背後的判斷，也就是 CI 用這次的量測擋下效能退化（效能 regression gate，下文簡稱 gate）時，門檻判定為什麼放在 JMeter 之外、逐筆 assertion 與統計門檻怎麼分工、gate 失敗時依什麼順序排除誤判，寫在 [JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/)；用 JMeter 逐級加壓找飽和點的做法寫在 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/)。GUI 的操作、HTTP(S) Test Script Recorder 的錄製與 plugin 都不在這次的實測裡。

## 受測服務

受測服務是一支只依賴 Python 標準函式庫的 HTTP 程式，`GET /items/<id>` 正常回應（`DELAY_MS` 環境變數可以加上固定延遲），`GET /flaky` 每 10 個請求回一次 500，`POST /login` 回一個 token。這篇不重列程式：開始之前先打開 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈受測服務：標準函式庫寫的 HTTP 程式〉，把那段程式存成 `target/app.py`，那一節也寫了它為什麼這樣設計。

這篇的程式碼區塊裡，`#` 開頭的那幾行是說明或預期的輸出；macOS 內建的 zsh 在互動模式下預設不把 `#` 當成註解，貼上之前先在同一個終端機分頁執行一次 `setopt interactivecomments`（只對這個 shell 有效），否則那幾行會印出 `command not found: #`；用 bash 時不需要這一步，bash 沒有 `setopt` 這個指令。`-v` 掛載本機的目錄，在 macOS 的 Docker Desktop 上這個目錄要在 Settings 的 File sharing 列出的路徑裡（預設是 `/Users`、`/Volumes`、`/private`、`/tmp`、`/var/folders`），不在的話 `docker run` 回 `Mounts denied`（依 Docker Desktop 官方文件的設定說明，這次沒有實跑）；OrbStack 不限定路徑，`/Users` 以外的目錄也掛得進去。在 Linux 主機上，container 以 root 寫出的 `jmeter/out/` 與 `jmeter/jmeter.log` 歸 root 所有，CI 重用工作目錄時下一次清理要 sudo（這一點從 container 以 root 執行推出，沒有在 Linux 上實跑）。啟動方式相同：

```bash
docker network create loadlab
docker run -d --rm --name target --network loadlab \
  -v "$PWD/target:/app:ro" python:3.12-slim python /app/app.py
# 從同一個 network 裡確認服務在回應，印出 {"id": "42"} 就是起來了
docker run --rm --network loadlab curlimages/curl:8.10.1 -s http://target:8080/items/42
```

`loadlab` 是這次建的 Docker network，`target` 是受測服務的 container 名稱，也是 JMeter 在同一個 network 裡連它用的主機名；`$PWD/target` 換成讀者放 `app.py` 的目錄。這篇的指令都在 `target/`、`jmeter/` 兩個目錄的上一層執行。自建的 network 讓 container 之間用名稱連線，後面的 `target`、`js1`、`jclient` 都靠它解析；改用 Docker 預設的 bridge network 時，container 之間不能用名稱連，要改填 IP，這次沒有實跑。

## 自建 JMeter 的 image

這次用 Java 的 JRE image 加上 Apache 的官方發行檔自己建，JMeter 的版本、Java 的版本與下載來源都寫在自己的 Dockerfile 裡。下面的內容存成 `jmeter/Dockerfile`：

```dockerfile
FROM eclipse-temurin:21-jre
ARG JMETER_VERSION=5.6.3
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz -o /tmp/jmeter.tgz \
 && curl -fsSL https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz.sha512 -o /tmp/jmeter.tgz.sha512 \
 && echo "$(cut -d' ' -f1 /tmp/jmeter.tgz.sha512)  /tmp/jmeter.tgz" | sha512sum -c - \
 && tar -xzf /tmp/jmeter.tgz -C /opt && rm /tmp/jmeter.tgz*
ENV PATH=/opt/apache-jmeter-${JMETER_VERSION}/bin:$PATH
WORKDIR /mnt/jmeter
```

```bash
docker build -t lab-jmeter jmeter/
# ASCII 字的 banner 最後一行結尾印出 5.6.3
docker run --rm lab-jmeter jmeter --version
# 後面的結果與報告都寫在 out/ 底下；JMeter 只建報告那一層資料夾，不建 out/ 本身
mkdir -p jmeter/out
```

`JMETER_VERSION` 寫死成 5.6.3，是建 image 當天 archive.apache.org 上最新的版本；基底的 Java 21 取的是當天的 LTS 版，沒有比較其他 Java 版本，而 `eclipse-temurin:21-jre` 這個 tag 會跟著 patch 版更新（這次是 21.0.12.1），要讓兩次執行的基底相同，改用帶完整版本的 tag 或 `@sha256:<建 image 當天的 digest>`（這次沒有實跑）。讀者重做時先查 archive.apache.org 的 `jmeter/binaries/` 目錄，版本不同時兩次結果要記下各自的版本才比得了。Dockerfile 裡的 `sha512sum -c` 拿官方同目錄的 `.sha512` 檔核對下載的檔案，雜湊對不上時 `docker build` 失敗、不會建出 image；省略這一步也建得出來，代價是下載被截斷或被替換時不會被發現。這次從 archive.apache.org 下載大約花了兩分鐘（依網路與當時 archive 的負載而變），官方的鏡像站（`dlcdn.apache.org`）分散在各地，這次沒有實測它的下載時間，但它只放最新版，版本更新之後舊版的網址就失效，所以 Dockerfile 用 archive。`jmeter/out` 不先建的話，第一次執行的 `-e -o out/report1` 回 exit 1，訊息是 `Cannot write to '/mnt/jmeter/out/report1' as folder does not exist and parent folder is not writable`。`jmeter/` 是放 Dockerfile 與 test plan 的目錄，`WORKDIR /mnt/jmeter` 是之後把它掛進 container 的位置，test plan 裡用相對路徑讀的 `items.csv` 從這裡找。

替代做法有兩種，這次都沒有實跑：在本機裝 Java 與 JMeter 的發行檔（官方文件〈Getting Started〉），換到的是可以開 GUI 編輯 test plan，付出的是本機的 Java 版本與 JVM 參數會影響結果；用社群維護的 image（Docker Hub 上有幾個），換到的是不必自己寫 Dockerfile，付出的是 JMeter 版本、預裝的 plugin 與 JVM 參數由維護者決定，要先讀它的 Dockerfile。

## test plan 的元件

test plan 是一個 `.jmx` 檔，平常在 JMeter 的 GUI 裡編輯、存檔就是這個格式；這次沒有開 GUI，直接手寫 XML，GUI 打開它會顯示同樣的樹狀結構。讀這棵樹之前要先知道三個名詞：JMeter 用一個 thread 代表一個虛擬使用者；thread 把 thread group 底下的元件由上到下執行一次叫一輪（iteration），跑完再從頭開始下一輪；sampler 是實際送出一個請求的元件（樹裡的 `POST /login`、`GET /items/[id]`、`GET /flaky`），每執行一次產生一筆 sample。元件由上而下是：

```text
shop（Test Plan）
├── HTTP Request Defaults    主機 ${__P(host,target)}、port ${__P(port,8080)}
├── items.csv（CSV Data Set）  每一輪讀一行，變數名取檔案第一行 item_id
└── shoppers（Thread Group）  thread 數、ramp-up（逐步啟動 thread 的期間）、持續時間都從屬性讀
    ├── roll 1-5（Random Variable）     每一輪產生 1 到 5 的隨機數
    ├── login once（Once Only Controller）
    │   └── POST /login  ── token（JSON Extractor，$.token 存進 ${token}）
    ├── items 4/5（If Controller：roll <= 4）
    │   └── GET /items/${item_id}  ── auth（Header Manager：Bearer ${token}）
    ├── flaky 1/5（If Controller：roll == 5）
    │   └── GET /flaky
    └── think（Flow Control Action）── think 1-3s（Uniform Random Timer）
```

`.jmx` 的全文，存成 `jmeter/shop2.jmx`，同一個目錄放 `items.csv`（第一行是表頭 `item_id`，下面五行是 `101` 到 `105`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="shop">
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments" guiclass="ArgumentsPanel" testclass="Arguments">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
    </TestPlan>
    <hashTree>
      <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults">
        <elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments">
          <collectionProp name="Arguments.arguments"/>
        </elementProp>
        <stringProp name="HTTPSampler.domain">${__P(host,target)}</stringProp>
        <stringProp name="HTTPSampler.port">${__P(port,8080)}</stringProp>
        <stringProp name="HTTPSampler.protocol">http</stringProp>
      </ConfigTestElement>
      <hashTree/>
      <CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet" testname="items.csv">
        <stringProp name="filename">items.csv</stringProp>
        <stringProp name="fileEncoding">UTF-8</stringProp>
        <stringProp name="variableNames"></stringProp>
        <boolProp name="ignoreFirstLine">false</boolProp>
        <stringProp name="delimiter">,</stringProp>
        <boolProp name="quotedData">false</boolProp>
        <boolProp name="recycle">true</boolProp>
        <boolProp name="stopThread">false</boolProp>
        <stringProp name="shareMode">shareMode.all</stringProp>
      </CSVDataSet>
      <hashTree/>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="shoppers">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControlPanel" testclass="LoopController">
          <intProp name="LoopController.loops">-1</intProp>
          <boolProp name="LoopController.continue_forever">false</boolProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">${__P(threads,10)}</stringProp>
        <stringProp name="ThreadGroup.ramp_time">${__P(rampup,5)}</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">${__P(duration,30)}</stringProp>
        <stringProp name="ThreadGroup.delay"></stringProp>
        <boolProp name="ThreadGroup.same_user_on_next_iteration">true</boolProp>
      </ThreadGroup>
      <hashTree>
        <RandomVariableConfig guiclass="TestBeanGUI" testclass="RandomVariableConfig" testname="roll 1-5">
          <stringProp name="variableName">roll</stringProp>
          <stringProp name="outputFormat"></stringProp>
          <stringProp name="minimumValue">1</stringProp>
          <stringProp name="maximumValue">5</stringProp>
          <stringProp name="randomSeed"></stringProp>
          <boolProp name="perThread">false</boolProp>
        </RandomVariableConfig>
        <hashTree/>
        <OnceOnlyController guiclass="OnceOnlyControllerGui" testclass="OnceOnlyController" testname="login once"/>
        <hashTree>
          <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="POST /login">
            <boolProp name="HTTPSampler.postBodyRaw">true</boolProp>
            <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
              <collectionProp name="Arguments.arguments">
                <elementProp name="" elementType="HTTPArgument">
                  <boolProp name="HTTPArgument.always_encode">false</boolProp>
                  <stringProp name="Argument.value">{"user":"load-test"}</stringProp>
                  <stringProp name="Argument.metadata">=</stringProp>
                </elementProp>
              </collectionProp>
            </elementProp>
            <stringProp name="HTTPSampler.path">/login</stringProp>
            <stringProp name="HTTPSampler.method">POST</stringProp>
            <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          </HTTPSamplerProxy>
          <hashTree>
            <JSONPostProcessor guiclass="JSONPostProcessorGui" testclass="JSONPostProcessor" testname="token">
              <stringProp name="JSONPostProcessor.referenceNames">token</stringProp>
              <stringProp name="JSONPostProcessor.jsonPathExprs">$.token</stringProp>
              <stringProp name="JSONPostProcessor.match_numbers">1</stringProp>
              <stringProp name="JSONPostProcessor.defaultValues">NOT_FOUND</stringProp>
            </JSONPostProcessor>
            <hashTree/>
          </hashTree>
        </hashTree>
        <IfController guiclass="IfControllerPanel" testclass="IfController" testname="items 4/5">
          <stringProp name="IfController.condition">${__jexl3(${roll} &lt;= 4)}</stringProp>
          <boolProp name="IfController.evaluateAll">false</boolProp>
          <boolProp name="IfController.useExpression">true</boolProp>
        </IfController>
        <hashTree>
          <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="GET /items/[id]">
            <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
              <collectionProp name="Arguments.arguments"/>
            </elementProp>
            <stringProp name="HTTPSampler.path">/items/${item_id}</stringProp>
            <stringProp name="HTTPSampler.method">GET</stringProp>
            <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          </HTTPSamplerProxy>
          <hashTree>
            <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="auth">
              <collectionProp name="HeaderManager.headers">
                <elementProp name="" elementType="Header">
                  <stringProp name="Header.name">Authorization</stringProp>
                  <stringProp name="Header.value">Bearer ${token}</stringProp>
                </elementProp>
              </collectionProp>
            </HeaderManager>
            <hashTree/>
          </hashTree>
        </hashTree>
        <IfController guiclass="IfControllerPanel" testclass="IfController" testname="flaky 1/5">
          <stringProp name="IfController.condition">${__jexl3(${roll} == 5)}</stringProp>
          <boolProp name="IfController.evaluateAll">false</boolProp>
          <boolProp name="IfController.useExpression">true</boolProp>
        </IfController>
        <hashTree>
          <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="GET /flaky">
            <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
              <collectionProp name="Arguments.arguments"/>
            </elementProp>
            <stringProp name="HTTPSampler.path">/flaky</stringProp>
            <stringProp name="HTTPSampler.method">GET</stringProp>
            <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          </HTTPSamplerProxy>
          <hashTree/>
        </hashTree>
        <TestAction guiclass="TestActionGui" testclass="TestAction" testname="think">
          <intProp name="ActionProcessor.action">1</intProp>
          <intProp name="ActionProcessor.target">0</intProp>
          <stringProp name="ActionProcessor.duration">0</stringProp>
        </TestAction>
        <hashTree>
          <UniformRandomTimer guiclass="UniformRandomTimerGui" testclass="UniformRandomTimer" testname="think 1-3s">
            <stringProp name="ConstantTimer.delay">1000</stringProp>
            <stringProp name="RandomTimer.range">2000</stringProp>
          </UniformRandomTimer>
          <hashTree/>
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

各元件在這份 test plan 裡負責的事：

- **HTTP Request Defaults**：所有 HTTP sampler 沒填的主機與 port 從這裡取，值寫成 `${__P(host,target)}`，執行時用 `-Jhost=...` 換掉，不必改 `.jmx`；`target` 是沒給屬性時的預設值。
- **CSV Data Set**：`items.csv` 第一行是表頭 `item_id`，下面五行是 `101` 到 `105`。`variableNames` 留空時，JMeter 把第一行當成變數名，所以 sampler 裡寫 `${item_id}`。`shareMode.all` 讓所有 thread 共用同一個讀取位置，每個 thread 每一輪讀下一行，讀到檔尾時 `recycle` 讓它回到開頭。這三個欄位接受別的值，這次都沒有實跑，依官方文件〈Component Reference〉的 CSV Data Set Config：`shareMode` 改成每個 thread 各自一份時，每個 thread 從第一行讀起，同一時間的請求集中在前幾行；`recycle` 改成 false、`stopThread` 改成 true 時，讀到檔尾的那個 thread 就停止，測試會在資料用完時提早結束。
- **Thread Group**：`num_threads`、`ramp_time`、`duration` 都從屬性讀；`loops` 是 `-1`（不限次數），由 `scheduler` 加 `duration` 決定什麼時候結束。這是 closed model：固定的 thread 數各自送出請求、等回應、停完再開始下一輪（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)）。`same_user_on_next_iteration` 是 GUI 上的 Same user on each iteration，勾選時連線在每一輪之間保留，這次的受測服務用 HTTP，沒有 TLS 握手的成本；換成 HTTPS 的服務時，這個選項決定每一輪要不要重做握手（[TLS Handshake（TLS 握手）的成本與連線重用](/backend/knowledge-cards/tls-handshake-cost/)）。不勾選時，`httpclient.reset_state_on_thread_group_iteration` 的預設值 true 讓每一輪開頭關掉連線，每一輪的第一個請求都重新建立連線，〈CLI mode 執行與 JTL〉數的 `Connect` 大於 0 的筆數會接近總輪數、不是 thread 數；sampler 的 keep-alive 關掉時，每個請求都重新建立連線（依官方文件與那張卡推出，這次沒有實跑）。Thread Group 本身也可以換：換成 5.5 起內建的 Open Model Thread Group 時，每次抵達建立一個新 thread、跑完一輪就結束，是 open model，每次抵達都重新建立連線，Once Only Controller 的登入也變成每次抵達一次；timer 換成 Constant Throughput Timer 或 Precise Throughput Timer 時是 pacing，仍然是 closed model（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的 pacing 那一段）。這兩種這次都沒有實跑。`on_sample_error` 是 `continue`：一個 sample 失敗時，這一輪接著跑後面的元件；改成 Stop Test 時，第一個 `/flaky` 回 500 就結束整次測試，改成 Start Next Thread Loop 時跳過這一輪剩下的元件（官方文件〈Component Reference〉的 Thread Group，這次沒有實跑）。
- **Random Variable 與兩個 If Controller**：每一輪開頭產生一個 1 到 5 的整數 `roll`，`roll` 小於等於 4 時送 `GET /items/[id]`、等於 5 時送 `GET /flaky`，兩者互斥，比例平均是四比一。為什麼不用 Throughput Controller，見〈Throughput Controller 與 CSV Data Set 的週期對齊〉。
- **Once Only Controller 與 JSON Extractor**：每個 thread 只在第一輪送 `POST /login`，JSON Extractor 從回應取出 `$.token` 存進這個 thread 的變數 `token`，之後每一輪的 Header Manager 用它。登入寫在每一輪裡的話，每一輪都多一次登入，登入的 endpoint 變成主要的負載來源。
- **Flow Control Action 加 Uniform Random Timer**：timer 讓 thread 在它範圍內的每一個 sampler 執行之前停一次，範圍是 timer 所在那一層與底下的元件；掛在 thread group 底下時，登入、商品頁、會失敗的 endpoint 前面都會停。這次把 timer 掛在一個 Flow Control Action 底下，放在每一輪的最後，所以每一輪只停一次，停 1000 毫秒加上 0 到 2000 毫秒的隨機值。Flow Control Action 不產生 sample，JTL 裡沒有它的列。
- **sampler 的名稱**：`GET /items/[id]` 是這個 sampler 在 JTL 與報告裡的 label，`[id]` 只是給人讀的名稱；不同商品編號的請求都算進同一個 label，因為 JMeter 依 sampler 的名稱分列統計，不依實際送出的網址。

## Throughput Controller 與 CSV Data Set 的週期對齊：某個商品編號沒被請求到的成因與改法

第一版的 test plan 用兩個 Throughput Controller 控制比例：一個設成 80% 包住商品頁，一個設成 20% 包住會失敗的 endpoint。要重現這一段時，把上一節的 `.jmx` 另存一份 `jmeter/shop1.jmx`，刪掉 `roll 1-5` 那個 `RandomVariableConfig`（連同它後面的 `<hashTree/>`），再把兩個 `IfController` 元素各換成一個 Throughput Controller，各自後面那段包著 sampler 的 `<hashTree>…</hashTree>` 保留不動。商品頁那一個是：

```xml
<ThroughputController guiclass="ThroughputControllerGui" testclass="ThroughputController" testname="items 80%">
  <intProp name="ThroughputController.style">1</intProp>              <!-- 1 是百分比模式 -->
  <boolProp name="ThroughputController.perThread">false</boolProp>    <!-- 計數由所有 thread 共用 -->
  <intProp name="ThroughputController.maxThroughput">1</intProp>
  <FloatProperty>
    <name>ThroughputController.percentThroughput</name>
    <value>80.0</value>
    <savedValue>0.0</savedValue>
  </FloatProperty>
</ThroughputController>
```

會失敗的 endpoint 那一個只差 `testname` 與 `<value>`（`flaky 20%`、`20.0`）。兩個 Throughput Controller 各自用全域的計數決定這一輪要不要執行，下文的算式代入之後，20% 那一個只在 80% 那一個跳過的那幾輪執行，兩者剛好互補，每一輪送出其中一個請求，每 5 輪剛好 4 輪商品頁、1 輪會失敗的 endpoint（這次 JTL 裡有請求的 141 輪中商品頁 113 筆、會失敗的 endpoint 28 筆；duration 到時已經開始、還沒送出請求的那幾輪不在 JTL 裡）。跑完之後依 URL 數 JTL 裡商品頁的請求：

```bash
docker run --rm --network loadlab -v "$PWD/jmeter:/mnt/jmeter" lab-jmeter \
  jmeter -n -t shop1.jmx -l out/run1.jtl -e -o out/report1 -f -Jthreads=10 -Jduration=30
awk -F, 'NR>1 && $3 ~ /items/ {print $14}' jmeter/out/run1.jtl | sort | uniq -c
#   28 http://target:8080/items/101
#   28 http://target:8080/items/102
#   29 http://target:8080/items/104
#   28 http://target:8080/items/105
```

這條 `jmeter` 指令的參數在〈CLI mode 執行與 JTL〉逐一說明；`-f` 讓重跑時先刪掉上一次的 `out/run1.jtl` 與 `out/report1`。`$3` 是 JTL 的 `label` 欄，`$14` 是 `URL` 欄；`awk -F,` 只在欄位裡沒有逗號時對得上欄號，錯誤訊息這類欄位帶逗號時 JMeter 會加引號，後面的欄號跟著位移，這時改用懂 CSV 引號的工具（例如 Python 的 `csv` 模組）。這次的錯誤訊息沒有逗號，所以對得上。`103` 一次都沒有出現，報告上的錯誤率、延遲看不出任何異樣。成因是兩個各自正確的元件週期對齊了。

Throughput Controller 的百分比模式是確定性的計數。5.6.3 的原始碼 `ThroughputController` 在測試開始時把「輪數」設成 -1，每一輪開頭先加 1（所以第 1 輪的輪數是 0），再拿「這一輪之前已執行的次數」代入 `(100 × 已執行次數 + 50) ÷ (輪數 + 1)`，小於設定的百分比時才執行；`perThread` 是 false 時，兩個計數都是所有 thread 合計的值。以 80% 代入，第 1、2 輪的值是 50、75，都執行；第 3 輪是 250 ÷ 3 = 83.3，跳過；之後第 8、13、18……輪被跳過，也就是 Throughput Controller 每 5 輪固定跳過 1 輪。20% 那一個代入同一個算式，正好只在第 3、8、13……輪執行。

CSV Data Set 在 `shareMode.all` 下同樣由所有 thread 共用，每一輪往下讀一行，5 行一個循環。兩個全域的序列週期都是 5，商品頁被跳過的第 3、8、13……輪，每次都讀到 CSV 的第 3 行 `103`；改了百分比或 CSV 的行數之後，被跳過的輪次可能固定對到另一行，也可能分散到每一行：Throughput Controller 的週期與 CSV 的行數有公因數時，固定對到某幾行；兩者互質時，分散到每一行。thread 同時開始新的一輪時，讀 CSV 與 Throughput Controller 的判定之間可能被別的 thread 插進來而錯開一格，所以沒有停頓、thread 很多的負載下，那一行仍可能有少量請求，筆數明顯偏少（這一點從機制推出，沒有實跑）。

這次只是少了一個商品編號；資料多、比例不同時，同樣的對齊會讓 CSV 裡固定對到被跳過那一輪的那幾行資料永遠不被請求，受測服務的快取命中率跟著偏離 production，量到的延遲偏低（測試資料怎麼取得接近 production 的分佈，見 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)）。改法是讓「這一輪送哪一個請求」跟 CSV 的位置無關，也就是〈test plan 的元件〉那一版的 Random Variable 加兩個 If Controller。改完之後照〈CLI mode 執行與 JTL〉的指令跑出 `out/run2.jtl`，把上面那條 `awk` 的檔名換成 `jmeter/out/run2.jtl` 再數，五個商品編號各有 19 到 23 筆；隨機數每次不同，這個筆數每次重跑都會變。這個改法的代價是比例變成隨機的：這次 125 輪裡會失敗的 endpoint 有 19 筆，佔 15%，不是 20%，兩次執行的比例不同時，`Total` 的延遲與錯誤率跟著變，樣本少的 PR 執行受影響最大。要同時保住精確的四比一，可以保留 Throughput Controller、改用 Random Variable 產生商品編號（不從 CSV 依序讀）；另一種做法是把 CSV 的行數改成跟 Throughput Controller 的週期互質，代價是改了比例或資料量之後要重新檢查一次。這兩種這次都沒有實跑。在 `roll 1-5` 填固定的 `randomSeed` 保不住四比一：固定的 seed 讓每次重跑抽到同一個序列，兩次執行的比例比較接近，而比例仍然由抽樣決定，加上所有 thread 共用同一個產生器，duration 結束時跑到第幾輪每次不同（依 `RandomVariableConfig` 的原始碼推出，這次沒有實跑）。

## CLI mode 執行與 JTL

```bash
docker run --rm --network loadlab -v "$PWD/jmeter:/mnt/jmeter" lab-jmeter \
  jmeter -n -t shop2.jmx -l out/run2.jtl -e -o out/report2 -f \
  -Jthreads=10 -Jduration=30
echo "exit=$?"
```

參數的意思：`-n` 是 CLI mode（不開 GUI）；`-t` 是 test plan；`-l` 是 JTL 的路徑，每一個 sample 寫一行；`-e -o out/report2` 在執行結束後從 JTL 產生 HTML dashboard 到 `out/report2`；`-f` 先刪掉上一次留下的 JTL 與報告資料夾，沒有它時 `-o` 指向的資料夾不是空的就失敗（〈dashboard、statistics.json 與從 JTL 重新產生報告〉有這個錯誤的訊息）；不給 `-e -o` 時只寫 JTL、不產生 dashboard 與 `statistics.json`，後面的門檻判定就要改讀 JTL；`-Jthreads=10 -Jduration=30` 設定 JMeter 屬性，test plan 裡的 `${__P(threads,10)}` 讀到的就是它。`shop2.jmx` 是改用 If Controller 的那一版。10 個 thread、30 秒、ramp-up 5 秒是示範用的值，沒有比較其他值。

執行中每 30 秒（以時鐘對齊）印一行 summary，結束時印合計：

```text
summary =    135 in 00:00:32 =    4.3/s Avg:    39 Min:     1 Max:   644 Err:     2 (1.48%)
```

`135 in 00:00:32` 是 32 秒內 135 筆 sample，`4.3/s` 是平均每秒的 sample 數，`Avg`、`Min`、`Max` 是毫秒，`Err` 是失敗的筆數與比例。這次有 2 個 sample 失敗（`/flaky` 回 500），`echo "exit=$?"` 印出的是 `exit=0`。JMeter 的 CLI mode 正常跑完（thread group 照排程跑到 `duration`、沒有因為 test plan 讀不到或 `-o` 寫不進去這類錯誤而中止）時 exit code 是 0，失敗的 sample 不改變它（這次實測）；這份 test plan 沒有 assertion，assertion 判成失敗時同樣不改變 exit code，依據是官方文件的推論，見 [JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/) 的〈JMeter 在 regression gate 裡負責的環節與 exit code 涵蓋的範圍〉。Locust 的約定相反，同一個受測服務、同樣有失敗的請求時回 1（[Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈內建的 exit code：有失敗、沒有失敗但變慢〉）。所以 CI 只看 JMeter 的 exit code 的話，有失敗 sample 的那次執行照樣讓 job 通過；門檻要在 JMeter 之外讀結果判定，寫法在〈JMeter 之外的門檻判定〉。

JTL 的第一行是欄位名，這次的設定寫出的是：

```text
timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect
1793156978830,624,POST /login,200,OK,shoppers 1-4,text,true,,179,203,5,5,http://target:8080/login,624,0,371
```

`timeStamp` 是毫秒的 epoch，`elapsed` 是這個 sample 從送出到收完回應的毫秒數，`success` 是 `true` 或 `false`，`Latency` 是從送出請求到收到第一個回應位元組的毫秒數，`Connect` 是建立連線花的毫秒數（含 TLS 握手，官方〈Glossary〉；`Latency` 沒有扣掉它），`allThreads` 是當下所有 thread group 的活躍 thread 數。`threadName` 的格式是 thread group 的名稱、一個空格、第幾個 thread group、`-`、第幾個 thread（5.6.3 的原始碼 `AbstractThreadGroup`），所以這一筆是第 1 個 thread group `shoppers` 裡第 4 個 thread 的第一個請求，624 毫秒裡有 371 毫秒花在建立連線。`awk -F, 'NR>1 && $17>0' jmeter/out/run2.jtl | wc -l`（`$17` 是 `Connect` 欄）數得出 `Connect` 大於 0 的剛好 10 筆，全是 `POST /login`，也就是每個 thread 的第一個請求。之後的請求重用同一條連線，`Connect` 是 0，這是 Same user on each iteration 勾選、sampler 開了 keep-alive 的結果。哪些欄位會寫出來由 `jmeter.properties` 的 `jmeter.save.saveservice.*` 決定，這次用預設值；兩次執行的這組屬性不同時，JTL 的欄位也不同，後處理要先核對欄位名。

## dashboard、statistics.json 與從 JTL 重新產生報告

`-e -o` 產生的 `out/report2/` 裡有 `index.html`（瀏覽器打開就是 dashboard）與 `statistics.json`。`statistics.json` 每個 label 一個物件，加上 `Total`；這次的值（只列幾個欄位）：

```text
label            sampleCount  errorPct  pct2ResTime
GET /items/[id]          106      0.00           76
GET /flaky                19     10.53          203
POST /login               10      0.00          644
Total                    135      1.48          217
```

`pct1ResTime`、`pct2ResTime`、`pct3ResTime` 是三個百分位數的延遲，對應 `jmeter.properties` 裡的 `aggregate_rpt_pct1`、`aggregate_rpt_pct2`、`aggregate_rpt_pct3`，預設是第 90、95、99 百分位（這次的 image 裡這三行是註解掉的預設值）。有人在 `user.properties` 改了這三個值，同一個欄位名就代表另一個百分位數，所以門檻判定的程式讀 `pct2ResTime` 時，執行條件要一起記下這組屬性。`POST /login` 的 p95 是 644 毫秒，遠高於其他 label：每個 thread 的第一個請求要建立連線，登入又只有 10 筆，`Total` 被它拉高到 217 毫秒。這些延遲是這台筆電、這一次的值，受測服務與 JMeter 共用同一台機器的 CPU，同一份 test plan 重跑會變動，不能拿來當門檻。

報告可以不重跑測試、從保存的 JTL 重新產生：

```bash
docker run --rm -v "$PWD/jmeter:/mnt/jmeter" lab-jmeter \
  jmeter -g out/run2.jtl -o out/report2b
# 再跑一次同一條：
# An error occurred: Cannot write to '/mnt/jmeter/out/report2b' as folder is not empty
```

第一次產生的 `statistics.json` 與執行時產生的那一份 sample 數相同。同一條指令再跑一次時，`-o` 指向的資料夾已經有內容，JMeter 回 exit 1；`-g` 這條指令要換一個空的資料夾，或先刪掉舊的。從 JTL 重新產生報告的用途是換一組設定重算：百分位數的設定改了、或要排除 ramp-up 的那一段時，拿同一份 JTL 加上不同的屬性產生報告，排除區間的屬性與寫法見 [JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/) 的〈ramp-up 期間的樣本與統計區間〉。

## JMeter 之外的門檻判定

下面這支程式存成 `jmeter/gate.py`：

```python
# 讀 JMeter dashboard 產生的 statistics.json，依門檻決定 exit code。
#   用法：python gate.py <statistics.json> [label ...]
#   不給 label 時判 Total；門檻從環境變數讀
import json
import os
import sys

MAX_ERROR_PCT = float(os.environ.get("GATE_MAX_ERROR_PCT", "5"))   # 百分比
MAX_P95_MS = float(os.environ.get("GATE_MAX_P95_MS", "300"))       # pct2ResTime，預設是第 95 百分位

path, labels = sys.argv[1], sys.argv[2:] or ["Total"]
try:
    with open(path) as f:
        stats = json.load(f)
except (OSError, ValueError) as e:      # 報告沒有產生、JTL 是空的、檔案寫壞
    print(f"GATE ERROR: cannot read {path}: {e}")
    sys.exit(4)

failed = False
missing = False
for label in labels:
    s = stats.get(label)
    # 沒有這個 label、沒有樣本，或缺判定要用的欄位，都算缺資料
    if s is None or s.get("sampleCount", 0) == 0 or "errorPct" not in s or "pct2ResTime" not in s:
        print(f"GATE ERROR: no samples for {label}")
        missing = True
        continue
    problems = []
    if s["errorPct"] > MAX_ERROR_PCT:
        problems.append(f"error {s['errorPct']:.2f}% > {MAX_ERROR_PCT}%")
    if s["pct2ResTime"] > MAX_P95_MS:
        problems.append(f"p95 {s['pct2ResTime']:.0f} ms > {MAX_P95_MS} ms")
    if problems:
        print(f"GATE FAIL: {label} " + "; ".join(problems))
        failed = True
    else:
        print(f"GATE PASS: {label} error {s['errorPct']:.2f}%, p95 {s['pct2ResTime']:.0f} ms")
# 門檻不成立排在缺資料之前：有資料的流程已經量到退化，這件事不因別的流程缺資料而消失
sys.exit(1 if failed else 4 if missing else 0)
```

下面用一個 shell 函式包住 `docker run`：`docker run` 依 `-v "$PWD/jmeter:/w" -w /w` 把 `jmeter/` 掛進 container 的 `/w` 並設成工作目錄，`gate.py` 與 `out/` 都從那裡讀。寫成函式，而不是把 `docker run …` 那一串存進一個變數再用 `$變數 gate.py …` 呼叫，是因為 zsh 不會把變數的內容切成幾個詞，那種寫法在 zsh 底下會把整串當成一個指令名，回報找不到指令。

```bash
gate() { docker run --rm -v "$PWD/jmeter:/w" -w /w python:3.12-slim python gate.py "$@"; }
# 不給 label，判 Total
gate out/report2/statistics.json
# GATE PASS: Total error 1.48%, p95 217 ms               → exit 0
gate out/report2/statistics.json "GET /flaky" "GET /items/[id]"
# GATE FAIL: GET /flaky error 10.53% > 5.0%
# GATE PASS: GET /items/[id] error 0.00%, p95 76 ms      → exit 1
gate out/report2/statistics.json "GET /checkout" "GET /flaky"
# GATE ERROR: no samples for GET /checkout
# GATE FAIL: GET /flaky error 10.53% > 5.0%              → exit 1
gate out/report2/statistics.json "GET /checkout" "GET /items/[id]"
# GATE ERROR: no samples for GET /checkout
# GATE PASS: GET /items/[id] error 0.00%, p95 76 ms      → exit 4
gate out/missing/statistics.json
# GATE ERROR: cannot read out/missing/statistics.json: ... → exit 4
```

`GET /checkout` 是這份 test plan 裡沒有的 label，用來看缺資料時的結果。上面五條 `gate` 指令的結果顯示兩件事。第一件是判定範圍的影響：只判 `Total` 時，`/flaky` 10.53% 的錯誤率被大量成功的商品頁攤成 1.48%，門檻通過；逐個 label 判定時，`/flaky` 那一條失敗。逐個列 label 時只列每一輪都會送的請求：`POST /login` 每個 thread 只送一次，延遲包含建立連線的時間（〈dashboard、statistics.json 與從 JTL 重新產生報告〉那一節），審查時把它列進 label 實跑過，p95 575 毫秒，300 的固定門檻每一次都判它失敗。

第二件是缺資料的處理：exit code 4 是這支程式自己的約定，代表報告沒有產生或缺少某個 label 的資料，跟「門檻不成立」的 1 分開，CI 才分得出這次是退化還是測試本身沒跑成；同一次判定裡兩種都有時回 1，因為有資料的那個流程已經量到退化，這件事不因別的流程缺資料而消失。這個優先序與 [JMeter 在效能 regression gate 的用法：JMeter 之外的門檻判定、逐筆 assertion 與統計門檻的分工、thread group 的負載模型、施壓端設定與基準的可比性、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/jmeter/jmeter-performance-regression-gate/) 〈門檻判定的落點：自寫的後處理與外層工具〉那一支比較基準的程式相同；那一篇的程式也叫 `gate.py`，介面不同：那一支比較這一次與基準兩份 `statistics.json`，這一支只讀一份、拿固定門檻比；關鍵流程各自設門檻的理由也寫在那一篇。

exit code 4 涵蓋不到最常見的一種沒跑成：受測服務整個連不上時，每一筆 sample 都失敗，報告照樣產生，錯誤率是 100%，這支程式回的是 1，跟退化分不開；要把這種情形也歸到 4，另外判錯誤率是不是 100%，或在測試之前先打一次健康檢查（審查時另外實跑過：`-Jhost` 指向不存在的 container，summary 是 `Err: 7 (100.00%)`，`-e -o` 照樣產生 `statistics.json`，這支程式印 `GATE FAIL: Total error 100.00% > 5.0%`、回 1）。受測環境只有一部分故障時（一台 replica 掛掉、連線被重設），健康檢查會通過，錯誤率落在 0 與 100% 之間，這兩種做法都把它判成退化；分辨的依據是失敗的類別：JTL 的 `responseCode` 以 `Non HTTP response code` 開頭的是連線層的錯誤，指向受測環境，HTTP 的錯誤狀態碼才可能是這一版程式的退化，錯誤率本身分不出來（把錯誤類別寫進判定這次沒有實跑）。門檻的環境變數不是數字時，`float()` 拋出例外，Python 同樣以 exit 1 結束；逐個 label 判定時，樣本少的 label（這次 `GET /flaky` 只有 19 筆）的 p95 與錯誤率每次重跑差很多，實際用時要另外設最少樣本數，不足時歸到 4：條件加在程式裡判缺資料的那一行，`sampleCount` 小於最少樣本數時跟 0 筆一樣記成缺資料（這兩點這次都沒有實跑）。最少樣本數要多少這篇沒有量，取法是讓基準版本在同一個環境重跑幾次，看那個 label 的 p95 波動降到可以接受時的樣本數（[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)〈Baseline 設定〉）。

`Total` 是英文語系下 dashboard 寫出的鍵名，JMeter 用別的語系產生報告時要先核對這個鍵。5 與 300 是佔位的門檻，實際的值從基準版本在同一個環境量到的結果取（[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)〈Baseline 設定〉）。這段程式也可以換成 shell 加 `jq`，或用 Taurus、jmeter-maven-plugin 這類工具內建的判定，這次都沒有實跑，各自的取捨見同一篇的〈門檻判定的落點：自寫的後處理與外層工具〉。

## remote testing：一台 client 與兩台 server

一台施壓機送不出需要的負載時，JMeter 的 remote testing 讓一台 client 把 test plan 送到幾台 server 上執行、收回結果（官方用語是 client 與 server，舊資料寫成 master 與 slave，也有資料把 server 稱為節點）。這次在同一個 Docker network 裡開兩台 server，每一台都掛載同一個 `jmeter/`：test plan 送到 server 上執行時，`items.csv` 是在 server 的工作目錄裡找，client 不會把資料檔送過去。

```bash
for i in 1 2; do
  docker run -d --name js$i --network loadlab -v "$PWD/jmeter:/mnt/jmeter" lab-jmeter \
    jmeter-server -Dserver.rmi.ssl.disable=true \
    -Djava.rmi.server.hostname=js$i -Dserver.rmi.localport=50000
done
# server 的 JVM 要幾秒才起來，剛啟動就看 log 可能還是空的；跑過測試之後 log 最後幾行會變成測試的開始與結束
docker logs js1 | grep -E 'local port|Created remote object'
# Using local port: 50000
# Created remote object: UnicastServerRef2 [liveRef: [endpoint:[js1:50000](local), ...
```

client 指定這兩台 server 執行：

```bash
docker run --rm --name jclient --network loadlab -v "$PWD/jmeter:/mnt/jmeter" lab-jmeter \
  jmeter -n -t shop2.jmx -R js1,js2 \
  -Jserver.rmi.ssl.disable=true -Djava.rmi.server.hostname=jclient -Jclient.rmi.localport=60000 \
  -Gthreads=5 -Gduration=20 -l out/remote.jtl -f
# Configuring remote engine: js1
# Configuring remote engine: js2
# Starting distributed test with remote engines: [js2, js1] ...
# summary =     86 in 00:00:22 =    3.8/s Avg:    87 Min:     2 Max:  1535 Err:     2 (2.33%)
```

各參數的作用：

- **`server.rmi.ssl.disable=true`**：client 與 server 之間用 Java RMI 溝通，JMeter 預設要求 RMI 走 SSL，要先用 `create-rmi-keystore.sh` 產生 keystore 並放到每一台（官方文件〈Remote Testing〉）。這次在一台機器的 Docker network 裡實驗，關掉 SSL；client 與 server 跨過不受控制的網路時，關掉 SSL 等於讓網路上的任何人都能對 server 下指令，要照官方文件建 keystore，這次沒有實跑那一條。client 與 server 兩邊都要設成同一個值。
- **`java.rmi.server.hostname`**：RMI 會把這台機器的位址告訴對方，對方再連回來；不設時 Java 取 container 自己解析到的位址，常常是對方連不到的位址，例如 loopback 位址（官方文件〈Remote Testing〉寫了 loopback 的情形；在 Docker 或 NAT 後面取到對方連不到的位址，是從 RMI 回報位址的機制推出，這次沒有實跑不設的情形）。每一台設成對方連得到它的名稱，這次用 container 名稱。
- **`server.rmi.localport` 與 `client.rmi.localport`**：把 RMI 用的 port 固定下來（server 的 50000、client 收結果的 60000）。官方文件〈Remote Testing〉的〈Tips〉寫明 client 連 server 時另外用 RMI registry 的 port（預設 1099，server 用 `server_port` 屬性改），server 把結果回傳給 client 時，client 從 `client.rmi.localport` 起最多開三個 port；所以跨主機時，server 那邊開 1099 與 50000，client 那邊開 60000 起的三個 port。這次同一個 network 裡沒有防火牆，不設這兩個屬性也連得上，沒有比較不設的情形。
- **`-R js1,js2`**：要執行的 server 名單。
- **`-G` 與 `-J`**：`-G` 設定的屬性送到每一台 server，`-J` 只設在 client 本身。
- **`-D` 與 `-J`**：`-D` 設定 Java 的系統屬性，`java.rmi.server.hostname` 是 Java 的 RMI 自己讀的系統屬性，所以用 `-D`；`server.rmi.ssl.disable` 是 JMeter 的屬性，這次 server 那邊用 `-D` 設、client 這邊用 `-J` 設，兩邊的 log 都印出 `Disabling SSL for RMI as server.rmi.ssl.disable is set to 'true'`：JMeter 的屬性以 Java 的系統屬性為預設值（5.6.3 的原始碼 `JMeterUtils.loadJMeterProperties`），所以 `-D` 設的值 JMeter 也讀得到；反過來，`-J` 不會設 Java 的系統屬性，`java.rmi.server.hostname` 只能用 `-D`。

`-G` 與 `-J` 的差別用登入的筆數就看得出來。每個 thread 只登入一次，所以登入筆數等於 thread 的總數：

```bash
awk -F, 'NR>1 && $3=="POST /login"' jmeter/out/remote.jtl | wc -l
# -Gthreads=5 的那一次印出 10

# 同一條 client 指令，把 -Gthreads=5 換成 -Jthreads=5、結果寫到另一個檔
# （duration 縮短成 15 秒只是省時間；每個 thread 只登入一次，登入筆數只看 thread 數）
docker run --rm --name jclient --network loadlab -v "$PWD/jmeter:/mnt/jmeter" lab-jmeter \
  jmeter -n -t shop2.jmx -R js1,js2 \
  -Jserver.rmi.ssl.disable=true -Djava.rmi.server.hostname=jclient -Jclient.rmi.localport=60000 \
  -Jthreads=5 -Gduration=15 -l out/remote-j.jtl -f
awk -F, 'NR>1 && $3=="POST /login"' jmeter/out/remote-j.jtl | wc -l
# 印出 20
```

`-Gthreads=5` 時每台 server 跑 5 個 thread，合計 10 個：每台 server 執行的是完整的 test plan，thread group 裡設定的 thread 數是每一台各自的量。Locust 的分散執行是反過來的：master 把 `-u` 個使用者分給各個 worker，合計不隨 worker 數增加（[Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈master 與兩個 worker〉），從其中一個工具換到另一個時，同樣的數字代表的施壓量不同。改成 `-Jthreads=5` 時，server 讀不到這個屬性，各自用 test plan 裡的預設值 10，合計 20 個；指令照樣跑完、exit code 是 0，不會有任何跟屬性有關的警告（輸出開頭那幾行 `WARN StatusConsoleListener The use of package scanning ...` 是 JMeter 用的 log4j 自己的訊息，`-G` 那一次也有），所以 remote testing 時每個要傳給 test plan 的屬性都用 `-G`。

JTL 由 client 寫出，分得出每一筆來自哪一台 server：remote testing 時 `threadName` 帶上 server 名稱的前綴（`js1-shoppers 1-1`、`js2-shoppers 1-1`）。`allThreads` 欄這次最大是 5，它是每一台 server 自己的活躍 thread 數，不是全部 server 的合計。要在 JTL 多一欄 Hostname 分節點計算時，在寫 JTL 的 client 上設 `jmeter.save.saveservice.hostname=true`（預設 false，這次沒有實跑）。summary 那一行的筆數與延遲是這一次的值，受測服務與兩台 server 共用同一台筆電的 CPU，量到的延遲包含施壓端與受測服務爭用 CPU 的時間（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)），重跑會變。施壓量大到要分散時，client 收結果本身會成為新的瓶頸、結果改用 Backend Listener 送到外部的時序資料庫、資料檔怎麼分到每一台 server，這些判斷寫在 [JMeter 在容量探測的用法：thread group 固定的負載變數、逐級加壓、knee 的判讀、施壓端與分散施壓的檢查、多 protocol 的涵蓋範圍與排查順序](/backend/09-performance-capacity/vendors/jmeter/jmeter-capacity-probing/) 的〈分散施壓：remote mode 的結果回傳、Backend Listener 與資料檔〉。

server 中途結束時，client 的行為依結束的時間點而不同，審查時殺掉 `js2` 各實跑過一次：

- **測試已經開始之後**（被 OOM 殺掉、主機重開）：client 不會自己結束，停在 `Waiting for possible Shutdown/StopTestNow/HeapDump/ThreadDump message on port 4445` 那一行；那一次 `-Gduration=40`，354 秒之後仍在等，另一台 server 的 log 已經印 `Finished the test`，JTL 只寫了一部分，報告沒有產生。CI 要等到 job 的逾時才結束。
- **啟動的過程中**：client 印 `The following remote engines have not started:[js2]`，exit code 是 0，沒有寫出 JTL。
- **還在設定 server 時**：client 印 `Following remote engines could not be configured`，exit code 是 1。

所以 CI 跑 remote testing 時，job 要設一個比 duration 長一點的逾時，並從 client 的輸出找 `have not started` 與 `could not be configured`；JMeter 的 exit code 分不出這幾種情形，前兩種都不會產生報告，`gate.py` 讀不到 `statistics.json` 時回 4。

## 清理 container 與 Docker network

```bash
docker rm -f js1 js2 target
docker network rm loadlab
```

兩台 server 沒有加 `--rm`，要自己刪；client 帶著 `--rm`，跑完就刪了。還有執行中的 container 連著 network 時，`docker network rm` 失敗，訊息是 `network loadlab has active endpoints`，後面列出 `target`、`js1`、`js2` 這幾個還在跑的 container，所以先刪 container 再刪 network。`jmeter/out/` 底下的 JTL 與報告，以及 `jmeter/` 底下的 `jmeter.log`、`jmeter-server.log`（兩台 server 掛載同一個目錄，寫的是同一份）都留在本機的目錄。
