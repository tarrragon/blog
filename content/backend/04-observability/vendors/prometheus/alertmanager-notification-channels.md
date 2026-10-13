---
title: "Alertmanager 的通知管道：路由樹、webhook 與 ntfy、email、私密網址的檔案、心跳與送不出去的偵測"
date: 2026-10-13
description: "Alertmanager 從只在網頁上看告警，到依嚴重度送到手機與信箱：路由樹怎麼決定一則告警送到哪裡、分組與三個時間參數控制什麼，以 webhook 接 ntfy 推播與它的訊息模板，email 與 Slack 的設定，私密網址為什麼要放在檔案裡，以及 Watchdog 心跳與通知送不出去時的偵測"
weight: 17
tags: ["backend", "observability", "vendor", "prometheus", "alertmanager"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列，接在 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 之後：那一篇的 Alertmanager 只有一個不送任何通知的 receiver，告警只出現在它的網頁上。

這一篇整理讓 Alertmanager 把告警送出去的設定：路由、receiver、私密值的放法，以及告警鏈本身停掉或送不出去時怎麼發現。哪些條件該告警、分組與抑制的規則見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)，這裡從「告警已經進到 Alertmanager」開始。文中的設定取自一個短網址服務的監控（Alertmanager 0.34.1、Prometheus 3.15.0），通知服務在本機以 ntfy 2.30 與 Mailpit（攔截郵件的測試用 SMTP 伺服器）的容器代替，時間與行為都是在那裡量到的；Slack 只以 `amtool check-config` 檢查過設定語法。

## 路由樹：一則告警送到哪個 receiver

receiver 是一組通知設定的名字，裡面寫要送到哪裡（ntfy、信箱、Slack 頻道）；route 決定哪些告警送到哪個 receiver。route 是一棵樹：最上層的 route 接住全部告警，底下的子路由各自以 `matchers` 比對告警的標籤，告警從上往下找，落在第一個比中的子路由；都沒比中的留在最上層，送到最上層的 receiver。子路由加上 `continue: true` 時，比中之後還會繼續往下比，同一則告警可以同時送到兩個地方。

那個短網址服務依嚴重度分兩條路，另外替心跳開一條：

```yaml
route:
  receiver: ntfy-warning          # 沒有被子路由接走的（warning）送到這裡
  group_by: [alertname, host]     # 同一台主機的同一種告警合成一則通知
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  routes:
    - matchers: [alertname="Watchdog"]
      receiver: heartbeat
      group_by: [alertname]
      group_wait: 0s
      group_interval: 1m
      repeat_interval: 5m
    - matchers: [severity="critical"]
      receiver: ntfy-critical
      repeat_interval: 2h          # 沒寫的參數沿用上層的值

receivers:
  - name: ntfy-critical
    webhook_configs:
      - url_file: /etc/alertmanager/secrets/ntfy-critical.url
  - name: ntfy-warning
    webhook_configs:
      - url_file: /etc/alertmanager/secrets/ntfy-warning.url
  - name: heartbeat
    webhook_configs:
      - url_file: /etc/alertmanager/secrets/heartbeat.url
        send_resolved: false
```

`Watchdog` 那一條排在 `severity="critical"` 之前，因為比對按順序進行；心跳的 `severity` 是 `none`，這裡不會被 critical 搶走，但把最特定的條件排在前面，之後改標籤時不必回頭檢查順序。

路由寫完，用 `amtool` 確認一組標籤會落到哪個 receiver，不必等告警實際發生：

```sh
# 在放 alertmanager.yml 的目錄底下執行；標籤是要測的告警帶的標籤，每個標籤一個參數
docker run --rm -v "$PWD:/a" --entrypoint amtool prom/alertmanager:v0.34.1 \
  config routes test --config.file=/a/alertmanager.yml severity=critical alertname=HostDown
```

上面的設定測三組，`severity=critical alertname=HostDown` 回 `ntfy-critical`，`severity=warning alertname=HostDiskLow` 回 `ntfy-warning`，`alertname=Watchdog severity=none` 回 `heartbeat`。標籤要拆成各自的參數：把三組標籤放進 zsh 的變數再展開時，zsh 不切字，整串被當成一個參數，三組全部回最上層的 `ntfy-warning`，看起來像路由寫錯。

**分組與三個時間參數。** `group_by` 列出的標籤值相同的告警屬於同一組，一組送一則通知。三個時間參數都以組為單位：

