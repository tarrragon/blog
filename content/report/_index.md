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
- [#208 修同質化的手法本身會同質化：均勻套用的生成端修法複製出新模具](uniform-remediation-recreates-homogenization/) — 為破 cadence 模具立的生成端規則（「段首一律目標詞先行」）均勻套整批會收斂成新模具、常比原模具更密（實測「目標詞先行」變「目標詞 + 的X在/是『引號』」12/16 張）；成因是換模不等於破模（單一替代句型仍是模板）+「多樣化規則」偽裝成多樣化 + 同源自審被「已修」背書遮蔽；修法要輪替多個 framing 不換統一模板、生成規則本身當 cadence 候選進整組跨卡異源 review；是 #123 便利解收斂的 deliberate 版（刻意修法反噬 vs 無意識收斂）、#167 修法新建模具而非同違規殘留、#122 cadence 隱形維度的動態版、#147 規範產物本身要進 audit、#165 同源盲區在修法後的加深
- [#168 多輪審查要有冷讀者 frame](cold-reader-frame-vs-informed-reviewer/) — 模擬讀者要分知情（讀完全部走旅程）與冷讀（經搜尋 / 直連落在單篇、零脈絡）；知情 reviewer 自動腦補脈絡、結構性看不見「洩漏撰寫者預設前提的行話」（未定義的「家族」「上述」「如前所述」）、只有冷讀者立刻卡住；原子 / Zettelkasten / glossary / 可直連單篇落地的內容必跑冷讀 frame、不可只靠旅程 frame；實證 til/terms 14 卡旅程審查全 A 卻漏「連到家族」行話；是 #165 文體異源在「讀者脈絡」維度的對偶（同源腦補 vs 異源冷讀）、#131 讀者旅程的單卡冷讀補面、#159 詞彙牆在單卡落地的形態、已回饋 multi-round-review 補 B′ 冷讀 frame
- [#169 原子筆記要有向上的議題入口](atomic-note-needs-situational-entry/) — 承載知識的原子卡不是字典條目：字典答「這個詞是什麼」、承載知識答「你在討論什麼議題、撞到什麼問題、才需要這知識」、從情境進入非從定義；撰寫者有預設前提讀者沒有、做法是建議題 hub（以讀者會遇到的問題為題）討論再分流到術語卡、術語卡頂回指它出自哪個議題；沒這層卡淪字典、搜尋落地者讀完仍不知對他何用；是 #131 教材讀者旅程在單張原子筆記的特化（課程旅程 vs 單卡進入動機）、#159 入口分流的內容動機面、卡片盒「為何讀這張卡」原則的落地
- [讀者不需要知道的資訊不該出現在最終文件](reader-does-not-need-to-know/) — meta 資訊（寫作動機、邊界聲明、脈絡解釋）服務作者不服務讀者；AI 生成傾向把推理中間產物外露到最終文件；判準是「拿掉後讀者體驗變不變差」；跟列舉殘留卡是同根原則的兩種表現（meta 動機 + 範圍枚舉）
- [列舉與數字殘留在定義型文件會製造維護債務](enumeration-creates-maintenance-debt/) — 定義型文件的冗餘列舉（A-G）和描述性數字（9 個函式）是撰寫推理殘留、維護成本高但閱讀價值低；判準「拿掉後理解不受影響 → 刪除」；區分冗餘列舉 vs 定義列舉、描述性數字 vs 規範性數字；是 #96 的鏡像（scope 文件要 enumerate、定義型文件的冗餘列舉要刪）、#156 在正文定義層的對應、#67 便利驅動殘留的具體形態

工具 opinion 文章三輪審查系列（從一篇 work-log 的三輪多視角審查抽出、一張總結卡帶四張 finding 卡）：

- [三輪審查的檢討收穫 — 工具 opinion 文章的寫作品質演進](tool-opinion-article-review-lessons/) — 本組的總結卡：一篇 work-log 經三輪、八個 frame、33 個 finding 從 B+ 走到 A+；價值在 frame 切換而非重複加深（每輪抓到的問題類型跟上一輪不重疊）、停止訊號是「想不出新 frame」而非「finding 數遞減」；同批四張 finding 卡各記一種 AI 輔助寫作反覆出現的 pattern（語氣 / 範圍 / 主題 / 歸因）；是 #148 停止訊號的前身實證、#168 冷讀者 frame 的來源批次
- [文章語氣校正：恐嚇式 hook 與技術分享的邊界](article-tone-scare-vs-share/) — 開頭語氣決定讀者跟作者的關係：恐嚇式（「問題可能正在你的工具中靜默發生」）把讀者放在被警告的對象位置、分享式（「從一個版本錯置的經驗出發」）放在同行位置；兩者傳遞相同資訊、讀者的接收姿態不同；判準是問「這句話預設讀者現在處於危險嗎」；跟 [信號不是承認](signal-not-admission/) 同屬語氣軸（讀者位置 vs 責任歸屬）
- [文章範圍漂移：從 CLI 工具到工具設計的泛化過程](article-scope-creep-cli-to-tool-design/) — 文章範圍在審查中被逐步泛化（CLI 工具 → 所有工具設計）時，五個位置要同步調整、遺漏任一個就會讓文章「說的」跟「做的」不一致：title、開頭 hook、原則段措辭、對照表範例、結尾 checklist；是 #97 metadata surface 要納入 review 範圍在「範圍變更」維度的展開、#95 scope 軸的內容面
- [主題偏移：內部系統知識洩漏到面向讀者的論述](topic-drift-internal-knowledge-leak/) — 一句話在技術上正確、但偏離文章主題時，刪除優於保留：補充內部系統細節滿足的是作者的完整性需求、不是讀者的理解需求；判斷流程是「這句服務的是誰的需求」；是 [讀者不需要知道](reader-does-not-need-to-know/) 在「主題邊界」而非「meta 動機」維度的 sibling、#212 找出路不刪除的邊界情況（真正離題且無處可去的才刪）
- [信號不是承認 — 技術寫作中的歸因語氣](signal-not-admission/) — 描述系統行為用中性詞（信號 / 提醒 / 觀測）、避免歸因詞（承認 / 暴露 / 證明了失敗）；工程上的信號指向可改善之處、不是對過去決策的道德判定；語氣偏差讓讀者從「可以改善」的正向心態轉為「做錯了要承認」的防禦心態；是 #150 stance 軸在「對系統」而非「對讀者」方向的對偶

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
- [#209 教鑑別能力、不教操作流程](teach-judgment-not-procedure/) — 文章的知識目標決定結構：判斷力導向把機制理解當主線、操作當自然推導的結果；流程導向把步驟當主線。多數教學文章應走判斷力導向——讀者只需要步驟時查官方文件更快、文章的價值在於提供判斷力；從 Preboot 卷文章重寫抽出（checklist → 機制理解結構）
- [#210 壓縮結論剝奪推導路徑](compressed-conclusion-strips-derivation/) — 結論是知識的壓縮形態、壓縮時丟掉推導路徑；威脅式（「一定不能」）、命令式（「記住」）、教訓式（「你就是因為」）是三種壓縮形式；命名 #150（喊話）/ #151（品質評價）/ #152（必然框架）三張卡共享但未被命名的根因——作者已走完推導但只輸出最後一步
- [#211 複合問題先拆機制再談交互](compound-problem-decompose-then-interact/) — 問題由多個概念交互導致時、先各自教 A/B/C 的機制再談 A×B×C 交互；讀者理解各元件後交互作用是自然推導的；磁碟空間系列（APFS 空間池 + Cryptex + Simulator + App Container）四篇各教一個機制、用同一台機器當貫穿案例
- [#212 不屬於這篇的內容要找出路、不是刪除](misplaced-content-needs-route-not-deletion/) — Review 發現 SRP 違反時、正確動作是幫內容找到該去的地方（另一篇、新文章、新分類）、刪除是最差選項；SRP 違反是路由訊號、多輪審查標記「不屬於」時要同時標「建議目的地」；從 Container 文章的 Steam 段路由過程抽出
- [#213 分類從內容深度浮現、不從規劃建立](category-emerges-from-content-depth/) — 文章拆到獨立機制的深度後主題群聚自然可見、先建空分類再填文章會產生稀疏分類和錯誤歸屬；浮現訊號是兜底資料夾裡 3+ 篇同主題文章且有互相引用；從 9 篇 macOS 文章從 other/ 畢業為 content/macos/ 的過程抽出
- [#214 解法排序依情境適用、不依作者採用順序](author-adoption-order-is-not-value-hierarchy/) — 多解法教學把作者「原本用 A、後來換 B」的採用時序寫成價值序列、先前解法被貶為最後手段、抹掉它成立的情境；排序該依訊號斷點與可改動範圍、反向測「換情境這個被排到最後的解法會不會是首選」；從 Flutter 重繪心跳文章把「正規解優先、心跳擺最後」改成情境並列抽出
- [#215 會誤解處補正向知識、不把誤會當敘事中心](fill-knowledge-gap-not-center-misconception/) — 「最容易誤解 / 常見的誤判 / 要抵抗直覺」這類把假想誤會當敘事中心的框架不是澄清、是知識缺口訊號：若某處會讓人誤解、補救是補上讓誤解無從發生的正向模型與機制、不是提醒讀者一個他本不需要有的困惑；界線是具體實測敘事與真實診斷區分（逾時 vs 被拒、症狀 vs 根因）保留、只有把假想誤會當主題句起手的才改；是 #150 stance 軸之外的知識供給軸 sibling、#166 重點位置在「誤會 vs 正確模型」的具體化、#210 壓縮結論的一種、[讀者不需要知道](reader-does-not-need-to-know/) 的「換正向知識非純刪」對照；從遠端 agent 工作機教材三輪 review catch 6 處同構框架抽出
- [#216 經驗談來源要重建分析層、不是換敘述口吻](anecdotal-source-needs-mechanism-reconstruction/) — 經驗談（訪談 / 社群貼文 / 口述）的斷言是從業者壓縮過的結論、素材沒有自帶分析層；教學轉換的核心工作是用成本結構、誘因、市場結構把斷言還原成可推導的機制，只做主題分類與書面化會產出披著教學結構的經驗談；跟 #143 按 source 類型分工（分析文拆層 / 經驗談重建）、是 #210 在「引用他人壓縮結論」的變體、#209 的素材端前置條件；從採購 planning 模組被判定「講故事不是商業分析」抽出
- [#217 審查要有斷言支撐 frame：抓知識類型與分類定位的失配](review-needs-claim-support-frame/) — 字句、cadence、讀者旅程、steelman 都在文字表面與結構層操作、對「整個模組是錯的知識類型」結構性不可見；斷言支撐 frame 抽樣核心斷言問「靠什麼成立——機制 / 量化 / 來源、還是口吻與權威」、並對照模組跟分類 house style 的知識類型；是 #126 多軸完整性的實證（七軸都跑仍 miss）、#153 design gap 的典型案例、outside-in 系列的支撐盲區 sibling；從採購模組三輪全過仍被判定粗糙的漏抓事故抽出
- [#218 文章按分析弧拆分、不按來源主題攤平](article-split-by-analysis-arc-not-source-spread/) — 文章邊界由「一個分析責任走完分析弧」（情境 / 機制 / 量化取捨 / 判準 / 失效條件）決定、素材不夠走完弧就併入或 backlog；按 source 主題聚類切篇會產出全模組均勻的多主題淺層節奏、素材句跨篇重複、genre 混裝；跟 #211 互補（跨篇拆機制 / 篇內驗深度）、是 #122 cadence 同質化的模組級形態、#212 的路由判斷前移到拆分階段；從採購模組 6 篇均勻 43-50 行的節奏檢討抽出
- [#219 教學模組要有推導源頭、不是主題集合](teaching-module-needs-derivation-anchor/) — 分析教學模組的結構要是推導體系：一個源頭機制、每篇承擔一條展開，模組索引能一句話說出推導起點；源頭買到四件事——判準折算到同一把尺、跨篇矛盾才會現形、新篇有掛載點、推導式閱讀路線成立；主題集合式模組深度補不上因為沒有「往哪裡深」的方向；是 #218（篇內弧）之上的模組級結構原則、#211 補「拆而有源」、#209 在模組層的展開；從採購模組 before / after 對比抽出
- [#220 判準要寫到條件層：維度清單是判準的空殼](criteria-need-condition-action-mapping/) — 判準有口訣 / 維度清單 / 條件映射三個成熟度、教學要到第三層（條件 → 行動的映射＋失效情境）、驗收用重算測試（讀者帶自己的參數能不能走出行動）；維度清單最有欺騙性——長得像判準、通過字句與機制審查、在讀者的決策點斷線；條件不可窮舉時用自查問句組＋排序規則；是 #218 判準步的驗收標準、#210 在判準段的具體形式、跟 #216 獨立（機制重建完成仍可能停在第二層——同一 batch 兩個版本各踩一次）；從採購模組重寫「同一個坑掉兩次」抽出
- [#221 檢查規則的作用域要顯式列舉：零 error 可能是沒被檢查](lint-scope-must-be-explicit-fact/) — 規則承載兩個獨立的 fact（規則說什麼 / 規則管哪些檔案），後者被編碼成路徑常數後從不被審視；未納管目錄的零 error 與合規目錄的零 error 訊號相同，違規以內容產出的速度靜默累積、症狀在下游（排序 / 索引 / 渲染）才浮現；作用域常數被多個檢查共用時，擴作用域會連帶擴語意、耦合反過來保護違規；驗收順序是先讓新規則對已知違規報錯再修違規，零 error 只在它從非零變過來時帶有資訊；是 #93 fact vs derivation 的同構（作用域錯了不改變任何可觀察行為、失效更晚被發現）、#139 在工具鏈維度的對偶（人類導覽層 vs 檢查層的註冊點）、#96 的工具端 sibling（心算失誤 vs 常數沉默）、#44 的反向失效（異義值擠在一處導致不可分別演化）；從 report 列表排序異常追到 mdtools 卡片檢查從未涵蓋 content/report/ 抽出；**第二種形態是偵測視窗**——偵測規則還編碼了「證據會出現在哪裡」（掃描視窗多大、往哪個方向看、算不算所屬章節標題），這個參數同樣寫下即被當成定義；實例是掃「表格未標年度」把視窗設成往回三行，三十個命中裡十七個假陽性（期間大量寫在表格下方的資料來源行、或所屬章節的標題裡）。兩形態的錯誤方向相反——作用域缺漏產生假陰性（症狀是怎麼都沒事）、視窗錯誤產生假陽性（症狀是怎麼這麼多事），後者看起來像工具很認真在工作因此更不引發懷疑；代價是未驗證的偵測器產出的數量會被當成量測寫進規劃文件（該案把「約五十處」寫進待辦、實際可修八處）。懷疑的分配不對稱且方向可預測：同一條管線上不信任的元件會被抽驗、自己寫的那段不會——假設沒被審視正因為它是自己下的。操作是偵測器的輸出被當成數量使用前先手動核對一個樣本、重點放在編碼「證據在哪裡」的那個參數上
- [#222 約束要讓違反路徑走不通：只寫在文件層的設計意圖是沒關的逃生口](design-intent-needs-enforcement-layer/) — 設計意圖有三個落點（文件層註解 / 慣例、型別層、執行層），只落在文件層的意圖對繞過路徑沒有阻力、逃生口使用者只是走阻力最小的路；「註解宣稱約束但實作沒查」比沒有約束更糟——宣稱本身消滅發現缺口的機會、reviewer 看到「約束」字樣就放行；判準是「這個型別有沒有不允許任意組合的欄位」、有就不該讓那些欄位 public 可寫（entity 的全欄位 copyWith）、沒有就是正當便利工具（DTO / value object）；是 #221 的程式設計層同構（宣稱與強制是兩個獨立 fact、失效靜默）、#100 false sense of security 在程式註解的形態、#124 「約束類型決定強制手段」在型別 / 執行層的對應、#110 當下三軸的應用實例、#67 便利贏過意圖的結構性對策；從 Dart entity 的 public copyWith 繞過領域方法、稽核軌跡靜默有洞抽出
- [#223 逃生口吸收建構路徑的缺陷：修工廠的表達力、不是修拼裝點](escape-hatch-absorbs-construction-gap/) — 存在「總有辦法把物件拼出來」的萬能出口（全欄位 copyWith / setter 氾濫）時、上游建構路徑的表達力缺陷永遠不被迫修好：需求進不了工廠就從逃生口出去、拼裝現場的最短路徑埋語意錯誤（建臨時物件撈預設值）、在別處復發；逃生口不只讓錯誤寫法變可能、它讓正確的修法變不必要；修法對準上游（工廠收該收的參數）、拼裝點的繞道流量本身是免費的需求調查；是 #222 的 sibling（意圖強制 vs 缺陷轉移、關逃生口是本卡機制的斷路器）、#42 兩次門檻的觸發應用（同族語意錯誤第二次出現就找共同缺口）、#64 在物件建構維度的同構（上游修一次 vs 下游補丁複製）、#86 該跳 L3 的訊號、#67 便利與正確重合的修法；從同型拼裝錯誤兩檔各復發一次抽出
- [#224 教學層引用 case 要剝離身分與規模鋪陳](teaching-cite-strips-identity-and-scale/) — 教學章引用 case 只帶論證需要的對比結構與機制；事件帳目（票數 / 案例數 / 版本號）、規模鋪陳、產品身分與領域功能詞住址在 work-log；修法階梯「先刪、刪不動才泛化」（逐句問「拿掉後論證還成立嗎」）、泛化有下限（論證要留具象載體）；通用化帳目（113 張 → 上百張）是半吊子修法、前情提要仍在；「規模感幫論證」是作者與同源 reviewer 共享的直覺、反差實際來自對比結構本身；跟 #115 同 surface 不同軸（#115 管斷言深度不編造、本卡管敘事重量不搬運）、#116 的 surface 間版（敘事歸屬地）、#44 的敘事住址版、#170 的同構（隨事件變動的細節不進穩定層）；從 ddd 組裝層可達性章多輪審查的兩次使用者指正抽出
- [#225 內容去留由教學目標把關、素材量只調整寫法](teaching-goal-gates-content-not-material-volume/) — 決定哲學層 / 思維模式 / 跨域對照該不該獨立成篇時、門檻只有教學目標（讀者需不需要這層）、素材量不參與否決；「只有一個案例撐不起」是出現頻率邏輯的變形、教學需求判準不只適用術語卡；素材量進場的位置是寫法——單案例模式卡照建、邊界段標示支撐範圍與候選掛載點；決策順序錯位讓教學目標層的問題被素材量層的答案回掉、「讀者需不需要這層」從未被正面評估、且否決聽起來務實（先聚焦）而不被察覺；#130 的 sibling（上位目的被下位語言接管）、#151 是單實例憑教學需求立卡的既有實踐、跟「常識相對於讀者背景」同屬建卡判準族；從緊緻性筆記哲學段收斂的使用者指正抽出
- [#226 延伸層內容以讀者問題立篇](extension-content-split-by-reader-question/) — 哲學面 / 跨域對照 / 思維模式的切分單位是「哪種讀者帶著什麼問題來」、一問一篇、標題寫問題本身；學科歸屬與原文段落結構都不是切分單位；讀者問題一次給原子邊界 / 入口 / 內容判準三樣；自我消解的延伸段（聲明「不打算把 X 套到 Y」後就結束）是缺讀者入口的訊號、不是該刪的證據——給它讀者問題就重獲知識點；延伸層不等於感想層、判讀訊號 / 邊界 / 下一步照樣要有；是 #169 在「篇」級的特化（入口內建在篇名）、#225 的形式層下一步、#218 拆分判準族（拆分單位是讀者的完整交付不是素材分類）、跟 #211 各管一段（前置概念按機制拆、延伸層按讀者問題拆）；從緊緻性工程段刪除後以讀者問題復活抽出
- [#227 可重現性只有乾淨機器重跑才驗得出](clean-room-reproduce-reveals-non-repo-state/) — 環境實際依賴的狀態散落在 repo 之外的許多地方（安裝器寫進 shell profile 的行 / 系統 PATH drop-in / 手裝殘留 / 來源寄居別專案的工具）；「從 repo 可重現」是未驗證宣稱——讀 repo 只顯示宣告了什麼、乾淨機器實跑才顯示實際依賴什麼、差額就是忘了宣告的狀態；「在我機器上能跑」是量測問題、不是人的問題（原機是被污染的儀器、偵測不到自己的污染）；乾淨 = 無累積狀態（全新 VM / 帳號 / container、且用過一次就被污染要重置）、每個分歧是 finding（搬進 repo 或標成刻意手動）；是 #44 SSoT 在重現維度的症狀（機器本地檔是值的第二住址）、#93 fact vs derivation 的環境狀態版、#11 靜態推理盲點只有實跑現形的同型、operational-how 環境差異族的 sibling；從 dotfiles bootstrap 全新 macOS VM 冷測抓 8 個 fresh-machine bug 抽出
- [#228 等比縮放不管空間分配](proportional-scaling-is-not-space-allocation/) — 用了 sizing 套件版面仍擠壓時、先分「換算錯 vs 分配錯」：換算工具工作在常數層（design px → device px）、空間分配發生在 layout 協商層（有限寬度分給動態內容）、兩層獨立；等比縮放的隱含假設「實際內容 = 設計稿內容」被動態計數 / i18n / 使用者資料打破、比例正確不等於空間夠用；「有用 X 套件為什麼還會壞」是把套件當整層保證的 false confidence — #82 / #92 工具 ceiling 家族的第三個 sibling（驗證 / 呈現 / 換算工具各有擋不到的層）、#221 的跨層版（工具靜默兩成因）；修法三層各補各的（設計層空間競爭規格 / 實作層 flex 顯式決策 / 驗證層窄幕檢查）、引入套件時記錄「它不保證什麼」；從書庫 app 驗收 U.C16 / U.C19 抽出

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

`#99 資安教學審查標準對應風險不對稱` → `#100 false sense of security 主要失敗模式` → `#101 threat model 明確性` → `#102 mitigation 對位` → `#103 mitigation context-dependence` → `#104 security citation 時效精確` → `#105 audit recommendation 層級` — 先確立風險不對稱論證、再用 false sense of security 作為主要 audit 目標、跑四個 dimension（threat model 對稱 / mitigation mechanism 對位 / context 條件顯式 / citation 版本精確）、最後用 tier 化 recommendation 把每個 weakness 映射到 ship 決策（accept / minor / major / withdraw）。適用 backend/07-security-data-protection/ 章節 audit、跨高 stakes 領域（concurrency / distributed / financial / medical）也適用 dimension 1-3。強度詞與誇飾的 audit 判準（兩軸四區、支撐存在測試、反比操縱訊號、降格對齊）另見 `#260 誇飾的合法性由段落位置的功能決定`。

### 路徑 19：翻譯 / 轉譯文章時檢查術語是否錯位

`#107 術語翻譯要保留原文錨點` → `#108 中文壓縮術語要保留完整名詞頭` → `#109 術語翻譯要保留概念角色` → `#259 轉述與翻譯要保留語意強度量級` → `#84 Naming 是 iterated artifact` → `#97 Metadata surface 要納入寫作 review 範圍` — 先保留原文讓概念可回溯，再確認中文離開原句仍有完整名詞頭；接著檢查名詞頭是否保留來源中的概念角色、強度詞是否停在原文的量級（鄰詞存在測試）；最後同步掃 heading / checklist / index entry。翻譯落在 `#260 誇飾的合法性由段落位置的功能決定` 的零容忍區——判斷一次升格是超譯還是正當文案設計時走該卡的兩軸。

### 路徑 20：寫教學模組 / 案例驅動內容時的引用紀律

先讀 [case-first + agent team review 方法論](/posts/case-first-agent-team-review-workflow/) 作 anchor、再依序 `#118 standard-driven vs case-driven 領域判讀` → `#119 章節已有 routing skeleton 走補強段` → `#115 案例引用深度跟著 case 類型走` → `#116 引用案例要分觀察層 / 判讀層` → `#117 跨多個 case 合成的 frame 必須標明` → `#120 案例引用三段式段落結構` — 先判讀領域該走 case-driven 還是 standard-driven、再判斷章節結構決定擴章策略；走 case-driven 時依 case 類型決定承接深度、引用 rich case 時分層標明 fact vs derive、跨多個 case 合成 frame 時 explicit 標為「本章合成」、最後用三段式（概念定義 → case 引用 → 通用展開）寫每個 case 引用段落。#116 / #117 順序可互換（先看單 case 內部 vs 先看跨 case 合成、看讀者習慣）。路徑尾補 standard citation surface 見 [#104](security-citation-currency-and-precision/)、補 agent team 工具設計見 [#121](agent-team-context-isolation/)；教學章引用 case 該帶多少敘事（帳目 / 身分 / 規模鋪陳）見 [#224](teaching-cite-strips-identity-and-scale/)——先刪、刪不動才泛化。#224 禁的是搬運帳目與身分、不是禁具體敘事，章節內該用什麼填見 [#242](micro-case-makes-consequences-imaginable/) 的無身分微案例。

### 路徑 21：寫 Backend 服務頁 / vendor 頁前的教材合約檢查

`#130 教材目標先於決策框架` → `#131 教材完整性要用讀者旅程驗證` → `#132 貫穿式案例是服務教材的教學骨架` → `#133 服務頁教材合約` — 先確認服務頁服務的是教材目標，再確認它能放進讀者旅程與 checkout episode；最後用服務頁教材合約檢查教學功能是否完整，章節路線則依服務對象與責任形狀設計。

### 路徑 22：跑字句層 review（正向陳述 / 口語修辭）卻仍漏 catch

`#114 Multi-pass review 的 frame 顆粒度盲點` → `#149 keyword bank 命中是候選、不是判決` → `#94 正向改寫要保留對照論據` → `#111 口語化修辭會稀釋技術精度` → `#147 規範化跟自審是兩種認知任務` → `#148 跨輪 review 停止訊號` — 先用 #114 把規則展開成 keyword bank 解偵測層（別靠記憶 sweep）；再用 #149 處理判定層（grep 命中後別把「建立概念的否定」合理化成「反例對照」放行、用「概念位置」判別）；判定的兩極由 #94（別過度刪對照）跟正向陳述優先（別過度留否定）夾出；#111 給字句層的具體訊號清單；#203 補「泛用詞濫用」（同一個泛用詞蓋過不同具體情境、坑 / 東西 / 搞、依情境換精確詞；「坑」的地區偏移面歸 #112）；#150 補「register/stance」軸（教材不對讀者喊話、跟 #111 精度軸正交）；#151 補「自評誇飾」（品質 verdict 頂替技術理由、跟 #111 同誇飾大類但評價對象不同）；#152 補「必然性框架」（把設計選擇講成天性、機會成本語氣的必然式 subtype）；#214 補「解法排序框架」（多解法教學把作者「原本用 A、後來換 B」的採用時序寫成價值序列、把先前解法貶為最後手段、跟 #152 同屬抹掉條件性 / 情境性的大類、但軸是時序而非必然）；#147 提醒「立了規範 / 跑了 grep」不等於判得對；#153 提醒漏抓先分 design gap（改框架）vs execution gap（改執行、別只加 keyword）；#165 揭露同源盲區現象（LLM 作者與 reviewer 共享文體、register 違規同源自審有上限）；#166 再校正一層 —— 把「不是 X、而是 Y」從「品味不可機械化」拉回「資訊結構：重點優先」這個跨語言可操作判準、主解是強制執行重點位置判準（核心概念在不在最前）、異源降為補充（換語言打不破、證偽過）；#167 提醒修法本身引入同類變體（補 POS pattern 連接詞清單擴兩次仍漏第四個）、review scope 要含修法後的產物、停止判斷不能停在「修完這批」；最後用 #148 判斷何時停止。字句層之下還有一層顆粒度：`#261 語句要在它的消費單位內資訊自足` —— keyword bank 與篇章層冷讀都抓不到「句內成分殘缺」（殘片指涉、缺主詞的表格格）、對單句消費位（checklist 項 / 表格格 / 判準句）逐句跑抽離重讀。

### 路徑 23：寫完文章、檢查尾端「重點 / 總結」段該不該留

`#154 總結段是內容發散的訊號` → `#64 在 source 同層修、不下游補` → `#150 教材不對讀者喊話` → `#199 SOP 跟 retrospective 混寫` → `#42 兩次門檻` — 寫完文章看到尾端有「重點 / 小結 / 結論 / TL;DR」段、先用 #154 的判準「刪掉它、正文站不站得住」診斷：站得住=冗餘（刪）、站不住=正文發散（重組、不靠總結救）。處理段內容分提醒（刪）vs 概念（按 #64 併回正文 source 位置、不在尾端打補丁）；提醒型常同時是 #150 的對讀者喊話。方法論文章同時塞 SOP 和驗證紀錄時用 #199 的減法測試判斷（去掉 SOP 看 retrospective 站不站得住）。真實樣本以「重述+路由混合型」最多、修法是外科式（切重述、留路由）；系統性出現（整個模組每章一個小結）時在模組層級統一決定、別逐章補丁 —— 此泛化暫按 #42 兩次門檻留 backlog、第二個系統性 smell 出現時抽獨立卡。

### 路徑 24：在活文件中命名與引用章節 / 階段 / 條列項

`#156 集合命名用角色、不內嵌數量` → `#157 語意錨用單一字串` → `#155 引用章節用語意標題、不用位置編號` → `#44 Single Source of Truth` → `#84 Naming 是 iterated artifact` — 先用 #156 淨化命名端：集合名稱抽掉成員數（「核心問題」不是「核心七問」）、否則標題一半是 derivation、引用端怎麼修都錨在會漂移的字串上；再用 #157 確認語意名是單一 canonical 字串（同義雙名讓 grep 掃 A 漏 B、重排修復退回人腦對應）；再用 #155 修引用端：「見 Stage N」「如第 N 點」換成語意標題（編號是排列的 derivation、重排時 silent 指向錯內容）；標題本身要通過 #84 的 cross-call-site 檢驗（單獨出現時讀者知道指什麼）；發布方凍結的編號與數量（RFC 段號 / 法條 / SOLID 五原則）是 fact、可用。結構重排或成員增減的 commit 要全 repo 掃、可用 `rg "Stage [0-9]|第 ?[一二三四五六七八九十0-9]+ ?(章|節|點|步|輪)|§[0-9]"`（引用端）跟 `rg "[一二三四五六七八九十0-9]+ ?(大|問|階段|支柱|原則|步驟|件事|個維度)"`（命名端）抓候選後逐處判讀。三卡各守一層（引用錨點 / 命名內容 / 命名唯一性）、檢查互不替代 — 只跑其中一層、另外兩層的違規仍然隱形。引用他卡的關係宣告另有一層：用被引卡自己的分類詞彙、逐條找支撐句、見 [#162](cite-cards-with-their-own-taxonomy/)。路由段落（下一步 / 依情境 / MOC）的引用再多一層容器要求：每條 bullet 自包含、目標文章連結顯式寫在句內、鄰條指代（同篇 / 上一條）在跳讀模式下必失效、見 [#204](routing-entry-self-contained/)。條目本身寫好之後還有另一端要驗：目的地實際承接這個主題、且到站的第一屏看得到，見 `#240 路由要驗證目的地承接該主題`。

### 路徑 25：設計判讀框架 / 多階段流程協議

`#158 決策表矛盾列 = 缺上游維度` → `#163 多階段 artifact 欄位契約` → `#153 design gap vs execution gap` → `#69 Test-First` — 設計判讀表或多階段流程後、用帶完整語境的真實案例 dry-run（#69 的 RED 精神：乾淨例子只會命中預想列）；兩列同時命中且結論相反 → 補前置澄清問（#158）；下游宣稱以上游為輸入 → 逐欄走查標「直給 / 明文推導 / 缺」（#163）；缺口歸因時先分 design gap（改框架）vs execution gap（改執行、#153）。

### 路徑 26：批量寫 sibling 文檔（多卡 / 多章）之前與之後

`#122 cadence 同質化` → `#123 多重硬規範收斂便利解` → `#160 跨 surface 重新語境化` → `#161 摘要模態` → `#147 規範化跟自審` → `#148 停止訊號` — 寫之前排開場 frame / 條目形態 / 敘事視角的輪替表（#122 的生成端防範）；同主題落兩個 surface 時憑概念重寫、不開雙視窗對照抄（#160）；每份的 description 跟本體比對模態（#161）；寫完的批次連讀比句式骨架、單份 review 抓不到同骨（#122）；自己立的規範要靠 reviewer 抓自己（#147）；同類 finding 第二次出現、把規則從 review 端升到生成端。

### 路徑 27：寫文章時的知識目標與展開結構

寫教學文章前決定知識目標（判斷力 vs 流程）、面對複合問題時拆分結構、遇到 SRP 違反時路由內容、文章拆夠深後分類自然浮現：

- 先讀 [#209](teach-judgment-not-procedure/)（知識目標決定結構）
- 複合問題：[#211](compound-problem-decompose-then-interact/)（先拆機制再談交互）
- 傳遞方式：[#210](compressed-conclusion-strips-derivation/)（結論不壓縮，展開推導）
- SRP 違反：[#212](misplaced-content-needs-route-not-deletion/)（找出路不刪除）
- 組織結構：[#213](category-emerges-from-content-depth/)（分類從深度浮現）

### 路徑 28：把經驗談 source 寫成分析教學模組

`#216 經驗談要重建分析層` → `#219 模組要有推導源頭` → `#218 文章按分析弧拆分` → `#220 判準寫到條件層` → `#217 審查要有斷言支撐 frame` — 素材是從業者經驗談（訪談 / 社群貼文 / 口述）時，先用 #216 判別 source 類型（分析文自帶分析層、走 #143 拆層；經驗談只有事實 + 判讀、分析層要重建）：事實保留、判讀當 hypothesis、機制由作者從領域理論補建，承擔判準的斷言要能回答「為什麼成立、什麼條件下不成立」；建構時先用 #219 立模組級的推導源頭（一個各篇判準能折算回去的基準機制、寫進模組索引），再用 #218 的分析弧判準規劃篇章邊界（一篇走完情境 / 機制 / 量化取捨 / 判準 / 失效條件）、素材不夠走完弧就併入或 backlog、心態類內容依知識類型分流成篇；判準段逐段用 #220 的重算測試驗收（條件 → 行動的映射＋失效情境、維度清單是空殼——機制重建完成仍可能停在第二層）；審查時用 #217 把斷言支撐 frame 排進第一輪（素材來源是經驗談即高風險 batch、知識類型錯位越早抓返工越小）、模組層對照分類 house style 與推導源頭的存在。五卡各守一段（素材轉換 / 模組結構 / 篇章結構 / 判準顆粒度 / 審查覆蓋）——只修任一段、其餘缺口仍會讓模組以「合規的經驗談」形態通過生產線。

### 路徑 29：新增內容目錄或擴充工具鏈規則時的註冊點檢查

`#221 作用域要顯式列舉` → `#139 新目錄要同步首頁入口` → `#93 slug 是 fact 不是 derivation` → `#96 適用範圍要 enumerate` → `#44 值的住址只能有一處` — 新增一個內容目錄時，它需要在數個彼此獨立的註冊點現身，而漏掉任何一個都不產生錯誤訊號：#139 管人類導覽層（首頁分類段落）、#221 管檢查層（lint 的作用域常數）。兩者的失效同形——目錄本身完全正常運作，只是某個地方沒登記，於是它在那個維度上不存在。診斷順序是先用 #221 的「該目錄從未在 lint 輸出裡出現過」測試作用域涵蓋（用一個已知違規測它報不報錯，零 error 只在從非零變過來時帶有資訊），再用 #96 檢查作用域的表達形式是列舉而非口語描述（「所有教學文件」執行時要心算、常數沉默時連心算的機會都沒有）。若擴作用域會噴出大量假陽性，那是 #44 的訊號——一個常數同時承載了異義值（schema 適用範圍與系統成員範圍），先拆責任再擴。#93 提供上位判準：凡是從其他值推導出來、看似不必宣告的量（slug 從檔名推、作用域從常數推），都要升格成顯式 fact，差別只在失效的可見度——slug 錯了壞連結、作用域錯了不改變任何可觀察行為，後者更晚被發現、累積更久。

### 路徑 30：entity 設計 / 「請走 X」慣例被繞過 / 同型錯誤復發

`#253 要處理的是那個約束、不是那行文字` → `#222 約束要讓違反路徑走不通` → `#223 逃生口吸收建構路徑的缺陷` → `#42 兩次門檻` → `#110 設計檢討用當下三軸` — 看到「狀態轉換請走領域方法」被 copyWith 繞過、或註解宣稱「只能從 X 狀態轉換」但函式體沒有檢查時，先用 #253 分辨這行是說明需求還是防護需求、以及那個約束能不能先被消除（消除掉就不必挑落點）；確定要守之後用 #222 判定意圖的落點層次（文件層意圖對繞過路徑沒有阻力、宣稱了但沒強制比沒有約束更糟）；同族語意錯誤第二次出現時切到 #223——停止修個案、找它們共同面對的建構路徑表達力缺口（修工廠、不是修每個拼裝點），觸發門檻正是 #42；要把「這是設計缺陷」的判定寫進檢討時用 #110 的當下三軸（成本對稱性 / 可逆性 / 領域先驗）論證、歸因落在工具預設與結構、不落在寫下繞過呼叫的個人。兩卡的分工：#222 管意圖的強制層次、#223 管缺陷的轉移機制；關逃生口是兩者的交點——出口關了、約束才成立、表達力缺口也才會痛。

### 路徑 31：延伸層內容（哲學面 / 跨域對照 / 思維模式）的去留與落點

`#225 教學目標把關、素材量只調寫法` → `#226 以讀者問題立篇` → `#169 原子筆記要有向上的議題入口` → `#130 教材目標先於決策框架` — 一層「不是主概念本體」的內容（哲學思考、工程對照、思維模式）在拆分討論裡搖擺時，先用 #225 檢查否決理由的層次：「素材撐不起一篇」是出現頻率邏輯的變形、門檻只有教學目標（讀者需不需要這層、交付什麼判讀能力），素材量只影響邊界段寫法（單案例照建、標示支撐範圍與候選掛載點）；目標成立後用 #226 決定形式——切分單位是讀者問題（哪種讀者帶著什麼問題來）、一問一篇、標題寫問題本身，自我消解的延伸段（免責聲明式收尾）是缺讀者入口的訊號、給它讀者問題就重獲知識點；各篇仍守 #169 的情境入口（篇名即問題、篇頂回指主概念 hub）；整條決策鏈是 #130 的下游應用——上位目的（教學）先於下位語言（素材量、學科歸屬）。

### 路徑 32：判斷某個 setup / bootstrap / 環境是否真的可重現

`#227 可重現性只有乾淨機器重跑才驗得出` → `#44 SSoT：值的住址只能有一處` → `#93 URL slug 必須顯式定義為 fact` → `#11 早一點用實跑看真實結果` — 要驗一份 setup 指引 / dotfiles / 環境是否真能在別人的機器重現、或追查「在我機器上能跑、換機器就壞」時，先用 #227 認清：讀 repo 只顯示宣告了什麼、乾淨機器實跑才顯示實際依賴什麼，驗證要在無累積狀態的機器（全新 VM / 帳號 / container）跑真實 install、每個分歧是一條未宣告的依賴；那些未宣告狀態（shell profile 的 `eval shellenv`、`/etc/paths.d` drop-in、手裝殘留、寄居別專案的工具）本質是 #44 的第二住址、#93 的隱式推導未提成顯式 fact；而「靜態看起來完整」的錯覺只有 #11 的實跑能戳破。修法都是把未宣告狀態搬進 repo（或明確標成刻意手動），讓 repo 重新成為環境的單一真實來源。

### 路徑 33：用了套件 / 工具、問題還是發生 — 歸因與補洞

`#228 等比縮放不管空間分配` → `#92 視覺手段對齊錯誤層次` → `#82 字面攔截 vs 行為精煉` → `#221 檢查規則的作用域要顯式列舉` — 「我們有用 X、為什麼還會出 Y」的疑問出現時，先用 #228 分層：工具的保證範圍是它輸入輸出所在的層、Y 發生在另一層時工具的靜默是「沒看」不是「沒問題」（等比縮放管常數換算、不管空間分配）；#92 / #82 給同骨的兩個領域對照 — 呈現工具修不到語意 / 邏輯層、字面攔截抓不到行為偏差、三者共享「超出 ceiling 是 false confidence」；同一層之內的靜默另有 #221 的成因二分（通過檢查 vs 不在作用域）。共同修法：引入工具時顯式記錄「它不保證什麼」、缺口層掛上對應驗證（窄幕驗收 / 結構 review / 作用域測試）。

### 路徑 34：分析文章引言的功能定位 — 讀者 surface 不放編輯 metadata

`#229 分析開頭定位問題不講創辦敘事` → `#230 寫作動機是編輯資訊不屬正文` → `#170 Description 是 recall trigger` → `#141 WRAP 是內部工具不是章節結構` — 分析文章的引言、description、章節標題各有讀者面對的功能，共用一個判準：放讀者需要的（分析問題定位 / 功能性 recall trigger / 教學流程章節），不放作者 / 編輯需要的（品牌創辦故事 / 系列覆蓋缺口 / WRAP 分析步驟）。#229 是正面（引言該放什麼：定位 + 結構差異 + 分析問題）、#230 是負面（引言不該放什麼：為什麼決定寫這篇）；兩者從同一篇引言的兩輪修訂抽出、是 sibling。#170 在 description surface、#141 在章節結構 surface 守同一個原則。

### 路徑 35：檢查 / 自審回報 clean 或 pass — 先問涵蓋、不問乾淨

`#232 自審偵測方法要對齊規則類型` → `#233 卡的缺孤錯住在卡↔文章關係裡` → `#221 檢查規則的作用域要顯式列舉` → `#165 register 違規判定靠異源` → `#147 規範化跟自審是兩種認知任務` → `#240 跨模組路由要驗證目的地承接該主題` — 一個檢查或自審回報 clean / 零 error 時，先問「這個通過是涵蓋內的通過、還是根本沒被涵蓋」：#232 是偵測模態軸（grep 對無關鍵詞的規則結構性失明、clean 是看不見不是沒違規）、#233 是 audit 視角軸（卡側 well-formedness 全過、缺孤錯的邊在文章關係裡看不到、要消費側 audit）、#221 是作用域軸（規則沒被納管、零 error 是沒被檢查）、三者同構——audit 的立足點限制它的可見範圍；#165 給無關鍵詞規則的真防線（異源冷讀）、#147 給自審在規則內仍漏同義變體的限度。共同修法：通過訊號要附「涵蓋聲明」——掃了什麼、什麼沒掃、哪些要交異源或換視角，不讓假 clean 跟真 clean 長得一樣。

### 路徑 36：判讀 / 選型類內容被讀者反映「看不懂什麼時候用得到」

`#241 判讀層只給機制屬性、可用程度隨讀者既有經驗遞減` → `#242 形態讓讀者對號入座、微案例才讓他想像得出後果` → `#224 教學層引用 case 要剝離身分與規模` → `常識是相對於讀者背景的` → `#126 寫作 review 是多軸完整性` — 讀者說「講理論沒有範例、想像不出什麼時候會遇到」時，先用 #241 判斷缺的是哪一層：形態（我是不是這一類）與觸發事件（什麼時候要動）都缺，就是純機制陳述；兩者都有而讀者仍說抽象，缺的是 #242 的後果敘事（動作晚了會怎樣）。補敘事時用 #224 劃邊界——它禁的是搬運帳目與身分、不是禁具體敘事，無身分微案例兩邊都滿足。術語層的同構問題見常識卡（作者的常識不是讀者的常識、本組是作者的經驗不是讀者的經驗）。整組的共同機制是 #126：需求被轉譯掉一半而全程沒有訊號，是缺一軸而非某軸不夠深。動筆補之前先過 #242 的來源條款——四拍要有來源、第三拍推不出來，寫不出真實來源時留白比杜撰好，因此這條路徑的終點常常是「登記缺口」而不是「補完」。補完之後接 `#244 範例讓最後一類出口缺口現形`：逐一問「讀者知道這是問題了他去哪解決」，微案例末端那句「補起來要……」是這時才掃得到的第三種盤點單位。

### 路徑 38：寫下一條規則、想知道它會不會被合規地繞過

`#243 判定型規則要規定判定的痕跡` → `#153 漏抓先分 design gap 與 execution gap` → `#232 偵測方法要對齊規則類型` → `#221 檢查規則的作用域要顯式列舉` → `#147 規範化跟自審是兩種認知任務` — 規則寫完之後先跑省力路徑推演（想少做事的人會怎麼合規執行它），#243 給的三種痕跡（產物 / 清單 / 依據）決定補什麼。規則上線之後仍然漏抓時，用 #153 分三種：缺 frame（design）、有 frame 沒跑（execution）、規則允許的最省力形態被執行了（#243）。第三種最容易被誤診成前兩種，因為執行者確實做了、也確實合規。偵測端的兩個同族問題見 #232（方法看不見違規形態）與 #221（規則沒涵蓋到那些檔案），三者合起來是「零 error 為什麼不等於沒問題」的三個獨立來源。最後用 #147 提醒：這一切都不保護規則寫下之前已經寫好的內容。

### 路徑 37：路由指過去卻找不到那篇內容

`#240 路由要驗證目的地承接該主題` → `#155 引用用語意標題不用位置編號` → `#204 路由條目要自包含` → `#232 偵測方法要對齊規則類型` — 讀者回報「這篇文章不存在嗎」時，先擋下兩個直覺解釋（還沒寫 / 已列 backlog），它們都預設方向是對的。第三種是方向本身錯了、內容在別處甚至就在讀者剛離開的那一頁底下，所以第一步是全站搜該主題。找到之後依 #240 的四種處置分流。寫路由這一端用 #204 檢查條目自包含、用 #155 挑穩定的引用錨點；為什麼整套審查抓不到這類錯誤，看 #232——用連結有效性去查「路由是否成立」，方法與規則類型不匹配。覆蓋面的對半是 `#244`：#240 驗既有路由指得對不對、#244 驗該有路由的地方有沒有路由。

---

- [#229 分析文章開頭定位分析問題、不講創辦敘事](analysis-opening-positions-question-not-narrative/) — 商業分析 / 案例判讀的引言用品牌創辦故事開場時，讀者要讀完整段才知道這篇要分析什麼、且 register 被設定成「公司介紹」而非「結構拆解」；開頭三要素是定位（產業 / 規模）、結構差異、分析問題；是 #230 的 sibling（正面 vs 負面）、#170 recall trigger 在正文開頭段的延伸
- [#230 寫作動機是編輯資訊、不屬正文](writing-motivation-is-editorial-not-content/) — 引言出現「A 文章引用了 X 但缺獨立佐證」是把編輯層的系列覆蓋缺口暴露給讀者、讀者不追蹤系列覆蓋地圖、跨篇引用的功能應該是建立分析上下文不是解釋文章存在的理由；是 #141 process metadata 不暴露的正文引言版、#229 的 sibling、#97 metadata 滲透方向的反向
- [#231 案例文章跟跨公司比較是兩個分析責任](article-srp-split-comparison-from-case/) — 案例分析裡嵌完整跨公司比較表時，案例深度被擠壓、比較段被鎖在單一公司脈絡裡無法擴充；判別方式是「刪掉比較段後案例分析是否仍完整」，完整就拆；拆分後案例篇深化自身分析（營業槓桿 / 關係人交易判讀方法）、比較篇可獨立擴充新公司；是 #212 SRP 路由原則在文章結構的應用
- [#232 自審 sweep 的偵測方法要對齊規則類型](self-audit-detection-method-must-match-rule-type/) — 用 grep sweep 自審一組規則時，回報某規則 clean 只有在偵測方法看得見該規則的違反形態時才可信；有標記的規則（動機句型 / 裝飾符號）grep 抓得到、無標記的（敘事開頭 / 結構 / register）grep 結構性失明、clean 是看不見不是沒違規；是 #221 作用域幻覺在偵測模態軸的同構版、#165 register 需異源的上游機制、案例來自 #229 在 self-sweep 漏網靠異源補回
- [#233 知識卡的缺 / 孤 / 錯住在卡↔文章的關係裡](card-defects-live-in-card-article-relationship/) — 缺卡（文章用了沒卡）、孤兒（卡沒文章用）、矛盾（卡的分類跟後來嚴謹 treatment 它的文章牴觸）三種問題都是圖上邊的缺陷、不是節點缺陷；單卡 well-formedness 檢查與建卡當下對單篇的術語掃描都看不到、要一輪從使用文章反向驗證的消費側 audit（多輪審查的 outbound frame 就是它的制度化位置）；案例是 Round 3 outbound 抓到的兩張缺卡 + CDP 分類矛盾；是 #232 的 audit 視角同家族、#81 卡是活系統的觸發機制、#198 缺卡判準的發現機制
- [#234 描述抽象概念要用貼合屬性的謂語](word-choice-fits-concept-attributes/) — 四種錯配：擬人化（「這個角度沒說完的話」該說「沒有提到的問題」）、形容詞（訊號的可辨識度是「清晰 / 明確」不是「直接」）、範疇（命題只有適用與否沒有存在與否——「前提在讀者這裡不存在」該說「不適用於讀者」；「在～這裡」處所框架需要地點、人進不去）、物理化（證據不會「撐得住」、論證不「掛在」前提上——抽象概念沒有重量與支點，該說「支持 / 依賴」）；物理化那種還會讓「支持什麼、到什麼範圍」不必被回答，是繞過不是說錯；**判準一般化為問這個謂語照字面成立需要主詞或賓語具備什麼屬性**——物理化要物理條件、擬人化要主體條件（判定沿轉喻鏈：「作者自述 / 課程頁自陳」合法、「書自述」違規；「自 X」的第一方訊號正面宣告做工、否定句不做工——「沒有自述」要說的是「沒有明說」）、範疇錯配要範疇條件；例外是就地展開成可逐項對應的類比；四者只有物理化有穩定關鍵詞可掃（撐 / 扛 / 掛 / 垮 / 頂）、其餘靠人類冷讀；是 #165 register 需異源的實例、#111 口語稀釋精度的微觀版、#203 用詞精確的 sibling、#270 同批修訂的詞層
- [#235 整合互斥規則集：抽共用 base、按層分離、把衝突顯性化成解析規則](integrate-conflicting-rulesets/) — 多套規則集 / 契約 / 需求部分重疊部分衝突、要合成一套不自我矛盾的規則時：抽共用規則成永遠開啟的 base（SSoT、只寫一次、門檻是三者都受益不是多數有）、按作用層把差異分到正交的層（附可操作但非萬能的判層測試）、把真衝突逐一定位到「爭同一個決定」顯性化成解析規則（力度分全域開關 / 逐項讓步 / 合成）；招牌陷阱是宣稱「衝突只剩一組」——它是搜尋不完整的產物、逐條枚舉規則對才算數、把搜尋結果講成結構定理跟 #152 必然性框架同構；是 #75 的對半（不衝突怎麼疊加 vs 衝突怎麼收斂）、#125 collapse 在規則整合 surface 的修法、#44 共用規則單源、#126 枚舉完整性、#90 疊加訊號一致；從神經多樣性三 skill 整合 + steelman 修正抽出
- [#236 承重論點先對抗驗證、再建下游：核心宣稱的錯誤會等比傳播](validate-load-bearing-claim-before-building/) — 一批工作建立在承重論點（方法論主張 / 核心假設 / 共用 spec）上時、在蓋依賴它的下游前先對抗驗證那個論點、別先寫滿再事後 steelman；承重論點錯了會等比傳播進每個下游、晚抓改一次要改 N 處、驗證順序跟依賴順序相反（最被依賴的先驗）；先寫再驗的兩個力量是產出感偏誤 + 同源相信盲區（作者對自己的地基有盲點、要對抗 / 異源）；steelman 用兩次（前置打地基當閘門 / 後置打全面當收尾）；判準是只前置承重的那一個（錯了下游要不要大改）；是 #11 早驗的相信盲區版、#64 上游修一次的論點維度、#217 斷言支撐 frame 的時機面、#165 同源盲區、#205 生產順序、#235 同事故的流程面；從神經多樣性方法論「衝突只有一組」錯論點寫進 6 檔、Round 3 才抓的生產順序事故抽出
- [#237 任務累積成基礎設施前先亮出 anchor：escalation 逐層加工具、anchor 卻最後才浮現](surface-anchor-before-apparatus-accretes/) — 一個任務經過連續幾次「再加一層」（模組 → skill → 審查 → 卡）滾大時、先把 anchor（最終為誰 / 為什麼 / 對不對外）講出來一次、按它定要蓋多少基礎設施；反模式是 apparatus 份量跟隨流程動能而非 anchor（產出感偏誤 + 工具化偏誤疊加、每層局部合理總量對不上）；anchor 傾向最後才浮現、一浮現就翻轉份量判斷；亮 anchor 是 escalation 訊號出現時的一次性閘門、不是每個請求都質疑；是 #235 / #236 同 session 姊妹（#236 驗正確性 / 本卡驗份量）、#125 collapse 的份量維版本、#75 疊加增量成本判準沒對照 anchor、WRAP Anchor Check 在多輪協作的具體化；從「幫朋友做 skill」滾成對外模組 + 三輪審查 + 兩卡、anchor「自用」最後才浮現的事故抽出
- [#238 承重事實要對到 primary source：自己的舊分析是 secondary、不是 ground truth](verify-load-bearing-facts-against-primary-source/) — 分析建立在某事實上、而該事實來自二手（新聞 / 彙整站 / 自己舊文）時，回到 primary source（申報書 / 官方登記）核對；自己的知識庫是 secondary、繼承當初的錯、還因出自己手不被重審；更正錯誤事實別停在第一個反例（驗到 primary 或多來源收斂）；是 #236 的事實版姊妹（#236 驗判斷 / 本卡驗事實）、#227 讀宣告≠實跑同型、#93 fact vs derivation、#217 斷言支撐補來源層級；從引用本站舊文「中聯未上市」傳播錯誤、再過度修正成「上市」、最後靠使用者觀察 + MOPS 年報落到「公開發行未上市」的查證骨牌抽出
- [#239 宣告的組合不等於執行的組合：顯著的那半擠掉費力的那半](declared-composition-is-not-performed-composition/) — 同時啟用兩個行為 / skill 並宣告「都在」時、在每個輸出點驗證兩半都真的現形——顯著省力的那半（帳本）會執行、費力不顯眼的那半（5w1h 結構化）會靜默掉、自審只查「有沒有宣告啟用」抓不到；修法是 pre-send 逐半驗證輸出裡的可見痕跡、費力那半優先檢；是 #235 組合設計的執行落差面、#147 規範化≠自審的組合版、#232 查宣告 vs 查現形、#163 宣告介面≠實際交付；自我示範——neurodivergent-output + 5w1h 同開卻只跑帳本沒跑 5w1h、由使用者抓到；後補一維**有檢查表的擠掉沒有檢查表的**——顯著／費力是一種不對稱、有沒有檢查表是另一種，而後者在設計審查維度時更常出現（實測：同一個 reviewer 同時交付「比對宣告與實際內容」與「走一次讀者路線」，前者可機械化有明確完成條件、後者要先固定讀者身分才有判準，結果走路線那半在報告裡只剩幾句概括）；判別同樣看產出量分布、處置是給沒有檢查表的那半一個檢查表（走路線的檢查表是逐跳表加上「沒有逐跳表的已走過不成立」）或拆給不同執行者

- [#240 跨模組路由要驗證目的地承接該主題、不只驗證目的地存在](routing-destination-must-own-the-topic/) — 把讀者送去別的模組 / 章節時、去目的地找出承接該主題的具體檔案再寫路由；目的地存在不等於它承接這個主題，而連結檢查只驗存在、code 格式的模組指涉（`` `05-deployment-platform` ``）連存在都不驗；落空時分四種處置（指錯改指正確落點 / 該有但沒寫則列 backlog 並判斷要不要先建簡版 / 根本不該路由則刪 / 目的地在自己維護範圍之外則寫明「到那裡要拿到什麼」），第一種最易被誤判成「還沒寫」、所以先全站搜該主題再假設要新寫；來源端三層失明（工具只驗存在、review frame 只查連結有效性與 outbound 方向、作者憑語感分配模組）加目的地端無人看 inbound讓它活過三輪十個 reviewer；是 #155 misdirected 比 dangling 難偵測的模組層形態、#204 的另一端（條目讀得懂 vs 目的地接得住）、#232 偵測方法對齊規則類型的實例、#126 缺一軸而非某軸不夠深；從 7.28 把金鑰託管送去 05 部署平台、而六個 KMS / Vault 服務頁其實都在 07 自己底下的事故抽出；承接之上還有第三道關卡**可達**（目的地有這個主題卻埋在第三層小節時、讀者到站體驗與落空相同、驗收走到落點第一屏）

- [#241 判讀層只給機制屬性時，可用程度隨讀者既有經驗遞減](judgment-content-needs-triggering-scenarios/) — 寫判讀 / 選型 / 決策類內容時、機制屬性要配上「什麼系統會遇到」與「什麼事件會逼出這個動作」才構成判準；只給屬性時讀者必須自己補情境，而補情境需要的經驗正是做判斷的輸入、可用程度隨既有經驗遞減、最需要它的那一端拿到最少；關鍵區分是**情境不等於實作**——判讀層宣告不展開實作是對的，但情境屬判讀層自己（判讀的定義就是「遇到 X 時該怎麼選」，拿掉 X 剩下分類學）；情境分兩種對應讀者兩個時刻：系統形態服務設計階段（我是哪一類）、觸發事件服務事故階段（發生這件事該動哪一層），而問題節點表的「判讀訊號」欄有時序陷阱（要等落地才觀察得到、設計階段是空的）；修法是兩拍寫法（先形態後後果）、形態份量夠就獨立成節；兩個固定副作用要一併掃——補情境會引入第二人稱（講情境時不自覺對著人講）、原本的封閉計數會失準（缺情境常伴隨缺段落、「三種混法」對不上四個節點）；辨識訊號是同篇通常有一兩節「不小心寫對了」＝能力在、檢查點不在、修法該加維度而非加寫作指導；是 #217 的另一種判準斷點（那是沒映射、本卡是有映射沒入口）、「常識是相對於讀者背景的」在情境層的同構、outside-in frame 的新盲點、#240 同批事故姊妹；從 API 認證分層章通過完整多輪審查、提需求的人讀完問「什麼情況需要撤銷」而浮現的事故抽出

- [#242 形態讓讀者對號入座，微案例才讓他想像得出後果](micro-case-makes-consequences-imaginable/) — 教學內容補完系統形態之後、判斷讀者是否還缺「出事會長什麼樣」；形態是分類語言（我是不是這一類）、微案例是過程語言（出事會怎樣），兩者服務不同認知動作、缺一則判讀不完整、而有經驗的讀者能自己補後者所以純形態內容對他看起來已完整；微案例＝無身分短敘事（三四句、無公司名年份帳目），它同時滿足 #224 的剝離要求——#224 禁的是搬運帳目與身分、不是禁具體敘事，分工是微案例在章節內讓形態可想像、真實 case 在案例庫承擔可查證；四拍寫法（當初為什麼這樣做／什麼時候開始出問題／為什麼沒被及時發現／止血的代價），第三拍最不可省略——其餘三拍讀者能從機制自行推得、它取決於組織的監控與責任配置，缺第一拍讀者會覺得是別人才會犯的蠢錯；反模式是把「補範例」轉譯成「補分類」——分類語言可檢查可窮舉所以執行者傾向選它、補完每項都正確但原始需求只滿足一半、且因為通過所有檢查而沒有訊號；辨識訊號是**提需求的人用原本的詞再問一次**；是 #241 的補完（那張把情境拆成形態與觸發事件、兩者都是分類語言、本卡把後果從分析換成敘事）、#224 留下空白的填法、#126 缺一軸；從補完形態後使用者再問「怎麼沒看到補案例」的事故抽出；**四拍要有來源**（親歷 / 案例庫已記形態 / 機制上必然）——第三拍是唯一推不出來的那一拍，推不出來就代表沒有這段經驗的作者或生成工具只能發明它，而模板不會擋下發明，寫不出真實來源時留白比杜撰好（編造的盲區比沒有微案例更難被後續審查推翻）；連帶排程後果是一輪掃描補不完全部章節，「一輪之後所有章節都有微案例」本身就是照模板填的訊號
- [#243 要求執行者做判定的規則，要一併規定判定留下什麼痕跡](judgment-rules-must-specify-their-trace/) — 寫下「先判斷 X、再依判斷做 Y」這類規則時、同時規定判定要留下什麼可複驗的產物；沒有痕跡的判定不可證偽（認真做過與完全沒做的產物相同）、規則因此只約束願意遵守它的人；塌陷方向可預測——**沿著零後續動作的那個結論走**（判成不適用 / 不需要補 / 份量不夠），那個結論同時最省力也最難質疑，因為它不產出任何東西可供檢查；痕跡三形態依規則性質選（產物層：判定結果寫進成品、清單層：判定範圍列出來、依據層：判成零後續結論時說出憑什麼）；反模式是把不適用清單寫成裸清單——清單描述整份內容的類型而實際內容很少純粹，拿其中一節對上任一項就能把整篇判成不適用、清單於是變成規則的關機鍵，同構形態是數量上限被當配額（「一兩個」的下限是一）與三級量表的中間值（只有「中」兩邊都不必舉證）；修法是對每條規則跑一次省力路徑推演（想少做事的人會怎麼合規執行 / 差多少 / 規則擋不擋得住），補的是痕跡不是語氣，並在三條之後停下來抽共用原則以免規則膨脹到需要導讀；是 #147 的下一層（立規範也不保護之後照它寫的內容）、#232 的前一層（違規形態根本沒留下可偵測的東西）、#217 的對半（規則沒寫完 vs 寫完了但不可證偽）、#221 同讓「零 error」失去意義、#153 的第三種 gap（規則存在也執行了、執行的是規則允許的最省力形態）；從本批三張卡與一份格式規範跑第四輪「誤用 / 激勵梯度」frame、十一項 finding 全部收斂成同一個形狀的觀察抽出；**規則生效之後判準要升級**——剛立時的失效是沒人照做，生效之後換成「每一處都留下規則要求的外觀而要件掉了一半」（實測：一條要求「明說 + 登記待辦 + 最小判準」的規則，同批五個實例只有一處三項齊全、其餘各掉一項不同的，而每一處單看都像照做了），另一種同型是**判準被同義替換**（要求「挑後果最不直觀的、其餘說出可以不寫的理由」而寫下的理由是「別處已經寫過」——聽起來是理由但換掉了判準）；因此核心那句要從「認真做過與完全沒做，產物有沒有差別」升級成「**做滿與做一半，產物有沒有差別**」，多要件的規則要讓每個要件各自可見

- [#244 範例讓最後一類出口缺口現形，而盤點要跨兩個階段各跑一次](examples-expose-missing-exits/) — 教學內容補完情境與範例之後、用「讀者知道這是問題了他去哪解決」掃全文；**讓缺口現形的是換視角這個動作本身**，既有的檢查維度都在驗「已經寫的內容對不對」、用段落當視角時分析句讀起來完整、本身沒有缺口；盤點單位是每一句「指名了問題卻沒有就地解決」的話——這是規則不是清單（本卡最初寫成三項封閉枚舉，而判讀徵兆自己就列了第四類：out-of-scope 宣告到「不在本章範圍」為止，那一類在多數章節的密度還高於前三類）；**盤點要跑兩次**，因為判讀表的列、風險邊界的條、out-of-scope 的宣告在文章寫完的當下就掃得到，只有微案例末端那句「補起來要……」要等範例存在——整個盤點延到補範例之後前幾類會被拖著、只在補範例之前掃一次第三類永遠掃不到；範例的貢獻是多出一類單位而非解鎖整個盤點；四種出口狀態依處置分（就在手邊＝合格 / 存在但在文末＝就地補連結、可達問題的文章內版本 / 不存在但可用最小可行答案打發＝當場補或寫簡版並在開頭明說是簡版 / 不存在且需完整推導＝明說它不存在並給最小判準，因為讀者找不到時的預設歸因是自己沒找到）；反模式是替換微案例時連帶刪掉唯一的止血知識（第四拍常是全篇唯一寫出止血路徑的地方、而替換理由只評估了前三拍）；是 #242 的交錯而非後續（出口盤點在形態階段與微案例階段各跑一次）、#240 的對半（那張驗既有路由指得對不對、本卡驗該有路由的地方有沒有路由）、#241 同一個投射的兩種形態（假設讀者知道何時遇到 vs 假設他知道遇到後怎麼辦）、#126 缺一軸；從 7.28 / 7.29 補完範例後盤出七處缺出口的實測抽出

- [#245 原則層與操作層是兩份會漂移的副本，而漂移只往一個方向](principle-operationalization-drifts/) — 一條原則同時寫在抽象卡片與操作手冊時、判斷執行者手上那一份是不是最新；**修正流向單向**——抽象層是討論焦點、改一段文字就完成，操作層是程序性的、同一條改動要先判斷影響哪幾步插在哪一步之後，於是時間壓力下先改抽象層而「稍後」沒有觸發器；漂移看不見是因為兩份各自讀起來都完整（操作層沒有殘缺沒有矛盾、也沒有指向抽象層說以那邊為準，它就是一份自洽的舊版本），而審查抽象層的人讀抽象層、審查稿件的人讀操作層，沒有任何一項檢查在並排比對；**最重要的是誤診代價**：套用率低時自審失效與漂移的表徵一模一樣而修法相反（加強檢查 vs 同步副本），誤診成前者時加再多輪審查、reviewer 拿的還是舊操作文件、掃出來仍是「符合舊規則」，而審查通過會反過來確認「規則已落實」讓漂移更難發現；分辨只需一個動作——套用率低到不像疏忽時先打開執行者實際讀的那一份，且這個動作要排在歸因之前；修法是改動單位取「這條原則的所有副本」而非被點名的那一份、抽象層記下執行入口、版本號粒度對齊、排一次**從操作層出發**的反向核對（方向要從操作層出發，因為漂移的形態是操作層缺內容、從抽象層出發只會確認每條都有對應段落）；是 #147 最常見的誤診來源、#243 的上游（規則設計得再好、執行者讀舊版就不生效）、#221 同讓「已檢查」失去意義但斷點不同、#44 在「無法只有一處」時的處置、#239 同型的宣告與實際落差；從一條規則套用率零、查下去發現卡片修過三次而操作文件停在第一版的實測抽出

- [#246 被多篇當成前提的判斷缺的是住址，而每一篇的檢查都看不到](shared-premise-has-no-home/) — 多篇教學內容各自交代了同一個概念的一角時、判斷它該不該有自己的篇章；**缺口只在把幾篇並置之後才出現**，而並置不是任何既有檢查會做的動作——每一篇只需要它的一角，而那一角每篇都寫得出來、寫完本篇就完整了；機制是共同前提沒有歸屬（章節由具體問題長出來、事故發生在機制上，而「該不該做這件事」是所有相關章節的共同前提、不是任何一篇的缺口，因此沒有任何一篇的寫作動機會帶出它）；**前置段是讓它更難察覺的形式**——不屬於本篇的內容放進前置段之後有了合法容身處（它確實是本篇的適用性閘門），因此不觸發 #212，而那條管的是「不屬於」、前置段屬於；反模式是**修法落點跟隨發現路徑**（reviewer 逐篇進行、從某篇出發說「缺前置」、修法就落回那一篇，整個過程沒有一步是錯的而產出是把跨篇的軸壓成某篇的一段），辨識訊號是修法後那一段讀起來比它所在的章節更上游；修法先分**缺卡還是缺章**——同一個名詞在多篇各解釋一次而內容相同是術語（建卡），同一條判斷軸在多篇各交代一角而角度不同是缺章（因為取捨需要並置、而並置只能發生在同一篇裡）；偵測用數（三篇以上當前提且各篇寫的不是同一句話），三篇是門檻不是定則——兩篇時通常仍是其中一篇的延伸段、三篇之後「哪一篇是主場」就沒有答案；新開一篇後各篇那一角要留著當適用性閘門（壓縮成一兩句加路由、保留判準把推導交上游），新篇要標明自己是誰的上游（它在所有下游章節之前，而模組入口的路線多半照編號寫）；是 #212 的盲區（那條靠「主題與篇標題不同」判別、而前置段主題對得上）、#244 第四格的反面（單篇視角下不落空）、#126 又一條沒人負責的軸且是跨篇的、#221 同讓「每篇都通過」失去意義、#245 同屬「並排才看得見」的家族；從一個資安模組四輪審查後盤點出十一項待辦裡有五項同形態、且全部由審查登記而非寫作當下浮現的實測抽出

---

- [#247 多次局部正確的修法會合成缺陷，而合成的缺陷對每一次修法的 frame 都不可見](sequential-fixes-compose-into-defects/) — 同一份內容經過多輪審查各自修法之後、判斷它有沒有累積出誰都沒看見的缺陷；**不可見是結構性的**——第一個 frame 的視野裡沒有第二次修法（還沒發生）、第二個 frame 的視野裡有第一次修法的產物但沒有它的動機（frame 只問自己那一軸），於是「這兩件事放在一起會怎樣」不落在任何一方的職責裡；與 #167 不同機制（那裡同成因、近 frame 抓得到，這裡兩次修法成因不同各自都對、缺陷只在關係上），要看見它必須有第三個 frame 而那個 frame 的對象是「這份內容現在整體長什麼樣」；**第二種形態是共用產物**——模組入口、待辦清單、索引被每一輪修改卻不在任何一輪的審查範圍裡（每輪的 frame 都是對著內容設計的），入口頁累積 N 輪插入之後可能已經不成句而 reviewer 讀的是章節；**登記與除籍的不對稱**是它在待辦清單上的表現（登記便宜且動機明確所以會做，除籍由「以為自己做完的人」執行而他在檢查自己的工作），實測是拆章時刪掉的那一列裡有一半還沒完成；修法是每輪收尾多一次通讀（判準：這份內容現在讀起來像一個人一次寫完的嗎）、共用產物進審查範圍且排最後一輪、除籍要說出它被哪一次改動完成、修法落在別人的段落上時讀完那一段再改；是 #148 的補充條件（frame 涵蓋齊備之後還差一次整體通讀）、#95 擴空間而本卡擴視角、#245 / #246 同屬「沒有人並排讀」的家族；從一組資安章節連續跑八輪審查之後的回看抽出
- [#248 推翻一個假說之後，替補者是在驗屍的空檔裡上位的](hypothesis-replacement-inherits-no-scrutiny/) — 剛推翻一個自己的判斷、手上已經有替代解釋時，那個替代解釋憑什麼被接受；**替補者沒有經過審查，因為當下所有的審查力氣都花在被告身上**，而它多半是從推翻的過程裡浮現的、帶著「已經被想過」的錯覺（實際只滿足「與已知事實不衝突」這個所有替代解釋的最低門檻）；**最關鍵的是替補者的證據常常就是為了測前任而蒐集的那批資料**——那批資料的設計目標是分辨舊假說真偽，對新假說是事後解釋而非預先檢驗；推論是一句可直接執行的話——推翻之後第一個要問替補者的，是那個剛剛用來殺死前任的問題；修法是替補假說不繼承前任的實驗、提出當下就寫出對照設計（寫不出來代表表述還不可證偽）、在它有自己的對照之前不得寫進規範（錯誤歸因會被後續工作當前提，且比原本的做法更差卻被固化）；是 #227 未驗證宣稱在解釋層的形態、#239 宣告與執行落差的假說層版本（多一層：套用標準的人正是剛訂出標準的人）、#153 的常見誤診方向（把執行落差說成缺一條規則）、#148 完成判準家族、#247 序列交界缺陷的 sibling；從一段方法論實驗的兩次假說替換抽出——兩次都是「說得通 + 零對照」，第二次是用剛驗證過有效的批評換上經不起同一批評的替代品
- [#249 對當下段落沒有收益的標註不會自發發生](annotation-with-no-local-payoff-needs-a-trigger/) — 內容裡的數字、事實與判準缺來源、版本或適用邊界時，判斷該補檢查表還是補觸發點；**標註會不會自發發生由它的收益結構決定、不由作者的仔細程度決定**——來源 / 版本 / 期間 / 量測條件 / 適用邊界這類標註對當下段落的完整度沒有貢獻（不標也讀得通、論證照樣成立），收益全落在日後回溯或驗證的人身上；**對照是內建的**——同一篇文章裡機制與判讀類標註的到位率顯著高於來源與適用條件類（技術模組四篇方向全一致、平均差約 30pp，財務模組七篇的三個維度全數失效），同一位作者同一次寫作，作者能力 / 內容成熟度 / 主題難度因此被消掉、只剩收益結構這個變因；修法是把檢查點綁在產生它的動作上（「寫下一個百分比時」）而非再寫一份事後清單，住址要選寫作者會撞到的地方（模組入口的擴充指引、不是審查流程文件），條目要用實際發生過的形態（「毛利率的分母是售價、35-40% 對應 54-67% 加成」而非「注意標來源」）；事後審查仍要有但定位是存量清理；**待測層**是「無當下收益且有當下代價」的更窄版本（時點與配置標了、而『此數為推估』一次都沒標，差別可能在標它會不會暴露作者知道得比看起來少）——依 #248 的紀律標為待測、不繼承主張層的證據地位；是 #247 登記除籍不對稱的姊妹（那裡是做了沒人看得到、這裡是不做沒人看得出來）、#116 分層判準的觸發時機、#227 宣告與實際落差在文字層的形態、#153 執行落差的典型案例；從財務七篇與技術四篇的跨領域量測抽出
- [#250 資料多出一種形狀時，既有分析邏輯靜默換語意](new-data-shape-silently-changes-analysis/) — 資料模型新增一種列或事件型別之後，判斷既有的公式、查詢與聚合是否還在算同一件事；**分析邏輯裡的每一個條件式都編碼了一個對資料形狀的假設，而那個假設沒有住址**——`COUNTIFS(...) = 1` 裡的「1」承載的是「一次瀏覽產生一列」這個資料模型事實，它不在公式旁邊、不在欄位定義裡、只存在於寫下公式那一刻的心智模型中，而心智模型不會隨資料模型一起更新；不可見的第二個成分是**錯誤輸出與正確輸出外觀相同**（合法標籤、無錯誤值、要察覺算錯得先有一個獨立來源知道本來該有多少，而分析邏輯存在的理由正是沒有那個來源），第三個成分是**變更的動機讓副作用難以聯想**（新增形狀的動機是知道更多、副作用卻是某些統計悄悄歸零，而歸零與「這種情況不存在」不可區分）；修法是把下游重算納入同一次變更、讓未涵蓋的資料標成「未分類」而非留白、用總量守恆檢查涵蓋（差額不為零即有形狀漏掉，不需預先知道漏了什麼）、條件式常數旁註明來源以支援反向搜尋；是 #221 在分析層的同構（零 error 與零命中都與「沒被涵蓋」不可區分）、#232 在資料層的對應、#228 的層次延伸（公式的保證只涵蓋寫下它時的資料形狀）、#239 落差家族但多一個條件——落差由另一次正確的變更引入，當下沒有人做錯事；從一套自建流量統計的資料判讀抽出
- [#251 清單過時的代價要落在精度、不落在覆蓋](stale-list-costs-precision-not-coverage/) — 判定依賴一份會過時的清單（已知名稱、白名單、簽章）時，先決定清單失效之後還剩下什麼；**清單會過時是確定的，設計上的自由度在於選擇過時的代價落在精度還是覆蓋、避免過時本身不在選項裡**——覆蓋的損失不可見（漏掉整類對象表現為數字變好看，而變好看的數字不促使任何人去查），精度的損失可見（標記成 `ua:bot` 而非 `ua:claudebot` 時，讀報表的人立刻知道自己不知道是誰）；**清單過時不產生通知**，維護需要外部觸發而「有新項目出現了」這個事件不會主動送達，仰賴定期審視的計畫在系統看似正常的期間最容易被延後；**退回層必須獨立於清單而非清單的擴充**——加更多同類條目只是把列舉的邊界往外推，退回層要用另一種特徵（具名比對身分、通用比對類別詞，後者不需要知道任何一個名字就能運作）；修法是精確層負責識別 / 粗略層負責覆蓋、退回層命中率要可觀測（比例上升即清單該更新，把不可見的過時變成可看的數字）、分辨清單用於分類（可只靠清單、其餘歸「其他」）還是偵測（不行，失敗形態就是漏掉）、用「清單從今天起不再更新、一年後還答得出什麼」做一次推演；是 #250 的姊妹卡（衰減分別由資料端與外部世界變化引發、處置同構）、#221 的常數過時家族、#232 在時間軸上的延伸（設計時成立的對齊會因對象演化而事後失效）、#125 把沒人決定過的預設轉成有人決定過的設計；從一套自建流量統計的自動化訪客辨識抽出
- [#252 配額耗盡的症狀落在申請最頻繁的元件、成因在持有最久的那個](resource-exhaustion-symptom-vs-holder/) — 共享配額（程序表格位、檔案描述子、連線池、鎖、rate limit）耗盡型故障要歸因時、決定從哪裡開始查；**症狀的位置由申請頻率決定、佔用量由申請頻率乘持有時間決定（Little's Law 在配額上的形態），而持有時間的跨度遠大於申請頻率的跨度、佔用量排序因此多半由持有時間主導**——兩個量共用申請頻率、並非互相獨立，分開它們的是「有沒有歸還」，於是症狀最密集的位置多半不是成因所在；這個方向的前提是配發者不挑受害者（OOM killer 依 RSS 挑對象、連線池驅逐持有最久的、依用量節流的 rate limiter 都內建了一次持有者歸因、症狀反而直接指向持有者）；例外是申請者與持有者重合，兩種長相——釋放漏在例外路徑上、以及**申請頻率沒變而持有時間退化**（熱門端點單次持有從 2ms 變 800ms、佔用量漲四百倍，修法既非回收也非擴容）；不可見有三個成分——**推論鏈的每個組成事實都為真**（症狀確實集中在那裡、那個元件確實高頻申請、錯誤確實是申請失敗，於是自洽度無法作為正確性的證據）、**症狀是零成本送達的證據而持有者紀錄要主動發起查詢**（哪一邊先發生由收益結構決定、非由仔細程度決定）、**囤積者在常規監控上是平的**（殭屍不佔記憶體、洩漏的 fd 不產生流量，「所有指標正常」與「沒有量測這一項」給出同一個訊號）；修法是先量配額再看誰在報錯（辨識形狀：失敗的操作在功能上互不相關、共同點是都要申請同一種資源）、查系統保存的持有者欄位並排在因果推論之前（ppid / lsof 持有 PID / 連線池 checkout owner / 鎖 holder，成本固定且不依賴任何關於誰在耗資源的假設；兩個前提會產生高信心的錯誤答案——查詢要在耗盡進行中執行否則空集合讀起來像「沒有持有者」、聚合欄位的粒度要對應得上可回收的單位否則 PID 1 / reactor thread / 共用 API key 會把所有洩漏聚成同一桶）、**依持有者聚合後看分佈而非單一最大值**（集中在單一持有者是回收問題、接近均勻是擴容問題，這個分岔決定後續全部工作方向）、取用持有時間欄位把發作時機與觸發原因接回去、把「提高上限」與「回收配額」在論述上分開；是 #248 的適用邊界（有一類故障可以先跳過建假說、因為系統保存了直接指認持有者的紀錄、它把搜尋範圍從全系統縮到一個元件；持有者不等於成因、縮完範圍仍要回到 #248）、#221 在監控層的形態（且監控涵蓋面連一份可查的清單都沒有）、#250 外觀相同家族在解釋層的成員、#249 收益結構決定行為框架用在診斷順序上、#153 同屬歸因分流卡；從一次 macOS 使用者程序額度耗盡的誤判抽出——數個各自為真的觀察串出一個自洽而錯誤的解釋，實際成因由一行 ppid 聚合查詢指認
- [#253 寫註解的動機是怕被改壞時，要處理的是那個約束、不是那行文字](protective-comment-signals-missing-enforcement/) — 準備為一段程式寫註解、或在 review 裡爭論某行註解該不該留時，先判斷這是說明需求還是防護需求；**註解不參與執行，因此改壞的當下不產生任何訊號**，它的作用發生在有人剛好讀到的時候、而「順手整理」的人正是不會停下來讀的那種，於是防護意圖寫成註解等於把需求送到一個沒有執行權的窗口；**辨識訊號是動機而不是文字**——動機不會寫在註解裡，要靠作者說出來或被問出來，這也是為什麼「這段文字該怎麼寫」這個問法問不到重點（實測是同一行 doc 改了兩版都被退，第二版寫的是真實存在的生命週期約束仍被退，循環直到動機被問出來才結束）；辨識成防護之後**消除那一步不可跳過**——先問這個約束能不能不存在（約束通常是某個結構選擇的產物，本案例的「必須活過重設」來自值被放在共享可變狀態裡，改成參數傳遞就消失），不能消除才在會發聲的層裡挑；挑選的軸是「訊號多快出現、能不能被忽略」（型別在編譯當下且無法忽略但裝得下的約束窄、測試在跑測試時且訊息描述症狀、命名在每個呼叫點被讀到但不自動發聲、註解只在剛好被讀到時），而**既有強制層清單把兩條獨立的軸壓成一條強度刻度**——「規則寫在哪」（寫進被約束的產物裡：註解、介面簽名、建構子檢查、schema 約束；或寫在產物外面：lint 設定、CI 規則、測試檔）與「違反時何時發聲」（永不 / 編譯當下 / 寫入當下 / 合併之前 / 上線之後）是獨立變化的，文件層與型別層同樣寫在產物內而發聲能力是零與編譯期的差距；壓成一條的代價是**產物外那一側只被看到一格**，而 CI 那格裡的 lint 與 architecture test 都是讀程式文本的檢查（掃原始碼長什麼樣、不掃程式跑起來怎樣），**觀測執行行為的那一種在清單裡沒有位置**；跨函式的讀寫順序、某個值必須活過某次操作這類約束在多數主流型別系統裡產物內沒有位置寫得下（Rust 的 lifetime 與 typestate 生態是例外），沿刻度往上找的人每格都塞不進去、於是被送回起點寫一行註解——這個分類買到的正是**刻度的終止條件**，而空著的那格裡放的是一條普通的行為測試；判準要有二元出口否則會停在「這段資訊算多還是算少」，可執行版本是三步、每一步的產出都是第三人看得到的物件：唸出型別名稱後說出還剩哪幾個字、問剩下的資訊有沒有對應的斷言（二元性掛在存不存在一條會紅的斷言、不掛在造得出句子）、問它的來源在不在 repo 裡；後兩步可以同時成立，此時測試守行為、註解留出處，這一步同時消掉「剩一點點」與「結構層面 vs 業務動機」兩個灰帶；驗證不必推論——**故意在違反約束的位置加一行改動、跑測試看有沒有機制發聲**，把關於未來的問題換成當下可執行的操作；是 #222 的上游加一格（那張處理意圖確定要強制時該落哪一層、本卡處理更早的動機辨識與消除 gate）、#100 假防護感在程式碼註解的形態、#67 便利度與有效性排序相反因此誤送系統性發生、#221「規則存在 vs 規則涵蓋」的同構、#249 的反向姊妹（那張是該標而沒標、收益落在日後的人身上，本卡是不該寫卻寫了、收益是作者當下的安心感）；從一次 code review 的兩輪退件與一次破壞實測抽出
- [#254 教學與檢討內容寫給帶問題來的讀者，不是要被吸引的聽眾](write-for-readers-not-audiences/) — 為教學文章、work-log 檢討或 report 卡決定標題形式與敘事視角時、或審查時判斷問句標題 / 懸念段標 / 第一人稱事件敘事該不該改時使用；**判準取決於受眾狀態**——演講面對注意力隨時會流失的聽眾、hook 與懸念是維持注意力的合法工具，教學與檢討內容的讀者由搜尋或路由帶來、自帶問題與動機，被扣住的答案對他是額外成本；兩類形態——**懸念型修辭**（問句標題把唯一保證被讀到的檢索錨用來提問、懸念弧把核心判準壓到文末、正面違反核心先行）與**第一人稱事件敘事**（可重用的判斷被包在一次性個人時間線裡、判斷的成立條件藏進對話重現、讀者要自己做一次抽象才能套用），修法是把事件單位換成條件單位（「reviewer 問了 X」改成「若對這個做法問 X 而答不出來、就該重新檢討」）、脈絡保留但載體換成客觀條件、「來自實際事件」的宣告開頭一句話帶過；判別線是位置——操作型自問句（判準的執行步驟）合規、出現在標題 / 段標 / 結論位且答案被扣在後文的是懸念型；**多輪審查抓不到有三層**——規範缺位（規則不存在時 compliance reviewer 產生不了 finding、零 finding 與沒有問題同訊號）、frame 射程（keyword bank 是現象枚舉而懸念與第一人稱不在枚舉、persona 檢查掛在批次流程而單篇不進）、同源文風默認（問句標題與三幕劇是生成端高頻默認、同源 reviewer 覺得自然）；修法主力在生產側（寫作規範與模板、生成時就不產生）、審查 keyword 是補位，模板要明定「問題情境」的單位是條件、否則會被最省力地填成個人事件劇；是 #166 的篇章層形態（懸念弧是重點後置放大到篇章、並限定它的敘事豁免——豁免屬於以敘事為目標的文體、教學與檢討內容即使取材自事件也不落在豁免內）、#165 的上游一層（那張處理規則存在但同源判定放水、本卡案例連規則都不存在）、#221 在審查 frame 層的同構（審查報告不會標示自己沒看什麼）、#170 的同族（metadata surface 是功能件不是修辭位）；從一篇 work-log 檢討通過多輪審查、語氣問題由使用者指出的事故抽出
- [#255 讀者重建不了的斷言清單，展開成讀者位置的走查](assertion-list-needs-reader-walkthrough/) — 寫作或審查時撞到條列式斷言（「拆開來看有三個毛病：1、2、3」）、要判斷這段說明讀者是否讀得懂時使用；**條列式斷言是作者走完推導後只輸出結論**——每一條背後都有作者做過的動作（搜過識別符、對照過型別宣告）、但清單只留下動作的結果，判定用**重建測試**：讀者只憑文中已給的材料能不能自己得出這一條，能是合格的壓縮、不能就是要求信任的裁決；重建測試同時暴露第二個問題——**斷言清單會把「缺材料」藏住**（「入口是自創行話」的證據是實際進入點程式碼、而那段程式碼根本不在文中，結論寫在那裡讓缺席的材料看起來不缺）；修法是**讀者位置的走查**三步：把讀者放到使用產物的位置（判定標準變成「資訊拿不拿得到」而不是「作者覺得好不好」）、每條斷言換成動作加材料（動作是讀者可以自己做的、材料是文中直接給的、結論由對照自己浮現）、可重用的檢查方式放在走完之後（浮現而不是被宣告）；走查的副產物是逼出缺的材料——第二步做不下去的地方就是文中該補而沒補的程式碼與對照；審查掛載在斷言支撐 frame、grep 曝光候選（拆開來看 / N 個毛病 / N 個問題）、判定靠重建測試，摘要位置的條列（前文已推導、條列是回收）與每條自帶證據的清單合規、規格參考型內容不適用；是 #254 灌輸那一半的段落層形態（同根因「結論與推導脫節」、兩卡出自同一篇文章連續兩輪修訂）、#242 的驗證材料版（那張給敘事材料讓後果可想像、本卡給驗證材料讓結論可重建、反面同構——純分類與純斷言都是只有結論的形式）、#244 同機制的另一面（換到讀者動作視角後原本不可見的缺席變得具體）；從一個「三個毛病」段落的兩版改寫抽出、修法有效性由提需求的使用者判定
- [#256 多份文件必然漂移：同步期待要嘛有機制承接、要嘛明示降級](doc-sync-needs-mechanism-or-demotion/) — 設計開發流程的文件鏈（proposal / spec / UC / 設計文件 / 追溯表 / 測試 / 註解）、或審查一套流程的文件模型時使用；**文件會不會漂移由「同步期待」與「守護機制」是否匹配決定、不由撰寫紀律決定**——同步對改程式的人當下零收益、收益結構決定它不會自發發生（Brooks《人月神話》的論點收斂成可操作形：多份文件的進度必然落差、有落差的文件最終沒人更新、方向是把文件併入程式）；修法是把每份文件分到三級——**活文件**（期待最新、必要條件是有機制守著：會紅的測試、編譯器、CI 比對腳本）、**scaffold**（只在被消費那一刻正確、要標記消費時點、過期不得被當權威引用）、**append-only 記錄**（史料、永不回改）——漂移只發生在「被期待最新、卻沒有機制」的錯配格、分級動作本身就是修法（給機制、或誠實降級）；第二條是**每類資訊指定唯一權威載體、其他位置引用不複製**（複製出去的每份都是不會被履行的同步義務）、行為的權威載體是測試（唯一改壞當下會發聲的那份、Brooks「併入程式」的現代形式）；含一次 TDD 文件鏈盤點的四個錯配實例（行為敘述四份副本、追溯表狀態欄是宣稱、設計文件無生命週期、回補機制單向）；是 #253 的文件層同構（不被機制守著的文件、同步需求同樣送錯窗口）、#245 的上游選項（那張給既有雙副本補機制、本卡說一開始就不要有第二份活文件）、#249 收益結構在同步工作上的應用、#221 宣稱與現狀不可區分的追溯表形態；從《人月神話》文件章 + 站內三個漂移實測 + 一次 TDD skill 文件模型盤點抽出
- [#257 軸名取了次好的代理變數，而正確的機制寫在括號裡](axis-named-by-proxy-not-mechanism/) — 一組判準讀起來都對、套到個案上卻分不開時，判斷問題是不是出在軸的名字；**判準失真最常見的來源不是機制想錯、是替它取名時選了較弱的代理**（識別碼之於預設行為、「做決定」之於存在性問題），而代理與機制分岔的那些情況正是判準要處理的難題。作者看不見是因為讀到軸名時腦中補的是機制、讀者拿走的卻只有名字。抓得到它的只有對抗性審查與個案實跑。
- [#258 軸是對的，而它底下有一個從未被當成選擇的實作前提](unstated-implementation-premise-under-a-correct-axis/) — 一套判準的推導每一步都成立、結論卻很費力時，判斷費力是不是來自沒寫出來的實作假設；**前提不是論點，因此躲得過所有針對論點的檢驗**——找反例、查來源、問支撐三者都預設要被檢驗的東西已經說出口。可辨識訊號是費力，而修法不是換掉前提、是先讓它顯形；顯形之後為了繞開它而長出來的結構會自己脫落。
- [#259 轉述與翻譯要保留語意強度量級](rewrite-preserves-claim-intensity/) — 翻譯、轉述或摘要他人材料時、判斷成品有沒有把原文的強度拉高或壓低；**強度是 claim 的一部分**——讚美量級（great 對 miraculous）、確定性（可能對必然）都在傳遞作者對 claim 的定位、量級改了讀者拿到的就是另一個 claim；可操作判準是**鄰詞存在測試**：目標語言存在更強的專詞而原文沒選用、代表原文刻意停在較低量級（日文有「奇跡」、日文版選「素晴らしい」、中譯寫「奇蹟」就是替來源句重做它明確沒做的選擇）；分流看**責任對象**——保真轉換（翻譯 / 轉述 / 摘要 / 引用）對原文負責、量級鎖定；宣告過的再創作與原創文案（標語 / 行銷）對訴求效果負責、量級是設計變數、「創造奇蹟」在原創標語裡是合法選項——分辨能力比禁令有用、混在一起會在保真情境放行超譯、也會在創作情境誤殺有效標語；根因是文體先驗接管——孤立短句、無上下文時、轉換者往目標文體的典型樣貌滑（中文行銷語「創造奇蹟」比「做出很棒的東西」更像 slogan）；鏈式轉換（翻譯的翻譯）漂移逐段累積、查證回最上游語言版本；是 #109 概念角色軸之外的量級軸 sibling（兩軸正交、一個譯名可以只錯一軸）、#161 摘要模態軸在跨語言轉換場景的對應（共享「成品比原文更有力就是失真訊號」）、#111 自產口語誇張的轉換端對應、#107 雙錨點是量級對照的前提；從一句登入頁標語的英→日→中三段轉換鏈抽出
- [#260 誇飾的合法性由段落位置的功能決定](hyperbole-legitimacy-by-position-function/) — 審查或閱讀時撞到誇飾、疑似超譯或強度異常的用詞、判斷它是合法修辭還是失實訊號；**判斷單位是段落位置的功能、以文件或文體一刀切兩個方向都會錯**——兩軸定位：文體契約（讀者預期字面還是修辭）× 行動耦合（讀者會不會依這段文字行動）、交叉出誇飾自由區（slogan / 詩）、管制邊界區（廣告誘導購買、界線可參照法律上的 puffery 概念）、有限使用區（教學 hook、進判準段要收）、零容忍區（規格 / SLA / 判準段 / 翻譯 / 安全陳述）；同一份文件內合法性會分區（README tagline 可誇、feature 清單零容忍）；**誇飾最危險的是中段強度**——強到失實、又沒強到讓人識破（荒謬級自我拆穿反而誠實）；接收端兩個可操作判準：**支撐存在測試**（強度詞旁有無機制 / 數字、「快 10 倍 + benchmark」是宣稱、裸的是誇飾佔位）與**反比操縱訊號**（強度與可驗證性反向、越難驗證話越滿、是推銷與詐騙話術的結構特徵、警惕等級最高）；**降格同樣失實**——強度的要求是對齊而非壓低、RCE 寫成「可能造成一些影響」跟 great 譯成「奇蹟」是同一種失真的兩個方向、incident report 的降格讓應變者依錯的緊急度行動；是 #259 生產端量級鎖定的接收端互補（責任對象分流拆到段落層）、#111 判斷工具型 vs hook 界線的機制化（兩軸解釋界線為何在那）、#161 降格方向的升格版判準、#100 安全陳述位誇飾即 false sense 入口、#152 必然性框架落在零容忍區；從一場「什麼情境誇飾合理、什麼情境該警惕」的框架討論抽出、落地為 auditing-articles 的強度對齊 dimension

- [#261 語句要在它的消費單位內資訊自足](sentence-self-sufficiency-by-consumption-unit/) — 寫或審查會被抽離消費的句子（checklist 項、表格格、判準句、給 LLM 讀的規範）時、判斷句子的資訊量夠不夠；**自包含義務由消費單位決定**——單句消費位（設計上會被單獨抽離的句子）必須句內自足、敘事位可依賴鄰句、壓縮合法；**資訊充足是正向規格四條件**：命題完整（主詞 / 謂語 / 對象 / 條件在場）、指涉閉合（殘片名詞有完整形先行）、實詞可反推（沿用 #111 精度判準）、一句一命題（對仗的每個半句能獨立判真）——負向禁令（「避免為美感犧牲資訊」）以模糊審美為軸、LLM 執行時只能用造成問題的同一個文體先驗去定義違規、正向規格才有梯度；驗收是**抽離重讀**（句子單獨給沒讀過上下文的消費者、命題能不能無歧義復原）；放大條件是中文單字多義 + LLM 三種消費模式（單行檢索 / attention 稀釋 / 風格繼承——壓縮到產生歧義的規範文字會在生成下游重演 #259 的漂移機制）+ 人類跳讀；是 #108 名詞頭義務的句子層推廣、#111 精度判準的成分完整度延伸、AGENTS 原則四 / 八「形式吃掉資訊」家族的字句層成員；從一條 checklist 項的兩版對照（壓縮重述由 Round 1 audit 修正自己引入、篇章層冷讀未見、審查流程外的讀者以抽離重讀抓到、修正後總長不增）與教學文章「簡潔到辨識不出議題」的佐證觀察抽出

- [#262 內容超出容器時擴充結構、不壓縮內容](content-pressure-resolves-by-expansion-not-compression/) — 寫作時判準裝不進表格格、概念裝不進標題、範例讓段落過長、想裁內容遷就容器時讀；**合法出口都在結構層**——就地展開（延伸段、本篇專屬內容）、拆卡外部化（跨篇可用的支撐 / 背景概念、範例寫進卡片、文章引用卡片承接論證）、或換成連結（概念已有卡或專章承載時刪掉格內自撰的 gloss）、壓縮內容遷就容器在出口之外；**選出口前有一個前置檢查**——同一個概念在兩篇以上有互不相容的定義時先收斂單一權威載體（三個出口都會把矛盾保留下來、機制見 #245）；機制是生成端的**容器形狀先驗**（標題 / 表格格 / 段落有學來的長度帶、內容被裁去符合容器的預期形狀、因果方向反了——歸因停在可觀察的輸出分布）；反模式命名**簡報式文章**（標題句化、表格當主體、格內殘語、條列連綴——簡報的正當性來自講者在場補完、文章沒有講者）、判定看消費單位不看表格密度（checklist 逐項執行、查表型段落——判讀徵兆表 / 關係表——逐列查詢、表格形態都合法；違規的精確形態是承載推導的內容被塞進表格、推導句從正文消失）；邊界：拆卡對象限支撐與背景概念（主線術語行內展開的既有規則優先、外部化會斷論證線）、擴充的對象是結構不是句長（句層歸 #261、metadata 歸精簡規範）、拆卡淨收益待試點驗證（搜尋落地讀者受益、順讀讀者付跳轉成本）、內容自身冗餘或過時時刪除合法（觸發源是內容性質、跟容器形狀無關）；是原則四「表格不是終點」的第二出口與機制補完、#261 的容器層 sibling（表格格是兩卡交會點）、#149 兩步驟分工在文體判定的應用；從容器形狀先驗的輸出觀察與 backend 章節「簡潔到辨識不出議題」的使用者判定抽出、經 WRAP 完整評估後帶邊界落地

- [#263 同一個對象被兩篇各自分解一次時，不相容會長得像互補](incompatible-decompositions-look-complementary/) — 兩篇平行章節各自給同一個對象一套階段表、欄位組或責任清單時、判斷它們是分工還是衝突；**判準是雙向對映測試**（兩套的成員能不能互相對映完整、不能就是不相容）加**動作測試**（讀者會不會為這件事做同一個動作兩次——一篇的產出是另一篇的輸入是互補、兩篇是同一個動作的兩份指示是衝突）；互相連結、語彙不同、各自宣稱處理另一半都不是分工的證據；**機制是平行發明**——要填一張表就要有一組成員、成員在填表的當下就地被造出來（#262 容器形狀先驗的後果）、而「去查別篇是不是已經分解過」不在寫作流程裡（流程的檢查單位是本篇）；**修法是選單一載體**——判準完整度決定哪一套內容留下（殘缺的那套當載體會把殘缺擴散到每一處引用）、引用數只決定住址搬不搬（它承擔遷移成本、不是品質、而且要數指向那組成員的引用不是指向那一頁的）、同一對象已有卡時卡通常是住址、**兩套各有對方缺的成員時載體要先補齊才有資格當載體**（收斂不是挑一套刪掉另一套、補齊時檢查新成員的名字在載體上有沒有被佔用的近義詞）、非載體那篇沿用載體語彙並重新界定 scope（保留它獨立的那一面、剩下不足以成篇才併篇、只留路由殼是最差結果）、載體補反向指標；**計數只算同層的住址**（不同層的分解對齊語彙而不收斂、混算會讓收斂範圍多出不該進去的對象），而搜尋的對象是「宣告一組固定成員、要求逐項填寫的段落」不論它排成表格、清單或散文（第一版寫成「掃表格」而實測住址全是清單、方法把載具形式當判準）；誤診成 #245 漂移的代價是「同步」會把兩份各自完整的分解合成兩邊都不像的第三套（平行發明沒有共同起源、時間順序不提供資訊）；是 #44 在「分解方式」這個對象上的形態（一組成員的住址）、#246 的另一端（零個住址對兩個住址、偵測動作同為跨篇並置）、#162 的邊界對照（那裡兩套術語並陳合法、這裡並陳等於把選擇丟給讀者）；從同一個資安模組的三組實例抽出、橫跨三種住址組合（章對章的成熟度階梯與資產類別、章對卡的證據包欄位、卡對卡的術語分工）；原本補上的第二個實例（例外協議）後來被對抗性審查判定為粒度與層級差、降級成判定的邊界示範

- [#264 規則用數量當門檻時，先問那個數量在代理什麼判斷](count-threshold-is-a-proxy-for-a-checkable-judgment/) — 訂規則時想寫「累積 N 個再做 X」的當下，分辨這個 N 是證據本身（重複出現就是證據，留著）還是某個判斷的代理（用數字頂替可直接檢查的事，換掉）；代理型門檻在維護者角度成立、在使用者角度失效，因為門檻跨過之前那段期間，有人正在承受這條規則本來要解決的問題

- [#265 查不查的判定要在查之前做完](query-restraint-must-precede-the-query/) — 要為一批事實跑外部查證（書目、規格、來源核對）、而查證有配額或時間成本時讀；判定只有一個問題「這個事實查不到的話成品會少掉什麼」，答案是可以直接刪的修飾語就不進查詢佇列；成本結構不對稱——判斷承不承重是免費的、查證有成本、而**查了以後沒用進成品的那些不留下任何痕跡**，所以事後檢討看不到這類浪費、配額耗盡是唯一訊號而它抵達時已經來不及；三個具名反模式是查了才判斷要不要用、查不到就換關鍵字再查一次（而上一次結果裡已經有可以直接抓的連結）、把被擋住的便宜工具靜默換成昂貴工具而不記下可靠度降級

- [#266 可核對的錨要跟它該偵測的狀態連動](checkable-anchor-must-be-able-to-fall/) — 要為一批自己做的判定補一個作者以外可核對的東西時讀；它的價值在該偵測的事情發生時會不會動，會下降只是連動的一種形態，而飽和的覆蓋率只偵測得到新增漏寫、關鍵詞計數量的是措辭不是判定

- [#267 入口由違規形態寫不寫得成 pattern 決定，佔比只決定能不能原樣進清單](keyword-list-needs-dominant-violating-sense/) — 某條用詞規則已經有 grep 清單、而漏抓的實例持續從外部指正進來時讀；入選判準是那個詞的違規義項佔它全部用法多少，比例低的擴充進清單只會用噪音蓋掉訊號，要改用探針

- [#268 要維持當期的內容，只能放在更新到得了讀者的載體上](current-content-needs-a-carrier-that-reaches-readers/) — 某一類判定怎麼做都會過期、而直覺是把判定做得更細時讀；**判別是兩問而不是一個變動速率的比值**——第一問「這段內容的正確性會不會隨時間失效」（最快的訊號是問這一段的主體是規則本身、還是讀規則的方法；訊號有兩處會漏：規則的結構本身改變時讀法會一起失效，另有一類是世界狀態的觀測值、兩邊都不屬），第二問「這一份到讀者手上之後有沒有一條會被實際走完的更新路徑」（再拆成有沒有人負責維護、維護完到不到得了讀者；路徑分沒有／弱／有三格，而「印出來就等於沒有路徑」是特定出版形態的實情、不是印刷品的本質——活頁加替換頁訂閱與推送修訂的線上版都是為這個問題長出來的）；**比值算不出答案是拆成兩問的理由**——書的改版與稅制修正都以年為單位、比值接近一，改用讀者手上那一本去算則每本書都失衡、連過時的語法示範都被掃進來；兩問給四種處置——照寫、落回 #256 分級、自建承接者、路由，而**判定的單位是「這段內容加上判定者手上所有可用的載體」**（改不動的常常只是引用來源那一層，做判定的人往往握有一個改得動的載體；選擇不自建的理由是維護成本與職責範圍、要明講，不能寫成載體不允許），外部也找不到承接者時明說沒有可指的承接者本身就是一則判定；往上產出範圍規則——以當期值為主體的內容不進這個載體，理由要註明是載體而非品質；四個反模式是把載體問題當判定深度問題、把有人維護的內容複製到沒有更新路徑的地方、用「以撰稿時為準」的免責換取照寫、不適用的維度留空（空白與「查過而沒有依賴」長得一樣，而跳過那一側會讓覆蓋率統計往好的方向錯）；是 #256 的邊界限定、#104 與 #118 的一般化（三張卡是同一條判準在三種更新路徑上的三個出口）、#262 的另一軸、#263 的上游、#170 的上位形式；從一次書單規劃中「稅制該判定到什麼強度」這個問錯層級的提問抽出，另有 #104 / #118 兩個站內獨立到達的實例；**限制寫在卡上且第二項最重**——三個實例分不出「有人維護」與「到得了讀者」各做了多少工，而三個實例的進入條件都是「錯配後來被辨識出來」，因此說明得了形狀、說明不了發生率
- [#269 舉證要求會把誠實的那個輸出定價成最貴的，檢查梯度指向哪裡](evidence-requirement-can-price-out-precision/) — 一條規則已經要求判定留下依據、而執行者仍然寫得含糊時讀；**判準是把規則產出的三種輸出排一次價**（誠實而具體的、含糊的、乾脆不寫的），最便宜的那個會變成預設而規則攔不住；價格不只是字數——降級標記是對具體收的稅（把判定的可信度掛在措辭上，等於讓作者靠寫粗換分級），要填的欄位是對承認不知道收的稅（「未評估要寫出未評估的是哪一項」比「未評估」貴，而比兩者都便宜的是不提那本書）；修法是把成本挪走而非放寬標準——分級的輸入從措辭換成來源（標通讀／章節摘要／第三方評述，無標記視為未密讀），誠實標籤的填寫成本降到不高於沉默；四個反模式是把降級掛在措辭上、只加要求不看梯度、用欄位懲罰承認不知道、逐條補限定句；**是 #243 的補集**（#243 管沒有痕跡要求的規則、沿零後續結論塌陷，本卡管有要求而定價錯的、沿含糊塌陷，兩者修法方向相反），是 #266 的上游、#264 的同型提問、#239 的同機制不同層；從一次書單分類第四輪誤用審查的十一項裡、方向與其餘九項相反的那兩項抽出；限制是兩個實例同批同作者同輪，說明得了形狀、說明不了發生率

- [#270 敘事的解碼材料要在讀者已讀的文本裡，不在作者的地圖裡](decodable-from-text-already-read/) — 教學敘事出現不具名的指涉、只給一面的對比或留給讀者自推的結論時讀；**判定問句逐句可執行**——讀者線性首讀讀到這一句、能不能當場復原完整命題（指涉的對象是誰、對比的兩面是什麼、結論的操作含義是什麼），復原不了的那一項就是被壓掉的解碼材料；機制是生成端的**語域混入**——作者持有全篇地圖、文學化壓縮（位置指涉「前兩本 / 另外兩本 / 這一側」、轉喻代替命名、單邊對比、隱式結論、名詞化主詞、破折號懸念）全部預設讀者共享這張地圖，書評體的密度審美在教學內容裡把成本轉嫁給線性首讀的讀者；**位置與數量指涉連作者自己都維護不出正確值**——實例的「前兩本」實指第一與第三個條目、「另外兩本」實為三本、另一章的「另外三本」實為四本，同一篇三次計數三次全錯，位置與數量是排列的 derivation、只在作者地圖上成立（#155 的篇內形態、且不必等結構重排就錯位）；極端形態是**跨頁位置指涉**（「該篇的起點書」——綁定在另一份文件裡、讀完本篇也解不開）；修法是指涉具名（首次全名、位置數量詞出現時順手驗計數）、對比補全另一面、結論寫到讀者能決定下一步動作的層級、具體實體當主詞、並列定義各自成段、旁註移到主線走完之後；展開的**價格依反模式類型分層**——具名替換是代換不加字、補全對比與隱式結論才花字數，實測隱式結論密集的導言多兩成、位置指涉為主的全篇只多百分之五，最高頻的違規恰好是最便宜的修法；命中是候選不是判決——向後近距回指、下半句立即揭曉的破折號、「」內引用都合規、判定只看解碼材料（綁定）在不在已讀文本裡、同一個角色詞可以在定義它的篇內合法而在跨頁處違規；是 #261 敘事位豁免的方向限定（可依賴的是已讀的鄰句）、#155 的篇內 sibling、#254 之外另一種借來的語域（演講姿態之外的書評體壓縮）、#210 的相鄰壓縮對象（那卡壓推導、本卡壓解碼材料）、#262 家族的另一個壓縮動機（密度審美、無容器壓力也發生）；從一篇書單導言的兩版對照抽出——LLM 原稿與使用者改寫版命題集合幾乎相同、差異全部落在解碼成本的分配上、改寫版被指定為風格基準；限制是單一實例單一文體、唯位置指涉的雙重數錯由機制推出、不依賴樣本數

- [#271 收錄取捨的結果進正文，判準運算不進](inclusion-deliberation-is-editorial-not-content/) — 策展型內容（書單 / 精選 / 系列）的條目裡出現「按某判準仍不到否決」「雖然有缺點仍收錄」這類句子時讀；**條目交付三種東西**——取捨的結果（不設定為起點、不收某類）、讀者要用的可信度標註（未通讀 / 反推 / 當線索用）、對象本身的判讀，取捨的**運算**（依哪條判準、離否決多遠、為什麼仍收）是編輯後台、屬編輯筆記與 commit message；判定問句是**行動測試**——這句刪掉後讀者「怎麼讀這個對象」的行動變不變、不變就不進正文；機制是判準框架的詞彙（判準 / 否決 / 門檻）既是編輯工具也是正文詞彙、運算句穿著正文的衣服，寫進去的動力跟 #243 的留痕同源、而痕跡的家在編輯筆記；**第二維度是決策寫成決策**——「當不了起點書」把書單的設定偽裝成書的能力上限、改成「不把這本書設定為起點書」（#268「選擇不能寫成載體不允許」在策展寫作的同構）；邊界兩側有實測——可信度標註留、收錄邏輯集中在「為什麼只收這幾本」專節合法、刪運算句前檢查夾帶的讀者資訊（讀法指引先搬再刪）；是 #230 的 sibling（動機在引言 / 運算在條目、同屬 process metadata 不進 content）、#141 同族的第三個 surface、#243 的位置限定、#170 的正文層對應；從一份書單條目的使用者修訂抽出、理由原話「讀者不需要知道我們寫這篇的決策」；限制是單一實例、「可信度標註留運算刪」的分線在其他策展文體未驗證

- [#272 教學內容不預設考核情境，檢核動詞用識別與應用的動詞](verify-by-recognition-not-recitation/) — 教學文字用「說得出 / 答得出」檢核讀者或團隊的能力時讀；**「說得出 / 答得出」預設一個考核情境**——有問的人、答案要被說出來給人聽——而讀者為吸收知識而來、實際活動是自我評估理解與應用，文章的定位是建立識別能力與應用能力、檢核動詞就用那些能力自己的動詞（識讀 / 辨別 / 指認 / 列得出 / 查得出 / 判斷得出 / 對應得出 / 追得出 / 算得出 / 重建得出——按被檢核的能力選、一律替換做出新模具依 #122）；判定問句是**這一句描述的情境裡有沒有真實的問方與言說行為**；三類合法保留——場景內真實對話（稽核 / 客服核身 / 會議追問 / 通報）、協定與查詢語意（DNS 回答查詢、稽核日誌可查——主詞是系統時「答不出」多半該寫「查不出」）、表達載體（名稱 / 註解 / 型別 / 錯誤訊息的本職是承載陳述）；自查問句框架合規、要看的是收尾的「答不出來就 X」；機制是教學者的職業慣性（教學現場以考核驗收學習、出題是驗收理解最順手的框架）由生成端從語料繼承；是 #254 / #270 之後借來的讀者框架家族第三個成員（聽眾 / 地圖共享者 / 受試者）、#234 一般化判準的情境版（「答得出」照字面需要一個對答的場）、#255 同方向（把讀者移回使用產物的位置）、#220 自查問句的收尾補充；從一句讀圖檢核句的使用者修正（說不說得出→能不能識讀）加全站掃描抽出——196 處命中、修約 100 處、保留 53 處，密度最高在檢核句密集的文體；限制是單人一輪判定、三類合法清單從這一批歸納

**Last Updated**: 2026-08-21（六）— 新增 #272 教學內容不預設考核情境，檢核動詞用識別與應用的動詞。從一句讀圖檢核句的使用者修正（「說不說得出」→「能不能識讀」、「答不出來」→「如果無法辨別」）與隨後的框架指正抽出：把知識預設為被拿來考核的用途並不理想——讀者為吸收知識而讀、實際活動是自我反省與評估理解、對答情境不存在，文章的定位是建立識別能力與應用能力。全站掃描 196 處命中（books 線先前已掃）、逐處判定修約 100 處：識讀 / 辨別（讀圖）、指得出（隔離需求、防什麼）、列得出（回復路徑、角色權限）、查得出（觀測資料、稽核日誌、憑證清單——「系統答不出」改「查不出」的精度差一併修）、判斷得出、對應得出（權限對動作、彙總問題）、追得出（接線路徑）、算得出（du）、確認得了 / 重建得出；保留 53 處合法——場景內真實對話、協定與查詢語意、表達載體，加上 #254 的條件句模板與自查問句框架。反向指標補在 #254（家族第三成員）、#270、#234（情境版實例）。compositional-writing v0.72.0 同步。

**Last Updated**: 2026-08-21（五）— 把三輪使用者逐字修訂累積的文法層修正回填 #234 與 #270。**#234 判準一般化**：原本只有物理化錯配有機械判準（照字面成立需要什麼物理條件），一般化為「問這個謂語照字面成立需要主詞或賓語具備什麼屬性」——擬人化要主體條件（判定沿轉喻鏈：「作者自述 / 課程頁自陳」合法因為主體在鏈上、「書自述」違規；全站 24 個檔案的第一方出處標記差一步被誤殺、由分佈掃描收手）、新增第四種**範疇錯配**（命題配存在謂語、「在＋人＋這裡」處所框架——實例是四頁共用 gloss 把權威定義的「組織」代換成「讀者」而沒換謂語，錯配是代換的殘留）；「自 X」動詞補極性軸（第一方訊號正面宣告做工、否定句不做工）。**#270 補兩條修法細節**：回指剛提過的對象用近指「這些」（「那幾條」遠指配近距先行詞、又多宣告一次計數）；對比的軸要寫明（二字對舉「有無 / 程度」壓住兩個不同性質的軸、展開成「有或無 / 程度上的高低」——二元寫成選言、量軸寫出刻度）。compositional-writing v0.71.0 同步兩張 principle 卡與 SKILL.md。

**Last Updated**: 2026-08-21（四）— 新增 #271 收錄取捨的結果進正文，判準運算不進。從窮查理條目處境相容性段的使用者修訂抽出：原稿以「按處境相容性的判準這仍然不到否決」收尾、把收錄門檻的權衡過程寫進條目，使用者整句刪除、理由是「讀者不需要知道我們寫這篇的決策」。同一次修訂示範了邊界兩側——留下可信度標註（「書裡沒有明說、同屬待驗證的線索」）與收錄邏輯專節、刪掉條目內的判準運算；並把「它當不了起點書」改成「不把這本書設定為起點書」（決策寫成決策、不寫成書的能力上限，#268 同構）。判定工具是行動測試：這句刪掉後讀者怎麼讀這個對象的行動變不變。修法 5 記下被刪句夾帶的讀法指引已由條目其他段落承載、無資訊損失。反向指標補在 #230（sibling、新 surface）與 #141（同族第三個 surface）。skill 側未動——#230 / #141 這一族本來就只住 report 層。

**Last Updated**: 2026-08-21（三）— #270 補名詞化主詞的高頻子型：**框架欄位名滲進句子當主詞**。使用者對「讀得出價值的前提幾乎沒有」的修正揭露——用固定欄位組寫作時（本例是書單的四項描述框架），欄位名會直接被拿來起句當主詞；修法是被描述的實體當主詞（「這本書幾乎不需任何前置作業」）、欄位對應由內容自己承載、標籤不必在句子裡現身。同一句的後半是隱式結論又一例：「適合分段讀而非通讀」是抽象讀法標籤、讀者拿不到行動，展開成「不需要通讀，即使只讀其中一個章節都會有幫助」。同批把該篇其餘三處欄位名起句（「讀得出價值的前提在兩本上不同 / 是讀得懂資產負債表 / 是本篇最重的一項」）一併改成實體主詞。compositional-writing v0.70.1 同步。

**Last Updated**: 2026-08-21（二）— #270 補第二批證據：同一篇文章其餘七個章節依卡上判準全篇改寫，共修約 15 處、位置指涉一類約 10 處佔比最高。三項新內容回填進卡：(1) 計數錯誤第三例——「另外三本都不碰」實為四本，同一篇三次計數三次全錯、分佈在兩個章節；(2) 位置指涉的極端形態**跨頁指涉**——「該篇的起點書」的綁定在另一份文件的第一個章節裡，讀完本篇也解不開，修法同為查證後具名；(3) **展開的價格依反模式類型分層**——具名替換是代換不加字、補全對比與隱式結論才花字數，實測導言（隱式結論密集）多兩成、全篇（位置指涉為主）只多百分之五，最高頻的違規恰好是最便宜的修法、「展開會讓文章膨脹」不構成保留壓縮的理由。另補「同詞兩判」的邊界實例：「起點書」在定義它的篇內向後回指合法、跨頁處違規——掃描抓詞面、判定看綁定位置。發生率宣稱仍限單篇、分佈形狀在別的文章要重新量。compositional-writing v0.70.0 同步。

**Last Updated**: 2026-08-21 — 新增 #270 敘事的解碼材料要在讀者已讀的文本裡，不在作者的地圖裡。從一篇書單導言的兩版對照抽出：LLM 原稿兩段約 320 字、命題完整而讀法緊湊，使用者改寫版字數多兩成、命題集合幾乎相同，差異全部落在解碼成本的分配——原稿的每一個壓縮手法（「本主題前兩本」「另外兩本」的位置指涉、「判斷者這一側」的轉喻、「留下文字的都是重現成功的那些」的單邊對比、「要分開的是評估它們的證據，不是決定本身」的隱式結論、並列定義擠單段），改寫版都有一個對應的展開動作（具名書名、直說角色、補全對立面、把操作含義寫出來、一段一命題）。最硬的證據是原稿的位置指涉自身數錯兩次：「前兩本」實指篇內第一與第三個條目、「另外兩本」實為三本——位置與數量是作者腦中地圖的 derivation、連作者自己都維護不出正確值，這一點由機制推出、不依賴樣本數。反向指標補在 #261（敘事位豁免的方向限定）、#155（篇內實體指涉的 sibling）、#254（另一種借來的語域）。同批把該篇導言依改寫版落稿（書名填實）、compositional-writing v0.69.0 新增同名 principle 卡與原則三對應段。新增場景導讀路徑 48。

**Last Updated**: 2026-08-18（二）— 對收斂本身跑三輪審查（九個 reviewer、frame 全換成對著重組動作而非內容的），十六項 finding 全落在紀錄層、沒有一項落在收斂的決定上——載體選對、內容併對、雙向對映的自我驗證也做對，錯的是「怎麼找到要收斂的東西」與「怎麼記下為什麼這樣選」。**根因在 #263 記的搜尋方法**：它寫成「列出所有帶表格的章節與卡」，而六個欄位住址實測全是編號清單、沒有一個是表格。方法從最早那幾個恰好用表格的實例歸納，把載具形式當成了判準，照它跑會漏掉全部。條件改成「宣告一組固定成員、要求逐項填寫的段落，不論排成表格、清單或散文」。**漏掉的是 7.18**（八個檔案連進去、標題直接宣稱交接主題），而它有一項載體沒有的成員（該輪任務的完成條件，與風險邊界的停止條件不同——一個問何時結案、一個問何時中止），所以「載體要先補齊」在第四處立刻用了第二次，載體補成八項。補的時候沒沿用原名 `Exit condition`，因為例外那組已有 `exit criteria`，照抄會把同名異義搬進唯一的住址——新規則：**補齊載體時檢查新成員的名字在載體上有沒有被佔用的近義詞**。**兩組住址數各錯一次而方向相反**：交接漏算（上述）、例外多算（治理章五責任被算進同層集合，而它是不同層——同層才計數、不同層對齊語彙而不收斂）。**「入連數最高」實測為假**（治理章十五、卡九、協議章六），錯在量測單位——入連數量的是整頁被引用幾次，而要選載體的對象是頁裡那張欄位表；判定步驟第一條（先對齊粒度）要延伸涵蓋整個修法而不只判定。另外：7.17 的可套用模板宣告六欄實給五欄（缺席之所以存活，是同名異義加三個物件混排讓缺的那欄看起來在席）、7.B1 與 7.18 的欄位段結尾同骨且帶位置式引用、「至少要填其中 N 項」把下限變成配額而省略判準全站未寫（補上三種可省的理由，並標出主責角色與完成條件幾乎不落在判準之內）。#42 補回指——2 次門檻的計數會倒退，這張卡的證據史就是實例，而 #42 原本把「已達 2 次」寫成到達後固定的狀態。修法過程自己踩到兩次同型錯誤（規則寫得比實際情形窄：先寫「完成條件三處都要填」再寫「對地圖不適用」、省略判準只寫了三種理由裡的一種），與根因的搜尋方法同機制——從手上正在看的那一處歸納出要涵蓋三處的通則。

**Last Updated**: 2026-08-18 — 第二人分診找出的兩組不相容分解都收斂完成，過程給了 #263 修法側的第一份證據（該卡原本只有判定側的證據）。**例外紀錄**的載體判給知識卡（欄位定義本來就是卡的責任）：卡把六欄各自的判準寫開，填寫協議那一章保留六欄在文內（讀者要逐項填、依冷讀的結論不能只給連結）但把定義權指回卡，治理那一章的五條責任重新界定成「誰要確保什麼」並逐條標出對應欄位——第四項（掛 tripwire）明寫沒有對應欄位，因為 tripwire 是並列物件而不是六欄之一。收斂順帶修掉一處異名同義：卡寫 close criteria、章節寫 exit criteria，而全站其他四處都用後者。

**交接欄位**的收斂產出一條新的操作規則。載體本來要判給模組路由那一章（交接的定義處、六項最完整），而對映時發現兩套互不為子集：載體缺「主責角色」，那一項只有控制面地圖有。所以載體先補齊成七項才有資格當載體，控制面地圖再沿用同一組名稱、只留它獨有的那一軸（控制面歸屬決定主責是誰），設計輸入那一章的交接物格式也指向同一份模板。規則寫成：**收斂不是挑一套刪掉另一套**——兩套各有對方缺的成員時，載體要先補齊，否則收斂會丟掉內容。這條已寫進 #263。

07 backlog 兩列除籍（19 → 17）。

**Last Updated**: 2026-08-17（十二）— 第二人分診量測完成，#262 的「分診程序可推廣」這個宣稱現在兩半都有數字。同一批 29 列交給另一個執行者獨立跑（協議寫在指示裡、禁讀 #262 與 skill 以免看到第一位的結果），逐列一致率 **25/29（86%）**，而四處分歧不是隨機落點：三處的方向相同——第二位判「先收斂載體」、第一位判了別的，而三處都成立。成因是協議缺口：**換成連結與先收斂載體在外觀上無法分辨**（兩者都是「這個概念別處已經有了」），差別在目的地那一套與本篇是不是同一個切法，而第一位在那幾列只確認了目的地存在、沒有把成員並排。補的動作寫進協議：判換成連結之前打開目的地比對分解；少了它，誤判方向永遠偏向連結。這次量測順帶產出 #263 的兩個新實例，都驗證成立：交接要填什麼在三處各有一套（設計章的 routing sheet、模組路由章的六項交接模板、控制面地圖的兩個 target 欄位），例外紀錄有四套（放行章自列四項、例外協議章六欄、治理章五責任、知識卡六欄）。兩者已登記進 07 backlog 並指出候選載體。第四處分歧是主線與支撐的邊界，兩位用的判準不同（論證承重測試對權威歸屬測試），由前一輪的冷讀斷開——讀者要逐項消耗的列舉該就地展開，所以承重測試在這個問題上比權威歸屬準。第二位另寫出一條排序規則收進協議：論證承重壓過跨篇重用，兩者都後於前置檢查。compositional-writing v0.62.0。

**Last Updated**: 2026-08-17（十一）— 獨立冷讀跑完，#262 掛著的那個問題（外部化對搜尋落地讀者是收益還是成本）有答案，而答案比原本的保守邊界精確。執行方式是把三篇改寫後的章節交給一個不知道審查脈絡的讀者、禁止它讀原則卡與 skill、給三個帶著具體問題的落地情境。結果：三篇合計約 56 條對外連結，判定「不點就接不下去」的只有 6 條（11%），其餘 50 條（16 張知識卡、判讀訊號表右欄的跨章路由、案例引用）全部可選——支撐與背景概念的外部化因此得到支持。而那 6 條必須點的全是同一種東西：**本篇的程序要逐項消耗的列舉被放在別處**（資產類別六類、證據包八欄、每類要驗什麼、階段名）。翻轉點寫成判準：被外部化的內容若是程序要逐項消耗的列舉，連結不能取代它——列舉留在本篇、定義才留在卡。這條與 #262 的第三出口衝突過一次，而衝突實例來自試點自己：Round 3 依第三出口把兩處「連結齊備而 gloss 也齊備」的重述刪成純連結，冷讀者隨即在那兩處被迫跳出去；分界是**重述**與**列舉**，第三出口的適用條件因此限縮到 gloss。冷讀另指出一個隱性前提：外部化的收益依賴目的地的語域一致——它兩次被帶到未改寫的樣板頁面（開頭「本篇的責任是」、結尾「完稿判準」）後判斷「這不是給我讀的」並退回，而落地讀者對連結的信任是一次性的。這給 07 那 21 篇樣板改寫排了優先序。據此修法：7.21 把三處被外部化的列舉收回文內（六類資產、八個證據欄位、交接對象改成具名角色而非模組編號）、7.22 的必備控制那節從三句外部化改成六列對照表、7.25 移除「階段名沿用」整節（冷讀點名它是最想關掉頁面的一段：帶著關不掉的例外清單進來、第二眼讀到兩篇文章之間誰定義詞彙）並把集合段的五條規則拆成分項。限制：冷讀由獨立模型執行、與作者不同源但仍同類，實際落地行為未驗。compositional-writing v0.61.0 同步。

**Last Updated**: 2026-08-17（十）— 兩張候選卡的全站反證跑完、結果一成一敗，而失敗那張的理由值得記下來。**成立**：「分母由被管理的那批自己列舉時，這個數字衡量的是管理範圍內的完成度、不是覆蓋率」這個定義在三章各寫一次而卡層無落點，反證確認鄰近的既有落點（一篇講網站統計母體的文章、以及 data completeness 卡）處理的是別的軸——前者問「漏掉了誰」、後者問「資料本身完整嗎」，都不是「誰列舉的」。已建 [覆蓋率與完成率](/backend/knowledge-cards/coverage-vs-completion-rate/)、7.5 與 7.25 改連卡。**不成立**：審查判定「宣稱層與生效層」缺卡，依據是三章各用一組本地名稱重述同一個區分（控制意圖對控制實作、證據對應機制對對應欄位、活動指標對能力指標）。反證推翻這個歸納——第一組是時點分工（設計階段只能給效果陳述、不能給產品，這是刻意的分界而不是宣稱與生效的落差），只有後兩組是同一個形態，而它們的共同形態已由 #232（查宣告 vs 查現形）與 #100（false sense of security）承載。建第三份分解正是 #263 要擋的事，所以那一列從 backlog 移除、只修真正的問題（7.22 的「流程層對實作層」與模組首頁的「實作層」撞名，已改成「關卡層對生產環境的實際狀態」並標明分別）。同批把 #262 的三個出口與 #263 的前置檢查升進 AGENTS.md 原則四（原本只有「就地展開」一個出口），並把 §6 完稿清單那條絕對句改成帶查表型豁免的版本。

**Last Updated**: 2026-08-17（九）— 三輪 agent 審查（九個 reviewer、frame 全換）對本批的修正，其中兩項改動了卡的內容而非措辭。**#263 的證據基礎重建**：對抗審查逐項核對原文後推翻原本的第二個實例——例外協議在一篇是五條治理責任、在另一篇是六個紀錄欄位，而後者沒有「觸發」欄位不是漏掉（它把 tripwire 提升成並列物件、自帶四欄協議），所以那是粒度與層級差、後果也弱一級（部分閱讀下的漏格，不是判讀結果失效）。若它是唯一的第二實例，整張卡立在 n=1 上。修法是換證據而不是護航：自我應用掃描與個案實跑另外找出三組——章對章的資產類別（設計章三類對發版章五類，而發版章明寫前者是預檢要對照的那一份）、章對卡的證據包欄位（兩章各重述七項而卡是八項）、卡對卡的術語分工（一張既有卡描述鄰卡時用了新卡實質否認的分類詞）。例外協議降級成判定的邊界示範（它示範「對映前沒對齊粒度會誤判成實例」），#42 那一列改寫成證據史。同批補對映測試的四種誤判形態（同名異義給假陰性最危險）與明示簡化出口（子集層與外部標準的固定分解不觸發）。**#262 的分診結論限縮**：原本寫「分診程序可以推廣」，實際只驗到程序對輸入敏感（同一人在兩批不同輸入得到不同分布），執行者之間的一致性從未測；第三出口另補一條已知偵測缺口——判定條件抓的是缺連結，而「連結齊備且 gloss 也齊備」不觸發任何檢查。審查另抓到三個機制值得記住：修法互相覆寫（一個 #156 違規在前一個 commit 修過、Round 1 重寫該段時又寫回）、規則升級沒回流到 skill（載體判準四處副本停在被推翻的順序，是 #245 的漂移發生在寫 #263 的同一批）、以及 skill 內兩份 reference 互相矛盾（Dimension 5 要求雙向連結，而 principle 卡明寫互連不是分工的證據）。skill 同批升版：compositional-writing v0.60.0、multi-round-review v1.32.0（G frame 補上「兩個住址」這一半）、knowledge-cards v1.6.0（落點站補卡層載體判準）。

**Last Updated**: 2026-08-17（八）— 新增 #263 同一個對象被兩篇各自分解一次時，不相容會長得像互補。第二輪試點把「跨章矛盾」記在 #262 與 #245 的段落裡之後，為了判斷該不該立卡而做了一次反例搜尋（對同一模組列出所有帶表格的章節、把鍵欄描述同一類對象的表並置），找到第二個實例：一篇把例外治理分解成五個責任、另一篇分解成六個欄位，雙向對映只有「關閉條件」單側存在——照五責任填的人不會產出可驗收的關閉條件，而那是例外治理最易失效的一格；兩篇互為必連、第三篇同時路由兩者，外觀完全是分工。兩個實例的 surface 不同（狀態分類法對欄位組），所以不是同一個 artifact 被數兩次，#42 的第二次訊號成立。卡的兩個判準是雙向對映測試與動作測試（讀者會不會為這件事做同一個動作兩次），並把「同步」與「兩套並陳」明確排除在修法之外——前者是 #245 漂移的修法（平行發明沒有共同起源、同步會產出第三套）、後者是 #162 的合法修法而在這裡等於把選擇丟給最沒有材料選的人。反向指標補在 #245 / #262 / #246 / #162。同批修掉上一輪殘留在篇目條目與路徑 45 的過度推廣句（「實測的出口分布裡這一類最多」）。待辦：7.14 與 7.17 的例外協議收斂已登記進 07 模組 backlog、本次未動稿。

**Last Updated**: 2026-08-17（七）— #262 拆卡試點第二輪：刻意挑一篇會反駁首輪結論的章節（同批樣板裡的組織與流程題材、主線概念在卡層零覆蓋），結果推翻了首輪「換成連結佔多數」的分布結論，並找出第四種處置。**新處置：先收斂單一權威載體**——該章自訂一套五階成熟度階段，而同模組另有一章定義四階、兩套切點不同（「可量測」獨立成一階或折進可稽核閉環），而該章的判讀訊號表還把另一章當成下一步路由，讀者帶著這一套的階段走過去對不到任何一格。這一類在 #262 原有的三個出口之外，因為三個出口都預設格內的內容是對的、只是裝錯容器；同一概念有兩個不相容版本時，展開會寫出兩套更詳細的版本、連結會把讀者送到用不同語彙描述同一件事的地方。修法：#262 結論段補前置檢查（收斂在選出口之前）並引 #245 為機制來源、#245 補反向指標（漂移在教學內容裡的形態是兩篇平行章節、不只是原則卡與操作文件那一組）、試點段改為兩輪並排並把分布明示為一次觀察而非預期值、compositional-writing v0.58.0 同步。改寫產出：7.25 收斂成節奏 / 角色 / 指標 / 回顧四段（回顧間隔的下限由沒有 tripwire 的那批治理物件的最短到期日決定、指標要標分母來源）、7.20 補階梯 SSoT 宣告與反向指標。

**Last Updated**: 2026-08-17（六）— #262 的拆卡試點首輪執行完成、產出一條規格修正：**增列第三個出口「換成連結」**。試點對象是資安模組裡相鄰且互為必連的兩章（設計輸入、發版關卡、同屬一組 24 篇共用樣板），改寫前對四張表 20 列逐列跑 #261 的抽離重讀、20 列全數判定資訊不足；依出口分診後的分布是換成連結 7、就地展開 4、外部化成新卡 1、補句內成分 8（查表型豁免延伸段）——最大的一類在試點前不在出口表上，因為它的觸發源是容器誘發的冗餘（表格三欄的形狀讓作者填一句自撰的 gloss，即使那個概念在同一個內容集合裡已有完整落點），與既有的「內容自身冗餘則刪除」不同源。同批產出 [Threat Model](/backend/knowledge-cards/threat-model/) 卡（量測於 commit ce7fa87d：全站約六十個檔案用到 threat model / 威脅模型 / 威脅建模，而十二個 knowledge-cards 目錄都沒有這個術語的落點。立卡當時寫的「二十餘處」是把一次 `head -20` 的截斷輸出當成計數；改成實測值之後 Round 4 又發現它在同一批之內就漂移了——分母是全站文字，每次寫作都在動它，所以這裡只留量級與量測點）、#261 的教學文章側觀察升級為第二實證（形態與原 case 不同：那裡卡在條件二的解壓成本、這裡是條件一的成分直接缺席）、compositional-writing v0.57.0。試點沒有回答跳轉成本的方向——冷讀對照由改寫者本人執行、與作者同源，因此全分類盤點仍未排、保守邊界維持。

**Last Updated**: 2026-08-17（五）— 新增 #262 內容超出容器時擴充結構、不壓縮內容。從 #261 的句層討論延伸到容器層：生成內容的標題與表格有固定構成模式、解釋被裁去遷就形狀、跟卡片盒筆記法「擴充文章與卡片、不節省文字」的設計哲學對撞。經 WRAP 完整評估：反向檢驗抓到兩個原提案沒擋的反例（過度拆卡是 Zettelkasten 已知失效模式、且會跟「主線術語行內展開」的既有規則對撞；「擴充優先」無邊界會被讀成全域加長、跟 #261「全域加長跟全域壓縮都是錯的答案」矛盾）、據此帶三條邊界落地；backend 全面盤點降級為試點後的第二階段（拆卡讀者體驗未驗證、資料不足不全面定案）。同批落地 knowledge-cards v1.5.0（內容壓力建卡觸發 + 範例入卡明文）、compositional-writing v0.55.0（原則一擴充優先段 + writing-articles 生成端自問句 + principle 卡）。反向指標補在 #261。

**Last Updated**: 2026-08-17（四）— 「命中是候選、不是判決」缺章候選的並置驗證結案：**不缺章**。前提的住址早已存在——#149（判定層：命中被合理化放行）與 #232（偵測層：clean 可信的前提是方法看得見違反形態）合為同一條管線的兩半、且 #149 已有六張卡直連；outbound reviewer 的「缺章候選」是錯誤的缺口宣告（全站掃描漏掉 slug 逐字對應的既有卡）、恰好印證 #232 家族「回報缺口前要反證」的教訓。修法：#149 ↔ #232 互補反向指標（兩卡原本互不指認）、#149 適用範圍補「兩步驟結構推廣到字句層之外的警告層偵測（lint 位置引用、量級檢查）」、#259 的候選判定句補 #149 錨點連結、multi-round-review v1.29.1 的 G frame 補「缺章宣稱要全站反證、預設處置是登記待驗證」。

**Last Updated**: 2026-08-17（三）— 新增 #261 語句要在它的消費單位內資訊自足。從 #259 / #260 的多輪審查過程中抽出：修法產物裡的壓縮句（「反比結構解釋不成無意」——同項已定義概念的壓縮重述）被使用者指出對 LLM 消費有歧義風險、而它正是 Round 1 audit 修正自己引入、Round 2 的篇章層冷讀 reviewer 未見——篇章層冷讀的顆粒度抓不到句子層、作者與同源 reviewer 帶完整 context 讀、殘片指涉對他們全部可回收。討論過程中使用者做了關鍵修正：初版把原則框成「資訊量優先於句式美感」、被指出「句式美感」是模糊審美概念、LLM 無法精準執行負向禁令——改為正向定義資訊充足的四條件、美感詞降級為判讀徵兆的候選訊號。同批落地 compositional-writing v0.54.0（原則 4 補行自足段、reference-authoring-standards 補單句消費位規範、principle 卡）與 multi-round-review v1.29.0（B′ frame 句子層顆粒度邊界）。反向指標補在 #108 / #111 / #259。

**Last Updated**: 2026-08-17（二）— 新增 #260 誇飾的合法性由段落位置的功能決定。#259 立卡後的延伸討論：超譯在翻譯是缺陷、在行銷標語是工具、寫作 skill 要能分辨並合理運用兩者。框架用兩軸（文體契約 × 行動耦合）取代文件級一刀切、判斷單位下沉到段落位置；接收端補支撐存在測試與反比操縱訊號兩個可操作判準；降格側明確化（對齊而非壓低）。同批落地 compositional-writing v0.53.0：auditing-articles 新增「強度對齊」audit dimension（兩軸四區 + checklist + 與 citation drift 三類的分工）、新增 hyperbole-legitimacy-by-position-function principle 卡、路徑 18 尾端補強度對齊。反向指標補在 #259。

**Last Updated**: 2026-08-17 — 新增 #259 轉述與翻譯要保留語意強度量級。從一句登入頁標語的三段轉換鏈抽出：英文原文「Build something great」、日文在地化「素晴らしいものを作りましょう」（量級對位、合格）、AI 中譯「讓我們製造一點奇蹟吧」（升格）。鄰詞存在測試給出可操作判準：日文有「奇跡」這個常用專詞、原文與日文版都沒選用、中譯把原文迴避的量級硬加回去。跟 #109 的概念角色軸正交（great 跟奇蹟類型相同、量級不同）、跟 #161 的摘要模態軸同族（成品更有力就是失真訊號）。卡內同時立適用邊界：量級升格是中性工具、對錯由責任對象決定——保真轉換鎖定原文量級、原創標語與宣告過的再創作以訴求效果為準（同一個「奇蹟」在中譯是超譯、在自家產品的中文標語是正當誇飾）。反向指標補在 #109 與 #161。同批把量級檢查層與鄰詞存在測試寫進 compositional-writing 的 translation-review reference（v0.52.0）、路徑 19 在 #109 之後插入量級層。

**Last Updated**: 2026-08-08（深夜二）— 新增 #256 多份文件必然漂移：同步期待要嘛有機制承接、要嘛明示降級。從「註解防不了改壞」延伸：Brooks《人月神話》指出多份文件不可能持續同步維護、落差出現後就沒人更新、方向是把文件併入程式——這正是 #253「防護需求交給會發聲的機制」的文件層同構。觸發是對剛從 skill 庫安裝的 tdd / spec 兩個 skill 做文件模型盤點、找到四個錯配：UC 場景被完整複製進種子包與設計文件（行為敘述四份副本）、traceability 的 covered 狀態靠人工改（宣稱與現狀不可區分、#221 形態）、Phase 1 功能規格沒有生命週期（實作完成後長得像權威規格、實際從 Phase 3 起漂移）、邊界回補只修 UC 不及於已複製的副本（回補反而擴大落差）。核心判準：文件分三級（活文件要機制、scaffold 標消費時點、append-only 是史料）、漂移只發生在期待與機制錯配的格；每類資訊指定唯一權威載體、行為的權威載體是測試。同批把紀律寫進 tdd skill 的 document-coherence reference（v2.1.0、含各 Phase 連貫性檢查點與註解判準）與 spec skill 的 feature-spec 生命週期標記（v1.6.0）、skill-sync 推回遠端庫。

**Last Updated**: 2026-08-08（深夜）— 新增 #255 讀者重建不了的斷言清單，展開成讀者位置的走查。從 #254 同一篇 work-log 的下一輪修訂抽出：「三個毛病」條列的三條結論都對、但正文只給了那行註解本身，讀者無從驗證「入口」在程式裡存不存在——只能硬記或盲信。改寫成讀者位置的走查（跳到這行想拿資訊的讀者逐字檢查、每條斷言換成動作加材料、實際進入點程式碼補進文中對照、檢查方式在走完後浮現）之後，由使用者判定「說得清楚非常多」並要求固化成寫作模式。判定工具是重建測試（讀者用文中材料能不能自己得出這條）、審查掛載在 multi-round-review 的斷言支撐 frame（v1.27.0）。同批把「檢視註解的最高原則——評估它有沒有解釋到這個行為、事件、flag 的商業邏輯、沒有就重新檢討寫它的動機」寫進 compositional-writing 的 writing-code-comments reference 頂端（v0.50.0）。反向指標補在 #254（灌輸那一半的段落層形態）。新增場景導讀路徑 43。

**Last Updated**: 2026-08-08（晚）— #254 補「灌輸與懸念是同一個缺陷的兩個方向」。#254 立卡當天、依它改寫的那篇 work-log 被使用者指出新問題：修懸念時把判準抽成開頭一段直接給（外加「觸發場景 / 整理目的 / 本文邊界」欄位組），讀者沒有推導可依附、只能硬記——概念要由讀者沿著推導自己長出來、不是被交付。這是修法自己踩進缺陷的另一個方向：懸念是結論被扣在推導後太遠、灌輸是結論出現在推導前沒有支撐、共同根因都是結論與推導脫節。分工修正為：標題承載結論（檢索錨）、開頭承載情境定位、判準在推導走完的位置浮現。同批修正：該篇 work-log 抽掉文首欄位組與「先給結論」段、「三個毛病」式斷言清單改成給讀者推導材料（「入口是自創行話」補上實際進入點的程式碼對照、讓讀者自己看出註解與程式斷線）、動機段改成直接的檢視標準（評估註解有沒有解釋到行為 / 事件 / flag 的商業邏輯、沒有就重新檢討寫它的動機）；work-log 模板的結構欄從「情境條件 → 判準 → 推導」改成「情境條件 → 推導與驗證 → 判準」；AGENTS.md 原則十、compositional-writing v0.49.0、multi-round-review v1.26.0 同步。

**Last Updated**: 2026-08-08 — 新增 #254 教學與檢討內容寫給帶問題來的讀者，不是要被吸引的聽眾。從 #253 同批的 work-log 檢討文章抽出：該篇標題是問句、段標帶懸念、全文以第一人稱事件敘事組織、核心判準壓在全文後半，經過多輪審查零 finding、由使用者讀後指出。根因分三層——「檢討用客觀視角、標題是直述句」這條規範當時不存在於任何地方（compliance reviewer 對不存在的規範產生不了 finding）、字句層 keyword bank 的枚舉不含懸念與第一人稱且單篇 work-log 不進批次審查流程、問句標題與三幕劇是生成端高頻默認而同源 reviewer 覺得自然。修法主力放生產側：work-log 模板明定情境單位是條件不是個人事件劇、compositional-writing 新增敘事姿態原則、multi-round-review 的 keyword bank 補問句標題與敘事轉折詞 grep 當補位。同批把原文章改寫成直述標題 + 判準先行 + 客觀條件視角（「reviewer 問了 X」改成「若對這個做法問 X 而答不出來、就該重新檢討」）。反向指標補在 #166（限定它的敘事豁免邊界）與 #165（規範缺位層在同源盲區上游）。新增場景導讀路徑 42。案例前後對照見 [註解防不了改壞](/work-log/comment_cannot_guard_invariant/) 的 git 歷史。

**Last Updated**: 2026-08-07 — 新增 #253 寫註解的動機是怕被改壞時要處理的是那個約束、不是那行文字。從一個 Dart 專案的 code review 抽出：一行欄位 doc 被退兩次，第一版重述型別名稱、第二版寫的是真實存在的跨函式讀寫順序約束，兩次的退件理由都停在文字層而作者照著改也走不出循環。轉折是追問動機——「怕有人動壞它」——問題於是從「這段文字寫得好不好」換成「這個防護需求該送到哪裡」。破壞實測（在重設函式裡加一行清除、跑整合測試）當場給出答案：測試紅了，防護已經有人接手，註解是沒有保護力的副本。這張卡與 #222 的分工是上游加一類手段：#222 從「意圖確定要強制」起步，本卡補動機辨識與「這個約束能不能不存在」這道 gate。同一個承重論點在四輪審查裡被推翻三次，值得記下這個過程。初稿說既有清單漏掉測試是因為「那些清單按違反時發生什麼排、而測試不阻止違反」，反證就在被引用的那張表裡：文件層那一列的「違反時發生什麼」正是「靜默通過」，文件層同樣不阻止違反卻在清單裡。替補的說法是「既有清單只列約束的載體、測試是觀測者」，而它也被推翻——ddd 那篇的 CI 格寫的是「architecture test、lint」，architecture test 就是測試、住在程式外面，逐字符合觀測者的定義，所以「只列載體」不成立。第二次推翻正是 #248 描述的形態：替補者從推翻前任的過程裡浮現、帶著「已經被想過」的錯覺，而當時沒有拿殺死前任的那個問題（回去讀那張表）再問它一次——只讀了欄位名就下結論，沒讀 CI 那一格的括號內容。第三版（「觀測者早就在清單裡、漏的是應用程式碼層的觀測者」）在第四輪也被推翻，而且錯法比前兩次更值得記：它給「載體」下的是析取式定義（「寫進程式的位置」或「違反時產不出來」），兩個析取項在文件層剛好分岔——文件層寫在產物內卻靜默通過。於是同一個詞在三個檔案裡指了兩種東西，而**殺死第一版的那張表格的矛盾，被原封不動寫回了同一篇裡**。析取式定義在單句閱讀時完全正常，只有把所有用例並排才會爆，這是它撐過三輪的原因。第四版拆成兩條獨立的軸：「規則寫在哪」與「違反時何時發聲」，既有清單把兩者壓成一條強度刻度，代價是產物外那側只剩 CI 一格、而那格裡只有讀程式文本的檢查，觀測執行行為的那一種沒有位置。這個分類買到的是刻度的終止條件——沿刻度找不到落點的人會被送回起點寫註解，而那正是案例裡發生的事。三次錯誤在被抓到時都已沿反向指標擴散到多個 surface，各自一併修正。卡片明標四項限制：單一案例、反事實那一支（測試不存在時註解值多少）沒有跑因此宣稱收在機制層、破壞實測本身需要一條跑得動的測試流程、以及步驟順序沒有對照。同批補的反向指標分佈在——#222 的關係段與判讀徵兆表、[不變式的強制層次](/ddd/invariant-enforcement-layers/) 的兩軸段與判讀訊號段、[型別取代 doc 的收益曲線](/record/types-replacing-docs/) 的 review 第四問與一句話 heuristic（該篇原本把時序契約與跨方法 invariant 無條件判給 doc，與新增段落結論相反、一併同步）、[程式碼註解撰寫方法論](/record/comment-writing-methodology/) 的品質驗證段——並新增場景導讀路徑 41、在路徑 30 前綴 #253。案例全文見 [註解防不了改壞](/work-log/comment_cannot_guard_invariant/)。

**Last Updated**: 2026-08-03（晚）— 新增 #252 配額耗盡的症狀落在申請最頻繁的元件、成因在持有最久的那個。從一次 macOS 程序額度耗盡的歸因誤判抽出：症狀是一批性質不同的操作同時開始 `fork` 失敗、最密集的是每次要開三個程序的多層 shebang hook，由此串出的解釋（hook 把自己的額度耗光）每一個組成事實都經得起查證而結論是錯的——實際是一個連續執行十天的模擬器累積了 2008 具殭屍程序、佔掉 2666 個名額的四分之三。這張卡的力量在於症狀與佔用量的分離可以從機制推出來而非事後歸納：佔用量是申請頻率乘持有時間，而持有時間的跨度（毫秒到永不歸還）遠大於申請頻率的跨度，於是佔用量的排序由持有時間主導、症狀的位置卻只跟申請頻率有關。多輪審查在這裡抓到一個承重錯誤——初稿寫「兩個量互相獨立」且說模擬器「只申請過一次格位」，兩句都不成立：兩個量共用申請頻率這個因子，而 2008 具殭屍代表模擬器 fork 過兩千多次、頻率與 hook 同一個數量級。分開它們的從來不是申請頻率，是有沒有歸還。同批在 #248 補反向指標（本卡限定它的前提——先問這個問題需不需要假說）、在 #221 補監控層形態、在 #250 補解釋層形態，並新增路徑 40 與 macos 目錄頁的入口列。案例的完整機制寫在 [殭屍程序與使用者程序上限](/macos/macos_process_limit_zombie_reaping/)。

**Last Updated**: 2026-08-03 — 新增 #250 / #251，從一套自建流量統計上線後的資料判讀抽出，兩張都在處理「能力隨時間衰減而不產生訊號」。#250 的觸發是同一個錯誤兩天內發生兩次、形狀完全相同：資料模型從單事件改成一進一離雙事件後，判斷「單頁即走」的 `COUNTIFS(...) = 1` 從此恆不成立；修正版加了「非進入事件留白」的條件，又在真實資料出現第三種形狀（爬蟲的進入事件送不出去、只有離開事件進來）時把整類流量排除掉。兩次都不報錯、輸出都是合法標籤，只有分佈變了。#251 的觸發是爬蟲辨識要從「有沒有」升級到「是誰」時，用具名清單做精確比對這個直覺做法會讓清單過時表現為自動化流量比例下降——而那個下降與「真人變多了」在數字上不可區分；實際採用兩層結構讓過時的代價落在精度而非覆蓋。該卡明標證據狀態與 #250 不同：失效模式在該系統上尚未觀測到、兩層結構是設計當下依推演採用的，旁證是同一份清單上線時就含有一個永遠不會命中的死條目（robots.txt 的控制 token 不出現在 UA 字串裡），而系統從不回報「某個條目從未命中」。兩張卡與 #221 同構（零 error 與零命中都無法與「沒被涵蓋」區分），該批同時在 #221 / #232 補了反向指標。

**Last Updated**: 2026-07-31 — #221 補第二種形態「偵測視窗也是一個沒被審視的 fact」。原卡講作用域被編碼成路徑常數後不再被檢驗，本次補同一結構的另一個參數——偵測規則編碼的「證據會出現在哪裡」。實例是掃描表格未標年度時視窗設成往回三行、三十個命中裡十七個假陽性；錯誤方向與原形態相反（假陽性看起來像工具很認真，因此更不引發懷疑），而未驗證的偵測器產出的數量會被當成量測寫進待辦。同時記下懷疑分配的不對稱：交給低階模型的那段被抽驗了十二項、自己寫的掃描沒有，而後者誤報率高出一個量級。

**Last Updated**: 2026-07-31 — 新增 #249 對當下段落沒有收益的標註不會自發發生。跨兩個領域量測：財務分析七篇跑嚴謹度審查（3 B / 4 C / 0 A，基準適用性、數據時效、推論鏈完整性三個維度在六篇裡全數失效）、技術模組四篇跑雙類標註盤點（機制與判讀類對來源與適用條件類，四篇方向全一致、來源類平均低約 30pp、標籤對調後結果不變）。這張卡的力量來自對照是內建的——兩類標註出自同一位作者的同一次寫作，唯一差別是收益結構。幅度不可信（兩類判定門檻不對等、兩位盤點員各自指出）、樣本同源（十一篇同一作者），兩項限制都寫進卡裡。

**Last Updated**: 2026-07-30 — 新增 #248 推翻一個假說之後替補者是在驗屍的空檔裡上位的。從一段方法論實驗的兩次假說替換抽出：第一個假說（弱模型當歧義偵測器）被補跑的對照組反向推翻——強模型不但沒有「自動修補所以看不見」、在每個量測到的軸上都找得更多更精確；而推翻之後立刻換上的第二個假說（抽取式協議才是作用中的變因）竟然帶著同樣的缺陷——十一個受測者全部跑抽取式協議、沒有任何一個跑評價式，零對照。這張卡的操作重點是那句可直接執行的話：推翻一個假說之後，第一個要問替補者的問題，是那個剛剛用來殺死前任的問題。

**Last Updated**: 2026-07-30 — 新增 #247 多次局部正確的修法會合成缺陷。從一組資安章節連續跑八輪審查（主批四輪、新章四輪）之後的回看抽出：每一輪都換 frame、每一輪的 finding 都修完，而事後至少四處缺陷的成因相同——兩次修法各自正確、合起來出問題。四個實例形狀一致：補進入動機的修法讓同一則故事出現兩次、換判準的修法讓一段不該存在的內容變得更完整、對齊待辦的修法把內部狀態帶進正文、模組入口被三輪各插一句而第三句落在句子中間讀起來不成句。這張卡的操作重點在於它的位置：它是所有維度跑完之後才存在的東西，因此停止判讀要在 frame 清單之外加一次整體通讀。

**Last Updated**: 2026-07-30 — #239 補「有檢查表的擠掉沒有檢查表的」這一維。來自一次刻意隔離的方法論實驗：把冷讀（只准讀一個檔案）與走路線（禁止對單篇提品質建議）拆成兩個 reviewer，各自標記每個 finding 的跨 frame 可見性。結果是冷讀 14 項有 7 項路線讀者看不見、走路線 8 項有 6 項冷讀者看不見，兩個 frame 誰都不涵蓋誰；而路線那一輪自己回報 finding 約各半來自「走路線」與「比對宣告與內容」，並指出這兩個動作不該算同一個 frame——前者是時序動作、只看得見讀者當下看得見的，後者是全域動作、要離開讀者視角窮盡查證，而混在一起時有檢查表的那件會擠掉沒有的。multi-round-review v1.22.0 據此把宣告核對放進 Round 1-C、走路線在 Round 2-B 獨立並強制指定讀者身分與起點。

**Last Updated**: 2026-07-29（深夜）— 新增 #246 被多篇當成前提的判斷缺的是住址。從 07 那批四輪審查後的盤點抽出：十一項待辦裡有五項是同一形狀（資產盤點 / 配發流程 / 隔離設定落點 / 委任型憑證 / 授權模型選型），全部在多篇被當前提引用而沒有任何一篇承接，且全部是審查時才登記、沒有一項在寫作當下浮現。觸發它的是第六個實例——一輪 steelman 說某章「缺了先問要不要自己做這件事」，修法因此落進那一章的前置段，而事後回看那一段與另外兩處碎片是同一條軸的三個角。這張卡的操作重點是缺卡與缺章的分界：定義重複是術語、判斷的各角重複是缺章，因為取捨需要並置。

**Last Updated**: 2026-07-29（夜）— 新增 #245 原則層與操作層是兩份會漂移的副本。從 07 資安模組那批的第三輪審查抽出：一條規則套用率零，直覺歸因是自審失效，實際是執行時被讀的操作文件停在規則抽出時的第一版、卡片後來修過三次都沒同步。回頭比對同批其他規則，漂移分布有規律——與操作文件同時寫下的都同步了，卡片在後續輪次被修正的全部停在原版。重點在誤診代價：兩種成因的表徵相同而修法相反，誤診會讓加強檢查完全無效，且審查通過會反過來確認規則已落實。同時修正本索引的 #244 條目——它停在改標題前的舊版，是同一個漂移形態發生在索引這一層。

**Last Updated**: 2026-07-29 — 新增 #244 範例是讓解方缺口現形的工具。7.28 / 7.29 補完範例後做出口盤點，七處缺出口在補範例之前全部不可見——純分析的段落讀起來完整，缺口要等讀者腦中有具體失敗、開始問「那我要怎麼辦」才顯現。其中兩處的目的地存在且承接，只是連結在一百行之後的文末路由段；三處主題沒有落點而文中未標明狀態。處置：新增 7.30 使用者密碼儲存簡版（7.28 第四類原語原本沒有下游）、7.28 的 out-of-scope 兩項補落點、7.29 補四處出口。同時記下一個反模式——替換微案例時連帶刪掉了它第四拍裡全篇唯一的止血知識。

**Last Updated**: 2026-07-28（深夜）— 新增 #243 判定型規則要規定判定的痕跡（Round 4「誤用 / 激勵梯度」frame 的產物）。這一輪換的問題是「想少做事的執行者會怎麼合規地執行這條規則」，出來十一項而十一項收斂成同一形狀：規則要求做判定、卻沒規定判定留下什麼，於是認真做過與完全沒做的產物相同、規則沿著零後續動作的那個結論塌陷。十一項的具體限定句已補進 #240 / #241 / #242 與 backlog 格式規範（路由驗證要寫出落點名稱、審查產出是逐條表、判成資深端要說出依據、留白要設 tripwire 與素材類別、「一兩個」是上限不是配額、規模欄的「中」要舉證），收斂原則抽成 #243 並同步進 multi-round-review skill 的 Round 3-F。腐化 frame 另修兩處：#240 的「六個服務頁」改成不內嵌數量的寫法、#241 的「上述那篇」改成具名。

**Last Updated**: 2026-07-28（夜）— 本批三卡（#240 / #241 / #242）與 backlog 格式規範跑完三輪十一個 reviewer 的多輪審查後修法。承重修正三項：#242 新增「四拍要有來源」硬條款（第三拍是唯一推不出來的那一拍、推不出來就代表無經驗的作者或生成工具只能發明它、留白比杜撰好），#240 補「存在 ≠ 承接 ≠ 可達」三道關卡與外部目的地的第四種處置，#241 把地基斷言從二元改成單峰（零經驗端缺的是術語入口而非情境）並把情境與實作的分界從內容類型改成解析度。Round 3-A 的 self-application sweep 另抓出十一項「規範寫下來之後同批仍犯」，含規模欄格式零套用、SSoT 禁複製在模組內失守、B‴ frame 自己的路由違反它剛加的路由維度。

**Last Updated**: 2026-07-28（傍晚）— 新增 #242 形態讓讀者對號入座、微案例才讓他想像得出後果（從補完形態後使用者再問「怎麼沒看到補案例」抽出）：原始需求「缺範例」被轉譯成「補形態」、只滿足一半；微案例是無身分四拍短敘事、與 #224 的剝離要求相容；反模式是把補範例轉譯成補分類、辨識訊號是提需求的人用原本的詞再問一次。7.29 已試寫兩段微案例（152 → 156 行）。

**Last Updated**: 2026-07-28（下午）— 新增 #241 判讀層只給機制屬性時可用程度隨讀者既有經驗遞減（從 7.29 API 認證分層章的檢討抽出）：情境不等於實作、系統形態與觸發事件分別服務設計與事故兩個時刻、判讀訊號欄的時序陷阱、兩拍寫法與兩個修法副作用。7.29 已依此補七處並新增「問題節點出現在什麼樣的系統」一節（127 → 152 行）。

**Last Updated**: 2026-07-28 — 新增 #240 跨模組路由要驗證目的地承接該主題（從 7.28 金鑰託管路由指錯模組、三輪十個 reviewer 沒抓到、由使用者提問「文章不存在還是列在 backlog」而浮現的事故抽出）：路由驗收條件是目的地實際承接該主題而非存在、落空時三種處置、code 格式模組指涉逃過所有連結檢查。同步在 multi-round-review skill 的 Round 1-C 加「路由目的地承接驗證」維度。

**Last Updated**: 2026-07-21（晚間）— 新增 #238 承重事實對 primary source（自己舊分析是 secondary、blog 錯誤傳播 + 過度修正的查證骨牌）、#239 宣告的組合≠執行的組合（neurodivergent-output + 5w1h 同開卻漏跑 5w1h、使用者抓到的自我示範）：兩張都從中聯財報查證 + 修文過程抽出。同步修正 neurodivergent-output 與 5w1h-decision 的 Collaboration / pre-send，加「組合各半這則有沒有現形」的強制檢查。

**Last Updated**: 2026-07-21（傍晚）— 新增 #237 任務累積成基礎設施前先亮出 anchor（從本 session escalation 事故抽出、由 neurodivergent-output skill 實測時的流程驗證觸發）：連續 escalation 每層加基礎設施、anchor「自用」最後才浮現、apparatus 份量被流程動能而非 anchor 決定；修法是 escalation 第 2 次出現就亮 anchor 定份量、亮一次不是每請求質疑；是 #235 / #236 同 session 姊妹（#236 驗正確性、本卡驗份量）、#125 collapse 份量維、#75 疊加成本判準、WRAP Anchor Check 具體化。同步回饋進 wrap-decision skill 的 Tripwire。

**Last Updated**: 2026-07-21（下午）— 新增 #236 承重論點先對抗驗證、再建下游（從神經多樣性方法論的生產順序事故抽出：「衝突只有一組」錯論點被寫進 4 篇 + skill + 索引、Round 3 steelman 才反證、跨 6 檔回改）：承重論點錯誤等比傳播、驗證順序跟依賴順序相反（最被依賴的先驗）、steelman 用兩次（前置閘門 + 後置收尾）、承重論點的挑戰交對抗 / 異源不靠自審；是 #11 早驗 / #64 上游一次 / #217 斷言支撐時機 / #205 生產順序 / #165 同源盲區 / #235 同事故另一面 的家族。跟同批 #235 是同一事故的兩面（#235 整合方法本身、#236 生產順序）。

**Last Updated**: 2026-07-21 — 新增 #235 整合互斥規則集：抽共用 base、按層分離、把衝突顯性化成解析規則（從神經多樣性三 skill 整合的方法論 + 一輪 steelman 修正抽出）：多套部分重疊部分衝突的規則集合成一套時、抽共用成永遠開啟的 base、按作用層正交分離（附判層測試但標明是啟發非判準）、把真衝突逐一定位顯性化成解析規則（全域開關 / 逐項讓步 / 合成、每次讓步都老實標成規則退讓）；招牌陷阱是把「分析只找到一組衝突」講成「結構上只有一組」——搜尋不完整偽裝成結構定理、跟 #152 必然性框架同構、修法是還原成「只找到一組」並逐條枚舉規則對；是 #75 的 compose vs conflict 對半、#125 collapse 在規則集整合 surface 的修法、#44 共用規則單源、#126 完整性靠枚舉不靠單軸做深、#90 疊加訊號一致、#86 分層選力度。

**Last Updated**: 2026-07-20 — 新增 #232 自審偵測方法要對齊規則類型、#233 知識卡的缺孤錯住在卡↔文章關係裡（都從本 session 多輪審查 Round 3 抽出：#232 是 grep self-sweep 對無關鍵詞規則失明、#233 是缺卡 / 孤兒 / 矛盾三種缺陷住在卡↔文章的邊上、要消費側 audit 才看得見、由 outbound frame 抓到兩缺卡 + CDP 矛盾）；路徑 35 串 #232 / #233 / #221 / #165 / #147（通過訊號先問涵蓋、audit 立足點限制可見範圍）。新增 #234 描述抽象概念要用貼合屬性的謂語（分析角度不會「說話」、訊號的可辨識度是「清晰」不是「直接」；兩處搭配錯位由人類冷讀 catch、是 #165 register 需異源的實例）。前次：新增 #229-#231 分析文章結構三卡、路徑 34 串 #229 / #230 / #170 / #141。

**Last Updated**: 2026-07-17 — 新增 #228 等比縮放不管空間分配（從書庫 app 驗收「用了 flutter_screenutil 為什麼版面還會擠壓」的疑問抽出、對應 ux-design 案例 U.C16 / U.C19）：換算工具工作在常數層、空間分配發生在 layout 協商層、工具靜默不等於該層無問題、引入套件時記錄「它不保證什麼」；是 #82 / #92 工具 ceiling 家族的第三個 sibling（換算工具 vs 佈局層次）、#221 的跨層版。新增路徑 33 串 #228 / #92 / #82 / #221。

**Last Updated**: 2026-07-15 — 新增 #227 可重現性只有乾淨機器重跑才驗得出（從 dotfiles bootstrap 的全新 macOS VM 冷測抽出、抓到 8 個只在乾淨機器現形的 fresh-machine bug）：環境實際依賴的狀態散落在 repo 之外的許多地方（安裝器寫進 shell profile 的行 / 系統 PATH drop-in / 手裝殘留 / 來源寄居別專案的工具），「從 repo 可重現」是未驗證宣稱、讀 repo 只顯示宣告了什麼、乾淨機器實跑才顯示實際依賴什麼；「在我機器上能跑」是量測問題（原機是被污染的儀器）。新增路徑 32 串 #227 / #44 / #93 / #11。是工程層卡（跟近期寫作方法論卡不同軸）、串既有 SSoT / fact-vs-derivation / 靜態 vs 實跑三族。

**Last Updated**: 2026-07-13 — 新增 #225-#226 延伸層內容雙卡（從 til 緊緻性筆記重構的兩次使用者指正抽出、同 case 兩個獨立原則）：#225 內容去留由教學目標把關、素材量只調整寫法（「只有一個案例撐不起」是出現頻率邏輯的變形、教學需求判準從術語卡推廣到層的去留決策）、#226 延伸層內容以讀者問題立篇（自我消解的延伸段是缺讀者入口的訊號不是該刪的證據、讀者問題一次給原子邊界 / 入口 / 內容判準三樣）。新增路徑 31 串 #225 / #226 / #169 / #130。同批完成 til/math/ 子分類重構（緊緻性拆成 hub + 前置概念 + 定理 + 思維層共 10 篇）、兩卡是該次重構的原則層。

**Last Updated**: 2026-07-13 — 新增 #224 教學層引用 case 要剝離身分與規模鋪陳（從 ddd 組裝層可達性章多輪審查的兩次使用者指正抽出：reviewer 偵測到帳目搬運、修法停在通用化「上百張票」；使用者補完階梯——規模鋪陳整句刪、產品身分與領域詞泛化為無身分載體「一個專案」「一筆資料」）。核心是兩 surface 的讀者契約：work-log 的價值是具體性、教學章的價值是可轉移性、case 敘事的住址只在前者；「刪掉後論證還成立嗎」的機械測試取代「規模感幫論證」的直覺。路徑 20 尾補 #224。

**Last Updated**: 2026-07-10 — 新增 #222-#223 逃生口雙卡（從 Dart 專案 copyWith entity 設計檢視的 work-log 抽出、同 case 兩個獨立原則）：#222 約束要讓違反路徑走不通（設計意圖三落點、註解宣稱約束但實作沒查比沒有約束更糟、「有沒有不允許任意組合的欄位」判準）、#223 逃生口吸收建構路徑的缺陷（萬能出口讓上游表達力缺陷不痛不修、語意錯誤在別處復發、修工廠不修拼裝點、繞道流量是免費需求調查）。新增路徑 30 串 #222 / #223 / #42 / #110。同批建立 content/ddd/ 與 content/flutter/ 模組骨架、兩卡是 ddd 模組「不變式強制層次」「建構路徑設計」章節的原則層。

**Last Updated**: 2026-07-10 — 新增 #221 檢查規則的作用域要顯式列舉（從 /report/ 列表排序異常的三層診斷抽出：表層是 Hugo timeZone 未設導致當日文章被判未來、中層是 8 篇缺 weight 被預設排序沉底、根因是 mdtools 的卡片層 frontmatter 檢查從未涵蓋 content/report/）。核心是「規則存在」與「規則涵蓋」是兩個獨立的 fact，而只有前者被寫進規範、被討論、被記得；作用域常數被多檢查共用時，耦合會讓正確的修法看起來很貴、反過來保護違規。新增路徑 29 串連註冊點檢查（#221 / #139 / #93 / #96 / #44）。

**Last Updated**: 2026-07-10 — 新增 #219-#220 建構端正面模型（採購模組重寫完成後的 retrospective）：#219 教學模組要有推導源頭（主題集合 vs 推導體系、源頭買到判準同尺 / 矛盾現形 / 擴篇掛載 / 推導式路線四件事）、#220 判準要寫到條件層（口訣 / 維度清單 / 條件映射三成熟度、重算測試驗收、機制重建後同坑再踩一次的實證）。路徑 28 從三卡診斷鏈擴成五卡生產鏈（素材 / 模組結構 / 篇章結構 / 判準顆粒度 / 審查）。

**Last Updated**: 2026-07-09 — 新增 #216-#218 經驗談轉分析教學系列（3 張卡：#216 經驗談來源要重建分析層 / #217 審查要有斷言支撐 frame / #218 文章按分析弧拆分）；新增路徑 28 串連三卡。從採購 planning 模組 retrospective 抽出：模組經三輪 multi-round review 修訂後 merge、使用者仍判定「講故事不是商業分析教學」——素材端（機制未重建）、結構端（按主題攤平）、審查端（frame 缺斷言支撐維度）三個根因各立一卡。

**Last Updated**: 2026-07-05 — 新增 #209-#213 教學文章知識目標與結構決策系列（5 張卡：#209 知識目標決定結構 / #210 壓縮結論剝奪推導路徑 / #211 複合問題先拆機制再談交互 / #212 SRP 違反是路由訊號 / #213 分類從內容深度浮現）；新增路徑 27 串連五卡。從 macOS 磁碟空間系列文章的寫作 retrospective 抽出。

**Last Updated**: 2026-07-04（til/vocab 擴充 cadence 修法反噬 retro）— 新增 #208 修同質化的手法本身會同質化：til/vocab 學術英文評論字擴充、原始 10 張跑過三輪修過分號模具、後續 16 張擴充卡在生成端自套「段首目標詞先行」避開該模具、只跑字源 fact-check 就交付；補跑整組 cadence 異源 reviewer 才發現「目標詞先行」均勻套成「目標詞 + 的X在/是『引號』」新模具 12/16 張、比原模具更密，連互指句與字源收尾也各自骨化；成因是換模不等於破模（單一替代句型仍是模板）+「多樣化規則」偽裝成多樣化 + 同源自審被「已修」背書遮蔽；修法要輪替多個 framing 不換統一模板、生成規則本身當 cadence 候選進整組跨卡異源 review；是 #123 便利解收斂的 deliberate 版、#167 修法新建模具而非同違規殘留、#122 cadence 隱形維度的動態版、#147 規範產物本身進 audit、#165 同源盲區在修法後的加深。教訓也印證「生成端套紀律不等於免審」——cadence 是跨卡屬性、逐張自掃 keyword 全 clean、只有整組連讀異源看得到。

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

### 路徑 39：剛推翻自己的一個判斷、手上已經有替代解釋

`#248 替補者是在驗屍的空檔裡上位` → `#153 漏抓先分 design gap 與 execution gap` → `#227 可重現性只有乾淨機器重跑才驗得出` — 先用 #248 的那句話當場測一次：剛剛用來殺死前任的問題，替補者經得起嗎；經不起就把它降回待測項、並在當下寫出對照設計。接著用 #153 分流，因為替補假說最常見的形狀是把執行落差說成設計落差（「我們缺一條規則」）。若替補解釋涉及「某個東西可以重現 / 可以從宣告推導」，用 #227 的乾淨執行驗它，不要用讀宣告的方式驗。三步都過之前，這個解釋不寫進規範——錯誤歸因會被後續工作當作前提。

### 路徑 40：一批性質不同的操作同時開始失敗、共同點是都要申請同一種資源

`#252 症狀落在申請最頻繁的元件、成因在持有最久的那個` → `#221 檢查規則的作用域要顯式列舉` → `#248 替補者是在驗屍的空檔裡上位` → `#153 漏抓先分 design gap 與 execution gap` — 先用 #252 判斷這是不是配額耗盡型故障（判準是失敗的操作在功能上互不相關、唯一共同點是都要申請同一種資源），成立時先用正向查詢問「這個配發器在耗盡那一刻做什麼」（三選一：失敗回給下一個申請者 / 從既有持有者挑一個收回 / 讓申請者排隊；第二種的 OOM killer、連線池驅逐、依用量節流的 rate limiter 已內建一次持有者歸因、症狀反而直接指向持有者），再把「誰在報錯」整批擱置、改去查系統保存的持有者欄位並依持有者聚合；查之前先驗那份紀錄的兩個前提（查詢要在耗盡進行中執行、聚合欄位的粒度要對應得上可回收的單位），否則會拿到空集合或共用容器這兩種高信心的錯誤答案。聚合集中在單一持有者是回收問題、接近均勻是擴容或分流問題，這個分岔決定後續全部工作方向。#221 用在監控這一側——先問「這一項配額有沒有被量測過」，因為所有指標正常與沒有量測這一項給出的訊號相同，而監控的涵蓋面通常沒有一份可以打開來核對的清單。持有者紀錄縮完範圍之後仍要回到假說路線，因為持有者不等於成因（連線池的持有者是那個 handler、成因可能在第三方的延遲上）；紀錄根本不存在時（無 allocation tracking 的洩漏是典型）更是從頭就靠假說。這兩種情況都適用 #248 的紀律：手上那個解釋要有自己的對照，而不是繼承「症狀集中在那裡」這個為了定位而蒐集的觀察。修法方向定不下來時用 #153 分流，配額耗盡最常見的誤診是把回收缺陷說成容量不足（提高上限會讓症狀立刻消失，因此它看起來像有效的修法，實際作用是延後下一次撞牆）。案例與機制細節見 [殭屍程序與使用者程序上限](/macos/macos_process_limit_zombie_reaping/)。

### 路徑 41：準備為一段程式寫一行 doc、或在 review 裡爭論某行註解該不該留

`#253 要處理的是那個約束、不是那行文字` → `#67 寫作便利度跟意圖對齊反相關` → `#222 約束要讓違反路徑走不通` → `#249 對當下段落沒有收益的標註不會自發發生` — 爭論停在「這段文字該怎麼寫」時，用 #253 換一個問法：寫它的動機是說明，還是怕有人改壞它。動機是後者就先問那個約束能不能被消除（多半是某個結構選擇的產物），不能消除才挑會發聲的手段，判準是問這段資訊有沒有對應的斷言——存不存在一條會紅的斷言，不是造不造得出句子。#67 解釋這個誤送為什麼系統性發生而不需要作者疏忽——寫一行註解是所有選項裡最便宜的，而它是唯一連被讀到都不保證的。挑落點時接 #222（文件 / 型別 / 執行三層的取捨，以及「宣稱了但沒強制」為何比沒有約束更糟）。反向的失敗用 #249 檢查：來源、版本、適用邊界這類對當下段落沒有收益的標註不會自發發生，該寫而沒寫跟不該寫而寫了是同一個收益結構的兩端。

### 路徑 42：寫教學或檢討文章時決定標題形式與敘事視角、或審查時撞到問句標題與第一人稱敘事

`#254 寫給帶問題來的讀者、不是要被吸引的聽眾` → `#166 重點優先陳述是跨語言的資訊結構原則` → `#165 register 違規判定要靠文體異源` → `#221 檢查規則的作用域要顯式列舉` — 先用 #254 定姿態：讀者由搜尋或路由帶來、自帶問題，標題承載結論、開頭承載情境定位、判準由推導交付、檢討的載體是客觀條件不是個人時間線；判別線是位置——操作型自問句合規、標題 / 段標 / 結論位的問句是懸念型。修懸念不是把結論搬到開頭：灌輸與懸念是同一個缺陷的兩個方向，都讓結論與推導脫節，未經推導的開頭結論摘要（含「觸發場景 / 整理目的」欄位組）同樣要抽掉。句子層的重點後置用 #166 的判準逐句修（核心概念第一次正面出現在不在句首），懸念弧是同一個缺陷的篇章層形態。審查時記得 #165 的上限：問句標題與三幕劇是生成端高頻默認、同源 reviewer 覺得自然，keyword grep 只曝光候選、真防線是生產側規範加異源冷讀。多輪審查零 finding 不等於沒有問題——用 #221 的形態問一句「這個維度在不在任何規範與 frame 的射程內」，缺位就先立規範再補檢查，往枚舉裡加 keyword 治不了規範缺位。

### 路徑 43：一段說明被判「讀者可能看不懂」、或自己寫出了條列式斷言

`#255 斷言清單展開成讀者位置的走查` → `#242 微案例讓後果可想像` → `#244 範例讓出口缺口現形` — 先用 #255 的重建測試定位問題：逐條問「讀者用文中已給的材料能不能自己得出這條」，重建不了就用走查三步改寫——把讀者放到使用產物的位置、每條斷言換成動作加材料（缺的材料要補進文中、那正是清單藏住的缺口）、可重用的檢查方式放在走完之後浮現。改寫時分清要補的是哪種材料：結論需要驗證的補程式碼與對照（本卡）、後果需要想像的補微案例（#242 的四拍寫法）。補完材料再跑一次 #244 的出口盤點——讀者跟著走查理解了問題之後、他的下一個動作有沒有落點。

### 路徑 44：流程要新增一份文件產出、或發現文件跟現狀對不上

`#256 同步期待要嘛有機制承接、要嘛明示降級` → `#253 要處理的是那個約束、不是那行文字` → `#245 原則層與操作層是兩份會漂移的副本` → `#249 沒有收益的標註不會自發發生` — 先用 #256 分級：這份文件被期待永遠最新嗎、守著它的機制是什麼；指不出機制就二選一——寫比對腳本掛進 CI、或降級成標記消費時點的 scaffold / append-only 記錄，「補一條同步規則」不在選項裡（那是在期待紀律做機制的工作、#249 解釋為什麼撐不過第一個 deadline）。同一段敘述出現在兩份以上文件時、指定唯一權威載體、其他處改引用；行為類資訊的權威載體是測試——判準沿 #253：會發聲的那份才守得住。既有的雙副本（原則卡 + 操作文件這類拆不掉的）用 #245 的機制補法：反向核對、版本號對齊、改動單位取所有副本。

### 路徑 45：內容裝不進容器、或文章越寫越像簡報

`#262 內容超出容器時擴充結構、不壓縮內容` → `#263 不相容的分解會長得像互補` → `#261 語句要在它的消費單位內資訊自足` → `#149 keyword bank 命中是候選、不是判決` — 判準裝不進表格格、概念裝不進標題時、先用 #262 選出口（本篇專屬加延伸段、跨篇可用拆卡外部化、範例寫進卡片、概念已有卡或專章的改放連結）、內容量不是可裁的變數。選出口前先搜內容集合有沒有既有落點（有落點就改放連結、不寫 gloss），並跑一個前置檢查（#263）：這個概念在別篇有沒有不相容的版本（兩篇各有一套階段表或欄位組時跑雙向對映與動作測試、有衝突先收斂單一載體再選容器）；表格格與 checklist 項的句內品質用 #261 的四條件加抽離重讀驗收；「表格為主體」「四字節奏」都是候選訊號、判定依 #149 的兩步驟分工看消費單位——查表型段落與 checklist 的表格形態合法。拆卡的判準與登記流程走 knowledge-cards skill 的「內容壓力是第二個建卡入口」段。

### 路徑 46：要為一批事實跑外部查證、或發現查證的配額與時間失控

`#265 查不查的判定要在查之前做完` → `#238 承重事實要對到 primary source` → `#243 判定要規定留下什麼痕跡` → `#236 承重論點先對抗驗證再建下游` — 先用 #265 過閘門：待查清單逐項問「查不到的話成品少掉什麼」，答案是可以直接刪掉的修飾語就不進佇列；一個對象一次查詢帶回全部屬性、失敗時先抓上一次結果已經給出的連結而不是重發查詢、便宜的取用路徑被擋而改用昂貴工具時記下可靠度降級。通過閘門的那些才進 #238 的來源層級——一手（申報書 / 官方登記）優先、自己的舊產出算二手、更正錯誤事實時驗到收斂才停。兩張卡的分界是時序：#265 決定要不要花這個成本，#238 決定花下去要驗到哪一層。這類浪費躲得過所有審查的原因用 #243 理解——丟棄的查詢跟根本沒查在成品上長得一樣，而 #243 的補法（規定判定留下痕跡）在這裡用不上，查詢被丟棄的那一刻就無處記錄，只能把判定移到動作之前。事實之上還有論點層，承重論點在建下游之前的對抗驗證走 #236。

### 路徑 47：要決定某一類知識放哪個載體、或某項判定怎麼修都會過期

`#268 要維持當期的內容只能放在更新到得了讀者的載體上` → `#256 同步期待要嘛有機制承接、要嘛明示降級` → `#104 標準引用要附版本與 review trigger` → `#262 內容超出容器時擴充結構、不壓縮內容` — 先用 #268 的兩問過一次：這段內容的正確性會不會隨時間失效（主體是規則本身、還是讀規則的方法），以及這個載體改完到不到得了讀者。第一問答「不會」就照寫，這一整條路線不必走。第一問答「會」而載體是印出來的書、發布後不再送達的文件或別人維護的內容時，那段內容放不進來——內容層只留規則的讀法、具體值路由到到得了讀者的載體，並在收錄或範圍規則上寫下界線與理由（是載體、不是品質）。第一問答「會」而載體自己改得動也送得到讀者時才進 #256 分級：被期待最新的要有機制守著，沒有機制就降級成 scaffold 或 append-only 記錄；#104 是這一格的完整示範（版本與年份標記加 review trigger，並把「這條過時的話讀者會做錯什麼」當投入量的判準）。載體確定之後，內容裝不裝得進容器是 #262 的問題——那裡的變數是量、這裡是當期性，兩者的錯誤方向同為改內容遷就容器。

### 路徑 48：敘事讀起來緊湊漂亮、讀者卻要回讀或自行補推論才接得起來

`#270 敘事的解碼材料要在讀者已讀的文本裡` → `#155 引用章節用語意標題、不用位置編號` → `#261 語句要在它的消費單位內資訊自足` → `#254 寫給帶問題來的讀者、不用演講姿態` — 先用 #270 逐句跑解碼測試：讀者線性首讀讀到這一句、能不能只靠已讀過的正文加模組基線復原完整命題（指涉對象、對比兩面、操作含義）；不具名的位置與數量指涉（前兩本 / 另外兩本 / 這一側）換成全名並順手驗計數——它們是作者地圖的 derivation、常常是錯的，跨檔引用的同一機制走 #155。句內成分的完整度（命題完整、指涉閉合、實詞可反推、一句一命題）用 #261 的四條件驗收，注意 #270 限定了它的敘事位豁免——可依賴的只有已讀的鄰句。問句標題、懸念段標與第一人稱事件敘事屬演講姿態、走 #254；本路徑抓的是另一種借來的語域——書評體的密度審美。命中是候選不是判決：向後近距回指、立即揭曉的破折號、「」內引用都合規。
