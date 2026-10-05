---
title: "PHP-FPM：常駐 PHP worker 的程序管理與主要的調校旋鈕"
date: 2026-10-05
description: "說明 PHP-FPM 怎麼管理一群常駐的 PHP worker：pool 怎麼做到每個站台不同執行帳號、pm 的三種開程序策略、max_children 如何決定並發上限與請求排隊、max_requests 定期換掉 worker 控制記憶體、request_terminate_timeout 與 slowlog 怎麼處理跑太久的請求、status 頁怎麼讀，以及每一項對壓測數字的影響"
weight: 5
tags: ["php", "php-fpm", "fastcgi", "deployment"]
---

這篇說明 PHP-FPM 要解決的問題，以及它主要的設定旋鈕在做什麼。PHP-FPM 是 [FastCGI](/php/01-server-runtime/fastcgi/) 協定在 PHP 這一側的程序管理實作，全名 FastCGI Process Manager。前面幾種執行模型各自留下一個沒回答的問題：[CGI](/php/01-server-runtime/cgi/) 每個請求啟動一個程序、成本太高；[mod_php](/php/01-server-runtime/mod-php/) 省掉啟動成本、卻讓 PHP 綁死在 web 伺服器的程序與執行帳號上。PHP-FPM 的答案是一群常駐的 PHP worker，而「常駐」帶出一個新問題：誰來管這群程序。文中的行為取自 `php:8.5-fpm-alpine`。

## 為什麼常駐程序需要一個管理者

FastCGI 要求應用程式程序常駐，於是出現幾個 CGI 下不存在的問題，因為 CGI 的程序活一個請求就結束、沒有機會累積：

- **開幾個程序**：太少，並發的請求要排隊；太多，記憶體吃光。
- **一個程序掛了誰補**：常駐的程序可能因為程式錯誤或記憶體不足而死掉，要有人把它補回來。
- **記憶體隨時間漲**：worker 活得久，C 擴充的記憶體洩漏會一點一點累積。
- **某個請求卡住**：一個跑不完的請求會一直佔著一個 worker，佔住的 worker 越多，能處理新請求的就越少。

PHP-FPM 就是處理這幾件事的常駐服務（見 [PHP-FPM](/php/knowledge-cards/php-fpm/)）。它的 PHP 版本記在官方 ChangeLog 裡：PHP 5.3.3（2010 年 7 月）的 ChangeLog 記著「Added FastCGI Process Manager (FPM) SAPI」，FPM 從這個版本起隨 PHP 本體發行。PHP-FPM 的架構是一個主程序（master）加一群 worker：master 不處理請求，只負責讀設定、開 worker、補死掉的 worker、轉送管理訊號；worker 才是實際執行 PHP 的程序。

