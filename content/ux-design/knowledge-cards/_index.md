---
title: "UX Design 知識卡片"
date: 2026-06-19
description: "畫面設計相關的術語卡片索引"
tags: ["ux-design", "knowledge-cards"]
---

UX 設計教學中出現的關鍵術語卡片。每張卡片說明一個語意責任，跨情境變義的概念拆成獨立卡片。

## 卡片索引

| 卡片                                                                                                                         | 核心問題                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [Gate](/ux-design/knowledge-cards/gate/)                                                                                     | 進入特定畫面前的前提檢查——fallback 設計                                                                            |
| [Debounce](/ux-design/knowledge-cards/debounce/)                                                                             | 連續快速觸發的合併策略——多久算「停下來了」                                                                         |
| [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/)                                                           | 回饋的時間門檻——多久沒反應使用者就覺得壞了                                                                         |
| [Screen State Matrix](/ux-design/knowledge-cards/screen-state-matrix/)                                                       | 畫面狀態的列舉與轉換條件——矩陣沒填的格子就是缺口                                                                   |
| [UX Fallback](/ux-design/knowledge-cards/ux-fallback/)                                                                       | 主路徑失敗時的退路設計——fallback 缺失等於死胡同                                                                    |
| [Touch Target](/ux-design/knowledge-cards/touch-target/)                                                                     | 可點擊區域的尺寸底線與範圍對齊——看起來可點的地方要真的可點                                                         |
| [Modal](/ux-design/knowledge-cards/modal/)                                                                                   | UI 元素阻斷背景互動——區分 Dialog 與 non-modal 元件的行為屬性                                                       |
| [Affordance](/ux-design/knowledge-cards/affordance/)                                                                         | 外觀傳達「可以對它做什麼」——暗示與實際行為要對齊                                                                   |
| [Fail-Safe Default（安全預設）](/ux-design/knowledge-cards/fail-safe-default/)                                               | 保護機制自己壞掉時倒向哪邊——預設倒向不可逆性低的那邊                                                               |
| [Progressive Disclosure（漸進式揭露）](/ux-design/knowledge-cards/progressive-disclosure/)                                   | 常用的放第一層、少用的需要時才展開——分層依使用頻率與漏看的代價                                                     |
| [VSync（垂直同步）](/ux-design/knowledge-cards/vsync/)                                                                       | 螢幕每次刷新的時間訊號——每個 vsync 都排幀的動畫，幀數等於螢幕更新率                                                |
| [On-demand Rendering（按需重繪）](/ux-design/knowledge-cards/on-demand-rendering/)                                           | 有要求才產生一幀的繪製方式——一個不停的驅動器讓整個畫面一直重繪                                                     |
| [Follow-through and Overlapping Action（跟隨動作與重疊動作）](/ux-design/knowledge-cards/follow-through-overlapping-action/) | 末端部位晚一點跟上、晚一點停下——用相位差、過衝曲線還是彈簧、幅度多大才看得出來                                     |
| [Rasterization（柵格化）](/ux-design/knowledge-cards/rasterization/)                                                         | 把幾何圖形轉成一格一格顏色值的那段工作——跑在 GPU 還是 CPU、剔除怎麼驗證沒畫錯                                      |
| [Damped Spring（阻尼彈簧）](/ux-design/knowledge-cards/damped-spring/)                                                       | 被拉向目標、略過頭再回來的數值變化——角頻率與阻尼比各決定什麼、什麼時候停掉驅動器                                   |
| [Specificity（特定性）](/ux-design/knowledge-cards/specificity/)                                                             | 兩條 CSS 規則搶同一個屬性時比的值——它排在 `!important` 與 cascade layer 之後，只替部分規則加權會打亂元件內部的勝負 |
| [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/)                                                       | 替設計決定取名、元件引用名字——數設計決定而不數值，primitive 與 semantic 兩層各管哪一種調整                         |
| [DTCG Format（具名設計值的交換格式）](/ux-design/knowledge-cards/dtcg-format/)                                               | 在設計工具、轉換工具與程式碼之間交換 token 的 JSON 格式——什麼時候當唯一來源、什麼時候手寫 CSS 自訂屬性就夠         |
| [Computed Style（計算後的樣式）](/ux-design/knowledge-cards/computed-style/)                                                 | 瀏覽器處理完層疊與繼承後元素實際套用的值——getComputedStyle 讀到哪一個階段、哪些狀態與元素讀不到                    |
| [Cascade Layer（層疊分層）](/ux-design/knowledge-cards/cascade-layer/)                                                       | `@layer` 的順序排在特定性之前——把對方的 CSS 放進較低的層何時會贏、自己放進 layer 何時反而會輸                      |
