---
title: "研究設計與因果推論的選讀書目"
date: 2026-11-17
description: "以隨機分派、迴歸不連續設計、差異中的差異等設計組織因果推論的計量經濟學入門、在產品上跑線上實驗的實務書、主張質性與量化研究共用一套推論邏輯的政治學方法論著作，以及用因果圖寫出假設的科普書，各建立在什麼材料上、哪些章節的方法已經被後續研究修正，以及讀它們之前要先有的經驗"
weight: 20
tags: ["books", "reading", "research-methods", "causal-inference", "experiments"]
---

這一篇收的書討論資料用什麼方式產生，觀察到的關聯才能解讀成因果。兩個變數一起變動，可能是其中一個影響另一個，也可能是第三個變數同時影響兩者，或是資料只收進了某一種人；只看 [統計推論與迴歸的選讀書目](/books/research-methods/inference-and-regression/) 收的那些計算的結果，研究者分辨不出是這幾種情形的哪一種，分辨的依據是設計。這一篇收的書各自討論設計的一個面向：Joshua Angrist 與 Jörn-Steffen Pischke 的《Mastering 'Metrics》以隨機分派、迴歸、工具變數、迴歸不連續設計（regression discontinuity design，其他中文資料常寫作斷點迴歸）、差異中的差異五種工具組織全書，討論研究者控制得了與控制不了分派時各用什麼設計；Ron Kohavi、Diane Tang 與 Ya Xu 的《Trustworthy Online Controlled Experiments》討論在網站與 App 上跑線上實驗（A/B 測試）時，實驗結果在哪些環節會失真；Gary King、Robert Keohane 與 Sidney Verba 的《Designing Social Inquiry》從政治學出發，主張質性與量化研究共用同一套推論邏輯；Stephen Van Evera 的《Guide to Methods for Students of Political Science》把個案研究裡的證據依它能不能推翻、能不能確立一個假設分級，讓讀者判斷一本以幾個案例論證的書，證據有多強；Judea Pearl 與 Dana Mackenzie 的《The Book of Why》用因果圖寫出「這個關聯在什麼假設下是因果」。

先讀哪一本，看讀者手上的資料怎麼來。資料是觀察來的（研究者決定不了誰接受處理），從《Mastering 'Metrics》開始。要在自己的產品上跑實驗、或要判斷一份 A/B 測試報告可不可信，讀《Trustworthy Online Controlled Experiments》。研究對象只有少數幾個案例（幾個國家、幾家公司、幾次選舉），讀《Designing Social Inquiry》；已經讀完它、手上正在讀一本以案例論證的書，要判斷書中每一項證據的分量，讀 Van Evera 那本的前兩章。要把「我認為哪些變數影響哪些變數」畫出來、再判斷該控制哪些變數，讀《The Book of Why》。不確定時從《Mastering 'Metrics》開始：它的第一章就是隨機實驗，後面四章是隨機實驗做不到時的替代設計。

## 起點書：Mastering 'Metrics

Joshua Angrist 與 Jörn-Steffen Pischke 的《Mastering 'Metrics》是一本計量經濟學的入門書，以五種估計因果效果的工具組織全書，作者把它們稱為 Furious Five：隨機分派（randomized trials）、迴歸、工具變數（instrumental variables）、迴歸不連續設計（regression discontinuity）與差異中的差異（differences-in-differences）。每一章用一兩個已發表的實證研究示範一種工具，例如用健康保險的隨機實驗示範隨機分派，用美國法定飲酒年齡 21 歲這個門檻前後的死亡率示範迴歸不連續設計。Angrist 是 2021 年諾貝爾經濟學獎的共同得主之一，獲獎理由是他對因果關係分析的方法論貢獻。

