---
title: "統計推論與迴歸的選讀書目"
date: 2026-11-17
description: "變異、共變、相關、兩組平均數的差異與信賴區間的概念入門，把這幾種比較統一成迴歸模型的應用教科書，以及用台灣學界的中文術語示範 SPSS 與 R 操作的教科書，各建立在什麼材料上、依賴哪一代軟體與報告慣例，以及讀它們之前要先有的經驗"
weight: 10
tags: ["books", "reading", "statistics", "regression", "hypothesis-testing"]
---

這一篇收的書討論從資料算出一個比較、並判斷那個比較有多少是抽樣造成的計算：變異數（variance）、共變數（covariance）與相關係數（correlation coefficient），兩組平均數的差與它的信賴區間（confidence interval），以及把這幾種比較寫成同一種模型的線性迴歸（linear regression）。三本各自討論這組計算的一個層次：David Freedman、Robert Pisani 與 Roger Purves 的《Statistics》幾乎不用公式，建立每一個統計量代表什麼、什麼時候能用；Andrew Gelman、Jennifer Hill 與 Aki Vehtari 的《Regression and Other Stories》把兩組比較、相關與多個預測變數放進同一個迴歸模型，並用 R 示範；邱皓政的《量化研究與統計分析》用台灣學界通行的中文術語，示範同一組計算在 SPSS 與 R 裡怎麼跑、輸出表怎麼讀。

先讀哪一本，看讀者要的是哪一層。要知道相關係數、信賴區間與顯著性檢定各自代表什麼，從《Statistics》開始。已經懂這些概念、要自己建模型分析資料，讀《Regression and Other Stories》。要寫中文的研究報告或論文、跟用中文術語的同事或審查者溝通，讀邱皓政那本。不確定時從《Statistics》開始：《Regression and Other Stories》與邱皓政那本都假設讀者已經知道抽樣誤差是什麼。

## 起點書：Statistics（Freedman、Pisani、Purves）

David Freedman、Robert Pisani 與 Roger Purves 的《Statistics》是三位加州大學柏克萊分校的統計學者為沒有數學背景的大學生寫的教科書。全書用文字、圖與數值例子取代公式推導，從實驗設計開始（受控實驗與觀察研究的差別），接著是描述統計、相關與迴歸、機率、抽樣、抽樣誤差，最後是信賴區間與顯著性檢定。書中把相關係數定義成兩個變數各自換成標準單位（減掉平均數、再除以標準差）之後乘積的平均：一個點落在兩個平均數劃出的右上或左下象限時乘積為正，落在左上或右下象限時乘積為負，全部乘積的平均就是相關係數。這正是散布圖用兩個平均數切成四個象限、看離均差乘積正負的那一套計算，只是先標準化。

這本書在這一篇被當成起點書，理由在涵蓋面：一般統計課板書上的每一項——離均差、共變、相關、兩組平均數差的標準誤（standard error）、t 分配、信賴區間、虛無假設（null hypothesis）——它都講到，而且講的是每一項的意義與適用條件，而不是公式。書的後段有整章討論顯著性檢定被誤用的情形：顯著跟重要是兩回事、資料先看過再挑檢定、檢定結果不能證明研究者主張的那個機制。這幾項批評跟美國統計學會 2016 年對 p 值的聲明方向一致，而這本書比那份聲明早出版。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構（整合研究的那一種）：書中的統計結果繼承數學推導的效力，但書不寫推導，只寫結論與適用條件；範例取自實際的研究，例如小兒麻痺疫苗的大規模臨床試驗與柏克萊研究所入學的性別比較。書中用柏克萊入學那一例說明辛普森悖論（Simpson's paradox）：全校合計時男性錄取率較高，分系看時多數系所的女性錄取率不低於男性，差別來自女性多申請錄取率低的系所。這個例子直接連到 [研究設計與因果推論的選讀書目](/books/research-methods/research-design/) 討論的混淆。

時效上，**過時的前提是計算環境**：全書假設讀者用手算與查常態分配表，沒有任何軟體操作，多元迴歸只簡短帶過。第一作者 Freedman 2008 年過世，第四版（2007）是最後一版。概念的部分不受計算環境影響；要動手分析資料的讀者，操作要從《Regression and Other Stories》、邱皓政那本或軟體文件補。書中把 t 檢定當成小樣本時對常態近似的修正，這個講法對應的是查表年代的慣例，讀者照 [研究方法與統計推論書單](/books/research-methods/research-methods-line-guide/) 說明的 t 分配適用條件讀就不會誤用。

