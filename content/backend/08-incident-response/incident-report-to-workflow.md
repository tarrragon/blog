---
title: "8.8 事故報告轉 workflow：從案例到日常流程"
date: 2026-04-24
description: "把事故報告拆成可執行流程，並與 red-team 案例庫建立雙向引用"
weight: 88
---

這一章的核心原則是把事故報告轉成可重複執行流程。每份報告都需要落地為 runbook、告警規則、演練腳本，並可回查到對應 red-team 案例。

## 轉換流程

1. 事件切片：把事故拆成入口、擴散、外送、回復四段。
2. 控制面對應：每段映射到身份、邊界、資料、可觀測性控制面。
3. 失效步驟定位：明確指出缺少或延遲的流程步驟。
4. 動作落地：把缺口寫成 runbook、告警與演練任務。
5. 驗證關閉：用桌上推演與實際演練驗證關閉結果。

## 常見輸出物

- [runbook](../../knowledge-cards/runbook/)：定義觸發條件、決策邊界與停止條件。
- [incident timeline](../../knowledge-cards/incident-timeline/)：建立跨團隊共用時間軸。
- [post-incident review](../../knowledge-cards/post-incident-review/)：保留可追蹤 action items。
- 量測指標：例如 [MTTR](../../knowledge-cards/mttr/)、告警到升級時間、回復耗時。

## 從案例到 workflow

案例入口在 [7.R7 事故案例庫（可引用）](../../07-security-data-protection/red-team/cases/)。

1. 先在服務章節選同類型案例。
2. 引用案例中的「如果 workflow 少一步會發生什麼」。
3. 把該步驟落地為 runbook 與演練任務。

## 從 workflow 回查案例

workflow 設計完成後要反向驗證案例覆蓋是否充足。引用地圖在 [案例引用地圖](../../07-security-data-protection/red-team/cases/case-reference-map/)。

- 身分或授權步驟：回查 `identity-access` 案例。
- 供應鏈或 CI/CD 步驟：回查 `supply-chain` 案例。
- 邊界設備或外網入口步驟：回查 `edge-exposure` 案例。
- 外送與回復步驟：回查 `data-exfiltration` 案例。

## 範例：邊界漏洞案例轉 workflow

- 觸發：外部公告高風險邊界漏洞。
- 立即動作：入口隔離與臨時緩解。
- 後續動作：分區修補、憑證輪替、狀態驗證。
- 驗證：48 小時內完成抽樣復測與事件回顧。

這組流程可直接套用到 VPN、WAF、API Gateway 與對外管理介面。
