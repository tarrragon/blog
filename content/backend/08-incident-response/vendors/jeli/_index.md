---
title: "Jeli"
date: 2026-05-01
description: "Post-incident learning 平台、2023 被 PagerDuty 收購、強調 interview-driven narrative 而非 timeline-only retro"
weight: 9
tags: ["backend", "incident-response", "vendor"]
---

Jeli 是 *post-incident learning platform*、2023 [被 PagerDuty 收購整合](https://www.pagerduty.com/blog/welcome-jeli/)、定位跟 [incident.io retro](/backend/08-incident-response/vendors/incident-io/) / [FireHydrant retrospective](/backend/08-incident-response/vendors/firehydrant/) / [PagerDuty 既有 Postmortem](/backend/08-incident-response/vendors/pagerduty/) 的差異不在 *retro template 本身*、而在 *human-in-the-loop interview workflow + narrative reconstruction + cross-incident pattern detection*。源自 Etsy / Honeycomb 等 SRE-mature org 的 learning-from-incident 流派、創辦人 Nora Jones 推 Production Excellence 文化。

## 服務定位

Jeli 的核心定位是 *post-incident learning 的方法論工具*、不是 paging / orchestration / on-call。底層三個責任：*incident import + 自動 narrative draft*（從 PagerDuty / Slack / Zoom transcript 拉資料、生 timeline + 故事框架）、*structured interview workflow*（OPM-style 訪談 facilitator → operator → contributor、question template 走 context / decision / surprise / pattern 四軸）、*cross-incident analysis*（多事故 longitudinal scan 找 systemic issue、非單事故 root cause）。

跟 [incident.io retrospective](/backend/08-incident-response/vendors/incident-io/) 比、incident.io 走 *Slack-native + lightweight template*、Jeli 走 *interview-heavy + narrative-first*；incident.io 適合 weekly retro 量大、Jeli 適合 sev1 / sev2 深度復盤。跟 [FireHydrant retrospective](/backend/08-incident-response/vendors/firehydrant/) 比、FireHydrant 走 *timeline + action item 結構化*、Jeli 走 *contributing factors + surprising behavior 敘事化*。跟 [PagerDuty Postmortem](/backend/08-incident-response/vendors/pagerduty/)（收購前的舊模組）比、PagerDuty 走 *report template 填空*、Jeli 走 *interview transcript → analyst-drafted narrative*；收購後 Jeli 是 PD 推薦的 deep-retro layer。

關鍵張力：*interview workflow 的人力成本* ↔ *narrative 品質*。Jeli 不能取代 facilitator、它放大有經驗的 incident analyst — 沒人投入 interview / coding / pattern review、narrative 流於 timeline 重寫、cross-incident analysis 空轉。組織要看清自己 *願意投入多少 incident analyst 時間換多深的 systemic learning*。

## 本章目標

讀完本頁、讀者能判斷：

1. Jeli 在 IR stack 中承擔哪一段（post-incident learning、不是 paging / orchestration）、為何要外接 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) on-call + [Slack / Zoom](/backend/08-incident-response/incident-communication/) 為 transcript source
2. Interview workflow 的 ownership 設計（誰當 facilitator、誰 code transcript、誰寫 narrative draft、誰 sign-off）
3. Cross-incident pattern detection 的最小條件（多少事故樣本、tag 怎麼一致、theme 怎麼歸納）
4. 何時用 Jeli、何時走 incident.io / FireHydrant / PagerDuty Postmortem 的取捨

## 最短判讀路徑

判斷 Jeli deployment 是否真的在學習、最少看四件事：

