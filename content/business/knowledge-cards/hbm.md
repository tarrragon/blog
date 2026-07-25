---
title: "HBM（High Bandwidth Memory，高頻寬記憶體）"
date: 2026-07-24
description: "AI 加速器專用的記憶體封裝——把多層 DRAM 晶粒垂直堆疊再與 GPU 封裝在同一基板上，頻寬比傳統 DRAM 高一個量級，但每顆消耗的晶圓面積是傳統 DRAM 的 3-4 倍，成為 AI 算力擴張的產能瓶頸"
weight: 106
tags: ["business", "knowledge-cards", "electronics", "supply-chain"]
---

HBM（High Bandwidth Memory）是一種把多層 [DRAM](/business/knowledge-cards/dram/) 晶粒垂直堆疊、再與 GPU 封裝在同一基板上的記憶體技術。核心目的是頻寬：AI 模型的推論和訓練需要在 GPU 和記憶體之間高速搬運大量資料，傳統 DRAM 模組透過主機板上的線路連接，頻寬受限於線路距離和接腳數量。HBM 把記憶體直接疊在晶片旁邊，用數千條微細的矽穿孔（TSV）垂直連接，頻寬比傳統 DDR 模組高一個量級。

## 概念位置

HBM 的產能瓶頸來自三個環節的交叉限制，是理解 AI 產業[產能擠壓](/business/financial-analysis/capacity-crowding-out/)的關鍵。

第一是晶圓面積。HBM 需要把 8-12 層 DRAM 晶粒堆疊，每層都是獨立的晶粒，一顆 HBM 消耗的晶圓面積是同容量傳統 DRAM 的 3-4 倍。當記憶體廠把產能從傳統 DRAM 轉向 HBM，同一座晶圓廠能產出的位元數大幅下降——這就是產能擠壓的機制。

第二是先進封裝。HBM 的垂直堆疊需要 TSV（Through-Silicon Via，矽穿孔）技術把每層晶粒的數千條訊號垂直貫穿，再用極細的焊點連接。這個封裝製程比傳統記憶體複雜得多，產能集中在少數封裝廠。

第三是與 GPU 的共封裝。HBM 和 GPU 要一起放在同一塊基板上（台積電的 CoWoS 製程），這個先進封裝的產能同樣是瓶頸。

跟 [MLCC](/business/knowledge-cards/mlcc/) 的類比：兩者都是「AI 需求把產能推向高階品類、擠壓低階品類可用產能」的結構，但驅動因素不同——MLCC 是製造 know-how 門檻，HBM 是晶圓面積的物理消耗。

## 可觀察訊號與例子

HBM 世代演進：HBM2e → HBM3 → HBM3e → HBM4，每代頻寬和容量提升，但堆疊層數也增加（HBM3e 為 8-12 層，HBM4 預計 16 層），晶圓面積消耗持續擴大。NVIDIA H100 搭配 HBM3（80GB），H200 搭配 HBM3e（141GB），B200 搭配 HBM3e（192GB）——每代旗艦的 HBM 用量倍增。

SK 海力士在 HBM 市場佔約 50-60%，三星約 20-35%（受 HBM3e 良率（合格品比例）波動影響），美光第三且快速成長。HBM 的合約價是傳統 DRAM 的 5-6 倍（以每 GB 計），且供不應求時不像傳統 DRAM 那樣走現貨市場——大客戶（NVIDIA、AMD）用長約鎖量，中小客戶幾乎拿不到貨。

## 判讀方式

HBM 營收佔比是判讀記憶體廠商毛利率走向的關鍵指標。HBM 的 [ASP](/business/knowledge-cards/asp/) 遠高於傳統 DRAM，當廠商把產能轉向 HBM，營收和毛利率會同步上升——但傳統 DRAM 的可用產能下降，可能讓傳統 DRAM 也因為供給減少而漲價。這是產能擠壓的雙向效應。風險面：HBM 的技術疊代快，良率爬坡期的成本高，如果下一代產品良率不如預期（如三星的 HBM3e 良率問題），會直接衝擊毛利率。
