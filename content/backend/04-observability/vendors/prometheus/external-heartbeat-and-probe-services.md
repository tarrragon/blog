---
title: "第三方心跳監看與外部探測服務：挑選條件、healthchecks 的 ping 與 /fail、Alertmanager 的接法與演練"
date: 2026-10-14
description: "以第三方服務當作監控主機失效域以外的觀察者：心跳監看服務的挑選條件與送出的告警資料留在哪裡，healthchecks 的 ping 網址、週期與寬限、/fail 與自架和託管版的回應差異，Alertmanager 送心跳與送失敗通知的 receiver 與路由順序、驗收與暫停，停掉 Alertmanager 的演練，以及外部探測服務的挑選條件"
weight: 18
tags: ["backend", "observability", "vendor", "prometheus", "alertmanager", "monitoring"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列。只有一台主機時為什麼需要失效域以外的觀察者、心跳監看與外部探測各回答什麼問題，見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)；手上有另一個失效域的主機、要自己架觀察者時的條件，見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/) 的〈兩台主機互相監看〉，本篇的 ping 網址、`/fail` 與路由在自架時同樣適用。

以第三方服務做心跳監看（dead man's switch）與外部探測時，挑選服務要看的條件，以及把 Alertmanager 接到心跳監看服務的設定，整理在這一篇。第三方服務提供的是失效域以外的位置，以及它自己的存活由業者維運。設定接在 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 那份路由與 `Watchdog` 規則之上，還沒有 Alertmanager 的從 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 起步。心跳監看以 healthchecks 為例：它是開源專案，有託管版 healthchecks.io，也可以自架。文中的行為以自架的 healthchecks 4.4 與 Alertmanager 0.34.1 在 macOS 的 OrbStack 上實測，通知信寄到本機的 Mailpit；本篇沒有實際接過託管版 healthchecks.io，兩者的網址結構與判斷方式相同，回應碼的差異寫在下文，通知管道與方案限制以託管版的文件為準。外部探測服務本篇只寫挑選條件，沒有實際接過任何一家。

## 心跳監看服務的挑選條件

**服務本身跑在哪裡。** 心跳監看服務與自己的主機在同一個雲端業者、同一個區域時，那家業者的區域故障會讓兩者一起停：主機停了，而本來要通知的監看服務也停了。查服務的文件或「關於」頁寫的業者與地區（healthchecks.io 寫在它的 about 頁），與自己主機的業者和區域比對；只寫了業者、沒寫地區時，至少要業者不同。

**通知管道。** 心跳中斷的通知由服務自己的管道送出（email、簡訊、電話、手機 App、Slack 這類整合）。這條管道不能經過自己的監控主機：心跳監看服務以 webhook 把通知送回監控主機上的 ntfy 時，監控主機停掉的那一刻，這條通知也送不到。收通知的人與 Alertmanager 通知的人相同，是會處理的人。

**判斷方式。** 服務要能讓每個檢查項目各自設定週期（period，預期的心跳間隔）與寬限（grace time，容許的延遲），最後一次心跳之後超過兩者相加就判定中斷。healthchecks 另外支援以 cron 表示式描述預期時間，給排程工作用；Alertmanager 的心跳是固定間隔，用週期加寬限就夠。

**回報失敗的端點。** 除了「我還在」，服務要能接受「出事了」。healthchecks 的 ping 網址加上 `/fail` 就是回報失敗，收到就立刻判定失敗並通知，不必等週期。Alertmanager 偵測到通知送不出去時，透過這個端點把「通知送不出去」這件事交給心跳監看服務，由它自己的管道通知。