- **Incident import workflow**：從 PagerDuty incident / Slack channel / Zoom transcript 自動 import 是否設好、新事故進來幾分鐘內是否有 draft、source coverage 是否包含主 IR 通訊管道
- **Interview prep**：sev1 / sev2 是否預設排 interview、facilitator 是否非當事人、question template 是否走 context / decision / surprise / pattern 四軸而非自由 freestyle
- **Narrative draft 品質**：draft 是否寫成 *story*（contributing factors / latent conditions / surprising behavior）、不是 timeline 重寫；analyst sign-off 前是否走過 transcript citation 驗證
- **Cross-incident pattern**：多事故 tag taxonomy 是否一致、是否有人定期跑 6-12 個月 pattern scan、output 是否回到 [Incident Pattern Library](/backend/08-incident-response/incident-pattern-library.md) 或 process / tooling 改善

四件事任一缺失、就是 [post-incident review](/backend/08-incident-response/post-incident-review.md) 邊界的待補項目。

## 最短路徑

```bash
# 1. PagerDuty 用戶 enable Jeli module（2024+ 整合）
# 2. 從 PagerDuty incident / Slack channel / Zoom transcript 自動 import
# 3. analyst 驗 timeline citation、補 contributing factors + latent conditions
# 4. Schedule interview（facilitator 非當事人）、走 context / decision / surprise / pattern 四軸
# 5. Sign-off narrative、tag 進固定 taxonomy、進 cross-incident 池
```

## 日常操作與決策形狀

**Incident import + 自動 draft**：Jeli 從 PagerDuty incident metadata、Slack incident channel transcript、Zoom recording transcript 三路 import、自動產 timeline + 參與人列表 + 初步 narrative skeleton。意義是 *把人力從「翻聊天紀錄拼 timeline」釋放出來、聚焦在 narrative + interview*。但 auto-draft 是骨架不是結論、analyst 必須驗每筆 citation 是否準。

**Interview workflow（OPM-style）**：Jeli 推的 *Operating Procedures Manual* style 訪談 — facilitator 不是 incident commander、不是當事人；question template 走 *context*（這個系統平常怎麼運作）→ *decision*（事故當下你想到什麼選項、為何選這個）→ *surprise*（什麼跟你預期不一樣）→ *pattern*（你是否在別的事故看過類似形狀）。錄音 + transcription + structured coding（標 contributing factor / latent condition / how-near-miss）是這層的工程化。

**Narrative reconstruction**：narrative 不是 chronological event list、是 *story*。三個必寫元素：*contributing factors*（多重原因疊加、不是 root cause）、*latent conditions*（事故前已存在但沒人 trip 的條件、像系統 default config / 文檔誤導）、*surprising / unexpected behavior*（responder 當下覺得「這不對」的點）。對照 [post-incident review](/backend/08-incident-response/post-incident-review.md) 的章節原則。

**Cross-incident pattern detection**：跨 6-12 個月事故跑 longitudinal analysis、找 *recurring component*（同一個服務反覆 trip）、*recurring handoff*（某 team 之間 incident 傳遞失敗）、*recurring process gap*（同類 runbook 缺漏）。Output 是 org-level intervention 建議（process / tooling / training）、不是個案 action item。需要 tag taxonomy 跨事故一致、否則 pattern detection 抓不出 signal。

**PagerDuty 整合（2023+）**：收購後 Jeli 從 PD incident 自動 import、整合進 PD Process Automation 的 post-incident workflow、roadmap 朝 PD 主產品 deep integration。對已是 PagerDuty 客戶的 org 是 ecosystem 一致性增加；對非 PD 環境（用 [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) / [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/) / [incident.io](/backend/08-incident-response/vendors/incident-io/)）整合曲線變陡、長期可能要遷 paging stack。

**Causal Analysis based on System Theory (CAST)**：Jeli methodology 受 Nancy Leveson 的 CAST / STAMP 影響、把事故看成 *control structure failure* 而非 *component failure*。意義是分析重心從「哪台機器壞」轉到「哪個 control loop（人 + tool + process）失效」。實作上反映在 interview question 的 *decision* 軸（你當下手上有什麼 control）。

## 核心取捨表

