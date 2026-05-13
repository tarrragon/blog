---
title: "5.7 Traffic、Config 與 Control Plane Boundary"
date: 2026-05-11
description: "說明流量、設定、secret、service discovery 與管理面如何分責任與回退。"
weight: 7
tags: ["backend", "deployment", "traffic", "control-plane"]
---

Traffic、config 與 control plane boundary 的核心責任是把平台切換中的資料面與控制面分開。進入 Kubernetes、ELB、Envoy、Consul 或 Terraform 前，讀者需要先知道流量、設定、secret、service discovery 與管理面各自有不同風險與回退方式。

## Traffic Boundary

Traffic boundary 的責任是決定 request 如何進入服務、如何分流、如何回退。它包含 load balancer、routing rule、health check、sticky session、timeout 與 drain。

流量切換要能回答三個問題：哪一批 request 會到新版本、失敗時如何停止擴批、舊版本是否仍能承接回退流量。這三個答案明確後，canary 才能從比例設定變成可回退策略。

Traffic boundary 的判讀重點是 customer impact 如何被分批限制。小比例 canary、區域切流、tenant 切流與 route rule 都是不同切換單位；切換單位越清楚，rollback window 越容易被驗證。

## Config Boundary

Config boundary 的責任是決定設定如何下發、如何生效、如何回退。[config rollout](/backend/knowledge-cards/config-rollout/) 和應用版本不一定同步，因此要保留相容窗口。

高風險設定包含 payment provider endpoint、feature flag、rate limit、routing rule、timeout 與 fallback policy。這些設定變更可能不需要新 image，卻能改變 production 行為，因此要進 release gate。

## Secret Boundary

Secret boundary 的責任是讓 credential、token、certificate 與 machine identity 可輪替、可稽核、可回退。Secret 變更同時影響平台、應用與外部依賴，應使用比普通 config 更嚴格的 evidence 與 rollback window。

Secret rollout 要回答版本相容、雙軌驗證、舊 secret 撤除時間與失敗回退。這裡要接到 [7.27 Credential Rotation with Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)。

## Service Discovery Boundary

Service discovery 的責任是維持可用 endpoint 集合。它回答服務應該連到哪些實例；業務設定與版本正確性則分別交給 config boundary 與 rollout gate。

Discovery 失準常見於 rollout、擴縮容與區域故障。判讀時要拆成註冊時序、健康判斷、DNS/registry 新鮮度與 fallback 存活時間。

## Control Plane Boundary

[management plane](/backend/knowledge-cards/management-plane/) 的責任是管理設定、策略、部署與路由規則。Control plane 變更會影響大量服務，因此需要更嚴格的 evidence、gate 與 decision log。

Control plane 事故常見於規則推送、routing 誤配、secret 下發失敗與 registry 異常。這類事故要先保留 decision timeline，避免事後只看到資料面錯誤率。

## 平台元件升級的可重播流程

平台基礎元件升級是 control plane 風險最高的場景。Service mesh、ingress controller、CNI、API server 這類元件影響面廣、單次升級可能形成全域風險放大器。

對應 [5.C7 Airbnb Istio 升級治理](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)：揭露「基礎平台元件升級若缺乏分批治理會形成全域風險放大器」「分批升級 + 回退窗口」「升級驗證標準固定化」「升級事件接入 incident command 節奏」四個方向。以下基於通用工程知識展開。

可重複套用的升級流程：

1. **分批升級單位**：先在開發 / staging 叢集驗證、再選低流量 production 叢集 / namespace 作為先導、之後分批擴大。分批單位可以是叢集、namespace、region、tenant，依風險面選擇。
2. **回退窗口跟驗證標準同時設**：每批升級前定義「驗證通過」的具體訊號（SLI 維持、特定 metric 不偏移、無新告警），跟「回退窗口」（多久內可以回退）。沒有驗證標準的分批等於連續高風險動作。
3. **升級流程紀錄到 incident-style 文件**：升級期間的決策、觀察、停止點都用 incident decision log 格式紀錄。下次升級可重播、不依賴執行者個人經驗。
4. **升級事件進 timeline**：升級本身產生的短暫錯誤、reconnect、配置同步延遲，要在事故 timeline 上可見、避免被誤判成事故。

