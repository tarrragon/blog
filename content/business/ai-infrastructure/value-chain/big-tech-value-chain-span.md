---
title: "AI 大廠在算力價值鏈上自製與外購的環節：Google、Microsoft、Amazon、Meta、Nvidia、Oracle 的涵蓋段與財報呈現"
date: 2026-11-12
description: "Google、Microsoft、Amazon、Meta、Nvidia、Oracle 在加速器設計、伺服器與網通、資料中心與供電、雲端、模型與應用各環節自製、委外設計、租用或外購的選擇，TPU、Trainium、Maia、MTIA 這些自製晶片的用途與對外銷售，以及這些選擇在分部損益、資本支出佔營收比、伺服器耐用年限與尚未開始的租約上的呈現"
weight: 2
tags: ["business", "ai-infrastructure", "vertical-integration", "value-chain", "financial-analysis"]
---

這篇比較六家 AI 大廠在算力價值鏈上各自涵蓋了哪些環節：Google、Microsoft、Amazon、Meta 同時是算力的買方與使用者，Nvidia 是加速器的賣方，Oracle 在算力上只經營雲端、不自製晶片。內容依序是一家公司涵蓋一個環節的幾種方式、六家的對照表、每一家的選擇與它在申報文件裡留下的證據，接著整理這些選擇出現在財報的哪些位置（資本支出佔營收比、分部營業利益率、伺服器耐用年限、尚未開始的租約），最後比較自製加速器、對外賣算力、資料中心與算力的取得、持有模型公司的股權與只做設計這幾種選擇各自成立的條件與帳上的後果。各環節本身的利益率、資本密集度與客戶集中度，由[AI 算力價值鏈各環節的經濟特性](/business/ai-infrastructure/value-chain/ai-value-chain-segment-economics/)用代表業者的數字建立；各家在本業以外延伸的業務（Waymo、Reality Labs、Amazon Leo、遊戲與 LinkedIn、Oracle Health、電力的取得方式，以及對模型公司的持股）由[AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)逐類比較。文中的申報文件是美國上市公司向證券交易委員會提交的：10-K 是年報，10-Q 是季報，8-K 是重大事件發生後的即時報告。Google 的申報主體是母公司 Alphabet，談財報數字時寫 Alphabet。各家數字取自最新一份 10-K 與最新一季 10-Q；Nvidia 截至 2026-10-25 的季報預計在 2026-11-17 發布，本文用截至 2026-07-26 的那一季，其餘各家用截至 2026 年 8 月或 9 月的那一季。算力合約常以 GW（十億瓦）計規模，因為資料中心能裝多少加速器，受限於它能供給多少電力。

## 一家公司涵蓋一個環節的幾種方式

算力價值鏈從上游到下游依序是加速器與晶片設計、晶圓代工與先進封裝、HBM（高頻寬記憶體）、伺服器與網通設備、資料中心與供電、雲端（把算力租給外部客戶）、模型、應用。這個切法比[AI 算力價值鏈各環節的經濟特性](/business/ai-infrastructure/value-chain/ai-value-chain-segment-economics/)粗：那一篇把伺服器組裝與網通分開、把電力設備與資料中心分開，是因為它比較各環節業者的利益率；本篇看一家公司在每一段做了什麼，伺服器與網通、資料中心與供電各合成一欄，算力租賃業者（neocloud）屬於本篇的雲端那一段。一家公司在一個環節上的位置分成下列幾種：

- **自有**：自己設計、自己擁有資產並營運，例如自建自營的資料中心。
- **自有設計、委外製造**：設計是自己的，製造交給代工廠或組裝廠。Nvidia 的 GPU、Google 的 TPU，以及 Meta、Microsoft 自己設計再交給 ODM 生產的伺服器，都屬於這一種。
- **租用**：資產屬於別人，自己簽長期合約取得使用權，例如向開發商租資料中心、向 neocloud 租 GPU 算力。
- **外購**：買別家的產品，例如雲端業者向 Nvidia 買 GPU。

[價值鏈涵蓋段](/business/knowledge-cards/value-chain-span/)指一家公司自己做了哪幾個環節，[垂直整合](/business/knowledge-cards/vertical-integration/)指把相鄰環節收進自己組織的選擇。在農食產業，涵蓋的段越多、同一單位產品累積的加價越多，利益率越高：[正大集團的垂直整合](/business/financial-analysis/case-studies/cp-group-vertical-integration/)從飼料、養殖做到零售，[台灣雞肉供應鏈三大廠商比較](/business/financial-analysis/chicken-supply-chain-comparison/)對照了卜蜂與超秦兩種往下游整合的做法。這個推論在算力鏈不成立：只做設計的 Nvidia 利益率最高，往利益率低的組裝延伸反而拉低整體利益率，每一段的利益率要看那一段本身的成本結構，分組列在[AI 算力價值鏈各環節的經濟特性](/business/ai-infrastructure/value-chain/ai-value-chain-segment-economics/)〈依成本結構分組：兩個比率是各組的觀察值〉。套到算力產業時也要多分一層：自有設計、委外製造也算涵蓋了設計那一個環節，因為設計決定了晶片的效能與成本。

