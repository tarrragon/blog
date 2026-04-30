---
title: "7.14 資安治理例外與 Tripwire"
date: 2026-04-24
description: "定義例外管理、風險接受與重新評估觸發器"
weight: 84
---

本章的責任是定義治理例外與重新評估問題節點，讓風險接受決策具備期限、條件與回收機制。

## 本章寫作邊界

本章聚焦決策治理與重新評估節奏，不討論單一審批系統流程細節。

## 例外治理模型

例外治理的核心責任是把暫時接受風險的決策，限制在可追蹤、可回收、可重評估的範圍內。

1. 決策責任：記錄例外目的、邊界、批准者與受影響資產。
2. 期限責任：設定明確到期日與重評估條件。
3. 補償責任：例外期間加上額外監測、限制或人工檢查。
4. 觸發責任：定義 tripwire，一旦觸發立即重審例外。
5. 關閉責任：例外結束後回寫知識與控制面改進。

## 判讀流程

判讀流程的責任是把「例外同意」轉成「例外可控」。

1. 先確認例外是否有清楚邊界與風險描述。
2. 再確認是否有到期日與量化關閉條件。
3. 接著確認補償控制面是否足以降低暴露窗口。
4. 最後確認 tripwire 與重評估流程是否可執行。

## 問題節點（案例觸發式）

| 問題節點         | 判讀訊號                       | 風險後果               | 前置控制面                                                       |
| ---------------- | ------------------------------ | ---------------------- | ---------------------------------------------------------------- |
| 例外條件描述不足 | 只記錄同意結果，未記錄邊界條件 | 例外範圍持續擴張       | [runbook](/backend/knowledge-cards/runbook/)                     |
| 風險接受缺乏期限 | 例外長期存續且無重評估節點     | 長期暴露風險累積       | [incident-timeline](/backend/knowledge-cards/incident-timeline/) |
| 補償控制面不足   | 例外期間缺少額外監測與限制     | 事件發生時缺乏止血槓桿 | [containment](/backend/knowledge-cards/containment/)             |
| tripwire 未定義  | 重大變化出現時無自動重審機制   | 決策過期仍持續生效     | [incident-severity](/backend/knowledge-cards/incident-severity/) |

## 常見風險邊界

風險邊界的責任是判斷例外決策何時已不可接受。

- 例外文件只有結論沒有條件時，代表例外邊界不可驗證。
- 例外到期後仍自動延長時，代表治理節奏失控。
- 例外期間缺少補償監測時，代表事件來臨時無法提早止血。
- 關鍵風險指標變化卻未觸發重審時，代表 tripwire 機制失效。

## 案例觸發參考

案例觸發的責任是驗證例外治理是否能承受高壓情境。

- 修補窗口中的暫時風險接受： [PAN-OS 2024](/backend/07-security-data-protection/red-team/cases/edge-exposure/panos-cve-2024-3400-edge-rce/)
- 供應鏈事件中的凍結與恢復判準： [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)
- 身分事件中的收斂與決策期限： [Uber 2022](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)

## 下一步路由

- 平台控制面補償設計：`05-deployment-platform`
- 驗證與回退節奏：`06-reliability`
- 分級、通報與重評估：`08-incident-response`
