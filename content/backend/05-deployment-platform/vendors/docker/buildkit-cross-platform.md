---
title: "BuildKit 與跨平台 build"
date: 2026-07-06
description: "docker build 每次重下載套件很慢、要同時出 amd64 與 arm64 image、或 build 時要用私有憑證卻不想烤進 image 時回來讀 — BuildKit 的 cache/secret mount 與 buildx 跨平台 build"
weight: 30
tags: ["backend", "deployment", "docker", "buildkit", "buildx"]
---

build 每次重下載套件、要同時出 amd64 與 arm64、build 時要用私有憑證卻不想烤進 image——這三個進階需求，是會寫 Dockerfile（[Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)）之後才撞上的。上游是 [Docker vendor overview](/backend/05-deployment-platform/vendors/docker/)。

## 舊 builder 做不好的三件事

理解 BuildKit 最快的方式，是先看它取代的舊 builder 卡在哪。Docker 最初的 legacy builder 逐層線性執行 Dockerfile，三個常見需求它都處理得很勉強：

- **build 加速**：每次 build，`RUN apt-get install` 或 `npm install` 都重新下載一次套件，就算內容一樣。legacy builder 只有 layer cache（整層命中或整層重跑），沒有「跨 build 保留下載快取」的機制。
- **跨架構**：要同時出 amd64 跟 arm64 的 image（M 系列 Mac 開發、amd64 伺服器部署），legacy builder 一次只能 build 當前主機的架構。
- **build-time secret**：build 時要用私有 registry 憑證或 SSH key 抓私有依賴，用 `COPY` 或 `ENV` 帶進去，secret 就永久烤進某層 image、`docker history` 挖得出來。

BuildKit 是重寫的 build engine，針對這三件重新設計；buildx 是它的前端命令，管 builder 實例與跨平台輸出。現代 Docker 預設就用 BuildKit，但上面三個能力要用對語法才吃得到。

## 核心概念：mount 與 builder 實例

BuildKit 帶來兩個 legacy builder 沒有的核心概念：

- **build-time mount**：`RUN --mount=...` 讓某個 `RUN` 在執行當下掛載一塊空間，但那塊空間**不進最終 image layer**。cache mount（保留套件下載快取）、secret mount（暫時給憑證）、ssh mount（轉發 SSH agent）都是它的形態。關鍵是「build 時用得到、build 完不留痕跡」。
- **builder 實例與 driver**：build 由一個 builder 執行。預設的 `docker` driver 綁在本機 daemon、功能受限；要跨平台這類進階能力，得建一個 `docker-container` driver 的 builder（跑在獨立 container 裡，功能完整）。這是很多人卡住的地方，見故障演練。

## 配置：三個需求逐一

三個能力的 `RUN --mount` 語法屬於較新的 Dockerfile frontend，Dockerfile 第一行要用 syntax directive 明確 opt-in：

```dockerfile
# syntax=docker/dockerfile:1
```

這行告訴 BuildKit「用 dockerfile:1 這個 frontend 解析」，`--mount=type=cache/secret/ssh` 才認得。少了它、舊 parser 會把 `--mount` 當語法錯誤。現代 Docker 對多數新語法會自動啟用，但 mount 這類要顯式標，養成習慣寫上去。

### cache mount：套件下載快取跨 build 保留

```dockerfile
# syntax=docker/dockerfile:1
FROM debian:bookworm
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends build-essential
```

`--mount=type=cache,target=/var/cache/apt` 把 apt 的下載快取目錄掛成一塊持久快取。第一次 build 下載套件、存進快取；之後就算這層因為別的原因重跑，套件直接從快取拿、不重新下載。npm（`target=/root/.npm`）、pip（`target=/root/.cache/pip`）、Go module（`target=/go/pkg/mod`）同理。

這跟 layer cache 是兩回事：layer cache 是「整層沒變就跳過」，cache mount 是「就算這層要重跑，它用到的下載內容不必重來」。兩者疊加才是最快的 build。

### secret mount：build 時用憑證但不留在 image

```dockerfile
RUN --mount=type=secret,id=npmtoken \
    NPM_TOKEN=$(cat /run/secrets/npmtoken) npm install
```

```bash
docker buildx build --secret id=npmtoken,src=$HOME/.npmtoken -t app .
```

secret 在 build 當下以檔案形式出現在 `/run/secrets/`，`RUN` 結束就消失、不寫進任何 layer。`docker history` 挖不到、image 送出去也不帶 secret。這取代了「`ENV NPM_TOKEN=...` 或 `COPY .npmrc`」那種會把 secret 烤進 image 的錯誤做法。

### 跨平台 build：一次出多架構

```bash
# 先建一個支援多平台的 builder（docker driver 不支援，見故障演練）
docker buildx create --name multi --driver docker-container --use

# 同時 build amd64 + arm64，直接推到 registry
docker buildx build --platform linux/amd64,linux/arm64 \
    -t ghcr.io/org/app:1 --push .
```

