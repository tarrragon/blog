---
title: "QEMU binfmt Emulation（跨架構模擬）"
date: 2026-07-06
description: "docker 跑非原生架構的 image 報 exec format error、mysql:5.7 在 Apple Silicon 要 platform: linux/amd64、或跨平台 build 特別慢時回來讀 — 非原生 image 怎麼被模擬跑起來"
weight: 130
tags: ["backend", "deployment", "docker", "container", "knowledge-cards"]
---

QEMU binfmt 模擬是「讓一台機器跑另一種 CPU 架構的執行檔」的機制。[container](/backend/knowledge-cards/container/) image 綁特定架構（amd64 / arm64），當 image 的架構跟主機不同時，核心透過 binfmt_misc 把該執行檔交給 QEMU 動態翻譯指令、模擬跑起來。它解釋了兩件在混架構環境常撞到的事：為什麼某些 image 在你的機器上「跑得起來但很慢」，以及為什麼有時直接「跑不起來」。

## 概念位置

QEMU binfmt 位在 image 架構與主機架構之間，是跨架構相容的底層機制。它被兩個場景依賴：跑一個非主機架構的 image（如 arm64 主機跑 amd64 的 [container](/backend/knowledge-cards/container/)），以及 buildx 一次 build 多架構 image 時模擬非主機架構的那一份。

## binfmt_misc 怎麼接手

binfmt_misc 是 Linux 核心的一個機制：註冊「看到這種格式的執行檔，就交給指定的 handler 跑」。跨架構情境下，handler 是 QEMU user-mode emulator。所以一個 arm64 主機要跑 amd64 image 時，核心認出 amd64 binary、丟給 `qemu-x86_64` 逐指令翻譯執行。整個過程對 container 內的程式透明，它不知道自己在被模擬。

關鍵是這個註冊要先存在。Docker Desktop 與 OrbStack 內建了 binfmt handler、開箱就能模擬；裸 Linux 主機與 CI runner（GitHub Actions ubuntu runner 是最常見的落點）沒有，要先註冊一次：

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
```

## 可觀察訊號

- **`exec format error`**：主機試圖跑一個非原生架構的 binary，但沒有對應的 binfmt handler。這是「沒註冊模擬」的典型症狀，不是 image 壞掉。
- **image 跑得起來但明顯慢**：模擬有效——但 QEMU 逐指令翻譯有固定開銷，模擬跑的 container 啟動與運算都比原生慢。
- **某個 image `docker pull` 後不啟動 / 找不到對應架構**：該 image 沒出你主機架構的版本（例如 MySQL 5.7 只出 amd64、無 arm64 原生 image），要靠模擬跑、且得明確指定 `platform`。

## 接近真實的例子

在 Apple Silicon（arm64）主機用 Docker 跑 MySQL 5.7，因為官方只出 amd64 image，compose 要明確宣告 `platform: linux/amd64` 讓它走模擬：

```yaml
  db:
    image: mysql:5.7
    platform: linux/amd64
```

同樣的機制也用在 build：`docker buildx build --platform linux/amd64,linux/arm64` 一次出多架構時，非主機架構的那一份就靠 QEMU 模擬 build。

## 設計判讀

模擬是相容手段、不是常態解。dev 階段可以忍模擬的慢（換來跟 prod 架構一致、或跑到沒有原生 image 的舊服務）；但若模擬慢到影響開發或 CI 時間，正解是在原生架構的機器 / 遠端 builder 上跑，而不是一直吃 QEMU 的開銷。跨平台 build 的完整配置見 [BuildKit 與跨平台 build](/backend/05-deployment-platform/vendors/docker/buildkit-cross-platform/)；image 架構怎麼被 tag 凍結見 [Container](/backend/knowledge-cards/container/)。
