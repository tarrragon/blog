---
title: "6.17 Feature Flag / Dark Launch Governance"
date: 2026-05-01
description: "把 feature flag 從上線工具升級為有 lifecycle、有 debt 治理的 artifact"
weight: 17
---

## 大綱

- feature flag 的責任分裂：release flag、experiment flag、ops flag、permission flag
- flag debt：上線後沒清的 flag 變技術債、增加 coverage 複雜度
- lifecycle 管理：建立 → 灰度 → 收敂 → 移除
- dark launch：流量導入但對用戶不可見、用於驗證效能 / 行為
- progressive rollout：percentage / cohort / region 控制
- experimentation reliability：A/B test 平台本身的可靠性
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的整合：flag 是 gate 通過後的細粒度控制
- 跟 [05 部署](/backend/05-deployment-platform/) 的分工：05 是 deploy artifact、6.17 是 runtime 控制
- 反模式：flag 上線後無人移除、累積數百 stale flag；flag 直接讀環境變數無 audit；flag 跟 permission 混用導致權限漏洞

## 判讀訊號

- 程式碼中存在 > 6 個月沒切換的 flag
- flag 移除流程靠 grep 跟人工 PR
- flag 實際分支跟預期不一致、靠生事故才發現
- experimentation 平台本身掛掉、影響所有 A/B 流量
- ops flag（緊急開關）跟 release flag 混在同系統、無權限隔離

## 交接路由

- 06.8 release gate：flag 是 progressive rollout 的細粒度層
- 06.10 contract testing：flag 不同分支的契約覆蓋
- 06.13 perf regression gate：flag 切換後的效能驗證
- 07 資安：permission flag 的權限約束
- 08.3 止血：ops flag 作為事中止血手段
