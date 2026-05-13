---
title: "Control Plane"
date: 2026-05-13
description: "負責下發策略、配置與路由決策的控制層"
weight: 253
---

Control plane 的核心概念是「管理系統行為的決策層」，負責下發策略、配置與流量規則。它的責任是控制系統怎麼運作，而不是直接承載業務資料讀寫。可對照 [management-plane](/backend/knowledge-cards/management-plane/) 與 [request-routing](/backend/knowledge-cards/request-routing/)。

## 概念位置

Control plane 常見於 service mesh、load balancer、Kubernetes 與 API gateway。它影響 data path 的行為，因此任何變更都可能造成大範圍連動，要和 [blast-radius](/backend/knowledge-cards/blast-radius/) 一起治理。

## 可觀察訊號與例子

需要 control plane 判讀的訊號是「小配置變更引發大面積錯誤」。例如路由規則更新後，多個服務同時 5xx，通常是控制層變更把錯誤快速擴散到資料路徑。

## 設計責任

控制層變更要有分批發布、回退窗口與生效可觀測性。沒有這三項，控制層會變成高權限單點風險，事件時難以定位責任邊界。
