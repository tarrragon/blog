---
name: vendor-deep-article
description: "Vendor 深度技術文章的寫作方法論：從 vendor overview 往下寫單一功能的深度文章。選題標準（3 條 + 反向判斷標準）、6 段結構模板（問題情境 → 概念 → 配置 → 故障演練 → 容量 → 整合）、跟 overview 與 hands-on 實作文章的職責劃分、寫作流程 7 step、批次 cadence variant 規劃。觸發詞：deep article、vendor 深度文章、vendor feature、pgBouncer、Patroni、寫 vendor 文章、sub-tool article、feature deep dive。Trigger when writing vendor-specific deep implementation articles."
license: MIT
metadata:
  version: 1.2.0
  category: writing-methodology
---

# Vendor Deep Article Methodology

Vendor 深度技術文章的寫作方法論 — vendor overview 飽和後、往下寫單一功能的深度實作文章。

跟 vendor overview 是不同產品：overview 回答「該不該選 / 跟同類差在哪」（選型層）、deep article 回答「某功能怎麼設 / 踩哪些坑 / 容量怎麼規劃」（實作層）。

## 適用情境

- Vendor overview 頁尾「預計實作話題」backlog 中的議題
- 跨 vendor 議題、不適合塞單一 vendor overview
- Overview 的「進階主題」段已經點到但 7-15 行說不清楚

不適用：

- **Vendor 文件已經夠好**：自己加一篇只是 paraphrase
- **議題太小**：塞進 vendor overview 某段 200 字解決
- **沒 production 經驗或 case 支撐**：純 spec 復述會變低品質內容
- **News-driven 短文**（CVE / 收購）：寫在 posts/
- **Cross-cutting 概念**（observability vs SRE）：寫在 report/ 或 posts/；單一術語或工具所屬那一類做法的通用模型（open 與 closed model）寫成知識卡，見〈同一個 vendor 在兩個模組各有一頁〉

## 選題標準

三條判斷標準、至少符合一條：

### 判斷標準一：被讀者問或被自己在 production 踩過

Overview backlog 的 9 項都重要、但寫作 ROI 不一樣。優先寫讀者最常問或自己踩最痛的、不是清單前幾項。

### 判斷標準二：跨 vendor 議題

跨兩個 vendor overview、寫在任一頁都偏。deep article 可以獨立、cross-link 兩個 vendor overview。

### 判斷標準三：overview 進階段落說不清楚

Overview 中 7-15 行的進階主題段、dynamic credential 怎麼 call / lease renewal 怎麼處理 — 不是 overview 該寫的。需要獨立深度文章。

## 6 段結構

| 段落                    | 內容                                                           | 比例 |
| ----------------------- | -------------------------------------------------------------- | ---- |
| 1. 問題情境             | 「為什麼會踩到這個」— 真實場景觸發、不是 textbook intro        | 10%  |
| 2. 核心概念             | 該 vendor 特有的概念（不是通用 concept、是這個 vendor 怎麼解） | 15%  |
| 3. 配置 step-by-step    | 真實可跑的 config + code + command（不是偽 code）              | 30%  |
| 4. 故障演練 / 邊界 case | 「踩到哪些坑、什麼徵兆、怎麼修」— production 經驗最有價值的段  | 25%  |
| 5. 容量 / cost 規劃     | 在什麼規模下這個配置適用、超出後要換什麼                       | 10%  |
| 6. 整合 / 下一步        | 跟其他 vendor 怎麼接、什麼 case 後該 revisit                   | 10%  |

6 段是內容指引、不是章節標題模板。章節名稱可隨主題調整。

跟 overview 的職責劃分：overview 不該出現在 deep article 的段落（服務定位 / 核心取捨表 / 跨 vendor 比較）。如果讀者沒看 overview 就直接讀 deep article、開頭一段引用 overview link 即可。

### 跟 `hands-on/` 實作文章的分工

專案把概念文章與讀者照著做的實作文章分開放，實作文章住在 vendor 資料夾底下的 `hands-on/`（例如 `vendors/<vendor>/hands-on/`）。deep article 屬於概念文章：「配置 step-by-step」段寫判讀需要的關鍵 config 與它每個參數的作用，「故障演練 / 邊界 case」段寫徵兆、成因與修法的判讀；從前置條件一路做到完成的完整 lab（整份 compose 檔、逐步的 restore drill、每一步該看到的輸出）放 `hands-on/`，deep article 在對應的段落連過去，連結寫出那一篇做了什麼操作。

