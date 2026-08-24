---
title: "模組五：測試設計判斷"
date: 2026-06-19
description: "Mock 邊界判斷、assertion 設計、test data 代表性、flaky test 診斷"
weight: 5
tags: ["testing", "assertion", "flaky", "test-data", "mock"]
---

回答「這個斷言該怎麼寫」「這個 mock 邊界對嗎」。

## 本模組回應的測試盲區

| 案例                                                        | 盲區與補位                                                                             |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [T.C3](/testing/cases/ansi-parser-test-data-blindspot/)     | 手寫測試資料是真實環境的乾淨子集                                                       |
| [T.C3](/testing/cases/ansi-parser-test-data-blindspot/)     | Parser 透傳未知序列的靜默副作用                                                        |
| [T.C8](/testing/cases/fire-and-forget-test-race/)           | fire-and-forget 編排讓測試單跑綠、合跑紅——對應 Flaky test 根因分類章                   |
| [T.C9](/testing/cases/outbox-sequence-external-display/)    | 序列斷言取代存在斷言、時序約束用索引比較鎖住——對應 Assertion 品質三問章                |
| [註解防不了改壞](/work-log/comment_cannot_guard_invariant/) | 宣稱約束的註解無機制發聲、reviewer 以為有人在守——對應 測試的價值發生在它變紅的那一刻章 |

## 章節

- [Mock 邊界判斷決策表](/testing/05-test-design-judgment/mock-boundary-decision/) — 什麼時候 mock 夠用、什麼時候需要真實服務
- [Test data 代表性](/testing/05-test-design-judgment/test-data-representativeness/) — 手寫 vs 錄製 vs 生成三種測試資料來源
- [Assertion 品質三問](/testing/05-test-design-judgment/assertion-quality/) — 斷言的是行為嗎、能區分正確和錯誤嗎、會 flaky 嗎
- [Flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/) — 計時依賴 / 環境差異 / 資源競爭 / 非確定性
- [Flaky test 團隊治理](/testing/05-test-design-judgment/flaky-team-governance/) — quarantine 政策、retry 預算、信任修復的可視化與行動閾值
- [測試註解與命名紀律](/testing/05-test-design-judgment/test-comment-and-naming-discipline/) — 測試名稱與斷言說內容、註解只說操作約束、分析詞彙不入程式碼
- [測試的價值發生在它變紅的那一刻](/testing/05-test-design-judgment/test-as-change-guard/) — 建立測試問「未來哪種改壞要被擋」、變更時測試是唯一發聲的防護、約束該寫測試還是註解的分工判準

## Agent 產出程式碼時這個模組怎麼變

本模組的判準預設寫測試的人懂需求、而且看得懂自己在斷言什麼。程式碼由 agent 產出時這個前提鬆動：mock 邊界的判斷照舊成立，但「這條斷言的預期值從哪裡來」變成要先問的問題——預期值若取自實作的執行結果，斷言品質三問的每一問都會通過而測試什麼也沒驗。判準來源、驗收條件的射程與品質閘門的更替走 [模組六：Agent 產出程式碼的驗證](/testing/06-agent-authored-code/)。

那個模組的名字宣告了 agent 情境，而其中三件事與程式碼由誰寫**無關**，人手寫測試同樣適用——放在那裡是因為它們是同一次寫作的產物，不是因為它們只在 agent 情境成立：

- **測試案例怎麼設計**：把條件攤成維度表、看維度兩兩相乘哪些格子空著，程序在[驗收條件的等價類](/testing/06-agent-authored-code/acceptance-equivalence-class/)。它自己指定的維度第二來源是既有的事故與客訴紀錄，那是人的流程。
- **覆蓋率該不該當 KPI**：為什麼它是下限指標、當成通過條件會發生什麼，在[品質閘門的更替](/testing/06-agent-authored-code/coverage-to-mutation-gate/)。
- **既有套件實際守著什麼**：存活的突變逐點指出「程式在這裡改掉行為，這套測試不會發現」，同章。

## 跨分類引用

- → [monitoring 模組五 平台適配](/monitoring/05-platform-adaptation/)：各平台的 error 攔截機制差異影響 test 設計
