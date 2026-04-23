---
title: "Security Misconfiguration"
date: 2026-04-23
description: "說明錯誤設定如何讓安全控制失效或暴露內部能力"
weight: 120
---

Security misconfiguration 的核心概念是「系統設定讓安全控制失效或暴露不該公開的能力」。它可能出現在 CORS、TLS、debug endpoint、admin route、bucket permission、default password、WAF rule 或 error detail。

## 概念位置

Security misconfiguration 是部署與操作層面的安全風險。程式邏輯正確仍可能因環境設定、預設值或部署流程錯誤而暴露資料或功能。

## 可觀察訊號與例子

系統需要設定檢查的訊號是服務有多個環境、公開入口或雲端資源。Debug endpoint 在 staging 可用，但若同設定進 production，可能暴露 runtime、config 或內部資料。

## 設計責任

防護要包含 baseline config、環境差異審查、secret scan、IaC review、security test 與 drift detection。高風險設定應進入 [Release Gate](release-gate/)。
