---
title: "ntfy：推送通知服務怎麼運作、公共站 vs 自架"
date: 2026-07-03
description: "用 ntfy 把機器的告警推到手機、想搞懂它是誰維護的開源服務、topic 的安全模型、以及該用公共站還是自架時回來讀"
weight: 6
tags: ["linux", "ntfy", "monitoring", "alerting", "notifications"]
---

ntfy（唸作 "notify"）是一套開源的發布/訂閱推送通知服務，把「一台機器想告訴你一件事」變成「你手機上跳一則通知」，而且發送端只要一個 HTTP 請求、不需要註冊帳號。[服務失敗監控](../service-failure-monitoring/)那篇的告警就是靠它把「某個 service 掛了」推到手機。這篇說清楚它怎麼運作、誰在維護、以及一個會直接影響你安全的模型：在公共站上，**topic 名稱就是唯一的密碼**。

## 怎麼運作：topic 是頻道，發送是一個 POST

ntfy 的模型簡單到幾乎不需要學：一個 **topic** 就是一個頻道，發送端對那個 topic 發 HTTP 請求、訂閱端就收到。發一則通知是這樣：

```bash
curl -d "sshd 在 web-01 掛了" ntfy.sh/你的topic
```

訂閱端可以是手機 app、瀏覽器，或程式（它提供 SSE、JSON stream、WebSocket 三種串流讓你的程式訂閱）。就這樣——沒有 broker 設定、沒有 API key 必填、沒有帳號流程。這種「一行 curl 就送出」正是它在監控告警場景最省事的原因：處理器腳本裡塞一行 `curl` 就完成推送。

進階一點的用法都是加 HTTP header：`Title`（標題）、`Priority`（優先級，高優先級手機會強提醒）、`Tags`（標籤/emoji）、`Click`（點通知打開的網址）。但核心就是「POST 到一個 topic」。

## 手機訂閱：官方 app 三步

告警最終要落到手機上，訂閱端在手機這頭是三步：

1. 裝官方 app：App Store（iOS）或 Google Play（Android）搜 **ntfy**，作者 `binwiederhier`（也可從 F-Droid 裝）。
2. 開 app、點 **Add subscription（新增訂閱）**，填入你的 **topic 名稱**（就是 `curl -d ... ntfy.sh/<topic>` 裡那個 `<topic>`）。用公共站的話到這步就收得到了。
3. 自架 server 的話，在同一個 Add subscription 對話框把「Use another server」打開、填自架的 base URL（例 `https://ntfy.example.com`），再填 topic。

填完發一則 `curl -d "test" ntfy.sh/<topic>` 驗證手機有跳通知，這條鏈就通了。app 收到後長按通知可設定每 topic 的優先級與勿擾。

## 本地訂閱：不只手機 app

訂閱端不一定要手機 app——因為訂閱也只是一個 HTTP GET，本地有好幾種方式：

- **純 curl（零安裝）**：`curl -sN https://ntfy.sh/<topic>/json` 即時串流、一行一則 JSON（`-N` 不緩衝）；`/raw` 只給純文字、`/sse` 給網頁、`/ws` 給 WebSocket。要補看最近的：`curl -s "https://ntfy.sh/<topic>/json?poll=1&since=10m"` 拉最近 10 分鐘就關。
- **瀏覽器**：直接開 `https://ntfy.sh/<topic>`，就是一個即時 web UI。
- **ntfy CLI**：`ntfy subscribe <topic>` 串到終端機；`ntfy subscribe <topic> <指令>` 每來一則跑一次指令（訊息塞進 `$NTFY_TITLE` / `$NTFY_MESSAGE`）。

### 常駐成桌面通知

Linux 桌面上最順的用法，是把訂閱做成一個常駐服務、每則告警用 `notify-send` 彈成桌面通知（走你的通知 daemon，mako 或桌面 shell 內建的都行）。核心就是一個串流迴圈：

```bash
curl -sN https://ntfy.sh/<topic>/json | while read -r l; do
  [ "$(jq -r '.event' <<<"$l")" = message ] || continue
  notify-send -u critical "$(jq -r '.title' <<<"$l")" "$(jq -r '.message' <<<"$l")"
done
```

把它包成一個 **user systemd 服務**（`WantedBy=default.target` + `Restart=always`）就能開機常駐、斷線自動重連。這是「盯著機器狀態」很實用的一塊：人在電腦前不必掏手機就看得到告警。

**放哪台有講究**：在被監控的機器上訂閱它自己的告警有點循環——那台掛了，桌面通知也彈不出來。桌面訂閱更適合放在**你盯著的工作機**上、訂遠端機器的 topic。放被監控機本身只適合當測試 / 示範。

## 誰維護它：開源專案，不是正式標準

ntfy 是**開源專案**（server 以 Apache-2.0 授權），主要由一個人維護——Philipp Heckel（GitHub `binwiederhier`）——加上社群貢獻。理解這個定位很重要：

- 它**不是**像 HTTP、SMTP 那種有 RFC、多廠商共同實作的正式標準。
- 但它的 API 公開又極簡（就是 HTTP + 幾種串流），所以**任何人都能寫自己的 client 或 server**去對接。官方已經有 Android / iOS / Web / CLI 客戶端，你要自己寫一個也完全可行。

