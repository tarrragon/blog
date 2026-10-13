---
title: "Alertmanager 的通知管道：路由樹與分組、webhook 與 ntfy、email 與 Slack、私密網址的檔案、心跳與通知送不出去的偵測"
date: 2026-10-13
description: "Alertmanager 從只在網頁上看告警，到依嚴重度送到手機與信箱：路由樹怎麼決定一則告警送到哪裡、分組與 group_wait、group_interval、repeat_interval 各控制什麼，以 webhook 接 ntfy 推播與它的訊息範本，email 與 Slack 的設定，私密網址為什麼要放在檔案裡（設定檔不展開環境變數），以及 Watchdog 心跳與通知送不出去時的偵測"
weight: 17
tags: ["backend", "observability", "vendor", "prometheus", "alertmanager"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列，接在 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 之後：那一篇的 Alertmanager 只有一個不送任何通知的 receiver，告警只出現在它的網頁上。

這一篇整理讓 Alertmanager 把告警送出去的設定：路由、receiver、私密值的放法，以及告警鏈本身停掉或送不出去時怎麼發現。哪些條件該告警、依原因抑制的規則見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)，這裡從「告警已經進到 Alertmanager」開始。文中的設定取自一個短網址服務的監控（Alertmanager 0.34.1、Prometheus 3.15.0），通知服務在本機以 ntfy 2.30 與 Mailpit（攔截郵件的測試用 SMTP 伺服器）的容器代替，文中的時間與行為都是在這套本機環境裡量到的。文中的「合成告警」指以 Alertmanager 的 API 直接送進去、只帶幾個標籤的測試告警，用來在不停掉任何服務的情況下觀察通知。

## 路由樹：一則告警送到哪個 receiver

receiver 是一組通知設定的名字，裡面寫要送到哪裡（ntfy、信箱、Slack 頻道）；route 決定哪些告警送到哪個 receiver。route 是一棵樹：最上層的 route 接住全部告警，底下的子路由各自以 `matchers` 比對告警的標籤，Alertmanager 由上往下比，告警落在第一個符合的子路由；一條都不符合的留在最上層，送到最上層的 receiver。子路由加上 `continue: true` 時，符合之後還會繼續往下比，同一則告警可以同時送到兩條符合的子路由；後面的子路由都不符合時，它不會再回到最上層的 receiver。

下面的設定依嚴重度分兩條路，另外替心跳開一條。心跳是一條永遠成立的 `Watchdog` 告警，持續送到監控主機以外的心跳監看服務（接收心跳、在心跳中斷時發出通知的外部服務，例如 healthchecks.io），用來證明告警鏈還在運作，規則與心跳監看服務的設定見〈Watchdog：告警鏈本身的心跳〉：

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

`Watchdog` 那一條排在 `severity="critical"` 之前，因為比對按順序進行；心跳的 `severity` 是 `none`，在這份設定裡不會被 critical 那條子路由接走，但把最特定的條件排在前面，之後改標籤時不必回頭檢查順序。

路由寫完，用 `amtool` 確認一組標籤會落到哪個 receiver，不必等告警實際發生：

```sh
# 在放 alertmanager.yml 的目錄底下執行；標籤是要測的告警帶的標籤，每個標籤一個參數
docker run --rm -v "$PWD:/a" --entrypoint amtool prom/alertmanager:v0.34.1 \
  config routes test --config.file=/a/alertmanager.yml severity=critical alertname=HostDown
```

上面的設定測三組，`severity=critical alertname=HostDown` 回 `ntfy-critical`，`severity=warning alertname=HostDiskLow` 回 `ntfy-warning`，`alertname=Watchdog severity=none` 回 `heartbeat`。amtool 把每一個參數當成一個標籤比對，所以標籤要拆成各自的參數；整串標籤被當成一個參數時（例如放進 zsh 的變數再展開，zsh 不切字），路由一律落到最上層，同時 stderr 印出 matchers 解析器的警告。

