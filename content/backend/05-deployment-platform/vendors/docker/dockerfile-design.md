---
title: "Dockerfile 設計：指令、layer 與 multi-stage"
date: 2026-07-06
description: "image 大得離譜、code 一改就整包重 build、或 multi-stage 複製 binary 後 container 起不來說找不到 library 時回來讀 — Dockerfile 指令怎麼變成 layer、build 與 runtime 怎麼分離"
weight: 10
tags: ["backend", "deployment", "docker", "dockerfile"]
---

這篇假設你已經知道 Docker 是什麼、為什麼要用它（[Docker vendor overview](/backend/05-deployment-platform/vendors/docker/)），往下寫 Dockerfile 本身怎麼設計。目標是讓你看得懂每個指令會變成什麼、build 慢或 image 大時知道從哪查。

## 問題情境：三個「不懂 layer」的症狀

建一個對齊線上的 PHP runtime，第一版 Dockerfile 常長成這樣，然後撞上三個症狀：

- **image 五百 MB 起跳**：明明只跑一個 PHP 程式，image 卻塞滿編譯工具、apt 快取、中間產物。
- **改一行 code 就整包重 build**：每次 `docker build` 都從頭跑一次 `apt install`，明明套件根本沒動。
- **multi-stage 複製 binary 後 container 起不來**：`COPY --from=build` 把執行檔搬到精簡的 runtime image，跑起來卻報 `Error loading shared library`。

三個症狀的共同根因是同一件事：不清楚 Dockerfile 的每個指令會變成什麼、build cache 以什麼為單位。把這個模型建起來，三個症狀都能對症。

## 核心概念：每個指令是一層唯讀 layer

Dockerfile 的每個指令產生一層唯讀的 image layer，layer 由上往下疊成最終 image。這個模型解釋了 Docker 幾乎所有 build 行為：

- **image 是 layer 的疊加**：`FROM` 給你底層 layer，之後每個 `RUN` / `COPY` / `ADD` 各加一層，只記錄「這層相對上一層改了什麼」。
- **build cache 以 layer 為單位**：build 時 Docker 逐層檢查「這個指令跟它的輸入有沒有變」，沒變就直接用快取的那層、跳過執行。
- **一層變，它與之後全部要重建**：某層的指令或輸入變了，那層以下所有 layer 的快取全部失效、必須重跑。layer 的**順序**因此直接決定 build 快不快。

記住「指令 = layer、cache 以 layer 為單位、一層變則後面全垮」這三句，後面的設計原則都是它的推論。

## 配置：逐指令怎麼寫

以下用一個版本凍結的 PHP runtime 為例（實際跑過的形態），逐指令說明。

### FROM：起點與凍結

```dockerfile
FROM php:7.2-fpm-buster
```

`FROM` 指定 base image，是整個 image 的地基。tag 要釘到夠精確——`php:7.2-fpm-buster` 把 PHP 版本連同底層 Debian 世代一起凍結，而不是用會漂的 `php:7.2-fpm`。為什麼 tag 精確度是可重現性的關鍵，見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)。