**送出去的資料留在哪裡。** Alertmanager 的 webhook 送出的是整份告警 JSON：標籤、註解（annotations），以及每則告警的 `generatorURL`。`generatorURL` 是 Prometheus 的網址，Prometheus 沒有設 `--web.external-url` 時取主機名，在容器裡就是容器 ID。healthchecks 會把每次 ping 的請求本文存下來（上限由自架版的 `PING_BODY_LIMIT` 設定，託管版寫在它的 API 文件），所以這些內容會存在服務那一邊。Watchdog 那一則的內容固定且少；送失敗通知的那一則帶著失敗的通知類型與主機標籤。告警內容不能離開組織時，改用自架的監看服務，或只送不帶本文的心跳請求（兩種做法見 4.28 的〈觀察者的位置：第三方服務、另一個失效域的主機（含互相監看）與另一個業者的排程平台〉）。

**方案的限制。** 免費方案通常限制檢查項目的數量、通知管道的種類與保留的歷史，各家的數字常變，選用時看服務當下公布的方案。心跳監看至少要兩個檢查項目，理由見下方〈Alertmanager 的 receiver 與路由：心跳與送失敗的通知〉。

## healthchecks 的 ping 網址、週期、寬限與 /fail

在 healthchecks 建立一個檢查項目（check），它會產生一個專屬的 ping 網址，路徑是一個 UUID（託管版的網址形如 `https://hc-ping.com/<UUID>`，自架版是 `SITE_ROOT` 環境變數設定的網站網址底下的 `/ping/<UUID>`）。對這個網址送一個 GET 或 POST 就算一次心跳，回應是 `OK`；接上 Alertmanager 之後，送心跳的是它的 webhook。網址本身就是寫入權限：知道它的人都能替這個檢查送心跳，或者回報失敗，所以它是私密值，與 ntfy 的網址一樣放在 Alertmanager 以 `url_file` 讀取的檔案裡（放法見〈Alertmanager 的通知管道〉的〈私密網址的存放：設定檔不展開環境變數，改用讀檔案的 `*_file` 欄位〉）。

檢查項目建立之後、還沒收過任何 ping 時是 `new` 狀態，這個狀態不會因為沒有心跳而通知。UUID 不存在時，自架版與託管版的回應不同。自架的 healthchecks 4.4 實測回 404 與 `not found`，Alertmanager 會把它記成送出失敗。託管版的 API 文件寫的是回 200 與 `OK (not found)`，Alertmanager 會把它當成送出成功：網址檔裡的 UUID 寫錯時，通知送不出去的偵測不會留下任何失敗計數，而那個檢查項目從來沒收到心跳、停在 `new`，也不會通知。所以接好之後，到服務的頁面確認檢查項目收到了第一次心跳。檢查項目之後被刪除時，託管版同樣回 200，心跳從此不再被看著而沒有任何訊號，這一種只有定期演練（見〈心跳中斷的演練〉）會發現。

週期與寬限在檢查項目上設定，選值的條件是 Alertmanager 實際送出心跳的最長間隔（`repeat_interval` 加一個 `group_interval`）要小於週期加寬限。沿用〈Alertmanager 的通知管道〉的 `repeat_interval: 5m` 與 `group_interval: 1m`，最長間隔是 6 分鐘，服務端設週期 5 分鐘、寬限 5 分鐘，總和 10 分鐘，留 4 分鐘的餘裕給一次稍晚的送出。週期設成 1 分鐘、寬限 1 分鐘而路由維持 5 分鐘的重送，服務會在每兩次心跳之間判定中斷，一直誤報。實測為了縮短等待，兩者各設 1 分鐘、路由也一起設短，停掉 Alertmanager 之後，`DOWN` 的通知信在最後一次心跳之後 2 分鐘寄出（時間線見〈心跳中斷的演練〉）：判斷的起點是最後一次收到心跳的時間，不是 Alertmanager 停掉的時間。所以從 Alertmanager 停掉到收到通知，最長是週期加寬限（剛送完一次心跳就停掉的情形）。停掉的是 Prometheus 時，Alertmanager 在已收到的 Watchdog 告警結束時間之前照常重送心跳，這段重送期另外加在延遲上，依 Prometheus 的原始碼約 4 個評估週期（評估週期短於 1 分鐘時以 1 分鐘計），本篇沒有實測。心跳恢復時，服務寄出 `UP` 的通知。

