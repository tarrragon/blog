---
title: "5.C9 反例：平台切流未先 Draining"
date: 2026-05-07
description: "切流時忽略連線清退造成請求錯誤與重試風暴。"
weight: 9
tags: ["backend", "deployment", "case-study"]
---

這個反例的核心責任是說明部署平台切換失敗常在 connection lifecycle 管理——平台元件本身健康，事故來源是切換時序錯位。

## 事故長相

平台切流一開始看似成功，新的 instance 也通過 readiness，但長連線、背景工作與 load balancer 仍把流量送到即將下線的節點。使用者看到的是短時間大量 5xx、重連風暴與 timeout。

典型 timeline：

- **T+0**：開始切流，新版本 pod readiness 通過，LB 開始導入流量。
- **T+30s**：5xx spike 出現。舊 pod 的 endpoint 尚未從所有 kube-proxy / envoy 移除，部分客戶端仍打到舊 pod。舊 pod 同時收到 SIGTERM 開始 shutdown，在途請求被中斷。
- **T+2m**：長連線客戶端偵測到斷線，觸發 reconnect。大量客戶端同時重連到新 pod，形成 [reconnect storm](/backend/knowledge-cards/thundering-herd/)。新 pod 的連線數瞬間飆高，部分 pod 因連線數超出預期開始 timeout。
- **T+5m**：on-call 判斷切流失敗，決定回退。但回退操作需要時間——DNS 權重切回、LB 規則恢復、舊 pod 重新啟動。
- **T+15m**：回退完成，舊版本重新接流量。但 reconnect storm 尚未收斂，連線數曲線仍高於 baseline，客戶端在新舊入口之間震盪。
- **T+30m**：連線數逐漸回落，錯誤率回到 baseline。事故實際影響時間遠超切流本身。

## 為什麼會擴大

事故擴大的根因是 drain、idle timeout、health check、client retry 四者節奏錯位。每一對的不同步都會放大問題：

**drain 與 endpoint 摘除不同步**：pod 收到 SIGTERM 開始 shutdown，但 endpoint 還在 LB 的可用集合中（endpoint controller 同步有延遲）。這段窗口內新請求仍被導到即將關閉的 pod，產生 5xx。解法是 preStop hook 先等 endpoint 傳播（5-15 秒），再開始 graceful shutdown。

**idle timeout 與 drain window 不同步**：LB 的 idle timeout 設 60 秒，但 drain window 只有 30 秒。drain 結束後 pod 被強制終止，LB 側認為連線還活著（60 秒內不算 idle），繼續送流量到已不存在的 pod。結果是 LB 拿到 connection reset，觸發重試或回 502。

**health check 與 readiness 語意不同步**：LB health check 每 10 秒打一次，連續 3 次失敗才摘除。pod 已經 not-ready 但 LB 要 30 秒後才反映。這 30 秒窗口跟 drain window 疊加，讓舊 pod 在 shutdown 狀態下持續收到流量。

**client retry 與 reconnect 策略不同步**：客戶端偵測到連線中斷後立即重試（無 backoff），大量客戶端同時重連。如果客戶端沒有 jitter，重連請求會集中在同一毫秒到達，形成 thundering herd。

這四組錯位在穩態下不會出現——穩態時 drain / timeout / health check 各自運作不衝突。只有在切流時四者同時被觸發，錯位才會互相放大。

## 回退判讀

回退分兩個階段，性質不同、節奏不同、不能合併執行。

**第一階段：凍結 + 恢復穩定路徑（分鐘級）**。發現切流失敗的第一動作是停止下一批切流（freeze rollout），然後恢復舊入口權重（DNS 加權切回 / LB 規則回復）。新版本 pod 不立即關閉——保留作為對照證據，也避免關閉動作觸發第二波 reconnect。這個階段的目標是「讓震盪不擴大」，所有動作要在 5 分鐘內完成。

**第二階段：等待收斂 + 修正錯位（小時級）**。凍結後進入觀察狀態。reconnect storm 需要時間消化——客戶端逐漸穩定到舊入口、連線數曲線下降、5xx 回到 baseline。觀察指標：連線數曲線、reconnect rate、per-version error rate。三項都回到 baseline 且持續 N 分鐘（通常 10-15 分鐘），才算穩定。穩定後開始修正：找出 drain / timeout / health check / retry 的具體錯位點，修正後重新進入小範圍驗證。

第一階段的陷阱是「回退了但沒凍結」——回退流量的同時繼續推下一批切流，兩個動作互相衝突。第二階段的陷阱是「時間到了就解凍」——用時間而非指標判斷穩定，可能在連線數仍高時重新切流。

## 這個事故教給後續章節什麼

- **5.3 load balancer 合約**的「切流告警條件」段：四條告警（批次 5xx、reconnect rate、RTO 超時、per-version error rate 偏離）直接來自這類事故的觀測需求。
- **5.6 Platform Lifecycle Contract**的「三種 Workload 的 Drain 差異」段：短 API、長連線、worker 的 drain 條件不同——這個事故揭露混用單一 drain window 的後果。
- **5.8 Rollout/Drain/Rollback**的「Traffic / Drain」段退場順序：readiness 先轉 not-ready → 保留 drain 窗口 → 確認連線數下降 → 終止進程，是從這類事故的 timeline 反推出來的。

## 部署專屬告警條件

- 切流批次內 5xx 突增（相對於前一批的升幅超過閾值）
- 長連線重連率快速上升（reconnect rate 超過 baseline N 倍）
- rollback time 超過既定 RTO（執行回退後恢復時間超標）
- per-version error rate 偏離（新舊版本 error rate 差距持續不收斂）

這些告警的閾值要在 release plan 中先定義。切流期告警跟日常告警分流到不同 channel，避免日常 noise 淹沒切流期的關鍵訊號。

## 下一步路由

回 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/) 看流量契約與回退框架。回 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 看 drain 的 workload 分類。回 [6.7 DR/Rollback Rehearsal](/backend/06-reliability/dr-rollback-rehearsal/) 看回退演練如何預防這類事故。
