---
title: "Report — 開發過程的事後檢討"
date: 2026-04-25
description: "blog 開發過程中、把實際遇到的版型 / 整合 / 框架共處等情境、整理成『應該怎麼做、沒這樣做會有什麼麻煩』的事後檢討。每篇皆為正向指引、幫助下一輪同類任務跳過反覆試錯。"
tags: ["report", "事後檢討", "工程方法論"]
---

## 這個資料夾是什麼

`content/report/` 收錄 blog 開發過程中累積的事後檢討文件。每篇對應一個具體情境 — 不寫「做錯了什麼」、寫「這需求應該怎麼做、沒這樣做會有什麼麻煩」。

每篇結構統一：

| 區塊           | 內容                                   |
| -------------- | -------------------------------------- |
| 情境           | 任務背景與當時的限制                   |
| 理想做法       | 系統層的解法（為什麼這個方向是對的）   |
| 沒這樣做的麻煩 | 略過此做法會在後續遇到的具體問題       |
| 判讀徵兆       | 下次遇到同類情境時、可以提早識別的訊號 |

本 index 只做路由、不重述各篇內容 — 每篇文章自包含、可獨立閱讀。

---

## 篇目索引

### 第一輪：搜尋頁版型 / 整合的具體情境（#1-6, +41）

