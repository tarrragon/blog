---
title: "glibc 與 musl"
date: 2026-07-06
description: "考慮用 alpine image 縮小體積、或 PHP/Python 擴充在容器裡行為跟線上不同時回來讀 — 兩種 libc 的差異與怎麼選"
weight: 41
tags: ["dotfile", "container", "prod-parity", "knowledge-cards"]
---

glibc 與 musl 是兩套不同的 C 標準函式庫實作。C 標準庫是幾乎每個 Linux 程式都會鏈結的最底層，負責記憶體配置、字串處理、DNS 解析、locale、執行緒這些基本能力。選哪一套會滲透到上層程式的行為，而不只是體積差異，是 [prod-parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/) 要盯的底層項目之一。

## 概念位置

這條規則跟 [image tag pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/) 同源：都是把 runtime 底層凍結到跟 prod 相同。判準見 [prod-parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/)。選 base image 的實作見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/) 與 [Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)。

## 誰用哪一套

主流商用發行版跟輕量容器發行版分屬兩邊：

```text
glibc  Debian, Ubuntu, RHEL/Rocky/Alma, CentOS  ← 商用 prod 幾乎都在這邊
musl   Alpine Linux                              ← 容器界為了縮小體積常選這邊
```

Alpine 的賣點是 image 極小（base 約 5MB vs Debian 約 70MB），所以很多人反射性地選 `php:7.2-alpine` 來省空間。

## 為什麼 prod 是 glibc 就別用 musl

當 prod 跑在 Debian/Ubuntu（glibc）而你本機 image 用 Alpine（musl），你就在一個跟線上不同 libc 的環境開發，差異會在幾個地方咬人：

- **DNS 解析行為不同**：musl 不讀 `/etc/nsswitch.conf`、對 `search` domain 與並發查詢的處理跟 glibc 有別，容器內連內部服務時可能出現「本機解得到、線上解不到」或反過來。
- **原生擴充要重編**：PHP/Python 的 C 擴充是對著某套 libc 編的；某些預編譯 wheel/extension 只提供 glibc 版，在 musl 上要自己編、甚至編不起來。
- **locale 與時間格式**：musl 的 locale 支援比 glibc 精簡，依賴特定 locale 的字串排序、日期格式可能不一致。

這些差異單獨看都小，但它們的共通點是「在你最不預期的地方，讓本機跟線上行為分岔」——正好抵消了本機模擬 prod 的目的。

## 判讀訊號

「本機容器跑得好好的、上線卻在 DNS 或某個原生擴充炸掉」是 libc 不一致的典型症狀。選 base image 時的判準很直接：**prod 是什麼 libc，本機就用什麼**。省那 60MB 換來的除錯成本遠高於節省。

## 邊界

musl 本身沒有問題——如果 prod 也跑 Alpine，那本機就該用 Alpine，parity 依然成立。重點不是「musl 比較差」，是「本機跟 prod 的 libc 要一致」。一個例外：如果 app 是純靜態連結的 binary（`CGO_ENABLED=0` 的 Go、Rust 靜態編譯），它不帶 libc 相依，上面 DNS / 原生擴充 / locale 三個咬人點全部消失——這時 base image 用 alpine 完全可行，即使 prod 的 base 不同（binary 自帶一切、不吃 image 的 libc）。
