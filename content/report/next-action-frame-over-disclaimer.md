---
title: "用 Next-action frame 取代 Disclaimer：把 prohibition 翻成 actionable chain"
slug: "next-action-frame-over-disclaimer"
date: 2026-05-01
weight: 106
description: "當 audit / risk 識別 reader 不該做 X、寫作回應若停在 disclaimer 段（告訴 reader 不要 X）、整段自然產出 negative phrasing（不是 / ≠ / 不要）、即使逐句翻正向句法仍是 disclaimer。Reframe 成 next-action 段（告訴 reader 沿 chain 做 Y / Z）整段自然 positive、不需 contrast。Frame 選擇是 #94 正向改寫的上游問題——逐句正向化處理不到 frame 層、reframe 整段才會根治。"
tags: ["report", "事後檢討", "工程方法論", "Writing", "原則"]
---

## 核心原則

**Audit / risk 識別 reader 不該做 X 後、寫作回應的 frame 決定整段自然 positive 還是 disclaimer。** 兩個 frame：

| Frame             | 段落主體                               | Reader 拿到           | 自然句法          |
| ----------------- | -------------------------------------- | --------------------- | ----------------- |
| Disclaimer frame  | 告訴 reader「不要 X / X is dangerous」 | Prohibition + warning | Negative phrasing |
| Next-action frame | 告訴 reader「沿 chain 做 Y / Z」       | Chain 步驟 + 完成判準 | Positive phrasing |

兩 frame 對應同一個 risk、但 reader 拿到的東西不同。Disclaimer frame 自然產出負面陳述；逐句翻成正向句法後 frame 仍是 disclaimer、後續 multi-pass review 會繼續 catch 到負面殘餘。**整段 reframe 成 next-action chain 才是根治、不是字面換句。**

---

## 情境

實際 case：對資安 problem-node 章節跑 audit、找到 D2 Major weakness——「reader 拿章節層 control name 直接 ship、會產生 false sense of security」。寫作回應的選擇：

**v1（Disclaimer frame，直覺選擇）**：

> 章節給的是 routing layer、不是 implementation layer。判讀完成 ≠ 控制面實作完成。Reader 拿章節層 control 名稱直接 ship、會產生 false sense of security。

「不是」「≠」「會產生」一連串負面陳述。Multi-pass review catch 到、要求正向改寫。

**v2（Disclaimer frame + 字面正向化）**：

> 判讀完成代表 routing 階段交付；實作完成要靠 mechanism 層跟下游模組接續。Reader 拿章節層 control 名稱直接 ship、會建立 false sense of security——routing 跟 implementation 是兩個分開的交付里程碑。

字面去掉「不是」「≠」、但 frame 仍是 disclaimer——主軸是「警告 reader 別把 routing 當 implementation」、reader 拿到的仍是 prohibition + warning、actionable next step 隱含在「靠下游接續」一句。

**v3（Next-action frame，reframe 後）**：

> 本章交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：
>
> 1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 knowledge-card、那層展開機制 / 邊界 / context-dependence。
> 2. **Delivery chain**：「交接路由」欄位指向下游模組（05 / 06 / 08 視章節而定）、接配置 / 驗證 / 處置交付。
>
> Implementation 強度取決於兩條 chain 的完成度。

整段 positive、不需 contrast。Reader 拿到兩條 actionable chain + 完成判準。Risk 仍被處理（chain 不走完 = implementation 沒交付）、用「該做什麼」取代「不要做什麼」。

---

## 理想做法

寫 audit response 段前先問 frame：

### Frame 選擇判準

1. **本段給 reader 什麼？**
   - 「不要做 X」→ disclaimer frame（避開）
   - 「做 Y / Z」→ next-action frame（採用）

