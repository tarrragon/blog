---
title: "6.3 fuzz campaign"
date: 2026-04-23
description: "用自動化輸入探索覆蓋未知邊界：target 設計、corpus 管理、crash reproduction 與 CI 整合"
weight: 3
tags: ["backend", "reliability"]
---

## 概念定位

[Fuzz test](/backend/knowledge-cards/fuzz-test/) 把沒想過的輸入轉成可重播、可修補的失敗案例，補齊人工列舉無法觸及的邊界盲區。

這一頁處理的是輸入空間的盲區。當 API、parser、codec 或 schema 的邊界不清楚時，fuzz 比人工列案例更能覆蓋非預期路徑。

## 核心判讀

判讀 fuzz 的品質先看 target 選擇是否對準高風險輸入邊界，再看 corpus 是否持續收斂，最後看 crash 是否能轉成可回歸的修復。

重點判斷：

- fuzz target 是否足夠小，能對準單一責任
- corpus 是否持續收斂，coverage delta 是否仍為正
- crash reproduction 是否可重播到同一條路徑
- 修補後是否回寫成 regression test

## Fuzz target 設計

Fuzz target 是 fuzz campaign 的最小驗證單位，責任是把外部輸入導入一個可觀測邊界的函式。

好的 target 對準單一 parser、codec、serializer 或 validation function，函式簽章接受原始位元組（如 `func([]byte)` 或等效形式）。target 選擇的判準有三個：這個函式是否直接處理外部輸入、邊界行為是否不清楚、crash 是否有業務影響。

target 粒度影響 fuzz 的效率與判讀價值。target 太大（整個 HTTP handler 含 auth / routing / DB 存取）會讓 crash 難以定位到具體邊界，因為 fuzz engine 需要同時探索太多分支，coverage 增長慢且 crash 歸因模糊。target 太小（單一 if 分支）會讓 coverage 增長無意義，因為分支行為已經被 unit test 覆蓋。

常見的高價值 target 類型：

| Target 類型         | 典型邊界風險                       | 範例                                     |
| ------------------- | ---------------------------------- | ---------------------------------------- |
| Protocol parser     | 畸形封包、長度溢位、巢狀深度       | HTTP header parser、gRPC frame decoder   |
| Schema deserializer | 型別不匹配、缺欄位、巢狀物件遞迴   | JSON/Protobuf/MessagePack deserializer   |
| Image / media codec | buffer overflow、memory allocation | PNG decoder、PDF parser                  |
| Validation function | 邊界值、正則回溯、encoding 混淆    | email validator、URL parser、SQL escaper |
| Config parser       | 非預期組合、環境變數注入           | YAML/TOML config loader                  |

## Corpus 管理

Corpus 累積有效的輸入種子，讓 fuzz engine 能從已知邊界往外探索。corpus 品質直接決定 fuzz campaign 的探索效率。

初始 corpus 從三個來源收集：unit test 的既有 fixture（已知的合法與邊界輸入）、production sample 脫敏後的真實請求（反映實際流量的輸入結構）、schema 範例與文件中的合法樣本。初始 corpus 的重點是涵蓋主要合法路徑，讓 fuzz engine 從合法輸入開始 mutation，更容易觸達邊界。

持續擴充靠 coverage-guided mutation。fuzz engine 每次產生的 mutated input 若觸發了新的 code path（新分支、新呼叫），這個 input 會自動加入 corpus。隨著 campaign 進行，corpus 會累積越來越多能觸達深層分支的種子。

corpus 品質的判讀指標是 coverage delta trend — 每個時段新增的 code path 數量。coverage delta 持續為正代表 corpus 仍在有效探索；coverage delta 趨近零代表當前 target 的探索接近飽和，應考慮三個方向：切換到新 target、調整 mutation dictionary（加入 domain-specific token）、或擴充初始 corpus 的多樣性。

corpus 需要持久化管理。corpus 檔案應納入版本控制或 artifact storage，跨 CI job 保留。每次 fuzz campaign 結束時，新發現的有效種子合併回 corpus；crash input 在修復後轉成 regression fixture，從 fuzz corpus 移到 test fixture。

## Crash reproduction 與 minimization

Fuzz 找到 crash 後的處理流程是 reproduce → minimize → fix → 回灌 regression test。

**Reproduce**：用 fuzz engine 產出的 crash input 在相同環境重跑，確認 crash 可穩定觸發。不可穩定觸發的 crash 通常來自 race condition 或環境差異，需要額外的 concurrency 或環境控制才能定位。

**Minimize**：minimization 把觸發 crash 的輸入縮到最小等效形式，讓 root cause 更容易定位。自動化 minimizer（如 Go 內建的 fuzz minimizer、libFuzzer 的 `-minimize_crash=1`）會反覆刪減 input 中的位元組，保留能觸發同一 crash 的最小子集。minimized input 通常比原始 input 短一到兩個數量級，讓開發者能直接看出觸發條件。

**Fix 與 regression test**：修復 crash 後，用 minimized input 作為 fixture 寫成 regression test。這個 test 確保同類 bug 不再出現，也讓未來的 refactor 不會重新打開已修復的邊界。regression test 歸入 [CI pipeline](/backend/06-reliability/ci-pipeline/) 的 fast path，每次 push 都跑。