這本書在這一篇被當成起點書，理由在涵蓋面：它把研究者能做的設計排成一個序列，以隨機實驗為標準，其餘每一種設計都在做不了隨機實驗時，用資料裡的某一個特徵替代隨機分派。迴歸不連續設計靠的是一條規則劃出的門檻（剛好過線與剛好沒過線的人，其他條件相近），差異中的差異靠的是兩組在處理之前的趨勢相同。讀者讀完，手上有一組問句可以拿去檢查任何一份觀察研究：這個設計用什麼替代了隨機分派，那個替代的假設在這份資料裡成不成立。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構（整合研究的那一種）：書中的每一種工具都由一份已發表的實證研究示範，它繼承那些研究的效力，也繼承它們的限制。方法本身的數學推導放在各章的附錄，正文以文字與圖為主。

時效上，**過時的前提是差異中的差異那一章的估計方式**：書中示範的是兩組、處理前後兩期的基本形式，以及用雙向固定效果（two-way fixed effects）迴歸把它推廣到多組多期。2018 年之後的計量經濟學研究（例如 Goodman-Bacon 2021 年的論文）指出，各組在不同時間點接受處理時，雙向固定效果迴歸的估計值可能是各組效果的加權平均，而權重可能是負的。基本形式的邏輯照樣成立；要把它用在各組處理時間不同的資料上，要讀這批 2018 年之後的方法論文。

處境相容性上，這本書的範例全部是美國的教育、健康與勞動政策，而每一種設計都依賴一個制度上的特徵：抽籤入學、法定年齡門檻、各州在不同年份修法。讀者的環境裡有對應的制度特徵時，那一章的設計才用得上。工程師用得上的多半是第一章：A/B 測試就是隨機分派，那一章直接適用；產品用一個分數門檻分派功能（分數過線的使用者才拿到）時，迴歸不連續設計那一章也適用。

讀得出價值的前提是讀者遇過一次「這兩個數字一起變動，但不知道能不能說是因果」：一份報告說用了某功能的使用者留存率較高、一則新聞說喝咖啡的人比較長壽。帶著那個疑問讀，五種工具各自是判斷它的一種方法；沒有那個疑問時，書中的設計讀起來像幾個不相關的技巧。迴歸的基礎在書中第二章就教，不必先讀別的書。

這一輪用「Mastering 'Metrics 繁體中文 譯本」與「精通計量」限定博客來、天瓏與三民查不到繁體中文版。簡體中文版有兩個譯本，譯者都是郎金焕：《精通计量：从原因到结果的探寻之旅》（2019）與《精通计量：因果之道》（2021，上海人民出版社與格致出版社），兩筆取自豆瓣；2019 那一版三民有上架，商品頁記的出版社跟豆瓣不同，這一輪沒有核對是哪一個。

