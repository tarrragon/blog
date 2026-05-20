---
title: "FDE 軍備競賽：SaaS 三支柱鬆動下的結構性轉變"
date: 2026-05-19
description: "用 WRAP 框架拆解三家基礎模型供應商同時押 FDE 模式背後的 SaaS 商業前提鬆動，並判讀 FDE 是過渡狀態還是長期結構"
weight: 2
tags: ["business", "case-analysis", "wrap", "fde", "saas", "gtm"]
---

OpenAI 開獨立 DeployCo、Anthropic 跟 Blackstone 與高盛合資、Google 把 FDE 納編進 Cloud—三家最大的基礎模型供應商在 2025-2026 年同時押 [FDE](/business/knowledge-cards/fde/) 模式。這個共識反映的是 [SaaS](/business/knowledge-cards/saas/) 商業模式三個核心前提同時鬆動：邊際成本不再接近零、產品壽命被 AI 迭代壓縮、切換成本因模型 API 標準化下降。本篇拆解三支柱怎麼鬆動、[Vibe Code](/business/knowledge-cards/vibe-code/) 怎麼改寫 FDE [單位經濟](/business/knowledge-cards/unit-economics/)、以及 FDE 是過渡狀態還是長期結構。

## 事件本身

2025-2026 年三家基礎模型供應商在 GTM 上做出方向一致的動作：

- OpenAI 開 140 億美元獨立 DeployCo 派工程師駐點
- Anthropic 跟 Blackstone 做 15 億美元合資、跟高盛合資
- Google 把 FDE 納編進 Cloud 體系

三種組織結構不同、做的事一樣：把工程師塞進客戶辦公室。Palantir 過去獨佔的 FDE 模式現在被多家供應商大規模採用。三家共同的選擇背後是 SaaS 商業模式的三個核心前提同時鬆動—這是本篇主體要拆的結構性原因。

## SaaS 三支柱怎麼鬆動

[SaaS](/business/knowledge-cards/saas/) 過去能跑出極高 [毛利](/business/knowledge-cards/gross-margin/) 跟 [PLG](/business/knowledge-cards/plg/) 自助上手、靠三個前提同時成立。三個前提在 AI 時代各自鬆動、合起來就是 PLG 模式不可行的結構原因。

### 第一支柱：接近零的邊際成本

傳統軟體寫一次賣無數次、多服務一個客戶幾乎沒成本。免費試用、口碑擴散、產品內建分享機制都成本可控。

AI 時代鬆動：每次推論都耗實際算力。[COGS](/business/knowledge-cards/cogs/) 從 20% 推到 40-50%、[毛利](/business/knowledge-cards/gross-margin/) 從 70-80% 掉到 50% 出頭。30 個百分點的毛利缺口已超出定價策略可吸收的範圍。

毛利結構性下移後、免費試用的單位推論成本直接消耗毛利、難依賴轉換率攤平。[CAC](/business/knowledge-cards/cac/) 上升、獲客需轉為業務面對面接觸。PLG 在這套經濟下難以收斂、必須轉 Sales-led 或 FDE。

### 第二支柱：非短暫性價值

傳統 SaaS 產品壽命長—Salesforce 用了 20 年、Slack 用了 10 年、客戶用越久越熟悉、[切換成本](/business/knowledge-cards/switching-cost/) 跟著累積。

AI 時代鬆動：工具迭代太快、產品壽命被壓縮。AI 模型 6 個月一代、產品介面跟工作流可能隔半年就被新一代功能取代。SaaS 賴以為生的「客戶用了 10 年捨不得換」假設不成立—客戶可能 6 個月就重新評估技術棧。

短壽命意味著：[Retention](/business/knowledge-cards/retention/) 假設不能用傳統數字、[LTV](/business/knowledge-cards/ltv/) 計算更保守。

### 第三支柱:高切換成本

傳統 SaaS：資料、流程、權限、整合都綁定在你這、客戶要換要付巨大代價。

AI 時代鬆動：當使用者是 agent 不是人、軟體的差異化變脆弱、切換成本下降。AI 模型 API 規格越來越標準化、prompt 也可以稍微改一改就跨模型用。當 LLM 應用層的差異化變脆弱、客戶換 backend 的成本變低。

切換成本下降意味著：[Lock-in](/business/knowledge-cards/lock-in/) 沒那麼牢、客戶可能隨時換、SaaS 的高 retention 假設崩。

### 三支柱鬆動的綜合結果

