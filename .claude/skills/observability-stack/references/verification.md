# 驗收：讀得到、有標籤、會反應

> 何時讀：每接上或改動一個收集來源之後，以及寫完告警規則之後。三項都要跑，結果以實測值寫進 README 或驗收紀錄。

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

一個服務一列，少了誰就是誰沒被看到。讀得到而缺標籤時，數字看起來正常，依服務分組的圖卻是空的。

## 數字會反應：故障注入

刻意製造一次每個來源該看到的狀況，記下指標的實測值。製造的狀況要能還原，做完把服務恢復原狀：

| 製造的狀況 | 怎麼做 | 看哪個指標 | 該看到 |
| --- | --- | --- | --- |
| 一個容器吃滿 CPU | 在容器裡跑 `timeout 80 sh -c 'while :; do :; done'` | `rate(container_cpu_usage_seconds_total[1m])` 依服務加總 | 約 1 顆核心 |
| 資料庫連線被佔住 | 開幾個連線各自 `select pg_sleep(90)` | `pg_stat_activity_count{state="active"}` | 增加開出的數量 |
| 一個容器停掉 | `docker compose stop <服務>` | 外部探測的成功指標；`time() - container_last_seen` | 探測失敗；秒數持續增加（序列本身不會消失） |
| 入口有流量 | 對入口送一批請求 | `rate(nginx_http_requests_total[1m])` | 上升 |
| 告警規則會成立 | 用上面的狀況觸發，或暫時把門檻調低 | Prometheus 的 Alerts 頁面、Alertmanager | 規則在 `for` 的時間後成立，被抑制的出現在抑制清單 |

主機本身正在過載時做故障注入，數字會混進主機的雜訊（同時量的探測延遲與讀取耗時都偏高）；記下當時主機的負載，結果有疑問時在主機安靜時重做。

## 驗收結果怎麼寫

每一項寫實測值，不寫「已確認」：「`up` 七個 job 皆為 1；`pg_up`、`redis_up`、`nginx_up` 皆為 1；15 個服務都有標籤；cache 空轉 0.98 核心；5 個 `pg_sleep` 連線 active=5；停掉 portal 後探測為 0、last_seen 每 15 秒增加 15」。只寫「已確認」與沒做過，在紀錄上長得一樣。