- `group_wait`：一組的第一則告警進來之後，等多久才送第一次通知。等待期間陸續成立的同組告警合進同一則，一台主機停掉時同時成立的好幾條規則不會變成好幾則推播。實測合成的告警送進去之後 30 秒送出。
- `group_interval`：一組已經通知過之後，組裡有變化（新的告警加入、有告警解除）時，距離上次通知至少隔多久才再送。解除的通知因此最晚在恢復之後一個 `group_interval` 才到：實測停掉前台容器之後 2 分 39 秒收到 critical 通知，重新啟動之後 5 分鐘收到解除。
- `repeat_interval`：組裡沒有變化、告警一直成立時，隔多久再提醒一次。critical 設 2 小時、warning 設 12 小時，一直沒處理的問題不會被遺忘，也不會每 5 分鐘響一次。

把 receiver 從不送通知的換成實際送出通知的那一個時，已經在 Alertmanager 裡的告警會馬上補送：實測重新載入設定之後 3 秒，兩則原本就成立的 warning（磁碟剩餘空間、探測變慢）送到了 ntfy。第一次接上通知時，手機會先收到一批既有的告警。

## webhook：原生清單以外的通知服務

Alertmanager 0.34 原生支援的通知服務有 email、Slack、Microsoft Teams、Discord、Telegram、PagerDuty、Opsgenie、Pushover、Amazon SNS、Webex、Mattermost、Rocket.Chat、Jira、incident.io、VictorOps 與企業微信，各自是一種 `*_configs`。清單以外的服務走 `webhook_configs`：Alertmanager 對一個網址 POST 一份固定格式的 JSON，由對方決定怎麼呈現。

這份 JSON 以組為單位，一次通知一份。頂層的 `status` 是整組的狀態，組裡還有任何一則在成立就是 `firing`，全部解除才是 `resolved`；`groupLabels` 是分組用的標籤，`commonLabels` 與 `commonAnnotations` 是組裡每一則都相同的標籤與註解；`alerts` 是組裡每一則告警，各自帶 `status`、`labels`、`annotations` 與開始、結束的時間。整組的 `status` 是 `firing` 時，`alerts` 裡可能混著已經解除的，要只列出還在成立的就得逐則檢查各自的 `status`。

## 以 ntfy 推播到手機

ntfy 是一個以 HTTP 發佈、以 App 訂閱的推播服務：對 `https://ntfy.sh/<topic>` POST 一段文字，訂閱了這個 topic 的手機就收到一則通知。可以用公開的 ntfy.sh，也可以自己架。Alertmanager 沒有原生的 ntfy 支援，所以用 webhook 送過去，但 webhook 送的是 JSON，直接 POST 到 topic，手機上看到的是一整段 JSON。

ntfy 的訊息模板解決這件事：網址加上 `tpl=yes`，ntfy 把收到的 JSON 當成資料，以 Go 的模板產生標題（`t`）、內容（`m`）與優先度（`p`）。

```text
https://ntfy.sh/<topic>?tpl=yes
  &t=[{{.status}}] {{.commonLabels.alertname}} {{.commonLabels.host}}
  &m={{if eq .status "resolved"}}已解除{{else}}{{range .alerts}}{{if eq .status "firing"}}{{.annotations.summary}}\n{{end}}{{end}}{{end}}
  &p={{if eq .status "resolved"}}default{{else}}urgent{{end}}
```

上面為了閱讀分行，實際是一行，模板要經過 URL 編碼（`{` 寫成 `%7B`、空白寫成 `+`）；`<topic>` 換成自己的 topic。這三個模板的作用：

- **標題**寫狀態、規則名稱與主機，鎖定畫面上只看標題就知道是哪台主機的哪一種問題，例如 `[firing] HostDown app-2`。
- **內容**在成立時逐一列出組裡還在成立的告警的 `summary`；解除時寫「已解除」。解除時不沿用 `summary`，因為 `summary` 是告警最後一次成立時算出的文字，實測解除通知裡寫著「portal 已有 2m 55s 沒被看到」，讀起來像問題還在。
- **優先度**依狀態切換。ntfy 的 `urgent`（5）會讓手機響鈴，`default`（3）是一般通知。只用固定的 `priority=urgent` 時，解除的通知也響鈴；實測換成模板之後，成立時是 5、解除時是 3。warning 那一條改成成立 `default`、解除 `low`。

模板裡的欄位名稱是 JSON 的鍵，小寫開頭（`.status`、`.commonLabels`）；Alertmanager 自己的通知模板（例如 Slack 的 `title`）用的是大寫開頭的 `.Status`、`.CommonLabels`，兩者在同一份設定的不同位置出現時不能互抄。`p` 的模板在 ntfy 2.30 上實測可用。ntfy 也內建一個 `template=alertmanager`，開箱即用，而它的標題帶 emoji、內容讀 `instance` 標籤；以 `host` 區分主機的設定裡，那一欄顯示 `<no value>`。

