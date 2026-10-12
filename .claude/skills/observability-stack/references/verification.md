# 驗收：讀得到、有標籤、會反應

> 何時讀：每接上或改動一個收集來源之後，以及寫完告警規則之後。三項都要跑，結果寫進 README 或驗收紀錄，格式見〈驗收紀錄怎麼寫〉。不適用：告警門檻怎麼定，見 SKILL.md〈告警〉。驗收前先跑 SKILL.md〈量測前的主機檢查〉；驗收紀錄寫完，回 SKILL.md〈流程〉表的下一列。

## 比較基準來自部署設定，不來自查詢結果

每一項驗收都是拿「預期」比「實際」。預期要來自執行者以外、而且在拿到查詢結果之前就存在的來源：部署設定、盤點表、使用者的原話、規則實際產生的告警。照查詢結果抄出來的預期清單，比對永遠成立，紀錄上和認真做過的版本分不出來。

## 讀得到，而且 exporter 連得到它監控的服務

```promql
up                          # 每個 job 都要是 1
pg_up                       # exporter 連得到 PostgreSQL
redis_up                    # exporter 連得到 Redis / Valkey
nginx_up                    # exporter 連得到 Nginx 的狀態頁
node_scrape_collector_success == 0   # 失敗的 collector；這台機器本來就沒有的硬體不算，預期有資料的出現在這裡要查
```

`up` 的 job 清單逐項對上盤點表的「收集方式」欄：該讀而沒寫進讀取設定的對象沒有 `up` 序列，「每個 job 都是 1」照樣成立。`up` 只代表 Prometheus 連得到 exporter，只看 `up` 的驗收，對「exporter 起來了但帳號錯、位址錯」全部回報通過。

## 每個預期的對象都在標籤裡

預期的對象從部署設定取：compose 跑 `docker compose config --services`。再查實際有哪些：

```promql
count by (container_label_com_docker_compose_service) (container_memory_working_set_bytes)
```

兩份清單並排寫進驗收紀錄，逐項對上才算通過。結果另有一列不帶服務標籤，是 root cgroup 與 compose 以外的容器；可是查詢結果**只有**這一列、或帶標籤的列少於預期清單時，是 cAdvisor 沒取得容器資訊（見 `layer-signals.md` 的 cAdvisor 一則），驗收不通過。讀得到而缺標籤時，數字看起來正常，依服務分組的圖卻是空的。

## 數字會反應：故障注入

盤點表的每個收集方式各配一個製造的狀況，記下注入前、注入中、還原後三個值；只記一個值，分不出數字是本來就這樣還是有反應。下表沒有對應列的來源（例如 node_exporter 的磁碟或 redis_exporter），自己設計一個狀況並寫明做法。製造的狀況要能還原，做完把服務恢復原狀：

| 製造的狀況 | 怎麼做 | 看哪個指標 | 該看到 |
| --- | --- | --- | --- |
| 一個容器吃滿 CPU | `docker compose exec <服務> timeout 80 sh -c 'while :; do :; done'`；只有 `docker compose exec <服務> sh -c true` 失敗的服務（scratch、distroless 映像）才改在同一台主機跑 `docker run --rm --cpus 1 alpine timeout 80 sh -c 'while :; do :; done'`，紀錄寫那條失敗訊息，並註明驗到的是主機與其他容器而非該服務 | `rate(container_cpu_usage_seconds_total[1m])` 依服務加總 | 約 1 顆核心 |
| 資料庫連線被佔住 | 開幾個連線各自 `select pg_sleep(90)`，例如 `docker compose exec -T <資料庫服務> psql -U <使用者> -c 'select pg_sleep(90)' &` 跑幾次；受管資料庫從能連到它的機器跑 `psql` | `sum(pg_stat_activity_count{state="active"})`（這個指標依資料庫分列） | 增加開出的數量 |
| 一個容器停掉 | `docker compose stop <服務>`，量完 `docker compose start <服務>` 還原 | 外部探測的成功指標；`time() - container_last_seen` | 探測失敗；秒數持續增加（序列本身不會消失） |
| 入口有流量 | 對入口送一批請求 | `rate(nginx_http_requests_total[1m])` | 上升 |
| 告警規則會成立 | 用上面的狀況觸發。製造不出狀況的規則（例如磁碟將滿）才暫時把門檻改成恰好會成立的值，紀錄寫明哪幾條是改門檻驗的，量完改回 | Prometheus 的 Alerts 頁面、Alertmanager | 規則在 `for` 的時間後成立 |
| 重建容器不誤報 | `docker compose up -d --force-recreate <服務>`，等超過規則的秒數 | 「容器停止」的規則 | 不成立（舊容器的序列還在，規則要依服務取最小值） |
| 主機外的訊號會發通知 | 停掉一個被監控的服務 | 主機外那一端的探測與它的通知管道 | 連續失敗次數之後收到通知；紀錄寫收到的時間 |
| Prometheus 停掉時有人知道 | `docker compose stop prometheus`，等超過外部服務的心跳期限，量完 start | 外部的心跳服務 | 心跳中斷的通知 |
| 抑制規則會壓下症狀 | 對 Alertmanager 的 `/api/v2/alerts` 送入合成的「原因」與「症狀」告警（設 `endsAt` 讓它們自己結束）。每一則的標籤各自從它那條規則的運算式取：拿掉比較運算子直接在 Prometheus 查，把查到的標籤原樣帶上，原因與症狀各查各的、不手動統一（`ALERTS` 只在規則成立過之後才有序列）；規則有 `equal` 時另送一則 `equal` 標籤值不同的症狀 | `GET /api/v2/alerts?active=false&silenced=false&unprocessed=false`（只列被抑制的告警）的 `status.state` | 標籤值相同的症狀是 `suppressed`，`inhibitedBy` 列出原因；標籤值不同的那一則用不帶篩選的 `GET /api/v2/alerts` 確認是 `active` |

