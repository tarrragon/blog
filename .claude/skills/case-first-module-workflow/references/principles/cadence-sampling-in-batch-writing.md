# 批量寫作 cadence 抽樣原則

> **角色**：本卡是 `case-first-module-workflow` 的支撐型原則（principle）、被 [SKILL.md](../../SKILL.md) Stage 2 / Stage 5、[stage-5-polish-pass](../stage-5-polish-pass.md)、[self-scan-regex](../self-scan-regex.md) 引用。
>
> **何時讀**：Stage 2 寫批量內容到進度 10-20% 時、Stage 5 polish pass 發現跨檔 cadence 同質化時、或 reviewer 抓到「跨章 case 引用句構同質化」族問題時。

## 核心原則

寫作違規分三類、enforcement 時機要對應違規類型：

| 違規類型       | 識別形式                                                        | Enforcement 時機       | 工具                             |
| -------------- | --------------------------------------------------------------- | ---------------------- | -------------------------------- |
| 字面違規       | 單檔 regex 可偵測（emoji、裸 URL、粗體當標題）                  | Pre-commit / pre-push  | mdtools / regex hook             |
| 結構違規       | 單檔機制可偵測（章節缺失、frontmatter、broken link）           | Linter / build         | mdtools lint                     |
| Emergence 違規 | 跨檔比對才偵測（cadence 同質化、語氣漂移、framing 重複）        | **Stage 內抽樣**       | 寫作流程內 checkpoint、不是 hook |

關鍵：emergence 違規 *規則化不了*、不能丟給 hook 或 batch 完成後 reviewer、要在生成中（batch 進度 10-20%）抽樣 catch。最佳時機 = emergence 訊號剛夠強、且修正成本還可控的位置。

## 為什麼 emergence 違規需要 stage 內抽樣

三層原因：

1. **跨檔才能偵測**：單檔 cadence 沒問題、N 檔對齊才是違規；單檔 linter 永遠看不出
2. **規則化會 over-fit**：寫「段末不可用 X 句構」會把正常用法也擋掉；寫「段首句句型分佈 ≥ 3 種」需要先語法剖析、複雜度爆炸
3. **訊號隨樣本變化**：5 檔比對訊號弱、50 檔訊號強；linter 沒有「批次」概念、只看單檔

字面違規有三層防護（default 不寫 + pre-commit + CI）、結構違規有兩層（lint + review）；emergence 違規目前只有 stage 3 reviewer 一層且不可靠 — 本原則的修法是在「寫作中」加 stage 內抽樣 checkpoint。

## Stage 內 checkpoint 排程

按 batch 進度設置 checkpoint、不是「等寫完再看」：

| 寫作進度               | Checkpoint 動作                                                                              |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| 第 1-3 篇（pilot phase）| 刻意產出 3 種不同 framing 變體（例：「四件事 / 三條紅線 / 兩個 attestation 點」）            |
| 第 5 篇（進度 ~10%）   | 抽 5 個段首句並列、確認 framing 變體仍在輪替、沒 collapse 到 dominant                        |
| 第 10 篇（進度 ~20%）  | 抽 10 個段末收尾語並列、確認句型分佈 ≥ 3 種                                                  |
| 每 +10 篇              | 重複抽樣、發現 collapse 立即回頭加變體、不繼續寫                                             |
| Batch 結束前           | 全 batch 跨檔 cadence audit、確認 framing 分佈                                              |

最佳時機是 batch 進度 10-20% — emergence 訊號剛夠強、且修正成本還可控。過了這位置不修、修正成本 N 倍上升。

## 跨檔 cadence 抽樣位置

抽樣不是讀全文、是抽固定位置的句子做骨架對照：

| 抽樣位置      | 比對方式                                                                       | 預期分佈                                       |
| ------------- | ------------------------------------------------------------------------------ | ---------------------------------------------- |
| 段首句        | 每篇每段第一句並列、看句型骨架是否相同                                         | ≥ 3 種不同骨架、不是全篇同一個                 |
| 段末收尾語    | 每篇每段最後一句並列、看是否反覆用同一 frame                                   | 跨同類段、收尾語句型該有 50% 以上變化         |
| 表格前導句    | 表格前的引導句、看是否反覆用「下表整理 N 個面向」「以下從 X 維度比較」         | 不該所有表格都用同一前導模板                  |
| 列表收尾結構  | 列表後的承接段、看是否反覆「以上 N 點任一缺失就是 X」                          | 列表收尾不該全是「N 點任一缺失」結構           |
| 過渡詞密度    | 跨檔 grep「實際上 / 換句話說 / 換個角度 / 同樣 / 進一步」                       | 任一過渡詞在 N 篇中 > 60% 是警訊               |

選 *最容易反覆使用* 的 2-3 個位置即可、批量越大抽樣位置越要多。

## Cadence 多樣性是預先設計、不是事後修補

寫第 1-3 篇時就該意識：cadence 會被複製到下 N 篇。對策不是「寫完後 review 改」、是 *寫第一篇時就刻意製造 N 種 framing 變體、之後在這 N 種裡輪替*：

