---
title: "容器的健康檢查：Docker HEALTHCHECK 的狀態、unhealthy 之後由誰處理、depends_on 的啟動把關與 distroless 映像檔"
date: 2026-10-05
description: "說明 Docker 的 HEALTHCHECK 與 Compose 的 healthcheck 怎麼運作：starting、healthy、unhealthy 三個狀態與時間參數的換算，容器變成 unhealthy 之後 Docker 與 restart policy 各自做什麼、不做什麼，depends_on 的 service_healthy 只在啟動時把關會帶來的連鎖失敗，以及沒有 shell 的 distroless 映像檔怎麼做健康檢查"
weight: 6
tags: ["devops", "health-check", "docker", "compose"]
---

這篇說明 Docker 容器這一層的健康檢查：Dockerfile 的 `HEALTHCHECK` 與 Compose 的 `healthcheck` 怎麼判定狀態、狀態變了之後誰有反應，以及在多容器的 Compose 專案裡設定它時會遇到的問題。健康端點本身要回什麼、探到多深，在 [Health check endpoint 設計](/operations/04-service-health/health-check-endpoint/)；文中的行為在 Docker 29（OrbStack）上以 Compose 實測。

## 健康狀態的三個值與時間參數

容器設了健康檢查之後，除了原本的執行狀態（running、exited），還多一個健康狀態，Docker 官方文件定義它有三個值：

| 健康狀態    | 意思                                                           |
| ----------- | -------------------------------------------------------------- |
| `starting`  | 容器剛啟動、還沒有一次檢查成功                                 |
| `healthy`   | 最近一次檢查成功（不論之前是什麼狀態，一次成功就回到 healthy） |
| `unhealthy` | 連續失敗的次數達到 `retries`                                   |

檢查的方式是 Docker 在容器裡執行一個指令，用指令的結束碼判定：`0` 是這次檢查通過，`1` 是不健康（這次檢查失敗），`2` 保留、文件明寫不要使用。實測 `curl -f` 遇到 HTTP 錯誤時結束碼是 `22`，Docker 同樣把它算成失敗，所以多數範例會寫成 `curl -f ... || exit 1`，讓結束碼落在定義過的值上。指令寫到 stdout 與 stderr 的內容會被保留下來，`docker inspect` 的 `.State.Health.Log` 讀得到每一次檢查的結束碼與輸出，排查時從這裡看是哪一個檢查、為什麼失敗。

決定「多久會被判 unhealthy」的是四個時間參數。官方文件的預設值與在 Compose 裡的寫法：

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "-o", "/dev/null", "http://127.0.0.1/"]
  interval: 10s      # 兩次檢查之間的間隔，預設 30s
  timeout: 3s        # 單次檢查超過這個時間就算失敗，預設 30s
  retries: 3         # 連續失敗幾次才判 unhealthy，預設 3
  start_period: 15s  # 啟動後這段時間內的失敗不計入連續失敗，預設 0s