三件事疊起來、傳統 SaaS 的 70-80% 毛利目標跟 AI 產品商 2026 年的 50% 預估之間差距、就是 [估值](/business/knowledge-cards/valuation/) 倍數結構性受壓的根因。三家基礎模型供應商共同放棄 PLG 路徑、改押 FDE / Enterprise License、是這套結構鬆動下的合理 GTM 選擇—不是個別公司的策略偏好、是 unit economics 算式倒推的結論。

## 為什麼必須派人到現場：Tacit Knowledge 萃取

三支柱鬆動只解釋「為什麼不能走 PLG」、不解釋「為什麼必須是 FDE 而不是傳統 Sales-led」。下一塊拼圖是需求探索方法。

傳統 SaaS 開發流程依賴一件事：「需求可以用語言或圖描述清楚」。[PRD](/business/knowledge-cards/prd/) 寫得清楚、[Wireframe](/business/knowledge-cards/wireframe/) 畫得清楚、跑使用者測試、就可以遠端做產品。這流程在 CRM、文件、會議、CI/CD 等功能型軟體都成立。

AI native 應用不一樣。客戶說「我要一個自動處理理賠的 agent」這句話資訊量極低—你必須現場生成第一版、餵真實 case 進去、跟業務人員一起看輸出。然後業務人員會說：「這個 case 處理錯了、因為我們公司的潛規則是某某某」。這層藏在資深員工腦袋裡、寫不進 SOP 的 [Tacit Knowledge](/business/knowledge-cards/tacit-knowledge/)、只有人坐在客戶端才能萃取出來、編碼進該客戶的 [Evaluation Set](/business/knowledge-cards/evaluation-set/)。

這就是 FDE 不只是「重 GTM」、而是結構性被迫的根因。傳統 Sales-led 還能遠端做產品；FDE 必須長駐客戶辦公室。

## Vibe Code 怎麼改變 FDE 經濟學

FDE 模式過去只有 Palantir 玩得起。為什麼？[單位經濟](/business/knowledge-cards/unit-economics/) 算不過來—一個 FDE 工程師一年只能服務 1-2 個大客戶、人力成本扛不起來。除非客戶合約金額大到誇張（政府百億合約），不然 LTV/CAC 算不出 3 倍。

[Vibe Code](/business/knowledge-cards/vibe-code/) 改變了這個。Cursor、Claude Code、Windsurf 把「從需求到可跑原型」週期從幾週壓到幾小時。FDE 在客戶會議室就能 vibe code 出第一版、當場跟業務人員迭代。產能變成過去的 3-5 倍—一個工程師原本一年服務 1-2 個大客戶、現在能服務 5-10 個中型企業。

單位經濟算得過去之後、FDE 模式從「只有 Palantir 玩得起」變成「可以 scale 到幾百個中型企業」。Anthropic 鎖定 [PE](/business/knowledge-cards/private-equity/) 旗下中型企業、背後就是這個轉變—一個 PE 巨頭背後的投資組合公司數量可達 Fortune 500 規模、一次簽進去能拿到幾十家。

## 三家不同押注的世界觀

三家共同押 FDE 模式、但在「AI 商業化最終護城河在哪」這個問題上押注不同：

OpenAI（140 億美元 DeployCo）押 [Frontier 能力](/business/knowledge-cards/frontier-capability/) 差距會繼續拉開—模型能力足以覆蓋大多數行業 know-how 的差異化價值、Tacit Knowledge 萃取的權重會下降。

Anthropic（15 億美元合資）押行業 know-how 比模型能力重要—模型差距會收斂、真正的差異在 [Tacit Knowledge](/business/knowledge-cards/tacit-knowledge/) 萃取深度。

Google（內部 Cloud FDE）押 [分發優勢](/business/knowledge-cards/distribution/) 勝過一切—它有 Cloud、Workspace、Android、既有客戶基礎大、轉化既有客戶比拉新更有效率。

三家押注互斥度高、預期至少有一條會在 5-10 年顯著勝出、但全部成功或全部失敗的機率都不高。差異化押注不影響本篇主論—三家在 FDE / Enterprise GTM 這層共識下做不同的長期賭。

## 長期影響

長期看 5-10 年：

對 AI 商業化整體：FDE 跟 enterprise license 會是這波 AI 進企業的主要 GTM、不會回到 PLG。即使開源模型追上 Frontier、Tacit Knowledge 萃取的需求仍在、所以 FDE 不會消失—但可能會被更便宜的「半 FDE」（遠端 + 短期駐點）取代。

對 SaaS 業者：純軟體輕資產的舊路長期回不來。任何想做 AI 應用的 SaaS 公司、都得學派人駐點、做服務、跟客戶綁深。這是商業模式本質改變、不是暫時轉折。

