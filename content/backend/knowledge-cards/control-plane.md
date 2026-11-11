---
title: "Control Plane"
date: 2026-05-13
description: "負責下發策略、配置與路由決策的控制層"
weight: 254
---

Control plane 的核心概念是「管理系統行為的決策層」，負責下發策略、配置與流量規則。它的責任是控制系統怎麼運作，而不是直接承載業務資料讀寫。可對照 [management-plane](/backend/knowledge-cards/management-plane/) 與 [request-routing](/backend/knowledge-cards/request-routing/)。

## 跟其他概念的關係

Control plane 常見於 service mesh、load balancer、Kubernetes 與 API gateway。Kubernetes 的控制平面以 [Control Loop](/backend/knowledge-cards/control-loop/) 的方式運作：持續比對期望狀態與實際狀態並修正落差。它影響 data path 的行為，因此任何變更都可能造成大範圍連動，要和 [blast-radius](/backend/knowledge-cards/blast-radius/) 一起治理。

## 可觀察訊號與例子

需要 control plane 判讀的訊號是「小配置變更引發大面積錯誤」。例如路由規則更新後，多個服務同時 5xx，通常是控制層變更把錯誤快速擴散到資料路徑。

## 判斷條件與後果

控制層的一次變更會同時改變所有讀取它的資料路徑，這次變更的風險由三項配套決定。變更一次推到全部節點時，錯誤的規則在一個發布週期內擴散到每個服務，[blast radius](/backend/knowledge-cards/blast-radius/) 等於整條 data path，原因是資料路徑照控制層下發的規則運作，不檢查規則本身是否正確；分批發布把第一批受影響的範圍限制在一小群節點。沒有回退窗口時，發現錯誤之後只能再寫一版新設定往前修，錯誤持續到新設定生效為止。生效不可觀測時，路由更新後多個服務同時回 5xx，排查的人分不出是哪一次控制層變更、哪一批節點已經套用，責任邊界定位不出來。
