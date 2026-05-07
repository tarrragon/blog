---
title: "Slack：2022 連線恢復與狀態通訊節奏"
date: 2026-05-07
description: "在通訊平台自身失效時，如何同步恢復節奏與對外狀態揭露。"
weight: 11
---

這起案例的核心責任是維持「恢復動作」與「外部通訊」同步。對通訊平台來說，狀態揭露本身就是事故處理的一級控制面。

## 判讀訊號

| 訊號                    | 判讀重點               | 回寫章節                                                            |
| ----------------------- | ---------------------- | ------------------------------------------------------------------- |
| reconnect spike         | 回復是否造成新一輪壓力 | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |
| status update cadence   | 對外節奏是否穩定       | [8.4](/backend/08-incident-response/incident-communication/)        |
| workspace impact spread | 影響是否跨租戶擴散     | [8.20](/backend/08-incident-response/customer-impact-assessment/)   |

## 控制面與下一步

先保住連線層穩態，再做狀態同步。事故後把通訊節奏與指揮欄位回寫 [8.19](/backend/08-incident-response/incident-decision-log/)。
