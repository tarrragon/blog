---
title: "AI 時代的獲利品質判讀：Alphabet 與 Tesla Q2 2026 財報拆解"
date: 2026-07-24
description: "判讀科技公司財報中投資收益灌水 GAAP 淨利、資本支出跑贏現金流的狀況時，用獲利品質拆解區分本業獲利與帳面收益、衡量 capex 強度是否有需求支撐"
weight: 56
tags: ["business", "financial-analysis", "ai", "earnings"]
---

2026 年 7 月 22 日盤後,Alphabet 和 Tesla 同時發布 Q2 財報。Alphabet 淨利從去年同期的 282 億美元跳到 1,121 億美元,年增近四倍;Tesla 營收 282.4 億美元創歷史新高,交付量 48 萬輛創同期紀錄。兩家的 headline 數字都超出市場預期,但盤後雙雙被賣——Alphabet 累計跌約 7-8%（多日累計）,Tesla 隔日單日暴跌約 14.5%。

這篇用兩家財報走一遍 AI 時代的獲利品質判讀——什麼情況下帳面淨利跟本業獲利差很遠、資本支出什麼時候值得擔心、以及為什麼這些科技公司的資本支出數字跟電子零件供應鏈的缺貨直接相關。

## 帳面淨利 vs 本業獲利

### 為什麼 GAAP（一般公認會計原則）淨利會被投資帳扭曲

2018 年生效的美國會計準則修訂（ASU 2016-01）規定:持有的股權證券必須每季按公允價值重估,未實現損益直接計入淨利。公司手上持有的股票漲了,即使一股沒賣、一分錢現金沒進來,帳面淨利也會暴增。反過來,持股跌了,淨利也會暴跌。這個規則適用於所有持有股權證券的公司,不是個別公司的會計選擇。

Berkshire Hathaway 的 Buffett 是最知名的批評者。他在股東信裡指出 Berkshire 2018 年 GAAP 淨利 40 億美元,2019 年跳到 814 億美元（增長 1,900%）,但營運利潤分別是 248 億和 240 億（幾乎持平）。他稱 GAAP 淨利數字「worse than useless」。Alphabet 和 Tesla 的 Q2 2026 財報正是同一個問題的大型示範。

### Alphabet:980 億美元投資收益佔淨利 87%

Alphabet Q2 2026 GAAP 淨利 1,121 億美元,其中「其他收支淨額」(other income/expense, net)為 980 億美元——佔淨利的 87%。這 980 億主要來自兩筆投資的公允價值重估（Bank of America 估算,非公司逐筆揭露）:

- **Anthropic**:Alphabet 持有約 14% 股權。Q2 期間 Anthropic 估值從約 3,800 億美元飆升至約 9,650 億美元（獲一輪 650 億美元融資）,估計貢獻約 800 億美元的投資收益
- **SpaceX**:2026 年 6 月 IPO（Initial Public Offering,首次公開發行,估值約 1.77 兆美元）,Alphabet 持有約 4.9% 股權,截至 Q2 末公允價值約 940 億美元

兩筆都是未實現收益——Alphabet 沒有賣出任何持股,沒有現金入帳。如果下一季 Anthropic 估值回調或 SpaceX 股價下跌,同樣金額的「虧損」會直接衝擊淨利。

剔除投資收益後的調整 EPS（Earnings Per Share,每股盈餘）為 $2.85,LSEG（London Stock Exchange Group,路透社母公司旗下的金融數據服務）的市場共識預期是 $2.89。本業獲利實際上小幅未達預期 $0.04。這跟 GAAP EPS $9.11（年增 294%）呈現的圖像完全不同。

### Tesla:淨利七成來自 SpaceX 帳面收益

Tesla Q2 GAAP 淨利 11.14 億美元,其中認列了 10.05 億美元的 SpaceX 股權未實現收益（稅後約 7.63 億美元）。68.5% 的淨利來自一筆帳面收益,而非賣車、能源或 FSD（Full Self-Driving,全自動駕駛）。

Tesla 持有 SpaceX 是 2026 年初才發生的:Tesla 投資 xAI 20 億美元,xAI 隨後併入 SpaceX,Tesla 取得 SpaceX Class A 股份約 1,900 萬股,取得成本 20 億美元。SpaceX 6 月 IPO 後持倉市值升至 30 億美元以上。

排除 SpaceX 收益後,Tesla 核心業務的稅後淨利僅約 3.5 億美元。整體營業利益率從去年同期的 4.1% 降至 1.4%（營業利潤 3.98 億 / 營收 282.4 億）,營業費用年增 47% 遠超營收 26% 增速。Non-GAAP EPS $0.33,市場共識約 $0.47-0.53（來源未統一,各平台共識略有差異）——miss 幅度約 30-38%,這是股價暴跌的核心原因。

Tesla 的非汽車業務在成長中——能源部門營收 31.4 億美元（年增 13%）、FSD（全自動駕駛）訂閱用戶 148 萬（年增 56%,attach rate 55%）、Robotaxi 已在 7 個都會區營運。但這些成長軌跡尚未反映在本季的核心獲利結構中,還原本業獲利後的稅後淨利只有 3.5 億美元。