## 分組與 group_wait、group_interval、repeat_interval

`group_by` 列出的標籤值相同的告警屬於同一組，一組送一則通知。三個時間參數都以組為單位：

- `group_wait`：一組的第一則告警進來之後，等多久才送第一次通知。等待期間陸續成立的同組告警合進同一則，一台主機停掉時同時成立的好幾條規則不會變成好幾則推播。實測合成告警送進去之後 30 秒送出。
- `group_interval`：一組已經通知過之後，組裡有變化（新的告警加入、有告警解除）時，距離上次通知至少隔多久才再送。解除的通知因此最晚在恢復之後一個 `group_interval`（這份設定是 5 分鐘）才到：實測停掉前台容器再重新啟動之後 5 分鐘收到解除。
- `repeat_interval`：組裡沒有變化、告警一直成立時，隔多久再提醒一次。critical 設 2 小時、warning 設 12 小時，一直沒處理的問題不會被遺忘，也不會每 5 分鐘響一次。

`group_wait` 30 秒與 `group_interval` 5 分鐘是 Alertmanager 的預設值（`repeat_interval` 的預設是 4 小時）；2 小時與 12 小時是這個服務依值班的回應時間選的。重送的計時與靜音存在 Alertmanager 的 `--storage.path` 目錄裡，這個目錄沒有掛 volume 時，容器重建之後所有成立中的組會立刻重送一次，靜音也會消失。

critical 與 warning 分成兩個 topic，是讓只想收 critical 的人只訂一個，也讓 warning 可以單獨靜音。這份設定把 warning 全天推送、以較低的優先度降低打擾；[dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/) 把 warning 定義成工作時間處理，要照那個定義，以 Alertmanager 的 `time_intervals` 定義工作時段，並在 warning 那條路由加上 `active_time_intervals`，工作時段以外的 warning 就不送（這一種沒有實測）。`severity` 是 `info` 或 `none` 的告警（Watchdog 以外）沒有子路由接走時會落到最上層的 warning，要另開一條送到不通知的 receiver。

把 receiver 從不送通知的換成實際送出通知的那一個時，已經在 Alertmanager 裡的告警會馬上補送：實測重新載入設定之後 3 秒，兩則原本就成立的 warning（磁碟剩餘空間、探測變慢）送到了 ntfy。第一次接上通知時，手機會先收到一批既有的告警。

## webhook：Alertmanager 原生支援以外的通知服務

Alertmanager 0.34 原生支援的通知服務有 email、Slack、Microsoft Teams、Discord、Telegram、PagerDuty、Opsgenie、Pushover、Amazon SNS、Webex、Mattermost、Rocket.Chat、Jira、incident.io、VictorOps 與企業微信，各自是一種 `*_configs`。清單以外的服務走 `webhook_configs`（[webhook](/backend/knowledge-cards/webhook/)）：Alertmanager 預設對一個網址 POST 一份固定格式的 JSON，由對方決定怎麼呈現（0.34 另有自訂內容的 `payload` 欄位，官方標註自行承擔風險，這裡不用）。所以對方要讀得懂這份 JSON：ntfy 以訊息範本讀它（見下一節），自己寫的轉接程式也可以。只接受自己格式的 API（例如 LINE 的 Messaging API）不能直接填成 webhook 的網址，中間要放一個轉接服務，把這份 JSON 轉成對方的格式。

這份 JSON 以組為單位，一次通知一份。頂層的 `status` 是整組的狀態，組裡還有任何一則在成立就是 `firing`，全部解除才是 `resolved`；`groupLabels` 是分組用的標籤，`commonLabels` 與 `commonAnnotations` 是組裡每一則都相同的標籤與註解；`alerts` 是組裡每一則告警，各自帶 `status`、`labels`、`annotations` 與開始、結束的時間。組裡有的告警已經解除、有的還在成立時，整組的 `status` 仍是 `firing`，而 `alerts` 裡混著兩種，要只列出還在成立的就得逐則檢查各自的 `status`。

