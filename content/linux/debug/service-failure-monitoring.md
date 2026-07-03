---
title: "服務掛了怎麼自動知道：從肉眼盯到主動告警"
date: 2026-07-02
description: "不想每次都手動 systemctl 檢查服務死活、想讓機器在 service 掛掉時主動推播通知、或擔心整台機器當掉沒人知道時回來讀"
weight: 5
tags: ["linux", "systemd", "monitoring", "alerting", "debugging"]
---

服務掛了不需要用肉眼盯——systemd 本來就在追蹤每個 unit 的狀態，你要做的是把「讀權威狀態」這件事自動化，並在狀態變成失敗時主動推播給自己。監控跟診斷的差別在時機：診斷是出事後回頭找根因，監控是讓系統在出事的當下就告訴你。兩者共用同一個地基——權威狀態。診斷是手動讀一次權威狀態，監控是訂閱權威狀態的變化、變壞就推播。

理解這個框架後，監控就不是「裝一套很重的東西」，而是分層選擇：從 systemd 內建的失敗鉤子（不裝任何額外服務），到推播管道，到「整台機器死掉」的體外心跳，到完整的指標儀表板。多數人只需要前一兩層。

## 你現在手動在做的事（要被取代的基線）

在自動化之前，先認清手動版本——這也是所有告警底層讀的同一個權威來源：

```bash
systemctl --failed          # 現在有哪些 unit 處於 failed（開機後系統怪怪的先掃這個）
systemctl is-failed <unit>  # 單一 unit 明確判失敗（比 is-active 直接）
journalctl -u <unit> -f     # 即時跟一個 unit 的 log
```

`systemctl --failed` 就是「服務死活」的權威清單。手動版的問題不是不準，是你得記得去看。下面每一層都是把「記得去看」換成「壞了它來找你」。

## 第一層：systemd 原生 `OnFailure` 鉤子（不裝額外服務）

systemd 每個 unit 進入 failed 狀態時，可以自動觸發另一個 unit——這個鉤子就是 [`OnFailure=`](/linux/dotfile/knowledge-cards/systemd-onfailure/)。這是最正統、零額外依賴的做法——告警邏輯就寫成一個普通的 systemd service。它由三塊組成：一個負責送通知的處理器 unit、一個實際送出的腳本、以及在要監控的 unit 上掛一行 `OnFailure=`。

（這一層前提是 systemd 環境。跑在**沒有 systemd 的容器**裡、或應用被 orchestrator 管的情境，`OnFailure` 這套用不上——那種環境改走第四層的外部探針，或讓 orchestrator / Prometheus 接管健康檢查與告警。）

**通知處理器**是一個 template unit（`@` 表示可帶參數），參數 `%i` 會是失敗的那個 unit 名：

```ini
# /etc/systemd/system/alert@.service
[Unit]
Description=Alert on failure of %i
[Service]
Type=oneshot
ExecStart=/usr/local/bin/notify-failure %i
```

**送出腳本**負責把「哪個 unit、在哪台機、什麼時候」推出去。這裡有個實測踩到的坑：在 systemd service 的執行環境下，`hostname` 指令可能回傳空字串，要改用 `uname -n` 或讀 `/etc/hostname` 才穩：

```bash
#!/bin/bash
# /usr/local/bin/notify-failure   （記得 chmod +x）
unit="$1"
# 只在「真正放棄」時告警：OnFailure 每次失敗都觸發（含 auto-restart 中途，見下節實測），
# auto-restart 中途 ActiveState 是 activating、撞重試上限才進 failed。gate 掉中途避免洗告警。
state="$(systemctl show "$unit" -p ActiveState --value)"
[ "$state" = failed ] || exit 0
host="$(uname -n)"                     # 不要用 hostname，systemd 環境下可能回空
ts="$(date -Is)"
topic="你的私密topic"
curl -fsS \
  -H "Title: $host: $unit failed" \
  -d "$unit 於 $ts 進入 failed" \
  "https://ntfy.sh/$topic"
```

**在要監控的 unit 掛上鉤子**。針對單一 unit，加一行：

```ini
[Unit]
OnFailure=alert@%n.service    # %n 是本 unit 的全名，會展開成 alert@<本unit>.service
```

要**一次套用到所有 service**，用 top-level [drop-in](/linux/dotfile/knowledge-cards/systemd-drop-in/)（放在 `service.d/` 這個型別目錄下的設定會套用到每個 `.service`）：

