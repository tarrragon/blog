---
title: "5.4 service discovery"
date: 2026-04-23
description: "整理 endpoint discovery 與 DNS"
weight: 4
tags: ["backend", "deployment", "service-discovery"]
---

服務發現（[service discovery](/backend/knowledge-cards/service-discovery/)）的核心責任是讓服務在變動環境中仍能找到正確目標實例。它處理的是定位與可用集合，不處理業務設定判斷；這個邊界清楚後，部署切換與故障回退才可預期。

## DNS 與 registry

service discovery 常見兩種路徑：DNS 查詢與 service registry。DNS 提供簡化解析路徑，適合標準服務發現；registry 提供更細節的實例狀態與元資料，適合複雜路由與多租戶治理。

選擇重點是變更頻率與一致性需求。實例變動頻繁或跨區路由複雜時，registry 能提供更細控制；穩定內網服務可優先 DNS 路徑降低操作成本。

## endpoint discovery

[Internal Endpoint](/backend/knowledge-cards/internal-endpoint/) discovery 的責任是維持可連線目標集合。這包含註冊、健康檢查、摘除、重建後回註冊。服務端 readiness 與 discovery 健康判斷要對齊，否則會出現不可服務實例仍被路由的情況。

endpoint 變更需要可追溯訊號，讓事故期間能快速判讀是路由失真、註冊延遲，還是下游本身不可用。

## failure fallback

[fallback](/backend/knowledge-cards/fallback/) 在 discovery 層的責任是縮小定位失敗影響。常見策略包含本地快取最後可用集合、區域優先回退、受控重試與短暫降級。

fallback 設計要明確停止條件。長期依賴過期 endpoint 快取會造成隱性錯誤累積，事故期反而更難收斂。

## 判讀訊號

| 訊號                               | 判讀重點                           | 對應動作                             |
| ---------------------------------- | ---------------------------------- | ------------------------------------ |
| 服務延遲上升且下游錯誤分布不均     | 路由到不可用或高負載實例           | 檢查註冊健康、刷新 endpoint 集合     |
| 節點重啟後短時間大量 5xx           | 註冊與 readiness 時序不對齊        | 延後註冊時機、收斂就緒條件           |
| 跨區呼叫比例異常升高               | 區域內可用集合失真或容量不足       | 檢查區域路由策略、恢復本地優先       |
| discovery 查詢成功但連線失敗率升高 | endpoint 新鮮度不足或 DNS 快取漂移 | 縮短 TTL、加入主動刷新               |
| fallback 命中率長期偏高            | 主路徑失效被掩蓋                   | 啟動故障調查、限制 fallback 存活時間 |

## 常見誤區

把 service discovery 當成純 DNS 設定，會忽略註冊時序、健康判斷與摘除節奏。這類缺口在平時不明顯，通常在切版、擴縮容或區域異常時集中爆發。

把 fallback 命中率視為穩定指標也容易誤判。fallback 長期偏高代表主路徑問題被遮蔽，應回頭檢查 endpoint 新鮮度與註冊健康，而不是只放寬重試。

## 定位邊界

service discovery 專注「找到可用實例」。當問題進入設定分發、版本切換、策略開關，責任轉到 [Config Rollout](/backend/knowledge-cards/config-rollout/) 與部署策略章節。邊界分明能避免故障排查時把不同控制面混為一談。

## 案例回寫

發現與定位鏈路可用 [5.C3 Orbitera：managed K8s migration](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/) 回寫。先看遷移期間實例註冊、摘除與 DNS/registry 同步節奏，再對照本章判讀 endpoint 新鮮度與 fallback 壽命是否合理。
這個案例主要支撐的是「定位集合新鮮度」判讀，不直接支撐 LB 連線 timeout 或 runtime 建置一致性；若問題在連線生命週期或映像漂移，應轉到 5.3 或 5.1。

遇到「查詢成功但連線失敗率高」時，應拆成註冊時序、TTL 與快取刷新三條線同步驗證，避免把定位問題誤判成下游異常，再把證據分流到 [8.18 Incident Intake & Evidence Triage](/backend/08-incident-response/incident-intake-evidence-triage/)。

## 跨模組路由

1. 與 5.2 的交接：實例註冊與可用判定回到 [Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
2. 與 5.3 的交接：路由目標與流量合約回到 [load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。
3. 與 4.13 的交接：依賴拓樸與發現信號回到 [Service Topology 與 Dependency Map](/backend/04-observability/service-topology/)。
4. 與 8.18 的交接：定位故障的證據分流回到 [Incident Intake & Evidence Triage](/backend/08-incident-response/incident-intake-evidence-triage/)。

## 下一步路由

要把發現機制放進流量契約，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要看部署切換如何影響可用集合，接著讀 [5.2 Kubernetes 部署策略](/backend/05-deployment-platform/kubernetes-deployment/)。
