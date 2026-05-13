# 自掃描 Regex 集合

> **角色**：本卡是 `case-first-module-workflow` 的執行型 reference、被 [SKILL.md](../SKILL.md) 跟 [stage-5-polish-pass](./stage-5-polish-pass.md) 引用。
>
> **何時讀**：Stage 2 寫完後、Stage 5 polish pass 啟動時。

## 為什麼要自掃描

Stage 2 寫完後、在 commit 跟 stage 3 reviewer 跑之前、寫稿端自己跑掃描、抓出最容易違規的 pattern。自掃描的目的：

- **減少 reviewer 抓到的低層次 issue 數量** — 讓 reviewer 把 context 留給高層次的判讀、不是用來標記「不是 X、而是 Y」這種寫作習慣
- **建立 pattern recognition** — 寫作者看到 regex 報出來的位置、能逐漸學會在寫作當下避開

自掃描 regex 跟 reviewer 抓的 pattern 會逐漸脫節。每個模組 reviewer 抓出新 pattern 後、回頭更新 self-scan regex、避免在下個模組重蹈覆轍。

## 核心 regex 集合

### 1. 負向骨架（最大宗）

```bash
# 基本負向句構（技術約束敘述可能誤觸發、要逐筆判讀）
rg -n "不行|不可以|不要|無法|不能" <module-paths>

# 對比骨架開段（「不是 X、是 Y」「不是 X、而是 Y」）
rg -n "^[^|].*[，,]而是|^[^|].*[，,]不是" <module-paths>

# 「核心責任不是 X、而是 Y」變體段首（04 模組新發現的 pattern）
rg -n "^[^|].*責任(不是|並非)" <module-paths>

# 「沒有 X、會 Y」鏈式負向句構（05 模組新發現）
rg -n "沒有.*[，、]會" <module-paths>

# 「而不是 X」結尾否定
rg -n "而不是" <module-paths>
```

修法原則：

- 改成「主動陳述 + 後置邊界提醒」結構
- 例：「不是 X、而是 Y」→「Y、X 是次要 / X 屬另一層」
- 例：「沒有 X、會 Y」→「Y 的前提是 X、缺位會導致 ...」

**例外保留**：技術約束敘述（「多人共用 IP 無法區分」「單一 timestamp 無法判斷漂移」）、case 揭露的反直覺判讀（「主要風險是 X、不是 Y」屬合法）。

### 2. Case 引用框架取代商業邏輯先行

```bash
# 段首直接是「對應 [case]」
rg -n "^對應 \[" <module-paths>
```

如果結果在 section 開頭、要改成「先寫核心責任 1-2 句、再用『對應 [case]』補強」。

### 3. 編號漂移

```bash
# 找 04.X / 05.X 等 plain text 編號（應改成 [4.X](url) markdown link）
grep -nE "0[0-9]\.[0-9]" <module-paths>
```

### 4. 表格 / 列表後缺延伸段

不能用 regex 直接抓、要手動 grep `^|` 找表格位置、後面 2-3 行確認是否有延伸段：

```bash
grep -n "^|" <file>  # 找表格位置
```

判讀條件：表格後若直接接 `## ` 或下一個列表、缺延伸段。

### 5. 模板化（四步驟並列）

```bash
# 找 1. ... 2. ... 3. ... 4. 的並列結構（手動 review 是否情境異質卻套同模板）
rg -n "^[0-9]\. " <file>
```

判讀條件：四點性質不同（例：時序 + 治理 + 風險 + 視角）卻用同一個 1-4 編號 → 應拆敘事。

### 6. 用語不一

模組級 grep、確認術語統一：

```bash
# K8s 場景：instance / node / replica / pod 混用
rg -n "實例|節點|副本|pod" <module-paths>

# 繁簡用語：生命周期 vs 生命週期
rg -n "生命周期" <module-paths>
```

### 7. 失效 cross-link

`mdtools cards` 會抓 broken link、但同名 link 指向不同 URL（knowledge card vs 章節 URL）抓不到、要手動 grep：

```bash
# 找 link text 含「5.X」但 URL 不在 backend/05-* 下
rg -n "\[5\.[0-9]+ .+\]\(/backend/knowledge-cards/" <module-paths>
```

## 自掃描的執行時機

- **Stage 2 寫完每章後**：抓最即時的負向骨架、case 引用框架、編號漂移
- **Stage 2 全部完成、commit 前**：跨檔模板化掃描 + 用語不一
- **Stage 5 polish pass 啟動時**：完整跑一輪、抓 stage 4 修正引入的新 pattern

## Self-scan 的演進原則

每個模組 reviewer 抓出新 pattern 後：

1. 看是否能寫成 regex
2. 寫成的話加進本檔
3. 寫不成的話加進「手動 review checklist」
4. 把這個 pattern 記入 [SKILL.md](../SKILL.md) 的「反覆陷阱」段、提醒下次寫作前防範

把 self-scan regex 視為持續演進的工具、不是固定 checklist。

## 模組執行 baseline

| 模組  | self-scan 通過 | reviewer 抓 issue 總數 | 顯露的新 pattern                        |
| ----- | -------------- | ---------------------- | --------------------------------------- |
| 01-03 | yes            | 47-55                  | 表格不延伸、模板化（已寫進 regex）      |
| 04    | yes（漏）      | 51                     | 「核心責任不是 X、而是 Y」變體段首      |
| 05    | yes（漏）      | 59                     | 「沒有 X、會 Y」鏈式 + 四步驟模板高密度 |

每次新發現 pattern 時、本檔要更新、把 regex 補上、讓下個模組能在自掃描階段就抓到。
