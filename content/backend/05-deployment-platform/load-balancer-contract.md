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
4. drain contract：版本切換時如何讓 [in-flight](/backend/knowledge-cards/in-flight/) request 安全收斂。

這四個部分共同定義 rollout 的穩定性。服務端 [readiness](/backend/knowledge-cards/readiness/) 與平台端健康檢查要對位，否則會出現「服務已啟動但尚未可服務」的切換抖動。

## draining 與 shutdown

[draining](/backend/knowledge-cards/draining/) 的責任是讓舊實例在下線前完成現有請求。drain 視窗的 workload 分類詳見 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)，本段聚焦 LB 如何配合 drain：短請求 API 的 drain 視窗可較短；長連線、串流或 websocket 場景需要更長窗口與明確 reconnect 策略。

部署流程中，LB 摘流量、服務停止接新請求、服務完成在途請求、實例退出，這四步要有固定順序。順序穩定後，rollback 才能在同一套機制下運作。

## timeout 與 sticky session

idle [timeout](/backend/knowledge-cards/timeout/) 是連線資源與使用者體驗的平衡點。timeout 太短會增加重連與錯誤，太長會占用連線與資源。設定時依請求型態與峰值流量校準、按 SLI 訊號迭代閾值。

### Timeout 層級串聯

一條請求路徑上的 timeout 分佈在多個層級，每層各自有預設值。全路徑的 timeout 設計原則是由外到內遞減：外層（離使用者近）的 timeout 要大於內層（離資料源近），否則外層先放棄，內層還在處理一個已經沒人等的請求。

| 層級             | 典型 timeout 範圍 | 設定位置                                   |
| ---------------- | ----------------- | ------------------------------------------ |
| Client / Browser | 30-120 秒         | 前端 fetch / axios / SDK 設定              |
| CDN edge         | 5-30 秒           | CDN vendor 設定（Cloudflare / CloudFront） |
| Load balancer    | 30-60 秒          | LB idle timeout / request timeout          |
| Application      | 5-30 秒           | HTTP server read/write timeout             |
| Database / Cache | 1-5 秒            | 連線池 query timeout / connect timeout     |

這張表的每一層 timeout 都要比它的下一層大。如果 LB timeout 30 秒但 application 設了 60 秒，LB 會在 30 秒回 504 給使用者，但 application 仍然持有連線等 DB 回應——佔用連線資源卻無法交付結果。

timeout 設計的常見失誤是只調 LB 層：團隊看到使用者回報 timeout，直接把 LB timeout 從 30 秒調到 120 秒。結果是慢請求佔用 LB 連線更久、連線池被慢請求填滿、其他正常請求也開始排隊 timeout。穩定做法是先在 application 或 DB 層找出延遲根因，而非放大外層 timeout 來「等更久」。

[sticky session](/backend/knowledge-cards/sticky-session/) 適合需要短期會話一致性的場景，但它會提高特定節點負載不均與失效轉移成本。採用 sticky policy 前要先定義會話狀態落點與失效時的回復路徑。

### LB + CDN 連線生命週期協調

當 LB 上游有 [CDN](/backend/05-deployment-platform/edge-cdn-static-distribution/) 時、兩層的 timeout / retry 行為要對齊、否則會出現「使用者已經 timeout 但 origin 還在處理」這類雙層不一致：

- **CDN edge timeout** 通常比 origin LB timeout 短（5-30 秒）— edge 認定 origin 慢就放棄。若 origin LB timeout 是 60 秒、edge 在 30 秒已放棄回 504、origin 還在處理一個沒人在意的 request。應對齊兩邊的 timeout 上限。
- **CDN retry policy** 在 edge miss 後若拿不到 origin response、預設不會重試（避免雙倍 origin 流量）— LB 端的 idle timeout 設計要假設「只有一次機會」、不依賴上游重試
- **長連線（WebSocket、SSE、gRPC）通常繞過 CDN** — 直接連到 origin LB。這些連線的 idle timeout 跟一般 HTTP 不同、要單獨配置
- **Edge cache HIT 時 LB 完全沒收到 request** — 容量規劃時要把 cache hit ratio 算進 origin RPS、不是用使用者 RPS 直接 size LB

詳見 [5.9 邊緣分發與靜態資源](/backend/05-deployment-platform/edge-cdn-static-distribution/) 的 origin protection 段。

## 切流失敗的回退判讀

切流失敗的回退判讀第一步是先分辨「平台問題」跟「流量生命週期問題」、再決定回退手法。平台問題用重啟服務恢復、流量生命週期問題用凍結切換並等待震盪收斂。回退手法錯位會把事故推進第二階段。

切流失敗的本質是 connection lifecycle 跟切換時序錯位、平台元件本身往往是健康的。對應 [5.C9 反例：平台切流未先 Draining](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)：揭露切流失敗常因 connection lifecycle 管理錯位、重啟動作會放大震盪。以下基於通用工程知識展開回退節奏。

回退節奏有兩個時序階段、性質不同。

**第一階段：先讓震盪不擴大**。發現切流失敗的第一動作是凍結 rollout（不再擴大切換範圍）跟恢復舊入口權重（把 LB 規則 / DNS 加權 / service mesh 流量切回舊版本主導）。新版本不立即關閉、保留作為對照證據。這個階段的目標是穩定當前狀態、為後續分析爭取時間、所有動作要在分鐘級內完成。

**第二階段：再讓系統可恢復**。震盪不擴大後、進入「等待 + 修正」狀態。長連線跟 reconnect 風暴需要時間消化、盲目重啟新版本實例會把重連集中在新一輪實例上、造成 thundering herd。觀察連線數、reconnect rate、5xx 趨勢回到 baseline 是進入修正階段的訊號。修正動作聚焦於 drain window、idle timeout、health check、client retry 之間的節奏錯位、找出後修正、重新進入小範圍驗證。這個階段的時間尺度通常是小時級、不能用第一階段的緊急節奏對待。