```ini
# /etc/systemd/system/service.d/onfailure.conf
[Unit]
OnFailure=alert@%n.service
```

改完 `sudo systemctl daemon-reload`。**一個必須注意的遞迴陷阱**：全域 drop-in 也會套到 `alert@` 自己，它若失敗會觸發自己。用 `sudo systemctl edit alert@.service` 開一個 override、在 `[Unit]` 段寫一行空的 `OnFailure=`（清掉繼承來的值）擋掉：

```ini
# systemctl edit alert@.service 會開這個檔
[Unit]
OnFailure=
```

這條鏈是實測驗證過的：故意讓一個 `ExecStart=/bin/false` 的測試 service 失敗，systemd log 出現 `Triggering OnFailure= dependencies`、`alert@` 處理器被觸發跑完、`curl` 推到 ntfy 回 HTTP 200——通知確實送出，全程沒有肉眼介入。

### 先自動重啟、放棄了才吵你

多數暫時性失敗（一次連線抖動、一個 race）自己重試就好，不值得半夜叫醒你。把「自動復原」跟「告警」分兩段：讓 systemd 先重啟幾次，撐過重試上限才真的算放棄。

```ini
[Service]
Restart=on-failure
RestartSec=5
[Unit]
StartLimitBurst=3          # 重試 3 次
StartLimitIntervalSec=60   # 60 秒內都失敗才進 failed（start-limit-hit）
```

**這裡有個實測踩到、跟直覺相反的意外**：`OnFailure` 不是「放棄才觸發」，而是**每一次失敗都觸發**——包含 `Restart=on-failure` 的每次 auto-restart 中途。實測一個反覆 crash 的服務（重試 3 次後放棄）觸發了 **4 次** `OnFailure`（3 次 auto-restart + 1 次最終 `start-limit-hit`）。所以只靠 `Restart=` + `StartLimit=` 這段 config，每次瞬斷都會發一則告警、把信箱洗爆。（這個觸發次數是特定 systemd 版本的實測行為；`OnFailure` 與 `Restart=` 的互動跨版本調整過，換一個版本可能量到不同次數，照抄前先在自己的版本上驗一次。）

真正做到「只在放棄才吵」，靠的是上面送出腳本開頭那道 gate：`systemctl show <unit> -p ActiveState` 在 auto-restart 中途是 `activating`、撞上限進 failed 才是 `failed`，腳本只在 `failed` 才送。加上 gate 後同一個 crash 測試從 4 次告警降到 1 次（只剩最終放棄那次）。config 負責「重試幾次」，handler 的 gate 負責「只在終局告警」——兩段合起來才是完整的「先重啟、放棄才吵」。

### 抓「進程活著但沒在做事」：外部健康探針

`OnFailure` 抓的是「進程狀態變了」——crash、exit、被 kill。但服務可能**進程還在、卻沒在做事**：hung、deadlock、內部子系統壞掉。這種 systemd 看它還 `active`、不會觸發任何告警——正是[「進程活著 ≠ 在運作」](../process-service-state-diagnosis/)那條，搬到監控場景。

要抓這種，先看控不控制得了那個服務。**控制得了**（服務是自己寫的）：systemd 原生的 `WatchdogSec=` 加服務端定期 `sd_notify(WATCHDOG=1)` 報活，超時沒報 systemd 就自動 kill + restart，不必自建探針、也零額外依賴。**控制不了**（別人的 HTTP 服務、閉源程式，改不了它的碼）：從外面**主動戳它、看它回不回應**——一個 timer 定時對服務發一個健康請求（HTTP 服務就 curl 它的 `/health`）並設逾時；戳不動、逾時失敗，就讓「那個檢查」自己 failed，一樣走 `OnFailure` 告警。

```ini
# health-check.service（oneshot）+ 一個每 2 分鐘跑的 .timer
[Service]
Type=oneshot
ExecStart=/usr/bin/curl -fsS --max-time 5 http://127.0.0.1:8899/health
```

實測對照最清楚：讓一個健康服務卡在 `sleep`（進程還在、單執行緒不再回應），`systemctl is-active` 仍顯示 `active`——systemd 沒察覺；但這個外部探針 curl `/health` 5 秒逾時、check 失敗、告警發出。**systemd 抓進程死、外部探針抓進程活著但 hung，兩層互補、缺一漏一種。**

