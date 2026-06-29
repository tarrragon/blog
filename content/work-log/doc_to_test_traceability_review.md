---
title: "10 個 Ticket、57 個綠燈、0 條追溯：從需求文件到測試的銜接檢討"
date: 2026-06-23
draft: false
description: "單元測試全綠、卻答不出「這些測試覆蓋了哪些 UseCase 場景」、需求到測試只有單向沒有反向追溯時回來看。列五個流程缺口（TDD 起手、靜態語言紅燈存根、反向追溯、邊界回補、Ticket 拆分對齊驗收）與對應的追溯矩陣、存根策略、拆分規則。"
tags: ["testing", "tdd", "traceability", "bdd", "go", "python", "monorepo", "process"]
---

## 這篇要解決什麼

**57 個 unit test 全綠，但沒有任何機制能回答「這些測試覆蓋了哪些 UseCase 場景」。**

monitor 專案 v0.1.0 從需求文件系統（Proposal → Spec → UseCase）一路走到 Collector 實作，中間經過 BDD 測試設計、紅燈測試撰寫、骨架實作讓綠。流程表面上順暢——10 個根 Ticket 全部完成、Collector 可啟動、所有 unit test 通過。但回頭檢視發現：需求→測試的銜接是單向管道，沒有反向追溯，也沒有邊界回補流程。

本文記錄 v0.1.0 的完整流程、發現的五個結構性差異、和落地的解決方案。

---

## 實際走過的流程

```text
saas 選型訪談
  → Proposal（MVP 範圍界定）
    → Spec（14 份，涵蓋 schema/ingestion/query/storage/rule-engine/SDK）
      → UseCase（5 個，UC-01 端到端事件流 ~ UC-05 Web 監控）
        → BDD 測試設計 ANA（全專案 26 個行為場景 → 整合/單元/協議測試清單）
          → 紅燈測試（9 個 Ticket 並行，72 個測試 FAIL）
            → 骨架實作（1 個 Ticket，57 個 unit test GREEN）
```

每個箭頭都有對應的框架機制：saas→doc 有 Stage 6 銜接、doc→TDD 有 doc-handoff 映射表。但箭頭只往右——沒有任何箭頭往左。

---

## 五個結構性差異

### 差異 1：「全專案 BDD 設計」不在 TDD Phase 模型中

TDD Skill 定義 Phase 0→1→2→3→4 的逐功能流程。v0.1.0 做的是「全專案 UseCase 一次性展開為 BDD 測試設計」，跨越 Phase 1 和 Phase 2 的邊界，粒度是專案級不是功能級。

這不是 Phase 設計的錯——Phase 模型適合增量開發（每次加一個功能）。新專案起手是不同的工作模式：批量設計、模組群組粒度。

**解法**：在 doc-handoff 新增「新專案起手模式」章節，描述批量 BDD 設計流程、Phase 0 豁免條件、模組群組粒度。

### 差異 2：紅燈測試需要存根（stub）

Go 是靜態語言，`go test` 必須編譯通過才能執行。紅燈測試引用的 type/interface 不存在時直接編譯失敗，不是「測試 FAIL」。

TDD Skill 的 Phase 2 說「設計測試」、Phase 3b 說「讓測試綠」，但中間的「建存根讓測試可紅」沒有定義。

**實作驗證**：v0.1.0 的每個紅燈 Ticket 都自帶建立存根（空 function return nil / 空 struct / 回 501 的 HTTP handler），存根讓 `go test` 編譯通過，合法測試 PASS、非法測試 FAIL = 紅燈狀態。

**解法**：Phase 3 rules 新增「存根策略」章節，涵蓋靜態語言（Go/Dart）和動態語言（Python/JS）的不同處理。

### 差異 3：測試→UseCase 沒有反向追溯

寫完 57 個 unit test 後，問「UC-01 的替代場景 01a（批次部分失敗 → 207）被哪些測試覆蓋？」——沒有任何機制能回答。

`doc test-map UC-01` 工具存在但回傳 0 個測試——因為它搜尋 UC frontmatter 的 `ticket_refs`，和測試檔案沒有連結。Spec 的「三方交叉比對」是建 Ticket 時的一次性動作，不是持續追溯。

**解法**：建立 `docs/traceability.yaml` 追溯矩陣，三層追溯（UC 場景 → 整合測試 IT-* → 單元測試 UT-* → Spec FR）。每個 entry 標記 `covered` / `gap` / `deferred`。

### 差異 4：邊界條件發現後沒有回補 UC 的流程

寫 Ingest Handler 測試時發現：「如果 POST body 不是 JSON 怎麼辦？」「如果 Content-Type 是 text/plain（sendBeacon）怎麼辦？」這些邊界在 UC-01 的場景描述中不存在。

