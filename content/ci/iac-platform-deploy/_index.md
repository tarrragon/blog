---
title: "IaC / Platform 部署 CI/CD"
date: 2026-05-06
description: "整理 Terraform / Helm / Pulumi 等基礎設施變更的 plan-apply、drift 與回復流程"
tags: ["CI", "CD", "IaC", "platform"]
weight: 16
---

IaC / Platform 部署 CI/CD 的核心責任是把基礎設施變更轉成可審查、可追溯、可回復的流程。它和應用部署不同，主要風險在 state、權限、drift 與不可逆資源變更。

## 場域定位

IaC 流程通常分成 plan、review、apply 三段，並依環境分層推進。部署成功不只代表指令完成，還代表資源狀態符合預期且未引入漂移。

| 面向     | IaC 部署常見責任       | 判讀訊號                      |
| -------- | ---------------------- | ----------------------------- |
| Plan     | 變更差異預覽與風險提示 | 是否包含高風險破壞性變更      |
| Review   | 審核資源變更與權限範圍 | 是否符合治理規範              |
| Apply    | 狀態寫入與資源同步     | state lock / timeout 是否可控 |
| Drift    | 實際環境與宣告差異檢查 | 是否存在未受控手動變更        |
| Recovery | 回退或補正策略         | 失敗時是否有安全回復路徑      |

## 常見注意事項

- plan 與 apply 要用同一份輸入與版本，避免結果漂移。
- state backend 要有鎖定與權限隔離，避免併發覆寫。
- 高風險資源變更需要額外 gate（人工審核或變更時窗）。
- drift 偵測要定期執行，並有修復責任人。

## 下一步路由

- 環境保護：讀 [Environment Protection](/ci/knowledge-cards/environment-protection/)。
- 部署合約：讀 [Deployment Contract](/backend/knowledge-cards/deployment-contract/)。
- 變更放行：讀 [Release Gate](/backend/knowledge-cards/release-gate/)。
