---
title: "OPcache 與程序壽命：編譯結果的快取在各種執行模型下的效果"
date: 2026-10-05
description: "說明 OPcache 快取的是什麼、它存在哪裡，以及為什麼它的效果取決於執行 PHP 的程序活多久：CGI 下命中次數永遠為零、PHP-FPM 的 worker 共用同一份快取；框架請求開與關 OPcache 的延遲差、memory_consumption 與 max_accelerated_files 的估算，以及部署新程式碼時 validate_timestamps 與 revalidate_freq 決定舊版還會執行多久"
weight: 6
tags: ["php", "opcache", "php-fpm", "deployment"]
---

這篇說明 OPcache 這個 PHP 內建的擴充：它快取什麼、快取存在哪裡、在不同執行模型下有沒有效果，以及部署新程式碼時要注意的設定。它接在 [PHP 的請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/) 那組問題的第二個上：執行 PHP 的程序活多久。OPcache 是程序層的資源，程序活得越久，它重用得越多。文中的預設值與行為取自 `php:8.5-fpm-alpine`。

## OPcache 快取的是編譯結果

PHP 每次執行一個 `.php` 檔，都要先把原始碼編譯成 opcode——Zend 引擎實際執行的指令——再執行它（見 [OPcache](/php/knowledge-cards/opcache/)）。沒有快取時，每個請求的每個檔案都要重新讀檔、解析、編譯。

OPcache 把編譯好的 opcode 存進一塊**共享記憶體**，下一次要執行同一個檔案時，直接從共享記憶體拿編譯結果，跳過讀檔與編譯。它快取的是程式碼，不是資料：變數的值、查詢結果、請求之間的狀態都不在裡面，[shared-nothing](/php/knowledge-cards/shared-nothing-request/) 不受影響。PHP 5.5 起 OPcache 隨 PHP 一起發行；PHP 8.5 依〈Make OPcache required〉這份 RFC 把它靜態編進 PHP 本體，不必也不能再另外安裝，開關仍然由 `opcache.enable` 控制。

框架讓這件事的份量變得很大。Laravel 13 處理一個最簡單的健康檢查請求，`get_included_files()` 回報這個請求載入了 484 個檔案——設定、服務提供者、路由、中介層、框架本身的類別。這 484 個檔案每個請求都要用到，所以有沒有快取它們的編譯結果，差距是每個請求都要重付一次的成本。

在同一個 Laravel 容器（Nginx 加 PHP-FPM）上循序請求 `/healthz`，只切換 OPcache 的開關：

| OPcache | 每個請求的平均時間 |
| ------- | ------------------ |
| 開      | 3.8 ms             |
| 關      | 49.3 ms            |

相差十幾倍，而請求做的事情完全一樣。差出來的時間幾乎都花在編譯那 484 個檔案上。

## 快取效果與程序壽命的關係

OPcache 的共享記憶體在 PHP 啟動時建立，屬於那個程序（以及它 fork 出來的子程序）。程序結束，那塊記憶體就跟著釋放，快取也就消失。所以同一個 OPcache，在不同的執行模型下效果完全不同。

**CGI：命中次數永遠是零。** [CGI](/php/01-server-runtime/cgi/) 每個請求啟動一個新程序。每個程序都建立自己的 OPcache、把這次用到的檔案編譯進去，然後隨請求結束一起消失。在 CGI 下印出 OPcache 的統計，`cached_scripts` 每次都是 1（這次編譯進去了），`hits` 每次都是 0（從來沒有被重用過）。OPcache 是開著的，只是沒有作用。

**PHP-FPM：worker 共用同一份快取。** [PHP-FPM](/php/01-server-runtime/php-fpm/) 的 master 在啟動時建立 OPcache 的共享記憶體，再 fork 出 worker，worker 繼承了這塊記憶體。所以一個 pool 裡所有 worker 讀寫的是同一份快取。對兩個 worker 輪流處理的請求印出統計：

```text
pid=6 opcache_enabled=true cached_scripts=1 hits=0
pid=7 opcache_enabled=true cached_scripts=1 hits=1
pid=6 opcache_enabled=true cached_scripts=1 hits=2
pid=7 opcache_enabled=true cached_scripts=1 hits=3
```

PID 6 第一次執行時把腳本編譯進快取，PID 7 接下來直接命中——它自己沒有編譯過這個檔案，用的是 PID 6 編譯好的結果。命中次數跨 worker 累加。這帶出兩個推論：

