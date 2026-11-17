---
title: "多變量分析的矩陣、主成分與因素分析的選讀書目"
date: 2026-11-17
description: "從樣本共變數矩陣推導多變量方法的教科書、依技術分章並示範軟體輸出與結果撰寫的應用教科書，以及專談探索性因素分析與主成分分析差別的短書，各建立在什麼材料上、依賴哪一代軟體預設值與資料規模，以及讀它們之前要先有的數學與經驗"
weight: 30
tags: ["books", "reading", "statistics", "multivariate-analysis", "factor-analysis"]
---

這一篇收的書討論多個變數一起分析時的計算：p 個變數兩兩之間的離均差交乘積排成的矩陣，以及在這些矩陣上做的主成分分析（principal component analysis，PCA）與因素分析（factor analysis，其他中文資料常寫作因子分析）。三張矩陣記錄的是同一份資訊、差在尺度：離均差平方和與交乘積矩陣（sums of squares and cross-products matrix，SSCP 矩陣）的對角線是各變數的離均差平方和，其餘格子是兩兩變數的離均差交乘積和；整張除以 n−1 是共變數矩陣；每一格再除以對應兩個變數的標準差是相關矩陣。這組計算怎麼從兩個變數的共變數推廣過來，寫在 [研究方法與統計推論書單](/books/research-methods/research-methods-line-guide/) 的四個主題那一節。

主成分分析與因素分析都從共變數矩陣或相關矩陣出發，而兩者對資料的模型不同，所以算出的得分性質也不同。主成分分析把觀測變數加權相加，找出能涵蓋最多總變異的幾組權重；主成分是觀測變數的精確線性組合，每一筆觀測值的主成分得分直接用權重乘上它的觀測值算出，只有一組答案。因素分析（共同因素模型，common factor model）反過來假設每個觀測變數由幾個看不到的共同因素加上這個變數自己的獨特部分組成，只分析各變數共有的那部分變異；因為未知的量（共同因素加上每個變數的獨特部分）比觀測變數多，因素得分（factor score）無法從資料唯一決定，只能估計，迴歸法與 Bartlett 法這幾種估計方法算出的得分彼此不同。分析的目的是把很多變數壓成少數幾個指標時，兩者的差別不大；目的是量出問卷背後的構念時，兩者的差別決定結論。

三本各自討論這組計算的一個層次：Richard Johnson 與 Dean Wichern 的《Applied Multivariate Statistical Analysis》用矩陣代數從樣本共變數矩陣推導出各種多變量方法；Barbara Tabachnick 與 Linda Fidell 的《Using Multivariate Statistics》依技術分章，每一章寫出適用的研究題目、要檢查的假設、軟體輸出怎麼讀、結果怎麼寫；Leandre Fabrigar 與 Duane Wegener 的《Exploratory Factor Analysis》專談探索性因素分析，以及它跟主成分分析的差別在研究上的後果。

先讀哪一本，看讀者要的是推導還是操作。要知道軟體輸出的每一個數字是怎麼從共變數矩陣算出來的，從《Applied Multivariate Statistical Analysis》開始。要決定一份資料該用哪一種技術、跑完怎麼寫結果，讀《Using Multivariate Statistics》。只要判斷主成分分析與因素分析該用哪一個、因素分析的萃取方法、因素數與轉軸（rotation）怎麼選，讀《Exploratory Factor Analysis》，它是三本裡最短的一本。

## 起點書：Applied Multivariate Statistical Analysis

Richard Johnson 與 Dean Wichern 的《Applied Multivariate Statistical Analysis》是多變量統計的標準教科書。全書先用一章複習矩陣代數，再用樣本的幾何說明共變數：把每個變數的 n 個離均差排成一個 n 維向量，兩個向量的內積除以 n−1 就是兩個變數的共變數，兩個向量夾角的餘弦就是相關係數。之後各章從樣本共變數矩陣推導出 Hotelling T² 檢定（t 檢定推廣到平均數向量）、多變量變異數分析、主成分分析、因素分析、典型相關、判別分析與分群。

這本書在這一篇被當成起點書，理由在涵蓋面與它的表示法：散布圖上的離均差乘積、三種矩陣、主成分與因素得分，在這本書裡是同一套矩陣表示法的幾個段落。主成分分析那一章同時示範從共變數矩陣與從相關矩陣出發的結果，讀者看得到選哪一張矩陣會改變主成分；因素分析那一章另有一節討論因素得分的估計方法。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構（整合研究的那一種），它整理的是多變量統計的數學結果，效力來自推導：書中的檢定與信賴區域在資料符合多變量常態分配、觀測值彼此獨立時成立。主成分數目與因素數目的選擇方式（陡坡圖 scree plot、特徵值大於 1）屬於實務慣例，書中把它們當成參考而不是規則。

