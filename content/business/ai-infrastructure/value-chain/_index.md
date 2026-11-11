---
title: "AI 大廠的垂直產業鏈與本業以外的業務"
breadcrumb: "垂直產業鏈"
date: 2026-11-12
description: "比較 Nvidia、AMD、Broadcom、TSMC、Micron、伺服器組裝廠與資料中心業者這些算力價值鏈各環節的利益率與資本密集度，或比較 Google、Microsoft、Amazon、Meta、Nvidia、Oracle 自製、租用與外購哪些環節、本業以外的業務在財報上的位置時，從這裡找對應的文章"
weight: 10
tags: ["business", "ai-infrastructure", "vertical-integration", "value-chain"]
---

本章節以算力價值鏈的環節為單位，比較六家 AI 大廠各自涵蓋了哪些環節、哪些外購，以及本業以外延伸了哪些業務。寫法比照財務分析模組裡的[台灣雞肉供應鏈三大廠商比較](/business/financial-analysis/chicken-supply-chain-comparison/)與[正大集團的垂直整合](/business/financial-analysis/case-studies/cp-group-vertical-integration/)：先建立各環節的經濟特性當比較基準，再看每一家選擇的涵蓋段與它在財報上的呈現。

跟上一層 [AI 基礎設施的產業鏈](/business/ai-infrastructure/) 的分工在分析單位：上一層的文章以一筆橫跨幾家公司的交易為單位（供應商融資的形態、Anthropic 與 OpenAI 的算力融資），本章節以一家公司為單位，看它在價值鏈上的位置。兩邊會用到同一批交易（Nvidia 的擔保、雲端業者對模型公司的持股），本章節只寫這些交易怎麼反映一家公司的涵蓋段，交易的結構連到上一層。Meta 與基金合資的資料中心（Hyperion）上一層還沒有分析，記在下面的 Backlog。

## 章節

| 文章                                                                                                        | 這一篇比較的內容                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [AI 算力價值鏈各環節的經濟特性](/business/ai-infrastructure/value-chain/ai-value-chain-segment-economics/)  | 加速器設計、晶圓代工與封裝、HBM、伺服器組裝、網通、電力設備、資料中心與 neocloud 各環節代表業者的營業利益率、毛利率、資本支出佔營收比、客戶集中度與交期                   |
| [AI 大廠在算力價值鏈上自製與外購的環節](/business/ai-infrastructure/value-chain/big-tech-value-chain-span/) | Google、Microsoft、Amazon、Meta、Nvidia、Oracle 在各環節的位置、各家選擇的理由，以及資本支出佔營收、分部利益率、伺服器耐用年限與尚未開始的租約的比較                      |
| [AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)              | Other Bets、Reality Labs、Amazon Leo、Microsoft 的 Xbox、LinkedIn 與搜尋廣告、Oracle Health、電力的取得方式、對模型公司的持股與入帳方式，以及持有方對同一個對象的合計曝險 |

## 寫這個章節的文章時

- **數字以申報文件為準**，規則同上一層目錄頁的〈寫這個模組的文章時〉：10-K、10-Q 與 8-K 是第一手，法說會的說法標出是誰在哪一天說的，媒體數字寫出媒體名與是否已簽定。
- **各家會計年度不同**：Microsoft 截至 6 月 30 日、Oracle 截至 5 月 31 日、Nvidia 截至 1 月底，其餘是日曆年。同一張表裡並排時，每一格寫出期間。
- **分部的範圍各家不同**：Google Cloud 不分攤模型研發、Oracle 的分部只扣直接成本、Microsoft 2027 會計年度起改了分部。跨公司比較分部利益率之前，先寫出各家分部包含什麼。
- **自製晶片的資訊多半不在申報文件裡**：TPU、Trainium、Maia、MTIA 的規模與設計夥伴，多數來自公司新聞稿、合作方的 8-K 或媒體報導，寫出是哪一種來源。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                                                                                   | 類型   | 前置條件                                          | 規模         |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------- | ------------ |
| Nvidia 截至 2026-10-25 的季報發布後更新：供應與產能承諾、AI cloud agreements、擔保與權益證券的金額，以及三篇文章裡用到 2026-07-26 數字的位置                                                                                                                                                                           | 主章   | Nvidia 截至 2026-10-25 的 10-Q 發布（2026-11-17） | 小           |
| Meta 的合資資料中心（Louisiana Venture／Hyperion、Texas Venture）：合資實體的出資比例、承租方殘值擔保的觸發條件、不併表的判斷依據，以及跟賣方擔保的對照                                                                                                                                                                | 主章   | 無                                                | 中           |
| Nvidia 承租雲端算力（cloud service agreements）與 AI cloud agreements 的合約結構與會計處理，跟未售產能承購的異同                                                                                                                                                                                                       | 主章   | Nvidia 截至 2026-10-25 的 10-Q 發布（2026-11-17） | 小           |
| 殘值擔保卡補上承租方擔保自己承租場地的情形（Meta Hyperion）                                                                                                                                                                                                                                                            | 知識卡 | 無                                                | 小           |
| 建卡：權益法（equity method，含 HLBV 變體）、分部報告（segment reporting，含分部範圍由管理層決定、重編前期）、表外安排（off-balance-sheet arrangement，含尚未開始的租約、擔保、未併表的合資）；三篇第一次出現的位置改連卡                                                                                              | 知識卡 | 無                                                | 3 張卡（中） |
| 既有文章補連到本章節：ai-era-earnings-quality 的資本支出比表（申報口徑差別）與公允價值段（measurement alternative）、memory-market-shortage-analysis 的利潤反轉段、capacity-expansion-cycle 的 CoWoS 段、wafer-foundry 卡與 odm 卡、depreciation-amortization 卡的耐用年限實例、正大集團與雞肉比較兩篇的垂直整合結論段 | 跨模組 | 無                                                | 小           |
| 自製加速器的經濟帳：用 Broadcom 的 AI 營收、各家揭露的自製晶片用量與 GPU 採購，估算自製一顆加速器相對外購省下的毛利，以及設計固定成本要多少用量才攤得掉                                                                                                                                                                | 主章   | 需取得 Broadcom 依客戶或產品別的 AI 營收揭露      | 中           |
| 持有對象上市之後的入帳變化：Anthropic 上市後 Amazon、Alphabet 的持股是否改依市價評價、無投票權類別股能否視為有市價、轉換當季認列的差額，更新本業以外的業務那一篇的持股節與合計曝險表                                                                                                                                   | 主章   | Anthropic 上市後 Amazon 與 Alphabet 的第一份 10-Q | 小           |
| 各家雲端分部的成本分攤對齊：Google Cloud、AWS、Microsoft Agents and Infra 各自分攤模型研發、共用基礎設施與折舊的方式，整理成可以並排的口徑                                                                                                                                                                             | 主章   | 無                                                | 中           |
