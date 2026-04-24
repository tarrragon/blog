---
title: "0.10 知識網：容量、觀測與資安決策路徑"
date: 2026-04-23
description: "把容量、可觀測、備援、權限、憑證與稽核術語串成統一的服務治理語言"
weight: 10
---

服務治理的核心原則是把可用性與安全性放在同一張決策圖上。`timeout`、`deadline`、`readiness`、`runbook`、`RTO/RPO`、`authentication`、`authorization`、`TLS/mTLS` 與 `audit log` 描述的是同一件事：系統如何在壓力與風險下維持可運作。

## 本章目標

學完本章後，你將能夠：

1. 用「容量-觀測-資安」三軸描述服務治理需求
2. 把術語連成可追蹤的決策鏈，而非獨立名詞
3. 判斷何時先補觀測與操作能力，何時先補安全控制
4. 明確區分概念決策與平台實作邊界

---

## 【判讀】容量控制與恢復目標是一條線

容量治理的核心問題是「系統在壓力下如何守住核心能力」。`timeout`、`deadline`、`backpressure`、`rate limit` 與 `fallback` 應該連到同一個恢復目標。

對應卡片關係：

- 請求邊界：  
  [Timeout](../knowledge-cards/timeout/) / [Deadline](../knowledge-cards/deadline/)
- 壓力控制：  
  [Backpressure](../knowledge-cards/backpressure/) / [Rate Limit](../knowledge-cards/rate-limit/) / [Token Bucket](../knowledge-cards/token-bucket/)
- 退讓策略：  
  [Fallback](../knowledge-cards/fallback/) / [Degradation](../knowledge-cards/degradation/) / [Failover](../knowledge-cards/failover/)
- 恢復目標：  
  [RTO](../knowledge-cards/rto/) / [RPO](../knowledge-cards/rpo/)

如果只定義 [timeout](../knowledge-cards/timeout)，沒有 [fallback](../knowledge-cards/fallback) 與回復目標，系統仍缺少操作上的可控性。

## 【判讀】可觀測訊號要服務操作決策

可觀測性的核心問題是「問題出現時，團隊能否在時間內採取正確動作」。`log`、`metrics`、`trace`、`alert` 與 `runbook` 必須一起設計。

對應卡片關係：

- 事件與脈絡：  
  [Log](../knowledge-cards/log/) / [Log Schema](../knowledge-cards/log-schema/) / [Correlation ID](../knowledge-cards/correlation-id/)
- 趨勢與目標：  
  [Metrics](../knowledge-cards/metrics/) / [SLI/SLO](../knowledge-cards/sli-slo/) / [Error Budget](../knowledge-cards/error-budget/)
- 路徑與定位：  
  [Trace](../knowledge-cards/trace/) / [Trace Context](../knowledge-cards/trace-context/)
- 執行與回應：  
  [Alert](../knowledge-cards/alert/) / [Alert Runbook](../knowledge-cards/alert-runbook/) / [Runbook](../knowledge-cards/runbook/)

當觀測鏈完整後，才適合比較具體平台組合。

## 【判讀】資安控制要對齊資料流與角色責任

資安治理的核心問題是「誰可以在什麼條件下接觸哪類資料」。身份、授權、傳輸保護、秘密管理與稽核需要同時成立。

對應卡片關係：

- 身份與存取：  
  [Authentication](../knowledge-cards/authentication/) / [Authorization](../knowledge-cards/authorization/) / [Least Privilege](../knowledge-cards/least-privilege/)
- 傳輸與憑證：  
  [TLS/mTLS](../knowledge-cards/tls-mtls/) / [Certificate Chain and Trust](../knowledge-cards/certificate-chain-trust/) / [Certificate Revocation](../knowledge-cards/certificate-revocation/)
- 秘密與輪替：  
  [Secret Management](../knowledge-cards/secret-management/) / [Certificate Rotation and Renewal](../knowledge-cards/certificate-rotation-renewal/)
- 敏感資料與稽核：  
  [PII](../knowledge-cards/pii/) / [Data Masking](../knowledge-cards/data-masking/) / [Audit Log](../knowledge-cards/audit-log/)

若資安設計只停在單一工具，缺少資料流路徑與角色責任描述，章節仍停在術語層。

## 【判讀】事故治理把容量、觀測與資安接起來

事故治理的核心問題是「異常發生時，如何在可接受風險下恢復服務」。severity、[on-call](../knowledge-cards/on-call)、timeline、[RCA](../knowledge-cards/rca) 與 [game day](../knowledge-cards/game-day) 是將前面三軸落地的操作語言。

對應卡片：

- [Incident Severity](../knowledge-cards/incident-severity/)
- [On-call](../knowledge-cards/on-call/)
- [Incident Timeline](../knowledge-cards/incident-timeline/)
- [RCA](../knowledge-cards/rca/)
- [Game Day](../knowledge-cards/game-day/)

這些概念建立後，事故處理不會只依賴個人臨場反應。

## 【邊界】何時從概念章節進入實作章節

當以下問題都能回答時，代表概念層已完成，可以進入實作模組：

1. 核心服務的容量保護鏈是什麼（timeout 到 fallback）
2. 告警觸發後，[runbook](../knowledge-cards/runbook) 的第一個與第二個動作是什麼
3. 高風險資料在系統內的流動路徑與存取角色是什麼
4. 事故升級與回報節點如何定義

下一步建議路由：

- 進入可觀測實作能力：[04-observability](../04-observability/)
- 進入部署與可靠性能力：[05-deployment-platform](../05-deployment-platform/) / [06-reliability](../06-reliability/)
- 進入資安與資料保護能力：[07-security-data-protection](../07-security-data-protection/)
- 進入事故治理能力：[08-incident-response](../08-incident-response/)