晶圓代工、先進封裝與 HBM 三個環節，本文的六家公司都沒有自己營運：自製加速器的公司把晶片交給代工廠製造，Oracle 與其他公司向 Nvidia、AMD 買 GPU，代工與 HBM 已經包在 GPU 的價格裡。Nvidia 在 10-K 寫明晶圓由 TSMC 與 Samsung 代工、記憶體向 SK Hynix、Micron 與 Samsung 採購、封裝用 CoWoS 技術，並寫明「We do not assemble, test, or package our products」；Microsoft 官方寫 Maia 200 用 TSMC 3 奈米製造。這三個環節的資本支出規模與製程技術由少數業者掌握，下面的對照表不再列出這三欄。

## Google、Microsoft、Amazon、Meta、Nvidia、Oracle 各自涵蓋的環節

| 公司      | 加速器設計                                                                                       | 伺服器與網通                                                                                       | 資料中心與供電                                                                                   | 雲端（對外賣算力）                                | 模型                                                  | 應用                                 |
| --------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------- | ----------------------------------------------------- | ------------------------------------ |
| Google    | 自有設計 TPU，由 Broadcom 開發與供貨；另向雲端客戶提供 GPU                                       | 網通元件由 Broadcom 依供貨保證協議供應到 2031 年                                                   | 自建加租用；收購再生能源開發商 Intersect                                                         | Google Cloud，另外把 TPU 系統賣給客戶自建機房使用 | Gemini                                                | Search、YouTube、Gemini app          |
| Microsoft | Maia、Cobalt 自有設計，同時外購 Nvidia 與 AMD                                                    | 通用伺服器自有設計（公開於 Open Compute Project），委外 ODM 製造；GPU 整櫃以 Nvidia 的參考設計為底 | 自建、租用，另向 neocloud 租 GPU 算力                                                            | Azure                                             | 持有 OpenAI 股權，並取得 OpenAI 模型的 IP 權利到 2032 | Microsoft 365 Copilot 等             |
| Amazon    | Trainium、Graviton 自有設計（GPU 採購的規模申報文件沒有揭露）                                    | 申報文件沒有揭露伺服器是自製還是外購                                                               | 自建加租用；與 Talen 簽核電購電                                                                  | AWS                                               | Nova；持有 Anthropic 與 OpenAI 的股權                 | 零售、廣告                           |
| Meta      | MTIA 與 Broadcom 共同開發，用於推薦與排序的推論；同時外購 Nvidia；AMD 與 Google TPU 只有媒體報導 | 通用伺服器與部分 AI 機櫃自有設計（公開於 Open Compute Project），委外 ODM 製造                     | 自建、租用，加上與基金合資的資料中心；另向第三方雲端承諾採購算力                                 | 沒有，算力全部自用                                | Llama（開放權重）、Muse                               | Facebook、Instagram、WhatsApp 與廣告 |
| Nvidia    | GPU、CPU、網通晶片自有設計                                                                       | 整櫃系統自有設計，組裝委外給鴻海（Hon Hai）、緯創（Wistron）等                                     | 承租自用資料中心；俄亥俄州一座園區由 OpenAI 關係企業承租，Nvidia 向出租方 SB Energy 提供殘值擔保 | 不對外經營雲端；承租雲端算力供自家研發使用        | Nemotron 等自研模型，用於研發                         | 沒有                                 |
| Oracle    | 沒有自製加速器，外購 Nvidia 與 AMD                                                               | 外購                                                                                               | 以長期租賃為主，場址由開發商以專案融資興建                                                       | OCI                                               | 沒有                                                  | 資料庫、應用軟體、Oracle Health      |

加速器、伺服器、資料中心與雲端各欄的出處寫在下面各家的段落；Meta 與 Microsoft 的伺服器那兩格依兩家在 Open Compute Project（Meta 在 2011 年發起的開放硬體規格組織）公開的伺服器設計；電力那幾格（Intersect、Talen）的出處寫在[AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)〈往上游延伸的電力：購電合約、投資與收購〉；模型與應用欄是各家公開的產品名。專案融資指銀行以這座資料中心本身的現金流與資產為償還來源放款，借款人通常是為這個場址成立的公司。表格只標出各家在每個環節的位置，同一格「外購」的公司，外購的規模與合約形式差很多，比較時要讀各家的段落。

## Google：TPU 的設計與對外銷售、Google Cloud、Gemini 與應用

Google 是本文比較的大廠裡涵蓋環節最多的兩家之一（另一家是 Amazon；依上表，Google 多出的是收購電力開發商與對外銷售加速器）：TPU 由 Google 自有設計，2026-04-06 Broadcom 的 8-K 揭露雙方簽了長期協議，由 Broadcom 為 Google 未來幾代 TPU 開發與供貨，另簽供貨保證協議，網通元件供應到 2031 年。Alphabet 的 10-K 寫自家同時提供第七代 TPU（Ironwood）與 GPU 給雲端客戶。