測試設計的 BDD ANA 有涵蓋這些邊界場景，但 UC 文件本身沒有更新。邊界條件「住」在測試設計文件而非 UseCase——下次有人讀 UC 不會知道這些邊界存在。

**解法**：追溯矩陣增加 `boundaries:` 區段，測試撰寫者發現新邊界時加 gap entry，PM 建 DOC Ticket 回補 UC/Spec。Phase 4d 掃描所有 gap 確認無遺漏。

### 差異 5：Ticket 拆分邊界未對齊測試變綠驗收點

Collector 實作被拆為 4 個 Ticket：骨架（interface 定義）/ Storage / Ingestion Handler / Query Handler。骨架 Ticket 指派做「main.go + Config + Storage interface」，代理人完成了所有模組實作——57 個 unit test 從紅全部變綠，其餘 3 個 Ticket 的 acceptance 全被涵蓋。

初看像是「代理人超額完成」，回頭用判讀三問檢查骨架 Ticket：完成後有測試變綠嗎？→ 沒有（只定義 interface）。能獨立跑測試嗎？→ 不能（其他模組引用骨架的 type）。共用 type？→ 是。三問全部指向「不應獨立拆」。**根因是 Ticket 拆分設計**，不是代理人行為——按 Spec FR 拆（輸入驅動）導致骨架 Ticket 完成後 0 個測試狀態改變，不是有意義的驗收點。

**判讀規則**：實作 Ticket 的拆分邊界必須對齊「測試從紅變綠」的驗收點。一個 Ticket 完成後若沒有任何測試狀態改變，它不應該是獨立 Ticket。

判讀三問：

1. 這個 Ticket 完成後，有測試從 FAIL 變 PASS 嗎？
2. 拆出的各部分能獨立跑測試嗎？
3. 不同部分共用同一組 type/error/constant 嗎？

**反模式**：按 Spec FR 拆（輸入驅動）。**正確做法**：按「哪組測試變綠」拆（輸出驅動）。

---

## 追溯矩陣的設計

追溯矩陣是三個問題（向上追溯 + 覆蓋驗證 + 邊界回補）的統一解法。

### 結構

```yaml
UC-01:
  title: 端到端事件流
  scenarios:
    main:
      integration_tests: [IT-01-01]
      unit_tests: [UT-COL-01-01, UT-COL-02-01, UT-COL-04-01]
      spec_frs: [SPEC-002-FR-01, SPEC-003-FR-01]
      status: covered
    alt-01a:
      integration_tests: [IT-01-02]
      unit_tests: [UT-COL-01-03, UT-COL-02-03]
      spec_frs: [SPEC-002-FR-02]
      status: covered

boundaries:
  batch-limit:
    discovered_during: "ingestion-handler-red-tests"
    status: gap  # 需回補 UC/Spec
```

### 三個問題的對應

| 問題                  | 矩陣欄位     | 查法                                    |
| --------------------- | ------------ | --------------------------------------- |
| 這個 UT 為了哪個 UC？ | `unit_tests` | 搜尋 UT ID → 找到歸屬的 scenario        |
| UC 場景都有測試嗎？   | `status`     | 掃描 `gap` entry                        |
| 新邊界怎麼回補 UC？   | `boundaries` | gap entry → DOC Ticket → 回補 → covered |

### 整合點

| 機制         | 時機      | 動作                                 |
| ------------ | --------- | ------------------------------------ |
| doc-handoff  | 銜接時    | 初始化矩陣骨架（UC scenario 空映射） |
| 紅燈測試撰寫 | Phase 2→3 | 填入 unit_tests 映射                 |
| 邊界發現     | 實作中    | 加 boundary gap entry                |
| Phase 4d     | 重構評估  | 掃描所有 gap，建 DOC Ticket          |

---

## 附帶發現：並行派發的 Git 隔離問題

5 個代理人以 worktree 並行派發時，commit 內容交叉混入——A 代理人的 commit 包含 B 代理人的檔案。根因：主 repo 不在 main 分支，多個 worktree 共用同一分支 ref，`git add + commit` race condition。

**防護**：派發前確保主 repo 在 main + 已 push。單一代理人和正確條件下的多代理人都驗證通過。

---

## 結論

v0.1.0 的流程不是失敗——Collector 可用、57 個 test GREEN。問題在於「走到終點後沒有辦法回頭驗證起點」。需求→測試的管道是單向的：Proposal 說了什麼、Spec 定了什麼 FR、UC 描述了什麼場景，和最終的測試之間沒有結構化連結。

追溯矩陣不增加任何程式碼——它是一個 YAML 檔案，記錄「每個測試為什麼存在」。維護成本是每次寫測試多填一行映射。回報是：任何時候都能回答「這個 UC 場景有沒有被測試保護」。
