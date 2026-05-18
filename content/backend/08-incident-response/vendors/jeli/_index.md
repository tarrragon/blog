---
title: "Jeli"
date: 2026-05-01
description: "Postmortem / learning 平台、PagerDuty 收購整合"
weight: 9
tags: ["backend", "incident-response", "vendor"]
---

Jeli（2023 被 PagerDuty 收購、整合進 PagerDuty 平台）是聚焦 incident learning 的工具、承擔三個責任：narrative-based investigation（把 incident 寫成故事而非 timeline 條目）、cross-incident pattern detection（多事故 longitudinal analysis 找 systemic issue）、interview-driven postmortem facilitation。源自 Honeycomb 的 Production Excellence 文化圈。

## 本章目標

1. 從 IR 平台 import incident
2. 用 narrative timeline builder 重組事故敘事
3. 跑 interview workflow + structured analysis
4. 跨多事故跑 longitudinal analysis 找 pattern
5. 評估 Jeli（PagerDuty 整合後）vs 其他 retro 模組

## 最短路徑

```bash
# 1. PagerDuty 用戶 enable Jeli module（2024+ 整合）
# 2. 從 incident 自動 import
# 3. 跑 narrative builder
# 4. Schedule interview + analysis
```

## 日常操作與決策形狀

### Narrative timeline construction

子議題：

- 不是 chronological event list、是 story
- Contributing factors / latent conditions
- Surprising / unexpected behavior 紀錄

### Interview workflow + Cross-incident pattern

子議題：

- Question template（context / decision / surprise / pattern）
- Recording + transcription + structured analysis
- 多事故 tag + theme
- Pattern detection（recurring component / handoff / process issue）

## 進階主題（按需閱讀）

### Production Excellence 文化

子議題：Charity Majors / Nora Jones 推的學習文化、blame-aware（不是 blameless）、跟 [Honeycomb](/backend/04-observability/vendors/honeycomb/) 對齊

### PagerDuty 整合

子議題：從 PagerDuty incident 自動 import、整合進 PD Process Automation、roadmap 整合到 PD 主產品

### Multi-incident analysis

子議題：跨 6-12 個月事故趨勢、common contributing factor、org-level intervention（process / tooling / training）

## 排錯快速判讀

- **Interview 沒安排**：facilitator 沒指派 / schedule 衝突
- **Narrative 流於表面**：interview 沒問 surprising / unexpected 角度
- **Pattern detection 太空**：多事故 tag 不一致 / 樣本太少

## 何時改走其他服務

| 需求形狀            | 改走                                                                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 輕量 retro template | [incident.io](/backend/08-incident-response/vendors/incident-io/) / [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) retro 模組 |
| 不在 PagerDuty 生態 | Blameless / Howie                                                                                                                                |
| 自建 retrospective  | Confluence template + Jira action item                                                                                                           |

## 不在本頁內的主題

- Production Excellence 完整理論 / PagerDuty 整合細節 / Interview methodology

## 案例回寫

**Jeli founder Nora Jones 推 Production Excellence 文化**：Jeli 案例多以工作坊 / interview 形式呈現、非單一事故 post-mortem、本案例庫尚未收錄直接揭露 Jeli 流程的事故。

**待補 candidate**：

| 案例方向                                                            | 對應主題                                   |
| ------------------------------------------------------------------- | ------------------------------------------ |
| Slack / Honeycomb / Netflix 等公司 learning 流程                    | Production Excellence 文化、跨事故 pattern |
| Nora Jones 公開演講 / interview 中的事故學習案例                    | Incident interview methodology             |
| 對照閱讀：[Slack cases](/backend/08-incident-response/cases/slack/) | Slack 內部事故 retro 結構（外部視角）      |

## 下一步路由

- 上游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
- 平行：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)（已整合）
- 下游：[Honeycomb](/backend/04-observability/vendors/honeycomb/)（observability + learning 文化）