Google 的 TPU 已經從自用延伸成對外銷售的產品，對外有兩條管道。一條直接由 Google 銷售：截至 2026-09-30 的 10-Q 寫明 Google Cloud 的產品營收「primarily from the sale of TPU systems」（主要來自 TPU 系統的銷售），並揭露 Google 跟少數需要自建機房（on-premises）的客戶簽了 TPU 系統的供貨合約，客戶沒有點名，2026 年第二季開始認列，大部分營收要到 2027 年認列；部分合約附有 Google 回購 TPU 的保證，最大潛在支付 66 億美元。另一條經由 Broadcom：Broadcom 同一份 8-K 寫，Anthropic 從 2027 年起經由 Broadcom 取得約 3.5 GW、以 TPU 為基礎的算力，也就是 Broadcom 把它開發的 TPU 系統供應給 Anthropic；這一條如果有營收進到 Alphabet，記在哪一行、金額多少，Alphabet 的申報文件沒有揭露。TPU 機櫃租給 Anthropic 時，違約後機櫃能賣給誰、Google 作為最可能的買家要看哪些條件，在[Anthropic 的算力融資結構〈擔保品：TPU 機櫃在第五年的價值〉](/business/ai-infrastructure/anthropic-compute-financing/)推論，那一篇討論的合約跟 Google 的回購保證是不同的合約。媒體另外報導 Meta 簽了多年期租用 Google TPU 的合約（The Information 與 Reuters，2026-02-27，金額為數十億美元），雙方都沒有評論，也沒有官方公告；Apple 用 Google 的 Cloud TPU（TPU v4 與 v5p）訓練自家模型，寫在 Apple 2024 年 7 月發表的技術報告《Apple Intelligence Foundation Language Models》。

自製加速器在 Google 划算的條件，是 TPU 的用量夠大、而且跑在 Google 自己控制的軟體堆疊上：Search、YouTube 與 Gemini 的工作負載由 Google 自己編譯與部署，設計晶片的固定成本分攤在這些工作負載上，換掉的是向 GPU 供應商支付的利潤。對外銷售 TPU 系統再把設計成本分攤到外部客戶身上（本文依 Google 的工作負載推論，申報文件沒有寫自製的理由）。

Google Cloud 分部的營業利益率從 2025 年第三季的 23.7% 升到 2026 年第三季的 36.2%（營業利益 111.21 億美元／營收 307.09 億美元），同期營收翻倍。這段上升混了幾個因素：2026 年第二季才開始認列的 TPU 系統銷售改變了營收組合，而這類硬體銷售的認列時點依交貨而定；不分攤給分部的 Alphabet-level activities 同期從負 44.67 億擴大到負 76.55 億，10-K 寫這一項「主要是共用的 AI 研發」，也就是模型研發的成本不在 Google Cloud 分部裡。這幾個因素各自的影響，申報文件拆不出來，所以這段上升不能直接外推成往後的利益率。Amazon 的申報文件沒有寫出 AWS 分部是否分攤模型研發，所以 Google Cloud 與 AWS 利益率的差距裡，可能含有分攤口徑的差別。

## Microsoft：Azure、Maia 與外購的 GPU、OpenAI 的模型授權

Microsoft 的涵蓋段集中在雲端與應用，伺服器則自己設計、委外製造。它有自有設計的晶片：2026-01-26 官方發表推論加速器 Maia 200，雲端用的 Cobalt 是 CPU；10-K 只寫「custom-built silicon and strong partnerships with chip manufacturers」，沒有寫出 Maia 的部署規模，而執行長 Nadella 在 2026-10-28 法說會的說法是「We continue to scale our fleet with the latest innovations from NVIDIA and AMD alongside our own Maia systems」（我們持續用 Nvidia 與 AMD 的新產品，加上自家的 Maia 系統擴充機群）。Microsoft 也向 neocloud 租 GPU 算力；依 Nebius 的 6-K、IREN 的 8-K 與 Nscale 的 S-1（經 FourWeekMBA 彙整，本文沒有讀原文），Nebius 的合約約 174 億美元、Microsoft 加購服務後最多約 194 億，IREN 約 97 億，Nscale 最多約 438 億，Microsoft 自己的申報文件沒有逐家金額，只寫依賴「colocation facilities, leased datacenters, and cloud infrastructure providers」。

模型這一個環節，Microsoft 主要經由 OpenAI 取得。2025-10-28 重組時公布的條款寫，Microsoft 取得 OpenAI 模型與產品的 IP 權利到 2032 年，並保有 OpenAI 資料中心硬體與軟體的 IP 權利。持股比例有兩個數字：重組公告寫約 27%，口徑是[完全稀釋](/business/knowledge-cards/dilution/)（把員工選擇權與其他可轉換的權利都假設轉成股份之後計算）；Microsoft 截至 2026-09-30 的 10-Q 寫約 24%，口徑是 as-converted（把各類特別股轉成普通股之後計算）。兩者納入分母的權利不同，申報文件沒有寫兩者之間的調節。OpenAI 同時是 Azure 的大客戶：Microsoft 2026 會計年度（截至 2026-06-30）向 OpenAI 認列的營收是 241 億美元，佔全年營收 3,318.39 億美元的 7.3%；重組時 OpenAI 另外承諾加購 2,500 億美元的 Azure 服務。OpenAI 對 Microsoft 的承諾與股權結構，拆解在[OpenAI 的算力融資結構〈Microsoft：股權與 Azure 算力合約〉](/business/ai-infrastructure/openai-compute-financing/)。

