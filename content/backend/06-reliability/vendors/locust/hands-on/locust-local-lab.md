---
title: "Locust 在本機跑負載測試的實測紀錄：受測服務、locustfile、headless 執行與 CSV、內建的 exit code、quitting 事件裡的門檻判定、--reset-stats 與 on_start、master 與 worker 的分散執行"
date: 2026-10-28
description: "要在本機用 Docker 照一次實測跑 Locust：寫 locustfile、headless 執行、讀終端機的統計表與 CSV、在 quitting 事件裡判定延遲門檻、開 master 與多個 worker 分散執行時讀；也用在受測服務變慢而 exit code 還是 0、加了 --reset-stats 之後登入請求還在統計裡、master 回報 worker failed to send heartbeat 的時候"
weight: 1
tags: ["backend", "reliability", "vendor", "locust", "load-test", "hands-on"]
slug: "locust-local-lab"
---

實測日期是 2026-10-28，環境是一台 macOS 筆電上的 Docker（server 29.8.2，Docker 可用 8 顆 CPU 與 8 GB 記憶體），Locust 2.47.0 跑在 `python:3.12-slim`（Python 3.12.15）的 container 裡，受測服務是同一個 Docker network 裡另一個 container 跑的 Python 標準函式庫程式；這次的操作是從寫 locustfile 開始，在本機跑 headless 的負載測試，接著驗證 exit code 在幾種情形下的值，最後開一個 master 與兩個 worker 分散執行。

這篇記錄在本機用 Docker 跑 Locust 的完整操作：一個有正常、回錯誤兩種 endpoint 的受測服務；裝了 Locust 的 image；locustfile 裡的 `wait_time`、`on_start` 登入、task 的權重、把不同網址併成同一列統計的 `name` 與從 CSV 讀的測試資料；headless 執行的參數、終端機的統計表怎麼讀、`--csv` 寫出的幾個檔案；內建的 exit code 在有失敗、沒有失敗但變慢兩種情形的值；在 `quitting` 事件裡判定延遲與錯誤率的門檻，以及它怎麼蓋掉內建的判定；`--reset-stats` 之後 `on_start` 的請求為什麼還在統計裡；一個 master 加兩個 worker 的啟動方式、門檻判定為什麼只在 master 做，以及這次遇到的 worker heartbeat 失敗；最後是清理。受測服務與負載模型（每個使用者登入一次、商品頁與會失敗的 endpoint 四比一、每一輪停 1 到 3 秒）跟 [JMeter 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/jmeter/hands-on/jmeter-local-lab/) 相同，兩個工具的輸出可以並排比較。這些操作背後的判斷，也就是 CI 用這次的量測擋下效能退化（效能 regression gate，下文簡稱 gate）時門檻怎麼設、預熱的請求怎麼處理、gate 失敗時依什麼順序排除誤判，寫在 [Locust 在效能 regression gate 的用法：exit code 與門檻判定、預熱與 on_start 的請求、closed model 下的比較、custom client 回報的請求範圍、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/)；拿 Locust 逐級加壓找飽和點的做法寫在 [Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/)。Web UI 的操作、Kubernetes 上的部署與 Locust Cloud 不在這次的實測裡。

## 受測服務：標準函式庫寫的 HTTP 程式

受測服務的職責是讓延遲與錯誤可以控制：負載工具量到的值變了，讀的人要知道那是受測服務被改了，還是工具或環境的雜訊。這次用一支只依賴 Python 標準函式庫的程式，放在 `target/app.py`：

```python
# 受測服務：只用標準函式庫，讓負載工具量得到可控的延遲與錯誤。
#   GET /items/<id>   正常回應；DELAY_MS 環境變數加上固定延遲
#   GET /flaky        每 ERROR_EVERY 個請求回一次 500
#   POST /login       回一個 token
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY_MS = int(os.environ.get("DELAY_MS", "0"))
ERROR_EVERY = int(os.environ.get("ERROR_EVERY", "10"))
_count = 0
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"   # 讓用戶端重用連線（keep-alive）

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        global _count
        if self.path.startswith("/items/"):
            time.sleep(DELAY_MS / 1000)
            self._send(200, {"id": self.path.rsplit("/", 1)[-1]})
        elif self.path == "/flaky":
            with _lock:
                _count += 1
                n = _count
            self._send(500 if n % ERROR_EVERY == 0 else 200, {"n": n})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if self.path == "/login":
            self._send(200, {"token": "t-" + str(time.time_ns())})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass                          # 不印每個請求的 log，避免 I/O 影響延遲


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
```

這篇的程式碼區塊裡，`#` 開頭的那幾行是說明或預期的輸出；macOS 內建的 zsh 在互動模式下預設不把 `#` 當成註解，貼上之前先在同一個終端機分頁執行一次 `setopt interactivecomments`（只對這個 shell 有效），否則那幾行會印出 `command not found: #`；用 bash 時不需要這一步，bash 沒有 `setopt` 這個指令。`-v` 掛載本機的目錄，在 macOS 的 Docker Desktop 上這個目錄要在 Settings 的 File sharing 列出的路徑裡（預設是 `/Users`、`/Volumes`、`/private`、`/tmp`、`/var/folders`），不在的話 `docker run` 回 `Mounts denied`（依 Docker Desktop 官方文件的設定說明）；OrbStack 不限定路徑。在 Linux 主機上，container 以 root 寫出的 `out/` 歸 root 所有，刪除時要 sudo（這兩點這次都沒有實跑）。

