---
title: "商業概念知識卡片"
date: 2026-05-19
description: "用原子化卡片整理商業模式、單位經濟、進入市場、競爭護城河、市場動態、資本估值與執行知識的術語"
weight: -1
tags: ["business", "knowledge-cards"]
---

商業知識卡片的核心目標是把商業分析文章中的高密度術語拆成可獨立閱讀的概念。VC、創辦人、策略分析師寫的文章常一句話塞進三到五個縮寫；工程背景的讀者若沒有共同術語表，就會卡在名詞而錯過真正的判斷邏輯。

每張卡片只處理一個術語的核心概念、概念位置、可觀察訊號與判讀方式。卡片之間用相對連結互引，建立可導航的概念網路。

## 建卡判準

商業術語建卡的判準是該術語是否承擔判斷成本，而不是只看是否常見。讀者如果不知道這個名詞，會誤判某段分析的結論或無法解碼一張財務表，就值得建卡。

適合建卡的術語通常有三個特徵。第一，它包含結構性意涵，超出字面翻譯—例如 lock-in 背後是切換成本與生態系設計，遠不只「鎖定」二字。第二，它會影響讀者對商業策略的判讀—例如 FDE 不只是「派工程師」，而是揭露 SaaS 模式不可行的訊號。第三，它可以被獨立說明成「核心概念、位置、訊號、判讀」的四段結構。

不適合建卡的是過度寬泛的詞（「策略」「成長」「轉型」）或僅在特定文章中成立的臨時詞。這類詞應在分析文章中直接補清楚。

## 卡片格式

每張卡片用四段結構：

```markdown
---
title: 術語中英文名
date: YYYY-MM-DD
description: 一行說明卡片責任
weight: 編號
---

開頭段：定義核心概念，回答「這個術語是什麼」。首段須包含至少一條鄰卡連結建立網路。

## 概念位置

說明這個概念在商業推理中的位置，跟其他概念的關係。應包含至少一條鄰卡連結。

## 可觀察訊號與例子

說明什麼時候這個概念變成判讀的重點，舉一到兩個具體情境。

## 判讀方式

說明遇到這個概念時要做什麼判斷，常見陷阱是什麼。
```

開頭段必須先給定義，不要先丟例子。可觀察訊號段必須是具體情境，不可只給名詞解釋。判讀方式段必須給可操作的判斷指引。

## 商業模式

公司賣什麼、賣給誰、怎麼收費。這是讀懂任何分析文章的第一層語言。

| 卡片                                                                | 核心問題               | 常見出現位置                 |
| ------------------------------------------------------------------- | ---------------------- | ---------------------------- |
| [SaaS](/business/knowledge-cards/saas/)                             | 雲端訂閱軟體的商業模式 | gross margin、PLG、retention |
| [Vertical SaaS](/business/knowledge-cards/vertical-saas/)           | 專做單一行業的 SaaS    | niche、tacit knowledge       |
| [Horizontal SaaS](/business/knowledge-cards/horizontal-saas/)       | 跨行業通用的 SaaS      | distribution、PLG            |
| [CDP](/business/knowledge-cards/cdp/)                               | 客戶資料平台           | 數據整合、應用層 SaaS        |
| [Enterprise License](/business/knowledge-cards/enterprise-license/) | 企業級授權模式         | lock-in、長期合約            |

## 單位經濟

每個客戶或每筆交易的成本與利潤結構。判讀一家公司是否真的賺錢的核心語言。

| 卡片                                                      | 核心問題                 | 常見出現位置            |
| --------------------------------------------------------- | ------------------------ | ----------------------- |
| [COGS](/business/knowledge-cards/cogs/)                   | 賣出產品的直接成本       | gross margin、毛利壓縮  |
| [Gross Margin](/business/knowledge-cards/gross-margin/)   | 毛利率                   | SaaS、AI 公司毛利、估值 |
| [Marginal Cost](/business/knowledge-cards/marginal-cost/) | 多服務一個客戶的邊際成本 | PLG、零邊際複製         |
| [P&L](/business/knowledge-cards/pnl/)                     | 損益表                   | burn rate、估值         |
| [Burn Rate](/business/knowledge-cards/burn-rate/)         | 燒錢速度                 | runway、新創存活        |
| [Runway](/business/knowledge-cards/runway/)               | 現金能撐多久             | burn rate、融資時點     |

## 進入市場

用什麼通路、銷售模式、組織安排把產品賣出去。

| 卡片                                  | 核心問題       | 常見出現位置                |
| ------------------------------------- | -------------- | --------------------------- |
| [GTM](/business/knowledge-cards/gtm/) | 進入市場策略   | PLG、FDE、銷售模式          |
| [PLG](/business/knowledge-cards/plg/) | 產品自助成長   | 低 CAC、SaaS 經典模式       |
| [FDE](/business/knowledge-cards/fde/) | 前線部署工程師 | tacit knowledge、企業客戶   |
| [JV](/business/knowledge-cards/jv/)   | 合資企業       | 進入企業市場、Palantir 模式 |
| [CAC](/business/knowledge-cards/cac/) | 獲客成本       | unit economics、PLG         |

