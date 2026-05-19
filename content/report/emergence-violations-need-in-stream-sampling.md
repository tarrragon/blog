---
title: "Emergence-class 違規規則化不了、要 stage 0 變體規劃 + stage 內抽樣兩層"
date: 2026-05-18
weight: 124
description: "違規分三類（字面 / 結構 / emergence）、enforcement 時機要對應違規類型；字面違規（emoji / 裸 URL）可 regex hook 在 pre-commit 攔、結構違規（章節缺失 / frontmatter）可 linter 攔、emergence 違規（cadence 同質化 / 跨檔語氣漂移）規則化不了、需要 *stage 0 變體規劃（主動設計）* + *stage 內抽樣（被動監測）* 兩層；checkpoint 只是監測工具、若 stage 0 沒準備 variant、被動抽樣不會自動發現 collapse；補 #82 字面 vs 行為的「時機」軸"
tags: ["report", "事後檢討", "工程方法論", "Review-timing", "Enforcement-design", "Writing"]
---

## 結論

違規類型決定 enforcement *時機 + 機制*。把所有違規都丟給 batch 完成後的 reviewer 是錯的；同樣錯的是 *只靠生成中抽樣*、沒有 stage 0 的主動變體規劃。Emergence 違規需要 *兩層防護*：

- **Stage 0 主動設計層**：寫批量前列 N 種 framing variant、分配給對應主題；這層決定 *cadence 是否錯開的根因*
- **Stage 內被動監測層**：生成中抽樣 audit、發現 collapse 立即修方向；這層 *偵測* 而不是 *設計*