```bash
docker network create loadlab
docker run -d --rm --name target --network loadlab \
  -v "$PWD/target:/app:ro" python:3.12-slim python /app/app.py
# 從同一個 network 裡確認服務在回應
docker run --rm --network loadlab curlimages/curl:8.10.1 -s http://target:8080/items/42
```

最後一條指令印出 `{"id": "42"}` 就是服務起來了。這篇的指令都在 `target/`、`locust/` 兩個目錄的上一層執行。`loadlab` 是這次建的 Docker network 名稱，`target` 是受測服務的 container 名稱，也是 Locust 在同一個 network 裡連它用的主機名；`$PWD/target` 是放 `app.py` 的目錄，換成讀者自己的路徑。自建的 network 讓同一個 network 裡的 container 用名稱互相連線，所以後面的指令寫得出 `http://target:8080` 與 `--master-host lmaster`；改用 Docker 預設的 bridge network 時，container 之間不能用名稱連，要改填 container 的 IP，這次沒有實跑。受測服務與 Locust 各自一個 container，是讓兩邊不共用同一個程序的 CPU；兩者仍然在同一台機器上，Docker 的 8 顆 CPU 是共用的，這台機器量到的延遲包含兩邊爭用 CPU 的時間（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)）。

受測服務可以換成讀者自己的服務：下面每一步的 `--host` 換成那個服務的位址，locustfile 裡的三個路徑（`/login`、`/items/<id>`、`/flaky`）、登入送出的 body 與取 token 的那一行（`resp.json()["token"]`）也要換成那個服務的 endpoint 與回應格式，只換 `--host` 的話，請求會回 404，或在取 token 時拋出例外。換掉之後少的是「延遲與錯誤可控」這一點，後面驗證 exit code 的幾步要自己找出會回錯誤、會變慢的 endpoint。`ERROR_EVERY` 用預設值 10，沒有比較其他值。[JMeter 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/jmeter/hands-on/jmeter-local-lab/) 沿用這支程式，改動它時，那一篇的輸出也要重新核對。

## 裝了 Locust 的 image

下面的內容存成 `locust/Dockerfile`：

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir locust==2.47.0
WORKDIR /mnt/locust
```

```bash
docker build -t lab-locust locust/
docker run --rm lab-locust locust --version
# locust 2.47.0 from /usr/local/lib/python3.12/site-packages/locust (Python 3.12.15)
```

Dockerfile 把版本寫死成這次實測的 2.47.0：下文引用的預設值與原始碼常數都是這個版本的，換版本時先改這一行，再核對那幾處；拿掉 `==2.47.0` 時 pip 裝到當時最新的版本，兩次執行的 Locust 可能不同。基底的 `python:3.12-slim` 這個 tag 會跟著 Python 的 patch 版更新，這次是 3.12.15；要讓兩次執行的基底也相同，改用帶完整版本的 tag 或 `@sha256:<建 image 當天的 digest>`，這次沒有實跑。`locust/` 是放 Dockerfile 與 locustfile 的目錄，`WORKDIR /mnt/locust` 是之後把這個目錄掛進 container 的位置，locustfile 裡用相對路徑讀的 `items.csv` 從這裡找。

這一步有兩種替代做法，這次都沒有實跑。一種是在本機的 Python 虛擬環境裡 `pip install locust`，換到的是不必經過 Docker、改 locustfile 之後直接重跑，付出的是本機的 Python 版本與套件會影響結果，交給 CI 時要再做一次環境；另一種是官方的 `locustio/locust` image（官方文件〈Running in Docker〉），換到的是不必自己寫 Dockerfile，付出的是要額外的 Python 套件時仍然要以它為基礎另建一個 image。

## locustfile：wait_time、on_start、task 的權重與測試資料

```python
import csv
import os
import random

from locust import HttpUser, between, events, tag, task
from locust.runners import WorkerRunner

# 測試資料：每一列一個商品編號，所有使用者共用同一份清單
with open("items.csv", newline="") as f:
    ITEM_IDS = [row["item_id"] for row in csv.DictReader(f)]


class Shopper(HttpUser):
    # 每個 task 跑完之後停 1 到 3 秒，模擬使用者的停頓
    wait_time = between(1, 3)

    def on_start(self):
        # 每個使用者啟動時登入一次，token 存在這個使用者自己的 instance 上
        resp = self.client.post("/login", json={"user": "load-test"})
        self.token = resp.json()["token"]

    @task(4)
    def view_item(self):
        item_id = random.choice(ITEM_IDS)
        # name 把不同 id 的請求併成同一列統計，否則每個 id 各占一列
        self.client.get(f"/items/{item_id}", name="/items/[id]",
                        headers={"Authorization": f"Bearer {self.token}"})

    @tag("flaky")
    @task(1)
    def flaky(self):
        self.client.get("/flaky")
