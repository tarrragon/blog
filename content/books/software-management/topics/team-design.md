---
title: "組織結構與團隊設計"
date: 2026-08-18
description: "決定團隊怎麼切、交接面誰負責、一個團隊還能不能再接一個服務時，依組織規模分層的選讀"
weight: 30
tags: ["books", "reading", "team-topologies", "organization-design", "conway-law"]
---

這個主題處理組織的形狀怎麼決定系統的形狀。團隊邊界一旦畫下去，溝通成本、交接延遲與架構耦合就跟著定下來，而這些代價通常在幾個月後才顯現、要改又得付重組成本。這使得團隊設計成為少數「事前多想一個月很划算」的決定。

這個主題的書對組織規模特別敏感。同一套結構模板，在三十人的公司是過度設計，在三百人的公司是必要基礎設施。選書時先確認自己的規模，否則會拿到一整套用不上的框架並且開始為不存在的問題做設計。

## 起點是 Team Topologies

Matthew Skelton 與 Manuel Pais 的《Team Topologies》涵蓋了從團隊型態到互動模式的完整設計語彙，套用成本也是本篇最低的一本：它把團隊互動收斂成三個具名選項，讀完就能拿去對照自己的組織。它從 Conway's Law 出發——系統架構會反映組織的溝通結構——並把這條規律當設計工具用：既然結構會互相映射，就先設計組織來得到想要的架構。

核心是四種團隊型態（stream-aligned、enabling、complicated-subsystem、platform）與三種互動模式（collaboration、X-as-a-Service、facilitating）。這套詞彙讓「這兩個團隊該怎麼合作」變成有限選項的決定：長期高頻協作是 collaboration，穩定介面是 X-as-a-Service，短期能力移轉是 facilitating。沒有這套詞彙時這個決定通常沒有被明確做過，於是預設落在成本最高的長期協作。

另一條主線是團隊認知負荷。書中主張團隊能承擔的領域範圍由認知負荷上限決定而非人數決定，這直接影響「這個團隊還能不能再接一個服務」的判斷。

證據來源是跨組織的顧問案例加上既有理論（Conway's Law、Dunbar number）的整合，不是統計。時效上，第二版於 2025 年出版並補上更多實作案例；Conway's Law 這個地基比書本身老得多，也還沒有被推翻的跡象。讀得出價值的前提是：經歷過一次跨團隊交接摩擦。三種互動模式的差別是成本差別，而成本要付過才有感。繁體中文版目前未見，簡體中文版譯名《高效能團隊模式》。