兩層缺一不可：跳過 stage 0、被動抽樣不會自動發現 *主題語意 attractor*（相似主題天然引出的 framing collapse、見 [#122 cadence 同質化](../cadence-homogenization-in-batch-writing/) Update 段定義；migration playbook 3/5 collapse 即此實證、見本卡「Update: 被動寫作下...」段）；跳過 stage 內抽樣、stage 0 設計可能在中途 drift 沒被 catch。

| 違規類型       | 識別形式                                                  | Enforcement 時機                     | 工具                                                    |
| -------------- | --------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------- |
| 字面違規       | 單檔可 regex 偵測（emoji、裸 URL、粗體當標題）            | Pre-commit / pre-push                | mdtools / regex hook                                    |
| 結構違規       | 單檔可機制偵測（章節缺失、frontmatter 必填、broken link） | Linter / build                       | mdtools lint                                            |
| Emergence 違規 | 跨檔比對才偵測（cadence 同質化、語氣漂移、frame 重複）    | **Stage 0 設計 + Stage 內監測 兩層** | Stage 0 variant 規劃 + 寫作流程內 checkpoint、不是 hook |

backend/07 案例對照：51 個 vendor 字面違規 0、結構違規 0、emergence 違規（cadence 同質化）51/51；後者三個 reviewer 中只有一個 footnote 提到、是因為 reviewer 一次審 51 檔、emergence 訊號夠強才看出 — *如果只審 5 檔、emergence 訊號還不夠強、會被漏掉*。

---

## 為什麼 emergence-class 違規規則化不了

字面違規可以寫成 regex（`rg "✅|❌"`）、結構違規可以寫成 grammar 規則（章節必須有 N 個 H2）。Emergence 違規的特徵：

1. **跨檔才能偵測**：單檔 cadence 沒問題、N 檔 cadence 對齊才是違規
2. **規則化會 over-fit**：寫「段末不可用『四件事任一缺失』」會把這句正常用法也擋掉；寫「段首句句型分佈要 ≥ 3 種」需要先語法剖析、複雜度爆炸
3. **訊號隨樣本數變化**：5 檔比對訊號弱、50 檔比對訊號強；linter 沒有「批次」概念、只看單檔
4. **跟風格邊界模糊**：cadence 一致 vs cadence 同質、之間是漸層、threshold 因領域而異

結論：emergence 違規不能靠 hook / linter / 字面規則攔、只能靠 *流程設計* 在生成中 trigger 抽樣 review。

---

## Stage 內抽樣的設計

對 [case-first-module-workflow](/posts/case-first-agent-team-review-workflow/) 補強：stage 2（內容生成）內部加入 cadence checkpoint、不要等 stage 3 reviewer 才發現。

| 寫作進度     | Checkpoint 動作                                                                                 |
| ------------ | ----------------------------------------------------------------------------------------------- |
| 第 1-3 篇    | 刻意產出 3 種不同 framing 變體（pilot phase）、人類 / Claude 自審「這 3 篇 cadence 是否真不同」 |
| 第 5 篇      | 抽 5 個段首句並列、確認 framing 變體仍在輪替、沒有 collapse 到 dominant                         |
| 第 10 篇     | 抽 10 個段末收尾語並列、確認收尾語句型分佈 ≥ 3 種                                               |
| 每 + 10 篇   | 重複上述抽樣、發現 collapse 立即回頭加變體、不要繼續寫                                          |
| Batch 結束前 | 全 batch 跨檔 cadence audit、確認 framing 分佈                                                  |

關鍵：抽樣不是「Reviewer 在 batch 完成後跑」、是「寫作者在生成中跑」。寫第 5 篇之前先回頭看前 5 篇、發現問題就在第 5 篇修方向、不是寫完 50 篇才回頭改 50 個。

### Dogfood evidence (2026-05-18、N=4 sub-threshold 驗證)

本卡浮現後立即跑 4 篇 deep article 小批量 dogfood、用 *寫作中抽樣 + pilot phase variant* 取代 batch 後 reviewer：

| Checkpoint 位置 | 動作                                                             | 結果                                                          |
| --------------- | ---------------------------------------------------------------- | ------------------------------------------------------------- |
| 第 1 篇寫完     | 確認自然 framing（標準問題情境）                                 | OK、為第 2 篇 variant 比對 baseline                           |
| 第 2 篇寫前     | 主動換 variant（痛點宣告 case-led）                              | 段首句骨架明顯異於第 1 篇                                     |
| 第 3 篇寫前     | 第三種 variant（概念反向定義）                                   | 三種骨架完全錯開                                              |
| 第 4 篇寫前     | 第四種 variant（對照表驅動）+ 抽前 3 篇章節 1 entry sample audit | 四種骨架完全錯開、過渡詞密度 0、cadence 「任一缺失」族 0 hits |

對照前批 backend/07 51 vendor（無寫作中 checkpoint）：

| 維度                         | backend/07 51 vendor（batch 後才 review） | deep article 4 篇（生成中抽樣） |
| ---------------------------- | ----------------------------------------- | ------------------------------- |
| 修正成本                     | ~30-60 分鐘 polish 51 處                  | ~5 分鐘 / 篇前規劃 + 0 polish   |
| Cadence collapse 比例        | 51/51 (100%)                              | 0/4 (0%)                        |
| 發現 collapse 時的 sample 數 | 51（已寫完才發現）                        | 1-3（生成中即時調方向）         |

兩個驗證：

1. **Stage 內抽樣在 sub-threshold N=4 仍有效**：原本 checkpoint 表格寫第 5 / 10 篇抽樣、預設批量 ≥ 5；實測 *寫每篇前都做一次 entry framing variant check* 在 N=4 也能完全錯開 cadence
2. **生成中抽樣的邊際成本 << batch 後 polish 成本**：每篇前 ~1-2 分鐘 cadence check vs batch 後修 51 處 ~30-60 分鐘 — 比例 ~10-15 倍。本卡論斷「修正成本 N 倍」獲實證

### Update: N=5 full-threshold checkpoint 排程驗證

第一次 N=4 後立即跑 N=5 full-threshold batch（5 篇 PostgreSQL sub-tool）、驗證 checkpoint 排程在 ≥ 5 真實閾值的表現：

| Checkpoint 位置       | N=4 batch 動作                   | N=5 batch 動作                                               | 結果                              |
| --------------------- | -------------------------------- | ------------------------------------------------------------ | --------------------------------- |
| 第 1 篇寫完（20%）    | 確認 baseline framing            | 確認 baseline framing（lifecycle）                           | OK、N=5 抽樣訊號比 N=4 略強       |
| 第 2 篇寫前（20%）    | 主動換 variant                   | 主動換 variant（pain-driven）                                | 兩種 framing 對照成立             |
| 第 3 篇寫前（40-60%） | 第三種 variant                   | 第三種 variant（concept-reversed）                           | 三種對照、cadence drift 機率變大  |
| 第 4 篇寫前（60-80%） | 第四種 variant + 抽前 3 篇 audit | 第四種 variant（table-driven）+ 抽前 3 篇 entry sample audit | 四種對照、確認 framing 不耗盡     |
| 第 5 篇寫前（80%）    | -                                | 第五種 variant（standard 6-section）+ 抽前 4 篇 audit        | 五種對照、進度 80% audit 信號最強 |
| 批次完成（100%）      | 全 batch 跨檔 cadence audit      | 全 batch 跨檔 cadence audit                                  | N=5 audit 樣本大、訊號更強        |

兩批對照：

| 維度                           | N=4 batch（跨 vendor） | N=5 batch（同 vendor sub-tool 系列）   |
| ------------------------------ | ---------------------- | -------------------------------------- |
| 修正成本 / 篇前規劃            | ~5 分鐘 / 篇           | ~5 分鐘 / 篇（不變）                   |
| Cadence collapse 比例          | 0/4 (0%)               | 0/5 (0%)                               |
| 進度 20% (1 篇後) 抽樣可發現性 | 訊號弱（1 樣本）       | 訊號弱（仍 1 樣本）                    |
| 進度 80% (4 篇後) 抽樣可發現性 | 訊號強（4 對照）       | 訊號更強（4 對照 + 進入第 5 篇）       |
| 同 vendor 共同 context 影響    | 較低（4 篇跨 vendor）  | 高（5 篇同 vendor、collapse 風險最高） |

額外驗證：

3. **進度 10-20% 抽樣訊號偏弱、80% 抽樣最強**：N=5 batch 確認 *進度 80% audit* 是 emergence 訊號最強位置；原 principle 寫「進度 10-20% 抽樣」是過早、實際 *寫前 variant 規劃 + 進度 60-80% audit* 組合更穩
4. **同 vendor 同 type 是 collapse 最高風險、checkpoint 仍 cover**：N=5 batch 共同 context 比 N=4 多（同 vendor / 同 audience / 同 article type）、本卡論斷 emergence 風險 = 共同 context × N 成立；checkpoint 設計能 cover 是因為 *variant 規劃在 stage 0*、不靠 sample size 補

### Update: 被動寫作下 stage-internal checkpoint 仍失效

第三輪 5 篇 migration playbook 中 *前 3 篇被動寫作*（沒主動規劃 variant）— stage-internal checkpoint 雖然按時 fired、但因為 *沒 variant 預先準備*、checkpoint 看到的「不同主題」誤以為 framing 會自然錯開、實際 collapse 到「為什麼遷：X/Y/Z driver」格式：

| 進度    | Checkpoint 觸發 | 看到的訊號                                       | 行動                                | 結果                                  |
| ------- | --------------- | ------------------------------------------------ | ----------------------------------- | ------------------------------------- |
| 第 1 篇 | baseline 確認   | 「為什麼遷：cost / multi-vendor / cloud-native」 | 沒設變體規劃                        | 第 2 篇預設複製 framing               |
| 第 2 篇 | 應該抽樣 audit  | 跟第 1 篇都「為什麼遷 X/Y/Z」                    | **被動接受、認為主題不同就 OK**     | 第 3 篇也複製                         |
| 第 3 篇 | 應該抽樣 audit  | 連續 3 篇相同 framing                            | **發現問題、決定後 2 篇換 variant** | 後 2 篇主動 variant、cadence 部分挽救 |
| 第 4 篇 | active variant  | cost-driven entry、跟前 3 篇骨架不同             | 持續 variant                        | OK                                    |
| 第 5 篇 | active variant  | paradigm contrast entry                          | 全 batch audit                      | 3/5 collapse、2/5 不同                |

兩個關鍵 finding：

5. **Checkpoint 不夠、變體規劃才是 root**：stage-internal checkpoint 確實 fire、但 *沒準備 variant* 時 checkpoint 變被動驗證、不是主動防護；本卡原論斷「checkpoint 取代 batch 後 reviewer」需修正為「checkpoint + 預先 variant 規劃 兩層」
6. **主題語意 attractor 是新失效源**：N=5 batch 中前 3 篇都圍繞「為什麼換 vendor」、entry 自然 collapse 到 driver list；這個 attractor 比結構 constraint 更強、未來寫作要 *預先列 framing 變體* 而不是 *依賴 checkpoint 提醒換*

修正後的 Stage 內 checkpoint 排程（補 stage 0 變體規劃）：

| 寫作進度                 | Checkpoint 動作                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------- |
| **Stage 0（寫前）**      | **列 N 種 framing 變體 + 對應 N 篇主題分配**（新增、原本缺失）                      |
| 第 1-3 篇（pilot phase） | 按 stage 0 分配執行、人類 / Claude 自審「實際 entry framing 跟 stage 0 規劃對齊嗎」 |
| 第 5 篇                  | 抽 5 個段首句並列、確認 framing 變體仍在輪替                                        |
| 第 10 篇                 | 抽 10 個段末收尾語並列、確認句型分佈 ≥ 3 種                                         |
| 每 + 10 篇               | 重複抽樣、發現 collapse 立即回頭加變體                                              |

關鍵：*Stage 0 變體規劃是必要 step*、不能跳；checkpoint 是 *監測* 工具、不是 *設計* 工具。

詳細 SOP 跟 5 種 type 的具體應用見 [Migration playbook methodology](/posts/migration-playbook-methodology/) — 該 methodology 從 5 篇 migration playbook batch 抽出 stage 0 variant 規劃流程、本卡的「checkpoint 不夠」訊號是該流程的觸發實證。

### Update（2026-05-19）：第二輪 migration batch 全主動 variant 驗證

第二輪 migration batch（5 篇）寫前主動列 5 種 entry framing variant、cadence audit 結果 0/5 collapse；跟第一輪 3/5 collapse 對照、唯一差異是 *variant 規劃完整度*：

| 批次             | Sample | Variant 規劃                  | Stage-internal checkpoint 結果 | Collapse rate |
| ---------------- | ------ | ----------------------------- | ------------------------------ | ------------- |
| 第一輪（混合）   | N=5    | 前 3 篇被動、後 2 篇主動      | 被動段 checkpoint 失效         | 3/5 (60%)     |
| 第二輪（全主動） | N=5    | 寫前列 5 種 variant、執行對應 | Checkpoint 監測通過            | 0/5 (0%)      |

第二輪確認本卡核心論斷：

5. **Checkpoint + Stage 0 兩層在全主動下成功**：第二輪 5 篇 stage 0 全列 variant、checkpoint 監測無 collapse alarm、最終 audit 0/5；證實兩層防護在 *都執行* 下達成 principle 目標
6. **Stage 0 規劃的標準動作**：第二輪 stage 0 動作為「列 5 種 distinct entry framing 候選、對應 5 篇主題分配」— 不是「想到才換」、是 *寫第一篇前就完成* 的設計步驟
7. **主題相似性不會自動解決 cadence**：第二輪 5 篇都是 migration playbook、主題相似性跟第一輪一樣高；唯一差異是 stage 0 是否做、結果差 60% collapse vs 0% — 確認本卡論斷「checkpoint 不夠變體規劃才是 root」在 *主題相似性高* 場景下仍成立

---

## Batch 完成後 reviewer 為什麼太晚

三個成本問題：

1. **修正成本 N 倍**：51 篇都同質化、修正要動 51 篇；如果第 5 篇就 catch、只動 5 篇
2. **Cadence 已內化成「正確答案」**：寫完 50 篇後 Claude 已經把 dominant framing 視為「合規最佳解」、要打破比第 5 篇難
3. **Reviewer 訊號要求高樣本**：5 檔不夠 emergence、50 檔才強訊號；但 50 檔出來時修正成本已經爆

最佳時機：*Sample size 剛夠看出 emergence、且修正成本還可控* — 通常是 batch 內 10-20% 進度的位置（51 批量 → 第 5-10 篇）。

---

## 跟字面 / 結構違規的時機對照

字面違規（emoji）的 enforcement 鏈：

- 寫作中：Claude 預設不寫 emoji（pre-trained behavior + system prompt）
- Pre-commit：mdtools / regex hook 攔
- CI：full lint sweep

三層防護、字面違規幾乎不可能漏網。

結構違規（章節缺失）的 enforcement 鏈：

- 寫作中：模板 / skeleton 提示
- Pre-commit：lint 章節結構
- Review：人類 / agent 看章節列表

兩層機制、結構違規會被攔。

Emergence 違規目前的 enforcement：

- 寫作中：**無**（cadence 沒提示）
- Pre-commit：**無**（regex 攔不到）
- Review：Stage 3 reviewer 可能漏（單 reviewer 視野有限）

只有 stage 3 reviewer 這一層、且不可靠。本卡的修法是在「寫作中」這層加 stage 內抽樣。

---

## 不只是寫作：emergence 違規的其他例子

| 任務類型    | 字面違規例             | 結構違規例             | Emergence 違規例                               |
| ----------- | ---------------------- | ---------------------- | ---------------------------------------------- |
| 寫作        | emoji / 裸 URL         | 章節缺失 / frontmatter | Cadence 同質化、語氣漂移、frame 重複           |
| Code review | console.log / typo     | 缺型別 / 缺 test       | 抽象層級不一致、命名漂移、相似函式散落         |
| Schema 設計 | 缺 NOT NULL / 缺 index | 缺 FK / 缺 unique      | 命名慣例分裂、欄位順序不一致、表間關係風格不齊 |
| API doc     | 拼字 / broken link     | 缺參數說明 / 缺範例    | 例子風格不一、術語使用漂移、章節長短差異懸殊   |

三類違規對應三層 enforcement、不能混用工具。

---

## 反模式

| 反模式                                        | 後果                                          |
| --------------------------------------------- | --------------------------------------------- |
| 把 emergence 違規丟給 hook 解決               | Hook 抓不到、false confidence                 |
| 把 emergence 違規丟給 batch 完成後 reviewer   | 修正成本 N 倍、cadence 已內化                 |
| 寫 batch 不在中段抽樣                         | Emergence collapse 後才發現、無法即時修方向   |
| Reviewer prompt 不明示跨檔比對                | Reviewer 用單檔 frame 審 N 檔、emergence 漏抓 |
| 把 cadence 抽樣只列在「Batch 結束前」         | 太晚、跟「Reviewer batch 後跑」沒差           |
| 規範裡寫「不可 cadence 同質化」但不提抽樣機制 | 規範文字成立、執行落空                        |

---

## 跟其他抽象層原則的關係

| 原則                                                                                       | 關係                                                                                                                  |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)              | 本卡是 #82 的時機軸延伸 — #82 分字面 / 行為兩類、本卡分字面 / 結構 / emergence 三類並對應 enforcement 時機            |
| [#122 Cadence 同質化是模板的隱形維度](../cadence-homogenization-in-batch-writing/)         | 配對 — #122 定義違規類型、本卡解 enforcement 時機；兩張一起解 cadence 問題                                            |
| [#123 多重硬規範同時生效會把 cadence 推向便利解](../compliance-optimum-converges-cadence/) | 配對 — #123 解釋成因（constraint 收斂）、本卡解 enforcement（時機 + 抽樣）                                            |
| [#68 驗收的時間軸：四個 checkpoint](../verification-timeline-checkpoints/)                 | 同骨 pattern — #68 把驗收切「寫之前 / 開發中 / ship 前 / ship 後」、本卡把寫作 review 切時機；都是 enforcement 時機軸 |
| [#95 Multi-pass review 的 scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/) | 補 timing 軸 — #95 是 scope（橫向）、本卡是 timing（縱向）；兩軸都要對齊才完整                                        |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                             | 補一條時機 — #83 把 multi-pass 描述成「N 輪 frame」、本卡點出「N 輪要分散在生成時間軸」、不是全集中 batch 後          |

---

## 判讀徵兆

| 訊號                                               | 該做的事                                               |
| -------------------------------------------------- | ------------------------------------------------------ |
| Hook / linter 全綠但批量讀完感覺品質下滑           | Emergence 違規、改 stage 內抽樣機制                    |
| Reviewer 報告抓到大量同類問題且都集中在 batch 末段 | Review 時機太晚、移到生成中                            |
| 想加新 lint rule 解決 cadence 問題                 | 警訊 — regex 攔不到、改 stage 內抽樣                   |
| 同 batch 修正 PR 改動 ≥ 20% 檔                     | Stage 3 才發現 emergence、預設下一批要加 stage 2 抽樣  |
| 「寫完 N 篇後抽樣」的 N 跟 batch size 同數量級     | 抽樣等於 batch 後 review、N 應該 ≤ batch size × 20%    |
| 寫作流程沒有「checkpoint」概念                     | Enforcement 缺生成中這層、emergence 違規會持續產生     |
| Reviewer 只跑單檔 frame                            | 跨檔 emergence 看不到、補 reviewer prompt 要求跨檔比對 |

**核心**：違規分字面 / 結構 / emergence 三類、enforcement 時機要對應類型。Emergence 違規規則化不了、不能丟給 hook 或 batch 後 reviewer、要在生成中（batch 進度 10-20% 時）抽樣 catch；最佳時機是 emergence 訊號剛夠強、且修正成本還可控的位置。