```

上面的程式存成 `locust/locustfile.py`，同一個目錄放 `items.csv`：第一行是表頭 `item_id`，下面五行是 `101` 到 `105`。這份檔案最後還要加一段 `quitting` 事件的處理函式（listener），在〈quitting 事件裡的門檻判定〉那一節說明；那一節之前的幾步跑的是 `locust/locustfile_basic.py`，它是上面這段程式去掉只有 listener 用到的 `import os`、`from locust.runners import WorkerRunner` 兩行，並把 `events` 從 `from locust import` 那一行拿掉的版本。分成兩個檔，是因為〈內建的 exit code〉要看沒有 listener 時 Locust 自己算出的 exit code；用加了 listener 的 `locustfile.py` 跑那幾步，exit code 由 listener 決定，量不到內建的判定。

Locust 的一個使用者是 `Shopper` 類別的一個 instance，task 是帶 `@task` 的方法；每個使用者反覆挑一個 task 執行、停頓、再挑下一個。各段的作用：

- **`wait_time = between(1, 3)`**：每個使用者跑完一個 task 之後停 1 到 3 秒的隨機時間，再挑下一個 task。使用者等到回應、停完才送下一個請求，所以這份 locustfile 下的 Locust 是 closed model：受測服務變慢時每秒請求數跟著下降（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)）。不寫 `wait_time` 時，預設是 `constant(0)`（2.47.0 的原始碼 `locust/user/users.py`），不停頓、task 一個接一個跑，每個使用者送出請求的速率只受受測服務回應的快慢限制，量到的是受測服務的吞吐上限，跟有停頓的使用者行為不同。另外兩種寫法這次沒有實跑：`constant_pacing(n)` 讓每個使用者每 n 秒開始一個 task，扣掉 task 花掉的時間才停頓；`constant_throughput(r)` 是同一件事的倒數寫法，每個使用者每秒至多 r 個 task。兩者都是 pacing，受測服務變慢、一個 task 花掉的時間超過間隔時，速率就低於設定值，仍然是 closed model（[Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 的 pacing 那一段）。
- **`on_start`**：每個使用者啟動時跑一次，這裡用來登入、拿 token。登入寫在 task 裡的話，每次挑到那個 task 都登入一次，登入的 endpoint 變成主要的負載來源。`on_start` 裡的請求照樣算進統計，下面的統計表裡 `POST /login` 有自己的一列。`HttpUser` 預設每個使用者一個連線池，連線在同一個使用者的各個 task 之間重用（官方文件〈Writing a locustfile〉），所以每個使用者只有第一個請求、也就是 `on_start` 的登入要建立連線，`POST /login` 的延遲包含建立連線的時間（審查時另外實跑過：在受測服務裡數連線，3 個使用者跑 15 秒、送出 22 個請求，連線正好 3 條；前提是受測服務用 HTTP/1.1，`app.py` 設了 `protocol_version = "HTTP/1.1"`。建立連線的時間沒有從延遲裡分開量）；受測服務換成 HTTPS 時，這個設定決定握手的次數（[TLS Handshake（TLS 握手）的成本與連線重用](/backend/knowledge-cards/tls-handshake-cost/)）。
- **`@task(4)` 與 `@task(1)`**：權重是相對值，使用者挑下一個 task 時，`view_item` 被挑中的機率是 4/5，`flaky` 是 1/5。
- **`name="/items/[id]"`**：Locust 依請求的名稱分列統計，名稱預設是網址的路徑；不給 `name` 時 `/items/101` 到 `/items/105` 各占一列，每一列的樣本少、百分位數不穩。`[id]` 只是給人讀的名稱，Locust 不解析它。
- **`@tag("flaky")`**：讓命令列可以用 `--exclude-tags flaky` 排除這個 task，後面驗證「沒有失敗但變慢」的情形時用到。
- **測試資料在模組層讀一次**：所有使用者共用 `ITEM_IDS`，每個使用者用 `random.choice` 挑。這次的五個值只用來示範；資料的種類太少時，受測服務的快取命中率比 production 高，量到的延遲偏低，資料怎麼取得接近 production 的分佈見 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)。

## headless 執行、終端機的統計表與 CSV

```bash
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile_basic.py --headless -u 20 -r 5 -t 30s \
  --host http://target:8080 --csv out/run1 --html out/run1.html --only-summary
echo "exit=$?"
# exit=1（原因在〈內建的 exit code〉）
```

參數的意思：`--headless` 不開 Web UI、直接開始；`-u 20` 是同時在線的使用者數；Locust 照 `-r 5` 每秒啟動 5 個使用者，第一批在第 0 秒啟動，這次 20 個在第 3.1 秒全部啟動；`-t 30s` 是從開始到結束的時間，包含啟動的那 3 秒；`--host` 是受測服務的位址，換成讀者自己的服務；Locust 依 `--csv out/run1` 在工作目錄 `/mnt/locust` 底下的 `out/`（也就是本機的 `locust/out/`，Locust 會自己建這個資料夾）寫出以 `run1` 開頭的幾個 CSV；`--html` 寫一份 HTML 報告；`--only-summary` 只在結束時印一次統計表，不在執行中每幾秒印一次。這次的使用者數、啟動速率與時間是示範用的值，沒有比較其他值；`-u` 與 `-t` 決定這次量的是哪一級負載、樣本有多少，gate 怎麼取見 [Locust 在效能 regression gate 的用法](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/) 的〈PR 與 nightly 兩種執行的分工〉，容量探測怎麼逐級加壓見 [Locust 在容量探測的用法](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/) 的〈closed model 下的逐級加壓：LoadTestShape 的 tick〉。

結束時終端機印出兩張統計表（這次的輸出，欄寬縮短），有失敗的請求時接著再印一張依錯誤訊息計數的 Error report：

```text
Type     Name           # reqs      # fails |    Avg     Min     Max    Med |   req/s  failures/s
GET      /flaky             55    6(10.91%) |      9       1      52      4 |    1.92        0.21
GET      /items/[id]       225     0(0.00%) |      8       1     107      5 |    7.87        0.00
POST     /login             20     0(0.00%) |     73      15     236     34 |    0.70        0.00
         Aggregated        300     6(2.00%) |     13       1     236      5 |   10.49        0.21

