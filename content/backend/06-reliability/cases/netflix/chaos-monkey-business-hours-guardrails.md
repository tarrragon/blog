---
title: "Netflix：Business-Hours Chaos 與 Guardrails"
date: 2026-05-07
description: "Chaos Monkey 為何刻意在 business hours 執行：把即時應變能力納入驗證，並用 guardrails 限制實驗風險。"
weight: 22
tags: ["backend", "reliability", "case-study"]
---

Netflix 把 Chaos Monkey 放在 business hours 執行，核心責任是同時驗證系統韌性與團隊反應能力。若只在離峰或隔離環境跑故障注入，很多真實依賴與協作問題不會被看見。

## 問題場景

團隊常把 chaos 排在低流量時段，理由是比較安全。這種做法雖然降低短期風險，但也降低驗證價值：人員不在位、依賴流量特徵不同、通訊鏈條沒被真正測到。最後得到的是工具可執行，不是服務可承受。

## 驗證機制

Business-hours chaos 是把風險放進 guardrails 內驗證，風險範圍是收斂的。

| 機制         | 核心問題                     | 控制方式                            |
| ------------ | ---------------------------- | ----------------------------------- |
| 時段限制     | 事故處理人力是否在線         | 僅在可支援時段啟動                  |
| 實驗範圍限制 | 是否影響過大 blast radius    | 先從小範圍服務群組啟動              |
| 停止條件     | 何時立即結束實驗             | 明確 abort trigger 與 rollback 路徑 |
| 事後回寫     | 是否有把結果回寫到工程控制面 | 固定接 [8.22 evidence write-back]   |

這個機制的本質是「在可控邊界內接近真實情境」，而不是追求更大故障。

## 可觀測訊號

| 訊號                    | 判讀重點               | 對應章節                                                     |
| ----------------------- | ---------------------- | ------------------------------------------------------------ |
| abort trigger latency   | 停止條件是否能即時生效 | [6.20](/backend/06-reliability/experiment-safety-boundary/)  |
| on-call handoff quality | 值班與指揮鏈條是否順暢 | [8.2](/backend/08-incident-response/incident-command-roles/) |
| steady-state drift      | 實驗期間是否偏離穩態   | [6.22](/backend/06-reliability/steady-state-definition/)     |
| communication lag       | 內外部更新是否跟上變化 | [8.4](/backend/08-incident-response/incident-communication/) |

## 常見陷阱

常見誤解是「business hours chaos 比較危險，所以應該避免」。真正風險在於沒有 guardrails，而不是時段本身。若有明確範圍、停止條件與值班協調，business-hours 測到的結果反而更接近真實事故。

## 下一步路由

先在 [6.19 Reliability Readiness Review](/backend/06-reliability/reliability-readiness-review/) 檢查實驗前置條件，再到 [6.20](/backend/06-reliability/experiment-safety-boundary/) 寫 guardrails 與 abort 條件。實驗結果回寫 [8.6 Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 與 [8.22](/backend/08-incident-response/incident-evidence-write-back/)。

## 引用源

- [Netflix/SimianArmy Wiki: Chaos Monkey](https://github.com/Netflix/SimianArmy/wiki/Chaos-Monkey)
- [Netflix/chaosmonkey](https://github.com/Netflix/chaosmonkey)
