# Codex Brief: knowledge-cards 知識網拓展（Task 2）

本 brief 為 Task 1（補卡 + 回填連結）完成後的下一階段工作。以 `backpressure.md` 為 worked example，示範如何從一個**已穩固的中心卡片**向外拓展知識網，讓鄰接概念形成雙向可達的網絡，而不只是散落的單點。

執行前請先完成 Task 1 並讀取 `.codex/codex.md`、`.codex/briefs/knowledge-cards.md`。

---

## 1. 任務定位

| 項目 | 說明 |
|------|------|
| 目標 | 讓每張 hub 卡片的鄰接概念形成密度足夠的知識網，單一卡片在閱讀時就能觸發下一層學習路徑 |
| 與 Task 1 差別 | Task 1 聚焦「既有正文出現的術語」；本任務聚焦「概念延伸到尚未寫入正文但必要的鄰接節點」 |
| 成功訊號 | 中心卡片閱讀後，讀者可透過 3 跳內的連結覆蓋該主題的所有核心相鄰概念 |

---

## 2. 拓展方法：Centered-Node Fan-Out

### 2.1 節點分層

以一個**已完善的中心卡片**（hub）為原點，將鄰接概念按語義距離分層：

| 層級 | 定義 | 舉例（中心：backpressure） |
|------|------|-------------------------|
| L0 中心 | 本輪拓展的主題 | backpressure |
| L1 直接相關 | 與中心共同出現在同一語境、解決同一問題空間 | buffer, queue, rate-limit, load-shedding, backpressure 的訊號（queue-depth / consumer-lag） |
| L2 機制層 | 實現 L0 時常用的具體手段 | concurrency-limit, semaphore, worker-pool, bounded-queue, admission-control, pause-resume |
| L3 運維層 | L0 失效時的觀測與處理 | retry-storm, cascading-failure, circuit-breaker, fail-fast, dashboard 指標 |
| L4 相關主題 | 跨語境類比，同一原理的變體 | pull-based-streaming, reactive-streams, flow-control, feedback-control |

### 2.2 拓展四問

每個 L1–L3 節點要進一步拓展前，逐項回答：

| 問題 | 判斷 |
|------|------|
| 此節點卡片是否存在？ | 存在 → 檢查品質；缺失 → 列入新增清單 |
| 既有卡片是否為薄卡片？ | 依 `.codex/briefs/knowledge-cards.md` §3.1 正面範例標竿自評 |
| 雙向連結是否完整？ | 中心 → 鄰居 有；鄰居 → 中心 有嗎？ |
| 與中心的邊界是否清楚？ | 薄卡片常把中心的責任寫進自己，需劃清範圍 |

### 2.3 連結密度目標

| 指標 | 目標 |
|------|------|
| 中心 → L1 鄰居連結數 | ≥ 5 |
| L1 鄰居 → 中心反向連結 | ≥ 60% 的 L1 節點指回中心 |
| L2 機制卡片獨立閱讀率 | 讀者不需回中心就能理解單一機制 |
| L3 運維卡片的取捨段落 | 明確說明此機制的失效模式與替代方案 |

---

## 3. Worked Example：以 backpressure 為中心的知識網

> **閱讀提示**：本節是**說明用的工作範例**（worked example），用途是示範「看到一張中心卡片後如何推導出拓展動作」。Codex 執行時依實際 hub 狀態自行盤點，**本節的缺口清單與優先序僅為示範**，不當作硬性任務清單使用。

### 3.0 推導過程示範（從閱讀到識別缺口）

實際執行時，拓展動作由「閱讀中心卡片 → 提問 → 產生清單」推導，而不是從預設清單勾選。示範流程：

| 步驟 | 動作 | 示例推導 |
|------|------|---------|
| 讀 | 讀完 `backpressure.md` 全文 | 關注四段結構中出現的術語與連結 |
| 列 | 列出文中提及但未連結的術語 | 例如「in-flight 數量」在「設計責任」段出現但無連結 → 候選缺口 |
| 辨 | 判斷該術語是否值得獨立成卡 | in-flight 在多處出現（backpressure / Kafka consumer / admission control）→ 值得獨立 |
| 查 | 檢查既有卡片是否已存在 | `in-flight-message.md` 偏訊息語境，缺通用版 → 確認缺口 |
| 記 | 記錄缺口 + 所屬層級 + 理由 | L2 機制層，理由：多處引用且語義獨立 |

產出的清單是「從證據推導的結果」，不是預設答案。

### 3.1 L1 直接相關（示例盤點）

| 概念 | 卡片狀態 | 雙向連結 | 拓展動作 |
|------|---------|---------|---------|
| queue | 已存在 | 需確認 queue → backpressure 反向連結 | 檢查 |
| buffer | 已存在 | 需確認反向 | 檢查 |
| queue-depth | 已存在 | 需確認反向 | 檢查 |
| rate-limit | 已存在 | 新增「與 backpressure 的差異」段落以對稱 | 補強 |
| load-shedding | 已存在 | 需確認反向 | 檢查 |
| consumer-lag | 已存在 | 需確認反向 | 檢查 |

### 3.2 L2 機制層（示例缺口識別）

> 下表示範**如何從推導過程產生缺口清單**。每個候選卡片附「識別理由」說明為何獨立成卡、與相鄰卡片的邊界在哪。實際執行時 Codex 依盤點結果產出自己的清單。

