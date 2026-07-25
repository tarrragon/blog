---
title: "6.17 Feature Flag Governance"
date: 2026-05-01
description: "把 feature flag 從上線開關升級為有角色分類、lifecycle 管理與 debt 治理的 runtime artifact"
weight: 17
tags: ["backend", "reliability"]
---

## 概念定位

Feature flag 在 [release gate](/backend/knowledge-cards/release-gate/) 之後提供 runtime 層的細粒度控制。Flag governance 把這個控制從單次開關提升為有生命週期的 artifact，涵蓋灰度、實驗與緊急止血的風險管理。

當 flag 變多，真正的風險是狀態分支不透明、技術債累積與權限混用。

## 核心判讀

Flag governance 的健康度先看旗標角色是否分離，再看移除與審計是否有固定流程。

重點訊號包括：

- release / experiment / ops / permission 是否分流
- stale flag 是否有回收機制
- progressive rollout 是否有可觀測的 cohort
- flag 變更是否可審計、可追責

## Flag 角色分類

Flag 按用途分離，不同角色的 lifecycle、權限與治理策略差異顯著。混用會讓審計失真、移除困難、權限控制失效。

| 角色            | 責任                       | Lifecycle 預期 | Owner        |
| --------------- | -------------------------- | -------------- | ------------ |
| Release flag    | 控制新功能是否對使用者可見 | 天到週         | 功能團隊     |
| Experiment flag | 控制 A/B test 流量分配     | 週到月         | 實驗平台團隊 |
| Ops flag        | 緊急止血、降級、流量限制   | 長期存在       | SRE / 值班   |
| Permission flag | 控制使用者 / 租戶功能存取  | 跟隨權限策略   | 產品 / IAM   |

**Release flag** 上線後應在固定時限內收斂為 always-on 或移除。它的存在意義是灰度期間的安全網。灰度結束後，flag 的控制作用消失，只剩代碼分支 — 這段分支就是 flag debt 的來源。

**Experiment flag** 的 lifecycle 受實驗週期決定。實驗結束後，flag 應收斂為勝出變體的行為並移除。實驗 flag 的特殊風險是依賴統計引擎的流量分配 — 引擎異常時，flag 的行為取決於 fallback 配置。

**Ops flag** 是長期存在的 kill switch 與降級控制。它與其他三類 flag 的關鍵差異是觸發頻率低但影響範圍大 — 觸發時通常是事故情境，需要秒級生效與審計紀錄。ops flag 的設計需求見下方「Kill switch 設計」段。

**Permission flag** 本質是權限控制，應走 RBAC 或 entitlement 系統。當 permission flag 混入 feature flag 系統，功能存取權會繞過正式權限審核流程 — 修改一個 flag 值就能改變租戶的功能範圍，沒有對應的審計軌跡。判斷標準：如果 flag 的值決定「誰能用什麼功能」，它是 permission，應該從 feature flag 系統遷移到權限系統。

## Lifecycle 管理

Flag 的生命週期是 create → rollout → converge → remove。每個階段有明確的輸入與交付物。

**Create**：flag 建立時記錄 owner、用途分類（release / experiment / ops）、預計移除日期與關聯 ticket。這些 metadata 是後續治理的基礎 — 沒有 owner 的 flag 在移除階段會變成無人認領的 debt。

**Rollout**：progressive rollout 按 percentage、[cohort](/backend/knowledge-cards/cohort/) 或 region 逐步放量。每一步有可觀測指標確認行為正常 — error rate、latency、business KPI。rollout 節奏跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的放行條件對齊：gate 通過後用 flag 做細粒度控制，flag 異常時 gate 提供回退依據。

**Converge**：功能穩定後，flag 設定 100%（always-on）或 0%（移除功能）。此時 flag 已無控制作用，只是代碼中的條件分支。converge 階段是 flag 治理的關鍵轉折 — 很多 flag 停在這裡不再前進，持續佔用代碼路徑。

**Remove**：移除 flag 代碼、清理條件分支、移除 flag 定義。移除動作困難的原因是 flag 可能被多處引用（server / client / config / test），每處都需要確認行為收斂到同一分支。自動化掃描（dead code detection、unused flag audit）能降低手動風險，但最終決策仍需要 flag owner 確認沒有殘留依賴。

## Flag debt 治理

每個未移除的 flag 讓測試需要覆蓋的狀態空間翻倍。10 個 stale flag 代表 1024 種潛在的狀態組合 — 實際測試覆蓋率遠低於這個數字，代碼行為的可預測性持續下降。

**TTL policy**：flag 建立時設定預計移除日期。超過 TTL 且沒有活躍修改的 flag 自動標記為 debt，進入清理 backlog。TTL 按角色設定：release flag 兩週到一個月，experiment flag 與實驗週期對齊，ops flag 免 TTL 但需要年度 review。

