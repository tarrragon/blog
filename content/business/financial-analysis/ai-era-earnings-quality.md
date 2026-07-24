---
title: "AI 時代的獲利品質判讀：Alphabet 與 Tesla Q2 2026 財報拆解"
date: 2026-07-24
description: "判讀科技公司財報中 AI 投資收益灌水 GAAP 淨利、資本支出跑贏現金流的狀況時，用獲利品質拆解區分本業獲利與帳面收益、衡量 capex 強度是否有需求支撐"
weight: 56
tags: ["business", "financial-analysis", "ai", "earnings"]
---

2026 年 7 月 22 日盤後,Alphabet 和 Tesla 同時發布 Q2 財報。Alphabet 淨利從去年同期的 282 億美元跳到 1,121 億美元,年增近四倍;Tesla 營收 282.4 億美元創歷史新高,交付量 48 萬輛創同期紀錄。兩家的 headline 數字都很漂亮,但盤後雙雙被賣——Alphabet 累計跌約 7-8%,Tesla 隔日暴跌約 14.5%。

市場在重新評估成長的代價與品質。這篇用兩家財報走一遍「AI 時代的獲利品質判讀」——什麼情況下帳面淨利跟本業獲利差很遠、資本支出什麼時候值得擔心、以及這些支出跟我們模組裡分析的[記憶體缺貨](/business/financial-analysis/memory-market-shortage-analysis/)和[被動元件排擠](/business/financial-analysis/passive-component-industry-structure/)有什麼直接關係。

## 第一層:帳面淨利 vs 本業獲利

### 為什麼 GAAP 淨利不可靠

2018 年生效的美國會計準則修訂（ASU 2016-01）規定:持有的股權證券必須每季按公允價值重估,未實現損益直接計入淨利。這代表公司手上持有的股票漲了,即使一股沒賣、一分錢現金沒進來,帳面淨利也會暴增。反過來,持股跌了,淨利也會暴跌。

這個規則適用於所有持有股權證券的公司。Berkshire Hathaway 的 Buffett 是最知名的批評者——他在股東信裡指出 Berkshire 2018 年 GAAP 淨利 40 億美元,2019 年跳到 814 億美元（增長 1,900%）,但營運利潤分別是 248 億和 240 億（幾乎持平）。他稱 GAAP 淨利數字「worse than useless」。

Alphabet 和 Tesla 的 Q2 2026 財報正是這個問題的大型示範。

### Alphabet:$98B 投資收益灌進淨利

Alphabet Q2 2026 GAAP 淨利 1,121 億美元,其中「其他收支淨額」(other income/expense, net)為 980 億美元——佔淨利的 87%。這 980 億主要來自兩筆投資的公允價值重估:

- **Anthropic**:Alphabet 持有約 14% 股權。Q2 期間 Anthropic 估值從約 3,800 億美元飆升至約 9,650 億美元（獲一輪 650 億美元融資）。Bank of America 估算約 800 億美元的投資收益來自 Anthropic
- **SpaceX**:2026 年 6 月 IPO（估值約 1.77 兆美元），Alphabet 持有約 4.9% 股權,截至 Q2 末公允價值約 940 億美元

兩筆都是未實現收益——Alphabet 沒有賣出任何持股,沒有現金入帳。如果下一季 Anthropic 估值回調或 SpaceX 股價下跌,同樣金額的「虧損」會直接衝擊淨利。

剔除投資收益後的調整 EPS 為 $2.85,路透社（LSEG）的市場共識預期是 $2.89——本業獲利實際上小幅**未達預期** $0.04。這跟 GAAP EPS $9.11（年增 294%）呈現的圖像完全不同。

### Tesla:淨利七成來自 SpaceX 帳面收益

Tesla Q2 GAAP 淨利 11.14 億美元,其中認列了 10.05 億美元的 SpaceX 股權未實現收益（稅後約 7.63 億美元）。$7.63 億 / $11.14 億 = 68.5%——淨利接近七成來自一筆帳面收益,而非賣車、能源或 FSD。

Tesla 持有 SpaceX 是 2026 年初才發生的:Tesla 投資 xAI 20 億美元,xAI 隨後併入 SpaceX,Tesla 取得 SpaceX Class A 股份約 1,900 萬股,取得成本 20 億美元。SpaceX 6 月 IPO 後持倉市值升至 30 億美元以上。