Response time percentiles (approximated)
Type     Name               50%    66%    75%    80%    90%    95%    98%    99%  99.9% 99.99%   100% # reqs
GET      /flaky               4      6      7      9     34     47     48     53     53     53     53     55
GET      /items/[id]          5      6      7      8     12     46     52     57    110    110    110    225
POST     /login              34     40    200    210    220    240    240    240    240    240    240     20
         Aggregated           5      7      9     10     39     49    110    210    240    240    240    300
```

上面那張表每一列是一個請求名稱：`# fails` 是失敗的請求數與比例，`Avg`、`Min`、`Max`、`Med` 是毫秒，`req/s` 是整段時間的平均每秒請求數。下面那張是百分位數，標題寫著 approximated：Locust 把回應時間分桶計數，百分位數是從桶算出來的近似值。`Aggregated` 是全部請求合起來的那一列，後面門檻判定用的 `environment.stats.total` 就是它。

讀這張表時有三件事要分開看。一是 `POST /login` 剛好 20 筆，每個使用者的 `on_start` 各一筆，登入的延遲算進了 `Aggregated`；二是 `/flaky` 的失敗率 10.91% 接近受測服務每 10 個請求回一次 500 的設定，`Aggregated` 被 `/items/[id]` 的大量成功請求攤成 2.00%，所以錯誤率的門檻只看 `Aggregated` 時，單一 endpoint 的高錯誤率可能過得了門檻；三是這張表的延遲是這台機器、這一次的值，受測服務、Locust 與 Docker 共用同一台筆電的 CPU。這次實測裡 `-u` 10 到 20、有沒有 `--reset-stats` 的幾次執行，Aggregated 的 p95 在 48 到 380 毫秒之間，同樣的 `-u 20 -r 5 -t 30s` 在不同時間跑兩次，一次 380、一次 49，所以這裡的數字只用來看表的形狀，不能拿來當門檻；門檻要從讀者自己的環境重跑幾次的波動範圍取（[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)〈Regression 判讀方法〉）。

`--csv out/run1` 寫出四個檔案：`run1_stats.csv` 每個請求名稱一列，欄位跟終端機的兩張表相同（多一欄 `Average Content Size`），但它是執行中每秒覆寫一次的快照，最後一次寫在結束之前，這次的 Aggregated 是 296 筆，終端機的表是 300 筆；`run1_stats_history.csv` 是執行中每秒一列的快照（2.47.0 的原始碼 `locust/stats.py` 的 `CSV_STATS_INTERVAL_SEC = 1`）；`run1_failures.csv` 依錯誤訊息計數；`run1_exceptions.csv` 記 locustfile 裡沒有處理的例外。

這次沒有加 `--csv-full-history`，所以 `_stats_history.csv` 每秒只有 Aggregated 一列，`Requests/s` 是最近十秒左右的平均，百分位數與以 Total 開頭的欄位（`Total Average Response Time` 這類）都從執行開始累積（原始碼 `StatsCSV._stats_history_data_rows` 只在 full history 時改用最近一段時間的百分位數）；加了 `--csv-full-history` 時，每個請求名稱各一列、百分位數用最近一段時間的視窗。累積的平均延遲兩列直接相減得不到那一段時間的平均，要用兩列的總筆數加權換算，換算寫在 [Locust 在容量探測的用法：closed model 下的逐級加壓、吞吐量與延遲的換算、pacing 的上限、worker 的檢查與排查順序](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/) 的〈從每秒請求數與延遲判讀受測服務的狀態〉。

CI 的後處理讀 `_stats.csv` 時，量到的是結束前最後一次寫入的快照，筆數與百分位數可能比終端機的表少一截；門檻要跟終端機一致時，判定寫在〈quitting 事件裡的門檻判定〉的 listener 裡。

## 內建的 exit code：有失敗、沒有失敗但變慢

〈headless 執行、終端機的統計表與 CSV〉那一次執行的 exit code 是 1。Locust 結束時，locustfile 沒有自己設定 exit code 的話，有任何失敗的請求或 task 裡未處理的例外時回 1（這個值可以用 `--exit-code-on-error` 換），listener 這類事件處理裡未處理的例外回 2，都沒有時回 0（官方文件〈Running without the web UI〉的〈Controlling the exit code of the Locust process〉；2.47.0 的原始碼 `locust/main.py` 的 `shutdown()`）。JMeter 的約定相反：同一個受測服務、同樣有失敗的請求，JMeter 的 CLI mode 回 0（[JMeter 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/jmeter/hands-on/jmeter-local-lab/) 的〈CLI mode 執行與 JTL〉）。這次分三種情形實跑：

```bash
# 有失敗的請求：/flaky 會回 500
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile_basic.py --headless -u 10 -r 5 -t 15s \
  --host http://target:8080 --only-summary
# exit=1

# 排除 /flaky：沒有失敗的請求
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile_basic.py --headless -u 10 -r 5 -t 15s \
  --host http://target:8080 --only-summary --exclude-tags flaky
# exit=0

# 有失敗時改回 3
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile_basic.py --headless -u 10 -r 5 -t 10s \
  --host http://target:8080 --only-summary --exit-code-on-error 3
# exit=3
```

