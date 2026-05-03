---
title: "6.8 Release Gate 與變更節奏"
date: 2026-05-01
description: "把驗證、migration、相容性納入放行判準"
weight: 8
---

## 概念定位

Release gate 是把放行決策從「看起來可以」變成「條件已經達成」的控制面。它的責任不是擋住所有變更，而是把哪些變更可以進、哪些變更要等、哪些變更必須先補證據說清楚。當 gate 被寫成政策，團隊就能用同一套條件判斷 CI、SLO、migration、相容性與高風險時段。

這個節點先處理節奏，再處理工具。先問變更是否應該放行，再問這次放行需要哪些訊號與檢查。當 gate 被看成節奏控制，讀者就會明白為什麼 freeze 不是例外，而是可靠性政策的一部分。

## 大綱

- release gate 的核心責任：把放行決策從個人判斷變成可驗證條件
- gate 類別：CI 通過、SLO 健康、error budget 餘額、migration 可逆、相容性檢查
- 變更節奏：deploy frequency、batch size、change failure rate（DORA 四指標）
- freeze 條件：error budget 耗盡、事故進行中、高風險時段
- 跟 [6.6 SLO](/backend/06-reliability/slo-error-budget/) 的耦合：error budget 是 gate 的一個條件
- 跟 [05 部署](/backend/05-deployment-platform/) 的交接：gate 通過後 rollout 策略接手
- 反模式：gate 流於形式、freeze 無 owner、緊急修復繞過 gate 變常態

## 核心判讀

gate 的責任是把放行條件具體化。CI green 只代表測試通過，不代表服務可以安全進 production；SLO 健康只代表目前風險可接受，不代表任何變更都能繼續推；migration 可逆只代表退路存在，不代表已經證明回退完全無害。這些條件要一起看，才知道 gate 有沒有真的在做事。

freeze 的責任是把風險攔住。當 error budget 耗盡、事故正在進行、或高風險時段已到時，freeze 不應該被視為拖延，而應該被視為維持可靠性的一種放行決策。這樣的政策，會比只看 CI 更接近真實的部署世界。

## 判讀訊號

- gate 只看 CI green、不看 SLO / error budget / migration 可逆性
- emergency bypass 從例外變週常
- freeze 條件無 owner、沒人知道誰能解凍
- change failure rate 沒量、無法評估 gate 是否有效
- migration 沒做向後相容檢查、rollback 後資料不一致

## 案例對照

Google 很適合用來看 gate 需要什麼政策語言，因為它把 SLO、error budget 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 連成一套治理系統。Stripe 則適合用來看交易場景下的 gate，因為 idempotency、canary 與 migration safety 會把放行和交易正確性綁在一起。Shopify 可以補峰值節奏，因為 BFCM 前的 gate 不只是測試通過，而是要確定高峰時仍能守住容量與隔離。

Amazon 和 Meta 則提供更偏架構層的 gate 視角。前者告訴我們隔離邊界與 [blast radius](/backend/knowledge-cards/blast-radius/) 會直接影響哪些變更可以放行，後者則顯示 control plane 變更如果沒有足夠的 gate，可能直接把整個區域或整個公司拖進事故。把這些案例一起看，gate 就不再只是 CI 的最後一步，而是整個變更節奏的控制面。

## gate 類別

| 類別           | 作用                             | 常見例子                                                             |
| -------------- | -------------------------------- | -------------------------------------------------------------------- |
| CI 通過        | 確認基礎測試與 artifact 可重播   | unit / integration / lint                                            |
| SLO 健康       | 確認服務健康仍在可接受區間       | burn rate、error budget                                              |
| Migration 可逆 | 確認 schema / data 變更有退路    | forward / backward compatibility                                     |
| 相容性檢查     | 確認上下游協議與資料不會互相打架 | contract / schema checks                                             |
| 高風險時段凍結 | 確認人在、窗在、風險可控         | freeze window、[on-call](/backend/knowledge-cards/on-call/) presence |

這張表的重點不是分類本身，而是每一類都要對應 owner 與回退條件。沒有回退條件的 gate，只是心理安慰。

## 交接路由

- 05 部署：canary / progressive delivery 實作
- 06.6 SLO：error budget 餘額查詢
- 06.10 contract testing：契約通過作為放行條件
- 06.11 migration safety：可逆性檢查
- 06.13 perf regression gate：退化作為 freeze 條件
- 07 資安：高風險變更的權限約束
- 08 事故閉環：事故進行中 freeze 觸發
- 06.17 feature flag：rollout 的細粒度控制層
- 06.18 reliability metrics：CFR 是 gate 健康度
