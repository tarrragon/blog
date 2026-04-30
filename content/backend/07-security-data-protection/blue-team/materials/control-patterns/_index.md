---
title: "7.BM4 藍隊控制模式素材"
tags: ["Blue Team", "Control Pattern", "Validation"]
date: 2026-04-30
description: "定義藍隊控制模式分類，支援 release gate、偵測驗證與事故交接"
weight: 7254
---

藍隊控制模式素材的責任是把反覆出現的防守做法整理成可搬運模式。控制模式介於來源卡與文章之間，負責把專業來源轉成服務可操作欄位。

## 模式分類

| 模式                           | 責任                                                                   | 承接章節    |
| ------------------------------ | ---------------------------------------------------------------------- | ----------- |
| Control owner pattern          | 明確主責、協作與升級角色                                               | 7.B1 / 08   |
| Evidence chain pattern         | 保留判讀、驗證、回復與通報證據                                         | 7.B3 / 7.7  |
| Detection lifecycle pattern    | 管理規則來源、測試、誤報與退場                                         | 7.B2 / 7.13 |
| Vulnerability response pattern | 管理曝險、緩解、修補與驗證                                             | 7.B2 / 05   |
| Exercise write-back pattern    | 把演練結果回寫到 [runbook](/backend/knowledge-cards/runbook/) 與控制面 | 7.B4 / 7.19 |

## 使用原則

控制模式的使用原則是先定義判讀欄位，再交給章節發展情境。模式卡提供可搬運骨架，文章負責說明它在真實服務中的取捨、風險與下一步路由。