### canary：先證明告警管線本身是好的

監控最怕的失效模式是「出事時才發現它早就不會叫了」。防這個的辦法是養一隻 **canary**——一個你可控的假服務，專門用來確認整條管線是活的。它一物兩用：

- **驗證管線**：故意弄掛它，看「失敗 → OnFailure → 推送」真的一路通到你手機，不必拿 sshd 這種真服務去冒險。
- **當活性訊號**：它自己若無故失敗告警，等於告訴你告警系統本身還在運作。

做法是一個極簡 HTTP 服務（stdlib 就夠、不必框架），留幾個測試入口：`/health` 正常回、`/crash` 故意退出（測 `OnFailure`）、`/hang` 進程活著但不回應（測外部探針）。這樣任何時候都能一鍵重驗監控沒有默默失效。

靶子本體用 Python stdlib 幾十行就成（VM 沒 Go toolchain 也免編譯）：

```python
#!/usr/bin/env python3
# /usr/local/lib/demo-health/health-server.py
import sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/"):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok\n")
        elif self.path == "/crash":                       # 進程退出 → systemd 標 failed → OnFailure
            self.send_response(200); self.end_headers(); self.wfile.write(b"crashing\n"); sys.exit(1)
        elif self.path == "/hang":                        # 進程活著但不回應 → 只有外部探針抓得到
            self.send_response(200); self.end_headers(); self.wfile.write(b"hanging\n"); time.sleep(3600)
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass                        # 不洗 journal

HTTPServer(("127.0.0.1", 8899), H).serve_forever()
```

把它掛成一個帶 `OnFailure=alert@%n.service` 與 `StartLimitBurst=3` 的 service，就是一隻可控 canary：`curl localhost:8899/crash` 驗第一層告警鏈、`curl localhost:8899/hang` 驗上面那個外部探針。平時它 `/health` 正常回、自己無故 failed 時等於告訴你告警系統本身還活著。

## 第二層：推去哪裡（關鍵是能離開這台機器）

處理器腳本裡那一段 `curl` 可以換成任何管道：

- **ntfy**（`ntfy.sh` 或自架）：一行 `curl` 推到手機，最省事，上面的例子就是。它怎麼運作、公共站 vs 自架、以及「topic 名稱就是唯一的密碼」這個安全模型，見 [ntfy：推送通知服務](../ntfy-push-notification-service/)。
- **email**：要先設好一個 MTA（如 `msmtp`），腳本改成 `mail` / `sendmail`。
- **Telegram bot、Apprise**（一個工具打多個目標）等。

判準只有一條：**告警要送到機器外**。送桌面 `notify-send` 只有你正盯著螢幕時才有用；送手機或 email，離開座位、人在外面也收得到。一台跑正事的機器，告警管道應該落在它之外。

## 第三層：整台機器死掉怎麼辦（監控自己的盲點）

`OnFailure` 有個根本限制：**它靠 systemd 觸發，機器整台掛了（當機、斷電、kernel panic），systemd 自己都沒了，發不出任何告警。** 這是所有「機器自己監控自己」方案的共同盲點——它報得了服務的死，報不了自己這台的死。

覆蓋這一層要反過來做：讓機器定時對一個**體外**的服務「報平安」，平安訊號一停，由那個體外服務替你告警。這叫 dead-man's switch（心跳監控）。