ntfy 的 topic 名稱本身就是讀取權限：公開的 ntfy.sh 上，知道 topic 名稱的人都能訂閱，收到這些告警。所以 topic 取一個猜不到的長名稱，而且不進版本控制，放法見〈私密的網址放在檔案裡〉。

## 私密的網址放在檔案裡

Alertmanager 的設定檔不展開環境變數，`${NTFY_TOPIC}` 會原封不動地被當成網址的一部分。含有私密值的欄位因此各有一個讀檔案的版本：webhook 的 `url_file`、email 的 `smtp_auth_password_file`、Slack 的 `api_url_file`。設定檔進版本控制，私密的檔案放在另一個不進版本控制的目錄，與設定檔一起掛進容器。

那個短網址服務的做法是 `alertmanager/secrets/` 列在 `.gitignore`，另外提交一份 `secrets.example/`，內容是 topic 換成 `CHANGE-ME` 的網址，模板的部分已經編碼好；部署時複製一份、只換 topic。

`url_file` 在每次送通知時才讀：實測改了檔案內容之後，下一則通知就用新的網址，不必重新載入 Alertmanager。檔案不存在時，`amtool check-config` 照樣通過、Alertmanager 照樣啟動，失敗發生在送通知的那一刻，要靠下方〈通知送不出去的偵測〉發現。

## email 與 Slack

email 的 SMTP 伺服器寫在 `global`，所有 `email_configs` 共用：

```yaml
global:
  smtp_smarthost: smtp.example.com:587       # SMTP 伺服器與連接埠
  smtp_from: alertmanager@example.com
  smtp_auth_username: alertmanager
  smtp_auth_password_file: /etc/alertmanager/secrets/smtp-password
receivers:
  - name: mail
    email_configs:
      - to: oncall@example.com
        send_resolved: true                 # email 預設不送解除的通知
```

`smtp_require_tls` 預設是 `true`，伺服器不支援 STARTTLS 時 Alertmanager 拒絕送出；本機以 Mailpit 測試時設成 `false`，信件以 `[FIRING:1] HostDiskLow app-1 (warning)` 為主旨送達。解除的通知是否送出各 integration 的預設不同：webhook 預設送，email 與 Slack 預設不送，要寫 `send_resolved: true`。

Slack 用 incoming webhook 的網址，標題與內容用 Alertmanager 自己的模板語法：

```yaml
receivers:
  - name: slack
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/slack-webhook.url
        channel: "#alerts"
        send_resolved: true
        title: '[{{ .Status }}] {{ .CommonLabels.alertname }} {{ .CommonLabels.host }}'
        text: '{{ range .Alerts.Firing }}{{ .Annotations.summary }}{{ "\n" }}{{ end }}'
```

`.Alerts.Firing` 只取組裡還在成立的告警，作用等同 ntfy 那一段模板裡逐則檢查 `status` 的寫法。這一段只以 `amtool check-config` 檢查過語法，沒有實際送到 Slack。

## Watchdog：告警鏈本身的心跳

上面的通知全部要 Prometheus 在評估規則、Alertmanager 在送通知才發得出來。Prometheus 停掉、Alertmanager 停掉、整台監控主機停電時，沒有任何告警成立，手機上什麼都沒有，和一切正常時看起來一樣。這種故障要由監控主機以外的地方發現：讓告警鏈持續送出一個「我還活著」的訊號，由外部的服務在訊號停止時通知。這個做法叫 dead man's switch，背後的推導見 [Watchdog / dead man's switch](/backend/04-observability/cases/watchdog-dead-mans-switch/)。

訊號是一條永遠成立的規則：

```yaml
- alert: Watchdog
  expr: vector(1)                 # 沒有任何輸入也成立
  labels: {severity: none, scope: monitoring}
  annotations:
    summary: "告警鏈的心跳：Prometheus 在評估規則、Alertmanager 在送通知"
```

路由把它送到心跳服務（例如 healthchecks.io，對它的 ping 網址發一個請求就算一次心跳），`group_wait: 0s` 讓它一成立就送，`repeat_interval: 5m` 讓它每 5 分鐘再送一次；它永遠不會解除，所以 `send_resolved: false`。實測兩次心跳相隔 5 分 01 秒。心跳服務那邊把預期的週期設 5 分鐘、寬限 5 分鐘，超過 10 分鐘沒收到就由心跳服務自己的通知管道（例如 email）通知。這條路徑上的判斷全部發生在監控主機以外，監控主機整台停掉時它照樣運作。