| 取捨維度          | Jeli (PagerDuty)                       | PagerDuty Postmortem 舊模組 | incident.io retrospective | FireHydrant retrospective      |
| ----------------- | -------------------------------------- | --------------------------- | ------------------------- | ------------------------------ |
| 主要產出          | Narrative + contributing factors       | Report template 填空        | Slack-native retro doc    | Timeline + action item 結構    |
| 訪談支援          | Interview workflow + transcript coding | 無                          | 無（手動）                | 無（手動）                     |
| 跨事故 pattern    | Longitudinal analysis 內建             | 無                          | 限於 tag filter           | 限於 tag filter                |
| 適用 incident sev | sev1 / sev2 深度復盤                   | 一般事故報告                | weekly retro 量大         | weekly retro + action tracking |
| 人力成本          | 高（需 incident analyst）              | 低                          | 低                        | 低                             |
| 平台耦合          | PagerDuty ecosystem                    | PagerDuty                   | incident.io               | FireHydrant                    |
| 文化前提          | Production Excellence、blame-aware     | 無前提                      | Slack-first IR            | 結構化 action tracking         |

選 Jeli 的核心訴求：*SRE-mature org + 願投入 incident analyst 時間 + 已是 PagerDuty 生態 + 想做 systemic learning 而非單事故 root cause*。中等成熟度組織單事故 retro 量大、走 incident.io / FireHydrant 的輕量模板就夠。

## 進階主題

**Production Excellence 文化前提**：Nora Jones / Charity Majors 推的 *blame-aware*（不是 blameless — blameless 太絕對、實務上人會自我審查；blame-aware 是承認情緒存在但不把責任貼個人）學習文化、跟 [Honeycomb](/backend/04-observability/vendors/honeycomb/) Production Excellence 對齊。Jeli 工具只在這個文化前提下有用、強行 deploy 到 blame-heavy org 會被當成「找戰犯的另一個工具」。

**Interview methodology 深層原則**：question template 不是 checklist、是 *讓 responder 重建當下心智模型* 的工具。常見反例是 facilitator 問「為什麼你沒看 dashboard」— 這是 *hindsight bias*；正確問法是「你當下看了哪些 signal、它們告訴你什麼」。facilitator 訓練是 Jeli 流程的隱性投資、不只是工具熟悉度。

**Cross-incident tag taxonomy**：pattern detection 的前提是 tag 一致。常見治理失敗：每個 incident 用 free-form tag、半年後同類事故掛不同 tag、longitudinal scan 抓不到 signal。實務治理走 *固定 tag dictionary*（component / failure mode / contributing factor type）+ 季度 retag review、犧牲一些彈性換 pattern detection 可用性。

**Multi-incident analysis 的樣本門檻**：跨事故 pattern 要可信、最少 20-30 個同類事故樣本、跨 6-12 個月時間窗。樣本不足時 *pattern* 可能只是巧合 — 解法是先把單事故 retro 做扎實、樣本累積到門檻再啟動 longitudinal scan、不要為了「跑 cross-incident」而提前下結論。Output 形狀是 *org-level intervention 建議書*（哪個 process / tooling / training 該改）、回寫 [Incident Pattern Library](/backend/08-incident-response/incident-pattern-library.md)。

## 排錯與失敗快速判讀

- **Interview transcript 沒寫好**：facilitator 用 leading question / hindsight bias 問法、responder 答案被引導 — 走 question template review、facilitator 訓練、不讓當事人當 facilitator
- **Narrative drafting AI hallucination**：auto-draft 把 timeline 缺漏處用 plausible 但無 citation 的描述補上、analyst sign-off 沒驗 citation — 強制每段 narrative claim 必須回指 transcript / Slack / metric 來源、AI draft 是骨架不是結論
- **Narrative 流於表面 timeline 重寫**：interview 沒問 *surprising / unexpected* 角度、只重述 chronology — 強化 question template 第三軸、analyst review 拒收沒 contributing factors 段落的 draft
- **Pattern detection 太空 / 抓不到 signal**：多事故 tag 不一致 / 樣本數不足（< 20 incident）/ 沒人定期跑 scan — 補 tag taxonomy + 季度 pattern review 排程、不到樣本數先當單事故 retro
- **Interview 排不出來**：sev1 後 facilitator 沒指派 / 當事人 schedule 衝突拖 2 週 — sev1 / sev2 預設 IC handoff 時即指派 facilitator、interview 14 天內必排（記憶衰減 window）
- **Action item 黑洞**：retro 完成但 action item 沒人 own、3 個月後同類事故重發 — Jeli 不是 action tracking 工具、必須外接 Jira / Linear、retro 完成 == action item 有 owner + due date

