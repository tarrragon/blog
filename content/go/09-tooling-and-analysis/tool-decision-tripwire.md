---
title: "9.5 工具決策：regex 到 AST、Python 到 Go 的 tripwire"
date: 2026-04-24
description: "什麼訊號代表工具該升級到下一個層次；用 WRAP 框架做語言與實作層的技術決策；延遲決策的成本"
weight: 5
---

9.1–9.4 講的是「怎麼寫 Go 工具」。這一章退一步，問：**什麼時候該寫這個工具、什麼時候該升級既有工具**。決策錯了，寫得多好都沒用。

這個問題典型的反面教材是**過早優化**：為了一個 shell one-liner 就搭一個 cobra + AST + CI 的架構，花三天寫、維護一輩子。正面教材是**及時升級**：regex 開始每週踩一次誤判，就該評估要不要進 AST。

本章介紹 tripwire（預設觸發條件）決策法，用 blog 自己的選型當案例。

## 為什麼需要 tripwire

「什麼時候升級」本身是決策。如果不做預設，會發生兩件事：

**太早升級**：每次問「該不該升」的時候都說「升吧反正不會錯」。結果工具複雜度爆炸，維護成本拖慢產品開發。

**太晚升級**：每次都說「regex 再撐一下就好」。結果工具的誤判累積，作者開始手動 override、skip lint、加例外，工具信譽破產。

Tripwire 是**事前約定**：「當以下條件之一命中，就重新評估是否升級」。這把「該不該升」從**臨時直覺**變成**有根據的再評估**。

這個概念在 Chip 與 Dan Heath 的《Decisive》裡有詳細討論 — tripwire 的要點是**用事前的明確條件，取代事後的模糊直覺**。

## WRAP 框架套用到工具決策

WRAP = Widen options / Reality-test / Attain distance / Prepare to be wrong。對應到技術決策：

**Widen options**：不要只在「Go 還是 Python」之間選。多選項至少要有：

- 現有工具撐著（regex + shell）
- 半自動化（Python + regex，50 行腳本）
- 自訂工具（Python / Go + 適當 parser）
- 買服務（買現成 linter SaaS）
- 不解決（接受這個問題）

**Reality-test**：用數字跟樣本驗證假設。「regex 夠用」是假設，數字可能說「每 100 個 match 裡 15 個誤判」。

**Attain distance**：退一步看，如果這個工具三年後可能被捨棄，現在投入多少才合理。

**Prepare to be wrong**：先設 tripwire，萬一決策錯了也能及時 pivot，不會沉沒到底。

blog 的工具鏈決策用這個框架跑過一次，結論是 Go + goldmark。過程紀錄在 [mdtools 設計](../../../posts/mdtools-design/)，這裡只提煉可複用的決策 pattern。

## 三個實戰 tripwire

以下三組 tripwire 對多數內部工具都適用。遇到其中一個命中時，該花一小時重新評估現有工具是否夠用。

### Tripwire 1：從 shell one-liner 升級到腳本

**訊號**：

- 同樣的 shell 指令在三個以上地方重複貼過
- 指令超過 3 個 pipe 或巢狀 subshell
- 指令的行為要根據環境（CI vs local）分支

**升級方向**：寫成 20-50 行 Python 或 Bash script，放進 `scripts/`。

**反例**：每次寫新 shell 命令都起腳本檔。常用的一行 `grep` 不需要變 script。

### Tripwire 2：從 regex 升級到 parser / AST

**訊號**：

- Regex 需要「上下文判斷」（這個 match 在 code block 內嗎？在 HTML tag 內嗎？）
- 規則要處理嵌套結構（表格內的 link、code block 內的 heading）
- 誤報率超過 1% 或每週出現
- 新規則要知道「父節點」「子節點」（MD024 siblings_only 就是這類）
- 跨檔案的 graph 需求出現（backlink 分析、broken link 偵測）

**升級方向**：引入該格式的官方 parser（markdown → goldmark；YAML → `gopkg.in/yaml.v3`；Go → `go/parser`）。

**反例**：簡單的「每行開頭是 `#` 就當 heading」這類規則，regex 永遠夠用。不要為了「學 AST」硬上。

### Tripwire 3：從腳本語言升級到 Go

**訊號**：

- 需要 parse 有官方 Go 實作的格式（goldmark、go/ast、protobuf 等）
- 需要跨平台分發單一 binary
- Python / Node 的啟動時間在 pre-commit 的 accumulated cost 已感
- 要整合到 Go 生態系（產生 Go 程式碼、讀 Go 原始碼）
- 團隊主要語言是 Go，Python 腳本的維護者變成單一瓶頸

**升級方向**：Go。

**反例**：臨時的資料轉換、一次性的 data migration、快速 prototyping — Python 永遠比 Go 快動筆。

## 實戰紀錄：blog 的三層升級

blog 的 markdown 品質工具鏈在一個 session 內走完三層升級。把這個時間線攤開當案例。

### Layer 0：沒工具，靠 markdownlint IDE extension

**狀況**：IDE 裝 markdownlint extension，作者寫稿時看到 yellow underline 手動改。

**出現什麼 tripwire**：內容規模長大後，reviewer 收到 PR 發現 20 個 MD026 違規，手動改成 cognitive burden。更糟的是紅隊教材有平行結構（13 個案例各有 `### 弱點環節`），被 MD024 誤判為重複，作者開始 ignore 警告。

**升級驅動**：Tripwire 2 命中（規則需要父標題上下文，siblings_only 規則 IDE 沒有）。決策：升級到自訂工具。