排除 SpaceX 收益後,Tesla 核心業務的稅後淨利僅約 3.5 億美元。Non-GAAP EPS $0.33,市場共識 $0.47-0.53——miss 幅度 30-39%,這是股價暴跌 14.5% 的核心原因。

### 判讀工具:[正常化盈餘](/business/knowledge-cards/normalized-earnings/)

把投資收益從淨利中剔除,看到的是本業的真實獲利能力。這正是[正常化盈餘](/business/knowledge-cards/normalized-earnings/)的操作——從 GAAP 淨利中剔除一次性或非經常性項目,還原成可持續的獲利基礎。在 ASU 2016-01 之下,持有大量股權證券的公司(Alphabet/Tesla/Berkshire/SoftBank)每季都需要做這個剔除,否則 EPS 會被投資帳的波動完全扭曲。

## 第二層:資本支出跑贏現金流

投資收益讓淨利失真,但本業獲利也有自己的壓力。兩家公司的資本支出都在快速膨脹,Q2 雙雙出現自由現金流轉負。

### Alphabet:capex 佔營收 42%

Alphabet Q2 資本支出 449 億美元（年增 101%）,吃掉了 391 億的營業現金流,自由現金流為 -59 億美元——近 20 年來首次季度自由現金流為負。全年 capex 指引從原本的 1,800-1,900 億上修到 1,950-2,050 億美元,中位數 2,000 億,約佔年化營收的 42%。

42% 的 capex/revenue 比在科技業同行中的位置:

| 公司      | 2026 年 capex 概估 | capex/revenue | 備註               |
| --------- | ------------------ | ------------- | ------------------ |
| Microsoft | ~1,900 億美元      | ~55-58%       | 最高,含 Azure 擴張 |
| Meta      | ~530-580 億美元    | ~53%          | AI 資料中心重投    |
| Alphabet  | ~2,000 億美元      | ~42%          | 本季上修           |
| Amazon    | ~1,200 億美元      | ~25%          | 最低（營收基數大） |

（來源:各公司法說會指引與分析師彙整。Microsoft 數字為日曆年,因會計年度 6 月底截止,跨年度計算口徑不同）

Alphabet 的 42% 在四大 hyperscaler 中居中,遠低於 Microsoft 和 Meta。社群貼文說「資本強度正在快速靠近電信與公用事業」——這對整個 hyperscaler 群體是對的,但把 Alphabet 單獨拿出來講會讓讀者以為它是最激進的,實際上 Microsoft 的比率更高。

### Tesla:不同性質的 capex 壓力

Tesla Q2 資本支出 57.9 億美元（年增 142%）,自由現金流 -10.9 億美元,兩年來首次轉負。全年 capex 指引 250 億美元。

Tesla 的 capex 壓力跟 Alphabet 性質不同。Alphabet 的支出投向已有明確需求排隊的 AI 基礎建設（Google Cloud backlog 5,140 億美元,年增近 5 倍）。Tesla 的支出投向 AI 訓練、Robotaxi 車隊擴張與工廠自動化——這些領域的需求仍處於驗證階段（付費 Robotaxi 里程約 250 萬英里,規模遠小於 Waymo;FSD 訂閱用戶 148 萬,attach rate 55%）。

兩家的共同點是自由現金流轉負。但原因不同:Alphabet 是「確定有需求但投資規模太大」,Tesla 是「需求尚待驗證但已大量投入」。市場對後者的懲罰更重（Tesla -14.5% vs Alphabet -7-8%）。

## 第三層:capex 有沒有需求支撐

社群貼文問了一個對的問題:「花錢的速度跑贏產生現金的速度」。但回答這個問題需要區分「有需求但暫時虧」和「需求本身存疑」。

### 有需求支撐的 capex 證據(Alphabet 為例)

- Google Cloud Q2 營收 248 億美元,年增 82%,遠超分析師預期的 63-64%
- Cloud 營業利潤率從 20.7% 升至 35.6%——成長的同時在賺錢
- Cloud backlog 從去年同期的 1,060 億飆到 5,140 億美元——客戶已簽多年合約等著用
- CEO Pichai:「需求已經排隊等著,不蓋更多資料中心就會把市場讓給競爭對手」

### 需求存疑的反面證據