```

`test` 裡的網址是容器自己的位址與服務的健康端點，要換成手上服務實際聽的 port 與路徑；四個時間值是範例，依服務的啟動時間與能容忍多久的誤判來調。服務從正常變成壞掉之後，大約要經過 `interval × retries` 才會被判 unhealthy：上面這組設定下，讓一個前端容器的 Nginx 開始回 403，31 秒後健康狀態變成 `unhealthy`。預設值（30 秒 × 3 次）要一分半。

`start_period` 期間的失敗不計入連續失敗次數，給服務載入的時間；這段期間 Docker 改用 `start_interval`（預設 5 秒，Docker Engine 25.0 起）的頻率檢查，所以服務一就緒就能很快變成 `healthy`。期間內只要有一次檢查成功，容器就視為啟動完成；從那次成功之後，即使還在 `start_period` 之內，失敗也會照常計入連續失敗次數。

## unhealthy 之後，容器重啟由什麼觸發

健康狀態與重啟是兩套各自運作的機制。Compose 裡常見的寫法是同一個服務同時設 `restart: unless-stopped` 與 `healthcheck`，讀起來像是「不健康就重啟」，而兩者互不相干：

- **restart policy 只看容器有沒有結束。** `no`、`on-failure`、`always`、`unless-stopped` 的觸發條件都是容器的主程序結束。
- **健康狀態只是一個狀態。** 變成 `unhealthy` 時，Docker 發出一個 `health_status: unhealthy` 事件，之後什麼也不做。

實測兩種情形的差別。讓一個設了 `restart: unless-stopped` 的前端容器回 403、程序照常執行：

```text
31 秒後      Health=unhealthy  FailingStreak=3   RestartCount=0
再 100 秒    Health=unhealthy  FailingStreak=10  RestartCount=0   StartedAt 沒變
事件         health_status: unhealthy 只出現一次
```

另一個容器讓它的主程序結束：

```text
1 秒後       RestartCount 0 → 1，restart policy 把它重新啟動
7 秒後       Health=healthy
```

所以「程序活著、但不回應」這種情形，單靠 Docker 不會自動恢復，要有另一個程序或平台讀健康狀態再動手。可以讀它的有三類：

- **編排平台**：Kubernetes 的 liveness probe 失敗會重啟容器（probe 的分工見 [Liveness 與 Readiness](/operations/04-service-health/liveness-vs-readiness/)）。Docker 自己的 Swarm 模式也會：Docker Engine 原始碼裡負責執行 Swarm 任務的那一段（moby 的 `daemon/cluster/executor/container/controller.go`）收到 `unhealthy` 事件時，會停掉容器並把這個任務標為失敗，Swarm 再依重啟條件排一個新的任務取代它。實測一個健康檢查在啟動 12 秒後開始失敗的 Swarm 服務，任務以 `task: non-zero exit (137): dockerexec: unhealthy container` 結束、隨即被新任務取代，之後每一輪都重複。同一段程式碼也在任務啟動時等到 `healthy` 才把它加進服務的負載平衡，所以在 Swarm 模式下，同一個健康檢查同時擔任 readiness 與 liveness。
- **監聽 Docker 事件的工具**：訂閱 `health_status` 事件，看到 unhealthy 就重啟那個容器，現成的有 autoheal 這類專做這件事的容器。這等於自己補上 liveness 的行為，代價是要多跑一個有權限操作 Docker 的程序。
- **讓服務自己結束**：服務偵測到自己回不了頭時直接結束，交給 restart policy 拉起來。一個容器裡跑多個程序時，讓 entrypoint 在任一個程序結束時結束整個容器，屬於這一類。

反過來，壞掉的服務修好之後也不需要重啟：健康檢查持續在跑，上面那個前端改回正常後，下一次檢查成功，狀態就回到 `healthy`，`RestartCount` 仍是 0。

所以同一個 `HEALTHCHECK`，效果取決於容器由誰管理。一般的 `docker run` 與 Compose 下，Docker 不拿它決定流量、也不拿它重啟，它的用途是顯示狀態、讓 Compose 決定啟動順序，以及給上面那幾類外部工具讀；Swarm 模式下它決定任務何時開始接流量、何時被取代。不論是 `docker run`、Compose 還是 Swarm，`HEALTHCHECK` 都只有一個健康狀態，沒有 Kubernetes 那樣分開的 readiness 與 liveness。

## depends_on 的 service_healthy 把關的時機與連鎖失敗

Compose 的 `depends_on` 可以要求依賴的服務達到某個條件才啟動自己：

```yaml
depends_on:
  postgres:
    condition: service_healthy   # 等 postgres 的健康狀態變成 healthy
  cache:
    condition: service_started   # 只等它啟動，不看健康狀態
