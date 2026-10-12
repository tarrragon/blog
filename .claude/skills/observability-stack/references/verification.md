# 驗收：讀得到、有標籤、會反應

> 何時讀：每接上或改動一個收集來源之後，以及寫完告警規則之後。三項都要跑，結果以實測值寫進 README 或驗收紀錄。不適用：告警門檻怎麼定，見 SKILL.md〈告警〉。驗收結果寫完，回 SKILL.md〈流程〉表的下一列。

## 讀得到，而且 exporter 連得到它監控的服務

```promql
up                          # 每個 job 都要是 1
pg_up                       # exporter 連得到 PostgreSQL
redis_up                    # exporter 連得到 Redis / Valkey
nginx_up                    # exporter 連得到 Nginx 的狀態頁
```

`up` 只代表 Prometheus 連得到 exporter。只看 `up` 的驗收，對「exporter 起來了但帳號錯、位址錯」全部回報通過。

## 每個預期的對象都在標籤裡

先列出預期的對象（例如 compose 的每個服務），再查實際有哪些：

```promql
count by (container_label_com_docker_compose_service) (container_memory_working_set_bytes)
```

一個服務一列，少了誰就是誰沒被看到；另有一列不帶服務標籤，是 root cgroup 與 compose 以外的容器，不算缺漏。讀得到而缺標籤時，數字看起來正常，依服務分組的圖卻是空的。

## 數字會反應：故障注入

刻意製造一次每個來源該看到的狀況，記下指標的實測值。製造的狀況要能還原，做完把服務恢復原狀：

| 製造的狀況 | 怎麼做 | 看哪個指標 | 該看到 |
| --- | --- | --- | --- |
| 一個容器吃滿 CPU | `docker compose exec <服務> timeout 80 sh -c 'while :; do :; done'`；映像沒有 `sh` 的服務（scratch、distroless）改在同一台主機上跑 `docker run --rm --cpus 1 alpine timeout 80 sh -c 'while :; do :; done'` 當干擾源，看主機與該容器以外的用量 | `rate(container_cpu_usage_seconds_total[1m])` 依服務加總 | 約 1 顆核心 |
| 資料庫連線被佔住 | 開幾個連線各自 `select pg_sleep(90)`，例如 `docker compose exec -T <資料庫服務> psql -U <使用者> -c 'select pg_sleep(90)' &` 跑幾次 | `sum(pg_stat_activity_count{state="active"})`（這個指標依資料庫分列） | 增加開出的數量 |
| 一個容器停掉 | `docker compose stop <服務>`，量完 `docker compose start <服務>` 還原 | 外部探測的成功指標；`time() - container_last_seen` | 探測失敗；秒數持續增加（序列本身不會消失） |
| 入口有流量 | 對入口送一批請求 | `rate(nginx_http_requests_total[1m])` | 上升 |
| 告警規則會成立 | 用上面的狀況觸發，或暫時把門檻調低 | Prometheus 的 Alerts 頁面、Alertmanager | 規則在 `for` 的時間後成立，被抑制的出現在抑制清單 |
| 重建容器不誤報 | `docker compose up -d --force-recreate <服務>`，等超過規則的秒數 | 「容器停止」的規則 | 不成立（舊容器的序列還在，規則要依服務取最小值） |
| 磁碟告警會成立 | 暫時把規則的門檻改成高於現在的剩餘比例，重新載入 | Prometheus 的 Alerts 頁面 | 每一顆磁碟各一則，主機的那一顆也在；量完改回門檻 |
| 抑制規則會壓下症狀 | 對 Alertmanager 的 `/api/v2/alerts` 送入一組合成的「原因」與「症狀」告警（設 `endsAt` 讓它們自己結束）；兩則的標籤要分別符合 `source_matchers` 與 `target_matchers`，規則有 `equal` 時兩則都帶上那幾個標籤且值相同 | `GET /api/v2/alerts?active=false&silenced=false&unprocessed=false`（只列被抑制的告警）的 `status.state` | 症狀是 `suppressed`，`inhibitedBy` 列出原因 |

`timeout` 與 `pg_sleep` 的秒數要長過查詢的時間窗（`[1m]`）加一個讀取間隔，時間窗改了就跟著改。

送入合成告警的指令（macOS 的 `date` 語法；Linux 用 `date -u -d '+15 min'`；位址與告警名稱依自己的部署替換）：

```sh
now=$(date -u +%Y-%m-%dT%H:%M:%SZ); end=$(date -u -v+15M +%Y-%m-%dT%H:%M:%SZ)
curl -XPOST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' -d "[
  {\"labels\":{\"alertname\":\"HostCpuSaturated\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ServiceSlow\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"}]"
curl -s 'http://127.0.0.1:9093/api/v2/alerts?active=false&silenced=false&unprocessed=false'
```

合成告警只驗證 Alertmanager 的抑制規則；Prometheus 的告警規則在實際的狀況下會不會成立，要另外用上表製造狀況的那幾種方式確認。

主機本身正在過載時做故障注入，數字會混進主機的雜訊（同時量的探測延遲與讀取耗時都偏高）；注入前與注入期間各記一次主機的 load 除以核心數；注入期間的值扣掉注入本身用掉的核心數之後仍高於注入前，而結果和預期不符時，等主機回到注入前的負載再重做。

## 驗收結果怎麼寫

每一項寫實測值，不寫「已確認」：「`up` 八個 job 皆為 1；`pg_up`、`redis_up`、`nginx_up` 皆為 1；16 個服務都有標籤；`<快取服務>` 空轉 0.98 核心；5 個 `pg_sleep` 連線 active=5；停掉 `<服務 A>` 後探測為 0、last_seen 每 15 秒增加 15」。只寫「已確認」與沒做過，在紀錄上長得一樣。