## 以 ntfy 推播到手機

ntfy 是一個以 HTTP 發佈、以 App 訂閱的推播服務：對 `https://ntfy.sh/<topic>` POST 一段文字，訂閱了這個 topic 的手機就收到一則通知。可以用公開的 ntfy.sh，也可以自己架。告警的標題與內容帶著主機名與錯誤描述送到 ntfy 的伺服器，資料不能離開組織環境時用自架的 ntfy，心跳監看服務同理。運作方式與兩者的差別見 [ntfy：推送通知服務怎麼運作、公共站 vs 自架](/linux/debug/ntfy-push-notification-service/)。Alertmanager 沒有原生的 ntfy 支援，所以以 webhook 送過去；webhook 送的是 JSON，Alertmanager 直接把它 POST 到 topic 時，手機上看到的是一整段 JSON。

ntfy 的訊息範本把 JSON 轉成可讀的通知：網址加上 `tpl=yes`，ntfy 把收到的 JSON 當成資料，以 Go 的範本語法產生標題（`t`）、內容（`m`）與優先度（`p`）。critical 用的範本如下，為了閱讀分行：

```text
https://ntfy.sh/<topic>?tpl=yes
  &t=[{{.status}}] {{.commonLabels.alertname}} {{.commonLabels.host}}
  &m={{if eq .status "resolved"}}已解除{{else}}{{range .alerts}}{{if eq .status "firing"}}{{.annotations.summary}}\n{{end}}{{end}}{{end}}
  &p={{if eq .status "resolved"}}default{{else}}urgent{{end}}
```

這三個範本的作用：

- **標題**寫狀態、規則名稱與主機，鎖定畫面上只看標題就知道是哪台主機的哪一種問題，例如 `[firing] HostDown app-2`。
- **內容**在成立時逐一列出組裡還在成立的告警的 `summary`；解除時寫「已解除」。解除時不沿用 `summary`，因為 `summary` 是告警最後一次成立時算出的文字，實測解除通知裡寫著「portal 已有 2m 55s 沒被看到」，讀起來像問題還在。
- **優先度**依狀態切換。ntfy 的優先度決定手機的提示強度：`urgent`（5）長時間震動並跳出橫幅，`default`（3）短震動加提示音，`low`（2）不震動也不出聲。只用固定的 `priority=urgent` 時，解除的通知也以最高強度跳出；實測換成範本之後，成立時是 5、解除時是 3。warning 的網址把 `p` 的範本改成成立時 `default`、解除時 `low`，所以 warning 成立時手機仍會短震動並出聲。

實際寫進檔案的網址是一行，每個參數都經過 URL 編碼。編碼有兩個作用：網址裡不能直接放空白、引號、中文這些字元；而 Alertmanager 0.34 會先以自己的範本語法處理 `url` 與 `url_file` 的內容，沒編碼的 `{{.status}}` 會被它先解析而送出失敗或變成 `<no value>`，編碼成 `%7B%7B` 之後才原樣送到 ntfy。手寫編碼容易漏字元，以腳本產生比較可靠：

```python
# ntfy_url.py：印出 ntfy 的網址
# 用法：python3 ntfy_url.py <伺服器網址與 topic> <成立時的優先度> <解除時的優先度>
import sys
from urllib.parse import quote_plus

base, firing_p, resolved_p = sys.argv[1:4]
t = "[{{.status}}] {{.commonLabels.alertname}} {{.commonLabels.host}}"
m = ('{{if eq .status "resolved"}}已解除{{else}}{{range .alerts}}'
     '{{if eq .status "firing"}}{{.annotations.summary}}\n{{end}}{{end}}{{end}}')
p = '{{if eq .status "resolved"}}' + resolved_p + '{{else}}' + firing_p + '{{end}}'
print(f"{base}?tpl=yes&t={quote_plus(t)}&m={quote_plus(m)}&p={quote_plus(p)}", end="")
```

