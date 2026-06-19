---
title: "A/B Test 的統計基礎"
date: 2026-06-19
description: "假設檢定、樣本量計算、多重比較校正 — A/B test 不只是「比較兩個數字」，統計方法決定結論是否可靠"
weight: 5
tags: ["monitoring", "analytics", "ab-test", "statistics", "hypothesis-testing"]
---

A/B test 把使用者隨機分成兩組，一組看到原版（control），一組看到改版（treatment），比較兩組的指標差異。統計方法的角色是判斷「觀察到的差異是真實的還是隨機波動」。

## 假設檢定

### 虛無假設和對立假設

虛無假設（H0）：兩組沒有差異，觀察到的差異來自隨機波動。對立假設（H1）：兩組有真實差異。

A/B test 的邏輯是：假設 H0 成立（兩組沒有差異），計算「在 H0 成立的前提下，觀察到目前這麼大的差異的機率」。如果這個機率（p-value）很小（通常 < 0.05），拒絕 H0，接受 H1。

### p-value 的意義

p-value = 0.03 代表「假設兩組沒有差異，觀察到目前差異的機率是 3%」。這個機率足夠小，合理推斷差異是真實的。

p-value 不代表「改版比原版好的機率是 97%」。p-value 是在 H0 成立的條件下計算的，不是改版效果的機率。

### 兩類錯誤

**Type I error（偽陽性）**：實際上沒有差異，但統計結果判定有差異。機率由顯著性水準 α 控制，通常設 0.05。

**Type II error（偽陰性）**：實際上有差異，但統計結果判定沒有差異。機率由統計檢定力（power = 1 - β）控制，通常要求 power ≥ 0.8。

## 樣本量計算

樣本量決定了 A/B test 能偵測到多小的差異。樣本量太小，即使改版有效果，test 也沒有足夠的統計檢定力偵測到。

樣本量計算需要四個參數：

- **基準轉換率**：control 組目前的轉換率（例如 5%）
- **最小可偵測效果（MDE）**：想偵測到的最小差異（例如 5% → 6%，相對提升 20%）
- **顯著性水準 α**：通常 0.05
- **統計檢定力 1 - β**：通常 0.8

以基準轉換率 5%、MDE 相對提升 20%（5% → 6%）、α = 0.05、power = 0.8 為例，每組需要約 14,500 個樣本。如果每天有 1,000 個使用者，需要跑 29 天。

樣本量不足時的常見錯誤是「提早看結果」— 跑了 3 天看到 p < 0.05 就停止。提早停止會膨脹 Type I error 率，因為隨機波動在小樣本中更容易產生看似顯著的差異。

## 多重比較

同時跑多個 A/B test 或測試多個變體（A/B/C/D）時，整體的 Type I error 率會膨脹。

跑 20 個 test，即使所有 test 的 H0 都成立（沒有真實差異），預期有 1 個 test（20 × 0.05）會出現 p < 0.05 的偽陽性。

### Bonferroni 校正

最簡單的校正方式：把顯著性水準除以測試數量。跑 5 個 test，每個 test 的顯著性水準改為 0.05 / 5 = 0.01。

Bonferroni 校正很保守 — 降低了偽陽性但也降低了統計檢定力，可能錯過真實的差異。

### False Discovery Rate（FDR）

Benjamini-Hochberg 方法控制的是「被判為顯著的結果中偽陽性的比例」，比 Bonferroni 更寬鬆。適合探索性分析（同時測試多個指標，容許一些偽陽性）。

## A/B test 在自架方案的可行性

自架 collector 可以做基礎的 A/B test 分析 — 在行為事件中記錄使用者的分組（`variant: "control"` / `variant: "treatment"`），計算每組的轉換率，用統計檢定比較差異。

統計計算（p-value、信賴區間）可以用 Python（scipy.stats）或 R 完成。不需要商業 A/B test 平台。

商業 A/B test 平台（Optimizely、LaunchDarkly、Firebase Remote Config）額外提供的是：隨機分組管理、提早停止的統計保護（sequential testing）、多變體管理的 UI、和其他分析工具的整合。

## 下一步路由

- 推薦系統概論 → [推薦系統概論](/monitoring/08-business-analytics/recommendation-overview/)
- 使用者分群 → [RFM 分群](/monitoring/08-business-analytics/rfm-segmentation/)
- 行為事件設計 → [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