- [三民（精通计量：从原因到结果的探寻之旅，郎金焕譯，簡體中文版，2019）](https://www.sanmin.com.tw/product/index/007227024)
- [Amazon（Mastering 'Metrics: The Path from Cause to Effect，Princeton University Press，2014 平裝）](https://www.amazon.com/Mastering-Metrics-Path-Cause-Effect/dp/0691152845)

## 《Trustworthy Online Controlled Experiments》：線上實驗結果失真的環節

Ron Kohavi、Diane Tang 與 Ya Xu 的《Trustworthy Online Controlled Experiments》是三位分別在 Microsoft、Google 與 LinkedIn 主持實驗平台的作者，整理大型網站跑線上實驗（A/B 測試）的做法。書中著重的是實驗結果在哪些環節會失真，顯著性的計算只佔一小部分：兩組分到的使用者人數比例跟設定的不同（sample ratio mismatch），代表分派或紀錄出了錯；兩組其實相同的 A/A 測試，用來檢查平台本身會不會製造假的差異；一個看起來好得不尋常的結果，多數時候是錯的（作者稱為 Twyman's law）；以及要用哪一個指標當實驗的主要判定依據、哪些指標當不能變差的護欄。

這本書在這一篇的用途，是把隨機分派從教科書的一章展開成一套運作中的系統。《Mastering 'Metrics》把隨機實驗當成標準，假設分派是隨機的、結果的量測是正確的；這本書討論的正是分派與量測這兩個假設在一個同時跑許多實驗的平台上怎麼被破壞，以及怎麼偵測。

[證據來源](/books/knowledge-cards/evidence-provenance/)是跨組織案例加理論建構：材料是作者在幾家大型網路公司的實驗紀錄，以敘述與實例呈現，書中引用的實驗多數沒有公開原始資料。它支持得了「這幾種失真在大型平台上發生過、偵測方法有效」，而讀者的平台會不會發生同樣的失真，要用書中的檢查自己驗。

時效上，這本書 2020 年出版，這一輪沒有找到它的論證依賴已經改變的條件。最可能先改變的是使用者識別：沒有登入的使用者靠瀏覽器的 cookie 分組，瀏覽器限制 cookie 的保存期限時，同一位使用者留在同一組的時間會縮短，書中以使用者為單位的分析要先確認這一點。

處境相容性上，這本書預設的環境是流量大的產品：書中的作者所在的平台，每個實驗有數十萬以上的使用者，才偵測得到千分之幾的效果。偵測得到的最小效果跟樣本數的平方根成反比，樣本少一百倍，效果要大十倍才偵測得到；使用者只有幾千人的產品，書中偵測千分之幾效果的那些做法在這種產品上沒有足夠的樣本。觀測值獨立性那一項上，書中專門討論了使用者之間互相影響的情形（社群網路、雙邊市場），那時兩組不獨立，標準的分析會算錯效果。

讀得出價值的前提是讀者跑過、或讀過一次 A/B 測試的結果，並對結果有過懷疑（例如一個小改動帶來不合理的大幅提升）；或即將負責建立實驗平台。沒有接觸過線上實驗的讀者，書中的檢查清單讀起來沒有對應的經驗。

這一輪用「Trustworthy Online Controlled Experiments 繁體中文版 A/B 測試 科哈維 譯」限定博客來、天瓏、三民、誠品與 Readmoo 查不到繁體中文版。簡體中文版《关键迭代：可信赖的线上对照实验》（韩玮等譯，機械工業出版社，2021），作者的官方網站放了中文版的第一章。

- [天瓏（关键迭代：可信赖的线上对照实验，簡體中文版，機械工業出版社，2021）](https://www.tenlong.com.tw/products/9787111678809)
- [Amazon（Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing，Cambridge University Press，2020 平裝）](https://www.amazon.com/Trustworthy-Online-Controlled-Experiments-Practical/dp/1108724264)

## 《Designing Social Inquiry》：質性與量化研究共用的推論邏輯

Gary King、Robert Keohane 與 Sidney Verba 的《Designing Social Inquiry》是一本政治學方法論的著作，常以三位作者的姓氏縮寫 KKV 稱呼。書的主張是質性研究與量化研究共用同一套推論邏輯：不論研究的是三個國家的歷史還是三萬份問卷，描述性推論與因果推論都要面對同樣的偏誤來源——只挑結果出現的案例來研究（按依變數的值選樣，selecting on the dependent variable）、遺漏同時影響原因與結果的變數（遺漏變數，omitted variable）、原因與結果互相影響、測量誤差。書中的建議是質性研究者也要盡量增加可觀察的含意，讓一個理論有更多機會被資料推翻。

這本書在這一篇的用途，是說明為什麼政治學要上方法論。政治學的研究對象多半無法隨機分派：研究者不能隨機決定哪些國家民主化、哪些選民受高等教育。在這種處境裡，結論能不能被檢驗，主要看研究設計，而 KKV 把這件事寫成一套檢查。工程師讀它的用途在少數案例的推論：「導入 X 的三家公司都成功了」這類論證，正是書中按依變數的值選樣與遺漏變數兩章討論的形態。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構：把量化方法的推論原則整理成一套適用於質性研究的規範，範例取自政治學的已發表研究。它的規範主張有爭議：Henry Brady 與 David Collier 編的《Rethinking Social Inquiry》（2004）回應這本書，論證質性研究另有它的推論工具（例如追蹤一個案例內部的因果過程），不必照量化研究的模板增加觀測值。讀這本書時，把它對量化推論的整理當成共識，把它對質性研究的處方當成一方的主張，另一方的論證在那本回應裡。

時效上，**過時的前提是政治學方法的版圖**：這本書出版於 1994 年，之後政治學大量轉向實驗與自然實驗，質性方法也發展出過程追蹤（process tracing）與集合論方法（set-theoretic methods）這類自己的系統。書中定義因果效果的方式（比較同一個單位在原因取不同值時的結果）沒有過時，而它對質性研究者的建議，是在那兩股發展之前提出的。

處境相容性上，這本書預設研究者只能觀察、案例數不多，這是政治學與國際關係最常見的處境。讀者能跑隨機實驗時，書中大半的設計建議沒有對象，讀《Mastering 'Metrics》的第一章與線上實驗那本就夠。

讀得出價值的前提是讀者做過、或評估過一次從少數案例推出的論證：比較幾個國家、幾家公司、幾次專案的成敗，然後下結論。帶著那個論證讀，書中的每一種偏誤都能拿去檢查它；沒有這類經驗的讀者，這本書讀起來像一套抽象的規範。

繁體中文版《好研究如何設計？：用量化邏輯做質化研究》（盛智明、韓佳譯，群學，2012）依 1994 年的原版翻譯；這一輪在三民與天瓏查不到它的商品頁，連結用博客來。簡體中文版《社会科学中的研究设计》（陈硕译，格致出版社，2014），2023 年出了增订版，這兩筆取自豆瓣。英文版 2021 年出了新版，加上 Keohane 與 King 的新序。

- [博客來（好研究如何設計？：用量化邏輯做質化研究，盛智明、韓佳譯，群學，2012）](https://www.books.com.tw/products/0010568250)
- [Amazon（Designing Social Inquiry，New Edition，Princeton University Press，2021 平裝）](https://www.amazon.com/Designing-Social-Inquiry-Scientific-Qualitative/dp/0691224625)

## 《The Book of Why》：用因果圖寫出因果推論的假設

Judea Pearl 與 Dana Mackenzie 的《The Book of Why》是 Pearl 為一般讀者寫的因果推論科普書。Pearl 是電腦科學家，發展了以因果圖（causal diagram，用箭頭表示哪個變數影響哪個變數）為基礎的因果推論框架。書中把因果推論分成三層，稱為因果階梯（ladder of causation）：觀察到的關聯（association）、介入（intervention）之後的結果（如果把某個變數設成某個值，會怎樣）、反事實（counterfactual，如果當初不是這樣，會怎樣），並論證只有關聯的資料推不出介入與反事實這兩層的結論，要加上一張因果圖寫出的假設。書中用因果圖解釋了什麼時候該控制一個變數、什麼時候控制它反而製造偏誤，以及辛普森悖論為什麼會發生。

這本書在這一篇的用途，是給讀者一種寫出假設的語言。《Mastering 'Metrics》的每一種設計都依賴一個假設（工具變數只透過處理影響結果、兩組處理前的趨勢相同），因果圖把這類假設畫成看得見的箭頭，讀者可以對著圖問少了哪一條箭頭。書中也回顧了 Sewall Wright 在 1920 年代提出的路徑分析（path analysis），那是 [結構方程模型與潛在變數的選讀書目](/books/research-methods/structural-equation-modeling/) 收的結構方程模型的前身。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構：書中的方法有數學基礎，Pearl 的技術論文與專書給了推導，這本書是它的通俗版。要特別標出來的是立場：這本書在介紹自己的框架時，對統計學與計量經濟學傳統的潛在結果框架（potential outcomes，《Mastering 'Metrics》用的那一套）評價偏低。Guido Imbens 2020 年在 Journal of Economic Literature 的論文比較了兩套框架，說明為什麼經濟學的實證研究者多數仍用潛在結果框架；讀者要兩邊的論證時，那篇論文是另一方。

時效上，**過時的前提是書末對人工智慧的判斷**：這本書出版於 2018 年，最後一章討論機器能不能做因果推理，那時的機器學習以模式辨識為主，大型語言模型還沒有出現。那一章關於機器做得到與做不到什麼的判斷，要放在出版當時的技術背景下讀。前面各章的因果推論方法不受影響。

處境相容性上，因果圖的方法不依賴特定的制度或資料來源，適用於實驗與觀察資料；它依賴的是讀者對這個領域的知識，因為圖要由研究者畫，資料本身畫不出來。讀者對研究對象的機制所知有限時，畫出的圖只是把猜測寫成箭頭，書中的推論會繼承那些猜測的錯誤。

讀得出價值的前提是讀者聽過「相關不等於因果」，而想知道在什麼條件下相關可以等於因果；或遇過一次加入一個控制變數之後結論反轉的分析。沒有這類經驗的讀者，會把這本書讀成一部統計思想史。

繁體中文版《因果革命：人工智慧的大未來》（甘錫安譯，行路，2019）；這一輪在三民只查到簡體版、在天瓏沒看到商品頁網址，連結用博客來。簡體中文版《为什么：关于因果关系的新科学》（江生、于华译，中信出版集团，2019），這一筆取自豆瓣。Amazon 另列有一個 2026 年 10 月的英文修訂版，描述寫加了新序與近年進展的摘要；這一輪沒有在出版社的頁面看到它，書末那一章的時效判定是否因此改變，等核對過修訂版再判。

- [博客來（因果革命：人工智慧的大未來，甘錫安譯，行路，2019）](https://www.books.com.tw/products/0010825178)
- [Amazon（The Book of Why: The New Science of Cause and Effect，Basic Books，2020 平裝）](https://www.amazon.com/Book-Why-Science-Cause-Effect/dp/1541698967)

## 《Guide to Methods for Students of Political Science》：個案研究證據的分級

Stephen Van Evera 的《Guide to Methods for Students of Political Science》是一本寫給政治學研究生的短書，作者是麻省理工學院政治系的榮譽教授。前兩章談方法：第一章說明假設、理論與檢驗，第二章說明怎麼用個案研究檢驗與建立理論、怎麼挑案例，介紹控制比較（controlled comparison）、一致性程序（congruence procedure）與過程追蹤三種用個案檢驗理論的做法；後面幾章是寫學位論文的建議。書中把用來檢驗一個假設的證據依兩個問題分級：這項證據沒出現時，假設是否就被推翻；這項證據出現時，假設是否就被確立。兩個答案組合出四種檢驗，後來的過程追蹤文獻沿用 Van Evera 給的英文名字，中文資料沒有固定的譯名：沒出現就推翻、出現也不足以確立的叫 hoop test（假設必須跳過的一道圈）；出現就足以確立、沒出現也推翻不了的叫 smoking-gun test（確鑿的證據）；兩者都成立的叫 doubly decisive test；兩者都不成立的叫 straw-in-the-wind test（只看得出風向）。

這本書在這一篇的用途，是給讀者一組分辨證據分量的問題。一般讀者讀到的政治學專書多數以幾個國家或幾段歷史論證，KKV 提醒的是案例怎麼挑、有沒有對照；這本書補的是案例內部的證據：作者引用的那一段史料，如果不存在，他的論點會不會倒；如果存在，能不能排除其他解釋。只屬於 straw-in-the-wind 那一級的證據，讀起來再生動，也只是讓假設的可信度高一點。

[證據來源](/books/knowledge-cards/evidence-provenance/)是理論建構：作者把政治學個案研究的做法整理成一套檢驗的分類，範例取自國際關係的研究。

時效上，**過時的前提是過程追蹤的方法發展**：這本書出版於 1997 年，過程追蹤（process tracing：在一個案例內部，逐步檢查因果機制每一環的證據）在那之後發展成一套有專書的方法，研究者也用機率推理把四種檢驗寫得更精確。書中的四種檢驗是那些發展的起點，讀者要的是判讀時的問題，這兩章就夠；要自己做過程追蹤研究，要讀後來的專書。

處境相容性上，這本書預設讀者是寫學位論文的政治學研究生，後半的論文寫作建議對一般讀者沒有對象，只讀前兩章即可。前兩章的檢驗分類不依賴特定的國家或資料來源。

讀得出價值的前提是讀者正在讀、或讀過一本以少數案例論證的書，對它的某一段證據有過懷疑。沒有這樣一本書在手上時，四種檢驗讀起來是抽象的分類。

簡體中文版《政治学研究方法指南》（陈琪譯，北京大學出版社，2006），這一筆取自豆瓣；這一輪用「Van Evera Guide to Methods 繁體中文 譯本 政治學方法論 研究方法」查不到繁體中文版。Amazon 有一筆列表標示這本缺貨。

- [Amazon（Guide to Methods for Students of Political Science，Cornell University Press，1997 平裝）](https://www.amazon.com/Guide-Methods-Students-Political-Science/dp/080148457X)

## 研究設計與因果推論各書的分工與沒收錄的實地實驗專書

這幾本各自討論設計的不同面向：《Mastering 'Metrics》討論做不了隨機實驗時的替代設計，《Trustworthy Online Controlled Experiments》討論做得了隨機實驗時結果在哪裡失真，《Designing Social Inquiry》討論只有少數案例時的推論規範，Van Evera 那本討論個案研究裡每一項證據的分量，《The Book of Why》討論怎麼把設計依賴的假設寫成圖。《Mastering 'Metrics》與線上實驗那本跟工程師的處境最近，KKV、Van Evera 與《The Book of Why》跟政治學方法論課的處境最近。KKV 與 Van Evera 兩本收的都是判讀個案研究所需的部分，質性研究怎麼做（訪談、田野觀察、資料編碼）不在這一篇的範圍，記在 [研究方法與統計推論書單](/books/research-methods/) 的 Backlog 段。

Alan Gerber 與 Donald Green 的《Field Experiments: Design, Analysis, and Interpretation》（2012）是政治學實地實驗的教科書，討論不遵從分派、樣本流失與干擾這些實驗在現場會遇到的狀況。本書單未評估它的角色歸屬：它跟《Mastering 'Metrics》的隨機分派章、線上實驗那本都在討論隨機實驗，要比對章節才判得出它的角色跟那兩本是否不同，這一項記在 [研究方法與統計推論書單](/books/research-methods/) 的 Backlog 段。

## 研究設計與因果推論的相鄰主題與接續閱讀

這一篇的設計最後都落到一個迴歸係數或一組平均數的差上，那組計算與它的信賴區間收在 [統計推論與迴歸的選讀書目](/books/research-methods/inference-and-regression/)。

樣本是不是先被結果篩過，站上的整理在 [Survivorship Bias（倖存者偏誤）](/business/knowledge-cards/survivorship-bias/)；A/B 測試的假設檢定與樣本量計算在 [A/B Test 的統計基礎](/devops/monitoring/08-business-analytics/ab-test-statistics/)。

同一份觀察資料被另一批研究者換一組資料重做而結論不同的實例，在媒介與輿論書單的 [公眾判斷能力的選讀書目](/books/media-public-opinion/public-competence/)：選民會不會因為與政府無關的事件懲罰執政者，兩批研究者用不同範圍的鯊魚攻擊資料得出相反的結論。
