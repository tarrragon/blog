---
title: "DRAM（動態隨機存取記憶體）"
date: 2026-07-24
description: "電腦運行時暫存資料的記憶體晶片——揮發性（斷電即失）、標準化規格、三家寡占（三星/SK 海力士/美光合計 95%+），景氣循環劇烈，是理解記憶體產業供需與 HBM 產能擠壓的基礎概念"
weight: 107
tags: ["business", "knowledge-cards", "electronics", "supply-chain"]
---

DRAM（Dynamic Random Access Memory，動態隨機存取記憶體）是電腦運行時暫存資料的記憶體晶片。CPU 或 GPU 處理資料時，先從儲存裝置（SSD/HDD）把資料搬進 DRAM，再從 DRAM 高速讀寫。DRAM 是揮發性記憶體——斷電後資料消失，跟儲存用的 NAND Flash（斷電保留資料）定位不同。手機、筆電、伺服器、AI 加速卡都需要 DRAM，是[大宗商品](/business/knowledge-cards/commodity-business/)特徵最明顯的半導體品類之一。

## 概念位置

DRAM 產業是典型的寡占結構：三星、SK 海力士、美光三家合計全球市佔超過 95%。產品高度標準化（DDR4、DDR5 等規格由國際標準組織 JEDEC 統一制定），差異化極低，具大宗商品特徵——但寡占結構讓三家廠商在供給端有一定的產能紀律，景氣谷底會同步減產止血。

DRAM 的景氣循環驅動因素跟 [MLCC](/business/knowledge-cards/mlcc/) 類似但放大機制不同：MLCC 的波動來自多層通路的[牛鞭效應](/business/knowledge-cards/bullwhip-effect/)和投機囤貨；DRAM 的波動來自產能投資的長前置期（新廠建設 18-24 個月）和位元需求的突然加速或減速。兩者共通的是：供需反轉時價格彈性極端。

[HBM](/business/knowledge-cards/hbm/) 是 DRAM 的衍生品類——物理上就是多層 DRAM 晶粒垂直堆疊。當廠商把晶圓產能從傳統 DRAM 轉向 HBM，同一座工廠能產出的傳統 DRAM 位元數下降，這是[產能擠壓](/business/financial-analysis/capacity-crowding-out/)的核心機制。

## 可觀察訊號與例子

DRAM 合約價有活躍的週報市場（DRAMeXchange / TrendForce 每週報價），是最即時的景氣觀測窗口——連續三個月合約價下跌通常預示景氣轉弱。位元出貨量成長率（記憶體用位元而非顆數計量，因為同一顆晶片的容量隨技術進步倍增）vs 位元產能成長率：需求成長率高於供給成長率時價格上漲，反之下跌。廠商資本支出計畫：三大廠同時宣布擴產是景氣高峰的訊號，同時宣布減產是谷底訊號。

2023 年是典型的谷底年——三大廠同步減產，DRAM [ASP](/business/knowledge-cards/asp/) 跌幅超過 40%，三星記憶體事業出現罕見的季度虧損。2024 年隨 AI 需求拉動 HBM，傳統 DRAM 也因產能被擠壓而供給趨緊，價格反轉上漲。

## 判讀方式

DRAM 的 ASP 波動極大（一年內可以漲跌 50%+），營收成長可能完全來自漲價而非出貨量增加——前者是週期性的，後者才是結構性的。看一家記憶體廠的長期競爭力，看製程節點推進速度（每顆晶粒的位元密度）和 HBM 等高階品類的營收佔比，而非短期的 ASP 漲幅。
