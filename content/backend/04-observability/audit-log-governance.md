---
title: "4.12 Audit Log 邊界與 PII 治理"
date: 2026-05-01
description: "把稽核訊號從 operational log 拆出、按法規與不變性治理"
weight: 12
tags: ["backend", "observability"]
---

## 大綱

- [audit log](/backend/knowledge-cards/audit-log/) 跟 operational log 的本質差異：對象、不變性、保留、法規
- [audit log](/backend/knowledge-cards/audit-log/) 該記什麼：who / what / when / where / outcome、不可被應用層改寫
- 不變性保證：append-only storage、tamper-evident hash chain、independent retention
- [PII](/backend/knowledge-cards/pii/) 治理：log 中的 PII 偵測、[data masking](/backend/knowledge-cards/data-masking/)、tokenization、最小揭露原則
- 法規維度：GDPR / HIPAA / SOC2 / 個資法 對保留期與存取的要求
- 跨團隊存取證據連續性：避免責任鏈斷在團隊邊界
- 跟 [4.1 log schema](/backend/04-observability/log-schema/) 的分工：4.1 是欄位設計、4.12 是治理邊界
- 跟 [07 資安](/backend/07-security-data-protection/) 的交接：稽核責任邊界
- 反模式：audit 跟 operational 混在同 stream；PII 直接打進 log；audit log 跟 application DB 同保留期

## 概念定位

[Audit log](/backend/knowledge-cards/audit-log/) 是把責任、授權與敏感操作留下可稽核證據的訊號，責任是支援合規、責任追蹤與安全事件調查。

這一頁處理的是 governance 邊界。Operational log 服務於除錯，audit log 服務於證據；兩者可以共享部分欄位，但保留、不變性、存取權限與 PII 規則不同。

Audit log 的治理優先序跟 operational log 相反。Operational log 優先服務 *當下* 的事故定位、追求即時性與覆蓋廣度；audit log 優先服務 *未來* 的責任追蹤、追求完整性、不變性與長期可查詢。當這兩種優先序衝突時，audit 治理要勝過 operational 便利性。

## 兩種 log 的責任分工

Audit log 跟 operational log 承擔兩條獨立治理鏈：前者服務證據與責任追蹤、後者服務除錯與事故定位。兩者在對象、保留、不變性、權限與粒度上的差異決定它們需要走分開的 pipeline、storage 與保留策略。把 audit log 視為 operational log 的子集、混在同一 stream 治理、會在第一次合規稽核或法規請求時讓證據鏈被打斷（典型徵兆是「靠 grep operational log 拼湊稽核需求」）。

| 維度     | Operational log                      | Audit log                          |
| -------- | ------------------------------------ | ---------------------------------- |
| 主要對象 | 工程師、SRE、IC                      | 合規、法務、安全事件調查、外部稽核 |
| 主要目的 | 還原事件、定位 root cause            | 證明授權、責任追蹤、事件不可否認   |
| 保留期   | 7-30 天為典型、依除錯需求            | 數月到數年、依法規與合約           |
| 不變性   | 通常可被 rotate、aggregate、re-index | append-only、tamper-evident        |
| 存取權限 | 工程團隊廣泛存取                     | 最小授權、存取本身也要被稽核       |
| 內容粒度 | 高頻、雜訊容忍                       | 低頻、語意精準、欄位穩定           |
| 查詢期望 | 秒級、即席                           | 分鐘到小時級、結構化、可重現       |

Operational log 在 incident timeline 還原時是主力證據。它的失分容忍度高：丟掉 1% 的 log 通常不影響 root cause 分析。

Audit log 的失分容忍度極低。一次授權記錄遺失、一個欄位漂移、一段時區錯位，都可能讓事後責任追蹤失效。這個差異決定 audit log 必須走獨立 pipeline、獨立 storage、獨立保留策略。

## 核心欄位與不變性

Audit event 的核心責任是回答五個問題：誰（who）、做了什麼（what）、何時（when）、在哪（where）、結果如何（outcome）。任一欄位缺失，責任追蹤鏈就有缺口。

