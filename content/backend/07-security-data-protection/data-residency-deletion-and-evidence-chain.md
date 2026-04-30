---
title: "7.11 資料駐留、刪除與證據鏈"
date: 2026-04-24
description: "定義跨區資料駐留、刪除請求與可驗證證據鏈問題"
weight: 81
---

本章的責任是把資料位置與刪除責任拆成可驗證閉環，讓資料治理在合規壓力與營運需求同時存在時仍可追蹤。

## 本章寫作邊界

本章聚焦資料位置責任、刪除流程閉環與證據保留語意，不展開法規條文逐條解釋。

## 資料駐留與刪除模型

資料駐留治理的核心責任是回答資料在哪裡，刪除治理的核心責任是證明資料已從所有可觸及路徑被收斂。

1. 位置責任：定義正式資料、衍生資料、備份資料的地理與服務邊界。
2. 刪除責任：定義請求受理、執行、驗證與回覆的責任鏈。
3. 一致性責任：定義主系統與衍生系統刪除節奏一致條件。
4. 證據責任：定義刪除證據與稽核證據的保留與可驗證性。
5. 通知責任：定義跨組織資料治理事件的通報與驗證時序。

## 判讀流程

判讀流程的責任是把「刪除完成」轉成「可驗證刪除完成」。

1. 先確認資料分類與駐留位置清單是否完整。
2. 再確認刪除是否覆蓋主路徑、衍生路徑與備份路徑。
3. 接著確認刪除證據是否可對應主體、時間與資產。
4. 最後把缺口交接到可靠性驗證與 incident 溝通流程。

## 問題節點（案例觸發式）

| 問題節點         | 判讀訊號                       | 風險後果               | 前置控制面                                                       |
| ---------------- | ------------------------------ | ---------------------- | ---------------------------------------------------------------- |
| 資料駐留邊界模糊 | 同一資料集跨區副本責任不清     | 通報與整改範圍擴大     | [data-lifecycle](/backend/knowledge-cards/data-lifecycle/)       |
| 刪除流程缺乏閉環 | 主系統刪除完成但衍生系統仍存留 | 使用者承諾失效         | [retention](/backend/knowledge-cards/retention/)                 |
| 備份刪除節奏脫鉤 | 正式資料移除後備份仍長期可還原 | 長尾暴露風險升高       | [object-storage](/backend/knowledge-cards/object-storage/)       |
| 刪除證據不可驗證 | 時序與主體資訊無法回查         | 合規與事故回應成本上升 | [incident-timeline](/backend/knowledge-cards/incident-timeline/) |

## 常見風險邊界

風險邊界的責任是界定何時資料治理需要升級處置。

- 同一資料集跨區副本沒有明確責任人時，代表駐留邊界不可控。
- 主系統刪除完成但索引或快取仍可查到資料時，代表刪除閉環失效。
- 備份保留策略與刪除承諾衝突時，代表長尾暴露窗口擴大。
- 刪除回覆缺少可驗證證據時，代表合規與信任成本上升。

## 案例觸發參考

案例觸發的責任是驗證資料位置與刪除證據是否能支撐現實事件回應。

- 備份鏈與資料外送壓力： [LastPass 2022](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)
- 憑證濫用下的大量資料外送： [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)
- 檔案服務暴露與資料治理壓力： [Progress WS_FTP 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/progress-wsftp-2023-file-service-breach/)

## 下一步路由

- 資料與儲存邊界實作：`05-deployment-platform`
- 一致性驗證與演練：`06-reliability`
- 通報與事件收斂：`08-incident-response`
