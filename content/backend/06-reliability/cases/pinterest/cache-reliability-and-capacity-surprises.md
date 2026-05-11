---
title: "Pinterest：快取可靠性與容量驚奇治理"
date: 2026-05-07
description: "針對快取層失效與流量突增，建立容量緩衝、退化路徑與重建節奏。"
weight: 61
tags: ["backend", "reliability", "case-study"]
---

Pinterest 案例的核心責任是處理快取層造成的容量驚奇。快取命中率下滑會在短時間放大到資料層與下游依賴，因此需要預先設計退化與重建節奏。

## 問題場景

流量高峰或快取失溫時，回源壓力會瞬間上升。若沒有緩衝機制與重建策略，系統容易進入連鎖退化。

## 決策機制

| 機制                 | 核心問題             | 交付結果   |
| -------------------- | -------------------- | ---------- |
| Cache headroom       | 命中率下滑能承受多久 | 容量緩衝   |
| Graceful degradation | 快取失效時如何降級   | 服務連續性 |
| Rewarm strategy      | 熱資料如何有序回填   | 恢復節奏   |

## 可觀測訊號

| 訊號                 | 判讀重點           | 對應章節                                                            |
| -------------------- | ------------------ | ------------------------------------------------------------------- |
| cache hit ratio drop | 是否進入危險區     | [6.9](/backend/06-reliability/capacity-cost/)                       |
| fallback latency     | 降級路徑是否可接受 | [6.22](/backend/06-reliability/steady-state-definition/)            |
| rewarm backlog       | 回填是否可收斂     | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |

## 下一步路由

先在 [6.2](/backend/06-reliability/load-testing/) 模擬命中率崩落，再把恢復證據寫入 [6.23](/backend/06-reliability/verification-evidence-handoff/)。
