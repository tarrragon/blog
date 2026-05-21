---
title: "IaC plan、apply、drift 與 recovery 流程"
date: 2026-05-21
description: "說明 Terraform / Helm / Pulumi 等平台變更 CI/CD 如何用 plan review、state lock、drift detection 與 recovery gate 控制風險"
tags: ["CI", "CD", "IaC", "platform", "drift"]
weight: 1
---

IaC 發布流程的核心責任是把基礎設施變更變成可審查、可套用、可追溯的狀態轉移。Terraform、Pulumi、Helm 或平台自動化會改變網路、權限、資料庫、節點、DNS 與部署平台，因此 CI/CD 要把 plan、review、apply、[Infrastructure Drift](/ci/knowledge-cards/infrastructure-drift/) 與 recovery 分成明確 gate。

## 流程定位

IaC 的風險集中在共享狀態與不可逆資源。應用部署失敗常可回退 artifact；基礎設施變更可能刪除資料、替換節點、改掉 IAM 權限或讓 state 與真實環境分叉。發布流程應讓 reviewer 在 apply 前看到「將要改什麼」，並讓 apply 後能確認「環境是否真的符合宣告」。

| 階段                                                              | 責任                       | 判讀訊號                            |
| ----------------------------------------------------------------- | -------------------------- | ----------------------------------- |
| Plan                                                              | 預覽資源差異與風險         | create / update / replace / destroy |
| Review                                                            | 審核變更意圖、權限與影響面 | 高風險資源、跨環境、資料資源        |
| Apply                                                             | 在鎖定狀態下套用變更       | state lock、timeout、partial apply  |
| Verify                                                            | 確認環境符合預期           | health、policy、smoke、connectivity |
| [Infrastructure Drift](/ci/knowledge-cards/infrastructure-drift/) | 偵測真實環境與宣告分叉     | 手動 hotfix、console edit、外部系統 |
| Recovery                                                          | 回退、補正或 state repair  | 是否能安全恢復服務與 state          |

Plan 階段負責產生可審查差異。Plan 是 reviewer 判斷資源替換、權限擴大、資料刪除與網路暴露的主要材料。CI 應保留 plan artifact，讓 apply 使用同一份輸入與版本。

Review 階段負責把風險放到正確 owner。平台、資安、資料庫或服務 owner 應依資源類型參與審核；高風險變更需要額外 gate，例如 maintenance window、人工 approval 或雙人審核。

Apply 階段負責把宣告狀態寫入環境。[State Lock](/ci/knowledge-cards/state-lock/)、credential、workspace 與環境變數都要固定；partial apply 或 timeout 後，要先判斷 state 與真實資源是否一致，再決定下一步。

Verify 階段負責確認平台可用。Apply 成功只代表 provider API 接受變更；仍需要 connectivity test、policy check、service smoke test、DNS / certificate check 或 cluster health，確認服務真的能跑。

[Infrastructure Drift](/ci/knowledge-cards/infrastructure-drift/) 階段負責發現宣告與現況分叉。手動 hotfix、雲端 console 調整、外部 controller 或 provider 預設值都可能造成 drift；drift detection 要定期執行，並把修復責任導回宣告檔。

Recovery 階段負責處理失敗套用。IaC 回復不一定是 `git revert` 後 apply；可能需要 import、state mv、taint / untaint、手動修復資料資源或 forward fix。流程要先保護資料與服務，再修正宣告與 state。

## Plan review 判讀

Plan review 的責任是讓變更影響在 apply 前被看見。Reviewer 應依資源語意判斷，讓 diff 行數退居輔助訊號。

| Plan 訊號      | 判讀               | 下一步                            |
| -------------- | ------------------ | --------------------------------- |
| `destroy`      | 資源將被刪除       | 確認資料、依賴與備份              |
| `replace`      | 先刪後建或重建資源 | 檢查 downtime、IP、DNS、資料      |
| IAM 權限擴大   | blast radius 增加  | 資安或平台 owner 審核             |
| Network 開放   | 暴露面增加         | 檢查 security group / firewall    |
| State 大量漂移 | 宣告與現況長期分叉 | 先處理 drift，再進 feature change |

這張表讓 review 從「有人按 approve」變成風險判讀。IaC review 的價值在於提前看見不可逆或高代價變更。

## Drift 處理路由

Drift 處理的責任是把現況重新帶回可管理狀態。Drift 發現後不應直接 apply 覆蓋，因為 drift 可能是事故 hotfix、外部系統自動調整或宣告檔過期。

1. 確認 drift 來源：人工 hotfix、provider 預設、外部 controller 或宣告過期。
2. 判斷 drift 是否仍需要保留：若是真實修復，應回寫到 IaC。
3. 判斷 apply 是否會破壞服務：特別看 replacement、destroy、權限與 network。
4. 修正宣告或 state：必要時使用 import、state mv 或 provider-specific repair。
5. 重新 plan，確認差異收斂到預期。

這個路由讓 drift 修復具備審查性。直接在 console 裡補到看起來正常，會讓下一次 CI apply 把修復覆蓋掉。

## 常見反模式

反模式的共同問題是把 IaC 降成指令自動化，忽略它承擔的狀態治理責任。

| 反模式                                             | 風險                          | 替代做法                           |
| -------------------------------------------------- | ----------------------------- | ---------------------------------- |
| plan 與 apply 使用不同輸入                         | review 內容與實際套用內容分叉 | 保存 plan artifact 或鎖定版本      |
| 沒有 [State Lock](/ci/knowledge-cards/state-lock/) | 併發 apply 覆寫狀態           | 使用 remote backend 與 locking     |
| drift 長期忽略                                     | 宣告失去可信度                | 定期 drift detection 與 owner 路由 |
| 高風險資源無額外 gate                              | 資料或網路變更直接進環境      | environment protection / approval  |

## 下一步路由

- IaC 部署總覽：回 [IaC / Platform 部署 CI/CD](../)。
- 環境保護：讀 [Environment Protection](/ci/knowledge-cards/environment-protection/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。