對 Palantir：過去獨佔 FDE 模式的差異化會被稀釋—因為 vibe code 讓 FDE 可規模化、其他公司也能做。Palantir 的優勢轉到「累積最久的 fat skill + 最深的客戶整合」。

對中型企業：享受到 AI 進企業的好處—過去 FDE 服務不到的中段、現在 Anthropic / OpenAI 開始服務。

## 預警訊號：何時要重新評估這個分析

關鍵假設要監控：

**假設一：AI 推論成本不會崩盤、毛利擠壓持續。** 監控訊號：GPU 價格走勢、新硬體（TPU、自研晶片）的成熟、推論優化技術突破。如果推論成本崩盤、邊際成本回到接近零、PLG 數學重新成立、FDE 模式可能被棄。

**假設二：Tacit Knowledge 萃取的需求不會被工具取代。** 監控訊號：客戶能不能用標準化工具自己編碼 evaluation set 而不用 FDE。如果工具夠成熟、FDE 從「結構性被迫」回到「可選 GTM」。

**假設三：三家押注勝出可預測。** 機會成本：選錯邊（押 Frontier 但行業 know-how 勝、押 distribution 但 Frontier 勝）會有大量沉沒成本。

下面任一具體訊號出現、要重新評估這套分析：

| 訊號                                                                  | 觸發的修正方向                                 |
| --------------------------------------------------------------------- | ---------------------------------------------- |
| 主要基礎模型供應商一年內大規模裁 FDE 團隊                             | FDE 模式不可持續、要轉回 PLG 或 Sales-led      |
| 標準化 evaluation set 工具讓客戶自助編碼 Tacit Knowledge              | FDE 從結構性被迫變回可選 GTM                   |
| 開源模型 + 開源 tooling 在多數 enterprise use case 上跟 Frontier 持平 | Lock-in 鬆動、enterprise license 的 LTV 假設崩 |
| 推論成本崩盤（例如 GPU 價格 1/10 以下）                               | 第一支柱重新成立、SaaS 老路有機會回來          |

## FDE 是過渡還是長期結構

回到開放問題：FDE 是過渡狀態還是長期結構？目前沒有答案、但兩種劇本對應完全不同的戰略意涵。

**如果是過渡狀態**：派人駐點只是因為產品還不夠成熟、等 AI 更強、工具更標準化、還是會回到 SaaS 低成本獲客模式。中期 SaaS 老路會復活、現有 PLG 工具有機會回來。對純軟體業者來說是「忍幾年回到老日子」。

**如果是長期結構**：AI 商業化本質上就是要貼著客戶做、SaaS 那套輕資產打法永遠回不來。整個軟體業形態被改寫。對純軟體業者來說是「商業模式本質改變、要學會做服務」。

兩種劇本的判讀分水嶺：Tacit Knowledge 萃取能不能被工具標準化。能標準化、FDE 是過渡；不能標準化、FDE 是長期。兩種劇本目前都有持續訊號、無法給出可靠判斷—建議每 6-12 個月重新評估、看哪個劇本的訊號更強。

## 判讀框架

| 判讀對象      | 看什麼                                                                                                                                        | 主要訊號                                  |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 新創 GTM 選擇 | 是 [PLG](/business/knowledge-cards/plg/) 還是 [FDE](/business/knowledge-cards/fde/) / Sales-led                                               | 自助註冊 vs Contact Sales、業務工程師比例 |
| 賽道毛利結構  | [COGS](/business/knowledge-cards/cogs/) 是否接近零                                                                                            | 推論成本佔比、有沒有自有模型減 token 費   |
| FDE 單位經濟  | 一個 FDE 一年能服務幾個客戶                                                                                                                   | 標準化工具是否成熟、客製化程度            |
| 三家押注勝出  | [Frontier](/business/knowledge-cards/frontier-capability/) / 行業 know-how / [Distribution](/business/knowledge-cards/distribution/) 哪個顯效 | 模型 benchmark 收斂速度、客戶留存差距     |

這個框架不只用在 AI 議題—當任何新興行業面對「自助上手 vs 高接觸服務」的 GTM 選擇時、都可以套這個三支柱問：邊際成本、產品壽命、切換成本三者是否成立？

## 延伸閱讀

- [Claude for Legal 之後：應用層、新創、知識工作者的三層擠壓](/business/case-analyses/claude-for-legal/) — 拆 vertical SaaS 與知識工作者衝擊
- [CoreWeave 收購 Bufstream：整併週期下的賽道判讀](/business/case-analyses/bufstream-acquisition/) — AI 基礎設施重組
- [FDE](/business/knowledge-cards/fde/)、[PLG](/business/knowledge-cards/plg/)、[Tacit Knowledge](/business/knowledge-cards/tacit-knowledge/) 卡片
