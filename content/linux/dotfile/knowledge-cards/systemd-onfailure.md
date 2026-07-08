---
title: "systemd OnFailure（失敗觸發鉤子）"
date: 2026-07-03
description: "想讓某個服務進 failed 時自動觸發告警或修復動作、或發現 OnFailure 每次重啟中途都觸發把告警洗爆時讀"
weight: 19
tags: ["dotfile", "linux", "systemd", "onfailure", "knowledge-cards"]
---

`OnFailure=` 是 systemd unit 的一個指令：當這個 unit 進入 failed 狀態時，自動啟動它指定的另一個 unit。它承擔的語意是「失敗時的鉤子」——把「某個服務掛了」這個事件，接到一段你自己定義的處理（送告警、跑修復腳本）。告警邏輯因此不必是額外的 daemon，寫成一個普通的 oneshot service 掛在 `OnFailure=` 上就成，零額外常駐依賴。這是 systemd 環境裡最正統的服務失效告警起點；沒有 systemd 的容器或被 orchestrator 管的服務用不上這套，改走外部探針或平台的健康檢查。

它最反直覺、也最容易踩的一點是觸發時機：`OnFailure` 不是「放棄才觸發」，而是**每一次失敗都觸發**——包含搭配 `Restart=on-failure` 時每次 auto-restart 中途的那些失敗。[服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/) 實測一個重試 3 次後放棄的服務，`OnFailure` 觸發了 4 次（3 次 auto-restart 加 1 次最終 `start-limit-hit`）。所以只掛 `OnFailure=` 加 `Restart=`，每次瞬斷都會發一則告警、把信箱洗爆。（這個觸發次數是特定 systemd 版本的實測、跨版本調整過，機制本身「每次失敗都觸發」則跨版本成立。）

真正做到「只在放棄才告警」，靠的是在處理器腳本裡加一道狀態閘門：auto-restart 中途服務的 `ActiveState` 是 `activating`、撞上限進 failed 才是 `failed`，腳本只在 `failed` 才送。`OnFailure=` 負責「失敗就觸發」、config 的 `Restart=` / `StartLimitBurst=` 負責「重試幾次」、handler 的閘門負責「只在終局告警」——三者合起來才是「先自動重啟、放棄才吵」。

要一次把 `OnFailure=` 套到所有 service，用 [drop-in](/linux/dotfile/knowledge-cards/systemd-drop-in/)：放一個 `service.d/` 的 top-level drop-in，設定就套用到每個 `.service`。這會帶出一個遞迴陷阱——全域 drop-in 也套到告警處理器自己，它失敗會觸發自己；用 `systemctl edit` 開 override、在 `[Unit]` 段寫一行空的 `OnFailure=` 清掉繼承值擋掉。完整的鉤子鏈（處理器 unit、送出腳本、遞迴陷阱、canary 驗證）在 [服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)。

相關概念：[systemd drop-in](/linux/dotfile/knowledge-cards/systemd-drop-in/)（全域套用 `OnFailure=` 的機制、以及清空繼承值的空賦值）、[服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)（`OnFailure` 告警鏈的完整單機實作）。從單機告警往上到概念層的探活、liveness 與自動重啟見 [DevOps：systemd watchdog 與自動重啟](/operations/04-service-health/systemd-watchdog-restart/)。