## CI 整合

Fuzz 在 CI 的執行模式跟 unit test 不同。unit test 有明確的 pass/fail 結束條件，fuzz campaign 是開放式探索，執行時間越長覆蓋越廣。

CI 整合分兩種模式，對齊 [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/) 的分層策略：

**Fast path regression**（30 秒至 5 分鐘）：用既有 corpus 跑 fuzz，確認已知邊界沒退化。這個模式的目標是 regression 檢查，每次 push 觸發。corpus 裡的種子已經覆蓋了過去發現的邊界，短時間跑完可以確保修復沒被破壞、新變更沒引入已知類型的 crash。

**Scheduled exploration**（小時級）：定期（每日或每週）跑長時間 fuzz，讓 engine 有足夠時間做深層 mutation 與路徑探索。新發現的種子合併回 corpus，crash input 產生 issue 或 alert。這個模式的 coverage delta 是判讀 campaign 價值的主要指標。

CI 整合的關鍵是 corpus 持久化。corpus 必須跨 job 保存（cache、artifact storage 或版本控制），每次 job 從上一次的 corpus 繼續探索。若 corpus 每次從零開始，fuzz engine 會重複探索已知路徑，浪費運算資源。

## Coverage 門檻與收斂判讀

Fuzz coverage 跟 unit test coverage 的意義不同。unit test coverage 衡量的是「多少行被執行過」，fuzz coverage 衡量的是「多少邊界被探索過」。同一個函式的 fuzz coverage 可以隨 corpus 擴充持續增長，因為 mutation 會觸發不同的分支組合。

判讀 fuzz campaign 是否仍有價值靠兩個指標：coverage delta trend（每小時新增多少 code path）與 corpus size growth（每小時新增多少有效種子）。兩者同時趨近零代表當前 target 的探索飽和。

飽和訊號指引兩個決策。第一，是否切換 target — 當前 target 的邊界已被充分探索，把 fuzz 資源移到另一個高風險 target 的邊際價值更高。第二，是否調整 mutation dictionary — 加入 domain-specific token（如 SQL keyword、JSON structure token、protocol magic bytes）可以讓 engine 更有效地觸達 domain-aware 的邊界。

## 案例對照

- [Google](/backend/06-reliability/cases/google/)：OSS-Fuzz 對大量基礎元件（parser、codec、serializer）做持續 fuzz，corpus 跨版本累積，crash 自動提 issue 並追蹤修復。這個規模的 fuzz campaign 說明 corpus 持久化與自動化 crash 處理是可擴展的前提。
- [Stripe](/backend/06-reliability/cases/stripe/)：API 與 serialization 邊界的 fuzz 需要 domain-specific dictionary（支付欄位、currency code、idempotency key 格式），通用 mutation 難以觸達業務語意上的邊界 crash。
- [GitHub](/backend/08-incident-response/cases/github/)：webhook payload 與 schema 邊界的 fuzz 適合用 schema-aware fuzzer，從 OpenAPI / JSON Schema 產生結構化 mutation，覆蓋嵌套物件與型別邊界。

## 判讀訊號

| 訊號                                       | 判讀條件                                                                 | 行動建議                                   |
| ------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------ |
| fuzz corpus 從未更新、覆蓋率停滯           | campaign 已失去探索價值 — 檢查是否需要換 target 或調整 mutation strategy | 換 target 或加 mutation dictionary         |
| crash 復現靠人工 minimization              | minimization 應自動化 — 手動 minimization 耗時且不可重複                 | 啟用 fuzzer 內建 minimizer 或接 CI 自動化  |
| fuzz 找到 bug 沒回灌成 regression test     | 修復後邊界可能被再次打開 — regression fixture 應歸入 CI fast path        | 把 minimized input 加入 CI regression 套件 |
| input boundary 無 spec、fuzz 範圍模糊      | target 選擇需要對齊 — 先定義哪些函式直接處理外部輸入                     | 盤點外部輸入函式、建立 target 清單         |
| production 出 crash 但 fuzz 沒抓到         | fuzz target 未覆蓋該輸入路徑 — 把 production crash input 加入 corpus     | 補 target + 把 crash input 加入 seed       |
| coverage delta 持續為零但仍在跑長時間 fuzz | 資源浪費 — 飽和後應切換 target 或調整 dictionary                         | 停止當前 campaign、轉移資源到新 target     |

## 交接路由

- [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)：fuzz regression 歸入 fast path、exploration 歸入 scheduled path
- [6.10 contract testing](/backend/06-reliability/contract-testing/)：schema fuzz 與契約驗證互補，contract 定義已知邊界、fuzz 探索未知邊界
- [6.16 test data](/backend/06-reliability/test-data-management/)：fuzz 找到的 crash input 沉澱成 seed 與 fixture
- [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/)：長時間 fuzz campaign 在 production-like 環境跑時需要資源邊界控制
- [6.8 release gate](/backend/06-reliability/release-gate/)：security-relevant fuzz crash 可作為 release 阻擋條件
- [8.9 事故型態庫](/backend/08-incident-response/incident-pattern-library/)：recurrent crash pattern 抽象化成型態
