---
title: "Collapse 是隱形預設：多維空間被壓成單格的三類典型"
date: 2026-05-18
weight: 125
description: "決策對話、決策呈現、批量輸出三個 surface 都有同一個 pattern — 高維選擇空間預設被 collapse 到 1-2 個窄格、且這個 collapse 因為「便利 / 合規 / 簡潔」被當成中性預設、不被覺察；#80 是 decision surface 上的極致 collapse、#79 是 dialogue 五維 collapse、#123 是 output framing 在 constraint 下 collapse；三者共骨：*某個高自由度空間被便利驅動 reduce 到最少格子*；對策不是去除 collapse、是讓 collapse 變顯性、由設計者決定要 collapse 哪一維、不是預設全 collapse"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "Collapse", "Default-design"]
---

## 結論

「Collapse」是同骨 pattern — 高維選擇空間被便利驅動 reduce 到最少格子、且這個 reduction 看似中性、實際藏掉維度。三個 surface 各自的 collapse 典型：

| Surface          | 高維原貌                                           | Collapse 後                                | 驅動力             | 對應卡                                           |
| ---------------- | -------------------------------------------------- | ------------------------------------------ | ------------------ | ------------------------------------------------ |
| Decision surface | 改 / 延後 / 疊加 / 分批 / 反問（多選空間）         | Yes / No 二選                              | 「最少字、最簡潔」 | [#80](../yes-no-binary-collapse/)                |
| Dialogue surface | 呈現格式 × 策略疊加 × 批次邊界 × 時間軸 × 選項類型 | 開放問 + 單策略 + 一次完成 + 立刻決 + 單選 | 「最容易寫的問句」 | [#79](../decision-dialogue-dimensions/)          |
| Output surface   | N 種 framing × 多種 cadence × 多軸敘事視角         | 單一 framing 複製 N 篇                     | 「合規最佳解」     | [#123](../compliance-optimum-converges-cadence/) |

三者共通結構：

1. 真實選擇空間是 *多維 / 多選*
2. 預設行為把它 *reduce 到 1-2 維 / 1 選*
3. 這個 reduction 看起來「合理 / 簡潔 / 合規」、不被覺察是 collapse
4. 後果是 *使用者 / 讀者被塞進最窄格子、要破格才能表達或回應*

---

## 為什麼 Collapse 是 default、不是 violation

跟其他「明確違規」不同、collapse 預設 *合規* — 沒有規則禁止 yes/no 問句、沒有規則禁止單一 framing、沒有規則禁止單一策略推薦。這是 collapse 最危險的特性：

| 違規類型 | 偵測機制                | Collapse 為什麼避開                          |
| -------- | ----------------------- | -------------------------------------------- |
| 字面違規 | hook / lint             | Collapse 沒有字面 pattern                    |
| 結構違規 | schema / linter         | Collapse 結構通常正確                        |
| 行為違規 | review                  | Collapse 看起來像「簡潔」                    |
| Collapse | 跨對話 / 跨批比對才浮現 | 單樣本看不出、要對照「完整高維」才知道缺維度 |

Collapse 是隱形預設、原因在 *對比標的不存在於眼前*。Yes/No 問句要 collapse 到 1 bit、需要使用者已經想過五維 collapse；五維 collapse 要看出、需要使用者已經理解 #79 五維框架；framing collapse 要看出、需要連讀多篇且預期有變體。沒有 *對照原型* 在眼前、collapse 看起來就是「正常」。

---

## Collapse 不是「該消除」、是「該變顯性」

對策不是去除 collapse — 多數情境下使用者 / 讀者確實受益於 reduction（不用每次都展開五維、不用每篇 cadence 都換）。對策是 *讓 collapse 變顯性*：

| 維度     | Collapse 隱性版    | Collapse 顯性版                                               |
| -------- | ------------------ | ------------------------------------------------------------- |
| Decision | 「OK 嗎？」        | 「我推薦 A、但 B / C 可選；想改方向、延後、或疊加？」         |
| Dialogue | 「你想怎麼做？」   | 「呈現 / 策略數 / 批次 / 時間 / 選項類型」五維各給預設 + 可改 |
| Output   | 全篇用同一 framing | Pilot phase 準備 3-5 個 framing 變體、輪替使用                |

顯性化的代價是 *寫的人多打字 / 多設計*、得益是 *接收方知道自由度在哪、可以選擇接受預設或破格*。預設展開、選窄格要證明 — 跟 #78「不互斥是預設」同條結構。

---

## 跨 surface 的判讀通則

判斷某個情境是不是 collapse、不是看「有沒有違規」、是問三個 diagnostic：

1. **真實選擇空間是幾維 / 幾選？** — 如果 ≥ 3、reduce 到 1-2 就是 collapse
2. **這個 reduction 是設計選擇還是預設?** — 設計選擇會有「為什麼選窄格」的論述、預設沒有
3. **接收方破格的成本是多少?** — 破格要破壞既有對話 / review / commit 結構就是高成本、表示 collapse 藏得深

三個 diagnostic 全 yes、就是隱形 collapse。

---

## 反模式

| 反模式                                    | 後果                                                      |
| ----------------------------------------- | --------------------------------------------------------- |
| 「簡潔」當作目的、不評估 collapse 副作用  | 把多維壓 1 bit、自以為對使用者好、實際藏掉維度            |
| 看不到的維度視為不存在                    | Decision space 真的有 N 維、不展開不代表只有 1 維         |
| 加更多 constraint 想解品質問題            | 越多 constraint、output space collapse 越快、品質反而下降 |
| 用 hook / lint 想擋 collapse              | Collapse 字面合規、hook 抓不到                            |
| 「預設好就好」做設計選擇                  | 沒評估高自由度的成本 / 效益、所有預設都選窄格             |
| 第一版定下來的 framing / 預設、之後不評估 | 第一版幾乎都是窄格、需要 iterate                          |

---

## 跟其他抽象層原則的關係

| 原則                                                                                       | 關係                                                                                                                                    |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| [#79 決策對話的五維度](../decision-dialogue-dimensions/)                                   | 子卡 — Dialogue surface 的 collapse；本卡上一層、把 #79 / #80 / #123 統一為跨 surface 同骨                                              |
| [#80 Yes/No 二選是隱式 collapse](../yes-no-binary-collapse/)                               | 子卡 — Decision surface 的極致 collapse；本卡是 #80 的 meta、列出其他 surface 上的同骨 case                                             |
| [#123 多重硬規範同時生效會把 cadence 推向便利解](../compliance-optimum-converges-cadence/) | 子卡 — Output surface 的 collapse；補上 batch writing 這個 surface 跟 decision / dialogue 並列                                          |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                  | Driver 卡 — 三類 collapse 的共同 driver 都是「便利」、便利驅動 collapse 是 #67 的具體 manifestation                                     |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)              | 補充偵測手段 — Collapse 屬 emergence 類、hook 抓不到、要 multi-pass review；#82 的 ceiling 在 collapse 上特別明顯                       |
| [#74 決策呈現格式](../decision-presentation-options-recommendation/)                       | Specific case — 給推薦不給選項是 decision surface 的 collapse 形式之一                                                                  |
| [#127 Process content 結構由最大差異維度決定](../content-structure-by-max-diff-dimension/) | 子實例 — Content structure surface 的 collapse；把 universal phased / 6-section 模板套到 5 種不同 type 是本卡在「結構 layer」的具體形態 |

---

## 判讀徵兆

| 訊號                                         | 該做的事                                                        |
| -------------------------------------------- | --------------------------------------------------------------- |
| 接收方反覆「破格」回應（用結構外的方式回答） | 你 collapse 太狠、展開維度                                      |
| 預設選項只有 1-2 個                          | 評估真實選擇空間、看是否藏掉維度                                |
| 「簡潔」「乾淨」是設計理由                   | 警訊 — 簡潔 / 乾淨可能是 collapse 的別名                        |
| 加新 constraint 後品質下降                   | Constraint collapse 了 output space、考慮拉開或加 anti-template |
| 想用 yes/no 結束對話                         | Decision collapse、改 multi-option                              |
| 批量輸出全篇同 framing                       | Output collapse、補 framing 變體                                |
| 「為什麼大家都這樣寫 / 都這樣回」            | 系統性 collapse、不是個別事件、查 driver 跟 constraint          |
| 設計新規範 / 新 default 時                   | 評估 collapse 副作用、不是只看「能不能用」                      |

**核心**：Collapse 是高維空間預設被 reduce 到 1-2 維、看似中性、實際藏掉維度。三個 surface（decision / dialogue / output）有同骨 collapse pattern、都被「便利 / 合規 / 簡潔」驅動、都需要顯性化。對策不是消除 collapse、是讓設計者主動選擇要 collapse 哪一維、預設展開、選窄格要證明。