### RUN：每個 RUN 一層，合併與清理要同層

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends libzip-dev libpng-dev \
    && docker-php-ext-install pdo_mysql mysqli gd zip \
    && rm -rf /var/lib/apt/lists/*
```

每個 `RUN` 產生一層。上面把 update、install、清理用 `&&` 串在**同一個** `RUN` 裡是刻意的：如果拆成三個 `RUN`，`apt-get update` 抓下來的 index、以及安裝產生的快取，會留在中間層裡——就算最後一層 `rm` 掉，前面層已經記錄了那些檔案，image 照樣變大。layer 是疊加的，後面的層刪不掉前面層已經寫進去的東西。清理必須跟產生它的指令同層。

### COPY：放在變動頻率的正確位置

```dockerfile
COPY composer.json composer.lock ./
RUN composer install --no-dev
COPY . .
```

`COPY` 把 build context 的檔案加一層進 image。這裡的順序是 build 快不快的關鍵：先只 `COPY` 依賴清單、裝完依賴，再 `COPY` 全部原始碼。因為原始碼幾乎每次都變、依賴清單很少變——把「常變的」放在「少變的」後面，改 code 時依賴那層的 cache 還在，不用重裝。順序反過來（先 `COPY . .` 再裝依賴）就是前面「改一行 code 整包重 build」的直接成因。

`COPY` 跟 `ADD` 的差別：`ADD` 會多做「自動解壓 tar、支援 URL」兩件事，但那兩件事讓行為變得不透明。預設用 `COPY`，需要解壓時自己 `RUN tar` 講清楚。

### CMD 與 ENTRYPOINT：預設命令與固定入口

```dockerfile
ENTRYPOINT ["php-fpm"]
CMD ["--nodaemonize"]
```

兩者都定義 container 啟動跑什麼，但角色不同：`ENTRYPOINT` 是「這個 image 固定是幹嘛的」（固定入口），`CMD` 是「預設參數」（可被 `docker run` 後面的參數覆蓋）。上面的組合表示這個 image 就是跑 `php-fpm`、預設帶 `--nodaemonize`，但 `docker run image --version` 會把 `--version` 覆蓋掉 CMD。只寫 `CMD ["php-fpm"]` 也能跑，但 `docker run image bash` 會整個換掉命令——要不要讓人輕易換命令，決定你用哪個。

### multi-stage：build 與 runtime 分離

```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN go build -o /app ./cmd/server

FROM gcr.io/distroless/base-debian12
COPY --from=build /app /app
ENTRYPOINT ["/app"]
```

multi-stage 用多個 `FROM` 切成幾個 stage，最終 image 只保留最後一個 stage。上面第一 stage 有整套 Go 編譯工具鏈（幾百 MB），第二 stage 是極精簡的 runtime，只用 `COPY --from=build` 把編譯出的單一 binary 搬過來。最終 image 不含編譯器、不含原始碼，只有跑得起來需要的東西。這是解決「image 五百 MB」的主要手段：把 build-time 才需要的東西留在被丟棄的 stage。

## 故障演練：從 build 失敗到 image 失控

deep article 的價值在這段。以下每個都是實跑撞到的。

### apt update 在凍結舊 base image 上 404

用 `php:7.2-fpm-buster` 這種舊 base image build 時，`apt-get update` 可能直接失敗：

```text
Err:5 http://deb.debian.org/debian buster Release
  404  Not Found
E: The repository 'http://deb.debian.org/debian buster Release' does not have a Release file.
```

徵兆是 build 停在第一個 `RUN` 的 `apt-get update`、exit code 100。根因是 Debian buster 已 EOL，套件庫從主 mirror 移到 `archive.debian.org`，原本的 mirror 路徑不存在了。修法是在 `RUN` 開頭改寫 apt source 指向 archive、並關掉過期檢查：

```dockerfile
RUN printf '%s\n' \
        'deb http://archive.debian.org/debian buster main' \
        'deb http://archive.debian.org/debian-security buster/updates main' \
        > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends libzip-dev \
    && rm -rf /var/lib/apt/lists/*
```

這是用退役 base image 的固有稅——預設 mirror 隨發行版過保而失效，任何釘在舊發行版世代的 image 都會遇到。

### multi-stage 複製 binary 卻漏了它的 library

這是 multi-stage 最常見的失誤。把一個動態連結的 binary 從 build stage 複製到精簡 runtime stage，只 `COPY` 執行檔本身：

```dockerfile
FROM alpine:3.19 AS build
RUN apk add --no-cache jq
FROM alpine:3.19
COPY --from=build /usr/bin/jq /usr/bin/jq   # 只複製 binary
CMD ["jq", "--version"]
```

build 會**成功**，但 `docker run` 起來報：

```text
Error loading shared library libonig.so.5: No such file or directory (needed by /usr/bin/jq)
Error relocating /usr/bin/jq: onig_search: symbol not found
```

關鍵在 build 會過、`docker run` 才炸：`jq` 動態連結到 `libonig.so.5`，而那個 `.so` 留在 build stage、沒跟著搬過來，runtime 才在載入時報「找不到 shared library」。把依賴庫一起帶上就解決：

```dockerfile
COPY --from=build /usr/bin/jq /usr/bin/jq
COPY --from=build /usr/lib/libonig.so.5 /usr/lib/libonig.so.5
```

另外兩種做法：讓 build stage 產出靜態連結的 binary（`CGO_ENABLED=0` 的 Go、musl 靜態編譯），就沒有 runtime library 依賴；或 runtime stage 不用 scratch / distroless-static，改用本來就自帶 libc 與常見庫的 base（debian-slim 或 `distroless/base`），用稍大的 image 換掉「逐一搬 `.so`」的麻煩。判讀哪些 `.so` 要帶，用 `ldd <binary>` 列出動態依賴。這個失誤的深層原因跟 [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/) 相關——binary 對哪套 libc 連結，決定它在目標 image 找不找得到符號。

### layer cache 明明該命中卻一直重跑

改一行 code、`docker build` 卻從 `apt install` 開始整包重跑。用 `--progress=plain` 看是哪層失效：

```bash
docker build --progress=plain -t app .   # 逐層輸出，看哪層開始不是 CACHED
```

若看到 `COPY . .` 之後的每一層都重跑，根因通常是 `COPY . .` 放太前面——它一層把所有原始碼灌進來，任何 code 變動都讓這層及其後全部 cache 失效。修法見前面 COPY 段：依賴清單先 COPY、原始碼後 COPY。

### RUN 拆太多行，層數爆炸

把每個指令拆成獨立 `RUN`（`RUN apt update`、`RUN apt install a`、`RUN apt install b`…）會產生一堆 layer，且中間層的殘留檔案清不掉。`docker history <image>` 看每層大小能直接看出哪些層在囤東西。修法是把邏輯相關、且需要一起清理的指令合併到同一個 `RUN`。

## 容量：什麼規模需要哪種手段

image 設計的規模判讀，不是每個專案都要做到極致精簡：

- **單一 binary 服務（Go / Rust）**：multi-stage + distroless 或 scratch，最終 image 可壓到十幾 MB。編譯型語言最吃這套。
- **直譯型 runtime（PHP / Python / Node）**：需要語言 runtime 在 image 裡，多階段收益較小，重點放在 base image 選擇（slim 版）與 layer 順序。
- **base image 選型**（沿 musl↔glibc、大小、可 debug 三軸權衡，常見幾類）：alpine（musl，最小但可能有相容性差異，見 [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/)）、debian-slim / ubuntu（glibc，相容性穩、稍大）、Wolfi / Chainguard（glibc 但極小，瓦解「要小就得選 musl」的取捨）、distroless（無 shell、無套件管理器，攻擊面最小但難 debug）。

判準用 `docker history <image>` 看每層大小定位肥的來源，再決定值不值得為它加 multi-stage。過早為一個內部工具 image 追求極致精簡是浪費。

寫好之後 build 成 image 並跑一次：

```bash
docker build -t app .        # 依當前目錄的 Dockerfile build
docker run --rm app          # 跑起來；-d 背景跑、-p 對 port
```

## 整合與下一步

- 多個 container（app + DB + cache）怎麼一起編排，見 [Docker Compose 深度設計](/backend/05-deployment-platform/vendors/docker/docker-compose/)。
- build 慢、要同時出 amd64 / arm64、build 時要塞 secret 或快取套件下載，見 [BuildKit 與跨平台 build](/backend/05-deployment-platform/vendors/docker/buildkit-cross-platform/)。
- 一個完整的「對齊 client 線上舊環境」的實作，把 Dockerfile 放進 compose 三件套，見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)。
- production 編排離開 Docker、走 Kubernetes 時，image 是不變的可攜介面，見 [Kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/)。