| 候選卡片 | 識別理由（為何值得獨立） | 與相鄰卡片的邊界 |
|---------|------------------------|----------------|
| concurrency-limit | backpressure 例子段落提到「動態調整 worker 取件速度」，但既有 rate-limit 卡片聚焦進入速度，缺了「活躍量」角度 | rate-limit 控制「每秒進來多少」；concurrency-limit 控制「同時有多少在跑」。兩者互補 |
| admission-control | backpressure 設計責任段落提到「排隊上限 / 拒絕策略」，這整個流程（檢查 in-flight → 進處理區或排隊 → queue 滿則拒絕）本身是一個值得獨立的模式 | 上位於 concurrency-limit + bounded-queue + fail-fast 的組合規則 |
| bounded-queue | 既有 queue 卡片說明 queue 是什麼，但「有界 + 拒絕策略」是獨立設計決策 | queue 講概念；bounded-queue 講「超限如何處理」 |
| hysteresis | 拉取節奏控制常需要雙水位避免抖動（例如 backpressure 在 Kafka consumer 的 pause/resume），這個模式跨多個情境重複出現 | 單一概念，與 pause-resume、autoscaling、circuit-breaker 的半開狀態都相關 |
| pause-resume | backpressure 在 pull-based 系統的具體落地機制，與 push-based 的「拒絕 / 排隊」策略不同 | backpressure 是抽象概念；pause-resume 是 Kafka consumer / reactive streams 的具體手段 |
| in-flight-count | backpressure 反覆提及，既有 in-flight-message 偏訊息語境，缺通用版 | in-flight-message 是訊息；in-flight-count 是跨語境的「尚未完成的工作量」 |
| worker-pool | 已存在 | 確認雙向連結 + 品質是否達薄卡補強標準 |

**semaphore 的判定示範**：semaphore 是具體實作手段（一種 concurrency-limit 的機制）。判定是否獨立成卡片的問題是「它是否跨多個 domain 重複出現」。若 backend 知識卡片以概念為主，semaphore 屬於語言/實作層（Go sync.Semaphore、Python asyncio.Semaphore），可能更適合放到 `go-advanced/` 或 `python-advanced/` 的章節內，而非進 backend knowledge-cards。這類判定**由 Codex 在執行時對齊用戶需求決定**。

### 3.3 L3 運維層

| 概念 | 卡片狀態 | 拓展動作 |
|------|---------|---------|
| retry-storm | 已存在 | 確認從 backpressure 失效段落可連到此 |
| cascading-failure | 已存在 | 確認反向 |
| circuit-breaker | 已存在 | 評估 backpressure 段落是否需 link |
| fail-fast | 已存在 | 確認反向 |

### 3.4 示例拓展優先序（Wave 1 草案）

以下為示範性質的執行順序。實際 Wave 劃分依盤點後的依賴關係調整：



1. **補強既有薄卡片**：依 Task 1 的「既有卡片補強判定」處理 L1 已存在但薄的卡片
2. **新增 L2 缺口卡片**：concurrency-limit → admission-control → bounded-queue → hysteresis → pause-resume（依依賴順序）
3. **回填雙向連結**：L1/L2 所有鄰居補上「→ backpressure」反向連結
4. **回填中心卡片**：若 backpressure.md 提及新建立的 L2 節點卻未連結，補連結

---

## 4. 推廣到其他 hub concepts（示例候選）

Task 2 完成 backpressure 子網後，以同樣方法推廣到其他 hub。下表為**示例候選清單**，實際 hub 選擇由用戶確認：

| 候選 hub | 所在主題 | 粗估 L1–L2 節點數 | 為何適合作為 hub |
|---------|---------|------------------|----------------|
| circuit-breaker | 可靠性 | 10–15 | 多種失效場景（timeout / error-rate / dependency-health）都匯集於此 |
| idempotency | 訊息與事件 | 8–12 | 與 retry / dedup / at-least-once 等概念高度相關 |
| replay-runbook | 事故應對 | 6–10 | 連結 event-log / offset / projection / dual-write 等運維場景 |
| transaction-boundary | 資料一致性 | 8–12 | 涉及 isolation / lock / saga / outbox 等多個次主題 |
| cache-invalidation | 快取 | 10–15 | 串起 ttl / eviction / stampede / write-through / write-behind |
| graceful-shutdown | 部署與運維 | 6–10 | 橋接 drain / in-flight / health-check / readiness |

**節點數為粗估**，用於決定單一 Wave 是否會過重（> 15 建議拆 Wave）。每個 hub 各自獨立一個 Wave，避免一次處理太多主題導致連結錯亂。

---

## 5. 執行流程

1. 選定中心卡片（hub），完成 §2.1 的 L0–L3 節點分層（先腦力激盪列表，再自評）
2. 對每個節點執行 §2.2 拓展四問，產出三份清單：新增 / 補強 / 雙向連結回填
3. 依 §3.4 優先序批次執行（每批 3–5 張卡片 + 對應連結）
4. 每批完成後執行 `.codex/codex.md §5` C1–C7 + `.codex/briefs/knowledge-cards.md §5` K1–K7 檢查循環
5. 在對話中回覆本 hub 拓展成果：節點數、新增清單、連結回填摘要

---

## 6. 與 Task 1 的關係

| 項目 | Task 1 | Task 2 |
|------|--------|--------|
| 驅動來源 | 既有正文術語 | 中心卡片鄰接拓展 |
| 拓展方向 | 向內補齊（正文需要的卡片） | 向外拓展（卡片需要的鄰居） |
| 依賴 | 獨立執行 | 需 Task 1 先建立基礎覆蓋 |
| 標竿卡片 | backpressure.md（新範例） | backpressure.md + 其 L1–L2 鄰居（本輪補完後成為樣板） |

Task 1 先做，Task 2 才有穩固的中心卡片可以展開。

---

**Last Updated**: 2026-04-23
**Version**: 0.1.0 — 初版：Task 2 知識網拓展 brief，以 backpressure 為 worked example