心跳的 `group_interval` 要比 `repeat_interval` 短。Alertmanager 只在每個 `group_interval` 的時間點檢查要不要重送，`group_interval` 沿用上層的 5 分鐘時，重送會落在 5 分鐘的倍數上，任何一次稍晚錯過檢查點就變成 10 分鐘，正好碰到心跳服務的寬限上限。

## 通知送不出去的偵測

心跳涵蓋的是告警鏈停掉；告警鏈在運作而通知送不出去是另一種情形：網址打錯、私密檔沒放、通知服務拒收或連不上。這時 Alertmanager 在日誌寫下 `Notify for alerts failed`，並遞增 `alertmanager_notifications_failed_total`，以 `integration`（webhook、email、slack）與 `reason` 分開計數。實測拿掉 critical 的網址檔之後送一則 critical 告警，日誌是 `notify retry canceled due to unrecoverable error`，計數在 `reason="other"` 加 1，這一次通知不重試。

Prometheus 讀得到 Alertmanager 自己的指標，所以這件事可以寫成一條規則：

```yaml
- alert: AlertmanagerNotificationsFailing
  expr: sum by (host, integration) (increase(alertmanager_notifications_failed_total[10m])) > 0
  for: 5m
  labels: {severity: warning, scope: monitoring}
```

這條規則送出的告警，同樣要經過 Alertmanager 的某一個 receiver，所以它能不能送到，取決於哪一條管道壞了。它是 warning，走 warning 的 topic：critical 的管道壞掉時它送得出來，實測送失敗之後 5 分 41 秒，它出現在 warning 的 topic 上（`for: 5m` 加上 `group_wait` 的 30 秒）；warning 的管道本身壞掉時它送不出來，只留在 Alertmanager 的頁面與日誌。兩個 topic 都在同一個 ntfy 服務上，ntfy 整個連不上時兩者一起斷，而心跳走的是另一個服務，照常送達，這種故障沒有任何通知。要補上這個缺口，需要一條不經過 ntfy 的路，例如把這條規則送到 email，或者由心跳服務另外探測 ntfy。

## 驗證：在單機上重現的結果

以下是在那個短網址服務上，以本機的 ntfy 容器代替 ntfy.sh 量到的結果，每一項對應上面一個設定：

- `amtool config routes test` 對三組標籤分別回 `ntfy-critical`、`ntfy-warning`、`heartbeat`。
- 重新載入之後 3 秒，兩則既有的 warning 送到 warning 的 topic。
- 停掉前台容器之後 2 分 39 秒，`EndpointDown` 與 `ContainerStopped` 以優先度 5 送到 critical 的 topic；重新啟動之後 5 分鐘收到兩則解除。
- 合成的 critical 告警送進 Alertmanager 之後 30 秒送出（優先度 5），解除之後 5 分鐘送出「已解除」（優先度 3）。
- Watchdog 兩次送達相隔 5 分 01 秒。
- 拿掉 critical 的網址檔之後，critical 告警送不出去，`alertmanager_notifications_failed_total{reason="other"}` 加 1，`AlertmanagerNotificationsFailing` 經由 warning 的 topic 送達。
- email 經由 Mailpit 送達，主旨 `[FIRING:1] HostDiskLow app-1 (warning)`。
- 規則的單元測試（promtool）涵蓋 Watchdog 沒有輸入也成立、通知失敗依 `integration` 分開且 10 分鐘內沒有新的失敗就不再成立；把規則的門檻從 `> 0` 改成 `> 1`，測試失敗。

沒有驗證的部分：公開的 ntfy.sh 與手機 App 的實際推播、healthchecks.io 在心跳停止時的通知、真正的 SMTP 伺服器，以及 Slack。

## 延伸閱讀：告警規則、抑制與觀測的共命運

- 哪些條件值得告警、`severity` 怎麼分、主機飽和時怎麼抑制它造成的症狀，見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)；抑制本身的概念見 [Alert Inhibition](/backend/knowledge-cards/alert-inhibition/)。
- 告警太多、推播響到沒人看時，`repeat_interval` 與分組之外的處理見 [Alert Fatigue](/backend/knowledge-cards/alert-fatigue/)。
- 監控和被監控的對象一起壞掉的各種形態，以及心跳以外的頻外訊號，見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。
- 多台主機時 `group_by` 與抑制規則為什麼要帶 `host`，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/)。