```sh
# 第一個引數換成自己的 ntfy 伺服器與 topic；輸出的路徑換成自己放私密檔的目錄
python3 ntfy_url.py https://ntfy.sh/<topic> urgent default > secrets/ntfy-critical.url
python3 ntfy_url.py https://ntfy.sh/<topic> default low > secrets/ntfy-warning.url
```

範本裡的欄位名稱是 JSON 的鍵，小寫開頭（`.status`、`.commonLabels`）；Alertmanager 自己的通知範本（例如 Slack 的 `title`）用的是大寫開頭的 `.Status`、`.CommonLabels`，兩者在同一份設定的不同位置出現時不能互抄。`p` 的範本在 ntfy 2.30 上實測可用。ntfy 也內建一個 `template=alertmanager`，開箱即用，而它的標題帶 emoji、內容讀 `instance` 標籤；以 `host` 區分主機的設定裡，那一欄顯示 `<no value>`。

ntfy 的 topic 名稱本身就是讀取權限：公開的 ntfy.sh 上，知道 topic 名稱的人都能訂閱，收到這些告警。所以 topic 取一個猜不到的長名稱，而且不進版本控制，放法見〈私密網址的存放：設定檔不展開環境變數，改用讀檔案的 `*_file` 欄位〉。

## 私密網址的存放：設定檔不展開環境變數，改用讀檔案的 `*_file` 欄位

Alertmanager 的設定檔不展開環境變數，`${NTFY_TOPIC}` 會原封不動地被當成網址的一部分。含有私密值的欄位因此各有一個讀檔案的版本：webhook 的 `url_file`、email 的 `smtp_auth_password_file`、Slack 的 `api_url_file`。設定檔進版本控制，私密的檔案放在一個不進版本控制的目錄。[單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 把整個 `infra/observability/alertmanager` 目錄掛到容器的 `/etc/alertmanager`，所以私密的檔案放在它底下的 `secrets/`，容器裡就出現在 `/etc/alertmanager/secrets/`；只掛單一設定檔的寫法要另加一行掛這個目錄。

`secrets/` 列進 `.gitignore`，旁邊提交一份 `secrets.example/`，內容是把 topic 換成 `CHANGE-ME` 的網址。範例裡的範本已經編碼好，部署時複製一份、只換 topic，不必重新產生網址。

`url_file` 在每次送通知時才讀：實測改了檔案內容之後，下一則通知就用新的網址，不必重新載入 Alertmanager。檔案不存在時，`amtool check-config` 照樣通過、Alertmanager 照樣啟動，失敗發生在送通知的那一刻，要靠下方〈通知送不出去的偵測〉發現。

## email 與 Slack

下面兩段的 receiver 併進主設定裡已有的 `receivers` 清單，不能整段附加在檔案後面：同一份設定出現兩個 `receivers` 時，`amtool check-config` 回 `field receivers already set`。receiver 也要有一條子路由指到它才會被用到，例子見〈通知送不出去的偵測〉的末段。

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

`smtp_require_tls` 預設是 `true`，伺服器不支援 STARTTLS 時 Alertmanager 拒絕送出；本機以 Mailpit 測試時設成 `false`，一則只帶 `alertname`、`host`、`severity` 的合成告警以 `[FIRING:1] HostDiskLow app-1 (warning)` 為主旨送達：主旨依序是狀態與告警數、分組標籤的值，括號裡是組內共同而不屬於分組的標籤值，所以帶著更多標籤的真實告警，括號裡會多出那些值。解除的通知是否送出，各通知類型（integration，例如 webhook、email）的預設不同：webhook 預設送，email 與 Slack 預設不送，要寫 `send_resolved: true`。真正的 SMTP 伺服器這裡沒有測過。

Slack 用 incoming webhook 的網址，標題與內容用 Alertmanager 自己的範本語法：

```yaml
receivers:
  - name: slack
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/slack-webhook.url
        channel: "#alerts"
        send_resolved: true
        title: '[{{ .Status }}] {{ .CommonLabels.alertname }} {{ .CommonLabels.host }}'
        text: '{{ if eq .Status "resolved" }}已解除{{ else }}{{ range .Alerts.Firing }}{{ .Annotations.summary }}{{ "\n" }}{{ end }}{{ end }}'
```

`.Alerts.Firing` 只取組裡還在成立的告警，作用等同 ntfy 那一段範本裡逐則檢查 `status` 的寫法；整組解除時它是空的，所以和 ntfy 一樣另外寫「已解除」。這一段只以 `amtool check-config` 檢查過語法，沒有實際送到 Slack。

## Watchdog：告警鏈本身的心跳

ntfy、email 與 Slack 的通知全部要 Prometheus 在評估規則、Alertmanager 在送通知才發得出來。Prometheus 停掉、Alertmanager 停掉、整台監控主機停電時，沒有任何告警成立，手機上什麼都沒有，和一切正常時看起來一樣。這種故障要由監控主機以外的地方發現：讓告警鏈持續送出一個「我還活著」的訊號，由外部的服務在訊號停止時通知（這類從監控主機以外發出的訊號叫 [頻外訊號](/backend/knowledge-cards/out-of-band-signal/)）。這個做法叫 dead man's switch，背後的推導見 [Watchdog / dead man's switch](/backend/04-observability/cases/watchdog-dead-mans-switch/)。