### 判讀工具:[正常化盈餘](/business/knowledge-cards/normalized-earnings/)

把投資收益從淨利中剔除,看到的是本業的真實獲利能力。這正是[正常化盈餘](/business/knowledge-cards/normalized-earnings/)的操作——從 GAAP 淨利中剔除一次性或非經常性項目,還原成可持續的獲利基礎。在 ASU 2016-01 之下,持有大量股權證券的公司（Alphabet/Tesla/Berkshire/SoftBank）每季都需要做這個剔除,否則 EPS 會被投資帳的波動完全扭曲。

## 資本支出與現金流的失衡

投資收益讓淨利失真,本業獲利也有自己的壓力。兩家公司的資本支出（capex,capital expenditure）都在快速膨脹,Q2 雙雙出現自由現金流（FCF,free cash flow = 營業現金流 − 資本支出）轉負。

### Alphabet:capex 佔營收 42%,FCF 近 20 年首次為負

Alphabet Q2 資本支出 449 億美元（年增 101%）,吃掉了 391 億的營業現金流,FCF 為 -59 億美元。全年 capex 指引從原本的 1,800-1,900 億上修到 1,950-2,050 億美元,中位數 2,000 億,約佔年化營收的 42%。

42% 的 capex/revenue 比在四大 hyperscaler（最大型雲端運算業者）中的位置:

| 公司      | 2026 年 capex 概估 | capex/revenue | 備註               |
| --------- | ------------------ | ------------- | ------------------ |
| Microsoft | ~1,900 億美元      | ~55-58%       | 最高,含 Azure 擴張 |
| Meta      | ~530-580 億美元    | ~53%          | AI 資料中心重投    |
| Alphabet  | ~2,000 億美元      | ~42%          | 本季上修           |
| Amazon    | ~1,200 億美元      | ~25%          | 最低（營收基數大） |

（來源:各公司法說會指引與分析師彙整。Microsoft 數字為日曆年估計,因會計年度 6 月底截止、跨年度計算口徑不同。四家合計約 5,630-5,680 億美元;若加入 Oracle、Apple 等其他 AI 基建投入,分析師估計 Mag 7 整體 2026 年 AI 相關 capex 合計約 7,250 億美元）

Alphabet 的 42% 在四大 hyperscaler 中居中,遠低於 Microsoft 和 Meta。整個 hyperscaler 群體的資本強度確實在快速靠近電信與公用事業的水準,但把 Alphabet 單獨拿出來讓讀者以為它是最激進的會誤導——Microsoft 和 Meta 的比率更高。

### Tesla:不同性質的 capex 壓力

Tesla Q2 資本支出 57.9 億美元（年增 142%）,FCF -10.9 億美元,兩年來首次轉負。全年 capex 指引 250 億美元。

Tesla 的 capex 壓力跟 Alphabet 性質不同。Alphabet 的支出投向的是雲端基礎設施（GPU 集群、資料中心），有直接的營收歸因——Google Cloud Q2 營收 248 億美元,年增 82%。Tesla 的 AI 相關 capex 散布在 FSD 訓練算力、Robotaxi 車隊部署、工廠自動化三個不同領域,更接近研發性質的賭注,而非服務已簽約客戶的基建。

兩家的共同點是 FCF 轉負;原因不同:Alphabet 是「確定有需求但投資規模太大」,Tesla 是「需求尚待驗證但已大量投入」。市場對後者的懲罰更重（Tesla -14.5% vs Alphabet -7-8%）。

## capex 有沒有需求支撐

判讀 capex 是否合理,要看支出有多少比例對應到可驗證的需求。

### Alphabet:Cloud 成長與 backlog 的支撐

Google Cloud Q2 營收 248 億美元,年增 82%,遠超分析師預期的 63-64%。Cloud 營業利潤率從 20.7% 升至 35.6%——成長的同時在賺錢。Cloud backlog（未履行合約餘額）從去年同期的 1,060 億飆到 5,140 億美元,年增近 5 倍。

Cloud backlog 的規模反映客戶已簽多年合約的總承諾金額,方向上支持 capex 有需求基礎。但 backlog 是需求的上界而非下界——多年合約通常有 ramp 條款（前期用量低、逐年放大）、部分合約有提前終止選項、committed minimum 可能低於 total contract value。年增 5 倍的增速也值得追問合約品質是否隨規模擴大而稀釋。Cloud backlog 代表「方向明確、規模可觀」,但把 $514B 除以 $200B 算出「2.5 年保證需求」是過度簡化——backlog 是營收承諾,capex 是投資支出,兩者量綱不同。

### Tesla:需求仍在驗證階段

Tesla 的 AI 相關支出主要投向 Robotaxi 和 FSD。目前 Robotaxi 在 7 個都會區營運,累計付費里程約 250 萬英里,規模遠小於 Waymo。FSD 訂閱用戶 148 萬、年化訂閱營收約 7.9 億美元。能源部門 Q2 部署 13.5 GWh 創同期紀錄。