- **worker 被換掉不會清空快取。** [`pm.max_requests`](/php/01-server-runtime/php-fpm/#max_requests定期換掉-worker-以控制記憶體) 換掉的是 worker，快取住在 master 建立的共享記憶體裡，新 worker 一啟動就能用。要清空快取得重啟或 reload 整個 PHP-FPM。
- **同一台機器上的不同 pool 共用同一個 master 時，也共用這塊記憶體。** 所以 `memory_consumption` 要容得下所有 pool 的程式碼。

[mod_php](/php/01-server-runtime/mod-php/) 的情況相同：Apache 的父程序載入 PHP 時建立共享記憶體，子程序繼承它。在 `php:8.5-apache` 上連續請求五次，五個不同的子程序（PID 16 到 20）回報的命中次數依序是 0、1、2、3、4。

## 快取的大小

OPcache 的共享記憶體大小固定，由兩個設定決定，`php:8.5-fpm-alpine` 的預設值是：

| 設定                            | 預設值 | 意義                      |
| ------------------------------- | ------ | ------------------------- |
| `opcache.memory_consumption`    | 128    | 共享記憶體的大小，單位 MB |
| `opcache.max_accelerated_files` | 10000  | 最多能快取幾個檔案        |

Laravel 13 骨架處理過請求之後，OPcache 回報快取了 467 個腳本，用掉 22.0 MB，剩下 106.0 MB；另外 interned strings（PHP 把重複出現的字串只存一份的區塊）用掉 4.3 MB。一個空骨架用不到預設值的五分之一，但正式專案加上大量套件之後，`vendor/` 裡的檔案數可以到上萬個。

快取滿了時，OPcache 不會報錯讓請求失敗：放不進去的檔案就不被快取，每次重新編譯。檔案改過而留下的舊版本佔用的空間算是「浪費的記憶體」，剩餘空間不夠、而浪費的比例又超過 `opcache.max_wasted_percentage`（預設 5%）時，OPcache 會排定一次重啟，清空整份快取重新累積。兩種情形從外面看都只是請求變慢，所以要從 `opcache_get_status()` 讀：`free_memory` 接近零、或 `num_cached_scripts` 接近 `max_accelerated_files`，就是該調大的時候。手上的專案實際要多大，在部署環境跑過一輪主要的請求之後，讀這兩個值就知道。

## 部署新程式碼時舊版還會執行多久

OPcache 快取了編譯結果，所以檔案改了之後，PHP 什麼時候才去讀新版，由 `opcache.validate_timestamps` 與 `opcache.revalidate_freq` 決定。這是部署時最常撞到的問題。

`opcache.validate_timestamps` 決定 OPcache 要不要檢查檔案有沒有改過。`opcache.revalidate_freq` 是檢查的間隔秒數。`php:8.5-fpm-alpine` 的預設值是 `validate_timestamps=On`、`revalidate_freq=2`。實測兩種設定下，改了檔案之後的行為：

```text
# validate_timestamps=1, revalidate_freq=2（預設）
改檔之前  version=2
改檔之後 t+0s  version=2
         t+1s  version=2
         t+3s  version=3     # 間隔過了，OPcache 檢查到檔案改了，重新編譯

# validate_timestamps=0
改檔之前  version=1
改檔之後  version=1          # 連續請求都還是舊版
         version=1
         version=1
reload 之後 version=2        # kill -USR2 讓 PHP-FPM reload，快取清空才換成新版
```

兩種設定各有用途：

- **`validate_timestamps=1`**：改檔之後最多 `revalidate_freq` 秒就生效，代價是每隔這段時間 PHP 要對檔案做一次 `stat`。開發環境與「直接覆寫伺服器上的檔案」的部署方式適合這個。
- **`validate_timestamps=0`**：OPcache 完全不檢查檔案，省掉所有 `stat`；改了檔案永遠不會生效，部署流程必須在換完程式碼之後 reload 或重啟 PHP-FPM。程式碼包在容器映像檔裡的部署適合這個：映像檔裡的檔案不會在執行中被改，每次部署都是啟動新容器，新容器的快取在啟動時是空的。開發時用 bind mount 把主機上的原始碼掛進容器，雖然也是容器，檔案卻會被改，要算成上一種情形、留著 `validate_timestamps=1`；設成 0 的話，改了檔案頁面不會變，也沒有任何錯誤訊息。

`validate_timestamps=1` 下還有一個中間狀態要知道：部署是逐一覆寫檔案時，在 `revalidate_freq` 那幾秒內，有的檔案已經重新編譯成新版、有的還是舊版快取，同一個請求可能同時執行到新舊兩版的程式碼。把整個版本目錄準備好再一次切換（例如換一個符號連結），然後 reload，可以避開這個狀態。

## OPcache 的 JIT 與 preload

OPcache 另外帶著 JIT 與 preload，兩者跟快取 opcode 相鄰，解決的是不同的問題：

- **JIT**：把 opcode 進一步編譯成 CPU 的機器碼。它對計算密集的程式（數學運算、影像處理）有幫助，對多數時間在等資料庫與網路的 web 請求效果有限。`php:8.5-fpm-alpine` 預設 `opcache.jit=disable`。
- **preload**（`opcache.preload`）：PHP-FPM 啟動時先執行一支指定的腳本，把它載入的類別常駐在共享記憶體裡，之後每個請求不必再載入它們。被 preload 的檔案改了要重啟 PHP-FPM 才生效。

## OPcache 與執行模型的關係

OPcache 的效果整個建立在程序壽命上：CGI 下沒有作用，常駐的 PHP-FPM worker 讓它重用到極致。但它只省掉「編譯」這一段。框架在每個請求開頭還要做另一件事——執行那 484 個檔案：建立服務容器、註冊服務、讀設定、建立路由表——這一段 OPcache 省不掉，因為 shared-nothing 要求每個請求從空白的狀態開始。

想連這一段也省掉，就要讓應用程式的狀態也跨請求保留，框架只啟動一次。那是 [常駐 worker 模型](/php/01-server-runtime/long-running-workers/) 的做法，也是它要付出的代價的來源。