時效上，**過時的前提是資料的規模**：書中的方法與範例預設觀測值數目遠大於變數數目，資料集是數十到數百筆觀測值、十個左右的變數。今天常見的資料（一筆紀錄帶上百個特徵、或變數數接近觀測值數）不滿足這個預設，樣本共變數矩陣在那種資料上不穩定甚至不可逆，後來發展的正則化（regularization）共變數估計與稀疏主成分分析（sparse PCA）不在書中。

處境相容性上，這本書對應的是 [處境相容性](/books/knowledge-cards/context-compatibility/) 裡樣本數與變數數的比例那一項，以及分析工具那一項：書中的計算不綁特定軟體，讀者要自己把推導對應到手上工具的函式與預設值。推論的章節（檢定、信賴區域、最大概似法因素分析的因素數檢定）另外依賴多變量常態分配，資料明顯偏態時那幾章的機率陳述要打折扣。

讀得出價值的前提有兩項。數學上，讀者要熟悉矩陣乘法、轉置、反矩陣與特徵值，書中第二章的複習只適合用來喚回，不適合第一次學。經驗上，讀者用軟體跑過主成分分析或因素分析，看著輸出的負荷量、特徵值與得分，想知道它們從哪裡來；沒有這個經驗時，書中的推導讀起來沒有要解釋的對象。

第 6 版之後沒有新版次，Pearson 2018 年以 Classic Version 的名義重印平裝。這一輪用「Applied Multivariate Statistical Analysis Johnson Wichern 中譯 應用多變量統計分析」限定博客來、天瓏與三民查不到繁體中文版。簡體中文版《实用多元统计分析》（陈旋、叶俊译，清华大学出版社，2008），豆瓣的簡介註明譯自第 6 版；同一家出版社另有一個同年的英文影印版，兩者容易混淆。

