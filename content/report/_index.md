---
title: "Report — 開發過程的事後檢討"
date: 2026-04-25
description: "blog 開發過程中、把實際遇到的版型 / 整合 / 框架共處等情境、整理成『應該怎麼做、沒這樣做會有什麼麻煩』的事後檢討。每篇皆為正向指引、幫助下一輪同類任務跳過反覆試錯。"
tags: ["report", "事後檢討", "工程方法論"]
---

## 這個資料夾是什麼

`content/report/` 收錄 blog 開發過程中累積的事後檢討文件。每篇對應一個具體情境 — 不寫「做錯了什麼」、寫「這需求應該怎麼做、沒這樣做會有什麼麻煩」。

每篇結構統一：

| 區塊           | 內容                                                            |
| -------------- | --------------------------------------------------------------- |
| 論述基礎與限制 | evidence 來源和邊界（不記怎麼發起檢討、用了什麼工具、主觀感受） |
| 情境           | 任務背景與當時的限制                                            |
| 理想做法       | 系統層的解法（為什麼這個方向是對的）                            |
| 沒這樣做的麻煩 | 略過此做法會在後續遇到的具體問題                                |
| 判讀徵兆       | 下次遇到同類情境時、可以提早識別的訊號                          |

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
- [#99 資安教學的審查標準要對應風險不對稱](security-teaching-rigor-asymmetry/) — 一般教學寫不清楚停在學習端、資安教學寫不清楚是生產端不可逆破口；audit bar 要從 readability-first 升級到 verifiability-first、預設讀者會 implement；是後續 #100-105 資安 audit 系列的 anchor
- [#100 False sense of security 是資安寫作的主要失敗模式](false-sense-of-security-as-primary-failure/) — 失敗模式不是「讀者學不到」、是「讀者以為學會了並照做、實際還有破口」；silent failure 比 noisy failure 貴 4-5 個數量級、教學擴散讓單篇 silent gap 變系統性 risk；audit 主軸是消滅讓讀者「我做了 X 就安全」的句子
- [#101 Threat model 明確性：「防什麼」與「不防什麼」必須對稱](threat-model-explicitness/) — Mitigation 句子要對稱寫 in-scope threat + out-of-scope threat + 補強路由；單寫前者讀者會 universal 詮釋、實作覆蓋只是作者腦中 subset；對稱論述是 scope qualifier、不違反「正向陳述優先」
- [#102 Mitigation 對位：防護對應到具體 threat 的驗證](mitigation-threat-alignment/) — Mitigation 名稱對位 threat 名稱是字面層（defense theater）、必須補 mechanism 層 + 前提層；對位鏈拆「攔的 threat / 攔的 mechanism / 失效訊號」三欄、reader 才能反向驗證實作強度跟追新 threat 變體
- [#103 Mitigation 的 context-dependence：deployment 條件改變有效性](mitigation-context-dependence/) — 同 mitigation 在不同 config / scale / runtime / actor 條件下強度從完整擋到 silent 失效；每個 mitigation 列「成立條件 / 失效條件 / deployment 變數」三類、跟 #89 規模改變可行性同骨
- [#104 Security 標準引用的時效性與精確度](security-citation-currency-and-precision/) — 資安標準（OWASP / RFC / NIST / CIS）best practice 衰退快、原文常被引用扭曲（conditional → unconditional drift）、版本之間語意可能反轉；citation 必須附「標準 / 版本 / 原文 quote / 適用 scope / review trigger」五欄；internal citation（knowledge-cards / 跨章引用）也適用、且因無版本號 anchor 更易 silent drift / broken
- [#105 Audit recommendation 層級：accept / minor / major / 教錯不可保留](security-audit-recommendation-tiers/) — Audit 產出是 ship 決策、不是評語；四 tier 判準（reader 會不會主動產生破口 / 結構性 vs 局部 / fix cost / 是否容忍）；withdraw tier 是資安 audit 跟學術 peer review 的關鍵差異——保留 = 增加 risk、不存在「先 ship 後改」
- [#106 用 Next-action frame 取代 Disclaimer：把 prohibition 翻成 actionable chain](next-action-frame-over-disclaimer/) — Audit findings 寫成回應段時、disclaimer frame 自然產出負面陳述、字面正向化後 frame 仍 disclaimer；reframe 成 next-action chain 整段才自然 positive；本卡是 #94 正向改寫的上游、#82 字面 vs 行為在寫作 frame 的具體實例；補 #83 multi-pass review 的輪 3 frame 檢查
- [#107 術語翻譯要保留原文錨點](terminology-keeps-original-anchor/) — 中文術語負責可讀性、原文術語負責概念邊界與可回溯性；第一次出現用「中文（original term）」避免翻譯漂移，尤其是學術 / 標準 / 方法論術語
- [#108 中文壓縮術語要保留完整名詞頭](compressed-chinese-terms-need-head-noun/) — 壓縮後仍要回答「這是什麼」；術語至少保留「盲點 / 偏誤 / 風險 / 模式 / 檢查 / 策略」等 head noun，避免只剩單字修飾或句子殘片
- [#109 術語翻譯要保留概念角色](translation-must-preserve-concept-role/) — 術語中文名詞頭要對應來源中的概念角色；`Steelman` 若翻成「最強版本測試」會把論證方法壓成檢查動作，較穩寫法是「最強版本論證（Steelman）」
- [#110 設計檢討用當下三軸論證、不依賴 hindsight](design-flaw-by-current-axes-not-hindsight/) — 「設計缺陷」精準定義是「當下成本對稱條件下選了限制更高的選項」、不是「沒預測到後來需求」；hindsight 論述依賴結局、把需求演化誤判成設計缺陷、歸因落在個人預見性；當下三軸論述（成本對稱性 / 可逆性 / 領域先驗）讓判斷不依賴結局、歸因轉到工具預設與制度
- [#111 口語化修辭會稀釋技術精度](colloquial-rhetoric-erodes-technical-precision/) — 「一輩子」「碰巧能用」「立刻撞牆」「沒事」「下次看到 X 時做 Y」這類修辭在三層稀釋精度：時間性誇張 / 因果模糊 / 結局描述代替契約描述 / 廢話前綴 / 否定先行；修法是把口語修辭翻譯回技術屬性語言（生命週期 / 觸發條件 / 型別契約 / 違反條件 / 判斷工具）
- [#112 地區用語對齊：寫作前先確定讀者的中文語料](regional-terminology-alignment/) — 繁中 vs 簡中的用詞差異（屏 / 螢幕、文件 / 檔案、默認 / 預設、質量 / 品質、視頻 / 影片、函數 / 函式、內存 / 記憶體）會在每個詞累積 0.5 秒對映成本、整篇下來顯著降低閱讀流暢度；寫前確定讀者地區、寫完跑 grep 對齊
- [#207 地區慣用語直譯：keyword grep 抓不到、同源讀得懂會放行](regional-idioms-evade-keyword-bank/) — 地區用語除了單詞漂移（#112），還有慣用語直譯（拍腦袋 / 靠譜 / 接地氣 / 給力）；慣用語是開放集合、列舉式 grep 抓不到片語，且語意讀得懂讓同源審查者合理化放行、跟 #165 register 同源盲區同構；已知個案入 keyword bank 抓存量、新個案交在地讀者異源冷讀；漏抓慣用語是 design 缺口（要異源）不是 execution 缺口（加清單）
- [#203 避免濫用泛用詞：具體詞讓文章更深刻](avoid-overused-generic-words/) — 同一個泛用詞（坑 / 東西 / 搞 / 處理）反覆出現把不同情境壓成同一個模糊標籤、讀起來扁平；每個情境用它自己精確的詞（意外 / 陷阱 / 出問題 / 發生狀況）、詞彙變化本身是資訊；「坑」另有地區偏移面（簡中高頻、繁中少用）歸 #112；grep `坑|東西|搞|弄|處理一下` 命中密集是徵兆；是 #122 從句型下沉到用詞的具體化、#111 的相鄰軸（泛用 vs 具體）
- [#113 商業邏輯論述要 self-contained：不依賴 code 才能被理解](prose-self-contained-without-code-reference/) — 不放 code 的段落仍要 self-contained——用「那個 payload 第二段」「剛才的 controller」「就好 / 就能」這類 reference 等於把理解門檻轉嫁給讀者去翻 code；修法是用名詞 / 角色 / 條件描述、即使讀者跳過所有 code block 也能理解論述
- [#114 Multi-pass review 的 frame 顆粒度盲點](multi-pass-review-frame-granularity-blindspot/) — Multi-pass 用「規則 frame」掃描有效抓結構性違反、抓不到字句層具體訊號（口語修辭 / 地區漂移 / 依賴 code / 廢話前綴）；同一 reviewer 跑多輪 catch 的東西高度相同；要擴大覆蓋度需要三機制——keyword bank（換工具）+ reader simulation（換視角）+ self-criticism（換層次）

Case-driven 寫作方法論系列（#115-119、從 [case-first-module-workflow skill](/posts/case-first-agent-team-review-workflow/) 抽出）：

- [#115 案例引用深度跟著 case 類型走](case-type-graded-citation-depth/) — skeleton / medium / rich case 各有不同承接深度；誤判類型 → 編造數字 / taxonomy（over-extrapolation）或漏掉 case 揭露的 mechanism；引用前先看 case 行數 + 內容密度判類型、決定該寫「揭露 X 方向」「揭露 N 個機制」還是「揭露具體數字 / 設計」
- [#116 引用案例要分觀察層 / 判讀層、強化詞是錯位訊號](fact-vs-derive-citation-layering/) — 引用案例（特別是 rich case）時、case 內容分兩層：觀察層（具體 fact）跟判讀層（作者推論）；兩層要分層標明、避免把作者判讀升級成 case fact；強化詞（才是 / 必須 / 一定 / 關鍵是）通常是錯位訊號、保留 case 原文的條件性表述（取決於 / 核心瓶頸 / 主要驅動）
- [#117 跨多個 case 合成的 frame 必須標為章節合成、非 case 原文](cross-case-synthesized-frame-must-be-labeled/) — 當段落把多個 case 的失效訊號抽象為更高層 frame（如「跨工具回查壓力」「平台責任切分」）、要 explicit 標為「本章合成、非 case 原文」；否則章節 derive 會被讀者當成 case fact、回查時找不到對應段；07 LLM 模組 batch 1 兩個 high issue 都屬此類
- [#118 Standard-driven 取代 Case-driven 適用 standard framework 比 case 庫成熟的領域](standard-driven-vs-case-driven-domain-judgment/) — 並非所有領域都該走 case-driven；判斷四維度（議題穩定度 / case 公開度 / standard 成熟度 / 維護半衰期）；LLM 安全屬 standard-driven 領域（OWASP LLM Top 10 + NIST AI RMF 已成型、case 半衰期 6 個月）、不該勉強建 case 庫；分散式系統 / 安全控制面屬 case-driven 領域
- [#119 章節已有 routing skeleton 走補強段、不空白擴章](routing-layer-chapter-recognition/) — 章節結構分兩類：空白章節 vs routing layer 章節（已有 threat scope + 問題節點表 + 風險邊界 + 案例觸發段）；擴章策略要對應結構——空白章節走 case-driven 大幅擴章、routing layer 章節走補強段（在現有結構內補 mechanism 深化）；07 batch 1 三個 H issue 都來自誤套空白擴章策略到 routing layer 章節
- [#120 案例引用三段式段落結構：概念定義 → case 引用 → 通用展開](case-citation-three-part-structure/) — Case 引用段落要走三段式結構紀律——段首是概念定義句、case 引用退到第二位置、最後通用工程知識展開；段首被 case 引用取代是 06 模組最大宗 systemic 違規（11/12 段都犯）；本卡跟 #115/#116/#117 是 case 引用紀律的不同 axis（引用深度 / 內部分層 / 跨 case 合成 / 段落結構）
- [#121 Agent team context 隔離設計：用不同 instance 換 frame、平行 background 保護主 context](agent-team-context-isolation/) — Multi-pass review 跨輪 frame（#83）跟跨 reviewer instance 隔離（本卡）是兩個 axis；context 隔離設計讓主 context 只接精煉摘要、節省 ~80% token；跟 #114 同 reviewer 多輪 catch 同類錯形成互補解法

Cadence 同質化系列（#122-124、從 backend/07 51 vendor 批量 review 反向抽出、症狀 / 機制 / enforcement 時機三軸）：

- [#122 Cadence 同質化是模板的隱形維度](cadence-homogenization-in-batch-writing/) — 規範定義「模板」通常只指內容欄位（規模對照 / tripwire / 失敗模式）、忽略句型骨架 / 段首語 / 段末收尾語 / 表格前導句 / 過渡詞也是模板；批量寫作時最易讓 cadence 同質化、單篇看起來合規、連讀多篇才浮現預期化；自檢要 grep 首句 / 段末句 / 表格前導句、不是只看欄位；51 vendor 都用「四件事 → 任一缺失就是 X 邊界的待補項目」是案例
- [#123 多重硬規範同時生效會把 cadence 推向便利解](compliance-optimum-converges-cadence/) — N 個硬 constraint 同時 enforce 時、找到一個「都通過」的 framing 後批量寫作會把它複製到所有檔；cadence 同質化是合規最佳解的副作用、不是違規；對策是拉開 constraint 或加 anti-template constraint、或 pilot phase 強制變體；不是只發生在寫作、code gen / API doc 批量同骨；是 #67 在「批量寫作」的具體機制
- [#124 Emergence-class 違規規則化不了、要 stage 內抽樣](emergence-violations-need-in-stream-sampling/) — 違規分字面 / 結構 / emergence 三類、enforcement 時機對應；字面（emoji）可 hook、結構（章節缺失）可 lint、emergence（cadence 同質）只能 stage 內抽樣；最佳時機 batch 進度 10-20%（emergence 訊號剛夠強且修正成本還可控）；補 #82 的 timing 軸、補 #83 multi-pass 的時間分散軸

Meta-卡（#125-126、從 #122-124 + 既有卡跨 surface 抽出）：

- [#125 Collapse 是隱形預設](collapse-is-implicit-default/) — 跨 surface meta；decision (#80) / dialogue (#79) / output (#123) 三個 surface 都有同一個 collapse pattern — 高維選擇空間被便利驅動 reduce 到 1-2 個窄格、且因為「便利 / 合規 / 簡潔」被當預設、不被覺察；對策不是消除 collapse、是讓設計者主動選擇要 collapse 哪一維；預設展開、選窄要證明
- [#126 寫作 review 是多軸完整性、不是單軸深度](writing-review-multi-axis-completeness/) — Review 完整性是七軸（frame / instance / surface / scope / cadence / timing / granularity）交集、缺軸不缺深度；對應 #83 / #121 / #97 / #95 / #122 / #124 / #114；單軸越做越深會 systematic miss 對應軸盲點；設計 review 流程時 enumerate 七軸覆蓋狀況、不是加輪數

Cadence + 結構雙軸延伸（#127、從 5 篇 migration playbook batch 抽出、跟 cadence 系列形成「framing layer + structure layer」雙軸）：

- [#127 Process content 結構由最大差異維度決定](content-structure-by-max-diff-dimension/) — 跨 X process content（migration / upgrade / rollout）結構不是 universal、由 source / target 的 *最大差異維度* 決定；6 種 migration / process type 實證（schema 差 / drop-in / operational / multi-tool / paradigm / topology re-layout）跑出 6 種結構；寫前必須跑 *diff dimension audit*、跳過會套錯模板（phase 變空白或 process 強行線性）；補 #122 在「結構 layer」的對偶、同時是 #125 在 content structure surface 的子實例；6 type 是 *axis-aligned simplification*、非窮盡分類（見卡內 limitation 段）
- [#128 Data topology 是 process content 的第 6 audit 維度](data-topology-as-audit-dimension/) — #127 原 5 維 audit 漏 data topology（sharding / partition / replication / region / co-location 5 sub-dimension）；topology 不在既有 5 維任一個、但決定 re-sharding / partition redesign / multi-region rollout 的結構；本卡擴 audit 到 6 維、新增 Type F「Topology re-layout」結構；從 Redis cluster re-sharding dogfood 抽出、是 #127 self-aware limitation 段「audit 維度補新軸」預測命中的結果
- [#129 公開案例量是 vendor 社群活躍度 signal](public-case-availability-vendor-signal/) — vendor 選型時、公開 customer engineering case 的累積量是社群活躍度與長期可維護性的合併信號；案例少不等於技術差、但可能代表社群稀薄、DevRel 投入低或議題公開度低；應跟 release 節奏、文件品質、issue 回應與生態整合一起判讀

教材設計反省系列（#130-133、從 Backend 教學定位對照 LLM / Go 目錄抽出）：

- [#130 教材目標先於決策框架](teaching-goal-before-decision-frame/) — 教材的上位目標是讓讀者學會領域心智模型、操作語意與演進路徑；服務能力、風險、成本與決策只是教學中的必要概念框架；若決策框架取代教材目標、文章會變成選型分析或治理文件
- [#131 教材完整性要用讀者旅程驗證](teaching-completeness-by-learner-journey/) — 章節數、案例數、vendor 覆蓋度只能證明素材充足；成熟教材要能回答不同讀者從哪開始、按什麼順序讀、讀完能做什麼；LLM / Go 的成熟訊號是讀者旅程、學習梯度與主題導讀
- [#132 貫穿式案例是服務教材的教學骨架](throughline-case-as-teaching-spine/) — 服務型教材需要一條可重播的貫穿式案例，把資料庫、快取、queue、觀測、部署、可靠性、資安、事故與容量串成同一個服務演進路徑；沒有主線案例時、章節各自正確但交接難學
- [#133 服務頁教材合約](service-page-teaching-contract/) — 服務頁是一篇能獨立教會讀者某個服務能力的教材；成熟服務頁追求單篇教材的討論細節與漸進教學，而非統一章節模板；章節路線要依服務對象、分類責任與使用情境設計

教材入口同步議題（#139、從 content/business/ 建立後漏首頁入口抽出）：

- [#139 新增頂層 content 資料夾要同步首頁 _index.md 入口](top-level-content-folder-needs-homepage-entry/) — Hugo 不會 auto-list 頂層資料夾、首頁清單是 content/_index.md 的手動 markdown；新增 content/<module>/ 必須同 commit 加首頁入口、否則模組對首頁讀者完全不可發現；補進 AGENTS.md 完稿檢查清單成為結構性保證；是 #44 SSoT 在「首頁清單」維度 + #97 metadata surface 在「上層索引」維度的具體案例

WRAP 寫作 framing 風險（#140-142、從 3 篇 case-analyses 套 WRAP 連續踩坑抽出、三卡互補）：

- [#140 WRAP Widen Options 容易塌成稻草人 framing、要改 evidence weight 結構](wrap-widen-options-strawman-risk/) — WRAP Widen Options 段在案例寫作易塌成「列爛選項 → 打掉 → 留正解」修辭、3 個 reviewer 獨立 catch 同 pattern 證明是 systematic 陷阱；修法是選項並陳合理因果鏈（每個有 prior + prediction）、Reality Test 改 evidence-based weight assessment + Falsifier；判別線是「刪 Reality Test 後讀者能不能猜出正解」；是 #125 Collapse 在 WRAP 寫作 surface 的具體 instance、#79 多軸的姊妹卡

- [#141 WRAP 是寫作者的內部工具、不是文章章節結構](wrap-as-internal-tool-not-section-structure/) — WRAP 七步驟（Anchor Check / Step 0 / Widen Options / Reality Test / Attain Distance / Prepare to be Wrong / Tripwire）是寫作者背後的 review checklist、不是讀者看的章節標題；暴露 process metadata 給讀者會踩三個壞 effect：預設讀者認知、塞滿分析報告 meta dialogue、同論點重複預告 3 次；修法是 WRAP 工作在腦中跑完、文章章節服從教學流程（開頭 → 事件本身 → 為什麼 X → 結構性機制 → 長期影響 → 預警訊號 → 可遷移框架）；是 #140 的上位原則、處理 surface presentation 而非 Widen Options 內容違規

- [#142 文章主體要對齊標題承諾、WRAP 內部分析不該喧賓奪主](article-body-must-align-with-title-commitment/) — 即使章節標題改成教學風格（#141 已處理）、章節內容仍可能偏離標題承諾；WRAP Widen Options + Reality Test 內容即使方法論做得好、不是標題承諾的內容就不該獨立成段；附帶議題：為了支撐 prior 引用 hallucinated source（「a16z / Sequoia 公開報告」這類沒實際出處的引用）的 fidelity 風險、把 WRAP 內部分析從主體移除就自然降低；修法是寫稿前明確標題承諾、跑完 WRAP 內部分析後區分主結論 vs 分析過程、完稿跑「標題對齊測試」；是 #141 的姊妹卡（#141 處理 surface、本卡處理 scope）

外部分析文章轉教學型商業分析（#143-145、從 content/business/ 文章演變與 reading-frameworks 抽出）：

- [#143 外部分析文章要先拆成事實、作者判讀、本文推導](external-analysis-source-layering/) — 外部分析師文章是 source、不是 case fact；改寫前先拆三層（可驗證事實 / 原作者判讀 / 本文推導），避免分析師 frame 被讀者誤當事實、也避免本文合成框架失去可回溯性；是 #116 fact vs derive 在 analyst source surface 的對應版
- [#144 跨領域分析要先定位讀者層級、再決定術語密度](cross-domain-reader-level-alignment/) — 商業分析寫給工程背景讀者時、不能繼承 VC / founder / industry insider 讀者假設；先辨識原文 reader contract、再用術語密度與因果鏈步長決定是否降一級；是 #131 讀者旅程在跨領域商業分析的具體化
- [#145 外部分析改寫的交付物是可遷移框架、不是風格轉換](analysis-rewrite-must-deliver-transferable-framework/) — AI 改寫外部分析文章時、任務目標是抽出讀者可帶到下一個事件的判讀框架，不能停在把語氣改成本站風格；正文要交付訊號、機制、長期影響、預警與下一步路由；是 #141/#142 之後的 deliverable 層原則

Case 引用對齊延伸（#146、從 backend/01.13 reviewer audit 抽出、補 #115-120 case-driven 系列在「case 庫不對齊章節主題」的特殊情境）：

- [#146 案例庫不對齊章節主題時用反向追問取代強掛](case-misalignment-reverse-inquiry/) — 案例庫主軸跟章節主題不在同一維度時、引用框架要從「正向掛入」切換到「反向追問」；強掛 case 的根因是「想填滿案例段」的模板配額、與 #122 cadence 同質化同源；反向追問三步驟（誠實標主軸差異 / 案例當「沒做 B 的後果」/ 明示分層追問）；補 #115（引用深度）/ #120（段落結構）在 case 對齊維度的上游、補 #122（cadence）在 case 引用 surface 的具體成因 + 修法

規範化跟自審斷層（#147、從 #146 立規範後 5 篇章節仍犯該規範的諷刺案例抽出）：

- [#147 規範化跟自審是兩種認知任務、立規範當下無法保護同批稿件](rule-codification-vs-self-audit/) — 把反模式抽象成規範卡跟在自己稿件辨識該反模式實例是兩種不同認知任務、視角分別是 outside-in（歸納）vs inside-out（比對）；案例：#146 才剛立「看 X 如何 Y」是反模式、同 batch 5 篇章節仍有 11 處未被察覺、Round 2 reviewer 才 catch；修法三層機制 — grep keyword（字面層）/ checklist 自審（結構層）/ reviewer in-stream（frame 層）；補 #114 在「規範作者本人 reviewer」的具體實例、補 #122 / #124 在「規範化動作本身」這個介入點的修法

跨輪 review 停止判讀（#148、從 backend 3 輪 review 38 個 finding 零重疊的實證抽出；#202 從 dotfile 系列三輪 43 個 finding 抽出最低輪數硬底線）：

- [#202 多輪審查至少三輪是硬底線](multi-round-review-minimum-three-rounds/) — Round 3 的 steelman/outbound frame 覆蓋 Round 1-2 結構性盲區（漏選項、反向引用、搜尋落點），每次實測都找出 10+ 項；問「要不要跑 Round 3」等於問「要不要跑一定有產出的審查」；三輪是硬底線、Round 3 結束後才進入停止判讀

- [#148 跨輪 review 停止訊號是 frame 涵蓋、不是 finding 數遞減](cross-round-review-stopping-signal/) — 判斷「該不該再來一輪 review」的訊號是「frame 軸是否還有未動」、不是「finding 變少」；多輪 review 的 ROI 不是 monotonically decreasing、Round 3 finding 數可能比 Round 1 / 2 多、但內容從 surface 往 structural / meta 層走；停止判讀 4 訊號（新 frame 卡住 / finding 退回 surface / 修法成本超過邊際價值 / frame 重複）；補 #114 / #126 / #147 沒覆蓋的「何時停止」缺口
- [#149 字句層 review：keyword bank 命中是候選、不是判決](keyword-bank-hit-is-candidate-not-verdict/) — 偵測（grep 命中可疑訊號）跟判定（這個命中是不是違規）是兩個認知步驟；reviewer 容易把「不是 A 而是 B」的命中合理化成「可接受反例對照」而放行、偵測成功判定失敗；判定準則用「概念位置」—— 否定在建立核心概念就改正向、只在明示反例段落才保留；另有訴諸群體贅語（「很多人卡在」）無固定關鍵詞、keyword bank 結構上抓不到、靠 reader-simulation 補；是 #114（偵測層）的判定層 sibling、夾在 #94（別過度刪對照）與正向陳述優先之間的判別線
- [#150 教材用中性陳述、不對讀者喊話](teaching-register-states-not-addresses-reader/) — 教材的 register 是中性陳述概念、不是對讀者說話；三形式（安撫「很多人卡在」/ 第二人稱「你天天寫」/ 祈使「先讀懂、別搞混」）共用「把讀者當要管理的對話對象」的違反；問題不在精度（「你天天寫的 int count」精度完全正確）、在 stance；修法換中性指稱或描述性名詞標題；是 #111（精度軸）的 register sibling、#149（review-process）的 content 對偶、補 AGENTS 原則六沒覆蓋的 stance 維度；邊界是 hook / narrative 段落輕度第二人稱可留
- [#151 教材給技術理由、不替方案下品質評價](teaching-gives-reasons-not-quality-verdicts/) — 自評誇飾（教科書級 / 堪稱經典 / 完美契合 / 漂亮地解決）傳遞作者滿意度而非概念、且品質 verdict 會頂替技術理由（寫「X 是教科書級的適配」就少寫「X 為什麼適配」）；修法把評價換成機制 / 條件；跟 #111 同屬誇飾大類但評價對象不同（#111 誇張技術屬性、本卡評價方案品質）、#150 的 stance sibling（#150 管理讀者、本卡評價方案）、#94 空降斷言在品質評價維度的變體、違反 AGENTS 原則七；邊界 narrative / 復盤型內容的評價是合理 register
- [#152 教材把設計選擇講成選擇、不講成必然或天性](design-choices-framed-as-choices-not-necessity/) — 本質主義 / 必然性框架（天生 / 本質就是 / 必然 / 唯一）把設計選擇講成自然法則、抹掉設計能動性；是「機會成本語氣 vs 絕對主義」的 subtype、比命令式絕對（應該做 X）更隱形（必然式偽裝成事實、躲過 review）；sharp feature 是常局部牴觸作者自己在別處的條件性立場（HOF 文章通篇講條件性、唯獨「天生」講成必然）；修法還原條件性（在選了某前提後 X 才以此形式成立）；是 #151 / #94 空降家族的 sibling（必然框架空降 vs 品質 verdict 空降 vs 刪對照空降）、補 compositional-writing 原則三的必然性維度；邊界物理 / 法律 / 數學事實可講必然
- [#153 Review 漏抓先分 design gap 與 execution gap](review-miss-diagnose-design-vs-execution-gap/) — review 漏抓某類問題有兩成因：design gap（框架沒對應 frame）vs execution gap（框架有 frame、reviewer 沒跑）；修法相反（前者改框架、後者改執行），診斷前先分清否則 framework bloat 或永遠漏同類；「加 keyword」是最誘人的假修法（只解 design gap 偵測 sub-type、對沒跑的輪無效）；case 是 register 類漏抓（兩 gap 都有：跳過輪 9/10 + 輪 9 缺 register lens）；是 #114（design gap 一面向）的上位、#147（execution 側）的一般化、#149（偵測 vs 判定）的成因分層 sibling
- [#154 教材的『重點 / 總結』段是內容發散的訊號、該重組正文不該補丁](summary-section-signals-scattered-prose/) — 單篇文章尾端「重述自己」的總結段（重點 / 小結 / TL;DR）是正文組織不佳的補丁；判準是「刪掉總結段、正文站不站得住」—— 站得住證明總結冗餘、站不住是正文要重組、兩種結果都指向不該留總結段；處理段內容先分提醒（養成習慣 / 回頭確認、刪）vs 概念（為何這樣設計、併回正文對應段）；補丁掩蓋發散會持續累積、概念被埋在尾端反而讓正文缺角違反「核心原則先行」；邊界是跨章模組的導覽型 summary（傳遞結構 / 路由這個新資訊）不適用；是 #64（在 source 同層修、不在下游補）的寫作層同構、#150 的結構層 sibling（#150 字句 stance、本卡整段結構）、#151 的「不貢獻新概念就刪」同判準、#153 的 diagnose 先於修法同類動作
- [#155 引用章節用語意標題、不用位置編號](reference-by-semantic-title-not-number/) — 編號是結構排列的 derivation、不是 fact；結構重排時編號位移、引用點 silent 指向錯的內容而不報錯（misdirected 比 dangling 難偵測 — broken link 會 404、錯位編號會成功解析到錯的東西）；修法是每個結構單位給語意標題、引用一律取語意半邊、編號只作當下排序導覽；邊界是發布方凍結的編號（RFC 段號 / 法條）是 fact 可引用；是 #44 SSoT 在結構引用維度的實例、#93 identifier-as-fact 家族 sibling、#84 命名 cross-call-site 檢驗在標題的應用、#97 的 surface 掃描面在引用句（navigation surface）的延伸
- [#156 集合命名用角色、不內嵌數量](name-collections-by-role-not-count/) — 「核心七問」「成長六階段」「四大支柱」把成員數烤進名字、數量是 membership 的 derivation、成員增減時名稱先失真、且名稱是被複製最多次的字串、缺陷隨引用繁殖；修法是命名只承載角色與層級（核心問題 / 撞牆階段）、數量讓清單自己呈現；邊界三種數字可留（外部凍結品牌 SOLID / OWASP Top 10、數字是概念內容的 #42 兩次門檻、緊鄰清單的行內計數）；是 #155 的命名端 sibling（#155 修引用端、本卡讓「語意標題是穩定錨」前提成立 — #155 初版自用「見核心七問」當正面範例而未察覺、證明是獨立檢查維度）、#44 SSoT 擴散最快形態、#84 命名 review 的數量維度、#67 便利驅動命名的實例
- [#157 語意錨用單一字串](semantic-anchor-single-string/) — 同一結構單位有兩個同義名稱（標題「決策記錄 + scaffold 建議」、引用「決策收斂階段」）時、語意引用的兩收益同時失效：grep 掃 A 漏 B、重排修復退回人腦對應；canonical 取標題語意半邊、全部引用統一；是 #155 / #156 之後的第三塊（引用端 → 命名內容 → 命名唯一性）、#44 在「同語意雙字串」的隱蔽形態、#84 輪 3 同概念同名檢查在結構單位引用場景的應用
- [#204 路由條目要自包含：跳轉單位不依賴鄰條上下文](routing-entry-self-contained/) — 路由段落（下一步 / 依情境讀法 / MOC）的每條 bullet 是獨立跳轉單位、讀者跳讀只看命中的那條；「見同篇的 XX 段」把目標容器押在鄰條指代上、「同篇」還會被解析成本篇、讀者在錯的文章裡搜不存在的段落；拆分判準是讀者情境數不是目標文章數、兩情境指同一篇時重複完整連結合規；掃 `rg "同篇|上一條|前述|該篇"` 命中在 routing 段落即高風險；是 #155 錨點字串層之外的容器層 sibling（實測兩層各踩一次、各修一輪才收斂）、#113 self-contained 在 navigation surface 的對應、#157 引用-命名鏈的第四塊
- [#205 合成章的引力：框架章會把主寫章的案例細節吸走](synthesis-chapter-gravity/) — 教學模組的合成型框架章（從全案例庫推導、無專屬案例）在寫作壓力下把 anchor 案例的機制 / 清單 / 時序完整吸進來、SSoT map 的主寫方向被靜默反轉（實測 6 個 High 重複展開 issue 有 4 個同此根因）；硬規則是合成章引用案例只允許「一句話結論 + 數字 + link 主寫章」、初稿可最後寫或回頭壓縮；是 #44 在「章節 × 案例」矩陣的失效模式、#204 自包含 vs 重複張力的對照組、#155 「寫前產物寫後失真」家族
- [#206 預測性索引要有寫後回填輪](predictive-index-needs-backfill-pass/) — 大綱的案例支撐欄與 case 檔的對應章節欄是寫作前的預測、正文完成後不回填就雙向失真（漏列實際引用、保留未實現預測、實測佔一致性 review 22 issue 中 10 個）；回填是正文完成後的固定機械工序、跟 lint 同級、讓寫作期可以放心偏離預測；是 #155/#156 「derivation 會過期」家族、#205 的伴生卡（SSoT map = 宣告 + 寫作紀律 + 回填工序三件套）
- [#158 決策表兩列同時命中且結論相反：缺的是上游區分維度](decision-table-conflict-reveals-missing-dimension/) — 真實案例 dry-run 同時命中兩列且結論相反時、修法在表外：案例承載兩種身分（要賣的產品 vs 業務的工具）、補前置澄清問把身分拆開、兩列各回適用域（拆不出身分的才是規則真衝突、回表內改規則）；表內加優先序 / 改窄列是蓋住矛盾；單列正確的表仍可能整體矛盾、逐列 review 抓不到、要用帶語境的真實案例 dry-run；是 #127/#128 維度補軸家族、#153 design gap 的決策表形態、#69 dry-run = 先看 RED
- [#159 入口分流要放在詞彙牆之前](audience-fork-before-jargon-wall/) — 為門外讀者補的章節、入口頁開頭全是門內詞彙、分流句埋在數十行後 = 目標讀者活不到分流點；分流位置由最外圈讀者的存活範圍決定、不由內容邏輯歸屬決定；是 #131 讀者旅程在入口單點的特化、#139 結構性不可達之外的體驗性不可達（link checker 與結構審查都會通過、只有 reader simulation 抓得到）、把入口頁開頭段視為 #97 navigation surface 的延伸（本卡的擴張、原卡分類未列）
- [#160 跨 surface 同主題內容要重新語境化、不是搬運](cross-surface-recontextualize-not-transplant/) — 「各寫一份、語境化在各 surface 內」用複製貼上執行 = 最差組合：兩份字面綁定（隱性同源、改一邊另一邊 silent 漂移）、卻各自沒為自己的讀者最佳化；可操作判準是跨 surface grep 逐字相同的完整句；教材版長成「為什麼 + 案例」、協議版長成「步驟 + 條件」、句子自然不同；是 #44 未宣告多源、#122 的跨 surface 對應、#147 字面合規 vs 實質合規、#150 register 是語境化最敏感維度
- [#161 摘要壓縮可以丟細節、不可以改模態](summary-compression-preserves-modality/) — description / hook 濃縮規則時可以丟細節、不可改模態：「可延後但要記錄」壓成「不可跳過」= 條件允許變絕對禁令、規則設計的出口被摘要抹掉；判準是讀者只依摘要行動會不會做出本體不要求的事；模態詞長、壓縮時最先被砍、「更有力」就是失真訊號；是 #97 的模態維度、#142 的反向對齊軸、#152 模態失真家族的壓縮層形態、#67 摘要字數壓力放大便利重力
- [#162 引用卡片用被引卡自己的分類詞彙](cite-cards-with-their-own-taxonomy/) — 關係宣告憑記憶轉述、把被引卡明確分開的兩類（metadata vs navigation surface）併成一類；記憶存概念不存分類結構、被引卡越熟越不會打開查；修法是寫關係段前重開被引卡的結論段與分類表、逐條關係配一次「找到支撐句」核對；是 #109 跨卡片版、#107 錨點在引用句的對應、#116 引用準確性家族、#97 的觸發 case 恰為引用它時錯置分類
- [#163 多階段流程的 artifact 欄位契約](pipeline-artifact-field-contract/) — 下游宣稱「以上游 X 為輸入」的成立條件是欄位層級可推導：下游每欄對到上游欄或明文推導規則；缺口安靜（上游七欄、下游要的第八種資訊沒人說從哪來）、執行者自由心證、且缺的常是分支開關欄；檢查法是逐欄走查標「直給 / 明文推導 / 缺」；是 #153 design gap 的交接形態、#68 交接處 checkpoint、#158 同族組合失效（規則間矛盾 vs 階段間缺口）、#44 推導規則要收斂成明文單源
- [#165 register 違規：偵測可機械化、判定要靠文體異源的眼睛](register-violation-needs-cross-style-eyes/) — 寫作違規分形式違規（emoji / 編號 / 連結、確定性、進工具鏈）與 register / 品味違規（概念前置 / 否定起手 / 喊話 / 誇飾、判定有不可消除的品味核心）；「不是 X 而是 Y」的陷阱是偵測可機械化偽裝成判定可機械化、誘導無限疊檢查方法（grep → 概念位置 → 行為測試）卻始終放水；更深因是 LLM 作者與 reviewer 共享文體、同源自審對 register 有結構上限、加再多輪都跨不過；結構解是文體異源視角（人類冷讀 / reader-simulation / 對抗文體 reviewer）、本身就比更好的檢查方法有效；是 #149 判定放水的根因上層、#147 自審執行對 register 的失效面、#82 字面 vs 行為的極限、#95 scope 軸的 source 軸對偶（後續被 #166 校正：「不是 X 而是 Y」子集本質是資訊結構問題、判定可操作、異源降為補充）
- [#166 重點優先陳述是跨語言的資訊結構原則、不是中文句型問題](lead-with-the-point-cross-language/) — 正向陳述優先的本質是資訊結構效率（讀者拿到核心概念的認知步驟越少越好）；「不是 X、而是 Y」表達能力差是因為重點後置、讓讀者先處理被否定的 X；缺陷跨語言成立 —— 英 not X but Y、日 X ではなく Y 同樣高頻、換語言不打破（證偽過的反例假設）；判別線「核心概念在不在最前」統一 #94（重點先行合法）與 #149（重點後置違規）、且可操作；LLM 放水根因是高頻偏置（把語料高頻句型評為表達好、跨語言）；主解是強制執行重點位置判準、#165 的異源降為補充；是 #165 的上層 + 校正（把 register 從品味上限拉回資訊結構可操作判準）、#149 概念位置的正名、#94/#149 判別線的統一、#153 把 execution gap 誤判 design 上限的實證
- [#167 修法是新違規的來源、且常引入同類變體](remediation-introduces-sibling-variants/) — 修法（改寫違規句、補 lint 規則 / pattern）這個動作本身引入新違規、且常是同類問題的變體（修「不是 X、而是 Y」就暴露「不是 X — 是 Y」、補一個 pattern 漏下一個）；review scope 要涵蓋修法後的產物、停止判斷不能停在「修完這批」、同類變體靠判準（重點位置）收斂不靠窮舉 pattern；實證是這次 POS pattern 連接詞清單擴兩次仍漏第四個 + 四輪每輪抓前輪修法引入的；是 #166 枚舉不完的過程面、#95 scope 的時間軸、#153 新 gap 來源、#148 停止訊號含修法產物、#149 判定優先在 remediation 的應用
- [#168 多輪審查要有冷讀者 frame](cold-reader-frame-vs-informed-reviewer/) — 模擬讀者要分知情（讀完全部走旅程）與冷讀（經搜尋 / 直連落在單篇、零脈絡）；知情 reviewer 自動腦補脈絡、結構性看不見「洩漏撰寫者預設前提的行話」（未定義的「家族」「上述」「如前所述」）、只有冷讀者立刻卡住；原子 / Zettelkasten / glossary / 可直連單篇落地的內容必跑冷讀 frame、不可只靠旅程 frame；實證 til/terms 14 卡旅程審查全 A 卻漏「連到家族」行話；是 #165 文體異源在「讀者脈絡」維度的對偶（同源腦補 vs 異源冷讀）、#131 讀者旅程的單卡冷讀補面、#159 詞彙牆在單卡落地的形態、已回饋 multi-round-review 補 B′ 冷讀 frame
- [#169 原子筆記要有向上的議題入口](atomic-note-needs-situational-entry/) — 承載知識的原子卡不是字典條目：字典答「這個詞是什麼」、承載知識答「你在討論什麼議題、撞到什麼問題、才需要這知識」、從情境進入非從定義；撰寫者有預設前提讀者沒有、做法是建議題 hub（以讀者會遇到的問題為題）討論再分流到術語卡、術語卡頂回指它出自哪個議題；沒這層卡淪字典、搜尋落地者讀完仍不知對他何用；是 #131 教材讀者旅程在單張原子筆記的特化（課程旅程 vs 單卡進入動機）、#159 入口分流的內容動機面、卡片盒「為何讀這張卡」原則的落地
- [讀者不需要知道的資訊不該出現在最終文件](reader-does-not-need-to-know/) — meta 資訊（寫作動機、邊界聲明、脈絡解釋）服務作者不服務讀者；AI 生成傾向把推理中間產物外露到最終文件；判準是「拿掉後讀者體驗變不變差」；跟列舉殘留卡是同根原則的兩種表現（meta 動機 + 範圍枚舉）
- [列舉與數字殘留在定義型文件會製造維護債務](enumeration-creates-maintenance-debt/) — 定義型文件的冗餘列舉（A-G）和描述性數字（9 個函式）是撰寫推理殘留、維護成本高但閱讀價值低；判準「拿掉後理解不受影響 → 刪除」；區分冗餘列舉 vs 定義列舉、描述性數字 vs 規範性數字；是 #96 的鏡像（scope 文件要 enumerate、定義型文件的冗餘列舉要刪）、#156 在正文定義層的對應、#67 便利驅動殘留的具體形態

讀者定位與跨專業溝通（從 infra 教學模組寫作 retrospective 抽出）：

- [讀者是缺經驗的專業人士、不是外行人](audience-is-professional-not-layperson/) — 技術教材的讀者定位是缺乏特定領域經驗的專業人士、寫法是補足經驗缺口而非從零科普；宣導式語氣（「跑得好好的」「你可能不知道」）預設讀者無能、降低教材可信度；替代是直接描述情境、列操作需求、說明不做的後果
- [跨專業溝通用情境遞進、不用比喻堆疊](cross-expertise-communication-scenario-not-analogy/) — 向非本領域專業人士解釋技術議題時、減少術語並從簡單情境遞進到複雜情境、比堆疊比喻有效；比喻傳遞形狀但不傳遞嚴重性、在細節處崩解、且隱含「對方聽不懂」的預設；情境遞進讓對方用自己熟悉的決策維度（成本、風險、時間）消化資訊
- [技術教材要內嵌管理層可彙報的資訊](technical-content-needs-management-reportable-info/) — 技術段落旁嵌入成本量級、時程估算、進度指標與決策簽核點；工程師讀完技術做法的同時拿到向上彙報的素材、不需要翻另一篇溝通指南；成本用量級不用精確數、時程用範圍不用單點
- [多輪審查缺 outside-in 讀者 frame](review-lacks-outside-in-reader-frames/) — review 框架全部從已寫內容出發（inside-out），缺從讀者需求出發的 frame（outside-in）；六個盲點由使用者而非 reviewer 發現：宣導語氣、管理層資訊、接手情境、工具指引、深度拆分、讀者定位；補五個 outside-in frame（persona register / downstream task / persona coverage / executable walkthrough / search landing）
- [操作指引的「怎麼做」要帶環境專屬的工具路徑](operational-how-needs-environment-specific-tooling/) — 「拍下現況」「匯出資料庫」在 container / VM / 共享主機對應完全不同的工具路徑；只寫動作不寫工具、讀者知道該做什麼但做不到；同根因被指出兩次的機制：第一輪補工具、第二輪補環境替代
- [跨 surface 鏡像的連結轉換 mapping 要窮盡](mirror-link-mapping-must-be-exhaustive/) — skill 鏡像的 references/principles/ → /report/ 轉換，slug 不匹配被誤判「沒有 report 卡」，三次 CI 失敗才修完；mapping 要用內容搜尋而非 slug 碰運氣
- [先建 report 卡再進 skill](report-before-skill-not-after/) — report 是原則的 SSoT、skill 是操作化引用；先改 skill 再補 report 會讓規則缺根據、report 被擠到「有空再做」；標準流程從 report 卡開始
- [常識是相對於讀者背景的](common-knowledge-is-relative-to-reader-background/) — 知識卡的建卡判準看「目標讀者群裡最不熟悉的那端能不能理解」、不看「作者覺得夠不夠常見」；.htaccess 對 PHP 工程師是常識、對 Node.js 工程師完全陌生；跨背景讀者群的教材幾乎所有領域特定術語都需要建卡
- [#170 Description 是未來自己的 recall trigger、不是文章摘要](description-as-recall-trigger/)

文章功能定位（從 posts/ 方法論文章分類檢討抽出）：

- [#199 一篇文章只承擔一種功能：SOP 跟 retrospective 混寫兩邊都做不好](single-function-per-article-sop-vs-retrospective/) — SOP 同時存在於 skill 和文章裡時、改 skill 文章沒同步更新會分歧；SOP 進 skill、文章精簡成 retrospective、兩者共存互連；判讀訊號是「步驟型段落跟證據型段落同時出現」（適用 posts/ 方法論文章、report 卡修法 + case 並存是正常形態）；是 #142 在文章層的對應、#154 減法測試判準的同類

Debugging 訊號辨識：

- [#200 Log 時間真空是 silent hang 訊號、happy log 是 anti-signal](time-vacuum-in-logs-signals-silent-hang/) — 非互動 process 最後一行是成功訊息、到被 cancel 之間有大段時間無輸出 = silent hang、不是時間不夠；辨識要從「訊息內容」轉到「訊息時序」；是 #20 在 CI timeout 場景的 evidence

Report 卡寫作：

- [#201 Report 卡的論述基礎記結論和 evidence 來源、不記檢討過程](report-basis-states-conclusion-not-process/) — 論述基礎段寫「從哪來 + evidence 邊界」、不寫「怎麼發起 + 用了什麼工具 + 主觀感受」；過程是作者工作紀錄、結論才是讀者的判讀前提 — description 要回答「你在什麼情境下需要這篇」（情境索引）、不只「這篇在講什麼」（內容索引）；類比 skill 的 description 讓系統自動觸發載入、文章的 description 讓未來自己在掃列表時自動判斷要不要進去讀；摘要式 description 讓列表頁一片「記錄了 / 介紹 / 整理出」無差異、recall 成本吃掉知識累積效益；是 #169 情境入口在 frontmatter surface 的體現、#131 讀者旅程第一站、#159 入口分流的欄位設計面

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

`#93 URL slug 是 fact` → `#44 Single Source of Truth` → `#82 字面攔截 vs 行為精煉` — 多工具各自推導 identifier 是 SSoT 違反、解法是把 identifier 升成 fact（顯式定義）、不要教工具學別人的推導規則；補 lint 規則作為 trigger（[#91](escalation-trigger-quantification/)）防止 debt 累積；引用錨點若是章節 / 階段編號這類位置推導值、同屬此家族、見 [#155](reference-by-semantic-title-not-number/)

### 路徑 17：寫作 review 要同步檢查 metadata surface

`#97 Metadata surface 要納入寫作 review 範圍` → `#96 適用範圍要展開成 file enumeration` → `#95 Multi-pass scope 要蓋同類風險區` → `#83 Writing 的 multi-pass review` → `#94 正向改寫要保留對照論據` — 先列 file scope，再列每個檔內的 title / description / heading / MOC hook / link label；最後用正向陳述與對照論據判準檢查讀者入口是否跟正文共用同一個概念錨點。description 對規則壓縮時的模態一致見 [#161](summary-compression-preserves-modality/)（可以丟細節、不可改模態）、入口頁開頭段的分流位置見 [#159](audience-fork-before-jargon-wall/)（分流要在最外圈讀者的存活範圍內）

### 路徑 18：對既有資安內容跑學術級 audit

`#99 資安教學審查標準對應風險不對稱` → `#100 false sense of security 主要失敗模式` → `#101 threat model 明確性` → `#102 mitigation 對位` → `#103 mitigation context-dependence` → `#104 security citation 時效精確` → `#105 audit recommendation 層級` — 先確立風險不對稱論證、再用 false sense of security 作為主要 audit 目標、跑四個 dimension（threat model 對稱 / mitigation mechanism 對位 / context 條件顯式 / citation 版本精確）、最後用 tier 化 recommendation 把每個 weakness 映射到 ship 決策（accept / minor / major / withdraw）。適用 backend/07-security-data-protection/ 章節 audit、跨高 stakes 領域（concurrency / distributed / financial / medical）也適用 dimension 1-3。

### 路徑 19：翻譯 / 轉譯文章時檢查術語是否錯位

`#107 術語翻譯要保留原文錨點` → `#108 中文壓縮術語要保留完整名詞頭` → `#109 術語翻譯要保留概念角色` → `#84 Naming 是 iterated artifact` → `#97 Metadata surface 要納入寫作 review 範圍` — 先保留原文讓概念可回溯，再確認中文離開原句仍有完整名詞頭；最後檢查名詞頭是否保留來源中的概念角色，並同步掃 heading / checklist / index entry。

### 路徑 20：寫教學模組 / 案例驅動內容時的引用紀律

先讀 [case-first + agent team review 方法論](/posts/case-first-agent-team-review-workflow/) 作 anchor、再依序 `#118 standard-driven vs case-driven 領域判讀` → `#119 章節已有 routing skeleton 走補強段` → `#115 案例引用深度跟著 case 類型走` → `#116 引用案例要分觀察層 / 判讀層` → `#117 跨多個 case 合成的 frame 必須標明` → `#120 案例引用三段式段落結構` — 先判讀領域該走 case-driven 還是 standard-driven、再判斷章節結構決定擴章策略；走 case-driven 時依 case 類型決定承接深度、引用 rich case 時分層標明 fact vs derive、跨多個 case 合成 frame 時 explicit 標為「本章合成」、最後用三段式（概念定義 → case 引用 → 通用展開）寫每個 case 引用段落。#116 / #117 順序可互換（先看單 case 內部 vs 先看跨 case 合成、看讀者習慣）。路徑尾補 standard citation surface 見 [#104](security-citation-currency-and-precision/)、補 agent team 工具設計見 [#121](agent-team-context-isolation/)。

### 路徑 21：寫 Backend 服務頁 / vendor 頁前的教材合約檢查

`#130 教材目標先於決策框架` → `#131 教材完整性要用讀者旅程驗證` → `#132 貫穿式案例是服務教材的教學骨架` → `#133 服務頁教材合約` — 先確認服務頁服務的是教材目標，再確認它能放進讀者旅程與 checkout episode；最後用服務頁教材合約檢查教學功能是否完整，章節路線則依服務對象與責任形狀設計。

### 路徑 22：跑字句層 review（正向陳述 / 口語修辭）卻仍漏 catch

`#114 Multi-pass review 的 frame 顆粒度盲點` → `#149 keyword bank 命中是候選、不是判決` → `#94 正向改寫要保留對照論據` → `#111 口語化修辭會稀釋技術精度` → `#147 規範化跟自審是兩種認知任務` → `#148 跨輪 review 停止訊號` — 先用 #114 把規則展開成 keyword bank 解偵測層（別靠記憶 sweep）；再用 #149 處理判定層（grep 命中後別把「建立概念的否定」合理化成「反例對照」放行、用「概念位置」判別）；判定的兩極由 #94（別過度刪對照）跟正向陳述優先（別過度留否定）夾出；#111 給字句層的具體訊號清單；#203 補「泛用詞濫用」（同一個泛用詞蓋過不同具體情境、坑 / 東西 / 搞、依情境換精確詞；「坑」的地區偏移面歸 #112）；#150 補「register/stance」軸（教材不對讀者喊話、跟 #111 精度軸正交）；#151 補「自評誇飾」（品質 verdict 頂替技術理由、跟 #111 同誇飾大類但評價對象不同）；#152 補「必然性框架」（把設計選擇講成天性、機會成本語氣的必然式 subtype）；#147 提醒「立了規範 / 跑了 grep」不等於判得對；#153 提醒漏抓先分 design gap（改框架）vs execution gap（改執行、別只加 keyword）；#165 揭露同源盲區現象（LLM 作者與 reviewer 共享文體、register 違規同源自審有上限）；#166 再校正一層 —— 把「不是 X、而是 Y」從「品味不可機械化」拉回「資訊結構：重點優先」這個跨語言可操作判準、主解是強制執行重點位置判準（核心概念在不在最前）、異源降為補充（換語言打不破、證偽過）；#167 提醒修法本身引入同類變體（補 POS pattern 連接詞清單擴兩次仍漏第四個）、review scope 要含修法後的產物、停止判斷不能停在「修完這批」；最後用 #148 判斷何時停止。

### 路徑 23：寫完文章、檢查尾端「重點 / 總結」段該不該留

`#154 總結段是內容發散的訊號` → `#64 在 source 同層修、不下游補` → `#150 教材不對讀者喊話` → `#199 SOP 跟 retrospective 混寫` → `#42 兩次門檻` — 寫完文章看到尾端有「重點 / 小結 / 結論 / TL;DR」段、先用 #154 的判準「刪掉它、正文站不站得住」診斷：站得住=冗餘（刪）、站不住=正文發散（重組、不靠總結救）。處理段內容分提醒（刪）vs 概念（按 #64 併回正文 source 位置、不在尾端打補丁）；提醒型常同時是 #150 的對讀者喊話。方法論文章同時塞 SOP 和驗證紀錄時用 #199 的減法測試判斷（去掉 SOP 看 retrospective 站不站得住）。真實樣本以「重述+路由混合型」最多、修法是外科式（切重述、留路由）；系統性出現（整個模組每章一個小結）時在模組層級統一決定、別逐章補丁 —— 此泛化暫按 #42 兩次門檻留 backlog、第二個系統性 smell 出現時抽獨立卡。

### 路徑 24：在活文件中命名與引用章節 / 階段 / 條列項

`#156 集合命名用角色、不內嵌數量` → `#157 語意錨用單一字串` → `#155 引用章節用語意標題、不用位置編號` → `#44 Single Source of Truth` → `#84 Naming 是 iterated artifact` — 先用 #156 淨化命名端：集合名稱抽掉成員數（「核心問題」不是「核心七問」）、否則標題一半是 derivation、引用端怎麼修都錨在會漂移的字串上；再用 #157 確認語意名是單一 canonical 字串（同義雙名讓 grep 掃 A 漏 B、重排修復退回人腦對應）；再用 #155 修引用端：「見 Stage N」「如第 N 點」換成語意標題（編號是排列的 derivation、重排時 silent 指向錯內容）；標題本身要通過 #84 的 cross-call-site 檢驗（單獨出現時讀者知道指什麼）；發布方凍結的編號與數量（RFC 段號 / 法條 / SOLID 五原則）是 fact、可用。結構重排或成員增減的 commit 要全 repo 掃、可用 `rg "Stage [0-9]|第 ?[一二三四五六七八九十0-9]+ ?(章|節|點|步|輪)|§[0-9]"`（引用端）跟 `rg "[一二三四五六七八九十0-9]+ ?(大|問|階段|支柱|原則|步驟|件事|個維度)"`（命名端）抓候選後逐處判讀。三卡各守一層（引用錨點 / 命名內容 / 命名唯一性）、檢查互不替代 — 只跑其中一層、另外兩層的違規仍然隱形。引用他卡的關係宣告另有一層：用被引卡自己的分類詞彙、逐條找支撐句、見 [#162](cite-cards-with-their-own-taxonomy/)。路由段落（下一步 / 依情境 / MOC）的引用再多一層容器要求：每條 bullet 自包含、目標文章連結顯式寫在句內、鄰條指代（同篇 / 上一條）在跳讀模式下必失效、見 [#204](routing-entry-self-contained/)。

### 路徑 25：設計判讀框架 / 多階段流程協議

`#158 決策表矛盾列 = 缺上游維度` → `#163 多階段 artifact 欄位契約` → `#153 design gap vs execution gap` → `#69 Test-First` — 設計判讀表或多階段流程後、用帶完整語境的真實案例 dry-run（#69 的 RED 精神：乾淨例子只會命中預想列）；兩列同時命中且結論相反 → 補前置澄清問（#158）；下游宣稱以上游為輸入 → 逐欄走查標「直給 / 明文推導 / 缺」（#163）；缺口歸因時先分 design gap（改框架）vs execution gap（改執行、#153）。

### 路徑 26：批量寫 sibling 文檔（多卡 / 多章）之前與之後

`#122 cadence 同質化` → `#123 多重硬規範收斂便利解` → `#160 跨 surface 重新語境化` → `#161 摘要模態` → `#147 規範化跟自審` → `#148 停止訊號` — 寫之前排開場 frame / 條目形態 / 敘事視角的輪替表（#122 的生成端防範）；同主題落兩個 surface 時憑概念重寫、不開雙視窗對照抄（#160）；每份的 description 跟本體比對模態（#161）；寫完的批次連讀比句式骨架、單份 review 抓不到同骨（#122）；自己立的規範要靠 reviewer 抓自己（#147）；同類 finding 第二次出現、把規則從 review 端升到生成端。

---

**Last Updated**: 2026-06-11（multi-round review Round 1-2 findings 抽象化）— 新增 #157-#163 七張卡：對 backend 0.21 + report #155/#156 + saas-tech-selection skill 的三輪 agent team review（compliance / fact-check / 一致性 → cadence / reader-sim / title 對齊）把 finding 分流成「既有卡實例」（第二人稱 → #150、必然性 → #152、三段同構 → #122、regex 漂移 → #44）與七個新原則：#157 語意錨單一字串（R1-C 抓到 Stage 5 標題與引用雙名）、#158 決策表矛盾列 = 缺上游維度（R2-B 用健身教練案例 dry-run 抓到 gate 兩列同時命中結論相反）、#159 入口分流在詞彙牆之前（R2-B reader-sim 抓到目標讀者活不到第 41 行的分流句）、#160 跨 surface 重新語境化不是搬運（R2-A 抓到三句逐字相同）、#161 摘要壓縮保留約束模態（R2-C 抓到 description 把「可延後但要記錄」壓成「不可跳過」）、#162 引用卡片用被引卡的分類詞彙（R1-B 抓到 #97 的 navigation surface 被轉述成 metadata surface）、#163 多階段 artifact 欄位契約（R2-B 抓到 BDD 七欄表推不出 event catalog 的失敗語意欄）。路徑 24 補 #157 進命名-引用鏈。

**Last Updated**: 2026-06-11（集合命名內嵌數量 retro）— 新增 #156 集合命名用角色、不內嵌數量：#155 立卡後使用者隨即指出「核心七問」「成長六階段」是另一層問題 — 核心問題加一問、「七」就在標題 / 引用 / 索引全面失真、且這跟編號引用是不同議題（編號寄生在引用句、數量寄生在名稱本身、名稱是被複製最多次的字串）；同 skill 當天已實際發生一次（四大支柱 → 六大支柱被迫全面改名）；最深訊號是 #155 卡初版自用「見核心七問」當正面範例而未察覺 — 修引用端時命名端的同型缺陷完全隱形、證明兩卡是獨立檢查維度；修法是命名只承載角色與層級、數量讓清單自己呈現；邊界三種數字可留（外部凍結品牌 / 概念閾值 / 緊鄰清單行內計數）；路徑 24 擴成「命名與引用」雙端檢查、補命名端掃描 regex。下一步同步 compositional-writing skill 與 saas-tech-selection 改名（核心七問 → 核心問題等）。

**Last Updated**: 2026-06-11（saas-tech-selection skill 階段重編號 retro）— 新增 #155 引用章節用語意標題、不用位置編號：設計多階段訪談 skill 時各檔用「Stage 1 核心七問」「Stage 3 收斂」互相引用、下一版流程從四階段改六階段、十多處跨檔引用 silent 錯位（「Stage 3 收斂」字面完好、語意已指向新的核心七問階段）、grep 只能抓字面、語意要人工逐處判讀、實修中兩處漏網靠第二輪掃描補上；核心判準是「編號是結構排列的 derivation、不是該單位的 fact」、引用一律錨在語意標題、編號只作當下排序導覽；失效模式是 misdirected（成功解析到錯內容）比 dangling（404）更難偵測；邊界是發布方凍結編號（RFC 段號 / 法條）是 fact 可引用；是 #44 SSoT 在結構引用維度的實例、#93 identifier-as-fact 家族 sibling、#84 命名 cross-call-site 檢驗在標題的應用、#97 metadata surface 在引用句的延伸；新增路徑 24。下一步同步 compositional-writing skill（自包含版、不引卡號）。

**Last Updated**: 2026-06-05（git stash `-u` 筆記 review retro）— 新增 #154 教材的『重點 / 總結』段是內容發散的訊號、該重組正文不該補丁：git stash `-u` 筆記尾端「重點」段被使用者指為沒有必要 ——「如果文章一定要寫重點才能讓讀者記住、表示內容太發散、該重新拆分組織、而不是為設計不佳又補一個重點章節」；核心判準是「刪掉總結段、正文站不站得住」（站得住=冗餘、站不住=正文要重組、都指向不留總結）；處理段內容先分提醒（刪）vs 概念（併回正文對應段）；是 #64（source 同層修、不下游補）的寫作層同構、#150（字句 stance）的結構層 sibling、#151（不貢獻新概念就刪）同判準、#153（diagnose 先於修法）同類動作；邊界是跨章導覽型 summary（傳遞結構 / 路由新資訊）不適用。同步建記憶（總結段是發散訊號）。

**Last Updated**: 2026-06-01（multi-pass review 失效 WRAP 檢討 retro）— 新增 #153 Review 漏抓先分 design gap 與 execution gap：對 HOF 文章 review 失誤（多輪 review 報 clean、使用者卻 catch 出 register 類問題）做 WRAP Consider the Opposite 檢驗、發現失敗有兩成因 —— execution gap（只跑臨時子集、跳過框架既有的輪 9/10）+ design gap（輪 9 定義聚焦自包含性、缺 register lens、且 register 類無穩定關鍵詞 keyword bank 抓不到）；修法相反（design 改框架、execution 改紀律）、「加 keyword」是只解 design 偵測 sub-type 的假修法；是 #114 的上位（先驗證「問題在框架」這個預設）、#147 的一般化、#149 的成因分層 sibling；觸發 case 是 #150-152 register 卡。下一步據此更新 compositional-writing skill（輪 9 擴 register lens）。

**Last Updated**: 2026-06-01（HOF/typedef 文章必然性框架 retro）— 新增 #152 教材把設計選擇講成選擇、不講成必然或天性：同篇「更新的本質天生就是一個函式」被讀者指出「不會有天生這件事、update 是設計出來的」；WRAP 再分析揭露三層 —— 表層語義場錯置、中層把設計選擇講成必然抹掉能動性、深層牴觸文章自己的條件性論點（通篇講 HOF 條件性、唯獨此句講天生）；本卡是「機會成本語氣 vs 絕對主義」的必然式 subtype（比命令式「應該做 X」更隱形、偽裝成事實躲過 review）、#151 / #94 空降家族 sibling、補 compositional-writing 原則三未 report 化的必然性維度；修法還原條件性（補上游前提）；邊界物理 / 法律 / 數學事實可講必然；路徑 22 補入 #152。

**Last Updated**: 2026-06-01（HOF/typedef 文章自評誇飾 retro）— 新增 #151 教材給技術理由、不替方案下品質評價：同篇「HOF 是教科書級的適配」被讀者指為「像個人檢討、沒有教學會說這是教科書寫法」；自評誇飾（教科書級 / 堪稱經典 / 完美 / 漂亮地）傳遞作者滿意度而非概念、且品質 verdict 會頂替技術理由（寫「X 是教科書級的適配」就少寫「X 為什麼適配」）；本卡跟 #111 同屬誇飾大類但靠評價對象區分（#111 誇張技術屬性、本卡評價方案品質）、是 #150 的 stance sibling、#94 空降斷言在品質維度的變體、違反原則七；建卡正當性來自教學需求（誇飾寫法常見）非本 case 頻率（1 實例）、對應知識卡片規範段的建卡判準；路徑 22 補入 #151。同步建記憶（教材不自評誇飾）。

**Last Updated**: 2026-06-01（HOF/typedef 文章對讀者喊話 retro）— 新增 #150 教材用中性陳述、不對讀者喊話：同篇 review 連續抓到三種對讀者喊話（安撫「很多人卡在」/ 第二人稱「你天天寫」/ 祈使標題「先讀懂、別搞混」）；共用違反是「把讀者當要管理的對話對象、而非陳述概念」；問題不在精度（「你天天寫的 int count」精度正確、grep 乾淨）、在 register/stance；本卡是 #111（精度軸）的 register sibling、#149（review-process）的 content 對偶、補 AGENTS 原則六（禁貼標籤）沒覆蓋的 stance 維度（禁稱呼 / 指揮）；邊界 hook / narrative 段落輕度第二人稱可留；路徑 22 補入 #150。同步把對讀者喊話三形式併入既有記憶（教材中性陳述）。

**Last Updated**: 2026-06-01（HOF/typedef 文章字句層 review 漏判 retro）— 新增 #149 字句層 review：keyword bank 命中是候選、不是判決：review HOF/typedef 文章時跑了字句層 grep、命中「不是 A 而是 B」卻判成「可接受反例對照」放行、由讀者 catch；另「很多人卡在」訴諸群體贅語連關鍵詞都沒有、bank 結構上抓不到；本卡把失敗從 #114 的偵測層延伸到判定層 —— 偵測（grep 命中）跟判定（這命中是不是違規）是兩個認知步驟、reviewer 容易把命中合理化放行；判定準則用「概念位置」（建立概念的否定改正向、明示反例段落才保留）；是 #114 的判定層 sibling、夾在 #94（別過度刪對照）與正向陳述優先之間；新增路徑 22 給字句層 review 漏 catch 情境。同步把兩條字句層判準寫進記憶（正向陳述 grep 盲點 / 教學文不安撫讀者）。

**Last Updated**: 2026-05-20（3 篇 case-analyses 主體對齊標題承諾 retro）— 新增 #142 文章主體要對齊標題承諾、WRAP 內部分析不該喧賓奪主：#141 修了章節標題暴露 process metadata、但讀者再次 feedback 指出更深問題—即使標題改成教學風格、章節內容仍是 WRAP 內部分析（「供應商為什麼選擇 enterprise 包裝」段佔 30%+ 篇幅）、且為了支撐 prior 引用「a16z、Sequoia 公開報告」這類 hallucinated source；本卡把這個 pattern 從 surface 議題延伸到 scope 議題、加上 source citation 真實性紀律；是 #141 的姊妹卡—#141 處理章節標題、本卡處理章節內容；3 篇 case-analyses Round 4 重寫：移除「為什麼 X」獨立段、把核心動機塞進「事件本身」一兩句 + cross-link、文章主體留給標題承諾的內容。

**Last Updated**: 2026-05-20（3 篇 case-analyses WRAP process metadata 暴露 retro）— 新增 #141 WRAP 是寫作者的內部工具、不是文章章節結構：3 篇 case-analyses 第一版把 WRAP 七步驟（Anchor Check / Step 0 / Widen Options / Reality Test / Attain Distance / Prepare to be Wrong / Tripwire）全部當章節標題暴露、Round 2 後讀者再次 feedback 指出開頭預設讀者認知、分析報告 disclaim、論點重複預告三次；本卡把這個 pattern 從具體事故抽象成「process metadata 不該暴露給讀者」的原則、同步更新 case-analyses/_index.md 的 WRAP 結構模板段為「WRAP 是寫作者內部工具、章節服從教學流程」；是 #140（Widen Options 稻草人）的上位原則、處理 surface presentation 而非內容違規。

**Last Updated**: 2026-05-20（3 篇 case-analyses 套 WRAP 都踩稻草人 framing retro）— 新增 #140 WRAP Widen Options 容易塌成稻草人 framing、要改 evidence weight 結構：3 篇商業 case-analyses（Claude for Legal / FDE 軍備競賽 / Bufstream 收購）套 WRAP 框架時都踩同一個「兩弱一強」結構、3-reviewer audit 平行獨立都 catch 到、證明這是 systematic 陷阱而非個別失誤；修法是 Widen Options 從「對抗稻草人」改成「並陳合理因果鏈用 evidence 配重」、Reality Test 從 binary verdict 改成 weight assessment + Falsifier；判別線是「刪 Reality Test 後讀者能不能猜出正解」；e00253c 重寫後 register 翻轉（opinion 40% → teaching 55-60%）；是 #125 Collapse 在 WRAP 寫作 surface 的子實例、#79 多軸決策的姊妹卡。

**Last Updated**: 2026-05-20（content/business/ 建立後漏首頁入口 retro）— 新增 #139 新增頂層 content 資料夾要同步首頁 _index.md 入口：c2c01bf 建 content/business/ 50 檔但漏更新 content/_index.md 教學系列段、business 模組對首頁讀者隱形、f665e6d 才補；本卡把這個 pattern 從一次性事故抽象成原則、同步把「新建頂層資料夾要同步首頁入口」加進 AGENTS.md 完稿檢查清單；是 #44 SSoT + #97 metadata surface 在「上層索引」維度的子實例。

**Last Updated**: 2026-05-19（later 6、MySQL 17 篇 batch + 4-reviewer audit retro）— 新增 4 張 retrospective 卡：#135 Sibling Coverage Asymmetry Blindspot（priority 評估漏「對稱性」維度、案例 MySQL 18 篇後 PG 11 篇被 priority 列表排除）+ #136 Sibling Vendor Cross-Link 雙向性 Audit（A → B 9 條 vs B → A 0 條 asymmetry、batch 結束必跑）+ #137 Vendor Feature 時間敏感性 Claim Verification（PlanetScale FK 過時 claim invalidates 整段 Phase 1 audit、需 *Last verified* date 紀律）+ #138 Cross-Reviewer Convergence Priority Weighting（4-reviewer audit、A+B 收斂 flag「缺 weight」是 2 軸 convergence、信號比單軸高 severity 強）。從 MySQL 17 篇 5715 行 batch 跟 4-reviewer audit dogfood 抽出 priority / audit pattern 原則。

**Last Updated**: 2026-05-19（later 5、Backend 服務頁教材合約）— 新增 #133 服務頁教材合約：把「每個服務頁要接近成熟單篇教材」抽象成 report 原則，避免用特定目錄名稱當規格名；服務頁完成標準從 vendor 收錄 / 選型摘要升級為教學功能完整、服務對象清楚、學習路線漸進；明確反對統一章節模板，SQLite / MongoDB / PostgreSQL 這類同分類服務也要依服務對象設計各自章節。0.17 同步落成服務頁教材合約規格與 audit 分級。

2026-05-19（later 4、第三輪 migration batch + retrospective）— #128 補 Update 段紀錄第三輪 batch 跑完 4 條 tripwire 的結果：Type F dogfood × 2 確認 anatomy 通用性、Type F sub-type 浮現（F-cluster vs F-multi-region、後者需 parallel run）、identity/consistency/residency 3 軸候選各 1 case 驗證工作量分佈支持獨立軸（45% / 85% / 40%）、residency 是 cross-cutting constraint 不只是 driver；methodology 加「第三輪 batch 完成」段、5 篇 1,292 行 collapse 0/5。

2026-05-19（later 3、4-reviewer audit Phase 1+2+3a 全修）— #128 / #127 / methodology「5 → 6」cross-file 對齊（title / description / lead / H2 / 核心收尾 / 主導維度優先序全升 6、re-sharding 漏類 row strikethrough 標 resolved）+ #128 章節 1 補 anchor sentence + 章節 5 Type F anatomy 加註「規範形態 vs 實作可 inline」+ Sub-dim row 3 example 改純 replication 變動跟 row 4 區隔 + Cassandra row 補明示「雙變」+ #128 / #127 加 Self-aware limitation Update 段承認 4-reviewer audit 揭露的 6 個結構性質疑（6 維非窮盡 / Type F 跟 Type B 重疊 / parallel run 例外 / 主導維度 audience-dependent / 拒絕理由依賴 narrow 定義 / 既有 5 篇 silent grandfathering）。

2026-05-19（later 2）— 新增 #128 Data topology 是 process content 的第 6 audit 維度、從 Redis cluster re-sharding dogfood 抽出 + #127 self-aware limitation 段「audit 維度補新軸」預測命中後升級執行；#127 audit table 5 → 6 維、結構 type 5 → 6 種（新增 Type F）+ multi-axis 主導維度優先序加入 topology；methodology Step 1 audit 維度 5 → 6、加 Type F 結構模板、「何時不該套」段 re-sharding 條改寫（現在 Type F 涵蓋、不再排除）。

2026-05-19（later）— #122 / #124 / #127 補第二輪 migration batch（5 篇）驗證段：collapse 0/5（vs 第一輪 3/5、唯一變數是 stage 0 variant 規劃完整度）、漏類確認（major version upgrade / topology re-sharding 結構跟 5 type 完全不同）、multi-axis 規則成立（三維 High 用 Type E + 高維度獨立段）。同步更新 methodology backlog 標完成 2 項 + Update 段補新議題（data topology audit 維度 / 漏類「為什麼這篇不套」frame / multi-axis 高維度獨立段升 standard）。

2026-05-19 — 新增 #127 Process content 結構由最大差異維度決定（從 5 篇 migration playbook batch 抽出、5 種 type 結構分類）+ #122 / #124 補 partial collapse 實證段（migration batch 3/5 collapse、natural attractor「為什麼遷 X/Y/Z driver」浮現、證實 *variant 規劃必須主動* 非 N≥5 自動避免）。

2026-05-18 — 新增 #122-126 cadence 同質化系列 + meta-卡（5 張卡）：#122 cadence 是模板隱形維度 / #123 多重硬規範收斂 cadence / #124 emergence 違規要 stage 內抽樣（atomic 三軸：症狀 / 機制 / enforcement 時機）+ #125 Collapse 是隱形預設（跨 surface meta、串 #79 #80 #123）+ #126 寫作 review 是多軸完整性（review 設計 meta、串 #83 #95 #97 #114 #121 #122 #124）。從 backend/07 51 vendor 批量 review 反向抽出 + 跨既有卡 wedge 浮現。同批微調 #82（補 #124 三類分法 cross-link）+ #42（補第 7 個跨檔 emergence 面向）。待後續評估如何轉化進 `compositional-writing` 跟 `case-first-module-workflow` skill。

2026-05-13 — 新增 #115-121 case-driven 寫作方法論系列（7 張卡：#115 case 類型決定引用深度 / #116 fact vs derive 分層引用 / #117 跨 case 合成 frame 必須標明 / #118 standard-driven vs case-driven 領域判讀 / #119 章節已有 routing skeleton 走補強段 / #120 案例引用三段式段落結構 / #121 Agent team context 隔離設計），從 [case-first-module-workflow skill](/posts/case-first-agent-team-review-workflow/) 反向抽出原子化原則；新增路徑 20 給寫教學模組的引用紀律。#120 跟 #121 是評估後拓展卡（#120 案例引用「結構」axis 跟 #115-117 引用深度 / 分層 / 合成 axis 正交、#121 reviewer instance 軸跟 #83 frame 軸正交）。

**Last Updated**: 2026-05-04 — 新增 #107-#109 術語翻譯 review 系列（原文錨點 / 完整名詞頭 / 概念角色），從 `paternalism`、`多步驟 perplexity 盲`、`Steelman` 三個 case 抽出翻譯檢查流程；新增路徑 19 給文章轉譯與術語 review。

**Last Updated**: 2026-05-01 — 新增 #99-#105 資安內容 audit 系列（七張卡：#99 anchor 風險不對稱 / #100 false sense of security 主要失敗模式 / #101-104 四個 audit dimension（threat model 對稱 / mitigation 對位 / context-dependence / citation 時效精確）/ #105 recommendation tier 化）；資安寫作的 audit bar 從 readability-first 升級到 verifiability-first；新增路徑 18 串聯 audit workflow。後續對應 skill reference（auditing-articles.md）跟 multi-pass review 的 epistemic rigor 第 6 輪會根據本系列展開。

**Last Updated**: 2026-04-30 — 新增 #97 Metadata surface 要納入寫作 review 範圍（從資安章節標題 review 漏判抽出 — 正文已建立正向概念、title 與 MOC hook 仍保留舊 frame，揭露 multi-pass review 缺 surface 軸）、新增路徑 17 給 title / frontmatter / index hook 的寫作 coverage 檢查。

**Last Updated**: 2026-04-28 — 第六輪新增 #92 視覺手段對齊錯誤層次（從 blog 文章寫作 retrospective 抽出 — emoji 圖例斷行的 trigger 揭露「multi-pass review 缺 vertical 軸」、跟 #82 並列為 sibling、補 #83 缺的 layer 維度）、新增路徑 15 給寫作 / UI 中誤判層次的情境。

**Last Updated**: 2026-04-28 — 新增 #93 URL slug 必須顯式定義為 fact（從 #92 的 mermaid cross-link broken 事故揭露 — 175 篇內容文章 0 篇有顯式 slug、檔名 / hugo title 推導 / frontmatter 三處散落、典型 #44 SSoT 違反在 toolchain integration 維度）、新增路徑 16 給跨工具 identifier 議題。

**Last Updated**: 2026-04-26 — 五輪實作 43 篇 + 第六輪抽象層 9 篇（#42-45, #67-71）+ 第七輪 Pattern 卡片 12 篇（#46-51, #54, #60-62, #65-66）+ 第八輪 Filter × Source 議題 7 篇（#55-59, #63-64）。八輪迭代完成 — 最新一輪：retrospective Checkpoint 1（修 search bug 後跳過的「列使用者意圖完整集合」）發現 3 個 silent 缺口（URL state / tab order / filter UI hint）、抽兩張新抽象層卡（#70 URL 儲存層 + #71 Tab Order 三對齊）、#68 加 Checkpoint 1 跳過的 self-case。