對 ping 網址加上 `/fail` 送出，檢查項目立刻變成失敗並寄出通知：實測 Alertmanager 送出之後約 2 秒，Mailpit 收到 `DOWN | <檢查項目名稱>`。收到 `/fail` 的檢查項目，之後只要再收到一次一般的 ping，就翻回正常。

## Alertmanager 的 receiver 與路由：心跳與送失敗的通知

心跳的子路由寫在〈Alertmanager 的通知管道〉的〈路由樹：一則告警送到哪個 receiver〉那份設定裡：`Watchdog` 送到 `heartbeat` receiver，`url_file` 指向放著 ping 網址的檔案，時間參數的理由見同篇〈Watchdog：告警鏈本身的心跳〉。送失敗的通知另外在 healthchecks 建一個檢查項目，下文稱 **notify-fail 檢查項目**（與送到它的 receiver 同名），網址是它的 ping 網址加上 `/fail`。下面的子路由與 receiver 併進那份設定已有的 `routes` 與 `receivers` 清單，不能整段附加在檔案後面（同一份設定出現兩個 `receivers` 時，`amtool check-config` 拒絕載入）：

```yaml
route:
  routes:
    # Watchdog 的子路由在最前面（〈Alertmanager 的通知管道〉的路由樹）
    - matchers: [alertname="AlertmanagerNotificationsFailing"]
      receiver: notify-fail
      continue: true                 # 送到 /fail 之後繼續往下比
    # 已經有〈通知送不出去的偵測〉裡送到 mail 的那一條（continue: true）時，它排在這裡
    - matchers: [alertname="AlertmanagerNotificationsFailing"]
      receiver: ntfy-warning         # 原本那一份；後面的子路由都不符合時不會回到最上層，所以明寫
    # severity="critical" 的子路由排在這些之後
receivers:
  - name: notify-fail
    webhook_configs:
      # 檔案內容是 notify-fail 檢查項目的 ping 網址加上 /fail
      - url_file: /etc/alertmanager/secrets/notify-fail.url
        send_resolved: false         # 解除時不再送：送出的會是同一個 /fail 網址
```

`continue: true` 讓這則告警送到 notify-fail 之後繼續往下比對；而一則告警只要比中了任何一條子路由，就不會回到最上層的 receiver，原本由最上層送到 ntfy 的那一份因此要再寫一條子路由接住。比對到沒有 `continue` 的子路由就停止，所以順序是：notify-fail、〈通知送不出去的偵測〉裡送到 `mail` 的那一條（兩者都帶 `continue: true`），最後才是送到 `ntfy-warning` 的那一條。notify-fail 若接在送到 `ntfy-warning` 那一條之後，永遠比不到。`send_resolved: false` 是因為 webhook 解除時送出的網址與成立時相同，設成 `true` 時，問題解除的那一刻會再對 `/fail` 送一次，心跳監看服務又記下一次失敗。

路由寫好之後，以〈路由樹〉那一節的 `amtool config routes test` 確認比對結果，標籤帶 `alertname=AlertmanagerNotificationsFailing severity=warning`：

```sh
# 在放 alertmanager.yml 的目錄底下執行；版本換成自己用的 Alertmanager
docker run --rm -v "$PWD:/a" --entrypoint amtool prom/alertmanager:v0.34.1 \
  config routes test --config.file=/a/alertmanager.yml alertname=AlertmanagerNotificationsFailing severity=warning
```

實測三條都寫時回 `notify-fail,mail,ntfy-warning`；只有 notify-fail 與 ntfy-warning 兩條時回 `notify-fail,ntfy-warning`，拿掉送到 `ntfy-warning` 的那一條時只剩 `notify-fail`；notify-fail 排在送到 `ntfy-warning` 那一條之後時回 `mail,ntfy-warning`，送不到 `/fail`。