| 欄位    | 內容                                 | 失分風險                          |
| ------- | ------------------------------------ | --------------------------------- |
| who     | 認證主體（user id、service account） | 用 IP 代替主體 → 多人共用無法區分 |
| what    | 操作類型 + 對象 ID                   | 只記操作不記對象 → 無法重現範圍   |
| when    | 事件時間（含時區）+ ingest 時間      | 單一 timestamp → 無法判斷漂移     |
| where   | 來源 IP、region、tenant、session     | 缺 tenant → 跨租戶事件無法區分    |
| outcome | 成功 / 失敗 / 拒絕 + 拒絕原因        | 只記成功 → 失敗操作無痕跡         |

不變性保證有三層遞進：

1. **Append-only storage**：寫入後不可修改、不可刪除。一般 object storage（S3 Object Lock、GCS Bucket Lock）或 immutable database table 可實作。
2. **Tamper-evident hash chain**：每個 audit event 含前一個 event 的 hash，篡改任一筆會破壞整條 chain。需要週期性 anchor 到外部時間戳服務或第三方公證。
3. **Independent retention**：audit log 的保留期跟 application DB 解耦，application 刪資料不影響 audit。retention 由合規團隊定義、不由應用團隊調整。

對應 [4.C1 FinTech 審計證據鏈](/backend/04-observability/cases/fintech-audit-evidence-observability/)：揭露「audit log completeness、event correlation integrity、retention policy drift」是合規場景的核心治理項目，本章關注的是治理邊界跟欄位設計，事件相關的 evidence 包裝由 [4.20](/backend/04-observability/observability-evidence-package/) 處理。

## 跨團隊存取證據連續性

跨團隊 audit 治理的核心責任是維持責任鏈在團隊邊界上的連續性。應用團隊記應用層事件、基礎設施團隊記 infra 層存取、IAM 團隊記授權變更，三段證據各自必要、但只有拼接後才能還原一次跨團隊敏感操作。常見失敗來自團隊邊界上的責任鏈斷裂 — 而非單一團隊技術不到位 — 任一段缺失都會讓事後復盤無法閉合。

對應 [4.C3 Healthcare 存取可追溯性與保留邊界](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)：揭露「access evidence continuity、retention boundary violations、timestamp integrity」三個方向。Healthcare 場景把這個問題放大，但跨團隊存取連續性是所有合規場景的共同議題。

讓存取證據跨團隊連續的可操作做法：

1. **共用 correlation field**：把 request id、trace id、session id 拉到應用層、infra 層、IAM 層共用，讓三段 log 可以拼起來。
2. **明確團隊 ownership 邊界**：每類 audit event 指定唯一 owner team，避免「應該是另一隊負責」的責任轉嫁。
3. **跨團隊 retention 對齊**：應用 audit、infra audit、IAM audit 的保留期要對齊或互為超集，避免一段過期一段還在的拼接斷裂。
4. **跨團隊查詢入口**：合規團隊有單一查詢介面能跨三段 log 拉同一 correlation id 的完整證據鏈。

把這些做法寫進 [4.18 operating model](/backend/04-observability/observability-operating-model/) 的 ownership 矩陣，能避免單次合規請求引發跨團隊的拼接工作。

## Retention 與保留策略漂移

Retention 是 audit log 跟 operational log 最大的治理差異。Operational log 通常用 30-90 天 rotation；audit log 依資料類型跟法規可能要 1-10 年。

把 audit log 跟 operational log 用同一條 retention 策略治理，會在合規稽核時被抓出來。常見的失敗：

- audit log 跟 application DB 同保留 90 天、不符 GDPR / HIPAA / 金融法規。
- audit log 經過 aggregation 處理、原始事件丟失、但 aggregated view 無法滿足法規要求。
- retention 策略由應用團隊調整、不經合規團隊審批、容易在成本壓力下被縮短。

Retention 漂移的偵測手段：把 retention compliance 變成可查詢的訊號。週期性對照各類 audit log 的實際留存時間跟政策要求、偏差超過閾值時觸發告警、讓漂移在治理週期內就被處理、避免等到稽核時才發現。