那個 `<你的-uuid>` 不是憑空來的，先在體外服務把 check 建好：到 [healthchecks.io](https://healthchecks.io/) 註冊、建一個 check、它給你一個像 `https://hc-ping.com/xxxxxxxx-xxxx-...` 的 ping URL（uuid 就在裡面）。**Period 設成比你的 heartbeat 間隔略長、再加一段 grace**（例：timer 每 5 分鐘打，period 設 6 分鐘、grace 5 分鐘），避免偶爾一次晚到就誤報。拿到 URL 後填進來：

```ini
# /etc/systemd/system/heartbeat.service
[Service]
Type=oneshot
ExecStart=curl -fsS https://hc-ping.com/<你的-uuid>
# 搭配一個 heartbeat.timer，OnUnitActiveSec=5min 定時打
```

心跳超過 period + grace 沒到，healthchecks.io（或自架的 Uptime Kuma）就通知你。**體內的監控管不了自己這台的死亡，一定要有體外的一隻眼睛**——這跟 [機器連不到或起不來](../machine-unreachable/) 是同一個問題的兩面：那篇是機器已經不回應時從外面怎麼查，心跳是讓「不回應」這件事本身自動觸發告警。

## 第四層：要指標、趨勢、門檻（不只是 up/down）

當你要的不只是「掛了沒」，而是 CPU、記憶體、磁碟、延遲的趨勢與門檻告警（例如磁碟用量超過 80% 就先警告——磁碟用滿常是多個服務同時故障的共同根因，見 [機器連不到或起不來](../machine-unreachable/) 的磁碟段），就進到完整監控堆疊：

| 工具                      | 定位                            | 什麼時候選它                                                       |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------ |
| Netdata                   | 開箱即用、自帶大量預設告警      | 單機、想要圖表 + 門檻告警、最不想設定                              |
| Monit                     | 輕量、每服務健康檢查 + 自動動作 | 要「掛了自動跑一段修復腳本」、超出 systemd `Restart=` 能表達的邏輯 |
| Prometheus + Alertmanager | 指標抓取 + 告警規則引擎         | 多台機器、要歷史數據與可擴展的告警規則                             |
| Uptime Kuma               | 自架的 up/down + 心跳面板       | 想要一個面板統一看多台/多服務、也能當第三層的心跳接收端            |

（表裡略過 Nagios / Icinga 這類老牌方案——它們跟 Monit 的「每服務健康檢查 + 自動動作」定位重疊，仍是成熟選項，只是新專案多半從上表那幾個起手。）

這一層不是每個人都需要。單機、只想知道某個服務死活，第一層就夠；要看趨勢、跨機、設門檻，才值得付這層的設定與維運成本。

## 先確認有沒有，沒有就從最簡單開始

監控最好在出事之前就建好，不是等第一次沒人發現的當機才想到。有兩個時機該主動確認這台機器有沒有在監控自己：**裝好一台新機器時**，跟**發現自己反覆在除同一個服務的失敗時**。確認的方式就是讀權威狀態：

```bash
systemctl --failed                      # 現在有沒有 failed 的
systemctl show sshd -p OnFailure        # 關鍵服務有沒有掛告警鉤子
```

沒有任何監控的話，**從最簡單那層開始建，別一開始就上重的**：第一層的 `OnFailure` + ntfy 就能讓「服務掛了」主動找上你，零額外 daemon、幾個檔案就設好。遠端機器至少把 sshd 掛上——它掛了你就失聯，是最該先監控的一個。等你真的需要趨勢圖、跨機、或告警內容不能經過第三方時，再往自架 ntfy（帳號 + ACL）跟完整監控堆疊爬。多數單機、個人用的情境，停在第一層就夠。

## 依情境選

把四層對回實際要監控的對象：

- **某個 service 掛了想被通知** → 第一層 `OnFailure` drop-in + ntfy。不裝額外 daemon，最貼近 systemd。
- **希望先自動重啟、救不回來才告警** → 第一層再加 `Restart=on-failure` + `StartLimit*`。
- **怕整台機器當掉沒人知道** → 第三層心跳 / dead-man switch。這層體內方案覆蓋不到，必須體外。
- **要看資源趨勢、跨多台、設門檻告警** → 第四層，單機用 Netdata、多機用 Prometheus 堆疊。

判準是先分清你要監控的層級：**單一 service 的死活、整台機器的死活、還是資源的趨勢**——三種對應不同層，別拿其中一種去蓋另一種。最常見的誤區是以為體內的 `OnFailure` 能報自己這台的當機，那正是它的盲點。

## 下一步

- 告警把你叫來之後，怎麼判那個服務到底是什麼狀態（failed、restart loop、還是活著但子系統 wedged）→ [程序、服務與狀態怎麼判](../process-service-state-diagnosis/)。
- 機器完全不回應、心跳斷掉之後從外面怎麼查 → [機器連不到或起不來](../machine-unreachable/)。
- 底層那套「讀權威狀態、不靠肉眼猜」的判讀紀律 → [診斷心法](../diagnosis-read-authoritative-state/)。
- 從單機往上到多機、要 liveness/readiness probe 與 process supervisor 選型的概念層 → [DevOps：服務探活與自動恢復](/devops/04-service-health/)。事件怎麼分類、告警怎麼收斂成儀表板 → [Monitoring 系列](/monitoring/)。
