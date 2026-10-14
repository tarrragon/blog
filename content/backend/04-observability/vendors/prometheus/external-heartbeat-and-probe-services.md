---
title: "第三方心跳監看與外部探測服務：挑選條件、healthchecks 的 ping 與 /fail、Alertmanager 的接法與演練"
date: 2026-10-14
description: "以第三方服務當作監控主機失效域以外的觀察者：心跳監看服務的挑選條件（服務的位置、通知管道、判斷方式、回報失敗的端點、送出的告警資料留在哪裡），healthchecks 的 ping 網址、週期與寬限、/fail 與自架和託管版的回應差異，Alertmanager 送心跳與送失敗通知的 receiver 與路由，停掉 Alertmanager 的演練，以及外部探測服務的挑選條件"
weight: 18
tags: ["backend", "observability", "vendor", "prometheus", "alertmanager"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列。只有一台主機時為什麼需要失效域以外的觀察者、心跳監看與外部探測各回答什麼問題，見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)；這一篇處理以第三方服務當觀察者時的挑選與接法。

這一篇整理以第三方服務做心跳監看（dead man's switch）與外部探測時，挑選服務要看的條件，以及把 Alertmanager 接到心跳監看服務的設定。心跳監看以 healthchecks 為例：它是開源專案，有託管版 healthchecks.io，也可以自架。文中的行為以自架的 healthchecks 4.4 與 Alertmanager 0.34.1 在 macOS 的 OrbStack 上實測，通知信寄到本機的 Mailpit；本篇沒有實際接過託管版 healthchecks.io，兩者的網址結構與判斷方式相同，回應碼的差異寫在下文，通知管道與方案限制以託管版的文件為準。外部探測服務本篇只寫挑選條件，沒有實際接過任何一家。

## 第三方服務提供的位置與維運

第三方服務提供的是失效域以外的位置，以及它自己的存活由業者維運；只有一台主機時，這是取得那個位置的唯一方式，推導見 4.28 的〈觀察者的位置：第三方服務、另一個失效域的主機與互相監看〉。手上有另一個失效域的主機時，自己做的條件見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/) 的〈兩台主機互相監看〉。

## 心跳監看服務的挑選條件

**服務本身跑在哪裡。** 心跳監看服務與自己的主機在同一個雲端業者、同一個區域時，那家業者的區域故障會讓兩者一起停：主機停了，而本來要通知的監看服務也停了。查服務的文件或「關於」頁寫的業者與地區（healthchecks.io 寫在它的 about 頁），與自己主機的業者和區域比對；只寫了業者、沒寫地區時，以業者不同為底線。

**通知管道。** 心跳中斷的通知由服務自己的管道送出（email、簡訊、電話、手機 App、Slack 這類整合）。這條管道不能經過自己的監控主機：心跳監看服務以 webhook 把通知送回監控主機上的 ntfy 時，監控主機停掉的那一刻，這條通知也送不到。通知的對象與 Alertmanager 的對象相同，是會處理的人。

**判斷方式。** 心跳監看的判斷是週期加寬限：週期（period）是預期的心跳間隔，寬限（grace time）是容許的延遲，最後一次心跳之後超過兩者相加就判定中斷。healthchecks 另外支援以 cron 表示式描述預期時間，給排程工作用；Alertmanager 的心跳是固定間隔，用週期加寬限就夠。

**回報失敗的端點。** 除了「我還在」，能不能主動回報「出事了」。healthchecks 的 ping 網址加上 `/fail` 就是回報失敗，收到就立刻判定失敗並通知，不必等週期。Alertmanager 偵測到通知送不出去時，以這個端點把消息交給心跳監看服務，由它自己的管道通知。

**送出去的資料留在哪裡。** Alertmanager 的 webhook 送出的是整份告警 JSON：標籤、註解（annotations），以及每則告警的 `generatorURL`。`generatorURL` 是 Prometheus 的網址，Prometheus 沒有設 `--web.external-url` 時取主機名，在容器裡就是容器 ID。healthchecks 會把每次 ping 的請求本文存下來（上限由自架版的 `PING_BODY_LIMIT` 設定，託管版寫在它的 API 文件），所以這些內容會存在服務那一邊。Watchdog 那一則的內容固定且少；送失敗通知的那一則帶著失敗的通知類型與主機標籤。告警內容不能離開組織時，改用自架的監看服務。

**方案的限制。** 免費方案通常限制檢查項目的數量、通知管道的種類與保留的歷史，各家的數字常變，選用時看服務當下公布的方案。心跳監看至少要兩個檢查項目，理由見下方〈Alertmanager 的 receiver 與路由：心跳與送失敗的通知〉。

## healthchecks 的 ping 網址、週期、寬限與 /fail

