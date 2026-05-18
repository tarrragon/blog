---
title: "Cadence 同質化是模板的隱形維度"
date: 2026-05-18
weight: 122
description: "規範定義「模板」時通常只指內容欄位（規模對照、tripwire、失敗模式），忽略句型骨架 / 段首語 / 段末收尾語 / 表格前導句 / 過渡詞同樣是模板的一種；批量寫作時最易讓 cadence 同質化、單篇看起來都合規、連讀多篇才浮現預期化；51 vendor 都用「四件事 → 任一缺失就是 X 邊界的待補項目」是案例；自檢要 grep 首句 / 段末句 / 表格前導句、不是只看欄位"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Batch-writing", "Template-abuse"]
---

## 結論

「模板」有兩個維度、寫作規範通常只 enforce 第一維、第二維是隱形維度：

| 維度          | 內容                                                                                | 規範狀態                                                                          |
| ------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 內容欄位模板  | 規模對照表、tripwire 條件、失敗模式、回退路徑                                       | 已被 AGENTS.md §1 原則八 enforce（情境優先於模板）                                |
| Cadence 模板  | 段首句句型、段末收尾語、表格前導句、過渡詞、列表收尾結構                            | **未被規範涵蓋** — 51 vendor 同 cadence、各篇單看都合規、連讀才預期化            |

實際案例（backend/07 批量 51 vendor）：51 個 vendor 個別頁的「最短判讀路徑」段都收尾在「四件事任一缺失、就是 X 邊界的待補項目」。51/51 同骨、跨 9 個 service group、跨不同 vendor 性質。每一篇單看符合規範、表格有延伸、無 emoji、章節結構齊、案例正確；連讀 5 篇後讀者預期化、cadence 變成「閱讀時自動跳過的雜訊」。

---

## 為什麼 cadence 維度最容易失守

三層原因疊加：

1. **規範語言只涵蓋 *內容* 層、不涵蓋 *形式* 層**：AGENTS.md §1 原則八寫「不為了整齊把不同案例硬套同一模板」、配的例子是「規模對照、tripwire、失敗模式」；批量寫作時 Claude 把「保留情境差異」自動解讀成「敘事內容不同就行」、cadence / framing 不在規範定義的「模板」內、沒被擋。

2. **批量寫作的便利成本最低**：寫第一個 vendor 找到一個「都過 lint + 章節完整 + 表格有延伸」的 framing 後、複製這個骨架到下 50 個 vendor 是最省 token 的選擇；每篇都合規、輸出快、且看不到單篇有問題。

3. **單篇 review 看不到 cadence 違規**：cadence 同質化是 *跨檔* emergence、單檔 review（一次只讀一份）不會 trigger 訊號；只有「連讀多份 + 對齊 first sentence / closing line」才會看出。連 reviewer agent 也容易漏 — backend/07 三個 reviewer 中、只有寫作規範 reviewer 一句 footnote 提到「cadence 過齊」、其他兩個都沒抓到。

---

## Cadence 自檢方法

寫批量內容（≥ 5 個同類檔案）時、加入 cadence 抽樣 pass。不是讀全文、是抽固定位置的句子做骨架對照：

| 抽樣位置         | 比對方式                                                                       | 預期分佈                                       |
| ---------------- | ------------------------------------------------------------------------------ | ---------------------------------------------- |
| 段首句           | 把每篇每段的第一句並列、看句型骨架是否相同（「X 的 first-class concept 是 Y」）| ≥ 3 種不同骨架、不是全篇都同一個               |
| 段末收尾語       | 把每篇每段的最後一句並列、看是否反覆用同一個 frame（「四件事任一缺失就是 X」）| 跨同類段落、收尾語句型該有 50% 以上變化       |
| 表格前導句       | 表格前的引導句、看是否反覆用「下表整理 N 個面向」「以下從 X 維度比較」         | 不該所有表格都用同一個前導模板                 |
| 列表收尾結構     | 列表後的承接段、看是否反覆用「以上 N 點任一缺失就是 X」                        | 列表收尾不該全都是「N 點任一缺失」結構         |
| 過渡詞密度       | 跨檔 grep「實際上 / 換句話說 / 換個角度 / 同樣 / 類似 / 進一步」               | 任一過渡詞在 N 篇中出現率 > 60% 是警訊         |

抽樣不需要全做、選 *最容易反覆使用* 的 2-3 個位置即可；批量越大、抽樣位置越要多。

---

## Cadence 多樣性是「正向設計」、不是「事後修補」

寫第 1-3 篇時就該意識：cadence 會被複製到下 N 篇。對策不是「寫完後 review 改」、是「寫第一篇時就刻意製造 N 種 framing 變體、之後在這 N 種裡輪替」：