`AlertmanagerNotificationsFailing` 是〈Alertmanager 的通知管道〉的〈通知送不出去的偵測〉裡那條規則的名稱；在 Kubernetes 上用 chart 附的規則時，名稱與 matcher 的寫法見 [在 Kubernetes 上接上監控](/backend/04-observability/vendors/prometheus/kubernetes-monitoring-entry/) 的〈chart 預設的 Alertmanager 路由：不送任何通知〉；那裡的私密檔以 Secret 掛載，`url_file` 的路徑多一層 Secret 名稱的目錄，而 Alertmanager 由 Operator 管理，刪掉它的 Pod 會被重建，〈心跳中斷的演練〉的停機演練在叢集上要另外安排，本篇沒有在叢集上演練。

`/fail` 要送到 notify-fail 檢查項目，不能送到心跳用的那一個。心跳用的檢查項目收到 `/fail` 之後，下一次一般的 ping 會把它翻回正常；以〈Alertmanager 的通知管道〉的 `repeat_interval: 5m` 與 `group_interval: 1m`，兩者相加，下一次心跳最晚約 6 分鐘後就到：通知雖然寄出了，服務上看到的狀態很快又變回正常，之後查歷史的人會以為只是一次短暫的波動。notify-fail 檢查項目只收 `/fail`，失敗的狀態會一直留到有人處理。

notify-fail 檢查項目平時不收 ping，所以「到服務的頁面確認收到第一次心跳」對它不適用；網址寫錯時它永遠沉默，在託管版上連失敗計數都沒有。驗收的方式是送一則合成的 `AlertmanagerNotificationsFailing`（送法見〈Alertmanager 的通知管道〉的〈本機測試：自架的 ntfy、Mailpit 與合成告警〉），確認 notify-fail 檢查項目變成失敗並寄出通知。實測以 Alertmanager 的 API 送出，`group_wait` 預設的 30 秒之後送到 `/fail`，notify-fail 檢查項目變成失敗並寄出通知。

驗收或處理完通知送不出去的問題之後，把 notify-fail 檢查項目恢復成等待的狀態要用暫停（paused），不要對它送一次一般的 ping。一次 ping 會讓它開始按週期等待下一次心跳，而 notify-fail 平時不會收到心跳，所以週期加寬限之後必定誤報一次：healthchecks 的預設週期是 1 天、寬限 1 小時，誤報會在約 25 小時後出現，很難連回當初那一次 ping。檢查項目的 `manual_resume`（暫停之後要手動恢復）維持關閉：開啟時暫停中的檢查項目會忽略 ping，它會不會也忽略 `/fail`，healthchecks 的文件沒有寫。實測在 healthchecks 建立之後從來沒收過 ping 的檢查項目，過了週期加寬限仍是 `new`，沒有寄出任何通知；送一次 ping 之後它寄出 `UP`，週期的計時從那一次 ping 開始，2 分鐘後因為沒有下一次心跳又寄出 `DOWN`，是一次誤報；設成暫停之後的 3 分鐘內沒有寄出任何通知，下一次 `/fail` 照常寄出 `DOWN`。實測以 healthchecks 的 Django 管理指令（`manage.py shell`）直接把狀態改成暫停，代替網頁上的暫停按鈕；託管版的暫停以它的文件為準。

## 心跳中斷的演練

心跳監看服務的中斷通知平時不會發出，演練確認的是它會發出，而且送到了人手上。實測的時間線（healthchecks 的週期與寬限各 1 分鐘，Alertmanager 的 `repeat_interval` 1 分鐘、`group_interval` 30 秒；這組值是為了縮短演練的等待而設短的，正式的值見〈healthchecks 的 ping 網址、週期、寬限與 /fail〉）：

- 03:47:47 與 03:49:10 各收到一次心跳，間隔 1 分 23 秒，落在 `repeat_interval` 加上一個 `group_interval` 之內。
- 03:50:26 停掉 Alertmanager。
- 03:51:10 寄出 `DOWN | heartbeat`，是最後一次心跳之後 2 分鐘、Alertmanager 停掉之後 44 秒。
- 03:51:40 重新啟動 Alertmanager。它不保存收到的告警，重新啟動之後告警清單是空的，要等 Prometheus 下一次送出告警；實測在合成告警重新送進去之後，03:51:49 寄出 `UP | heartbeat`。

