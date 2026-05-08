---
title: "5.3 load balancer 合約"
date: 2026-04-23
description: "整理 idle timeout、draining 與 health check"
weight: 3
tags: ["backend", "deployment", "load-balancer"]
---

流量平衡合約（load balancer contract）的核心責任是定義平台何時把流量交給服務，以及服務何時安全退出流量。這份合約一旦模糊，部署、擴容、回退與事故處理都會出現同型問題。

## contract 組成

[Load Balancer Contract](/backend/knowledge-cards/load-balancer-contract/) 可以拆成四個部分：

1. routing contract：哪些路徑導向哪些服務，如何處理權重與版本。
2. health contract：哪些訊號代表可接流量，何時摘除節點。
3. connection contract：長短連線的 idle timeout、keepalive、重試規則。
4. drain contract：版本切換時如何讓 in-flight request 安全收斂。

這四個部分共同定義 rollout 的穩定性。服務端 [readiness](/backend/knowledge-cards/readiness/) 與平台端健康檢查要對位，否則會出現「服務已啟動但尚未可服務」的切換抖動。

## draining 與 shutdown

[draining](/backend/knowledge-cards/draining/) 的責任是讓舊實例在下線前完成現有請求。短請求 API 的 drain 視窗可較短；長連線、串流或 websocket 場景需要更長窗口與明確 reconnect 策略。

部署流程中，LB 摘流量、服務停止接新請求、服務完成在途請求、實例退出，這四步要有固定順序。順序穩定後，rollback 才能在同一套機制下運作。

## timeout 與 sticky session

idle [timeout](/backend/knowledge-cards/timeout/) 是連線資源與使用者體驗的平衡點。timeout 太短會增加重連與錯誤，太長會占用連線與資源。設定時要以請求型態與峰值流量校準，而不是套用單一預設值。

[sticky session](/backend/knowledge-cards/sticky-session/) 適合需要短期會話一致性的場景，但它會提高特定節點負載不均與失效轉移成本。採用 sticky policy 前要先定義會話狀態落點與失效時的回復路徑。

## 判讀訊號

| 訊號                                    | 判讀重點                           | 對應動作                             |
| --------------------------------------- | ---------------------------------- | ------------------------------------ |
| rollout 期間 5xx 上升且集中在舊版本     | drain 順序或窗口不足               | 拉長 drain 時間、調整摘流順序        |
| readiness 通過但首批請求延遲高          | 應用啟動完成與可服務條件未對齊     | 細化 readiness 指標、補 startup gate |
| reconnect storm 出現在切版後            | timeout 與連線生命週期不匹配       | 調整 idle timeout、分批切流          |
| canary 比例低時正常，擴到高比例出現抖動 | LB 權重策略與服務容量曲線不一致    | 降低增量批次、補容量保護             |
| 多租戶場景下單租戶延遲飆升              | sticky/routing policy 造成熱點聚集 | 分離租戶路由、加入負載重平衡         |

## 常見誤區

把 load balancer 當成「只做轉發」的元件，會忽略它在部署與事故中的決策角色。LB 設定其實定義了流量切換節奏、回退可行性與故障擴散速度。

把 health check 視為固定 URL 檢查，會讓複雜服務在切換時暴露隱性風險。health contract 要反映服務真實 readiness，而不是單一探針成功訊號。

## 案例回寫

流量契約可用 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 回寫。先看事件中的摘流量順序、drain 視窗與連線重建節奏，再回到本章判讀 connection contract 與 drain contract 是否對齊。

當回退後錯誤率仍高或重連風暴延續，通常表示 timeout 與 sticky policy 仍在放大舊連線狀態。先重建連線生命週期時序，再把回退判斷同步到 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨模組路由

load balancer contract 是部署平台與操作控制面的匯流點。

1. 與 04 的交接：版本切換訊號與錯誤率證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
2. 與 06 的交接：canary 放行與回退條件進入 [Release Gate](/backend/06-reliability/release-gate/)。
3. 與 07 的交接：入口治理與管理面保護進入 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。
4. 與 08 的交接：切換與回退判斷記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要把 LB 合約放進整體部署流程，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/) 與 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。要把部署切換接到事故流程，接著讀 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。