Microsoft 同時外購 GPU 的理由，本文從它的客戶結構推論：Azure 的外部客戶多半要在 Nvidia 的 CUDA 軟體堆疊上跑既有的模型與工具，而 Maia 200 是推論加速器，用在 Microsoft 自己部署的推論工作負載（官方公告寫它跑 OpenAI 的 GPT-5.2，Microsoft 對 OpenAI 的模型有 IP 權利），這些工作負載的軟體由 Microsoft 控制。同一段期間 Microsoft Cloud 的毛利率從 2025 會計年度的 69% 降到 2026 會計年度的 66%，管理層預估 2027 會計年度第二季約 65%；同期折舊費用從 220 億美元增加到 343 億。毛利率下降跟資本支出擴大帶來的折舊、AI 營收組合與外購 GPU 的價格都有關，各自佔多少申報文件沒有拆分，跟外購 GPU 的連結是本文的推論。財務長 Hood 在 2026-10-28 法說會說當季資本支出約四分之三是 CPU 與 GPU 這類短年限資產。

Microsoft 從 2027 會計年度第一季起把分部改成 Agents and Infra 與 Devices and Consumer 兩個，並以 2026-10-28 的 8-K 重編前一年的數字；2027 會計年度第一季 Agents and Infra 的營業利益率是 52.8%。Azure 與 Microsoft 365 都在 Agents and Infra 裡，LinkedIn 被拆開、其中一部分也併了進來。雲端基礎設施自己的利益率因此從分部數字看不出來，只剩 Microsoft Cloud 毛利率這個公司自訂的指標。

## Amazon：Trainium、AWS 與對 Anthropic、OpenAI 的持股

Amazon 涵蓋加速器設計、資料中心、雲端與應用，並經由股權連到模型。AWS 的 Trainium（訓練與推論加速器）與 Graviton（CPU）由旗下的 Annapurna Labs 設計；2026-02-05 的財報新聞稿寫兩者合計年化營收超過 100 億美元、以三位數百分比成長，Trainium2 累計交付 140 萬顆，Project Rainier 叢集用超過 50 萬顆 Trainium2 讓 Anthropic 訓練 Claude。設計夥伴是 Marvell 與 Alchip、由 TSMC 製造，這一點只有 TrendForce 等研究機構與媒體的報導，AWS 沒有證實。Amazon 的 10-K 與 10-Q 都沒有出現 Trainium 這個字，也沒有寫自製晶片的理由。

Amazon 的投資與 AWS 的算力合約寫在同一組交易裡。依 Amazon 截至 2026-09-30 的 10-Q，Amazon 在 2023 年第三季到 2025 年第四季累計投入 Anthropic [可轉換本票](/business/knowledge-cards/convertible-note/) 80 億美元（其中一部分已轉成特別股），2026 年前九個月再投入 Anthropic 無投票權特別股 100 億、OpenAI 特別股 500 億。同一段期間，AWS 跟 Anthropic 宣布把既有的多年期合作與承諾擴大超過 1,000 億美元、為期 10 年，跟 OpenAI 的既有承諾 380 億在第一季再擴大 1,000 億、為期 8 年。10-Q 的寫法是雙方擴大合作與承諾，沒有寫出付款方向；兩家模型公司在這些合約裡購買 AWS 的算力，本文因此把它們讀成模型公司對 AWS 的採購承諾。10-Q 另外寫跟 Anthropic 的合約「includes contractual obligations related to the performance of AWS chips」（包含跟 AWS 晶片效能有關的合約義務），10-Q 用的詞是 AWS chips，範圍可能不只 Trainium。這個結構讓 Trainium 有了用量大、又綁著股權的客戶，自製晶片的設計成本有地方分攤，代價是 AWS 自家晶片的效能寫進了對大客戶的合約義務（本文依交易結構推論 Amazon 自製的理由）。持股在 Amazon 帳上怎麼入帳，比較在[AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)〈對算力交易對手的持股：入帳方式與損益出現的位置〉。

AWS 分部的營業利益率從 2025 年第三季的 34.6% 升到 2026 年第三季的 38.7%。Amazon 在 2025-01-01 把一部分伺服器與網通設備的耐用年限從 6 年縮短為 5 年，2025 年的折舊因此增加 14 億美元、主要記在 AWS；同一段期間 Meta 把耐用年限延長，兩家的方向相反，各家年限的比較列在〈涵蓋段的選擇在財報上出現的位置〉。

## Meta：MTIA、自用的資料中心、合資園區與第三方雲端承諾

Meta 在算力價值鏈上的位置跟 Google、Microsoft、Amazon 不同：它沒有把算力賣給外部客戶的雲端業務，資料中心與加速器的成本全部要靠 Family of Apps 的廣告營收回收。加速器方面，Meta 2026-04-14 公告與 Broadcom 擴大合作、共同開發多代 MTIA，初期部署超過 1 GW；Meta 在 2023、2024 年發表 MTIA 時說明的用途是推薦與排序模型的推論。同時，Meta 2026-02-17 公告跟 Nvidia 簽長期合作（Vera Rubin 叢集與 Spectrum-X 網通），AMD 最多 6 GW、為期 5 年的合約與租用 Google TPU 的合約則只有媒體報導（AMD 那一筆的出處是 2026 年 2 月的媒體轉述，本文沒有讀到 AMD 的公告原文）。Meta 的 10-K 與 10-Q 沒有出現 MTIA，也沒有點名任何晶片供應商。依 MTIA 公開的用途，Meta 的分工可以讀成推論用自製晶片、訓練以 Nvidia 為主（本文推論，Meta 沒有公開說明這個分工）。

