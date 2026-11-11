---
title: "Security Misconfiguration"
date: 2026-04-23
description: "說明錯誤設定如何讓安全控制失效或暴露內部能力"
weight: 121
---

Security misconfiguration 的核心概念是「系統設定讓安全控制失效或暴露不該公開的能力」。它可能出現在 CORS、TLS、debug endpoint、admin route、bucket permission、default password、WAF rule 或 error detail。 可先對照 [Release Gate](/backend/knowledge-cards/release-gate/)。

## 跟其他概念的關係

Security misconfiguration 是部署與操作層面的安全風險。程式邏輯正確仍可能因環境設定、預設值或部署流程錯誤而暴露資料或功能。 可先對照 [Release Gate](/backend/knowledge-cards/release-gate/)。

## 可觀察訊號與例子

系統需要設定檢查的訊號是服務有多個環境、公開入口或雲端資源。Debug endpoint 在 staging 可用，但若同設定進 production，可能暴露 runtime、config 或內部資料。

## 判斷條件與後果

Security misconfiguration 出在環境設定與部署流程，程式邏輯的測試涵蓋不到，每一項設定檢查缺席時，各有一類設定錯誤會原樣進到 production。沒有 baseline config 時，正確的設定沒有可比對的版本，偏差無從判定；沒有環境差異審查時，staging 為了除錯打開的 debug endpoint 隨同一份設定進到 production；沒有 secret scan 時，寫在設定檔裡的密碼隨 repo 散佈；沒有 IaC review 時，bucket permission 這類雲端資源設定的變更沒有第二個人看過；沒有 security test 時，設定錯誤只能由外部掃描或攻擊者發現；沒有 drift detection 時，在主控台手動改過的設定跟 IaC 的版本分岔，審查看的檔案已經不代表現況。影響公開入口與資料存取的設定錯一次就是對外暴露，所以這類高風險設定進 [Release Gate](/backend/knowledge-cards/release-gate/)，在上線前攔截。

CORS 是這一類設定裡最常被當成存取控制的一項，它實際管的範圍見 [same-origin policy](/backend/knowledge-cards/same-origin-policy/)。
