---
title: "Engine 不可調時、把 transformation 移到外層"
date: 2026-04-26
weight: 88
description: "當底層 engine 沒開放某能力的客製 API、不該硬戳 engine 內部、改在 engine 的「輸入層」做 transformation。Search engine 不支援 substring → build-time 加 suffix tokens；LLM 不支援某 reasoning → prompt 層做 chain-of-thought；DB 不支援某 query → 預先 denormalize column；compiler 不可調 → source-level macro。本卡是 #45 外部組件合作四層 + #87 build-time vs runtime 的具體實作 pattern。"
tags: ["report", "事後檢討", "工程方法論", "Pattern", "Architecture"]
---

## 結論

當底層 engine（search engine、LLM、DB、compiler、framework）**沒開放某能力的客製 API**、不該硬改 engine 內部、改在 engine 的**輸入層 / 外層做 transformation**：

| Engine 限制                   | 外層 transformation                                                    |
| ----------------------------- | ---------------------------------------------------------------------- |
| Search engine 只 prefix match | Build-time emit suffix tokens（"backpressure" → 加 hidden "pressure"） |
| LLM 不會 CoT reasoning        | Prompt 層加「請逐步推理」instruction                                   |
| DB 不能 query JSON 內欄位     | 預先 denormalize 成獨立 column                                         |
| Compiler 不可調 lowering      | Source-level macro 展開                                                |
| Framework 沒 hook 點          | Wrapper component / proxy                                              |
| API rate limit 不能調         | Client-side batching / queueing                                        |

**核心原則**：engine 不開放 = 不要硬改 engine、改改你給 engine 的輸入。

---

## 為什麼移到外層是合理 escape

直覺反應遇到 engine 限制是「fork engine」「升級到能調的 engine」「換 engine」 — 但這三條都成本爆炸：

- **Fork engine**：維護 fork 成本（merge upstream changes、bug fix back-port）
- **升級**：可能需要等好幾版、可能 breaking change、可能根本沒得升
- **換 engine**：data migration、API 重寫、config 重學

**外層 transformation** 跳過這三條：

- 不動 engine 內部
- 用 engine 既有的合法 API（input、metadata、wrapper）
- 升級 engine 時 transformation 通常仍兼容
- 換 engine 時也常能直接搬

代價：

- 多一層 indirection
- 需要維護 transformation 邏輯
- 可能有 leak（transformation 不完美、edge case 露出 engine 限制）

通常代價遠小於三條「動 engine」路線。

---

## 五個跨領域實例

### 1. Search：suffix token injection

Pagefind / 多數 build-time search engine 只 prefix match。要支援 substring，build-time emit 額外 hidden tokens：

```html
<!-- 原文 -->
<p>backpressure handling</p>
<!-- transformation 後 -->
<p>backpressure handling</p>
<span hidden>pressure handling</span>
```

`grep "pre"` → matches `pressure` prefix → finds page。

### 2. LLM：prompt-level chain-of-thought

LLM 不會自動 CoT。在 prompt 層加：

```text
請先列出已知資訊、然後推理步驟、最後給出結論。
```

Engine 沒變、輸入變了、行為變了。

### 3. DB：denormalized columns

PostgreSQL JSON column query 慢、但:

```sql
ALTER TABLE events ADD COLUMN user_id_extracted UUID
  GENERATED ALWAYS AS (data->>'user_id') STORED;
CREATE INDEX ON events(user_id_extracted);
```

Engine 沒變、schema 加了 generated column、query 走 index、變快。

### 4. Compiler：source-level macros

C 語言沒泛型、用 `#define` macro 模擬：

```c
#define SWAP(a, b, T) do { T tmp = a; a = b; b = tmp; } while(0)
```

Compiler 沒變、source 經 preprocessor transformation、行為變了。

### 5. Framework：wrapper component

React 沒 onAttach lifecycle、用 wrapper:

```jsx
function withMount(Component) {
  return (props) => {
    useEffect(() => { props.onMount?.(); }, []);
    return <Component {...props} />;
  };
}
```

