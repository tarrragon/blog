---
title: "Healthcare：資料主權與回復順序選型"
date: 2026-05-07
description: "醫療場景下，如何把資料主權、存取邊界與災難回復放進同一套決策。"
weight: 3
tags: ["backend", "service-selection", "case-study"]
---

這個案例的核心責任是讓資料主權與可用性同時被治理。Healthcare 場景常同時面臨資料區域限制、最小存取原則與緊急回復需求。

## 判讀訊號

| 訊號                       | 判讀重點               | 對應章節                                                                    |
| -------------------------- | ---------------------- | --------------------------------------------------------------------------- |
| cross-region data movement | 是否違反主權邊界       | [0.8](/backend/00-service-selection/security-data-protection-requirements/) |
| access audit completeness  | 存取證據是否可追溯     | [0.2](/backend/00-service-selection/state-storage-selection/)               |
| recovery ordering conflict | 回復步驟是否與合規衝突 | [0.7](/backend/00-service-selection/failure-observability-design/)          |

## 風險與邊界

將合規需求與 DR 流程分開設計，容易在事故時出現互斥決策。較穩定做法是先定義可恢復資料集合與不可跨境資料集合，再安排回復順序。

## 下一步路由

先補 [4.18](/backend/04-observability/observability-operating-model/) 的責任邊界，再在 [6.7](/backend/06-reliability/dr-rollback-rehearsal/) 驗證回復流程。
