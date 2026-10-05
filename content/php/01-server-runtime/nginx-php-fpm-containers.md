---
title: "容器裡的 Nginx 與 PHP-FPM：拆成兩個容器與放進同一個容器的做法與各自的陷阱"
date: 2026-10-05
description: "說明把 Nginx 與 PHP-FPM 放進容器的兩種擺法：官方 php-fpm 映像檔替容器改掉的預設值（log 導向、clear_env、監聽位址、停機訊號），拆成兩個容器時程式碼要兩邊都有、否則靜態檔會被 PHP 回成 200 的 HTML，以及放進同一個容器時要自己處理的程序監看、停機訊號轉送與 FastCGI 的監聽範圍"
weight: 7
tags: ["php", "php-fpm", "nginx", "docker", "deployment"]
---

這篇說明在容器裡跑 Nginx 加 [PHP-FPM](/php/01-server-runtime/php-fpm/) 的兩種擺法，以及各自要處理的問題。PHP-FPM 只講 [FastCGI](/php/01-server-runtime/fastcgi/)，所以前面一定要有一個講 HTTP 的 web 伺服器，這兩個程序怎麼放進容器就成了部署時第一個要決定的事。文中的行為取自官方的 `php:8.5-fpm-alpine` 與 `nginx:1.30-alpine` 映像檔。

## 兩種擺法

| 擺法           | 容器                                           | 對外講的協定        |
| -------------- | ---------------------------------------------- | ------------------- |
| 拆成兩個容器   | 一個 Nginx、一個 PHP-FPM，用容器網路連 FastCGI | Nginx 容器講 HTTP   |
| 放進同一個容器 | 一個容器裡同時跑 Nginx 與 PHP-FPM              | 這個容器自己講 HTTP |

拆成兩個容器符合「一個容器一個職責」的慣例（見 [Container per Service](/backend/knowledge-cards/container-per-service/)）：Nginx 與 PHP-FPM 可以各自更新映像檔、各自看 log、各自重啟。放進同一個容器則讓這個 PHP 服務對外就是一個講 HTTP 的單位，這在兩種情況下有用：平台只接受「一個容器、一個 HTTP 埠」的服務（多數 PaaS 與 serverless 容器平台），以及要把 PHP 服務跟其他講 HTTP 的後端一起放進同一個負載平衡的 upstream——一個 upstream 只能用一種協定轉送，Nginx 的 `proxy_pass`（HTTP）與 `fastcgi_pass`（FastCGI）不能混在同一個 upstream 裡。

「拆成兩個容器」指的是兩個容器仍然部署在一起：同一個 compose 專案，或 Kubernetes 的同一個 pod。同一個 pod 裡的容器共用網路（Nginx 用 `127.0.0.1:9000` 連 PHP-FPM），也能共用一個 volume 放程式碼，由 Kubernetes 分別監看兩個容器，不必手寫下面〈放進同一個容器〉那一節的腳本。拆成兩個獨立部署、跨 pod 連 FastCGI 也做得到，但 9000 就得在叢集網路上開放，要另外用 NetworkPolicy 之類的機制限制只有 Nginx 連得到。

兩種擺法共用同一個起點：官方的 php-fpm 映像檔。

## 官方 php-fpm 映像檔替容器改掉的預設值

PHP-FPM 原本是為「裝在一台伺服器上、由 systemd 管理」設計的，它的預設值有幾項在容器裡不適用。官方映像檔用一個 `php-fpm.d/docker.conf` 把它們改掉：

```ini
[global]
error_log = /proc/self/fd/2      ; 錯誤 log 寫到 stderr，docker logs 才看得到

[www]
access.log = /proc/self/fd/2     ; 存取 log 也寫到 stderr（PHP-FPM 啟動時會關掉 stdout）
clear_env = no                   ; 把容器的環境變數交給 worker
catch_workers_output = yes       ; worker 的輸出也收進主 log
listen = 9000                    ; 聽所有網路介面的 9000
```