- [Amazon（Applied Multivariate Statistical Analysis，6th edition，Pearson，2007）](https://www.amazon.com/Applied-Multivariate-Statistical-Analysis-6th/dp/0131877151)

## 《Using Multivariate Statistics》：依技術分章的應用教科書

Barbara Tabachnick 與 Linda Fidell 的《Using Multivariate Statistics》是寫給社會科學與心理學研究者的應用教科書。全書先用幾章處理所有技術共用的事：資料矩陣、相關矩陣、共變數矩陣與離均差交乘積矩陣的定義，以及資料清理（遺漏值、極端值、常態性、多元共線性）。之後每一種技術一章，從多元迴歸、多變量變異數分析、判別分析、邏輯斯迴歸，到主成分分析與因素分析、結構方程模型、多層次模型；書末附一份簡短的矩陣代數導論。

這本書在這一篇的用途，是把 Johnson 與 Wichern 的推導接到實際的分析決定上。每一章用固定的結構寫：這個技術適合哪一類研究題目、有哪些限制與要先檢查的假設、基本的計算式與一個小資料集的手算示範、軟體的語法與輸出、以及一份完整的分析範例與結果的寫法。主成分分析與因素分析合寫在同一章，章中說明兩者分析的變異不同，以及什麼研究目的用哪一個。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構（整合研究的那一種）。書中有不少實務建議屬於慣例，讀者要把它們跟數學結果分開讀：例如因素分析的樣本數，書中引用 Comrey 與 Lee 教科書的分級（100 筆差、200 筆尚可、300 筆好、1000 筆極佳），那是教科書作者的經驗分級；MacCallum、Widaman、Zhang 與 Hong 1999 年的模擬研究顯示，需要的樣本數取決於各變數共同性（communality，一個變數的變異裡由共同因素解釋的比例）的高低與每個因素有幾個變數，沒有單一的數字。

時效上，**過時的前提是書中示範的軟體版本**：範例用 SPSS 與 SAS 的語法與輸出，軟體改版時選單、語法與輸出表的排版都會變。這本書歷經多個版次，每一版更新軟體示範；讀者手上的版次跟軟體版本差距越大，照書操作時對不上的地方越多。

處境相容性上，這本書預設的分析工具是 SPSS 與 SAS，預設的資料是心理學與社會科學的問卷與實驗資料。用 R 或 Python 的讀者，推導與決策的部分照讀，操作要自己對應；各軟體因素分析的預設萃取方法與轉軸方式不同，照書上的 SPSS 預設值解讀 R 的輸出會讀錯。

讀得出價值的前提是讀者手上有一份多個變數的資料，要決定用哪一種技術，或要寫一份分析結果給審查者讀。沒有這樣一份資料時，這本書讀起來是一本技術目錄。

第 7 版（2019）是這一輪查到的最新版次，結構方程模型那一章由 Jodie Ullman 執筆；美國版多以活頁裝出版。這一輪用「Using Multivariate Statistics Tabachnick 中譯 多變量統計」限定博客來、天瓏、三民與豆瓣查不到繁體與簡體中文版。

- [Amazon（Using Multivariate Statistics，7th edition，Pearson，2019）](https://www.amazon.com/Using-Multivariate-Statistics-Barbara-Tabachnick/dp/0134790545)

## 《Exploratory Factor Analysis》：探索性因素分析與主成分分析的差別

Leandre Fabrigar 與 Duane Wegener 的《Exploratory Factor Analysis》是牛津大學出版社 Understanding Statistics 系列的一本短書，專談探索性因素分析。書中說明共同因素模型的假設，論證研究目的是找出問卷題目背後的構念時，主成分分析不能代替因素分析；接著逐項討論研究者要做的決定：用哪一種萃取方法、保留幾個因素（平行分析 parallel analysis、陡坡圖、特徵值大於 1 各自的缺點）、用直交（orthogonal）還是斜交（oblique）轉軸。

這本書在這一篇的用途，是把主成分分析與因素分析的差別從模型層次落到研究者的決定上。兩位作者與 MacCallum、Strahan 在 1999 年發表的論文檢視了 Journal of Personality and Social Psychology 與 Journal of Applied Psychology 兩本期刊在 1991 到 1995 年間的因素分析研究，發現許多研究用主成分分析加上特徵值大於 1 與直交轉軸——那正是當時常用統計軟體的預設組合——而沒有說明理由；這本書是那篇論文的延伸，寫給要自己做這幾個決定的研究者。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構，加上 1999 年那篇論文對已發表研究做法的調查。書中的建議（偏好共同因素模型、偏好斜交轉軸、用平行分析決定因素數）有模擬研究支持，而它們是心理計量學界一派的立場：Velicer 與 Jackson 1990 年的論文主張，在多數實際資料上主成分分析與因素分析得出的負荷量型態相近，選哪一個的實際後果比這一派說的小。讀者要知道兩邊的論證都存在，再依自己的研究目的判斷。

時效上，**過時的前提是統計軟體的預設值**：書中批評的是 SPSS 長期的預設組合。R 的 psych 套件預設的萃取方法是最小殘差法、轉軸是斜交的 oblimin，跟書中批評的組合不同；用這類工具的讀者，書中針對預設值的那部分批評沒有對象，關於每一個決定該怎麼做的論證照樣適用。

處境相容性上，這本書預設變數是用多個題目量構念的問卷資料，這是 [處境相容性](/books/knowledge-cards/context-compatibility/) 裡變數的測量方式那一項。分析的全部是直接觀測的量（各項系統指標、各項成本），目的只是把它們壓成少數幾個綜合指標時，主成分分析就是合適的工具，書中反對用主成分分析的論證不適用。

讀得出價值的前提是讀者跑過一次探索性因素分析、而且沿用了軟體的預設值，或即將發展一份問卷量表。沒有這類經驗的讀者，書中每一個決定的取捨讀起來沒有對照。

這一輪用「Fabrigar Wegener Exploratory Factor Analysis 探索性因素分析 中译」限定豆瓣，以及「探索性因子分析 法布里加 韦格纳」查不到繁體與簡體中文版。

- [Amazon（Exploratory Factor Analysis，Oxford University Press，2012 平裝）](https://www.amazon.com/Exploratory-Factor-Analysis-Understanding-Statistics/dp/0199734178)

## 多變量分析各書的分工與沒收錄的線性代數教科書

這三本各自討論不同的層次：《Applied Multivariate Statistical Analysis》討論每一個多變量方法怎麼從共變數矩陣推導出來，《Using Multivariate Statistics》討論分析資料時怎麼選技術、檢查假設與寫結果，《Exploratory Factor Analysis》只討論因素分析的決定，而且討論得最深。三本對主成分分析與因素分析的差別給出一致的說明，差別在推導的深度與落到操作的程度。

線性代數本身還沒有收書。Johnson 與 Wichern 那本要讀者熟悉矩陣運算，而它的複習章只適合喚回；要不要另收一本線性代數教科書、或只連一門公開課，記在 [研究方法與統計推論書單](/books/research-methods/) 的 Backlog 段。

## 多變量分析的相鄰主題與接續閱讀

這一篇的矩陣從兩個變數的共變數與相關推廣而來，那組計算收在 [統計推論與迴歸的選讀書目](/books/research-methods/inference-and-regression/)。

因素分析只描述變數背後有幾個構念時，叫探索性因素分析；研究者先寫下哪幾個題目量哪一個構念、再檢驗資料符不符合，是驗證性因素分析，它與構念之間的路徑一起構成結構方程模型，收在 [結構方程模型與潛在變數的選讀書目](/books/research-methods/structural-equation-modeling/)。