正式的值與選值條件見〈healthchecks 的 ping 網址、週期、寬限與 /fail〉。照正式的值演練時，停掉 Alertmanager 之後最晚 10 分鐘收到 `DOWN`。服務寄出了 `DOWN` 只證明它判定了中斷，沒有證明有人收到：通知寄到的信箱有沒有人看、手機 App 有沒有跳出通知、通知裡寫不寫得出是哪一個檢查項目中斷，要在演練時一併確認。

## 外部探測服務的挑選條件

外部探測服務從業者的多個地點，照使用者的路徑對服務發請求。心跳監看回答監控還在不在，外部探測回答使用者連不連得到，兩者都要。挑選時看幾件事：

- **探測的路徑。** 請求要打使用者用的公開網址，經過 DNS、HTTPS 與公開的入口。打主機的 IP 時，探測量不到 DNS 與 TLS 憑證的故障。
- **判斷成功的方式。** 只看狀態碼時，入口回一個錯誤頁也可能是 200；能比對回應內容裡的一段固定字串，或打一個只有服務正常時才回得出內容的端點，判斷才會準。以短網址服務為例，探測一條固定的測試短網址，檢查回應是 `302` 而且 `Location` 指向預期的網址，比打首頁更貼近使用者要的功能。
- **探測的地點與次數。** 探測地點要包含使用者所在的地區：以台灣使用者為主的服務，探測點全在其他洲時，在地路由的故障量不到。服務要能設定成多個地點同時失敗才通知，排除單一地點自己網路的問題；代價是只有某個地區或某家網路業者的使用者連不進來時，這個設定不會通知。
- **服務本身跑在哪裡。** 與心跳監看的條件相同。外部探測與心跳監看向同一家業者購買時，那家停掉會同時拿掉兩種訊號，分屬不同業者時一家停掉還剩另一種。
- **通知管道。** 與心跳監看的條件相同，不經過自己的監控主機。
- **送出去的資料。** 送到探測業者的是探測的設定（網址、預期的回應內容）與服務的回應，不是告警 JSON；告警內容不能離開組織的服務，要查業者存了哪些回應內容，回應裡有內部資訊時改打只回固定內容的端點。
- **對服務的影響。** 探測請求會出現在服務的存取紀錄與指標裡；探測打的是會記錄點擊的轉址路徑時，點擊數會被探測灌高，要在服務的統計裡以來源或 User-Agent 排除，或改打不記錄的端點。

外部探測服務的候選（UptimeRobot、Better Stack、Pingdom 這類）與各自的免費方案對照，見 [無 SSH 環境的監控與告警](/infra/takeover/legacy-external-monitoring/) 的〈工具選型〉。自己有另一個失效域的主機時，外部探測也可以自己跑（例如在那台主機上跑 Prometheus 的 blackbox_exporter 或 Gatus），條件是那台主機不與服務主機共用失效域，而且它停掉時有人知道；兩台主機互相監看時，用來分辨兩台之間連線中斷的那一個探測要同時避開服務主機與監控主機的失效域，理由見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/) 的〈觀察者的位置：第三方服務、另一個失效域的主機（含互相監看）與另一個業者的排程平台〉。

## 延伸閱讀：觀察者的位置、Alertmanager 的路由與自架的觀察者

- 心跳監看與外部探測放在第三方、另一個失效域的主機或兩台互相監看時各自的差別，以及心跳監看、外部探測與主機內部探測並排時怎麼判讀，見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。
- 心跳之外的通知管道（ntfy、email、Slack）、Watchdog 的時間參數與通知送不出去的偵測規則，見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)。
- 觀察者改成自架、跑在另一個失效域的主機上時，VPN、互相監看的條件與兩台同時停掉的風險，見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/)。
- 心跳監看的判斷方式見 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。