## 何時改走其他服務

| 需求形狀                   | 改走                                                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 輕量 weekly retro template | [incident.io](/backend/08-incident-response/vendors/incident-io/) / [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) retro 模組 |
| 不在 PagerDuty 生態        | Blameless / Howie / 自建 Confluence template                                                                                                     |
| Action item tracking 為主  | Jira / Linear（Jeli 不擅長）                                                                                                                     |
| 沒 incident analyst 人力   | PagerDuty Postmortem 舊模組 / Confluence template + Jira action item                                                                             |
| Blame-heavy 文化未準備     | 先補 Production Excellence 文化、再上 Jeli                                                                                                       |
| Pattern library 治理       | [Incident Pattern Library](/backend/08-incident-response/incident-pattern-library.md)（章節層、不是工具）                                        |

## 不在本頁內的主題

- Production Excellence 完整理論（Nora Jones / Charity Majors 公開資料）
- PagerDuty Process Automation 跟 Jeli 的整合細節 roadmap
- CAST / STAMP 完整方法論（Nancy Leveson MIT 公開教材）
- Interview facilitator 訓練課程
- Tag taxonomy 設計細節（屬 [Incident Pattern Library](/backend/08-incident-response/incident-pattern-library.md)）

## 案例回寫

Jeli 流程本身的客戶多為 SRE-mature org（Slack / Honeycomb / Netflix 等公開 talk 引用）、本案例庫沒有直接揭露 Jeli 流程的事故、但所有跨事故 systemic learning 的 case 都是 Jeli 方法論的對照閱讀：

| 案例方向                                                                                        | 跟 Jeli 的關係（對照啟示）                                                                           |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [Slack cases](/backend/08-incident-response/cases/slack/)                                       | Slack 內部事故 retro 結構（外部視角）、Production Excellence 文化內生的 learning 流程                |
| [Cloudflare cases](/backend/08-incident-response/cases/cloudflare/)                             | 多次 control plane / data plane 事故的跨事故 pattern、systemic learning 的具體形狀                   |
| [GitHub cases](/backend/08-incident-response/cases/github/)                                     | 大型平台連續事故的 contributing factor 累積、cross-incident pattern detection 的典型 input           |
| [Datadog cases](/backend/08-incident-response/cases/datadog/)                                   | 觀測平台事故的 surprising / unexpected behavior 紀錄、interview workflow 該抓的 narrative 軸         |
| [Incident Pattern Library (section)](/backend/08-incident-response/incident-pattern-library.md) | Jeli cross-incident analysis output 該回寫的 collection、tag taxonomy 治理的章節層原則               |
| [Post-Incident Review (section)](/backend/08-incident-response/post-incident-review.md)         | Narrative reconstruction + contributing factors + interview workflow 的章節層原則、Jeli 是其工具實作 |

## 下一步路由

- 上游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)、[Post-Incident Review](/backend/08-incident-response/post-incident-review.md)
- 平行：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)（已整合 paging 來源）、[incident.io](/backend/08-incident-response/vendors/incident-io/)、[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)（輕量 retro 對照）
- 下游：[Incident Pattern Library](/backend/08-incident-response/incident-pattern-library.md)（cross-incident output）、[Honeycomb](/backend/04-observability/vendors/honeycomb/)（observability + Production Excellence 文化）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)、[4 observability](/backend/04-observability/)（事故當下 signal 來源 → Jeli narrative source）
- 官方：[Welcome Jeli (PagerDuty blog, 2023)](https://www.pagerduty.com/blog/welcome-jeli/)