Meta 取得算力的方式比 Google、Microsoft、Amazon 多一種：向第三方雲端承諾採購。截至 2026-09-30，Meta 的不可取消承諾 4,545.2 億美元，主要是第三方雲端算力、伺服器、能源服務與 Reality Labs 的硬體（2025 年底是 1,310.5 億）；尚未開始的租約另外揭露，3,557.3 億美元，不在這筆承諾裡。資料中心還有一種不進 Meta 資產負債表的取得方式：Meta 跟基金合資成立的 Louisiana Venture（Hyperion 園區），Meta 持股 20%、以權益法（equity method）入帳（只認列持股比例的損益，不把合資公司的資產與負債併進自己的報表），開發成本約 270 億美元由各方依持股比例分攤。Meta 是這座園區的承租方，同時向合資公司（出租方）擔保租約結束時園區的殘值；10-K 揭露最大損失曝險 459.5 億美元。這個安排跟[殘值擔保](/business/knowledge-cards/residual-value-guarantee/)卡寫的機制相同，差別在擔保方：卡與[AI 算力交易裡的供應商融資形態](/business/ai-infrastructure/vendor-financing-forms/)寫的是賣方或第三方替出租方擔保，這裡是承租方擔保自己承租的場地。

Meta 2026 年第三季的資本支出（現金流量表的 purchases of property and equipment）是營收的 52.5%，在 Alphabet、Microsoft、Amazon、Meta 裡最高；cost of revenue 佔營收比從 2025 年第三季的 18.0% 升到 20.7%。Meta 在 2025-01-01 把多數伺服器與網通資產的耐用年限延長到 5.5 年，2025 年的折舊因此減少 29.2 億美元。

## Nvidia：晶片與整櫃系統的設計、委外的製造、下游的承諾與擔保

Nvidia 涵蓋的環節是設計：GPU、CPU、網通晶片，以及把這些組成整櫃系統的設計。10-K 寫產品「typically delivered to customers as rack-scale systems, subsystems, or modules」（通常以整櫃系統、子系統或模組交給客戶），組裝、測試與封裝委外給鴻海、緯創與 Fabrinet。網通是 Nvidia 往系統擴張的那一塊：2026 會計年度（截至 2026-01-25）資料中心網通營收 313.76 億美元、年增 142%，10-K 寫成長來自 GB200 與 GB300 系統（Nvidia 的整櫃產品）的 NVLink（GPU 之間的互連），以及 Ethernet 與 InfiniBand 平台。

製造全部委外，讓 Nvidia 的資本支出很低：2026 會計年度購置不動產、設備與無形資產的支出 60.42 億美元，是營收 2,159.38 億美元的 2.8%。Nvidia 對上游的投入改以採購承諾的形式出現：截至 2026-07-26 的供應與產能承諾 2,790 億美元（前一季 1,190 億），10-Q 寫「primarily memory and manufacturing facilities」，金額比它一整年的營收還多，所以資本支出低不代表 Nvidia 投入上游的資金少。

Nvidia 往下游延伸時，用承諾、擔保與股權代替自建資產。截至 2026-07-26 的 10-Q 揭露三類：Nvidia 承租雲端算力、供自家開放模型研發的承諾 290 億美元；一類 AI cloud agreements 360 億美元，是 AI 雲端業者向 Nvidia 買設備、Nvidia 再承諾向它們購買雲端服務；以及 OpenAI 關係企業承租的俄亥俄州園區，Nvidia 向出租方 SB Energy 提供的擔保，上限 1,050 億美元。這三類跟表裡「自用資料中心 250 億美元」的租約是不同的項目：250 億是 Nvidia 自己要用、還沒開始的資料中心租約。SB Energy 那一筆屬於殘值擔保，形態與 Nvidia 承擔的風險比較在[AI 算力交易裡的供應商融資形態〈殘值擔保：賣方替出租方承擔資產價值〉](/business/ai-infrastructure/vendor-financing-forms/)；AI cloud agreements 讓 Nvidia 在雲端業者的產能賣不出去時成為買家，跟同一篇〈未售產能承購：賣方當最後的買家〉的結構相近（本文依 10-Q 的描述推論）。Nvidia 的股權投資列在[AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)的持股表。

Compute & Networking 分部 2026 會計年度的營業利益率是 67.3%，最近一季（截至 2026-07-26）是 71.0%；這個分部不含[股份基礎薪酬](/business/knowledge-cards/share-based-compensation/)與併購相關費用。依美國一般公認會計原則（GAAP）計算的全公司毛利率，2026 會計年度全年是 71.1%，含第一季一筆跟 H20 晶片出口限制有關的 45 億美元費用，10-K 寫的另一個成因是產品從 Hopper 轉到 Blackwell 整櫃方案；最近四季（2026 會計年度第三季到 2027 會計年度第二季）在 73.4% 到 75.0% 之間，所以年度與季度的差距有一部分來自這筆一次性費用。營收集中在少數客戶：截至 2026-07-26 的半年有三家直接客戶各佔 16%、15%、13%，申報文件沒有點名。