## 競爭護城河

為什麼客戶留下來、為什麼別人打不進來。決定一家公司能否長期擊敗對手。

| 卡片                                                                  | 核心問題                   | 常見出現位置               |
| --------------------------------------------------------------------- | -------------------------- | -------------------------- |
| [Lock-in](/business/knowledge-cards/lock-in/)                         | 客戶離不開的結構           | enterprise license、生態系 |
| [Switching Cost](/business/knowledge-cards/switching-cost/)           | 切換到競爭對手的成本       | lock-in、retention         |
| [Retention](/business/knowledge-cards/retention/)                     | 客戶留存率                 | unit economics、SaaS       |
| [Thin Wrapper](/business/knowledge-cards/thin-wrapper/)               | 只在底層服務外包一層薄殼   | AI 新創、被輾平            |
| [Fat Data / Fat Skill](/business/knowledge-cards/fat-data-fat-skill/) | 有獨家資料或行業隱性能力   | 護城河、生存空間           |
| [Connector](/business/knowledge-cards/connector/)                     | 被收編進生態系變成整合工具 | 整併週期、AI Labs          |

## 市場動態

賽道處在什麼階段、競爭強度、需求類型。判讀一個產業現在能不能進、何時進。

| 卡片                                                                      | 核心問題           | 常見出現位置            |
| ------------------------------------------------------------------------- | ------------------ | ----------------------- |
| [Red Ocean / Blue Ocean](/business/knowledge-cards/red-ocean-blue-ocean/) | 紅海競爭與藍海空白 | 整併週期、賽道判讀      |
| [Consolidation Cycle](/business/knowledge-cards/consolidation-cycle/)     | 整併週期           | M&A、紅海後段           |
| [Niche Market](/business/knowledge-cards/niche-market/)                   | 利基市場           | Vertical SaaS、護城河   |
| [High Stickiness](/business/knowledge-cards/high-stickiness/)             | 高黏著度           | lock-in、SaaS retention |
| [Rigid Demand](/business/knowledge-cards/rigid-demand/)                   | 剛性需求           | 客戶非要不可的訊號      |
| [Frontier Capability](/business/knowledge-cards/frontier-capability/)     | 前沿能力           | AI Labs、領先差距       |
| [Distribution](/business/knowledge-cards/distribution/)                   | 分發優勢           | Big Tech、現有客戶基礎  |

## 資本估值

公司價值怎麼被定價、被誰定價、何時崩塌。

| 卡片                                                                      | 核心問題     | 常見出現位置         |
| ------------------------------------------------------------------------- | ------------ | -------------------- |
| [VC](/business/knowledge-cards/venture-capital/)                          | 創投         | 種子輪、A 輪、估值   |
| [PE](/business/knowledge-cards/private-equity/)                           | 私募基金     | 中型企業、被併購     |
| [Valuation](/business/knowledge-cards/valuation/)                         | 估值         | 融資、退場、毛利     |
| [Valuation Compression](/business/knowledge-cards/valuation-compression/) | 估值壓縮     | 毛利下降、新創生存   |
| [Unit Economics](/business/knowledge-cards/unit-economics/)               | 單位經濟     | LTV/CAC、是否賺錢    |
| [LTV](/business/knowledge-cards/ltv/)                                     | 客戶終身價值 | retention、CAC、毛利 |

## 執行知識

把產品做出來、把客戶服務好的隱性能力。常被低估、卻是 AI 時代差異化的核心。

| 卡片                                                          | 核心問題               | 常見出現位置                  |
| ------------------------------------------------------------- | ---------------------- | ----------------------------- |
| [Tacit Knowledge](/business/knowledge-cards/tacit-knowledge/) | 隱性知識               | FDE、SOP 寫不出來的部分       |
| [Evaluation Set](/business/knowledge-cards/evaluation-set/)   | 評估集                 | AI 產品、tacit knowledge 編碼 |
| [PRD](/business/knowledge-cards/prd/)                         | 產品需求文件           | 傳統 SaaS、wireframe          |
| [Wireframe](/business/knowledge-cards/wireframe/)             | 線框圖                 | PRD、UI 規劃                  |
| [Vibe Code](/business/knowledge-cards/vibe-code/)             | 用 AI 即時生成程式     | FDE、需求迭代                 |
| [Judgment Stake](/business/knowledge-cards/judgment-stake/)   | 判斷的賭注被放大       | AI 取代論、資深角色           |
| [Junior Buffer](/business/knowledge-cards/junior-buffer/)     | 初階員工作為判斷緩衝層 | judgment stake、組織結構      |