- [#1 在外部組件上加客製功能：以邊界為中心的方法選擇](external-component-customization/) — 客製穩定性與「離組件邊界多近」成正比
- [#2 跨 viewport 雙模式 UI 的物理空間預算](viewport-dual-mode-spatial-budget/) — breakpoint 從固有尺寸加總推算、不從常見值取
- [#3 視覺對齊用單一真實來源](visual-alignment-single-source-of-truth/) — 對齊基準上的尺寸值定義位置只能有一處
- [#4 拓樸理解先行於 CSS 規則](dom-topology-before-css/) — 寫 CSS 之前先看真實 DOM tree、不靠 class name 推測層級
- [#5 客製 UI 留 framework 邊界外、用 CSS 控制視覺位置](coexisting-with-framework-managed-dom/) — 注入 framework 子樹會被 reconciliation 清掉
- [#6 Filter 順序由使用者掃描成本決定](filter-order-by-scan-cost/) — 短清單先、長清單後、不接受字母排序預設
- [#41 Mode 與 Facet 是不同語意層級、UI 區域分開擺放](mode-vs-facet-semantics/) — Mode 緊貼 input、Facet 靠近結果

### 第二輪：開發方法論與工具選擇（#7-15）

- [#7 量測值缺一不可：依賴未測量值會錯位](measurement-completeness/) — 對齊本質是方程組、未知數沒解整組無解
- [#8 置中元件與絕對定位元件並存：用疊層而非排擠](centered-and-positioned-coexistence/) — 絕對定位跳出 layout 流、不擠壓置中
- [#9 同一元件三互動狀態下顯示位置不同的 root cause](component-tristate-root-cause/) — 元件「跟著狀態飄」是錨點在動、不是元件問題
- [#10 從色塊 placeholder 開始的漸進式 UI 除錯](placeholder-driven-ui-debug/) — UI 除錯的最小可驗證單位是「一個有顏色的盒子」
- [#11 在開發循環裡早一點用 playwright 看真實結果](playwright-early-in-loop/) — 靜態推理 ≥ 2 次失敗、改用 playwright 讀 live DOM
- [#12 排版精度的工具選擇：CSS-only vs JS-assisted](css-only-vs-js-assisted/) — 問值能否在 build time 定下來、能 → CSS、不能 → JS
- [#13 JS 操作 framework 元件：邊界辨識與安全規則](component-boundary-and-js-impact/) — 整節點 reparent 安全、改內部不安全、改 attribute 是灰區
- [#14 Selector 精準度：讓 query 只命中你想要的元素](dom-selector-precision/) — 起點 / 範圍 / 過濾三維度顯式設計
- [#15 用前端測試把排版問題自動化](layout-tests-with-playwright/) — 版型 debug 兩次以上就值得寫 playwright 測試

### 第三輪：指令理解與澄清時機（#16-23）

- [#16 空間 / 尺寸類指令的澄清時機](spatial-instruction-clarification/) — 缺數字時先列計算過程、不直接寫死
- [#17 元件相對位置類指令的澄清時機](relative-position-instruction-clarification/) — 「在 X 旁/上/下」先用文字畫 layout 草圖
- [#18 隔離程度類指令的澄清時機](isolation-instruction-clarification/) — 「隔離」先確認邊界是 DOM / layout / state / framework
- [#19 覆寫深度的成本告知](override-depth-cost-report/) — 對抗多層時先報成本、讓使用者參與決定值不值
- [#20 同方向反覆失敗的轉折點](failure-direction-pivot-point/) — 第 2 次同方向失敗就停下來換思路、不到第 4 次
- [#21「可決定」與「該先確認」的邊界](decide-vs-confirm-boundary/) — 使用者會看到的數字 / 順序 / 文字先確認再寫
- [#22「先還原」「先重來」類退出指令的處理](revert-instruction-handling/) — 先問「還原到哪、要不要先 commit checkpoint」
- [#23 驗證方法的選擇時機](verification-method-timing/) — 靜態推理 ≥ 2 次失敗就主動提改用 playwright 量測

### 第四輪：程式碼結構與重構機會（#24-32）

- [#24 CSS Layers 取代 specificity 戰](css-layers-over-specificity/) — vendor CSS 進 layer、自家 unlayered 自動贏
- [#25 CSS / JS 拆出獨立檔案](extract-css-js-files/) — inline > 30 行就拆檔、minify / fingerprint 自動化
- [#26 CSS 變數定義位置統一](css-variable-single-location/) — 定義集中一處、其他地方只引用
- [#27 runtime 量測模式統一](runtime-measurement-unification/) — 對齊基準上要嘛全寫死、要嘛全量測、不要混搭
- [#28 以 class toggle 取代 inline display:none !important](class-toggle-over-important/) — JS 只 toggle class、樣式留在 CSS
- [#29 MutationObserver 範圍與觸發頻率：監聽最少必要的變動](mutation-observer-scope/) — root / option / 頻率三維度 + self-mutation 處理
- [#30 setTimeout 輪詢換 MutationObserver](mutationobserver-over-polling/) — 有事件可監聽就不要輪詢
- [#31 Init function 是 orchestrator、職責拆出獨立 function](split-setup-by-responsibility/) — 函式名動詞 + 對象、純函式優先
- [#32 baseof.html override 範圍最小化](minimize-baseof-override/) — override theme 檔案只動非改不可的部分

### 第五輪：效能與無障礙的風險點盤點（#33-40）

效能組：

- [#33 Reactive 監聽器的效能 audit：跨 listener 類型盤點觸發頻率](reactive-listener-frequency-management/) — audit 視角、跟 #29 設計指引互補
- [#34 Runtime 計算成本：每筆迭代與正則](runtime-iteration-and-regex-cost/)
- [#35 Layout reflow / repaint 的可量化評估](layout-reflow-measurement/)
- [#36 資源載入時序：lazy chunk 與 critical path](lazy-loading-and-critical-path/)

無障礙組：

- [#37 動態 DOM 移動時的 focus 管理](focus-management-on-dom-move/)
- [#38 Screen reader 與動態內容變動的 live region 設計](aria-live-for-dynamic-content/)
- [#39 Native HTML element 優先於 ARIA role 的取捨](native-html-over-aria-role/)
- [#40 視覺輔助：對比度、放大、字型 zoom 的 layout 適配](visual-aids-contrast-zoom-responsive/) — 純視覺呈現面 a11y
- [#52 鍵盤可達性：focus indicator、tab 順序、escape 路徑](keyboard-accessibility/) — 鍵盤使用者導航三要素
- [#53 Motor 可達性：hit target、間距、誤點防護](motor-accessibility-hit-target/) — 行動 / motor 使用者的點擊精準度

### 第六輪：抽象層原則（待補完）

跨多篇實作的共同骨架。每篇不重述具體 case、只展開原則本身、結尾列出對應的實作篇。

- [#42 2 次門檻：第一次是運氣、第二次是訊號](two-occurrence-threshold/) — 串 #11 / #15 / #20 / #23 / #56、跨工具/測試/思路/溝通/驗收五面向
- [#43 最小必要範圍是 sanity 防線](minimum-necessary-scope-is-sanity-defense/) — 串 #13 / #14 / #29 / #64、跨 JS 邊界 / selector / observer / stream 操作四類範圍
- [#44 Single Source of Truth：值的住址只能有一處](single-source-of-truth/) — 串 #3 / #26 / #27 / #64、跨定義位置 / 來源機制 / 對齊基準 / stream 全集四類違反
- [#45 跟外部組件合作的層次：離介面越近、合作越穩](external-component-collaboration-layers/) — 串 #1 / #5 / #19 / #24 / #59、四層代價對照與跳維度機制
- [#67 寫作便利度跟意圖對齊反相關](ease-of-writing-vs-intent-alignment/) — 串 #55 / #43 / #44 / #45 / #64、跨層 / 範圍 / 來源 / 客製 / 合成五面向、是「便利 vs 正確」的共同上位原則
- [#68 驗收的時間軸：四個 checkpoint](verification-timeline-checkpoints/) — 串 #42 / #56、寫之前 / 開發中 / ship 前 / ship 後分散驗收
- [#69 Test-First：先看到 RED 才相信 GREEN](test-first-red-before-green/) — 串 #42 / #56 / #67 / #68 / #11 / #15、測試驗收的 RED-GREEN 兩訊號協議
- [#70 URL 是 stateful UI 的儲存層](url-as-state-container/) — 串 #44 / #67 / #55、可分享 / 可恢復 / 可導航的 state 該寫進 URL、預設 in-memory 是 silent 犧牲
- [#71 Tab Order = DOM Order = Mental Model 三者對齊](tab-order-mental-model-alignment/) — 串 #52 / #67 / #43、優先重排 DOM、tabindex > 0 是反模式
- [#72 高 ROI 無外部觸發的工作會被結構性跳過](external-trigger-for-high-roi-work/) — meta-#67/#68/#69、修法是 L1-L5 結構性對策、「之後我會 X」是 plan 警訊
- [#73 搜尋引擎的匹配模式跟使用者預期的對齊](search-engine-matching-mode-mismatch/) — Prefix / substring / fuzzy / semantic 對照、預設多為 prefix（為 index size）、使用者預期 substring（被 Google 訓練）、不對齊 = silent 失敗
- [#74 決策呈現：選項 + 推薦 + 開放修改](decision-presentation-options-recommendation/) — 不要開放問「你想怎麼做」、給選項表 + 適配性 + 標推薦 + 「想改？」開放、把整理成本攤開
- [#75 主策略 + 補強策略：選擇不必互斥](main-strategy-plus-supplementary/) — 多策略可疊加（structural + UX）、判準三條：解不同層 / 沒副作用衝突 / 增量成本可接受
- [#76 分批 ship：低風險可見價值先行、結構性下輪](incremental-shipping-criteria/) — 三軸切分（可見性 / 風險 / 驗證）、先 ship 甜蜜點 = 高可見 + 低風險 + 低驗證、ship 順序 ≠ 重要程度
- [#77 「現在不決定」是合法選項](decide-later-as-valid-option/) — 決策清單預設加「延後 + 條件」、區分「逃避決策」vs「結構性延後」、配 trigger 避免 #72 跳過
- [#78 反省任務預設複選](retrospective-multi-select-default/) — 互斥要證明、不互斥是預設、反省題的 radio 格式 = 結構性把多面向 collapse 成單點
- [#79 決策對話的五個維度](decision-dialogue-dimensions/) — meta-#74-#78、五個獨立維度（呈現 / 策略疊加 / 批次 / 時間軸 / 選項類型）、預設都 collapse 到窄格 = 把使用者塞進最少自由度的盒子
- [#80 Yes/No 二選是隱式 collapse](yes-no-binary-collapse/) — 「需要 X 嗎？」「OK 嗎？」是五維 collapse 的極致形態、把多選空間壓成 1 bit、最常見最隱形
- [#81 卡片系統的迭代浮現](cards-as-living-system-iteration/) — 原子卡 → meta-卡 → reference 三層 spiral、跳層或一次寫成都會 over-fit、process-level 元原則
- [#82 字面攔截 vs 行為精煉](literal-interception-vs-behavioral-refinement/) — 驗證粒度匹配：字面用 hook、行為用 multi-pass spiral、強行用 hook 蓋行為錯誤 = false confidence 比沒保護更危險、#72 的 ceiling
- [#83 Writing 的 multi-pass review](writing-multi-pass-review/) — 寫 = N 輪不同 frame（生成 / 意圖 / 語氣 / grep / 反例）、單輪寫不出全部維度、跳輪的代價 = 某維度永遠做一半
- [#84 Naming 是 iterated artifact](naming-as-iterated-artifact/) — 第一版命名幾乎不對（基於狹窄 context）、四輪 review（第一版 / grep / cross-call-site / impl 洩漏）才收斂、接受重命名是常態
- [#85 Methodology 的 multi-pass 該升級為 pillar 層](methodology-multi-pass-embedding/) — 升 pillar = 結構性必跑、留 appendix = #72 結構性跳過、本卡是 #82 + #72 在「方法論設計本身」的展現
- [#86 Capability gap 的三層對策階梯](capability-gap-three-layer-escalation/) — L1 expectation alignment / L2 augmenting computation / L3 structural rebuild、預設 L1→L2→L3 升級、不必每次跳 L3、跟 #75 互補（#75 疊加 / 本卡選層）
- [#87 Build-time vs Runtime 計算的光譜](build-time-vs-runtime-computation-spectrum/) — 兩極 + hybrid hot-path、四軸判準（頻率 / 大小 / freshness / pipeline）、「能 precompute 就 precompute」是便利驅動口號、實際要套軸才知道
- [#88 Engine 不可調時、把 transformation 移到外層](transformation-at-outer-layer-when-engine-closed/) — 跨領域 pattern：search engine 不支援 substring → build-time emit suffix tokens、LLM 不會 CoT → prompt 加 instruction、DB JSON 不能 query → denormalize；engine 不開放 = 不該硬戳內部、改 transformation 輸入 / 外層
- [#89 Dataset 規模改變什麼可行](dataset-scale-changes-feasibility/) — 「需要 index / cache / 分散式」是 production scale 的詞、不是普世詞；具體 threshold（< 1MB 無腦 / 1-10MB O(N) 仍可 / > 100MB 才強制 index）；「以後會長大」是過度工程藉口
- [#90 L1 + L2 疊加時的訊號一致性](layered-strategy-signal-consistency/) — UX hint 跟自動 fallback 講的話要對齊、Silent fallback 看似簡潔實為 false confidence；三設計原則（fallback 訊號明示 / hint 承認 L2 / 可 trace 結果來源）
- [#91 升級 trigger 的量化設計](escalation-trigger-quantification/) — 「不夠就升 Y」需要 metric + threshold + window + owner 四元素、L1 ship 時就同步寫 L2 / L3 trigger、「再觀察一下」是缺 trigger 的訊號
- [#92 視覺手段對齊錯誤層次](visual-tool-error-layer-alignment/) — CSS / emoji 修不到語意 / 邏輯問題、修法順序「邏輯 → 語意 → 視覺」深層往淺層、用視覺工具蓋下游症狀 = false confidence、是 #82 在「呈現層」的 sibling、補 #83 multi-pass 缺的 vertical 軸
- [#93 URL slug 必須顯式定義為 fact](url-slug-must-be-explicit-fact/) — 跨工具共用的 identifier（slug / route / ID）必須顯式定義在一處 fact、不能依賴各工具各自推導；slug 散落在「檔名 / hugo title 推導 / frontmatter」三處 = SSoT 違反、跨工具接縫時才爆；本卡是 #44 在 toolchain integration 的具體實例、跟 #82 / #92 並列為「工具 ceiling pattern」系列
- [#94 正向改寫要保留對照論據、不能空降結論](positive-rewrite-preserves-contrast/) — 「X、不是 Y」同時給結論 + 排除讀者直覺、為了「正向陳述優先」直接刪 Y 會讓 X 變空降斷言；合法做法：保留 contrast / 補 reasoning / 升級對照表；本卡是 #82 在「寫作規則執行」層的同形 pattern、補 `compositional-writing` 規則六沒覆蓋的反向 case（只有錨點沒有對照）
- [#95 Multi-pass review 的 scope 要蓋『同類風險區』](multi-pass-scope-must-cover-risk-zone/) — Pass 用「我改過的檔」當 scope 是便利選擇、會 systematic miss 整個 corpus 的同類違規；合法 scope = 原則適用範圍 ∩ 待 review corpus、跟改動區無關；用 grep 把同類風險區結構性掃出來；本卡是 #67 在 review 流程的具體展現、補 #83 沒覆蓋的 scope 軸（frame × scope 兩軸都對齊才完整）
- [#96 適用範圍要展開成 file enumeration](applicability-scope-must-be-enumerated/) — 「所有教學文件」這類口語描述執行時要心算具體檔、推導步驟易漏（mirror / fork / 翻譯版）；合法形式是 enumerated file list 或可重現的 grep / find 規則；本卡是 #95 的下游具體化（#95 答 scope 從哪來、本卡答 scope 長什麼樣）、跟 #82 互補（enumerate 是字面層、completeness 是行為層判準）、是 #44 在「原則作用域」維度的具體案例
- [#97 Metadata surface 要納入寫作 review 範圍](metadata-surface-in-writing-review/) — title / description / frontmatter / heading / link label / MOC hook 是讀者入口與搜尋入口；body review 通過後仍要跑 metadata surface，frame × surface 兩軸同時完整才代表寫作 review coverage 完整
- [#98 素材庫比例要支撐主情境的反向驗證](source-library-ratio-supports-scenario-validation/) — 文章主情境保持 4-5 個、素材庫保留 2-3 倍 field/source cards；每個 scenario 背後要有 2-3 個來源，才能支撐反向驗證、壓力變體與後續擴寫

### 第七輪：Pattern 卡片（待補完）

從實作篇的「設計取捨」段落抽出、單一做法的深入卡片。每張卡片只討論一個 pattern：什麼時候用、什麼時候不用、跟其他做法的取捨。實作篇在取捨段落引用對應卡片。

Selector 起點四選一（從 #14 抽出）：

- [#46 Pattern：Document 全文件 query](pattern-document-query/) — 原型期、單例、跨元件邊界元素
- [#47 Pattern：元件根變數 query](pattern-component-root/) — production 客製預設
- [#48 Pattern：起點當函式參數](pattern-root-as-parameter/) — 多實例支援、純函式設計
- [#49 Pattern：closest 反向找根](pattern-closest-lookup/) — 動態元件、事件委派

Idempotency 過濾兩選一（從 #14 抽出）：

- [#50 Pattern：DOM attribute idempotency 標記](pattern-attribute-idempotency-marker/) — production 預設、devtools 可見
- [#51 Pattern：WeakMap idempotency 紀錄](pattern-weakmap-idempotency-record/) — library 設計、不污染 DOM

跨 slot 搬遷（從 #2 抽出）：

- [#54 Pattern：跨 slot 同節點搬遷](pattern-cross-slot-node-relocation/) — stateful UI 在兩個 slot 間搬同一節點、不複製

Filter × Source 合成三選（從 #59 抽出）：

- [#60 Pattern：自動續抓直到湊滿 quota](pattern-fetch-until-quota/) — 策略 B、source 不支援 server filter、match 密度可預期
- [#61 Pattern：把 filter 推進 query 引擎](pattern-query-side-pushdown/) — 策略 A、source 支援、避免層錯位的最優解
- [#62 Pattern：誠實進度 UX（已掃 N / 命中 K / 共 M）](pattern-honest-progress-ui/) — 策略 D、sourcing 限制下的合理透明度
- [#65 Pattern：預先建獨立 index](pattern-multiple-indexes/) — 策略 C、build time 為每種 mode 各建一份 index
- [#66 Pattern：明示語意縮小](pattern-explicit-semantic-narrowing/) — 策略 E、explicit 告訴使用者「filter 範圍 = subset」

### 第八輪：Filter × Source / Data Flow 議題（#55-#59, #63-#64）

從搜尋頁 title/content filter bug 萃取出的「stream 操作 × 分批 source」主軸。跨前端 / 後端 / 演算法 / 資料庫通用、不只 UI。

問題分析：

- [#55 Filter 與 Source 的抽象層錯位](view-layer-filter-vs-source-layer/) — filter 在視覺層、source 在資料層分批 → silent 語意縫
- [#56 視覺完成 ≠ 功能完成](visual-completion-vs-functional-completion/) — 視覺驗收訊號早於功能驗收成立、容易誤判完工
- [#57 Loading / Empty / End 三狀態的區分](loading-empty-end-state-distinction/) — 三事實不同、UX 必須分

指令澄清（補 #16-23 第三輪第 5 類）：

- [#58 篩選類指令的澄清時機](filter-instruction-clarification/) — 三問模板（定義域 / 資料源型態 / 空狀態）

解法策略：

- [#59 Filter × Source 合成策略五選一](filter-source-composition-strategies/) — A 推進 query / B 自動續抓 / C 預先 index / D 誠實 UX / E 接受語意縮小

抽象原則（屬第六輪、跨領域升級）：

- [#63 資料源的形狀決定 feature 的形狀](data-source-shape-defines-feature-shape/) — 不能憑 UI 倒推資料層
- [#64 Feature 操作要跟 Source 同層合成](compose-feature-at-source-layer/) — stream 操作 = 同層或更上游、跨前端 / 後端 / 演算法 / 資料庫通用

---

## 場景導讀

依任務情境查、不需要按編號逐篇讀。每條路徑列「該讀哪幾篇、什麼順序」。

### 路徑 1：面對 layout 對齊或位置問題

`#7 量測值缺一不可` → `#3 視覺對齊用單一真實來源` → `#4 拓樸理解先行於 CSS 規則` → `#11 早一點用 playwright 看真實結果`

### 路徑 2：要客製外部組件

`#1 在外部組件上加客製功能` → `#5 與 framework-managed DOM 共處` → `#24 CSS Layers 取代 specificity 戰` → `#19 覆寫深度的成本告知`

### 路徑 3：要 refactor 既有 code

`#25 CSS / JS 拆出獨立檔案` → `#24 CSS Layers` → `#27 runtime 量測模式統一` → `#28 class toggle 取代 important` → `#31 init 拆 orchestrator`

依序是：拆檔（基礎）→ Layers（前提）→ 量測模式統一 → class toggle → 函式拆分。後面三項依賴前面、不要跳過。

### 路徑 4：debug 一個元件位置「跟著狀態飄」

`#9 三互動狀態下 root cause` → `#4 拓樸理解先行` → `#11 用 playwright 量 live DOM`

### 路徑 5：遇到不明確的指令

依指令類型挑：

- 缺數字（「對齊」「padding」） → `#16 空間 / 尺寸類`
- 元件位置（「在 X 旁邊」） → `#17 元件相對位置類`
- 「不要動 X」「隔離」 → `#18 隔離程度類`
- 客製需求看似簡單但會對抗多層 → `#19 覆寫深度的成本告知`
- 同方向反覆失敗 → `#20 同方向反覆失敗的轉折點`
- 「依 X 篩選」「只看 X」「過濾 Y」 → `#58 篩選類指令的澄清時機`

### 路徑 6：寫測試固化已 debug 過的版型

`#15 用前端測試把排版問題自動化` → `#11 早一點用 playwright`

### 路徑 7：使用者反映效能問題

按症狀：

- 卡頓、CPU 100% → `#33 Reactive 監聽器的觸發頻率`
- 結果規模大時慢 → `#34 Runtime 計算成本`
- Resize 視窗、視覺跳動 → `#35 Layout reflow / repaint`
- 首次互動延遲 → `#36 資源載入時序`

### 路徑 8：使用者反映無障礙問題

按使用者類型：

- 鍵盤使用者 focus 跑掉 → `#37 動態 DOM 移動時的 focus 管理`
- Screen reader 不知道有變動 → `#38 aria-live region 設計`
- 想用 fieldset 取代自訂 radiogroup → `#39 Native HTML 優先於 ARIA`
- 低視力 / 色弱 / 字型放大 → `#40 視覺輔助`
- Focus indicator / tab 順序 / modal escape → `#52 鍵盤可達性`
- 行動裝置誤點 / hit target 太小 → `#53 Motor 可達性`

### 路徑 9：搜尋 UI / facet UX 設計

`#6 Filter 順序由掃描成本決定` → `#41 Mode 與 Facet 語意分區` → `#19 覆寫深度的成本告知`

### 路徑 10：對話 protocol 自我檢查

`#16-23 第三輪八篇` 整批是「下次看到這類指令該怎麼處理」、開發前重溫一遍可避免反覆失敗。

### 路徑 11：設計含 filter / sort 的 feature、source 是分批 / streaming

`#63 資料源形狀決定 feature 形狀` → `#58 篩選類指令的澄清時機` → `#55 Filter 與 Source 層錯位` → `#59 五策略選一` → 依選擇看 `#60 / #61 / #62` 對應 pattern

### 路徑 12：feature「畫面對了但功能怪」debug

`#56 視覺完成 ≠ 功能完成` → `#57 三狀態區分` → `#55 層錯位（如果是 filter 類）` → `#64 同層合成原則`

### 路徑 13：跨前端 / 後端 / 演算法的 stream 操作架構

`#64 Feature 操作要跟 Source 同層合成` → `#63 資料源形狀` → `#59 策略五選一` — 適用於後端 middleware filter、map-reduce post-filter、pipeline transform 等非 UI 情境

### 路徑 14：寫測試固化 bug fix / feature

`#68 驗收的時間軸（Checkpoint 2/3）` → `#69 Test-First RED-GREEN 順序` → `#15 layout-tests-with-playwright` / `#11 playwright-early-in-loop` — 修 bug 或加 feature 時、測試該怎麼寫才被驗證

### 路徑 15：寫作 / UI 中看到視覺異常、想直接改 CSS / emoji

`#92 視覺手段對齊錯誤層次` → `#82 字面攔截 vs 行為精煉` → `#83 Writing 的 multi-pass review` — 先問「是不是語意 / 邏輯層的下游症狀」、確認純視覺再修 CSS；multi-pass review 要同時跑 horizontal frame（#83）和 vertical layer（#92）

### 路徑 16：跨工具 identifier（slug / route / ID）broken / 不一致

`#93 URL slug 是 fact` → `#44 Single Source of Truth` → `#82 字面攔截 vs 行為精煉` — 多工具各自推導 identifier 是 SSoT 違反、解法是把 identifier 升成 fact（顯式定義）、不要教工具學別人的推導規則；補 lint 規則作為 trigger（[#91](escalation-trigger-quantification/)）防止 debt 累積

### 路徑 17：寫作 review 要同步檢查 metadata surface

`#97 Metadata surface 要納入寫作 review 範圍` → `#96 適用範圍要展開成 file enumeration` → `#95 Multi-pass scope 要蓋同類風險區` → `#83 Writing 的 multi-pass review` → `#94 正向改寫要保留對照論據` — 先列 file scope，再列每個檔內的 title / description / heading / MOC hook / link label；最後用正向陳述與對照論據判準檢查讀者入口是否跟正文共用同一個概念錨點

---

**Last Updated**: 2026-04-30 — 新增 #97 Metadata surface 要納入寫作 review 範圍（從資安章節標題 review 漏判抽出 — 正文已建立正向概念、title 與 MOC hook 仍保留舊 frame，揭露 multi-pass review 缺 surface 軸）、新增路徑 17 給 title / frontmatter / index hook 的寫作 coverage 檢查。

**Last Updated**: 2026-04-28 — 第六輪新增 #92 視覺手段對齊錯誤層次（從 blog 文章寫作 retrospective 抽出 — emoji 圖例斷行的 trigger 揭露「multi-pass review 缺 vertical 軸」、跟 #82 並列為 sibling、補 #83 缺的 layer 維度）、新增路徑 15 給寫作 / UI 中誤判層次的情境。

**Last Updated**: 2026-04-28 — 新增 #93 URL slug 必須顯式定義為 fact（從 #92 的 mermaid cross-link broken 踩坑揭露 — 175 篇內容文章 0 篇有顯式 slug、檔名 / hugo title 推導 / frontmatter 三處散落、典型 #44 SSoT 違反在 toolchain integration 維度）、新增路徑 16 給跨工具 identifier 議題。

**Last Updated**: 2026-04-26 — 五輪實作 43 篇 + 第六輪抽象層 9 篇（#42-45, #67-71）+ 第七輪 Pattern 卡片 12 篇（#46-51, #54, #60-62, #65-66）+ 第八輪 Filter × Source 議題 7 篇（#55-59, #63-64）。八輪迭代完成 — 最新一輪：retrospective Checkpoint 1（修 search bug 後跳過的「列使用者意圖完整集合」）發現 3 個 silent 缺口（URL state / tab order / filter UI hint）、抽兩張新抽象層卡（#70 URL 儲存層 + #71 Tab Order 三對齊）、#68 加 Checkpoint 1 跳過的 self-case。