- [Amazon（Team Topologies, 2nd Edition）](https://www.amazon.com/Team-Topologies-2nd-Organizing-Technology/dp/1966280009)
- [Amazon（第一版）](https://www.amazon.com/Team-Topologies-Organizing-Business-Technology/dp/1942788819)
- [天瓏（高效能團隊模式：支持軟件快速交付的組織架構，簡體中文版）](https://www.tenlong.com.tw/products/9787121410826)

## 已經在調度多個團隊時讀 An Elegant Puzzle

Will Larson 的《An Elegant Puzzle》預設讀者越過了「怎麼帶三個人」的階段，關心的是團隊規模怎麼定、技術債怎麼排進計畫、接班怎麼安排、組織成長時哪些結構會先斷。書名的 puzzle 指的是這類問題的性質：沒有唯一解，但有明顯較好與較差的解，而各個約束彼此牽動。

書中的團隊狀態模型把團隊分成落後、追平、還債、創新四種狀態，並主張每種狀態該用不同的介入方式——落後的團隊要減負載而不是加人，追平的團隊要保護不被打斷。這個模型讓「這個團隊需要什麼」變成可以問出答案的問題，而不是憑感覺調度資源。

讀得出價值的前提很硬：手上同時有兩個以上團隊要調度資源。只帶一個團隊的人讀它，四種狀態是四個形容詞；要在兩個團隊之間分配同一批人的時候，它們才變成可以吵的依據。

證據來源是作者在 Digg、Uber、Stripe 的經驗，細節具體但屬於單一路徑的觀察；素材來自長期經營的部落格，章節之間偏獨立、不是線性論述。時效上，書中的規模假設是快速成長的矽谷公司，招募與晉升制度那幾章綁定那個環境，團隊狀態模型與負載判斷不依賴它。目前沒有中譯本。

- [Amazon（An Elegant Puzzle: Systems of Engineering Management）](https://www.amazon.com/Elegant-Puzzle-Systems-Engineering-Management/dp/1732265186)

## 要理解規模與時間怎麼改變決策時讀 Software Engineering at Google

《Software Engineering at Google》處理的問題是：當程式碼要活二十年、當有數萬名工程師在同一個 repo 上工作時，哪些工程判斷會反過來。它把軟體工程定義成「隨時間推移的程式設計」，然後逐項檢視這個定義如何改變測試策略、程式碼審查、依賴管理、棄用流程與工具投資。

書中的 Hyrum's Law 及其衍生的設計態度可遷移到任何規模：介面的所有可觀察行為終將被某人依賴，因此棄用是需要制度而非公告的過程。這個洞察與組織規模無關，小團隊維護長壽專案時同樣成立。

證據來源是單一組織的制度紀錄，且大量做法依賴 Google 的內部基礎設施，直接套用的成本很高。時效上，書出版於 2020 年，工具鏈章節描述的內部系統外部無法取得也無從更新；時間與規模如何改變工程決策這個論證軸不依賴特定工具。讀得出價值的前提是：維護過一個自己沒有參與初版開發的系統。繁體中文版由歐萊禮出版，譯名《Google 的軟體工程之道》。

- [Amazon（Software Engineering at Google）](https://www.amazon.com/Software-Engineering-Google-Lessons-Programming/dp/1492082791)
- [博客來（Google 的軟體工程之道：從程式設計經驗中吸取教訓）](https://www.books.com.tw/products/0010938794)

## 想把零散做法串成一套解釋時讀 Wiring the Winning Organization

Gene Kim 與 Steven Spear 的《Wiring the Winning Organization》（2023）處理的問題是：為什麼同樣的工作在某些組織裡很難、在另一些組織裡很簡單。答案由三個機制構成——slowification（把問題移到壓力較低的場合先解決）、simplification（把大問題切成可獨立處理的小問題）、amplification（讓問題訊號快速被聽見並回應）。

它與這個主題其他書的差別在抽象層級。Skelton 與 Pais 給結構模板，Larson 給調度模型，Kim 與 Spear 想給的是解釋那些做法為何有效的底層理論。Spear 的背景是豐田生產系統與醫療安全研究，案例因此跨產業。

證據來源是理論建構加上跨產業案例，而三個機制的解釋力在不同案例上並不平均——這是它適合當第四本而非第一本的原因。時效上是本篇最新的一本，眼下沒有過期的部分。讀得出價值的前提是：已經讀過這個主題的另外兩三本、手上有一批彼此不相干的做法想找共同解釋——沒有那批做法時，三個機制只是三個造詞。目前沒有中譯本。

- [Amazon（Wiring the Winning Organization）](https://www.amazon.com/Wiring-Winning-Organization-Slowification-Simplification/dp/1950508420)

## 推動重組時的人的阻力在溫伯格第 4 卷

Weinberg 的《Quality Software Management, Vol. 4: Anticipating Change》處理組織轉變的推動過程。前面幾本給出目標結構長什麼樣，這一卷處理從現狀走到目標的路上會遇到什麼——誰會抗拒、抗拒的形式有哪些、哪些抗拒其實是有效資訊。

證據來源是作者的顧問經驗。時效上，書中預設的組織轉型節奏是以年為單位的變革專案，與現在的做法不同；抗拒的形式與應對方式處理的是人對不確定的反應，不依賴那個節奏。讀得出價值的前提是：推動過一次失敗或半途而廢的組織改變——事前讀跟事後讀是兩本不同的書。

- [Amazon（Quality Software Management: Anticipating Change）](https://www.amazon.com/Quality-Software-Management-Anticipating-Change/dp/0932633323)
- [博客來（溫伯格的軟體管理學：擁抱變革，第 4 卷）](https://www.books.com.tw/products/0010545251)

## 為什麼只收這幾本

這個主題的五本按抽象層級排：設計語彙（Team Topologies）、調度模型（An Elegant Puzzle）、規模與時間的約束（Software Engineering at Google）、底層理論（Wiring）、推動過程（溫伯格第 4 卷）。前四本回答結構該長什麼樣，最後一本回答怎麼走過去。

組織設計的書大量來自一般管理領域（矩陣式組織、事業部制），它們不處理軟體特有的約束——程式碼的耦合會把組織的溝通成本固定下來，這件事在非軟體組織裡沒有對應物。要分辨，翻目錄找「架構與組織互相映射」這件事有沒有被當成前提；沒有的話，那本處理的是另一個問題。

規模化敏捷框架（SAFe、LeSS 之類）本書單未評估。它們提供的是流程模板而非結構判準，適用性高度依賴組織既有的成熟度，要給出可靠的選讀建議需要在不同成熟度的組織各導入一次，這裡沒有這個基礎。

## 這個主題接到哪裡

團隊切好之後，交接面上的溝通品質決定結構有沒有真的生效——結構對但沒人講真話時，X-as-a-Service 的介面會變成互相推責的邊界。那條路徑走 [組織文化與心理安全感](../culture-safety/)。

要判斷重組後的交付效能有沒有改善，走 [持續交付與交付效能](../continuous-delivery/)。要理解為什麼每次重組的效果都被抵銷，走 [問題定義與系統思考](../problem-definition/)。

既有團隊的結構評估協議看 [發射管制隊視角：評估工作團隊設計](/record/launch-control-team-lens-methodology/)。