| 寫作階段       | Cadence 策略                                                                |
| -------------- | --------------------------------------------------------------------------- |
| 第 1-3 篇      | 產出 3 種不同 framing 變體                                                  |
| 第 4-10 篇     | 輪替使用 pilot 階段的 3 種變體、不固定一個                                  |
| 第 10+ 篇      | 加入第 4-5 個新變體、避免變體耗盡再變單調                                    |
| Batch 結束前   | 跨檔 cadence audit、發現同質化提前修                                        |

關鍵：*變體不是事後抽出來的、是設計階段就準備好的*。一旦寫過 5 篇還沒主動製造變體、就會默認複製第一篇 framing 到所有後續檔。

## 為什麼 multi-constraint 會把 cadence 推向便利解

當 N 個硬規範同時 enforce（章節結構 + 表格深化 + 行數範圍 + lint 規則 + 案例引用紀律），能通過所有過濾器的 framing 種類有限；批量寫作下、找到一個「都過」的 framing 後複製是 *合規 + 省 token + 風險最低* 的選擇；每篇都合規、輸出快、且看不到單篇有問題 — 同質化是「合規最佳解」的副作用、不是違規。

| Constraint 數 | 可通過的 framing 種類 | 批量同質化風險 |
| ------------- | --------------------- | -------------- |
| 0-1（自由寫）| 幾乎無限              | 低             |
| 2-3           | 多種                  | 中             |
| 4-5           | 幾種                  | 高             |
| 6+            | 1-2 種                | 極高、不可避免 |

對策不是加更多 constraint（會更 collapse）、是 pilot phase 強制變體 + stage 內抽樣。

## 不只是寫作

同骨機制在其他批量產出任務上也成立：

- **Code generation**：批量 service boilerplate 收斂到同 error handling 跟 log 格式
- **Test case 批量寫**：N 個 unit test 都用同一 setup-act-assert framing、覆蓋面看似齊但其實只測一種 axis
- **API doc 批量寫**：N 個 endpoint doc 都用同一段「方法 / 參數 / 回傳」三段式、抓不到 endpoint-specific 邊界

寫作 cadence 是 instance、機制是 *constraint 多 + 批量 → 便利驅動 collapse*。

## 跟其他原則的關係

| 原則                                                                  | 關係                                                                                                          |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [case-citation-three-part](./case-citation-three-part.md)              | 補 timing 軸 — 三段式紀律是 *單檔* 結構、本原則處理 *跨檔* cadence；兩者同 batch 都跑、不衝突              |
| [fact-vs-derive-layering](./fact-vs-derive-layering.md)                | 不同層 — fact-vs-derive 是 case 引用內部分層、本原則是跨檔 cadence；兩者正交                                 |
| [review-multi-axis-completeness](./review-multi-axis-completeness.md)  | Sibling — review 多軸的 *timing 軸* + *cadence 軸* 是本原則對應的兩條                                          |
| [ssot-correspondence](./ssot-correspondence.md)                        | Sibling — SSoT 處理「值的住址只能一處」、本原則處理「framing 的住址不能只有一處」；不同 surface 的對偶設計 |

## Stage 2 自查清單

寫批量內容（≥ 5 個同類檔）時、進度 10-20% 跑一次：

1. **第 1-3 篇是否準備了 framing 變體**？（不該第一篇定下來複製 N 次）
2. **進度 10% 時抽樣**：每篇段首句並列、看骨架分佈
3. **進度 20% 時抽樣**：每篇段末收尾語並列、看句型分佈
4. **跨檔 grep 過渡詞**：「實際上 / 換句話說」等密度是否 > 60%
5. **發現 collapse 立即回頭加變體**、不繼續寫

掃描指令：

```bash
# 抽段首句（每段 ## 標題後的第一段第一行）
rg "^## .+" <module-paths> -A 2 | rg -v "^##" | rg -v "^--$" | head -30

# 段末收尾語並列
# 用 awk 或手動抽取每段倒數第 2 行（最後通常空行）

# 過渡詞密度
rg -c "實際上|換句話說|換個角度|進一步|同樣" <module-paths>

# 列表收尾「N 點任一缺失就是 X」族
rg -c "任一缺失|任一不足|任一不到位" <module-paths>
```

## Polish pass 修法

如果 stage 3 reviewer 抓出大量 cadence 同質化 issue：

1. 列出同質 cadence 出現的位置（段首 / 段末 / 表格前導 / 列表收尾）
2. 不重寫整篇、只改 2-3 處 cadence、保留其他（不追求 0 重複）
3. 變化原則：把 N/N 同句構打散成 3-4 種變化、依該段 case 結構選對應句構
4. 修完跑跨檔抽樣確認 framing 分佈 ≥ 3 種

修法成本：每 batch 30-60 分鐘（依批量大小）。

## 跟 case 引用句構同質化的差異

[self-scan-regex](../self-scan-regex.md) §2a 跟 [stage-5-polish-pass](../stage-5-polish-pass.md) §7 已經處理「case 引用句構同質化」這個 *單一句構* 的同質化。本原則處理 *更廣的 cadence 同質* — 不只 case 引用句構、也包括段首 / 段末 / 表格前導 / 過渡詞等 *所有重複出現的句型骨架*。

兩者關係：

- §2a / §7：cadence 同質化的 *case 引用句構子集*、單檔可掃
- 本原則：cadence 同質化的 *全 surface 通則*、跨檔抽樣

§2a 跟 §7 是本原則在 case 引用 surface 的具體實作、不衝突。
