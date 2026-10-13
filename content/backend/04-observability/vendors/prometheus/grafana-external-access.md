---
title: "Grafana 的對外存取：SSH 通道、監控主機上的反向代理，與經由應用入口轉送的對照"
date: 2026-10-13
description: "Grafana 只綁本機之後，讓其他人看到它的做法：看的人有沒有主機帳號時各自的存取方式，SSH 通道的連法，監控主機上專用反向代理的 TLS、WebSocket、GF_SERVER_ROOT_URL 與來源限制，應用入口 Nginx 加上 Grafana 的轉送之後在多台主機時起不來的原因，以及登入頁對外之後的帳號鎖定與認證放置"
weight: 16
tags: ["backend", "observability", "vendor", "prometheus", "grafana"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列，接在 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 之後：那一篇把 Prometheus、Alertmanager 與 Grafana 放在一台監控主機上，三者的連接埠沿用 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 〈連接埠與資源用量〉的做法，只綁在那台主機的 `127.0.0.1`。

這一篇整理 Grafana 只綁本機之後，讓其他電腦上的人看到它的做法，範圍是自己架設的 Grafana；託管服務的登入與網域由供應商處理，不在這裡。文中的設定取自一個短網址服務的監控（Grafana 13.2.3、Nginx 1.30），在 macOS 的 OrbStack 上實測過；雲端上的部分（DNS、正式憑證、負載平衡器）沒有實際部署過，寫的是要改的位置。

## SSH 通道與對外代理的選擇條件：看的人有沒有主機帳號

Grafana 綁在 `127.0.0.1:3000` 時，只有在監控主機上的程式連得到它。讓別台電腦上的人看到它有兩類做法，分別對應兩種讀者：

- **要看的人有這台主機的 SSH 或 VPN 帳號**：在他自己的電腦上開一條 SSH 通道，或者經由 VPN 連進主機所在的網路。Grafana 的連接埠不對外，登入頁不出現在網際網路上，也不必準備網域與憑證。
- **要看的人沒有主機帳號**：主管、行銷或外部合作方只需要看儀表板，不該拿到能登入主機的帳號。這時 Grafana 要以一個網域、經過 HTTPS 對外，前面放一個反向代理處理 TLS 與來源限制。

兩者的差別在於誰承擔「這個人能不能連進來」的判斷。SSH 與 VPN 由既有的主機帳號判斷，對外的做法則把判斷交給 Grafana 的登入頁加上代理的來源限制，而登入頁一旦對外，就會被掃描與猜密碼（見〈登入頁對外之後的帳號鎖定與認證放在哪裡〉）。所以只有工程師要看時，SSH 通道就夠；「沒有主機帳號的人也要看」是加反向代理的觸發條件，在那之前把代理的設定檔準備好，但不放進預設的啟動組合。

## SSH 通道的連法

SSH 的本機轉送（local forwarding）在自己的電腦上開一個連接埠，把連到這個連接埠的連線經由 SSH 連線轉到遠端主機上指定的位址。用在 Grafana 上時，遠端的位址正是它綁的 `127.0.0.1:3000`：

```sh
# -L 本機連接埠:遠端主機上看到的位址:連接埠；monitor-1 換成監控主機的位址或 ~/.ssh/config 裡的名稱
# -N 只轉送、不開遠端的 shell
ssh -N -L 3000:127.0.0.1:3000 monitor-1
```

通道開著時，瀏覽器開自己電腦上的 `http://127.0.0.1:3000` 就是監控主機上的 Grafana。`-L` 中間那一段的 `127.0.0.1` 由遠端主機解讀，指的是監控主機自己，所以 Grafana 不必改綁其他介面；自己電腦上的 3000 已被占用時，改前面那一段的本機連接埠（例如 `-L 13000:127.0.0.1:3000`），瀏覽器改開 13000。這條指令是 SSH 的標準用法，那個短網址服務的驗證只在單機上做，沒有實際從另一台電腦連過監控主機。

VPN（例如 Tailscale、WireGuard）是另一種沒有對外連接埠的做法：Grafana 改綁在 VPN 介面的位址上（compose 的 `ports` 寫成 `"<VPN 位址>:3000:3000"`），VPN 裡的人直接開那個位址。團隊已經有 VPN 時，每個人不必各自開通道。

## 監控主機上的反向代理

沒有主機帳號的人也要看時，在監控主機上、和 Grafana 同一個 compose 專案裡加一個只服務 Grafana 的 Nginx。它放在監控主機而不是應用的入口，理由在〈經由應用入口 Nginx 轉送的做法與它在多台主機時的問題〉；這一節先看它的設定。

代理以一個可選的 compose 檔加進來，監控主機的 `COMPOSE_FILE` 結尾加上它才會啟動。以下的路徑沿用那個短網址服務的目錄配置（範本放在 `infra/observability/grafana-proxy/templates/`），換成自己專案裡放這些檔案的位置：

```yaml
# compose.grafana-proxy.yml
services:
  grafana-proxy:
    image: nginx:1.30-alpine
    restart: unless-stopped
    environment:
      GRAFANA_DOMAIN: ${GRAFANA_DOMAIN:?設成開 Grafana 用的網域}
      GRAFANA_ALLOW_CIDR: ${GRAFANA_ALLOW_CIDR:?設成允許連進來的網段}
    ports:
      - "443:443"
    volumes:
      - ./infra/observability/grafana-proxy/templates:/etc/nginx/templates:ro
      - ${GRAFANA_TLS_DIR:?設成放 fullchain.pem 與 privkey.pem 的目錄}:/etc/nginx/tls:ro
    depends_on:
      - grafana

  grafana:
    environment:
      GF_SERVER_ROOT_URL: https://${GRAFANA_DOMAIN}/
```

三個變數都寫成 `${VAR:?訊息}`，沒設就讓 `docker compose` 在啟動前停下並印出訊息，不會帶著空的網域或空的網段起來。`grafana` 那一段併進 `compose.monitoring.yml` 裡已有的 Grafana：compose 把同名的服務合併，這一段只替它多加一個環境變數。

`GF_SERVER_ROOT_URL` 是 Grafana 對外的網址。Grafana 產生絕對網址時以它為準：登入之後轉回原頁面、OAuth 登入的回呼網址、告警通知裡指回面板的連結。沒設時預設是 `http://localhost:3000/`，經過代理的使用者會在這些位置被帶到他自己電腦上的 localhost。

Nginx 的設定放在 `templates/` 底下，檔名以 `.template` 結尾。官方的 nginx 映像啟動時以 `envsubst` 把範本裡的 `${GRAFANA_DOMAIN}` 這類環境變數換成實際值，輸出到 `/etc/nginx/conf.d/`；`$host`、`$http_upgrade` 這些是 Nginx 自己的變數，不是容器的環境變數，原樣保留。

```nginx
# templates/grafana.conf.template

# Grafana Live 以 WebSocket 推送面板更新：請求帶 Upgrade 時轉成升級連線，沒帶時照一般請求轉送
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl;
    server_name ${GRAFANA_DOMAIN};

    ssl_certificate     /etc/nginx/tls/fullchain.pem;
    ssl_certificate_key /etc/nginx/tls/privkey.pem;

    # 只讓來自這個網段的連線進來，其他來源回 403
    allow ${GRAFANA_ALLOW_CIDR};
    deny all;

    location / {
        proxy_set_header Host $host;          # Grafana 依 Host 判斷請求的網域
        proxy_pass http://grafana:3000;
    }

    location /api/live/ {
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_pass http://grafana:3000;
    }
}

# 用 IP 直接連、或帶了其他網域時，關掉連線、不回應任何內容
server {
    listen 443 ssl default_server;
    ssl_certificate     /etc/nginx/tls/fullchain.pem;
    ssl_certificate_key /etc/nginx/tls/privkey.pem;
    return 444;
}
```

`/api/live/` 那一段處理的是 Grafana Live：Grafana 以 WebSocket 把資料推到開著的面板，WebSocket 連線從一個帶 `Upgrade: websocket` 的 HTTP 請求開始。Nginx 轉送時預設使用 HTTP/1.0 而且不轉送 `Upgrade` 與 `Connection` 這兩個逐跳（hop-by-hop）的標頭，所以要明確寫出 HTTP/1.1 與這兩個標頭。實測拿掉這一段時，`/api/live/ws` 的升級請求由 Grafana 回 400；加上之後回 101（協定切換成功）。一般的儀表板查詢走普通的 HTTP，不受影響，所以漏掉這一段時畫面看起來正常，只是即時推送的部分沒有更新。

`return 444` 是 Nginx 自訂的狀態碼，意思是不回應、直接關掉連線。網際網路上的掃描多半以 IP 直接連，或帶著別的網域；這些請求落到 `default_server`，看不到 Grafana 的登入頁。

憑證在雲端上由 Let's Encrypt 這類 CA 簽發，放進 `GRAFANA_TLS_DIR`；簽發與續期的流程見 [域名與 HTTPS 怎麼接上](/going-live/domain-and-https/) 的〈憑證怎麼拿：Let's Encrypt 讓它免費又自動〉。本機測試用自簽憑證，`*.localhost` 在瀏覽器與 curl 都解析到本機：

```sh
# 自簽一張 30 天的 grafana.localhost 憑證；這個目錄要列在 .gitignore，私鑰不進版本控制
mkdir -p infra/observability/grafana-proxy/tls
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=grafana.localhost" \
  -addext "subjectAltName=DNS:grafana.localhost" \
  -keyout infra/observability/grafana-proxy/tls/privkey.pem \
  -out infra/observability/grafana-proxy/tls/fullchain.pem
```

`.env` 加上 `GRAFANA_DOMAIN=grafana.localhost`、`GRAFANA_ALLOW_CIDR=0.0.0.0/0`（本機只能這樣設，理由見〈來源限制比對的是哪一個位址〉）與 `GRAFANA_TLS_DIR=./infra/observability/grafana-proxy/tls`，`COMPOSE_FILE` 結尾加上 `:compose.grafana-proxy.yml`，再 `docker compose up -d`。Grafana 因為多了環境變數會被重建，重建的那幾秒代理回 502。Nginx 在啟動時解析一次 `grafana` 的位址，之後沿用；之後只重建 Grafana（例如升級映像）而沒有重啟代理時，新的容器若拿到不同的 IP，代理會一直回 502，所以升級 Grafana 之後一併執行 `docker compose restart grafana-proxy`。

想用路徑而不是網域區分（例如 `https://ops.example.com/grafana/`）時，`GF_SERVER_ROOT_URL` 寫成含路徑的網址，並設 `GF_SERVER_SERVE_FROM_SUB_PATH=true`，Nginx 的 `location` 改成那個路徑。這是 Grafana 設定文件裡的做法，那個短網址服務沒有測過。獨立的網域讓 Grafana 的 cookie 與應用的 cookie 分屬不同網域，路徑的做法則共用同一個網域，所以能另開一個子網域時用獨立的網域，只有一個網域可用時才用路徑。

## 經由應用入口 Nginx 轉送的做法與它在多台主機時的問題

服務本身已經有一個入口 Nginx，最直接的想法是在那裡多加一個 `server_name` 轉給 Grafana。單機時這樣可行：應用與監控在同一個 compose 專案，入口以服務名稱 `grafana` 連得到它。拆成多台主機之後有兩個問題。

入口 Nginx 起不來。Nginx 在載入設定時解析 `proxy_pass` 裡的主機名稱，應用主機上沒有 `grafana` 這個服務，解析失敗。以 `nginx:1.30-alpine` 實測，`proxy_pass http://grafana:3000` 在找不到 `grafana` 時，`nginx -t` 回 `host not found in upstream "grafana"`，整個入口拒絕啟動，連帶短網址與前台都停掉。改成先設 `resolver` 再把位址放進變數（`set $g http://grafana:3000; proxy_pass $g;`），Nginx 改在請求當下才解析，啟動時不再報錯（實測 `nginx -t` 通過），但那只是把錯誤延到請求時變成 502；真正要的是讓入口跨主機轉送到監控主機，應用的入口因此依賴監控主機。

入口出事時監控跟著看不到。入口過載、設定改壞或被攻擊時，正是要開 Grafana 查原因的時候，而這時 Grafana 的入口和出問題的入口是同一個。監控主機上的專用代理和應用入口分開，入口出事不影響監控畫面；代價是單機上多一個對外的連接埠（443 給 Grafana、應用另有自己的連接埠），要把兩者合到同一個 443 時，得在兩者前面再放一層依網域分流的代理或負載平衡器。

## 來源限制比對的是哪一個位址

`allow` 與 `deny` 比對的是 Nginx 看到的來源位址，也就是 TCP 連線的另一端。這個位址等於使用者真正的位址，前提是連線直接到達這台主機。

- **Linux 主機直接收外部連線**：Docker 以 iptables 把連到發佈連接埠的封包轉給容器，保留原本的來源位址，`allow` 比對的就是使用者的位址。
- **macOS 上的 OrbStack**：容器跑在 Linux 虛擬機裡，連線經過虛擬機的網路轉送，Nginx 看到的全是虛擬機的閘道位址。實測 `GRAFANA_ALLOW_CIDR` 設成不含本機的網段時，Nginx 回 403，日誌記下的來源是虛擬機的閘道位址（每台安裝不同，在 Nginx 的 access log 裡看得到）。本機測試因此只能設成 `0.0.0.0/0`，限制的效果要到 Linux 主機上才看得到。Docker Desktop 同樣把容器放在虛擬機裡，這裡沒有實測它看到的來源位址。
- **前面還有雲端負載平衡器**：連線的另一端是負載平衡器，Nginx 看到的是負載平衡器的私有位址，`allow` 寫使用者的網段會擋掉所有人。這時用 Nginx 的 `real_ip` 模組，在 `set_real_ip_from` 寫負載平衡器的網段、`real_ip_header X-Forwarded-For`，讓 Nginx 改用負載平衡器填的來源位址；或者把來源限制移到負載平衡器或安全群組（security group），代理只負責 TLS 與轉送。

## 登入頁對外之後的帳號鎖定與認證放在哪裡

對外之後，判斷誰能看的是 Grafana 自己的登入。Grafana 預設開著登入失敗的保護：實測同一個帳號連續 5 次密碼錯誤之後，第 6 次起連正確的密碼也回 401，回應的內容和密碼錯誤時相同，原因只寫在 Grafana 的日誌裡（`too many consecutive incorrect login attempts for user`）。鎖定是暫時的：實測鎖住 3 分鐘時仍然登不進去，6 分半時已經可以登入。這個保護擋住對單一帳號的猜測，而它的副作用是有人持續猜 `admin` 的密碼時，管理者自己也登不進去，且從畫面上分不出是密碼錯還是被鎖。來源限制先擋掉網段外的連線，能觸發這個鎖定的就只剩允許網段裡的人。

認證可以放在三個位置，選擇看組織裡已經有什麼：

- **Grafana 的帳號與密碼**：預設的做法，適合組織沒有集中的身分系統、看的人不多時。每個人一組 Grafana 帳號，看畫面的人給 Viewer 角色。帳號由 Grafana 管理，離職時要另外停用。
- **Grafana 的 OAuth 登入**：公司已經有 Google Workspace、Microsoft Entra ID 或 GitHub 組織時，Grafana 以 OAuth 把登入交給它們，可以依群組對應角色。帳號跟著公司的身分系統走，這時 `GF_SERVER_ROOT_URL` 必須正確，OAuth 的回呼網址由它產生。
- **代理前面的身分驗證服務**：組織已經用雲端負載平衡器的身分驗證、Cloudflare Access 這類服務保護其他內部工具時，同一套服務在請求到達 Grafana 之前先驗證身分，Grafana 以 auth proxy 模式讀代理填入的使用者名稱標頭。這時 Grafana 完全信任那個標頭，只能接受來自代理的連線，否則任何人自己填一個標頭就能登入。

## 驗證：在單機上重現的結果

以下是在那個短網址服務上，把 `compose.grafana-proxy.yml` 加進單機的 `COMPOSE_FILE` 之後的實測，每一項對應上面一個設定：

- `https://grafana.localhost/api/health` 回 Grafana 的健康狀態，代理到 Grafana 的轉送通了。
- `https://grafana.localhost/` 回 302，轉到 `https://grafana.localhost/login`：轉址的網址來自 `GF_SERVER_ROOT_URL`。
- 帶 WebSocket 升級標頭請求 `/api/live/ws` 回 101；另起一個只有 `location /` 的 Nginx 轉送同一個請求，Grafana 回 400。
- `GRAFANA_ALLOW_CIDR` 設成 `10.99.0.0/16` 時回 403，日誌的來源位址是 OrbStack 的閘道。
- 必要的變數沒設時，`docker compose config` 停在 `required variable GRAFANA_DOMAIN is missing a value`，並印出 compose 檔裡寫的提示。
- `admin` 連續 5 次錯誤密碼之後，正確的密碼也回 401，Grafana 日誌記下 `too many consecutive incorrect login attempts`；6 分半之後正確的密碼回 200。

沒有驗證的部分：從另一台電腦經 SSH 通道連進來、正式 CA 簽發的憑證、Linux 主機上 `allow` 比對到真實來源位址、負載平衡器後面的 `real_ip` 設定，以及路徑形式的 `GF_SERVER_SERVE_FROM_SUB_PATH`。

## 延伸閱讀：Grafana 的角色、監控主機的位置與 Grafana 本身的設定

- 為什麼對外開的是 Grafana 而不是 Prometheus：Prometheus 與 Alertmanager 只有 basic auth、通過的人擁有完整權限，Grafana 有 Viewer 這種只能看的角色，見 [Prometheus 指標的視覺化工具](/backend/04-observability/vendors/prometheus/visualization-tool-selection/) 的〈Grafana〉一節講存取控制的那一段。
- 監控主機和應用主機分開之後，代理跟著 Grafana 放在監控主機；兩者放在同一台與分開的取捨，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 的〈監控主機放在哪裡〉。
- Grafana 本身的設定（資料來源與儀表板的佈建、`/var/lib/grafana` 的 volume、admin 密碼只在第一次建立資料庫時生效），見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 的〈Grafana：以檔案佈建資料來源與儀表板〉。