| 寫作階段             | Cadence 策略                                                                   |
| -------------------- | ------------------------------------------------------------------------------ |
| 第 1-3 篇（pilot）    | 刻意寫 3 種不同 framing 變體（如「四件事 / 三條紅線 / 兩個 attestation 點」）  |
| 第 4-10 篇（早期 batch）| 輪替使用 pilot 階段的 3 種變體、不固定一個                                   |
| 第 10+ 篇             | 加入第 4-5 個新 framing 變體、避免變體耗盡再變單調                            |
| 批量結束前            | 抽樣 5 個檔做 cadence 對照、發現同質化提前修                                  |

這個做法的關鍵是 *變體不是事後抽出來的、是設計階段就準備好的*。一旦寫過 5 篇還沒主動製造變體、就會默認複製第一篇 framing 到所有後續檔案。

### Dogfood evidence (2026-05-18、N=4 sub-threshold 驗證)

本卡浮現後立即跑了一次小批量 dogfood：4 篇 deep article（Vault dynamic credential / K8s graceful shutdown / Splunk RBA / Cloudflare Page Shield）寫作前主動規劃 4 種不同 entry framing（標準問題情境 / 痛點宣告 / 概念反向定義 / 對照表驅動）、跨檔 cadence audit 結果：

| 維度                                | backend/07 51 vendor（前批、無 variant 規劃） | deep article 4 篇（本批、pilot variant） |
| ----------------------------------- | --------------------------------------------- | ---------------------------------------- |
| Cadence collapse「任一缺失」族重複  | 51/51 (100%)                                  | 0/4 (0%)                                 |
| 章節 1 entry framing 種類           | 1 種                                          | 4 種                                     |
| 過渡詞密度（實際上 / 進一步 等）     | 未量化（同質化嚴重）                           | 全 0 hits                                |
| Lint / emoji / MD036 違規           | 0                                             | 0                                        |

兩個重點驗證：

1. **Sub-threshold（N < 5）仍適用**：原本 pilot 表格寫「第 1-3 篇刻意寫 3 種變體」、預設批量 ≥ 5 篇；實測 N=4 sub-threshold 配 4 種 variant 也能完全錯開 cadence
2. **Pilot phase 邊際成本低於 batch 後 polish**：寫作前花 ~5 分鐘規劃 4 種 framing variant、vs backend/07 51 vendor 批量後 polish ~30-60 分鐘改 51 處 cadence — 預先設計成本 < 事後修正成本 ~10 倍

### Update: N=5 full-threshold + 同 vendor sub-tool 系列驗證

第一次 N=4 驗證後、立即再跑 N=5 full-threshold batch — 5 篇 PostgreSQL sub-tool deep article（Patroni HA / autovacuum tuning / declarative partitioning / logical replication + Debezium / PITR + WAL archiving）。這批比第一批 *cadence collapse 風險更高* — 同 vendor、同 article type、同 6-section structure、同 audience。

三批 cadence 比較：

| 維度                                | backend/07 51 vendor（無規劃） | deep article 第一批 N=4（跨 vendor）| deep article 第二批 N=5（同 vendor）|
| ----------------------------------- | ----------------------------- | ---------------------------------- | ----------------------------------- |
| Cadence collapse「任一缺失」族重複  | 51/51 (100%)                  | 0/4 (0%)                           | 0/5 (0%)                           |
| 章節 1 entry framing 種類           | 1                             | 4                                  | 5                                   |
| 過渡詞密度                          | 未量化                         | 全 0 hits                          | 全 0 hits                          |
| 共同變數                            | 11 章節結構 + 表格深化         | 6-section deep article            | 6-section + 同 vendor + 同 audience |

額外驗證（補既有 sub-threshold 驗證）：

3. **Full-threshold N=5 variant 不耗盡**：5 種 variant（lifecycle-driven / pain-driven / concept-reversed / table-driven / standard 6-section）都對應主題本質、沒有「為了不同而不同」、5 篇骨架完全錯開
4. **同 vendor 同 article type 仍可錯開**：理論上 *同 vendor 同 type* 是 cadence collapse 最高風險場景（共同變數最多）；實測 variant 設計仍能覆蓋、collapse 風險不來自共同 context、來自 *寫作前是否主動規劃 variant*
5. **批次間 sample size 邊界更寬**：原 principle 寫 ≥ 5 才適用、實測 *N=4 跟 N=5 一樣有效*、threshold 5 是 emergence 訊號偵測的閾值、不是 *principle 適用* 的閾值；變體規劃在 N ≥ 2 就該做

### Update: Partial collapse 實證（被動 vs 主動 variant 對照）

第三輪 batch 寫 5 篇 migration playbook（跨 vendor、不同 module）、*前 3 篇被動寫作、後 2 篇主動規劃 variant*。結果：

| 篇 | Variant 規劃 | 章節 1 entry framing                          |
| --- | ----------- | -------------------------------------------- |
| 1 Splunk → Elastic     | 被動 | 「為什麼遷：X / Y / Z 三條 driver」          |
| 2 Redis → DragonflyDB  | 被動 | 「為什麼遷：X / Y / Z 三條 driver」          |
| 3 Postgres → Aurora    | 被動 | 「為什麼遷：X / Y / Z 三條 driver」          |
| 4 Datadog → Grafana    | 主動 | 「$50K/month bill 拆解」                     |
| 5 Kafka ↔ NATS         | 主動 | 「『Kafka → NATS migration』字面上不成立」    |

