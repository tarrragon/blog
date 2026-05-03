---
title: "6.6 SLO 與 Error Budget 政策"
date: 2026-05-01
description: "把可靠性目標轉成可驗證量測與凍結條件"
weight: 6
---

## 概念定位

SLO 與 error budget 是把可靠性從口號變成政策的工具。SLO 定義的是服務要對哪個使用者旅程負責，error budget 定義的是這個責任在一段時間內可以承受多少退化。當這兩個條件被寫清楚，可靠性就能從「感覺上應該穩」變成「超過哪個門檻就不能繼續往前」。

這個節點先處理目標，再處理門檻。先問服務要守住什麼體驗，再問這個體驗要用哪些訊號衡量，最後才決定 burn rate 到多少時要 freeze。這樣寫的好處是，讀者會先理解政策責任，再理解數字本身。

## 大綱

- SLI 選型：user-journey-centric vs system-metric
- SLO 目標訂定：可達性、商業意義、頻率窗
- error budget：burn rate、policy、freeze 條件
- 跟 [04 觀測](/backend/04-observability/) 的訊號交接
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的凍結觸發
- 跟 [8.1 事故分級](/backend/08-incident-response/incident-severity-trigger/) 的門檻對齊
- 反模式：cargo-cult 99.99%、SLO 無人擁有、burn rate 無 alert

## 核心判讀

SLO 的責任是讓團隊知道自己到底在保護什麼。當讀者看到一個 SLO 時，第一個問題不是數字高不高，而是這個數字是否對應使用者行為、商業風險與回復成本。若對應不清楚，這個 SLO 就只是裝飾。

error budget 的責任是把風險傳導成決策。當 burn rate 開始上升時，團隊不是先爭論要不要放行，而是先確認 budget 還剩多少、目前的變更是否會放大風險、freeze 條件是否已經被觸發。這裡的重點是路由清楚，而不是數字漂亮。

## 判讀訊號

- SLO 數字無 owner、過半年沒檢視
- burn rate 無 alert、只有 monthly review
- error budget 耗盡但 deployment 節奏不變
- SLI 用 system metric（CPU / memory）、不對應 user journey
- 目標數字是抄來的（99.9 / 99.99）、無商業 anchor

## 案例對照

Google 提供的是制度原點，因為它把 SLO、[post-incident review](/backend/knowledge-cards/post-incident-review/) 與 toil budget 串成可管理的可靠性文化。Honeycomb 提供的是訊號層的延伸，因為 high-cardinality 與 burn rate alert 讓 SLO 可以在真實流量下被看見。Stripe 則把 SLO 風格的決策壓到交易語義上，讓 idempotency 與 migration 不會因為重試而失真。

當讀者把這三個案例放在一起，就會看見 SLO 不只是「填一個百分比」，而是把不同層級的風險接到同一條路由：制度、訊號與交易正確性。這也是本節章節要建立的核心能力。

## 交接路由

- 04 訊號治理：SLI / burn rate metric 設計
- 06.8 release gate：error budget 耗盡觸發 freeze
- 06.9 capacity / cost：容量不足傳導為 SLO 風險
- 06.14 dependency budget：依賴可靠性納入 SLO 算式
- 08 事故閉環：burn rate alert 啟動條件
- 08.13 repeated / toil：error budget 撥用 toil reduction
- 06.18 reliability metrics：SLO 跟 DORA / SPACE 的指標分層