所以「誰都能訂閱跟寫 app 嗎」的答案是：協議公開、可以；但它是一個專案的 API，不是一份跨廠商標準。你用的 app 多半是官方那幾個，或你自己寫的。

## 公共站 vs 自架：兩種很不一樣的東西

ntfy 同時是「一個免費公共服務」跟「一套你能自己跑的軟體」，兩者的安全性差很多：

|            | `ntfy.sh` 公共站               | 自架                                   |
| ---------- | ------------------------------ | -------------------------------------- |
| 認證       | 預設無、topic 名稱就是存取控制 | 可開帳號 / access token / 每 topic ACL |
| 資料經過誰 | 別人的伺服器                   | 你自己的機器                           |
| 成本       | 免費（有額度上限）             | 自己的一台機器 + 維運                  |
| 上手       | 立刻能用                       | 一個 Go binary 或 docker container     |

**公共站**適合測試、個人用、告警內容不敏感的場景——立刻能用。**自架**因為 ntfy 是開源的，一個單一 Go 執行檔（或 docker）就能跑起你自己的 ntfy server，支援帳號、token、以及「哪個 topic 誰能讀寫」的 ACL；適合「不想讓告警內容經過第三方伺服器」或要正式部署的場景。

最小起手（docker，先跑起來再談 ACL）：

```bash
docker run -d --name ntfy -p 80:80 -v /var/cache/ntfy:/var/cache/ntfy \
  binwiederhier/ntfy serve --base-url http://你的主機
# 之後把發送端 curl 的 ntfy.sh 換成你這台的 base-url，行為完全一樣
```

要開認證再加 `--auth-file` 與 `--auth-default-access deny-all`，然後用 `ntfy access` 逐條授權 topic。想先驗證能跑通就先不開認證。

## 安全模型：公共站上，topic 名稱就是密碼

這是用 ntfy.sh 一定要懂的一件事：**公共站預設沒有認證，topic 名稱本身就是唯一的存取控制。** 這導致兩個後果：

- 任何知道或猜到你 topic 名稱的人，能**讀到你所有推去那個 topic 的通知**——而告警內容常含主機名、哪個服務掛了這類資訊。
- 他也能**往你的 topic 發訊息**，讓你收到不是真的的假告警。

所以在公共站上，topic 名稱要當**密碼**看待：用長的、隨機的、不可猜的字串（`server-alert-8f3k2xq9` 而不是 `myserver`）。一個好記好猜的 topic 等於把告警頻道公開。要更徹底就走上一節的自架加 ACL，或用 ntfy.sh 的「保留 topic」（見下）把 topic 綁定到你帳號、別人不能佔用。

判準：告警內容有多敏感、被人偷看或偽造的代價有多高，決定你停在「長隨機 topic」還是往「自架 + 認證」走。純個人測試機，長隨機 topic 通常夠；跑正事、內容敏感，自架。

## 商業模式與維護

單一維護者靠三塊支撐這個免費服務：免費公共站、**ntfy Pro**（付費層，買更高的發送額度與「保留 topic」——保留 topic 就是把名稱綁到你帳號、擋掉別人在公共站上佔用或偷聽同名 topic）、以及贊助。所以核心是開源免費，商業只是加值層，不是把功能鎖在付費牆後。這種模式對「一個人維護的基礎服務」是常見且可持續的安排。

## 同類服務對照

ntfy 不是唯一選擇，依你的取捨還有幾個：

| 服務     | 定位                                   | 什麼時候選它                                         |
| -------- | -------------------------------------- | ---------------------------------------------------- |
| ntfy     | 免帳號、一行 curl、可自架              | 要最省事的 HTTP 推送、或想自架掌握資料               |
| Gotify   | 自架的開源推送 server（跟 ntfy 最像）  | 只想自架、要一個簡單的 self-host 方案                |
| Pushover | 商業、一次性買斷、以穩定著稱           | 願意付費換「不用自己維運、送達可靠」                 |
| Apprise  | 不是服務、是打通幾十種通知目標的函式庫 | 要一份程式碼同時能發 ntfy / Telegram / email / Slack |

Apprise 跟其他三個不同一層：它是抽象層，底下可以接 ntfy 或其他。如果你不確定未來要用哪個推送目標、或要同時發多個，用 Apprise 當中介、之後換目標不用改發送端程式碼。

## 下一步

- 把 ntfy 接進 systemd 服務失敗告警的完整做法（`OnFailure` 鉤子、只在放棄才告警、canary 驗證管線）：[服務掛了怎麼自動知道](../service-failure-monitoring/)。
- 整台機器死掉時 ntfy 這種體內推送發不出來、要改用體外心跳（healthchecks.io / Uptime Kuma），見同篇的「整台機器死掉怎麼辦」段。
- ntfy 是個人 / 單機規模的最小告警通道；規模長大後事件怎麼分類、告警怎麼收斂 → [Monitoring 系列](/monitoring/)；服務探活與自動恢復的概念層 → [DevOps：服務探活與自動恢復](/devops/04-service-health/)。