`timeout` 與 `pg_sleep` 的秒數要長過查詢的時間窗（`[1m]`）加一個讀取間隔，時間窗改了就跟著改。

送入合成告警的指令（macOS 的 `date` 語法；Linux 用 `date -u -d '+15 min'`；位址、告警名稱與標籤值依自己的部署替換，標籤值從各規則的運算式查）：

```sh
now=$(date -u +%Y-%m-%dT%H:%M:%SZ); end=$(date -u -v+15M +%Y-%m-%dT%H:%M:%SZ)
curl -XPOST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' -d "[
  {\"labels\":{\"alertname\":\"HostCpuSaturated\",\"severity\":\"warning\",\"host\":\"host-a\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ServiceSlow\",\"severity\":\"warning\",\"host\":\"host-a\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ServiceSlow\",\"severity\":\"warning\",\"host\":\"host-b\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"}]"
# 只列被抑制的告警：host-a 的 ServiceSlow 應在這裡，狀態 suppressed
curl -s 'http://127.0.0.1:9093/api/v2/alerts?active=false&silenced=false&unprocessed=false'
# 全部告警：host-b 的 ServiceSlow 應為 active
curl -s 'http://127.0.0.1:9093/api/v2/alerts'
```

合成告警只驗證 Alertmanager 的抑制規則；Prometheus 的告警規則在實際的狀況下會不會成立，要另外用上表製造狀況的那幾種方式確認。

主機本身正在過載時做故障注入，數字會混進主機的雜訊（同時量的探測延遲與讀取耗時都偏高）。主機的 load 在主機本身看（指令見 SKILL.md〈量測前的主機檢查〉），注入前與注入期間都記錄；注入期間的 load 扣掉注入本身用掉的核心數之後，除以核心數仍高於注入前，而結果和預期不符時，等主機回到注入前的負載再重做。

## 驗收紀錄怎麼寫

每一項寫三樣：比較基準與它的出處（部署設定、盤點表、使用者的原話、規則實際產生的告警，不是這次查詢的結果）、實測值、兩者對不對得上。「會反應」的項目寫注入前、注入中、還原後三個值；有 `equal` 或分組的規則，另寫一個不該成立的對照。例：

「`up`：盤點表 8 個收集方式、讀取設定 8 個 job，皆為 1；`pg_up`、`redis_up`、`nginx_up` 皆為 1。標籤：`docker compose config --services` 列出 16 個服務，帶標籤的 16 列逐項對上。`<快取服務>` CPU 0.01 → 0.98 → 0.02 核心；active 連線 0 → 5 → 0；停掉 `<服務 A>` 後探測 1 → 0 → 1、last_seen 每 15 秒增加 15。主機：Mac 上 `uptime` 與 `sysctl -n hw.ncpu`，load 除以核心數注入前 0.4、注入中 0.5，門檻 1.0（使用者給的值）。」

只寫「已確認」與沒做過，在紀錄上長得一樣。

紀錄最後一節列「未驗」：本環境做不到的（例如虛擬機裡主機飽和的規則不會成立、開發環境沒有主機外的機器）、選擇不做的（例如不做的告警），各寫原因，以及出現哪個條件時補驗。沒有這一節，暫時沒驗的項目之後沒有人會回來驗。