判斷某一段該留在 deep article 還是搬進 `hands-on/`：讀者讀這一段是要理解「為什麼這樣配、壞了是什麼樣子」，留在 deep article；讀者讀這一段是要在自己的環境照著打一遍，放 `hands-on/`。`hands-on/` 的落點、寫法與量測值的處置照專案的資料夾規則。

### 同一個 vendor 在兩個模組各有一頁

同一個工具常常在兩個模組（或同一個模組的兩個章節資料夾）各有一個 vendor 資料夾，例如負載測試工具同時出現在可靠性模組與效能容量模組。兩頁從工具往外寫（這個工具是什麼、怎麼裝、有哪些功能）時，拿到的是同一批材料，因為工具的事實不隨模組改變；所以每一頁的 overview 與 deep article 都從所屬模組的讀者要做的判斷往回寫。可靠性模組的讀者在負載測試這一段要決定這一版的效能有沒有退化、能不能過 release gate，工具負責產生 regression 的證據；效能容量模組的讀者要決定目前的配置在延遲目標內處理得了多少請求、要加多少機器，工具負責找出受測服務的飽和點。

動筆之前，用工具名找別的模組或章節資料夾有沒有同一個工具的頁面：`rg --files <內容根目錄> | rg -i '<工具名>'`。工具頁不一定在 `vendors/` 底下，所以不只掃 `vendors/`；清單裡應該有這一頁自己，沒有代表工具名打錯。同一家業者的不同產品（同一家的 SIEM 與觀測平台）不做逐段並排，只問有沒有業者層的共通事實（同一支 agent、授權與計費、帳號結構）要寫成知識卡。找到同一個工具的另一頁時，兩頁並排，逐段依序問兩件事：

| 問句                                           | 答案                         | 這一段是什麼                                                                    | 處置                                                                                   |
| ---------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 一、這一段是不是操作細節                       | 是                           | 操作細節（安裝、設定步驟、介面操作）                                            | 放 `hands-on/`（已經有一邊有就放那裡，都沒有就放這次改的那一邊），或連到官方文件       |
| 二、其餘的段落，原封不動放進另一頁還成立嗎     | 成立，而且是一個概念         | 工具所屬那一類做法的通用模型（open 與 closed model、注入節奏、施壓端飽和）       | 寫成知識卡（先查有沒有現成的卡，一段裡有幾個概念就拆幾張），兩頁各改成一句連到卡     |
|                                                | 成立，而且拆不成單一概念     | 工具層的深度內容（版本沿革、JVM 調校、商業版與開源版的差異）                    | 寫成其中一邊的 deep article（已經有這個工具 deep article 的那一邊），另一頁連過去      |
|                                                | 只在本模組成立               | 本模組的觀點                                                                    | 留在本頁，往下寫深；deep article 的選題從這裡取                                        |
|                                                | 只在另一個模組成立           | 另一個模組的觀點（寫錯頁了）                                                    | 移到另一個模組的那一頁（已有同一個判斷就併進那一段），本頁需要時連過去               |

第二道問句是假設性的，不論另一頁現在有沒有這一段；比對的是內容、順序與輕重，兩頁段標相同不算成立。overview 的標準章節（核心取捨表、排錯快速判讀、服務定位）是兩頁差別最大的位置：照所屬模組工程師的視角寫，衡量哪些取捨、除錯時先查哪個症狀、照什麼順序查、每一項的權重都會不同。例如同樣看到 p99 變慢，可靠性的工程師先比對這一版跟基準的差距、找出退化的 endpoint，決定擋不擋 release；容量的工程師先確認施壓端沒有先飽和，再看受測服務哪一項資源先到頂。這幾節是讀者最需要、也最沒辦法從官方文件拿到的內容，所以兩頁都寫，各自寫深。

兩道問句分開問：操作細節放進另一頁也照樣成立，只問第二道的話它會被歸成知識卡。一段裡混了兩類以上（同一段寫了操作步驟與判斷，或通用模型的事實與它在某個模組的後果）時，先照類別拆成幾段再逐段問。抽成知識卡的段落，在兩頁都改成一句連到卡、寫出這個概念在本模組的判斷裡起什麼作用。觀點段落裡用到通用概念時（容量那一頁的排錯段提到施壓端飽和），概念連到卡，排錯的順序與權重留在本頁。