另外映像檔設了 `STOPSIGNAL SIGQUIT`，`docker stop` 送給它的是 SIGQUIT 而不是預設的 SIGTERM。SIGQUIT 是 PHP-FPM 的 graceful stop，SIGTERM 是立即終止。但 graceful stop 要等進行中的請求多久，由 `process_control_timeout` 決定，**而它的預設值是 0**：只靠 STOPSIGNAL，`docker stop` 時進行中的請求仍然拿到 502。實測與設定方式見 [PHP-FPM 的停機與重載的訊號](/php/01-server-runtime/php-fpm/#停機與重載的訊號)。映像檔沒有改這個值，所以要在自己的設定檔加上：

```ini
[global]
; 停機與 reload 時，最多等進行中的請求這麼久；要比最長的正常請求長，比平台的停機逾時短
process_control_timeout = 10
```

其中 `clear_env` 最容易在自己寫設定時改壞。PHP-FPM 自己的預設是 `clear_env = yes`：worker 啟動時清掉所有環境變數，PHP 程式用 `getenv()` 讀不到。而容器的設定慣例正是用環境變數傳進去（資料庫密碼、`APP_KEY`）。同一個容器帶著 `APP_KEY=secret-from-env` 啟動，只改這一個設定：

```text
clear_env = no   →  getenv("APP_KEY") = 'secret-from-env'
clear_env = yes  →  getenv("APP_KEY") = false
```

沒有任何錯誤訊息，程式讀到的是 `false`。自己寫 pool 設定或從非容器環境搬一份 `www.conf` 進來時，要確認這一行還是 `no`。

## 拆成兩個容器：Nginx 這一側也要有程式碼

拆成兩個容器時，最容易漏的是**程式碼要兩邊都有**。理由是兩個容器各自要用到檔案，用途不同：

- **PHP-FPM 容器要有 PHP 檔**：Nginx 送來的 `SCRIPT_FILENAME` 是一個路徑，PHP-FPM 在**自己的**檔案系統裡找這個路徑去執行。
- **Nginx 容器要有靜態檔**：CSS、JS、圖片由 Nginx 直接從**自己的**檔案系統回，不經過 PHP。`try_files` 判斷檔案存不存在，也是看 Nginx 自己的檔案系統。

只把程式碼掛進 PHP-FPM 容器，而 Nginx 容器沒有，一般的 Laravel 式設定（`try_files $uri /index.php$is_args$args`）不會報錯，而是給出錯的內容。請求 `/app.css`：

```text
# Nginx 容器沒有程式碼
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
（內容是 index.php 產生的頁面）

# Nginx 容器也掛上同一份程式碼
HTTP/1.1 200 OK
Content-Type: text/css
body{}
```

Nginx 在自己的檔案系統找不到 `app.css`，`try_files` 就照設定退回給 `index.php`，於是 PHP 回了一頁 HTML，狀態碼 200。監控看到的是全部成功，瀏覽器看到的是樣式全部消失。做法有兩種：用同一個 volume 把程式碼同時掛進兩個容器；或者正式部署時在建置映像檔的階段，把 `public/` 底下的靜態檔複製一份進 Nginx 的映像檔。兩個容器裡的路徑也要一致（例如都是 `/var/www/html`），因為 Nginx 組出來的 `SCRIPT_FILENAME` 是拿自己的 `root` 拼的，PHP-FPM 要能在同一個路徑找到檔案。

另一件事是 FastCGI 埠的暴露範圍。映像檔的 `listen = 9000` 聽所有網路介面，在 compose 網路裡 Nginx 才連得到它。PHP 官方文件明寫 php-fpm 不能讓不受信任的網路連到——FastCGI 沒有驗證，連得到 9000 的人能指定 PHP 執行哪個檔案。所以 compose 裡 PHP-FPM 服務不寫 `ports:`，9000 只在容器網路內可達。

## 放進同一個容器：要自己做程序監看

同一個容器裡跑兩個程序，容器的主程序（PID 1）就不能直接是 `php-fpm` 或 `nginx`，要有一支腳本把兩個都啟動起來。這支腳本要負責三件事，而三件都是單一程序的容器不必想的。

**任一個程序結束，整個容器也要結束。** 只剩一半在跑的容器最難排查：Nginx 還活著，PHP-FPM 已經掛了，每個請求都回 502，而容器的狀態仍是 running，平台不會重啟它。腳本要等待任一個子程序結束，然後停掉另一個、讓自己結束。shell 的 `wait -n` 做的就是「等任一個子程序結束」，但 Alpine 預設的 busybox sh（1.37）在這裡有一個陷阱：子程序被訊號殺掉時（`kill -9`、記憶體不足被系統終止），它的 `wait -n` 不會返回，正好漏掉崩潰這個最需要偵測的情況。換成 bash 的 `wait -n`，子程序被 `kill -9` 時會立刻返回、帶著狀態碼 137。

**把停機訊號轉給兩個程序。** `docker stop` 只把訊號送給 PID 1，也就是這支腳本，shell 不會自動轉給子程序。腳本要接住訊號、自己轉送。這裡有一個連帶的細節：映像檔設了 `STOPSIGNAL SIGQUIT`，所以腳本收到的是 QUIT。只寫 `trap ... TERM` 的腳本接不到它，而 PID 1 對沒有註冊處理器的訊號一律忽略，結果 `docker stop` 要等滿 10 秒的逾時才強制終止——實測只接 TERM 時 `docker stop` 花 10 秒，加上 QUIT 之後 1 秒完成。

**把 FastCGI 只開給容器內部。** 兩個程序在同一個容器裡，Nginx 用 `127.0.0.1:9000` 連 PHP-FPM 就夠了，FastCGI 不必聽在網路介面上。映像檔的 `listen = 9000` 設在 `docker.conf`，在 `php-fpm.d/` 底下放一個檔名排在它後面的設定檔（例如 `zzz-listen.conf`）覆蓋它：

```ini
[www]
listen = 127.0.0.1:9000
```

`php-fpm.d/` 底下的檔案依檔名順序讀取，後讀到的設定覆蓋前面的，所以檔名要排在 `docker.conf` 之後。

這三件事寫成 entrypoint 腳本：

```bash
#!/bin/bash
# 用 bash：busybox sh 的 wait -n 在子程序被訊號殺掉時不返回

# docker stop 送來的是 SIGQUIT（映像檔的 STOPSIGNAL），一併接 TERM 與 INT
stop() {
    kill -QUIT "$fpm" "$web" 2>/dev/null   # 兩者的 graceful stop；PHP-FPM 要設 process_control_timeout 才會等
}
trap stop QUIT TERM INT

php-fpm -F &                               # -F：前景執行，讓這支腳本當它的父程序
fpm=$!
nginx -e stderr -g 'daemon off;' &         # -e stderr：讀設定之前的錯誤 log 也寫到 stderr
web=$!

wait -n                                    # 任一個結束就往下走
status=$?
stop                                       # 停掉另一個
wait
exit "$status"
```

映像檔要另外裝 bash 與 nginx（`apk add bash nginx`）。以非 root 使用者執行時，Nginx 的 pid 檔與暫存目錄要放在那個使用者寫得進去的位置（例如 `/tmp`），監聽的埠也要用 1024 以上。

這組驗證值得在建好映像檔時跑一次，因為三件事出錯時容器都照樣啟動、照樣回應：用 `kill -9` 分別殺掉 PHP-FPM 與 Nginx 的 master，確認容器在幾秒內結束；量 `docker stop` 的時間，確認不是 10 秒；從容器外面連 9000，確認連線被拒。

## 兩種擺法的選擇

兩種擺法的差別落在「誰負責程序監看」：拆成兩個容器時，平台（compose、Kubernetes）監看每個程序，每個容器只有一個主程序，失敗時平台看得到；放進同一個容器時，這份責任移進了 entrypoint 腳本，上面那三件事都要自己做對。

放進同一個容器時，手寫腳本之外也可以用 process supervisor（s6-overlay、supervisord）管理兩個程序，由它負責監看與回收結束的子程序，代價是映像檔多一個相依；手寫腳本的好處是沒有額外相依，三件事都看得到。

所以預設是拆成兩個容器；只有在平台只接受單一 HTTP 容器、或要讓 PHP 服務跟其他 HTTP 後端進同一個 upstream 時，才放進同一個容器，並把上面的驗證當成映像檔的驗收條件。兩種擺法都繼承 PHP-FPM 的 shared-nothing 模型；不再每個請求重新啟動框架的做法是另一個執行模型，見 [常駐 worker 模型](/php/01-server-runtime/long-running-workers/)。