**3/5 collapse、2/5 錯開** = partial collapse。

四批 cadence rate 對照：

| 批次                              | Sample | Variant 規劃    | Collapse rate |
| --------------------------------- | ------ | --------------- | ------------- |
| backend/07 vendor batch           | N=51   | 無               | 51/51 (100%)  |
| Deep article 第一批（跨 vendor）   | N=4    | 主動             | 0/4 (0%)      |
| Deep article 第二批（同 vendor）   | N=5    | 主動             | 0/5 (0%)      |
| Migration playbook（混合）         | N=5    | **3 被動 + 2 主動** | **3/5 (60%)** |

三個關鍵 finding：

6. **Natural attractor 跟主題相似性正相關**：5 篇 migration playbook 都圍繞「為什麼換 vendor」、entry 自然收斂到「driver list」格式；同類主題的 *語意 attractor* 比結構 constraint 更強
7. **Sample size 不能解 cadence collapse**：N=5 跟前批 N=5 全錯開差異在 *variant 規劃*、不是 sample size；證實本卡論斷「variant 規劃必須主動、不是 N≥5 自動避免」
8. **Partial collapse 比 0% collapse 教育價值高**：負面 evidence（natural attractor 不規劃就 collapse）比正面 evidence（規劃就錯開）更證明 principle；後續寫作流程應 *預期* 主題相似批次的 collapse 風險、不是樂觀假設

---

## 反模式

| 反模式                                             | 後果                                                                |
| -------------------------------------------------- | ------------------------------------------------------------------- |
| 規範只列「內容欄位不可模板化」、沒列 cadence       | Cadence 同質化合規無感、批量產出後才浮現                            |
| 批量寫作前不準備 framing 變體                      | 第一篇 cadence 被複製到 N 篇、修正成本 = N × 重寫                   |
| Review 用單檔 frame                                | 跨檔同質化抓不到、需要跨檔抽樣對照                                  |
| 看到 cadence 過齊就改個別檔                        | 修不到根因 — 沒準備變體、改完一個下次還是會同質化                   |
| Cadence 視為「寫作風格、不算違規」                 | 對單篇成立、對批量不成立；連讀預期化就是品質損失                    |
| Reviewer prompt 沒明示「比對跨檔 first/closing」   | Reviewer 抓不到 emergence-class 違規                                |

---

## 跟其他抽象層原則的關係

| 原則                                                                                            | 關係                                                                                                                              |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                       | 本卡是 #67 在「寫作骨架」維度的具體實例 — 複製第一篇 framing 最便利、但意圖（情境化敘事）失準                                     |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                                  | 補一條 frame — multi-pass 該加「跨檔 cadence 抽樣」這輪、單檔 frame 抓不到本卡反模式                                              |
| [#94 正向改寫要保留對照論據](../positive-rewrite-preserves-contrast/)                          | 同骨 pattern — 寫作規則執行時、字面合規（正向陳述 / 不模板化）但行為失準（cadence 同質 / 結論空降）                              |
| [#114 Multi-pass review 的 frame 顆粒度盲點](../multi-pass-review-frame-granularity-blindspot/) | 互補軸 — #114 是 frame 顆粒度（規則 vs 字句層）、本卡是 cadence 維度（內容 vs 形式層）                                            |
| [#117 跨多 case 合成的 frame 必須標為章節合成](../cross-case-synthesized-frame-must-be-labeled/)| Sibling — 都是「合規但有隱形偏差」族；#117 是引用層、本卡是骨架層                                                                |

---

## 判讀徵兆

| 訊號                                              | 該做的事                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| 連讀同 batch 3-5 篇後、感覺「節奏一樣」           | Cadence 同質化、跑跨檔抽樣對照確認                                    |
| 段末收尾語在 batch 內出現率 > 60%                 | 收尾語模板化、改寫部分檔的收尾                                        |
| 段首句句型在 batch 內反覆出現                     | 段首模板化、補 framing 變體                                          |
| 批量 ≥ 5 篇但寫作前沒準備 framing 變體            | 預設會同質化、補 pilot 階段 3 種變體                                  |
| Reviewer 報告沒提到「cadence」字眼                | Reviewer prompt 沒明示跨檔 frame、要補                                |
| 「四件事 / 三點 / 兩個 trade-off」反覆出現        | 列表收尾結構模板化、改用敘事段或重組視角                              |
| 想拿 batch 內某一篇當下次寫作參考                 | 警訊 — 該篇 cadence 可能會被複製到下批、應準備變體再起筆              |

**核心**：模板不只是內容欄位的模板、cadence / 句型骨架 / 收尾語也是。批量寫作前準備 framing 變體、寫作中跨檔抽樣對照、不要等 batch 完成後 reviewer 才發現連讀預期化。
