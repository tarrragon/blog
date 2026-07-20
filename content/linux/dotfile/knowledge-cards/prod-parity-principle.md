---
title: "Prod Parity 原則"
date: 2026-07-06
description: "要建一個對齊 client 線上環境的本機 runtime、不知道該對齊到多細時回來讀 — parity 對齊的是凍結舊環境而非最新版"
weight: 42
tags: ["dotfile", "container", "prod-parity", "knowledge-cards"]
---

Prod parity 是「讓本機 runtime 跟線上環境逐項相同」的目標。它對齊的方向常跟開發者的直覺相反：要把環境**凍結成線上那個特定的、通常偏舊的形狀**，而非升到最新、最乾淨。凍結的目標是行為對齊、不是版本追新，這跟 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/) 用 tag 精確度落地凍結是同一件事的兩層。

## 概念位置

這條原則是個人 dotfile「環境可重現性」思想往 runtime 層的延伸：[模組零：Dotfile 心智模型](/linux/dotfile/00-dotfile-mindset/) 教的是工作站可重現，parity 教的是 runtime 可重現。要凍結到多細見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)。實作見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)。

## 對齊的是凍結環境，不是最新

接案 / 商用場景的 prod 通常是幾年前定版後就凍結的環境：PHP 7.2、MySQL 5.7、某個特定的 Debian 世代。這跟 rolling release 發行版（Arch）「永遠最新」的方向剛好相反。用你的 Arch 工作站直接當開發環境，等於在一個比線上新好幾代的環境寫 code，寫出來的成品可能用了線上沒有的語法、擴充或預設行為。

Parity 的意義就是把這個差距關掉：本機刻意退回線上那個舊形狀，讓「本機能跑」直接等於「線上能跑」。

## 要對齊哪些維度

Parity 不是只對齊語言版本號，是對齊會影響 runtime 行為的每一層：

- **語言版本**：PHP/Python/Node 的主版與 patch 版
- **底層 OS 與 libc**：Debian 世代、glibc vs musl（見 [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/)）
- **擴充/套件清單**：`php -m` 逐項相等，不是涵蓋
- **服務版本**：MySQL/Redis/nginx 的版本與關鍵設定（如 `sql_mode`、時區）
- **image 精確度**：用凍結 tag 把以上全部釘死（見 [image tag pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)）

取得這些維度的權威來源是線上環境本身：`php -m`、`SELECT @@sql_mode`、`phpinfo()` 抄回來，而不是憑印象填。

## 判讀訊號：什麼時候值得逐項對齊

Parity 是有成本的紀律，不是每個專案都要做到逐項。值得的訊號：app 有原生擴充、依賴 DB 嚴格模式行為、有時區 / locale / charset collation 邏輯（MySQL 的 collation，以及 macOS 開發 ↔ Linux 部署的檔名大小寫敏感度差異，都常在這裡咬人）、或 client 明確凍結某版環境。可放寬的訊號：app 無原生擴充、不碰 DB 嚴格模式與時區 / collation（純直譯、行為跟 OS 世代解耦），或你完全掌控 prod（自己的 VPS，想升就升）——這時本機可以直接用較新的 stable，行為分岔風險低。

把這個判斷轉成對非技術決策者的話（接案時常要向業主 / PM 說明值不值得投入）：不對齊的代價是行為分岔只在線上才炸——本機測不出、上線才發現，變成緊急修加上客戶信任損耗；對齊的投入則是一次性建一個 parity runtime（通常幾小時到一天）。比較的是「一次性投入」對上「反覆的線上驚嚇與救火」，而不是純技術潔癖。

## 邊界

Parity 對齊的是「行為」，不是「連漏洞一起複製」。凍結舊環境意味著也繼承了它的已知漏洞與 EOL 稅（如 [image tag pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/) 提到的 base image mirror 退役）。Parity 讓你**在本機重現線上問題**，不代表線上該永遠停在舊版——它跟「該不該升級 prod」是兩個獨立決策。