2. **能否把「不要 X」翻成「該做 Y / Z」？**
   - 多數 case 可以、因為 risk 通常對應 missing action
   - 例：「不要把 routing 當 implementation」= 「沿 mechanism + delivery 兩條 chain 走完」
   - 例：「不要用 universal mitigation」= 「對稱寫 in-scope + out-of-scope + 補強路由」（[#101](../threat-model-explicitness/)）
   - 例：「不要用名稱層 mitigation 對位」= 「補 mechanism + 前提兩層」（[#102](../mitigation-threat-alignment/)）

3. **段落主體寫 Y / Z chain、completeness 判準明示**
   - Chain 步驟具體可執行
   - 完成判準明示（reader 知道何時 chain 走完）

4. **若必須提到 risk、放段落結尾、subordinate 結構**
   - Risk 是 chain 不走完的後果、放段尾一行
   - Main flow 仍是 chain、risk 是 chain 失敗的描述
   - 例：「兩條 chain 走完，控制面交付完整。Chain 走不完，章節閱讀只完成 routing 階段。」

### 跟 #94 的分工

[#94 正向改寫保留對照論據](../positive-rewrite-preserves-contrast/) 處理「保留 contrast 怎麼正向」——適用於 contrast 是論述完整性必需的 case（X、不是 Y 是讀者直覺替代）。本卡處理「整段能否不需 contrast」——適用於 disclaimer frame 整段。

兩卡互補：

- 先跑本卡：能否 reframe 成 next-action？能 → 不需 contrast、整段自然 positive
- 再跑 #94：必須保留 contrast 的 case（reader 直覺替代是 Y、明確排除）→ 用「X、不是 Y」+ reasoning 結構

順序錯（先跑 #94 再考慮 reframe）= 在 disclaimer frame 內逐句正向化、frame 沒動、surface fix。

---

## 沒這樣做的麻煩

### Disclaimer 段反覆陷入字面 surface fix

整段 frame 是「不要 X」、逐句改 positive 後仍是「不要 X」變體。Multi-pass review 會反覆 catch 到負面殘餘、每次只改字面、frame 沒動。跟 [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) 同骨——字面層補丁不解行為層問題。

### Reader 拿到 prohibition、不知道 actionable next step

Disclaimer 給 reader 的 actionable 是「不要做」、但「該做什麼」reader 自己腦補。多 reader 各自腦補不同 next step、結果各不相同。Next-action frame 把 next step 寫進文字、跨 reader 一致。

### Self-case：本系列實際踩過

寫資安章節「從本章到實作」段時：

1. 第一次 batch（v1，8 章）：disclaimer frame、negative phrasing
2. Multi-pass review catch、第二次 batch（v2，8 章 sed 換句）：字面去否定詞、frame 仍 disclaimer
3. User 指出「應該重新思考為什麼這樣寫」：浮現 frame 議題、reframe v3

兩次 batch 改 8 章是高 cost surface fix；frame 反思在 v1 之前就該做、避開兩次無效 batch。**Disclaimer 段一出現、第一反應該是「能不能 reframe」、不是「怎麼把否定詞翻正向」。**

---

## 跟其他抽象層原則的關係

| 原則                                                                                                  | 關係                                                                                                                                     |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [#94 正向改寫保留對照論據](../positive-rewrite-preserves-contrast/)                                   | **本卡是 #94 的上游** — #94 處理「contrast 是論述完整性必需時怎麼正向」、本卡處理「整段能否不需 contrast」；frame 選對、#94 議題自然消失 |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                             | Disclaimer 是寫作便利（從 audit 警告語言抄）、跟 reader 意圖（actionable next step）反向；本卡是 #67 在 audit response 維度的展現        |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)                         | 把「不是」改「兩個分開」是字面 fix、reframe 整段是行為層 fix；本卡是 #82 在寫作 frame 的具體實例                                         |
| [#100 False sense of security 主要失敗模式](../false-sense-of-security-as-primary-failure/)           | Audit 識別 reader 風險、寫作端該翻成 actionable next step、不該照搬 audit 警告語言當 disclaimer                                          |
| [#88 Engine 不可調時把 transformation 移到外層](../transformation-at-outer-layer-when-engine-closed/) | 同骨 transformation 邏輯——prohibition 改 next-action 是把 transformation 移到 reader 動作層、不停在警告層                                |
| [#95 Multi-pass scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/)                      | Disclaimer frame 在多章重複時、batch surface fix 會在每章踩同樣 frame issue；reframe 要蓋整個 scope corpus、不只首章                     |
| [#83 Writing 的 multi-pass review](../writing-multi-pass-review/)                                     | 本卡補 multi-pass review 的 frame 軸——輪 3 機會成本語氣只 catch 字面絕對詞、frame 議題要在生成階段就反思、不能完全靠後輪 review          |

---

## 判讀徵兆

| 徵兆                                            | 該做的事                                                                   |
| ----------------------------------------------- | -------------------------------------------------------------------------- |
| 段落出現「不是」「≠」「不要」「不可以」連串     | 字面換句之前先檢查段落 frame 是否 disclaimer                               |
| 整段在告訴 reader「X 是 dangerous / 會產生 Y」  | Reframe：把 X 對應的 missing action 寫進段落主體                           |
| 字面翻成 positive 後、段落仍像警告              | Frame 沒換、reframe 整段為 next-action chain                               |
| Reader 讀完不知道下一步該做什麼                 | Disclaimer 沒給 actionable next step、補 chain                             |
| 同模板段在多章重複出現、每章都是負面 frame      | Frame 議題系統性、不是個案；改 frame + 考慮 SSoT 化（單一定義 + 各章引用） |
| Multi-pass review 反覆 catch 同段「絕對詞太多」 | 字面 fix 不解、reframe 段落                                                |
| Audit findings 直接抄進章節當警告               | Audit 語言是 reviewer 視角、章節 reader 需要 actionable chain              |

---

## 適用範圍與邊界

- **適用**：寫 audit / risk 的回應段、prohibition 段、warning 段、disclaimer 段；任何起手是「告訴 reader 不要做 X」的段落
- **不適用**：純 reference 段（不傳達 risk、純列 fact）、合規必填 disclaimer（法律 / 合約必須照規定文字）、安全告警（值班場景需要強烈警示語、reader 已是 expert）
- **邊界**：「Reframe 成 next-action」≠「刪掉所有警示」——risk 嚴重 / actionable 不明時、保留 warning subordinate 在段落結尾、main flow 仍是 next-action chain；判別準則：「reader 讀完段落、能否列出 next step？」能 → frame OK、不能 → 仍是 disclaimer
- **過度應用反例**：所有段都 reframe 成 next-action、把 reference / 規格段也改成「該做 Y」、reader 找不到 fact reference；frame 選擇對應段落責任、不是普世 rule

---

## 對 multi-pass review 的補丁

[#83 multi-pass review](../writing-multi-pass-review/) 的輪 3「機會成本語氣」目前只跑 grep 抓絕對詞（應該 / 必須 / 不行 / 不可以 / 正確）、catch 不到 frame 議題——disclaimer frame 段落的字面可能全 positive、但整段仍是 prohibition。

補丁：輪 3 加一條 frame 檢查問題：「**段落主體在告訴 reader 該做什麼、還是不該做什麼？**」——告訴不該做 → reframe；告訴該做 → frame OK。

這條檢查放在輪 3 是因為 frame 議題跟「絕對主義語氣」同軸、都是「告訴 reader 規則 vs 教 reader 思考」的延伸。**Frame 議題的根因檢查在輪 1 生成時更便宜**（生成段落時就問 frame）、輪 3 是 fallback safety net。
