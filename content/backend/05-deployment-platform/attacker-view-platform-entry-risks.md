---
title: "5.5 平台與入口威脅建模（Threat Modeling）"
date: 2026-04-24
description: "以概念層判讀部署平台弱點，聚焦入口、生命週期、設定與交付節奏"
weight: 5
tags: ["backend", "deployment", "threat-modeling"]
---

平台與入口威脅建模的核心責任是把部署平台的弱點維持在可操作的概念層。本章的輸出是平台問題地圖、案例對照與交接條件，讓實作前決策可先對齊，避免進入 YAML / unit file / LB rule 前就已經漏掉攻擊面。

## 服務環節問題地圖

平台弱點盤點的第一層是把服務環節跟攻擊面對齊。同一個服務交付路徑上、入口、生命週期、設定、交付節奏各自有不同失分模式。

| 環節           | 主要問題                                 | 注意事項                                                                                           | 優先案例                                                                                                                             |
| -------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 入口暴露面     | 入口分級與實際可達範圍不一致             | 入口清單與責任鏈要先對齊                                                                           | [MOVEit 2023](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/)                      |
| 生命週期訊號   | readiness、draining、shutdown 節奏不一致 | 平台合約要先定義再驗證                                                                             | [Ivanti 2024](/backend/07-security-data-protection/red-team/cases/edge-exposure/ivanti-2024-vpn-chain/)                              |
| 設定與密鑰下發 | 設定漂移與權限擴張同時發生               | 高風險設定要進 release gate，並分離 [management plane](/backend/knowledge-cards/management-plane/) | [F5 BIG-IP 2023](/backend/07-security-data-protection/red-team/cases/edge-exposure/f5-bigip-cve-2023-46747-auth-bypass/)             |
| 交付切換節奏   | 回滾與切換條件不清晰                     | 先定停損條件再定交付速度                                                                           | [TeamCity 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/teamcity-2024-cve-27198-27199-auth-path-traversal/) |

### 入口暴露面