平台元件升級的核心治理價值是把「一次性高風險作業」變成「可重複的低風險作業」。第一次升級用流程，第二次升級用同樣流程，第三次升級流程已經穩定到可以委派、不再需要資深工程師親自執行。

## Managed 平台跟團隊職責邊界

平台託管化（self-managed → managed）改變維運責任跟團隊精力的分配。本段聚焦團隊職責邊界；流量跟依賴的分段切換流程見 [5.2 分階段平台遷移](/backend/05-deployment-platform/kubernetes-deployment/#分階段平台遷移)、紅隊視角的攻擊面變動見 [5.5 平台遷移期的攻擊面變動](/backend/05-deployment-platform/attacker-view-platform-entry-risks/#平台遷移期的攻擊面變動)、三者組合才完整。

Platform team 從「維持 Kubernetes 跑起來」轉向「定義 release flow、observability convention、cost governance」。managed 平台採用後第一個治理動作是顯式重新定義職責邊界、讓 platform team 從 cluster ops 轉到 release flow / observability convention / cost governance。重新定義缺位、組織轉型紅利容易被誤判為純技術升級。

對應 [5.C5 Miro Managed EKS 遷移](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)：揭露 1 個判讀（平台託管化的價值在讓團隊把心力從底層維護轉到交付效率與可靠性策略）+ 3 條策略（先定義遷移後的平台責任邊界、自動化流程取代手動平台操作、incident 跟 release policy 接回平台治理）。對應 [9.C33 Maersk + Bosch Azure AKS](/backend/09-performance-capacity/cases/maersk-bosch-azure-aks/)：揭露 Maersk 工程訴求引語「focus on things that makes the most business impact」、傳統產業 K8s 動機是治理一致性 + 釋放工程資源到業務功能（後者屬作者判讀）。以下基於通用工程知識展開。

managed 平台採用後的職責邊界重訂可以分四層：

1. **Cluster 層**：control plane 上游接管（API server、etcd、scheduler、controller-manager）、platform team 從 cluster ops 退到 cluster policy。CIS benchmark、network policy、admission controller 配置仍是 platform 責任。
2. **Cluster-internal 層**：CNI、ingress controller、service mesh、cluster DNS、storage CSI 通常仍由 platform team own。這層是 managed 服務沒覆蓋的 grey zone、需要明確 ownership。
3. **Application 層**：deployment、service、HPA、PDB 由 service team own、platform 提供 convention 跟 review process。
4. **跨層議題**：cost governance、observability convention、release flow、incident response 是 platform / service / SRE / finance 跨層協作、需要 operating model 明確化。

managed 採用後 day-1 治理項目有兩件事：明確界定 grey zone ownership（避免「以為 managed 服務什麼都管了」的心智模型）、把 platform team 心力從 cluster ops 轉到組織轉型紅利（release flow、observability convention、cost governance）。把重新定義職責當 day-2 議題、會錯失組織轉型紅利。

## 選型前判準

平台選型前要先回答：

1. 哪些變更屬於 traffic，哪些屬於 config，哪些屬於 secret。
2. 每種變更是否能分批、暫停與回退。
3. Discovery 失準時是否有可控 fallback。
4. Control plane 變更是否有 audit、owner 與 blast radius 限制。
5. 基礎元件升級是否有可重播流程跟回退窗口。
6. Managed 平台採用後團隊職責邊界是否重新定義。

這些答案決定後續要比較 load balancer、service mesh、secret manager、service registry 或 deployment controller 的能力。

## 實體服務討論承接點

實體平台文章要承接本篇的 traffic、config 與 control plane boundary。ELB、nginx、Envoy、service mesh、Consul、Kubernetes controller、secret manager 或 Terraform 的比較，要先分清它們是在資料面接流量、在控制面改規則，還是在設定面下發狀態。

若主問題是流量切換，後續文章要比較 routing rule、weight、health check、drain 與 rollback。若主問題是設定與 secret，後續文章要比較 rollout、audit、rotation 與相容窗口。若主問題是 control plane 風險，後續文章要比較 blast radius、approval、observability 與 incident decision log。

## 下一步路由

要把流量邊界接到實際 LB 合約，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要把 control plane 決策寫入事故流程，接著讀 [8.23 Control Plane Decision Log and Write-back](/backend/08-incident-response/control-plane-decision-log-write-back/)。