訊號是一條永遠成立的規則：

```yaml
- alert: Watchdog
  expr: vector(1)                 # 沒有任何輸入也成立
  labels: {severity: none, scope: monitoring}
  annotations:
    summary: "告警鏈的心跳：Prometheus 在評估規則、Alertmanager 在送通知"
```

心跳監看服務（例如 healthchecks.io）替每一個檢查發一個 ping 網址，收到一個請求就算一次心跳。這個網址寫進 `heartbeat.url`，Alertmanager 以 webhook 對它 POST，就是一次心跳。心跳那條子路由把 `group_wait` 設成 `0s`，Alertmanager 在 Watchdog 一成立就送出；`repeat_interval: 5m` 讓 Alertmanager 每 5 分鐘重送一次；它永遠不會解除，所以 `send_resolved: false`。實測兩次心跳相隔 5 分 01 秒。在心跳監看服務上把這個檢查的預期週期設 5 分鐘、寬限 5 分鐘，超過 10 分鐘沒收到，心跳監看服務就經由它自己的通知管道（例如 email）通知。這條路徑上的判斷全部發生在監控主機以外，監控主機整台停掉時它照樣運作。心跳監看服務在心跳停止時實際發出的通知，這裡沒有測過。

時間參數的條件是：兩次心跳之間最長的間隔，要小於心跳監看服務的週期加寬限。Alertmanager 只在每個 `group_interval` 的時間點檢查要不要重送，所以最長的間隔約是 `repeat_interval` 加一個 `group_interval`。這份設定是 5 分加 1 分，小於 10 分鐘；`group_interval` 沿用上層的 5 分鐘時，重送落在 5 分鐘的倍數上，任何一次稍晚錯過檢查點就變成 10 分鐘，正好碰到心跳監看服務的上限，所以心跳的 `group_interval` 要比 `repeat_interval` 短。

## 通知送不出去的偵測

心跳涵蓋的是告警鏈停掉；告警鏈在運作而通知送不出去是另一種情形：網址打錯、私密檔沒放、通知服務拒收或連不上。這時 Alertmanager 在日誌寫下 `Notify for alerts failed`，並遞增 `alertmanager_notifications_failed_total`，以 `integration`（webhook、email、slack）與 `reason` 分開計數。實測拿掉 critical 的網址檔之後送一則 critical 告警，日誌是 `notify retry canceled due to unrecoverable error`，計數在 `reason="other"` 加 1，這一次通知不重試。