PHP 官方文件對它有一句明確的安全要求：**php-fpm must not be reachable from an untrusted network**——FastCGI 的埠（預設 `9000`）不能對不受信任的網路開放。FastCGI 協定本身沒有驗證，誰連得上這個埠，誰就能指定 `SCRIPT_FILENAME` 要 PHP 執行哪個檔案（見 [FastCGI 的安全邊界](/php/01-server-runtime/fastcgi/#web-伺服器決定-php-執行哪個檔案)）。所以它只聽 `127.0.0.1` 或 Unix socket，或用 `listen.allowed_clients` 限制來源。

## pool：一組 worker 與它的執行身分

PHP-FPM 把 worker 分成一個或多個 **pool**，每個 pool 是一組設定相同的 worker，可以指定自己的執行帳號（`user` / `group`）、監聽位址（`listen`）、以及 PHP 設定。這一個機制解掉了 mod_php 最大的限制：

mod_php 的所有站台都以 Apache 的帳號執行，彼此的檔案互相看得到。PHP-FPM 讓每個站台一個 pool、各自指定執行帳號：

```ini
[site_a]
user = site_a
group = site_a
listen = /run/php/site_a.sock

[site_b]
user = site_b
group = site_b
listen = /run/php/site_b.sock
```

`listen` 可以是 Unix socket 的路徑（如上）或 `IP:埠`。web 伺服器與 PHP-FPM 在同一台機器、同一個檔案系統時可以用 Unix socket，少走一層 TCP；分在不同容器或不同機器時要用 TCP，這也是容器環境預設 `listen = 9000` 的原因。

`site_a` 的 PHP 以 `site_a` 的帳號執行，讀不到 `site_b` 的檔案，產生的檔案也屬於 `site_a`。這把 [CGI 加 suEXEC](/php/01-server-runtime/cgi/#cgi-在共享主機上留下來的理由) 才有的隔離，做在了常駐程序上——既有隔離，又沒有每個請求啟動程序的成本。這是共享主機從 CGI 換到 PHP-FPM 的主因。

## pm：開 worker 的三種策略

`pm` 決定 PHP-FPM 怎麼決定開幾個 worker，有三個值：

| `pm` 的值  | 行為                                                                                               | 適合                                        |
| ---------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `static`   | 固定開 `pm.max_children` 個 worker，一直都在                                                       | 流量穩定、記憶體足夠、要最可預測的延遲      |
| `dynamic`  | 在 `pm.min_spare_servers` 與 `pm.max_spare_servers` 之間，依閒置數量增減，上限是 `pm.max_children` | 流量有高低起伏                              |
| `ondemand` | 平常不開 worker，有請求才開，閒置超過 `pm.process_idle_timeout` 就收掉                             | 流量很低、或同一台機器上有很多不常用的 pool |

三者的上限都是 `pm.max_children`，差別只在平常保持幾個 worker 活著。`dynamic` 是預設，它的「動態」是 PHP-FPM 在常駐的 worker 群裡依閒置數量增減，不是每個請求開關程序，所以跟 CGI 的每請求一程序是兩回事。

容器裡的取捨跟整台伺服器不同。一個容器通常只跑一個 pool，而且 `max_children` 已經依容器的記憶體上限配好；這時 `dynamic` 省下的閒置記憶體別的程式也用不到，`static` 反而省掉流量上升時臨時開 worker 的延遲。

## max_children：並發上限與排隊

`pm.max_children` 是這個 pool 最多能同時存在的 worker 數量，也就是這個 pool 最多能同時處理幾個請求。一個 worker 一次只處理一個請求，所以超過這個數量的請求要排隊等。

這一點可以直接量。設 `pm = static`、`pm.max_children = 2`，然後同時送 6 個各需要 1 秒的請求：

```text
各請求完成的秒數：[1.06, 1.06, 2.07, 2.07, 3.08, 3.09]  總時間 3.1 秒
```

兩個 worker 同時處理兩個請求（約 1 秒完成），剩下的排隊：第三、四個等前兩個做完（約 2 秒），第五、六個再等一輪（約 3 秒）。這就是 `max_children` 太小時的樣子：請求都成功了，延遲隨排隊長度線性增加。

`max_children` 要設多大，由兩件事夾出來：

- **上界是記憶體**：每個 worker 都佔記憶體（框架越大佔越多）。`max_children` 乘上單一 worker 的記憶體，不能超過機器分給 PHP 的量，否則系統開始用 swap 或直接把程序殺掉。單一 worker 的記憶體要用**最重的那一類請求的峰值**估，不能用平均值：下面〈max_requests〉一節量到，worker 處理完一個重請求之後，記憶體會保留一段時間才降回來，而尖峰時可能每個 worker 剛好都處理過重請求。
- **下界是並發需求**：太小就像上面那樣排隊。需要多少並發，看請求把時間花在哪裡：大部分時間在等資料庫或外部 API 的請求，worker 等待時不佔 CPU，數量可以遠多於 CPU 核心數；大部分時間在計算的請求，worker 數超過核心數之後只增加切換成本，處理量不會再上升。

這是 PHP-FPM 最常調、也最該記進壓測結果的一個值。壓測時換了機器、換了框架、改了這個值，數字就不能跟之前比。

## max_requests：定期換掉 worker 以控制記憶體

`pm.max_requests` 讓一個 worker 處理滿指定數量的請求之後，自己結束，由 master 開一個新的 worker 補上。設 `pm.max_requests = 3`，對計數腳本連續請求，可以看到 PID 換掉：

```text
pid=7 static=1 ...
pid=7 static=1 ...
pid=7 static=1 ...
pid=8 static=1 ...     # PID 7 處理滿 3 個請求後，換成 PID 8
```

它防的是哪一種記憶體成長，要先把 worker 的記憶體分成兩類，因為兩類跨請求的行為不同。

**PHP 程式碼用的記憶體不會隨處理過的請求數增長，但會暫時停在高點。** PHP 程式碼建立的變數、陣列與物件，由 PHP 自己的記憶體管理器（Zend Memory Manager）配置，請求結束時全部釋放——這是 [shared-nothing](/php/knowledge-cards/shared-nothing-request/) 的一部分。不過「釋放」是釋放給記憶體管理器，不等於立刻還給作業系統，所以從作業系統看到的 RSS 不會馬上降。用一個只開一個 worker 的 pool，讓每個請求都落在同一個程序上，量它的 RSS（作業系統看到的實體記憶體佔用）：

```text
初始                                  rss=10MB
一個建立 50 萬筆小陣列的請求（PHP 峰值 210MB）
之後的小請求，依序：                  rss=112MB → 62MB → 36MB → 24MB → 18MB → 14MB → 14MB
```

請求早就結束了，RSS 卻停在 112MB，再隨後面的請求逐步降回約 14MB。原因在記憶體管理器的實作：它以 2MB 的 chunk 為單位向作業系統要記憶體，請求結束時不把 chunk 全部還回去，而是留下一部分給下一個請求用，省掉反覆向作業系統申請與歸還的成本。留下多少由一個移動平均決定，每個請求結束時更新成「上一次的平均與這次請求的峰值兩者的平均」，保留的 chunk 數跟著這個平均走。代入上面的量測：重請求之前平均接近 0，重請求的峰值約 210MB，這個請求結束時平均變成兩者的一半、約 105MB，所以保留了約 102MB；之後每個輕請求的峰值只有約 2MB，平均每次再減半。PHP 回報的記憶體依序是 102、52、26、14、8、4、2 MB，就是這個減半。這個調整只在請求結束時發生：worker 閒著沒有請求時，RSS 停在原來的值，不會隨時間自己降下來。單一一次配置超過約 2MB 的大區塊不走 chunk，請求結束時直接還給作業系統：一個配置 200MB 字串的請求結束後，RSS 立刻回到 12MB。

所以 worker 的 RSS 反映的是**最近處理過的請求的峰值**，不是它累計處理過幾個請求。重複「每 5 個輕請求夾 1 個重請求」六輪，每輪結束時的 RSS 都停在 14MB，沒有一輪比一輪高。

**真正會跨請求累積的，是 PHP 記憶體管理器以外的記憶體。** C 寫的擴充與它們依賴的函式庫，有一部分記憶體直接向作業系統的配置器要，不經過 Zend Memory Manager，也不在請求結束時被清掉。這一類有洩漏時，worker 的 RSS 會隨處理過的請求數一路往上，不會降回來。`max_requests` 防的是這一類：與其逐一追查是哪個擴充在漏，讓 worker 處理一定數量的請求後整個換掉，舊程序累積的記憶體隨它結束一起還給作業系統。代價是新 worker 的 OPcache 命中要重新累積（見 [OPcache 與程序壽命](/php/01-server-runtime/opcache/)），所以這個值不設太小。

這兩類的分別給出一個判讀方法：在穩定的負載下，觀察 worker 的 RSS **在輕請求之後回落到的底部**。底部固定，代表成長來自重請求的暫時保留，`max_requests` 不必設；底部隨時間一路往上，代表有 PHP 記憶體管理器以外的洩漏，這才是 `max_requests` 要處理的情形。

## request_terminate_timeout 與 slowlog：跑太久的請求

一個卡住的請求會一直佔著一個 worker。佔住的 worker 越多，`max_children` 裡能處理新請求的名額就越少，到最後整個 pool 都卡在慢請求上，新請求全部排隊。PHP-FPM 有兩個設定處理這件事。

`request_terminate_timeout` 是強制上限：一個請求跑超過這個時間，PHP-FPM 直接終止處理它的 worker。設 `request_terminate_timeout = 3s`，對一個會跑 5 秒的請求：

```text
$ curl -o /dev/null -w "%{http_code} after %{time_total}s" localhost/sleep.php?s=5
502 after 3.24s
```

PHP-FPM 的 log 記下整個過程：

```text
WARNING: child 11, script 'sleep.php' execution timed out (3.2 sec), terminating
WARNING: child 11 exited on signal 15 (SIGTERM) ...
```

而 Nginx 這一側，因為 worker 被終止、連線斷掉，記下：

```text
[error] recv() failed (104: Connection reset by peer) while reading
  response header from upstream
```

這解釋了一個常見的現象：前端收到 502 Bad Gateway，但 Nginx 的 log 寫的是「連線被 upstream 重設」——因為 PHP-FPM 為了保護 worker 名額，主動把那個卡住的 worker 殺掉了。5xx 還有另一個常見成因跟逾時無關：worker 全忙時新請求在佇列裡排隊，延遲一路上升，排得夠久會撞到 Nginx 自己的逾時。兩者在 status 頁分得開，後者的 `max listen queue` 會大於 0（見下面的〈status 頁〉一節）。`request_terminate_timeout` 跟 PHP 自己的 `max_execution_time` 量的不是同一種時間。PHP 官方文件寫明，`max_execution_time` 只計算腳本本身執行的時間，花在腳本以外的活動——系統呼叫、串流操作、資料庫查詢——不算進去（Windows 例外，那裡量的是實際經過的時間）。所以一個卡在等資料庫回應的請求，`max_execution_time` 可能永遠不會觸發。`request_terminate_timeout` 由 PHP-FPM 從外部計算實際經過的時間，卡在哪裡都會終止。

`request_slowlog_timeout` 不終止請求，只在請求超過指定時間時把它當下的 PHP 呼叫堆疊記進 slowlog。設 `request_slowlog_timeout = 1s`，一個在 `loadReport()` 裡 sleep 的請求會留下：

```text
[pool www] pid 6
script_filename = /var/www/html/slow.php
[0x...] usleep() /var/www/html/slow.php:2
[0x...] loadReport() /var/www/html/slow.php:3
[0x...] handle() /var/www/html/slow.php:4
```

堆疊直接指出慢在哪一行、哪一層呼叫。這是找出慢請求根源最直接的工具，不必改程式加計時。

一個部署上的細節：PHP-FPM 取 worker 的堆疊是靠 `ptrace` 這個系統呼叫，在 Docker 預設的權限下會失敗（`failed to ptrace(ATTACH) ... Operation not permitted`），slowlog 因此是空的。容器裡要用 slowlog 得在啟動時加 `--cap-add SYS_PTRACE`。

## status 頁：看這個 pool 現在的狀態

`pm.status_path` 開一個狀態頁，列出 pool 當下的 worker 數量、排隊與累計計數。前面那個 `max_children = 2` 的排隊測試跑完後，狀態頁是：

```text
pool:                 www
process manager:      static
accepted conn:        15
listen queue:         0
max listen queue:     4
idle processes:       1
active processes:     1
total processes:      2
max active processes: 2
max children reached: 0
slow requests:        0
```

幾個欄位直接對應前面的設定：

- **`max listen queue`**：等待空閒 worker 的請求，最多排到過幾個。上面是 4，正好是那次 6 個並發裡、扣掉 2 個正在處理的其餘 4 個。這個數字長期大於 0，代表 `max_children` 在尖峰時不夠用，請求要排隊等空閒的 worker。
- **`max children reached`**：PHP-FPM 想多開 worker、卻撞到 `max_children` 上限的次數。這個計數只在 `dynamic` 與 `ondemand` 下會動，因為只有這兩種模式會「想多開」：上面那次是 `static`，請求排了 4 個而它仍然是 0；同樣 6 個並發換成 `pm = dynamic`（`max_children = 2`）時，它變成 1、`max listen queue` 是 5。所以 `static` 模式要看 `max listen queue`，不能看這一欄。
- **`slow requests`**：超過 `request_slowlog_timeout` 的請求累計數。

所以判斷 `max_children` 夠不夠，要先看 pool 用的是哪一種 `pm`：**`static` 只能看 `max listen queue`**（`max children reached` 在 `static` 下永遠是 0），`dynamic` 與 `ondemand` 兩欄都能看。`max listen queue` 長期大於 0 就該往上調，前提是記憶體容得下；長期是 0 代表還有餘裕。

## 停機與重載的訊號

PHP-FPM 的 master 依收到的訊號決定怎麼停或怎麼換掉 worker，PHP 原始碼附的 man page 列出四個：

| 訊號                | 動作                                       |
| ------------------- | ------------------------------------------ |
| `SIGINT`、`SIGTERM` | 立即終止                                   |
| `SIGQUIT`           | graceful stop                              |
| `SIGUSR1`           | 重新開啟 log 檔                            |
| `SIGUSR2`           | graceful reload：重讀設定、換掉所有 worker |

「graceful」要等正在處理的請求多久，由另一個設定 `process_control_timeout` 決定：master 送出停止訊號之後，最多等 worker 這麼久。它的預設值是 0，也就是**不等**。一個請求要跑 3 秒，在它跑到第 1 秒時對 master 送 `SIGUSR2`：

```text
process_control_timeout = 0（預設）  →  502，在 1.07 秒時中斷
process_control_timeout = 10         →  200，跑滿 3.0 秒才回應
```

`SIGQUIT` 一樣：預設值下 `docker stop` 一送出 PHP-FPM 就結束，進行中的請求拿到 502；設成 10 之後，`docker stop` 花了 2 秒，等那個請求做完。所以要讓 reload 與停機不中斷請求，`process_control_timeout` 要設成比最長的正常請求還長的秒數（它寫在設定檔的 `[global]` 段），而容器平台的停機逾時（`docker stop -t`、Kubernetes 的 `terminationGracePeriodSeconds`）要比它更長，否則平台會先強制終止。

設好之後，reload 只換 PHP 不動 Nginx。這跟 [mod_php](/php/01-server-runtime/mod-php/#設定的位置與生效時機) 的「改 PHP 設定要重載 Apache」是不同的隔離層級：PHP-FPM 是獨立的服務，重載 PHP 時 Nginx 的程序與它和客戶端之間的連線都不受影響。這也是 PHP 官方建議「用 PHP-FPM 取代 mod_php」的理由之一——PHP 能獨立於 web 伺服器重啟。

## PHP-FPM 管的事情總覽

回到開頭那幾個「常駐程序帶出的問題」，PHP-FPM 的每一個旋鈕各對應一個：

| 問題                                                     | 對應的設定                                                   |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| 開幾個程序、怎麼增減                                     | `pm`、`pm.max_children`、`pm.*_spare_servers`                |
| 並發上限與排隊                                           | `pm.max_children`（配 status 的 `max listen queue` 判讀）    |
| 記憶體隨時間漲（RSS 底部一路往上；重請求後暫時偏高不算） | `pm.max_requests`                                            |
| 某個請求卡住                                             | `request_terminate_timeout`、`request_slowlog_timeout`       |
| 每個站台不同執行身分                                     | pool 的 `user` / `group` / `listen`                          |
| 不中斷地改設定與停機                                     | `SIGUSR2`（reload）、`SIGQUIT`，配 `process_control_timeout` |

這些旋鈕都是因為 worker 常駐才需要。worker 常駐同時讓一件事變得有意義：OPcache。程序活得夠久，編譯好的 opcode 才有機會被下一個請求重用，重用的程度在 [OPcache 與程序壽命](/php/01-server-runtime/opcache/) 實測。

如果連應用程式的狀態也想跨請求保留（框架只啟動一次），就要再往前走一步到常駐 worker 模型，那是另一組取捨，見 [常駐 worker 模型](/php/01-server-runtime/long-running-workers/)。而把 Nginx 跟 PHP-FPM 放進容器時，兩個程序怎麼擺、要不要拆成兩個容器，見 [容器裡的 Nginx 與 PHP-FPM](/php/01-server-runtime/nginx-php-fpm-containers/)。
