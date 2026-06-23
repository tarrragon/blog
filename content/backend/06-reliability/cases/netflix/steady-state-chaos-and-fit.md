---
title: "Netflix：Steady State、Chaos 與 FIT 的驗證路徑"
date: 2026-05-07
description: "把故障注入從工具操作升級成可驗證流程：先定義穩態，再設計注入與回復條件。"
weight: 21
tags: ["backend", "reliability", "case-study"]
---

Netflix chaos 實踐的核心責任是驗證「服務在失效條件下是否仍維持 [steady state](/backend/knowledge-cards/steady-state/)」。重點不是注入了多少故障，而是注入後能否用明確訊號證明系統仍可服務。

## 問題場景

許多團隊會做壓測與演練，但演練設計常停在工具層：kill instance、斷連線、延遲注入。這些動作本身不會自動產生可靠性結論。若沒有 steady state 與停止條件，演練只會留下「有做過 chaos」的紀錄。

Netflix 的價值在於把 chaos 轉成科學化驗證循環：先定義穩態，再設計可證偽的假設。

## 決策機制

一輪有效的 chaos 驗證要同時具備四個元素。

| 元素            | 核心問題                 | 交付結果     |
| --------------- | ------------------------ | ------------ |
| Steady state    | 服務正常時應維持什麼行為 | 穩態指標     |
| Hypothesis      | 失效發生後仍應維持什麼   | 可證偽假設   |
| Blast radius    | 實驗範圍怎麼限制         | 實驗邊界     |
| Abort condition | 何時立即停止             | 風險切斷條件 |

FIT（Failure Injection Testing）把注入粒度推進到 request path，讓測試更接近真實依賴路徑。這讓團隊能在不擴大範圍的前提下，驗證高價值路徑的容錯能力。

## 可觀測訊號

| 訊號                      | 判讀重點               | 對應章節                                                            |
| ------------------------- | ---------------------- | ------------------------------------------------------------------- |
| steady-state SLI          | 注入後是否維持服務承諾 | [6.22](/backend/06-reliability/steady-state-definition/)            |
| abort trigger count       | 停止條件是否可執行     | [6.20](/backend/06-reliability/experiment-safety-boundary/)         |
| fallback success ratio    | 降級與替代路徑是否有效 | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |
| trace degradation pattern | 退化是否集中於預期依賴 | [4.3](/backend/04-observability/tracing-context/)                   |

## 常見陷阱

最常見錯誤是把 chaos 視為「故障越大越好」。這會把演練從驗證流程變成壓力展示，增加真實風險卻不提升可學習性。有效做法是用最小 blast radius 驗證最高價值假設，然後逐步放大。

## 下一步路由

若要把本案例落地，先寫 [6.22](/backend/06-reliability/steady-state-definition/) 的穩態欄位，再在 [6.20](/backend/06-reliability/experiment-safety-boundary/) 定義停止條件。案例輸出的證據交給 [6.23](/backend/06-reliability/verification-evidence-handoff/) 與 [8.22](/backend/08-incident-response/incident-evidence-write-back/)。