- MIT Project NANDA（2025 年 7 月）調查 300+ 企業 AI 專案:95% 的 GenAI 試點產生零可量化的 P&L 影響
- Allianz Research（2026 年 3 月）:AI capex 與營收的成長背離率約 46%,超過 2001 年電信泡沫高峰的 32%
- 2025 年至少 1,560 億美元的資料中心專案被取消或延後
- Meta 首度承認有「excess compute capacity」

兩組證據同時存在,且各自都有紮實的支撐——這代表判讀不能用「AI 投資一定會回收」或「AI 是泡沫」的二元框架。要看的是每家公司的 capex 有多少比例對應到已簽合約的 backlog、有多少是賭未來需求。Google Cloud 的 $514B backlog 讓 Alphabet 的 $200B capex 有明確的需求錨點;Tesla 的 Robotaxi 和 AI 訓練目前缺乏同等規模的需求證據。

## 跟供應鏈的直接連結

這些 capex 數字不只是科技公司的財報議題——它們是驅動整條電子零件供應鏈缺貨的根源。

四大 hyperscaler 2026 年 capex 合計約 7,250 億美元,較 2025 年增長 77%。這些錢大部分花在蓋資料中心:買 NVIDIA GPU（驅動 HBM 需求）、伺服器主機板（驅動高容值 MLCC 和鉭質電容需求）、交換器與電源系統（驅動電感和 PMIC 需求）。

所以 Alphabet 把 capex 從 1,850 億上修到 2,000 億時,不只是 Alphabet 股東在重新計算自由現金流——SK Hynix 的 HBM 訂單簿在增厚,村田的高容值 MLCC 交期在延長,DDR5 的合約價在被這些需求推高。[記憶體缺貨分析](/business/financial-analysis/memory-market-shortage-analysis/)裡的「HBM 排擠一般 DRAM」,需求端的源頭就在這些財報的 capex 行裡。[產能排擠機制](/business/financial-analysis/capacity-crowding-out/)裡的「高階搶走共用產能」,推動力就是 hyperscaler 每季追加的幾百億美元。

反過來,如果這些 capex 計畫被縮減（經濟衰退/AI ROI 不如預期/資料中心過建）,記憶體和被動元件的需求端會同步收縮——這正是記憶體缺貨分析裡「訊號四:AI 投資放緩」的具體觀察點。

## 判讀框架:看到漂亮財報先問三件事

這兩份財報提供了一個可重複使用的判讀框架,適用於持有大量投資部位、同時在大量投入 AI 基建的科技公司:

**一、淨利裡有多少是本業賺的?** 用 GAAP 淨利減去「其他收支淨額」(other income/expense)還原本業獲利。持有股權證券的公司(Alphabet/Tesla/SoftBank/Berkshire)的 GAAP 淨利每季都會被投資帳的公允價值波動扭曲。看調整後 EPS 或營業利潤,比看 GAAP EPS 更接近本業表現。

**二、資本支出有沒有需求錨點?** 高 capex 本身不是壞事——問題是這些支出有多少比例對應到已簽合約的 backlog 或可驗證的需求。Cloud backlog $514B 是 capex $200B 的 2.5 倍,代表 Alphabet 至少有兩年半的已簽約需求在等。Tesla 的 Robotaxi 沒有同等規模的已簽約需求,capex 的風險曝露更高。

**三、自由現金流轉負的原因是什麼?** FCF 轉負可以是「投資期的正常現象」(營收快速成長期先花後收)也可以是「燒錢失控」。區分的方法是看 capex 增速跟營收增速的比例——如果營收年增 25% 但 capex 年增 100%,差距越大、投資期越長、回收越不確定。

## 跟其他文章的關係

本篇從科技公司財報的需求端,接上[記憶體缺貨分析](/business/financial-analysis/memory-market-shortage-analysis/)和[被動元件產業結構](/business/financial-analysis/passive-component-industry-structure/)的供給端——hyperscaler 的 capex 是驅動電子零件缺貨的根源。[正常化盈餘](/business/knowledge-cards/normalized-earnings/)卡片提供了從 GAAP 淨利還原本業獲利的方法。[產能擴建週期](/business/financial-analysis/capacity-expansion-cycle/)的產能紀律段解釋了為什麼三大記憶體廠選擇不擴產一般 DRAM——它們的產能決策對應的正是 hyperscaler 的 HBM 採購承諾。
