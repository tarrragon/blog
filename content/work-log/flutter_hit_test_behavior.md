---
title: "Flutter HitTestBehavior：控制點擊命中測試的三種模式"
date: 2026-04-07
draft: false
tags: ["flutter"]
---

## 概念

當使用者點擊螢幕，Flutter 從 widget tree 根節點往下做 **hit test**（命中測試），判斷哪些 widget 被點擊命中。

`HitTestBehavior` 控制 GestureDetector **自己要不要算作被命中**，以及**如何影響子元件的命中判定**。

---

## 三種模式

### `deferToChild`（預設）

**「我自己不算，讓子元件決定」**

```text
GestureDetector (100x100)
  └── Container (50x50, 置中)
```

- 點擊 Container 範圍內 → Container 被命中 → GestureDetector **也算命中** → onTap 觸發
- 點擊 Container 範圍外（空白 padding）→ 沒有子元件被命中 → GestureDetector **不算命中** → onTap **不觸發**

適合：只想在子元件的可視範圍內接收點擊。

---

### `opaque`

**「整個區域都算我的，而且我擋住下面所有人」**

```text
GestureDetector (100x100)  ← 整個 100x100 都算命中
  └── Container (50x50, 置中)
```

- 點擊任何位置（包含空白處）→ GestureDetector **都算命中** → onTap 觸發
- 同時**阻擋**同層或下層的 widget 接收這個點擊

適合：需要一個「全範圍點擊區域」，例如整個螢幕的 barrier。

---

### `translucent`

**「整個區域都算我的，但我不擋別人」**

```text
GestureDetector (100x100)  ← 整個 100x100 都算命中
  └── Button (50x50, 置中)  ← Button 也算命中
```

- 點擊 Button 範圍 → **兩者都進入手勢競爭**（gesture arena），Button 更具體所以勝出
- 點擊空白處 → 只有 GestureDetector 參與 → onTap 觸發

適合：想在空白處接收點擊，但**不干擾子元件自身的手勢處理**。

---

## 手勢競爭（Gesture Arena）

當多個 widget 都被命中並註冊了同一種手勢（如 onTap），Flutter 透過 **gesture arena** 決定誰贏：

```text
外層 GestureDetector (onTap: close)
  └── 內層 GestureDetector (onTap: close, translucent)
        └── Button (onTap: doSomething)
```

- 點擊 Button → 三者都進入競爭 → **最深層（最具體）的 Button 勝出** → 只執行 `doSomething`
- 點擊空白處 → 只有外層和內層參與 → **內層勝出**（更具體）→ 執行 `close`

---

## 對照表

|                | deferToChild | opaque              | translucent        |
| -------------- | ------------ | ------------------- | ------------------ |
| 空白處命中？   | 否           | 是                  | 是                 |
| 阻擋下層？     | —            | 是                  | 否                 |
| 子元件能收到？ | 是           | 是（子元件更優先）  | 是（子元件更優先） |
| 典型用途       | 一般按鈕     | barrier、全螢幕手勢 | 透明背景 dialog    |

---

## 實際應用：透明 Dialog 點擊穿透

自訂 Dialog 使用透明背景時，點擊空白處無法關閉 Dialog，因為內容區域攔截了所有點擊事件。

## 解法：雙層 GestureDetector + HitTestBehavior

```dart
Get.dialog<String>(
  // 外層：攔截 Dialog 以外的區域（barrier）
  GestureDetector(
    behavior: HitTestBehavior.opaque,
    onTap: () => Get.back(),
    child: Center(
      // 內層：攔截 Dialog 內的空白區域，同時讓子元件參與手勢競爭
      child: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: () => Get.back(),
        child: Material(
          color: Colors.transparent,
          child: MyDialog(),
        ),
      ),
    ),
  ),
);
```

## 為什麼有效

- 外層 `opaque`：確保 Dialog 外的透明區域也能接收點擊
- 內層 `translucent`：Dialog 內的空白處觸發 `Get.back()`，但卡片和按鈕因為在 widget tree 中更深層（更具體），在手勢競爭中勝出，執行自身的 onTap/onPressed

## 點擊結果

| 點擊位置                    | 行為                                    |
| --------------------------- | --------------------------------------- |
| Dialog 外空白               | 外層 GestureDetector → 關閉             |
| Dialog 內空白（間距、標題） | 內層 GestureDetector → 關閉             |
| 卡片                        | 卡片自身 GestureDetector → 執行卡片邏輯 |
| 按鈕                        | 按鈕 onPressed → 執行按鈕邏輯           |
