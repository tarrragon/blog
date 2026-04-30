---
title: "7.BM 藍隊素材庫"
tags: ["Blue Team", "Security Materials", "Detection Engineering"]
date: 2026-04-30
description: "整理藍隊專業來源、真實案例、推演情境與控制模式，支援防守章節的大規模延伸"
weight: 725
---

藍隊素材庫的責任是提供防守推演的可回溯證據。素材庫把專業來源、現場案例、演練情境與控制模式分層整理，讓後續文章能從可靠材料延伸，並降低單一事故敘事的依賴。

## 素材分層

| 分層                 | 責任                                 | 使用時機                                                                   |
| -------------------- | ------------------------------------ | -------------------------------------------------------------------------- |
| Professional sources | 建立藍隊詞彙、流程與驗證基準         | 寫控制面、偵測、事故流程時引用                                             |
| Field cases          | 補充攻防事件中的防守壓力與決策節點   | 設計案例推演與 tabletop 時引用                                             |
| Scenarios            | 把來源與案例轉成可演練的服務情境     | 寫 Game Day 與 [runbook](/backend/knowledge-cards/runbook/) 時引用         |
| Control patterns     | 把重複出現的防守做法整理成可搬運模式 | 寫 [release gate](/backend/knowledge-cards/release-gate/) 與驗證規則時引用 |

素材分層的核心是讓來源、推演與文章分工清楚。Professional sources 提供判讀語言，field cases 提供現場壓力，scenarios 提供演練路徑，control patterns 提供工程化重用。

## 使用路由

藍隊文章引用素材時先選來源層級。若文章要定義流程，優先引用 NIST 或 CISA；若文章要定義防守技術詞彙，優先引用 MITRE D3FEND；若文章要定義偵測規則生命週期，優先引用 Sigma 與 SANS；若文章要補現場壓力，優先引用 Mandiant。

## 反向驗證

素材庫的反向驗證責任是提醒作者區分「來源能支撐什麼」與「來源需要在本章轉譯什麼」。NIST 與 CISA 適合支撐流程基準，MITRE 適合支撐威脅導向與防守詞彙，Sigma 適合支撐偵測規則格式，Mandiant 與 SANS 適合支撐現場壓力與職能趨勢。

## 子分類

| 子分類                                                                                                 | 責任                          | 初始狀態         |
| ------------------------------------------------------------------------------------------------------ | ----------------------------- | ---------------- |
| [Professional sources](/backend/07-security-data-protection/blue-team/materials/professional-sources/) | 專業來源卡與引用限制          | 先建立七張來源卡 |
| [Field cases](/backend/07-security-data-protection/blue-team/materials/field-cases/)                   | 藍隊現場案例與事件壓力        | 已收錄 11 張案例 |
| [Scenarios](/backend/07-security-data-protection/blue-team/materials/scenarios/)                       | Tabletop 與 Game Day 情境素材 | 已收錄 4 張情境  |
| [Control patterns](/backend/07-security-data-protection/blue-team/materials/control-patterns/)         | 控制面模式與驗證模式          | 已收錄 7 張模式  |

## 推演資產化大綱

| 順序 | 素材層           | 預計產出                               | 使用方式                                                                          |
| ---- | ---------------- | -------------------------------------- | --------------------------------------------------------------------------------- |
| 1    | Field cases      | 11 張現場案例卡(含變體)                | 抽出 defender pressure、control gap、detection route                              |
| 2    | Scenarios        | 4 張推演情境卡                         | 組成 tabletop、Game Day 與 incident handoff 演練                                  |
| 3    | Control patterns | 7 張控制模式卡                         | 提供 release gate、evidence chain、owner、credential、recovery 與 write-back 欄位 |
| 4    | Write-back       | 已回寫 `7.B1`、`7.B9`、`7.B12`、`7.24` | 讓素材回到文章主路由與實作交接                                                    |

比例設計參考 [素材庫比例支撐主情境的反向驗證](/report/source-library-ratio-supports-scenario-validation/):主情境 4 個、來源 2-3 倍、scenario 4-5 張、pattern 5-7 張。素材庫已達上述上限,進入穩定維護狀態。

## 下一步路由

素材庫先服務 [7.B1 防守控制面地圖](/backend/07-security-data-protection/blue-team/defense-control-map/)、[7.B2 偵測到回應的路由](/backend/07-security-data-protection/blue-team/detection-to-response-routing/) 與 [7.B4 Tabletop 與 Game Day](/backend/07-security-data-protection/blue-team/tabletop-and-game-day-design/)。後續每新增一篇藍隊文章，都要回到本素材庫補來源、情境或控制模式。