## Oracle：OCI、租賃的資料中心、客戶預付與舉債

Oracle 的硬體環節全部外購：沒有自製加速器（它原本持有的 CPU 設計公司 Ampere 股權已經出售），GPU 向 Nvidia 與 AMD 採購，資料中心以長期租賃為主。截至 2026-08-31 的剩餘履約義務（[RPO](/business/knowledge-cards/remaining-performance-obligation/)，已簽約、還沒認列的營收）6,640 億美元，其中約 13% 預計在 12 個月內認列；Microsoft 截至 2026-09-30 的商業 RPO 約 6,770 億，Oracle 的雲端合約規模跟它在同一個量級。Oracle 的申報文件沒有點名客戶，只寫部分 OCI 產品的客戶集中在少數大客戶；把最大的客戶寫成 OpenAI 的是華爾街日報 2025 年 9 月的報導，Oracle 沒有證實。

Oracle 的資本支出逼近營收，最近一季已經超過：2026 會計年度資本支出 556.63 億美元，是營收 673.57 億的 82.6%；2027 會計年度第一季（截至 2026-08-31）是 284.99 億，超過當季營收 193.45 億。[自由現金流](/business/knowledge-cards/free-cash-flow/)（營業現金流減資本支出）在 2026 會計年度與 2027 會計年度第一季都是負的，2026 會計年度是負 236.86 億。Oracle 另外揭露一個不依 GAAP 計算的指標（[non-GAAP measure](/business/knowledge-cards/non-gaap-measure/)）「Net Cash Outlay for Capital Expenditures」：資本支出扣掉客戶預付與資本支出相關的短期融資之後，第一季是 179.66 億；被扣掉的客戶預付是 113.63 億。尚未開始的租約 2,880 億美元，租期 15 到 19 年。資本支出超過營業現金流的部分，由客戶預付、公司債與增資支應，2026-11-04 Oracle 同日發行 100 億美元公司債與 100 億美元普通股。

AI 投資期間發債的不只 Oracle：Microsoft 在 2026-10-29 簽了 250 億美元公司債的承銷協議，Meta 在 2026-11-05 發行 150 億美元公司債，並在 2026-10-26 以遠期出售協議發行 4,600 萬股普通股。Oracle 跟它們的差別是自由現金流已經轉負，資本支出超過營業現金流的缺口要靠客戶預付與外部資金；其他幾家的自由現金流本文沒有逐家列出。Oracle 為 OpenAI 的合約舉債蓋資料中心的安排，拆解在[OpenAI 的算力融資結構〈Oracle：為 OpenAI 的合約舉債蓋資料中心〉](/business/ai-infrastructure/openai-compute-financing/)。

## 涵蓋段的選擇在財報上出現的位置

涵蓋段的差別要從資本支出佔營收、分部營業利益率、伺服器耐用年限與尚未開始的租約幾處拼出來：

| 公司      | 資本支出佔營收（最近完整年度） | 資本支出佔營收（最近一季） | 雲端或主要分部的營業利益率（最近一季）   | 伺服器耐用年限                 | 尚未開始的租約          |
| --------- | ------------------------------ | -------------------------- | ---------------------------------------- | ------------------------------ | ----------------------- |
| Alphabet  | 22.7%（2025）                  | 40.3%（2026 Q3）           | Google Cloud 36.2%                       | 6 年                           | 1,305 億美元            |
| Microsoft | 34.9%（FY2026）                | 42.7%（FY2027 Q1）         | Agents and Infra 52.8%                   | 2 至 6 年                      | 3,646 億美元            |
| Amazon    | 18.4%（2025）                  | 38.3%（2026 Q3）           | AWS 38.7%                                | 5 至 6 年（2025 年縮短）       | 1,649 億美元            |
| Meta      | 34.7%（2025）                  | 52.5%（2026 Q3）           | Family of Apps 26.7%（含一次性和解費用） | 5 至 5.5 年（2025 年延長）     | 3,557 億美元            |
| Nvidia    | 2.8%（FY2026）                 | 本文沒有計算               | Compute & Networking 71.0%               | 本文沒有取用（自有設備規模小） | 自用資料中心 250 億美元 |
| Oracle    | 82.6%（FY2026）                | 147.3%（FY2027 Q1）        | Cloud and software 55%（只扣直接成本）   | 6 年                           | 2,880 億美元            |

資本支出取各家現金流量表購置不動產與設備的那一行（Nvidia 那一行含無形資產），不含[融資租賃](/business/knowledge-cards/finance-lease/)；租約與營業利益率的日期跟各家最近一季相同（Alphabet、Amazon、Meta、Microsoft 為 2026-09-30，Oracle 為 2026-08-31，Nvidia 為 2026-07-26）。比率是本文計算。表裡各欄各有自己的口徑：