### Layer 1 候選：Python + regex

**狀況**：50 行 Python 腳本，逐行 match。

**為什麼沒選**：兩個跨檔需求已經浮現 — 卡片雙向完整性、L1 link 驗證。這是 graph 需求，regex 做不到 (Tripwire 2 的後半段命中)。加上 blog 本身用 Hugo（Go 寫的，markdown 由 goldmark parse），用 Python 的 markdown parser 會有 render 跟 lint 判讀不一致的長尾風險。

這個評估花了約 15 分鐘，記錄在決策文件裡 — 重點不是最後選 Go，而是**評估本身有 artefact 可追溯**。

### Layer 2：Go + goldmark

**狀況**：選 Go，因為 (a) goldmark 是 Hugo 的 parser，lint 結果跟 render 必然一致；(b) 跨檔 graph 分析用 Go struct 乾淨；(c) 單一 binary 方便接 pre-commit hook 跟 CI，不用擔心 Python 環境。

**如何驗證決策正確**：看三個月後的狀態 — 工具有沒有被 bypass？新規則加起來順不順？CI 有沒有反覆失敗？作者有沒有開始覺得工具阻礙產出？這些訊號都沒出現，表示決策有效。若有出現，就是 Tripwire 3 的反向觸發（「該降級回 Python」或「該拆成多個專門工具」），又要重新評估。

## 延遲決策的具體成本

常見反論：「不急，等真的需要再升」。問題是**延遲本身有成本**：

- **Technical debt 複利**：regex 工具越長越大，每條新 rule 都變難，最後要重寫時要一次 migration 所有 rule。
- **誤報侵蝕信譽**：使用者每週看到工具報錯、檢查後發現是誤判，開始忽略工具。信譽一旦壞，再好的工具也沒用。
- **Option value 流失**：跨檔分析、graph 視覺化、CI 整合這些 downstream feature 都要在 AST 基礎上才能做；延遲升級等於延遲 feature 路徑。
- **機會成本複利**：每週花 30 分鐘手動改 lint 誤判，一年累積 26 小時 — 比升級工具的 8 小時多 3 倍。

時間視角變長，升級的 NPV 幾乎永遠正。**延遲不是零成本的預設，是要主動合理化的選擇**。

## 為什麼 blog 不走「先 Python 再 Go」的雙階段

有個常見建議：「先用 Python 快速做出雛形，驗證概念後再用 Go 重寫」。這個建議對**不確定需求**的情境有效（「我們不知道要什麼工具」），對**已知需求**的情境是浪費。

blog 的狀況是已知：

- 要 markdown lint + 跨檔 graph + pre-commit + CI — 四個需求都很明確
- 目標語言（Go）已經確定（Hugo 生態、單一 binary 需求）
- 第三方 parser 選擇（goldmark）已經是最優解

在這些條件下，寫 Python 原型的唯一價值是「學 AST 概念」。但同樣學習也能直接用 Go + goldmark 完成。花兩倍時間寫兩遍只為了「先驗證」，邏輯不成立。

判準：**需求越明確、目標語言越確定，雙階段越浪費；需求越模糊、選型還在評估，雙階段越值得**。

## 決策的副作用：artefact

不管最終選什麼，決策過程本身要留下 artefact。blog 案例裡的 artefact：

- [mdtools 設計紀錄](../../../posts/mdtools-design/)：為什麼是 Go、為什麼是 goldmark、tripwire 怎麼設的
- [什麼是 AST](../../../posts/what-is-ast/)：AST vs regex 的概念說明
- [markdown 寫作規範](../../../posts/markdown-writing-spec/)：工具要滿足的契約

三個文件加起來約 900 行，寫作時間不到半天。

**為什麼留 artefact 比決策本身更重要**：

- 半年後同樣問題再浮現時，不會重跑一遍評估
- 新加入的協作者能快速跟上決策脈絡
- Tripwire 條件寫下來才能被驗證（「三個月後有沒有命中？」）
- 反面證據出現時（例如發現 goldmark 有 bug），有清楚的位置記錄 revised decision

沒 artefact 的決策基本上等於沒做過。**決策是動作，artefact 才是沉澱**。

## 常見陷阱

### 把 tripwire 設太低

「每週誤判一次就升級」實務上等於「每週升級」。Tripwire 要設在**真的造成信譽或產出瓶頸**的位置。

### 把 tripwire 設太高

「等到 50% 誤判才升級」就太晚了 — 信譽早就垮了。合理範圍是 1-5% 誤判，或每週一次以上。

### 用 tripwire 取代日常 review

Tripwire 是「提醒重新評估」，不是「自動升級」。命中時要花時間評估，可能發現「還不該升，因為還有 X 原因」。Tripwire 是重新思考的觸發，不是自動化決策。

### 忽視已命中的 tripwire

「這個誤判已經出現第四週了，但我還是覺得先不要升」— 這是在告訴自己原本的 tripwire 設錯了，不是在等更好的時機。重新評估 tripwire 本身，不是 ignore。

## 擴充路徑

- **Decision log 範本**：把團隊的決策過程寫成 template，讓下次不用從零開始
- **Post-mortem of decisions**：決策後三個月回頭看，把「當時怎麼想」跟「現在怎麼看」對照
- **Pre-mortem 技巧**：決策前假設「三個月後這決定被推翻，最可能的原因是什麼」，當成補充 tripwire

## 下一步

[9.6 pre-commit hook 與 CI 整合](../pre-commit-and-ci/) 回到工程落地，看工具怎麼從 binary 變成 commit 與 CI 流程裡的執行體。
