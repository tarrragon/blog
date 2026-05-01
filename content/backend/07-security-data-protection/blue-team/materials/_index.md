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

藍隊文章引用素材時先選來源層級、並在引用前確認來源與當下文章主題的對應關係。下表是條件式對應、不是無條件 universal 推薦：

| 文章主題                    | 適合優先引用               | 適合場景                                     | 不適合場景                                                             |
| --------------------------- | -------------------------- | -------------------------------------------- | ---------------------------------------------------------------------- |
| 流程 / 治理基準             | NIST CSF、NIST SP 800 系列 | 政策層、合規對齊、跨組織共通語言             | 具體偵測規則 / IoC（NIST 不深入到 detection content layer）            |
| 處置建議 / 跨機構協作       | CISA advisory、CISA KEV    | 重大事件期間的處置時序、KEV 列入、公部門協作 | 平時穩定流程設計（CISA advisory 是事件驅動、節奏跟長期 baseline 不同） |
| 防守技術詞彙 / 對抗能力對照 | MITRE D3FEND、MITRE ATT&CK | 對抗矩陣、控制能力對照、紅藍對齊語言         | 具體 tooling 配置 / vendor-specific 設定                               |
| 偵測規則格式 / 生命週期     | Sigma、SANS detection 教材 | 規則格式、test event、retirement 流程設計    | 政策對齊 / 合規語言（detection content 不是 governance layer）         |
| 現場壓力 / 職能趨勢 / TTP   | Mandiant、Crowdstrike 報告 | 補事件案例、actor TTP、telemetry 視角        | 標準化基準（廠商報告各有觀察偏差、不適合當 single source of truth）    |

引用前的 verifiability check：「此來源原文有沒有 conditional scope？我引用時有沒有保留？」——避免把 NIST 的 organizational risk discussion 引成 universal mandate、把 MITRE 的 abstract technique 引成 specific tool requirement。

## 反向驗證

素材庫的反向驗證責任是提醒作者區分「來源能支撐什麼」與「來源需要在本章轉譯什麼」：

- **NIST / CISA**：適合支撐流程基準與處置建議、不適合直接生成 detection rule 內容。原文常是 organizational-level guidance、轉譯到 service-level 時要明示 deployment scope。
- **MITRE D3FEND / ATT&CK**：適合支撐威脅導向與防守詞彙、不適合直接當 implementation checklist。Technique-level 描述需要在文章補 product-specific mechanism。
- **Sigma**：適合支撐偵測規則格式、不適合當完整的 detection coverage map。單一規則的有效性 depends on log source / parser 一致性。
- **Mandiant / SANS**：適合支撐現場壓力與職能趨勢、不適合當 universal baseline。廠商視角受客戶基數 / 行業組成偏差影響。

每個素材的 last-checked 與適用範圍變動風險、由各 source 卡片在 professional-sources 子分類各自記錄。

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
