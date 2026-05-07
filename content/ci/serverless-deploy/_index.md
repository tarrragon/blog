---
title: "Serverless 部署 CI/CD"
date: 2026-05-06
description: "整理 Lambda / Cloud Functions / Edge Functions 的打包、版本推進、權限與回退流程"
tags: ["CI", "CD", "serverless", "deployment"]
weight: 14
---

Serverless 部署 CI/CD 的核心責任是把函式型服務安全推進到受管執行環境。它和長駐服務不同，風險集中在 artifact 打包、runtime 相容、權限設定、版本別名與冷啟動行為。

## 場域定位

Serverless 發布通常以函式版本為單位，並透過 alias 或流量權重切換。部署步驟看起來短，但對權限、事件來源、重試政策與 observability 欄位要求很高。

| 面向         | Serverless 部署常見責任                     | 判讀訊號               |
| ------------ | ------------------------------------------- | ---------------------- |
| Build        | function bundle、dependency、runtime target | package 是否可重現     |
| Deploy       | function version、alias、traffic shift      | 新舊版本是否可並存     |
| Permission   | IAM、resource policy、secret scope          | 執行是否具最小權限     |
| Event Source | queue/topic/http trigger 設定               | 重試與死信策略是否明確 |
| Recovery     | alias rollback、disable trigger             | 故障時是否可快速止血   |

## 常見注意事項

- 部署前要先驗證 runtime 與依賴版本，避免 deploy 成功但 invocation 失敗。
- 事件觸發型函式要明確設定 retry、dead-letter 或回放策略。
- 權限設定要收斂到最小範圍，避免函式擴權風險。
- 冷啟動與併發上限要納入發布後觀測指標。

## 下一步路由

- Gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- 失敗處理：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
- Backend 相關概念：讀 [Serverless / worker 相關知識卡](/backend/knowledge-cards/local-worker/)。