Docker Desktop / OrbStack 內建了跨架構所需的 QEMU binfmt handler、開箱能模擬；裸 Linux 主機與 CI runner（GitHub Actions ubuntu runner 是跨平台 build 最主要的落點）沒有，跨架構前要先註冊一次，否則模擬會 `exec format error`：

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
```

`--platform` 帶多個架構，BuildKit 用 QEMU 模擬各架構分別 build，產出一個 multi-arch manifest（同一個 tag 底下有多架構、pull 時自動選對的）。cache backend 可以進一步把快取存到 registry 或 CI，讓不同機器 / CI job 共用：

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
    --cache-to type=registry,ref=ghcr.io/org/app:cache \
    --cache-from type=registry,ref=ghcr.io/org/app:cache \
    -t ghcr.io/org/app:1 --push .
```

CI 上更常用平台原生 cache——GitHub Actions 用 `type=gha`（工作流先掛 `docker/setup-buildx-action`）：

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
    --cache-to type=gha,mode=max --cache-from type=gha \
    -t ghcr.io/org/app:1 --push .
```

## 故障演練：driver 與 secret 的邊界

### default docker driver 不支援多平台

直接 `docker build --platform linux/amd64,linux/arm64` 或用預設 builder，會直接失敗：

```text
ERROR: failed to build: Multi-platform build is not supported for the docker driver.
```

徵兆很明確、錯誤訊息就講了。根因是預設的 `docker` driver（綁本機 daemon）不支援多平台輸出。修法是建一個 `docker-container` driver 的 builder 再用它：

```bash
docker buildx create --name multi --driver docker-container --use
docker buildx build --builder multi --platform linux/amd64,linux/arm64 -t app .
```

換上 container driver builder 後，同一條指令就能同時 build 出兩個架構（實測 amd64 + arm64 各自完成、產出 multi-arch）。這是跨平台 build 的第一道門檻，卡最多人。

### 多平台 build 不能 --load 回本機

建好 multi-arch 之後想 `--load` 到本機 image store，會失敗——本機的 docker image store 一個 tag 只能存單一架構。多平台結果要嘛 `--push` 到 registry（registry 支援 multi-arch manifest），要嘛輸出成 OCI tarball。判讀：本機測單一架構用 `--load` + 單一 `--platform`；要發佈多架構就 `--push`。想在本機留多架構的期待，本機 image store 這層就擋住了。

### QEMU 模擬非原生架構很慢

在 arm64 主機 build（或跑）amd64 image，BuildKit 靠 [QEMU binfmt 模擬](/backend/knowledge-cards/qemu-binfmt-emulation/)，效能明顯掉。這在跑舊服務時特別有感——例如 MySQL 5.7 沒有 arm64 原生 image，在 Apple Silicon 上只能 `platform: linux/amd64` 走模擬，啟動與運算都比原生慢。這不是壞掉、是模擬的固有成本。判讀：dev 階段可以忍模擬的慢（換來跟 amd64 prod 的架構對齊）；如果模擬慢到影響開發，考慮在原生架構的遠端 builder 上 build。實際應用見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/) 的 arm64 段。

### secret 用錯機制，還是進了 layer

`ENV` / `COPY` 都會產生 layer、內容永久記錄，所以拿它們帶 secret（`ENV TOKEN=xxx`、`COPY .npmrc`）等於把 secret 烤進 image——`docker history --no-trunc <image>` 或把 image 拆開就翻得到 token。改用 `--mount=type=secret`（前面配置段）才不落 layer，secret 只在 `RUN` 當下以檔案存在。驗證：build 完 `docker history` 確認翻不到 secret。

## 容量：什麼時候需要這些

這些是進階能力、不是每個專案都要開：

- **cache mount**：build 頻繁（CI 每次 commit build）、或依賴下載很重（大量 npm / apt 套件）時收益明顯。單機偶爾 build 一次的內部工具，layer cache 就夠。
- **跨平台**：要發佈給不同架構使用者（open source image、公司同時有 M 系列 Mac 與 amd64 伺服器）才需要。只在單一架構部署就不必扛 QEMU 的複雜與慢。
- **cache backend 選型**：本機開發用預設 local cache；CI 用 registry cache（`--cache-to/from type=registry`）或平台原生 cache（如 GitHub Actions 的 `type=gha`），讓每次 CI job 不必冷啟動重建。選哪個看 CI 環境提供什麼。

## 整合與下一步

- Dockerfile 指令與 layer 的基礎（cache mount 疊在 layer cache 之上），見 [Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)。
- 多 service 的 dev 環境編排，見 [Docker Compose 深度設計](/backend/05-deployment-platform/vendors/docker/docker-compose/)。
- image build 進 CI/CD pipeline、跟供應鏈掃描接起來，見 [Docker / Image 部署 CI/CD](/ci/docker-deploy/)。
