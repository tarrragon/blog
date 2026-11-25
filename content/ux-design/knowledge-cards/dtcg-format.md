---
title: "DTCG Format（具名設計值的交換格式）"
date: 2026-11-25
description: "讀到 .tokens.json 檔、$value 與 $type 這類欄位，或要決定 design token 的來源檔該寫成 JSON 交給轉換工具產生 CSS 與各平台常數、還是直接手寫 CSS 自訂屬性時"
weight: 18
tags: ["ux-design", "knowledge-card", "design-token", "design-system", "dtcg", "json"]
---

DTCG Format（具名設計值的交換格式）是 W3C 的 Design Tokens Community Group（DTCG）制定的 JSON 檔案格式，用來在設計工具、轉換工具與程式碼之間交換 [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/)。第一個穩定版是 2025 年 10 月 28 日發布的 2025.10，由三份規格組成：Format Module 定義檔案結構與型別，Color Module 定義顏色值的寫法，Resolver Module 定義同一組 token 在不同情境（亮色與暗色主題、高對比模式）下取不同值的方式。三份都是社群小組的最終報告（Final Community Group Report），規格的狀態段寫明它不是 W3C 標準、也不在 W3C 的標準制定流程上；規格自稱穩定、可供實作。檔案的副檔名建議用 `.tokens` 或 `.tokens.json`，媒體型別建議用 `application/design-tokens+json`。

## 跟其他概念的關係

一份 DTCG 檔是巢狀的 JSON 物件。帶 `$value` 的物件是一個 token，不帶 `$value` 的物件是分組（group），token 的完整名稱是它從根往下經過的分組名加上自己的名字（`color.teal.500`）。以 `$` 開頭的欄位是保留字：`$type` 寫型別，寫在分組上時是分組內 token 的預設型別；`$description` 寫說明；`$deprecated` 標記停用；`$extensions` 放各工具自己的資料，工具讀寫時要原樣保留；`$extends` 讓一個分組繼承另一個分組的內容。token 的值可以引用另一個 token，寫成大括號包住完整名稱的 `"{color.teal.500}"`，也可以用 `$ref` 寫成 JSON Pointer；引用可以一層接一層，但不能繞回自己，形成循環時工具要報錯。

規格不定義 primitive token 與 semantic token 這類分層。規格寫明分組的劃分由作者任意決定，工具不應從分組推斷 token 的型別或用途；所以「只放數值的一層」與「用途命名、引用前一層的一層」在 DTCG 檔裡是兩個分組加上引用，分層是專案自己的命名約定，分層的條件與兩層各管哪一種調整在 [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/) 卡。

規格也不定義輸出成 CSS 的方式。把 DTCG 檔轉成 CSS 自訂屬性、Sass 變數、iOS 或 Android 常數的是轉換工具（translation tool），規格舉的例子是 Style Dictionary 與 Terrazzo；同一個 token 在 CSS 裡叫什麼名字、引用要輸出成 `var()` 還是解析後的值，依轉換工具而定（Style Dictionary 用 `outputReferences` 設定）。CSS 端的勝負規則（token 定義在哪個元素上、被哪一條規則蓋過）照 CSS 的層疊與 [Specificity（特定性）](/ux-design/knowledge-cards/specificity/) 決定，跟 DTCG 檔無關。

## 可觀察訊號與例子

專案用 DTCG 格式的訊號是 repo 裡有 `.tokens.json` 檔、JSON 的鍵是 `$value` 與 `$type`，CSS 或平台常數檔的開頭註明由工具產生、不要手改。下面這份檔用兩個分組寫出兩層：`size` 只放數值，`text` 用用途命名並引用 `size`。

```json
{
  "size": {
    "$type": "dimension",
    "md": { "$value": { "value": 16, "unit": "px" } },
    "lg": { "$value": { "value": 18, "unit": "px" } }
  },
  "text": {
    "body": { "$value": "{size.md}", "$description": "內文字級" },
    "prompt": { "$value": "{size.lg}", "$description": "題目需求的字級" }
  },
  "color": {
    "link": {
      "$type": "color",
      "$value": { "colorSpace": "srgb", "components": [0, 0.741, 0.89], "hex": "#00bde3" }
    }
  }
}
```

`text.body` 沒有寫 `$type`，它的型別取自它引用的 `size.md`。轉換工具保留引用時，產生的 CSS 類似 `--text-body: var(--size-md)`，`var()` 在宣告 `--text-body` 的那個元素上代換成值，所以執行時在同一個元素（通常是 `:root`）上改 `--size-md` 會連帶改到 `--text-body`，在子孫元素上改 `--size-md` 則不會，那一層要連 `--text-body` 一起重新宣告；工具輸出解析後的值時產生 `--text-body: 16px`，兩者之間的關係只留在 JSON 裡。

2025.10 規定 `dimension` 的值是 `value` 與 `unit` 兩個欄位的物件，`unit` 只能是 `px` 或 `rem`；`color` 的值是物件，`colorSpace`（`srgb`、`display-p3`、`oklch` 等十四種）與 `components` 必填，`alpha` 省略時當成 1，`hex` 是選填的六位數色碼，用途是給不支援該色彩空間的工具當備援。穩定版之前的草稿與許多既有的檔案把這兩種值寫成字串（`"#00bde3"`、`"16px"`），讀到字串寫法時，先確認手上的轉換工具支援哪一版的格式。

2026 年本站 SQL 練習頁的 token 直接寫在一份手寫的 CSS（`tokens.css`）裡，沒有用 DTCG 檔：token 只給網頁的 CSS 與一段讀 token 的 JavaScript 用，沒有其他平台或設計工具要讀同一份值（[CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](/work-log/css-token-refactor-verified-by-computed-style-diff/)）。

## 判斷條件與後果

同一組 token 要給兩種以上的讀取端用時（網頁與 Flutter App、程式碼與設計工具的外掛），DTCG 檔當唯一的來源、各平台的常數由轉換工具產生，換到的是一個值只改一處、每個平台拿到同一份值，設計工具支援這個格式時設計師改的也是同一份。付出的是多一道建置步驟，以及兩種表示法：讀 CSS 的人看到的是產生出來的檔案，要回 JSON 才改得到值，產生的檔案被手改時，下一次建置會蓋掉那次修改。

token 只給一個平台的 CSS 用、也沒有設計工具要讀時，手寫一份 CSS 自訂屬性的 token 檔就是來源，少一道建置與一種表示法；之後出現第二個讀取端時，再把這份檔轉成 DTCG 檔，名稱與分層照搬，因為兩邊都只是名字加引用。

規格的型別寫不出的值要另外處理：`dimension` 只收 `px` 與 `rem`，`em`、百分比、`vw` 這類單位，以及 `clamp()`、`calc()` 這類運算式，寫不成合法的 dimension token；規格的非規範段把百分比與比例列為之後可能補的型別。這些值留在 CSS 端手寫，或用 `$extensions` 記給特定工具讀；`$extensions` 裡的資料只有寫入它的那個工具讀得懂，換轉換工具時這些值要逐一重新對過。

亮色與暗色主題、品牌或密度這類情境切換，在 Resolver Module 裡寫成另一份 `.resolver.json`：`sets` 列出共用的 token 檔，`modifiers` 列出每一種情境（`theme` 的 `light` 與 `dark`）各自要疊上的 token 檔，`resolutionOrder` 決定疊加的先後，後面的覆蓋前面的。只有一個主題、或主題只在 CSS 端用 media query 或 class 切換時，用不到這一層。