在 healthchecks 建立一個檢查項目（check），它會產生一個專屬的 ping 網址，路徑是一個 UUID（託管版的網址形如 `https://hc-ping.com/<UUID>`，自架版是 `SITE_ROOT` 環境變數設定的網站網址底下的 `/ping/<UUID>`）。對這個網址送一個 GET 或 POST 就算一次心跳，回應是 `OK`。網址本身就是寫入權限：知道它的人都能替這個檢查送心跳，或者回報失敗，所以它是私密值，與 ntfy 的網址一樣放在 Alertmanager 以 `url_file` 讀取的檔案裡（放法見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 的〈私密網址的存放：設定檔不展開環境變數，改用讀檔案的 `*_file` 欄位〉）。

UUID 不存在時，自架版與託管版的回應不同。自架的 healthchecks 4.4 實測回 404 與 `not found`，Alertmanager 會把它記成送出失敗。託管版的 API 文件寫的是回 200 與 `OK (not found)`，Alertmanager 會把它當成送出成功：網址檔裡的 UUID 寫錯時，通知送不出去的偵測不會留下任何失敗計數，心跳監看服務上那個檢查項目也從來沒收到心跳，因為它停在下文的 `new` 狀態，不會通知。所以接好之後，到服務的頁面確認檢查項目收到了第一次心跳。

週期與寬限在檢查項目上設定。實測兩者各設 1 分鐘，停掉 Alertmanager 之後，`DOWN` 的通知信在最後一次心跳之後正好 2 分鐘寄出：判斷的起點是最後一次收到心跳的時間，不是 Alertmanager 停掉的時間。所以從 Alertmanager 停掉到收到通知，最長是週期加寬限（剛送完一次心跳就停掉的情形）。停掉的是 Prometheus 時，Alertmanager 在已收到的 Watchdog 結束時間之前照常重送心跳，延遲另外加上這一段（依 Prometheus 的原始碼約 4 個評估週期，評估週期短於 1 分鐘時以 1 分鐘計，本篇沒有實測）。心跳恢復時，服務寄出 `UP` 的通知。

對 ping 網址加上 `/fail` 送出，檢查項目立刻變成失敗並寄出通知：實測 Alertmanager 送出之後約 2 秒，Mailpit 收到 `DOWN | <檢查項目名稱>`。同一個檢查項目在 `/fail` 之後收到一次一般的 ping，就翻回正常。

## Alertmanager 的 receiver 與路由：心跳與送失敗的通知

心跳的路由沿用 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 的〈Watchdog：告警鏈本身的心跳〉：`Watchdog` 的子路由送到 `heartbeat` receiver，`url_file` 指向放著 ping 網址的檔案。送失敗的通知另外在 healthchecks 建一個檢查項目，下文稱 **notify-fail 檢查項目**（與送到它的 receiver 同名），網址是它的 ping 網址加上 `/fail`。路由寫兩條：

```yaml
route:
  routes:
    # Watchdog 的子路由在最前面（見〈Alertmanager 的通知管道〉）
    - matchers: [alertname="AlertmanagerNotificationsFailing"]
      receiver: notify-fail
      continue: true                 # 送到 /fail 之後繼續往下比
    - matchers: [alertname="AlertmanagerNotificationsFailing"]
      receiver: ntfy-warning         # 原本那一份；後面的子路由都不符合時不會回到最上層，所以明寫
    # severity="critical" 的子路由排在這兩條之後
receivers:
  - name: notify-fail
    webhook_configs:
      # 檔案內容是 notify-fail 檢查項目的 ping 網址加上 /fail
      - url_file: /etc/alertmanager/secrets/notify-fail.url
        send_resolved: false         # 解除時不再送：送出的會是同一個 /fail 網址
```

`continue: true` 讓這則告警送到 notify-fail 之後繼續往下比對；而一則告警只要比中了任何一條子路由，就不會回到最上層的 receiver，原本由最上層送到 ntfy 的那一份因此要再寫一條子路由接住，與〈Alertmanager 的通知管道〉的〈通知送不出去的偵測〉裡送到 `mail` 的寫法相同。`send_resolved: false` 是因為 webhook 解除時送出的網址與成立時相同，設成 `true` 時，問題解除的那一刻會再對 `/fail` 送一次，心跳監看服務又記下一次失敗。

`AlertmanagerNotificationsFailing` 是〈Alertmanager 的通知管道〉的〈通知送不出去的偵測〉裡那條規則的名稱；在 Kubernetes 上用 chart 附的規則時，名稱與 matcher 的寫法見 [在 Kubernetes 上接上監控](/backend/04-observability/vendors/prometheus/kubernetes-monitoring-entry/) 的〈chart 預設的 Alertmanager 路由：不送任何通知〉。實測以 Alertmanager 的 API 送一則合成的 `AlertmanagerNotificationsFailing`，`group_wait` 預設的 30 秒之後送到 `/fail`，notify-fail 檢查項目變成失敗並寄出通知。兩條路由以 `amtool config routes test` 檢查：兩條都寫時，這則告警比對到 `notify-fail,ntfy-warning`；拿掉送到 `ntfy-warning` 的那一條時只剩 `notify-fail`。