接著讓受測服務每個請求多等 400 毫秒，再跑一次排除 `/flaky` 的那一條：

```bash
docker rm -f target
docker run -d --rm --name target --network loadlab -e DELAY_MS=400 \
  -v "$PWD/target:/app:ro" python:3.12-slim python /app/app.py
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile_basic.py --headless -u 10 -r 5 -t 15s \
  --host http://target:8080 --only-summary --exclude-tags flaky
#          Aggregated   65     0(0.00%) |    456      45    1879    420 | ...
# exit=0
```

平均延遲從前一次的幾十毫秒升到 456 毫秒，exit code 仍然是 0：內建的判定只看有沒有失敗，不看延遲。CI 只看 exit code 的話，這一次變慢的執行照樣讓 job 通過，所以延遲的門檻要另外判定，寫法在〈quitting 事件裡的門檻判定〉。另一種做法是在 Locust 之外用 shell 或一支程式讀 `_stats.csv` 判定（這次沒有實跑），換到的是判定跟 locustfile 分開、同一支程式可以給別的工具用，付出的是 CI 的指令要多一步、判定與 locustfile 分兩處版控；寫在 locustfile 裡時兩者一起版控，CI 的指令不必改。

## quitting 事件裡的門檻判定

`quitting` 事件在 Locust 結束、算出 exit code 之前觸發；listener 設了 `environment.process_exit_code`，Locust 就用這個值當 exit code，不再看有沒有失敗。locustfile 最後加上這一段：

```python
@events.quitting.add_listener
def check_thresholds(environment, **kwargs):
    # 內建的 exit code 只看有沒有失敗；延遲與錯誤率的門檻在這裡自己判定
    if isinstance(environment.runner, WorkerRunner):
        return  # worker 每 3 秒把統計送給 master 並清空，判定只在 master 或單機做
    max_fail_ratio = float(os.environ.get("GATE_MAX_FAIL_RATIO", "0.05"))
    max_p95_ms = float(os.environ.get("GATE_MAX_P95_MS", "300"))
    total = environment.stats.total
    if total.num_requests == 0:
        print("GATE ERROR: no requests")
        environment.process_exit_code = 4  # 沒有樣本：測試本身沒跑成，跟門檻不成立分開
        return
    p95 = total.get_response_time_percentile(0.95)
    if total.fail_ratio > max_fail_ratio:
        print(f"GATE FAIL: fail ratio {total.fail_ratio:.3f} > {max_fail_ratio}")
        environment.process_exit_code = 1
    elif p95 > max_p95_ms:
        print(f"GATE FAIL: p95 {p95} ms > {max_p95_ms} ms")
        environment.process_exit_code = 1
    else:
        print(f"GATE PASS: fail ratio {total.fail_ratio:.3f}, p95 {p95} ms")
        environment.process_exit_code = 0
```

兩個門檻從環境變數讀，CI 的 job 用 `-e GATE_MAX_P95_MS=...` 傳進去，門檻改了不必改 locustfile；`0.05` 與 `300` 是佔位的預設值，實際的值從基準版本在同一個環境量到的結果取（[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)〈Baseline 設定〉）。這次的環境沒有加延遲時 p95 就到過 380 毫秒，300 會連正常的執行一起擋下；下面加 400 毫秒延遲的那一次判成 FAIL，只說明 listener 的判定路徑有作用，不說明 300 是這個環境適用的門檻。`WorkerRunner` 那一行在分散執行時才有作用，原因在〈master 與兩個 worker〉那一節。`num_requests == 0` 那一段擋的是一次沒有送出任何請求的執行：沒有它時，空的統計裡錯誤率是 0、p95 是 0，兩個門檻都通過，listener 回 0，CI 放行一次什麼都沒量到的執行；這次分散執行時實際遇到過這種情形（〈master 與兩個 worker〉的 heartbeat 那一段），加了這一段之後那條路徑沒有重跑，回 4 是照程式推出的結果。

`num_requests == 0` 那一段涵蓋不到最常見的一種沒跑成：受測服務整個連不上時，`on_start` 的登入就失敗，請求數不是 0、錯誤率是 100%，listener 回的是 1，跟退化分不開（審查時另外實跑過：`--host` 指向不存在的 container，`POST /login` 5 筆全部失敗，listener 印 `GATE FAIL: fail ratio 1.000 > 0.05`）；要把它也歸到 4，另外判錯誤率是不是 100%，或在測試之前先打一次健康檢查。受測環境只有一部分故障時（一台 replica 掛掉、連線被重設），健康檢查會通過，錯誤率落在 0 與 100% 之間，這兩種做法都把它判成退化（審查時讓受測服務對一部分連線不回應就關閉，Error report 是 `RemoteDisconnected('Remote end closed connection without response')`，失敗率 14%，listener 回 1）；分辨的依據是 Error report 裡錯誤的類別，連線層的錯誤（`RemoteDisconnected`、`ConnectionRefusedError`）指向受測環境，HTTP 的錯誤狀態碼才可能是這一版程式的退化，錯誤率本身分不出來（把錯誤類別寫進判定這次沒有實跑）。門檻的環境變數不是數字時，`float()` 在 listener 裡拋出例外，exit code 沒被設定，回的是內建判定的 1 或 2。4 是這支 listener 自己的約定，[JMeter 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/jmeter/hands-on/jmeter-local-lab/) 的 `gate.py` 也用 4 表示「測試本身沒跑成」。

拿受測服務多等 400 毫秒的那個狀態跑：