**定期掃描**：每月或每季掃描 stale flag（超過 TTL + 無活躍修改），生成清理 backlog。掃描結果對應到 flag owner，由 owner 決定是移除、延長 TTL 還是升級為 ops flag。無 owner 的 stale flag 是最高風險 — 沒有人能確認移除是否安全。

**Flag count dashboard**：追蹤活躍 flag 數量趨勢。flag 數量持續上升是治理失敗的訊號 — 代表建立速度超過移除速度，debt 在累積。dashboard 按角色分類顯示，讓團隊知道 debt 集中在哪一類 flag。

## Kill switch 設計

Ops flag 作為事中止血工具，需要跟一般 feature flag 不同的設計約束。

**觸發延遲**：kill switch 需要秒級生效。依賴 redeploy 才能生效的 flag 在事故中無法作為止血工具 — 部署流程本身需要數分鐘到數十分鐘。實作通常靠 flag evaluation service 的即時推送或短間隔 polling，讓 flag 值變更能在秒級傳播到所有 instance。

**權限控制**：kill switch 的觸發權限應受控。值班人員與 SRE 有觸發權，一般開發者沒有。觸發記錄包含誰、什麼時間、因什麼原因觸發，接到 [8.3 止血策略](/backend/08-incident-response/containment-recovery-strategy/) 的決策 log。

**Fallback 行為明確**：每個 kill switch 在觸發後的預期行為應事前定義。「關掉這個 flag 後會怎樣」的答案應寫在 flag 定義中，讓觸發者在壓力下可快速判斷副作用，而不是臨場推理。

## Experimentation 平台可靠性

A/B test 平台本身是 feature flag 的下游消費者。平台的可用性直接影響所有走 experiment flag 的流量分配。

平台掛掉時，flag 的行為取決於 fallback 配置：default-on 會讓所有使用者看到實驗中的變體，default-off 會讓所有使用者回到 control group。兩者的商業影響完全不同，fallback 行為應在每個 experiment flag 建立時明確配置。

experimentation 平台的 SLO 應獨立定義。當平台自身的 [error budget](/backend/knowledge-cards/error-budget/) 消耗過快時，影響的是所有進行中的實驗的流量分配正確性。平台故障不只是「實驗暫停」— 如果 fallback 行為配置錯誤，使用者可能被導向尚未驗證的功能路徑。

## 案例對照

- [Stripe](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)：progressive rollout 用 flag 控制 migration 的流量切換比例，每一步驗證交易正確性後再擴大，flag 的 rollout 節奏跟 migration safety 綁定。
- [Shopify](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)：高峰流量期間 ops flag 用於細粒度降級控制 — 關閉非核心功能釋放容量給 checkout 路徑。flag 的降級策略在 game day 驗證，確認觸發後的行為符合預期。
- [Stripe S2](/backend/06-reliability/cases/stripe/canary-deploy-and-progressive-rollout/)：progressive rollout 用 flag 控制 canary 放量比例，每一步用交易指標判斷是否繼續。flag 的 rollout 節奏跟金流風險的延遲確認窗綁定。

## 判讀訊號

| 訊號                                            | 判讀條件                                                   | 行動建議                                   |
| ----------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------ |
| 程式碼中存在 > 6 個月未切換的 flag              | flag 已停在 converge 階段，應進入移除流程或升級為 ops flag | 啟動 stale flag 掃描 + 移除 sprint         |
| flag 移除流程靠 grep 跟人工 PR                  | 缺少自動化掃描，移除成本高導致 debt 累積                   | 導入 dead code detection 工具自動標記      |
| flag 實際分支跟預期不一致                       | flag 狀態與代碼路徑脫鉤，通常在事故時才被發現              | 建 flag 狀態 dashboard 定期對齊            |
| experimentation 平台掛掉影響所有 A/B 流量       | 平台 fallback 行為未配置或未驗證                           | 配置 default-on/off fallback + 定期演練    |
| ops flag 跟 release flag 混在同系統、無權限隔離 | 止血操作的審計軌跡與一般功能開關無法區分，事後回查困難     | 分離 flag 系統或加 RBAC 權限隔離           |
| 活躍 flag 數量每季持續上升                      | 建立速度超過移除速度，測試覆蓋的狀態空間在膨脹             | 設 flag count budget、超額暫停新 flag 建立 |

## 交接路由

- [6.8 release gate](/backend/06-reliability/release-gate/)：flag 是 gate 通過後的細粒度 rollout 控制
- [6.10 contract testing](/backend/06-reliability/contract-testing/)：flag 不同分支的契約覆蓋
- [6.13 perf regression gate](/backend/06-reliability/performance-regression-gate/)：flag 切換後的效能驗證
- [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)：stale flag 進入 debt 治理
- [07 資安與資料保護](/backend/07-security-data-protection/)：permission flag 的權限約束
- [8.3 止血策略](/backend/08-incident-response/containment-recovery-strategy/)：ops flag 作為事中止血手段
