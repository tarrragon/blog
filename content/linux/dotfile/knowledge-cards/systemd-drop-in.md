---
title: "systemd drop-in（不改原檔的設定疊加）"
date: 2026-07-03
description: "想覆寫套件裝的 systemd unit 又不被升級蓋掉、一次對所有 service 套一條設定、或搞不清 systemctl edit 改了哪個檔時讀"
weight: 20
tags: ["dotfile", "linux", "systemd", "drop-in", "knowledge-cards"]
---

drop-in 是 systemd 疊加設定的機制：不去改原始的 unit 檔，而是在一個對應的 `.d/` 目錄裡放一小段 `.conf`，systemd 載入時把它疊加或覆寫到原 unit 上。它承擔的語意是「在原檔之外改設定」——套件裝的 unit 檔升級時會被覆蓋，寫在 drop-in 裡的自訂設定不會，因為它是獨立的檔案。這讓「客製套件裝的服務」跟「升級不衝突」兩件事同時成立。

drop-in 有兩種作用範圍。針對單一 unit，`<unit>.service.d/` 目錄下的 `.conf` 只疊加到那個 unit。要一次套用到某個型別的所有 unit，用 top-level drop-in——放在 `service.d/` 這種型別目錄下的設定，會套到每個 `.service`。[服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/) 就是用一個 `service.d/onfailure.conf` 的 top-level drop-in，把 [OnFailure](/linux/dotfile/knowledge-cards/systemd-onfailure/) 告警鉤子一次掛到系統上所有服務。改完要 `sudo systemctl daemon-reload` 讓 systemd 重讀。

`systemctl edit <unit>` 是操作 drop-in 的標準入口：它開的是那個 unit 的 drop-in override 檔（`/etc/systemd/system/<unit>.d/override.conf`）、不是套件裝的原始 unit 檔。搞不清「我剛改的設定寫進哪」時，記住這條——`systemctl edit` 動的永遠是 drop-in、不是套件裝的原檔，`systemctl cat <unit>` 可以看到原檔加所有 drop-in 疊起來的最終結果。

drop-in 疊加有一個要注意的語意：對一個接受多值的設定，drop-in 是「再加一條」而不是「取代」。要清空某個從原檔或上層 drop-in 繼承來的值，得先寫一行空賦值（例如空的 `OnFailure=`）把它歸零、再視需要重設。[OnFailure](/linux/dotfile/knowledge-cards/systemd-onfailure/) 的遞迴陷阱正是靠這招擋掉——全域 drop-in 把 `OnFailure=` 也套到告警處理器自己，用一行空的 `OnFailure=` override 清掉繼承值、避免它失敗時觸發自己。

相關概念：[systemd OnFailure](/linux/dotfile/knowledge-cards/systemd-onfailure/)（最常用 top-level drop-in 全域套用的指令、以及空賦值清繼承的實例）、[服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)（drop-in 掛全域告警鉤子的完整實作）。