```bash
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile.py --headless -u 10 -r 5 -t 15s \
  --host http://target:8080 --only-summary --exclude-tags flaky
# GATE FAIL: p95 480 ms > 300.0 ms
# exit=1
```

同一個狀態，內建的判定回 0，listener 判出 p95 超過門檻、回 1。listener 在門檻通過時把 exit code 設成 0，這時即使有失敗的請求，內建的判定也被蓋掉；下面讓受測服務恢復成不延遲、放寬延遲門檻再跑一次，看這個情形：

```bash
# 受測服務恢復成不延遲：不帶 DELAY_MS 重新啟動
docker rm -f target
docker run -d --rm --name target --network loadlab \
  -v "$PWD/target:/app:ro" python:3.12-slim python /app/app.py
# -e 是 docker run 的參數，要寫在 image 名稱 lab-locust 之前；
# 寫在 image 名稱之後，docker 會把它當成要在 container 裡執行的指令（exit 127）
docker run --rm --network loadlab -e GATE_MAX_P95_MS=5000 \
  -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile.py --headless -u 10 -r 5 -t 15s \
  --host http://target:8080 --only-summary
#          Aggregated   77     1(1.30%) | ...
# GATE PASS: fail ratio 0.013, p95 80 ms
# exit=0
```

受測服務剛重啟，`/flaky` 要累積到第 10 個請求才回第一個 500，15 秒裡送出的 `/flaky` 少於 10 個時失敗數是 0，看不到這個情形，那時把 `-t` 拉長到 30 秒重跑。這次有 1 個失敗的請求，失敗率 1.3% 低於 5% 的門檻，exit code 是 0：錯誤率門檻允許一定比例的失敗，listener 判它通過，同時把內建的「有失敗就回 1」蓋掉了。要讓任何失敗都擋下時，把 `GATE_MAX_FAIL_RATIO` 設成 0，或在 listener 裡另外看 `total.num_failures`。

這一段 listener 是最小的寫法，照抄進 CI 之前有三件事要知道。一是門檻不成立時設 1，跟沒有 listener 時內建判定「有失敗的請求」用的 1 是同一個值，CI 換過 locustfile、同一條 job 跑兩種 locustfile，或 listener 本身拋出例外而又有失敗的請求時，分不出這次的 1 是門檻不成立還是零星的失敗；二是門檻通過時設 0 會蓋掉內建判定，task 裡未處理的例外也一起被蓋掉；三是只判 `stats.total`，〈headless 執行、終端機的統計表與 CSV〉那一次已經看到單一 endpoint 的高錯誤率被攤平，要逐個請求名稱判定時改讀 `environment.stats.get(<name>, <method>)`（這次沒有實跑）。門檻不成立改用另一個 exit code、通過時不設 0、依關鍵流程各自判定的寫法與理由，見 [Locust 在效能 regression gate 的用法：exit code 與門檻判定、預熱與 on_start 的請求、closed model 下的比較、custom client 回報的請求範圍、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/) 的〈quitting listener 的寫法：統計的範圍、百分位數的分桶與回應的驗證〉。

## --reset-stats 與 on_start 的請求

統計表裡的 `POST /login` 是 `on_start` 送的，登入只在啟動時發生，它的延遲跟穩態下的請求混在一起。`--reset-stats` 讓 Locust 在使用者全部啟動之後清空一次統計；下面這次執行看清空之後，`on_start` 送的 `POST /login` 還留下幾筆：

```bash
docker run --rm --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile.py --headless -u 20 -r 5 -t 30s \
  --host http://target:8080 --only-summary --reset-stats
# ... locust.runners: Resetting stats
# POST     /login     5     0(0.00%) | ...
```

清空之後 `POST /login` 還剩 5 筆，不是 0。`-r 5` 每秒啟動 5 個使用者，最後一秒啟動的那 5 個，它們的 `on_start` 在統計清空的時候還沒跑完：「使用者全部啟動」這件事在最後一批使用者被建立時就成立，不等它們的 `on_start` 結束。所以 `--reset-stats` 排除得了大部分的登入，排除不了最後一批；要完全排除時，門檻只看量測的那幾個請求名稱、不看 Aggregated，或 listener 判定時從統計裡去掉 `/login` 那一列（兩種這次都沒有實跑）。預熱的請求還有哪些處理方式、各自的代價，見 [Locust 在效能 regression gate 的用法：exit code 與門檻判定、預熱與 on_start 的請求、closed model 下的比較、custom client 回報的請求範圍、PR 與 nightly 的分工、證據保存與 gate 失敗的排查順序](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/) 的〈預熱與量測區間：--reset-stats 與 on_start 裡的請求〉。

## master 與兩個 worker

Locust 用 gevent 在一個作業系統執行緒裡輪流執行所有使用者，所以一個 Locust 程序只用得到一顆 CPU 核心（[Gevent Monkey Patching](/backend/knowledge-cards/gevent-monkey-patching/)），施壓量不夠時要開多個 worker 程序，由一個 master 分配使用者、收集統計。這次在同一台機器上開一個 master 與兩個 worker：

