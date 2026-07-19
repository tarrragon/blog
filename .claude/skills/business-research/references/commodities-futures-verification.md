# Commodities and Futures Verification

> **Role**: Operational reference for the `business-research` skill — verification methods for raw-material price claims (grains, oils, softs, dairy, energy, freight) that feed cost-structure and margin analysis of processing companies.
>
> **When to read**: When an analysis cites commodity prices as input costs (feed, crush, chocolate, fuel), decomposes margin changes into structural vs windfall, or fact-checks social-media claims about raw material economics.

## Source Hierarchy for Commodities

| Tier | Source type | Examples | Notes |
| --- | --- | --- | --- |
| 1 | Exchange official data | CME/CBOT（玉米、黃豆、小麥、黃豆油粕）、ICE（可可、咖啡、糖、布蘭特）、Bursa Malaysia（棕櫚油 FCPO、馬幣計價）、NZX + GlobalDairyTrade（乳品——GDT 拍賣約兩週一次、是乳品國際價的正典來源）、Baltic Exchange（BDI 散裝運價） | The settlement price of a named contract is a fact; everything else is derived |
| 2 | Government supply-demand statistics | USDA WASDE（月度全球農產供需、產業定錨報告）、USDA PSD 資料庫、EIA（能源） | The canonical fundamentals — production, stocks, usage; explains price moves |
| 3 | Aggregators | TradingEconomics、Investing.com、MacroMicro、StockQ | Convenient series; verify unusual values against tier 1 |

## Five Verification Rules

### 1. Contract Specificity

「黃豆價格」不是一個數字——是哪個交割月份的哪個合約、什麼單位。近月合約價 ≠ 加工商實際支付價。引用時標明：交易所、合約月份（或註明為近月/連續）、單位、日期。

### 2. Unit Conversion Discipline

美系農產用蒲式耳（bushel）與英磅計價，跨市場比較必須換算並展示換算：

| 商品 | 交易單位 | 換算 |
| --- | --- | --- |
| 黃豆/小麥 | 美分/蒲式耳（60 lb/bu） | $/bu × 36.74 = $/公噸 |
| 玉米 | 美分/蒲式耳（56 lb/bu） | $/bu × 39.37 = $/公噸 |
| 黃豆油、可可（部分） | 美分/磅 或 $/公噸 | ¢/lb × 22.05 = $/公噸 |
| 棕櫚油 FCPO | 馬幣/公噸 | 另需 MYR 匯率——雙重換算陷阱 |

實例模式：用零售小包裝價（22.3 元/kg 的蝦皮黃豆）當原料成本、忽略大宗散裝到岸價（15.7 元/kg）——零售與大宗差 40%+ 是常態、不是異常。

### 3. Term Structure Awareness

同一商品在不同到期月的價格不同（正價差 contango / 逆價差 backwardation）。「現在的現貨」跟「半年後的期貨」相比不是漲跌、是期限結構。比較必須同 tenor 對同 tenor。

### 4. Landed Cost ≠ Futures Price

加工商的實際成本 = 期貨/離岸價 + 基差 + 海運費 + 保險 + 匯率 + 關稅。引用期貨價評論進口商成本時，缺這串調整就是結構性低估。反向亦然：到岸價的變動可能來自運費或匯率、跟商品本身的供需無關——拆解來源再歸因。

### 5. Recompute Spreads

壓榨/裂解價差類的宣稱用組成價格重算驗證。黃豆壓榨（噸基準）：crush margin = 豆油價 × 0.185 + 豆粕價 × 0.78 − 黃豆成本 − 加工費；CME 盤面慣例（bu 基準）：crush = 豆粕($/短噸) × 0.022 + 豆油(¢/lb) × 0.11 − 黃豆($/bu)。聯產品事業的「利潤暴增/崩跌」宣稱，先重算價差再接受敘事。

## Commodity-Specific Failure Modes

| Failure mode | How it happens | Prevention |
| --- | --- | --- |
| 連續合約的拼接失真 | 長期圖表用轉倉調整後的連續合約，跨年百分比變動與實際合約價不同 | 長期漲跌幅宣稱回到各年度實際合約結算價驗證 |
| 名目價跨年比較 | 「十年新高」未計匯率與通膨；台幣計價的進口成本混入匯率效果 | 拆開商品價與匯率兩個因子（實例：飼料成本 = 穀價 + 海運 + 台幣貶值三因子各自標註幅度） |
| 行銷年度 vs 日曆年度 | USDA 的美豆行銷年度為 9 月-8 月，「2024 年產量」在不同來源指涉不同區間 | 標明區間定義 |
| 雙合約混淆 | 同商品有多個交易所合約（可可：ICE 美國 $/噸 vs ICE 倫敦 £/噸）、幣別不同 | 標明交易所與幣別 |
| 峰值當常態 | 用衝擊期高點（可可 $10,000+/噸、運費 $12,000/櫃）做長期成本假設 | 對照 5-10 年區間、標記當前價位於歷史帶的位置 |

## Purpose Map: What Each Verification Serves

| Analytical claim | Verification path |
| --- | --- |
| 「原料成本暴漲壓縮毛利」 | Tier-1 合約價序列確認幅度與期間 → 對照公司毛利率變動時點（傳導通常落後 1-2 季，視庫存策略） |
| 「獲利提升是結構性的」 | 重算價差：若價差擴大解釋了大部分獲利、屬 windfall 而非結構改善 |
| 「A 公司受益、B 公司受損於同一波行情」 | 確認兩家在該商品的位置（賣方/買方/賣替代品）——同一價格變動對不同鏈位方向相反 |
| 供給衝擊的時間線 | WASDE/官方統計的產量與庫存數據錨定敘事、新聞報導只當佐證 |