React 沒變、加一層 wrapper、行為加上了。

---

## 何時不該用外層 transformation

| 情境                                                                  | 為什麼                                                                                  |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Engine 開放了 API、有官方解                                           | 用官方、別自己 transformation                                                           |
| Transformation 跟 engine 行為衝突（例：injected tokens 影響 ranking） | 副作用大、考慮其他路                                                                    |
| Transformation 邏輯比 engine 還複雜                                   | 可能該換 engine 了                                                                      |
| Transformation 永遠 catch 不全 edge case                              | 用了會誤導、不如顯式說「不支援」（[#86 L1](../capability-gap-three-layer-escalation/)） |
| Engine 升級會破壞 transformation                                      | 維護成本長期高                                                                          |

五類共通：**transformation 的成本 / 風險 > 動 engine 的成本**。其他情境外層 transformation 是首選。

---

## 跟 #45 外部組件合作四層的關係

[#45](../external-component-collaboration-layers/) 講「離公共介面越近越穩」、本卡是這條原則的具體展開：

| #45 層次           | 本卡對應                            |
| ------------------ | ----------------------------------- |
| 公共介面層（最穩） | Engine 開放的 API                   |
| 邊界層             | **外層 transformation**（本卡焦點） |
| 內部結構層         | Engine 內部、不該動                 |
| 客戶端層           | Wrapper / proxy                     |

**外層 transformation 是邊界層的具體技法** — 在 engine 公共介面外、做 input / output transformation。

---

## 反模式

| 反模式                                        | 後果                                                 |
| --------------------------------------------- | ---------------------------------------------------- |
| 沒先試外層、直接 fork engine                  | 維護成本爆炸                                         |
| Transformation 寫得太聰明、catch 不全 case    | 看似 work、暗藏 silent failure                       |
| Transformation 跟 engine 預設行為衝突         | 結果不可預期                                         |
| 把 transformation 寫在 engine code 裡（混入） | 該升級 engine 時 transformation 跟著動、失去隔離價值 |
| Engine 升級後不重 review transformation       | 可能新版已支援、舊 transformation 變累贅             |
| Transformation 沒文件、只有 implicit comment  | 後人不懂為什麼 / 不敢碰                              |

---

## 跟其他抽象層原則的關係

| 原則                                                                          | 關係                                                                      |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [#45 外部組件合作四層](../external-component-collaboration-layers/)           | 本卡是「邊界層」的具體技法                                                |
| [#86 Capability gap 三層階梯](../capability-gap-three-layer-escalation/)      | 外層 transformation 多是 L2 augmenting computation 的實作方式             |
| [#87 Build-time vs Runtime](../build-time-vs-runtime-computation-spectrum/)   | Transformation 可放 build-time（suffix token）或 runtime（query rewrite） |
| [#73 search 匹配模式](../search-engine-matching-mode-mismatch/)               | search engine prefix-only 限制是本卡 case 1 的具體場景                    |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) | Transformation 是字面層 catch、適合 hook 自動化（build step）             |

---

## 判讀徵兆

| 訊號                                   | 該做的事                                     |
| -------------------------------------- | -------------------------------------------- |
| 「engine 不支援 X、所以 X 不能做」     | 檢查能不能在外層做 transformation            |
| 「我們需要 fork 這個 lib」             | 先試外層、多數情況夠                         |
| 「等 upstream 加 feature」             | 多半永遠等不到、外層先解                     |
| 「這個 hack 太醜、要改 engine」        | 醜不是換工具的理由、看實際 ROI               |
| Transformation 寫了沒文件              | 補 why、否則後人會誤拆                       |
| 同一 engine 累積 ≥ 3 種 transformation | 可能該換 engine 了                           |
| 升級 engine 後 transformation 沒測     | 可能新版 native 支援、舊 transformation 多餘 |

**核心**：Engine 限制不等於 capability 限制 — engine 沒開放的能力、通常可在 engine 的輸入 / 輸出層做 transformation 補上。**「engine 不支援」是表象、「我沒思考外層解」是根因**。