```bash
# 重跑時先刪掉上一次留下的 container，名稱才能重用（否則回 Conflict）
docker rm -f lmaster lw1 lw2 2>/dev/null
# master：不跑使用者，等兩個 worker 都連上才開始
docker run -d --name lmaster --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
  locust -f locustfile.py --master --headless --expect-workers 2 \
  -u 20 -r 5 -t 20s --host http://target:8080 --csv out/dist --only-summary \
  --logfile out/master.log
# 兩個 worker：連到 master 的主機名
for i in 1 2; do
  docker run -d --name lw$i --network loadlab -v "$PWD/locust:/mnt/locust" lab-locust \
    locust -f locustfile.py --worker --master-host lmaster
done
# 等 master 結束，印出它的 exit code
docker wait lmaster
# listener 的判定與統計表只寫到 master 的 stdout，從 container 的 log 讀
docker logs lmaster 2>&1 | grep GATE
# GATE PASS: fail ratio 0.014, p95 49 ms
```

`--expect-workers 2` 讓 master 等到兩個 worker 都連上才開始；不給時預設是 1（2.47.0 的原始碼 `locust/argument_parser.py`），master 等到第一個 worker 連上就開始、把使用者全部派給它；第二個 worker 晚幾秒連上時，master 重新把使用者分給兩個 worker：原始碼 `MasterRunner` 處理 worker 連上的那一段，在測試執行中會再呼叫一次 `start()`。`--enable-rebalancing` 管的是另一件事，worker 失聯時要不要把它的使用者分給其他 worker。所以開頭那幾秒（從原始碼推出，這次沒有實跑不給 `--expect-workers` 的情形）的負載全在一個 worker 程序上，統計裡混著一段單一 worker 送出的數據，它的那一顆 CPU 核心先到頂的話，那一段量到的是施壓端的上限；`--expect-workers` 設成 worker 的數量，才從第一個請求起就由兩個 worker 分擔。

`--expect-workers` 的代價是有 worker 一直沒連上時（還沒連上就被殺掉、image 拉不下來），master 會一直等下去，`-t` 管不到這段等待，`docker wait lmaster` 跟著卡住，CI 要等到 job 逾時；`--expect-workers-max-wait <秒數>` 設定等待的上限，`locust --help` 寫明不給時是一直等。審查時另外實跑過：只開一個 worker 時 master 每秒印 `Waiting for workers to be ready, 1 of 2 connected`；加 `--expect-workers-max-wait 8` 之後 master 印 `Gave up waiting for workers to connect` 並回 1，沒有 `GATE` 那一行。這個 1 是測試沒跑成，listener 沒有機會判定，跟門檻不成立的 1 是同一個值，CI 要分開時從 log 找 `Gave up waiting`。上限取多少看 worker 的 container 平常多久連得上，這次沒有量。

`lmaster` 是 master 的 container 名稱，worker 用 `--master-host` 指向它；`-u 20` 是全部 worker 合計的使用者數，master 把它平均分給兩個 worker，加 worker 不會讓合計增加；JMeter 的 remote testing 是反過來的，每台 server 都跑完整的 test plan，負載隨台數倍增（[JMeter 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/jmeter/hands-on/jmeter-local-lab/) 的〈remote testing：一台 client 與兩台 server〉）。master 這次放在背景跑，所以統計用 `--csv` 寫進掛載的目錄，Locust 自己的 log 用 `--logfile` 寫成 `out/master.log`；listener 印的 `GATE` 那一行與 `--only-summary` 的統計表寫到 stdout，不進 `--logfile`，所以 master 與 worker 都沒有加 `--rm`，結束之後還能用 `docker logs lmaster`、`docker logs lw1` 讀；加了 `--rm` 的話，container 結束時 stdout 一起消失，只拿得到 `docker wait` 印的 exit code，看不到判定的理由。CI 裡要用 master 的結果當 job 的結果時，取 `docker wait` 印出的值（`exit "$(docker wait lmaster)"`），不是 `grep` 那一條的 exit code。master 送出結束訊息之後只等 0.5 秒收 worker 的最後一份統計就觸發 `quitting`（2.47.0 的 `MasterRunner.quit()`）；加了 `--stop-timeout` 時，worker 要等使用者停完才送，最後一段可能不在判定裡（這一點從原始碼推出，沒有實跑）。

master 的 log 裡看得到兩個 worker 連上、使用者被派出：

```text
... (index 0) reported as ready. 1 workers connected.
... (index 1) reported as ready. 2 workers connected.
... Sending spawn jobs of 20 users at 5.00 spawn rate to 2 ready workers
```

門檻判定只在 master 做的原因，是 worker 每 3 秒把手上的統計送給 master，送出之後就清空（2.47.0 的原始碼 `locust/runners.py` 的 `WORKER_REPORT_INTERVAL = 3.0`），結束時也先送最後一次再觸發 `quitting`：listener 還沒加 `WorkerRunner` 那一行時，worker 的 log 在結束時印出 `GATE PASS: fail ratio 0.000, p95 0 ms`，它手上的統計是空的。加了那一行之後，worker 不再判定，exit code 由 master 決定。

worker 的 heartbeat 失敗是這次遇到、成因沒有查出來的現象。最早的兩次分散執行，master 在派出使用者大約 4 秒後印出 `Worker ... failed to send heartbeat, setting state to missing.`。第一次接著印出 `The last worker went missing, stopping test.`，整次執行 0 個請求，而那時的 listener 還沒有 `num_requests == 0` 那一段，判了 `GATE PASS`、exit code 0；第二次跑完了 20 秒，但 `POST /login` 的最大延遲到 4 秒。之後改了受測服務的位址與 master、worker 的啟動順序重跑五次，都沒有重現。