這些業務在成長,但規模跟 $250 億年 capex 之間的差距很大。Tesla 目前沒有等同於 Google Cloud backlog 那種已簽約的大規模需求錨點。

### AI ROI 的雙面證據

需求支撐的判讀不能用「AI 投資一定會回收」或「AI 是泡沫」的二元框架。兩面的證據都有紮實支撐:

正面:Google Cloud 82% 成長 + 35.6% 營業利潤率,GenAI 經濟年化營收已達 1,750 億美元,每 1 美元基礎建設折舊對應約 1.19 美元 hyperscaler 營收（首次翻正）。

反面:MIT Project NANDA（2025 年 7 月）調查 300+ 企業 AI 專案,95% 的 GenAI 試點產生零可量化的 P&L 影響;Allianz Research 指出 AI capex 與營收的成長背離率約 46%,超過 2001 年電信泡沫高峰的 32%;2025 年至少 1,560 億美元的資料中心專案被取消或延後;Meta 首度承認有「excess compute capacity」。

要看的是每家公司的 capex 有多少比例對應到已驗證的需求、有多少是賭未來。同一個 AI capex 框架下,Alphabet 和 Tesla 的風險曝露程度截然不同。

## 跟供應鏈的直接連結

這些 capex 數字是驅動電子零件供應鏈缺貨的需求端源頭。

Hyperscaler 的資本支出大部分花在蓋資料中心:買 NVIDIA GPU（驅動 [HBM](/business/knowledge-cards/hbm/),High Bandwidth Memory 高頻寬記憶體的需求）、伺服器主機板（驅動高容值 [MLCC](/business/knowledge-cards/mlcc/) 積層陶瓷電容和鉭質電容需求）、交換器與電源系統（驅動電感和 PMIC 電源管理晶片需求）。

Alphabet 把 capex 從 1,850 億上修到 2,000 億時,SK Hynix 的 HBM 訂單簿在增厚,村田的高容值 MLCC 交期在延長,DDR5 的合約價在被這些需求推高。[記憶體缺貨分析](/business/financial-analysis/memory-market-shortage-analysis/)裡的「HBM 排擠一般 [DRAM](/business/knowledge-cards/dram/)（Dynamic Random Access Memory,動態隨機存取記憶體）」,需求端的源頭就在這些財報的 capex 行裡。[產能排擠機制](/business/financial-analysis/capacity-crowding-out/)裡的高階搶走共用產能,推動力就是 hyperscaler 每季追加的投資。

反過來,如果這些 capex 計畫被縮減（經濟衰退 / AI ROI 不如預期 / 資料中心過建）,記憶體和被動元件的需求端會同步收縮——這正是記憶體缺貨分析裡「訊號四:AI 投資放緩」的具體觀察點。

## 判讀框架:看到科技財報先問的初篩問題

這兩份財報提供了一個初篩框架,適用於持有大量投資部位、同時在投入 AI 基建的科技公司。這三個問題能快速過濾被 headline 數字誤導的判斷,但完整的分析還需要看資產負債表健康度、營收品質與管理層資本配置紀錄。

**淨利裡有多少是本業賺的?** 用 GAAP 淨利減去「其他收支淨額」還原本業獲利。持有股權證券的公司每季都會被投資帳的公允價值波動扭曲。看調整後 EPS 或營業利潤,比看 GAAP EPS 更接近本業表現。

**資本支出投向的需求有多少已驗證?** 高 capex 可以是健康的投資訊號——Cloud backlog $514B 代表需求方向明確。但 backlog 規模要跟合約品質一起看（ramp 條款、取消風險、committed minimum）。Tesla 的 Robotaxi 沒有同等規模的已驗證需求,capex 的風險曝露更高。

**自由現金流轉負是投資期還是燒錢?** 看 capex 增速跟營收增速的差距——Alphabet 營收年增 24% 但 capex 年增 101%,差距 77 個百分點;Tesla 營收年增 26% 但 capex 年增 142%,差距 116 個百分點。差距越大、投資期越長、回收越不確定。

## 跟其他文章的關係

本篇從科技公司財報的需求端,接上[記憶體缺貨分析](/business/financial-analysis/memory-market-shortage-analysis/)和[被動元件產業結構](/business/financial-analysis/passive-component-industry-structure/)的供給端——hyperscaler 的 capex 是驅動電子零件缺貨的根源。[正常化盈餘](/business/knowledge-cards/normalized-earnings/)卡片提供了從 GAAP 淨利還原本業獲利的方法。[產能擴建週期](/business/financial-analysis/capacity-expansion-cycle/)的產能紀律段解釋了為什麼三大記憶體廠選擇不擴產一般 DRAM——它們的產能決策對應的正是 hyperscaler 的 HBM 採購承諾。[產能排擠機制](/business/financial-analysis/capacity-crowding-out/)裡高階搶走共用產能的推動力,量化後就是這些財報的 capex 數字。