兩階段時序不能合併。把第一階段（凍結 + 切回）跟第二階段（等待 + 修正）並列執行、會在連線尚未穩定時嘗試修正、造成第二次震盪。

回退時最常見的誤判是「LB 顯示新節點 healthy = 服務可服務」。LB 的健康判斷通常是定期 health check 通過，跟「該節點能承受重連潮」是不同問題。事故中要把這兩個訊號分開看：節點層健康（health check pass）、連線層健康（reconnect rate、長連線錯誤率、tail latency）。

## 切流告警條件

對應 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 的「部署專屬告警條件」段：揭露切流期告警的三個核心訊號（批次內 5xx 突增、長連線重連率快速上升、rollback time 超過既定 RTO）。本段在 case 三條基礎上補第 4 條（per-version error rate 偏離）與操作建議。

切流期告警的核心責任是對應切流批次節奏、跟日常閾值分離。日常閾值在切流期會被切換本身的短暫波動觸發、變成 alert noise；切流期需要更嚴格的「批次內偏差」訊號。

可操作的切流期告警條件：

- **批次內 5xx 異常升高**：當前批次相對於前一批的 5xx 升幅超過閾值、停止下一批。
- **長連線重連率飆升**：reconnect rate 超過 baseline N 倍、暗示 drain / timeout 錯位。
- **回退時間超過 RTO**：執行回退後恢復時間超過既定 RTO、升級為事故等級。
- **per-version error rate 偏離**：新舊版本 error rate 差距超過閾值、不收斂（屬本章補強、case 未明示）。

這些告警的閾值要在 release plan 中先定義、進事故時直接套用、避免臨時拍定。把切流告警跟一般日常告警分流到不同 channel，避免事故團隊在切流期被日常 noise 淹沒。

## 判讀訊號

| 訊號                                                                                | 判讀重點                           | 對應動作                             |
| ----------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------ |
| rollout 期間 5xx 上升且集中在舊版本                                                 | drain 順序或窗口不足               | 拉長 drain 時間、調整摘流順序        |
| readiness 通過但首批請求延遲高                                                      | 應用啟動完成與可服務條件未對齊     | 細化 readiness 指標、補 startup gate |
| reconnect storm 出現在切版後                                                        | timeout 與連線生命週期不匹配       | 調整 idle timeout、分批切流          |
| [canary](/backend/knowledge-cards/canary-release/) 比例低時正常，擴到高比例出現抖動 | LB 權重策略與服務容量曲線不一致    | 降低增量批次、補容量保護             |
| 多租戶場景下單租戶延遲飆升                                                          | sticky/routing policy 造成熱點聚集 | 分離租戶路由、加入負載重平衡         |
| 回退後 reconnect 風暴持續                                                           | 重啟動作放大震盪、未先恢復穩定路徑 | 凍結切換、等連線數穩定、再修錯位點   |

「回退後 reconnect 風暴持續」是切流事故中最容易誤判的訊號。判讀順序：先看是否「凍結切換」已執行（rollout 是否真的停了）、再看「舊入口權重」是否回到主導比例（DNS / LB 規則是否切回）、最後看連線數曲線是否進入下降。三項都做完仍見風暴持續、才考慮新版本實例層級的問題（image / config / runtime 漂移）、而非反向重啟新版本。解凍切換的條件是「連線數曲線回到 baseline + reconnect rate 低於閾值連續 N 分鐘」、不是「等夠久了就解凍」的時間導向。

## 常見誤區

把 load balancer 當成「只做轉發」的元件，會忽略它在部署與事故中的決策角色。LB 設定定義了流量切換節奏、回退可行性與故障擴散速度。

Health check 跟 readiness 的混淆會在切換時暴露隱性風險。health contract 要反映服務真實 readiness — 含依賴連線池、必要 config、關鍵背景任務狀態 — 而非停在單一探針成功訊號。

把「LB 顯示節點 healthy」當作「服務可承受流量」的訊號，也是事故中的常見誤判。健康檢查通過跟承受重連潮是不同層級的訊號。

## 案例回寫

流量契約可用 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 回寫。先看事件中的摘流量順序、drain 視窗與連線重建節奏，再回到本章判讀 connection contract 與 drain contract 是否對齊。

這個案例主要支撐的是「連線生命週期與摘流量順序」判讀，不直接支撐 container build 可重現性；若根因在映像與 runtime 漂移，應回到 5.1。

當回退後錯誤率仍高或重連風暴延續，通常表示 timeout 與 sticky policy 仍在放大舊連線狀態。先重建連線生命週期時序，再把回退判斷同步到 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨模組路由

load balancer contract 是部署平台與操作控制面的匯流點。

1. 與 5.6 的交接：drain 的生命週期定義與 workload 分類回到 [Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。
2. 與 04 的交接：版本切換訊號與錯誤率證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
3. 與 06 的交接：canary 放行與回退條件進入 [Release Gate](/backend/06-reliability/release-gate/)。
4. 與 07 的交接：入口治理與管理面保護進入 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。
5. 與 08 的交接：切換與回退判斷記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。
6. 與 [5.9 邊緣分發](/backend/05-deployment-platform/edge-cdn-static-distribution/) 的交接：CDN 是 origin LB 的上游、edge miss 後流量進 origin LB、timeout / retry 設定要協調。

## 下一步路由

要把 LB 合約放進整體部署流程，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/) 與 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。要把部署切換接到事故流程，接著讀 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。