`/fail` 要送到 notify-fail 檢查項目，不能送到心跳用的那一個。心跳用的檢查項目收到 `/fail` 之後，下一次一般的 ping 會把它翻回正常；以〈Alertmanager 的通知管道〉的 `repeat_interval: 5m` 與 `group_interval: 1m`，下一次心跳最晚約 6 分鐘後就到：通知雖然寄出了，服務上看到的狀態很快又變回正常，之後查歷史的人會以為只是一次短暫的波動。notify-fail 檢查項目只收 `/fail`，失敗的狀態會一直留到有人處理。

notify-fail 檢查項目從來沒收過一般的 ping，所以停在 `new` 狀態，不因為沒有心跳而通知：實測在 healthchecks 建立之後從來沒收過 ping 的檢查項目，過了週期加寬限仍是 `new`，沒有寄出任何通知。處理完通知送不出去的問題之後，把它恢復成等待的狀態要用暫停（paused），不能對它送一次一般的 ping：實測送一次 ping 之後它寄出 `UP`，週期的計時從那一次 ping 開始，2 分鐘後因為沒有下一次心跳又寄出 `DOWN`，是一次誤報；設成暫停的檢查項目在 3 分鐘內沒有寄出任何通知，下一次 `/fail` 照常寄出 `DOWN`。實測以 healthchecks 的 Django 管理指令（`manage.py shell`）直接把狀態改成暫停，代替網頁上的暫停按鈕；託管版的暫停以它的文件為準。

## 心跳中斷的演練

心跳監看平時不會觸發，接好之後要演練一次。實測的時間線（healthchecks 的週期與寬限各 1 分鐘，Alertmanager 的 `repeat_interval` 1 分鐘、`group_interval` 30 秒）：

- 03:47:47 與 03:49:10 各收到一次心跳，間隔 1 分 23 秒，落在 `repeat_interval` 加上一個 `group_interval` 之內。
- 03:50:26 停掉 Alertmanager。
- 03:51:10 寄出 `DOWN | heartbeat`，是最後一次心跳之後 2 分鐘、Alertmanager 停掉之後 44 秒。
- 03:51:40 重新啟動 Alertmanager。它不保存收到的告警，重新啟動之後告警清單是空的，要等 Prometheus 下一次送出告警；實測在合成告警重新送進去之後，03:51:49 寄出 `UP | heartbeat`。

正式的設定以〈Alertmanager 的通知管道〉的 5 分鐘 `repeat_interval` 配上服務端的週期 5 分、寬限 5 分，演練的等待時間照比例拉長。演練時同時確認通知送到了人手上：信寄到了哪個信箱、手機 App 有沒有跳出通知、通知裡有沒有寫是哪一個檢查項目中斷。

## 外部探測服務的挑選條件

外部探測服務從業者的多個地點，照使用者的路徑對服務發請求。心跳監看回答監控還在不在，外部探測回答使用者連不連得到，兩者都要。挑選時看幾件事：

- **探測的路徑。** 請求要打使用者用的公開網址，經過 DNS、HTTPS 與公開的入口。打主機的 IP 時，DNS 與憑證的故障量不到。
- **判斷成功的方式。** 只看狀態碼時，入口回一個錯誤頁也可能是 200；能比對回應內容裡的一段固定字串，或打一個只有服務正常時才回得出內容的端點，判斷才會準。以短網址服務為例，探測一條固定的測試短網址，檢查回應是 `302` 而且 `Location` 指向預期的網址，比打首頁更貼近使用者要的功能。
- **探測的地點與次數。** 從多個地點探測、要多個地點同時失敗才通知，可以排除單一地點自己網路的問題。
- **通知管道。** 與心跳監看的條件相同，不經過自己的監控主機。
- **對服務的影響。** 探測請求會出現在服務的存取紀錄與指標裡；探測打的是會記錄點擊的轉址路徑時，點擊數會被探測灌高，要以來源或 User-Agent 排除，或改打不記錄的端點。

自己有另一個失效域的主機時，外部探測也可以自己跑（例如在那台主機上跑 Prometheus 的 blackbox_exporter 或 Gatus），條件是那台主機不與服務共用失效域，而且它停掉時有人知道；兩台主機互相監看時，用來分辨兩台之間連線中斷的那一個探測要放在第三個位置，理由見 4.28 的〈觀察者的位置：第三方服務、另一個失效域的主機與互相監看〉。

## 延伸閱讀：失效域以外的觀察者、Alertmanager 的路由與多台主機的配置

- 同一台主機上的監控看不到哪些故障、心跳監看、外部探測與內部告警並排時怎麼判讀，見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。
- Watchdog 的時間參數、通知送不出去的偵測規則與送到 email 的另一條管道，見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)。
- 不用第三方服務、以另一個失效域的主機互相監看的配置，見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/)。
- 心跳監看的判斷方式見 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。