Prometheus 讀得到 Alertmanager 自己的指標，所以這件事可以寫成一條規則：

```yaml
- alert: AlertmanagerNotificationsFailing
  expr: sum by (host, integration) (increase(alertmanager_notifications_failed_total[10m])) > 0
  for: 5m
  labels: {severity: warning, scope: monitoring}
  annotations:
    summary: "Alertmanager 經由 {{ $labels.integration }} 送通知失敗，10 分鐘內 {{ $value | printf \"%.0f\" }} 次"
```

`summary` 不能省：ntfy 範本的內容欄讀的是它，沒有的話推播內容只剩 `<no value>`。這條規則與 Watchdog 以 promtool 的單元測試檢查：測試檔餵進一條失敗計數的序列，promtool 確認 Watchdog 沒有任何輸入也成立、失敗的告警帶著 `integration` 標籤、10 分鐘內沒有新的失敗就不再成立。測試本身也要驗：把規則的門檻從 `> 0` 改成 `> 1`，測試應該失敗，實測確實失敗；改壞規則而測試照樣通過，代表測試沒有在檢查那個門檻。

這條規則送出的告警，同樣要經過 Alertmanager 的某一個 receiver，所以它能不能送到，取決於哪一條管道壞了。它是 warning，走 warning 的 topic：critical 的管道壞掉時它送得出來，實測送失敗之後 5 分 41 秒，它出現在 warning 的 topic 上（`for: 5m` 加上 `group_wait` 的 30 秒）；warning 的管道本身壞掉時它送不出來，只留在 Alertmanager 的頁面與日誌。兩個 topic 都在同一個 ntfy 服務上，ntfy 整個連不上時兩者一起斷，而心跳走的是另一個服務，照常送達，這種故障不會產生任何通知。只有一條通知管道的設定裡更是如此，這條規則永遠走那條壞掉的管道。

要補上這個缺口，這條規則要另走一條不經過 ntfy 的路。一種是在路由裡替它開子路由，送一份到〈email 與 Slack〉裡的 `mail` receiver，同時保留 ntfy 那一份，排在 critical 那一條之前：

```yaml
    - matchers: [alertname="AlertmanagerNotificationsFailing"]
      receiver: mail
      continue: true                 # 送 mail 之後繼續往下比
    - matchers: [alertname="AlertmanagerNotificationsFailing"]
      receiver: ntfy-warning         # 後面的子路由都不符合時不會回到最上層，所以明寫
```

email 本身送不出去時，送 email 的那一份照樣失敗，這一類由 ntfy 那一份或心跳監看服務發現。

另一種是送到心跳監看服務：在 healthchecks.io 上另開一個檢查，它的 ping 網址加上 `/fail` 就是回報失敗的網址，以一個 `send_resolved: false` 的 webhook receiver 送到那裡，由心跳監看服務自己的管道通知。不另開檢查、用心跳的那一個時，下一次 Watchdog 心跳會在 5 分鐘內把它翻回正常。這一種沒有實測。

## 延伸閱讀：告警規則、抑制與觀測的共命運

- 哪些條件值得告警、`severity` 怎麼分、主機飽和時怎麼抑制它造成的症狀，見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)；抑制本身的概念見 [Alert Inhibition](/backend/knowledge-cards/alert-inhibition/)。
- 告警太多、推播響到沒人看時，`repeat_interval` 與分組之外的處理見 [Alert Fatigue](/backend/knowledge-cards/alert-fatigue/)。
- 監控和被監控的對象一起壞掉的各種形態，以及心跳以外的頻外訊號，見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。
- 多台主機時 `group_by` 與抑制規則為什麼要帶 `host`，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 的〈代表主機的 host 標籤〉。
