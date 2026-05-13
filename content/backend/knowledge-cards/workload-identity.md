---
title: "Workload Identity"
date: 2026-05-13
description: "用於機器工作負載的身份語意與授權邊界"
weight: 257
---

Workload identity 的核心概念是「把機器身份與人類身份分開治理」。它的責任是讓服務到服務授權可追蹤、可撤銷，避免長期共享憑證造成高權限擴散。可對照 [credential](/backend/knowledge-cards/credential/) 與 [federation](/backend/knowledge-cards/federation/)。

## 概念位置

Workload identity 常見於 Kubernetes、跨雲服務整合與 CI/CD 自動化。它通常搭配短時 token 與最小授權範圍，降低憑證被竊取後的利用窗口。

## 可觀察訊號與例子

需要 workload identity 判讀的訊號是「機器授權來源不清、scope 過寬、事件後難以分域回收」。例如供應商事件後，內部多個服務仍使用同一聯邦 token 存活。

## 設計責任

設計 workload identity 時要定義三件事：簽發責任主體、token 生命周期、事件後收斂流程。缺少任一項，都會把身份治理退化成不可驗證的長期信任假設。