對應 [4.C1 FinTech retention policy drift](/backend/04-observability/cases/fintech-audit-evidence-observability/) 跟 [4.C3 Healthcare retention boundary violations](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)：兩個案例的判讀訊號都把 retention 偏離列為一級訊號（兩 case 的表格行明示這點）；本章在此基礎上補上「偏離視為治理事件、retention compliance 變成可查詢訊號」的展開、屬章節推論。

保留階梯（hot / warm / cold tier）與成本歸屬的詳細設計見 [4.7 控制面與保留階梯](/backend/04-observability/cardinality-cost-governance/#控制面與保留階梯)。

## PII 治理與最小揭露

[PII](/backend/knowledge-cards/pii/) 在 log 治理裡是雙重風險：寫入時的合規風險、長期保留時的外洩風險。Audit log 的長保留期讓 PII 風險被放大。

可操作的 PII 治理層次：

1. **寫入前 redaction**：應用層在輸出 log 時用結構化欄位 + 顯式 marking，避免把整個 request body 序列化進 log。
2. **Pipeline 層 PII 偵測**：collector 加上 PII pattern 偵測（信用卡號、身分證、token），預設遮罩、例外要顯式授權。
3. **Tokenization / pseudonymization**：把直接識別碼換成 token，token 跟原值的映射存在獨立、受嚴格授權的 vault 中。
4. **存取本身的稽核**：誰存取了哪段 audit log、何時存取、為什麼存取，本身也是 audit event。

最小揭露原則的實作關鍵是「預設遮罩、需要時申請」。把預設值設成揭露，會在某次事故除錯為了方便而打開、之後忘記關閉。預設遮罩讓每次解碼都是可追蹤的事件。

## 核心判讀

判讀 audit log 時，先看事件是否能回答 who / what / when / where / outcome，再看資料是否受到獨立保護。

重點訊號包括：

- audit event 是否不可由一般應用流程修改
- [PII](/backend/knowledge-cards/pii/) 是否經過 redaction、tokenization 或最小揭露
- [retention](/backend/knowledge-cards/retention/) 是否符合法規與客戶合約要求
- security incident 與 operational incident 是否能引用同一條證據鏈
- 跨團隊存取的 correlation field 是否連續

## 判讀訊號

- 稽核需求出現時、靠 grep operational log 拼湊
- log 中發現 credit card / 身分證 / token 等 PII
- audit log 跟 application 同 retention（30 / 90 天）、不符法規
- 應用層帳號可寫入 / 修改 audit log
- 法規稽核請求耗時數週、事件鏈定位需要人工補洞
- 跨團隊查詢同一 correlation id 拼不出完整鏈

## 反模式

| 反模式                         | 表面現象                                              | 修正方向                                        |
| ------------------------------ | ----------------------------------------------------- | ----------------------------------------------- |
| Audit 跟 operational 同 stream | 用一條 pipeline 處理所有 log                          | 拆獨立 pipeline、獨立 storage                   |
| PII 直接進 log                 | 信用卡、身分證在 raw log 中可見                       | Pipeline 層偵測 + 預設 redaction                |
| 同保留期治理                   | audit log 跟 application DB 同 90 天                  | 依法規重訂保留期、retention compliance 變成告警 |
| 應用層可改寫 audit             | service account 對 audit storage 有 write/delete 權限 | append-only + tamper-evident hash chain         |
| 跨團隊責任鏈斷裂               | 同一事件三段 log 互不關聯                             | 共用 correlation field、跨團隊 retention 對齊   |

## 交接路由

- [4.1 log schema](/backend/04-observability/log-schema/)：欄位設計
- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/)：audit 的長期保留成本
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：跨團隊 audit ownership 矩陣
- [4.20 evidence package](/backend/04-observability/observability-evidence-package/)：audit log 進入 evidence 交接
- [07 資料保護](/backend/07-security-data-protection/)：[PII](/backend/knowledge-cards/pii/) redaction 與責任邊界
- [8.5 post-incident review](/backend/knowledge-cards/post-incident-review/)：事故證據鏈引用 audit log
- [8.17 security vs operational IR](/backend/08-incident-response/security-vs-operational-incident/)：證據鏈來源
