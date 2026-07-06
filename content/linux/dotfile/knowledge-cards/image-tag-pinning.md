---
title: "Image Tag Pinning"
date: 2026-07-06
description: "本機跟線上跑同一份 code 卻行為不一致、或 image 隔幾週重 build 就變樣時回來讀 — 為什麼 tag 要釘到 OS 世代"
weight: 40
tags: ["dotfile", "container", "prod-parity", "knowledge-cards"]
---

Image tag pinning 是「用夠精確的 tag 把 base image 凍結成一個固定形狀」的紀律。它決定的是可重現性：同一個 Dockerfile 今天 build 跟三個月後 build，跑出來的 runtime 是不是同一個——這也是讓本機跟線上逐項相同（即 parity）的前提。「本機能 build、CI 卻掛掉」而 code 沒動時，第一個要查的就是 tag 夠不夠精確。

## 浮動 tag 與凍結 tag

同一個 image 的 tag 有不同精確度，愈短愈會漂：

```text
php:7.2-fpm          浮動 — 官方隨時 rebuild，底層 OS 從 stretch 換到 buster 你不會知道
php:7.2-fpm-buster   釘住 PHP 主版 + OS 世代 — 這是 parity 的最低精確度
php:7.2.34-fpm-buster 連 patch 版也釘死 — 完全凍結
```

`php:7.2-fpm` 這種浮動 tag 的問題是它「同名不同物」：官方每次安全更新都會用同一個 tag 重推，底層 Debian 世代、內建套件版本、glibc 版本都可能換掉。你本機三個月前 pull 的 `7.2-fpm` 跟 CI 現在 pull 的 `7.2-fpm`，可能是兩個不同 OS 世代的 image。

## 為什麼 OS 世代是最低精確度

Parity 要對齊的不只是 PHP 版本，是整個 runtime 的行為，而行為很大一部分由底層 OS 世代決定：glibc 版本、內建 CA 憑證、時區資料庫、系統套件版本。釘到 `-buster` 才把這層凍結；只釘 `7.2` 等於把 OS 世代交給官方的 rebuild 節奏決定。

## 判讀訊號

「本機能跑、CI 掛掉」或「上週還好、今天重 build 就壞」而 code 沒動時，第一個要查的就是有沒有用浮動 tag。凍結 tag 把「環境變了」這個變因從除錯空間裡消掉，讓你能專注在 code 差異。

## 邊界

釘死 tag 的代價是安全更新不會自動進來——凍結的 image 也凍結了已知漏洞。所以 pinning 搭配的是「明確的升級動作」：要更新時改 tag、重測、記錄（怎麼建升級版、又留住舊版並跑對照，見 [image 版本管理與升級](/backend/05-deployment-platform/vendors/docker/image-versioning-upgrade/)），而不是靠浮動 tag 偷偷幫你更新（那正是不可重現的來源）。取捨依 [prod-parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/)——對齊凍結環境本來就要付這個稅。

底層 OS 世代為什麼影響行為，見 [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/)。實作見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)。