入口暴露面的主要弱點判讀是「實際可達範圍是否超過設計意圖」。容器化、service mesh、ingress controller 升級、新增 LoadBalancer 都可能無意中把內部服務暴露到公網。入口清單跟責任鏈先對齊、能避免發版本就改變了攻擊面。升級流程跟回退窗口設計見 [5.7 平台元件升級的可重播流程](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#平台元件升級的可重播流程)。

入口暴露面的盤點要區分三類入口，各自有不同的失分模式：

1. **設計意圖內的入口**（Ingress / LoadBalancer Service / API Gateway）：這些入口有明確 owner、有 WAF / TLS 保護。弱點在於設定漂移——port 範圍擴大、路由規則放寬、wildcard host 引入。盤點方式是定期比對實際 Ingress 規則與設計意圖。
2. **隱性入口**（NodePort、hostNetwork pod、debug endpoint、metrics endpoint）：這些入口在設計時不被視為外部可達，但在特定網路拓樸下可能從外部存取。NodePort 預設 range 30000-32767 在某些雲端 security group 設定下可能對外開放。metrics endpoint（/metrics、/debug/pprof）常不帶認證、暴露服務內部狀態。
3. **暫態入口**（kubectl port-forward、臨時 LoadBalancer、tunnel 測試）：開發或除錯時臨時打開的入口，使用後忘記關閉。這類入口沒有 WAF、沒有 TLS、沒有 audit log，是攻擊面中最難盤點的部分。

Tunnel 形態的入口（cloudflared、Tailscale Funnel）有獨立的弱點盤點框架，見 [5.10 Outbound Tunnel 入口](/backend/05-deployment-platform/outbound-tunnel-entry/) 的認證疊法段。

### 生命週期訊號

生命週期訊號的弱點聚焦於脆弱窗口期被利用：readiness 過早通過、shutdown 階段仍在處理 [in-flight](/backend/knowledge-cards/in-flight/) request、drain 視窗內接收新請求，都會把短暫的脆弱窗口拉長。

脆弱窗口的判讀要跟 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 的生命週期狀態對齊：

- **startup → readiness 窗口**：服務正在初始化、依賴尚未驗證、安全中介軟體（WAF sidecar、auth proxy）可能還沒就緒。此時如果 readiness 過早通過讓流量進來，請求可能繞過安全層直接打到後端。
- **readiness → drain 窗口**：正常服務狀態，弱點集中在 readiness 條件太鬆——只檢查 port 可達但 auth middleware 沒初始化。
- **drain → shutdown 窗口**：服務正在收斂，此時安全元件（rate limiter、WAF）可能已停止更新規則但仍在處理請求。攻擊者若在 drain 窗口送入惡意請求，安全元件可能無法正常攔截。

### 設定與密鑰下發

設定與密鑰下發是最容易被忽略的維度。Image 沒變但 config / secret 變了、權限因 RBAC 漂移擴張、feature flag 在 production 偷偷開啟未經 review 的新行為。這些變更不走 release gate 的話，攻擊者有大量低噪音入口可以利用。

設定變更的弱點盤點要分兩個方向：

**顯式設定變更**（ConfigMap、Secret、feature flag 更新）：變更本身是可追蹤的，弱點在於 review 機制是否涵蓋高風險設定。payment endpoint、auth provider URL、rate limit 閾值、CORS 允許來源——這些設定的變更影響跟程式碼變更等量，應走同等 review 流程。設定變更的 review 與 rollout 策略見 [5.7 Config Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)。

**隱式設定漂移**（RBAC 逐步放寬、network policy 例外累積、service account 權限擴張）：這類變更是多次小修改累積的結果，單次變更看起來合理但累積後超出安全邊界。盤點方式是定期用 policy-as-code（OPA/Gatekeeper、Kyverno）掃描 cluster 內的 RBAC binding、network policy、pod security 設定，跟 baseline 比對偏移程度。

### 交付切換節奏

交付切換節奏的弱點判讀是「在不穩定窗口期、系統是否還有防禦能力」。Canary / rollout / rollback 期間 5xx 升高、connection 重建、auth 短暫失敗，會掩蓋同期間的攻擊訊號。沒有先定停損條件就推交付速度、是把切換期變成攻擊期的常見做法。

交付窗口期的防禦能力退化有兩個機制：

**訊號淹沒**：rollout 本身產生的短暫錯誤（5xx spike、reconnect、auth retry）跟攻擊訊號長得一樣。事故團隊在切流期把所有異常歸因於部署變更，攻擊者剛好利用這個注意力盲區。對策是把切流期 alert 跟安全 alert 分流到不同 channel，安全訊號走獨立通道、由 security on-call 獨立判讀。

**防禦元件版本不一致**：[canary](/backend/knowledge-cards/canary-release/) 期間新舊版本同時在線，WAF 規則、rate limit 設定、auth middleware 版本可能不同。攻擊者可以針對舊版本的已知弱點送流量，利用 canary 期間的路由特性讓流量到達舊版本。對策是把安全元件的更新跟應用版本解耦——WAF 規則、rate limit 是平台層設定，應在所有版本一致生效。

## 案例對照表（情境 → 判讀 → 注意事項 → 路由章節）

| 情境                               | 判讀                         | 注意事項                            | 路由章節                                                                              |
| ---------------------------------- | ---------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------- |
| 外網可達入口在發版後增加           | 入口分級與交付節奏存在脫鉤   | 入口盤點要成為交付前條件            | [5.3 Load Balancer Contract](/backend/05-deployment-platform/load-balancer-contract/) |
| readiness 通過但實際流量錯誤率上升 | 生命週期合約與流量模型不一致 | 探針、draining、shutdown 要同批驗證 | [6.5 失敗模式預判](/backend/06-reliability/failure-mode-pre-mortem/)                  |
| 設定異動與異常事件同時出現         | 設定漂移可能已跨越安全邊界   | 設定審查與責任追蹤要同步維護        | [8.5 復盤與改進追蹤](/backend/08-incident-response/post-incident-review/)             |
| 切流期間入侵告警被淹沒             | rollout 噪音掩蓋攻擊訊號     | 切流期 alert 分流、攻擊訊號獨立通道 | [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)                 |

「外網可達入口在發版後增加」是平台變更弱點盤點的頭號議題。Ingress class 換、Service type 改、LB 規則重組都可能讓原本內部服務獲得外部 IP。把入口盤點放進 release pre-check、能讓這類變更在合併前被擋下。

「readiness 通過但實際流量錯誤率上升」揭露 readiness probe 設計失誤的弱點面向。Probe 只回 200 OK 不代表服務可承受真實流量、攻擊者剛好可以在這個窗口送高頻 request 看是否壓垮服務。Readiness 反映依賴就緒條件而非單一探針成功、能縮短這個窗口。

「設定異動與異常事件同時出現」是 config rollout 的弱點風險。Config 變更後出現異常事件、可能是設定本身的問題、也可能是攻擊者剛好利用了設定窗口。Config 審查跟責任追蹤同步維護、能讓事後復盤分辨兩者。

「切流期間入侵告警被淹沒」是新加入的議題。切流產生大量短暫 5xx、reconnect、auth retry、可能淹沒真正的攻擊訊號。把切流期 alert 跟一般 alert 分流、攻擊訊號走獨立通道、能避免攻擊在切流窗口下被忽略。

## 平台遷移期的攻擊面變動

對應 5.C1 / 5.C4 / 5.C5 揭露的遷移分段切換流程、本段從弱點盤點角度補充其攻擊面變動風險（case 庫未直接揭露此角度、屬通用工程經驗）。遷移期的職責邊界重訂見 [5.7 Managed 平台跟團隊職責邊界](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#managed-平台跟團隊職責邊界)、弱點盤點跟治理視角合用才完整。

平台遷移（self-managed → managed、單 cluster → 多 cluster、舊版本 → 新版本）會短期擴大攻擊面、然後逐步收斂。遷移期顯式管理攻擊面變化、避免雙軌期變成攻擊面雙倍期。

可重複套用的弱點判讀：

1. **盤點雙軌期入口**：舊平台跟新平台的入口清單分別列出、確認新平台不繼承舊平台已知漏洞、舊平台的廢棄入口確實關閉。
2. **identity / credential 重新對位**：service account、API token、TLS cert 在新平台是否走新的 rotation flow、舊平台的 credential 是否在切換完成後撤除。
3. **observability 對應更新**：新平台的 audit log、access log、security event 是否進入同一個 SIEM / 告警通道、避免遷移期內攻擊訊號掉到觀測缺口。
4. **回退路徑的攻擊面評估**：回退到舊平台時、舊平台是否仍處於最新 patch 狀態、回退本身會不會把已修補的漏洞重新引入。

遷移計畫要把資安 review 列為 gate 之一、讓遷移期攻擊面變動進入可見治理流程。沒有這道 gate、遷移期容易被當成純技術項目處理、漏掉攻擊面的隱性擴大。

## 到實作前的最後一層

弱點盤點在概念層回答的是平台風險判讀與交接節奏。當討論進入 Kubernetes 欄位、LB 規則、系統服務參數或腳本配置時，就代表已進入實作層。

實作層的防護驗證跟概念層分工：實作層看具體 YAML / config / rule 是否符合 hardening baseline、概念層看交付路徑跟責任鏈是否完整。兩者都做才能讓平台變更的攻擊面在 release 前可見。

進實作層後接 [07 資料保護模組](/backend/07-security-data-protection/) 的具體 hardening 章節、跟 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 對齊入口分級。