標題與 description 寫出這一頁的觀點，兩頁不用同一個標題：讀者在搜尋結果與連結文字上只看得到這兩處。兩頁互相連結，連結文字寫出另一頁的觀點（「這個工具在容量規劃裡的用法：找飽和點與施壓端的檢查」）。

判錯的代價：把重疊看成「兩邊在維護同一份東西」，處置就會變成合併或指定其中一頁當唯一的頁面；照從工具往外寫的現狀合併，留下來的是通用材料，另一個模組的觀點段落在合併後的那一頁沒有位置。分類之後某一頁歸成本模組觀點的段落是 0 段時，那一頁照現狀保留，在那一頁所在章節資料夾的規劃（Backlog）記下分段結果與「這個模組的章節改為直接連卡」的候選，刪頁與搬頁不在這一步做。推導與個案見 [same-tool-page-per-module-derives-from-the-modules-question](references/principles/same-tool-page-per-module-derives-from-the-modules-question.md)。

## 寫作流程

### Step 1：選題 + 經驗驗證

從 vendor overview 頁尾 backlog 挑一個、確認自己在 production 踩過或處理過。沒踩過的議題寫不出有價值的故障演練段。同一個工具在別的模組也有一頁時，先照〈同一個 vendor 在兩個模組各有一頁〉分段，選題從歸成本模組觀點的段落裡挑；歸成工具層深度內容的議題，只在它的落點那一邊寫。

### Step 2：草稿 outline + 真實 config

先列 6 段結構、把真實能跑的 config / code 放進 step-by-step 段。從 config 寫起、不從文字寫起 — 確保 implementation 段有實質內容。

### Step 3：補敘事文字

回頭補每段敘事 — 為什麼這樣配、跟 default 差異、邊界什麼時候會踩。對著 config 寫、不是憑印象寫。

### Step 4：故障演練段是核心

deep article 的差異化價值在故障演練段。Production 經驗、debug log、metric 徵兆描述、recovery 步驟。沒這段就跟 vendor 官方 docs 沒差。

### Step 5：cross-link 回 overview + case

開頭 link 到 vendor overview、結尾 link 到被引用的 case。

### Step 6：單一 reviewer 即可

deep article 的跨章一致性風險低（焦點窄）、案例引用密度低（1-2 個對照）。單一 reviewer 看「config 對不對 + 敘事流暢」就足夠。同一次另外寫了 `hands-on/` 實作文章時，那一篇照專案審查規則的觸發條件跑多輪審查，不套這一步：讀者會照著它在自己的環境操作。

### Step 7：行數檢查

200-400 行 sweet spot。超過 500 行該拆兩篇。低於 200 行通常是 overview 重複、應該塞回 overview。

## 批次 cadence variant 規劃

批次寫 ≥ 4 篇 deep article 時、寫前準備 N 種 framing 變體、每篇對應一種。

已驗證的 5 種 entry framing variant：

```text
- Variant A: 標準 6-section「問題情境」開頭
- Variant B: 痛點宣告 case-led
- Variant C: 概念反向定義
- Variant D: 對照表 / 矩陣驅動
- Variant E: lifecycle-driven 結構標題
```

cadence audit 抽樣位置在進度 60-80%（有 4 樣本對照訊號強、進度 10-20% 只有 1 樣本訊號弱）。

## 反覆陷阱

1. **從文字寫起**：沒有真實 config 的 deep article 是 paraphrase、不是 implementation 指引
2. **重複 overview 內容**：deep article 開頭寫了三段「為什麼選這個 vendor」— 已經在 overview
3. **跳過故障演練段**：deep article 沒有故障演練就跟官方 docs 沒差
4. **被動寫 batch 不做 variant**：同 vendor 多篇 deep article 特別容易 cadence collapse

## 跟其他 skill 的關係

- [compositional-writing](../compositional-writing/SKILL.md)：寫作 atomic 原則、適用所有寫作
- [migration-playbook-methodology](../migration-playbook-methodology/SKILL.md)：sibling、處理 cross-vendor process content
- [case-first-module-workflow](../case-first-module-workflow/SKILL.md)：跨多章節教學模組批次、本 skill 適用單篇或小批次 deep article

---

版本紀錄在同目錄的 `CHANGELOG.md`。