master 判定 worker 失聯的機制是心跳訊息（heartbeat）：worker 每秒送一次 heartbeat 告訴 master 自己還在；master 替每個 worker 記一個計數，收到 heartbeat 時設回 3，之後每秒減 1，減到負數時判它失聯，所以一個 worker 大約 4 秒沒送 heartbeat 就被判失聯（2.47.0 的原始碼 `locust/runners.py` 的 `HEARTBEAT_INTERVAL = 1`、`HEARTBEAT_LIVENESS = 3`）。這次兩次都是在派出使用者之後 4.1 到 4.2 秒判失聯，代表那段時間 worker 的程序停住了。從這個機制推得出的成因有三種：施壓機的 CPU 被別的工作占走、locustfile 裡有 gevent 管不到的在 C 裡做的 I/O，或 locustfile 裡長時間不讓出執行權的 CPU 運算（[Gevent Monkey Patching](/backend/knowledge-cards/gevent-monkey-patching/)）。這次的 locustfile 沒有在 C 裡做的 I/O，CPU 運算只有解析登入回應的一個小 JSON；施壓機的 CPU 有沒有被占走，那段時間沒有收集到指標，無法確認。之後照最早那兩次的條件（worker 先啟動、master 在前景、受測服務用名稱）在同一台機器上又重跑 10 次，都沒有重現，其中兩次用來驗證兩個假設。一次在 Docker 的 VM 裡跑 16 個占滿 CPU 的迴圈：`POST /login` 的中位數到 1300 毫秒、最大值 4560 毫秒，跟第二次的形狀相同，但 worker 沒有失聯，所以 VM 裡的 CPU 競爭解釋得了第二次的登入延遲，解釋不了 heartbeat 大約 4 秒都送不出去。另一次讓名稱解析卡住 8 秒：worker 用的是 gevent 的 thread resolver，查詢在另一個執行緒裡等，同一個程序裡每 0.1 秒醒一次的 greenlet，最大間隔是 0.12 秒，所以名稱解析變慢不會讓 heartbeat 停住。

出現這個訊息的那一次執行，結果不能用：worker 停住的那幾秒，請求延遲被拉高；被判失聯的 worker 沒有被叫停，它之後送回的統計照樣算進去（master 收到統計時不看 worker 的狀態），所以統計裡看不出哪一段是停住的，只有全部 worker 都失聯時 master 才停止測試。這次的 listener 判不出這種情形：只要請求數不是 0，有 worker 失聯的那一次照樣判 PASS 或 FAIL；CI 要擋下時，從 `--logfile` 寫出的 `locust/out/master.log` 找 `failed to send heartbeat`：這一行跟 Locust 其他的 log 一起寫進那個檔案，不在 stdout，讀 `GATE` 用的 `docker logs lmaster` 裡找不到（審查時另外實跑過：在執行中殺掉一個 worker，`master.log` 裡有這一行，`docker logs` 裡 0 筆，那一次 listener 照樣判 `GATE PASS`、exit 0）；或在 listener 裡另外查 runner 記錄的 worker 狀態（這次沒有實跑）；master 在 worker 失聯大約 60 秒之後刪掉它的紀錄（2.47.0 的 `HEARTBEAT_DEAD_INTERNAL = -60`），執行時間長、worker 失聯得早時，`quitting` 觸發時那筆紀錄已經不在，要在失聯的當下記下來。

分辨成因時（這一段的查法這次沒有在 heartbeat 失敗的當下跑過），`docker ps -a` 一條指令就分得出 worker 的程序是結束了還是被卡住，`-a` 讓已經結束的 container 也列出來。container 已經結束時，看它的結束碼。137 是程序被 SIGKILL 殺掉，`docker inspect -f '{{.State.OOMKilled}}' lw1` 印 `true` 時是記憶體不足被殺，這兩種情形 worker 的 log 裡沒有原因（審查時用 `docker kill -s KILL` 實跑過，被殺的 worker 的 log 只有 `Starting Locust 2.47.0` 一行）；其他結束碼的原因記在它的 log 裡。程序已經結束的這幾種情形，CPU 指標都不必查。container 還在跑時，程序是被卡住，要靠那段時間施壓機的 CPU 指標才分得出是不是 CPU 被占走。worker 要量哪些資源、worker 數怎麼決定，見 [Locust 在容量探測的用法](/backend/09-performance-capacity/vendors/locust/locust-capacity-probing/) 的〈worker 程序的檢查與 worker 數的量法〉。

這次有幾次執行，worker 的 log 結尾出現 `Error resolving address: [Errno -2] Name or service not known`，另外幾次沒有；有出現時都在 master 結束之後：master 的 container 結束之後，Docker 的 DNS 不再解析它的名稱（container 只是停止、沒有刪掉也一樣），worker 收到結束訊息之後還在重連那個主機名，這一行不影響結果。

## 清理 container 與 Docker network

```bash
docker rm -f lmaster lw1 lw2 target
docker network rm loadlab
```

master 與 worker 沒有加 `--rm`，要自己刪；`target` 帶著 `--rm`，`docker rm -f` 停掉它時一起刪除。還有執行中的 container 連著 network 時，`docker network rm` 失敗，訊息是 `network loadlab has active endpoints`，後面列出那幾個 container；已經結束、還沒刪的 container（這裡的 worker）不在那份清單裡，不擋刪除，但不刪的話會留在 `docker ps -a` 裡。`out/` 底下的 CSV、HTML 與 log 留在本機的目錄，不隨 container 刪除。
