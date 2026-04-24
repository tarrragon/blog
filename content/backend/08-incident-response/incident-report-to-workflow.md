---
title: "8.8 事故報告轉 workflow：從案例到日常流程"
date: 2026-04-24
description: "把事故報告拆成可執行流程：偵測、分級、止血、回復、復盤與演練"
weight: 88
---

這一章的核心原則是：事故報告的價值是產生可重複執行的流程，而不是只留下事件摘要。每份報告都應該被轉成可演練的 workflow，並能回寫到日常值班、部署、授權與資料治理。

## 轉換流程

1. 事件切片：把事故拆成「入口、擴散、外送、回復」四段。
2. 控制面對應：每一段映射到已有控制面（身份、邊界、資料、可觀測性）。
3. 失效步驟定位：找出當時缺少或延遲的流程步驟。
4. 動作落地：把缺口寫成 runbook、告警規則、演練腳本。
5. 驗證關閉：用演練或桌上推演確認缺口真的被關閉。

## 常見輸出物

- 一份 [runbook](../knowledge-cards/runbook/)：定義觸發條件、決策邊界與停止條件。
- 一份 [incident timeline](../knowledge-cards/incident-timeline/)：提供跨團隊共用時間軸。
- 一份 [post-incident review](../knowledge-cards/post-incident-review/)：留下可驗證 action items。
- 一組量測指標：例如 [MTTR](../knowledge-cards/mttr/)、告警到升級時間、回復耗時。

## 與紅隊案例庫串接

紅隊案例庫放在：
- [7.R7 事故案例庫（可引用）](../07-security-data-protection/red-team/cases/)
- [案例引用地圖（服務主題 -> 案例 -> workflow）](../07-security-data-protection/red-team/cases/case-reference-map/)

使用方式：
1. 在服務章節選一個同類型案例。
2. 引用該案例的「如果 workflow 少一步會發生什麼」段落。
3. 把該步驟寫入服務專屬 runbook 與演練計畫。

## 範例：邊界漏洞案例轉 workflow

- 觸發：外部公告高風險邊界漏洞。
- 立即動作：入口隔離與臨時緩解。
- 後續動作：分區修補、憑證輪替、狀態驗證。
- 驗證：48 小時內完成抽樣復測與事件回顧。

這組流程可直接套用到 VPN、WAF、API Gateway 與對外管理介面。