- **資本支出佔營收**：分母方面，Amazon 的分母含零售營收，Alphabet、Meta 的分母含廣告營收，所以這個比率衡量的是整家公司的營收要撥多少給資本支出；本文六家的資本支出以伺服器與資料中心為主，所以可以讀成撥給算力的比例，套到資本支出以工廠或門市為主的公司就不能這樣讀。雲端業務本身的資本密集度，要拿雲端分部的營收另外估。分子方面，表裡的資本支出不含融資租賃，而各家用融資租賃取得設備的程度差很多：Microsoft 財務長在法說會說 2027 會計年度第一季含融資租賃的資本支出約 452 億美元（其中融資租賃約 74 億），除以當季營收 922.79 億是 49.0%；Amazon 前九個月償還的融資租賃本金只有 13 億，代表它很少用融資租賃取得設備。已經起租的融資租賃記在資產負債表的使用權資產與租賃負債，不在這一欄；還沒起租的記在下面「尚未開始的租約」那一欄，兩者是不同的項目。Meta 沒有雲端營收，比率高代表算力的成本全部壓在廣告上；Oracle 最近一季的比率超過 100%，代表營業現金流以外還要靠客戶預付與外部資金。
- **分部營業利益率**：各家分部的範圍不同。Meta Family of Apps 2026 年第三季的 26.7% 含一筆 98.9 億美元的州檢察長和解費用，扣掉之後約 42.1%（本文計算），前一年同季是 49.2%；Oracle 的 55% 只扣直接成本，不分攤研發與管理費用；Google Cloud 不分攤模型研發；Nvidia 的分部不含股份基礎薪酬。分部範圍不同時，跨公司的高低差含有範圍的差別；同一家在分部劃分沒有改變、或用公司重編的數字時，跟自己的前期比較沒有這個差別。
- **伺服器耐用年限**：同樣是伺服器，Alphabet 與 Oracle 用 6 年，Amazon 把一部分縮短到 5 年，Meta 延長到 5.5 年。年限越長，每年的[折舊](/business/knowledge-cards/depreciation-amortization/)越少、營業利益越高；Meta 延長年限讓 2025 年折舊少了 29.2 億美元，Amazon 縮短年限讓折舊多了 14 億。加速器每一兩代就被新產品超過，年限假設跟實際的經濟年限差得越多，之後一次提列減損或加速折舊的金額越大。
- **尚未開始的租約**：資料中心交付、租約開始之前，這些承諾不在資產負債表上，只寫在附註。Microsoft、Meta、Oracle 的金額都超過各自一年的營收（Meta 2025 年營收 2,009.66 億），租約陸續開始之後，每年的租金或折舊會進入成本。

## 自製、對外賣算力、資料中心與算力的取得、持股與只做設計：各自成立的條件與帳上的後果

各家段落寫的是一家公司的選擇，這一節把同一種選擇跨公司比較，寫出它在什麼條件下成立、代價記在帳上的哪裡。

