---
title: "Discord：Gateway 容量事件與恢復節奏"
date: 2026-05-07
description: "長連線平台在容量邊界被擊穿時，如何控制擴散並分批恢復。"
weight: 31
---

這起案例的核心責任是把長連線流量恢復做成可分批節奏。容量事件若直接全量回復，容易觸發二次擁塞。

## 判讀訊號

| 訊號                   | 判讀重點         | 回寫章節                                                            |
| ---------------------- | ---------------- | ------------------------------------------------------------------- |
| gateway saturation     | 是否超出穩態邊界 | [6.22](/backend/06-reliability/steady-state-definition/)            |
| reconnect queue growth | 回復是否放大壓力 | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |
| region imbalance       | 影響是否偏斜     | [8.20](/backend/08-incident-response/customer-impact-assessment/)   |

## 邊界判讀

這個案例的邊界是「長連線回復節奏」不能跨過穩態容量。主要風險是全量 reconnect 直接壓垮 gateway，讓恢復動作本身成為二次事故來源。

## 下一步路由

先定義分批回復門檻，再在 [8.14](/backend/08-incident-response/multi-incident-coordination/) 固化協調規則，並回寫 [6.22](/backend/06-reliability/steady-state-definition/) 的穩態門檻。