```

`service_healthy` 解決的是啟動順序：資料庫還在初始化時，應用程式不會先起來然後連線失敗。它的作用範圍只有「啟動或重建設了這個 `depends_on` 的服務（上例的應用程式）的那一刻」。依賴的服務在之後變成 unhealthy，已經在跑的服務不受影響，Compose 不會因此停掉或重啟它。

這個時間點上的限制會帶出一個連鎖失敗。把入口的反向代理設成等所有上游 `service_healthy`，然後讓其中一個前端變成 unhealthy，再重建入口：

```text
Container portal-1 Error dependency portal failed to start
dependency failed to start: container portal-1 is unhealthy
```

入口的容器停在 `created`，沒有啟動。一個前端頁面壞掉，結果整個站的入口在下一次部署或重啟時起不來，其他正常的服務也連帶進不去。改成 `service_started` 之後，同樣的情形下入口照常啟動，只有壞掉的那個前端所在的路徑出錯。

判斷要用哪一個條件，問的是「依賴的服務不健康時，這個服務啟動起來還有沒有用」：

- **沒有用**：後端沒有資料庫就無法服務任何請求，等資料庫 `service_healthy` 合理。
- **有用**：入口後面有多個上游，其中一個壞了，其他路徑仍然要能服務。這時用 `service_started` 只排順序，上游的故障留給入口在請求當下處理（那條路徑回 502）。

`service_started` 有一個前提：入口在啟動時不需要連上上游。Nginx 在載入設定時就要解析 `upstream` 裡的主機名，解析不到會直接拒絕啟動（實測訊息是 `host not found in upstream`）；`service_started` 保證上游的容器已經建立、名字解析得到，所以上游只是 unhealthy 時入口起得來，但上游的容器根本沒建立起來時，入口一樣起不來。要讓入口連這一點都不依賴，要把上游的解析延到請求當下（Nginx 用 `resolver` 加上變數形式的 `proxy_pass`）。

`docker compose up` 遇到 `dependency failed to start` 時以非零結束碼結束（實測結束碼 1），所以部署腳本看得到失敗；從錯誤訊息看不出的是影響範圍——訊息點名的是壞掉的前端，起不來的卻是入口。

部署流程要在當下就確認服務健康，可以用 `docker compose up -d --wait --wait-timeout 60`：它會等所有啟動的服務變成 healthy 才結束，任一個變成 unhealthy 就以結束碼 1 結束（實測健康檢查一開始就失敗的服務，7 秒後回報 `container ... is unhealthy`，不必等滿逾時）。`60` 是範例，換成服務正常啟動需要的最長秒數。

## 沒有 shell 的映像檔怎麼做健康檢查

健康檢查的指令在容器裡執行，所以容器裡要有能執行它的工具，而映像檔帶了哪些工具隨映像檔與它的變體而不同：實測官方的 Nginx 與 PHP 映像檔帶著 `curl`，Valkey 的 Alpine 版只有 `wget`、Debian 版兩者都沒有。資料庫與快取這類不講 HTTP 的服務，健康檢查改用它們自己的指令列工具（`pg_isready`、`valkey-cli ping`）。手上的映像檔有什麼，用 `docker run --rm --entrypoint sh <映像檔> -c 'command -v curl wget'` 查一次就知道（`<映像檔>` 換成映像檔名稱與標籤）。這條指令要靠映像檔裡的 `sh` 執行，它本身失敗時，代表那是一個連 shell 都沒有的映像檔：為了縮小攻擊面而選用的 distroless 映像檔就是這樣，`CMD-SHELL` 與 `curl` 都用不了。

常見的做法是讓服務的執行檔自己兼任檢查的客戶端：帶一個參數啟動時不開伺服器，改成對本機的健康端點發一次請求，用結束碼回報。以 Go 為例，`main` 裡先處理這個參數：

```go
healthcheck := flag.Bool("healthcheck", false, "請求本機的 /healthz，成功時結束碼 0，失敗時 1")
flag.Parse()
if *healthcheck {
    // 逾時比 compose 的 timeout 短，Docker 判逾時之前就能留下錯誤訊息
    client := http.Client{Timeout: 2 * time.Second}
    resp, err := client.Get("http://127.0.0.1:8080/healthz")
    if err != nil || resp.StatusCode != http.StatusOK {
        os.Exit(1)
    }
    os.Exit(0)
}
```

Compose 裡用 exec 形式呼叫同一支執行檔（exec 形式不經過 shell，distroless 裡也能執行）：

```yaml
healthcheck:
  test: ["CMD", "/server", "-healthcheck"]
```

`/server` 是執行檔在映像檔裡的路徑，`-healthcheck` 是上面定義的參數名稱，兩者都要換成手上服務的實際值。這個做法不增加映像檔的內容，檢查的也是服務自己的 HTTP 端點；代價是健康檢查的邏輯寫進了應用程式碼，換語言或換框架時要跟著改。另一種做法是把一個靜態編譯的小型檢查工具複製進映像檔，邏輯與應用程式分開，但映像檔多了一個要維護的檔案。

## 容器健康檢查看不到的範圍

容器的健康檢查在容器自己裡面執行，所以它回答的是「這個容器自己的端點能不能回應」。它看不到兩件事：別的容器透過網路連不連得到它，以及請求經過入口的路由之後能不能到達它。另外，狀態變了之後沒有人被通知，除非有工具去讀它。

這兩件事要靠從外部探測的工具補上：另一個容器定期從網路對各服務發請求，並把結果彙整成儀表板或告警。多容器服務怎麼把容器內的檢查、外部探測與指令列查詢分工，見 [多容器服務的存活監看](/operations/04-service-health/multi-container-monitoring/)。