處境相容性上，全書的推論建立在作者稱為 box model 的抽籤模型上：抽籤模型把資料看成從一個裝著號碼票的箱子裡隨機抽出的票。書中要求讀者在用任何檢定之前，先判斷資料像不像這樣抽出來的——這正是 [處境相容性](/books/knowledge-cards/context-compatibility/) 裡觀測值獨立性那一項。資料是同一位使用者的多筆紀錄、或同一個選區的多位選民時，抽籤模型不成立，書中的標準誤公式算出的值會偏小。

讀得出價值的前提是手上有一個要解讀的數字：一份報告裡的 p 值或信賴區間、一次 A/B 測試的結果、一篇論文寫的「兩者顯著相關」。帶著那個數字讀，每一章都在說明它代表什麼；沒有那個數字時，抽籤模型讀起來像一組抽象的練習題。數學上只要求代數。

第四版之後沒有新版次。這一輪用「Freedman Pisani Purves 統計學 繁體中文 譯本」限定博客來、天瓏與三民查不到繁體中文版；簡體中文版《统计学》（魏宗舒等譯，中國統計出版社，1997）譯自較早的版次，不是第四版，這一筆只在豆瓣的書目看到。

- [Amazon（Statistics，4th edition，W. W. Norton，2007）](https://www.amazon.com/Statistics-4th-David-Freedman/dp/0393929728)

## 《Regression and Other Stories》：把各種比較寫成迴歸模型的應用教科書

Andrew Gelman、Jennifer Hill 與 Aki Vehtari 的《Regression and Other Stories》是一本以迴歸為中心的應用統計教科書。Gelman 是哥倫比亞大學統計系與政治學系的教授，書中的範例大量取自政治學、經濟學與公共衛生的實際資料。它改寫自 Gelman 與 Hill 2007 年的《Data Analysis Using Regression and Multilevel/Hierarchical Models》的前半部，涵蓋線性迴歸、邏輯斯迴歸（logistic regression）與廣義線性模型（generalized linear model）、模型檢查，以及用迴歸做因果推論的基礎；多層次模型（multilevel model，同一個單位有多筆觀測值時用的模型）留給續作。全書用模擬呈現不確定性：從估計出的模型反覆抽樣，看預測值或係數的分布，取代只看一個 p 值。

這本書在這一篇的用途，是把《Statistics》分開介紹的幾種比較放進同一個模型。兩組平均數的比較寫成對一個 0／1 組別變數的迴歸，係數就是兩組的差；相關寫成標準化之後的迴歸斜率；再加入其他預測變數，就是在控制那些變數之下比較。讀者讀完會看到 t 檢定、相關與多元迴歸是同一個線性模型的幾種特例，這是後面多變量分析與結構方程模型的共同起點。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構（整合研究的那一種），範例多來自作者自己的應用研究。實務建議的部分（變數要不要先轉換、怎麼呈現不確定性、少用顯著性檢定下結論）是作者的研究經驗與立場，書中寫出了理由，但讀者要知道那是一派主張：Gelman 長期批評以 p 值門檻判定研究結果的做法。

時效上，**過時的前提是軟體版本**：書中的範例用 R 與 rstanarm 套件（經由 Stan 做貝氏估計），程式碼放在作者維護的線上範例庫。套件改版會讓書上印的語法與輸出跟讀者跑出來的不同，以線上範例庫為準。報告慣例上，這本書出版於 2020 年，它對 p 值的立場跟 2016 年之後的審稿趨勢一致。

處境相容性上，這本書預設讀者用 R，而且估計方式預設貝氏（Bayesian，搭配弱資訊的先驗分布 prior distribution）。讀者所在的報告環境要求頻率學派（frequentist）的 p 值與標準誤時，要自己把書中的輸出對應回最小平方法的結果。觀測值獨立性那一項上，同一個單位有多筆紀錄的資料要用多層次模型，而這本書把多層次模型留給續作，這類資料的讀者讀到這本書的結尾時還沒有拿到需要的工具。

讀得出價值的前提是讀者讀過一本統計入門（《Statistics》或同等的課程），而且自己跑過一次迴歸、對係數代表什麼或該不該相信它有過疑問；另外要會基本的 R。沒跑過迴歸的讀者讀這本書，會把它讀成一本 R 的操作書。

作者在範例網站提供全書的線上 PDF，限個人閱讀，網站註明已取得 Cambridge University Press 的同意；作者請讀者連結網站而不要直接連 PDF，因為勘誤放在網站上。這一輪用「Regression and Other Stories 中文版 OR 中译 回归 格尔曼」查不到繁體與簡體中文版。

- [作者的範例網站（Regression and Other Stories 的範例程式碼、全書 PDF 與勘誤）](https://avehtari.github.io/ROS-Examples/)
- [Amazon（Regression and Other Stories，Cambridge University Press，2020 平裝）](https://www.amazon.com/Regression-Stories-Analytical-Methods-Research/dp/1107676517)

## 邱皓政《量化研究與統計分析》：台灣學界的中文術語與 SPSS、R 操作

邱皓政的《量化研究與統計分析》是台灣大學部與研究所量化方法課常用的中文教科書。全書從量化研究的設計與測量開始，依序是描述統計、抽樣與假設檢定、卡方檢定、t 檢定、變異數分析、相關與迴歸、多元迴歸、中介與調節效果，後段有量表發展、項目分析與信度估計、探索性因素分析（exploratory factor analysis）與驗證性因素分析（confirmatory factor analysis）各一章。分析以 SPSS 為主、R 為輔，多數章節並列兩種軟體的操作步驟與輸出表的讀法。

這本書在這一篇的用途在語言與報告環境。《Statistics》與《Regression and Other Stories》是英文，讀者讀完拿到的是英文術語；在台灣寫論文或研究報告時，指導教授與審查者用的是這本書這一套中文術語與輸出表格式（因素分析、信度係數、標準化迴歸係數這些詞與它們在表格裡的位置）。這本書的後段也是多變量分析與結構方程模型兩篇的中文入口：讀者先用它的因素分析兩章對照中文術語，再讀那兩篇收的英文教科書。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構（整合研究的那一種）。書中的判讀標準（信度係數、因素負荷量要多高才算可以接受）多屬學界慣例，照 [研究方法與統計推論書單](/books/research-methods/research-methods-line-guide/) 說明的數學結果與實務建議分開讀。

時效上，**過時的前提是 SPSS 的版本**：六版（2019）的 SPSS 範例以當時的版本示範，SPSS 之後的版本陸續改動對話框與輸出（例如 t 檢定的輸出加入了效果量），照書操作時畫面可能對不上；R 的部分隨套件改版，同樣以讀者手上的版本為準。這本書至今沒有七版，五南持續以六版再刷。

處境相容性上，這本書預設的分析工具是 SPSS，報告慣例是台灣社會科學與管理學界的論文格式。讀者在工程團隊裡用 Python 分析產品資料時，書中的操作步驟用不上，概念與術語的部分照讀。

讀得出價值的前提是讀者要用中文寫一份帶統計分析的論文或報告，或要跟用中文術語的同事、審查者溝通；只讀英文文獻、用英文工作的讀者，這本書跟那兩本英文教科書重疊的部分多於它補上的部分。

這本書是中文原著，Amazon 查不到英譯本，不附英文版連結。簡體字版《量化研究與統計分析：SPSS與R數據分析範例解析》2024 年由重慶大學出版社出版，這一筆取自三民的商品描述。

- [三民（量化研究與統計分析：SPSS與R資料分析範例解析，六版，五南，2019）](https://www.sanmin.com.tw/product/index/007175043)

## 統計推論與迴歸各書的分工與沒收錄的軟體操作手冊

這三本各自討論不同的層次：《Statistics》討論每一個統計量的意義與適用條件，《Regression and Other Stories》討論怎麼把比較建成模型並呈現不確定性，邱皓政那本討論同一組計算在中文學術環境裡怎麼操作與報告。《Statistics》與《Regression and Other Stories》是英文、互相銜接；邱皓政那本的內容跟它們有重疊，收它的理由在語言與報告環境：在台灣寫論文或研究報告的讀者，審查者用的是那一套中文術語與輸出表格式。

沒收錄的最大一類是整本教軟體選單操作的手冊：一章一個檢定，寫出點哪幾個選單、輸出表在哪裡，而不寫那個檢定在什麼條件下不能用。照[書單怎麼描述一本書](/books/describing-a-book/#收錄與排除的規則)的判斷標準，這類書沒有交代自己的適用邊界；這是類別級的排除，遇到具體某一本時翻目錄找有沒有討論假設與違反假設的章節。Kosuke Imai 的《Quantitative Social Science: An Introduction》以政治學資料與 R 示範同一組計算，本書單未評估它跟《Regression and Other Stories》的內容重疊程度：兩本都以社會科學資料示範 R，要比對章節才判得出角色是否相同。

## 統計推論與迴歸的相鄰主題與接續閱讀

迴歸係數在什麼設計下可以解讀成因果效果，收在 [研究設計與因果推論的選讀書目](/books/research-methods/research-design/)。

變數從兩個變成多個時，這一篇的共變數與相關排成矩陣，在矩陣上做的主成分分析與因素分析收在 [多變量分析的矩陣、主成分與因素分析的選讀書目](/books/research-methods/multivariate-matrices/)。

A/B 測試的樣本量計算與多重比較校正，站上的整理在 [A/B Test 的統計基礎](/devops/monitoring/08-business-analytics/ab-test-statistics/)；顯著性檢定的兩種錯誤在 [Type I error：統計學給假陽性的編號](/til/terms/type-i-error/) 與 [Type II error：統計學給假陰性的編號](/til/terms/type-ii-error/)。