- **自製加速器**：判斷的單位是工作負載，不是公司。一種工作負載同時符合下面幾項時，自製把原本付給 GPU 供應商的利潤留在公司內：用量大到分攤得掉好幾代晶片的設計成本；模型架構跨幾代晶片保持穩定，晶片可以針對它設計；跑在公司自己控制的軟體堆疊上；另外有一項看的是公司、不是工作負載：第一代晶片量產之前的幾年，公司付得起同時外購 GPU 與開發晶片兩套成本（現金流或融資都可以，OpenAI 與 Broadcom 的客製晶片以第三方融資支應，見[OpenAI 的算力融資結構〈Broadcom：為 OpenAI 的客製加速器安排中的第三方融資〉](/business/ai-infrastructure/openai-compute-financing/)）。這幾項是必要條件，成立了也不保證自製成功，還要跟得上外購 GPU 一兩年一代的換代速度：Tesla 的工作負載與軟體堆疊都是自己的，仍在 2025 年 8 月停掉訓練晶片 Dojo、改向外採購（Bloomberg 2025 年 8 月報導）。推論與推薦模型最符合這幾項，所以 Microsoft 的 Maia 200、Meta 的 MTIA 都先用在推論；前沿模型的訓練要追最新的架構與 CUDA 生態，多數公司仍以外購 GPU 為主。Google 的 Search 與 Gemini 由同一家公司從模型做到晶片，是把自製延伸到訓練的一例。對外部雲端客戶，雲端業者賣自製晶片的條件是客戶願意改寫軟體：多數客戶要在 CUDA 上跑既有軟體，改寫的成本由客戶承擔，所以雲端業者仍要外購 GPU（Microsoft Azure、Oracle OCI）；有自己的框架與編譯器團隊、能吸收改寫成本的大客戶是例外，Anthropic 同時使用 Google 的 TPU 與 AWS 的 Trainium，Apple 用 Google 的 Cloud TPU 訓練自家模型。這樣的大客戶也讓自製多一條路徑：Trainium 的主要用量來自外部客戶 Anthropic 的模型訓練，自製晶片的動力來自一個以股權綁定的錨定客戶，而不是 Amazon 自己的工作負載。這一條是本文依各家的工作負載與客戶結構推論的，「用量」這一項各家的申報文件都沒有揭露。
- **對外賣算力**：有雲端業務的公司（Google、Microsoft、Amazon、Oracle），自用需求減少時，同一批設備的產能還能租給外部客戶、由外部客戶分攤設備成本；這個分攤效果只在自用與外部需求不同步時成立，整體 AI 需求一起轉弱時，外部客戶的需求也同步下降。沒有雲端業務的 Meta，需求判斷錯誤時，閒置的產能只能在推薦、廣告與模型訓練這些內部工作負載之間調度，成本留在廣告營收要回收的那一邊。
- **資料中心與算力的取得**：用自己的現金流自建時，資產與折舊進入自己的報表；長期租賃把支出延到租期內，租約開始之前只在附註，起租之後依租約的性質，營業租賃與融資租賃都會在資產負債表上認列使用權資產與租賃負債，融資租賃的本金償還列在融資活動、不算進資本支出那一行（Microsoft 2027 會計年度第一季的融資租賃約 74 億）；合資實體出錢蓋、自己承租並擔保殘值（Meta 的 Hyperion），讓資產與債務都不進自己的報表，代價是殘值擔保這類或有負債（contingent liability，要等某個事件發生才成為實際債務的義務）；向 neocloud 或第三方雲端租算力（Microsoft 向 Nebius、Nscale 租用，Meta 的第三方雲端承諾），付款義務記在附註的採購承諾，資產與債務在 neocloud 的帳上；合約指定專用的設備時，依美國租賃準則可能構成內含的租賃，起租後也要在承租方認列使用權資產（本文依準則推論，沒有核對個別合約）。這幾種方式的差別在支出出現的時點與位置；算力需求不如預期時，自建的資產要自己承擔，租賃、擔保與租算力的義務照合約要付。
- **持有模型公司的股權**：雲端業者入股模型公司、模型公司又向它買算力時（Amazon 與 Anthropic、OpenAI，Microsoft 與 OpenAI，Alphabet 與申報文件沒有點名、媒體報導為 Anthropic 的一家非上市公司），雲端營收與投資綁在同一個客戶上。這個客戶的估值下跌或付不出錢時，營收與應收帳款立刻受影響，投資帳面值依入帳方式在不同時點受影響（出現可觀察交易價格或減損時、依權益法認列虧損時，或公允價值變動時）；各家的入帳方式與合計曝險列在[AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)〈持有方對同一個對象的營收、應收、投資與承諾〉。反方向的持股（晶片供應商入股它的客戶，例如 Nvidia 入股 CoreWeave、OpenAI）讓供應商承擔什麼風險，比較在[AI 算力交易裡的供應商融資形態〈股權投資：賣方成為買方的股東〉](/business/ai-infrastructure/vendor-financing-forms/)。
- **只做設計、資產留給別人**：Nvidia 的資本支出低來自委外製造；它的利益率高，本文能找到的候選成因有幾個：客戶的軟體建在 CUDA 上、換供應商要改寫（看 AMD 與自製晶片的份額變化）；產品的技術領先與上市時間（看新一代產品推出時售價的變化）；整櫃系統與網通一起賣（看網通營收佔資料中心營收的比例）；用採購承諾搶到稀缺的 CoWoS 與 HBM 產能（看供應與產能承諾的金額）；以及加速器缺貨期間的稀缺租金（看供給放寬時毛利率與售價的變化）。各成因各佔多少申報文件拆不出來。這個結構讓 Nvidia 在需求轉弱時沒有閒置的廠房要折舊；它往上游的採購承諾、往下游的承租雲端算力與擔保，在需求轉弱時照合約條款要履行，而這些金額只寫在附註，資產負債表上看不到。

## 延伸閱讀：各環節的經濟特性、本業以外的業務與融資結構

- [AI 算力價值鏈各環節的經濟特性](/business/ai-infrastructure/value-chain/ai-value-chain-segment-economics/)：從加速器設計、晶圓代工、HBM、伺服器組裝、網通、電力設備到資料中心與算力租賃，各環節代表業者的營業利益率、資本支出佔營收比與客戶集中度，以及依成本結構的分組。
- [AI 大廠本業以外的業務](/business/ai-infrastructure/value-chain/big-tech-adjacent-businesses/)：Waymo、Reality Labs、Amazon Leo、遊戲與 LinkedIn、Oracle Health、電力的取得方式，以及對模型公司的持股，各自在財報上出現在哪個分部或哪一行。
- [AI 算力交易裡的供應商融資形態](/business/ai-infrastructure/vendor-financing-forms/)：Nvidia 對 SB Energy 的擔保、晶片供應商入股客戶，各自屬於哪一種形態、風險由誰承擔。
- [AI 時代的獲利品質判讀：Alphabet 與 Tesla Q2 2026 財報拆解](/business/financial-analysis/case-studies/ai-era-earnings-quality/)：資本支出跑贏營業現金流時，怎麼從雲端營收與合約積壓判斷這筆支出背後的需求；那一篇的資本支出比率用的是分析師的日曆年口徑，跟本篇的申報口徑不同。
- 術語卡：[價值鏈涵蓋段](/business/knowledge-cards/value-chain-span/)、[垂直整合](/business/knowledge-cards/vertical-integration/)、[資本支出](/business/knowledge-cards/capex/)、[折舊與攤銷](/business/knowledge-cards/depreciation-amortization/)、[融資租賃](/business/knowledge-cards/finance-lease/)、[自由現金流](/business/knowledge-cards/free-cash-flow/)。
